"""习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_worker_base_context, salvage_json_from_llm
from app.resource.schemas import WorkerResult, WorkerState


class QuizOption(BaseModel):
    label: str = Field(description="选项标签，如 A/B/C/D")
    content: str = Field(description="选项内容")


class QuizQuestion(BaseModel):
    id: int = Field(description="题目编号")
    type: str = Field(default="single_choice", description="题目类型")
    question: str = Field(description="题目内容")
    options: list[QuizOption] = Field(default_factory=list, description="选项列表")
    answer: str | bool | list[str] = Field(description="正确答案")
    explanation: str = Field(default="", description="解析说明")
    difficulty: str = Field(default="medium", description="难度")
    knowledge_points: list[str] = Field(default_factory=list, description="考查知识点")


class QuizPayload(BaseModel):
    title: str = Field(description="习题集标题")
    summary: str = Field(default="", description="考查重点简介")
    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")


@register_agent
class QuizAgent(BaseResourceAgent):
    """习题生成 Agent。"""

    agent_id = "quiz"
    agent_name = "习题生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, state: WorkerState) -> WorkerResult:
        from app.prompts import registry

        parts = build_worker_base_context(state)
        config = state.agent_config
        if config:
            cfg = ["## 习题配置"]
            cfg.append(f"- 题目数量: {config.get('question_count', 5)}")
            cfg.append(f"- 难度模式: {config.get('difficulty_mode', 'basic')}")
            cfg.append(f"- 考试风格: {config.get('exam_style', 'school')}")
            cfg.append("- 每题包含详细解析" if config.get("include_analysis", True) else "- 不包含解析")
            parts.append("\n".join(cfg))

        prompt = registry.get("resource/quiz")
        full_prompt = f"{prompt}\n\n{'\n\n'.join(parts)}\n\n请生成习题集，以 JSON 格式输出。"

        try:
            result = await self.llm.ainvoke_json(
                QuizPayload,
                full_prompt,
                temperature=0.3,
                function_name="generate_quiz",
                function_description="生成习题集",
            )
            quiz_data = result.model_dump(mode="json")
            content = json.dumps(quiz_data, ensure_ascii=False, indent=2)
        except Exception as exc:
            response = await self.llm.ainvoke(full_prompt, temperature=0.3)
            raw = response.content if hasattr(response, "content") else str(response)
            quiz_data = salvage_json_from_llm(raw, require_key="questions")
            if quiz_data is None:
                return WorkerResult(success=False, error=f"习题 JSON 解析失败: {exc}")
            try:
                validated = QuizPayload.model_validate(quiz_data)
                quiz_data = validated.model_dump(mode="json")
            except Exception:
                pass
            content = json.dumps(quiz_data, ensure_ascii=False, indent=2)

        questions = quiz_data.get("questions", [])
        difficulty_dist: dict[str, int] = {}
        for q in questions:
            d = q.get("difficulty", "medium")
            difficulty_dist[d] = difficulty_dist.get(d, 0) + 1

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - 习题集",
            summary=f"生成 {len(questions)} 道习题",
            summary_data={
                "total_count": len(questions),
                "difficulty_distribution": difficulty_dist,
            },
            metadata={
                "engine": "quiz_json",
                "question_count": len(questions),
                "agent_id": "quiz",
            },
        )
