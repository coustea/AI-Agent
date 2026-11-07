"""Chat 模块 —— 通用学习答疑。

模块职责结构（命名即职责，扁平内聚）：
- ``api.py``         HTTP 与 SSE 路由端点
- ``service.py``     运行入口、历史消息组装、后台任务调度
- ``harness/``       Agent 循环内核：纯循环 + 钩子 + 运行事件流
- ``tools.py``       Chat 工具注册与装配（基于 app.shared.tools 的 @tool）
- ``context.py``     从数据库构建历史消息列表与工具链清洗
- ``attachment.py``  上传存储、安全路径解析、文档提取、Vision 图片理解与预处理编排
- ``schemas.py``     数据契约 DTO
- ``memory/``        会话增量压缩与跨会话长期记忆
- ``prompts/``       Prompt 模板
"""

CHAT_MODULE_NAME = "mentor"

__all__ = ["CHAT_MODULE_NAME"]
