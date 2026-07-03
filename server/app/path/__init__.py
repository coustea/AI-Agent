"""路径规划模块 — 学习路径的生成、查询、节点工作区、测验和评估。

核心组件：
- api.py        — FastAPI 路由，处理路径相关 HTTP 请求
- service.py    — 业务逻辑层，协调路径生成、节点管理、测验评分
- schemas.py    — 请求/响应/内部状态的 Pydantic 数据模型
- event.py      — 路径生成进度的事件总线（SSE 推送）
- workflows.py  — LangGraph 工作流（路径规划、节点学习）
- prompts/      — 路径规划相关的 Prompt 模板目录

主要业务流程：
1. 路径规划：POST /path-plan → PathPlannerAgent → LearningPlan → 持久化
2. 节点学习：节点工作区 → 教程生成 → 测验评分 → 进度推进
3. 资源生成：节点资源请求 → NodeInput → resource 模块 agent → PathNodeResource
"""
