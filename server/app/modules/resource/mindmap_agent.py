"""
思维导图生成 Agent
基于 LangGraph 的扁平化 ReAct 工作流，使得 Agent 可以自主调用 MCP 工具和本地检查工具。
"""

import os
import re
import json
from pathlib import Path
from typing import TypedDict, Optional, Dict, Any, Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.utils.skills_manager import skills_manager
from app.utils.tools_manager import tools_manager

load_dotenv()
logger = get_logger(__name__)


PROMPT_DIR = Path(__file__).parent / "prompt"
MINDMAP_PROMPT_PATH = PROMPT_DIR / "mindmap.md"

with open(MINDMAP_PROMPT_PATH, "r", encoding="utf-8") as f:
    MINDMAP_GENERATOR_PROMPT = f.read()


# ==========================================
# State 定义
# ==========================================
class MindmapState(TypedDict, total=False):
    """思维导图工作流状态。"""

    # 输入
    major: str
    course: str
    gap: str
    need: str
    extra: str

    # 上游 Agent 传递的上下文（DAG 编排）
    upstream_context: str

    # 统一的消息历史
    messages: Annotated[list[AnyMessage], add_messages]

    # 输出
    file_path: Optional[str]
    html_content: Optional[str]
    agent_output: Optional[str]
    error: Optional[str]


# 学习需求映射
NEED_MAP = {
    "exam": "考前突击 (侧重考点与易错题)",
    "review": "课后复习 (侧重知识梳理与图解)",
    "deep": "深度探究 (侧重底层原理与拓展)",
    "practice": "实践应用 (侧重代码或实操案例)",
}


def _custom_tools_condition(state: MindmapState) -> str:
    """判断是否调用了工具，决定下一步流向"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "finalize"


# ==========================================
# MindmapGenerator 类
# ==========================================
class MindmapGenerator:
    """思维导图生成器 (LangGraph StateGraph 模式)"""

    # 配置当前 Agent 所需的最小权限工具与技能
    REQUIRED_TOOLS = ["read_file_safe", "safe_shell"]
    REQUIRED_MCP = ["markmap"]
    REQUIRED_SKILLS = []

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.1,
        )
        self.graph = None
        self._tools = None

    async def _ensure_graph(self):
        """延迟构建图，以便可以异步加载 MCP 工具"""
        if self.graph is not None:
            return

        # 根据所需的权限配置获取对应的工具列表
        self._tools = await tools_manager.get_agent_tools(
            tool_names=self.REQUIRED_TOOLS, 
            mcp_services=self.REQUIRED_MCP
        )
        
        graph = StateGraph(MindmapState)

        # 添加节点
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("finalize", self._finalize_node)

        # 构建扁平化流转
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", _custom_tools_condition)
        graph.add_edge("tools", "agent")  # 工具调用完毕后返回 agent 继续思考
        graph.add_edge("finalize", END)

        self.graph = graph.compile()
        logger.info("[MindmapAgent] 扁平化 StateGraph 构建完成")

    async def _agent_node(self, state: MindmapState) -> dict:
        """主控 LLM 节点"""
        messages = state.get("messages", [])
        
        # 第一次执行，注入 System Prompt
        if not messages:
            major = state.get("major", "通用")
            course = state.get("course", "待定")
            gap = state.get("gap", "")
            need_key = state.get("need", "review")
            need_text = NEED_MAP.get(need_key, need_key)
            extra = state.get("extra", "无")

            system_msg = MINDMAP_GENERATOR_PROMPT.format(
                major=major,
                course=course,
                gap=gap,
                need=need_text,
                extra=extra,
            )
            
            skills_prompt = skills_manager.get_skill_instructions(self.REQUIRED_SKILLS)
            if skills_prompt:
                system_msg += "\n\n" + skills_prompt

            # 注入上游 Agent 上下文（DAG 编排）
            upstream_ctx = state.get("upstream_context", "")
            if upstream_ctx:
                system_msg += (
                    "\n\n## [上游智能体协作上下文]\n"
                    "以下是同一任务中其他智能体已生成的输出，供你参考以保持内容一致性。\n"
                    + upstream_ctx
                )
            
            instruction = (
                "\n\n【重要指令】\n"
                "1. 请首先思考并直接调用 `markdown_to_mindmap` 工具，将你构思好的 Markdown 思维导图内容作为参数传入并生成 HTML。\n"
                "2. 工具会返回一个包含 `filePath` 的 JSON，或者返回文件路径文本。\n"
                "3. 根据该路径，使用 `read_file_safe` 或 `safe_shell` 工具（如 ls）检查文件是否成功生成。\n"
                "4. 确认无误后，向用户总结文件生成的路径即可结束对话。\n"
                "注意：不要在回答中直接输出长篇大论的 Markdown 源码，请直接传给工具！"
            )

            messages = [
                SystemMessage(content=system_msg + instruction),
                HumanMessage(content=f"请为知识短板 '{gap}' 生成思维导图。")
            ]

        # 绑定工具并调用 LLM
        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        
        logger.info(f"[MindmapAgent] LLM 返回 (包含 tool_calls={bool(response.tool_calls)})")
        return {"messages": [response]}

    async def _finalize_node(self, state: MindmapState) -> dict:
        """从历史消息中提取最终成果"""
        messages = state.get("messages", [])
        file_path = None
        html_content = None
        agent_output = ""

        if messages and isinstance(messages[-1], AIMessage):
            agent_output = messages[-1].content

        # 遍历历史寻找 markdown_to_mindmap 工具的返回结果
        for msg in messages:
            if isinstance(msg, ToolMessage) and msg.name == "markdown_to_mindmap":
                content = str(msg.content)
                # 尝试解析 JSON
                try:
                    res = json.loads(content)
                    if isinstance(res, dict) and "filePath" in res:
                        file_path = res["filePath"]
                    elif isinstance(res, list) and len(res) > 0 and "text" in res[0]:
                        # 有些 MCP Adapter 会返回带 text 的列表
                        inner_text = res[0]["text"]
                        inner_res = json.loads(inner_text)
                        if "filePath" in inner_res:
                            file_path = inner_res["filePath"]
                except Exception:
                    pass
                
                # 正则保底匹配路径
                if not file_path:
                    match = re.search(r"(/.*\.html)", content)
                    if match:
                        file_path = match.group(1)

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
            except Exception as e:
                logger.warning(f"[MindmapAgent] 无法读取生成的 HTML 文件 {file_path}: {e}")

        return {
            "file_path": file_path,
            "html_content": html_content,
            "agent_output": agent_output
        }

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
    async def generate_mindmap(
        self,
        gap: str,
        course: str = "",
        major: str = "通用",
        need: str = "review",
        extra: str = "",
        upstream_context: str = "",
    ) -> Dict[str, Any]:
        """生成思维导图。"""
        logger.info(f"[MindmapAgent] 收到生成请求: gap={gap}")

        await self._ensure_graph()

        initial_state: MindmapState = {
            "major": major,
            "course": course,
            "gap": gap,
            "need": need,
            "extra": extra,
            "upstream_context": upstream_context,
            "messages": [],
            "file_path": None,
            "html_content": None,
            "agent_output": None,
            "error": None,
        }

        try:
            # 增加 recursion_limit 防止工具陷入死循环
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 10})
        except Exception as e:
            logger.error(f"[MindmapAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "file_path": None,
                "html_content": None,
                "agent_output": "",
                "error": str(e),
            }

        success = bool(result.get("file_path"))
        return {
            "success": success,
            "file_path": result.get("file_path"),
            "html_content": result.get("html_content"),
            "agent_output": result.get("agent_output", ""),
            "error": result.get("error") if not success else None,
        }


# 全局实例
mindmap_generator = MindmapGenerator()


# ==========================================
# 测试入口
# ==========================================
async def main():
    """本地测试：生成一个思维导图并打印结果。"""
    import asyncio

    gap = "TCP三次握手为什么不是两次？"
    major = "计算机科学"
    course = "计算机网络"
    need = "review"
    extra = "尽量用通俗的比喻，多一些图解"

    print(f"正在生成思维导图: gap={gap}, major={major}, course={course}")
    print("-" * 50)

    result = await mindmap_generator.generate_mindmap(
        gap=gap, major=major, course=course, need=need, extra=extra
    )

    print(f"成功: {result['success']}")
    print(f"文件路径: {result.get('file_path')}")
    print(f"HTML 长度: {len(result.get('html_content') or '')} 字符")
    print(f"Agent 输出: {result.get('agent_output')}")
    if result.get("error"):
        print(f"错误: {result['error']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
