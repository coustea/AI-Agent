# -*- coding: utf-8 -*-
"""统一回答生成与处理模块。

提供自适应的统一回答节点（直接回答与搜索后回答的合并形式）、带有最大轮次与超时保护的工具增强生成循环、
附件回答节点，以及从 answer_policy.md 加载提示策略的解析逻辑。
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.chat.schemas import TutorState
from app.chat.utils import (
    build_messages,
    extract_question,
    node_timer,
    normalize_message_content,
    truncate,
)
from app.chat.tools.search import duckduckgo_search, serp_search, tavily_search, spark_search
from app.chat.tools.knowledge import search_knowledge_base, format_knowledge_context
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 工具调用循环控制常量
MAX_TOOL_CALL_ROUNDS = 5
TOOL_LOOP_TIMEOUT_SECONDS = 60


def parse_markdown_sections(text: str) -> dict[str, str]:
    """解析 Markdown 文件中的各个章节，以一级标题（#）分割。"""
    sections = {}
    current_header = None
    current_lines = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_header:
                sections[current_header] = "\n".join(current_lines).strip()
            current_header = line.lstrip("#").strip()
            current_lines = []
        elif current_header is not None:
            current_lines.append(line)
    if current_header:
        sections[current_header] = "\n".join(current_lines).strip()
    return sections


def _load_answer_policy_sections() -> dict[str, str]:
    """从 Prompts 注册中心读取并解析答复策略 Markdown 文件。"""
    from app.prompts import registry
    content = registry.get("chat/answer_policy")
    return parse_markdown_sections(content)


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
        f"# 工具使用说明\n{sections_dict.get('工具使用说明', '')}"
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


async def stream_answer_with_retry(
    agent: Any,
    messages: list[Any],
    *,
    node_name: str,
    config: RunnableConfig,
    runnable: Any = None,
    fallback_text: str = "抱歉，我暂时无法回答这个问题，请稍后重试。",
    retry_prompt: str = "请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。",
) -> AIMessage:
    """流式输出文本块；仅在尚未输出可见内容时重试。"""
    has_visible_output = False
    effective_runnable = runnable or agent.llm

    async def generate(input_messages: list[Any]) -> AIMessage | None:
        nonlocal has_visible_output
        final_chunk = None
        try:
            kwargs = {"temperature": 0.3} if effective_runnable is agent.llm else {}
            async for chunk in effective_runnable.astream(
                input_messages,
                **kwargs,
            ):
                if final_chunk is None:
                    final_chunk = chunk
                else:
                    final_chunk += chunk
                    
                text = _stream_chunk_text(chunk)
                if text:
                    has_visible_output = True
                    await adispatch_custom_event(
                        "answer_token",
                        {"node": node_name, "text": text},
                        config=config,
                    )
            return final_chunk
        except Exception as exc:
            logger.warning("[TutorAgent] %s 流式调用失败 err=%s", node_name, exc)
            if has_visible_output:
                raise
        return None

    result = await generate(messages)
    if result and (result.content or getattr(result, "tool_calls", [])):
        return result

    logger.warning("[TutorAgent] %s 重试 原因=未产生可见流式内容", node_name)
    result = await generate(messages + [HumanMessage(content=retry_prompt)])
    if result and (result.content or getattr(result, "tool_calls", [])):
        return result

    await adispatch_custom_event(
        "answer_token",
        {"node": node_name, "text": fallback_text},
        config=config,
    )
    return AIMessage(content=fallback_text)


async def _run_tool_augmented_generation(
    agent: Any,
    *,
    messages: list[Any],
    tools: list[Any],
    node_name: str,
    config: RunnableConfig,
    fallback_text: str = "抱歉，我暂时无法回答这个问题，请稍后重试。",
    retry_prompt: str = "请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。",
    knowledge_fallback_query: str = "",  # 知识库兜底查询
) -> dict[str, Any]:
    """带保护的工具增强生成循环。

    支持知识库兜底：当模型不支持 function calling 时，自动调用知识库检索。
    注意：星火模型不支持标准 function calling，因此不绑定 tools，直接使用基础 LLM。
    """
    start_time = time.monotonic()

    tools_by_name = {t.name: t for t in tools}

    # 星火模型不支持标准 function calling，直接使用基础 LLM 避免序列化问题
    # 知识库检索通过 knowledge_fallback_query 参数兜底实现
    llm_to_use = agent.llm if tools else agent.llm

    full_messages = list(messages)
    final_result = None
    knowledge_sources: list[dict[str, Any]] = []

    result = await stream_answer_with_retry(
        agent,
        full_messages,
        node_name=node_name,
        config=config,
        runnable=llm_to_use,
        fallback_text=fallback_text,
        retry_prompt=retry_prompt,
    )

    final_result = result

    # 知识库兜底：如果开启了知识库，自动检索并注入
    if knowledge_fallback_query and "search_knowledge_base" in tools_by_name:
        logger.info("[TutorAgent] %s 知识库兜底检索 query=%s", node_name, truncate(knowledge_fallback_query, 100))
        try:
            # 获取检索结果和来源信息
            kb_context, kb_rows = format_knowledge_context(knowledge_fallback_query)
            knowledge_sources = [
                {
                    "rank": item.get("rank"),
                    "source": (item.get("metadata") or {}).get("source") or (item.get("metadata") or {}).get("book_title") or "未知来源",
                    "file_name": (item.get("metadata") or {}).get("file_name") or "",
                    "distance": item.get("distance"),
                }
                for item in kb_rows
            ]

            if kb_context and "没有检索到" not in kb_context:
                # 将知识库结果注入消息，让模型参考
                enhanced_messages = list(full_messages)
                enhanced_messages.append(HumanMessage(
                    content=f"【本地知识库检索结果】\n{kb_context}\n\n请参考以上内容回答用户问题。"
                ))
                final_result = await stream_answer_with_retry(
                    agent,
                    enhanced_messages,
                    node_name=node_name,
                    config=config,
                    fallback_text=fallback_text,
                    retry_prompt=retry_prompt,
                )
        except Exception as exc:
            logger.warning("[TutorAgent] 知识库兜底检索失败: %s", exc)

    return {
        "messages": [final_result],
        "answer_text": final_result.content,
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
    _include_knowledge: bool = False,  # Deprecated: 知识库已改为工具，此参数保留兼容但不再使用
) -> tuple[str, list[dict[str, Any]]]:
    """联网搜索上下文收集。

    注意：本地知识库检索已改为 Agent Tool，不再在此处预检索。
    """
    from app.prompts import registry

    attachment_context_section = f"\n\n附件预分析上下文：\n{attachment_context}" if attachment_context else ""
    search_instruction_template = registry.get("chat/search_instruction")

    search_instruction = HumanMessage(
        content=search_instruction_template.format(attachment_context_section=attachment_context_section)
    )
    full_messages = build_messages(system_prompt, list(messages) + [search_instruction])

    llm_with_tools = agent.llm.model.bind_tools(
        [duckduckgo_search, tavily_search, serp_search, spark_search],
    )

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
            if tool_name == "duckduckgo_search":
                result = await duckduckgo_search.ainvoke(tool_args)
            elif tool_name == "tavily_search":
                result = await tavily_search.ainvoke(tool_args)
            elif tool_name == "serp_search":
                result = await serp_search.ainvoke(tool_args)
            elif tool_name == "spark_search":
                result = await spark_search.ainvoke(tool_args)
            else:
                result = ""
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
    """统一自适应回答节点。

    当 state 存在 search_result 时，充当总结回答角色 (spark_summary)；
    当 state 没有 search_result 时，充当直接回答角色 (direct_answer)，支持自主调用搜索和记忆工具。
    当 enable_knowledge_base=True 时，绑定知识库检索工具供 Agent 自主调用。
    """
    messages = list(state.get("messages") or [])
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    system_prompt = state.get("system_prompt", "")
    question = extract_question(messages)
    search_result = state.get("search_result", "")
    diagram_enabled = bool(state.get("need_teaching_diagram", False))
    enable_knowledge_base = bool(state.get("enable_knowledge_base", False))

    # 构建工具列表
    from app.chat.tools.memory import make_memory_tools
    memory_tools = []
    if agent.context.memory_reader:
        memory_tools = make_memory_tools(agent.context.memory_reader)

    # 知识库工具：当开启知识库时绑定
    knowledge_tools = [search_knowledge_base] if enable_knowledge_base else []

    if search_result:
        node_name = "spark_summary"
        with node_timer("spark_summary", user=user_id, session=session_id):
            logger.debug("[TutorAgent] Spark 总结回答：question=%s", truncate(question, 180))

            sections_dict = _load_answer_policy_sections()
            summary_template = sections_dict.get("搜索总结提示词", "")
            prompt_content = summary_template.format(question=question, search_result=search_result)

            fallback_text = search_result or "抱歉，我暂时无法回答这个问题，请稍后重试。"
            retry_prompt = "请基于已有资料重新回答，给出完整、可读、适合教学场景的中文回答。"

            scoped_prompt = _scoped_answer_prompt(
                system_prompt,
                question=question,
                diagram_enabled=diagram_enabled,
            )

            full_messages = [
                SystemMessage(content=scoped_prompt),
                HumanMessage(content=prompt_content),
            ]

            # 记忆工具 + 知识库工具
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

            # 记忆工具 + 知识库工具
            tools = memory_tools + knowledge_tools
            fallback_text = "抱歉，我暂时无法回答这个问题，请稍后重试。"
            retry_prompt = "请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。"

    return await _run_tool_augmented_generation(
        agent=agent,
        messages=full_messages,
        tools=tools,
        node_name=node_name,
        config=config,
        fallback_text=fallback_text,
        retry_prompt=retry_prompt,
        knowledge_fallback_query=question if enable_knowledge_base else "",
    )


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
        knowledge_sources: list[dict[str, Any]] = []
        enable_web_search = bool(state.get("enable_web_search", False))
        if enable_web_search:
            # 搜索节点会获取网络搜索结果，知识库改为工具后不再在此处混合
            search_context, knowledge_sources = await collect_search_context(
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

        # 构建工具列表：知识库工具在开启时绑定
        from app.chat.tools.memory import make_memory_tools
        memory_tools = []
        if agent.context.memory_reader:
            memory_tools = make_memory_tools(agent.context.memory_reader)

        enable_knowledge_base = bool(state.get("enable_knowledge_base", False))
        knowledge_tools = [search_knowledge_base] if enable_knowledge_base else []
        tools = memory_tools + knowledge_tools

        return await _run_tool_augmented_generation(
            agent=agent,
            messages=full_messages,
            tools=tools,
            node_name="attachment_answer",
            config=config,
            fallback_text="抱歉，我暂时无法回答这个问题，请稍后重试。",
            retry_prompt="请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。",
            knowledge_fallback_query=question if enable_knowledge_base else "",
        )
