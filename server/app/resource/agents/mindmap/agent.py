"""
思维导图生成 Agent。
独立实现：deepagents + markdown_to_mindmap 工具。
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
from langchain_core.messages import AIMessage
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from app.infra.llm import get_deepseek_llm
from app.infra.logging import get_logger
from app.resource.utils import append_context, load_prompt
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

_SERVER_ROOT = Path(__file__).resolve().parents[4]

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


def _extract_markdown_content(text: str) -> str:
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


def _count_mindmap_nodes(markdown_text: str) -> int:
    if not markdown_text.strip():
        return 0
    lines = [line.strip() for line in markdown_text.splitlines() if line.strip()]
    return sum(1 for line in lines if line.startswith("# ") or line.startswith("- "))


def _check_markdown_quality(markdown_text: str) -> tuple[bool, str, int]:
    node_count = _count_mindmap_nodes(markdown_text)
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


def _extract_file_path_from_tool_payload(content: Any) -> str | None:
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and "text" in item:
                try:
                    inner = json.loads(item["text"]) if isinstance(item["text"], str) else item["text"]
                except (json.JSONDecodeError, TypeError):
                    continue
                file_path = _extract_file_path_from_tool_payload(inner)
                if file_path:
                    return file_path
        return None
    if isinstance(content, dict):
        return content.get("file_path") or content.get("filePath")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"(/.*\.html)", content)
            return match.group(1) if match else None
        return _extract_file_path_from_tool_payload(parsed)
    return None


def _render_markmap_html(markdown_text: str) -> str:
    title_match = _TITLE_RE.search(markdown_text)
    title = title_match.group(1).strip() if title_match else "思维导图"
    md_json = json.dumps(markdown_text, ensure_ascii=False)
    return _HTML_TEMPLATE.format(title=title, md_json=md_json)


def _save_mindmap_html(topic: str, html_content: str) -> str:
    target_dir = WORKPLACE_DIR / "mindmap"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()[:50] or "untitled"
    file_path = target_dir / f"{safe_topic}_{int(time.time())}.html"
    file_path.write_text(html_content, encoding="utf-8")
    return str(file_path)


@tool("markdown_to_mindmap")
def markdown_to_mindmap(markdown_text: str) -> str:
    """将 Markdown 思维导图渲染为 HTML 文件，并返回包含 file_path 的 JSON 字符串。"""
    title_match = _TITLE_RE.search(markdown_text)
    title = title_match.group(1).strip() if title_match else "思维导图"
    html_content = _render_markmap_html(markdown_text)
    file_path = _save_mindmap_html(title, html_content)
    return json.dumps({"file_path": file_path, "filePath": file_path, "title": title}, ensure_ascii=False)


class MindmapGenerator:
    def __init__(self) -> None:
        self.name = "MindmapAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_deepseek_llm(temperature=0.1, max_tokens=900)

    def _build_system_message(self, state: dict[str, Any]) -> str:
        need_key = state.get("need", "review")
        need_text = NEED_MAP.get(need_key, need_key)
        prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", "待定"),
            topic=state.get("topic", "未知知识点"),
            gap=state.get("gap", "无"),
            need=need_text,
            extra=state.get("extra", "无"),
        )
        prompt += (
            "\n\n【执行指南】\n"
            "1. 严格基于用户当前请求生成内容，先满足主题、薄弱点和额外要求。\n"
            "2. 只输出 Markdown，不要解释过程，不要分步规划，不要先输出提纲。\n"
            "3. 不要调用 `write_todos`、`ls`、`read_file`、`write_file`、`edit_file`、`glob`、`grep`、`execute`、`task`。\n"
            "4. 不要调用工具；系统会在你输出 Markdown 后自动渲染 HTML。"
            "5. 一级分支必须顶格写成 `- 分支名称`，不要在一级分支前加空格。"
            "6. 只在有助于理解或应用时适当拓展，不要默认生成百科式大而全导图。"
        )
        return append_context(prompt, state=state)

    def _build_initial_human_message(self, state: dict[str, Any]) -> str:
        topic = state.get("topic")
        gap = state.get("gap")
        need = state.get("need", "review")
        extra = state.get("extra", "")
        msg = f"请为知识点 '{topic}' 生成思维导图。"
        if gap and gap != "无":
            msg += f" 特别注意学生在 '{gap}' 方面存在薄弱环节，请在图中重点体现。"
            msg += " 如果主题范围很大，请围绕这个薄弱点生成导图，主题只作为必要背景，不要展开无关章节。"
        if need:
            msg += f" 本次导图目标为：{need}。"
        if extra:
            msg += f" 额外要求：{extra}。"
        return msg + " 请只输出可直接渲染的 Markdown 思维导图内容。"

    async def _validate(self, messages: list[Any], retry_count: int) -> dict[str, Any]:
        file_path = None
        html_content = None
        agent_output = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                agent_output = msg.content if isinstance(msg.content, str) else str(msg.content)
                break
        markdown_content = _extract_markdown_content(agent_output)
        quality_ok, quality_feedback, node_count = _check_markdown_quality(markdown_content)
        if not file_path and markdown_content and quality_ok:
            try:
                tool_result = markdown_to_mindmap.invoke({"markdown_text": markdown_content})
                file_path = _extract_file_path_from_tool_payload(tool_result)
            except Exception as exc:
                return {"file_path": None, "html_content": None, "agent_output": agent_output, "markdown_content": markdown_content, "node_count": node_count, "is_valid": False, "retry_count": retry_count + 1, "validation_feedback": f"导图 Markdown 已生成，但转换 HTML 失败：{exc}"}
        if file_path and os.path.exists(file_path):
            try:
                html_content = Path(file_path).read_text(encoding="utf-8")
            except Exception:
                logger.exception("[MindmapAgent] 无法读取 HTML 文件 %s", file_path)
        return {
            "file_path": file_path,
            "html_content": html_content,
            "agent_output": agent_output,
            "markdown_content": markdown_content,
            "node_count": node_count,
            "is_valid": bool(file_path),
            "retry_count": retry_count + 1,
            "validation_feedback": "" if file_path else quality_feedback or "未检测到思维导图文件路径。请确保调用了 markdown_to_mindmap 工具并正确生成了 HTML 文件。",
        }

    async def generate_mindmap(
        self,
        topic: str = "",
        gap: str = "",
        course: str = "",
        major: str = "通用",
        need: str = "review",
        extra: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
    ) -> dict[str, Any]:
        logger.info("[MindmapAgent] 收到生成请求: topic=%s gap=%s", topic, gap)
        state = {"major": major, "course": course, "topic": topic, "gap": gap, "need": need, "extra": extra, "user_profile": user_profile or {}, "shared_memory": shared_memory or {}}
        try:
            agent = create_deep_agent(
                name="mindmap-agent",
                model=self.llm,
                tools=[],
                system_prompt=self._build_system_message(state),
                middleware=[
                    _ToolExclusionMiddleware(
                        excluded=[
                            "write_todos",
                            "ls",
                            "read_file",
                            "write_file",
                            "edit_file",
                            "glob",
                            "grep",
                            "execute",
                            "task",
                            "markdown_to_mindmap",
                        ]
                    )
                ],
                checkpointer=MemorySaver(),
            )
            feedback = ""
            result: dict[str, Any] = {}
            for attempt in range(3):
                user_message = self._build_initial_human_message(state)
                if feedback:
                    user_message += f"\n\n上一次生成未通过校验，原因：{feedback}\n请重新生成合格的 Markdown 思维导图。"
                response = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]}, config={"configurable": {"thread_id": f"mindmap:{topic or 'default'}:{attempt}"}})
                result = await self._validate(response.get("messages", []), attempt)
                if result.get("is_valid"):
                    break
                feedback = result.get("validation_feedback", "")
        except Exception as exc:
            logger.error("[MindmapAgent] 工作流执行失败: %s", exc)
            return {"success": False, "file_path": None, "html_content": None, "agent_output": "", "error": str(exc)}

        return {"success": result.get("is_valid", False), "file_path": result.get("file_path"), "html_content": result.get("html_content"), "agent_output": result.get("agent_output", ""), "markdown_content": result.get("markdown_content", ""), "node_count": result.get("node_count", 0), "error": result.get("validation_feedback") if not result.get("is_valid") else None}


if __name__ == '__main__':
    import asyncio
    agent = MindmapGenerator()
    result = asyncio.run(agent.generate_mindmap(
        topic="计算机操作系统",
        gap="进程之间的调度薄弱",
        course="操作系统",
    ))
    print(json.dumps(result, ensure_ascii=False, indent=2))
