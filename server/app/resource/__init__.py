"""资源生成模块 (app.resource) —— 多智能体协作生成个性化教学资源。

对齐 chat 模块架构模式：
- ``api.py``: FastAPI 路由与 SSE 快照推流端点
- ``service.py``: 资源任务编排、产物持久化与状态管理
- ``agent.py``: 课程总设计师 Lead Agent 执行循环
- ``tools.py``: 7 类子智能体执行工具
- ``hooks.py``: 运行快照观察容器与状态机
- ``schemas.py``: 统一请求/响应/运行时数据契约
- ``agents/``: 路径模块适配与智能体工厂定义
"""
