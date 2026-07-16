"""Render teaching diagram JSON into a PNG image asset.

The LLM still produces structured diagram JSON, but the browser client no
longer renders that JSON with Vue diagram templates. This module turns the
validated JSON into a self-contained backend-rendered image and returns a
small image payload for SSE/history metadata.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from html import escape
from math import ceil, sqrt
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import chat_upload_url, user_chat_uploads_dir
from app.infra.logging import get_logger

logger = get_logger(__name__)

DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 900
PNG_DEVICE_SCALE_FACTOR = 2
Screenshotter = Callable[[str, int, int], Awaitable[bytes]]
ImageUrlBuilder = Callable[[str], str]
DiagramRenderer = Callable[..., Awaitable[dict[str, Any]]]


def _build_legacy_diagram_image_document(diagram: dict[str, Any], *, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> str:
    title = _text(diagram.get("title")) or "Teaching Diagram"
    subtitle = _text(diagram.get("subtitle"))
    graph_type = _text(diagram.get("graph_type")) or "diagram"
    visual_content = diagram.get("visual_content") if isinstance(diagram.get("visual_content"), dict) else {}
    teaching_content = diagram.get("teaching_content") if isinstance(diagram.get("teaching_content"), dict) else {}
    center, sections = _extract_visual_model(graph_type, visual_content, teaching_content)
    weak_visual = not any(_section_has_teaching_content(section) for section in sections)

    if weak_visual:
        sections = _teaching_overview_sections(teaching_content) or _fallback_sections(visual_content)
    elif not sections:
        sections = _fallback_sections(visual_content)

    section_html = "\n".join(_section_html(section, index) for index, section in enumerate(sections, start=1))
    map_class = "map is-compact" if weak_visual else "map"
    key_points = _string_list(teaching_content.get("key_points"))[:5]
    key_point_html = "".join(f"<li>{escape(point)}</li>" for point in key_points)
    summary = _text(teaching_content.get("summary")) or _text(teaching_content.get("core_explanation"))
    learning_html = _learning_html(teaching_content)

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      width: {width}px;
      min-height: {height}px;
      overflow: visible;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      color: #163033;
      background: #f7fbfb;
    }}
    #diagram-canvas {{
      width: {width}px;
      min-height: {height}px;
      padding: 52px 58px 44px;
      background:
        linear-gradient(rgba(38, 166, 154, 0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(38, 166, 154, 0.07) 1px, transparent 1px),
        radial-gradient(circle at 18% 10%, rgba(37, 99, 235, 0.14), transparent 24%),
        linear-gradient(135deg, #fbffff 0%, #edf8f7 100%);
      background-size: 32px 32px, 32px 32px, 100% 100%, 100% 100%;
    }}
    .topline {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 28px;
      margin-bottom: 36px;
    }}
    .kicker {{
      margin: 0 0 8px;
      color: #2563eb;
      font-size: 22px;
      font-weight: 800;
    }}
    h1 {{
      max-width: 980px;
      margin: 0;
      color: #10292d;
      font-size: 46px;
      line-height: 1.12;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 14px 0 0;
      color: #5a7478;
      font-size: 24px;
      font-weight: 600;
    }}
    .badge {{
      flex: 0 0 auto;
      padding: 14px 20px;
      border: 1px solid rgba(38, 166, 154, 0.32);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.78);
      color: #11645e;
      font-size: 20px;
      font-weight: 800;
    }}
    .map {{
      position: relative;
      min-height: 520px;
      padding: 38px 34px 34px;
      border: 1px solid rgba(38, 166, 154, 0.22);
      border-radius: 30px;
      background: rgba(255, 255, 255, 0.82);
      box-shadow: 0 24px 70px rgba(31, 71, 82, 0.10);
    }}
    .map.is-compact {{
      min-height: 0;
      padding: 30px 34px 34px;
    }}
    .map.is-compact .center {{
      margin-bottom: 24px;
    }}
    .center {{
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 86px;
      max-width: 740px;
      margin: 0 auto 34px;
      padding: 20px 36px;
      border-radius: 999px;
      color: white;
      text-align: center;
      font-size: 31px;
      line-height: 1.28;
      font-weight: 900;
      background: linear-gradient(135deg, #26a69a, #2563eb);
      box-shadow: 0 18px 42px rgba(37, 99, 235, 0.28);
    }}
    .sections {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 24px;
    }}
    .section {{
      min-height: 148px;
      padding: 24px 26px 22px;
      border: 1px solid rgba(23, 105, 116, 0.18);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(241,250,249,0.92));
    }}
    .section-head {{
      display: flex;
      gap: 14px;
      align-items: center;
      margin-bottom: 15px;
    }}
    .index {{
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      color: #2563eb;
      background: #e8f0ff;
      font-size: 18px;
      font-weight: 900;
    }}
    h2 {{
      margin: 0;
      color: #183a3f;
      font-size: 27px;
      line-height: 1.18;
      letter-spacing: 0;
    }}
    ul {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 9px;
    }}
    li {{
      position: relative;
      padding-left: 22px;
      color: #4d686d;
      font-size: 21px;
      line-height: 1.3;
      font-weight: 650;
    }}
    li::before {{
      content: "";
      position: absolute;
      left: 2px;
      top: 0.62em;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #26a69a;
    }}
    .summary {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 14px;
      align-items: start;
      margin-top: 24px;
      padding: 18px 24px;
      border-left: 6px solid #2563eb;
      border-radius: 18px;
      background: rgba(232, 240, 255, 0.78);
      color: #304e54;
      font-size: 22px;
      line-height: 1.35;
      font-weight: 700;
    }}
    .summary ul {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-start;
      gap: 8px;
    }}
    .summary li {{
      padding: 8px 12px;
      border-radius: 999px;
      background: #ffffff;
      color: #2563eb;
      font-size: 17px;
      line-height: 1;
    }}
    .summary li::before {{ display: none; }}
    .learning {{
      margin-top: 24px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .learning-card {{
      padding: 20px 22px;
      border: 1px solid rgba(23, 105, 116, 0.18);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.88);
    }}
    .learning-card.wide {{
      grid-column: 1 / -1;
    }}
    .learning-title {{
      margin: 0 0 10px;
      color: #183a3f;
      font-size: 22px;
      font-weight: 900;
      line-height: 1.22;
    }}
    .learning-text {{
      margin: 0;
      color: #405f65;
      font-size: 20px;
      line-height: 1.45;
      font-weight: 650;
    }}
    .learning-card ul {{
      gap: 8px;
    }}
    .learning-card li {{
      font-size: 19px;
      line-height: 1.38;
      font-weight: 650;
    }}
  </style>
</head>
<body>
  <main id="diagram-canvas">
    <div class="topline">
      <div>
        <p class="kicker">{escape(graph_type.upper())} PNG DIAGRAM</p>
        <h1>{escape(title)}</h1>
        {f'<p class="subtitle">{escape(subtitle)}</p>' if subtitle else ''}
      </div>
      <div class="badge">Backend Rendered PNG</div>
    </div>
    <section class="{map_class}">
      <div class="center">{escape(center or title)}</div>
      <div class="sections">{section_html}</div>
    </section>
    <section class="summary">
      <div>{escape(summary)}</div>
      <ul>{key_point_html}</ul>
    </section>
    {learning_html}
  </main>
</body>
</html>"""


def build_teaching_diagram_html(
    diagram: dict[str, Any],
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> str:
    """Render structured content with comparison, flow, or knowledge cards."""
    title = _localize_title(_text(diagram.get("title")) or "教学图解")
    subtitle = _text(diagram.get("subtitle"))
    graph_type = _text(diagram.get("graph_type")) or "summary"
    visual = diagram.get("visual_content") if isinstance(diagram.get("visual_content"), dict) else {}
    teaching = diagram.get("teaching_content") if isinstance(diagram.get("teaching_content"), dict) else {}
    center, sections = _extract_visual_model(graph_type, visual, teaching)

    if graph_type == "comparison":
        template = "comparison"
        sections = _comparison_sections(visual)
        subtitle = subtitle or "标题 + 多栏对比 + 底部结论"
        visual_summary = visual.get("visual_summary") if isinstance(visual.get("visual_summary"), dict) else {}
        summary = _text(visual_summary.get("center_conclusion")) or _text(teaching.get("summary"))
    elif graph_type in {"flowchart", "sequence", "timeline"}:
        template = "flow"
        subtitle = subtitle or "标题 + 主流程 + 关键说明"
        summary = _text(teaching.get("summary")) or _text(teaching.get("core_explanation"))
    else:
        template = "cards"
        subtitle = subtitle or "标题 + 中心主题 + 重点卡片"
        summary = _text(teaching.get("summary"))

    if not any(_section_has_teaching_content(section) for section in sections):
        sections = _teaching_overview_sections(teaching) or _fallback_sections(visual)
    sections = [
        section for section in sections
        if _text(section.get("title")) or _string_list(section.get("items"))
    ]

    content_html = _render_template_content(template, sections)
    center_html = (
        f'<div class="center-topic">{escape(center or title)}</div>'
        if template == "cards" else ""
    )
    conclusion_html = (
        f'<footer class="conclusion"><strong>核心结论：</strong>{escape(summary)}</footer>'
        if summary else ""
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; width: {width}px; min-height: {height}px; color: #092f5e; background: #f4f9ff; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }}
    #diagram-canvas {{ width: {width}px; min-height: {height}px; padding: 44px 40px 32px; border: 2px solid #397cff; border-radius: 28px; background: linear-gradient(180deg, #f6faff, #f1f8fb); }}
    header {{ margin-bottom: 30px; text-align: center; }}
    h1 {{ margin: 0; color: #0a3470; font-size: 42px; line-height: 1.2; letter-spacing: 0; }}
    .subtitle {{ margin: 20px 0 0; color: #55708f; font-size: 20px; }}
    .comparison-grid {{ display: grid; grid-template-columns: repeat(var(--comparison-columns), minmax(0, 1fr)); gap: 20px; }}
    .compare-column {{ padding: 24px 22px 22px; border: 1.5px solid #78a9ff; border-radius: 20px; background: #fff; }}
    .compare-column h2 {{ margin: 0 0 18px; padding-bottom: 16px; border-bottom: 1px dashed #75a7ff; color: #07546f; font-size: 30px; text-align: center; }}
    .fact-list {{ display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }}
    .fact-list li {{ padding: 14px 16px; border-radius: 10px; color: #092e58; background: #eef6ff; font-size: 20px; line-height: 1.35; font-weight: 600; }}
    .flow {{ display: grid; gap: 0; }}
    .flow-step {{ padding: 21px 28px; border-radius: 18px; color: #fff; background: linear-gradient(90deg, #315ead, #407dd1); text-align: center; font-size: 22px; font-weight: 800; }}
    .flow-step:nth-of-type(even) {{ background: linear-gradient(90deg, #1d877f, #35b3a8); }}
    .flow-detail {{ display: block; margin-top: 7px; font-size: 17px; font-weight: 500; opacity: .92; }}
    .flow-arrow {{ height: 44px; color: #3672d8; text-align: center; font-size: 38px; line-height: 40px; }}
    .center-topic {{ margin-bottom: 18px; padding: 20px 26px; border-radius: 16px; color: #fff; background: linear-gradient(90deg, #1d877f, #35b3a8); text-align: center; font-size: 22px; font-weight: 800; }}
    .knowledge-grid {{ --card-min: {_card_min_width(sections)}px; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, var(--card-min)), 1fr)); gap: 18px; }}
    .knowledge-card {{ min-height: 180px; padding: 22px 24px; border: 1.5px solid #89cec9; border-radius: 20px; background: #fff; }}
    .knowledge-card h2 {{ margin: 0 0 12px; color: #08716d; font-size: 22px; }}
    .knowledge-card p {{ margin: 0; color: #49647f; font-size: 19px; line-height: 1.55; }}
    .conclusion {{ min-height: 76px; margin-top: 24px; padding: 20px 24px; border-left: 7px solid #3779e8; background: #eaf2ff; color: #0a2e5d; font-size: 20px; line-height: 1.45; }}
  </style>
</head>
<body>
  <main id="diagram-canvas" data-template="{template}">
    <header><h1>{escape(title)}</h1><p class="subtitle">{escape(subtitle)}</p></header>
    {center_html}
    {content_html}
    {conclusion_html}
  </main>
</body>
</html>"""


def build_diagram_image_document(
    diagram: dict[str, Any],
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> str:
    source = build_mermaid_source(diagram)
    title = _localize_title(_text(diagram.get("title")) or "教学图解")
    subtitle = _text(diagram.get("subtitle"))
    graph_type = _text(diagram.get("graph_type")) or "diagram"
    teaching = diagram.get("teaching_content") if isinstance(diagram.get("teaching_content"), dict) else {}
    summary = _text(teaching.get("summary"))
    source_literal = json.dumps(source, ensure_ascii=False).replace("<", "\\u003c")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; width: {width}px; min-height: {height}px; background: #f5f9ff; color: #092f5e; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }}
    #diagram-canvas {{ width: {width}px; min-height: {height}px; padding: 36px 40px 30px; border: 2px solid #4b83e8; border-radius: 26px; background: linear-gradient(180deg, #f8fbff 0%, #f2f8ff 100%); }}
    header {{ margin-bottom: 22px; text-align: center; }}
    h1 {{ margin: 0; color: #073b7a; font-size: 40px; line-height: 1.2; letter-spacing: 0; font-weight: 800; }}
    .subtitle {{ margin: 12px 0 0; color: #58779c; font-size: 19px; }}
    #mermaid-output {{ display: flex; align-items: center; justify-content: center; width: 100%; min-height: 610px; padding: 28px 34px; border: 1px solid #d8e6f8; border-radius: 18px; background: rgba(255, 255, 255, .78); box-shadow: 0 12px 34px rgba(37, 83, 145, .08); }}
    #mermaid-output svg {{ display: block; width: 100%; height: auto; max-height: 650px; overflow: visible; }}
    #mermaid-output .node rect,
    #mermaid-output .node polygon,
    #mermaid-output .node path {{ stroke-width: 2px !important; filter: drop-shadow(0 6px 8px rgba(31, 76, 135, .12)); }}
    #mermaid-output .nodes > .node:nth-child(3n+1) rect,
    #mermaid-output .nodes > .node:nth-child(3n+1) polygon {{ fill: #eaf3ff !important; stroke: #4f87e8 !important; }}
    #mermaid-output .nodes > .node:nth-child(3n+2) rect,
    #mermaid-output .nodes > .node:nth-child(3n+2) polygon {{ fill: #e8f8f5 !important; stroke: #2b9a8e !important; }}
    #mermaid-output .nodes > .node:nth-child(3n) rect,
    #mermaid-output .nodes > .node:nth-child(3n) polygon {{ fill: #f1f6ff !important; stroke: #6a8fcf !important; }}
    #mermaid-output .nodeLabel,
    #mermaid-output .edgeLabel {{ color: #0a315f !important; font-weight: 650 !important; line-height: 1.45 !important; }}
    #mermaid-output .edgePath .path,
    #mermaid-output .flowchart-link {{ stroke: #3975d2 !important; stroke-width: 2.5px !important; }}
    #mermaid-output marker path {{ fill: #3975d2 !important; stroke: #3975d2 !important; }}
    #mermaid-output .cluster rect {{ fill: #f8fbff !important; stroke: #a8c4ee !important; stroke-width: 1.5px !important; rx: 14px; ry: 14px; }}
    #mermaid-output .actor {{ fill: #eaf3ff !important; stroke: #4f87e8 !important; stroke-width: 2px !important; }}
    #mermaid-output .messageLine0,
    #mermaid-output .messageLine1 {{ stroke: #3975d2 !important; stroke-width: 2.2px !important; }}
    #render-error {{ display: none; padding: 24px; color: #a42323; white-space: pre-wrap; }}
    .conclusion {{ margin-top: 20px; padding: 18px 22px; border-left: 7px solid #3779e8; border-radius: 0 10px 10px 0; background: #e8f1ff; font-size: 19px; line-height: 1.45; }}
  </style>
</head>
<body>
  <main id="diagram-canvas" data-renderer="mermaid" data-graph-type="{escape(graph_type)}">
    <header><h1>{escape(title)}</h1>{f'<p class="subtitle">{escape(subtitle)}</p>' if subtitle else ''}</header>
    <section id="mermaid-output" aria-label="{escape(title)}"></section>
    <pre id="render-error"></pre>
    {f'<footer class="conclusion"><strong>核心结论：</strong>{escape(summary)}</footer>' if summary else ''}
  </main>
  <script>
    const source = {source_literal};
    window.renderTeachingMermaid = async () => {{
      try {{
        mermaid.initialize({{
          startOnLoad: false,
          securityLevel: "strict",
          theme: "base",
          flowchart: {{ htmlLabels: true, curve: "basis", useMaxWidth: true, nodeSpacing: 58, rankSpacing: 72, padding: 24 }},
          sequence: {{ useMaxWidth: true, wrap: true, actorMargin: 80, messageMargin: 38, diagramMarginX: 40, diagramMarginY: 24 }},
          themeVariables: {{
            fontFamily: "Microsoft YaHei, PingFang SC, sans-serif",
            fontSize: "19px",
            primaryColor: "#eef6ff",
            primaryTextColor: "#092f5e",
            primaryBorderColor: "#5c91ed",
            lineColor: "#3779e8",
            secondaryColor: "#e7f8f6",
            tertiaryColor: "#ffffff",
            clusterBkg: "#ffffff",
            clusterBorder: "#78a9ff"
          }}
        }});
        await mermaid.parse(source);
        const result = await mermaid.render("teaching-mermaid", source);
        const output = document.getElementById("mermaid-output");
        output.innerHTML = result.svg;
        result.bindFunctions?.(output);
        output.querySelectorAll(".node rect").forEach((rect) => {{
          rect.setAttribute("rx", "12");
          rect.setAttribute("ry", "12");
        }});
        document.documentElement.dataset.mermaidReady = "true";
      }} catch (error) {{
        document.getElementById("render-error").textContent = String(error);
        document.documentElement.dataset.mermaidError = String(error);
      }}
    }};
  </script>
</body>
</html>"""


def _mermaid_runtime_path() -> Path:
    runtime_path = Path(__file__).resolve().parents[3] / "node_modules" / "mermaid" / "dist" / "mermaid.min.js"
    if not runtime_path.is_file():
        raise RuntimeError("Mermaid runtime is missing; run npm install")
    return runtime_path


def build_mermaid_source(diagram: dict[str, Any]) -> str:
    """Return model-authored Mermaid, or convert legacy structured diagrams."""
    source = _text_block(diagram.get("mermaid_source"))
    if source:
        return _sanitize_mermaid_source(source)
    return _legacy_diagram_to_mermaid(diagram)


def _sanitize_mermaid_source(source: str) -> str:
    """Repair harmless punctuation that commonly breaks flowchart parsing.

    Models sometimes append a prose colon after a completed node declaration,
    for example ``A --> B[LL 型]:``.  Mermaid treats that trailing colon as a
    new token and rejects the whole diagram, although the intended graph is
    otherwise unambiguous.
    """
    first_line = source.lstrip().splitlines()[0] if source.strip() else ""
    if not re.match(r"^(?:flowchart|graph)\b", first_line, re.IGNORECASE):
        return source.strip()

    sanitized = re.sub(
        r"(?P<node>(?:\[[^\]\n]*\]|\([^\)\n]*\)|\{[^}\n]*\}))\s*[:：]\s*$",
        r"\g<node>",
        source.strip(),
        flags=re.MULTILINE,
    )

    def normalize_nested_label(match: re.Match[str]) -> str:
        label = match.group("label")
        label = label.replace("\\n", "<br/>")
        label = label.replace('"', "").replace("`", "")
        label = re.sub(r"\s+", " ", label).strip()
        label = label.replace("[", "").replace("]", "")
        return f'{match.group("node_id")}["{_mermaid_text(label)}"]'

    # Models occasionally combine Mermaid's stadium shape with several quoted
    # fragments, e.g. ``LL(["title"\n"detail"])``.  Mermaid cannot parse the
    # nested quotes, so retain the full label as one ordinary rounded-safe node.
    sanitized = re.sub(
        r"(?P<node_id>[A-Za-z_][A-Za-z0-9_-]*)\(\[(?P<label>.+)\]\)\s*$",
        normalize_nested_label,
        sanitized,
        flags=re.MULTILINE,
    )
    return sanitized


def _legacy_diagram_to_mermaid(diagram: dict[str, Any]) -> str:
    graph_type = _text(diagram.get("graph_type")) or "summary"
    visual = diagram.get("visual_content") if isinstance(diagram.get("visual_content"), dict) else {}

    if graph_type == "sequence":
        actors = _string_list(visual.get("actors"))
        lines = ["sequenceDiagram"]
        aliases = {actor: f"A{index}" for index, actor in enumerate(actors, start=1)}
        for actor, alias in aliases.items():
            lines.append(f"    participant {alias} as {_mermaid_text(actor)}")
        for message in _dict_list(visual.get("messages")):
            sender = _text(message.get("from"))
            receiver = _text(message.get("to"))
            if sender not in aliases:
                aliases[sender] = f"A{len(aliases) + 1}"
                lines.append(f"    participant {aliases[sender]} as {_mermaid_text(sender)}")
            if receiver not in aliases:
                aliases[receiver] = f"A{len(aliases) + 1}"
                lines.append(f"    participant {aliases[receiver]} as {_mermaid_text(receiver)}")
            label = _text(message.get("label")) or _text(message.get("detail")) or "消息"
            lines.append(f"    {aliases[sender]}->>{aliases[receiver]}: {_mermaid_text(label)}")
        return "\n".join(lines)

    direction = "LR" if _text(visual.get("direction")) == "horizontal" else "TB"
    lines = [f"flowchart {direction}"]
    if graph_type == "flowchart":
        nodes = _dict_list(visual.get("nodes"))
        id_map: dict[str, str] = {}
        for index, node in enumerate(nodes, start=1):
            raw_id = _text(node.get("id")) or str(index)
            node_id = f"N{index}"
            id_map[raw_id] = node_id
            label = _first_text(node, ("title", "label", "name", "text", "content", "id")) or raw_id
            details = _items_from(
                node,
                (
                    "short_desc", "description", "definition", "details", "detail",
                    "explanation", "note", "items", "points", "children",
                ),
                exclude={label},
            )
            lines.append(f'    {node_id}["{_mermaid_text(label, *details)}"]')
        for edge in _dict_list(visual.get("edges")):
            left = id_map.get(_text(edge.get("from")))
            right = id_map.get(_text(edge.get("to")))
            if left and right:
                label = _text(edge.get("label"))
                lines.append(f"    {left} -->|{_mermaid_text(label)}| {right}" if label else f"    {left} --> {right}")
        return "\n".join(lines)

    center, sections = _extract_visual_model(graph_type, visual, diagram.get("teaching_content") or {})
    center = _localize_title(center)
    if graph_type == "comparison":
        sections = _comparison_sections(visual)
    if not any(_section_has_teaching_content(section) for section in sections):
        teaching = diagram.get("teaching_content") if isinstance(diagram.get("teaching_content"), dict) else {}
        sections = _teaching_overview_sections(teaching) or _fallback_sections(visual)
    if center:
        lines.append(f'    ROOT["{_mermaid_text(center)}"]')
    for index, section in enumerate(sections, start=1):
        title = _text(section.get("title")) or f"知识点 {index}"
        items = _string_list(section.get("items"))
        lines.append(f'    S{index}["{_mermaid_text(title, *items)}"]')
        if center:
            lines.append(f"    ROOT --> S{index}")
    if not center and len(sections) > 1:
        for index in range(1, len(sections)):
            lines.append(f"    S{index} ~~~ S{index + 1}")
    return "\n".join(lines)


def _mermaid_text(*parts: str) -> str:
    text = "<br/>".join(part for part in parts if part)
    return text.replace("\\", "\\\\").replace('"', "&quot;").replace("\n", " ")


def _text_block(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _comparison_sections(visual: dict[str, Any]) -> list[dict[str, Any]]:
    left = visual.get("left_entity") if isinstance(visual.get("left_entity"), dict) else {}
    right = visual.get("right_entity") if isinstance(visual.get("right_entity"), dict) else {}
    dimensions = _dict_list(visual.get("dimensions"))

    def entity_section(entity: dict[str, Any], side: str) -> dict[str, Any]:
        items = [
            text for text in (
                _text(entity.get("core_label")),
                _text(entity.get("short_desc")),
            ) if text
        ]
        for dimension in dimensions:
            value = _text(dimension.get(side))
            if not value:
                continue
            name = _text(dimension.get("name"))
            items.append(f"{name}：{value}" if name else value)
        return {
            "title": _text(entity.get("name")) or ("左侧" if side == "left" else "右侧"),
            "items": items,
        }

    return [entity_section(left, "left"), entity_section(right, "right")]


def _render_template_content(template: str, sections: list[dict[str, Any]]) -> str:
    if template == "comparison":
        columns = "".join(
            (
                '<article class="compare-column">'
                f'<h2>{escape(_text(section.get("title")))}</h2>'
                f'<ul class="fact-list">{_list_items_html(section)}</ul>'
                "</article>"
            )
            for section in sections
        )
        column_count = _balanced_column_count(len(sections))
        return (
            f'<section class="comparison-grid" style="--comparison-columns: {column_count}">'
            f"{columns}</section>"
        )

    if template == "flow":
        steps: list[str] = []
        for index, section in enumerate(sections):
            if index:
                steps.append('<div class="flow-arrow">↓</div>')
            details = _string_list(section.get("items"))
            detail_html = (
                f'<span class="flow-detail">{escape(" · ".join(details))}</span>'
                if details else ""
            )
            steps.append(
                f'<article class="flow-step">{escape(_text(section.get("title")))}'
                f"{detail_html}</article>"
            )
        return f'<section class="flow">{"".join(steps)}</section>'

    cards = "".join(
        (
            '<article class="knowledge-card">'
            f'<h2>{escape(_text(section.get("title")))}</h2>'
            f'<p>{escape("；".join(_string_list(section.get("items"))))}</p>'
            "</article>"
        )
        for section in sections
    )
    return f'<section class="knowledge-grid">{cards}</section>'


def _list_items_html(section: dict[str, Any]) -> str:
    return "".join(
        f"<li>{escape(item)}</li>"
        for item in _string_list(section.get("items"))
    )


def _card_min_width(sections: list[dict[str, Any]]) -> int:
    """Let CSS auto-fit choose the column count from actual content density."""
    longest = max(
        (
            len(_text(section.get("title")))
            + sum(len(item) for item in _string_list(section.get("items")))
            for section in sections
        ),
        default=0,
    )
    return max(260, min(620, 240 + longest * 3))


def _balanced_column_count(item_count: int) -> int:
    if item_count <= 0:
        return 1
    if item_count <= 3:
        return item_count
    if item_count == 4:
        return 2
    return ceil(sqrt(item_count))


def _localize_title(title: str) -> str:
    return title.replace(" vs ", " 与 ").replace(" VS ", " 与 ").replace(" Vs ", " 与 ")


async def render_teaching_diagram_png(
    diagram: dict[str, Any],
    *,
    username: str,
    session_id: str,
    screenshotter: Screenshotter | None = None,
    uploads_dir: Path | None = None,
    image_url_builder: ImageUrlBuilder | None = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> dict[str, Any]:
    mermaid_source = build_mermaid_source(diagram)
    html = build_diagram_image_document(diagram, width=width, height=height)
    screenshot = screenshotter or _screenshot_html_to_png
    render_mode = "mermaid"
    try:
        png_bytes = await screenshot(html, width, height)
    except Exception as exc:
        # Model-authored Mermaid is useful when valid, but it must never be a
        # single point of failure for diagram delivery. The structured teaching
        # fields can always be rendered as a self-contained HTML infographic.
        logger.warning(
            "[diagram] Mermaid render failed; using structured HTML fallback: %s",
            exc,
        )
        render_mode = "structured"
        fallback_html = build_teaching_diagram_html(
            diagram,
            width=width,
            height=height,
        )
        png_bytes = await screenshot(fallback_html, width, height)
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("diagram renderer did not return PNG bytes")
    pixel_width, pixel_height = _png_dimensions(png_bytes, fallback=(width, height))

    root_dir = uploads_dir or user_chat_uploads_dir(username, session_id)
    diagrams_dir = root_dir / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"diagrams/diagram-{timestamp}-{uuid4().hex[:8]}.png"
    image_path = root_dir / filename
    image_path.write_bytes(png_bytes)

    url_builder = image_url_builder or (lambda name: chat_upload_url(username, session_id, name))
    return {
        "kind": "image",
        "title": _text(diagram.get("title")) or "教学图解",
        "subtitle": _text(diagram.get("subtitle")) or None,
        "graph_type": _text(diagram.get("graph_type")) or "diagram",
        "mermaid_source": mermaid_source,
        "render_mode": render_mode,
        "image_url": url_builder(filename),
        "filename": filename,
        "mime_type": "image/png",
        "width": pixel_width,
        "height": pixel_height,
        "logical_width": width,
        "logical_height": height,
        "pixel_ratio": round(pixel_width / width, 2) if width else 1,
    }


async def ensure_teaching_diagram_png_payload(
    diagram: dict[str, Any] | None,
    *,
    username: str,
    session_id: str,
    renderer: DiagramRenderer = render_teaching_diagram_png,
) -> dict[str, Any] | None:
    if not diagram:
        return None
    if diagram.get("kind") == "image" and _text(diagram.get("image_url")):
        return diagram

    source = diagram.get("diagram") if diagram.get("kind") == "fallback" else diagram
    if not isinstance(source, dict):
        return diagram

    for attempt in range(2):
        try:
            return await renderer(source, username=username, session_id=session_id)
        except Exception as exc:
            logger.warning(
                "[diagram] PNG delivery attempt %d/2 failed: %s",
                attempt + 1,
                exc,
            )

    if diagram.get("kind") == "fallback":
        return diagram
    return {
        "kind": "fallback",
        "diagram": source,
        "render_error": "图片生成暂时失败",
        "retryable": True,
    }


async def _screenshot_html_to_png(html: str, width: int, height: int) -> bytes:
    # FastAPI's Windows development loop may use SelectorEventLoop, where
    # asyncio subprocess creation is unsupported. Playwright async launch then
    # fails before Chromium starts. Run its synchronous API in a worker thread;
    # this uses the normal Windows process launcher and keeps the request loop
    # responsive while the PNG is rendered.
    return await asyncio.to_thread(_screenshot_html_to_png_sync, html, width, height)


def _screenshot_html_to_png_sync(html: str, width: int, height: int) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=PNG_DEVICE_SCALE_FACTOR,
            )
            page.set_content(html, wait_until="networkidle")
            if page.locator('[data-renderer="mermaid"]').count():
                page.add_script_tag(path=str(_mermaid_runtime_path()))
                page.evaluate("window.renderTeachingMermaid()")
                page.wait_for_function(
                    "document.documentElement.dataset.mermaidReady === 'true' || "
                    "Boolean(document.documentElement.dataset.mermaidError)",
                    timeout=15_000,
                )
                render_error = page.evaluate(
                    "document.documentElement.dataset.mermaidError || ''"
                )
                if render_error:
                    raise ValueError(f"Mermaid render failed: {render_error}")
            canvas = page.locator("#diagram-canvas")
            rendered_height = canvas.evaluate(
                """element => Math.ceil(element.getBoundingClientRect().height)"""
            )
            if isinstance(rendered_height, int) and rendered_height > height:
                page.set_viewport_size({"width": width, "height": rendered_height})
            return canvas.screenshot(type="png")
        finally:
            browser.close()


def _png_dimensions(data: bytes, *, fallback: tuple[int, int]) -> tuple[int, int]:
    """Read the IHDR dimensions without adding another image dependency."""
    if len(data) >= 24 and data[12:16] == b"IHDR":
        return (
            int.from_bytes(data[16:20], "big"),
            int.from_bytes(data[20:24], "big"),
        )
    return fallback


def _extract_visual_model(
    graph_type: str,
    visual_content: dict[str, Any],
    teaching_content: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    if graph_type == "framework":
        return _text(visual_content.get("center")), [
            {"title": _text(module.get("title")), "items": _items_from(module, ("items", "children", "points", "details", "definition", "description", "explanation", "detail", "note"))}
            for module in _dict_list(visual_content.get("modules"))
        ]

    if graph_type == "hierarchy":
        return _text(visual_content.get("root")), [
            {"title": _text(branch.get("title")), "items": _string_list(branch.get("children"))}
            for branch in _dict_list(visual_content.get("branches"))
        ]

    if graph_type == "flowchart":
        nodes = _dict_list(visual_content.get("nodes"))
        return _text(teaching_content.get("summary")) or "Flow", [
            {
                "title": _first_text(node, ("title", "label", "name", "text", "content", "id")),
                "items": _items_from(
                    node,
                    (
                        "short_desc",
                        "description",
                        "desc",
                        "detail",
                        "details",
                        "definition",
                        "explanation",
                        "note",
                        "notes",
                        "items",
                        "points",
                        "children",
                        "examples",
                    ),
                    exclude={_first_text(node, ("title", "label", "name", "id"))},
                ),
            }
            for node in nodes
        ]

    if graph_type == "sequence":
        messages = _dict_list(visual_content.get("messages"))
        actors = _string_list(visual_content.get("actors"))
        return " -> ".join(actors[:3]) or "Sequence", [
            {
                "title": f"{_text(msg.get('from'))} -> {_text(msg.get('to'))}",
                "items": [item for item in [_text(msg.get("label")), _text(msg.get("detail"))] if item],
            }
            for msg in messages
        ]

    if graph_type == "comparison":
        left = visual_content.get("left_entity") if isinstance(visual_content.get("left_entity"), dict) else {}
        right = visual_content.get("right_entity") if isinstance(visual_content.get("right_entity"), dict) else {}
        dimensions = _dict_list(visual_content.get("dimensions"))
        return f"{_text(left.get('name'))} vs {_text(right.get('name'))}", [
            {"title": _text(dimension.get("name")), "items": [_text(dimension.get("left")), _text(dimension.get("right"))]}
            for dimension in dimensions
        ]

    if graph_type == "summary":
        return _text(teaching_content.get("summary")) or "Summary", [
            {"title": _text(card.get("title")), "items": [_text(card.get("short_desc"))]}
            for card in _dict_list(visual_content.get("cards"))
        ]

    if graph_type == "tree":
        return _text(visual_content.get("root_id")) or "Tree", [
            {
                "title": _text(node.get("label")) or _text(node.get("id")),
                "items": [item for item in [_text(node.get("detail")), _text(node.get("type"))] if item],
            }
            for node in _dict_list(visual_content.get("nodes"))
        ]

    if graph_type == "grid":
        return "Grid", [
            {
                "title": f"{_text(cell.get('index'))}: {_text(cell.get('label'))}",
                "items": [item for item in [_text(cell.get("pointer")), _text(cell.get("detail")), _text(cell.get("status"))] if item],
            }
            for cell in _dict_list(visual_content.get("cells"))
        ]

    if graph_type == "protocol":
        return "Protocol Fields", [
            {"title": _text(field.get("name")), "items": [item for item in [_text(field.get("detail"))] if item]}
            for field in _dict_list(visual_content.get("fields"))
        ]

    if graph_type == "timeline":
        return _text(visual_content.get("axis_label")) or "Timeline", [
            {
                "title": _text(track.get("track_name")),
                "items": [_text(block.get("label")) for block in _dict_list(track.get("blocks")) if _text(block.get("label"))],
            }
            for track in _dict_list(visual_content.get("tracks"))
        ]

    return "", []


def _fallback_sections(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        sections = []
        for key, child in value.items():
            if len(sections) >= 6:
                break
            items = _flatten_text(child)[:5]
            if items:
                sections.append({"title": _text(key), "items": items})
        return sections
    return []


def _teaching_overview_sections(teaching_content: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    core = _text(teaching_content.get("core_explanation"))
    if core:
        sections.append({"title": "核心定义", "items": [core]})

    key_points = _string_list(teaching_content.get("key_points"))
    if key_points:
        sections.append({"title": "必须掌握", "items": key_points})

    examples = _string_list(teaching_content.get("examples"))
    if examples:
        sections.append({"title": "示例", "items": examples})

    mistakes = _string_list(teaching_content.get("common_mistakes"))
    if mistakes:
        sections.append({"title": "常见误区", "items": mistakes})

    return sections[:4]


def _section_has_teaching_content(section: dict[str, Any]) -> bool:
    return bool(_string_list(section.get("items")))


def _section_html(section: dict[str, Any], index: int) -> str:
    title = _text(section.get("title")) or f"Part {index}"
    items = _string_list(section.get("items"))
    item_html = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"""
      <article class="section">
        <div class="section-head">
          <span class="index">{index:02d}</span>
          <h2>{escape(title)}</h2>
        </div>
        {f'<ul>{item_html}</ul>' if item_html else ''}
      </article>"""


def _learning_html(teaching_content: dict[str, Any]) -> str:
    cards: list[str] = []

    core = _text(teaching_content.get("core_explanation"))
    if core:
        cards.append(_learning_card("定义 / 核心解释", core, wide=True))

    key_points = _string_list(teaching_content.get("key_points"))
    if key_points:
        cards.append(_learning_card("必须掌握", key_points))

    examples = _string_list(teaching_content.get("examples"))
    if examples:
        cards.append(_learning_card("结合例子", examples))

    mistakes = _string_list(teaching_content.get("common_mistakes"))
    if mistakes:
        cards.append(_learning_card("易错点", mistakes))

    summary = _text(teaching_content.get("summary"))
    if summary:
        cards.append(_learning_card("一句话带走", summary, wide=True))

    return f'<section class="learning">{"".join(cards)}</section>' if cards else ""


def _learning_card(title: str, content: str | list[str], *, wide: bool = False) -> str:
    class_name = "learning-card wide" if wide else "learning-card"
    if isinstance(content, list):
        items = "".join(f"<li>{escape(item)}</li>" for item in content if item)
        body = f"<ul>{items}</ul>"
    else:
        body = f'<p class="learning-text">{escape(content)}</p>'
    return f'<article class="{class_name}"><h3 class="learning-title">{escape(title)}</h3>{body}</article>'


def _flatten_text(value: Any) -> list[str]:
    if isinstance(value, str):
        text = _text(value)
        return [text] if text else []
    if isinstance(value, (int, float, bool)):
        return [_text(value)]
    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            texts.extend(_flatten_text(item))
        return texts
    if isinstance(value, dict):
        texts = []
        for child in value.values():
            texts.extend(_flatten_text(child))
        return texts
    return []


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _text(item))]


def _first_text(mapping: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _text(mapping.get(key))
        if text:
            return text
    return ""


def _items_from(mapping: dict[str, Any], keys: tuple[str, ...], *, exclude: set[str] | None = None) -> list[str]:
    excluded = {item for item in (exclude or set()) if item}
    items: list[str] = []
    for key in keys:
        value = mapping.get(key)
        values = _flatten_text(value) if isinstance(value, (list, dict)) else [_text(value)]
        for text in values:
            if text and text not in excluded and text not in items:
                items.append(text)
    return items


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""

