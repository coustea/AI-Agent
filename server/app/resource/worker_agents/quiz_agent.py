"""
Quiz Agent — 习题 Agent。

生成练习题、答案和解析（JSON 格式）。
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import (
    append_backend_context_for_prompt,
    learning_need_from_task,
    title_from_learning_need,
)
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)


class QuizOption(BaseModel):
    """选择题选项。"""

    model_config = ConfigDict(extra="allow")

    label: str = Field(description="选项标签，如 A/B/C/D")
    content: str = Field(description="选项内容")


class QuizQuestion(BaseModel):
    """单道习题，保留弹性字段以兼容多题型输出。"""

    model_config = ConfigDict(extra="allow")

    id: int = Field(description="题目序号")
    type: str = Field(description="题型")
    difficulty: str = Field(description="难度")
    knowledge_points: list[str] = Field(default_factory=list, description="知识点标签")
    question: str = Field(description="题干")
    options: list[QuizOption] = Field(default_factory=list, description="选择题选项")
    answer: str | bool | list[str] | None = Field(default=None, description="标准答案")
    explanation: str = Field(default="", description="解析")
    reference_answer: str | None = Field(default=None, description="简答题参考答案")
    scoring_points: list[str] = Field(default_factory=list, description="评分要点")


class QuizPayload(BaseModel):
    """QuizAgent 结构化输出。"""

    model_config = ConfigDict(extra="allow")

    title: str = Field(description="练习题标题")
    summary: str = Field(default="", description="考查重点简介")
    questions: list[QuizQuestion] = Field(default_factory=list, description="题目列表")


class QuizAgent:
    """习题 Agent。"""

    STEPS = ["分析输入", "融合画像与依赖", "生成内容", "整理输出"]
    ROLE_NAME = "自测题训练智能体"

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "quiz.md"

    async def _emit_action(
        self,
        state: WorkerState,
        action: str,
        detail: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
        current_action: str = "",
        output_preview: str = "",
    ) -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action(
                state.agent_name,
                action,
                detail,
                current_step=current_step,
                total_steps=total_steps,
                step_label=step_label,
                current_action=current_action,
                output_preview=output_preview,
                layer=state.layer_index,
                layer_name="检测巩固层",
                agent_role=self.ROLE_NAME,
                resource_type=state.agent_name,
            )

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行习题生成。"""
        logger.info("[QuizAgent] 开始执行: learning_need=%s", learning_need_from_task(state.task)[:80])
        total = 5

        await self._emit_action(
            state,
            "analyze_input",
            "自测题训练智能体正在分析检测目标",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[0],
            current_action="分析测评需求",
            output_preview="正在识别需要检测的知识点、题型数量和难度分布",
        )
        prompt = self._load_prompt()

        await self._emit_action(
            state,
            "merge_profile_dependencies",
            "自测题训练智能体正在读取上游资源和画像",
            current_step=3,
            total_steps=total,
            step_label=self.STEPS[1],
            current_action="融合画像与依赖",
            output_preview="正在结合 ContentAgent 与 CodeAgent 结果、薄弱点权重和考试风格",
        )
        input_text = await self._build_input(state)

        try:
            await self._emit_action(
                state,
                "generate_content",
                "自测题训练智能体正在生成练习题",
                current_step=4,
                total_steps=total,
                step_label=self.STEPS[2],
                current_action="生成自测题与解析",
                output_preview="正在生成题干、选项、答案、解析和易错点提示",
            )
            quiz_payload = await self._invoke_quiz_payload(prompt, input_text)

            quiz_json = quiz_payload.model_dump(mode="json", exclude_none=True)

            await self._emit_action(
                state,
                "finalize_output",
                "自测题训练智能体正在整理输出",
                current_step=5,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="整理测评资源",
                output_preview=quiz_payload.summary or str(quiz_json)[:240],
            )
            questions = quiz_json.get("questions", [])
            question_count = len(questions) if isinstance(questions, list) else 0

            return WorkerResult.model_construct(
                success=True,
                content=quiz_json,
                file_type="json",
                title=title_from_learning_need(state.task, "个性化练习题"),
                summary="生成练习题、答案与解析",
                metadata={"question_count": question_count},
            )

        except Exception as exc:
            logger.exception("[QuizAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

    async def _invoke_quiz_payload(self, prompt: str, input_text: str) -> QuizPayload:
        """优先走结构化输出，失败时回退到 JSON 文本解析。"""
        messages = [HumanMessage(content=f"{prompt}\n\n{input_text}")]

        try:
            return await self.llm_manager.ainvoke_structured(
                "spark_max",
                QuizPayload,
                messages,
                strict=True,
                function_name="submit_quiz",
                function_description="Submit a structured quiz JSON object for the resource generation system.",
                model_kwargs={"temperature": 0.2, "streaming": False},
            )
        except ValueError as exc:
            if "no tool_calls" not in str(exc):
                raise
            logger.warning("[QuizAgent] structured output 未返回 tool_calls，回退为 JSON 文本解析")

        response = await self.llm_manager.ainvoke(
            "spark_max",
            messages,
            model_kwargs={
                "temperature": 0.2,
                "streaming": False,
                "response_format": {"type": "json_object"},
            },
        )
        raw_content = response.content if hasattr(response, "content") else str(response)
        payload = parse_first_json_object(raw_content)
        return QuizPayload.model_validate(payload)

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位教育测评专家。请根据给定的内容，生成练习题。

要求输出 JSON 格式：
```json
{
  "title": "习题标题",
  "questions": [
    {
      "id": 1,
      "type": "choice|fill|short",
      "difficulty": "basic|intermediate|advanced",
      "question": "题目内容",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "answer": "正确答案",
      "analysis": "解析说明"
    }
  ]
}
```"""

    async def _build_input(self, state: WorkerState) -> str:
        """构建输入内容。"""
        task = state.task
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## 学习场景",
            f"- 场景类型: {state.learning_scenario}",
            "",
            "## Agent 配置",
            f"- 题目数量: {agent_config.get('question_count', 10)}",
            f"- 难度模式: {agent_config.get('difficulty_mode', 'adaptive')}",
            f"- 薄弱点权重: {agent_config.get('weak_point_weight', 50)}%",
            f"- 考试风格: {agent_config.get('exam_style', 'school')}",
            f"- 包含解析: {agent_config.get('include_analysis', True)}",
        ]

        append_backend_context_for_prompt(parts, state)

        parts.append("")
        parts.append("请基于学习需求生成练习题（JSON 格式）。")
        return "\n".join(parts)
