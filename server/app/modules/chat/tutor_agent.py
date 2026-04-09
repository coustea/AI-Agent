"""
智能辅导 TutorAgent：LangGraph 工作流 + 分层路由 + 千人千面。

工作流设计（两阶段路由）：
  ┌─────────────────────────────────────────────────────┐
  │  用户消息                                            │
  │    ↓                                                │
  │  [classify] 分类节点（轻量 LLM，不绑工具，流式）       │
  │    ├─ "direct"  → [direct_answer] 直接回答 → END     │
  │    └─ "tool_needed" → [agent] → [tools] → [agent]   │
  │                                  ↓ 没有更多 tool_calls │
  │                                 END                   │
  └─────────────────────────────────────────────────────┘

分类依据：
  - 用户是否上传了文件（file_urls 不为空）→ tool_needed
  - 用户是否要求生成资源（思维导图等）→ tool_needed
  - 简单概念/代码/理论问题 → direct
  - 需要读取文件、调用外部服务 → tool_needed

好处：
  - 简单问题不绑定工具，响应更快
  - 复杂问题走完整的工具循环，能力更强
"""

import json
import os
from pathlib import Path
from typing import TypedDict, Optional, List, Annotated, Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, AnyMessage,
)
from langchain_core.tools import BaseTool, tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.services.memory import memory_service
from app.utils.skills_manager import skills_manager
from app.utils.tools_manager import tools_manager

load_dotenv()
logger = get_logger(__name__)

# 共享配置
MODULE_NAME = "mentor"
GLOBAL_SESSION_ID = "global_profile_chat"
UPLOAD_DIR = Path("workplace/chat-uploads")
MAX_FILE_CONTENT_CHARS = 15000


# ==========================================
# 1. 本地工具
# ==========================================

def _resolve_upload_path(file_url: str) -> Optional[str]:
    """将前端 URL 转换为服务器绝对路径。"""
    if not file_url.startswith("/uploads/"):
        return None
    relative = file_url.removeprefix("/uploads/")
    path = (UPLOAD_DIR / relative).resolve()
    if not str(path).startswith(str(UPLOAD_DIR.resolve())):
        return None
    return str(path) if path.exists() else None


def _read_file_impl(absolute_path: str) -> str:
    """底层文件读取，支持 PDF、DOCX、TXT。"""
    path = Path(absolute_path)
    if not path.exists():
        return f"文件不存在: {absolute_path}"
    if not path.is_file():
        return f"路径不是文件: {absolute_path}"

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pymupdf import open as pdf_open
        text_parts = []
        with pdf_open(str(path)) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        content = "\n".join(text_parts)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        content = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    elif suffix in {".txt", ".md", ".log"}:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    else:
        return f"不支持的文件类型: {suffix}（支持: .pdf, .docx, .txt, .md）"

    if not content or not content.strip():
        return "文件内容为空"
    if len(content) > MAX_FILE_CONTENT_CHARS:
        content = content[:MAX_FILE_CONTENT_CHARS] + "\n\n[...文档内容过长，已截断...]"
    return content


@tool("read_uploaded_file")
def read_uploaded_file(file_url: str) -> str:
    """读取用户上传的文档内容（PDF、Word、TXT 等）。

    Args:
        file_url: 前端上传后返回的文件 URL，格式如 /uploads/{user_id}/{filename}
    """
    absolute_path = _resolve_upload_path(file_url)
    if absolute_path is None:
        return f"无法解析文件路径: {file_url}。请确认文件 URL 格式正确且文件存在。"
    return _read_file_impl(absolute_path)


@tool("list_uploaded_files")
def list_uploaded_files(user_id: int) -> str:
    """列出用户上传的所有文件。"""
    user_dir = UPLOAD_DIR / str(user_id)
    if not user_dir.exists():
        return "用户暂无上传文件。"
    files = [f for f in user_dir.iterdir() if f.is_file()]
    if not files:
        return "用户暂无上传文件。"
    return "用户上传的文件列表:\n" + "\n".join(
        f"- {f.name} ({f.stat().st_size} bytes)" for f in files
    )


# 注册到 tools_manager
tools_manager.register_tool("read_uploaded_file", read_uploaded_file)
tools_manager.register_tool("list_uploaded_files", list_uploaded_files)


# ==========================================
# 2. Prompt 模板
# ==========================================

CLASSIFIER_PROMPT = """你是一个问题分类器。根据用户的最新消息判断回答这个问题是否需要调用外部工具。

需要调用工具的情况：
- 用户上传了文件并要求分析文件内容
- 用户明确要求生成思维导图、知识卡片等外部资源
- 用户要求执行代码或命令来验证某件事
- 需要读取外部文件才能回答

不需要工具、可以直接回答的情况：
- 概念解释、理论问题
- 代码编写、调试建议
- 学习方法建议、学习路径规划
- 一般性的知识问答
- 数学推导、算法分析
- 对话、闲聊、鼓励

## 用户最新消息
{user_message}

## 是否有附件
{has_attachments}

请只回答 "direct" 或 "tool_needed"，不要输出任何其他内容。"""

DIRECT_SYSTEM_PROMPT = """# 角色：高情商多模态流式学习导师 (Adaptive Learning Mentor)

你是一位拥有深厚教育心理学背景的计算机专业 AI 导师。你精通各类计算机学科知识（如数据结构、计算机网络、操作系统、人工智能等），擅长通过"苏格拉底式"的自然对话解答学生的疑问。

# 交互铁律
1. **画像约束**：初学者用通俗比喻+最简代码示例；高阶选手直接给优化代码和底层逻辑。
2. **遵守事实偏好**：尊重用户的个人事实与偏好。
3. **不要说套话**：直接进入主题。
4. **人格魅力**：语气如老友，多用鼓励性话语。

# 实时上下文参考

## 【当前学生画像 (指导你的辅导策略)】
{profile_context}

## 【已知关于该用户的特定事实偏好 (Long-term Fact Memory)】
{fact_context}
"""

TOOL_AGENT_SYSTEM_PROMPT = """# 角色：高情商多模态流式学习导师 (Adaptive Learning Mentor)

你是一位拥有深厚教育心理学背景的计算机专业 AI 导师。你精通各类计算机学科知识（如数据结构、计算机网络、操作系统、人工智能等），擅长通过"苏格拉底式"的自然对话解答学生的疑问。

# 核心职责
1. **文档理解**：用户上传文档时，调用 `read_uploaded_file` 工具读取内容后回答。
2. **学习资源生成**：判断是否需要为用户生成思维导图等辅助学习资源，自主调用 MCP 工具生成。
3. **千人千面辅导**：严格遵循【当前学生画像】调整语气、解释深度和比喻种类。

# 工具使用规则
1. **先读后答**：关于文档的提问必须先读取文档，不要凭空猜测。
2. **文档读取**：用户消息含 [Attached Files: ...] 时，调用 `read_uploaded_file` 读取后再回答。
3. **图片跳过**：图片文件暂不支持文本提取，跳过。
4. **资源辅助**：当发现学生对某个知识点理解困难时，可调用 markmap 等工具生成思维导图辅助理解。

# 交互铁律
1. **画像约束**：初学者用通俗比喻+最简代码示例；高阶选手直接给优化代码和底层逻辑。
2. **遵守事实偏好**：尊重用户的个人事实与偏好。
3. **不要说套话**：直接进入主题。
4. **人格魅力**：语气如老友，多用鼓励性话语。

# 实时上下文参考

## 【当前学生画像 (指导你的辅导策略)】
{profile_context}

## 【已知关于该用户的特定事实偏好 (Long-term Fact Memory)】
{fact_context}

## 【用户上传的文件信息】
{file_info_context}

{skills_context}
"""


# ==========================================
# 3. LangGraph State
# ==========================================

class TutorState(TypedDict, total=False):
    """TutorAgent 工作流状态。"""
    user_id: int
    session_id: str
    image_url: Optional[str]
    file_urls: Optional[List[str]]
    # 分类结果
    route: str  # "direct" | "tool_needed"
    # 渲染好的 system prompt
    system_prompt: str
    tool_system_prompt: str
    # 消息历史
    messages: Annotated[list[AnyMessage], add_messages]


# ==========================================
# 4. TutorAgent
# ==========================================

class TutorAgent:
    """智能辅导 Agent：两阶段 LangGraph 工作流。

    快速路径: classify → direct_answer → END（不绑工具，流式直出）
    工具路径: classify → agent(+tools) → agent ... → END
    """

    REQUIRED_TOOLS = ["read_uploaded_file", "list_uploaded_files", "read_file_safe"]
    REQUIRED_MCP = ["markmap"]
    REQUIRED_SKILLS: list[str] = []

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.7,
            streaming=True,
        )
        # 分类用轻量模型（更快、更省）
        self.classifier_llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.0,
            max_tokens=10,
        )
        self.module_name = MODULE_NAME
        self.global_session_id = GLOBAL_SESSION_ID
        self.graph = None
        self._tools: list[BaseTool] = []

    async def _ensure_graph(self) -> None:
        """延迟构建 LangGraph。"""
        if self.graph is not None:
            return

        self._tools = await tools_manager.get_agent_tools(
            tool_names=self.REQUIRED_TOOLS,
            mcp_services=self.REQUIRED_MCP,
        )
        logger.info("[TutorAgent] tools loaded: %s", [t.name for t in self._tools])

        graph = StateGraph(TutorState)

        # 节点
        graph.add_node("classify", self._classify_node)
        graph.add_node("direct_answer", self._direct_answer_node)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))

        # 边
        graph.add_edge(START, "classify")
        graph.add_conditional_edges("classify", self._route_after_classify)
        graph.add_edge("direct_answer", END)
        graph.add_conditional_edges("agent", self._should_use_tools)
        graph.add_edge("tools", "agent")

        self.graph = graph.compile()
        logger.info("[TutorAgent] StateGraph 构建完成 (两阶段路由)")

    # ------------------------------------------
    # 节点实现
    # ------------------------------------------

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

        # 快速规则：有附件直接走工具路径（不需要调 LLM 分类）
        if file_urls:
            logger.info("[TutorAgent] classify: tool_needed (有文件附件)")
            return {"route": "tool_needed"}

        # 调用轻量 LLM 分类
        has_attachments = "无附件" if not file_urls else f"有附件: {', '.join(file_urls)}"
        classify_prompt = CLASSIFIER_PROMPT.format(
            user_message=user_msg[:500],
            has_attachments=has_attachments,
        )

        try:
            result = await self.classifier_llm.ainvoke([HumanMessage(content=classify_prompt)])
            route = result.content.strip().lower()
            if "tool" in route:
                route = "tool_needed"
            else:
                route = "direct"
        except Exception as e:
            logger.warning(f"[TutorAgent] classify failed, fallback to direct: {e}")
            route = "direct"

        logger.info(f"[TutorAgent] classify: {route}")
        return {"route": route}

    @staticmethod
    def _route_after_classify(state: TutorState) -> str:
        """根据分类结果路由到对应节点。"""
        return state.get("route", "direct")

    async def _direct_answer_node(self, state: TutorState) -> dict:
        """快速路径：不带工具直接回答（流式）。"""
        system_prompt = state.get("system_prompt", "")
        messages = state.get("messages", [])

        full_messages: list[AnyMessage] = [SystemMessage(content=system_prompt)]
        # 只加入对话消息，跳过第一个 SystemMessage（已替换）
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                full_messages.append(msg)

        response = await self.llm.ainvoke(full_messages)
        return {"messages": [response]}

    async def _agent_node(self, state: TutorState) -> dict:
        """工具路径：绑定工具的 Agent 节点。"""
        messages = state.get("messages", [])

        # 如果没有 SystemMessage，注入工具路径的 system prompt
        has_system = any(isinstance(m, SystemMessage) for m in messages)
        if not has_system:
            tool_prompt = state.get("tool_system_prompt", "")
            messages = [SystemMessage(content=tool_prompt)] + list(messages)

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        logger.info(f"[TutorAgent] agent response, tool_calls={bool(response.tool_calls)}")
        return {"messages": [response]}

    @staticmethod
    def _should_use_tools(state: TutorState) -> str:
        """判断 agent 是否还要继续调用工具。"""
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return END

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
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

        # 1. 保存用户消息（含附件信息）
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
        direct_prompt = DIRECT_SYSTEM_PROMPT.format(
            profile_context=profile_str,
            fact_context=fact_str,
        )

        skills_ctx = ""
        skills_prompt = skills_manager.get_skill_instructions(self.REQUIRED_SKILLS)
        if skills_prompt:
            skills_ctx = "## 【已加载的专家技能】\n" + skills_prompt

        tool_prompt = TOOL_AGENT_SYSTEM_PROMPT.format(
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
        if image_url:
            pass  # TODO: 多模态模型接入
        if file_urls:
            full_msg += f"\n[Attached Files: {', '.join(file_urls)}]"
        initial_messages.append(HumanMessage(content=full_msg))

        # 7. 执行 LangGraph 并流式输出
        full_reply = ""
        tool_call_records: list[dict] = []  # 收集工具调用记录

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

                # 流式输出 LLM 文本
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and chunk.content:
                        text = chunk.content if isinstance(chunk.content, str) else ""
                        if text:
                            full_reply += text
                            yield text

                # 收集工具调用记录
                if kind == "on_tool_end":
                    tool_input = event.get("data", {}).get("input", {})
                    tool_output = event.get("data", {}).get("output", "")
                    tool_name = event.get("name", "unknown")
                    tool_call_records.append({
                        "tool": tool_name,
                        "args": tool_input if isinstance(tool_input, dict) else str(tool_input),
                        "result": str(tool_output)[:2000],  # 截断过长的结果
                        "status": "success",
                    })

        except Exception as e:
            logger.error(f"[Tutor] Graph execution error: {e}")
            yield f"服务器出错，请稍后再试: {e}"

        # 8. 保存 AI 回复（含工具调用记录）
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
