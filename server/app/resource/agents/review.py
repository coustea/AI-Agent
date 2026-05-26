"""
审查智能体 — 质量审查 + 学习路径规划。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import (
    LearningBlueprint,
    ReviewResult,
    StudyPathStep,
    WorkerResult,
)
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)


class _ReviewOutput(BaseModel):
    """LLM 结构化输出格式。"""

    overall_score: int = Field(default=100, ge=0, le=100)
    consistency_score: int = Field(default=100, ge=0, le=100)
    personalization_score: int = Field(default=100, ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    study_path: list[StudyPathStep] = Field(default_factory=list)


class ReviewAgent:
    """审查所有资源质量并生成个性化学习路径。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(
        self,
        results: dict[str, WorkerResult],
        blueprint: LearningBlueprint,
        profile: dict[str, Any],
        learning_need: str,
    ) -> ReviewResult:
        await self.emitter.emit_agent("review", status="running", message="正在审查资源质量", progress=0)
        await self.emitter.emit_agent_action(
            "review", "check", detail="正在检查内容完整性",
            current_step=1, total_steps=3, step_label="完整性检查", progress=20,
        )

        prompt = registry.get("resource/review")
        input_text = self._build_input(results, blueprint, profile, learning_need)

        await self.emitter.emit_agent_action(
            "review", "evaluate", detail="正在评估个性化匹配度",
            current_step=2, total_steps=3, step_label="匹配度评估", progress=55,
        )

        output = await self.llm.ainvoke_json(
            _ReviewOutput,
            f"{prompt}\n\n{input_text}",
            temperature=0.2,
        )

        review = ReviewResult(
            passed=output.overall_score >= 60,
            overall_score=output.overall_score,
            consistency_score=output.consistency_score,
            personalization_score=output.personalization_score,
            issues=output.issues,
            suggestions=output.suggestions,
            study_path=output.study_path,
        )

        await self.emitter.emit_agent_action(
            "review", "done", detail="质量审查完成",
            current_step=3, total_steps=3, step_label="审查完成", progress=100,
        )
        review_status = "success" if review.passed else "failed"
        review_message = "质量审查完成" if review.passed else "质量审查未通过，已保留可用资源"
        await self.emitter.emit_agent("review", status=review_status, message=review_message, progress=100)
        return review

    def _build_input(
        self,
        results: dict[str, WorkerResult],
        blueprint: LearningBlueprint,
        profile: dict[str, Any],
        learning_need: str,
    ) -> str:
        parts = [f"## 学习需求\n{learning_need}"]

        # 教学蓝图
        parts.append(f"## 教学蓝图\n{blueprint.model_dump_json(indent=2)}")

        # 各资源摘要
        parts.append("## 已生成的资源")
        for agent_id, result in results.items():
            if not result.success:
                parts.append(f"### {agent_id} (失败)\n错误: {result.error}")
                continue
            preview = result.content[:500] if result.content else "(无内容)"
            parts.append(f"### {agent_id}\n- 标题: {result.title}\n- 格式: {result.file_type}\n- 内容预览:\n{preview}")

        # 学习者画像
        profile_text = format_learner_profile_for_prompt(profile)
        if profile_text:
            parts.append(f"## 学习者画像\n{profile_text}")

        return "\n\n".join(parts)
