## Context

路径规划模块当前有两条画像获取路径：

1. `_get_profile_dict(user_id)` → 返回 `dict` (JSON)，用于 `WorkerState.profile`，被 quiz/code/mindmap 等 Resource Agent 消费
2. `get_user_learning_profile(user_id)` → 返回 `str` (Markdown)，新增方法，尚未被任何消费点调用

当前画像注入的缺失点：

- 教程生成（`_generate_tutorial_payload`）完全不读取画像，所有学生拿到相同教程
- 路径规划 Agent 使用 `json.dumps(profile_dict)` 拼入 prompt，LLM 吸收率低于自然语言画像
- 节点进入时无 `available → in_progress` 状态切换
- 辅助资源白名单只有 mindmap/code/ppt，content/reading 被拒绝

## Goals / Non-Goals

**Goals:**
- 教程生成根据用户画像做个性化内容适配（深度、风格、侧重点）
- 路径规划 Agent 使用文字画像 Markdown 替代 JSON，提升规划质量
- 补齐节点状态流转缺失的 `available → in_progress` 切换
- 辅助资源支持 content 和 reading 类型

**Non-Goals:**
- 不修改 `WorkerState.profile` 的接口格式（Resource Agent 仍用 JSON dict）
- 不修改数据库表结构
- 不修改 API 接口签名
- 不实现测验题目难度自适应（后续优化）
- 不实现断线重连事件补偿（后续优化）

## Decisions

### Decision 1：教程生成使用 Markdown 画像而非 JSON

**选择**：教程生成通过 `get_user_learning_profile()` 获取 Markdown 文字画像，直接注入 prompt。

**替代方案**：
- A) 使用 `_get_profile_dict()` 的 JSON + `json.dumps` 拼入 prompt — 当前 planner 的做法，但 LLM 对自然语言画像吸收率更高
- B) 同时传入 JSON + Markdown — 增加 prompt token 开销，信息冗余

**理由**：教程生成不走 `WorkerState`，是直接拼 prompt 的场景。Markdown 画像是已渲染的完整文字描述，包含 8 维度的中文摘要，对 LLM 更友好。新用户时返回 "暂无画像信息" 也不会影响 prompt 质量。

### Decision 2：PathState 同时保留 profile dict 和 profile_markdown

**选择**：`PathState` 新增 `profile_markdown: str` 字段，保留 `profile: dict`。

**理由**：
- `profile` (dict) 被 `_collect_search_evidence` 和 `build_search_research_messages` 使用
- `profile_markdown` (str) 被 `node_strategist_node` 用于生成规划
- 两者并存，各走各的消费路径，不破坏现有接口

### Decision 3：节点状态切换在 get_node_workspace 中触发

**选择**：在 `get_node_workspace` 中，当节点状态为 `available` 时自动切换为 `in_progress` 并记录 `started_at`。

**替代方案**：
- A) 前端主动调用状态更新接口 — 增加前端复杂度，且容易遗漏
- B) 在 `_create_tutorial` 时触发 — 语义不对，教程生成 ≠ 开始学习

**理由**：学生进入节点工作空间就等于开始学习，这是最自然的触发时机。

### Decision 4：辅助资源白名单扩充为 5 种

**选择**：`AUX_RESOURCE_TYPES` 从 `{"mindmap", "code", "ppt"}` 扩充为 `{"mindmap", "code", "ppt", "content", "reading"}`。

**理由**：
- `ALLOWED_RESOURCE_TYPES` 在 `schemas.py` 中已定义 6 种（含 quiz）
- `AGENT_REGISTRY` 中 content 和 reading Agent 已注册可用
- quiz 通过独立的 questions 接口，不走 resources 接口，所以不加入白名单

## Risks / Trade-offs

- **[Token 开销]** 教程 prompt 增加画像段落可能增加 500-1500 token → 画像 Markdown 截取前 2000 字符，控制开销
- **[画像为空]** 新用户没有画像时 `get_user_learning_profile` 返回默认文本 → prompt 中已有 fallback 处理，不影响生成
- **[状态切换副作用]** `get_node_workspace` 中的 commit 可能影响后续查询 → 在状态切换后 refresh session，确保一致性
- **[资源白名单扩充]** content 和 reading 类型的 Agent 生成速度可能较慢 → 异步生成，不阻塞响应
