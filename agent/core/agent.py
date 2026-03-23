import logging
from pathlib import Path
from typing import Literal, Annotated, TypedDict, List, Optional, Dict, Protocol, Callable, Any
import asyncio

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """LangGraph 状态机"""
    messages: Annotated[list[BaseMessage], add_messages]
    task: str
    current_sop: str
    iteration_count: int  # 迭代次数


class MemoryInterface(Protocol):
    """记忆存储接口，用于解耦 Agent 与具体存储实现"""
    
    async def get_short_term_memory(self, session_id: str) -> List[BaseMessage]:
        """获取近期记忆（会话历史）"""
        ...
        
    async def get_long_term_memory(self, user_id: str) -> str:
        """获取长期记忆"""
        ...
        
    async def save_short_term_memory(self, session_id: str, messages: List[BaseMessage]) -> None:
        """保存近期记忆"""
        ...
        
    async def save_long_term_memory(self, user_id: str, memory: str) -> None:
        """保存长期记忆"""
        ...


class Agent:
    def __init__(
            self,
            llm: BaseChatModel,
            tools: Optional[List[BaseTool]] = None,
            system_prompt: str = "你是一个专业的智能助手。",  # 外部注入：业务人设
            prompts_dir: str = "src/agent/prompts",  # 框架内置：底层工作流逻辑
            skills_dir: Optional[str] = "src/agent/skills",  # 外部注入：业务知识库
            max_iterations: int = 5  # 最大迭代次数限制
    ):
        """
        初始化无状态 ReAct 智能体（完全独立，不依赖任何记忆存储）
        """
        self.llm = llm
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.skills_dir = skills_dir
        self.max_iterations = max_iterations

        # 加载框架内置的四个阶段工作流 Prompt
        self.internal_prompts = self._load_internal_prompts(prompts_dir)

        # 绑定工具
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.tools_node = ToolNode(self.tools)
        else:
            self.llm_with_tools = self.llm

        # 编译流转图 (纯无状态，不挂载 MemorySaver)
        self.graph = self._build_graph()

    # ==========================================
    # 🌟 对外暴露的核心接口 (完全无状态，不依赖任何服务层)
    # ==========================================

    async def chat(self, messages: List[BaseMessage], context: Optional[Dict[str, Any]] = None) -> str:
        """
        【非流式接口】传入完整的历史消息列表，阻塞执行并直接返回最终回答
        """
        # 取最后一条消息作为当前的任务意图，用于后续环节参考
        current_task = messages[-1].content if messages else ""

        initial_state = {
            "task": current_task,
            "messages": messages,
            "current_sop": ""
        }

        # 使用传入的上下文配置
        config = {"configurable": context or {}}

        try:
            final_state = await self.graph.ainvoke(initial_state, config=config)
            last_msg = final_state["messages"][-1].content

            if last_msg.startswith("✅ [最终答复]:\n"):
                last_msg = last_msg.replace("✅ [最终答复]:\n", "", 1)
            return last_msg.strip()
        except Exception as e:
            logger.error(f"非流式调用失败: {e}", exc_info=True)
            return f"❌ Agent 执行异常: {str(e)}"

    async def stream(self, messages: List[BaseMessage], context: Optional[Dict[str, Any]] = None):
        """
        【流式接口】传入完整的历史消息列表，实时吐出规范化的进度和消息事件 (适合 SSE 推送)
        """
        current_task = messages[-1].content if messages else ""

        initial_state = {
            "task": current_task,
            "messages": messages,
            "current_sop": ""
        }

        config = {"configurable": context or {}}

        try:
            async for output in self.graph.astream(initial_state, config=config):
                for node_name, state_update in output.items():
                    if node_name == "retrieve":
                        yield {"event": "status", "data": "📚 正在提取您的专属记忆与业务库..."}
                    elif node_name == "think":
                        yield {"event": "status", "data": "🤔 正在深度思考..."}
                    elif node_name == "plan":
                        state_messages = state_update.get("messages", [])
                        if state_messages:
                            last_msg = state_messages[-1]
                            # 如果有 tool_calls，说明大模型想调工具
                            if getattr(last_msg, "tool_calls", None):
                                tool_names = ", ".join([tc["name"] for tc in last_msg.tool_calls])
                                yield {"event": "status", "data": f"🛠️ 正在调用系统能力 ({tool_names})..."}
                            else:
                                # 否则说明得出结论，准备结束
                                final_ans = last_msg.content
                                if final_ans.startswith("✅ [最终答复]:\n"):
                                    final_ans = final_ans.replace("✅ [最终答复]:\n", "", 1)
                                yield {"event": "message", "data": final_ans.strip()}
                    elif node_name == "act":
                        yield {"event": "status", "data": "📥 能力调用成功，正在反思..."}
                    elif node_name == "reflect":
                        yield {"event": "status", "data": "👀 正在反思结果..."}

        except Exception as e:
            logger.error(f"流式调用失败: {e}", exc_info=True)
            yield {"event": "error", "data": f"❌ 执行异常: {str(e)}"}

    # ==========================================
    # 获取配置机制
    # ==========================================
    def get_agent_config(self) -> dict:
        """获取 Agent 当前挂载的能力配置"""
        loaded_tools = [t.name for t in self.tools] if self.tools else []
        loaded_skills = []
        if self.skills_dir:
            skills_path = Path(self.skills_dir)
            if skills_path.exists() and skills_path.is_dir():
                for folder in skills_path.iterdir():
                    if folder.is_dir() and (folder / "SKILL.md").exists():
                        loaded_skills.append(folder.name)

        llm_model_name = getattr(self.llm, "model_name", getattr(self.llm, "model", "Unknown Model"))
        return {"llm_model": llm_model_name, "tools": loaded_tools, "skills": loaded_skills}

    def print_agent_config(self) -> str:
        """格式化输出配置信息"""
        config = self.get_agent_config()
        tools_str = ", ".join(config["tools"]) if config["tools"] else "无"
        skills_str = ", ".join(config["skills"]) if config["skills"] else "无"

        return (
            "📦 [系统配置] 当前 Agent 已挂载能力：\n"
            f"   - 🧠 大语言模型 (LLM)  : {config['llm_model']}\n"
            f"   - 🛠️ 物理工具 (Tools) : {tools_str}\n"
            f"   - 📚 业务技能 (Skills): {skills_str}\n"
        )

    # ==========================================
    # 内部加载（缓存优化）
    # ==========================================
    def _read_skills_from_dir(self, task: str) -> str:
        """自动扫描并加载技能 SOP（带缓存）"""
        if not self.skills_dir:
            return ""
        skills_path = Path(self.skills_dir)
        if not skills_path.exists() or not skills_path.is_dir():
            return ""

        sops = []
        for folder in skills_path.iterdir():
            if folder.is_dir() and (folder / "SKILL.md").exists():
                with open(folder / "SKILL.md", "r", encoding="utf-8") as f:
                    sops.append(f"### 技能: {folder.name}\n{f.read()}")

        if not sops:
            return ""
        return "【当前可用的业务 SOP 指南】\n\n" + "\n\n".join(sops)

    def _load_internal_prompts(self, prompts_dir: str) -> Dict[str, str]:
        """加载框架底层逻辑 Prompt（带缓存）"""
        p_dir = Path(prompts_dir)
        prompts = {"think": "", "plan": "", "act": "", "reflect": ""}

        if not p_dir.exists():
            return prompts

        files_map = {
            "think": "01_think.md",
            "plan": "02_plan.md",
            "act": "03_act.md",
            "reflect": "04_reflect.md"
        }

        for key, filename in files_map.items():
            file_path = p_dir / filename
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    prompts[key] = f.read()

        return prompts

    # ==========================================
    # 节点定义 (Nodes) - 完全解耦
    # ==========================================
    def retrieve_node(self, state: AgentState):
        """节点 0：仅获取业务 SOP（完全独立，不访问任何记忆存储）"""
        # 加载 SOP（业务知识库）
        sop_content = self._read_skills_from_dir(state["task"])

        # Agent 不再访问任何记忆存储，所有记忆由后端服务提供
        # 仅返回业务 SOP 作为上下文
        combined_context = sop_content.strip()
        
        # 初始化或保持迭代计数
        iteration_count = state.get("iteration_count", 0)
        return {"current_sop": combined_context, "iteration_count": iteration_count}

    async def think_node(self, state: AgentState):
        sys_content = (
            f"{self.system_prompt}\n\n"
            f"{state.get('current_sop', '')}\n\n"
            f"{self.internal_prompts['think']}"
        )
        messages = [SystemMessage(content=sys_content)] + state["messages"]

        response = await self.llm.ainvoke(messages)
        return {"messages": [AIMessage(content=f"🤔 [思考分析]:\n{response.content}")]}

    async def plan_node(self, state: AgentState):
        sys_content = (
            f"{self.system_prompt}\n\n"
            f"{state.get('current_sop', '')}\n\n"
            f"{self.internal_prompts['plan']}\n\n"
            f"{self.internal_prompts['act']}"
        )
        messages = [SystemMessage(content=sys_content)] + state["messages"]

        response = await self.llm_with_tools.ainvoke(messages)

        if not response.tool_calls:
            response.content = f"✅ [最终答复]:\n{response.content}"
        else:
            tool_names = [tc["name"] for tc in response.tool_calls]
            response.content = f"🛠️ [规划动作]: 准备调用工具 {', '.join(tool_names)}"

        return {"messages": [response]}

    async def reflect_node(self, state: AgentState):
        sys_content = (
            f"{self.system_prompt}\n\n"
            f"{self.internal_prompts['reflect']}"
        )
        messages = [SystemMessage(content=sys_content)] + state["messages"]

        response = await self.llm.ainvoke(messages)
        # 增加迭代计数
        iteration_count = state.get("iteration_count", 0) + 1
        return {
            "messages": [AIMessage(content=f"👀 [结果反思]:\n{response.content}")],
            "iteration_count": iteration_count
        }

    # ==========================================
    # 路由与流转构建
    # ==========================================
    def should_act(self, state: AgentState) -> Literal["act", "__end__"]:
        """判断是否需要执行工具"""
        last_message = state["messages"][-1]

        # 检查最大迭代次数
        iteration_count = state.get("iteration_count", 0)
        if iteration_count >= self.max_iterations:
            # 达到最大迭代次数，强制结束
            return "__end__"

        # 如果有工具调用，执行
        if getattr(last_message, "tool_calls", None):
            return "act"
        return "__end__"

    def should_continue(self, state: AgentState) -> Literal["think", "__end__"]:
        """判断是否继续循环（reflect 之后）"""
        last_message = state["messages"][-1]

        # 检查最大迭代次数
        iteration_count = state.get("iteration_count", 0) + 1
        if iteration_count >= self.max_iterations:
            return "__end__"

        # 如果最后一条消息包含 "✅ [最终答复]" 或没有工具调用，结束
        content = last_message.content if hasattr(last_message, "content") else ""
        if "✅ [最终答复]" in content or not getattr(last_message, "tool_calls", None):
            return "__end__"

        return "think"

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("think", self.think_node)
        workflow.add_node("plan", self.plan_node)

        if self.tools:
            workflow.add_node("act", self.tools_node)
            workflow.add_node("reflect", self.reflect_node)

        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "think")
        workflow.add_edge("think", "plan")

        if self.tools:
            workflow.add_conditional_edges("plan", self.should_act, {"act": "act", "__end__": END})
            workflow.add_edge("act", "reflect")
            workflow.add_conditional_edges("reflect", self.should_continue, {"think": "think", "__end__": END})
        else:
            workflow.add_edge("plan", END)

        # 🌟 彻底转为无状态 (不挂载 checkpointer)
        return workflow.compile()