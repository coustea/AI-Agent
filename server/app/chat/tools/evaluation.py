"""近期学习评估读取工具。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from app.chat.schemas import TurnRequest
from app.evaluation.service import evaluation_service
from app.infra.database import session_scope
from app.infra.logging import get_logger

logger = get_logger(__name__)


# 近期学习评估查询工具的输入参数模型
# limit: 获取最近 N 条评估记录（1-10），默认 5
# reason: 记录查询原因，用于审计和调试
class GetRecentEvaluationArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=10, description="Number of recent evaluation events to summarize.")
    reason: str = Field(default="", description="Why recent evaluation data is needed.")


def _compact(text: str, *, limit: int = 3500) -> str:
    """截断过长文本，防止撑爆 LLM 上下文窗口。"""
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def make_get_recent_evaluation(
    request: TurnRequest,
) -> Callable[..., Awaitable[str]]:
    """工厂函数：创建闭包绑定当前请求的近期评估查询工具。

    与 profile/memory 不同，评估需要独立数据库会话（非 DI 注入），
    因此使用 session_scope 上下文管理器。
    """
    async def _impl(
        limit: int = 5,
        reason: str = "",
    ) -> str:
        try:
            # 使用独立的数据库会话（自动提交），避免 DI 会话生命周期问题
            async with session_scope() as db:
                summary = await evaluation_service.get_summary(db, user_id=request.user_id, limit=limit)
        except Exception as exc:
            logger.warning("[get_recent_evaluation] failed: %s", exc)
            return "暂无近期学习测验评估记录。"
        if summary.event_count <= 0:
            return "暂无近期学习测验评估记录。"
        # 构建可读的评估摘要文本
        lines = [f"评估读取原因: {reason or '未提供'}", f"测验记录数: {summary.event_count}"]
        if summary.average_score is not None:
            lines.append(f"平均测验分: {summary.average_score}")
        if summary.weak_topics:
            lines.append(f"薄弱点: {', '.join(summary.weak_topics)}")
        if summary.recommendations:
            lines.append(f"系统建议: {', '.join(summary.recommendations)}")
        return _compact("\n".join(lines))

    return _impl
