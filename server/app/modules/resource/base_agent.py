"""
基础资源 Agent 类。
提供统一的 LangGraph 工作流、工具加载、重试机制和强大的三层记忆结构（情景、长效、黑板）。
"""

import os
from abc import ABC, abstractmethod
from typing import Any, TypedDict, Optional, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.utils.tools_manager import tools_manager
from app.utils.skills_manager import skills_manager

load_dotenv()
logger = get_logger(__name__)

class BaseAgentState(TypedDict, total=False):
    """基础 Agent 状态字典，包含三层记忆架构。子类可继承此字典扩展内部字段。"""
    # 1. 任务级情景记忆 (Episodic Memory)
    major: str
    course: str
    topic: str
    gap: str
    
    # 2. 全局长效记忆 (Long-Term Memory - 来源于 tutor_agent 收集的用户画像)
    user_profile: dict[str, Any]
    
    # 3. 智能体间共享黑板 (Shared Blackboard - DAG 前置节点的输出)
    shared_memory: dict[str, Any]
    
    # 4. 执行与控制状态
    messages: Annotated[list[AnyMessage], add_messages]
    is_valid: bool
    validation_feedback: str
    retry_count: int
    max_retries: int
    error: Optional[str]


class BaseResourceAgent(ABC):
    """资源生成 Agent 基类。"""
    
    def __init__(
        self,
        name: str,
        prompt_template: str,
        required_tools: list[str],
        required_mcp: list[str],
        required_skills: list[str],
        state_schema: type = BaseAgentState,
        temperature: float = 0.3,
    ):
        self.name = name
        self.prompt_template = prompt_template
        self.required_tools = required_tools
        self.required_mcp = required_mcp
        self.required_skills = required_skills
        self.state_schema = state_schema
        
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=temperature,
        )
        self.graph = None
        self._tools = None

    async def _ensure_graph(self):
        """默认的图构建逻辑（生成 -> 工具 -> 校验 -> 重试）。如果子类图结构不同，可重写此方法。"""
        if self.graph is not None:
            return

        self._tools = await tools_manager.get_agent_tools(
            tool_names=self.required_tools, 
            mcp_services=self.required_mcp
        )

        graph = StateGraph(self.state_schema)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("validate", self._validate_node)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self._custom_tools_condition)
        graph.add_edge("tools", "agent")
        
        graph.add_conditional_edges(
            "validate",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )

        self.graph = graph.compile()
        logger.info(f"[{self.name}] 扁平化 StateGraph 构建完成")

    def _custom_tools_condition(self, state: Any) -> str:
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            return "tools"
        return "validate"

    def _should_retry(self, state: Any) -> str:
        if state.get("is_valid", False):
            return "end"
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry"
        return "end"

    @abstractmethod
    def _build_system_message(self, state: Any) -> SystemMessage:
        """子类必须实现：构建 System Prompt。"""
        pass

    @abstractmethod
    def _build_initial_human_message(self, state: Any) -> HumanMessage:
        """子类必须实现：构建初次请求的 Human Message。"""
        pass

    async def _agent_node(self, state: Any) -> dict:
        """标准的 LLM 调用节点，包含重试 Prompt 的注入。"""
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        feedback = state.get("validation_feedback", "")

        logger.info(f"[{self.name}] _agent_node: retry={retry_count}")

        if not messages:
            sys_msg = self._build_system_message(state)
            human_msg = self._build_initial_human_message(state)
            messages = [sys_msg, human_msg]
        elif retry_count > 0 and feedback and len(messages) < 3:
            messages.append(HumanMessage(
                content=f"上一次生成未通过校验，原因：{feedback}\n请根据上述反馈修正后重新生成。"
            ))

        llm_with_tools = self.llm.bind_tools(self._tools) if self._tools else self.llm
        response = await llm_with_tools.ainvoke(messages)
        
        return {"messages": [response]}

    @abstractmethod
    async def _validate_node(self, state: Any) -> dict:
        """
        子类必须实现：结构或质量校验。
        注意：失败时应返回 {"retry_count": state.get("retry_count", 0) + 1, "is_valid": False, "validation_feedback": "..."}
        """
        pass

    # ==========================================
    # 记忆层 (Memory Layer) 核心方法
    # ==========================================
    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """
        【黑板记忆】子类可按需重写此方法，从前置 Agent 的输出（shared_memory）中精准提取关键上下文。
        默认不提取，防止冗余 Token 干扰。
        """
        return ""

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        """
        【长效记忆】子类可重写此方法，从全局用户画像中提取自身关心的特征（如 QuizAgent 只提取 error_pattern）。
        默认提取所有有值的画像字段。
        """
        if not profile:
            return ""
        parts = [f"- {k}: {v}" for k, v in profile.items() if v]
        return "\n".join(parts) if parts else ""

    def _append_memory_and_skills(self, system_prompt: str, state: Any) -> str:
        """辅助方法：将技能库、长效用户画像记忆、动态黑板记忆注入到 System Prompt 中。"""
        # 1. 注入 Skills
        skills_prompt = skills_manager.get_skill_instructions(self.required_skills)
        if skills_prompt:
            system_prompt += f"\n\n## [操作规范 (Skills)]\n{skills_prompt}"

        # 2. 注入 Long-term Memory (基于 tutor_agent 收集的 User Profile)
        profile = state.get("user_profile", {})
        profile_str = self._format_user_profile(profile)
        if profile_str:
            system_prompt += (
                f"\n\n## [学习者画像 (Long-Term Memory)]\n"
                f"请根据以下提取自历史聊天的学习者个性化特征，针对性地调整你的生成策略（如难度、语气、偏好）：\n{profile_str}"
            )

        # 3. 注入 Shared Blackboard (前置 Agent 生成的成果)
        shared_memory = state.get("shared_memory", {})
        memory_ctx = self._extract_memory(shared_memory)
        if memory_ctx:
            system_prompt += (
                f"\n\n## [智能体协作黑板 (Shared Memory)]\n"
                f"以下是同一任务流水线中，前置智能体生成的核心资源片段。请参考以保持知识的连贯性和一致性：\n{memory_ctx}"
            )
            
        return system_prompt
