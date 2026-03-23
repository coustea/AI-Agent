import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "start_server:app", 
        host="0.0.0.0", 
        port=9999, 
        reload=True,
        reload_dirs=["."]
    )