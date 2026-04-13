"""
智能辅导 TutorAgent：LangGraph 工作流 + 分层路由 + 千人千面。

目录结构：
  chat/
    agent.py              ← 本文件
    prompt.md             ← 系统提示词模板
    skills/               ← 技能目录
    tools/                ← 本地工具

工作流设计（两阶段路由）：
  用户消息 → [classify]
    ├─ "direct"     → [direct_answer] → END
    └─ "tool_needed" → [agent] ↔ [tools] → END
"""

import asyncio
import importlib
import json
import os
from pathlib import Path
from typing import TypedDict, Optional, List, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, AnyMessage,
)
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.modules.chat.runtime_context import chat_runtime_context
from app.modules.profile.fact_agent import fact_agent
from app.modules.profile.profile_agent import profile_agent, PROFILE_UPDATE_TOKEN_THRESHOLD
from app.services.memory import memory_service
from app.services.memory import MEMORY_EXTRACTION_TOKEN_THRESHOLD
from app.utils.paths import WORKPLACE_DIR
from app.utils.plugin_manager import PluginManager

load_dotenv()
logger = get_logger(__name__)

AGENT_DIR = Path(__file__).resolve().parent

# 共享配置
MODULE_NAME = "mentor"
GLOBAL_SESSION_ID = "global_profile_chat"


# ==========================================
# 1. Prompt 加载
# ==========================================

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


# ==========================================
# 2. LangGraph State
# ==========================================

class TutorState(TypedDict, total=False):
    """TutorAgent 工作流状态。"""
    user_id: int
    session_id: str
    image_url: Optional[str]
    file_urls: Optional[List[str]]
    route: str  # "direct" | "tool_needed" | "vision_needed"
    system_prompt: str
    tool_system_prompt: str
    messages: Annotated[list[AnyMessage], add_messages]


# ==========================================
# 3. TutorAgent
# ==========================================

class TutorAgent:
    """智能辅导 Agent：两阶段 LangGraph 工作流。

    快速路径: classify → direct_answer → END（不绑工具，流式直出）
    工具路径: classify → agent(+tools) → agent ... → END
    """

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.7,
            streaming=True,
        )
        self.classifier_llm = ChatOpenAI(
            model=os.getenv("FAST_LLM_MODEL", "general"),
            api_key=os.getenv("FAST_LLM_API_KEY", os.getenv("OPENAI_API_KEY")),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.0,
            max_tokens=10,
        )
        self.module_name = MODULE_NAME
        self.global_session_id = GLOBAL_SESSION_ID
        self.graph = None
        self._tools: list[BaseTool] = []
        self._init_lock = asyncio.Lock()

        self.plugin_manager = PluginManager(
            workspace=WORKPLACE_DIR / "chat",
            skills_path=AGENT_DIR / "skills",
        )

    # ══════════════════════════════════════════════════════════
    # 工具加载
    # ══════════════════════════════════════════════════════════

    def _load_local_tools(self) -> list[BaseTool]:
        """从 agent_dir/tools/ 自动发现本地工具。"""
        tools_dir = AGENT_DIR / "tools"
        if not tools_dir.exists() or not tools_dir.is_dir():
            return []

        local_tools: list[BaseTool] = []
        for py_file in sorted(tools_dir.glob("*.py")):
            # 跳过 __pycache__ 等，但允许 __init__.py（shared_tools 重导出）
            if py_file.name != "__init__.py" and py_file.name.startswith("_"):
                continue
            found = self._discover_tools_in_module(py_file)
            local_tools.extend(found)

        if local_tools:
            logger.info(f"[TutorAgent] 本地工具: {[t.name for t in local_tools]}")
        return local_tools

    @staticmethod
    def _discover_tools_in_module(py_file: Path) -> list[BaseTool]:
        """动态导入 Python 模块并提取 BaseTool 实例。"""
        tools_found: list[BaseTool] = []
        module_name = f"_chat_tools_{py_file.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                return []
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            logger.error(f"[TutorAgent] 导入工具模块失败 ({py_file}): {e}")
            return []

        for attr_name in dir(mod):
            obj = getattr(mod, attr_name, None)
            if isinstance(obj, BaseTool):
                tools_found.append(obj)

        return tools_found

    async def _ensure_graph(self) -> None:
        """延迟构建 LangGraph。"""
        if self.graph is not None:
            return

        async with self._init_lock:
            if self.graph is not None:
                return

            # 1. 加载本地工具
            local_tools = self._load_local_tools()
            if local_tools:
                self.plugin_manager.register(*local_tools)

            # 2. 加载 Skills
            await self.plugin_manager.load_all()

            # 3. 获取所有工具
            self._tools = await self.plugin_manager.get_tools()
            logger.info(
                f"[TutorAgent] tools loaded: {[t.name for t in self._tools]}"
            )

            # 4. 构建 LangGraph
            graph = StateGraph(TutorState)
            graph.add_node("classify", self._classify_node)
            graph.add_node("direct_answer", self._direct_answer_node)
            graph.add_node("vision_answer", self._vision_answer_node)
            graph.add_node("agent", self._agent_node)
            graph.add_node("tools", ToolNode(self._tools))

            graph.add_edge(START, "classify")
            graph.add_conditional_edges(
                "classify",
                self._route_after_classify,
                {
                    "direct": "direct_answer",
                    "vision_needed": "vision_answer",
                    "tool_needed": "agent",
                },
            )
            graph.add_edge("direct_answer", END)
            graph.add_edge("vision_answer", END)
            graph.add_conditional_edges("agent", self._should_use_tools)
            graph.add_edge("tools", "agent")

            self.graph = graph.compile()
            logger.info("[TutorAgent] StateGraph 构建完成 (两阶段路由)")

    # ══════════════════════════════════════════════════════════
    # 节点实现
    # ══════════════════════════════════════════════════════════

    async def _classify_node(self, state: TutorState) -> dict:
        """分类节点：判断走快速路径还是工具路径。"""
        messages = state.get("messages", [])
        file_urls = state.get("file_urls") or []
        image_url = state.get("image_url")

        # 提取用户最新消息
        user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_msg = msg.content
                break

        # 文档附件优先走工具路径（需要 read_uploaded_file 等工具）
        if file_urls:
            logger.info("[TutorAgent] classify: tool_needed (有文件附件)")
            return {"route": "tool_needed"}

        # 图片走多模态理解节点（不绑定工具，直接多模态回答）
        if image_url:
            logger.info("[TutorAgent] classify: vision_needed (有图片附件)")
            return {"route": "vision_needed"}

        # 调用轻量 LLM 分类
        has_attachments = "有附件" if image_url or file_urls else "无附件"
        classify_prompt = PROMPTS["classifier"].format(
            user_message=user_msg[:500],
            has_attachments=has_attachments,
        )

        try:
            result = await self.classifier_llm.ainvoke(
                [HumanMessage(content=classify_prompt)]
            )
            route = result.content.strip().lower()
            route = "tool_needed" if "tool" in route else "direct"
        except Exception as e:
            logger.warning(f"[TutorAgent] classify failed, fallback to direct: {e}")
            route = "direct"

        logger.info(f"[TutorAgent] classify: {route}")
        return {"route": route}

    @staticmethod
    def _route_after_classify(state: TutorState) -> str:
        return state.get("route", "direct")

    async def _direct_answer_node(self, state: TutorState) -> dict:
        """快速路径：不带工具直接回答。"""
        system_prompt = state.get("system_prompt", "")
        messages = state.get("messages", [])

        full_messages: list[AnyMessage] = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                full_messages.append(msg)

        response = await self.llm.ainvoke(full_messages)
        return {"messages": [response]}

    async def _vision_answer_node(self, state: TutorState) -> dict:
        """图片理解路径：走多模态输入，不绑定工具。"""
        system_prompt = state.get("system_prompt", "")
        messages = list(state.get("messages", []))
        image_url = state.get("image_url")

        if image_url:
            for idx in range(len(messages) - 1, -1, -1):
                msg = messages[idx]
                if isinstance(msg, HumanMessage):
                    user_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                    messages[idx] = HumanMessage(
                        content=[
                            {"type": "text", "text": user_text},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ]
                    )
                    break

        full_messages: list[AnyMessage] = [SystemMessage(content=system_prompt)]
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                full_messages.append(msg)

        response = await self.llm.ainvoke(full_messages)
        return {"messages": [response]}

    async def _agent_node(self, state: TutorState) -> dict:
        """工具路径：绑定工具的 Agent 节点。"""
        messages = list(state.get("messages", []))
        image_url = state.get("image_url")

        has_system = any(isinstance(m, SystemMessage) for m in messages)
        if not has_system:
            tool_prompt = state.get("tool_system_prompt", "")
            messages = [SystemMessage(content=tool_prompt)] + list(messages)

        # 工具路径也支持图片理解：将最新用户消息升级为多模态输入
        if image_url:
            for idx in range(len(messages) - 1, -1, -1):
                msg = messages[idx]
                if isinstance(msg, HumanMessage):
                    user_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                    messages[idx] = HumanMessage(
                        content=[
                            {"type": "text", "text": user_text},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ]
                    )
                    break

        # 修复工具返回 list 内容导致部分模型 API 报 400 Invalid Data 的问题
        from langchain_core.messages import ToolMessage
        safe_messages = []
        for msg in messages:
            if getattr(msg, "type", "") == "tool" and isinstance(msg.content, list):
                texts = []
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    else:
                        texts.append(str(block))
                safe_msg = ToolMessage(
                    content="\n".join(texts),
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                    status=getattr(msg, "status", "success")
                )
                safe_messages.append(safe_msg)
            else:
                safe_messages.append(msg)
        
        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(safe_messages)
        logger.info(
            f"[TutorAgent] agent response, tool_calls={bool(response.tool_calls)}"
        )
        return {"messages": [response]}

    @staticmethod
    def _should_use_tools(state: TutorState) -> str:
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return END

    @staticmethod
    def _spawn_background(coro, task_name: str) -> None:
        """统一后台任务入口：不阻塞主响应，异常写日志。"""
        task = asyncio.create_task(coro)

        def _on_done(done: asyncio.Task):
            try:
                done.result()
            except Exception as exc:
                logger.error(f"[TutorAgent] 后台任务失败 ({task_name}): {exc}")

        task.add_done_callback(_on_done)

    async def _build_profile_context(self, user_id: int) -> str:
        profile_str = "暂无画像信息（新用户），请直接开始对话。"
        profile = await memory_service.get_user_profile(user_id)
        if not profile:
            return profile_str

        profile_dict = profile.model_dump(
            exclude_unset=True, exclude={"updated_at", "created_at"},
        )
        if profile_dict:
            profile_str = "\n".join([f"- {k}: {v}" for k, v in profile_dict.items() if v])
        return profile_str

    async def _build_memory_context(self, user_id: int) -> str:
        memories_by_type = await memory_service.get_user_context_memories(user_id=user_id)
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

    async def _build_recent_chat_context(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        image_url: Optional[str],
        file_urls: Optional[List[str]],
    ) -> tuple[list[AnyMessage], str]:
        initial_messages: list[AnyMessage] = []
        recent_context_lines: list[str] = []
        recent_msgs = await memory_service.get_recent_messages(
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
        if image_url:
            full_msg += f"\n[Attached Image: {image_url}]"
        if file_urls:
            full_msg += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=full_msg))
        recent_context = "\n".join(recent_context_lines) if recent_context_lines else "最近 7 天暂无历史对话。"
        return initial_messages, recent_context

    @staticmethod
    def _build_file_context(image_url: Optional[str], file_urls: Optional[List[str]]) -> str:
        lines: list[str] = []
        if image_url:
            lines.append(f"- 图片: {image_url} (可直接进行图片理解)")
        if file_urls:
            lines.extend([
            f"- 文件名: {url.split('/')[-1]}, URL: {url} (使用 read_uploaded_file 工具读取)"
            for url in file_urls
            ])
        if not lines:
            return "用户未上传文件。"
        return "用户上传了以下附件:\n" + "\n".join(lines)

    async def _maybe_trigger_memory_extraction(self, user_id: int, session_id: str) -> None:
        should_trigger = await memory_service.should_trigger_memory_extraction(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=MEMORY_EXTRACTION_TOKEN_THRESHOLD,
        )
        if not should_trigger:
            return

        success = await fact_agent.extract_and_save_fact(user_id=user_id, session_id=session_id)
        if success:
            await memory_service.reset_memory_extraction_counter(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
            )
            logger.info(f"[TutorAgent] 长期记忆提取完成并重置计数 (user={user_id}, session={session_id})")

    async def _maybe_trigger_profile_update(self, user_id: int, session_id: str) -> None:
        token_ready = await memory_service.should_trigger_profile_update_by_tokens(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            threshold=PROFILE_UPDATE_TOKEN_THRESHOLD,
        )
        if not token_ready:
            return

        recent_msgs = await memory_service.get_recent_messages(
            user_id=user_id,
            session_id=session_id,
            module=self.module_name,
            limit=20,
        )
        if not profile_agent.should_trigger_profile_update(recent_msgs):
            logger.info(f"[TutorAgent] 画像更新未通过显著性判断 (user={user_id}, session={session_id})")
            return

        success = await profile_agent.build_profile(user_id=user_id, session_id=session_id)
        if success:
            await memory_service.reset_profile_update_counter(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
            )
            logger.info(f"[TutorAgent] 画像更新完成并重置计数 (user={user_id}, session={session_id})")

    async def _run_post_chat_pipeline(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """对话完成后异步执行的后处理链路。"""
        try:
            await memory_service.accumulate_session_tokens(
                user_id=user_id,
                session_id=session_id,
                module=self.module_name,
                content=f"{user_message}\n{assistant_reply}",
            )
            await self._maybe_trigger_memory_extraction(user_id, session_id)
            await self._maybe_trigger_profile_update(user_id, session_id)
        except Exception as exc:
            logger.error(f"[TutorAgent] post chat pipeline failed: {exc}")

    # ══════════════════════════════════════════════════════════
    # 公共 API
    # ══════════════════════════════════════════════════════════

    async def chat_stream(
        self,
        user_id: int,
        user_message: str,
        session_id: Optional[str] = None,
        image_url: Optional[str] = None,
        file_urls: Optional[List[str]] = None,
    ):
        """处理用户消息，流式返回回复文本。"""
        effective_session = session_id or f"user-{user_id}-default-mentor"
        logger.info(f"[Tutor] User {user_id} message: {user_message[:50]}...")

        await self._ensure_graph()

        # 1. 保存用户消息
        IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        attachments_json = None
        attachment_items: list[dict] = []
        if image_url:
            attachment_items.append(
                {
                    "url": image_url,
                    "type": "image",
                    "name": image_url.split("/")[-1],
                }
            )
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

        try:
            msg_content = user_message
            if image_url:
                msg_content += f" [Attached Image: {image_url}]"
            if file_urls:
                msg_content += f" [Attached Files: {', '.join(file_urls)}]"
            await memory_service.save_message(
                user_id, effective_session, self.module_name, "user", msg_content,
                attachments=attachments_json,
            )
        except Exception as e:
            logger.error(f"[Tutor] Failed to save message: {e}")
            yield f"抱歉，系统暂时无法保存您的消息，请稍后重试 ({e})"
            return

        # 2. 分块构建上下文
        profile_str = await self._build_profile_context(user_id)
        fact_str = await self._build_memory_context(user_id)
        file_info_str = self._build_file_context(image_url, file_urls)

        skills_ctx = ""
        skills = self.plugin_manager.list_skills()
        if skills:
            skills_desc = "\n".join(
                f"- {s['name']}: {s['description']}" for s in skills
            )
            skills_ctx = (
                f"## 【可用技能】\n"
                f"你可以通过调用 load_skill_<name> 工具加载专家技能指令：\n{skills_desc}"
            )

        # 6. 构建最近 7 天会话上下文（默认过期过滤）
        initial_messages, recent_chat_context = await self._build_recent_chat_context(
            user_id=user_id,
            session_id=effective_session,
            user_message=user_message,
            image_url=image_url,
            file_urls=file_urls,
        )

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

        # 7. 执行 LangGraph 并流式输出
        full_reply = ""
        tool_call_records: list[dict] = []

        initial_state: TutorState = {
            "user_id": user_id,
            "session_id": effective_session,
            "image_url": image_url,
            "file_urls": file_urls,
            "route": "",
            "system_prompt": direct_prompt,
            "tool_system_prompt": tool_prompt,
            "messages": initial_messages,
        }

        try:
            with chat_runtime_context(user_id):
                async for event in self.graph.astream_events(
                    initial_state,
                    version="v2",
                    config={"recursion_limit": 15},
                ):
                    kind = event.get("event", "")

                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and chunk.content:
                            text = chunk.content if isinstance(chunk.content, str) else ""
                            if text:
                                full_reply += text
                                yield text

                    if kind == "on_tool_end":
                        tool_input = event.get("data", {}).get("input", {})
                        tool_output = event.get("data", {}).get("output", "")
                        tool_name = event.get("name", "unknown")
                        tool_call_records.append({
                            "tool": tool_name,
                            "args": tool_input if isinstance(tool_input, dict) else str(tool_input),
                            "result": str(tool_output)[:2000],
                            "status": "success",
                        })

        except Exception as e:
            logger.error(f"[Tutor] Graph execution error: {e}")
            yield f"服务器出错，请稍后再试: {e}"

        # 8. 保存 AI 回复
        if full_reply:
            try:
                tool_calls_json = json.dumps(tool_call_records) if tool_call_records else None
                await memory_service.save_message(
                    user_id, effective_session, self.module_name, "assistant", full_reply,
                    tool_calls=tool_calls_json,
                )
                if tool_call_records:
                    logger.info(f"[Tutor] Saved reply with {len(tool_call_records)} tool call(s)")
                self._spawn_background(
                    self._run_post_chat_pipeline(
                        user_id=user_id,
                        session_id=effective_session,
                        user_message=user_message,
                        assistant_reply=full_reply,
                    ),
                    task_name="post_chat_pipeline",
                )
            except Exception as e:
                logger.error(f"[Tutor] Failed to save reply: {e}")


# 全局单例
tutor_agent = TutorAgent()
