"""
代码实操案例生成 Agent。
轻量实现：直接生成 Markdown 代码案例，再补充教学讲解。
"""

import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_deepseek_chat_llm
from app.infra.logging import get_logger
from app.resource.agent_support import append_context, format_profile_fields, load_prompt, save_to_workplace

logger = get_logger(__name__)

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


class CodeAgent:
    def __init__(self) -> None:
        self.name = "CodeAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_deepseek_chat_llm(temperature=0.2)

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        mm = ((shared_memory or {}).get("mindmap") or {}).get("agent_output", "")
        outline = ((shared_memory or {}).get("content") or {}).get("outline", "")
        if mm:
            ctx += f"【思维导图核心结构】\n{mm}\n"
        if outline:
            ctx += f"【内容大纲】\n{outline}\n"
        return ctx

    @staticmethod
    def _format_user_profile(profile: dict[str, Any]) -> str:
        return format_profile_fields(profile, [("knowledge_level", "知识水平"), ("learning_pace", "学习节奏")])

    def _build_system_message(self, state: dict[str, Any]) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            knowledge_level=user_profile.get("knowledge_level", "中等"),
            learning_pace=user_profile.get("learning_pace", "中等"),
        )
        system_prompt = append_context(system_prompt, state=state, format_user_profile=self._format_user_profile, extract_memory=self._extract_memory)
        return system_prompt + (
            "\n\n【重要指令】\n"
            "1. 请直接生成对应的完整实操代码，并以 Markdown 形式输出。\n"
            "2. 不要只回复计划、说明或向用户追问，必须产出最终代码内容。\n"
            "3. 输出结构包含：问题场景、完整代码、运行结果、关键点解析。"
        )

    async def _add_explanation(self, code_content: str, language: str) -> str:
        prompt = (
            "你是一位编程教学专家。请在以下代码案例中添加详细的编号式逐步解析：\n\n"
            "1. 在代码中的关键行前添加编号行内注释（如 `# [1] 定义数据结构`）\n"
            "2. 在代码块之前添加 2-3 句的背景说明\n"
            "3. 在代码块之后添加编号解析列表，解释每一步的含义和设计思路\n\n"
            f"编程语言：{language}\n\n原始代码：\n{code_content}\n\n"
            "请输出完整的 Markdown 文档（包含说明 + 带注释的代码 + 解析）。"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip() if isinstance(response.content, str) else str(response.content)

    async def _fallback_generate_code(self, state: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "你是一位编程教学专家。请直接生成一个完整、可运行的 Markdown 代码案例，不要输出计划，不要追问用户。\n\n"
            f"专业：{state.get('major', '通用')}\n课程：{state.get('course', '')}\n主题：{state.get('topic', '')}\n知识短板：{state.get('gap', '')}\n"
            f"知识水平：{state.get('user_profile', {}).get('knowledge_level', '中等')}\n"
            "要求：\n1. 使用 Python\n2. 输出结构必须包含：问题场景、完整代码、运行结果、关键点解析\n3. 代码块使用 ```python 标记\n4. 示例要适合初学者并可直接运行\n"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip() if isinstance(response.content, str) else str(response.content)
        return {"explained_content": content, "code_content": content, "detected_language": _detect_language(content), "error": None}

    async def generate_code(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
    ) -> dict[str, Any]:
        logger.info("[CodeAgent] 收到生成请求: topic=%s", topic)
        state = {"major": major, "course": course, "topic": topic, "gap": gap, "user_profile": user_profile or {}, "shared_memory": shared_memory or {}}
        try:
            messages = [HumanMessage(content=self._build_system_message(state)), HumanMessage(content=f"请为主题 '{topic}' 生成一个完整的可运行代码案例。")]
            response = await self.llm.ainvoke(messages)
            code_content = response.content.strip() if isinstance(response.content, str) else str(response.content)
            language = _detect_language(code_content)
            explained = await self._add_explanation(code_content, language)
            result = {"explained_content": explained, "code_content": code_content, "detected_language": language, "error": None}
        except Exception as exc:
            logger.error("[CodeAgent] 主流程失败: %s", exc)
            result = await self._fallback_generate_code(state)

        explained = result.get("explained_content", "") or result.get("code_content", "")
        code_only = _extract_code_block(result.get("code_content", ""))
        language = result.get("detected_language", "unknown")
        file_path = save_to_workplace("code", topic, explained, "md") if explained else None
        return {"success": bool(explained), "content": explained, "file_path": file_path, "detected_language": language, "code_only": code_only, "error": result.get("error") if not explained else None}
