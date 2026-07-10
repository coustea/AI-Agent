# 资源生成模块：聚合 api / service / orchestrator / agents / workflow 等子模块
"""资源生成模块 — 多智能体协作生成个性化学习资源。

核心组件：
- api.py           — FastAPI 路由，处理资源生成 HTTP 请求
- service.py       — 业务逻辑层，CRUD 用例，Agent ID 常量
- orchestrator.py  — 后台任务编排入口，协调 LangGraph 工作流
- event.py         — SSE 事件系统，实时推送 agent 状态变更
- agents/          — 资源生成智能体（content/mindmap/code/quiz/reading/ppt/video/cartoon）
- schemas/         — 请求/响应/运行时数据模型
- workflow/        — LangGraph 工作流（全局编排图 + 节点函数）
- prompts/         — LLM 提示词模板

注：路径规划模块的资源生成已统一使用 PathResourceRequest + generate_for_path 接口，
   不再依赖独立的 path_helpers.py 文件。
"""
