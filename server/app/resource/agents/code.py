"""
代码 Agent — 生成代码示例，支持多种编程语言和案例类型。
"""

from __future__ import annotations

import json
import re

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.agents.base import Agent
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


class CodeAgent(Agent):
    """代码生成 Agent。"""

    AGENT_NAME = "code"
    ROLE_NAME = "代码生成智能体"
    STEPS = ["分析输入", "融合画像与依赖", "生成代码", "整理输出"]

    def _default_template_values(self) -> dict[str, str]:
        return {
            "programming_language": "python",
            "case_type": "basic_demo",
            "comment_level": "standard",
            "difficulty": "beginner",
            "include_test_instruction": "包含测试用例",
        }

    def _resolve_template_variables(self, variables: set, state: WorkerState) -> dict[str, str]:
        """Code Agent 特殊变量解析。"""
        result = super()._resolve_template_variables(variables, state)
        config = state.agent_config or {}

        if "include_test_instruction" in variables:
            result["include_test_instruction"] = "包含测试用例" if config.get("include_test", True) else "不包含测试用例"

        return result

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        lang = state.agent_config.get("programming_language", "python")
        case_type = state.agent_config.get("case_type", "basic_demo")
        comment_level = state.agent_config.get("comment_level", "standard")
        include_test = state.agent_config.get("include_test", True)
        difficulty = state.agent_config.get("difficulty", "beginner")

        code_instruction = self._build_code_instruction(lang, case_type, comment_level, include_test, difficulty)
        full_input = f"{input_text}\n\n{code_instruction}"

        llm = get_llm_manager()

        # 尝试 JSON 结构化输出
        try:
            response = await llm.generate_json(
                None,
                f"{prompt}\n\n{full_input}\n\n请以 JSON 格式输出，包含 code 和 explanation 字段。",
                model_kwargs={"temperature": 0.2, "model_kwargs": {"response_format": {"type": "json_object"}}},
            )
            raw = response.content if hasattr(response, "content") else str(response)
            code_data = self._parse_code_json(raw)
        except Exception as exc:
            logger.warning("[CodeAgent] JSON 输出失败，回退到纯文本: %s", exc)
            response = await llm.generate(
                f"{prompt}\n\n{full_input}",
                model_kwargs={"temperature": 0.2},
            )
            raw = response.content if hasattr(response, "content") else str(response)
            code_data = {
                "code": self._extract_code_from_output(raw),
                "explanation": "",
                "language": lang,
            }

        content = json.dumps(code_data, ensure_ascii=False, indent=2)

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=self._title(state, "代码示例"),
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

    def _build_code_instruction(
        self,
        lang: str,
        case_type: str,
        comment_level: str,
        include_test: bool,
        difficulty: str,
    ) -> str:
        parts = [
            "## 代码要求",
            f"- 编程语言: {lang}",
            f"- 案例类型: {case_type}",
            f"- 注释级别: {comment_level}",
            f"- 难度: {difficulty}",
        ]
        if include_test:
            parts.append("- 包含测试用例")
        if comment_level == "verbose":
            parts.append("- 每行关键代码都需要注释")
        elif comment_level == "minimal":
            parts.append("- 仅在关键逻辑处添加注释")
        return "\n".join(parts)

    def _parse_code_json(self, raw: str) -> dict:
        """解析 JSON 格式的代码输出。"""
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "code" in data:
                return data
        except json.JSONDecodeError:
            pass

        pattern = r"```(?:json)?\s*\n(.*?)```"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "code" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return {"code": raw, "explanation": "", "language": "python"}

    def _extract_code_from_output(self, content: str) -> str:
        """从纯文本输出中提取代码。"""
        pattern = r"```(?:\w+)?\s*\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content.strip()

    def _input_suffix(self) -> str:
        return "请生成代码示例。"