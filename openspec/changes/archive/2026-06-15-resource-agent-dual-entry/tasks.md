## 1. 替换运行时类型

- [x] 1.1 在 `server/app/resource/schemas.py` 中删除 `WorkerState` 和 `WorkerResult`，添加 `AgentResult`、`ResourceInput`、`NodeInput`
- [x] 1.2 创建 `server/tests/resource/test_agent_dual_entry.py`，验证新类型可实例化且旧类型已删除

## 2. 替换 Base Agent 入口方法

- [x] 2.1 在 `server/app/resource/agents/base.py` 中删除 `run()` 和 `_execute()`，添加 `generate_resource()` 和 `generate_node()` 抽象方法及 `emit_start`/`emit_finish` 事件辅助方法
- [x] 2.2 更新 `AGENT_REGISTRY` 的 TYPE_CHECKING 导入，从 WorkerState/WorkerResult 改为 ResourceInput/NodeInput/AgentResult

## 3. 替换公共上下文构建器

- [x] 3.1 在 `server/app/resource/agents/common.py` 中删除 `build_worker_base_context()`，添加 `build_resource_context(ResourceInput)` 和 `build_node_context(NodeInput)`
- [x] 3.2 在测试文件中追加 `test_build_resource_context` 和 `test_build_node_context` 测试

## 4. 重构 Content Agent

- [x] 4.1 在 `server/app/resource/agents/content.py` 中将 `_execute()` 拆为 `generate_resource()`、`generate_node()` 和 `_generate_content()` 私有方法
- [x] 4.2 替换 WorkerState/WorkerResult 导入为 ResourceInput/NodeInput/AgentResult

## 5. 重构 Mindmap、Code Agent

- [x] 5.1 在 `server/app/resource/agents/mindmap.py` 中将 `_execute()` 拆为 `generate_resource()`、`generate_node()` 和 `_generate_mindmap()` 私有方法
- [x] 5.2 在 `server/app/resource/agents/code.py` 中将 `_execute()` 拆为 `generate_resource()`、`generate_node()` 和 `_generate_code()` 私有方法

## 6. 重构 PPT 素材模型与构建

- [x] 6.1 在 `server/app/resource/agents/ppt_models.py` 中添加 `NodeMaterialContext` 模型，扩展 `MaterialBundle` 增加 `source_type` 和 `node_context` 字段
- [x] 6.2 在 `server/app/resource/agents/ppt_sources.py` 中将 `build_material_bundle()` 替换为 `build_resource_material(ResourceInput)` 和 `build_node_material(NodeInput)`
- [x] 6.3 在 `server/app/resource/agents/ppt.py` 中将 `run()`/`_execute()` 替换为 `generate_resource()`、`generate_node()` 和 `_run_pipeline()` 私有方法

## 7. 重构 Planning 和 Review Agent

- [x] 7.1 在 `server/app/resource/agents/planning.py` 中将 `run()` 替换为 `generate_resource()`，添加 `generate_node()` 返回 not-supported
- [x] 7.2 在 `server/app/resource/agents/review.py` 中将 `run()` 替换为 `generate_resource()`，添加 `generate_node()` 返回 not-supported

## 8. 更新 ResourceService

- [x] 8.1 在 `server/app/resource/service.py` 中将 `run_multi_agent_generation()` 的 WorkerState 替换为 ResourceInput，将 `agent.run(state)` 替换为 `agent.generate_resource(input)`
- [x] 8.2 删除 `run_single_agent_generation()` 函数
- [x] 8.3 更新 `save_worker_result()` 和 `results_for_review()` 中的 WorkerResult 类型注解为 AgentResult
- [x] 8.4 在 `server/app/resource/items.py` 中将 WorkerResult 替换为 AgentResult
- [x] 8.5 在 `server/app/resource/review.py` 中将 WorkerResult 替换为 AgentResult

## 9. 更新路径数据库模型

- [x] 9.1 在 `server/app/infra/models.py` 的 PathNodeResource 中添加 `summary`、`status`、`error_message`、`input_json` 字段
- [x] 9.2 在 `server/init_schema.sql` 的 path_node_resources 表中添加对应列和 GIN 索引

## 10. 重构 PathService 节点资源生成

- [x] 10.1 在 `server/app/path/schemas.py` 中将 `AuxiliaryResourceRequest.resource_type` 扩展为 `Literal["content", "mindmap", "code", "reading", "quiz", "ppt"]`，扩展 `LearningPathResourceDTO` 添加 summary/status/error_message/input_data 字段
- [x] 10.2 在 `server/app/path/service.py` 中删除 `_generate_auxiliary_resource_payload()`，添加结构化 NodeInput 构建和 agent.generate_node() 调用
- [x] 10.3 在 `generate_node_resource()` 中调用 `agent.generate_node(node_input)` 替代 `agent.run(state)`
- [x] 10.4 更新 `AUX_RESOURCE_TYPES` 为 `{"content", "mindmap", "code", "reading", "quiz", "ppt"}`

## 11. 更新前端路径资源类型与按钮

- [x] 11.1 在 `src/features/learning/model/path.ts` 中扩展路径资源类型和 DTO 字段
- [x] 11.2 在 `src/features/learning/views/LearningPathNode.vue` 中将硬编码资源按钮替换为 resource_policy 驱动
- [x] 11.3 在 `src/features/learning/views/PathResourceDetail.vue` 中支持 content/mindmap/ppt/code/reading/quiz 渲染

## 12. 清理旧运行时引用

- [x] 12.1 在 server/app 和 server/tests 中搜索并替换所有 WorkerState/WorkerResult 残留引用
- [x] 12.2 确认所有 AGENT_REGISTRY 中的 Agent 都不再暴露 `run()` 方法

## 13. 验证

- [x] 13.1 运行 `cd server && uv run pytest tests/resource tests/path -q` 确认测试通过（179 passed, 4 pre-existing failures unrelated to refactor）
- [x] 13.2 运行 `cd .. && npm run build` 确认前端编译通过
- [x] 13.3 运行 `rg -n "WorkerState|WorkerResult" server/app server/tests` 确认无残留（仅 test 中 assert not hasattr 检查）
