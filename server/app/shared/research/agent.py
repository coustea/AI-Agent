"""ResearchAgent - 独立的搜索子 Agent。

可以被 chat、resource、path 等模块调用。
只负责搜索和总结，不涉及存储或业务逻辑。
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.infra.tool_excute import ToolExcute
from app.infra.logging import get_logger
from app.shared.research.schemas import (
    ResearchDepth,
    ResearchError,
    ResearchEvidence,
    ResearchEvent,
    ResearchEventHandler,
    ResearchReport,
    ResearchTask,
)
from app.shared.research.tools import (
    RESEARCH_TOOL_ACTIONS,
    SEARCH_TOOL_NAMES,
    build_search_tools,
)

logger = get_logger(__name__)


# ============================================================================
# 失败标记（用于过滤无效搜索结果）
# ============================================================================

FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到结果",
    "未找到相关",
    "无可用搜索结果",
    "API Key",
    "未配置",
    "不可用",
    "失败",
)


# ============================================================================
# ResearchAgent 实现
# ============================================================================

class ResearchAgent:
    """搜索子 Agent。

    特点：
    1. 只负责搜索和总结，不存储数据
    2. 多引擎并发搜索，竞速返回
    3. 大模型总结搜索结果，提高质量
    4. 无状态，每次调用独立
    """

    def __init__(
        self,
        *,
        model: Any | None = None,
        tools: list[Any] | None = None,
        event_handler: ResearchEventHandler | None = None,
        system_prompt: str | None = None,
    ) -> None:
        """初始化 ResearchAgent。

        Args:
            model: 大模型实例（可选，默认使用系统配置）
            tools: 工具列表（可选，默认使用所有搜索工具）
            event_handler: 事件回调（可选，用于监听执行进度）
            system_prompt: 总结提示词（可选，默认使用内置模板）
        """
        llm = get_llm()
        self.model = model if model is not None else llm.model
        self.tools = list(tools) if tools is not None else build_search_tools()
        self.event_handler = event_handler
        self.system_prompt = system_prompt  # None = 从 prompts 注册表加载

    async def run(self, task: ResearchTask) -> ResearchReport:
        """执行搜索任务，返回总结后的报告。

        流程：
        1. 多引擎并发搜索
        2. 收集有效结果
        3. 大模型总结
        4. 返回结构化报告

        Args:
            task: 搜索任务定义

        Returns:
            ResearchReport: 搜索结果报告
        """
        logger.info("[ResearchAgent] starting search: query=%r", task.query)

        # 1. 创建请求级 ToolExcute
        tool_excute = ToolExcute(
            tools=self.tools,
            event_handler=self._emit_event,
        )

        # 2. ResearchAgent 只负责普通网页搜索与网页抓取。
        search_tasks = [
            self._search_tool(
                tool_excute,
                tool_name,
                task.query,
            )
            for tool_name in SEARCH_TOOL_NAMES
        ]

        # 3. 并发执行，收集结果
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # 4. 过滤有效结果
        valid_results: list[tuple[str, str]] = []
        errors = []

        for i, result in enumerate(all_results):
            if isinstance(result, Exception):
                logger.debug("[ResearchAgent] result[%d] is exception: %s", i, result)
                errors.append(ResearchError(
                    stage="search",
                    code="tool_error",
                    message=str(result),
                    recoverable=True,
                ))
                continue

            if self._is_valid_result(result):
                logger.debug("[ResearchAgent] result[%d] valid len=%d", i, len(str(result)))
                valid_results.append(result)
            else:
                reason = "too_short" if len(str(result).strip()) < 50 else "failure_marker"
                logger.debug("[ResearchAgent] result[%d] invalid reason=%s", i, reason)
                errors.append(ResearchError(
                    stage="filter",
                    code="invalid_result",
                    message="搜索结果无效或为失败标记",
                    recoverable=True,
                ))

        # 5. 如果没有有效结果
        if not valid_results:
            logger.warning("[ResearchAgent] no valid results: query=%r", task.query)
            return ResearchReport(
                query=task.query,
                errors=errors,
            )

        logger.info("[ResearchAgent] found %d valid results", len(valid_results))

        # 6. 大模型总结（不限制长度）
        import time
        start_time = time.time()
        summary = await self._summarize(task.query, [result for _, result in valid_results])
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info("[ResearchAgent] LLM summarize done duration_ms=%d input_chars=%d output_chars=%d",
                    duration_ms, len("\n\n---\n\n".join(result for _, result in valid_results)), len(summary))

        evidence = []
        for tool_name, result in valid_results:
            evidence.append(
                ResearchEvidence(
                    source_type="web",
                    summary=result[:500],
                    details={"tool_name": tool_name},
                    confidence=0.8,
                )
            )

        # 7. 构建报告
        report = ResearchReport(
            query=task.query,
            context=summary,
            evidence=evidence,
            errors=errors,
        )

        logger.info("[ResearchAgent] completed: query=%r context_length=%d", task.query, len(summary))
        return report

    async def _emit_event(self, event: dict[str, Any]) -> None:
        """补充展示语义后，把生命周期事件交还给调用方。"""
        if self.event_handler is None:
            return
        payload = dict(event)
        tool_name = str(payload.get("tool_name") or "")
        payload["action"] = RESEARCH_TOOL_ACTIONS.get(tool_name, "核验研究资料")
        await self.event_handler(payload)

    async def _search_tool(
        self,
        tool_excute: ToolExcute,
        tool_name: str,
        query: str,
    ) -> Any:
        """调用单个搜索工具。

        Args:
            tool_excute: 工具执行器
            tool_name: 工具名称
            query: 搜索查询

        Returns:
            搜索结果（可能是异常）
        """
        try:
            result = await tool_excute.execute({
                "id": f"{tool_name}-{uuid4().hex}",
                "name": tool_name,
                "args": {"query": query},
            })
            logger.debug("[ResearchAgent] tool=%s success result_len=%d", tool_name, len(str(result)))
            return tool_name, str(result)
        except Exception as exc:
            logger.warning("[ResearchAgent] tool=%s failed: %s", tool_name, exc)
            return exc

    def _is_valid_result(self, result: Any) -> bool:
        """检查搜索结果是否有效。

        Args:
            result: 搜索结果

        Returns:
            是否有效
        """
        if isinstance(result, Exception):
            return False

        text = str(result[1] if isinstance(result, tuple) and len(result) == 2 else result)
        if len(text.strip()) < 50:
            return False

        # 过滤失败标记
        for marker in FAILURE_MARKERS:
            if marker in text:
                return False

        return True

    async def _summarize(self, query: str, results: list[str]) -> str:
        """大模型总结搜索结果。

        Args:
            query: 搜索查询
            results: 有效搜索结果列表

        Returns:
            总结后的文本
        """
        # 合并搜索结果
        combined_results = "\n\n---\n\n".join(results)

        # 如果结果太长，截取（避免 token 超限）
        # 但不限制输出长度，让模型自由总结
        max_input_chars = 8000
        if len(combined_results) > max_input_chars:
            combined_results = combined_results[:max_input_chars]

        # 加载总结 prompt（优先使用外部模板，fallback 到内置简版）
        if self.system_prompt:
            system_content = self.system_prompt
        else:
            try:
                system_content = prompts.get("research").render(
                    "summary",
                    query=query,
                    objective="",
                )
            except Exception:
                system_content = "你是一个专业的信息总结助手。从搜索结果中提取关键信息，整理成清晰、结构化的总结。"

        # 构建总结 prompt
        prompt_messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=f"""请根据以下搜索结果，总结关于"{query}"的关键信息。

要求：
1. 提取核心观点和关键信息
2. 去除重复和冗余内容
3. 保持信息准确，不添加搜索结果中没有的内容
4. 用清晰的结构化格式呈现
5. 可以详细展开，不要限制长度

搜索结果：
{combined_results}

请总结："""),
        ]

        # 调用大模型
        try:
            response = await self.model.ainvoke(prompt_messages)
            return response.content
        except Exception as exc:
            logger.warning("[ResearchAgent] summarize failed: %s", exc)
            # 如果总结失败，直接返回合并的原始结果
            return combined_results
