"""
代码实操案例生成 Agent。
生成分步讲解 + 代码块 + 完整代码。

输出结构：
1. 分步讲解：讲解 + 代码块（每一步）
2. 完整代码：所有代码合并
"""

import re
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_spark_x_llm
from app.infra.logging import get_logger
from app.resource.utils import append_context, format_profile_fields, load_prompt, save_resource_file

logger = get_logger(__name__)

_LANG_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "python3", "py"],
    "javascript": ["javascript", "js", "node", "nodejs"],
    "java": ["java"],
    "c": ["c", "clang"],
    "cpp": ["cpp", "c++", "cxx"],
    "sql": ["sql", "postgresql"],
    "go": ["go", "golang"],
    "rust": ["rust", "rs"],
}
_CODE_BLOCK_RE = re.compile(r"```(\w+)\s*\n(.*?)\n```", re.DOTALL)


def _detect_language(code_content: str) -> str:
    """从 Markdown 中检测编程语言。"""
    match = _CODE_BLOCK_RE.search(code_content)
    if match:
        lang_tag = match.group(1).lower()
        for canonical, aliases in _LANG_KEYWORDS.items():
            if lang_tag in aliases:
                return canonical
        return lang_tag
    return "unknown"


def _extract_all_code_blocks(content: str) -> list[str]:
    """提取所有代码块内容。"""
    matches = _CODE_BLOCK_RE.findall(content)
    return [match[1] for match in matches]


def _merge_code_blocks(code_blocks: list[str]) -> str:
    """合并所有代码块为完整代码（去重）。"""
    if not code_blocks:
        return ""
    unique_blocks = []
    seen = set()
    for block in code_blocks:
        stripped = block.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            unique_blocks.append(stripped)
    return "\n\n".join(unique_blocks)


class CodeAgent:
    """代码实操案例生成 Agent。"""

    def __init__(self) -> None:
        self.name = "CodeAgent"
        self.agent_dir = Path(__file__).parent
        self.prompt_template = load_prompt(self.agent_dir)
        self.llm = get_spark_x_llm(temperature=0.2)

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """从黑板提取上下文。"""
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
        """构建系统提示词。"""
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            knowledge_level=user_profile.get("knowledge_level", "中等"),
            learning_pace=user_profile.get("learning_pace", "中等"),
        )
        system_prompt = append_context(
            system_prompt,
            state=state,
            format_user_profile=self._format_user_profile,
            extract_memory=self._extract_memory,
        )
        return system_prompt + (
            "\n\n【输出格式要求】\n"
            "请按以下结构生成分步讲解的代码案例：\n\n"
            "## 步骤1：xxx\n"
            "讲解这一步的目的和原理...\n"
            "```语言\n"
            "# 这一步的代码\n"
            "```\n\n"
            "## 步骤2：xxx\n"
            "讲解...\n"
            "```语言\n"
            "# 代码\n"
            "```\n\n"
            "...（继续更多步骤）\n\n"
            "## 完整代码\n"
            "```语言\n"
            "# 所有步骤合并后的完整可运行代码\n"
            "```\n\n"
            "要求：\n"
            "1. 每个步骤必须包含：标题、讲解、代码块\n"
            "2. 步骤之间逻辑连贯，逐步构建\n"
            "3. 最后必须提供完整代码块\n"
            "4. 直接输出内容，不要追问用户"
        )

    async def generate_code(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict | None = None,
        shared_memory: dict | None = None,
        user_id: int = 0,
        resource_id: int = 0,
    ) -> dict[str, Any]:
        """生成代码案例。

        Args:
            topic: 主题
            course: 课程名称
            major: 专业
            gap: 知识薄弱点
            user_profile: 用户画像
            shared_memory: 共享记忆（黑板）
            user_id: 用户 ID，用于保存文件
            resource_id: 资源 ID，用于保存文件

        Returns:
            - step_by_step: 分步讲解内容（Markdown 格式）
            - full_code: 完整代码（纯代码，无 Markdown）
            - content: 完整内容（包含分步讲解和完整代码）
            - detected_language: 检测到的编程语言
            - file_path: 保存的文件路径
        """
        logger.info("[CodeAgent] 收到生成请求: topic=%s user_id=%s resource_id=%s", topic, user_id, resource_id)

        state = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
        }

        messages = [
            HumanMessage(content=self._build_system_message(state)),
            HumanMessage(content=f"请为主题 '{topic}' 生成一个完整的可运行代码案例。"),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip() if isinstance(response.content, str) else str(response.content)
            language = _detect_language(content)
            code_blocks = _extract_all_code_blocks(content)
            full_code = _merge_code_blocks(code_blocks)
            error = None
        except Exception as exc:
            logger.error("[CodeAgent] 生成失败: %s", exc)
            content = ""
            language = "unknown"
            full_code = ""
            error = str(exc)

        # 保存文件
        file_path = None
        if content and user_id and resource_id:
            file_path = save_resource_file(topic, content, user_id, resource_id, "md", prefix="code")
            logger.info("[CodeAgent] 内容已保存到文件: %s", file_path)

        return {
            "success": bool(content),
            "content": content,
            "step_by_step": content,
            "full_code": full_code,
            "file_path": file_path,
            "detected_language": language,
            "error": error,
        }
