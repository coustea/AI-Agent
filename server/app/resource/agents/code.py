"""
代码智能体 — 生成代码示例，支持多种编程语言和案例类型。
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


class CodePayload(BaseModel):
    """代码资源的结构化输出。"""

    code: str = Field(description="完整代码内容")
    explanation: str = Field(default="", description="代码说明")
    language: str = Field(default="python", description="编程语言")


class CodeAgent:
    """代码生成 Agent。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("code", status="running", message="正在生成代码示例")

        prompt = registry.get("resource/code")
        input_text = self._build_input(state)
        full_prompt = f"{prompt}\n\n{input_text}\n\n请以 JSON 格式输出，包含 code 和 explanation 字段。"

        lang = state.agent_config.get("programming_language", "python")

        # 尝试结构化 JSON 输出
        try:
            payload = await self.llm.ainvoke_json(
                CodePayload,
                full_prompt,
                temperature=0.2,
                function_name="generate_code_example",
                function_description="生成代码示例，包含代码、说明和编程语言",
            )
            code_data = payload.model_dump(mode="json")
        except Exception as exc:
            logger.warning("[CodeAgent] JSON 输出失败，回退到纯文本: %s", exc)
            response = await self.llm.ainvoke(
                f"{prompt}\n\n{input_text}",
                temperature=0.2,
            )
            raw = response.content if hasattr(response, "content") else str(response)
            code_data = {
                "code": self._extract_code_from_output(raw),
                "explanation": "",
                "language": lang,
            }

        content = json.dumps(code_data, ensure_ascii=False, indent=2)
        case_type = state.agent_config.get("case_type", "basic_demo")
        difficulty = state.agent_config.get("difficulty", "beginner")
        include_test = state.agent_config.get("include_test", True)

        await self.emitter.emit_agent("code", status="success", message=f"{lang} 代码示例生成完成")
        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - 代码示例",
            summary=f"生成 {lang} 代码示例",
            summary_data={
                "language": lang,
                "case_type": case_type,
                "difficulty": difficulty,
                "include_test": include_test,
            },
            metadata={
                "engine": "code_json",
                "language": lang,
                "case_type": case_type,
                "agent_id": "code",
            },
        )

    def _build_input(self, state: WorkerState) -> str:
        parts = [f"## 学习需求\n{state.learning_need}"]

        # 学习者画像（首要依据）
        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像摘要\n{profile_text}")

        if state.knowledge_graph:
            parts.append(f"## 知识图谱\n{state.knowledge_graph.model_dump_json(indent=2)}")

        if state.instruction:
            lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
            for c in state.instruction.constraints:
                lines.append(f"- 约束: {c}")
            parts.append("\n".join(lines))

        # Code-specific config
        config = state.agent_config
        lang = config.get("programming_language", "python")
        case_type = config.get("case_type", "basic_demo")
        comment_level = config.get("comment_level", "standard")
        include_test = config.get("include_test", True)
        difficulty = config.get("difficulty", "beginner")

        code_lines = [
            "## 代码要求",
            f"- 编程语言: {lang}",
            f"- 案例类型: {case_type}",
            f"- 注释级别: {comment_level}",
            f"- 难度: {difficulty}",
        ]
        if include_test:
            code_lines.append("- 包含测试用例")
        if comment_level == "verbose":
            code_lines.append("- 每行关键代码都需要注释")
        elif comment_level == "minimal":
            code_lines.append("- 仅在关键逻辑处添加注释")
        parts.append("\n".join(code_lines))

        return "\n\n".join(parts)

    def _extract_code_from_output(self, content: str) -> str:
        """从纯文本输出中提取代码。"""
        pattern = r"```(?:\w+)?\s*\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content.strip()
