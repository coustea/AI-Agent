"""习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, model_validator

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_node_context,
    build_resource_context,
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


# LLM 输出包装类（ainvoke_json 要求 BaseModel 子类）
class QuizPayload(BaseModel):
    """习题集 — LLM 结构化输出容器。"""
    questions: list[QuizQuestion] = Field(description="生成的习题列表")


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

        agent_config 已由 build_resource_context / build_node_context 统一注入，
        此处仅提取运行时需要的参数（如 question_count 用于空数组重试）。

        LLM 返回空数组时自动重试一次（json_mode 下常见问题）。
        """
        # 禁止空数组的硬性约束（json_mode 下 LLM 倾向返回空数组）
        question_count = config.get("question_count", 5) if config else 5
        input_text += (
            f"\n\n【严禁】返回空数组 []。"
            f"你必须生成至少 {question_count} 道题目，缺少任何题目都是错误。"
        )

        prompt = prompts.get("resource").get("quiz")
        # 执行搜索以获取相关的习题出题参考信息
        await self.emitter.send(self.agent_id, "running", "正在搜索相关习题参考素材...", 30)
        search_query = f"{title_prefix} 习题 题型"
        search_text = await self.search(search_query)

        if "搜索失败" not in search_text and "未找到" not in search_text:
            input_text = f"## 搜索到的出题参考背景\n{search_text}\n\n" + input_text

        full_prompt = f"{prompt}\n\n{input_text}\n\n请生成习题集，直接输出 JSON 数组。"

        await self.emitter.send(self.agent_id, "running", "正在构建习题集提示词...", 45)

        logger.info("Agent[quiz] 步骤: 调用 LLM 生成习题集, input_len=%d", len(full_prompt))
        await self.emitter.send(self.agent_id, "running", "正在生成测试题与解析...", 60)
        payload = await self.llm.ainvoke_json(
            QuizPayload,
            full_prompt,
            temperature=INFERENCE_TEMPERATURE,
        )
        questions = payload.questions

        # LLM 返回空数组时重试一次（注入错误反馈）
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
                "【错误反馈】你上一次返回了空数组 []，这是严重错误。\n"
                f"你必须生成至少 {question_count} 道题目。\n"
                "数组绝不能为空。"
            )
            retry_payload = await self.llm.ainvoke_json(
                QuizPayload,
                retry_prompt,
                temperature=INFERENCE_TEMPERATURE,
            )
            questions = retry_payload.questions

        # 序列化为 JSON
        content = json.dumps(
            [q.model_dump(mode="json") for q in questions],
            ensure_ascii=False,
            indent=2,
        )

        logger.info("Agent[quiz] 步骤: 习题解析完成, questions=%d", len(questions))
        difficulty_dist: dict[str, int] = {}
        for q in questions:
            d = q.difficulty
            difficulty_dist[d] = difficulty_dist.get(d, 0) + 1
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
