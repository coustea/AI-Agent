## Context

当前 `server/app/chat/` 已经具备 LangGraph、附件分析、搜索工具、教学图解和 chat 私有记忆管线，但这些能力之间的关系仍然偏“互斥路由树”。当前实现中存在几个主要问题：一是附件回答和普通回答分成了多套路径；二是 service 和 agent 同时承担上下文装配与记忆读取职责；三是图解节点和回答节点仍会跨层直接访问记忆服务；四是默认上下文持续膨胀，降低了 agent 的可控性。

这次重构的直接目标不是增加能力，而是把现有能力重新组织成更简单的执行链，并删除与旧模型绑定的多余状态、重复节点和死代码。

## Goals / Non-Goals

**Goals:**
- 将 chat agent 执行流收敛为线性状态链，而不是互斥分叉树
- 保留 LangGraph state，让附件分析结果和搜索结果自然传入 answer 节点
- 让画像和长期记忆成为 answer 阶段的按需工具，而不是 service 每轮预加载的上下文
- 合并重复回答逻辑，统一最终回答入口
- 清理 chat 模块中与旧执行流冲突的多余类型、字段和测试基线

**Non-Goals:**
- 不重写 chat 私有记忆压缩和长期记忆算法本身
- 不新增外部依赖或替换现有 LLM / LangGraph 框架
- 不改变公开聊天 API 的基础输入输出形态
- 不在本次重构中引入复杂的并行 fan-out / join 图结构

## Decisions

### 1. 使用线性节点链而非复杂计划节点
保留 `classify`，但其职责仅限于判断是否需要附件分析、搜索和图解，以及设置轻量执行标记。后续节点按顺序执行：附件优先、搜索次之、统一回答、图解后置。这样可以保留流程可读性，并避免为简单 if 逻辑引入多余图节点。

备选方案：
- 使用专门的 `plan` 节点生成执行计划对象。未采用，因为当前需求简单，计划节点会让图结构复杂化。
- 将附件分析和搜索完全移出 LangGraph。未采用，因为用户希望这些中间结果明确写入状态并被统一消费。

### 2. 将附件分析和搜索结果视为前置证据，而不是最终回答草稿
`attachment_analysis` 和 `search` 节点只负责生成中间结果：
- `attachment_analysis_context`
- `search_result`
- `search_sources`

这些结果写入 state，统一由 answer 节点使用。这样可以避免搜索节点替回答、附件节点自带回答逻辑等职责重叠。

备选方案：
- 保留 `attachment_answer` 作为附件专用回答节点。未采用，因为它会和统一 answer 阶段形成重复实现。

### 3. 画像和长期记忆默认不进入初始上下文
`TutorAgentContext` 和初始 state 只承载本轮必要输入与准备上下文，不默认注入 learner profile 或 long-term memory。answer 阶段保留对应工具，以便模型在真正需要个性化连续性时自行读取。

备选方案：
- service 每轮预先注入 profile / memory。未采用，因为会扩大 prompt、增加噪音，并让 service 与 agent 的职责再次重叠。

### 4. 统一最终回答入口
无论当前轮是否有附件、是否需要搜索，最终都进入同一个 `answer` 节点。该节点统一消费：
- 当前消息与 recent history
- session summary
- 附件分析结果（如有）
- 搜索结果（如有）

并在信息不足时追加调用 profile / memory / extra search 工具。

备选方案：
- 保留 direct answer 和 attachment answer 两套路径。未采用，因为会造成 prompt、日志、持久化和测试的双份维护。

### 5. 图解节点只依赖最终回答
`diagram` 节点只在文本回答完成后运行，只读取：
- 当前问题
- `answer_text`
- 当前 state 中已有的必要上下文

它不再单独跨层访问记忆服务，避免再次扩大节点职责。

## Risks / Trade-offs

- **[Risk] 统一 answer 节点后 prompt 变重** → Mitigation: 保持 search / attachment 只提供摘要化证据块，避免重复拼装长文本
- **[Risk] 按需记忆工具调用可能增加单轮不确定性** → Mitigation: 在 answer prompt 中明确何时适合调用 profile / long-term memory
- **[Risk] 删除旧状态字段可能影响现有测试与日志** → Mitigation: 同步更新测试基线，收敛日志字段并保留必要兼容信息
- **[Risk] 线性顺序牺牲部分并行性能** → Mitigation: 当前优先目标是流程稳定与职责清晰，后续若有性能瓶颈再评估并行化

## Migration Plan

1. 先收敛 `TutorState`、`TutorAgentContext` 和 runtime 初始状态字段
2. 再重写 agent 图结构，移除重复回答节点与旧路由分支
3. 将附件分析与搜索节点改为中间结果节点，并接入统一 answer 节点
4. 将默认个性化上下文注入改为 answer 阶段按需工具使用
5. 更新 diagram 节点、service 编排代码和相关测试
6. 删除已无调用路径的旧函数、旧状态字段和废弃工具接线

回滚策略：若重构过程中发现线性链无法覆盖关键场景，可临时保留旧 graph 分支并以 feature branch 方式恢复；但目标状态不保留长期双轨实现。

## Open Questions

- answer prompt 中对“何时调用 profile / long-term memory”是否需要进一步拆成明确规则段落
- search 节点是否继续保留自动兜底多搜索源策略，还是在本次重构中一并收敛
- service 当前依赖前端 `history` 作为近端上下文来源，这一事实是否在后续单独重构为“后端自取 recent messages”
