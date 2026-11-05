"""全系统共享能力层 (app.shared)。

子模块架构（文件名与单一职责严格对齐）：
- ``tools/``: 全系统统一工具注册执行器 (``registry.py``)、沙箱路径安全 (``sandbox.py``)、技能加载 (``skills.py``) 及内置工具集 (``builtin/``)
- ``ppt/``: Plan-and-Execute python-pptx 课件智能体（``schemas.py``, ``workspace.py``, ``validator.py``, ``renderer.py``, ``agent.py``, ``tool.py``）
- ``cartoon/``: Plan-and-Execute HyperFrames 视频智能体（``schemas.py``, ``workspace.py``, ``validator.py``, ``renderer.py``, ``tts.py``, ``agent.py``, ``tool.py``）
"""
