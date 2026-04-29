"""
Reporter Agent — Agent 执行报告生成器。

在每个 Worker Agent 执行完成后，生成一份执行报告，供下一层 Agent 参考。

报告内容：
- Agent 名称和任务描述
- 执行状态和结果摘要
- 生成内容的关键信息提取
- 产物文件路径

存储位置：workplace/userId/resourceId/{agent_type}_report.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.utils import write_agent_artifact, get_workspace_dir

logger = get_logger(__name__)


class ReporterAgent:
    """Agent 执行报告生成器。

    使用方式：
        reporter = ReporterAgent()
        report_path, report_content = await reporter.generate_report(
            user_id=1,
            resource_id=100,
            agent_type="content",
            task={"course": "Python", "gap": "变量", "need": "review"},
            content="生成的讲解内容...",
        )
    """

    def __init__(self):
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "reporter.md"

    async def generate_report(
        self,
        user_id: int,
        resource_id: int,
        agent_type: str,
        task: dict[str, Any],
        content: str,
        error: str | None = None,
    ) -> tuple[str, str]:
        """生成 Agent 执行报告。

        Args:
            user_id: 用户 ID
            resource_id: 资源 ID
            agent_type: Agent 类型（如 "content", "mindmap", "quiz"）
            task: 用户任务信息（course, gap, need 等）
            content: Agent 生成的内容
            error: 错误信息（如果执行失败）

        Returns:
            (报告路径, 报告内容)
        """
        logger.info("[ReporterAgent] 生成报告: agent_type=%s", agent_type)

        if error:
            # 失败时生成简化报告
            report = self._generate_failure_report(agent_type, task, error)
        else:
            # 成功时生成详细报告
            report = await self._generate_success_report(agent_type, task, content)

        # 写入产物
        artifact_path = await write_agent_artifact(
            user_id, resource_id, f"{agent_type}_report", report, file_type="md"
        )

        logger.info("[ReporterAgent] 报告已保存: %s", artifact_path)

        return artifact_path, report

    def _generate_failure_report(
        self,
        agent_type: str,
        task: dict[str, Any],
        error: str,
    ) -> str:
        """生成失败报告。"""
        report_lines = [
            f"# {agent_type} Agent 执行报告",
            "",
            f"**执行状态**: ❌ 失败",
            f"**执行时间**: {self._get_timestamp()}",
            "",
            "## 任务信息",
            "",
            f"- **课程主题**: {task.get('course', '未知')}",
            f"- **知识点**: {task.get('gap', '未知')}",
            f"- **需求类型**: {task.get('need', 'review')}",
            "",
            "## 错误信息",
            "",
            f"```\n{error or '未知错误'}\n```",
            "",
            "## 影响",
            "",
            f"由于 {agent_type} Agent 执行失败，依赖此产物的后续 Agent 可能无法正常执行。",
        ]

        return "\n".join(report_lines)

    async def _generate_success_report(
        self,
        agent_type: str,
        task: dict[str, Any],
        content: str,
    ) -> str:
        """生成成功报告。"""
        # 使用 LLM 提取关键信息
        key_info = await self._extract_key_info(agent_type, content, task)

        report_lines = [
            f"# {agent_type} Agent 执行报告",
            "",
            f"**执行状态**: ✅ 成功",
            f"**执行时间**: {self._get_timestamp()}",
            "",
            "## 任务信息",
            "",
            f"- **课程主题**: {task.get('course', '未知')}",
            f"- **知识点**: {task.get('gap', '未知')}",
            f"- **需求类型**: {task.get('need', 'review')}",
            "",
            "## 执行摘要",
            "",
            key_info.get("summary", "无摘要"),
            "",
            "## 关键内容",
            "",
            key_info.get("key_points", "无关键内容"),
            "",
            "## 产物信息",
            "",
            f"- **内容长度**: {len(content)} 字符",
            "",
            "## 可供后续 Agent 参考",
            "",
            key_info.get("reference_hint", "无参考提示"),
            "",
            "---",
            "",
            f"*此报告由 ReporterAgent 自动生成，供下一层 Agent 参考。*",
        ]

        return "\n".join(report_lines)

    async def _extract_key_info(
        self,
        agent_type: str,
        content: str,
        task: dict[str, Any],
    ) -> dict[str, str]:
        """使用 LLM 提取关键信息。"""
        prompt = self._load_prompt()

        # 限制内容长度
        content_preview = content[:3000] if len(content) > 3000 else content

        input_text = f"""## Agent 信息
- Agent 类型: {agent_type}
- 课程主题: {task.get('course', '')}
- 知识点: {task.get('gap', '')}

## 生成内容
{content_preview}

请提取关键信息，输出 JSON 格式。"""

        try:
            response = await self.llm_manager.ainvoke(
                "deepseek",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            from app.shared.json_utils import parse_first_json_object

            response_content = response.content if hasattr(response, "content") else str(response)
            result = parse_first_json_object(response_content)

            if result:
                return {
                    "summary": result.get("summary", ""),
                    "key_points": result.get("key_points", ""),
                    "reference_hint": result.get("reference_hint", ""),
                }

        except Exception as exc:
            logger.warning("[ReporterAgent] LLM 提取失败: %s", exc)

        # Fallback: 简化提取
        return self._fallback_extract(agent_type, content, task)

    def _fallback_extract(
        self,
        agent_type: str,
        content: str,
        task: dict[str, Any],
    ) -> dict[str, str]:
        """Fallback 关键信息提取。"""
        # 提取前 500 字作为摘要
        summary = content[:500] if content else "无内容"

        # 提取标题作为关键点
        lines = content.split("\n")
        headings = [line for line in lines if line.startswith("#")][:5]
        key_points = "\n".join(headings) if headings else "无关键标题"

        reference_hint = f"{agent_type} Agent 已生成关于 {task.get('course', '')} 的 {task.get('gap', '')} 相关内容，可直接读取产物文件获取完整信息。"

        return {
            "summary": summary,
            "key_points": key_points,
            "reference_hint": reference_hint,
        }

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")

        return """你是一个 Agent 执行报告分析器。请从 Agent 生成的内容中提取关键信息。

## 输出格式

请输出以下 JSON 结构：

```json
{
  "summary": "一句话描述 Agent 完成了什么任务，生成了什么内容",
  "key_points": "列出 3-5 个关键内容点，使用 Markdown 列表格式",
  "reference_hint": "一句话提示后续 Agent 如何参考此产物"
}
```

## 要求

1. summary 应简洁明了，不超过 100 字
2. key_points 应提取内容的核心结构或关键信息
3. reference_hint 应说明此产物对后续 Agent 的价值
"""

    def _get_timestamp(self) -> str:
        """获取当前时间戳。"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")