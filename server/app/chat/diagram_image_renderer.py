"""Render validated teaching-diagram payloads as resilient PNG information graphics."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import user_chat_uploads_dir
from app.infra.logging import get_logger

logger = get_logger(__name__)

Renderer = Callable[..., Awaitable[dict[str, Any]]]
_BROWSER_TIMEOUT_MS = 20_000
_PNG_WIDTH = 1280
_PNG_HEIGHT = 900


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _items(values: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_text(value) for value in values[:limit] if _text(value)]


def _card(title: str, body: str, *, accent: str = "") -> str:
    return (
        f'<article class="card {accent}"><h3>{escape(title)}</h3>'
        f'<p>{escape(body)}</p></article>'
    )


def _comparison_body(content: dict[str, Any]) -> str:
    left = content.get("left_entity") if isinstance(content.get("left_entity"), dict) else {}
    right = content.get("right_entity") if isinstance(content.get("right_entity"), dict) else {}
    summary = content.get("visual_summary") if isinstance(content.get("visual_summary"), dict) else {}
    left_name, right_name = _text(left.get("name")), _text(right.get("name"))
    entity_cards = "".join((
        _card(left_name or "左侧实体", " · ".join(filter(None, (_text(left.get("core_label")), _text(left.get("short_desc"))))), accent="left"),
        '<div class="relation"><span>核心关系</span><strong>' + escape(_text(summary.get("center_conclusion")) or "关键差异") + "</strong></div>",
        _card(right_name or "右侧实体", " · ".join(filter(None, (_text(right.get("core_label")), _text(right.get("short_desc"))))), accent="right"),
    ))
    rows = []
    for dimension in (content.get("dimensions") or [])[:6]:
        if not isinstance(dimension, dict):
            continue
        rows.append(
            "<tr>"
            f"<th>{escape(_text(dimension.get('name')))}</th>"
            f"<td>{escape(_text(dimension.get('left')))}</td>"
            f"<td>{escape(_text(dimension.get('right')))}</td>"
            "</tr>"
        )
    table = (
        "<section class=\"dimensions\"><h2>核心差异对比</h2>"
        "<table><thead><tr><th>维度</th>"
        f"<th>{escape(left_name or '左侧实体')}</th><th>{escape(right_name or '右侧实体')}</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></section>"
    )
    return f'<section class="comparison">{entity_cards}</section>{table}'


def _generic_body(diagram: dict[str, Any]) -> str:
    content = diagram.get("visual_content") if isinstance(diagram.get("visual_content"), dict) else {}
    graph_type = _text(diagram.get("graph_type"))
    cards: list[str] = []
    if graph_type == "framework":
        center = _text(content.get("center"))
        if center:
            cards.append(_card("核心主题", center, accent="center"))
        for module in (content.get("modules") or [])[:6]:
            if isinstance(module, dict):
                cards.append(_card(_text(module.get("title")) or "知识模块", " · ".join(_items(module.get("items")))))
    elif graph_type in {"flowchart", "sequence", "timeline"}:
        source = content.get("nodes") or content.get("messages") or content.get("tracks") or []
        for index, item in enumerate(source[:8], start=1):
            if not isinstance(item, dict):
                continue
            title = _text(item.get("title") or item.get("label") or item.get("track_name")) or f"步骤 {index}"
            detail = _text(item.get("short_desc") or item.get("detail"))
            cards.append(_card(title, detail or "关键过程", accent="step"))
    else:
        source = content.get("cards") or content.get("branches") or content.get("cells") or content.get("fields") or content.get("nodes") or []
        for item in source[:8]:
            if not isinstance(item, dict):
                continue
            title = _text(item.get("title") or item.get("label") or item.get("name")) or "知识点"
            detail = _text(item.get("short_desc") or item.get("detail"))
            if not detail and isinstance(item.get("children"), list):
                detail = " · ".join(_items(item["children"]))
            cards.append(_card(title, detail or "重点内容"))
    return '<section class="card-grid">' + "".join(cards or [_card("知识图解", "暂无可视化内容")]) + "</section>"


def build_teaching_diagram_html(diagram: dict[str, Any]) -> str:
    """Build a self-contained A-style Chinese teaching information graphic."""
    title = _text(diagram.get("title")) or "教学图解"
    subtitle = _text(diagram.get("subtitle")) or _text(diagram.get("teaching_goal"))
    content = diagram.get("visual_content") if isinstance(diagram.get("visual_content"), dict) else {}
    teaching = diagram.get("teaching_content") if isinstance(diagram.get("teaching_content"), dict) else {}
    body = _comparison_body(content) if diagram.get("graph_type") == "comparison" else _generic_body(diagram)
    points = "".join(f"<li>{escape(point)}</li>" for point in _items(teaching.get("key_points")))
    summary = _text(teaching.get("summary")) or _text(teaching.get("core_explanation"))
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}} body{{margin:0;padding:40px;background:#f4fbfb;color:#153f4d;font-family:"Microsoft YaHei",Arial,sans-serif}}
.board{{width:1200px;min-height:630px;padding:42px;border:1px solid #b9e6e0;border-radius:28px;background:linear-gradient(145deg,#fff 0%,#f0fffc 100%);box-shadow:0 18px 48px #0b6d6b18}}
header{{padding:0 0 28px;border-bottom:2px solid #a7e3dc}} .eyebrow{{color:#118a85;font-size:16px;font-weight:700;letter-spacing:2px}} h1{{margin:10px 0 8px;font-size:40px;color:#104c62}} .subtitle{{margin:0;color:#4d7180;font-size:19px}}
.comparison{{display:grid;grid-template-columns:1fr 220px 1fr;gap:20px;align-items:stretch;margin:30px 0}} .card,.relation{{padding:22px;border:1px solid #bde6e1;border-radius:18px;background:#fff}} .card h3{{margin:0 0 12px;color:#116d7b;font-size:21px}} .card p{{margin:0;line-height:1.65;color:#426572}} .left{{border-top:6px solid #31a8c6}} .right{{border-top:6px solid #46b98f}} .relation{{display:flex;flex-direction:column;justify-content:center;text-align:center;background:#e9faf6}} .relation span{{font-size:14px;color:#4c7b77}} .relation strong{{margin-top:10px;color:#157d74;font-size:20px;line-height:1.45}}
.dimensions{{margin-top:22px}} h2{{font-size:22px;color:#10586a}} table{{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;border:1px solid #c6e9e4;border-radius:14px}} th,td{{padding:14px 16px;text-align:left;border-bottom:1px solid #d9efec}} th{{background:#dff7f3;color:#125d69}} tr:last-child td{{border-bottom:0}}
.card-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:30px 0}} .center{{grid-column:span 3;background:#e7f8f7}} .step{{position:relative}} .step::before{{content:"";position:absolute;top:-7px;left:22px;width:38px;height:6px;background:#31a8c6;border-radius:8px}}
.takeaway{{margin-top:28px;padding:22px 24px;border-radius:18px;background:#104c62;color:#fff}} .takeaway h2{{margin:0 0 10px;color:#a9f1e5}} .takeaway p{{margin:0;line-height:1.7;font-size:18px}} ul{{display:flex;gap:12px;flex-wrap:wrap;padding:0;margin:20px 0 0;list-style:none}} li{{padding:7px 12px;border-radius:999px;background:#dff7f3;color:#19626d}}
</style></head><body><main class="board"><header><div class="eyebrow">知识信息图</div><h1>{escape(title)}</h1><p class="subtitle">{escape(subtitle)}</p></header>{body}<ul>{points}</ul><section class="takeaway"><h2>学习结论</h2><p>{escape(summary)}</p></section></main></body></html>"""


async def _screenshot_html_to_png(html: str, output_path: Path) -> None:
    """Capture HTML with bounded browser operations and always release Chromium."""
    from playwright.async_api import async_playwright

    output_path.parent.mkdir(parents=True, exist_ok=True)
    playwright = await async_playwright().start()
    browser = None
    try:
        browser = await playwright.chromium.launch(timeout=_BROWSER_TIMEOUT_MS)
        page = await browser.new_page(viewport={"width": _PNG_WIDTH, "height": _PNG_HEIGHT}, device_scale_factor=1)
        await page.set_content(html, wait_until="networkidle", timeout=_BROWSER_TIMEOUT_MS)
        await page.screenshot(path=str(output_path), full_page=True, timeout=_BROWSER_TIMEOUT_MS)
    finally:
        if browser is not None:
            await browser.close()
        await playwright.stop()


async def render_teaching_diagram_png(
    diagram: dict[str, Any], *, username: str, session_id: str,
) -> dict[str, Any]:
    """Render one diagram and store its PNG beneath the chat diagram directory."""
    html = build_teaching_diagram_html(diagram)
    filename = f"diagram-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:8]}.png"
    output_path = user_chat_uploads_dir(username, session_id) / "diagrams" / filename
    await _screenshot_html_to_png(html, output_path)
    return {
        "kind": "image",
        "title": _text(diagram.get("title")),
        "graph_type": _text(diagram.get("graph_type")),
        "image_url": f"/api/v1/ai/chat/uploads/{username}/{session_id}/diagrams/{filename}",
        "width": _PNG_WIDTH,
        "height": _PNG_HEIGHT,
    }


def build_diagram_fallback(diagram: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "fallback",
        "diagram": diagram,
        "render_error": "图片生成暂时失败",
        "retryable": True,
    }


async def ensure_teaching_diagram_png_payload(
    diagram: dict[str, Any] | None,
    *,
    username: str,
    session_id: str,
    renderer: Renderer = render_teaching_diagram_png,
) -> dict[str, Any] | None:
    """Return an image payload, retrying once before preserving the diagram as fallback."""
    if not diagram:
        return None
    if diagram.get("kind") == "image" and _text(diagram.get("image_url")):
        return diagram
    for attempt in range(1, 3):
        try:
            return await renderer(diagram, username=username, session_id=session_id)
        except Exception as exc:
            logger.warning("[chat] 图解图片渲染失败 attempt=%s: %s", attempt, exc)
    return build_diagram_fallback(diagram)
