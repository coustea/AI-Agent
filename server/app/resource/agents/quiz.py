"""
习题 Agent — 生成选择题/判断题等习题，支持 JSON 结构化输出。
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.agents.base import Agent
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import learning_need_from_task

logger = get_logger(__name__)


# 习题结构化 Schema
class QuizOption(BaseModel):
    label: str = Field(description="选项标签，如 A/B/C/D")
    content: str = Field(description="选项内容")
    is_correct: bool = Field(default=False, description="是否为正确答案")


class QuizQuestion(BaseModel):
    question_id: int = Field(description="题目编号")
    question_type: str = Field(default="single_choice", description="题目类型: single_choice/multiple_choice/true_false")
    question_text: str = Field(description="题目内容")
    options: list[QuizOption] = Field(default_factory=list, description="选项列表")
    correct_answer: str = Field(description="正确答案")
    analysis: str = Field(default="", description="解析说明")
    difficulty: str = Field(default="medium", description="难度: easy/medium/hard")
    knowledge_point: str = Field(default="", description="考查知识点")


class QuizPayload(BaseModel):
    title: str = Field(description="习题集标题")
    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")
    total_count: int = Field(default=0, description="题目总数")
    difficulty_distribution: dict[str, int] = Field(default_factory=dict, description="难度分布")


class QuizAgent(Agent):
    """习题生成 Agent。"""

    AGENT_NAME = "quiz"
    ROLE_NAME = "习题生成智能体"
    STEPS = ["分析输入", "融合画像与依赖", "生成习题", "整理输出"]

    def _default_template_values(self) -> dict[str, str]:
        return {
            "question_count": "5",
            "difficulty_mode": "basic",
            "exam_style": "school",
            "include_analysis_instruction": "包含答案解析",
            "weak_point_weight": "0.3",
        }

    def _resolve_template_variables(self, variables: set, state: WorkerState) -> dict[str, str]:
        """Quiz Agent 特殊变量解析。"""
        result = super()._resolve_template_variables(variables, state)
        config = state.agent_config or {}

        if "include_analysis_instruction" in variables:
            result["include_analysis_instruction"] = "每题包含详细解析" if config.get("include_analysis", True) else "不包含解析"

        return result

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        llm = get_llm_manager()

        # 尝试结构化输出
        try:
            result = await llm.ainvoke_structured(
                "spark_max",
                QuizPayload,
                f"{prompt}\n\n{input_text}\n\n请生成习题集，以 JSON 格式输出。",
                model_kwargs={"temperature": 0.3},
                function_name="generate_quiz",
                function_description="生成习题集，包含题目、选项、答案和解析",
            )
            quiz_data = result.model_dump(mode="json")
            content = json.dumps(quiz_data, ensure_ascii=False, indent=2)

        except Exception as exc:
            logger.warning("[QuizAgent] 结构化输出失败，尝试 JSON 文本解析: %s", exc)
            response = await llm.ainvoke(
                "spark_max",
                f"{prompt}\n\n{input_text}\n\n请生成习题集，以 JSON 格式输出。",
                model_kwargs={"temperature": 0.3, "model_kwargs": {"response_format": {"type": "json_object"}}},
            )
            raw = response.content if hasattr(response, "content") else str(response)
            quiz_data = self._salvage_quiz_payload(raw)
            if quiz_data is None:
                return WorkerResult(success=False, error=f"习题 JSON 解析失败: {exc}")
            content = json.dumps(quiz_data, ensure_ascii=False, indent=2)

        # 统计难度分布
        questions = quiz_data.get("questions", [])
        difficulty_dist: dict[str, int] = {}
        for q in questions:
            d = q.get("difficulty", "medium")
            difficulty_dist[d] = difficulty_dist.get(d, 0) + 1

        summary_data = {
            "total_count": len(questions),
            "difficulty_distribution": difficulty_dist,
            "exam_style": state.agent_config.get("exam_style", "school"),
        }

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=self._title(state, "习题集"),
            summary=f"生成 {len(questions)} 道习题",
            summary_data=summary_data,
            metadata={
                "engine": "quiz_json",
                "question_count": len(questions),
                "exam_style": state.agent_config.get("exam_style", "school"),
                "agent_id": "quiz",
            },
        )

    def _salvage_quiz_payload(self, raw: str) -> dict | None:
        """从原始文本中抢救 JSON 数据。"""
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "questions" in data:
                return data
        except json.JSONDecodeError:
            pass

        pattern = r"```(?:json)?\s*\n(.*?)```"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "questions" in data:
                    return data
            except json.JSONDecodeError:
                pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
                if isinstance(data, dict) and "questions" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None

    def _input_suffix(self) -> str:
        return "请生成习题集，以 JSON 格式输出。"