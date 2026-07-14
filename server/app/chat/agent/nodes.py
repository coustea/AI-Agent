"""TutorAgent 节点实现 — LangGraph 图的各个处理节点。

节点列表（重构后）：
  - preprocess_node: 附件预处理（确定性步骤）
  - react_node: ReAct Agent 循环（自主决策工具调用和回答）
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.chat.agent.state import TutorAgentState
from app.chat.emitter import (
    build_agent_status_payload,
    build_attachment_status_payload,
    build_research_status_payload,
    build_workflow_activity_payload,
)
from app.chat.agent.tool_runner import ToolExecutionContext, TutorToolRunner
from app.chat.schemas import TutorRequestContext, TutorRuntimeEvent
from app.chat.schemas.diagram import validate_diagram_json
from app.chat.streaming import ResponseStreamer
from app.chat.agent.tools import build_tutor_tools
from app.chat.utils import normalize_message_content
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import IMAGE_EXTENSIONS
from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute, ToolRuntimeEvent

logger = get_logger(__name__)


# 返回当前日期字符串，用于注入 system prompt 的“今日日期”上下文
def _current_date_text() -> str:
    return datetime.now().date().isoformat()


_ANSWER_BLOCK_RE = re.compile(
    r"^\s*(?P<reasoning>.*?)\s*"
    r"<answer>\s*(?P<answer>.*?)\s*</answer>\s*$",
    re.DOTALL | re.IGNORECASE,
)

_DIAGRAM_TAG_RE = re.compile(
    r"<diagram>\s*(?P<json>.*?)\s*</diagram>",
    re.DOTALL | re.IGNORECASE,
)


def _normalize_reasoning_summary(text: str) -> str:
    summary = re.sub(r"</?[^>]+>", " ", text)
    summary = re.sub(r"\*\*([^*]+)\*\*", r"\1", summary)
    summary = re.sub(r"\*([^*]+)\*", r"\1", summary)
    return re.sub(r"\s+", " ", summary).strip()[:200]


# LLM 不支持图片输入时返回的错误文本模式，需从回答中剥离并替换为友好提示
_LLM_IMAGE_UNSUPPORTED_RE = re.compile(
    r"ERROR:\s*Cannot read \".+?\".*?does not support image input.*?Inform the user\.?",
    re.IGNORECASE | re.DOTALL,
)


def _strip_llm_image_error(text: str) -> tuple[str, bool]:
    """检测并移除 LLM 因不支持图片输入而返回的错误文本。

    返回 (清理后的文本, 是否包含该错误)。
    """
    if _LLM_IMAGE_UNSUPPORTED_RE.search(text):
        cleaned = _LLM_IMAGE_UNSUPPORTED_RE.sub("", text).strip()
        return cleaned, True
    return text, False


# 拆分可公开的进度摘要与严格包裹在 <answer> 标签内的正式回答
def split_reasoning_and_answer(text: str) -> tuple[str, str]:
    """拆分可公开的进度摘要与严格包裹的正式回答。"""
    # 匹配标准 <answer> 协议：前半段为推理摘要，后半段为正式回答
    match = _ANSWER_BLOCK_RE.match(text)
    if match:
        return (
            _normalize_reasoning_summary(match.group("reasoning")),
            match.group("answer").strip(),
        )

    # 出现半截 answer 标签时，整段内容都不可信，不能进入思考卡片或正式回答。
    if re.search(r"</?answer\b", text, re.IGNORECASE):
        return "", ""

    # 无标准标签：整段作为推理摘要，不产出正式回答
    return _normalize_reasoning_summary(text), ""


# 根据图解 JSON 校验错误，生成针对性的修复建议，帮助 LLM 理解出错原因
def _build_diagram_repair_hint(raw_diagram: dict[str, Any], error_msg: str) -> str:
    """根据校验错误生成具体的修复建议，帮助 LLM 理解哪里出错。"""
    if "mermaid_source" in error_msg:
        return (
            "请输出非空 mermaid_source，并确保第一行是合法 Mermaid 图类型声明；"
            "源码必须放在 JSON 字符串中，换行和双引号需要正确转义。"
        )
    graph_type = raw_diagram.get("graph_type", "")
    visual_content = raw_diagram.get("visual_content", {})
    hints: list[str] = []

    # hierarchy 类型 root 字段类型错误的修复提示
    if "root" in error_msg.lower() and graph_type == "hierarchy":
        root = visual_content.get("root")
        if isinstance(root, dict):
            hints.append(
                "hierarchy 的 root 字段必须是字符串（根节点名称），不能是嵌套对象。"
                "例如：\"root\": \"数据结构\" 而非 \"root\": {\"id\": \"ds\", ...}。"
                "嵌套树结构请使用 tree 类型。"
            )

    # hierarchy 类型 children 字段应为字符串数组的修复提示
    if "children" in error_msg.lower() and graph_type == "hierarchy":
        branches = visual_content.get("branches", [])
        for i, branch in enumerate(branches if isinstance(branches, list) else []):
            children = branch.get("children", []) if isinstance(branch, dict) else []
            if any(isinstance(c, dict) for c in children):
                hints.append(
                    f"hierarchy 的 branches[{i}].children 必须是字符串数组，不能包含嵌套对象。"
                    "例如：\"children\": [\"排序\", \"查找\"] 而非 \"children\": [{\"label\": \"排序\"}]。"
                )
                break

    # grid 类型 cells index 字段必须为整数的修复提示
    if "index" in error_msg.lower() and graph_type == "grid":
        hints.append("grid 的 cells[].index 必须是整数，不能是字符串。")

    # graph_type 与 visual_content 不匹配时，给出各类图结构的字段要求
    if "visual_content must match" in error_msg.lower() or "完整校验失败" in error_msg:
        # graph_type 与 visual_content 不匹配，建议重新选择
        type_hints = {
            "comparison": "root 应包含 left_entity, right_entity, dimensions, visual_summary",
            "flowchart": "root 应包含 direction, nodes, edges；edges 使用 'from'（非 'from_'）",
            "sequence": "root 应包含 actors, messages；messages 使用 'from'（非 'from_'）",
            "framework": "root 应包含 center, modules",
            "summary": "root 应包含 cards",
            "hierarchy": "root 是字符串（非嵌套对象），branches 是数组",
            "tree": "root 应包含 root_id, nodes",
            "grid": "root 应包含 layout, cells",
            "protocol": "root 应包含 orientation, fields",
            "timeline": "root 应包含 axis_label, tracks",
        }
        if graph_type in type_hints:
            hints.append(f"{graph_type} 类型要求：{type_hints[graph_type]}")

    # 没有更具体的提示时，给出通用校验建议
    if not hints:
        hints.append("请检查 mermaid_source 是否为可直接渲染的 Mermaid 源码。")

    # 将修复提示拼接为单行中文说明
    return "；".join(hints)


# 从 <answer> 内容中提取 <diagram> 标签内的 JSON，返回去除标签后的回答与解析结果
def _try_repair_json(text: str) -> dict[str, Any] | None:
    """尝试修复 LLM 输出的常见 JSON 格式问题。"""
    repaired = text
    # 1. 移除尾逗号（对象/数组最后一个元素后的逗号）
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    # 2. 移除行尾注释 // ... 或 /* ... */
    repaired = re.sub(r"//[^\n]*", "", repaired)
    repaired = re.sub(r"/\*.*?\*/", "", repaired, flags=re.DOTALL)
    # 3. 将单引号替换为双引号（仅当不含内部双引号时）
    if "'" in repaired and '"' not in repaired:
        repaired = repaired.replace("'", '"')
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # 4. 尝试补全缺失的右括号
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")
    if open_braces > 0 or open_brackets > 0:
        attempt = repaired + "]" * max(0, open_brackets) + "}" * max(0, open_braces)
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            pass

    return None


# 从 <answer> 内容中提取 <diagram> 标签内的 JSON，返回去除标签后的回答与解析结果
def extract_diagram_from_answer(answer_body: str) -> tuple[str, dict[str, Any] | None, str]:
    """从 <answer> 内容中提取 <diagram> 标签的 JSON。

    返回 (cleaned_answer, diagram_dict, parse_status)。
    - parse_status: "ok" | "no_tag" | "json_error"
    - 如果找到 <diagram> 标签且 JSON 合法，返回去除 <diagram> 的回答、解析后的 dict、"ok"
    - 如果未找到 <diagram> 标签，返回原回答、None、"no_tag"
    - 如果 JSON 解析失败（含修复尝试），返回原回答、None、"json_error"
    """
    # 未找到 <diagram> 标签则直接返回原回答，无图解
    match = _DIAGRAM_TAG_RE.search(answer_body)
    if not match:
        return answer_body, None, "no_tag"

    # 提取 JSON 文本
    json_text = match.group("json").strip()
    # 移除可能的 markdown 代码块包裹
    if json_text.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*\n?", "", json_text)
        json_text = re.sub(r"\n?```\s*$", "", json_text)
        json_text = json_text.strip()

    # 解析 JSON，失败则尝试常见修复后再解析
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        repaired = _try_repair_json(json_text)
        if repaired is not None:
            parsed = repaired
            logger.info("[extract_diagram] JSON 修复成功")
        else:
            logger.warning("[extract_diagram] JSON 解析失败，标记为可修复")
            return answer_body, None, "json_error"

    # 从回答中移除 <diagram> 标签并清理空白
    cleaned = _DIAGRAM_TAG_RE.sub("", answer_body).strip()
    return cleaned, parsed, "ok"


# 生成思考卡片的降级摘要：优先用推理文本，其次用决策文本，最后用默认模板
def _thinking_summary(reasoning: str, iteration: int, decision_text: str = "") -> str:
    return (
        reasoning
        or _normalize_reasoning_summary(decision_text)
        or f"第 {iteration} 次推理：分析问题 → 规划回答策略"
    )


# -----------------------------------------------------------------------
# 节点 1: preprocess_node（附件预处理）
# -----------------------------------------------------------------------


# 预处理节点：分析附件（图片 OCR / 文档解析），填充 attachment_context 供后续回答使用
async def preprocess_node(
    agent: Any,
    state: TutorAgentState,
) -> dict:
    """预处理节点：分析附件（图片 OCR、文档解析），填充 attachment_context。

    这是确定性步骤，无条件执行。无附件时返回空结果。
    """
    attachments = state.get("attachments", [])
    user_id = state.get("user_id", 0)
    username = state.get("username", "")
    session_id = state.get("session_id", "")
    user_message_id = state.get("user_message_id", 0)

    # 无附件则直接返回空上下文
    if not attachments:
        return {"attachment_context": ""}

    # 按扩展名将附件分为图片与文档两类
    image_urls, file_urls = [], []
    for url in attachments:
        ext = url.rsplit(".", 1)[-1].lower().split("?")[0] if "." in url else ""
        if ext in IMAGE_EXTENSIONS:
            image_urls.append(url)
        else:
            file_urls.append(url)

    # 收集附件分析事件与持久化记录
    events: list[TutorRuntimeEvent] = []
    analysis_records: dict[str, Any] = {}
    # 遍历图片、文档两类附件，分别创建分析记录并发送 running 事件
    activity_groups = (("image", image_urls), ("document", file_urls))
    for index, (analysis_type, urls) in enumerate(activity_groups):
        if not urls:
            continue
        # 为本次附件分析在记忆中创建一条记录
        analysis_records[analysis_type] = await agent.memory_service.create_attachment_analysis(
            user_id=user_id,
            session_id=session_id,
            user_message_id=user_message_id,
            analysis_type=analysis_type,
        )
        event = TutorRuntimeEvent(
            type="agent_status",
            payload=build_attachment_status_payload(
                activity_id=f"attachment-{analysis_type}-{index}",
                status="running",
                file_names=[url.split("/")[-1] for url in urls],
                analysis_type=analysis_type,
            ),
            sequence=len(state.get("stream_events", [])) + 1 + index,
            timestamp=time.time(),
        )
        events.extend(await agent._emit_event(state, event))

    analysis_results: dict[str, str] = {}
    analysis_errors: dict[str, str] = {}

    # 图片附件：调用视觉服务进行 OCR / 图表分析
    if image_urls:
        try:
            vision_result = await VisionService().analyze_images(
                image_urls[:5],
                "请详细分析这些图片中的文字、题目、图表和关键信息，并用中文总结。",
            )
            analysis_text = str(vision_result.get("analysis_text") or "").strip()
            if analysis_text:
                analysis_results["image"] = analysis_text
                await agent.memory_service.finish_attachment_analysis(
                    analysis_id=str(analysis_records["image"].id),
                    content=analysis_text,
                )
            else:
                analysis_errors["image"] = "未提取到可用内容"
        # 图片分析失败则记录错误，不阻断流程
        except Exception as exc:
            logger.warning("[preprocess_node] 图片分析失败: %s", exc)
            analysis_errors["image"] = str(exc)
        # 分析失败时更新附件分析记录的错误信息
        if "image" in analysis_errors:
            await agent.memory_service.finish_attachment_analysis(
                analysis_id=str(analysis_records["image"].id),
                content="",
                error_message=analysis_errors["image"],
            )

    # 文档附件：调用文档解析服务提取内容
    if file_urls:
        try:
            analysis = await analyze_documents(
                current_username=username,
                file_urls=file_urls[:5],
                question="请分析这些文档",
            )
            summary = str(analysis.get("analysis_text") or "").strip()
            if summary:
                analysis_results["document"] = summary
                await agent.memory_service.finish_attachment_analysis(
                    analysis_id=str(analysis_records["document"].id),
                    content=summary,
                )
            else:
                analysis_errors["document"] = "未提取到可用内容"
        # 文档分析失败则记录错误，不阻断流程
        except Exception as exc:
            logger.warning("[preprocess_node] 文档分析失败: %s", exc)
            analysis_errors["document"] = str(exc)
        # 分析失败时更新文档分析记录的错误信息
        if "document" in analysis_errors:
            await agent.memory_service.finish_attachment_analysis(
                analysis_id=str(analysis_records["document"].id),
                content="",
                error_message=analysis_errors["document"],
            )

    # 将图片/文档分析结果拼接为附件上下文文本
    attachment_context = "\n".join(
        f"[{'图片' if analysis_type == 'image' else '文档'}] {content}"
        for analysis_type, content in analysis_results.items()
    )

    # 为每个附件类型发送完成/失败事件
    done_events: list[TutorRuntimeEvent] = []
    for index, (analysis_type, urls) in enumerate(activity_groups):
        if not urls:
            continue
        # 根据分析结果判定状态
        status = "done" if analysis_results.get(analysis_type) else "failed"
        event = TutorRuntimeEvent(
            type="agent_status",
            payload=build_attachment_status_payload(
                activity_id=f"attachment-{analysis_type}-{index}",
                status=status,
                file_names=[str(url).split("/")[-1] for url in urls],
                analysis_type=analysis_type,
                summary=analysis_results.get(analysis_type, "") if status == "done" else "",
                error=analysis_errors.get(analysis_type, "未提取到可用内容") if status == "failed" else "",
            ),
            sequence=len(state.get("stream_events", [])) + len(events) + 1 + index,
            timestamp=time.time(),
        )
        done_events.extend(await agent._emit_event(state, event))

    # 返回附件上下文与全部流式事件，供状态图累积
    return {
        "attachment_context": attachment_context,
        "stream_events": events + done_events,
    }


# -----------------------------------------------------------------------
# 节点 2: react_node（ReAct Agent 循环）
# -----------------------------------------------------------------------


# ReAct 节点：LLM 自主决策工具调用并流式输出回答，处理图解提取与格式修复
async def react_node(
    agent: Any,
    state: TutorAgentState,
    llm: Any,
    prompts: Any,
    memory_service: Any,
) -> dict:
    """ReAct 节点：LLM 自主决策工具调用，流式输出回答。

    流程：
    1. 构建工具集（per-request binding）
    2. 构建 system prompt（统一 tutor_agent.md）
    3. ReAct loop: LLM → tool_call → tool_result → LLM → ... → 最终回答
    4. 流式输出 answer_token（进入 SafetyBuffer）
    5. 从 <answer> 中提取 <diagram> 标签内容，校验并持久化
    """
    question = state.get("question", "")
    history = state.get("history_messages", [])
    session_summary = state.get("session_summary", "")
    attachment_context = state.get("attachment_context", "")
    attachments = state.get("attachments", [])
    user_id = state.get("user_id", 0)
    session_id = state.get("session_id", "")
    user_message_id = state.get("user_message_id", 0)
    enable_web_search = state.get("enable_web_search", False)
    need_teaching_diagram = state.get("need_teaching_diagram", False)

    node_events: list[TutorRuntimeEvent] = []
    node_tool_invocations: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    node_errors: list[str] = []
    node_diagram_result: dict[str, Any] | None = None
    full_answer = ""
    base_seq = len(state.get("stream_events", [])) + 1

    # 联网搜索状态事件发射器：转发研究状态为 agent_status 事件
    async def emit_research_status(event: Any) -> None:
        nonlocal base_seq
        base_seq += 1
        emitted = await agent._emit_event(
            state,
            TutorRuntimeEvent(
                type="agent_status",
                payload=build_research_status_payload(event),
                sequence=base_seq,
                timestamp=time.time(),
            ),
        )
        node_events.extend(emitted)

    # ── 1. 构建工具集 ──
    # 组装本轮请求上下文（用户、附件、联网搜索、图解开关）
    request_context = TutorRequestContext(
        user_id=user_id,
        username=state.get("username", ""),
        session_id=session_id,
        user_input=question,
        attachments=attachments,
        enable_web_search=enable_web_search,
        need_teaching_diagram=need_teaching_diagram,
    )
    tools = build_tutor_tools(
        request_context,
        research_event_handler=emit_research_status,
    )

    # 工具调用状态事件发射器：转发工具运行时事件为 agent_status 事件
    async def emit_tool_status(event: ToolRuntimeEvent) -> None:
        nonlocal base_seq
        base_seq += 1
        emitted = await agent._emit_event(
            state,
            TutorRuntimeEvent(
                type="agent_status",
                payload=build_agent_status_payload(event),
                sequence=base_seq,
                timestamp=time.time(),
            ),
        )
        node_events.extend(emitted)

    tool_excute = ToolExcute(tools=tools, event_handler=emit_tool_status)
    tool_context = ToolExecutionContext(
        user_id=user_id,
        session_id=session_id,
        user_message_id=user_message_id,
        memory_service=memory_service,
    )

    # 统一的工具执行封装：调用 TutorToolRunner 并收集调用记录、来源与错误
    async def execute_tutor_tool(
        *,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str,
    ) -> Any:
        runner = TutorToolRunner()
        result = await runner.execute(
            tool_name=tool_name,
            arguments=arguments,
            tool_call_id=tool_call_id,
            context=tool_context,
            tool_excute=tool_excute,
        )
        if result.invocation:
            node_tool_invocations.append(result.invocation)
        node_sources.extend(result.sources)
        node_errors.extend(result.errors)
        return result

    # 若开启联网搜索，强制先执行 research 工具并将结果注入上下文
    forced_context_blocks: list[str] = []
    if enable_web_search:
        search_result = await execute_tutor_tool(
            tool_name="research",
            arguments={
                "query": question,
                "objective": "Provide current web evidence for the tutor answer.",
                "depth": "standard",
            },
            tool_call_id="forced-research",
        )
        search_text = str((search_result.invocation or {}).get("result_text", "") or "").strip()
        if search_text:
            forced_context_blocks.append(f"[联网搜索结果]\n{search_text}")

    # ── 2. 构建 system prompt（统一 tutor_agent 模板，注入会话概要/附件/日期/辅导策略等）──
    from app.infra.database import session_scope
    from app.evaluation.guidance import get_effective_guidance_strategy
    async with session_scope() as db:
        strategy = await get_effective_guidance_strategy(db, user_id)
    
    strategy_str = (
        f"当前周期目标: {strategy.get('weekly_goal')}\n"
        f"推荐单次时长: {strategy.get('recommended_session_minutes')} 分钟\n"
        f"辅导风格: {strategy.get('tutoring_style')}\n"
        f"重点关注主题: {'、'.join(strategy.get('focus_topics', [])) or '无'}\n"
        f"偏好资源类型: {'、'.join(strategy.get('preferred_resource_types', [])) or '无'}"
    )

    system_prompt = prompts.get("chat").render(
        "tutor_agent",
        session_summary_context=session_summary,
        file_context=f"附件 {len(attachments)} 个" if attachments else "本轮没有上传附件。",
        attachment_analysis_context=attachment_context or "本轮没有可用的附件预分析内容。",
        current_date=_current_date_text(),
        diagram_mode=(
            "开启（学生已在前端勾选“图解”开关，你必须在 <answer> 中包含 <diagram> 标签输出图解 JSON）"
            if need_teaching_diagram
            else "关闭"
        ),
        guidance_strategy_context=strategy_str,
    )

    # ── 3. 初始化消息和事件收集 ──
    # 组装用户消息，依次拼接附件分析结果与强制搜索上下文
    human_content = question
    if attachment_context:
        human_content = f"{question}\n\n[附件分析结果]\n{attachment_context}"

    if forced_context_blocks:
        human_content = f"{human_content}\n\n" + "\n\n".join(forced_context_blocks)

    # 构建完整消息列表：system + 历史 + 本轮 human
    messages: list[AnyMessage] = [SystemMessage(content=system_prompt), *history, HumanMessage(content=human_content)]

    # ── 4. ReAct 循环（最多 8 轮：LLM → 工具 / 回答）──
    max_iterations = 8
    iteration = 0

    tool_model = (
        llm.model.bind_tools(tool_excute.get_tools_description())
        if tools
        else llm.model
    )
    format_repair_used = False
    diagram_repair_used = False

    while iteration < max_iterations:
        iteration += 1

        # ── 4.1 发送"正在思考"状态事件 ──
        thinking_event = TutorRuntimeEvent(
            type="agent_status",
            payload=build_workflow_activity_payload(
                stage="thinking",
                activity_id=f"thinking-iteration-{iteration}",
                title="分析思考过程",
                message=f"第 {iteration} 次推理：正在分析问题并规划回答策略...",
                status="running",
            ),
            sequence=base_seq + iteration * 10 - 1,
            timestamp=time.time(),
        )
        await agent._emit_event(state, thinking_event)

        # ── 4.2 流式调用 LLM（支持工具调用）──
        # 先收集完整一轮。只有流结束后才能可靠判断该轮是工具决策还是最终回答，
        try:
            # 因此不能在这里提前把文本作为 answer_token 发给前端。
            answer_text = ""
            seq = base_seq + iteration * 10
            accumulated_response = None  # 用于累积工具调用

            async for chunk in llm.astream(
                messages,
                runnable=tool_model,
            ):
                # 累积完整响应（流式结束后用于提取 tool_calls）
                accumulated_response = chunk if accumulated_response is None else accumulated_response + chunk

                # 文本可能是思考摘要、工具决策说明或最终回答，暂不对外发送。
                token = normalize_message_content(getattr(chunk, "content", ""))
                if token:
                    answer_text += token

                # 处理工具调用 chunks（流式累积）
                # tool_call_chunks 在流式过程中逐步到达
                tool_call_chunks = getattr(chunk, "tool_call_chunks", None)
                if tool_call_chunks:
                    # 工具调用正在生成，可以在这里发送状态
                    # 但完整的工具调用信息需要在流式结束后从 accumulated_response 获取
                    pass

            # ── 4.3 从累积的响应中获取完整的 tool_calls ──
            # 提取工具调用并拆分推理摘要与正式回答
            tool_calls = getattr(accumulated_response, "tool_calls", None) if accumulated_response else None
            reasoning_summary, answer_body = split_reasoning_and_answer(answer_text)

            # 检测 LLM 因不支持图片输入而返回的错误，替换为友好提示
            answer_body, has_image_error = _strip_llm_image_error(answer_body)
            if has_image_error:
                answer_body = "抱歉，当前模型暂不支持直接读取图片。请将图片中的关键内容以文字描述发送，我会尽力帮助你。"
                logger.info("[react_node] 检测到 LLM 不支持图片输入，替换为友好提示")

            # 判断本轮是否产出最终回答或需要格式修复
            has_final_answer = bool(answer_body)
            needs_format_repair = not tool_calls and not has_final_answer

            # 每轮 thinking 都必须收口；工具轮使用其决策文本作为降级摘要。
            thinking_done_event = TutorRuntimeEvent(
                type="agent_status",
                payload=build_workflow_activity_payload(
                    stage="thinking",
                    activity_id=f"thinking-iteration-{iteration}",
                    title="思考完成",
                    message=(
                        f"第 {iteration} 次推理完成，准备调用工具"
                        if tool_calls
                        else "回答边界校验未通过，正在重新整理"
                        if needs_format_repair
                        else f"第 {iteration} 次推理完成，开始生成回答"
                    ),
                    summary=_thinking_summary(
                        reasoning_summary,
                        iteration,
                        answer_text if tool_calls else "",
                    ),
                    status="failed" if needs_format_repair and format_repair_used else "done",
                ),
                sequence=base_seq + iteration * 10,
                timestamp=time.time(),
            )
            # 发送本轮思考完成事件
            await agent._emit_event(state, thinking_done_event)

            # 本轮没有工具调用 → 可能是最终回答或需要格式修复
            if not tool_calls:
                # 无工具调用且无正式回答 → 触发格式修复（仅一次）
                if needs_format_repair:
                    # 已修复过仍失败 → 报错并终止循环
                    if format_repair_used:
                        error_message = "模型未按 <answer>...</answer> 协议返回正式回答"
                        node_errors.append(error_message)
                        await agent._emit_event(
                            state,
                            TutorRuntimeEvent(
                                type="error",
                                payload={"error": error_message},
                                sequence=seq,
                                timestamp=time.time(),
                            ),
                        )
                        break

                    # 首次触发：将本轮响应与修复提示追加到消息列表并重试
                    format_repair_used = True
                    if accumulated_response is not None:
                        messages.append(accumulated_response)
                    messages.append(HumanMessage(content=(
                        "[FORMAT REPAIR]\n"
                        "上一条响应缺少完整的最终回答边界。不要调用工具，不要重复内部推理。"
                        "请仅输出一条简短、可公开的进度摘要，随后把面向学生的完整回答严格放入 "
                        "<answer>...</answer> 中。"
                    )))
                    continue

                # ── 无工具调用 → 这是最终回答 ──

                # 提取回答中的 <diagram> 标签内容
                cleaned_answer, raw_diagram, diagram_parse_status = extract_diagram_from_answer(answer_body)

                # JSON 解析失败但找到了 <diagram> 标签 → 触发修复重试
                if diagram_parse_status == "json_error" and not diagram_repair_used:
                    diagram_repair_used = True
                    logger.info("[react_node] 图解 JSON 解析失败，发起修复重试")
                    if accumulated_response is not None:
                        messages.append(accumulated_response)
                    messages.append(HumanMessage(content=(
                        "[DIAGRAM REPAIR]\n"
                        "上一次图解 JSON 格式不合法，无法解析。\n"
                        "请严格输出合法 JSON，确保所有字符串使用双引号、属性间用逗号分隔、无尾逗号。\n"
                        "请修复并重新输出完整的 <answer>，包含修复后的 <diagram>...</diagram>。"
                        "确保 graph_type 合法，mermaid_source 是正确转义的 Mermaid 源码。"
                    )))
                    continue
                elif diagram_parse_status == "json_error":
                    # 修复已用过仍失败，放弃图解，去除标签保留文字回答
                    logger.warning("[react_node] 图解 JSON 修复重试仍失败，放弃图解")
                    answer_body = cleaned_answer

                # 存在图解 JSON 则进行校验与修复处理
                if raw_diagram is not None:
                    # 校验图解 JSON 结构是否合法
                    validated, diagram_error = validate_diagram_json(raw_diagram)
                    if validated is not None:
                        # 校验通过：保存图解结果并去除标签
                        node_diagram_result = validated
                        answer_body = cleaned_answer
                    elif not diagram_repair_used:
                        # 校验失败 → 修复重试
                        # 校验失败且未重试过：生成修复提示并重试一次
                        diagram_repair_used = True
                        logger.info("[react_node] 图解 JSON 校验失败，发起修复重试: %s", diagram_error)
                        if accumulated_response is not None:
                            messages.append(accumulated_response)
                        repair_hint = _build_diagram_repair_hint(raw_diagram, diagram_error)
                        messages.append(HumanMessage(content=(
                            "[DIAGRAM REPAIR]\n"
                            f"上一次图解 JSON 校验失败：{diagram_error}\n"
                            f"已生成内容：{json.dumps(raw_diagram, ensure_ascii=False)[:2000]}\n"
                            f"修复建议：{repair_hint}\n"
                            "请修复并重新输出完整的 <answer>，包含修复后的 <diagram>...</diagram>。"
                            "确保 graph_type 合法，mermaid_source 是可直接渲染的 Mermaid 源码。"
                        )))
                        continue
                    else:
                        # 修复重试已用完，放弃图解，仅保留文字回答
                        logger.warning("[react_node] 图解 JSON 修复重试仍失败，放弃图解: %s", diagram_error)
                        answer_body = cleaned_answer

                # 流式输出最终回答（逐 token 发送 answer_token 事件）
                streamer = ResponseStreamer()
                async for chunk_event in streamer.stream_answer(answer_body, skip_blank=False):
                    chunk_token = chunk_event.get("data", "")
                    if chunk_token:
                        # 累积完整回答并实时推送 token
                        full_answer += chunk_token
                        event = TutorRuntimeEvent(
                            type="answer_token",
                            payload={"token": chunk_token},
                            sequence=seq,
                            timestamp=time.time(),
                        )
                        await agent._emit_event(state, event, persist=False)
                        seq += 1

                # 回答完成事件
                answer_done_event = TutorRuntimeEvent(
                    type="answer_done",
                    payload={"answer_length": len(full_answer)},
                    sequence=seq,
                    timestamp=time.time(),
                )
                # 发送回答完成事件并跳出循环
                await agent._emit_event(state, answer_done_event)

                break  # 跳出循环

            # ── 4.4 有 tool_calls → 执行工具，将结果回灌给 LLM ──
            # 将本轮含 tool_calls 的 AI 消息加入上下文
            messages.append(accumulated_response)  # 添加完整的 AIMessage（含 tool_calls）

        # 捕获 LLM 流式调用异常，返回空回答与错误信息
        except Exception as exc:
            logger.exception("[react_node] LLM 流式输出失败")
            return {
                "final_answer": "",
                "stream_events": node_events,
                "errors": [f"LLM streaming failed: {exc}"],
            }

        # 逐个执行 LLM 请求的工具调用
        for tool_call in tool_calls:
            tool_call_id = str(tool_call.get("id", ""))
            tool_name = str(tool_call.get("name", ""))
            tool_args = tool_call.get("args", {}) if isinstance(tool_call.get("args"), dict) else {}

            try:
                # 执行工具并收集结果
                result = await execute_tutor_tool(
                    tool_name=tool_name,
                    arguments=tool_args,
                    tool_call_id=tool_call_id,
                )

                # 将工具返回文本封装为 ToolMessage 加入上下文
                tool_result_text = str((result.invocation or {}).get("result_text", "") or "")
                messages.append(ToolMessage(content=tool_result_text, tool_call_id=tool_call_id))

            # 单个工具执行失败则记录错误并回灌失败消息，避免中断循环
            except Exception as exc:
                logger.warning("[react_node] 工具 %s 失败: %s", tool_name, exc)
                node_errors.append(f"{tool_name}: {exc}")
                messages.append(ToolMessage(content=f"工具调用失败: {exc}", tool_call_id=tool_call_id))

    # ── 5. 返回 state 更新（最终回答、图解、消息、事件、调用记录、来源、错误）──
    return {
        "final_answer": full_answer,
        "diagram_result": node_diagram_result,
        "messages": messages,
        "stream_events": node_events,
        "tool_invocations": node_tool_invocations,
        "sources": node_sources,
        "errors": node_errors,
    }
