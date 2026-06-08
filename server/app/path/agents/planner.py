import asyncio
import json
import re
from typing import Any, Awaitable, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from loguru import logger


from app.chat.tools.search import duckduckgo_search, serp_search, spark_search, tavily_search
from app.infra.llm import get_llm
from app.path.prompt_manager import path_prompts
from app.path.schemas import AgentLearningPathPlan, AgentPathNode, AgentStage, CreateLearningPathRequest

ProgressCallback = Callable[[str, int, str], Awaitable[None]]


class PathState(TypedDict):
    request: CreateLearningPathRequest
    profile: dict[str, Any]
    search_evidence: list[dict[str, Any]]
    progress_callback: ProgressCallback | None

    # Internal state
    strategy_report: str
    macro_stages: list[AgentStage]

    # Final output
    final_plan: AgentLearningPathPlan


class PathPlannerAgent:
    """课程级学习路径规划智能体 (LangGraph 多智能体实现)。"""

    def __init__(self, search_tools: list[Any] | None = None):
        self.llm = get_llm()
        self.search_tools = search_tools if search_tools is not None else [
            tavily_search,
            duckduckgo_search,
            serp_search,
            spark_search,
        ]
        self.max_search_tool_calls = 3
        self.max_search_evidence_chars = 6000
        self.system_prompt = path_prompts.planner_system()
        self.generate_graph = self._build_generate_graph()

    def _build_generate_graph(self):
        workflow = StateGraph(PathState)

        async def research_node(state: PathState) -> dict:
            logger.info("LangGraph [Path Research] starting...")
            if state["request"].enable_search:
                await emit_progress(state.get("progress_callback"), "researching", 30, "正在检索高价值参考资料")
            evidence_records = await self._collect_search_evidence(
                request=state["request"],
                profile=state["profile"],
            )
            logger.info("LangGraph [Path Research] finished with %d evidence records.", len(evidence_records))
            return {"search_evidence": evidence_records}

        async def node_strategist_node(state: PathState) -> dict:
            logger.info("LangGraph [Node Strategist] starting...")
            await emit_progress(state.get("progress_callback"), "analyzing", 44, "正在分析画像、目标与课程结构")
            await emit_progress(state.get("progress_callback"), "strategizing", 58, "正在生成阶段、节点与资源策略")
            profile_json = json.dumps(state["profile"], ensure_ascii=False, indent=2)
            request_context = format_path_request_context(state["request"])
            search_context = format_evidence_for_prompt(state.get("search_evidence", []))
            sys_msg = SystemMessage(content=path_prompts.planner_system())
            human_msg = HumanMessage(content=f"{request_context}{search_context}\n\n当前画像:\n{profile_json}")

            result = await self.llm.ainvoke_json(AgentLearningPathPlan, [sys_msg, human_msg])
            result = repair_generated_plan_from_macro_stages(
                plan=result,
                macro_stages=result.stages,
                request=state["request"],
                strategy_report=result.strategy_report,
            )
            logger.info(f"LangGraph [Node Strategist] finished with {len(result.nodes)} nodes.")
            return {"final_plan": result}

        workflow.add_node("research", research_node)
        workflow.add_node("strategist", node_strategist_node)

        workflow.add_edge(START, "research")
        workflow.add_edge("research", "strategist")
        workflow.add_edge("strategist", END)

        return workflow.compile()

    async def generate_plan(
        self,
        request: CreateLearningPathRequest,
        profile: dict[str, Any],
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[AgentLearningPathPlan, list[dict[str, Any]]]:
        """执行多智能体路径规划 (LangGraph版)。

        Returns:
            (plan, search_evidence_records) — 规划结果和结构化搜索证据列表。
        """
        logger.info("PathPlannerAgent 开始规划路径 - Topic: {}", request.topic)
        try:
            initial_state = {
                "request": request,
                "profile": profile,
                "search_evidence": [],
                "progress_callback": progress_callback,
                "strategy_report": "",
                "macro_stages": [],
                "final_plan": None
            }
            final_state = await self.generate_graph.ainvoke(initial_state)
            search_evidence = final_state.get("search_evidence", [])
            return final_state["final_plan"], search_evidence
        except Exception as e:
            logger.error(f"PathPlannerAgent 路径规划失败: {str(e)}")
            raise e

    async def _collect_search_evidence(
        self,
        request: CreateLearningPathRequest,
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Let the path planner call search tools when external evidence is useful.

        Returns structured evidence records: [{tool, query, title, url, snippet}].
        """
        if not request.enable_search or not self.search_tools:
            return []

        try:
            bound_model = self.llm.model.bind_tools(self.search_tools)
            messages = build_search_research_messages(request, profile)
            first_response = await self.llm.ainvoke(messages, model=bound_model, max_tokens=1000)
        except Exception as exc:
            logger.warning("[PathPlannerAgent] search tool setup failed: %s", exc)
            return []

        tool_calls = list(getattr(first_response, "tool_calls", []) or [])[: self.max_search_tool_calls]
        if not tool_calls:
            direct_content = message_content(first_response)
            if is_usable_search_result(direct_content):
                return _parse_text_evidence("llm_direct", "", direct_content[:self.max_search_evidence_chars])
            return []

        evidence_records = await self._run_search_tool_calls(tool_calls)
        return evidence_records

    async def _run_search_tool_calls(self, tool_calls: list[Any]) -> list[dict[str, Any]]:
        """Execute search tool calls and return structured evidence records."""
        tools_by_name = {tool.name: tool for tool in self.search_tools}
        record_groups = await asyncio.gather(*[
            self._run_single_search_tool_call(tool_call, tools_by_name)
            for tool_call in tool_calls
        ])
        all_records = [record for records in record_groups for record in records]

        total_chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in all_records)
        if total_chars > self.max_search_evidence_chars:
            all_records = _truncate_evidence_records(all_records, self.max_search_evidence_chars)

        return all_records

    async def _run_single_search_tool_call(
        self,
        tool_call: Any,
        tools_by_name: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Execute one search tool call and parse its evidence records."""
        try:
            tool_name, tool_args = parse_tool_call(tool_call)
            query = tool_args.get("query", "")
            result = await self._invoke_search_tool(
                tool=tools_by_name.get(tool_name),
                tool_name=tool_name,
                tool_args=tool_args,
            )

            if isinstance(result, dict):
                records = _parse_structured_evidence(tool_name, query, result)
            elif isinstance(result, str) and is_usable_search_result(result):
                records = _parse_text_evidence(tool_name, query, result)
            else:
                records = []
            return records
        except Exception as exc:
            logger.warning("[PathPlannerAgent] search tool call parsing failed: %s", exc)
            return []

    async def _invoke_search_tool(
        self,
        *,
        tool: Any | None,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> dict | str:
        """Invoke a search tool and return the raw result (dict or str)."""
        if tool is None:
            return f"搜索工具不存在: {tool_name}"
        try:
            result = await tool.ainvoke(tool_args)
            if isinstance(result, dict):
                return result
            return str(result)
        except Exception as exc:
            logger.warning("[PathPlannerAgent] search tool failed: tool=%s error=%s", tool_name, exc)
            return f"{tool_name} 搜索失败: {exc}"


def repair_generated_plan_from_macro_stages(
    *,
    plan: AgentLearningPathPlan,
    macro_stages: list[AgentStage],
    request: CreateLearningPathRequest,
    strategy_report: str,
) -> AgentLearningPathPlan:
    """Recover a structurally usable plan from the architect stage output.

    The planner is designed as a single LLM pass after research/profile/stage
    planning. If the final structured output omits stages or nodes, reuse the
    already-generated macro stages instead of retrying.
    """
    if not plan.stages and macro_stages:
        plan.stages = list(macro_stages)

    if strategy_report:
        plan.strategy_report = strategy_report

    if not plan.adjustment_rationale:
        plan.adjustment_rationale = ["基于画像与路径规划阶段骨架生成学习路径"]

    if not plan.nodes and plan.stages:
        previous_node_id = ""
        nodes: list[AgentPathNode] = []
        for index, stage in enumerate(plan.stages, 1):
            node_id = f"{stage.stage_id}-core"
            difficulty = "beginner" if index == 1 else "intermediate"
            if index == len(plan.stages) and len(plan.stages) >= 3:
                difficulty = "advanced"
            node = AgentPathNode(
                node_id=node_id,
                stage_id=stage.stage_id,
                title=stage.title,
                prerequisites=[previous_node_id] if previous_node_id else [],
                mastery_target=stage.description or f"完成{stage.title}阶段学习",
                estimated_minutes=45,
                difficulty=difficulty,
                recommendation_reason=(
                    f"围绕“{request.goal}”的阶段目标生成，"
                    "用于保证路径规划结果可直接开始学习"
                ),
                priority=index * 10,
            )
            nodes.append(node)
            previous_node_id = node_id
        plan.nodes = nodes

    return plan


async def emit_progress(
    callback: ProgressCallback | None,
    status: str,
    progress: int,
    message: str,
) -> None:
    if callback is None:
        return
    await callback(status, progress, message)


SEARCH_FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到相关搜索结果",
    "无可用搜索结果",
    "所有搜索引擎调用均失败",
)

def format_path_request_context(request: CreateLearningPathRequest) -> str:
    """Format learner request fields consistently for every planner agent."""
    current_knowledge = "、".join(request.current_knowledge) if request.current_knowledge else "未提供"
    preferences = (
        json.dumps(request.preferences, ensure_ascii=False, indent=2)
        if request.preferences
        else "未提供"
    )
    return (
        f"学习目标: {request.goal}\n"
        f"学习主题: {request.topic or '未提供'}\n"
        f"所属模块: {request.module}\n"
        f"已掌握知识: {current_knowledge}\n"
        f"学习偏好:\n{preferences}"
    )


def is_usable_search_result(result: object) -> bool:
    """Return whether a search provider response has useful planning evidence."""
    text = str(result or "").strip()
    if not text:
        return False
    return not any(marker in text for marker in SEARCH_FAILURE_MARKERS)


def build_search_research_messages(request: CreateLearningPathRequest, profile: dict[str, Any]) -> list[Any]:
    """Build messages that let the planner choose search tools."""
    profile_context = (
        json.dumps(profile, ensure_ascii=False, indent=2)
        if profile
        else "未提供"
    )
    return [
        SystemMessage(content=path_prompts.search_research_system()),
        HumanMessage(
            content=path_prompts.render_search_research_user(
                request_context=format_path_request_context(request),
                profile_context=profile_context,
            )
        ),
    ]


def parse_tool_call(tool_call: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(tool_call, dict):
        name = str(tool_call.get("name", ""))
        args = tool_call.get("args") or {}
    else:
        name = str(getattr(tool_call, "name", ""))
        args = getattr(tool_call, "args", {}) or {}
    return name, dict(args)


def message_content(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content or "")


def _parse_structured_evidence(tool_name: str, query: str, result: dict) -> list[dict[str, Any]]:
    """Parse a structured search result dict into evidence records.

    Handles spark_search format: {"query": ..., "results": [{title, summary, url, ...}]}
    and similar dict-based results.
    """
    records: list[dict[str, Any]] = []
    items = result.get("results", [])
    if not items:
        if any(k in result for k in ("title", "summary", "snippet", "url")):
            items = [result]
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "") or item.get("name", "")
        url = item.get("url", "") or item.get("link", "")
        snippet = item.get("summary", "") or item.get("snippet", "") or item.get("content", "")
        if not title and not snippet:
            continue
        records.append({
            "tool": tool_name,
            "query": query,
            "title": str(title)[:200],
            "url": str(url)[:500],
            "snippet": str(snippet)[:500],
        })
    return records


_SERP_ITEM_PATTERN = re.compile(
    r"\d+\.\s*(?P<title>.+?)\n\s*链接:\s*(?P<url>\S+)\n\s*摘要:\s*(?P<snippet>.+?)(?=\n\n|\Z)",
    re.DOTALL,
)


def _parse_text_evidence(tool_name: str, query: str, text: str) -> list[dict[str, Any]]:
    """Parse plain-text search results into evidence records.

    Handles serp_search format: "1. Title\\n   链接: URL\\n   摘要: snippet"
    and generic text (tavily, duckduckgo) as single-record fallback.
    """
    records: list[dict[str, Any]] = []
    for m in _SERP_ITEM_PATTERN.finditer(text):
        records.append({
            "tool": tool_name,
            "query": query,
            "title": m.group("title").strip()[:200],
            "url": m.group("url").strip()[:500],
            "snippet": m.group("snippet").strip()[:500],
        })
    if not records:
        records.append({
            "tool": tool_name,
            "query": query,
            "title": "",
            "url": "",
            "snippet": text.strip()[:500],
        })
    return records


def _truncate_evidence_records(records: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    """Truncate evidence records to fit within max_chars total JSON size."""
    kept: list[dict[str, Any]] = []
    total = 0
    for r in records:
        size = len(json.dumps(r, ensure_ascii=False))
        if total + size > max_chars:
            logger.warning("[PathPlannerAgent] search evidence truncated: %d/%d records kept", len(kept), len(records))
            break
        kept.append(r)
        total += size
    return kept


def format_evidence_for_prompt(records: list[dict[str, Any]]) -> str:
    """Format structured evidence records into prompt text with anti-hallucination disclaimer."""
    if not records:
        return ""
    lines = [
        "\n\n联网检索参考:",
        "以下内容只作为课程路径规划的外部参考。必须优先服从用户目标、画像和已掌握知识；"
        "不得编造检索资料未支持的事实，不要把搜索摘要中的广告、无关页面或不确定内容写成课程结论。",
        "引用检索资料时必须标明出处编号（如[检索1]）。",
    ]
    for i, r in enumerate(records, 1):
        title_part = f"标题: {r['title']}" if r.get("title") else ""
        url_part = f"来源: {r['url']}" if r.get("url") else ""
        snippet_part = f"摘要: {r['snippet']}" if r.get("snippet") else ""
        entry_lines = [f"[检索{i}] 工具: {r['tool']} | 检索词: {r['query']}"]
        if title_part:
            entry_lines.append(f"  {title_part}")
        if url_part:
            entry_lines.append(f"  {url_part}")
        if snippet_part:
            entry_lines.append(f"  {snippet_part}")
        lines.append("\n".join(entry_lines))
    return "\n".join(lines)
