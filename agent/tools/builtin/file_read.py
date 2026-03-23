"""文件读取工具"""

from typing import Optional
from langchain_core.tools import tool
import os


@tool
async def file_read(file_path: str, max_chars: int = 10000) -> str:
    """异步读取文件内容。支持文本文件，限制最大读取字符数以防止内存溢出。"""
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"Error: File does not exist: {file_path}"
        
        # 检查是否为文件（而不是目录）
        if not os.path.isfile(file_path):
            return f"Error: Path is not a file: {file_path}"
        
        # 检查文件大小，防止读取过大的文件
        file_size = os.path.getsize(file_path)
        if file_size > max_chars:
            return f"Error: File is too large ({file_size} bytes). Maximum allowed: {max_chars} characters."
        
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [Content truncated. Showing first {max_chars} characters]"
        
        return content
    
    except UnicodeDecodeError:
        return f"Error: Unable to decode file as UTF-8: {file_path}"
    except PermissionError:
        return f"Error: Permission denied when reading file: {file_path}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"