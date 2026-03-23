"""文件列表工具"""

from typing import Optional
from langchain_core.tools import tool
import os
from pathlib import Path


@tool
async def file_list(directory: str = ".", max_items: int = 100) -> str:
    """列出目录中的文件和子目录。默认列出当前目录，可指定其他目录路径。"""
    try:
        # 展开用户路径（如 ~/）
        directory = os.path.expanduser(directory)
        
        # 检查目录是否存在
        if not os.path.exists(directory):
            return f"Error: Directory does not exist: {directory}"
        
        # 检查是否为目录
        if not os.path.isdir(directory):
            return f"Error: Path is not a directory: {directory}"
        
        # 列出目录内容
        items = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            is_dir = os.path.isdir(item_path)
            size = "-" if is_dir else str(os.path.getsize(item_path))
            items.append({
                "name": item,
                "type": "DIR" if is_dir else "FILE",
                "size": size
            })
        
        # 限制返回项目数量
        if len(items) > max_items:
            items = items[:max_items]
            items.append({"name": f"... and {len(items) - max_items} more items", "type": "", "size": ""})
        
        # 格式化输出
        result = f"Contents of directory: {directory}\n"
        result += f"{'Name':<30} {'Type':<6} {'Size':<10}\n"
        result += "-" * 48 + "\n"
        
        for item in items:
            result += f"{item['name']:<30} {item['type']:<6} {item['size']:<10}\n"
        
        return result
    
    except PermissionError:
        return f"Error: Permission denied when accessing directory: {directory}"
    except Exception as e:
        return f"Error listing directory {directory}: {str(e)}"