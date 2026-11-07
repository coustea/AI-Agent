"""习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, load_resource_prompt, register_agent
from app.resource.agents.common import build_resource_context
from app.resource.schemas import (
    AgentResult,
    QuizBlueprintSlot,
    QuizPayload,
    ResourceInput,
    build_quiz_blueprint,
    validate_quiz_payload,
)

if TYPE_CHECKING:
    from app.resource.event import ResourceEvents

logger = get_logger(__name__)


@register_agent
class QuizAgent(BaseResourceAgent):
    """习题生成 Agent — 输出 JSON 结构化的习题集。"""

    agent_id = "quiz"
    agent_name = "随堂练习"

    def __init__(self, emitter: ResourceEvents | None = None) -> None:
        """初始化习题 Agent 及其低温度 LLM 客户端。"""
        super().__init__(emitter=emitter)
        self.llm = LLM(temperature=0.1)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """根据学习需求生成包含选择题与判断题的 JSON 练习题库资源。"""
        parts = build_resource_context(input_data)
        input_text = "\n\n".join(parts)
        return await self._generate_quiz(
            input_text=input_text,
            title_prefix=input_data.learning_need[:32],
            config=input_data.agent_config,
        )

    async def _generate_quiz(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 调用 LLM 生成结构化习题集。

        agent_config 已由 build_resource_context 统一注入，
        此处仅提取运行时需要的参数（如 question_count 用于空数组重试）。

        题型和难度先由后端形成确定性蓝图，再由模型填充题目内容。
        """
        question_count = config.get("question_count", 5) if config else 5
        emphasis = config.get("emphasis", "foundations")
        logger.info("Agent[%s] 开始生成: learning_need=%s question_count=%d", self.agent_id, title_prefix, question_count)
        started = time.perf_counter()
        # 先生成确定性蓝图（题号/题型/难度），约束模型输出
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

        prompt = load_resource_prompt("quiz")

        full_prompt = (
            f"{prompt}\n\n{input_text}\n\n"
            "## 本次确定性题目蓝图\n"
            f"{blueprint_json}\n\n"
            "必须逐项按照蓝图生成题目，题目顺序、id、type、difficulty "
            "不得修改。输出严格符合 QuizPayload 的单个 JSON 对象。"
        )

        await self.emitter.send(self.agent_id, "running", "正在构建习题集提示词...", 45)

        logger.info("Agent[%s] LLM 调用: input_len=%d blueprint=%d", self.agent_id, len(full_prompt), len(blueprint))
        llm_started = time.perf_counter()
        await self.emitter.send(self.agent_id, "running", "正在生成测试题与解析...", 60)
        payload = await self.run_with_heartbeat(
            self._generate_payload(full_prompt, blueprint),
            messages=[
                "正在生成题目与选项...",
                "正在补充答案解析与考点说明...",
            ],
            interval_seconds=12.0,
            progress=70,
        )
        questions = payload.questions
        llm_elapsed = int((time.perf_counter() - llm_started) * 1000)

        content = payload.model_dump_json(indent=2)

        logger.info(
            "Agent[%s] LLM 完成: questions=%d elapsed_ms=%d",
            self.agent_id, len(questions), llm_elapsed,
        )
        # 统计各难度题目数量
        difficulty_dist: dict[str, int] = {}
        for question in questions:
            difficulty_dist[question.difficulty] = (
                difficulty_dist.get(question.difficulty, 0) + 1
            )

        total_elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: total_count=%d difficulty=%s elapsed_ms=%d",
            self.agent_id, len(questions), difficulty_dist, total_elapsed,
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
                "emphasis": emphasis,
                "agent_id": "quiz",
            },
        )

    async def _generate_payload(
        self,
        prompt: str,
        blueprint: list[QuizBlueprintSlot],
    ) -> QuizPayload:
        """生成题库并在统一 JSON 边界校验确定性题目蓝图。

        ``ainvoke_json`` 保存首次原始输出；当蓝图校验失败时，会把那份原文
        与错误一起交回模型修复一次。因此这里不能再发起脱离原文的第二次生成。
        """
        def validate_blueprint(candidate: object) -> None:
            """校验生成的结果是否满足预设的习题蓝图约束。"""
            payload = QuizPayload.model_validate(candidate)
            validate_quiz_payload(payload, blueprint)

        payload = await self.llm.json(
            QuizPayload,
            prompt,
            validator=validate_blueprint,
        )
        return QuizPayload.model_validate(payload)
