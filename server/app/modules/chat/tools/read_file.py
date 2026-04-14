from langchain.tools import tool

from app.modules.chat.runtime_context import get_current_user_id
from app.modules.chat.services.attachments import (
    UPLOAD_DIR,
    read_uploaded_file_content,
    resolve_uploaded_path,
)


@tool("read_uploaded_file")
def read_uploaded_file(file_url: str) -> str:
    """读取当前用户上传的文档内容（PDF、DOCX、TXT、MD、LOG）。

    Args:
        file_url: 上传文件 URL，格式如 /api/v1/ai/chat/uploads/{user_id}/{session_id}/{filename}
    """
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return "读取失败：缺少用户上下文。"

    resolved = resolve_uploaded_path(file_url)
    if resolved is None:
        return f"无法解析文件路径: {file_url}。请确认文件 URL 格式正确且文件存在。"

    owner_id, absolute_path = resolved
    if owner_id != current_user_id:
        return "无权限读取该文件。"

    return read_uploaded_file_content(absolute_path)


@tool("list_uploaded_files")
def list_uploaded_files() -> str:
    """列出当前用户上传的所有文件。"""
    current_user_id = get_current_user_id()
    if current_user_id is None:
        return "读取失败：缺少用户上下文。"

    user_dir = UPLOAD_DIR / str(current_user_id)
    if not user_dir.exists():
        return "用户暂无上传文件。"
    files = [f for f in user_dir.rglob("*") if f.is_file()]
    if not files:
        return "用户暂无上传文件。"
    return "用户上传的文件列表:\n" + "\n".join(
        f"- {f.relative_to(user_dir)} ({f.stat().st_size} bytes)" for f in files
    )
