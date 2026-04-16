"""Chat tool: normalize content via LLM and write to markdown/docx/pdf file.

Strategy A — preserve original content, only fix structure and formatting.
For docx/pdf: LLM reads the corresponding skill and generates Python code,
              which is then executed to produce the file.
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import time
from pathlib import Path

from langchain.tools import tool

from app.chat.context import get_current_session_id, get_current_user_id
from app.infra.llm import get_fast_llm
from app.shared.paths import WORKPLACE_DIR
from app.tools.registry import register

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────

CHAT_DOC_DIR = WORKPLACE_DIR / "chat"
DEFAULT_FILE_TYPE = "markdown"
SUPPORTED_FILE_TYPES = {"markdown", "md", "docx", "pdf"}

_FILE_TYPE_SKILL_NAME: dict[str, str] = {
    "docx": "docx",
    "pdf": "pdf",
}

_BASE_NORMALIZE_PROMPT = """\
你是一个文档格式规范化助手。

## 任务
将传入的文本整理为结构清晰的 Markdown，**严格保留原文所有信息和表达**，不得删减、补充或改写。

## 通用规范
1. 标题层级：使用 # 表示标题层级（最多 4 级）
2. 段落：段落间保留一个空行
3. 列表：统一用 - 表示无序，1. 2. 3. 表示有序
4. 代码块：用 ``` 包裹并标注语言
5. 保留原文加粗、斜体等标记
6. 不添加原文没有的总结、导语、结尾

直接输出 Markdown，不加任何解释。"""

# ── Helpers ────────────────────────────────────────────────────


def _normalize_file_type(file_type: str) -> tuple[str, str]:
    raw = (file_type or "").strip().lower()
    if raw in {"", "markdown", "md"}:
        return "markdown", "md"
    if raw == "docx":
        return "docx", "docx"
    if raw == "pdf":
        return "pdf", "pdf"
    return DEFAULT_FILE_TYPE, "md"


def _safe_title(title: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", (title or "").strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80] or "untitled_document"


def _target_path(user_id: int, session_id: str, title: str, ext: str) -> Path:
    target_dir = CHAT_DOC_DIR / str(user_id) / session_id
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_title(title)}_{int(time.time())}.{ext}"
    return target_dir / filename


# ── Skill loading ──────────────────────────────────────────────

# Skills 现在在统一的 app/skills/ 目录下
_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
_skill_instructions_cache: dict[str, str] = {}


async def _read_skill_instructions(file_type: str) -> str | None:
    """Read skill instructions from unified skills directory."""
    from app.skills.manager import SkillManager
    skill_name = _FILE_TYPE_SKILL_NAME.get(file_type)
    if not skill_name:
        return None

    if skill_name in _skill_instructions_cache:
        return _skill_instructions_cache[skill_name]

    sm = SkillManager(skills_path=_SKILLS_DIR)
    await sm.load_all()
    instructions = sm.read_skill_instructions(skill_name)
    if instructions:
        _skill_instructions_cache[skill_name] = instructions
    return instructions


# ── Markdown normalization ────────────────────────────────────


async def _normalize_content(title: str, content: str, file_type: str) -> str:
    """Call fast LLM to normalize markdown structure without changing content."""
    parts = [_BASE_NORMALIZE_PROMPT]
    skill_body = await _read_skill_instructions(file_type)
    if skill_body:
        parts.append(
            f"\n\n## {file_type.upper()} 格式参考\n"
            f"以下是 {file_type} 格式的专业排版规范，请参考这些规范来组织文档结构：\n\n"
            f"{skill_body}"
        )
    system_prompt = "".join(parts)

    llm = get_fast_llm(temperature=0.0, max_tokens=8192)
    messages = [
        ("system", system_prompt),
        (
            "human",
            f"## 文档标题\n{title}\n\n## 目标格式\n{file_type}\n\n## 原始内容\n{content}",
        ),
    ]
    try:
        response = await llm.ainvoke(messages)
        text = response.content.strip()
        return text or content
    except Exception:
        logger.warning("LLM normalization failed, using original content", exc_info=True)
        return content


# ── Skill-driven file creation (docx/pdf) ─────────────────────


async def _create_file_via_skill(
    title: str,
    content: str,
    file_type: str,
    target_path: Path,
) -> None:
    """LLM reads the skill, generates Python code, then execute it to create the file."""
    skill_body = await _read_skill_instructions(file_type)

    libs_hint = {
        "docx": "python-docx (`from docx import Document, ...`)",
        "pdf": "reportlab (`from reportlab.platus import SimpleDocTemplate, Paragraph, Spacer, ...`) 或 pymupdf",
    }

    skill_section = ""
    if skill_body:
        skill_section = (
            f"\n## {file_type.upper()} 排版专家指南\n"
            f"请严格遵循以下规范来创建文档：\n\n{skill_body}\n"
        )

    prompt = (
        f"你是文档生成专家。请生成一段 Python 代码来创建一个高质量的 {file_type} 文件。\n\n"
        f"## 要求\n"
        f"- 输出路径: {target_path}\n"
        f"- 文档标题: {title}\n"
        f"- 使用库: {libs_hint[file_type]}\n"
        f"- 中文字体: 优先使用系统中文字体（如 PingFang SC、SimHei 等），或使用 reportlab 内置 CIDFont\n"
        f"- 代码必须自包含、可直接运行\n"
        f"- 只输出 Python 代码，不要任何解释\n"
        f"- 确保所有父目录存在（用 path.parent.mkdir(parents=True, exist_ok=True)）\n"
        f"{skill_section}"
        f"\n## 文档内容（请完整保留）\n{content}"
    )

    llm = get_fast_llm(temperature=0.0, max_tokens=8192)
    response = await llm.ainvoke([("human", prompt)])
    code = response.content.strip()

    code = re.sub(r"^```(?:python)?\s*\n", "", code)
    code = re.sub(r"\n```\s*$", "", code)

    script = WORKPLACE_DIR / f"_docgen_{int(time.time() * 1000)}.py"
    script.write_text(code, encoding="utf-8")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(WORKPLACE_DIR),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace").strip()
            raise RuntimeError(f"Code execution failed (exit {proc.returncode}):\n{err_msg}")

        if not target_path.exists():
            raise FileNotFoundError(f"File was not created at {target_path}")

    finally:
        script.unlink(missing_ok=True)


# ── Tool entry point ──────────────────────────────────────────


@tool("create_document_file")
async def create_document_file(
    title: str,
    content: str,
    file_type: str = DEFAULT_FILE_TYPE,
) -> dict:
    """Create a markdown/docx/pdf file with LLM-normalized content under chat/<user_id>/<session_id>/."""
    current_user_id = get_current_user_id()
    current_session_id = get_current_session_id()

    if current_user_id is None:
        return {
            "success": False,
            "title": title,
            "content": content,
            "file_type": file_type or DEFAULT_FILE_TYPE,
            "file_path": None,
            "error": "缺少当前用户上下文，无法创建文档。",
        }

    if not current_session_id:
        return {
            "success": False,
            "title": title,
            "content": content,
            "file_type": file_type or DEFAULT_FILE_TYPE,
            "file_path": None,
            "error": "缺少当前会话上下文，无法创建文档。",
        }

    normalized_type, ext = _normalize_file_type(file_type)
    body = (content or "").strip()
    if not body:
        return {
            "success": False,
            "title": title,
            "content": content,
            "file_type": normalized_type,
            "file_path": None,
            "error": "文档内容为空，无法创建文件。",
        }

    normalized = await _normalize_content(title, body, normalized_type)

    target = _target_path(current_user_id, current_session_id, title, ext)
    try:
        if normalized_type == "markdown":
            target.write_text(normalized, encoding="utf-8")
        else:
            await _create_file_via_skill(title, normalized, normalized_type, target)
    except Exception as exc:
        logger.exception("Failed to create document file")
        return {
            "success": False,
            "title": title,
            "content": normalized,
            "file_type": normalized_type,
            "file_path": None,
            "error": f"创建文档失败: {exc}",
        }

    return {
        "success": True,
        "title": title,
        "content": normalized,
        "file_type": normalized_type,
        "file_path": str(target),
        "error": None,
    }


# 自注册到工具注册表
register(create_document_file)