"""
智能辅导 TutorAgent：LangGraph 工作流 + 分层路由 + 千人千面。

目录结构：
  chat/
    agent.py              ← 本文件
    prompt.md             ← 系统提示词模板
    mcp/settings.json     ← MCP 配置
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
from app.services.memory import memory_service
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
    route: str  # "direct" | "tool_needed"
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
            mcp_settings_path=AGENT_DIR / "mcp" / "settings.json",
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

            # 2. 加载 MCP + Skills
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
            graph.add_node("agent", self._agent_node)
            graph.add_node("tools", ToolNode(self._tools))

            graph.add_edge(START, "classify")
            graph.add_conditional_edges("classify", self._route_after_classify)
            graph.add_edge("direct_answer", END)
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

        # 提取用户最新消息
        user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_msg = msg.content
                break

        # 有附件直接走工具路径
        if file_urls:
            logger.info("[TutorAgent] classify: tool_needed (有文件附件)")
            return {"route": "tool_needed"}

        # 调用轻量 LLM 分类
        has_attachments = "无附件"
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

    async def _agent_node(self, state: TutorState) -> dict:
        """工具路径：绑定工具的 Agent 节点。"""
        messages = state.get("messages", [])

        has_system = any(isinstance(m, SystemMessage) for m in messages)
        if not has_system:
            tool_prompt = state.get("tool_system_prompt", "")
            messages = [SystemMessage(content=tool_prompt)] + list(messages)

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
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
        effective_session = session_id or self.global_session_id
        logger.info(f"[Tutor] User {user_id} message: {user_message[:50]}...")

        await self._ensure_graph()

        # 1. 保存用户消息
        IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        attachments_json = None
        if file_urls:
            attachments_json = json.dumps([
                {
                    "url": url,
                    "type": "image" if Path(url).suffix.lower() in IMAGE_EXTS else "document",
                    "name": url.split("/")[-1],
                }
                for url in file_urls
            ])

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

        # 2. 加载画像
        profile_str = "暂无画像信息（新用户），请直接开始对话。"
        profile = await memory_service.get_user_profile(user_id)
        if profile:
            profile_dict = profile.model_dump(
                exclude_unset=True, exclude={"updated_at", "created_at"},
            )
            if profile_dict:
                profile_str = "\n".join(
                    [f"- {k}: {v}" for k, v in profile_dict.items() if v]
                )

        # 3. 加载长期事实记忆
        facts = await memory_service.get_user_facts(user_id, limit=20)
        fact_str = "暂无特定事实记忆。"
        if facts:
            fact_str = "\n".join(
                [f"- {f.content} (属性: {f.memory_type})" for f in facts]
            )

        # 4. 构建文件信息上下文
        file_info_str = "用户未上传文件。"
        if file_urls:
            file_info_str = "用户上传了以下文件:\n" + "\n".join(
                f"- 文件名: {url.split('/')[-1]}, URL: {url} (使用 read_uploaded_file 工具读取)"
                for url in file_urls
            )

        # 5. 渲染两套 prompt
        direct_prompt = PROMPTS["direct_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
        )

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

        tool_prompt = PROMPTS["tool_system"].format(
            profile_context=profile_str,
            fact_context=fact_str,
            file_info_context=file_info_str,
            skills_context=skills_ctx,
        )

        # 6. 构建消息列表
        initial_messages: list[AnyMessage] = []
        recent_msgs = await memory_service.get_recent_messages(
            user_id, effective_session, self.module_name, limit=10
        )
        for msg in recent_msgs[:-1]:
            if msg.role == "user":
                initial_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                initial_messages.append(AIMessage(content=msg.content))

        full_msg = user_message
        if file_urls:
            full_msg += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=full_msg))

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
            except Exception as e:
                logger.error(f"[Tutor] Failed to save reply: {e}")


# 全局单例
tutor_agent = TutorAgent()
