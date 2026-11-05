from copy import deepcopy
from typing import Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.infra.models import UserProfile

DEFAULT_GUIDANCE_STRATEGY = {
    "version": 1,
    "conclusion": "暂无学习数据，开始学习后将生成个性化评估。",
    "focus_topics": [],
    "recommended_session_minutes": 30,
    "tutoring_style": "以精细解构、步步启发为主的讲授与练习辅导风格",
    "action_plan": [],
    "reason": "新用户尚未生成诊断报告，使用缺省初始自适应辅导策略"
}


async def get_effective_guidance_strategy(session: AsyncSession, user_id: int) -> dict[str, Any]:
    """获取用户有效的自适应辅导策略。

    优先从 UserProfile.guidance_strategy 读取（由评估生成时写入），
    若没有或为空则返回初始缺省默认值。
    该方法仅读取数据库，不创建画像行，不更新评分。
    """
    profile = await session.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile and profile.guidance_strategy:
        return profile.guidance_strategy
    return deepcopy(DEFAULT_GUIDANCE_STRATEGY)
