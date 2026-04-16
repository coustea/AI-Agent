"""TutorAgent: orchestrates direct, multimodal, and tool-assisted mentor chat."""

import asyncio
import json
import os
from pathlib import Path
from typing import TypedDict, Optional, List, Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, AnyMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.infra.logging import get_logger
from app.profile import build_fact_agent, build_profile_agent
from app.chat.context import chat_runtime_context
from app.profile.profile_agent import PROFILE_UPDATE_TOKEN_THRESHOLD
from app.memory.service import MEMORY_EXTRACTION_TOKEN_THRESHOLD, memory_service
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

AGENT_DIR = Path(__file__).resolve().parent

MODULE_NAME = "mentor"

# 加载 Prompt
def _load_prompt() -> dict[str, str]:
    """从 prompt.md 加载三段 prompt（用 `## classifier` / `## direct_system` / `## tool_system` 分隔）。"""
    prompt_path = AGENT_DIR / "prompt.md"
    content = prompt_path.read_text(encoding="utf-8")

    sections = {"classifier": "", "direct_system": "", "tool_system": ""}
    current = None
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## classifier"):
            current = "classifier"
            continue
        elif stripped.startswith("## direct_system"):
            current = "direct_system"
            continue
        elif stripped.startswith("## tool_system"):
            current = "tool_system"
            continue
        if current:
            sections[current] += line + "\n"

    return sections


PROMPTS = _load_prompt()


class TutorState(TypedDict, total=False):
    """LangGraph 节点间共享的运行时状态。"""
    user_id: int
    session_id: str
    image_urls: Optional[List[str]]  # 用户上传的图片 URL 列表
    file_urls: Optional[List[str]]   # 用户上传的文档 URL 列表
    route: str  # 分类结果: "direct" | "tool_needed" | "vision_needed"
    system_prompt: str               # 直接回答路径的 system prompt
    tool_system_prompt: str          # 工具调用路径的 system prompt
    messages: Annotated[list[AnyMessage], add_messages]


class TutorAgent:
    """Mentor chat agent with direct, vision, and tool-capable paths."""

    def __init__(
        self,
        *,
        memory=memory_service,
        fact_agent=None,
        profile_agent=None,
    ) -> None:
        # 主模型：负责对话生成与工具调用，支持流式输出
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.7,
            streaming=True,
        )
        # 分类模型：轻量快速，用于判断用户意图走哪条路由
        self.classifier_llm = ChatOpenAI(
            model=os.getenv("FAST_LLM_MODEL", "general"),
            api_key=os.getenv("FAST_LLM_API_KEY", os.getenv("OPENAI_API_KEY")),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.0,
            max_tokens=100,
        )
        # GLM 图片理解模型

        self.glm_vision_llm = ChatOpenAI(
            model=os.getenv("GLM_VISION_MODEL", "glm-4v-flash"),
            api_key=os.getenv("GLM_API_KEY"),
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            temperature=0.7,
        )
        self.module_name = MODULE_NAME
        self.memory = memory
        self.fact_agent = fact_agent or build_fact_agent()
        self.profile_agent = profile_agent or build_profile_agent()
        self.graph = None
        self._tools: list[BaseTool] = []
        self._init_lock = asyncio.Lock()
        self._background_tasks: set[asyncio.Task] = set()

        # Chat agent 的工具和技能声明
        self.tool_names = [
            "create_document_file",
            "read_uploaded_file", "list_uploaded_files",
            "save_to_workplace", "read_file_safe",
            "write_file", "edit_file", "append_file", "read_file_lines",
        ]
        self.skill_names = ["baidu-search", "docx", "pdf"]

    @staticmethod
    def _looks_like_external_lookup_request(user_msg: str) -> bool:
        """Detect search/fetch style requests that benefit from tools or skills."""
        text = (user_msg or "").strip()
        if not text:
            return False
        lookup_keywords = ("搜索", "搜一下", "查一下", "查找", "检索", "帮我找", "网上", "近几年", "最新")
        return any(keyword in text for keyword in lookup_keywords)

    async def _ensure_graph(self) -> None:
        """懒加载构建 LangGraph 状态图（双重检查锁），首次调用时初始化。

        图结构:
            START → classify ─┬→ direct_answer → END
                              ├→ vision_answer → END
                              └→ agent ↔ tools → END
        """
        if self.graph is not None:
            return

        async with self._init_lock:  # 防止并发重复构建
            if self.graph is not None:
                return

            # 从统一注册表加载声明的工具
            from app.tools import registry
            from app.resource.base_agent import _ensure_tools_loaded
            from app.skills.manager import SkillManager

            _ensure_tools_loaded()

            registered_tools = []
            if self.tool_names:
                registered_tools = registry.get_many(self.tool_names)

            # 从 SkillManager 加载声明的技能
            skill_tools = []
            if self.skill_names:
                sm = SkillManager()
                await sm.load_all()
                skill_tools = await sm.get_tools(self.skill_names)

            self._tools = registered_tools + skill_tools
            logger.info(
                f"[TutorAgent] tools loaded: {[t.name for t in self._tools]}"
            )

            # 构建状态图节点
            graph = StateGraph(TutorState)
            graph.add_node("classify", self._classify_node)         # 意图分类
            graph.add_node("direct_answer", self._direct_answer_node)  # 纯文本回答
            graph.add_node("vision_answer", self._vision_answer_node)  # 图片理解
            graph.add_node("agent", self._agent_node)               # 工具调用 LLM
            graph.add_node("tools", ToolNode(self._tools))          # 工具执行节点

            # 连接边
            graph.add_edge(START, "classify")
            graph.add_conditional_edges(  # 根据分类结果走不同路径
                "classify",
                self._classify_route,
                {
                    "direct": "direct_answer",
                    "vision_needed": "vision_answer",
                    "tool_needed": "agent",
                },
            )
            graph.add_edge("direct_answer", END)
            graph.add_edge("vision_answer", END)
            graph.add_conditional_edges("agent", self._should_use_tools)  # agent 输出含 tool_calls → tools，否则 → END
            graph.add_edge("tools", "agent")  # 工具执行结果回到 agent 继续推理

            self.graph = graph.compile()
            logger.info("[TutorAgent] StateGraph 构建完成 (两阶段路由)")

    async def _classify_node(self, state: TutorState) -> dict:
        """意图分类：根据附件和消息内容选择最轻量的处理路径。"""
        messages = state.get("messages", [])
        file_urls = state.get("file_urls") or []
        image_urls = state.get("image_urls") or []

        # 提取最后一条用户消息作为分类依据
        user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_msg = msg.content
                break

        wants_lookup = self._looks_like_external_lookup_request(user_msg)
        logger.info(
            "[TutorAgent] classify input: text=%r file_count=%d image_count=%d wants_lookup=%s",
            user_msg[:200],
            len(file_urls),
            len(image_urls),
            wants_lookup,
        )

        # 硬规则：有文档直接走工具路径（需要 read_uploaded_file 工具）
        if file_urls:
            logger.info("[TutorAgent] classify: tool_needed (有文件附件)")
            return {"route": "tool_needed"}

        if wants_lookup:
            logger.info("[TutorAgent] classify: tool_needed (外部检索请求)")
            return {"route": "tool_needed"}

        # 硬规则：有图片直接走视觉路径
        if image_urls:
            logger.info(f"[TutorAgent] classify: vision_needed ({len(image_urls)}张图片)")
            return {"route": "vision_needed"}

        # 无附件时用分类 LLM 判断意图
        has_attachments = "有附件" if image_urls or file_urls else "无附件"
        classify_prompt = PROMPTS["classifier"].format(
            user_message=user_msg[:500],
            has_attachments=has_attachments,
        )

        try:
            result = await self.classifier_llm.ainvoke(
                [HumanMessage(content=classify_prompt)]
            )
            raw_route = result.content.strip()
            route = raw_route.lower()
            route = "tool_needed" if "tool" in route else "direct"
            logger.info("[TutorAgent] classify llm raw=%r normalized=%s", raw_route, route)
        except Exception as e:
            logger.warning(f"[TutorAgent] classify failed, fallback to direct: {e}")
            route = "direct"

        logger.info(f"[TutorAgent] classify: {route}")
        return {"route": route}

    @staticmethod
    def _classify_route(state: TutorState) -> str:
        return state.get("route", "direct")

    @staticmethod
    def _add_system_msg(messages: list[AnyMessage], system_prompt: str) -> list[AnyMessage]:
        """在消息列表头部插入 system prompt（若已存在则跳过）。"""
        if any(isinstance(message, SystemMessage) for message in messages):
            return list(messages)
        return [SystemMessage(content=system_prompt)] + list(messages)

    @staticmethod
    def _inject_images(
        messages: list[AnyMessage],
        image_urls: Optional[List[str]],
    ) -> list[AnyMessage]:
        """将图片 URL 注入最后一条用户消息，构造多模态输入。"""
        if not image_urls:
            return list(messages)

        updated_messages = list(messages)
        for idx in range(len(updated_messages) - 1, -1, -1):
            msg = updated_messages[idx]
            if isinstance(msg, HumanMessage):
                user_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                content_blocks: list[dict] = [{"type": "text", "text": user_text}]
                for url in image_urls:
                    content_blocks.append({"type": "image_url", "image_url": {"url": url}})
                updated_messages[idx] = HumanMessage(content=content_blocks)
                break
        return updated_messages

    @staticmethod
    def _build_messages(system_prompt: str, messages: list[AnyMessage]) -> list[AnyMessage]:
        """拼接 system prompt 和历史消息，过滤已有的 system 消息。"""
        return [SystemMessage(content=system_prompt)] + [
            msg for msg in messages if not isinstance(msg, SystemMessage)
        ]

    async def _direct_answer_node(self, state: TutorState) -> dict:
        """直接回答路径：纯文本对话，不加载工具，延迟最低。"""
        system_prompt = state.get("system_prompt", "")
        messages = state.get("messages", [])
        full_messages = self._build_messages(system_prompt, messages)
        response = await self.llm.ainvoke(full_messages)
        return {"messages": [response]}

    @staticmethod
    def _resolve_image_file(image_url: str) -> Path | None:
        """将上传接口的 URL（如 /api/v1/ai/chat/uploads/1/abc/xxx.png）解析为本地文件路径。"""
        prefix = "/api/v1/ai/chat/uploads/"
        if not image_url.startswith(prefix):
            return None
        relative = image_url[len(prefix):]
        parts = relative.split("/")
        if len(parts) != 3:
            return None
        # parts: [userId, sessionId, filename]
        file_path = (WORKPLACE_DIR / "chat-uploads" / parts[0] / parts[1] / parts[2]).resolve()
        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    @staticmethod
    def _extract_question(messages: list[AnyMessage]) -> str:
        """从消息列表中提取最后一条用户消息的纯文本。"""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                # 去掉附加的附件标记
                return content.split(" [Attached Images:")[0].split(" [Attached Image:")[0].split(" [Attached Files:")[0].strip()
        return "请描述这些图片"

    async def _vision_answer_node(self, state: TutorState) -> dict:
        """图片理解路径：优先星火 API → 主 LLM 统一风格回复；失败回退 GLM 多模态。"""
        image_urls = state.get("image_urls") or []
        messages = list(state.get("messages", []))
        question = self._extract_question(messages)
        system_prompt = state.get("system_prompt", "")

        # 第一选择：星火图片理解（逐张处理，所有图都成功才行）
        if spark_image_service.configured and image_urls:
            spark_results: list[str] = []
            spark_ok = True
            for url in image_urls:
                image_path = self._resolve_image_file(url)
                if not image_path:
                    spark_ok = False
                    break
                try:
                    image_bytes = image_path.read_bytes()
                    result = await spark_image_service.analyze(image_bytes, question)
                    if result:
                        spark_results.append(result)
                    else:
                        spark_ok = False
                        break
                except Exception as e:
                    logger.warning(f"[TutorAgent] vision: 星火图片理解失败，回退 GLM: {e}")
                    spark_ok = False
                    break

            if spark_ok and spark_results:
                combined = "\n\n".join(spark_results) if len(spark_results) > 1 else spark_results[0]
                logger.info(f"[TutorAgent] vision: 星火图片理解成功 ({len(spark_results)}张)")
                # 将星火的 OCR 结果交给主 LLM，保持统一回复风格
                vision_prompt = (
                    f"图片识别结果如下：\n{combined}\n\n"
                    f"请根据以上图片识别结果，回答用户的问题。如果用户没有具体问题，请对图片内容进行描述。"
                )
                vision_messages = [
                    msg for msg in messages if not isinstance(msg, SystemMessage)
                ]
                full_messages = [SystemMessage(content=system_prompt)] + vision_messages[:-1] + [HumanMessage(content=vision_prompt)]
                response = await self.llm.ainvoke(full_messages)
                return {"messages": [response]}

        # 第二选择（回退）：直接用 GLM 多模态模型处理图片
        logger.info("[TutorAgent] vision: 使用 GLM 多模态")
        injected_messages = self._inject_images(messages, image_urls)
        full_messages = self._build_messages(system_prompt, injected_messages)
        response = await self.glm_vision_llm.ainvoke(full_messages)
        return {"messages": [response]}

    async def _agent_node(self, state: TutorState) -> dict:
        """工具调用路径：LLM 绑定工具后推理，输出可能包含 tool_calls（由 _should_use_tools 判断是否继续循环）。"""
        messages = self._add_system_msg(
            list(state.get("messages", [])),
            state.get("tool_system_prompt", ""),
        )
        messages = self._inject_images(messages, state.get("image_urls"))

        # 清洗工具消息格式，确保 API 兼容
        from app.shared.sanitizers import sanitize_tool_messages
        messages = sanitize_tool_messages(messages)

        last_human = next(
            (msg.content for msg in reversed(messages) if isinstance(msg, HumanMessage)),
            "",
        )
        logger.info(
            "[TutorAgent] agent invoke: tools=%d last_user=%r",
            len(self._tools),
            str(last_human)[:200],
        )

        llm_with_tools = self.llm.bind_tools(self._tools)  # 将工具注入 LLM，使其可以决定调用哪个
        try:
            response = await llm_with_tools.ainvoke(messages)
        except Exception:
            logger.exception("[TutorAgent] agent invoke failed")
            raise

        tool_names = [call.get("name", "unknown") for call in (response.tool_calls or [])]
        if getattr(response, "tool_calls", None):
            logger.info(
                "[TutorAgent] LLM 选择工具: names=%s args=%s",
                [call.get("name", "unknown") for call in response.tool_calls],
                [call.get("args", {}) for call in response.tool_calls],
            )
        logger.info(
            "[TutorAgent] agent response: tool_calls=%s names=%s content_preview=%r",
            bool(response.tool_calls),
            tool_names,
            (response.content or "")[:200] if isinstance(response.content, str) else str(response.content)[:200],
        )
        return {"messages": [response]}

    @staticmethod
    def _should_use_tools(state: TutorState) -> str:
        """条件边：如果 agent 最后输出含 tool_calls → 跳到 tools 节点执行；否则 → END 结束。"""
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return END

    def _spawn_background(self, coro, task_name: str) -> None:
        """创建后台任务（不阻塞流式响应），完成后自动从集合移除并记录异常。"""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)  # 强引用防止被 GC 回收

        def _on_done(done: asyncio.Task):
            self._background_tasks.discard(done)  # 完成后移除引用
            try:
                done.result()  # 触发异常传播
            except asyncio.CancelledError:
                logger.info(f"[TutorAgent] 后台任务已取消 ({task_name})")
            except Exception as exc:
                logger.error(f"[TutorAgent] 后台任务失败 ({task_name}): {exc}")

        task.add_done_callback(_on_done)

    async def wait_for_background_tasks(self) -> None:
        """等待当前已注册的后台任务结束，适合脚本模式退出前调用。"""
        while self._background_tasks:
            pending = tuple(self._background_tasks)
            await asyncio.gather(*pending, return_exceptions=True)

    async def _build_profile_ctx(self, user_id: int) -> str:
        """读取用户画像（8 维度学习特征），渲染为 system prompt 中的上下文段落。"""
        profile_str = "暂无画像信息（新用户），请直接开始对话。"
        profile = await self.memory.get_user_profile(user_id)
        if not profile:
            return profile_str

        profile_dict = profile.model_dump(
            exclude_unset=True, exclude={"updated_at", "created_at"},
        )
        if profile_dict:
            profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])
        return profile_str

    async def _build_memory_ctx(self, user_id: int) -> str:
        """读取长期记忆，按类型分组（偏好/目标/薄弱点/事实/背景）渲染为 prompt 段落。"""
        memories_by_type = await self.memory.get_user_context_memories(user_id=user_id)
        section_titles = {
            "preference": "偏好",
            "goal": "目标",
            "weakness": "薄弱点",
            "fact": "稳定事实",
            "background": "背景信息",
        }
        chunks: list[str] = []
        for memory_type, title in section_titles.items():
            items = memories_by_type.get(memory_type, [])
            if not items:
                continue
            lines = "\n".join([f"- {m.content}" for m in items])
            chunks.append(f"### {title}\n{lines}")
        return "\n\n".join(chunks) if chunks else "暂无特定事实记忆。"

    async def _build_chat_ctx(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        image_urls: Optional[List[str]],
        file_urls: Optional[List[str]],
    ) -> tuple[list[AnyMessage], str]:
        """读取最近 10 条历史消息，构造 LangChain 消息列表 + 可读摘要（供 prompt 填充）。"""
        initial_messages: list[AnyMessage] = []
        recent_context_lines: list[str] = []
        recent_msgs = await self.memory.get_recent_messages(
            user_id, session_id, self.module_name, limit=10
        )
        for msg in recent_msgs[:-1]:
            if msg.role == "user":
                initial_messages.append(HumanMessage(content=msg.content))
                recent_context_lines.append(f"- 用户: {msg.content}")
            elif msg.role == "assistant":
                initial_messages.append(AIMessage(content=msg.content))
                recent_context_lines.append(f"- 助手: {msg.content}")

        full_msg = user_message
        if image_urls:
            full_msg += f"\n[Attached Images: {', '.join(image_urls)}]"
        if file_urls:
            full_msg += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=full_msg))
        recent_context = "\n".join(recent_context_lines) if recent_context_lines else "最近 7 天暂无历史对话。"
        return initial_messages, recent_context

    @staticmethod
    def _build_file_ctx(image_urls: Optional[List[str]], file_urls: Optional[List[str]]) -> str:
        """将附件 URL 转为描述文本，告知 LLM 有哪些可用资源（图片可直接理解，文档需调用工具读取）。"""
        lines: list[str] = []
        if image_urls:
            for url in image_urls:
                lines.append(f"- 图片: {url} (可直接进行图片理解)")
        if file_urls:
            lines.extend([
            f"- 文件名: {url.split('/')[-1]}, URL: {url} (使用 read_uploaded_file 工具读取)"
            for url in file_urls
            ])
        if not lines:
            return "用户未上传文件。"
        return "用户上传了以下附件:\n" + "\n".join(lines)

    async def _try_extract_memory(self, user_id: int, session_id: str) -> None:
        """当会话 token 累积超过阈值时，触发 fact_agent 从对话中提取长期事实记忆。"""
        should_trigger = await self.memory.should_trigger_memory_extraction(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_EXTRACTION_TOKEN_THRESHOLD,
        )
        if not should_trigger:
            return

        success = await self.fact_agent.extract_and_save_fact(user_id=user_id, session_id=session_id)
        if success:
            await self.memory.reset_memory_extraction_counter(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
            )
            logger.info(f"[TutorAgent] 长期记忆提取完成并重置计数 (user={user_id}, session={session_id})")

    async def _try_update_profile(self, user_id: int, session_id: str) -> None:
        """双门控画像更新：token 累积阈值 + 对话显著性判断都通过后才触发 profile_agent。"""
        token_ready = await self.memory.should_trigger_profile_update_by_tokens(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=PROFILE_UPDATE_TOKEN_THRESHOLD,
        )
        if not token_ready:
            return

        recent_msgs = await self.memory.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=20,
        )
        if not self.profile_agent.should_trigger_profile_update(recent_msgs):
            logger.info(f"[TutorAgent] 画像更新未通过显著性判断 (user={user_id}, session={session_id})")
            return

        success = await self.profile_agent.build_profile(user_id=user_id, session_id=session_id)
        if success:
            await self.memory.reset_profile_update_counter(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
            )
            logger.info(f"[TutorAgent] 画像更新完成并重置计数 (user={user_id}, session={session_id})")

    async def _post_chat_pipeline(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """对话后处理流水线（后台执行）: 累积 token → 记忆提取 → 画像更新。"""
        try:
            await self.memory.accumulate_session_tokens(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
                content=f"{user_message}\n{assistant_reply}",
            )
            await self._try_extract_memory(user_id, session_id)
            await self._try_update_profile(user_id, session_id)
        except Exception as exc:
            logger.error(f"[TutorAgent] post chat pipeline failed: {exc}")

    async def _persist_tool_messages(
        self,
        *,
        user_id: int,
        session_id: str,
        tool_call_records: list[dict],
    ) -> None:
        """将工具调用记录落库为独立消息，便于后续审计与回放。"""
        for record in tool_call_records:
            tool_name = str(record.get("tool", "unknown"))
            status = str(record.get("status", "success"))
            args = record.get("args", {})
            result = str(record.get("result", ""))

            content = (
                f"工具调用: {tool_name}\n"
                f"状态: {status}\n"
                f"参数: {args}\n"
                f"结果: {result[:2000]}"
            )
            payload = json.dumps([record], ensure_ascii=False)
            await self.memory.save_message(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
                role="tool",
                content=content,
                tool_calls=payload,
            )

    async def chat_stream(
        self,
        user_id: int,
        user_message: str,
        session_id: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        file_urls: Optional[List[str]] = None,
    ):
        """主入口：保存用户消息 → 构建 3 层上下文 → 流式输出回复 → 后台触发记忆/画像更新。"""
        effective_session = session_id or f"user-{user_id}-default-mentor"
        logger.info(f"[Tutor] User {user_id} message: {user_message[:50]}...")

        await self._ensure_graph()  # 确保 LangGraph 已构建

        IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        # 构造附件元数据列表（用于持久化到 ChatMessage.attachments）
        attachments_json = None
        attachment_items: list[dict] = []
        if image_urls:
            attachment_items.extend([
                {
                    "url": url,
                    "type": "image",
                    "name": url.split("/")[-1],
                }
                for url in image_urls
            ])
        if file_urls:
            attachment_items.extend([
                {
                    "url": url,
                    "type": "image" if Path(url).suffix.lower() in IMAGE_EXTS else "document",
                    "name": url.split("/")[-1],
                }
                for url in file_urls
            ])
        if attachment_items:
            attachments_json = json.dumps(attachment_items)

        # 步骤 1: 持久化用户消息到短期记忆
        try:
            msg_content = user_message
            if image_urls:
                msg_content += f" [Attached Images: {', '.join(image_urls)}]"
            if file_urls:
                msg_content += f" [Attached Files: {', '.join(file_urls)}]"
            await self.memory.save_message(
                user_id, effective_session, self.module_name, "user", msg_content,
                attachments=attachments_json,
            )
        except Exception as e:
            logger.error(f"[Tutor] Failed to save message: {e}")
            yield f"抱歉，系统暂时无法保存您的消息，请稍后重试 ({e})"
            return

        # 步骤 2: 构建 3 层上下文（画像 + 长期记忆 + 附件信息）
        profile_str = await self._build_profile_ctx(user_id)
        fact_str = await self._build_memory_ctx(user_id)
        file_info_str = self._build_file_ctx(image_urls, file_urls)

        # 构建可用技能描述
        skills_ctx = ""
        if self.skill_names:
            from app.skills.manager import SkillManager
            sm = SkillManager()
            sm._load_skills()
            skills = sm.list_skills()
            # 过滤只显示声明的技能
            skills = [s for s in skills if s["name"] in self.skill_names]
            if skills:
                skills_desc = "\n".join(
                    f"- {s['name']}: {s['description']}" for s in skills
                )
                skills_ctx = (
                    f"## 【可用技能】\n"
                    f"你可以通过调用 load_skill_<name> 工具加载专家技能指令：\n{skills_desc}"
                )

        # 步骤 3: 读取近期聊天历史，构造 LangChain 消息列表
        initial_messages, recent_chat_context = await self._build_chat_ctx(
            user_id=user_id,
            session_id=effective_session,
            user_message=user_message,
            image_urls=image_urls,
            file_urls=file_urls,
        )

        # 步骤 4: 填充两套 system prompt（直接回答 vs 工具调用）
        direct_prompt = PROMPTS["direct_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
            recent_chat_context=recent_chat_context,
        )
        tool_prompt = PROMPTS["tool_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
            recent_chat_context=recent_chat_context,
            file_info_context=file_info_str,
            skills_context=skills_ctx,
        )

        full_reply = ""
        tool_call_records: list[dict] = []
        graph_error_text = ""

        # 步骤 5: 构建初始状态并运行 LangGraph
        initial_state: TutorState = {
            "user_id": user_id,
            "session_id": effective_session,
            "image_urls": image_urls,
            "file_urls": file_urls,
            "route": "",
            "system_prompt": direct_prompt,
            "tool_system_prompt": tool_prompt,
            "messages": initial_messages,
        }

        try:
            # chat_runtime_context 通过 ContextVar 将 user_id/session_id 注入到工具调用中
            with chat_runtime_context(user_id, effective_session):
                async for event in self.graph.astream_events(
                    initial_state,
                    version="v2",  # v2 事件格式，按节点输出事件
                    config={"recursion_limit": 15},  # 防止工具调用无限循环
                ):
                    kind = event.get("event", "")

                    # 事件 1: LLM 流式输出 — 逐 token yield 给前端
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and chunk.content:
                            text = chunk.content if isinstance(chunk.content, str) else ""
                            if text:
                                full_reply += text
                                yield text

                    # 事件 2: 非流式节点完成（vision_answer / direct_answer 不走流式）
                    if kind == "on_chain_end" and event.get("name") in ("vision_answer", "direct_answer"):
                        output = event.get("data", {}).get("output", {})
                        output_msgs = output.get("messages", []) if isinstance(output, dict) else []
                        for msg in output_msgs:
                            if isinstance(msg, AIMessage) and msg.content and msg.content not in full_reply:
                                full_reply += msg.content
                                yield msg.content

                    # 事件 3: 工具执行完成 — 记录调用结果用于持久化
                    if kind == "on_tool_end":
                        tool_input = event.get("data", {}).get("input", {})
                        tool_output = event.get("data", {}).get("output", "")
                        tool_name = event.get("name", "unknown")
                        logger.info(
                            "[TutorAgent] tool success: name=%s args=%r output_preview=%r",
                            tool_name,
                            tool_input,
                            str(tool_output)[:300],
                        )
                        record_result = (
                            json.dumps(tool_output, ensure_ascii=False)
                            if isinstance(tool_output, dict)
                            else str(tool_output)
                        )
                        tool_call_records.append({
                            "tool": tool_name,
                            "args": tool_input if isinstance(tool_input, dict) else str(tool_input),
                            "result": record_result,
                            "status": "success",
                        })
                    if kind == "on_tool_error":
                        tool_input = event.get("data", {}).get("input", {})
                        tool_error = event.get("data", {}).get("error", "unknown tool error")
                        tool_name = event.get("name", "unknown")
                        logger.error(
                            "[TutorAgent] tool error: name=%s args=%r error=%r",
                            tool_name,
                            tool_input,
                            str(tool_error)[:500],
                        )
                        tool_call_records.append({
                            "tool": tool_name,
                            "args": tool_input if isinstance(tool_input, dict) else str(tool_input),
                            "result": str(tool_error)[:2000],
                            "status": "error",
                        })

        except Exception as e:
            logger.error(f"[Tutor] Graph execution error: {e}")
            graph_error_text = f"服务器出错，请稍后再试: {e}"

        if tool_call_records:
            try:
                await self._persist_tool_messages(
                    user_id=user_id,
                    session_id=effective_session,
                    tool_call_records=tool_call_records,
                )
            except Exception as e:
                logger.error(f"[Tutor] Failed to save tool messages: {e}")

        if graph_error_text:
            full_reply += graph_error_text
            yield graph_error_text

        # 步骤 6: 持久化助手回复 + 后台触发记忆/画像更新
        if full_reply:
            try:
                tool_calls_json = json.dumps(tool_call_records) if tool_call_records else None
                await self.memory.save_message(
                    user_id, effective_session, self.module_name, "assistant", full_reply,
                    tool_calls=tool_calls_json,
                )
                if tool_call_records:
                    logger.info(f"[Tutor] Saved reply with {len(tool_call_records)} tool call(s)")
                # 后台不阻塞：累积 token → 记忆提取 → 画像更新
                self._spawn_background(
                    self._post_chat_pipeline(
                        user_id=user_id,
                        session_id=effective_session,
                        user_message=user_message,
                        assistant_reply=full_reply,
                    ),
                    task_name="post_chat_pipeline",
                )
            except Exception as e:
                logger.error(f"[Tutor] Failed to save reply: {e}")
