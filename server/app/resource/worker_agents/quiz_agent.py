"""
Quiz Agent — 习题 Agent。

生成练习题、答案和解析（JSON 格式）。
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import generate_execution_report
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)


class QuizAgent:
    """习题 Agent。"""

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "quiz.md"

    async def _emit_action(self, action: str, detail: str = "") -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action("quiz", action, detail)

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行习题生成。"""
        logger.info("[QuizAgent] 开始执行: topic=%s", state.task.get("topic", ""))

        await self._emit_action("loading_prompt", "加载习题生成提示词")
        prompt = self._load_prompt()

        await self._emit_action("building_input", "构建输入内容，整合任务信息和依赖报告")
        input_text = await self._build_input(state)

        try:
            await self._emit_action("calling_llm", "调用 spark_x 生成习题")

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            content = response.content if hasattr(response, "content") else str(response)

            await self._emit_action("parsing_json", "解析习题 JSON 结构")

            quiz_json = self._parse_quiz_json(content)

            if quiz_json is None:
                logger.warning("[QuizAgent] JSON 解析失败，返回原始内容")
                quiz_json = {"error": "解析失败", "raw_content": content}

            await self._emit_action("finalizing_result", "生成习题 JSON")
            questions = quiz_json.get("questions", [])
            question_count = len(questions) if isinstance(questions, list) else 0

            execution_report = generate_execution_report(
                agent_type="quiz",
                task=state.task,
                content=quiz_json,
                success=True,
            )

            return WorkerResult.model_construct(
                success=True,
                content=quiz_json,
                file_type="json",
                title=f"{state.task.get('topic', state.task.get('course', ''))} - 个性化练习题",
                summary="生成练习题、答案与解析",
                execution_report=execution_report,
                metadata={"question_count": question_count},
            )

        except Exception as exc:
            logger.exception("[QuizAgent] 执行失败")

            execution_report = generate_execution_report(
                agent_type="quiz",
                task=state.task,
                content=None,
                success=False,
                error=str(exc),
            )

            return WorkerResult(success=False, error=str(exc), execution_report=execution_report)

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
        personalization = state.personalization
        agent_config = state.agent_config
        profile = state.learner_profile

        parts = [
            "## 课程信息",
            f"- 课程: {task.get('course', '')}",
            f"- 章节: {task.get('chapter', '')}",
            f"- 学习主题: {task.get('topic', task.get('course', ''))}",
            f"- 知识短板: {', '.join(task.get('weak_points', []))}",
            f"- 学习目标: {task.get('learning_goal', '')}",
            "",
            "## 个性化配置",
            f"- 当前水平: {personalization.get('current_level', 'basic')}",
            f"- 目标水平: {personalization.get('target_level', 'understand')}",
            f"- 讲解风格: {personalization.get('explanation_style', 'easy')}",
            "",
            "## Agent 配置",
            f"- 题目数量: {agent_config.get('question_count', 10)}",
            f"- 题型: {', '.join(agent_config.get('question_types', ['choice', 'blank', 'short_answer']))}",
            f"- 难度模式: {agent_config.get('difficulty_mode', 'adaptive')}",
            f"- 聚焦短板: {agent_config.get('focus_on_weak_points', True)}",
            f"- 包含答案: {agent_config.get('include_answer', True)}",
            f"- 包含解析: {agent_config.get('include_analysis', True)}",
            f"- 包含错误原因: {agent_config.get('include_wrong_reason', True)}",
            f"- 包含知识点标签: {agent_config.get('include_knowledge_tags', True)}",
        ]

        if profile:
            parts.append("")
            parts.append("## 学习者画像")
            profile_markdown = profile.get("profile_markdown", "")
            if profile_markdown:
                parts.append(profile_markdown)

        if state.upstream_results:
            parts.append("")
            parts.append("## 上游结果摘要")
            for agent_id, result in state.upstream_results.items():
                content_preview = str(result.get("content", ""))[:300]
                parts.append(f"- {agent_id}: {content_preview}...")

        parts.append("")
        parts.append("请生成练习题（JSON 格式）。")
        return "\n".join(parts)

    def _parse_quiz_json(self, content: str) -> dict | None:
        """解析 LLM 返回的 JSON。"""
        try:
            return parse_first_json_object(content)
        except (TypeError, ValueError):
            return None
