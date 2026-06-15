"""FastAPI 应用入口文件。

负责创建应用实例，支持通过命令行直接运行开发服务器。
"""

from __future__ import annotations

# 从工厂模块导入应用创建函数
from app.app_factory import create_app

# 创建 FastAPI 应用实例（供 uvicorn / gunicorn 等 ASGI 服务器加载）
app = create_app()


# 直接运行此文件时，启动 FastAPI 开发服务器
if __name__ == "__main__":
    import subprocess
    import sys

    # 从配置中读取主机地址和端口号
    from app.config import HOST, PORT

    # 构建 fastapi dev 命令，支持热重载
    cmd = [
        sys.executable, "-m", "fastapi",
        "dev", "main.py",
        "--host", HOST,
        "--port", str(PORT),
    ]
    # 执行开发服务器启动命令
    subprocess.run(cmd)
