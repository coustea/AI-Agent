"""
思维导图生成 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
MINDMAP_PROMPT_PATH = PROMPT_DIR / "mindmap.md"

with open(MINDMAP_PROMPT_PATH, "r", encoding="utf-8") as _f:
    MINDMAP_PROMPT = _f.read()

class MindmapState(BaseAgentState):
    need: str
    extra: str
    file_path: Optional[str]
    html_content: Optional[str]
    agent_output: Optional[str]

NEED_MAP = {
    "exam": "考前突击 (侧重考点与易错题)",
    "review": "课后复习 (侧重知识梳理与图解)",
    "deep": "深度探究 (侧重底层原理与拓展)",
    "practice": "实践应用 (侧重代码或实操案例)",
}

class MindmapGenerator(BaseResourceAgent):
    def __init__(self) -> None:
        super().__init__(
            name="MindmapAgent",
            prompt_template=MINDMAP_PROMPT,
            required_tools=["read_file_safe", "safe_shell"],
            required_mcp=["markmap"],
            required_skills=[],
            state_schema=MindmapState,
            temperature=0.1,
        )

    def _build_system_message(self, state: Any) -> SystemMessage:
        need_key = state.get("need", "review")
        need_text = NEED_MAP.get(need_key, need_key)

        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", "待定"),
            gap=state.get("gap", ""),
            need=need_text,
            extra=state.get("extra", "无"),
        )
        system_prompt = self._append_memory_and_skills(system_prompt, state)
        
        instruction = (
            "\n\n【重要指令】\n"
            "1. 请首先思考并直接调用 `markdown_to_mindmap` 工具，将你构思好的 Markdown 思维导图内容作为参数传入并生成 HTML。\n"
            "2. 工具会返回一个包含 `filePath` 的 JSON，或者返回文件路径文本。\n"
            "3. 根据该路径，使用 `read_file_safe` 或 `safe_shell` 工具（如 ls）检查文件是否成功生成。\n"
            "4. 确认无误后，向用户总结文件生成的路径即可结束对话。\n"
            "注意：不要在回答中直接输出长篇大论的 Markdown 源码，请直接传给工具！"
        )
        return SystemMessage(content=system_prompt + instruction)

    def _build_initial_human_message(self, state: Any) -> HumanMessage:
        return HumanMessage(content=f"请为知识短板 '{state.get('gap')}' 生成思维导图。")

    async def _validate_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        file_path = None
        html_content = None
        agent_output = ""

        if messages and isinstance(messages[-1], AIMessage):
            agent_output = messages[-1].content

        for msg in messages:
            if isinstance(msg, ToolMessage) and msg.name == "markdown_to_mindmap":
                content = str(msg.content)
                try:
                    res = json.loads(content)
                    if isinstance(res, dict) and "filePath" in res:
                        file_path = res["filePath"]
                    elif isinstance(res, list) and len(res) > 0 and "text" in res[0]:
                        inner_text = res[0]["text"]
                        inner_res = json.loads(inner_text)
                        if "filePath" in inner_res:
                            file_path = inner_res["filePath"]
                except Exception:
                    pass
                
                if not file_path:
                    match = re.search(r"(/.*\.html)", content)
                    if match:
                        file_path = match.group(1)

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
            except Exception as e:
                logger.warning(f"[MindmapAgent] 无法读取生成的 HTML 文件 {file_path}: {e}")

        return {
            "file_path": file_path,
            "html_content": html_content,
            "agent_output": agent_output,
            "is_valid": True,
        }

    async def generate_mindmap(
        self,
        gap: str,
        course: str = "",
        major: str = "通用",
        need: str = "review",
        extra: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[MindmapAgent] 收到生成请求: gap={gap}")
        await self._ensure_graph()

        initial_state: MindmapState = {
            "major": major,
            "course": course,
            "gap": gap,
            "need": need,
            "extra": extra,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "file_path": None,
            "html_content": None,
            "agent_output": None,
            "is_valid": False,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 10})
        except Exception as e:
            logger.error(f"[MindmapAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "file_path": None,
                "html_content": None,
                "agent_output": "",
                "error": str(e),
            }

        success = bool(result.get("file_path"))
        return {
            "success": success,
            "file_path": result.get("file_path"),
            "html_content": result.get("html_content"),
            "agent_output": result.get("agent_output", ""),
            "error": result.get("error") if not success else None,
        }

mindmap_generator = MindmapGenerator()
