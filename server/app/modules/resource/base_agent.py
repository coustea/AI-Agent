"""
基础资源 Agent 类。
提供统一的 LangGraph 工作流、工具加载、重试机制和三层记忆结构（情景、长效、黑板）。

每个 Agent 拥有独立目录，自动从目录中加载：
  - prompt.md       → 系统提示词模板
  - skills/         → 技能文件（SKILL.md）
  - tools/          → 本地工具（@tool 装饰器函数）
"""

import asyncio
import importlib
import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypedDict, Optional, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AnyMessage
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.utils.paths import WORKPLACE_DIR
from app.utils.plugin_manager import PluginManager

load_dotenv()

# 清除代理环境变量，避免 ChatOpenAI 因不支持的代理协议（如 socks://）初始化失败
for _pk in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
    os.environ.pop(_pk, None)

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────
# 常量定义
# ──────────────────────────────────────────────────────────────


class BlackboardKeys:
    """黑板共享内存的标准键名常量"""
    CONTENT = "content"
    MINDMAP = "mindmap"
    CODE = "code"
    QUIZ = "quiz"
    READING = "reading"
    IMAGE = "image"
    VIDEO = "video"
    PPT = "ppt"

    @classmethod
    def all_keys(cls) -> list[str]:
        """获取所有标准键名"""
        return [cls.CONTENT, cls.MINDMAP, cls.CODE, cls.QUIZ, cls.READING, cls.IMAGE, cls.VIDEO, cls.PPT]


# ──────────────────────────────────────────────────────────────
# State 定义
# ──────────────────────────────────────────────────────────────


class BaseAgentState(TypedDict, total=False):
    """基础 Agent 状态字典，包含三层记忆架构。子类可继承此字典扩展内部字段。

    字段语义说明：
      - major:    学生所属专业（上下文，可为空）
      - course:   当前锾课程名称
      - topic:    请求详细知识点（如“二叉树遍历算法”），应比 gap 更具体
      - gap:      学生的知识短板描述（如“不理解递归”）
      - user_profile: 用户画像字典，来自长效记忆
      - shared_memory: 前置 Agent 输出的黑板共享上下文
    """
    # 1. 任务级情景记忆 (Episodic Memory)
    major: str
    course: str
    topic: str   # 知识点（具体请求对象）
    gap: str     # 学生知识短板

    # 2. 全局长效记忆 (Long-Term Memory)
    user_profile: dict[str, Any]

    # 3. 智能体间共享黑板 (Shared Blackboard)
    shared_memory: dict[str, Any]

    # 4. 执行与控制状态
    messages: Annotated[list[AnyMessage], add_messages]
    is_valid: bool
    validation_feedback: str
    retry_count: int
    max_retries: int
    error: Optional[str]


# ──────────────────────────────────────────────────────────────
# BaseResourceAgent
# ──────────────────────────────────────────────────────────────


class BaseResourceAgent(ABC):
    """资源生成 Agent 基类。

    从 agent_dir 自动发现并加载所有资源：
      - agent_dir/prompt.md   → 系统提示词模板
      - agent_dir/skills/     → 技能文件目录（可选）
      - agent_dir/tools/      → 本地 @tool 工具（可选）
    """

    def __init__(
        self,
        name: str,
        agent_dir: Path,
        state_schema: type = BaseAgentState,
        temperature: float = 0.3,
        plugin_manager: PluginManager | None = None,
    ):
        """初始化 Agent，配置 LLM、插件管理器及并发锁。"""
        self.name = name
        self.agent_dir = agent_dir
        self.state_schema = state_schema

        # 初始化 LLM 实例，默认使用 gpt-4o-mini
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=temperature,
        )
        self.graph = None
        self._tools: list[BaseTool] | None = None

        # 初始化插件管理器，负责加载本地工具与技能
        if plugin_manager is not None:
            self.plugin_manager = plugin_manager
        else:
            agent_type = name.lower().replace("agent", "")
            self.plugin_manager = PluginManager(
                skills_path=self.agent_dir / "skills",
                workspace=WORKPLACE_DIR / agent_type,
            )

        # P5：应对并发初始化竞态，确保 graph 唯一
        self._init_lock = asyncio.Lock()

        # 加载 prompt 模板
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """从 agent_dir/prompt.md 加载提示词模板。"""
        prompt_path = self.agent_dir / "prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"[{self.name}] prompt 文件不存在: {prompt_path}")
        content = prompt_path.read_text(encoding="utf-8")
        logger.info(f"[{self.name}] 加载 prompt: {prompt_path}")
        return content

    def _load_local_tools(self) -> list[BaseTool]:
        """从 agent_dir/tools/ 自动发现本地工具。"""
        tools_dir = self.agent_dir / "tools"
        if not tools_dir.exists() or not tools_dir.is_dir():
            return []

        local_tools: list[BaseTool] = []
        # 扫描并加载所有 .py 文件中的 BaseTool 实例
        for py_file in sorted(tools_dir.glob("*.py")):
            if py_file.name != "__init__.py" and py_file.name.startswith("_"):
                continue
            found = self._discover_tools_in_module(py_file)
            local_tools.extend(found)

        if local_tools:
            logger.info(f"[{self.name}] 本地工具: {[t.name for t in local_tools]}")
        return local_tools

    def _discover_tools_in_module(self, py_file: Path) -> list[BaseTool]:
        """动态导入 Python 模块并提取 BaseTool 实例。"""
        tools_found: list[BaseTool] = []
        module_name = f"_agent_tools_{self.name}_{py_file.stem}"

        try:
            # 使用 importlib 动态加载工具模块
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                return []
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            logger.error(f"[{self.name}] 导入工具模块失败 ({py_file}): {e}")
            return []

        # 遍历模块属性，提取所有继承自 BaseTool 的工具
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name, None)
            if isinstance(obj, BaseTool):
                tools_found.append(obj)

        return tools_found

    # ══════════════════════════════════════════════════════════
    # 图构建（LangGraph StateGraph）
    # ══════════════════════════════════════════════════════════

    async def _ensure_graph(self):
        """P5：协程安全的图构建入口（double-check + asyncio.Lock）。"""
        if self.graph is not None:
            return
        async with self._init_lock:
            if self.graph is not None:  # double-check
                return
            await self._load_tools()
            self.graph = await self._build_graph()
            logger.info(f"[{self.name}] LangGraph 工作流构建完成")

    async def _load_tools(self) -> None:
        """P1：工具加载阶段，聚合本地工具和技能工具。"""
        local_tools = self._load_local_tools()
        if local_tools:
            self.plugin_manager.register(local_tools)
        await self.plugin_manager.load_all()
        self._tools = await self.plugin_manager.get_tools()
        logger.info(
            f"[{self.name}] 共加载 {len(self._tools)} 个工具: "
            f"{[t.name for t in self._tools]}"
        )

    async def _build_graph(self):
        """P1：构建默认图拓扑（生成 → 工具 → 校验 → 重试）。"""
        graph = StateGraph(self.state_schema)
        # 添加核心节点：生成、工具执行、产物校验
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("validate", self._validate_node)
        
        # 定义边：循环执行直至校验通过或重试耗尽
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self._custom_tools_condition) # 决定是调工具还是去校验
        graph.add_edge("tools", "agent")
        graph.add_conditional_edges(
            "validate",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )
        return graph.compile()

    def _custom_tools_condition(self, state: Any) -> str:
        """判断 LLM 是否发起了工具调用请求。"""
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools" # 跳转至工具执行节点
        return "validate" # 跳转至结果校验节点

    def _should_retry(self, state: Any) -> str:
        """控制重试逻辑，当校验失败且未达最大重试次数时触发重试。"""
        if state.get("error"):
            return "end" # 发生不可恢复错误，直接结束
        if state.get("is_valid", False):
            return "end" # 校验通过，正常结束
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry" # 允许重试，返回生成节点
        return "end" # 重试耗尽，强制结束

    # ══════════════════════════════════════════════════════════
    # 抽象方法（子类必须实现）
    # ══════════════════════════════════════════════════════════

    @abstractmethod
    def _build_system_message(self, state: Any) -> str:
        """子类必须实现：构建系统提示词，定义 Agent 角色。"""
        ...

    @abstractmethod
    def _build_initial_human_message(self, state: Any) -> str:
        """子类必须实现：构建用户请求消息，定义具体任务。"""
        ...

    @abstractmethod
    async def _validate_node(self, state: Any) -> dict:
        """子类必须实现：校验节点逻辑，检查产物质量。"""
        ...

    # ══════════════════════════════════════════════════════════
    # 公共节点实现
    # ══════════════════════════════════════════════════════════

    def _truncate_messages(
        self,
        messages: list[AnyMessage],
        keep_last_n: int = 20,
    ) -> list[AnyMessage]:
        """截断消息历史，保留系统消息和最近 N 条对话，防止上下文溢出。"""
        if len(messages) <= keep_last_n + 1:
            return messages

        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]

        if len(non_system) <= keep_last_n:
            return messages

        truncated = system_msgs + non_system[-keep_last_n:] # 滑动窗口裁剪
        logger.info(
            f"[{self.name}] 消息截断: {len(messages)} → {len(truncated)} 条"
        )
        return truncated

    async def _agent_node(self, state: Any) -> dict:
        """标准的 LLM 调用节点，负责生成内容及处理重试反馈。"""
        existing_messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        feedback = state.get("validation_feedback", "")

        logger.info(f"[{self.name}] _agent_node: existing_msgs={len(existing_messages)}, retry={retry_count}")

        new_messages = []
        
        # 初次执行：构建完整的上下文环境
        if not existing_messages:
            sys_content = self._build_system_message(state)
            human_content = self._build_initial_human_message(state)
            
            new_messages = [
                SystemMessage(content=str(sys_content)),
                HumanMessage(content=str(human_content)),
            ]
            llm_messages = new_messages
        else:
            # 重试流程：注入上一次的失败反馈
            if retry_count > 0 and feedback:
                last_msg_content = existing_messages[-1].content if existing_messages else ""
                if not isinstance(last_msg_content, str) or "上一次生成未通过校验" not in last_msg_content:
                    new_messages.append(HumanMessage(
                        content=f"上一次生成未通过校验，原因：{feedback}\n请根据上述反馈修正后重新生成。"
                    ))
            
            llm_messages = list(existing_messages) + new_messages

        # 裁剪上下文，确保符合模型窗口限制
        max_history = int(os.getenv("MAX_MESSAGE_HISTORY", "20"))
        llm_messages = self._truncate_messages(llm_messages, keep_last_n=max_history)

        # 规范化结构化 ToolMessage 内容，避免部分模型接口拒绝 list 类型 content
        from langchain_core.messages import ToolMessage
        safe_llm_messages = []
        for msg in llm_messages:
            if getattr(msg, "type", "") == "tool" and isinstance(msg.content, list):
                texts = []
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    else:
                        texts.append(str(block))
                # 创建具有纯文本内容的新的 ToolMessage
                safe_msg = ToolMessage(
                    content="\n".join(texts), 
                    tool_call_id=msg.tool_call_id, 
                    name=msg.name, 
                    status=getattr(msg, "status", "success")
                )
                safe_llm_messages.append(safe_msg)
            else:
                safe_llm_messages.append(msg)
        llm_messages = safe_llm_messages

        try:
            # 绑定工具箱
            llm_with_tools = self.llm.bind_tools(self._tools) if self._tools else self.llm

            # 设置超时保护，避免长连接挂起
            llm_timeout = int(os.getenv("LLM_TIMEOUT", "300"))
            try:
                response = await asyncio.wait_for(
                    llm_with_tools.ainvoke(llm_messages),
                    timeout=llm_timeout,
                )
            except asyncio.TimeoutError:
                logger.error(f"[{self.name}] LLM 调用超时")
                return {"error": f"LLM 调用超时", "is_valid": False}
            
            # P6：针对非原生支持工具调用格式的模型进行文本补丁处理
            if isinstance(response, AIMessage) and not response.tool_calls and self._tools:
                content = response.content.strip()
                if (content.startswith("```json") and content.endswith("```")) or (content.startswith("{") and content.endswith("}")):
                    try:
                        # 尝试将文本形式的 JSON 解析为工具调用对象
                        json_str = content[7:-3].strip() if content.startswith("```json") else content
                        data = json.loads(json_str)
                        if isinstance(data, dict) and "name" in data:
                            response.tool_calls = [{
                                "name": data["name"],
                                "args": data.get("arguments", data.get("args", {})),
                                "id": f"call_{int(time.time())}",
                                "type": "tool_call"
                            }]
                    except: pass

            return {"messages": new_messages + [response]}
            
        except Exception as e:
            logger.error(f"[{self.name}] LLM 接口调用异常: {e}")
            return {"error": str(e), "is_valid": False}

    # ══════════════════════════════════════════════════════════
    # 记忆层辅助方法
    # ══════════════════════════════════════════════════════════

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """从黑板共享内存中提取协作上下文（子类可重写）。"""
        return ""

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        """将用户画像（长效记忆）格式化为 Prompt 指令。"""
        if not profile:
            return ""
        parts = [f"- {k}: {v}" for k, v in profile.items() if v]
        return "\n".join(parts) if parts else ""

    def _append_context_to_prompt(self, system_prompt: str, state: Any) -> str:
        """三层记忆注入逻辑：将画像、黑板、知识库动态拼接到 System Prompt。"""
        # 1. 注入长效记忆（用户画像）
        profile = state.get("user_profile", {})
        profile_str = self._format_user_profile(profile)
        if profile_str:
            system_prompt += f"\n\n## [学习者画像 (Long-Term Memory)]\n{profile_str}"

        # 2. 注入共享黑板（Agent 间协作上下文）
        shared_memory = state.get("shared_memory", {})
        memory_ctx = self._extract_memory(shared_memory)
        if memory_ctx:
            system_prompt += f"\n\n## [协作上下文 (Shared Memory)]\n{memory_ctx}"

        # 3. 注入外部知识（RAG 检索内容）
        kb_context = state.get("knowledge_base_context", "")
        if kb_context:
            system_prompt += f"\n\n## [知识库参考]\n{kb_context}"

        return system_prompt

    @staticmethod
    def format_blackboard_summary(shared_memory: dict[str, Any]) -> str:
        """格式化黑板共享内存为可读摘要，用于日志输出。"""
        if not shared_memory:
            return "（暂无前置资源）"

        summary_parts = []
        for key, value in shared_memory.items():
            if isinstance(value, dict) and value.get("success"):
                summary_parts.append(f"- {value.get('type', key)}: {value.get('file_path', str(len(str(value.get('content', '')))) + ' 字')}")
        return "\n".join(summary_parts) if summary_parts else "（暂无可用资源）"
