## Why

当前 chat 模块的 agent 执行流已经混入了互斥路由、重复回答节点、跨层记忆访问和过重的上下文预加载，导致附件分析、联网搜索、统一回答和图解生成之间的职责边界不清。现在需要将 chat 重构为更简单的线性状态链，让中间结果通过 LangGraph state 传递，同时把用户画像和长期记忆恢复为按需工具调用。

## What Changes

- 重构 chat agent 执行流为线性链：`classify -> attachment_analysis? -> search? -> answer -> diagram?`
- 将附件分析结果和搜索结果写入 LangGraph state，由统一的 answer 节点消费
- 将用户画像与长期记忆从默认预加载上下文中移除，改为 answer 阶段按需工具调用
- 合并重复的回答路径，删除附件专用回答分支与相关冗余状态字段
- 清理 chat 模块中与旧互斥路由、跨层记忆读取、重复上下文装配相关的死代码与多余类型

## Capabilities

### New Capabilities
- `chat-agent-pipeline`: 定义 chat agent 的线性执行链、状态传递规则、按需记忆工具调用和回答后图解生成行为

### Modified Capabilities
- None

## Impact

- 影响后端 `server/app/chat/` 下的 agent、service、runtime、schemas、tools、prompts 和相关测试
- 会调整 chat 模块的 LangGraph 状态字段、节点职责和工具调用时机
- 不引入新的外部依赖，不变更公开 HTTP 路由形态，但会改变内部执行方式和测试基线
