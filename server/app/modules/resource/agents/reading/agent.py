"""
拓展阅读推荐 Agent。
基于 BaseResourceAgent 实现，并使用黑板模式与用户画像。
"""

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState
from app.modules.resource.validation_utils import (
    extract_last_ai_content,
    validate_json_response,
    make_validation_result,
)

logger = get_logger(__name__)


class ReadingItem(BaseModel):
    title: str
    author_or_source: str
    abstract: str
    relevance: str
    type: str


class ReadingOutput(BaseModel):
    recommendations: list[ReadingItem]


class ReadingState(BaseAgentState):
    recommendations_json: str
    parsed_recommendations: list


class ReadingAgent(BaseResourceAgent):
    """拓展阅读推荐 Agent。

    根据知识点和用户兴趣偏好，推荐多种类型的拓展阅读资源，
    通过 Pydantic 校验推荐结构，确保数量、摘要质量和类型多样性。

    Attributes:
        name:           "ReadingAgent"
        agent_dir:      agents/reading/，包含 prompt.md
        state_schema:   ReadingState，包含 recommendations_json/parsed_recommendations
        method:         generate_reading() — 对外入口
        output:         {success, recommendations, file_path, raw_json, error}

    工作流: agent → validate(解析JSON + 校验数量/摘要/类型多样性) → retry/end
    DAG 阶段: enrichment（依赖 mindmap、content、code）
    黑板记忆: 读取 content.outline（内容大纲）
    用户画像: 读取 interest_preference（兴趣偏好）和 cognitive_style（认知风格）
    """
    def __init__(self) -> None:
        super().__init__(
            name="ReadingAgent",
            agent_dir=Path(__file__).parent,
            state_schema=ReadingState,
            temperature=0.3,
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
        if profile.get("interest_preference"):
            parts.append(f"- 兴趣偏好: {profile['interest_preference']}")
        if profile.get("cognitive_style"):
            parts.append(f"- 认知风格: {profile['cognitive_style']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            interest_preference=user_profile.get("interest_preference", ""),
            cognitive_style=user_profile.get("cognitive_style", ""),
        )
        return self._append_context_to_prompt(system_prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        return f"请为主题 '{state.get('topic')}' 生成推荐阅读清单。"

    async def _validate_node(self, state: Any) -> dict:
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        raw = extract_last_ai_content(messages)

        error = state.get("error")
        if error or not raw:
            return make_validation_result(
                False, retry_count, error or "未生成推荐内容",
                recommendations_json=raw, parsed_recommendations=[],
            )

        logger.info("[ReadingAgent] _validate_node: 评审推荐质量")

        is_valid, feedback, validated, extra = validate_json_response(
            raw, ReadingOutput, retry_count, "推荐结构"
        )
        if not is_valid:
            return {**extra, "recommendations_json": raw, "parsed_recommendations": []}

        items = validated.recommendations
        if len(items) < 3:
            return make_validation_result(
                False, retry_count,
                f"推荐数量不足（{len(items)} 条），至少需要 5 条。",
                recommendations_json=raw, parsed_recommendations=[],
            )

        for i, item in enumerate(items):
            if len(item.abstract) < 20:
                return make_validation_result(
                    False, retry_count,
                    f"第 {i + 1} 条推荐摘要过短（'{item.title}'），请补充实质性内容。",
                    recommendations_json=raw, parsed_recommendations=[],
                )

        types = {item.type for item in items}
        if len(types) < 2:
            return make_validation_result(
                False, retry_count,
                f"推荐类型单一（仅 {types}），请混合不同类型的资源。",
                recommendations_json=raw, parsed_recommendations=[],
            )

        logger.info(f"[ReadingAgent] 评审通过: {len(items)} 条推荐, 类型={types}")
        return {
            "recommendations_json": raw,
            "is_valid": True,
            "validation_feedback": "",
            "parsed_recommendations": [item.model_dump() for item in items],
        }

    async def generate_reading(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[ReadingAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()

        initial_state: ReadingState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "recommendations_json": "",
            "is_valid": False,
            "validation_feedback": "",
            "parsed_recommendations": [],
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[ReadingAgent] 工作流执行失败: {e}")
            return {"success": False, "recommendations": [], "raw_json": "", "error": str(e)}

        parsed = result.get("parsed_recommendations", [])
        raw_json = result.get("recommendations_json", "")
        file_path = None
        if parsed:
            from .tools import save_to_workplace
            file_path = save_to_workplace("reading", topic, json.dumps(parsed, ensure_ascii=False, indent=2), "json")

        return {
            "success": bool(parsed),
            "recommendations": parsed,
            "file_path": file_path,
            "raw_json": raw_json,
            "error": result.get("error") if not parsed else None,
        }
