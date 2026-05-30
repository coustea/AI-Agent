# -*- coding: utf-8 -*-
"""教学图解模块。

包含显式图解请求检测、纯图解指令检测以及教学图解节点的生成逻辑。
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.chat.schemas import InsightCanvas, TutorState
from app.chat.utils import extract_question, normalize_message_content, node_timer
from app.infra.logging import get_logger

logger = get_logger(__name__)


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
            # 连续的"生成图解"轮次必须继续使用最近的实质性讲解，
            # 而非更早的图解确认回复。
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
                logger.warning("[Diagram] 跳过图解生成: 缺少问题或回答 user_id=%s", user_id)
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
            state["diagram_type"] = diagram.type
            state["teaching_diagram_error"] = None
            logger.info("[Diagram] 图解生成完成: user_id=%s type=%s", user_id, diagram.type)
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
) -> InsightCanvas:
    """使用注入的上下文生成经过验证的面向学习者的图板。"""
    from app.prompts import registry

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
        "请生成一张能辅助学生理解答案的 InsightCanvas 图板 JSON。"
    )
    return await agent.llm.ainvoke_json(
        InsightCanvas,
        [SystemMessage(content=registry.get("chat/teaching_diagram")), HumanMessage(content=prompt)],
        temperature=0.1,
    )
