"""
Worker Agent 工具函数集合。

包含：
- Workspace 文件产物系统
- Markdown 转 HTML
- 文件读写工具
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from app.infra.logging import get_logger
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)

MAX_FILE_SIZE = 1024 * 1024  # 1MB

# manifest 缓存（简单实现，避免频繁读取文件）
_manifest_cache: dict[str, dict[str, Any]] = {}


# =============================================================================
# Workspace 目录管理
# =============================================================================

def get_workspace_dir(user_id: int, resource_id: int) -> Path:
    """获取 workspace 目录路径。"""
    return RESOURCE_DIR / str(user_id) / str(resource_id)


async def init_workspace(user_id: int, resource_id: int) -> Path:
    """初始化 workspace，创建目录结构和 manifest.json。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID

    Returns:
        workspace 目录路径
    """
    workspace_dir = get_workspace_dir(user_id, resource_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = workspace_dir / "manifest.json"
    if not manifest_path.exists():
        initial_manifest = {
            "user_id": user_id,
            "resource_id": resource_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized",
            "agents": {},
        }
        content = json.dumps(initial_manifest, ensure_ascii=False, indent=2)
        await write_file_atomic(manifest_path, content, workspace_dir)
        _manifest_cache[f"{user_id}_{resource_id}"] = initial_manifest
        logger.info("[Workspace] 初始化完成: %s", workspace_dir)

    return workspace_dir


async def read_manifest(user_id: int, resource_id: int) -> dict[str, Any]:
    """读取 manifest.json。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID

    Returns:
        manifest 字典
    """
    cache_key = f"{user_id}_{resource_id}"
    if cache_key in _manifest_cache:
        return _manifest_cache[cache_key]

    workspace_dir = get_workspace_dir(user_id, resource_id)
    manifest_path = workspace_dir / "manifest.json"
    content = await read_file_safe(manifest_path, workspace_dir)
    if content is None:
        return {}

    manifest = json.loads(content)
    _manifest_cache[cache_key] = manifest
    return manifest


async def update_manifest(user_id: int, resource_id: int, updates: dict[str, Any]) -> None:
    """更新 manifest.json。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        updates: 要更新的字段
    """
    manifest = await read_manifest(user_id, resource_id)
    manifest.update(updates)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

    workspace_dir = get_workspace_dir(user_id, resource_id)
    manifest_path = workspace_dir / "manifest.json"
    content = json.dumps(manifest, ensure_ascii=False, indent=2)
    await write_file_atomic(manifest_path, content, workspace_dir)

    cache_key = f"{user_id}_{resource_id}"
    _manifest_cache[cache_key] = manifest
    logger.debug("[Workspace] Manifest 已更新: %s", list(updates.keys()))


# =============================================================================
# Agent 状态与产物管理
# =============================================================================

async def update_agent_status(
    user_id: int,
    resource_id: int,
    agent_name: str,
    status: str,
    artifact_path: str | None = None,
    error: str | None = None,
) -> None:
    """更新 Agent 执行状态。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称
        status: 状态
        artifact_path: 产物路径
        error: 错误信息
    """
    manifest = await read_manifest(user_id, resource_id)
    agents = manifest.get("agents", {})

    if agent_name not in agents:
        agents[agent_name] = {
            "status": status,
            "dependencies": [],
            "artifact_path": artifact_path,
            "error": error,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        agents[agent_name]["status"] = status
        if artifact_path:
            agents[agent_name]["artifact_path"] = artifact_path
        if error:
            agents[agent_name]["error"] = error
        if status in ("completed", "failed", "skipped"):
            agents[agent_name]["completed_at"] = datetime.now(timezone.utc).isoformat()

    await update_manifest(user_id, resource_id, {"agents": agents})


async def write_agent_artifact(
    user_id: int,
    resource_id: int,
    agent_name: str,
    content: str,
    file_type: str = "md",
) -> str:
    """写入 Agent 产物。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称
        content: 产物内容
        file_type: 文件类型

    Returns:
        产物文件路径
    """
    workspace_dir = get_workspace_dir(user_id, resource_id)
    artifact_path = workspace_dir / f"{agent_name}.{file_type}"
    return await write_file_atomic(artifact_path, content, workspace_dir)


async def read_agent_artifact(
    user_id: int,
    resource_id: int,
    agent_name: str,
    file_type: str = "md",
) -> str | None:
    """读取 Agent 产物。

    Args:
        user_id: 用户 ID
        resource_id: 资源 ID
        agent_name: Agent 名称
        file_type: 文件类型

    Returns:
        产物内容或 None
    """
    workspace_dir = get_workspace_dir(user_id, resource_id)
    artifact_path = workspace_dir / f"{agent_name}.{file_type}"
    return await read_file_safe(artifact_path, workspace_dir, MAX_FILE_SIZE)


# =============================================================================
# 文件读写工具
# =============================================================================

def validate_path(path: Path, base_dir: Path) -> bool:
    """校验路径安全，防止目录穿越攻击。"""
    try:
        resolved = path.resolve()
        base_resolved = base_dir.resolve()
        return str(resolved).startswith(str(base_resolved))
    except Exception:
        return False


async def write_file_atomic(path: Path, content: str, base_dir: Path) -> str:
    """原子写入文件（tmp → rename）。

    Args:
        path: 目标文件路径
        content: 文件内容
        base_dir: 基础目录（用于安全校验）

    Returns:
        文件路径字符串
    """
    if not validate_path(path, base_dir):
        raise ValueError(f"Invalid path: {path}")

    fd, tmp_path = tempfile.mkstemp(dir=base_dir, suffix=".tmp")
    try:
        async with aiofiles.open(fd, "w", encoding="utf-8") as f:
            await f.write(content)
        await aiofiles.os.rename(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    logger.info("[FileUtils] 文件已写入: %s", path)
    return str(path)


async def read_file_safe(path: Path, base_dir: Path, max_size: int = MAX_FILE_SIZE) -> str | None:
    """安全读取文件，限制大小。

    Args:
        path: 文件路径
        base_dir: 基础目录（用于安全校验）
        max_size: 最大文件大小

    Returns:
        文件内容或 None（文件不存在）
    """
    if not path.exists():
        return None

    if not validate_path(path, base_dir):
        raise ValueError(f"Invalid path: {path}")

    stat = await aiofiles.os.stat(path)
    if stat.st_size > max_size:
        raise ValueError(f"File too large: {stat.st_size} > {max_size}")

    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return await f.read()


# =============================================================================
# Markdown 转 HTML
# =============================================================================

def markdown_to_mindmap_html(markdown: str, title: str = "知识思维导图") -> str:
    """将 Markdown 列表转换为交互式思维导图 HTML。

    Args:
        markdown: Markdown 格式的思维导图内容
        title: HTML 页面标题

    Returns:
        完整的 HTML 字符串
    """
    html_lines = _convert_markdown_lists_to_html(markdown)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
        }}
        .mindmap-container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .mindmap-title {{
            text-align: center;
            font-size: 28px;
            color: #333;
            margin-bottom: 30px;
            font-weight: 600;
        }}
        .mindmap-tree ul {{
            list-style: none;
            padding-left: 25px;
            margin: 10px 0;
        }}
        .mindmap-tree li {{
            position: relative;
            padding: 8px 0 8px 20px;
            margin: 5px 0;
            border-left: 2px solid #667eea;
        }}
        .mindmap-tree li::before {{
            content: '';
            position: absolute;
            left: -2px;
            top: 50%;
            width: 20px;
            height: 2px;
            background: #667eea;
        }}
        .mindmap-tree li:last-child {{
            border-left-color: transparent;
        }}
        .mindmap-tree > ul {{
            padding-left: 0;
        }}
        .mindmap-tree > ul > li {{
            border-left: none;
            padding-left: 0;
        }}
        .mindmap-tree > ul > li::before {{
            display: none;
        }}
        .node {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }}
        .node.level-0 {{
            font-size: 18px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .node.level-1 {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        .node.level-2 {{
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }}
        .node.level-3 {{
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
    </style>
</head>
<body>
    <div class="mindmap-container">
        <h1 class="mindmap-title">{title}</h1>
        <div class="mindmap-tree">
{html_lines}
        </div>
    </div>
</body>
</html>"""


def _convert_markdown_lists_to_html(markdown: str) -> str:
    """将 Markdown 列表转换为 HTML 树形结构。"""
    lines = markdown.strip().split("\n")
    html_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        level = indent // 2 if indent > 0 else 0

        # 移除列表标记
        if stripped.startswith("- ") or stripped.startswith("* "):
            content = stripped[2:]
        elif stripped.startswith("# "):
            content = stripped[2:]
            level = 0
        elif stripped.startswith("## "):
            content = stripped[3:]
            level = 1
        elif stripped.startswith("### "):
            content = stripped[4:]
            level = 2
        else:
            content = stripped

        # 生成节点
        node_class = f"level-{min(level, 3)}"
        html_parts.append(f'            <li><span class="node {node_class}">{content}</span></li>')

    # 包装成 ul 结构
    if html_parts:
        return "            <ul>\n" + "\n".join(html_parts) + "\n            </ul>"
    return ""
