# 入口文件：直接运行 `python -m app.rag.indexing` 时调用构建主流程
from app.rag.indexing.build import main

if __name__ == "__main__":
    main()
