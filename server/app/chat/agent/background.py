"""TutorAgent 后台任务 — 长期记忆和会话压缩。

职责：
  - run_background_memory_jobs: 对话轮次结束后的后台记忆管线
  - 检查并执行：长期记忆更新、会话压缩
  - 两个任务独立触发，根据 token 阈值判断

注：学习者画像不再在对话后实时更新。画像改由 GET /profile 懒加载触发
infer_profile_from_digest（基于周概要缓冲），见 app/profile/service.py。
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.infra.logging import get_logger

logger = get_logger(__name__)


async def run_background_memory_jobs(
    memory_service: Any,
    *,
    user_id: int,
    session_id: str,
    user_message: str = "",
    assistant_reply: str = "",
) -> None:
    """后台记忆管线：长期记忆、会话压缩，根据 token 阈值独立触发。"""
    logger.info(
        "[background] 后台记忆任务开始: user_id=%s session_id=%s",
        user_id, session_id,
    )

    payload: dict[str, Any] = {}

    try:
        evaluation = await memory_service.evaluate_post_turn_jobs(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
        should_ltm = evaluation["should_ltm"]
        ltm_schedule = evaluation["ltm_schedule"]
        should_compress = evaluation["should_compress"]
        payload["ltm_schedule"] = ltm_schedule
        logger.info(
            "[background] 调度检查: should_ltm=%s should_compress=%s",
            should_ltm, should_compress,
        )

        # ── 两个任务独立执行，根据 token 阈值触发 ──
        tasks: list[asyncio.Task] = []

        if should_compress:
            tasks.append(asyncio.create_task(
                _run_compress(memory_service, user_id, session_id),
                name="compress",
            ))

        if should_ltm:
            tasks.append(asyncio.create_task(
                _run_ltm_update(memory_service, user_id, session_id, user_message, assistant_reply, ltm_schedule),
                name="ltm_update",
            ))

        if not tasks:
            logger.info("[background] 无后台任务需要执行，全部跳过")
            return

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error("[background] 任务 %s 失败: %s", task.get_name(), result)
                payload[f"{task.get_name()}_error"] = str(result)
            else:
                payload[f"{task.get_name()}_result"] = result

        logger.info("[background] 后台记忆任务完成: tasks=%d", len(tasks))

    except Exception as exc:
        logger.error("[background] 后台记忆任务失败: %s", exc)


async def _run_ltm_update(
    memory_service: Any,
    user_id: int,
    session_id: str,
    user_message: str,
    assistant_reply: str,
    ltm_schedule: dict[str, Any],
) -> dict[str, Any]:
    """执行长期记忆更新。"""
    ltm_result = await memory_service.update_long_term_memory(
        user_id=user_id,
        session_id=session_id,
        user_message=user_message,
        assistant_reply=assistant_reply,
        signal_detected=bool(ltm_schedule.get("signal_detected")),
    )
    status = (
        "completed" if ltm_result.get("updated")
        else "analyzed" if ltm_result.get("analyzed")
        else "skipped"
    )
    logger.info(
        "[background] 长期记忆更新完成: status=%s updated=%s analyzed=%s",
        status, ltm_result.get("updated"), ltm_result.get("analyzed"),
    )
    return {"job": "long_term_memory", "status": status, "ltm_result": ltm_result}


async def _run_compress(
    memory_service: Any,
    user_id: int,
    session_id: str,
) -> dict[str, Any]:
    """执行会话压缩。"""
    result = await memory_service.compress_session(
        user_id=user_id,
        session_id=session_id,
        reason="post_turn",
    )
    status = "completed" if result else "skipped"
    logger.info(
        "[background] 会话压缩完成: status=%s",
        status,
    )
    return {"job": "compress", "status": status, "compress_result": result is not None}
