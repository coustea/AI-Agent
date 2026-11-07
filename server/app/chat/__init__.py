"""Chat 模块 —— 基于 learn-claude-code 的极简透明个性化辅导智能体。

模块扁平结构（7 个文件，命名即职责）：
- ``api.py``      HTTP 与 SSE 路由端点
- ``service.py``  会话 CRUD、附件上传、历史组装与后台运行调度
- ``agent.py``    核心 Agent 单循环与 RunStream 实时状态流
- ``tools.py``    工具箱注册与工具意图语义化描述器
- ``context.py``  本地附件存储、文档提取、s06 微压缩与多模态上下文组装
- ``memory.py``   s06 会话滚动摘要压缩与跨会话长期记忆管线
- ``schemas.py``  运行状态、步骤时间线、SSE 事件与历史消息 DTO
"""

CHAT_MODULE_NAME = "mentor"

__all__ = ["CHAT_MODULE_NAME"]
