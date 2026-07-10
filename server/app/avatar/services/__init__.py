"""
虚拟人服务导出模块。
"""

# 暴露数字人控制器，供其他模块使用
from app.avatar.services.avatar_ctrl import AvatarController

__all__ = ["AvatarController"]
