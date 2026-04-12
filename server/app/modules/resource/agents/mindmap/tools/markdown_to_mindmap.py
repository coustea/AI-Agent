import html
import json
from typing import Any

from langchain.tools import tool

from app.modules.resource.shared_tools.file_handler import FileHandler


def _line_depth(line: str) -> int:
    indent = len(line) - len(line.lstrip(" "))
    return indent // 2


def _parse_markdown_tree(markdown_text: str) -> dict[str, Any]:
    lines = [line.rstrip() for line in markdown_text.splitlines() if line.strip()]
    root_title = "思维导图"
    children: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = [(-1, {"title": root_title, "children": children})]

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("# "):
            root_title = stripped[2:].strip() or root_title
            stack[0] = (-1, {"title": root_title, "children": children})
            continue
        if not stripped.startswith("- "):
            continue

        node = {"title": stripped[2:].strip(), "children": []}
        depth = _line_depth(raw_line)

        while stack and stack[-1][0] >= depth:
            stack.pop()

        parent = stack[-1][1]
        parent["children"].append(node)
        stack.append((depth, node))

    return {"title": root_title, "children": children}


def _render_node(node: dict[str, Any]) -> str:
    title = html.escape(str(node.get("title", "")))
    children = node.get("children", [])
    if not children:
        return f"<li><span class='node leaf'>{title}</span></li>"

    rendered_children = "".join(_render_node(child) for child in children)
    return (
        "<li>"
        f"<span class='node'>{title}</span>"
        f"<ul>{rendered_children}</ul>"
        "</li>"
    )


def _render_html(tree: dict[str, Any], markdown_text: str) -> str:
    title = html.escape(str(tree.get("title", "思维导图")))
    children = "".join(_render_node(child) for child in tree.get("children", []))
    source = html.escape(markdown_text)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f5efe4;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d8c9a8;
      --accent: #0f766e;
      --leaf: #f4f0e5;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 24rem),
        radial-gradient(circle at bottom right, rgba(180, 83, 9, 0.10), transparent 20rem),
        var(--bg);
    }}
    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    .hero {{
      background: rgba(255, 253, 248, 0.88);
      border: 1px solid rgba(216, 201, 168, 0.8);
      border-radius: 24px;
      padding: 24px 28px;
      backdrop-filter: blur(12px);
      box-shadow: 0 12px 40px rgba(31, 41, 55, 0.08);
    }}
    .hero h1 {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 3.4rem);
      line-height: 1.05;
      letter-spacing: -0.03em;
    }}
    .hero p {{
      margin: 12px 0 0;
      color: var(--muted);
      font-size: 0.98rem;
    }}
    .mindmap {{
      margin-top: 24px;
      background: var(--panel);
      border-radius: 28px;
      border: 1px solid rgba(216, 201, 168, 0.8);
      padding: 28px 28px 18px;
      box-shadow: 0 18px 48px rgba(31, 41, 55, 0.08);
      overflow-x: auto;
    }}
    .mindmap > ul,
    .mindmap ul {{
      list-style: none;
      margin: 0;
      padding-left: 28px;
      position: relative;
    }}
    .mindmap > ul {{
      padding-left: 0;
    }}
    .mindmap ul::before {{
      content: "";
      position: absolute;
      left: 10px;
      top: 0;
      bottom: 14px;
      width: 1px;
      background: linear-gradient(to bottom, var(--line), rgba(216, 201, 168, 0.1));
    }}
    .mindmap li {{
      position: relative;
      padding: 10px 0 4px 18px;
      min-width: 240px;
    }}
    .mindmap li::before {{
      content: "";
      position: absolute;
      left: 10px;
      top: 26px;
      width: 14px;
      height: 1px;
      background: var(--line);
    }}
    .node {{
      display: inline-block;
      padding: 10px 14px;
      border-radius: 14px;
      background: linear-gradient(135deg, rgba(15, 118, 110, 0.10), rgba(255, 253, 248, 0.98));
      border: 1px solid rgba(15, 118, 110, 0.16);
      font-weight: 600;
      line-height: 1.4;
      box-shadow: 0 8px 20px rgba(15, 118, 110, 0.08);
    }}
    .leaf {{
      background: var(--leaf);
      border-color: rgba(180, 83, 9, 0.18);
      box-shadow: none;
      font-weight: 500;
    }}
    details {{
      margin-top: 18px;
      border-top: 1px dashed rgba(216, 201, 168, 0.9);
      padding-top: 16px;
      color: var(--muted);
    }}
    summary {{
      cursor: pointer;
      font-weight: 600;
      color: var(--accent);
    }}
    pre {{
      margin: 12px 0 0;
      padding: 16px;
      border-radius: 14px;
      background: #1f2937;
      color: #f9fafb;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 0.92rem;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>{title}</h1>
      <p>由本地工具 `markdown_to_mindmap` 生成。</p>
    </section>
    <section class="mindmap">
      <ul>{children}</ul>
      <details>
        <summary>查看原始 Markdown</summary>
        <pre>{source}</pre>
      </details>
    </section>
  </main>
</body>
</html>
"""


@tool("markdown_to_mindmap")
def markdown_to_mindmap(markdown_text: str) -> str:
    """将 Markdown 层级结构转换为 HTML 思维导图，并保存到 workplace/mindmap。"""
    tree = _parse_markdown_tree(markdown_text)
    html_content = _render_html(tree, markdown_text)
    file_path = FileHandler.save_to_workplace("mindmap", tree["title"], html_content, "html")
    return json.dumps(
        {
            "file_path": file_path,
            "filePath": file_path,
            "title": tree["title"],
        },
        ensure_ascii=False,
    )
