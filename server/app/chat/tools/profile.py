"""学习者画像读取工具。"""

from __future__ import annotations

from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from app.chat.schemas import TutorTurnContext
from app.profile.service import get_profile_service
from app.infra.logging import get_logger

logger = get_logger(__name__)


# Pydantic 模型定义：学习者画像查询工具的输入参数
# dimension: 指定读取画像的维度（如 goals、preferences），为空则读取全部
# course_name: 限定课程范围，可获取特定课程的学习者画像
# reason: 记录导师为何需要此画像信息，便于审计和调试
class GetLearnerProfileArgs(BaseModel):
    dimension: str | None = Field(default=None, description="Profile dimension to read, such as goals or preferences.")
    course_name: str | None = Field(default=None, description="Course-specific profile scope when available.")
    reason: str = Field(default="", description="Why the tutor needs the profile.")


def _compact(text: str, *, limit: int = 3500) -> str:
    """截断过长文本，防止撑爆 LLM 上下文窗口。"""
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def make_get_learner_profile(
    request: TutorTurnContext,
    profile_service: Any | None = None,
) -> Callable[..., Awaitable[str]]:
    """工厂函数：创建闭包绑定当前请求的画像查询工具。

    闭包捕获 request.user_id，使 LLM 工具调用无需显式传递用户 ID。
    profile_service 可注入以支持测试。
    """
    async def _impl(
        dimension: str | None = None,
        course_name: str | None = None,
        reason: str = "",
    ) -> str:
        # 使用注入的服务或获取默认全局服务实例
        svc = profile_service or get_profile_service()
        try:
            # 调用画像服务获取 Markdown 格式的学习者画像
            markdown = await svc.get_profile_markdown(
                request.user_id,
                course_name=course_name,
                dimension=dimension,
            )
            return _compact(f"画像读取原因: {reason or '未提供'}\n{markdown}")
        except Exception as exc:
            logger.warning("[get_learner_profile] failed: %s", exc)
            return "暂时无法读取学习者画像。"

    return _impl
