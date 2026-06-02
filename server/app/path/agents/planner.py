import json
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from loguru import logger
from pydantic import BaseModel, Field

from app.chat.tools.search import duckduckgo_search, serp_search, spark_search, tavily_search
from app.infra.llm import get_llm
from app.path.schemas import AgentCoursePathPlan, AgentStage, GeneratePathRequest


class StrategyReport(BaseModel):
    strategy_report: str = Field(description="详细的个性化诊断与裁剪策略报告")


class MacroStages(BaseModel):
    stages: list[AgentStage] = Field(description="宏观阶段骨架列表")


class PathState(TypedDict):
    request: GeneratePathRequest
    profile: dict[str, Any]
    search_evidence: list[dict[str, Any]]

    # Internal state
    strategy_report: str
    macro_stages: list[AgentStage]

    # Final output
    final_plan: AgentCoursePathPlan


class AdjustState(TypedDict):
    active_path: Any
    completed_nodes: list[Any]
    remaining_nodes: list[Any]
    profile: dict[str, Any]
    feedback: str
    weak_points: list[str]
    resource_context: str

    # Internal state
    diagnosis_report: str

    # Final output
    final_plan: AgentCoursePathPlan


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
        self.system_prompt = NODE_STRATEGIST_SYSTEM_PROMPT
        self.generate_graph = self._build_generate_graph()
        self.adjust_graph = self._build_adjust_graph()

    def _build_generate_graph(self):
        workflow = StateGraph(PathState)

        async def research_node(state: PathState) -> dict:
            logger.info("LangGraph [Path Research] starting...")
            evidence_records = await self._collect_search_evidence(
                request=state["request"],
                profile=state["profile"],
            )
            logger.info("LangGraph [Path Research] finished with %d evidence records.", len(evidence_records))
            return {"search_evidence": evidence_records}

        async def profile_analyst_node(state: PathState) -> dict:
            logger.info("LangGraph [Profile Analyst] starting...")
            profile_json = json.dumps(state["profile"], ensure_ascii=False, indent=2)
            request_context = format_path_request_context(state["request"])
            search_context = format_evidence_for_prompt(state.get("search_evidence", []))
            sys_msg = SystemMessage(content="""你是一个世界顶级的学习画像诊断专家。
                你的任务是对比用户的学习目标与他们的个人画像，输出一份诊断与裁剪策略。
                如果用户在某方面已经掌握，你需要明确指出"可跳过或快速复习"；
                如果用户缺乏某前置基础，你需要明确指出"必须补充前置基础"。
                重点分析其认知风格和薄弱点，为后续的规划定下基调。
                引用检索资料时必须标明出处，不得编造检索资料未支持的事实。"""
                )
            human_msg = HumanMessage(content=f"{request_context}{search_context}\n\n当前画像:\n{profile_json}")

            result = await self.llm.ainvoke_json(StrategyReport, [sys_msg, human_msg])
            logger.info("LangGraph [Profile Analyst] finished.")
            return {
                "strategy_report": result.strategy_report
            }

        async def curriculum_architect_node(state: PathState) -> dict:
            logger.info("LangGraph [Curriculum Architect] starting...")
            request_context = format_path_request_context(state["request"])
            search_context = format_evidence_for_prompt(state.get("search_evidence", []))
            sys_msg = SystemMessage(content="""你是一个世界顶级的课程架构师。
                你的任务是根据用户的学习目标、主题和个性化诊断策略，设计出宏观的学习阶段骨架（stages）。
                通常分为 3-6 个阶段（如基础入门、核心进阶、实战演练等）。必须严格遵照诊断策略中的"跳过"或"补充"建议！
                只需输出 stages 列表，不要拆分具体节点。
                引用检索资料时必须标明出处，不得编造检索资料未支持的事实。"""
            )
            human_msg = HumanMessage(content=f"{request_context}{search_context}\n\n诊断策略:\n{state['strategy_report']}")

            result = await self.llm.ainvoke_json(MacroStages, [sys_msg, human_msg])
            logger.info(f"LangGraph [Curriculum Architect] finished with {len(result.stages)} stages.")
            return {"macro_stages": result.stages}

        async def node_strategist_node(state: PathState) -> dict:
            logger.info("LangGraph [Node Strategist] starting...")
            stages_json = json.dumps([s.model_dump() for s in state["macro_stages"]], ensure_ascii=False, indent=2)
            request_context = format_path_request_context(state["request"])
            search_context = format_evidence_for_prompt(state.get("search_evidence", []))
            sys_msg = SystemMessage(content=NODE_STRATEGIST_SYSTEM_PROMPT)
            human_msg = HumanMessage(content=f"{request_context}{search_context}\n\n诊断策略:\n{state['strategy_report']}\n\n宏观阶段骨架:\n{stages_json}")

            result = await self.llm.ainvoke_json(AgentCoursePathPlan, [sys_msg, human_msg])
            result.strategy_report = state["strategy_report"]
            logger.info(f"LangGraph [Node Strategist] finished with {len(result.nodes)} nodes.")
            return {"final_plan": result}

        workflow.add_node("research", research_node)
        workflow.add_node("analyst", profile_analyst_node)
        workflow.add_node("architect", curriculum_architect_node)
        workflow.add_node("strategist", node_strategist_node)

        workflow.add_edge(START, "research")
        workflow.add_edge("research", "analyst")
        workflow.add_edge("analyst", "architect")
        workflow.add_edge("architect", "strategist")
        workflow.add_edge("strategist", END)

        return workflow.compile()

    def _build_adjust_graph(self):
        workflow = StateGraph(AdjustState)

        async def feedback_analyst_node(state: AdjustState) -> dict:
            logger.info("LangGraph [Feedback Analyst] starting...")
            profile_json = json.dumps(state["profile"], ensure_ascii=False, indent=2)
            weak_points_text = "、".join(state["weak_points"]) if state["weak_points"] else "无明确薄弱点"
            sys_msg = SystemMessage(content="""你是一个世界顶级的学习反馈诊断师。
你的任务是根据用户当前的学习进展、画像以及最新的反馈/测试成绩，诊断后续课程存在的问题，并给出微调策略。
明确指出：哪些待学内容需要删减，哪些待学内容需要增加实操或降低难度。""")
            human_msg = HumanMessage(
                content=(
                    f"当前课程: {state['active_path'].title}\n"
                    f"用户反馈: {state['feedback']}\n"
                    f"薄弱知识点: {weak_points_text}\n"
                    f"关联资源上下文:\n{state['resource_context'] or '无'}\n\n"
                    f"画像:\n{profile_json}"
                )
            )

            result = await self.llm.ainvoke_json(StrategyReport, [sys_msg, human_msg])
            logger.info("LangGraph [Feedback Analyst] finished.")
            return {"diagnosis_report": result.strategy_report}

        async def node_replanner_node(state: AdjustState) -> dict:
            logger.info("LangGraph [Node Replanner] starting...")
            completed_data = [
                {
                    "node_id": n.node_id,
                    "stage_id": n.stage_id,
                    "title": n.title,
                }
                for n in state["completed_nodes"]
            ]
            remaining_data = [
                {
                    "node_id": n.node_id,
                    "stage_id": n.stage_id,
                    "title": n.title,
                    "prerequisites": n.prerequisites or [],
                }
                for n in state["remaining_nodes"]
            ]
            completed_json = json.dumps(completed_data, ensure_ascii=False, indent=2)
            remaining_json = json.dumps(remaining_data, ensure_ascii=False, indent=2)

            sys_msg = SystemMessage(content="""你是一个路径重构专家。
请根据反馈诊断师的策略报告，重构剩余的路径节点。
规范：
1. 必须原样保留所有已完成的节点（保持其 node_id, stage_id, title 不变）。
2. 对后续未完成节点进行精细化调整增删改，必须在 adjustment_rationale 中说明。
3. 返回全新的阶段与所有节点结构。""")
            human_msg = HumanMessage(content=f"诊断策略:\n{state['diagnosis_report']}\n\n已完成节点(需保留):\n{completed_json}\n\n原定剩余节点(可调整):\n{remaining_json}")

            result = await self.llm.ainvoke_json(AgentCoursePathPlan, [sys_msg, human_msg])
            result.strategy_report = state["diagnosis_report"]
            logger.info("LangGraph [Node Replanner] finished.")
            return {"final_plan": result}

        workflow.add_node("feedback_analyst", feedback_analyst_node)
        workflow.add_node("replanner", node_replanner_node)
        workflow.add_edge(START, "feedback_analyst")
        workflow.add_edge("feedback_analyst", "replanner")
        workflow.add_edge("replanner", END)
        return workflow.compile()

    async def generate_plan(
        self,
        request: GeneratePathRequest,
        profile: dict[str, Any],
    ) -> tuple[AgentCoursePathPlan, list[dict[str, Any]]]:
        """执行多智能体路径规划 (LangGraph版)。

        Returns:
            (plan, search_evidence_records) — 规划结果和结构化搜索证据列表。
        """
        logger.info(f"PathPlannerAgent (LangGraph) 开始规划路径 - Topic: {request.topic}")
        try:
            initial_state = {
                "request": request,
                "profile": profile,
                "search_evidence": [],
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

    async def adjust_plan(
        self,
        active_path: Any,
        completed_nodes: list[Any],
        remaining_nodes: list[Any],
        profile: dict[str, Any],
        feedback: str,
        weak_points: list[str] | None = None,
        resource_context: str = "",
    ) -> AgentCoursePathPlan:
        """根据画像和反馈动态微调未完成的路径节点 (LangGraph版)。"""
        logger.info(f"PathPlannerAgent (LangGraph) 开始微调路径 - Path ID: {active_path.id}")
        try:
            initial_state = {
                "active_path": active_path,
                "completed_nodes": completed_nodes,
                "remaining_nodes": remaining_nodes,
                "profile": profile,
                "feedback": feedback,
                "weak_points": weak_points or [],
                "resource_context": resource_context,
                "diagnosis_report": "",
                "final_plan": None
            }
            final_state = await self.adjust_graph.ainvoke(initial_state)
            return final_state["final_plan"]
        except Exception as e:
            logger.error(f"PathPlannerAgent 路径微调失败: {str(e)}")
            raise e

    async def _collect_search_evidence(
        self,
        request: GeneratePathRequest,
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
        all_records: list[dict[str, Any]] = []
        for tool_call in tool_calls:
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

            all_records.extend(records)

        total_chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in all_records)
        if total_chars > self.max_search_evidence_chars:
            all_records = _truncate_evidence_records(all_records, self.max_search_evidence_chars)

        return all_records

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

NODE_STRATEGIST_SYSTEM_PROMPT = """你是一个世界顶级的课程节点规划师。
你的任务是将架构师给出的宏观阶段骨架（stages），拆解为具体的拓扑节点（nodes）。
1. 请提供一个精心设计的宏观课程标题。
2. adjustment_rationale 必须是字符串数组，每项写出一条基于画像或学习输入的调整依据。
3. confidence 必须是 0-100 的整数百分比。
4. 必须原样包含前面规划好的 stages。
5. 必须为所有阶段生成具体学习节点（nodes），不能只生成第一个阶段。
6. 每个节点应该是一个不可再分的最小知识点或能力点，明确指出前置依赖（prerequisites），形成无环拓扑结构。
7. 每个节点必须包含 resource_policy，指定该节点推荐生成的资源类型和策略：
   - primary_resource_type: 主要资源类型（只能是 content/quiz/code/reading/ppt/mindmap）
   - required_resource_types: 必须生成的资源类型列表（只能是上述六种之一）
   - optional_resource_types: 可选增强资源类型列表
   - assessment_type: 掌握度评估方式（quiz/code/none）
   - generation_focus: 资源生成内容重点提示（如 ["概念解释", "基础练习"]）
   - personalization_reason: 为什么此策略适合该学习者
   - expected_resource_count: 预期生成资源数量（1-6）
8. 资源策略参考规则：
   - 基础概念节点：primary=content, required=[content, quiz], optional=[mindmap]
   - 结构关系节点：primary=content, required=[content, mindmap, quiz]
   - 算法/编程节点：primary=content, required=[content, code, quiz]
   - 拓展提升节点：primary=reading, required=[reading, quiz]
   - 阶段总结节点：primary=ppt, required=[ppt, quiz]
9. 每个节点必须填写 recommendation_reason，说明为什么推荐学习该节点。
10. 防幻觉与证据归属要求：
   - 引用检索资料时必须标明出处编号（如"基于[检索1]的结论"、"参考[检索2]的建议"）。
   - 不得编造检索资料未支持的事实，不得将不确定的搜索摘要写成确定结论。
   - adjustment_rationale 中应区分"基于画像"和"基于检索参考"的不同依据。
   - 如果某项规划没有检索证据支撑，应明确标注"基于画像/经验判断"而非虚构来源。"""


SEARCH_FAILURE_MARKERS = (
    "搜索不可用",
    "搜索失败",
    "未找到相关搜索结果",
    "无可用搜索结果",
    "所有搜索引擎调用均失败",
)

def format_path_request_context(request: GeneratePathRequest) -> str:
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


def build_search_research_messages(request: GeneratePathRequest, profile: dict[str, Any]) -> list[Any]:
    """Build messages that let the planner choose search tools."""
    profile_context = (
        json.dumps(profile, ensure_ascii=False, indent=2)
        if profile
        else "未提供"
    )
    return [
        SystemMessage(
            content=(
                "你是课程路径规划 Agent 的联网检索子步骤。你可以调用搜索工具补充外部参考，"
                "但最多只提出少量高价值检索。重点查证：前置知识、合理学习顺序、"
                "课程阶段、实践能力目标。不要生成最终学习路径。"
                "检索时优先选择权威来源（官方文档、教材、学术论文），"
                "避免引用广告、营销页面或不可靠的博客。"
                "每条检索结果必须能追溯到具体来源。"
            )
        ),
        HumanMessage(
            content=(
                f"{format_path_request_context(request)}\n\n"
                f"用户画像:\n{profile_context}\n\n"
                "请判断需要检索哪些资料，并调用合适的搜索工具。"
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
