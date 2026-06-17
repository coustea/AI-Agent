"""路径规划模块 — 学习路径的生成、查询、节点工作区、测验和评估。

核心组件：
- api.py        — FastAPI 路由，处理路径相关 HTTP 请求
- service.py    — 业务逻辑层，协调路径生成、节点管理、测验评分
- schemas.py    — 请求/响应/内部状态的 Pydantic 数据模型
- events.py     — 路径生成进度的事件总线（SSE 推送）
- validation.py — 路径规划结构校验与依赖环检测
- agents/       — LLM 智能体（规划器、节点学习）
- workflows/    — LangGraph 工作流（路径规划、节点学习）
"""
