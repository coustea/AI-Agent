import os
import time
import re
from pathlib import Path

# 获取 server/ 根目录 (当前位于 app/modules/resource_generator/tools/file_saver.py)
SERVER_DIR = Path(__file__).resolve().parents[4]
WORKPLACE_DIR = SERVER_DIR / "workplace"

def save_to_workplace(sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
    """
    将内容保存到 workplace 下的指定子目录，文件名按主题+时间戳生成。
    
    Args:
        sub_dir: workplace 下的子目录名（如 "content", "code" 等）
        topic: 文件主题（用于文件名）
        content: 要写入的文件内容
        ext: 文件扩展名（不含点，默认为 "md"）
        
    Returns:
        保存的绝对文件路径
    """
    target_dir = WORKPLACE_DIR / sub_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 净化 topic 名称，去除非法字符并限制长度
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    if not safe_topic:
        safe_topic = "untitled"
        
    filename = f"{safe_topic}_{int(time.time())}.{ext}"
    filepath = target_dir / filename
    
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)
