"""
代码实操案例生成 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import os
import ast
import re
import json
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
CODE_PROMPT_PATH = PROMPT_DIR / "code.md"

with open(CODE_PROMPT_PATH, "r", encoding="utf-8") as _f:
    CODE_PROMPT = _f.read()

class CodeState(BaseAgentState):
    code_content: str
    detected_language: str
    explained_content: str

_LANG_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "python3", "py"],
    "javascript": ["javascript", "js", "node", "nodejs"],
    "java": ["java"],
    "c": ["c", "clang"],
    "cpp": ["cpp", "c++", "cxx"],
    "sql": ["sql", "mysql", "postgresql"],
    "go": ["go", "golang"],
    "rust": ["rust", "rs"],
}

_CODE_BLOCK_RE = re.compile(r"```(\w+)\s*\n(.*?)\n```", re.DOTALL)

def _detect_language(code_content: str) -> str:
    match = _CODE_BLOCK_RE.search(code_content)
    if match:
        lang_tag = match.group(1).lower()
        for canonical, aliases in _LANG_KEYWORDS.items():
            if lang_tag in aliases:
                return canonical
        return lang_tag
    return "unknown"

def _extract_code_block(code_content: str) -> str:
    match = _CODE_BLOCK_RE.search(code_content)
    if match:
        return match.group(2)
    return code_content

class CodeAgent(BaseResourceAgent):
    def __init__(self) -> None:
        super().__init__(
            name="CodeAgent",
            prompt_template=CODE_PROMPT,
            required_tools=["read_file_safe", "safe_shell"],
            required_mcp=[],
            required_skills=[],
            state_schema=CodeState,
            temperature=0.2,
        )

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        if "mindmap" in shared_memory:
            mm = shared_memory["mindmap"].get("agent_output", "")
            if mm: ctx += f"【思维导图核心结构】\n{mm}\n"
        if "content" in shared_memory:
            outline = shared_memory["content"].get("outline", "")
            if outline: ctx += f"【内容大纲】\n{outline}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        if not profile: return ""
        parts = []
        if profile.get("knowledge_level"):
            parts.append(f"- 知识水平: {profile['knowledge_level']}")
        if profile.get("learning_pace"):
            parts.append(f"- 学习节奏: {profile['learning_pace']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> SystemMessage:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            knowledge_level=user_profile.get("knowledge_level", "中等"),
            learning_pace=user_profile.get("learning_pace", "中等"),
        )
        system_prompt = self._append_memory_and_skills(system_prompt, state)
        
        instruction = (
            "\n\n【重要指令】\n"
            "1. 请首先思考并生成对应的实操代码。\n"
            "2. 生成代码后，**必须**使用 `safe_shell` 工具来实际运行这段代码（例如通过 `echo \"代码\" > test.py && python3 test.py`）。\n"
            "3. 根据运行结果，如果出现错误请自我修正并再次运行验证。\n"
            "4. 只有在代码成功运行并验证无误后，再最终输出包含代码的 Markdown 结果。"
        )
        return SystemMessage(content=system_prompt + instruction)

    def _build_initial_human_message(self, state: Any) -> HumanMessage:
        return HumanMessage(content=f"请为主题 '{state.get('topic')}' 生成一个完整的可运行代码案例。")

    async def _validate_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        code_content = ""

        if messages and isinstance(messages[-1], AIMessage):
            code_content = messages[-1].content

        language = _detect_language(code_content)
        logger.info(f"[CodeAgent] _validate_node (add_explanation): 为 {language} 代码添加教学注释")

        explain_messages = [
            HumanMessage(
                content=(
                    "你是一位编程教学专家。请在以下代码案例中添加详细的编号式逐步解析：\n\n"
                    "1. 在代码中的关键行前添加编号行内注释（如 `# [1] 定义数据结构`）\n"
                    "2. 在代码块之前添加 2-3 句的背景说明\n"
                    "3. 在代码块之后添加编号解析列表，解释每一步的含义和设计思路\n\n"
                    f"编程语言：{language}\n\n"
                    f"原始代码：\n{code_content}\n\n"
                    "请输出完整的 Markdown 文档（包含说明 + 带注释的代码 + 解析）。"
                )
            ),
        ]

        try:
            response = await self.llm.ainvoke(explain_messages)
            explained = response.content.strip()
            logger.info(f"[CodeAgent] 教学注释添加完成，长度={len(explained)} 字符")
            return {
                "code_content": code_content,
                "detected_language": language,
                "explained_content": explained,
                "is_valid": True,
            }
        except Exception as e:
            logger.error(f"[CodeAgent] 添加注释失败: {e}")
            return {
                "code_content": code_content,
                "detected_language": language,
                "explained_content": code_content,
                "is_valid": True,
            }

    async def generate_code(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[CodeAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()

        initial_state: CodeState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "code_content": "",
            "detected_language": "unknown",
            "explained_content": "",
            "is_valid": False,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[CodeAgent] 工作流执行失败: {e}")
            return {"success": False, "content": "", "detected_language": "unknown", "code_only": "", "error": str(e)}

        explained = result.get("explained_content", "") or result.get("code_content", "")
        code_only = _extract_code_block(result.get("code_content", ""))
        language = result.get("detected_language", "unknown")
        file_path = None
        if explained:
            from app.modules.resource.tools.file_saver import save_to_workplace
            file_path = save_to_workplace("code", topic, explained, "md")

        return {
            "success": bool(explained),
            "content": explained,
            "file_path": file_path,
            "detected_language": language,
            "code_only": code_only,
            "error": result.get("error") if not explained else None,
        }

code_agent = CodeAgent()
