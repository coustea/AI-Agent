# 认证数据模型汇总：统一从 request/response 导出 Schema，作为其他模块的单一导入入口
"""认证模块数据模型汇总。

从 request.py 和 response.py 统一导出请求/响应 Schema，
保持向后兼容性，便于其他模块从单一入口导入。
"""

# 导入请求相关的数据模型
from app.auth.request import UserLogin, UserRegister, UserUpdate
# 导入响应相关的数据模型
from app.auth.response import UserRead

# 定义公开导出的符号列表
__all__ = ["UserRegister", "UserLogin", "UserUpdate", "UserRead"]
