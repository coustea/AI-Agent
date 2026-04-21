"""
文档处理工具集。

提供 DOCX / PDF 生成与导出能力：
- save_docx_file: 从 Markdown 内容生成 .docx 文档
- extract_pdf_text: 从 PDF 文件提取文本
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from app.infra.logging import get_logger
from app.shared.paths import WORKPLACE_DIR
from app.tools.registry import register

logger = get_logger(__name__)

DOCX_OUTPUT_DIR = WORKPLACE_DIR / "docx"
PDF_OUTPUT_DIR = WORKPLACE_DIR / "pdf"


@tool("save_docx_file")
def save_docx_file(
    title: str,
    content: str,
    style: str = "default",
) -> str:
    """将 Markdown 内容转换为 .docx 文档并保存。

    Args:
        title: 文档标题，用于文件命名和文档内首标题
        content: Markdown 格式的文档内容
        style: 文档风格 (default / academic / report)
    """
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # 设置默认字体
    style_obj = doc.styles['Normal']
    font = style_obj.font
    font.name = '微软雅黑'
    font.size = Pt(12)

    # 标题
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 解析 Markdown
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # 代码块
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code_text = '\n'.join(code_lines)
            code_para = doc.add_paragraph(code_text)
            code_para.style = doc.styles['Normal']
            for run in code_para.runs:
                run.font.name = 'Consolas'
                run.font.size = Pt(10)
            i += 1
            continue

        # 标题
        if line.startswith('#### '):
            doc.add_heading(line[5:].strip(), level=4)
        elif line.startswith('### '):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith('## '):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith('# '):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith('- ') or line.startswith('* '):
            doc.add_paragraph(line[2:].strip(), style='List Bullet')
        elif re.match(r'^\d+\.\s+', line):
            text = re.sub(r'^\d+\.\s+', '', line)
            doc.add_paragraph(text.strip(), style='List Number')
        elif line.startswith('---'):
            doc.add_paragraph('─' * 50)
        elif line.startswith('|') and '|' in line[1:]:
            # 简单表格处理：第一行为表头
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                row_text = lines[i].strip()
                if not re.match(r'^\|[\s\-]+\|$', row_text):
                    cells = [c.strip() for c in row_text.split('|')[1:-1]]
                    table_lines.append(cells)
                i += 1
            if table_lines:
                cols = max(len(row) for row in table_lines)
                table = doc.add_table(rows=len(table_lines), cols=cols)
                table.style = 'Table Grid'
                for row_idx, row_data in enumerate(table_lines):
                    for col_idx, cell_text in enumerate(row_data):
                        if col_idx < cols:
                            table.rows[row_idx].cells[col_idx].text = cell_text
            continue
        else:
            # 普通段落
            para = doc.add_paragraph()
            # 简单粗体处理
            parts = re.split(r'\*\*(.+?)\*\*', line)
            for j, part in enumerate(parts):
                run = para.add_run(part)
                if j % 2 == 1:
                    run.bold = True

        i += 1

    # 保存
    DOCX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(title) + ".docx"
    filepath = DOCX_OUTPUT_DIR / filename
    doc.save(str(filepath))

    result = {
        "file_path": str(filepath),
        "title": title,
    }
    logger.info("[save_docx_file] saved: path=%s", filepath)
    return json.dumps(result, ensure_ascii=False)


# ── PDF 文本提取 ───────────────────────────────────────────────

@tool("extract_pdf_text")
def extract_pdf_text(
    file_path: str,
    *,
    max_pages: int = 50,
) -> str:
    """从 PDF 文件提取文本内容。

    Args:
        file_path: PDF 文件的绝对路径
        max_pages: 最多提取的页数，默认 50
    """
    path = Path(file_path)
    if not path.exists():
        return f"文件不存在: {file_path}"
    if not path.suffix.lower() == '.pdf':
        return f"不是 PDF 文件: {file_path}"

    try:
        import pymupdf

        doc = pymupdf.open(str(path))
        pages_to_read = min(len(doc), max_pages)
        text_parts: list[str] = []

        for page_idx in range(pages_to_read):
            page = doc[page_idx]
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- 第 {page_idx + 1} 页 ---\n{text.strip()}")

        doc.close()
        result = "\n\n".join(text_parts)

        if not result.strip():
            return "PDF 文件中未提取到文本内容（可能是扫描件或纯图片 PDF）"

        # 截断保护
        if len(result) > 15000:
            result = result[:15000] + f"\n\n... (已截断，共 {len(result)} 字符)"

        logger.info("[extract_pdf_text] extracted: path=%s pages=%d len=%d", file_path, pages_to_read, len(result))
        return result

    except Exception as e:
        logger.error("[extract_pdf_text] failed: path=%s error=%s", file_path, e)
        return f"PDF 提取失败: {e}"


# ── PDF 生成 ───────────────────────────────────────────────────

def _register_chinese_font():
    """注册中文字体供 reportlab 使用。优先使用系统中文字体，回退到 CIDFont。"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    font_name = "ChineseFont"
    try:
        pdfmetrics.getFont(font_name)
        return font_name
    except Exception:
        pass

    # 尝试注册 macOS 系统中文字体
    import platform
    if platform.system() == "Darwin":
        mac_font_paths = [
            "/System/Library/Fonts/STSong.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
        from reportlab.pdfbase.ttfonts import TTFont
        for fp in mac_font_paths:
            if Path(fp).exists():
                try:
                    pdfmetrics.registerFont(TTFont(font_name, fp))
                    return font_name
                except Exception:
                    continue

    # 回退：使用 reportlab 内置 CID 字体（STSong-Light）
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception:
        pass

    return "Helvetica"


@tool("save_pdf_file")
def save_pdf_file(
    title: str,
    content: str,
) -> str:
    """将 Markdown 内容转换为 PDF 文档并保存。

    Args:
        title: 文档标题，用于文件命名和文档内首标题
        content: Markdown 格式的文档内容
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak,
        Table, TableStyle, ListFlowable, ListItem,
    )

    font_name = _register_chinese_font()

    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(title) + ".pdf"
    filepath = PDF_OUTPUT_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    # 样式定义
    base_size = 11
    styles = {
        "title": ParagraphStyle(
            "Title", fontName=font_name, fontSize=22,
            alignment=TA_CENTER, spaceAfter=12 * mm, spaceBefore=6 * mm,
            leading=28,
        ),
        "h1": ParagraphStyle(
            "H1", fontName=font_name, fontSize=18,
            spaceBefore=8 * mm, spaceAfter=4 * mm, leading=24,
            textColor=colors.HexColor("#1a1a1a"),
        ),
        "h2": ParagraphStyle(
            "H2", fontName=font_name, fontSize=15,
            spaceBefore=6 * mm, spaceAfter=3 * mm, leading=20,
            textColor=colors.HexColor("#2c3e50"),
        ),
        "h3": ParagraphStyle(
            "H3", fontName=font_name, fontSize=13,
            spaceBefore=4 * mm, spaceAfter=2 * mm, leading=17,
            textColor=colors.HexColor("#34495e"),
        ),
        "body": ParagraphStyle(
            "Body", fontName=font_name, fontSize=base_size,
            spaceBefore=2 * mm, spaceAfter=2 * mm, leading=17,
            firstLineIndent=22,
        ),
        "code": ParagraphStyle(
            "Code", fontName="Courier", fontSize=9,
            spaceBefore=2 * mm, spaceAfter=2 * mm, leading=13,
            backColor=colors.HexColor("#f5f5f5"),
            borderColor=colors.HexColor("#e0e0e0"),
            borderWidth=0.5,
            borderPadding=4,
        ),
        "bullet": ParagraphStyle(
            "Bullet", fontName=font_name, fontSize=base_size,
            spaceBefore=1 * mm, spaceAfter=1 * mm, leading=17,
            leftIndent=20, bulletIndent=8,
        ),
        "numbered": ParagraphStyle(
            "Numbered", fontName=font_name, fontSize=base_size,
            spaceBefore=1 * mm, spaceAfter=1 * mm, leading=17,
            leftIndent=20, bulletIndent=8,
        ),
    }

    story: list = []

    # 文档标题
    story.append(Paragraph(_escape_xml(title), styles["title"]))
    story.append(Spacer(1, 4 * mm))

    # 解析 Markdown 并转为 reportlab 元素
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # 代码块
        if line.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(_escape_xml(lines[i]))
                i += 1
            code_text = "<br/>".join(code_lines) if code_lines else ""
            if code_text:
                story.append(Paragraph(code_text, styles["code"]))
            i += 1
            continue

        # 标题
        if line.startswith("#### "):
            story.append(Paragraph(_escape_xml(line[5:].strip()), styles["h3"]))
        elif line.startswith("### "):
            story.append(Paragraph(_escape_xml(line[4:].strip()), styles["h2"]))
        elif line.startswith("## "):
            story.append(Paragraph(_escape_xml(line[3:].strip()), styles["h1"]))
        elif line.startswith("# "):
            story.append(Paragraph(_escape_xml(line[2:].strip()), styles["h1"]))
        elif line.startswith("- ") or line.startswith("* "):
            text = _format_inline_markdown(line[2:].strip())
            story.append(Paragraph(f"• {text}", styles["bullet"]))
        elif re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line)
            text = _format_inline_markdown(text.strip())
            story.append(Paragraph(text, styles["numbered"]))
        elif line.startswith("---"):
            story.append(Spacer(1, 3 * mm))
        elif line.startswith("|") and "|" in line[1:]:
            # 表格处理
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_text = lines[i].strip()
                if not re.match(r"^\|[\s\-]+\|$", row_text):
                    cells = [_escape_xml(c.strip()) for c in row_text.split("|")[1:-1]]
                    table_lines.append(cells)
                i += 1
            if table_lines:
                cols = max(len(row) for row in table_lines)
                # 补齐列数
                for row in table_lines:
                    while len(row) < cols:
                        row.append("")
                table = Table(table_lines, colWidths=[doc.width / cols] * cols)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
            continue
        else:
            text = _format_inline_markdown(line)
            story.append(Paragraph(text, styles["body"]))

        i += 1

    doc.build(story)

    result = {
        "file_path": str(filepath),
        "title": title,
    }
    logger.info("[save_pdf_file] saved: path=%s", filepath)
    return json.dumps(result, ensure_ascii=False)


def _escape_xml(text: str) -> str:
    """转义 XML 特殊字符，防止 reportlab Paragraph 解析报错。"""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _format_inline_markdown(text: str) -> str:
    """将 Markdown 行内格式（粗体、行内代码）转为 reportlab XML 标记。

    先提取 Markdown 标记片段，对其余部分做 XML 转义，再拼接标签。
    """
    parts: list[str] = []
    # 按粗体和行内代码分片
    pattern = re.compile(r"(\*\*(.+?)\*\*|`(.+?)`)")
    last = 0
    for m in pattern.finditer(text):
        # 转义标记之前的普通文本
        parts.append(_escape_xml(text[last:m.start()]))
        if m.group(2):  # **bold**
            parts.append(f"<b>{_escape_xml(m.group(2))}</b>")
        elif m.group(3):  # `code`
            parts.append(f'<font face="Courier" size="9">{_escape_xml(m.group(3))}</font>')
        last = m.end()
    parts.append(_escape_xml(text[last:]))
    return "".join(parts)


# ── 注册所有工具 ───────────────────────────────────────────────

register(save_docx_file)
register(extract_pdf_text)
register(save_pdf_file)
