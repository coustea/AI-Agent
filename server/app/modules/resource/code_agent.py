"""
代码实操案例生成 Agent。

基于 LangGraph 的扁平化 ReAct 工作流，使得 Agent 可以自主调用本地环境工具执行代码校验。
"""

import os
import ast
import re
import json
from pathlib import Path
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

PROMPT_DIR = Path(__file__).parent / "prompt"
CODE_PROMPT_PATH = PROMPT_DIR / "code.md"

with open(CODE_PROMPT_PATH, "r", encoding="utf-8") as _f:
    CODE_PROMPT = _f.read()

# ==========================================
# State 定义
# ==========================================
class CodeState(TypedDict, total=False):
    """代码生成工作流状态。"""

    # 输入
    major: str
    course: str
    topic: str
    gap: str
    knowledge_level: str
    learning_pace: str

    # 上游 Agent 传递的上下文（DAG 编排）
    upstream_context: str

    # 统一的消息历史
    messages: Annotated[list[AnyMessage], add_messages]

    # 生成节点输出
    code_content: str
    detected_language: str

    # add_explanation 节点输出
    explained_content: str

    # 错误
    error: Optional[str]


# ==========================================
# 辅助函数
# ==========================================

_LANG_KEYWORDS: dict[str, list[str]] = {
    "python": ["python", "python3", "py"],
    "javascript": ["javascript", "js", "node", "nodejs"],
    "java": ["java"],
    "c": ["c", "clang"],
    "cpp": ["cpp", "c++", "cxx"],
    "sql": ["sql", "mysql", "postgresql"],
    "go": ["go", "golang"],
    "rust": ["rust", "rs"],
}

_CODE_BLOCK_RE = re.compile(r"```(\w+)\s*\n(.*?)\n```", re.DOTALL)


def _detect_language(code_content: str) -> str:
    """从 Markdown 代码块中检测编程语言。"""
    match = _CODE_BLOCK_RE.search(code_content)
    if match:
        lang_tag = match.group(1).lower()
        for canonical, aliases in _LANG_KEYWORDS.items():
            if lang_tag in aliases:
                return canonical
        return lang_tag
    return "unknown"


def _extract_code_block(code_content: str) -> str:
    """从 Markdown 中提取纯代码部分。"""
    match = _CODE_BLOCK_RE.search(code_content)
    if match:
        return match.group(2)
    return code_content


def _custom_tools_condition(state: CodeState) -> str:
    """判断是否调用了工具，决定下一步流向"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "add_explanation"


# ==========================================
# CodeAgent 类
# ==========================================
class CodeAgent:
    """代码实操案例生成智能体 (LangGraph StateGraph 模式)。"""

    # 配置当前 Agent 所需的最小权限工具与技能
    REQUIRED_TOOLS = ["read_file_safe", "safe_shell"]
    REQUIRED_MCP = []
    REQUIRED_SKILLS = []

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.2,
        )
        self.graph = None
        self._tools = None

    async def _ensure_graph(self):
        """延迟构建图，异步获取工具"""
        if self.graph is not None:
            return

        self._tools = await tools_manager.get_agent_tools(
            tool_names=self.REQUIRED_TOOLS, 
            mcp_services=self.REQUIRED_MCP
        )

        graph = StateGraph(CodeState)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("add_explanation", self._add_explanation)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", _custom_tools_condition)
        graph.add_edge("tools", "agent")
        graph.add_edge("add_explanation", END)

        self.graph = graph.compile()
        logger.info("[CodeAgent] 扁平化 StateGraph 构建完成")

    # ------------------------------------------
    # 节点：主控 LLM (生成与校验)
    # ------------------------------------------
    async def _agent_node(self, state: CodeState) -> dict:
        messages = state.get("messages", [])

        if not messages:
            system_prompt = CODE_PROMPT.format(
                major=state.get("major", "通用"),
                course=state.get("course", ""),
                topic=state.get("topic", ""),
                gap=state.get("gap", ""),
                knowledge_level=state.get("knowledge_level", "中等"),
                learning_pace=state.get("learning_pace", "中等"),
            )

            skills_prompt = skills_manager.get_skill_instructions(self.REQUIRED_SKILLS)
            if skills_prompt:
                system_prompt += "\n\n" + skills_prompt

            # 注入上游 Agent 上下文（DAG 编排）
            upstream_ctx = state.get("upstream_context", "")
            if upstream_ctx:
                system_prompt += (
                    "\n\n## [上游智能体协作上下文]\n"
                    "以下是同一任务中其他智能体已生成的输出，供你参考以保持代码案例与知识框架的一致性。\n"
                    + upstream_ctx
                )

            instruction = (
                "\n\n【重要指令】\n"
                "1. 请首先思考并生成对应的实操代码。\n"
                "2. 生成代码后，**必须**使用 `safe_shell` 工具来实际运行这段代码（例如通过 `echo \"代码\" > test.py && python3 test.py`）。\n"
                "3. 根据运行结果，如果出现错误请自我修正并再次运行验证。\n"
                "4. 只有在代码成功运行并验证无误后，再最终输出包含代码的 Markdown 结果。"
            )

            messages = [
                SystemMessage(content=system_prompt + instruction),
                HumanMessage(content=f"请为主题 '{state.get('topic')}' 生成一个完整的可运行代码案例。")
            ]

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        
        logger.info(f"[CodeAgent] LLM 返回 (包含 tool_calls={bool(response.tool_calls)})")
        return {"messages": [response]}

    # ------------------------------------------
    # 节点：添加教学注释 (并且提取最终的代码)
    # ------------------------------------------
    async def _add_explanation(self, state: CodeState) -> dict:
        messages = state.get("messages", [])
        code_content = ""

        if messages and isinstance(messages[-1], AIMessage):
            code_content = messages[-1].content

        language = _detect_language(code_content)
        logger.info(f"[CodeAgent] _add_explanation: 为 {language} 代码添加教学注释")

        explain_messages = [
            HumanMessage(
                content=(
                    "你是一位编程教学专家。请在以下代码案例中添加详细的编号式逐步解析：\n\n"
                    "1. 在代码中的关键行前添加编号行内注释（如 `# [1] 定义数据结构`）\n"
                    "2. 在代码块之前添加 2-3 句的背景说明\n"
                    "3. 在代码块之后添加编号解析列表，解释每一步的含义和设计思路\n\n"
                    f"编程语言：{language}\n\n"
                    f"原始代码：\n{code_content}\n\n"
                    "请输出完整的 Markdown 文档（包含说明 + 带注释的代码 + 解析）。"
                )
            ),
        ]

        try:
            response = await self.llm.ainvoke(explain_messages)
            explained = response.content.strip()
            logger.info(f"[CodeAgent] 教学注释添加完成，长度={len(explained)} 字符")
            return {
                "code_content": code_content,
                "detected_language": language,
                "explained_content": explained
            }
        except Exception as e:
            logger.error(f"[CodeAgent] _add_explanation 失败: {e}")
            return {
                "code_content": code_content,
                "detected_language": language,
                "explained_content": code_content
            }

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
    async def generate_code(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        knowledge_level: str = "中等",
        learning_pace: str = "中等",
        upstream_context: str = "",
    ) -> dict[str, Any]:
        """生成可运行的代码实操案例。"""
        logger.info(f"[CodeAgent] 收到生成请求: topic={topic}")

        await self._ensure_graph()

        initial_state: CodeState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "knowledge_level": knowledge_level,
            "learning_pace": learning_pace,
            "upstream_context": upstream_context,
            "messages": [],
            "code_content": "",
            "detected_language": "unknown",
            "explained_content": "",
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[CodeAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "content": "",
                "detected_language": "unknown",
                "code_only": "",
                "error": str(e),
            }

        explained = result.get("explained_content", "") or result.get("code_content", "")
        code_only = _extract_code_block(result.get("code_content", ""))
        language = result.get("detected_language", "unknown")

        file_path = None
        if explained:
            from app.modules.resource.tools.file_saver import save_to_workplace
            file_path = save_to_workplace("code", topic, explained, "md")

        return {
            "success": bool(explained),
            "content": explained,
            "file_path": file_path,
            "detected_language": language,
            "code_only": code_only,
            "error": result.get("error") if not explained else None,
        }


# 全局实例
code_agent = CodeAgent()
