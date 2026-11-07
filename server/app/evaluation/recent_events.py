"""近期学习事件的统一读取与文本上下文构建。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.models import LearningEvent, LearningSession


EVENT_LABELS = {
    "chat_dialogue": "智能辅导对话",
    "resource_generated": "生成学习资源",
    "resource_viewed": "查看学习资源",
    "resource_completed": "完成学习资源",
    "resource_feedback": "提交资源反馈",
    "path_node_started": "开始路径节点",
    "path_node_completed": "完成路径节点",
    "path_quiz_answered": "提交路径练习",
    "quiz_submitted": "提交练习",
}


@dataclass(frozen=True, slots=True)
class RecentLearningContext:
    """同一时间窗口内的学习事件、会话与可供模型使用的文本摘要。"""

    window_start: datetime
    window_end: datetime
    events: list[LearningEvent]
    sessions: list[LearningSession]

    def to_markdown(self, *, max_events: int = 100) -> str:
        """生成供 LLM 使用的学习事件文本，不作为前端 API 响应。"""
        if max_events < 1:
            raise ValueError("max_events must be at least 1")
        days = max(1, (self.window_end - self.window_start).days)
        lines = [f"## 最近 {days} 天学习事件"]

        if not self.events:
            lines.append("- 暂无已记录的学习事件。")
        else:
            for event in self.events[:max_events]:
                occurred_at = event.occurred_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
                label = EVENT_LABELS.get(event.event_type, event.event_type)
                details = [f"模块：{event.module}"]
                if event.course:
                    details.append(f"课程：{event.course}")
                if event.topic:
                    details.append(f"主题：{event.topic}")
                if event.score is not None:
                    details.append(f"得分：{event.score:g}")
                lines.append(f"- {occurred_at}｜{label}（{'；'.join(details)}）")
            if len(self.events) > max_events:
                lines.append(f"- 其余 {len(self.events) - max_events} 条事件已省略，统计快照仍基于完整记录。")

        total_seconds = sum(item.duration_seconds or 0 for item in self.sessions)
        if self.sessions:
            lines.extend([
                "",
                "## 同期学习会话",
                f"- 共 {len(self.sessions)} 次有效学习会话，累计 {round(total_seconds / 60)} 分钟。",
            ])

        return "\n".join(lines)


async def get_recent_learning_context(
    session: AsyncSession,
    *,
    user_id: int,
    range_days: int | None = None,
    event_limit: int | None = 50,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> RecentLearningContext:
    """统一读取用户近期学习事实。

    调用方可传 ``range_days`` 获取相对时间窗，也可传固定窗口以保证报告快照
    的边界可复现。评估聚合使用 ``event_limit=None``，避免统计因展示上限被截断。
    """
    if window_start is None:
        if range_days is None or not 1 <= range_days <= 90:
            raise ValueError("range_days must be between 1 and 90")
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=range_days)
    elif window_end is None:
        raise ValueError("window_end is required when window_start is provided")

    assert window_end is not None
    if window_start >= window_end:
        raise ValueError("window_start must be before window_end")
    if event_limit is not None and not 1 <= event_limit <= 100:
        raise ValueError("event_limit must be between 1 and 100")

    events_stmt = (
        select(LearningEvent)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.occurred_at >= window_start,
            LearningEvent.occurred_at < window_end,
        )
        .order_by(col(LearningEvent.occurred_at).desc())
    )
    if event_limit is not None:
        events_stmt = events_stmt.limit(event_limit)

    sessions_stmt = (
        select(LearningSession)
        .where(
            LearningSession.user_id == user_id,
            LearningSession.started_at >= window_start,
            LearningSession.started_at < window_end,
        )
        .order_by(col(LearningSession.started_at).desc())
    )

    events = list((await session.exec(events_stmt)).all())
    sessions = list((await session.exec(sessions_stmt)).all())
    return RecentLearningContext(
        window_start=window_start,
        window_end=window_end,
        events=events,
        sessions=sessions,
    )
