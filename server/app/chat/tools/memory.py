from langchain_core.tools import BaseTool, tool
from app.memory import get_memory_service

def build_memory_tools(user_id: int) -> list[BaseTool]:
    """构建记忆相关的大模型工具（闭包注入 user_id）。"""

    @tool
    async def get_user_profile() -> str:
        """获取当前用户的学习画像（如学习风格、优势弱点、基础水平等）。当你需要调整回答风格或了解用户背景时使用此工具。"""
        svc = get_memory_service()
        profile_md = await svc.get_profile_markdown(user_id)
        if not profile_md.strip() or "暂无画像信息" in profile_md:
            return "当前用户暂无可用画像信息。"
        return profile_md

    @tool
    async def search_long_term_memory() -> str:
        """检索用户历史交互中产生的长期知识记忆（事实、偏好、学过的概念）。当用户提及过去学过的内容或你感到缺乏上下文时使用此工具。"""
        svc = get_memory_service()
        memory_md = await svc.get_memory_markdown(user_id)
        if not memory_md.strip() or "暂无长期记忆" in memory_md:
            return "当前用户暂无长期记忆。"
        return memory_md

    return [get_user_profile, search_long_term_memory]
