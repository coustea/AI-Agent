# -*- coding: utf-8 -*-
"""TutorAgent: 轻量级教育场景编排器。

当前工作流：
    START -> classify
      ├─ direct_answer -> END
      └─ attachment_answer -> END

职责：
- 接收请求
- 识别问题应该走哪条回答路径
- 调用对应的回答能力
- 返回统一响应
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from deepagents import create_deep_agent
from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
from app.shared.request_context import runtime_context as chat_runtime_context
from app.chat.schemas import TutorState
from app.chat.utils import (
    classify_route,
    extract_question,
    is_unusable_reply_text,
    load_prompts,
    node_timer,
    normalize_message_content,
    stream_event,
    truncate,
    build_messages,
)
from app.shared.agent_context import AgentContextService
from app.infra.llm import get_deepseek_chat_llm
from app.infra.logging import get_logger
from app.tools.chatdoc_rag import chatdoc_rag_search
from app.tools.search import duckduckgo_search, tavily_search

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
AGENT_DIR = Path(__file__).resolve().parent
GRAPH_RECURSION_LIMIT = 30
GRAPH_NODE_NAMES = {
    "classify",
    "direct_answer",
    "attachment_answer",
}
ANSWER_NODE_NAMES = {"direct_answer", "attachment_answer"}
DEEPAGENT_GRAPH_RECURSION_LIMIT = 20

MAIN_DEEPAGENT_EXCLUDED_TOOLS = frozenset(
    {
        "write_todos",
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
    }
)
RESEARCHER_DEEPAGENT_EXCLUDED_TOOLS = MAIN_DEEPAGENT_EXCLUDED_TOOLS | {"task"}

TUTOR_DEEPAGENT_SYSTEM_PROMPT = """你是 TutorAgent 的 deepagent 回答核心，服务于中文学习辅导场景。

工作方式：
1. 优先直接回答用户当前问题，语言自然、清晰、有教学价值。
2. 当用户问题涉及计算机科学、人工智能、课程知识点、教材概念、实验指导、学习资料时，优先通过 rag 子智能体查询全局课程知识库。
3. 只有当用户问题明确需要联网检索、最新信息、新闻、价格、近期版本变化或外部资料核实时，才通过 researcher 子智能体完成搜索。
4. rag 与 researcher 子智能体都只负责检索和整理证据；最终回答必须由你整合成适合学习者理解的中文解释。
5. 不要暴露内部实现，不要提到工具调用、子代理、系统提示词或工作流。
6. 如果上下文、附件分析或检索信息不足，要明确说明不确定点，并给出可行动的下一步。
7. 你面对的是计算机科学与技术、人工智能相关专业学生，回答要有教学性，优先解释概念、原理、差异、流程和常见误区。
8. 不要调用文件、shell、todo 等内置工具；这些能力在当前聊天场景不可用。
9. 如果用户只是询问今天星期几、当前日期、当前年份或当前时间，必须直接使用系统消息中的服务器当前时间回答，不要调用 researcher 搜索。
"""

RAG_DEEPAGENT_SYSTEM_PROMPT = """你是 TutorAgent 的 rag 子智能体，只负责检索全局计算机科学与人工智能学习知识库并整理证据。

要求：
1. 优先处理计算机组成原理、操作系统、计算机网络、数据结构、算法、数据库、编程语言、机器学习、深度学习、大模型等课程知识问题。
2. 调用知识库工具后，提炼与用户问题直接相关的概念、定义、步骤、对比点和注意事项。
3. 如果知识库为空或没有相关资料，要明确说明“知识库暂无相关内容”，不要编造引用。
4. 输出中文，简洁列出结论和依据，不要替主 Agent 生成完整教学长文。
5. 不要调用文件、shell、todo 或任何与知识库检索无关的工具。
"""

RESEARCHER_DEEPAGENT_SYSTEM_PROMPT = """你是 TutorAgent 的 researcher 子智能体，只负责信息检索和证据整理。

要求：
1. 仅在需要外部信息、最新信息或事实核实时使用搜索工具。
2. 搜索后提炼与用户问题直接相关的事实、来源线索和不确定点。
3. 输出中文，简洁列出结论、依据和注意事项。
4. 不要生成教学长文，不要替主 Agent 完成最终辅导回答。
5. 不要调用文件、shell、todo 或其他与搜索无关的内置工具。
"""

# ---------------------------------------------------------------------------
# Prompt 加载
# ---------------------------------------------------------------------------
PROMPTS: dict[str, str] = load_prompts(AGENT_DIR)
WEEKDAY_CN = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
CURRENT_TIME_KEYWORDS = (
    "今天星期几",
    "今天周几",
    "今天礼拜几",
    "现在星期几",
    "现在周几",
    "现在礼拜几",
    "今天几号",
    "今天日期",
    "当前日期",
    "现在日期",
    "今天是什么日期",
    "今天是什么日子",
    "今天是哪天",
    "现在几点",
    "当前时间",
    "现在时间",
    "今天几几年",
    "今年几几年",
    "今年是哪年",
    "当前年份",
    "现在是哪一年",
)
CURRENT_TIME_REQUIRED_TERMS = (
    "星期",
    "周几",
    "礼拜",
    "几号",
    "日期",
    "几点",
    "时间",
    "年份",
    "哪一年",
    "几几年",
)
CURRENT_TIME_CONTEXT_TERMS = ("今天", "现在", "当前", "今年")
EXTERNAL_REALTIME_KEYWORDS = (
    "天气",
    "气温",
    "温度",
    "下雨",
    "降雨",
    "下雪",
    "空气质量",
    "aqi",
    "湿度",
    "风力",
    "预报",
    "台风",
    "紫外线",
)


def _build_current_time_context(now: datetime | None = None) -> str:
    """构建供 Agent 直接回答当前日期/星期问题的时间上下文。"""
    current = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    return (
        "\n\n## 【服务器当前时间】\n"
        f"{current.strftime('%Y-%m-%d %H:%M:%S')} Asia/Shanghai，{WEEKDAY_CN[current.weekday()]}。\n"
        "用户询问今天星期几、当前日期、当前年份或当前时间时，直接依据本节回答，不要联网搜索。\n"
    )


def _compact_question_text(question: str) -> str:
    """压缩常见空白和标点，便于识别极窄的当前时间快答意图。"""
    removable = " \t\r\n，。！？；：,.!?;:、"
    return "".join(ch for ch in question.lower() if ch not in removable)


def _is_current_time_question(question: str) -> bool:
    """判断是否是只需要服务器时间即可回答的日期/星期/时间问题。"""
    text = _compact_question_text(question)
    if not text:
        return False

    if any(keyword in text for keyword in EXTERNAL_REALTIME_KEYWORDS):
        return False

    if any(keyword in text for keyword in CURRENT_TIME_KEYWORDS):
        return True

    has_context = any(term in text for term in CURRENT_TIME_CONTEXT_TERMS)
    has_time_term = any(term in text for term in CURRENT_TIME_REQUIRED_TERMS)
    return has_context and has_time_term


def _answer_current_time_question(question: str, now: datetime | None = None) -> str:
    """用服务器时间直接回答日期/星期问题，避免模型误触发联网搜索。"""
    current = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    weekday = WEEKDAY_CN[current.weekday()]
    text = _compact_question_text(question)

    if "星期" in text or "周几" in text or "礼拜" in text:
        return (
            f"今天是 {current.year}年{current.month}月{current.day}日，"
            f"{weekday}。"
        )

    if "几点" in text or "时间" in text:
        return (
            f"现在是 {current.year}年{current.month}月{current.day}日 "
            f"{current.strftime('%H:%M:%S')}（Asia/Shanghai），{weekday}。"
        )

    if "年份" in text or "哪一年" in text or "几几年" in text:
        return f"今年是 {current.year} 年。"

    return f"今天是 {current.year}年{current.month}月{current.day}日，{weekday}。"


class TutorAgent:
    """智能辅导 Agent — 轻量级编排器。

    两种对话路径：
    1. direct_answer — 纯文本对话，无需工具
    2. attachment_answer — 图片/文档分析后回答

    知识库检索与联网搜索由主 deepagent 自主委托子智能体完成，
    不再作为外层图节点参与路由。
    """

    _shared_instance: "TutorAgent | None" = None

    def __init__(self) -> None:
        # LLM 实例
        self.llm = get_deepseek_chat_llm(temperature=0.7, streaming=True)
        self.research_llm = get_deepseek_chat_llm(
            temperature=0.2,
            streaming=False,
            max_tokens=1200,
        )
        # 上下文服务
        self.ctx_service = AgentContextService(module_name="mentor")

        # 图与工具
        self.graph = None
        self.deep_agent = None
        self._init_lock = asyncio.Lock()
        self._deep_agent_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()

        logger.info("[TutorAgent] 初始化完成")

    @classmethod
    def get_shared(cls) -> "TutorAgent":
        """获取全局单例。"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    def _build_researcher_subagent(self) -> dict[str, Any]:
        """构建本地 researcher 子 deepagent。"""
        researcher_agent = create_deep_agent(
            model=self.research_llm,
            tools=[duckduckgo_search, tavily_search],
            subagents=[],
            system_prompt=RESEARCHER_DEEPAGENT_SYSTEM_PROMPT,
            middleware=[
                _ToolExclusionMiddleware(excluded=RESEARCHER_DEEPAGENT_EXCLUDED_TOOLS)
            ],
        )

        return {
            "name": "researcher",
            "description": (
                "用于联网搜索、最新信息核验、资料检索和证据整理的研究子智能体。"
                "当用户问题涉及最新、最近、新闻、价格、外部资料或需要事实核实时使用。"
            ),
            "runnable": researcher_agent,
        }

    def _build_rag_subagent(self) -> dict[str, Any]:
        """构建本地 rag 子 deepagent。"""
        rag_agent = create_deep_agent(
            model=self.research_llm,
            tools=[chatdoc_rag_search],
            subagents=[],
            system_prompt=RAG_DEEPAGENT_SYSTEM_PROMPT,
            middleware=[
                _ToolExclusionMiddleware(excluded=RESEARCHER_DEEPAGENT_EXCLUDED_TOOLS)
            ],
        )

        return {
            "name": "rag",
            "description": (
                "用于检索全局计算机科学与人工智能课程知识库的子智能体。"
                "当用户询问课程概念、教材知识点、实验指导、学习资料时优先使用。"
            ),
            "runnable": rag_agent,
        }

    def _build_deep_agent(self) -> Any:
        """构建 Tutor 主 deepagent，并把知识库检索/联网搜索隔离到本地子智能体。"""
        rag_subagent = self._build_rag_subagent()
        researcher_subagent = self._build_researcher_subagent()

        return create_deep_agent(
            model=self.llm,
            tools=[],
            subagents=[rag_subagent, researcher_subagent],
            system_prompt=TUTOR_DEEPAGENT_SYSTEM_PROMPT,
            middleware=[_ToolExclusionMiddleware(excluded=MAIN_DEEPAGENT_EXCLUDED_TOOLS)],
        )

    async def _ensure_deep_agent(self) -> Any:
        """懒加载 deepagent，确保搜索子代理拿到最新工具实例。"""
        if self.deep_agent is not None:
            return self.deep_agent

        async with self._deep_agent_lock:
            if self.deep_agent is not None:
                return self.deep_agent
            self.deep_agent = self._build_deep_agent()
            logger.info("[TutorAgent] deepagent 构建完成，知识库检索与联网搜索已拆分为本地子智能体")
            return self.deep_agent

    # ------------------------------------------------------------------
    # 图构建
    # ------------------------------------------------------------------
    async def _ensure_graph(self) -> None:
        """构建 LangGraph 状态图。"""
        if self.graph is not None:
            return

        async with self._init_lock:
            if self.graph is not None:
                return

            logger.info("[TutorAgent] 图构建开始")
            await self._ensure_deep_agent()

            graph = StateGraph(TutorState)
            graph.add_node("classify", self._classify_node)
            graph.add_node("direct_answer", self._direct_answer_node)
            graph.add_node("attachment_answer", self._attachment_answer_node)

            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "direct_answer",
                    "attachment_needed": "attachment_answer",
                },
            )
            graph.add_edge("direct_answer", END)
            graph.add_edge("attachment_answer", END)

            self.graph = graph.compile()
            logger.info("[TutorAgent] 图构建完成")

    # ------------------------------------------------------------------
    # 节点: classify
    # ------------------------------------------------------------------
    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：仅区分 direct / attachment_needed。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        resource_mode = state.get("resource_mode", "none")
        user_message = extract_question(messages)

        with node_timer("classify", user=user_id, session=session_id):
            # 快速路径1：附件优先
            if file_urls or image_urls:
                logger.info(
                    "[TutorAgent] 路由分类 route=attachment_needed reason=attachments_present images=%s files=%s resource_mode=%s",
                    len(image_urls),
                    len(file_urls),
                    resource_mode,
                )
                return {"route": "attachment_needed", "execution_mode": "attachment"}

            logger.info(
                "[TutorAgent] 路由分类 route=direct reason=no_attachments resource_mode=%s question=%s",
                resource_mode,
                truncate(user_message, 120),
            )
            return {"route": "direct", "execution_mode": "direct"}

    # ------------------------------------------------------------------
    # 回答执行公共方法
    # ------------------------------------------------------------------
    async def _run_answer_model(
        self,
        *,
        state: TutorState,
        stage_name: str,
        prompt_messages: list[Any],
        extra_log: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """统一执行回答模型，包含无效回复兜底。"""
        extra_log = extra_log or {}
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        system_prompt = state.get("system_prompt", "")

        with node_timer(stage_name, user=user_id, session=session_id, **extra_log):
            full_messages = build_messages(system_prompt, prompt_messages)
            agent = await self._ensure_deep_agent()
            agent_result = await agent.ainvoke(
                {"messages": full_messages},
                config={
                    "recursion_limit": DEEPAGENT_GRAPH_RECURSION_LIMIT,
                    "configurable": {
                        "thread_id": f"tutor:{user_id}:{session_id}:{stage_name}",
                    },
                },
            )
            agent_messages = agent_result.get("messages", []) if isinstance(agent_result, dict) else []
            response = next(
                (msg for msg in reversed(agent_messages) if isinstance(msg, AIMessage)),
                None,
            )
            text = normalize_message_content(response.content if response else "")

            if is_unusable_reply_text(text):
                logger.warning("[TutorAgent] %s 重试 原因=无效回复", stage_name)
                retry_messages = (agent_messages or full_messages) + [
                    HumanMessage(
                        content="你上一条回复无效或过短。请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。"
                    )
                ]
                retry_result = await agent.ainvoke(
                    {"messages": retry_messages},
                    config={
                        "recursion_limit": DEEPAGENT_GRAPH_RECURSION_LIMIT,
                        "configurable": {
                            "thread_id": f"tutor:{user_id}:{session_id}:{stage_name}:retry",
                        },
                    },
                )
                retry_messages_result = (
                    retry_result.get("messages", []) if isinstance(retry_result, dict) else []
                )
                retry_resp = next(
                    (msg for msg in reversed(retry_messages_result) if isinstance(msg, AIMessage)),
                    None,
                )
                retry_text = normalize_message_content(retry_resp.content if retry_resp else "")
                if not is_unusable_reply_text(retry_text):
                    response = retry_resp
                    text = retry_text

            if response is None:
                response = AIMessage(content=text)

            logger.info("[TutorAgent] %s 完成 preview=%s", stage_name, truncate(text, 220))
            return {
                "messages": [response],
                "answer_text": text,
                "termination_reason": f"{stage_name}_done",
            }

    # ------------------------------------------------------------------
    # 节点: direct_answer
    # ------------------------------------------------------------------
    async def _direct_answer_node(self, state: TutorState) -> dict[str, Any]:
        """直接回答路径：纯文本对话，不调用工具。"""
        messages = state.get("messages") or []
        question = extract_question(messages)
        logger.info("[TutorAgent] 直接回答 route=direct_answer question=%s", truncate(question, 180))
        if _is_current_time_question(question):
            text = _answer_current_time_question(question)
            logger.info("[TutorAgent] 服务器时间快答 question=%s answer=%s", truncate(question, 120), text)
            return {
                "messages": [AIMessage(content=text)],
                "answer_text": text,
                "termination_reason": "direct_answer_done",
            }

        return await self._run_answer_model(
            state=state,
            stage_name="direct_answer",
            prompt_messages=list(messages),
            extra_log={"route": "direct_answer"},
        )

    # ------------------------------------------------------------------
    # 节点: attachment_answer
    # ------------------------------------------------------------------
    async def _attachment_answer_node(self, state: TutorState) -> dict[str, Any]:
        """附件理解路径：消费上传阶段完成的图片/文档预分析后回答。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        messages = list(state.get("messages") or [])
        question = extract_question(messages)
        pre_analysis = state.get("attachment_analysis") or {}

        with node_timer(
            "attachment_answer",
            user=user_id,
            session=session_id,
            image_count=len(image_urls),
            file_count=len(file_urls),
        ):
            logger.info(
                "[TutorAgent] 附件回答 route=attachment_answer question=%s images=%s files=%s",
                truncate(question, 180),
                len(image_urls),
                len(file_urls),
            )

            full_context = str(state.get("attachment_analysis_context", "")).strip()
            if not full_context and isinstance(pre_analysis, dict):
                full_context = str(pre_analysis.get("analysis_context", "")).strip()

            if not full_context:
                full_context = (
                    "本轮包含附件，但上传阶段未返回可用的附件预分析结果。"
                    "请基于用户问题说明目前无法可靠读取附件内容，并建议用户重新上传或稍后重试。"
                )

            answer_prompt = (
                f"用户问题: {question}\n\n"
                f"以下是上传阶段已经完成的附件预分析内容：\n{full_context}\n\n"
                "请只根据这些预分析内容和已有对话回答用户问题，不要尝试读取附件、调用文件工具或重新分析图片。"
                "如果内容不足以回答问题，请明确说明缺失点；"
                "回答要清晰、分点、适合教学场景。"
            )

            result = await self._run_answer_model(
                state=state,
                stage_name="attachment_answer",
                prompt_messages=[HumanMessage(content=answer_prompt)],
                extra_log={"route": "attachment_answer"},
            )
            result["attachment_analysis_result"] = {
                "mode": "upload_preanalysis",
                "analysis_context": full_context,
            }
            return result

    # ------------------------------------------------------------------
    # 后台任务
    # ------------------------------------------------------------------
    def _spawn_background(self, coro: Any, *, task_name: str) -> None:
        """安全启动后台任务。"""
        task = asyncio.create_task(coro, name=task_name)
        self._background_tasks.add(task)

        def _done_callback(done_task: asyncio.Task) -> None:
            self._background_tasks.discard(done_task)
            if done_task.cancelled():
                return
            try:
                done_task.result()
            except Exception:
                logger.exception("[TutorAgent] 后台任务异常 task=%s", task_name)

        task.add_done_callback(_done_callback)

    # ------------------------------------------------------------------
    # 主入口：SSE 流式对话
    # ------------------------------------------------------------------
    async def chat_stream(
        self,
        user_id: int,
        user_message: str,
        session_id: Optional[str] = None,
        image_urls: Optional[list[str]] = None,
        file_urls: Optional[list[str]] = None,
        generate_image: bool = False,
        generate_video: bool = False,
        resource_mode: Optional[str] = None,
        attachment_analysis: Optional[dict[str, Any]] = None,
    ):
        """流式生成对话响应。"""
        effective_session = session_id or f"user-{user_id}-default-mentor"
        image_urls = image_urls or []
        file_urls = file_urls or []
        resource_requested = bool(resource_mode and resource_mode != "none") or generate_image or generate_video
        if resource_requested:
            logger.info("[TutorAgent] 当前版本仅生成文字回答，已忽略多模态资源请求")

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments(images=%s,files=%s)",
            truncate(user_message, 180),
            len(image_urls),
            len(file_urls),
        )

        await self._ensure_graph()

        # 保存用户消息
        try:
            msg_content = user_message
            if image_urls:
                msg_content += f" [Attached Images: {', '.join(image_urls)}]"
            if file_urls:
                msg_content += f" [Attached Files: {', '.join(file_urls)}]"

            attachments_json = (
                json.dumps(
                    [
                        {
                            "url": u,
                            "type": "image" if u.split(".")[-1].lower() in {"png", "jpg", "jpeg", "gif", "webp"} else "document",
                            "name": u.split("/")[-1],
                        }
                        for u in image_urls + file_urls
                    ],
                    ensure_ascii=False,
                )
                if (image_urls or file_urls)
                else None
            )

            await self.ctx_service.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="user",
                content=msg_content,
                attachments=attachments_json,
            )
        except Exception as exc:
            logger.exception("[TutorAgent] 用户消息保存失败")
            yield stream_event("error", f"保存消息失败: {exc}")
            return

        # 构建上下文
        profile_str, fact_str = await asyncio.gather(
            self.ctx_service.build_profile_ctx(user_id),
            self.ctx_service.build_memory_ctx(user_id),
        )
        file_info_str = self.ctx_service.build_file_ctx(image_urls, file_urls)
        attachment_analysis_context = str((attachment_analysis or {}).get("analysis_context", "")).strip()
        initial_messages, recent_chat_context = await self.ctx_service.build_chat_ctx(
            user_id,
            effective_session,
            user_message,
            image_urls,
            file_urls,
        )

        analysis_hint = (
            f"\n\n### 附件并行预分析结果\n{attachment_analysis_context}\n"
            if attachment_analysis_context
            else ""
        )

        direct_prompt = PROMPTS["direct_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
            recent_chat_context=recent_chat_context,
        ) + _build_current_time_context() + analysis_hint

        initial_state: TutorState = {
            "user_id": user_id,
            "session_id": effective_session,
            "image_urls": image_urls,
            "file_urls": file_urls,
            "resource_mode": "none",
            "route": "",
            "execution_mode": "",
            "profile_context": profile_str,
            "fact_context": fact_str,
            "recent_chat_context": recent_chat_context,
            "file_context": file_info_str,
            "attachment_analysis_context": attachment_analysis_context,
            "attachment_analysis": attachment_analysis or {},
            "system_prompt": direct_prompt,
            "messages": initial_messages,
            "answer_text": "",
            "retrieved_docs": [],
            "termination_reason": "",
        }

        full_reply = ""
        runtime_state: dict[str, Any] = dict(initial_state)
        graph_error_text = ""
        active_node = ""

        try:
            with chat_runtime_context(user_id, effective_session):
                async for event in self.graph.astream_events(
                    initial_state,
                    version="v2",
                    config={"recursion_limit": GRAPH_RECURSION_LIMIT},
                ):
                    kind = event.get("event", "")
                    name = event.get("name", "")

                    if kind == "on_chain_start" and name in GRAPH_NODE_NAMES:
                        active_node = name
                        if name in ANSWER_NODE_NAMES:
                            yield stream_event(
                                "status",
                                {
                                    "stage": name,
                                    "message": "正在检索和组织答案，请稍候...",
                                },
                            )

                    if kind == "on_chain_end" and name in GRAPH_NODE_NAMES:
                        active_node = ""
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            for key, value in node_output.items():
                                if key == "messages" and isinstance(value, list):
                                    runtime_state[key] = list(runtime_state.get(key, [])) + value
                                else:
                                    runtime_state[key] = value

                    if kind == "on_chain_end" and name in ANSWER_NODE_NAMES:
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
                                    full_reply = final_text
                                    yield stream_event("token", final_text)

        except Exception as exc:
            logger.exception("[TutorAgent] 请求异常")
            graph_error_text = f"服务器出错: {exc}"

        logger.info(
            "[TutorAgent] 请求结束 termination_reason=%s",
            runtime_state.get("termination_reason", ""),
        )

        if graph_error_text:
            yield stream_event("error", graph_error_text)
            return

        if not full_reply:
            messages = runtime_state.get("messages", [])
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        full_reply = normalize_message_content(msg.content)
                        break

        if is_unusable_reply_text(full_reply):
            yield stream_event("error", "模型未返回有效内容，请重试。")
            return

        # 保存回复
        try:
            await self.ctx_service.save_message(
                user_id=user_id,
                session_id=effective_session,
                role="assistant",
                content=full_reply,
            )

            self._spawn_background(
                self.ctx_service.post_chat_pipeline(
                    user_id=user_id,
                    session_id=effective_session,
                    user_message=user_message,
                    assistant_reply=full_reply,
                ),
                task_name="post_chat_pipeline",
            )
        except Exception as exc:
            logger.exception("[TutorAgent] 回复保存失败")
            yield stream_event("error", f"保存回复失败: {exc}")
            return

        yield stream_event(
            "done",
            {
                "session_id": effective_session,
                "resource_mode": "none",
                "resource": None,
            },
        )
