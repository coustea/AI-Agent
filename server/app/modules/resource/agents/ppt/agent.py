"""
PPT 演示文稿生成 Agent（骨架）。
基于 BaseResourceAgent 实现，预留用于后续生成结构化的 PPT 大纲及幻灯片内容。
"""

import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)


class PptState(BaseAgentState):
    """PPT 生成的专属状态字段"""
    # PPT 特有的输出字段
    slide_count: int
    outline: str
    speaker_notes: str
    file_path: Optional[str]


class PptAgent(BaseResourceAgent):
    """PPT 演示文稿生成 Agent。

    生成结构化的 PPT 大纲和幻灯片内容（骨架实现，预留后续扩展）。

    Attributes:
        name:           "PptAgent"
        agent_dir:      agents/ppt/，包含 prompt.md
        state_schema:   PptState，包含 slide_count/outline/speaker_notes/file_path
        method:         generate_ppt() — 对外入口
        output:         {success, content, file_path, slide_count, outline, speaker_notes, error}

    工作流: agent → validate(校验内容长度) → retry/end
    DAG 阶段: presentation（最后执行，依赖所有前置 Agent）
    黑板记忆: 读取 content.outline（内容大纲）和 mindmap.file_path（思维导图）
    用户画像: 读取 cognitive_style（认知风格）
    """
    def __init__(self) -> None:
        super().__init__(
            name="PptAgent",
            agent_dir=Path(__file__).parent,
            state_schema=PptState,
            temperature=0.3,
        )

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """黑板记忆：从前置 Agent 输出中提取关键上下文"""
        ctx = ""
        if "content" in shared_memory:
            content_data = shared_memory["content"]
            outline = content_data.get("outline", "")
            if outline:
                ctx += f"【参考内容大纲】\n{outline}\n"
        if "mindmap" in shared_memory:
            mindmap_data = shared_memory["mindmap"]
            file_path = mindmap_data.get("file_path", "")
            if file_path:
                ctx += f"【知识拓扑图】\n已生成思维导图: {file_path}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        if not profile: return ""
        parts = []
        if profile.get("cognitive_style"):
            parts.append(f"- 认知风格: {profile['cognitive_style']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> str:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            cognitive_style=user_profile.get("cognitive_style", "通用"),
        )
        return self._append_context_to_prompt(system_prompt, state)

    def _build_initial_human_message(self, state: Any) -> str:
        return f"请为主题 '{state.get('topic')}' 生成一份 PPT 演示文稿大纲。"

    async def _validate_node(self, state: Any) -> dict:
        """校验节点：提取 MCP 返回的文件路径"""
        messages = state.get("messages", [])
        content = ""
        file_path = None

        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content.strip()

            # 尝试从工具调用中提取文件路径
            if hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
                for tool_call in messages[-1].tool_calls:
                    if tool_call.get('name') == 'save_ppt_file':
                        args = tool_call.get('args', {})
                        file_path = args.get('file_path')
                        break

        # 从内容中提取文件路径（如果有）
        if not file_path and content:
            path_match = re.search(r'file_path[：:]\s*(.+?)(?:\n|$)', content)
            if path_match:
                file_path = path_match.group(1).strip()

        logger.info(f"[PptAgent] 校验 PPT 内容，文件路径: {file_path}")

        is_valid = bool(content and len(content) > 100)

        return {
            "is_valid": is_valid,
            "validation_feedback": "" if is_valid else "PPT 内容过短，请补充更多细节",
            "file_path": file_path,
        }

    async def generate_ppt(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
    ) -> dict[str, Any]:
        logger.info(f"[PptAgent] 收到生成请求: topic={topic}")
        await self._ensure_graph()

        initial_state: PptState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": user_profile or {},
            "shared_memory": shared_memory or {},
            "messages": [],
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            result = await self.graph.ainvoke(initial_state, {"recursion_limit": 15})
        except Exception as e:
            logger.error(f"[PptAgent] 工作流执行失败: {e}")
            return {"success": False, "content": "", "error": str(e)}

        messages = result.get("messages", [])
        final_content = messages[-1].content if messages else ""

        # 提取校验节点设置的文件路径
        file_path = result.get("file_path")

        return {
            "success": bool(final_content),
            "content": final_content,
            "file_path": file_path,
            "slide_count": final_content.count("##") if final_content else 0,
            "outline": final_content,
            "speaker_notes": "",
            "error": result.get("error")
        }


if __name__ == '__main__':
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()

    async def check_tools():
        agent = PptAgent()

        # 加载工具并打印详细信息
        print("=" * 50)
        print("[PptAgent] 工具加载检查")
        print("=" * 50)

        await agent._ensure_graph()

        # 本地工具
        local_tools = agent.plugin_manager.list_local_tools()
        print(f"\n[本地工具] ({len(local_tools)} 个): {local_tools}")

        # MCP 服务
        mcp_services = agent.plugin_manager.list_mcp_services()
        print(f"\n[MCP 服务] ({len(mcp_services)} 个): {mcp_services}")

        # Skills
        skills = agent.plugin_manager.list_skills()
        skill_names = [s["name"] for s in skills]
        print(f"\n[Skills] ({len(skills)} 个): {skill_names}")

        # 所有工具
        all_tools = agent._tools or []
        print(f"\n[所有工具] ({len(all_tools)} 个):")
        for t in all_tools:
            print(f"  - {t.name}: {t.description[:80]}..." if len(t.description) > 80 else f"  - {t.name}: {t.description}")

        # 检查是否有 PPT 相关工具
        ppt_tools = [t for t in all_tools if "ppt" in t.name.lower() or "slide" in t.name.lower() or "powerpoint" in t.description.lower()]
        print(f"\n[PPT 相关工具] ({len(ppt_tools)} 个): {[t.name for t in ppt_tools]}")

        print("\n" + "=" * 50)

    asyncio.run(check_tools())
