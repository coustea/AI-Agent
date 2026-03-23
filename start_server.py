import sys
import os

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from api.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app", 
        host="0.0.0.0", 
        port=9999, 
        reload=True,
        reload_dirs=["."]
    )