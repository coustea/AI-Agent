"""习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    assigned_outline_ids,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)


class QuizOption(BaseModel):
    """单个选项：标签（A/B/C/D）+ 内容文本。"""
    label: str = Field(description="选项标签，如 A/B/C/D")
    content: str = Field(description="选项内容")


class QuizQuestion(BaseModel):
    """单道题目：包含题干、选项、答案、解析、难度和知识点。"""
    id: int = Field(description="题目编号")
    type: str = Field(default="single_choice", description="题目类型")
    question: str = Field(description="题目内容")
    options: list[QuizOption] = Field(min_length=2, description="选项列表，至少2个选项")
    answer: str | bool | list[str] = Field(description="正确答案")
    explanation: str = Field(default="", description="解析说明")
    difficulty: str = Field(default="medium", description="难度")
    knowledge_points: list[str] = Field(default_factory=list, description="考查知识点")


class QuizPayload(BaseModel):
    """LLM 结构化输出模型：完整习题集。"""
    title: str = Field(default="随堂练习", description="习题集标题")
    summary: str = Field(default="", description="考查重点简介")
    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")


@register_agent
class QuizAgent(BaseResourceAgent):
    """习题生成 Agent — 输出 JSON 结构化的习题集。"""

    agent_id = "quiz"
    agent_name = "习题生成"

    def __init__(self, events=None, emitter=None):
        super().__init__(events=events, emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        parts = build_resource_context(input_data)
        input_text = "\n\n".join(parts)
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_quiz(
            input_text=input_text,
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        try:
            quiz_data = json.loads(result.content)
            questions = quiz_data.get("questions", [])
            q_ids = [str(q.get("id")) for q in questions if q.get("id") is not None]
            knowledge_points: list[str] = []
            for question in questions:
                if isinstance(question, dict):
                    for point in question.get("knowledge_points", []):
                        if isinstance(point, str) and point not in knowledge_points:
                            knowledge_points.append(point)
        except Exception:
            q_ids = []
            knowledge_points = []
        outline_ids = assigned_outline_ids(input_data.teaching_plan, "quiz")
        handoff = build_basic_handoff(
            source_agent="quiz",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            covered_outline_ids=outline_ids,
            practice_refs=q_ids,
        )
        result.downstream_context = handoff
        await self.events.send_agent_status(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        parts = build_node_context(input_data)
        input_text = "\n\n".join(parts)
        result = await self._generate_quiz(
            input_text=input_text,
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.events.send_agent_status(self.agent_id, status="completed" if result.success else "failed", message=result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), progress=100 if result.success else 0)
        return result

    async def _generate_quiz(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成结构化习题集。"""
        if config:
            cfg = ["## 习题配置"]
            cfg.append(f"- 题目数量: {config.get('question_count', 5)}")
            cfg.append(f"- 难度模式: {config.get('difficulty_mode', 'basic')}")
            cfg.append(f"- 考试风格: {config.get('exam_style', 'school')}")
            cfg.append("- 每题包含详细解析" if config.get("include_analysis", True) else "- 不包含解析")
            input_text += f"\n\n{chr(10).join(cfg)}"

        prompt = prompts.get("resource").get("quiz")
        full_prompt = f"{prompt}\n\n{input_text}\n\n请生成习题集，以 JSON 格式输出。"

        await self.events.send_agent_step(self.agent_id, phase="start", message="正在构建习题集提示词", progress=25)

        logger.info("Agent[quiz] 步骤: 调用 LLM 生成习题集, input_len=%d", len(full_prompt))
        result = await self.llm.ainvoke_json(
            QuizPayload,
            full_prompt,
            temperature=INFERENCE_TEMPERATURE,
        )

        quiz_data = result.model_dump(mode="json")
        content = json.dumps(quiz_data, ensure_ascii=False, indent=2)

        questions = quiz_data.get("questions", [])
        logger.info("Agent[quiz] 步骤: 习题解析完成, questions=%d", len(questions))
        difficulty_dist: dict[str, int] = {}
        for q in questions:
            d = q.get("difficulty", "medium")
            difficulty_dist[d] = difficulty_dist.get(d, 0) + 1

        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - 习题集",
            summary=f"生成 {len(questions)} 道习题",
            metrics={
                "total_count": len(questions),
                "difficulty_distribution": difficulty_dist,
            },
            metadata={
                "engine": "quiz_json",
                "question_count": len(questions),
                "agent_id": "quiz",
            },
        )
