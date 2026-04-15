"""
代码实操案例生成 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import asyncio
import ast
import re
import json
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.agents.shared.tools import save_with_tool
from app.core.logging import get_logger
from app.agents.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


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
    """代码实操案例生成 Agent。

    根据知识点生成可运行代码案例，并通过 safe_shell 工具验证执行，
    最后由 LLM 添加教学注释和逐步解析。

    Attributes:
        name:           "CodeAgent"
        agent_dir:      agents/code/，包含 prompt.md、tools/
        state_schema:   CodeState，包含 code_content/detected_language/explained_content
        method:         generate_code() — 对外入口
        output:         {success, content, file_path, detected_language, code_only, error}

    工作流: agent → tools(safe_shell) → validate(添加教学注释) → end
    DAG 阶段: core（依赖 mindmap）
    黑板记忆: 读取 mindmap.agent_output（知识结构）和 content.outline（内容大纲）
    用户画像: 读取 knowledge_level（知识水平）和 learning_pace（学习节奏）
    """
    def __init__(self) -> None:
        super().__init__(
            name="CodeAgent",
            agent_dir=Path(__file__).parent,
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

    def _build_system_message(self, state: Any) -> str:
        """构建 System Prompt（返回字符串）。"""
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            knowledge_level=user_profile.get("knowledge_level", "中等"),
            learning_pace=user_profile.get("learning_pace", "中等"),
        )
        # 注入上下文（用户画像、黑板记忆、skills 工具说明）
        system_prompt = self._append_context_to_prompt(system_prompt, state)

        instruction = (
            "\n\n【重要指令】\n"
            "1. 请首先直接生成对应的完整实操代码，并以 Markdown 形式输出。\n"
            "2. 如果你能够稳定调用 `safe_shell` 工具，可以在生成代码后进行一次本地运行验证。\n"
            "3. 如果当前轮次没有调用工具能力，也不要停下来，直接给出完整、可运行、带说明的代码案例。\n"
            "4. 不要只回复计划、说明或向用户追问，必须产出最终代码内容。"
        )
        return system_prompt + instruction

    def _build_initial_human_message(self, state: Any) -> str:
        """构建初次请求的消息（返回字符串）。"""
        return f"请为主题 '{state.get('topic')}' 生成一个完整的可运行代码案例。"

    def _save_to_workplace(self, sub_dir: str, topic: str, content: str, ext: str = "md") -> str:
        from .tools import save_to_workplace
        return save_with_tool(
            save_to_workplace,
            sub_dir=sub_dir,
            topic=topic,
            content=content,
            ext=ext,
        )

    def _failure_result(self, state: Any, feedback: str, **fields: Any) -> dict[str, Any]:
        retry_count = state.get("retry_count", 0) + 1
        result = {
            "is_valid": False,
            "validation_feedback": feedback,
            "retry_count": retry_count,
            **fields,
        }
        if retry_count >= state.get("max_retries", 2):
            result["error"] = feedback
        return result

    async def _validate_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        code_content = ""
        for message in reversed(messages):
            if isinstance(message, AIMessage) and isinstance(message.content, str) and message.content.strip():
                code_content = message.content.strip()
                break

        if not code_content:
            return self._failure_result(
                state,
                "未生成任何代码内容，请直接输出完整可运行的 Markdown 代码案例，不要只给解释或空响应。",
                code_content="",
                detected_language="unknown",
                explained_content="",
            )

        language = _detect_language(code_content)
        if "```" not in code_content:
            return self._failure_result(
                state,
                "缺少带语言标记的代码块，请按 Markdown 结构输出完整代码案例。",
                code_content=code_content,
                detected_language=language,
                explained_content="",
            )

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

    async def _fallback_generate_code(self, state: CodeState) -> dict[str, Any]:
        prompt = (
            "你是一位编程教学专家。请直接生成一个完整、可运行的 Markdown 代码案例，"
            "不要调用工具，不要输出计划，不要追问用户。\n\n"
            f"专业：{state.get('major', '通用')}\n"
            f"课程：{state.get('course', '')}\n"
            f"主题：{state.get('topic', '')}\n"
            f"知识短板：{state.get('gap', '')}\n"
            f"知识水平：{state.get('user_profile', {}).get('knowledge_level', '中等')}\n"
            "要求：\n"
            "1. 使用 Python\n"
            "2. 输出结构必须包含：问题场景、完整代码、运行结果、关键点解析\n"
            "3. 代码块使用 ```python 标记\n"
            "4. 示例要适合初学者并可直接运行\n"
        )
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip() if isinstance(response.content, str) else str(response.content)
        return {
            "explained_content": content,
            "code_content": content,
            "detected_language": _detect_language(content),
            "error": None,
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
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await asyncio.wait_for(
                self.graph.ainvoke(initial_state, {"recursion_limit": 15}),
                timeout=90,
            )
        except Exception as e:
            logger.error(f"[CodeAgent] 工作流执行失败: {e}")
            try:
                result = await self._fallback_generate_code(initial_state)
            except Exception as fallback_error:
                return {"success": False, "content": "", "detected_language": "unknown", "code_only": "", "error": str(fallback_error)}

        explained = result.get("explained_content", "") or result.get("code_content", "")
        code_only = _extract_code_block(result.get("code_content", ""))
        language = result.get("detected_language", "unknown")
        if not explained:
            try:
                fallback = await self._fallback_generate_code(initial_state)
                explained = fallback.get("explained_content", "")
                code_only = _extract_code_block(fallback.get("code_content", ""))
                language = fallback.get("detected_language", language)
            except Exception as fallback_error:
                logger.error(f"[CodeAgent] 降级生成失败: {fallback_error}")
        file_path = None
        if explained:
            file_path = self._save_to_workplace("code", topic, explained, "md")

        return {
            "success": bool(explained),
            "content": explained,
            "file_path": file_path,
            "detected_language": language,
            "code_only": code_only,
            "error": result.get("error") if not explained else None,
        }
