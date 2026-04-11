"""
多模态教学脚本生成 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import AIMessage

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


class MediaState(BaseAgentState):
    script_content: str


_SCENE_RE = re.compile(r"###\s*场景\s*\d+", re.IGNORECASE)
_NARRATION_RE = re.compile(r"\*\*旁白\*\*[：:]\s*(.+?)(?=\n[-*]|\n###|\n---|\Z)", re.DOTALL)
_ANIMATION_RE = re.compile(r"\*\*画面\*\*[：:]\s*(.+?)(?=\n[-*]|\n###|\n---|\Z)", re.DOTALL)
_PLACEHOLDER_RE = re.compile(r"(TODO|TBD|FIXME|\.{3,}|待补充|待完善)", re.IGNORECASE)


def _count_scenes(content: str) -> int:
    return len(_SCENE_RE.findall(content))


def _check_scene_completeness(content: str) -> list[str]:
    issues: list[str] = []
    scenes = _SCENE_RE.split(content)
    scene_contents = scenes[1:]
    for i, scene_text in enumerate(scene_contents):
        if not scene_text.strip():
            continue
        scene_num = i + 1
        if not _NARRATION_RE.search(scene_text):
            issues.append(f"场景 {scene_num} 缺少旁白内容")
        if not _ANIMATION_RE.search(scene_text):
            issues.append(f"场景 {scene_num} 缺少画面/动画描述")
    return issues


def _check_placeholders(content: str) -> list[str]:
    matches = _PLACEHOLDER_RE.findall(content)
    if matches:
        return [f"发现 {len(matches)} 处占位符文本（{set(matches)}），请替换为实际内容。"]
    return []


class MediaAgent(BaseResourceAgent):
    """多模态教学脚本生成 Agent。

    生成分场景的教学脚本，包含旁白、画面/动画描述等多模态元素，
    通过正则校验场景完整性（数量、旁白、画面、占位符）。

    Attributes:
        name:           "MediaAgent"
        agent_dir:      agents/media/，包含 prompt.md
        state_schema:   MediaState，包含 script_content
        method:         generate_media() — 对外入口
        output:         {success, content, file_path, error}

    工作流: agent → validate(校验场景数/旁白字数/占位符) → retry/end
    DAG 阶段: enrichment（依赖 mindmap、content、code）
    黑板记忆: 读取 content.outline（内容大纲）
    用户画像: 读取 cognitive_style（认知风格）
    """
    def __init__(self) -> None:
        super().__init__(
            name="MediaAgent",
            agent_dir=Path(__file__).parent,
            state_schema=MediaState,
            temperature=0.4,
        )

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        ctx = ""
        if "content" in shared_memory:
            outline = shared_memory["content"].get("outline", "")
            if outline:
                ctx += f"【内容大纲】\n{outline}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        if not profile: return ""
        parts = []
        if profile.get("cognitive_style"):
            parts.append(f"- 认知风格: {profile['cognitive_style']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            cognitive_style=user_profile.get("cognitive_style", "通用"),
        )
        return self._append_context_to_prompt(system_prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        return f"请为主题 '{state.get('topic')}' 生成一份多模态教学脚本。"

    async def _validate_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        content = ""
        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content.strip()

        error = state.get("error")
        if error or not content:
            return {
                "script_content": content,
                "is_valid": False,
                "validation_feedback": error or "未生成脚本内容",
                "retry_count": state.get("retry_count", 0) + 1,
            }

        logger.info("[MediaAgent] _validate_node: 校验脚本完整性")
        all_issues: list[str] = []

        scene_count = _count_scenes(content)
        if scene_count < 3:
            all_issues.append(f"场景数量不足（{scene_count} 个），至少需要 3 个场景。")

        all_issues.extend(_check_scene_completeness(content))
        all_issues.extend(_check_placeholders(content))

        narration_texts = _NARRATION_RE.findall(content)
        total_narration = sum(len(t) for t in narration_texts)
        if total_narration < 100:
            all_issues.append(f"旁白总字数过少（{total_narration} 字），需要更丰富的讲解内容。")

        if all_issues:
            feedback = "；".join(all_issues)
            logger.warning(f"[MediaAgent] 校验失败: {feedback}")
            return {
                "script_content": content,
                "is_valid": False,
                "validation_feedback": feedback,
                "retry_count": state.get("retry_count", 0) + 1,
            }

        logger.info(f"[MediaAgent] 校验通过: {scene_count} 个场景, 旁白总字数={total_narration}")
        return {
            "script_content": content,
            "is_valid": True,
            "validation_feedback": ""
        }

    async def generate_media(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[MediaAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()

        initial_state: MediaState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "script_content": "",
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[MediaAgent] 工作流执行失败: {e}")
            return {"success": False, "content": "", "error": str(e)}

        content = result.get("script_content", "")
        file_path = None
        if content:
            from .tools.file_saver import save_to_workplace
            file_path = save_to_workplace("media", topic, content, "md")

        return {
            "success": bool(content),
            "content": content,
            "file_path": file_path,
            "error": result.get("error") if not content else None,
        }
