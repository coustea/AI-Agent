import json
import re
import time
from pathlib import Path

from langchain.tools import tool
from pptx import Presentation
from pptx.util import Inches, Pt

from app.utils.paths import WORKPLACE_DIR


_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_SLIDE_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*-\s+(.+)$", re.MULTILINE)


def _safe_filename(topic: str) -> str:
    safe = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50]
    return safe or "untitled"


def _split_sections(outline_markdown: str) -> list[tuple[str, str]]:
    matches = list(_SLIDE_RE.finditer(outline_markdown))
    if not matches:
        return [("内容概览", outline_markdown.strip())]

    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(outline_markdown)
        sections.append((match.group(1).strip(), outline_markdown[start:end].strip()))
    return sections


def _extract_bullets(section_body: str) -> list[str]:
    bullets = [item.strip() for item in _BULLET_RE.findall(section_body)]
    if bullets:
        return bullets[:5]

    fallback = [line.strip() for line in section_body.splitlines() if line.strip()]
    return fallback[:5] or ["待补充内容"]


@tool("save_ppt_file")
def save_ppt_file(topic: str, outline_markdown: str, file_path: str | None = None) -> str:
    """将 Markdown 大纲保存为本地 PPTX 文件，并返回文件路径、页数和标题索引。"""
    title_match = _TITLE_RE.search(outline_markdown)
    presentation_title = title_match.group(1).strip() if title_match else topic
    sections = _split_sections(outline_markdown)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = presentation_title
    if len(cover.placeholders) > 1:
        cover.placeholders[1].text = f"{topic} · 自动生成教学演示文稿"

    slide_titles = [presentation_title]
    for title, body in sections:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title
        slide_titles.append(title)

        text_frame = slide.placeholders[1].text_frame
        text_frame.clear()
        for idx, bullet in enumerate(_extract_bullets(body)):
            paragraph = text_frame.paragraphs[0] if idx == 0 else text_frame.add_paragraph()
            paragraph.text = bullet
            paragraph.level = 0
            paragraph.font.size = Pt(22)

    if file_path:
        target = Path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = WORKPLACE_DIR / "ppt"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{_safe_filename(topic)}_{int(time.time())}.pptx"

    prs.save(str(target))

    return json.dumps(
        {
            "file_path": str(target),
            "slide_count": len(prs.slides),
            "slide_titles": slide_titles,
        },
        ensure_ascii=False,
    )
