"""习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。"""

from __future__ import annotations

import json

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
from app.resource.schemas.quiz import (
    QuizBlueprintSlot,
    QuizPayload,
    build_quiz_blueprint,
    validate_quiz_payload,
)

logger = get_logger(__name__)


@register_agent
class QuizAgent(BaseResourceAgent):
    """习题生成 Agent — 输出 JSON 结构化的习题集。"""

    agent_id = "quiz"
    agent_name = "随堂练习"

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

        题型和难度先由后端形成确定性蓝图，再由模型填充题目内容。
        """
        question_count = config.get("question_count", 5) if config else 5
        blueprint = build_quiz_blueprint(
            question_count=question_count,
            question_types=config.get("question_types"),
            difficulty_mode=config.get("difficulty_mode", "basic"),
        )
        blueprint_json = json.dumps(
            [slot.model_dump(mode="json") for slot in blueprint],
            ensure_ascii=False,
            indent=2,
        )

        prompt = prompts.get("resource").get("quiz")
        # 执行搜索以获取相关的习题出题参考信息
        await self.emitter.send(self.agent_id, "running", "正在搜索相关习题参考素材...", 30)
        search_query = f"{title_prefix} 习题 题型"
        search_text = await self.search(search_query)

        if "搜索失败" not in search_text and "未找到" not in search_text:
            input_text = (
                f"## 搜索到的出题参考背景\n{search_text[:6000]}\n\n"
                + input_text
            )

        full_prompt = (
            f"{prompt}\n\n{input_text}\n\n"
            "## 本次确定性题目蓝图\n"
            f"{blueprint_json}\n\n"
            "必须逐项按照蓝图生成题目，题目顺序、id、type、difficulty "
            "不得修改。输出严格符合 QuizPayload 的单个 JSON 对象。"
        )

        await self.emitter.send(self.agent_id, "running", "正在构建习题集提示词...", 45)

        logger.info("Agent[quiz] 步骤: 调用 LLM 生成习题集, input_len=%d", len(full_prompt))
        await self.emitter.send(self.agent_id, "running", "正在生成测试题与解析...", 60)
        payload = await self._generate_payload(full_prompt, blueprint)
        questions = payload.questions

        content = payload.model_dump_json(indent=2)

        logger.info("Agent[quiz] 步骤: 习题解析完成, questions=%d", len(questions))
        difficulty_dist: dict[str, int] = {}
        for question in questions:
            difficulty_dist[question.difficulty] = (
                difficulty_dist.get(question.difficulty, 0) + 1
            )

        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=payload.title,
            summary=payload.summary,
            metrics={
                "total_count": len(questions),
                "difficulty_distribution": difficulty_dist,
            },
            metadata={
                "engine": "quiz_structured_v2",
                "question_count": len(questions),
                "agent_id": "quiz",
            },
        )

    async def _generate_payload(
        self,
        prompt: str,
        blueprint: list[QuizBlueprintSlot],
    ) -> QuizPayload:
        """使用结构化输出生成题库；语义不匹配时仅做一次定向纠正。"""
        temperature = min(INFERENCE_TEMPERATURE, 0.35)
        try:
            payload = await self.llm.ainvoke_json(
                QuizPayload,
                prompt,
                temperature=temperature,
                max_attempts=1,
            )
            payload = QuizPayload.model_validate(payload)
            validate_quiz_payload(payload, blueprint)
            return payload
        except Exception as first_error:
            logger.warning(
                "Agent[quiz] 首次结构化输出不符合题库契约，正在定向纠正: %s",
                first_error,
            )
            await self.emitter.send(
                self.agent_id,
                "running",
                "正在按题目蓝图纠正输出结构...",
                75,
            )
            correction_prompt = (
                f"{prompt}\n\n"
                "## 上一次输出的校验错误\n"
                f"{str(first_error)[:1600]}\n\n"
                "重新生成完整 QuizPayload。只纠正上述结构或蓝图偏差，"
                "仍须保持题目准确、选项有区分度、解析能够说明正确与错误原因。"
            )
            payload = await self.llm.ainvoke_json(
                QuizPayload,
                correction_prompt,
                temperature=temperature,
                max_attempts=1,
            )
            payload = QuizPayload.model_validate(payload)
            validate_quiz_payload(payload, blueprint)
            return payload
