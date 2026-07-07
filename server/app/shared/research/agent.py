"""ResearchAgent - 统一搜索子 Agent。

可以被 chat、resource、path 等模块调用。
支持两种搜索来源：
  - web: 联网搜索（DuckDuckGo / Tavily / 星火 等）
  - knowledge_base: 本地知识库检索（ChromaDB + BM25 + RRF 融合）

只负责搜索和返回结构化结果，不涉及 LLM 总结、存储或业务逻辑。
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute
from app.shared.research.schemas import (
    ResearchError,
    ResearchEvent,
    ResearchEventHandler,
    ResearchReport,
    ResearchSourceItem,
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
    "本地知识库当前不可用",
    "本地知识库没有检索到",
)

# 知识库工具名
_KB_TOOL_NAME = "search_knowledge_base"

# Web 搜索工具名集合
_WEB_TOOL_NAMES = frozenset(set(SEARCH_TOOL_NAMES) - {_KB_TOOL_NAME})


# ============================================================================
# ResearchAgent 实现
# ============================================================================

class ResearchAgent:
    """统一搜索子 Agent。

    特点：
    1. 并发执行联网搜索 + 知识库检索
    2. 根据 task.sources 控制启用哪些来源
    3. 结果统一到 ResearchReport（web → sources，KB → knowledge_chunks + sources）
    4. 无状态，每次调用独立
    """

    def __init__(
        self,
        *,
        tools: list[Any] | None = None,
        event_handler: ResearchEventHandler | None = None,
    ) -> None:
        self.tools = list(tools) if tools is not None else build_search_tools()
        self.event_handler = event_handler

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def run(self, task: ResearchTask) -> ResearchReport:
        """执行搜索任务，返回结构化结果。

        流程：
        1. 根据 task.sources 过滤要调用的工具
        2. 并发搜索（Web + KB）
        3. 解析有效结果，KB 结果同时写入 knowledge_chunks 和 sources
        4. 去重并返回
        """
        logger.info(
            "[ResearchAgent] starting: query=%r sources=%s",
            task.query, task.sources,
        )

        # 1. 确定要调用的工具名
        tool_names = self._filter_tool_names(task.sources)

        # 2. 创建请求级 ToolExcute
        tool_excute = ToolExcute(
            tools=self.tools,
            event_handler=self._emit_event,
        )

        # 3. 并发搜索
        search_tasks = [
            self._search_tool(tool_excute, name, task.query, task.context)
            for name in tool_names
        ]
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # 4. 解析有效结果
        sources: list[ResearchSourceItem] = []
        knowledge_chunks: list[Any] = []
        errors: list[ResearchError] = []

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

            tool_name, result_data = result

            # 知识库工具返回结构化 dict
            if tool_name == _KB_TOOL_NAME and isinstance(result_data, dict):
                kb_items, kb_chunks = self._parse_kb_result(result_data)
                sources.extend(kb_items)
                knowledge_chunks.extend(kb_chunks)
                if not kb_items:
                    errors.append(ResearchError(
                        stage="filter",
                        code="kb_empty",
                        message="知识库检索未返回有效结果",
                        recoverable=True,
                    ))
                continue

            # Web 搜索工具返回格式化文本
            result_text = str(result_data)
            if self._is_valid_text(result_text):
                parsed = self._parse_search_text(result_text, tool_name)
                sources.extend(parsed)
                logger.debug(
                    "[ResearchAgent] result[%d] web parsed %d items",
                    i, len(parsed),
                )
            else:
                reason = "too_short" if len(result_text.strip()) < 50 else "failure_marker"
                logger.debug("[ResearchAgent] result[%d] invalid reason=%s", i, reason)
                errors.append(ResearchError(
                    stage="filter",
                    code="invalid_result",
                    message="搜索结果无效或为失败标记",
                    recoverable=True,
                ))

        # 5. 去重（Web 按 URL，KB 按 chunk_id）
        unique_sources: list[ResearchSourceItem] = []
        seen_keys: set[str] = set()
        for s in sources:
            dedup_key = s.chunk_id if s.source == "knowledge_base" else s.url
            if not dedup_key or dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            unique_sources.append(s)

        logger.info(
            "[ResearchAgent] completed: query=%r sources=%d kb_chunks=%d",
            task.query, len(unique_sources), len(knowledge_chunks),
        )

        # 6. 返回报告
        return ResearchReport(
            query=task.query,
            sources=unique_sources,
            knowledge_chunks=knowledge_chunks,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # 工具过滤
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_tool_names(requested_sources: set[str]) -> list[str]:
        """根据请求的来源集合过滤工具名列表。

        - "web" → 所有 Web 搜索工具
        - "knowledge_base" → search_knowledge_base
        - 默认两者都包含
        """
        result: list[str] = []
        for name in SEARCH_TOOL_NAMES:
            if name in _WEB_TOOL_NAMES and "web" not in requested_sources:
                continue
            if name == _KB_TOOL_NAME and "knowledge_base" not in requested_sources:
                continue
            result.append(name)
        return result

    # ------------------------------------------------------------------
    # 知识库结果解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_kb_result(
        result: dict[str, Any],
    ) -> tuple[list[ResearchSourceItem], list[Any]]:
        """将知识库搜索工具返回的 dict 解析为 ResearchSourceItem + RetrievedChunk。

        Returns:
            (sources, chunks) — sources 用于统一的格式化输出，
            chunks 保留原始结构供需要完整元数据的调用方使用。
        """
        if result.get("status") in ("empty", "unavailable"):
            return [], []

        from app.rag.models import RetrievedChunk

        kb_sources: list[ResearchSourceItem] = []
        kb_chunks: list[RetrievedChunk] = []
        for raw in result.get("sources", []):
            # 构造 RetrievedChunk 保留原始结构
            chunk = RetrievedChunk(
                chunk_id=str(raw.get("chunk_id", "")),
                content=str(raw.get("summary", raw.get("content", ""))),
                source=str(raw.get("source", "")),
                title=str(raw.get("title", "")),
                section=str(raw.get("section", "")),
                course=str(raw.get("course", "")),
                heading_path=str(raw.get("heading_path", "")),
                page=raw.get("page"),
                score=raw.get("score"),
                retrieval_type=str(raw.get("retrieval_type", "")),
                chunk_index=raw.get("chunk_index"),
                distance=None,
                parent_id="",
            )
            kb_chunks.append(chunk)

            # 同时构造 ResearchSourceItem 供统一格式化
            kb_sources.append(ResearchSourceItem(
                source="knowledge_base",
                title=str(raw.get("title", "")),
                url="",
                summary=str(raw.get("summary", "")),
                chunk_id=str(raw.get("chunk_id", "")),
                section=str(raw.get("section", "")),
                course=str(raw.get("course", "")),
                heading_path=str(raw.get("heading_path", "")),
                page=raw.get("page"),
                score=raw.get("score"),
                retrieval_type=str(raw.get("retrieval_type", "")),
            ))

        return kb_sources, kb_chunks

    # ------------------------------------------------------------------
    # 事件与工具执行
    # ------------------------------------------------------------------

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
        course_name: str | None = None,
    ) -> Any:
        """调用单个搜索工具。

        Args:
            tool_excute: 工具执行器
            tool_name: 工具名称
            query: 搜索查询
            course_name: 课程名（仅知识库工具需要）

        Returns:
            (tool_name, result_data) — web 工具返回 str，
            知识库工具返回结构化 dict。
        """
        try:
            args: dict[str, Any] = {"query": query}
            if tool_name == _KB_TOOL_NAME and course_name:
                args["course_name"] = course_name

            result = await tool_excute.execute({
                "id": f"{tool_name}-{uuid4().hex}",
                "name": tool_name,
                "args": args,
            })

            # 知识库工具直接返回 dict；其他工具返回文本
            if tool_name == _KB_TOOL_NAME and isinstance(result, dict):
                logger.debug(
                    "[ResearchAgent] tool=%s success (dict, status=%s)",
                    tool_name, result.get("status"),
                )
                return tool_name, result

            result_text = str(result)
            logger.debug(
                "[ResearchAgent] tool=%s success result_len=%d",
                tool_name, len(result_text),
            )
            return tool_name, result_text
        except Exception as exc:
            logger.warning("[ResearchAgent] tool=%s failed: %s", tool_name, exc)
            return exc

    # ------------------------------------------------------------------
    # Web 搜索结果验证与解析
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_text(text: str) -> bool:
        """检查 Web 搜索结果文本是否有效。"""
        if len(text.strip()) < 50:
            return False
        for marker in FAILURE_MARKERS:
            if marker in text:
                return False
        return True

    @staticmethod
    def _parse_search_text(text: str, source: str) -> list[ResearchSourceItem]:
        """解析 Web 搜索工具返回的格式化字符串为结构化数据。"""
        results: list[ResearchSourceItem] = []
        lines = text.split("\n")
        current: dict[str, str] = {"source": source}

        for line in lines:
            line = line.strip()

            if line and line[0].isdigit() and ". " in line:
                if current.get("url"):
                    results.append(ResearchSourceItem(
                        source=current.get("source", source),
                        title=current.get("title", ""),
                        url=current.get("url", ""),
                        summary=current.get("summary", ""),
                    ))
                current = {"source": source}
                current["title"] = line.split(". ", 1)[-1]

            elif "链接:" in line or "链接 :" in line:
                url = line.split("链接:")[-1].split("链接 :")[-1].strip()
                if url.startswith("http"):
                    current["url"] = url

            elif "摘要:" in line or "摘要 :" in line:
                snippet = line.split("摘要:")[-1].split("摘要 :")[-1].strip()
                current["summary"] = snippet

        if current.get("url"):
            results.append(ResearchSourceItem(
                source=current.get("source", source),
                title=current.get("title", ""),
                url=current.get("url", ""),
                summary=current.get("summary", ""),
            ))

        return results
