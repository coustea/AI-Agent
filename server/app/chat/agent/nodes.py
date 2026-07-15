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
from app.chat.schemas import DiagramMode, TutorRequestContext, TutorRuntimeEvent
from app.chat.schemas.diagram import validate_diagram_json
from app.chat.streaming import ResponseStreamer
from app.chat.agent.tools import GENERATE_TEACHING_DIAGRAM_TOOL_NAME, build_tutor_tools
from app.chat.utils import normalize_message_content
from app.chat.utils.files import analyze_documents
from app.chat.utils.vision import VisionService
from app.config import IMAGE_EXTENSIONS
from app.infra.logging import get_logger
from app.infra.tool_excute import ToolExcute, ToolRuntimeEvent

logger = get_logger(__name__)

VOICE_DIAGRAM_MAX_CHARS = 96

_VOICE_TOOL_DEPENDENT_REQUEST_RE = re.compile(
    r"(?:图解|流程图|架构图|示意图|思维导图|mermaid|diagram|"
    r"联网|上网|搜索|检索|查资料|最新|新闻|今天发生|"
    r"知识库|学习画像|长期记忆)",
    re.IGNORECASE,
)

_VOICE_DETAILED_REQUEST_RE = re.compile(
    r"(?:详细|深入|完整|系统|展开讲|分步骤|步骤|代码|证明|推导|"
    r"时间复杂度|空间复杂度|性质|原理|机制|区别|比较|优缺点|"
    r"举例|例子|为什么|如何实现)",
    re.IGNORECASE,
)

_VOICE_CONCISE_REQUEST_RE = re.compile(
    r"(?:一句(?:完整(?:的)?)?话|两句话|三句话|简短|简要|概括|不要展开|不展开|"
    r"\d+\s*个?字以内)",
    re.IGNORECASE,
)

_VOICE_HARD_TECHNICAL_REQUEST_RE = re.compile(
    r"(?:分步骤|步骤|代码|证明|推导|公式|时间复杂度|空间复杂度|性质|如何实现)",
    re.IGNORECASE,
)


# 返回当前日期字符串，用于注入 system prompt 的"今日日期"上下文
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


def _recover_unwrapped_answer(text: str) -> str:
    """Recover a public answer after the one allowed envelope repair failed."""
    recovered = re.sub(
        r"<think\b[^>]*>.*?</think>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    opening = re.search(r"<answer\b[^>]*>", recovered, re.IGNORECASE)
    if opening:
        recovered = recovered[opening.end():]
    return re.sub(r"</answer\s*>", "", recovered, flags=re.IGNORECASE).strip()


def _should_use_fast_voice_response(
    *,
    question: str,
    voice_mode: bool,
    attachments: list[str],
    enable_web_search: bool,
    diagram_mode: DiagramMode,
) -> bool:
    """Use one direct model round for ordinary spoken conversation.

    Requests that explicitly depend on tools, structured diagram output, or a
    detailed technical explanation keep the full tutor prompt and ReAct loop.
    The lightweight prompt is intentionally limited to ordinary conversation;
    using it for formulas and multi-part knowledge questions can trade away
    factual precision for brevity.
    """
    if not voice_mode or attachments or enable_web_search or diagram_mode == "required":
        return False
    text = question or ""
    if (
        _VOICE_CONCISE_REQUEST_RE.search(text)
        and not _VOICE_HARD_TECHNICAL_REQUEST_RE.search(text)
    ):
        return True
    return not (
        _VOICE_TOOL_DEPENDENT_REQUEST_RE.search(text)
        or _VOICE_DETAILED_REQUEST_RE.search(text)
    )


def _build_fast_voice_system_prompt(session_summary: str) -> str:
    summary = (session_summary or "").strip()
    context_line = f"\n会话摘要：{summary[:800]}" if summary else ""
    return (
        "你是面向计算机专业学生的中文辅导老师，当前回答会由数字人一次性完整播报。\n"
        "直接回答用户当前这句话；结合最近对话理解省略和指代，不要复述无关的旧问题。\n"
        "普通问答使用一到三句自然口语，优先给核心结论，通常控制在120个中文字以内。\n"
        "用户明确要求详细讲解、步骤或代码时可以适当展开。\n"
        "技术定义、性质和复杂度必须使用教材标准术语并保留成立前提；回答前先核对事实。\n"
        "比较两个概念时只说明可验证的差异和适用场景；未指定实现和操作类型时，禁止断言某一个整体更快或更慢。\n"
        "不要调用工具，不要展示思考过程，不要使用Markdown标题或表格。\n"
        "只输出可直接朗读的完整回答正文，不要添加<answer>等标签。"
        f"{context_line}"
    )


def _build_detailed_voice_accuracy_guard(question: str) -> str:
    """Add compact, topic-specific facts that must survive voice summarization."""
    normalized = str(question or "")
    if "红黑树" not in normalized:
        return ""
    return """

## 红黑树事实边界
- 经典 CLRS 插入修复最多执行 2 次旋转；删除修复最多执行 3 次旋转。
- 重新着色可能沿祖先方向传播到根，不能写成"修正只涉及常数层"。
- 查找、插入、删除的最坏时间复杂度都是 O(log n)，但旋转次数与重新着色传播范围必须分别表述。
- 与 AVL 树比较时，只能说红黑树通常旋转次数较少，不能无条件断言插入删除的均摊代价一定更低。
"""


def condense_voice_diagram_answer(
    text: str,
    max_chars: int = VOICE_DIAGRAM_MAX_CHARS,
) -> str:
    """Keep digital-human diagram narration concise while the image holds details."""
    cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"^\s*(?:#{1,6}|[-*+] |\d+\. )", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= max_chars:
        return cleaned

    sentences = re.findall(r"[^。！？!?]+[。！？!?]?", cleaned)
    selected = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(selected) + len(sentence) > max_chars:
            break
        selected += sentence
    if selected:
        return selected.strip()

    prefix = cleaned[:max_chars]
    boundary = max(prefix.rfind(mark) for mark in "，,；;：:")
    if boundary >= max_chars // 2:
        prefix = prefix[:boundary]
    return prefix.rstrip("，,；;：: ") + "。"


def build_deterministic_fallback_diagram(question: str, answer: str) -> dict[str, Any] | None:
    """Build a deterministic diagram when the model omitted diagram markup."""
    topic = re.sub(r"(?:请|给我|帮我|生成|制作|画|一个|一张|的?图解)", "", question)
    topic = re.sub(r"\s+", " ", topic).strip(" ，。！？,.!?") or "本节知识"

    def safe_label(value: str, limit: int = 42) -> str:
        cleaned = re.sub(r'["<>\[\]{}()]', "", value)
        return re.sub(r"\s+", " ", cleaned).strip()[:limit]

    normalized_question = question.lower().replace(" ", "")
    known_points: list[str] = []
    if "b+树" in normalized_question or "b＋树" in normalized_question:
        known_points = [
            "查找：从根索引逐层定位到叶子节点",
            "插入：写入有序叶子，溢出时分裂并向上更新索引",
            "删除：移除叶子键，低于下限时借位或合并",
            "范围查询：沿叶子链表顺序扫描",
        ]
    elif "红黑树" in normalized_question:
        known_points = [
            "根节点和空叶子节点为黑色",
            "红色节点不能拥有红色子节点",
            "任一路径包含相同数量的黑色节点",
            "插入删除后通过变色与旋转恢复平衡",
        ]
    elif "avl" in normalized_question:
        known_points = [
            "LL 型：对失衡节点执行右旋",
            "RR 型：对失衡节点执行左旋",
            "LR 型：先左旋子节点，再右旋失衡节点",
            "RL 型：先右旋子节点，再左旋失衡节点",
        ]
    elif "堆排序" in normalized_question:
        known_points = [
            "从最后一个非叶子节点开始建最大堆",
            "交换堆顶与当前末尾元素",
            "缩小堆范围并向下调整",
            "重复提取堆顶直到完成排序",
        ]

    points = [safe_label(point) for point in known_points]
    if not points:
        points = [
            label
            for part in re.split(r"[。！？!?\n]+", answer)
            if (label := safe_label(part))
        ][:4]
    if not points:
        points = ["核心概念", "关键规则", "典型示例"]

    mermaid_lines = ["flowchart TB", f'    ROOT["{safe_label(topic)}"]']
    mermaid_lines.extend(
        f'    ROOT --> S{index}["{point}"]'
        for index, point in enumerate(points, start=1)
    )
    raw_diagram = {
        "graph_type": "summary",
        "title": f"{topic}图解",
        "teaching_goal": f"理解{topic}的核心概念与关键规则",
        "difficulty": "beginner",
        "mermaid_source": "\n".join(mermaid_lines),
        "teaching_content": {
            "core_explanation": answer,
            "key_points": points,
            "common_mistakes": [],
            "examples": [],
            "summary": points[0],
        },
    }
    validated, error = validate_diagram_json(raw_diagram)
    if validated is None:
        logger.warning("[react_node] deterministic diagram fallback failed: %s", error)
    return validated


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
    diagram_mode = state.get("diagram_mode", "auto")
    diagram_required = diagram_mode == "required"
    voice_mode = state.get("voice_mode", False)
    fast_voice_response = _should_use_fast_voice_response(
        question=question,
        voice_mode=voice_mode,
        attachments=attachments,
        enable_web_search=enable_web_search,
        diagram_mode=diagram_mode,
    )

    node_events: list[TutorRuntimeEvent] = []
    node_tool_invocations: list[dict[str, Any]] = []
    node_sources: list[dict[str, Any]] = []
    node_errors: list[str] = []
    node_diagram_result: dict[str, Any] | None = None
    full_answer = ""
    messages: list[AnyMessage] = []
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
        diagram_mode=diagram_mode,
    )
    tools = build_tutor_tools(
        request_context,
        research_event_handler=emit_research_status,
        diagram_context=attachment_context,
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

    # ── 1b. diagram_mode="required": skip LLM, directly call diagram tool ──
    if diagram_required:
        diagram_result = await execute_tutor_tool(
            tool_name=GENERATE_TEACHING_DIAGRAM_TOOL_NAME,
            arguments={"focus": question},
            tool_call_id="direct-diagram",
        )
        raw_payload = diagram_result.result_payload
        if raw_payload is not None:
            validated, diagram_error = validate_diagram_json(raw_payload)
            if validated is not None:
                node_diagram_result = validated
            else:
                raise RuntimeError(
                    f"diagram generation failed validation: {diagram_error}"
                )
        else:
            raise RuntimeError("diagram generation returned no payload")

        if voice_mode:
            condensed = condense_voice_diagram_answer(question)
            full_answer = condensed
        # Return immediately with diagram only — no answer_token events.
        return {
            "final_answer": full_answer,
            "diagram_result": node_diagram_result,
            "messages": messages,
            "stream_events": node_events,
            "tool_invocations": node_tool_invocations,
            "sources": node_sources,
            "errors": node_errors,
        }

    # ── 2. 构建 system prompt ──
    if fast_voice_response:
        system_prompt = _build_fast_voice_system_prompt(session_summary)
        # Recent turns are sufficient for spoken references and keep prompt
        # evaluation latency bounded in long-running voice conversations.
        history = history[-6:]
        logger.info("[react_node] fast voice response path enabled history=%d", len(history))
    else:
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
                "开启（学生已在前端勾选'图解'开关，系统会自动调用 generate_teaching_diagram 工具生成图解）"
                if diagram_required
                else "关闭"
            ),
            guidance_strategy_context=strategy_str,
        )
    if voice_mode and not fast_voice_response:
        system_prompt += """

## 数字人口语回答模式
当前回答将由数字人直接播报。请优先使用简短、自然、可直接朗读的口语：
- 闲聊、问候或简单事实问题，默认用 1—3 句回答，不列清单。
- 一般讲解先给核心结论，整体尽量控制在 120 个中文字以内。
- 只有用户明确要求详细讲解、分步骤、代码或完整方案时，才扩展长度。
- 涉及定义、性质、公式、复杂度和算法步骤时必须保证事实准确；禁止为了简短而省略关键条件、编造公式或给出错误范围。
- 不要把旋转、着色、比较等不同操作次数合并成一个上界；具体常数或公式不确定时不要猜测。
- 即使用户要求详细讲解，也尽量控制在 600 个中文字以内；只输出一个连续自然段，不使用 Markdown 标题、表格或项目列表。
- 避免冗长开场白，不要用多套数学排版重复书写同一个复杂度。
"""
        system_prompt += _build_detailed_voice_accuracy_guard(question)

    # ── 3. 初始化消息和事件收集 ──
    # 组装用户消息，依次拼接附件分析结果与强制搜索上下文
    human_content = question
    if attachment_context:
        human_content = f"{question}\n\n[附件分析结果]\n{attachment_context}"

    if forced_context_blocks:
        human_content = f"{human_content}\n\n" + "\n\n".join(forced_context_blocks)

    # 构建完整消息列表：system + 历史 + 本轮 human
    messages = [SystemMessage(content=system_prompt), *history, HumanMessage(content=human_content)]

    # ── 4. ReAct 循环（最多 8 轮：LLM → 工具 / 回答）──
    max_iterations = 8
    iteration = 0

    tool_model = (
        llm.model.bind_tools(tool_excute.get_tools_description())
        if tools and not fast_voice_response
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

            # The lightweight voice prompt deliberately asks for plain public
            # text. Accept that first complete response immediately instead of
            # spending another model round repairing an internal envelope.
            if fast_voice_response and not tool_calls and not answer_body:
                if not re.search(r"</?answer\b", answer_text, re.IGNORECASE):
                    answer_body = _recover_unwrapped_answer(answer_text)
                    reasoning_summary = ""

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
                    # 已修复过仍失败 → 回收可公开内容，不能让整轮回答中断
                    if format_repair_used:
                        answer_body = _recover_unwrapped_answer(answer_text)
                        if not answer_body:
                            answer_body = "我已经整理好这个问题的核心内容，请查看下面的图解。"
                        needs_format_repair = False
                        logger.warning(
                            "[react_node] answer envelope repair failed; recovered public response"
                        )

                    # 首次触发：将本轮响应与修复提示追加到消息列表并重试
                    if needs_format_repair:
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

                if voice_mode and diagram_required:
                    condensed_answer = condense_voice_diagram_answer(answer_body)
                    if condensed_answer != answer_body:
                        logger.info(
                            "[react_node] condensed voice diagram answer: %d -> %d chars",
                            len(answer_body),
                            len(condensed_answer),
                        )
                    answer_body = condensed_answer

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

                # generate_teaching_diagram is terminal: validate and break
                if tool_name == GENERATE_TEACHING_DIAGRAM_TOOL_NAME:
                    raw_payload = result.result_payload
                    if raw_payload is not None:
                        validated, diagram_error = validate_diagram_json(raw_payload)
                        if validated is not None:
                            node_diagram_result = validated
                            # Break outer ReAct loop — no further LLM rounds.
                            break
                        else:
                            raise RuntimeError(
                                f"diagram generation failed validation: {diagram_error}"
                            )
                    else:
                        raise RuntimeError("diagram generation returned no payload")

                # 将工具返回文本封装为 ToolMessage 加入上下文
                tool_result_text = str((result.invocation or {}).get("result_text", "") or "")
                messages.append(ToolMessage(content=tool_result_text, tool_call_id=tool_call_id))

            # 单个工具执行失败则记录错误并回灌失败消息，避免中断循环
            except Exception as exc:
                logger.warning("[react_node] 工具 %s 失败: %s", tool_name, exc)
                node_errors.append(f"{tool_name}: {exc}")
                messages.append(ToolMessage(content=f"工具调用失败: {exc}", tool_call_id=tool_call_id))

        # If diagram tool was called and validated, break the outer ReAct loop.
        if node_diagram_result is not None:
            if voice_mode and diagram_required:
                condensed_answer = condense_voice_diagram_answer(full_answer or question)
                full_answer = condensed_answer
            break

    if diagram_required and node_diagram_result is None and full_answer.strip():
        node_diagram_result = build_deterministic_fallback_diagram(question, full_answer)
        if node_diagram_result is not None:
            logger.warning(
                "[react_node] model omitted a usable diagram; generated deterministic fallback"
            )

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
