# -*- coding: utf-8 -*-
"""TutorAgent: 轻量级教育场景编排器。

简化后的工作流：
    START -> classify
      ├─ direct_answer -> generate_resource -> END
      ├─ attachment_answer -> generate_resource -> END
      └─ search_answer -> generate_resource -> END

职责：
- 接收请求
- 识别问题应该走哪条回答路径
- 调用对应的回答能力
- 在回答完成后根据前端标志决定是否生成资源
- 返回统一响应
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

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
from app.shared.vision import build_vision_service
from app.shared.agent_context import AgentContextService
from app.infra.llm import (
    get_deepseek_chat_llm,
    get_deepseek_llm,
    get_glm_vision_llm,
    get_spark_x_llm,
)
from app.infra.logging import get_logger
from app.tools import registry

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
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
    "search_answer",
    "generate_resource",
}
ANSWER_NODE_NAMES = {"direct_answer", "attachment_answer", "search_answer"}
RESOURCE_MODES = {"none", "image", "video"}

# 搜索触发关键词（仅作为弱信号）
SEARCH_KEYWORDS = (
    "搜索", "搜一下", "查一下", "查找", "检索", "帮我找",
    "最新", "最近", "新闻", "今年", "今天", "价格",
)

# ---------------------------------------------------------------------------
# Prompt 加载
# ---------------------------------------------------------------------------
PROMPTS: dict[str, str] = load_prompts(AGENT_DIR)


class ImageGenerationPlanSchema(BaseModel):
    """图片生成计划结构。"""

    title: str = ""
    visual_goal: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    style: str = ""
    aspect_ratio: str = "16:9"
    key_elements: list[str] = Field(default_factory=list)
    safety_notes: str = ""


class VideoSceneSchema(BaseModel):
    """视频场景结构。"""

    scene_id: int = 1
    shot: str = ""
    duration_sec: int = 4
    description: str = ""


class VideoGenerationPlanSchema(BaseModel):
    """视频生成计划结构。"""

    title: str = ""
    visual_goal: str = ""
    positive_prompt: str = ""
    negative_prompt: str = ""
    style: str = ""
    aspect_ratio: str = "16:9"
    total_duration_sec: int = 12
    scenes: list[VideoSceneSchema] = Field(default_factory=list)
    audio_notes: str = ""
    safety_notes: str = ""


class TutorAgent:
    """智能辅导 Agent — 轻量级编排器。

    三种对话路径：
    1. direct_answer — 纯文本对话，无需工具
    2. attachment_answer — 图片/文档分析后回答
    3. search_answer — 检索增强后回答
    """

    _shared_instance: "TutorAgent | None" = None

    def __init__(self) -> None:
        # LLM 实例
        self.llm = get_spark_x_llm(temperature=1.0, streaming=True)
        self.classifier_llm = get_deepseek_chat_llm(
            temperature=0.0,
            streaming=False,
            max_tokens=100,
        )
        self.image_plan_llm = get_deepseek_chat_llm(
            temperature=0.1,
            streaming=False,
            max_tokens=900,
        ).with_structured_output(ImageGenerationPlanSchema)
        self.video_plan_llm = get_deepseek_llm(
            temperature=0.1,
            streaming=False,
            max_tokens=1200,
        ).with_structured_output(VideoGenerationPlanSchema)

        # 视觉模型
        self.glm_vision_llm = get_glm_vision_llm()
        self.vision_service = build_vision_service(self.glm_vision_llm)

        # 上下文服务
        self.ctx_service = AgentContextService(module_name="mentor")

        # 图与工具
        self.graph = None
        self._init_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()

        # 搜索工具
        self._search_tool: BaseTool | None = None
        self._document_tool: BaseTool | None = None
        self._tool_lock = asyncio.Lock()

        logger.info("[TutorAgent] 初始化完成")

    @classmethod
    def get_shared(cls) -> "TutorAgent":
        """获取全局单例。"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    # ------------------------------------------------------------------
    # 工具加载与资源模式
    # ------------------------------------------------------------------
    @staticmethod
    def normalize_resource_mode(
        *,
        resource_mode: Optional[str] = None,
        generate_image: bool = False,
        generate_video: bool = False,
    ) -> Literal["none", "image", "video"]:
        """将旧布尔开关统一归一化为单一 resource_mode。"""
        if resource_mode:
            normalized = str(resource_mode).strip().lower()
            if normalized in RESOURCE_MODES:
                return normalized  # type: ignore[return-value]

        if generate_image and generate_video:
            logger.warning("[TutorAgent] 检测到互斥资源请求冲突，按 image 优先处理")
            return "image"
        if generate_image:
            return "image"
        if generate_video:
            return "video"
        return "none"

    async def _ensure_tools(self) -> None:
        """确保搜索/文档工具可用。"""
        if self._search_tool is not None and self._document_tool is not None:
            return

        async with self._tool_lock:
            registry.ensure_loaded()

            if self._search_tool is None:
                try:
                    self._search_tool = registry.get("duckduckgo_search")
                    logger.info("[TutorAgent] 搜索工具加载完成")
                except Exception:
                    logger.exception("[TutorAgent] 搜索工具加载失败")
                    self._search_tool = None

            if self._document_tool is None:
                try:
                    self._document_tool = registry.get("read_uploaded_file")
                    logger.info("[TutorAgent] 文档读取工具加载完成")
                except Exception:
                    logger.exception("[TutorAgent] 文档读取工具加载失败")
                    self._document_tool = None

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
            await self._ensure_tools()

            graph = StateGraph(TutorState)
            graph.add_node("classify", self._classify_node)
            graph.add_node("direct_answer", self._direct_answer_node)
            graph.add_node("attachment_answer", self._attachment_answer_node)
            graph.add_node("search_answer", self._search_answer_node)
            graph.add_node("generate_resource", self._generate_resource_node)

            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                classify_route,
                {
                    "direct": "direct_answer",
                    "attachment_needed": "attachment_answer",
                    "search_needed": "search_answer",
                },
            )
            graph.add_edge("direct_answer", "generate_resource")
            graph.add_edge("attachment_answer", "generate_resource")
            graph.add_edge("search_answer", "generate_resource")
            graph.add_edge("generate_resource", END)

            self.graph = graph.compile()
            logger.info("[TutorAgent] 图构建完成")

    # ------------------------------------------------------------------
    # 节点: classify
    # ------------------------------------------------------------------
    async def _classify_node(self, state: TutorState) -> dict[str, Any]:
        """分类节点：direct / attachment_needed / search_needed。"""
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

            # 快速路径2：搜索关键词作为弱信号
            if any(kw in user_message for kw in SEARCH_KEYWORDS):
                logger.info(
                    "[TutorAgent] 路由分类 route=search_needed reason=search_keywords resource_mode=%s question=%s",
                    resource_mode,
                    truncate(user_message, 120),
                )
                return {"route": "search_needed", "execution_mode": "search"}

            # 慢速路径：LLM 分类
            classify_prompt = PROMPTS["classifier"].format(
                user_message=user_message[:800],
                has_attachments="无附件",
            )

            try:
                response = await self.classifier_llm.ainvoke([HumanMessage(content=classify_prompt)])
                raw = normalize_message_content(response.content).strip().lower()

                if "search" in raw or "tool" in raw or "rag" in raw:
                    route = "search_needed"
                    execution_mode = "search"
                else:
                    route = "direct"
                    execution_mode = "direct"

                logger.info(
                    "[TutorAgent] 路由分类 route=%s reason=llm_classifier resource_mode=%s question=%s",
                    route,
                    resource_mode,
                    truncate(user_message, 120),
                )
                return {"route": route, "execution_mode": execution_mode}

            except Exception:
                logger.exception("[TutorAgent] 路由分类回退=direct")
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
            response = await self.llm.ainvoke(full_messages)
            text = normalize_message_content(response.content)

            if is_unusable_reply_text(text):
                logger.warning("[TutorAgent] %s 重试 原因=无效回复", stage_name)
                retry_messages = full_messages + [
                    HumanMessage(
                        content="你上一条回复无效或过短。请重新回答用户问题，给出完整、可读、适合教学场景的中文回答。"
                    )
                ]
                retry_resp = await self.llm.ainvoke(retry_messages)
                retry_text = normalize_message_content(retry_resp.content)
                if not is_unusable_reply_text(retry_text):
                    response = retry_resp
                    text = retry_text

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
        """附件理解路径：并行处理图片和文档后回答。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []
        messages = list(state.get("messages") or [])
        question = extract_question(messages)

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

            context_parts: list[str] = []

            async def analyze_images() -> str:
                if not image_urls:
                    return ""
                pre_analysis = state.get("attachment_analysis") or {}
                pre_image = pre_analysis.get("image") if isinstance(pre_analysis, dict) else None
                if isinstance(pre_image, dict) and str(pre_image.get("analysis_text", "")).strip():
                    logger.info("[TutorAgent] 复用图片预分析结果")
                    return str(pre_image.get("analysis_text", ""))
                try:
                    result = await self.vision_service.analyze_images(image_urls, question)
                    analysis = str(result.get("analysis_text", "")).strip()
                    logger.info("[TutorAgent] 图片分析完成 mode=%s", result.get("mode", "unknown"))
                    return analysis
                except Exception:
                    logger.exception("[TutorAgent] 图片分析失败")
                    return "[图片分析失败]"

            async def read_one_document(file_url: str) -> str:
                if self._document_tool is None:
                    logger.warning("[TutorAgent] 文档读取工具不可用")
                    return f"### 文档: {file_url}\n[读取工具不可用]"
                try:
                    result = await asyncio.wait_for(
                        self._document_tool.ainvoke({"file_url": file_url}),
                        timeout=30,
                    )
                    content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                    logger.info("[TutorAgent] 文档读取完成 url=%s", truncate(file_url, 80))
                    return f"### 文档: {file_url}\n{content}"
                except Exception:
                    logger.exception("[TutorAgent] 文档读取失败 url=%s", truncate(file_url, 80))
                    return f"### 文档: {file_url}\n[读取失败]"

            async def read_documents() -> str:
                if not file_urls:
                    return ""
                results = await asyncio.gather(*(read_one_document(url) for url in file_urls))
                return "\n\n".join(results)

            image_result, doc_result = await asyncio.gather(
                analyze_images(),
                read_documents(),
            )

            if image_result:
                context_parts.append(f"### 图片分析结果\n{image_result}")
            if doc_result:
                context_parts.append(doc_result)

            full_context = "\n\n".join(context_parts).strip()
            answer_prompt = (
                f"用户问题: {question}\n\n"
                f"以下是与问题相关的附件内容：\n{full_context}\n\n"
                "请根据以上内容回答用户问题。"
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
                "image_analysis": image_result,
                "document_analysis": doc_result,
            }
            return result

    # ------------------------------------------------------------------
    # 节点: search_answer
    # ------------------------------------------------------------------
    async def _search_answer_node(self, state: TutorState) -> dict[str, Any]:
        """搜索回答路径：检索增强后回答。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        messages = state.get("messages") or []
        question = extract_question(messages)

        with node_timer("search_answer", user=user_id, session=session_id):
            logger.info("[TutorAgent] 检索回答 route=search_answer question=%s", truncate(question, 180))

            search_context = ""
            search_docs: list[Any] = []

            if self._search_tool:
                try:
                    search_result = await asyncio.wait_for(
                        self._search_tool.ainvoke({"query": question}),
                        timeout=30,
                    )
                    if isinstance(search_result, str):
                        search_context = search_result
                    else:
                        search_context = json.dumps(search_result, ensure_ascii=False)
                        if isinstance(search_result, list):
                            search_docs = search_result
                    logger.info("[TutorAgent] 检索完成 length=%s", len(search_context))
                except Exception:
                    logger.exception("[TutorAgent] 检索失败")
                    search_context = "[检索失败，请稍后重试]"
            else:
                logger.warning("[TutorAgent] 搜索工具不可用")
                search_context = "[搜索工具不可用]"

            answer_prompt = (
                f"用户问题: {question}\n\n"
                f"检索结果：\n{search_context}\n\n"
                "请根据检索结果回答用户问题。"
                "如果检索结果不相关或不完整，请明确说明不确定之处；"
                "回答要适合教学场景，尽量讲解清楚，不要只堆砌材料。"
            )

            result = await self._run_answer_model(
                state=state,
                stage_name="search_answer",
                prompt_messages=[HumanMessage(content=answer_prompt)],
                extra_log={"route": "search_answer"},
            )
            result["retrieved_docs"] = search_docs or [search_context]
            return result

    # ------------------------------------------------------------------
    # 资源生成
    # ------------------------------------------------------------------
    def _build_resource_prompt(self, state: TutorState, *, modality: str) -> str:
        """构建多模态资源规划提示词。"""
        question = extract_question(state.get("messages") or [])
        profile_context = truncate(state.get("profile_context", ""), 600)
        fact_context = truncate(state.get("fact_context", ""), 600)
        latest_answer = truncate(state.get("answer_text", ""), 1200)

        if not latest_answer:
            messages = state.get("messages") or []
            if isinstance(messages, list):
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        latest_answer = truncate(normalize_message_content(msg.content), 1200)
                        break

        return (
            f"你是多模态学习资源规划器，请基于上下文生成{modality}创作指令。\n"
            "要求：不得脱离上下文，不得凭空创作与用户问题无关内容。\n"
            f"用户问题: {question}\n"
            f"主回答摘要: {latest_answer}\n"
            f"用户画像: {profile_context}\n"
            f"用户记忆: {fact_context}\n"
        )

    async def _generate_resource_node(self, state: TutorState) -> dict[str, Any]:
        """统一资源生成规划节点。"""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        resource_mode = str(state.get("resource_mode", "none")).lower()

        with node_timer("generate_resource", user=user_id, session=session_id, resource_mode=resource_mode):
            if resource_mode == "none":
                logger.info("[TutorAgent] 跳过资源生成 reason=no_resource_requested")
                return {
                    "generated_resource": None,
                    "resource_generation_status": "skipped",
                    "termination_reason": state.get("termination_reason") or "answer_done",
                }

            if resource_mode == "image":
                prompt = self._build_resource_prompt(state, modality="图片图解")
                try:
                    generation_plan = await self.image_plan_llm.ainvoke([HumanMessage(content=prompt)])
                    if isinstance(generation_plan, ImageGenerationPlanSchema):
                        generation_plan = generation_plan.model_dump()
                    logger.info("[TutorAgent] 图解资源规划完成 plan=%s", truncate(generation_plan, 500))
                    return {
                        "generated_resource": {
                            "type": "image",
                            "status": "planned",
                            "prompt": prompt,
                            "plan": generation_plan,
                        },
                        "resource_generation_status": "done",
                        "termination_reason": "resource_planned",
                    }
                except Exception:
                    logger.exception("[TutorAgent] 图解资源规划失败")
                    return {
                        "generated_resource": {
                            "type": "image",
                            "status": "error",
                            "prompt": prompt,
                            "plan": {"title": "图片生成计划(降级)", "positive_prompt": prompt},
                        },
                        "resource_generation_status": "error",
                        "termination_reason": "resource_plan_failed",
                    }

            if resource_mode == "video":
                prompt = self._build_resource_prompt(state, modality="讲解视频")
                try:
                    generation_plan = await self.video_plan_llm.ainvoke([HumanMessage(content=prompt)])
                    if isinstance(generation_plan, VideoGenerationPlanSchema):
                        generation_plan = generation_plan.model_dump()
                    logger.info("[TutorAgent] 视频资源规划完成 plan=%s", truncate(generation_plan, 500))
                    return {
                        "generated_resource": {
                            "type": "video",
                            "status": "planned",
                            "prompt": prompt,
                            "plan": generation_plan,
                        },
                        "resource_generation_status": "done",
                        "termination_reason": "resource_planned",
                    }
                except Exception:
                    logger.exception("[TutorAgent] 视频资源规划失败")
                    return {
                        "generated_resource": {
                            "type": "video",
                            "status": "error",
                            "prompt": prompt,
                            "plan": {"title": "视频生成计划(降级)", "positive_prompt": prompt},
                        },
                        "resource_generation_status": "error",
                        "termination_reason": "resource_plan_failed",
                    }

            logger.warning("[TutorAgent] 未知 resource_mode=%s，按跳过处理", resource_mode)
            return {
                "generated_resource": None,
                "resource_generation_status": "skipped",
                "termination_reason": state.get("termination_reason") or "answer_done",
            }

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
        normalized_resource_mode = self.normalize_resource_mode(
            resource_mode=resource_mode,
            generate_image=generate_image,
            generate_video=generate_video,
        )

        logger.info(
            "[TutorAgent] 对话开始 message=%s attachments(images=%s,files=%s) resource_mode=%s",
            truncate(user_message, 180),
            len(image_urls),
            len(file_urls),
            normalized_resource_mode,
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
        ) + analysis_hint

        initial_state: TutorState = {
            "user_id": user_id,
            "session_id": effective_session,
            "image_urls": image_urls,
            "file_urls": file_urls,
            "resource_mode": normalized_resource_mode,
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
            "generated_resource": None,
            "resource_generation_status": "pending" if normalized_resource_mode != "none" else "skipped",
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

                    if kind == "on_chain_end" and name in GRAPH_NODE_NAMES:
                        active_node = ""
                        node_output = event.get("data", {}).get("output", {})
                        if isinstance(node_output, dict):
                            for key, value in node_output.items():
                                if key == "messages" and isinstance(value, list):
                                    runtime_state[key] = list(runtime_state.get(key, [])) + value
                                else:
                                    runtime_state[key] = value

                    if kind == "on_chat_model_stream" and active_node in ANSWER_NODE_NAMES:
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and chunk.content:
                            text = chunk.content if isinstance(chunk.content, str) else ""
                            if text:
                                full_reply += text
                                yield stream_event("token", text)

        except Exception as exc:
            logger.exception("[TutorAgent] 请求异常")
            graph_error_text = f"服务器出错: {exc}"

        logger.info(
            "[TutorAgent] 请求结束 termination_reason=%s resource_mode=%s resource_status=%s",
            runtime_state.get("termination_reason", ""),
            normalized_resource_mode,
            runtime_state.get("resource_generation_status", "unknown"),
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

        if runtime_state.get("generated_resource") is not None:
            yield stream_event("resource", runtime_state["generated_resource"])

        yield stream_event(
            "done",
            {
                "session_id": effective_session,
                "resource_mode": normalized_resource_mode,
                "resource": runtime_state.get("generated_resource"),
            },
        )
