"""
多模态教学脚本生成 Agent。

基于 LangGraph 扁平化工作流，使得 Agent 可以自主调用文件读取等工具辅助。
"""

import os
import re
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
MEDIA_PROMPT_PATH = PROMPT_DIR / "media.md"

with open(MEDIA_PROMPT_PATH, "r", encoding="utf-8") as _f:
    MEDIA_PROMPT = _f.read()

# ==========================================
# State 定义
# ==========================================
class MediaState(TypedDict, total=False):
    """多模态教学脚本工作流状态。"""

    # 输入
    major: str
    course: str
    topic: str
    gap: str
    cognitive_style: str

    # 上游 Agent 传递的上下文（DAG 编排）
    upstream_context: str

    # 统一消息历史
    messages: Annotated[list[AnyMessage], add_messages]

    # 输出
    script_content: str
    validation_passed: bool
    validation_feedback: str

    # 循环控制
    retry_count: int
    max_retries: int

    # 错误
    error: Optional[str]


# ==========================================
# 场景提取辅助
# ==========================================
_SCENE_RE = re.compile(r"###\s*场景\s*\d+", re.IGNORECASE)
_NARRATION_RE = re.compile(r"\*\*旁白\*\*[：:]\s*(.+?)(?=\n[-*]|\n###|\n---|\Z)", re.DOTALL)
_ANIMATION_RE = re.compile(r"\*\*画面\*\*[：:]\s*(.+?)(?=\n[-*]|\n###|\n---|\Z)", re.DOTALL)
_PLACEHOLDER_RE = re.compile(r"(TODO|TBD|FIXME|\.{3,}|待补充|待完善)", re.IGNORECASE)


def _count_scenes(content: str) -> int:
    """统计脚本中的场景数量。"""
    return len(_SCENE_RE.findall(content))


def _check_scene_completeness(content: str) -> list[str]:
    """检查每个场景是否完整，返回问题列表。"""
    issues: list[str] = []
    scenes = _SCENE_RE.split(content)

    # scenes[0] 是前言，之后交替为 [分隔符, 场景内容]
    scene_contents = scenes[1:]  # 去掉前言
    for i, scene_text in enumerate(scene_contents):
        if not scene_text.strip():
            continue
        scene_num = i + 1

        has_narration = _NARRATION_RE.search(scene_text) is not None
        has_animation = _ANIMATION_RE.search(scene_text) is not None

        if not has_narration:
            issues.append(f"场景 {scene_num} 缺少旁白内容")
        if not has_animation:
            issues.append(f"场景 {scene_num} 缺少画面/动画描述")

    return issues


def _check_placeholders(content: str) -> list[str]:
    """检查是否包含占位符文本。"""
    matches = _PLACEHOLDER_RE.findall(content)
    if matches:
        return [f"发现 {len(matches)} 处占位符文本（{set(matches)}），请替换为实际内容。"]
    return []


def _custom_tools_condition(state: MediaState) -> str:
    """判断是否调用了工具，决定下一步流向"""
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "validate_completeness"


# ==========================================
# MediaAgent 类
# ==========================================
class MediaAgent:
    """多模态教学脚本生成智能体 (LangGraph StateGraph 模式)。"""

    # 配置当前 Agent 所需的最小权限工具与技能
    REQUIRED_TOOLS = ["read_file_safe"]
    REQUIRED_MCP = []
    REQUIRED_SKILLS = []

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            temperature=0.4,
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

        graph = StateGraph(MediaState)

        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools))
        graph.add_node("validate_completeness", self._validate_completeness)

        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", _custom_tools_condition)
        graph.add_edge("tools", "agent")
        
        graph.add_conditional_edges(
            "validate_completeness",
            self._should_retry,
            path_map={"end": END, "retry": "agent"},
        )

        self.graph = graph.compile()
        logger.info("[MediaAgent] 扁平化 StateGraph 构建完成")

    # ------------------------------------------
    # 节点：主控 LLM
    # ------------------------------------------
    async def _agent_node(self, state: MediaState) -> dict:
        messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)
        feedback = state.get("validation_feedback", "")

        logger.info(f"[MediaAgent] _agent_node: retry={retry_count}")

        if not messages:
            system_prompt = MEDIA_PROMPT.format(
                major=state.get("major", "通用"),
                course=state.get("course", ""),
                topic=state.get("topic", ""),
                gap=state.get("gap", ""),
                cognitive_style=state.get("cognitive_style", "通用"),
            )

            skills_prompt = skills_manager.get_skill_instructions(self.REQUIRED_SKILLS)
            if skills_prompt:
                system_prompt += "\n\n" + skills_prompt

            # 注入上游 Agent 上下文（DAG 编排）
            upstream_ctx = state.get("upstream_context", "")
            if upstream_ctx:
                system_prompt += (
                    "\n\n## [上游智能体协作上下文]\n"
                    "以下是同一任务中其他智能体已生成的输出，供你参考以设计与内容配套的教学脚本。\n"
                    + upstream_ctx
                )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"请为主题 '{state.get('topic')}' 生成一份多模态教学脚本。")
            ]
        elif retry_count > 0 and feedback and len(messages) < 3:
            messages.append(HumanMessage(
                content=f"上一次脚本未通过校验，原因：{feedback}\n请根据上述反馈修正后重新生成。"
            ))

        llm_with_tools = self.llm.bind_tools(self._tools)
        response = await llm_with_tools.ainvoke(messages)
        
        return {"messages": [response]}

    # ------------------------------------------
    # 节点：完整性校验
    # ------------------------------------------
    async def _validate_completeness(self, state: MediaState) -> dict:
        messages = state.get("messages", [])
        content = ""

        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content.strip()

        error = state.get("error")

        if error or not content:
            return {
                "script_content": content,
                "validation_passed": False,
                "validation_feedback": error or "未生成脚本内容",
            }

        logger.info("[MediaAgent] _validate_completeness: 校验脚本完整性")

        all_issues: list[str] = []

        # 1. 场景数量检查
        scene_count = _count_scenes(content)
        if scene_count < 3:
            all_issues.append(f"场景数量不足（{scene_count} 个），至少需要 3 个场景。")

        # 2. 场景完整性检查
        scene_issues = _check_scene_completeness(content)
        all_issues.extend(scene_issues)

        # 3. 占位符检查
        placeholder_issues = _check_placeholders(content)
        all_issues.extend(placeholder_issues)

        # 4. 总长度检查
        narration_texts = _NARRATION_RE.findall(content)
        total_narration = sum(len(t) for t in narration_texts)
        if total_narration < 100:
            all_issues.append(
                f"旁白总字数过少（{total_narration} 字），需要更丰富的讲解内容。"
            )

        if all_issues:
            feedback = "；".join(all_issues)
            logger.warning(f"[MediaAgent] 校验失败: {feedback}")
            return {
                "script_content": content,
                "validation_passed": False,
                "validation_feedback": feedback,
            }

        logger.info(
            f"[MediaAgent] 校验通过: {scene_count} 个场景, "
            f"旁白总字数={total_narration}"
        )
        return {
            "script_content": content,
            "validation_passed": True,
            "validation_feedback": ""
        }

    # ------------------------------------------
    # 条件边
    # ------------------------------------------
    @staticmethod
    def _should_retry(state: MediaState) -> str:
        if state.get("validation_passed", False):
            return "end"
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry"
        return "end"

    # ------------------------------------------
    # 公共 API
    # ------------------------------------------
    async def generate_media(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        cognitive_style: str = "通用",
        upstream_context: str = "",
    ) -> dict[str, Any]:
        """生成多模态教学脚本。"""
        logger.info(f"[MediaAgent] 收到生成请求: topic={topic}")

        await self._ensure_graph()

        initial_state: MediaState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "cognitive_style": cognitive_style,
            "upstream_context": upstream_context,
            "messages": [],
            "script_content": "",
            "validation_passed": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[MediaAgent] 工作流执行失败: {e}")
            return {
                "success": False,
                "content": "",
                "error": str(e),
            }

        content = result.get("script_content", "")
        
        file_path = None
        if content:
            from app.modules.resource.tools.file_saver import save_to_workplace
            file_path = save_to_workplace("media", topic, content, "md")

        return {
            "success": bool(content),
            "content": content,
            "file_path": file_path,
            "error": result.get("error") if not content else None,
        }


# 全局实例
media_agent = MediaAgent()
