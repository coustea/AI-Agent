"""LangGraph 图路由函数。

各条件边从节点输出状态路由到下一个节点。
这些函数作为 staticmethod 附加在 TutorAgent 上，但逻辑上独立于类实例。
"""

from __future__ import annotations

from langgraph.graph import END

from app.chat.agent.state import TutorAgentState


def route_after_classify(state: TutorAgentState) -> str:
    cls = state.get("classification")
    if cls is None:
        return "answer_node"
    if cls.needs_file_analysis and state.get("attachments"):
        return "analysis_files"
    if cls.needs_knowledge_search or cls.needs_web_search or cls.needs_profile or cls.needs_long_term_memory or cls.needs_recent_evaluation:
        return "search_node"
    return "answer_node"


def route_after_analysis(state: TutorAgentState) -> str:
    cls = state.get("classification")
    if cls and (cls.needs_knowledge_search or cls.needs_web_search or cls.needs_profile or cls.needs_long_term_memory or cls.needs_recent_evaluation):
        return "search_node"
    return "answer_node"


def route_after_search(state: TutorAgentState) -> str:
    return "answer_node"


def route_after_answer(state: TutorAgentState) -> str:
    cls = state.get("classification")
    if cls and cls.needs_diagram:
        return "diagram_node"
    if state.get("need_teaching_diagram") and state.get("final_answer"):
        return "diagram_node"

    final_answer = state.get("final_answer", "")
    search_attempted = state.get("_search_attempted", False)
    enable_web_search = state.get("enable_web_search", False)

    if (not search_attempted
            and enable_web_search
            and final_answer
            and len(final_answer) < 30
            and not state.get("evidence", [])):
        return "search_node"

    return END