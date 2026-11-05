"""资源生成模块 (app.resource) —— 多智能体协作生成个性化学习资源。

核心结构：
- ``api.py``: FastAPI 路由
- ``service.py``: 资源任务与产物持久化服务
- ``orchestrator.py``: 线性阶段 + 并行 Worker 资源生成编排器
- ``validator.py``: 确定性结果校验与上游交接内容提取
- ``event.py``: SSE 实时事件发布与订阅
- ``schemas.py``: 统一请求/响应/运行时数据契约
- ``catalog.py``: 资源 Agent 静态目录
- ``agents/``: 资源生成智能体实现
"""
