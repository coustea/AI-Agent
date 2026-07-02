"""习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, model_validator

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
    # 判断题（true_false）不需要选项，其他类型至少需要2个选项
    options: list[QuizOption] = Field(default_factory=list, description="选项列表")
    answer: str | bool | list[str] = Field(description="正确答案")
    explanation: str = Field(default="", description="解析说明")
    difficulty: str = Field(default="medium", description="难度")
    knowledge_points: list[str] = Field(default_factory=list, description="考查知识点")

    @model_validator(mode="after")
    def validate_options_by_type(self):
        """根据题型验证选项数量：选择题至少2个选项，判断题/填空题可为空。"""
        # 判断题和填空题不需要选项
        if self.type in ("true_false", "fill_blank", "fill"):
            return self
        # 选择题（单选/多选）至少需要2个选项
        if len(self.options) < 2:
            raise ValueError(f"{self.type} 类型题目需要至少2个选项，当前只有 {len(self.options)} 个")
        return self


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

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
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
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
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
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def _generate_quiz(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成结构化习题集。

        LLM 返回空 questions 时自动重试一次（json_mode 下常见问题）。
        """
        if config:
            cfg = ["## 习题配置"]
            cfg.append(f"- 题目数量: {config.get('question_count', 5)}")
            cfg.append(f"- 难度模式: {config.get('difficulty_mode', 'basic')}")
            cfg.append(f"- 考试风格: {config.get('exam_style', 'school')}")
            cfg.append("- 每题包含详细解析" if config.get("include_analysis", True) else "- 不包含解析")
            question_types = config.get("question_types", ["single", "multiple", "judge"])
            if question_types:
                type_labels = {"single": "单选", "multiple": "多选", "judge": "判断", "fill": "填空"}
                cfg.append(f"- 题型分布: {', '.join(type_labels.get(t, t) for t in question_types)}")
            weak_point_weight = config.get("weak_point_weight")
            if weak_point_weight:
                cfg.append(f"- 薄弱点侧重权重: {weak_point_weight}%")
            input_text += f"\n\n{chr(10).join(cfg)}"

        # 禁止空数组的硬性约束（json_mode 下 LLM 倾向返回空数组）
        question_count = config.get("question_count", 5) if config else 5
        input_text += (
            f"\n\n【严禁】questions 为空数组 []。"
            f"你必须生成至少 {question_count} 道题目，缺少任何题目都是错误。"
        )

        prompt = prompts.get("resource").get("quiz")
        # 执行搜索以获取相关的习题出题参考信息
        await self.emitter.send(self.agent_id, "running", "正在搜索相关习题参考素材...", 30)
        search_query = f"{title_prefix} 习题 题型"
        search_text = await self.search(search_query)

        if "搜索失败" not in search_text and "未找到" not in search_text:
            input_text = f"## 搜索到的出题参考背景\n{search_text}\n\n" + input_text

        full_prompt = f"{prompt}\n\n{input_text}\n\n请生成习题集，以 JSON 格式输出。"

        await self.emitter.send(self.agent_id, "running", "正在构建习题集提示词...", 45)

        logger.info("Agent[quiz] 步骤: 调用 LLM 生成习题集, input_len=%d", len(full_prompt))
        await self.emitter.send(self.agent_id, "running", "正在生成测试题与解析...", 60)
        result = await self.llm.ainvoke_json(
            QuizPayload,
            full_prompt,
            temperature=INFERENCE_TEMPERATURE,
        )

        # LLM 返回空 questions 时重试一次（注入错误反馈）
        questions = result.questions
        if not questions:
            logger.warning(
                "Agent[quiz] questions 为空，正在重试 (expected_count=%d)",
                question_count,
            )
            await self.emitter.send(
                self.agent_id, "running",
                "首次生成题目为空，正在重试...", 70,
            )
            retry_prompt = (
                f"{full_prompt}\n\n"
                "【错误反馈】你上一次返回了 questions: []（空数组），这是严重错误。\n"
                f"你必须生成至少 {question_count} 道题目。\n"
                "questions 绝不能为空数组 []。"
            )
            result = await self.llm.ainvoke_json(
                QuizPayload,
                retry_prompt,
                temperature=INFERENCE_TEMPERATURE,
            )
            questions = result.questions

        quiz_data = result.model_dump(mode="json")
        content = json.dumps(quiz_data, ensure_ascii=False, indent=2)

        logger.info("Agent[quiz] 步骤: 习题解析完成, questions=%d", len(questions))
        difficulty_dist: dict[str, int] = {}
        for q in questions:
            d = q.get("difficulty", "medium") if isinstance(q, dict) else getattr(q, "difficulty", "medium")
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
