"""
PPT 演示文稿生成 Agent（骨架）。
基于 BaseResourceAgent 实现，预留用于后续生成结构化的 PPT 大纲及幻灯片内容。
"""

import os
from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.logging import get_logger
from app.modules.resource.base_agent import BaseResourceAgent, BaseAgentState

logger = get_logger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompt"
PPT_PROMPT_PATH = PROMPT_DIR / "ppt.md"

with open(PPT_PROMPT_PATH, "r", encoding="utf-8") as _f:
    PPT_PROMPT = _f.read()


# ==========================================
# State 定义
# ==========================================
class PptState(BaseAgentState):
    """PPT 生成的专属状态字段"""
    # 预留给后续具体的生成内容，例如：
    # ppt_outline: str
    # slide_contents: list[dict]
    pass


# ==========================================
# PptAgent 类
# ==========================================
class PptAgent(BaseResourceAgent):
    def __init__(self) -> None:
        super().__init__(
            name="PptAgent",
            prompt_template=PPT_PROMPT,
            required_tools=[],  # 后续可加入生成 PPT 文件的工具
            required_mcp=[],
            required_skills=["pptx"],  # 假设后续使用该技能
            state_schema=PptState,
            temperature=0.3,
        )

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """
        从黑板中提取上下文。
        PPT 通常需要【大纲】和【核心知识点】，可以直接提取 ContentAgent 的 outline。
        """
        ctx = ""
        if "content" in shared_memory:
            outline = shared_memory["content"].get("outline", "")
            if outline:
                ctx += f"【参考内容大纲】\n{outline}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        """提取决定 PPT 风格的用户画像"""
        if not profile: return ""
        parts = []
        if profile.get("cognitive_style"):
            parts.append(f"- 认知风格: {profile['cognitive_style']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> SystemMessage:
        user_profile = state.get("user_profile", {})
        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            cognitive_style=user_profile.get("cognitive_style", "通用"),
        )
        system_prompt = self._append_memory_and_skills(system_prompt, state)
        return SystemMessage(content=system_prompt)

    def _build_initial_human_message(self, state: Any) -> HumanMessage:
        return HumanMessage(content=f"请为主题 '{state.get('topic')}' 生成一份 PPT 演示文稿大纲。")

    async def _validate_node(self, state: Any) -> dict:
        """
        预留的校验节点。
        后期实现时，可在此处校验 PPT 的页数、结构完整性，甚至调用工具生成真实的 .pptx 文件。
        目前直接放行。
        """
        messages = state.get("messages", [])
        content = ""
        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content.strip()

        logger.info("[PptAgent] (占位) 校验 PPT 内容...")
        
        return {
            "is_valid": True,
            "validation_feedback": ""
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
        """对外的核心生成方法（占位）"""
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

        # 这里预留提取最终结果的逻辑
        messages = result.get("messages", [])
        final_content = messages[-1].content if messages else ""

        return {
            "success": bool(final_content),
            "content": final_content,
            "error": result.get("error")
        }

# 全局实例
ppt_agent = PptAgent()
