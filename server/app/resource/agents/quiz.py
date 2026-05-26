"""
习题智能体 — 生成选择题/判断题等习题，支持 JSON 结构化输出。
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)


# 习题结构化 Schema
class QuizOption(BaseModel):
    label: str = Field(description="选项标签，如 A/B/C/D")
    content: str = Field(description="选项内容")


class QuizQuestion(BaseModel):
    id: int = Field(description="题目编号")
    type: str = Field(default="single_choice", description="题目类型: single_choice/multiple_choice/blank/true_false/short_answer/coding")
    question: str = Field(description="题目内容")
    options: list[QuizOption] = Field(default_factory=list, description="选项列表")
    answer: str | bool | list[str] = Field(description="正确答案")
    explanation: str = Field(default="", description="解析说明")
    difficulty: str = Field(default="medium", description="难度: basic/medium/advanced")
    knowledge_points: list[str] = Field(default_factory=list, description="考查知识点")
    reference_answer: str | None = Field(default=None, description="简答题参考答案")
    scoring_points: list[str] = Field(default_factory=list, description="简答题评分要点")
    input_description: str | None = Field(default=None, description="编程题输入说明")
    output_description: str | None = Field(default=None, description="编程题输出说明")
    constraints: list[str] = Field(default_factory=list, description="编程题约束条件")
    sample_cases: list[dict] = Field(default_factory=list, description="编程题样例")
    reference_solution: str | None = Field(default=None, description="编程题参考代码")


class QuizPayload(BaseModel):
    title: str = Field(description="习题集标题")
    summary: str = Field(default="", description="考查重点简介")
    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")


class QuizAgent:
    """习题生成 Agent。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("quiz", status="running", message="正在准备习题", progress=0)
        await self.emitter.emit_agent_action(
            "quiz", "analyze", detail="正在分析考点分布",
            current_step=1, total_steps=4, step_label="分析考点", progress=10,
        )

        prompt = registry.get("resource/quiz")
        input_text = self._build_input(state)
        full_prompt = f"{prompt}\n\n{input_text}\n\n请生成习题集，以 JSON 格式输出。"

        await self.emitter.emit_agent_action(
            "quiz", "generate", detail="正在出题",
            current_step=2, total_steps=4, step_label="出题", progress=30,
        )

        # 尝试结构化输出
        try:
            result = await self.llm.ainvoke_json(
                QuizPayload,
                full_prompt,
                temperature=0.3,
                function_name="generate_quiz",
                function_description="生成习题集，包含题目、选项、答案和解析",
            )
            quiz_data = result.model_dump(mode="json")
            content = json.dumps(quiz_data, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("[QuizAgent] 结构化输出失败，尝试 JSON 文本解析: %s", exc)

            await self.emitter.emit_agent_action(
                "quiz", "fallback", detail="正在重新整理习题格式",
                current_step=3, total_steps=4, step_label="格式整理", progress=55,
            )

            response = await self.llm.ainvoke(full_prompt, temperature=0.3)
            raw = response.content if hasattr(response, "content") else str(response)
            quiz_data = self._salvage_quiz_payload(raw)
            if quiz_data is None:
                return WorkerResult(success=False, error=f"习题 JSON 解析失败: {exc}")
            try:
                validated = QuizPayload.model_validate(quiz_data)
                quiz_data = validated.model_dump(mode="json")
            except Exception:
                pass
            content = json.dumps(quiz_data, ensure_ascii=False, indent=2)

        await self.emitter.emit_agent_action(
            "quiz", "analyze_answers", detail="正在编写答案解析",
            current_step=3, total_steps=4, step_label="编写解析", progress=75,
        )

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

        await self.emitter.emit_agent_action(
            "quiz", "done", detail=f"已生成 {len(questions)} 道习题",
            current_step=4, total_steps=4, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("quiz", status="success", message=f"已生成 {len(questions)} 道习题", progress=100)
        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - 习题集",
            summary=f"生成 {len(questions)} 道习题",
            summary_data=summary_data,
            metadata={
                "engine": "quiz_json",
                "question_count": len(questions),
                "exam_style": state.agent_config.get("exam_style", "school"),
                "agent_id": "quiz",
            },
        )

    def _build_input(self, state: WorkerState) -> str:
        parts = [f"## 学习需求\n{state.learning_need}"]

        # 学习者画像（首要依据）
        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像摘要\n{profile_text}")

        if state.blueprint:
            parts.append(f"## 教学蓝图\n{state.blueprint.model_dump_json(indent=2)}")

        if state.instruction:
            lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
            for c in state.instruction.constraints:
                lines.append(f"- 约束: {c}")
            parts.append("\n".join(lines))

        # Quiz-specific config
        config = state.agent_config
        if config:
            cfg_lines = ["## 习题配置"]
            cfg_lines.append(f"- 题目数量: {config.get('question_count', 5)}")
            cfg_lines.append(f"- 难度模式: {config.get('difficulty_mode', 'basic')}")
            cfg_lines.append(f"- 考试风格: {config.get('exam_style', 'school')}")
            cfg_lines.append(f"- 薄弱点权重: {config.get('weak_point_weight', 50)}%")
            cfg_lines.append(
                "- 每题包含详细解析" if config.get("include_analysis", True) else "- 不包含解析"
            )
            parts.append("\n".join(cfg_lines))

        return "\n\n".join(parts)

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