import os
from typing import TypedDict, Annotated, List, Any, AsyncGenerator
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from app.modules.tutor.agent import TutorAgent
from app.modules.profile_builder.profile_agent import profile_agent

class TutorState(TypedDict):
    messages: Annotated[List[BaseMessage], "对话历史记录（含多模态ImageMessage）"]
    user_id: int
    session_id: str
    current_profile: dict         # 当前8维度画像
    retrieved_context: List[Any]  # RAG 检索到的课件/知识片段
    requires_profile_update: bool # 标记位

# 初始化核心 Agent
tutor_agent = TutorAgent()

async def retrieve_node(state: TutorState) -> dict:
    """检索 CS 知识库的节点"""
    last_message = state["messages"][-1].content
    # 在这里可以从 last_message 中提取纯文本部分进行检索
    query_text = last_message if isinstance(last_message, str) else str(last_message)
    context = await tutor_agent.retrieve_knowledge(query_text)
    return {"retrieved_context": context}

async def tutor_node(state: TutorState) -> dict:
    """导师生成回复并流式输出的节点（这里由于需要 streaming，实际上会在 API 层调用 agent 产生流，
       这里的 node 主要用于 Graph 状态的流转和记录）"""
    # 实际上由于流式输出，我们会直接在 API 层用 astream 跑 LLM，
    # 但为了配合 Graph，这里可以是一个非流式的占位，或者直接让 Graph 返回状态，API 自行处理。
    pass
    # 注意：在真实的 FastAPI 生产环境中，通常直接在 agent 里做 stream，Graph 更适合跑后台 pipeline。
    # 为了满足计划，我们将 Tutor 的核心对话能力实现在 TutorAgent 中。
    return {"requires_profile_update": True}

async def profile_trigger_node(state: TutorState) -> dict:
    """异步触发画像更新"""
    if state.get("requires_profile_update"):
        # 触发后台画像合并任务
        # 这应该是一个后台任务，这里直接调用 async 方法
        await profile_agent.build_profile(state["user_id"])
    return {}

def build_tutor_graph():
    workflow = StateGraph(TutorState)
    
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("tutor", tutor_node)
    workflow.add_node("profile_trigger", profile_trigger_node)
    
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "tutor")
    workflow.add_edge("tutor", "profile_trigger")
    workflow.add_edge("profile_trigger", END)
    
    return workflow.compile()

tutor_graph = build_tutor_graph()
