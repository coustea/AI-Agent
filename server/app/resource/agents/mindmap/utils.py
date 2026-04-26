"""
思维导图生成工具函数。
"""

import json
import re
import time
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.shared.paths import RESOURCE_DIR

logger = get_logger(__name__)

NEED_MAP = {
    "exam": "考前突击 (侧重考点与易错题)",
    "review": "课后复习 (侧重知识梳理与图解)",
    "deep": "深度探究 (侧重底层原理与拓展)",
    "practice": "实践应用 (侧重代码或实操案例)",
}

_MARKDOWN_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
_ROOT_RE = re.compile(r"^#\s+.+$", re.MULTILINE)
_TOP_LEVEL_BRANCH_RE = re.compile(r"^-\s+.+$", re.MULTILINE)
_NESTED_BRANCH_RE = re.compile(r"^\s+-\s+.+$", re.MULTILINE)
_TITLE_RE = re.compile(r"^#\s+(.+)", re.MULTILINE)

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; overflow: hidden; }}
    #mindmap {{ width: 100%; height: 100vh; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.18.12"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.18.12"></script>
</head>
<body>
  <svg id="mindmap"></svg>
  <script>
    const {{ Transformer }} = window.markmap;
    const {{ Markmap }} = window.markmap;
    const transformer = new Transformer();
    const {{ root }} = transformer.transform({md_json});
    Markmap.create("svg#mindmap", {{}}, root);
  </script>
</body>
</html>"""


def extract_markdown_content(text: str) -> str:
    """从文本中提取 Markdown 内容。"""
    raw = (text or "").strip()
    if not raw:
        return ""
    match = _MARKDOWN_FENCE_RE.search(raw)
    if match:
        raw = match.group(1).strip()
    if "# " not in raw or "- " not in raw:
        return ""
    return _normalize_markdown_indent(raw)


def _normalize_markdown_indent(markdown_text: str) -> str:
    """标准化 Markdown 缩进。"""
    lines = markdown_text.splitlines()
    bullet_indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.lstrip(" ").startswith("- ")
    ]
    if not bullet_indents:
        return markdown_text.strip()
    min_indent = min(bullet_indents)
    if min_indent == 0:
        return markdown_text.strip()
    normalized = []
    for line in lines:
        if line.startswith(" " * min_indent):
            normalized.append(line[min_indent:])
        else:
            normalized.append(line)
    return "\n".join(normalized).strip()


def count_mindmap_nodes(markdown_text: str) -> int:
    """统计思维导图节点数量。"""
    if not markdown_text.strip():
        return 0
    lines = [line.strip() for line in markdown_text.splitlines() if line.strip()]
    return sum(1 for line in lines if line.startswith("# ") or line.startswith("- "))


def check_markdown_quality(markdown_text: str) -> tuple[bool, str, int]:
    """检查 Markdown 思维导图质量。"""
    node_count = count_mindmap_nodes(markdown_text)
    if not markdown_text:
        return False, "未检测到可用的 Markdown 思维导图内容。", node_count
    if not _ROOT_RE.search(markdown_text):
        return False, "导图缺少根节点标题，请以一级标题作为主题根节点。", node_count
    if len(_TOP_LEVEL_BRANCH_RE.findall(markdown_text)) < 3:
        return False, "导图结构过于单薄，一级分支至少需要 3 个。", node_count
    if len(_NESTED_BRANCH_RE.findall(markdown_text)) < 4:
        return False, "导图展开深度不足，请补充更多二级或三级节点。", node_count
    if node_count < 8:
        return False, "导图结构过于稀疏，请补充更多关键知识节点。", node_count
    return True, "", node_count


def render_markmap_html(markdown_text: str) -> str:
    """将 Markdown 渲染为 Markmap HTML。"""
    title_match = _TITLE_RE.search(markdown_text)
    title = title_match.group(1).strip() if title_match else "思维导图"
    md_json = json.dumps(markdown_text, ensure_ascii=False)
    return _HTML_TEMPLATE.format(title=title, md_json=md_json)


def save_mindmap_html(topic: str, html_content: str, user_id: int, resource_id: int) -> str:
    """保存思维导图 HTML 到文件。

    文件命名格式: mindmap_{user_id}_{resource_id}.html

    Args:
        topic: 主题（用于日志）
        html_content: HTML 内容
        user_id: 用户ID（必须）
        resource_id: 资源ID（必须）

    Raises:
        ValueError: 如果 user_id 或 resource_id 无效
    """
    if not user_id or not resource_id:
        raise ValueError(f"user_id 和 resource_id 必须为有效值: user_id={user_id}, resource_id={resource_id}")

    target_dir = RESOURCE_DIR / str(user_id) / str(resource_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"mindmap_{user_id}_{resource_id}.html"
    file_path = target_dir / file_name
    file_path.write_text(html_content, encoding="utf-8")
    logger.info("[MindmapUtils] 文件已保存: %s", file_path)
    return str(file_path)
