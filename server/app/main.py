"""FastAPI application entry point."""

from __future__ import annotations

from app.app_factory import create_app

app = create_app()


if __name__ == "__main__":
    import subprocess
    import sys

    from app.config import HOST, PORT

    cmd = [
        sys.executable, "-m", "fastapi",
        "dev", "main.py",
        "--host", HOST,
        "--port", str(PORT),
    ]
    subprocess.run(cmd)
