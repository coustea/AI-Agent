import logging
from pathlib import Path
from typing import Literal, Annotated, TypedDict, List, Optional, Dict

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


class Agent:
    def __init__(
            self,
            llm: BaseChatModel,
            tools: Optional[List[BaseTool]] = None,
            system_prompt: str = "你是一个专业的智能助手。",  # 外部注入：业务人设
            prompts_dir: str = "agent/prompts",  # 框架内置：底层工作流逻辑
            skills_dir: Optional[str] = "agent/skills"  # 外部注入：业务知识库
    ):
        """
        初始化四节点 ReAct 智能体
        """
        self.llm = llm
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.skills_dir = skills_dir

        # 加载框架内置的四个阶段工作流 Prompt
        self.internal_prompts = self._load_internal_prompts(prompts_dir)

        # 绑定工具
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.tools_node = ToolNode(self.tools)
        else:
            self.llm_with_tools = self.llm

        # 编译流转图
        self.graph = self._build_graph()

    # ==========================================
    # 🌟 新增：配置与能力审查机制
    # ==========================================
    def get_agent_config(self) -> dict:
        """获取 Agent 当前挂载的能力配置 (返回字典格式，方便代码调用)"""
        # 获取工具名称
        loaded_tools = [t.name for t in self.tools] if self.tools else []

        # 获取技能名称
        loaded_skills = []
        if self.skills_dir:
            skills_path = Path(self.skills_dir)
            if skills_path.exists() and skills_path.is_dir():
                for folder in skills_path.iterdir():
                    if folder.is_dir() and (folder / "SKILL.md").exists():
                        loaded_skills.append(folder.name)

        # 尝试安全地获取 LLM 的模型名称
        llm_model_name = getattr(self.llm, "model_name", getattr(self.llm, "model", "Unknown Model"))

        return {
            "llm_model": llm_model_name,
            "tools": loaded_tools,
            "skills": loaded_skills
        }

    def print_agent_config(self) -> str:
        """格式化输出 Agent 的配置信息，方便日志打印"""
        config = self.get_agent_config()
        tools_str = ", ".join(config["tools"]) if config["tools"] else "无"
        skills_str = ", ".join(config["skills"]) if config["skills"] else "无"

        output = (
            "📦 [系统配置] 当前 Agent 已挂载能力：\n"
            f"   - 🧠 大语言模型 (LLM)  : {config['llm_model']}\n"
            f"   - 🛠️ 物理工具 (Tools) : {tools_str}\n"
            f"   - 📚 业务技能 (Skills): {skills_str}\n"
        )
        return output

    # ==========================================
    # 内部加载与文件读取
    # ==========================================
    def _load_internal_prompts(self, prompts_dir: str) -> Dict[str, str]:
        """按阶段加载框架内置的底层逻辑 Prompt"""
        p_dir = Path(prompts_dir)
        prompts = {"think": "", "plan": "", "act": "", "reflect": ""}

        if not p_dir.exists():
            logger.warning(f"⚠️ 内置 Prompts 目录未找到: {prompts_dir}。框架将降级运行。")
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

    def _read_skills_from_dir(self, task: str) -> str:
        """自动扫描并加载技能 SOP"""
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

    # ==========================================
    # 节点定义 (Nodes)
    # ==========================================
    def retrieve_node(self, state: AgentState):
        """节点 0：获取 SOP"""
        return {"current_sop": self._read_skills_from_dir(state["task"])}

    async def think_node(self, state: AgentState):
        """节点 1：意图理解与状态分析 (Think)"""
        # 缝合逻辑：用户人设 + 业务SOP + 框架思考规范
        sys_content = (
            f"{self.system_prompt}\n\n"
            f"{state.get('current_sop', '')}\n\n"
            f"{self.internal_prompts['think']}"
        )
        messages = [SystemMessage(content=sys_content)] + state["messages"]

        response = await self.llm.ainvoke(messages)

        thought_msg = AIMessage(content=f"🤔 [思考分析]:\n{response.content}")
        return {"messages": [thought_msg]}

    async def plan_node(self, state: AgentState):
        """节点 2：制定动作或生成最终答案 (Plan)"""
        # 缝合逻辑：用户人设 + 业务SOP + 框架规划规范 + 框架执行红线约束
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
        """节点 4：评估工具返回结果 (Reflect)"""
        # 缝合逻辑：用户人设 + 框架反思规范
        sys_content = (
            f"{self.system_prompt}\n\n"
            f"{self.internal_prompts['reflect']}"
        )
        messages = [SystemMessage(content=sys_content)] + state["messages"]

        response = await self.llm.ainvoke(messages)

        reflect_msg = AIMessage(content=f"👀 [结果反思]:\n{response.content}")
        return {"messages": [reflect_msg]}

    # ==========================================
    # 路由与流转构建
    # ==========================================

    def should_act(self, state: AgentState) -> Literal["act", "__end__"]:
        """路由：根据 Plan 节点的决策流转"""
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "act"
        return "__end__"

    def _build_graph(self):
        """构建严格的 Think -> Plan -> Act -> Reflect 闭环"""
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
            workflow.add_edge("reflect", "think")
        else:
            workflow.add_edge("plan", END)

        return workflow.compile()