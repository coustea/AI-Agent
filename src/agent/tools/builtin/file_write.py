import logging
from pathlib import Path
from langchain_core import tool

logger = logging.getLogger(__name__)

@tool
def file_append(file_path: str, content: str) -> str:
    """
    将文本追加写入到指定文件中。如果文件或目录不存在会自动创建。
    极其适合用来写日志、保存笔记或记录 Learnings。
    参数:
    - file_path: 相对路径 (例如 ".learnings/ERRORS.md")
    - content: 要追加的多行文本内容
    """
    try:
        path = Path(file_path)
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 追加写入内容
        with path.open("a", encoding="utf-8") as f:
            f.write(content + "\n")  # 追加换行符分隔不同内容
        
        logger.info(f"成功将内容追加写入到 {file_path}")
        return f"成功将内容追加写入到 {file_path}"
    except Exception as e:
        logger.error(f"写入文件 {file_path} 时出错: {e}")
        return f"写入文件 {file_path} 时出错: {e}"