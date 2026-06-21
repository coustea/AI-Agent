## Why

资源 Agent 系统只有一个 `run(WorkerState)` 入口，路径规划调用时把节点上下文拼成字符串塞进 `learning_need`，导致 Agent 无法区分独立资源生成和路径节点生成两种场景，也无法为路径场景提供结构化的知识点、教程内容等输入。需要为每个 Agent 设计两个对等入口，分别面向多智能体系统调用和路径规划单独调用。

## What Changes

- **BREAKING**: 删除 `WorkerState` 和 `WorkerResult`，替换为 `ResourceInput`、`NodeInput`、`AgentResult`
- **BREAKING**: 删除 `BaseResourceAgent.run()`，替换为 `generate_resource(input: ResourceInput)` 和 `generate_node(input: NodeInput)`
- **BREAKING**: 删除 `run_single_agent_generation()`，不再需要单 Agent 封装
- 替换 `build_worker_base_context()` 为 `build_resource_context()` 和 `build_node_context()`
- 所有子 Agent（content/mindmap/code/ppt）实现两个入口，planning 和 review 的 `generate_node()` 返回 not-supported
- PPT 素材构建拆为 `build_resource_material()` 和 `build_node_material()`
- `ResourceService` 只调用 `generate_resource()`
- `PathService` 只调用 `generate_node()`，传入结构化节点上下文而非拼接字符串
- 路径节点资源类型限定为 `content`、`mindmap`、`ppt`、`code`（去掉 reading 和 quiz）
- `PathNodeResource` 补齐 `summary`、`status`、`error_message`、`input_json` 字段
- 前端路径节点资源按钮由 `resource_policy` 驱动，支持 4 种类型

## Capabilities

### New Capabilities
- `agent-dual-entry`: Agent 双入口机制 — `generate_resource()` 和 `generate_node()` 两个对等入口，以及 `ResourceInput`、`NodeInput`、`AgentResult` 三种运行时类型
- `node-input-context`: 路径节点结构化输入 — `NodeInput` 携带知识点、教程内容、生成重点等结构化字段，替代字符串拼接

### Modified Capabilities
- `resource-service-orchestration`: ResourceService 编排逻辑从 `agent.run(WorkerState)` 切换到 `agent.generate_resource(ResourceInput)`
- `path-node-resource-generation`: PathService 节点资源生成从 `agent.run(WorkerState)` 切换到 `agent.generate_node(NodeInput)`，资源类型收窄为 4 种

## Impact

- **后端核心**: `resource/schemas.py`、`resource/agents/base.py`、`resource/agents/common.py`、6 个 Agent 实现、`resource/service.py`、`resource/items.py`、`resource/review.py`、`path/service.py`、`path/schemas.py`
- **PPT 子系统**: `ppt_models.py`、`ppt_sources.py`、`ppt.py`
- **数据库**: `infra/models.py`（PathNodeResource 加字段）、`init_schema.sql`（加列和索引）
- **前端**: `learning/model/path.ts`、`LearningPathNode.vue`、`PathResourceDetail.vue`
- **测试**: 新增 `test_agent_dual_entry.py`、`test_path_node_resource_agents.py`，更新现有测试
