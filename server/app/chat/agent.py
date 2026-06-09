# -*- coding: utf-8 -*-
"""TutorAgent：基于上下文初始化的智能辅导编排器。

负责 LangGraph 图编排、路由条件控制、回答生成、图解生成以及前端 SSE 事件的流式分发。
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from app.chat.prompt_manager import chat_prompts
from app.chat.request import ChatHistoryMessage
from app.chat.schemas import TeachingDiagram, TutorAgentContext, TutorState
from app.infra.context import runtime_context as chat_runtime_context
from app.chat.runtime import prepare_tutor_state
from app.chat.utils import (
    build_messages,
    classify_route,
    extract_question,
    is_unusable_reply_text,
    node_timer,
    normalize_message_content,
    stream_event,
    truncate,
)
from app.chat.tools.search import duckduckgo_search, serp_search, spark_search, tavily_search
from app.chat.tools.knowledge import aformat_knowledge_context, search_knowledge_base
from app.config import LANGGRAPH_DEBUG
from app.infra.llm import get_llm
from app.infra.logging import get_logger

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# LangGraph 递归限制
GRAPH_RECURSION_LIMIT = 30

# 图节点名称集合
GRAPH_NODE_NAMES = {
    "classify",
    "answer_node",
    "search_node",
    "attachment_answer",
    "teaching_diagram_generate",
}

# 回答节点名称集合（会发送 token 事件，包含逻辑节点和内部标识）
ANSWER_NODE_NAMES = {"answer_node", "direct_answer", "spark_summary", "attachment_answer"}


def _graph_stream_kwargs(agent: "TutorAgent | None" = None) -> dict[str, Any]:
    """构建 LangGraph 流式参数。"""
    kwargs: dict[str, Any] = {
        "version": "v2",
        "config": {"recursion_limit": GRAPH_RECURSION_LIMIT},
    }
    if agent is not None:
        kwargs["config"]["configurable"] = {"agent": agent}
    if LANGGRAPH_DEBUG:
        kwargs["debug"] = True
    return kwargs


def _load_answer_policy_sections() -> dict[str, str]:
    """从 Prompts 注册中心读取并解析答复策略 Markdown 文件。"""
    return chat_prompts.answer_policy_sections()


def _answer_generation_policy(user_message: str) -> str:
    """选择提示词级别的回答深度，不施加输出截断。"""
    normalized = re.sub(r"\s+", "", (user_message or "").lower())
    is_learning_statement = bool(
        re.search(r"(?:我)?(?:最近|目前|现在|正在)?(?:在)?(?:学习|复习|了解|看)(?:一下)?", normalized)
    )
    asks_for_explanation = bool(
        re.search(r"(?:什么|为何|为什么|怎么|如何|解释|讲解|介绍|梳理|区别|对比|举例|详细|展开|请问|？|\?)", normalized)
    )

    sections = _load_answer_policy_sections()
    if is_learning_statement and not asks_for_explanation:
        return sections.get("陈述学习方向", "")
    if re.search(r"(?:详细|系统|深入|展开|完整|从头|全面|结合例题|结合代码)", normalized):
        return sections.get("深入讲解", "")
    return sections.get("默认深度", "")


def _scoped_answer_prompt(
    system_prompt: str,
    *,
    question: str,
    diagram_enabled: bool,
) -> str:
    """基于本轮实际读取的依据组织回答提示词。"""
    sections_dict = _load_answer_policy_sections()
    sections = [
        system_prompt,
        f"# 本轮答复深度\n{_answer_generation_policy(question)}",
        f"# 工具使用说明\n{sections_dict.get('工具使用说明', '')}",
    ]
    if diagram_enabled:
        sections.append(
            f"# 本轮图解输出已启用\n{sections_dict.get('图解输出已启用', '')}"
        )
    return "\n\n".join(sections)


def _stream_chunk_text(chunk: Any) -> str:
    """从 LangChain 流式块中提取纯文本。"""
    if chunk is None:
        return ""
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


async def stream_answer(
    agent: Any,
    messages: list[Any],
    *,
    node_name: str,
    config: RunnableConfig,
    runnable: Any = None,
) -> AIMessage:
    """流式调用 LLM 并逐 token 推送。失败直接抛出异常，不做重试。"""
    effective_runnable = runnable or agent.llm
    final_chunk = None

    kwargs = {"temperature": 0.3} if effective_runnable is agent.llm else {}
    async for chunk in effective_runnable.astream(
        messages,
        **kwargs,
    ):
        if final_chunk is None:
            final_chunk = chunk
        else:
            final_chunk += chunk

        text = _stream_chunk_text(chunk)
        if text:
            await adispatch_custom_event(
                "answer_token",
                {"node": node_name, "text": text},
                config=config,
            )

    if final_chunk is None:
        raise RuntimeError(f"[TutorAgent] {node_name} 流式调用未返回任何内容")

    return final_chunk


async def _run_tool_augmented_generation(
    agent: Any,
    *,
    messages: list[Any],
    tools: list[Any],
    node_name: str,
    config: RunnableConfig,
) -> dict[str, Any]:
    """绑定工具、执行工具调用，并生成最终回答。"""
    tools_by_name = {t.name: t for t in tools}

    if tools:
        try:
            llm_to_use = agent.llm.model.bind_tools(tools)
        except Exception:
            logger.warning("[TutorAgent] 模型不支持 bind_tools，降级为基础模型")
            llm_to_use = agent.llm
    else:
        llm_to_use = agent.llm

    full_messages = list(messages)
    knowledge_sources: list[dict[str, Any]] = []

    result = await stream_answer(
        agent,
        full_messages,
        node_name=node_name,
        config=config,
        runnable=llm_to_use,
    )

    if getattr(result, "tool_calls", []):
        full_messages.append(result)

        for tool_call in result.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_instance = tools_by_name.get(tool_name)

            logger.info("[TutorAgent] 执行工具: %s args=%s", tool_name, tool_args)
            if tool_instance:
                try:
                    tool_output = await tool_instance.ainvoke(tool_args)
                    if tool_name == "search_knowledge_base":
                        query = str(tool_args.get("query", "")).strip()
                        if query:
                            _context, kb_rows = await aformat_knowledge_context(query)
                            knowledge_sources = [
                                {
                                    "rank": item.get("rank"),
                                    "source": (item.get("metadata") or {}).get("source") or (item.get("metadata") or {}).get("book_title") or "未知来源",
                                    "file_name": (item.get("metadata") or {}).get("file_name") or "",
                                    "chunk_index": (item.get("metadata") or {}).get("chunk_index"),
                                    "distance": item.get("distance"),
                                    "retrieval_mode": item.get("retrieval_mode") or "",
                                }
                                for item in kb_rows
                            ]
                    full_messages.append(ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_call.get("id", ""),
                    ))
                except Exception as exc:
                    logger.warning("[TutorAgent] 工具执行失败 %s: %s", tool_name, exc)
                    full_messages.append(ToolMessage(
                        content=f"执行失败: {exc}",
                        tool_call_id=tool_call.get("id", ""),
                    ))
            else:
                full_messages.append(ToolMessage(
                    content=f"未知工具: {tool_name}",
                    tool_call_id=tool_call.get("id", ""),
                ))

        logger.info("[TutorAgent] 工具执行完毕，发起第二轮生成")
        result = await stream_answer(
            agent,
            full_messages,
            node_name=node_name,
            config=config,
            runnable=llm_to_use,
        )

    return {
        "messages": [result],
        "answer_text": result.content,
        "retrieved_profile_context": "",
        "retrieved_memory_context": "",
        "knowledge_sources": knowledge_sources,
        "termination_reason": f"{node_name}_done",
    }


async def collect_search_context(
    agent: Any,
    *,
    question: str,
    system_prompt: str,
    messages: list[Any],
    attachment_context: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    """联网搜索上下文收集。"""
    attachment_context_section = f"\n\n附件预分析上下文：\n{attachment_context}" if attachment_context else ""
    search_instruction = HumanMessage(
        content=chat_prompts.render_search_instruction(
            attachment_context_section=attachment_context_section
        )
    )
    full_messages = build_messages(system_prompt, list(messages) + [search_instruction])

    search_tools = [duckduckgo_search, tavily_search, serp_search, spark_search]
    tools_by_name = {tool_item.name: tool_item for tool_item in search_tools}
    llm_with_tools = agent.llm.model.bind_tools(search_tools)

    response = None
    try:
        response = await agent.llm.ainvoke(full_messages, model=llm_with_tools)
    except Exception as exc:
        logger.warning("[TutorAgent] 搜索意图生成失败，进入直接检索兜底 err=%s", exc)

    search_result = normalize_message_content(getattr(response, "content", "") if response else "")
    tool_calls = getattr(response, "tool_calls", []) if response else []
    tool_results = []

    async def invoke_search_tool(tool_call):
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("args", {})
        try:
            tool_instance = tools_by_name.get(tool_name)
            result = await tool_instance.ainvoke(tool_args) if tool_instance else ""
            if result:
                return f"【{tool_name}】\n{result}"
        except Exception as exc:
            logger.warning("[TutorAgent] 搜索工具 %s 失败: %s", tool_name, exc)
            return f"【{tool_name}】搜索失败"
        return ""

    if tool_calls:
        tasks = [invoke_search_tool(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks)
        for res in results:
            if res:
                tool_results.append(res)

    if not tool_results:
        logger.info("[TutorAgent] 搜索节点未触发工具调用或无结果，启动自动兜底搜索")
        tavily_result = ""
        try:
            tavily_result = await tavily_search.ainvoke({"query": question})
        except Exception as exc:
            logger.warning("[TutorAgent] 自动兜底 Tavily 搜索失败: %s", exc)

        if not tavily_result or "Tavily 搜索不可用" in tavily_result or "Tavily 搜索失败" in tavily_result:
            logger.info("[TutorAgent] Tavily 不可用或失败，使用 DuckDuckGo 搜索兜底")
            try:
                ddg_result = await duckduckgo_search.ainvoke({"query": question})
                if ddg_result and "DuckDuckGo 搜索失败" not in ddg_result:
                    tool_results.append(f"【duckduckgo_search (自动兜底)】\n{ddg_result}")
                else:
                    tool_results.append("【自动搜索兜底】无可用搜索结果。")
            except Exception as exc:
                logger.warning("[TutorAgent] 自动兜底 DuckDuckGo 搜索失败: %s", exc)
                tool_results.append("【自动搜索兜底】所有搜索引擎调用均失败。")
        else:
            tool_results.append(f"【tavily_search (自动兜底)】\n{tavily_result}")

    combined_parts = [part for part in [search_result, "\n\n".join(tool_results)] if part.strip()]
    return "\n\n".join(combined_parts), []


async def answer_node(agent: Any, state: TutorState, config: RunnableConfig) -> dict[str, Any]:
    """统一自适应回答节点。"""
    messages = list(state.get("messages") or [])
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    system_prompt = state.get("system_prompt", "")
    question = extract_question(messages)
    search_result = state.get("search_result", "")
    diagram_enabled = bool(state.get("need_teaching_diagram", False))

    from app.chat.tools.memory import make_memory_tools
    memory_tools = []
    if agent.context.memory_reader:
        memory_tools = make_memory_tools(agent.context.memory_reader)
    knowledge_tools = [search_knowledge_base]

    if search_result:
        node_name = "spark_summary"
        with node_timer("spark_summary", user=user_id, session=session_id):
            logger.debug("[TutorAgent] Spark 总结回答：question=%s", truncate(question, 180))
            prompt_content = chat_prompts.render_answer_policy_section(
                "搜索总结提示词",
                question=question,
                search_result=search_result,
            )
            scoped_prompt = _scoped_answer_prompt(
                system_prompt,
                question=question,
                diagram_enabled=diagram_enabled,
            )
            full_messages = [
                SystemMessage(content=scoped_prompt),
                HumanMessage(content=prompt_content),
            ]
            tools = memory_tools + knowledge_tools
    else:
        node_name = "direct_answer"
        with node_timer("direct_answer", user=user_id, session=session_id):
            logger.debug("[TutorAgent] 直接回答：question=%s", truncate(question, 180))
            scoped_prompt = _scoped_answer_prompt(
                system_prompt,
                question=question,
                diagram_enabled=diagram_enabled,
            )
            full_messages = build_messages(scoped_prompt, list(messages))
            tools = memory_tools + knowledge_tools

    result = await _run_tool_augmented_generation(
        agent=agent,
        messages=full_messages,
        tools=tools,
        node_name=node_name,
        config=config,
    )
    return result


async def attachment_answer_node(
    agent: Any,
    state: TutorState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """附件回答节点：基于附件预分析和可选搜索结果生成教学回答。"""
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    attachments = state.get("attachments") or []
    messages = list(state.get("messages") or [])
    question = extract_question(messages)
    pre_analysis = state.get("attachment_analysis") or {}
    system_prompt = state.get("system_prompt", "")

    with node_timer(
        "attachment_answer",
        user=user_id,
        session=session_id,
        attachment_count=len(attachments),
    ):
        logger.info(
            "[TutorAgent] 附件回答 route=attachment_answer question=%s attachments=%s",
            truncate(question, 180),
            len(attachments),
        )

        full_context = str(state.get("attachment_analysis_context", "")).strip()
        if not full_context and isinstance(pre_analysis, dict):
            full_context = str(pre_analysis.get("analysis_context", "")).strip()

        if not full_context:
            full_context = (
                "附件内容暂时无法解析，请尝试重新上传。\n"
                "建议使用清晰的图片或标准格式的文档文件。"
            )

        search_context = ""
        enable_web_search = bool(state.get("enable_web_search", False))
        if enable_web_search:
            search_context, _knowledge_sources = await collect_search_context(
                agent=agent,
                question=question,
                system_prompt=system_prompt,
                messages=messages,
                attachment_context=full_context,
            )

        answer_prompt = f"""用户问题: {question}

附件预分析内容:
{full_context}

"""
        if search_context:
            answer_prompt += f"""本地和网络检索到的补充参考资料:
{search_context}

"""
        answer_prompt += (
            "请结合上述附件预分析内容和补充参考资料，完整回答用户的提问。\n"
            "语言自然、清晰、有教学价值。不要在回答中提及检索或解析的具体过程。\n"
            "直接面向学生进行耐心讲解。"
        )

        scoped_prompt = _scoped_answer_prompt(
            system_prompt,
            question=question,
            diagram_enabled=bool(state.get("need_teaching_diagram", False)),
        )
        full_messages = build_messages(scoped_prompt, [HumanMessage(content=answer_prompt)])

        from app.chat.tools.memory import make_memory_tools
        memory_tools = []
        if agent.context.memory_reader:
            memory_tools = make_memory_tools(agent.context.memory_reader)

        knowledge_tools = [search_knowledge_base]
        tools = memory_tools + knowledge_tools

        return await _run_tool_augmented_generation(
            agent=agent,
            messages=full_messages,
            tools=tools,
            node_name="attachment_answer",
            config=config,
        )


def explicit_diagram_requested(user_message: str) -> bool:
    """仅在用户本轮显式请求时才激活图解图板。"""
    normalized = re.sub(r"\s+", "", (user_message or "").lower())
    if not normalized:
        return False
    if re.search(r"(?:不要|不需要|无需|别|取消|关闭).{0,8}(?:图解|画图|流程图|示意图|结构图|可视化)", normalized):
        return False
    patterns = (
        r"图解(?:说明|解释|展示|一下)?",
        r"(?:请|帮我|能否|可以)?(?:用|通过)(?:一张|一个)?(?:图|图解|图示)(?:说明|解释|展示|梳理|讲解)?",
        r"(?:请|帮我|能否|可以)?(?:用图|画图|画一下)(?:说明|解释|展示|梳理|讲解)?",
        r"(?:画|生成|提供|做|来)(?:一张|一个)?(?:流程图|示意图|结构图|时序图|图解|图示)",
        r"(?:把|将).{1,24}(?:画|整理|转成|做成)(?:一张|一个)?(?:图|图解|流程图|示意图)",
        r"(?:图示|视觉化)(?:说明|解释|展示|呈现|讲解)?",
        r"(?:可视化)(?:说明|解释|展示|呈现)",
        r"(?:diagram|visuali[sz]e|visualization)",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def diagram_only_requested(user_message: str) -> bool:
    """检测依赖上一轮教学回答的纯图解指令。"""
    normalized = re.sub(r"[\s，。！？!?、：:；;]", "", (user_message or "").lower())
    if not normalized:
        return False
    patterns = (
        r"(?:我想|我要|请|帮我|给我|能否|可以|麻烦)?(?:生成|制作|做|画|展示|提供|来)?(?:一张|一个)?(?:教学)?图解(?:说明)?(?:一下|看看)?",
        r"(?:我想|我要|请|帮我|给我|能否|可以|麻烦)?(?:生成|制作|做|画|展示|提供|来)?(?:一张|一个)?(?:流程图|示意图|结构图|时序图)(?:一下|看看)?",
    )
    return any(re.fullmatch(pattern, normalized) for pattern in patterns)


def previous_teaching_exchange(messages: list[Any]) -> tuple[str, str]:
    """返回本轮之前的用户问题和助教讲解。"""
    latest_user_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if isinstance(messages[index], HumanMessage)),
        -1,
    )
    if latest_user_index <= 0:
        return "", ""

    for answer_index in range(latest_user_index - 1, -1, -1):
        message = messages[answer_index]
        if not isinstance(message, AIMessage):
            continue
        answer = normalize_message_content(message.content).strip()
        if not answer:
            continue
        prior_question = extract_question(messages[:answer_index])
        if diagram_only_requested(prior_question):
            continue
        return prior_question, answer
    return "", ""


async def teaching_diagram_generate_node(agent: Any, state: TutorState) -> TutorState:
    """基于本轮回答或上一轮教学对话生成教学图板。"""
    if not state.get("need_teaching_diagram", False):
        return state
    user_id = int(state.get("user_id") or 0)
    session_id = str(state.get("session_id") or "")
    logger.info("[Diagram] 开始生成教学图解: user_id=%s session_id=%s", user_id, session_id)
    with node_timer("teaching_diagram_generate", user=user_id, session=session_id):
        try:
            question = extract_question(state.get("messages") or [])
            answer = normalize_message_content(state.get("answer_text", "")).strip()
            if diagram_only_requested(question):
                question, answer = previous_teaching_exchange(list(state.get("messages") or []))
                state["termination_reason"] = "teaching_diagram_only_done"
            if not question or not answer:
                state["teaching_diagram"] = None
                state["teaching_diagram_error"] = "缺少问题或文字回答，跳过图解说明生成"
                return state

            diagram = await generate_teaching_diagram(
                agent=agent,
                question=question,
                answer=answer,
                state=state,
            )
            state["teaching_diagram"] = diagram.model_dump(mode="json")
            state["diagram_type"] = diagram.graph_type
            state["teaching_diagram_error"] = None
            logger.info("[Diagram] 图解生成完成: user_id=%s type=%s", user_id, diagram.graph_type)
            return state
        except Exception as exc:
            logger.exception("[Diagram] 教学图解节点失败: user_id=%s", user_id)
            state["teaching_diagram"] = None
            state["teaching_diagram_error"] = str(exc)
            return state


async def generate_teaching_diagram(
    agent: Any,
    *,
    question: str,
    answer: str,
    state: TutorState,
) -> TeachingDiagram:
    """使用注入的上下文生成经过验证的面向学习者的图板。"""
    profile_context = str(state.get("retrieved_profile_context", "")).strip()
    long_term_memory_context = str(state.get("retrieved_memory_context", "")).strip()
    session_summary_context = str(state.get("session_summary_context", "")).strip()
    attachment_context = str(state.get("attachment_analysis_context", "")).strip()
    context_parts = []
    if profile_context:
        context_parts.append(f"本轮按需读取的用户画像：\n{profile_context}")
    if long_term_memory_context:
        context_parts.append(f"本轮按需检索的长期学习依据：\n{long_term_memory_context}")
    if session_summary_context:
        context_parts.append(f"会话摘要上下文：\n{session_summary_context}")
    if attachment_context:
        context_parts.append(f"附件预分析上下文：\n{attachment_context}")
    preferred = state.get("diagram_type") or "由你选择最适合的类型"

    prompt = (
        f"学生问题：\n{question}\n\n"
        f"最终回答：\n{answer}\n\n"
        f"上下文：\n{chr(10).join(context_parts) if context_parts else '无额外上下文。'}\n\n"
        f"偏好图板类型：{preferred}\n\n"
        "请生成一张能辅助学生理解答案的教学图解 JSON。"
    )
    return await agent.llm.ainvoke_json(
        TeachingDiagram,
        [SystemMessage(content=chat_prompts.teaching_diagram_system()), HumanMessage(content=prompt)],
        temperature=0.1,
    )


class TutorAgent:
    """智能辅导 Agent — 状态图与 SSE 编排层。

    四大对话路径：
    1. classify -> answer_node -> diagram(可选)
    2. classify -> search_node -> answer_node -> diagram(可选)
    3. classify -> attachment_answer -> diagram(可选)
    4. classify -> teaching_diagram_generate (纯图解生成模式)
    """

    _compiled_graph: Any | None = None
    _compile_lock = asyncio.Lock()

    def __init__(self, context: TutorAgentContext) -> None:
        """初始化 TutorAgent。"""
        self.context = context
        self.llm = get_llm()
        self.graph = TutorAgent._compiled_graph

        logger.info("[TutorAgent] 初始化完成")

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------

    async def _ensure_graph(self) -> None:
        """构建 LangGraph 状态图。"""
        if TutorAgent._compiled_graph is not None:
            self.graph = TutorAgent._compiled_graph
            return

        # 使用异步锁保证 LangGraph 状态图只被编译和初始化一次
        async with TutorAgent._compile_lock:
            if TutorAgent._compiled_graph is not None:
                self.graph = TutorAgent._compiled_graph
                return

            graph = StateGraph(TutorState)
            
            # 添加节点
            graph.add_node("classify", _graph_classify_node)
            graph.add_node("answer_node", _graph_answer_node)
            graph.add_node("search_node", _graph_search_node)
            graph.add_node("attachment_answer", _graph_attachment_answer_node)
            graph.add_node("teaching_diagram_generate", _graph_teaching_diagram_generate_node)

            # 添加边
            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "answer_node",
                    "diagram_only": "teaching_diagram_generate",
                    "search": "search_node",
                    "attachment_needed": "attachment_answer",
                },
            )
            graph.add_conditional_edges(
                "answer_node",
                self._route_after_answer,
                {
                    "diagram": "teaching_diagram_generate",
                    "end": END,
                },
            )
            graph.add_edge("search_node", "answer_node")
            graph.add_conditional_edges(
                "attachment_answer",
                self._route_after_answer,
                {
                    "diagram": "teaching_diagram_generate",
                    "end": END,
                },
            )
            graph.add_edge("teaching_diagram_generate", END)

            TutorAgent._compiled_graph = graph.compile()
            self.graph = TutorAgent._compiled_graph

    # ------------------------------------------------------------------
    # 条件路由
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_answer(state: dict) -> str:
        """在文字回答完成后运行可选的图解生成。"""
        return "diagram" if state.get("need_teaching_diagram", False) else "end"

    # ------------------------------------------------------------------
    # 节点实现 (状态机节点包装)
    # ------------------------------------------------------------------

    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：决定意图路由与执行模式。

        知识库检索作为 Agent Tool 常驻提供，不再由前端开关控制。
        """
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        attachments = state.get("attachments") or []
        enable_web_search = bool(state.get("enable_web_search", False))
        need_teaching_diagram = bool(state.get("need_teaching_diagram", False))
        user_message = extract_question(messages)

        has_attachments = bool(attachments)

        with node_timer("classify", user=user_id, session=session_id):
            # 判断是否需要请求画图
            need_diagram = need_teaching_diagram or explicit_diagram_requested(user_message)

            state_updates: dict[str, Any] = {}
            if need_diagram != need_teaching_diagram:
                state_updates["need_teaching_diagram"] = need_diagram

            # 根据附件情况、搜索开关以及是否只要画图，决定路由去向
            # 知识库检索改为 Tool 方式，不作为独立路由
            if has_attachments:
                if enable_web_search:
                    execution_mode = "attachment_search"
                else:
                    execution_mode = "attachment"
                route = "attachment_needed"
            elif enable_web_search:
                route = "search"
                execution_mode = "search"
            elif need_diagram and diagram_only_requested(user_message):
                _, prior_answer = previous_teaching_exchange(list(messages))
                if prior_answer:
                    route = "diagram_only"
                    execution_mode = "diagram_only"
                else:
                    need_diagram = False
                    route = "direct"
                    execution_mode = "direct"
                    state_updates["need_teaching_diagram"] = False
            else:
                route = "direct"
                execution_mode = "direct"

            logger.debug(
                "[TutorAgent] 路由分类 route=%s execution_mode=%s need_diagram=%s web_search=%s knowledge=%s question=%s",
                route,
                execution_mode,
                need_diagram,
                enable_web_search,
                truncate(user_message, 120),
            )

            state_updates.update({
                "route": route,
                "execution_mode": execution_mode,
            })

            return state_updates

    async def _answer_node(self, state: TutorState, config: RunnableConfig) -> dict[str, Any]:
        """统一回答节点 (合并直接回答与检索总结)。"""
        return await answer_node(self, state, config)

    async def _search_node(self, state: TutorState) -> dict[str, Any]:
        """搜索节点：委托 collect_search_context 获取参考资料。"""
        messages = state.get("messages") or []
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        system_prompt = state.get("system_prompt", "")
        question = extract_question(messages)
        attachment_context = str(state.get("attachment_analysis_context", "")).strip()

        with node_timer("search_node", user=user_id, session=session_id):
            logger.info("[TutorAgent] 联网搜索节点 question=%s", truncate(question, 180))

            search_result, knowledge_sources = await collect_search_context(
                agent=self,
                question=question,
                system_prompt=system_prompt,
                messages=messages,
                attachment_context=attachment_context,
            )

            logger.debug("[TutorAgent] search_node 完成 preview=%s", truncate(search_result, 220))

            return {
                "search_result": search_result,
                "knowledge_sources": knowledge_sources,
                "termination_reason": "search_done",
            }

    async def _attachment_answer_node(self, state: TutorState, config: RunnableConfig) -> dict[str, Any]:
        """附件回答节点。"""
        return await attachment_answer_node(self, state, config)

    async def _teaching_diagram_generate_node(self, state: TutorState) -> TutorState:
        """教学图解生成节点。"""
        return await teaching_diagram_generate_node(self, state)

    # ------------------------------------------------------------------
    # 主入口：SSE 流式对话
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        history: list[ChatHistoryMessage],
    ):
        """流式生成对话响应。"""
        context = self.context
        current_message = ""
        for item in reversed(history):
            if item.role == "user" and item.content.strip():
                current_message = item.content.strip()
                break

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments=%s web_search=%s knowledge=%s",
            truncate(current_message, 180),
            len(context.attachments),
            context.enable_web_search,
        )

        await self._ensure_graph()

        # 将前端传入的历史消息与 Agent 初始化 Context 合并，生成 LangGraph 初始状态
        initial_state = prepare_tutor_state(context, history)
        initial_msg_count = len(initial_state.get("messages", []))

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""
        started_at = time.monotonic()
        first_token_ms: int | None = None

        try:
            with chat_runtime_context(context.user_id, context.session_id):
                # 监听 LangGraph 运行过程中发出的各类事件，并转换为 SSE 数据流给前端
                async for event in self.graph.astream_events(initial_state, **_graph_stream_kwargs(self)):
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    # 节点开始事件：给前端发送状态更新信息，展示“正在思考...”等提示语
                    if kind == "on_chain_start" and name in GRAPH_NODE_NAMES:
                        active_node = name
                        if name == "classify":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在判断最合适的答疑方式..."},
                            )
                        elif name == "search_node":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在联网搜索与问题相关的资料..."},
                            )
                        elif name == "answer_node":
                            # 自适应子节点状态消息
                            is_search = bool(runtime_state.get("search_result"))
                            stage_name = "spark_summary" if is_search else "direct_answer"
                            message = "正在结合检索资料组织回答..." if is_search else "正在组织回答..."
                            yield stream_event(
                                "status",
                                {"stage": stage_name, "message": message},
                            )
                        elif name == "attachment_answer":
                            yield stream_event(
                                "status",
                                {"stage": name, "message": "正在结合附件内容组织回答..."},
                            )
                        elif name == "teaching_diagram_generate":
                            yield stream_event(
                                "status",
                                {
                                    "stage": name,
                                    "message": "正在生成图解说明...",
                                },
                            )

                    # 节点结束事件
                    if kind == "on_chain_end" and name in GRAPH_NODE_NAMES:
                        active_node = ""
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            for key, value in node_output.items():
                                if key == "messages" and isinstance(value, list):
                                    runtime_state[key] = list(runtime_state.get(key, [])) + value
                                else:
                                    runtime_state[key] = value

                    # 自定义 answer_token 事件处理：接收大模型流式生成的每一个 Token，透传给前端做到打字机效果
                    if kind == "on_custom_event" and name == "answer_token":
                        payload = event.get("data", {})
                        node_name = payload.get("node") if isinstance(payload, dict) else active_node
                        chunk_text = payload.get("text", "") if isinstance(payload, dict) else ""
                        if node_name in ANSWER_NODE_NAMES and chunk_text:
                            if first_token_ms is None:
                                first_token_ms = int((time.monotonic() - started_at) * 1000)
                                logger.info("[TutorAgent] 首个 token 已发送 first_token_ms=%s", first_token_ms)
                            full_reply += chunk_text
                            yield stream_event("token", chunk_text)

                    if kind == "on_custom_event" and name == "learner_context_status":
                        payload = event.get("data", {})
                        if isinstance(payload, dict):
                            yield stream_event("status", payload)

                    # 兼容未产生流式 chunk 的兜底逻辑
                    if kind == "on_chain_end" and name in ANSWER_NODE_NAMES and not full_reply:
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            final_messages = node_output.get("messages")
                            if isinstance(final_messages, list):
                                final_ai = next(
                                    (msg for msg in reversed(final_messages) if isinstance(msg, AIMessage)),
                                    None,
                                )
                                final_text = normalize_message_content(final_ai.content if final_ai else "")
                                if final_text:
                                    if first_token_ms is None:
                                        first_token_ms = int((time.monotonic() - started_at) * 1000)
                                        logger.info("[TutorAgent] 首个 token 已发送 first_token_ms=%s", first_token_ms)
                                    full_reply = final_text
                                    yield stream_event("token", final_text)

        except Exception as exc:
            logger.exception("[TutorAgent] 请求异常")
            graph_error_text = f"服务器出错: {exc}"

        logger.info(
            "[TutorAgent] 请求结束 termination_reason=%s first_token_ms=%s total_ms=%s",
            runtime_state.get("termination_reason", ""),
            first_token_ms,
            int((time.monotonic() - started_at) * 1000),
        )

        if graph_error_text:
            yield stream_event("error", graph_error_text)
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        if not full_reply and runtime_state.get("execution_mode") != "diagram_only":
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

        teaching_diagram = runtime_state.get("teaching_diagram")
        knowledge_sources = runtime_state.get("knowledge_sources")

        # 从大模型生成的所有新消息中提取并聚合本轮产生的 Tool Calls 和 Token 消耗数据
        tool_calls = []
        usage_metadata = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        has_usage = False
        messages_list = runtime_state.get("messages", [])
        if isinstance(messages_list, list) and len(messages_list) > initial_msg_count:
            for msg in messages_list[initial_msg_count:]:
                if isinstance(msg, AIMessage):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_calls.extend(msg.tool_calls)
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        has_usage = True
                        usage_metadata["input_tokens"] += msg.usage_metadata.get("input_tokens", 0)
                        usage_metadata["output_tokens"] += msg.usage_metadata.get("output_tokens", 0)
                        usage_metadata["total_tokens"] += msg.usage_metadata.get("total_tokens", 0)
        
        final_usage_metadata = usage_metadata if has_usage else None

        # 打印关键单行日志，方便观察本轮会话的工具调用和 Token 消耗情况
        logger.info(
            "[TutorAgent] 会话 %s 回答生成完毕 | 提取到 ToolCalls: %d 个 | Token使用量: %s",
            context.session_id,
            len(tool_calls),
            final_usage_metadata,
        )

        if not isinstance(teaching_diagram, dict) and is_unusable_reply_text(full_reply) and not tool_calls:
            yield stream_event("error", "模型未返回有效内容，请重试。")
            yield stream_event("done", {"session_id": context.session_id, "error": True})
            return

        if isinstance(teaching_diagram, dict):
            yield stream_event("diagram", teaching_diagram)

        # 最后一并发出 done 事件，将完整的响应和工具消耗元数据传给 service 层落库
        yield stream_event(
            "done",
            {
                "session_id": context.session_id,
                "full_response": full_reply,
                "knowledge_sources": knowledge_sources or [],
                "resource_mode": "none",
                "resource": None,
                "teaching_diagram": teaching_diagram,
                "resources": {"teaching_diagram": teaching_diagram, "video": None},
                "tool_calls": tool_calls,
                "usage_metadata": final_usage_metadata,
            },
        )


def _agent_from_config(config: RunnableConfig) -> TutorAgent:
    configurable = (config or {}).get("configurable", {})
    agent = configurable.get("agent") if isinstance(configurable, dict) else None
    if not isinstance(agent, TutorAgent):
        raise RuntimeError("[TutorAgent] LangGraph config 缺少当前 agent 实例")
    return agent


async def _graph_classify_node(state: TutorState, config: RunnableConfig) -> dict[str, Any]:
    return await _agent_from_config(config)._classify_node(state)


async def _graph_answer_node(state: TutorState, config: RunnableConfig) -> dict[str, Any]:
    return await _agent_from_config(config)._answer_node(state, config)


async def _graph_search_node(state: TutorState, config: RunnableConfig) -> dict[str, Any]:
    return await _agent_from_config(config)._search_node(state)


async def _graph_attachment_answer_node(state: TutorState, config: RunnableConfig) -> dict[str, Any]:
    return await _agent_from_config(config)._attachment_answer_node(state, config)


async def _graph_teaching_diagram_generate_node(state: TutorState, config: RunnableConfig) -> TutorState:
    return await _agent_from_config(config)._teaching_diagram_generate_node(state)
