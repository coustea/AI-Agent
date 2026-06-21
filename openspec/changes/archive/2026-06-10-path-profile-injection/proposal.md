## Why

路径规划模块的教程生成环节完全缺失用户画像注入，导致所有学生拿到相同的教程内容，违背个性化学习核心理念。同时路径规划 Agent 使用原始 JSON 画像拼入 prompt，信息密度和 LLM 吸收率低于文字画像 Markdown。此外节点进入时缺少 `available → in_progress` 状态切换，导致状态流转链断裂。

## What Changes

- 教程生成（`_generate_tutorial_payload`）注入用户文字画像 Markdown，使 LLM 根据学习者画像调整内容深度、风格和侧重点
- 路径规划 Agent（`PathPlannerAgent`）的 strategist 节点改用文字画像 Markdown 替代 JSON 画像，提升 LLM 理解质量
- 节点进入工作空间（`get_node_workspace`）时自动将 `available` 状态切换为 `in_progress` 并记录 `started_at`
- 辅助资源类型白名单从 `{"mindmap", "code", "ppt"}` 扩充为 `{"mindmap", "code", "ppt", "content", "reading"}`
- 教程 prompt 模板增加画像上下文段落和个性化适配指令

## Capabilities

### New Capabilities
- `tutorial-profile-injection`: 教程生成时读取并注入用户文字画像，使教程内容根据学习者背景、知识水平、认知风格做个性化适配
- `planner-markdown-profile`: 路径规划 Agent 使用文字画像 Markdown 替代 JSON 画像，提升规划质量

### Modified Capabilities
- `path-node-lifecycle`: 节点状态流转增加 `available → in_progress` 自动切换
- `path-resource-types`: 辅助资源白名单扩充，支持 content 和 reading 类型

## Impact

- `app/path/service.py` — `_generate_tutorial_payload`、`get_node_workspace`、`run_path_generation_task`、`_generate_path_plan`、`AUX_RESOURCE_TYPES`
- `app/path/agents/planner.py` — `PathState`、`generate_plan`、`node_strategist_node`、`build_search_research_messages`
- `app/path/prompt_manager.py` — `render_tutorial` 新增 `profile_section` 参数
- `app/path/prompts/tutorial.md` — 增加画像上下文和适配指令占位符
- 无 API 接口变更，无数据库表结构变更，无破坏性改动
