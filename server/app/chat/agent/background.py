"""TutorAgent 后台任务 — 长期记忆、画像更新和会话压缩。

职责：
  - run_background_memory_jobs: 对话轮次结束后的后台记忆管线
  - 检查并执行：长期记忆更新、学习者画像更新、会话压缩
  - 三个任务互相独立，并行执行
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.infra.logging import get_logger
from app.profile.service import get_profile_service

logger = get_logger(__name__)


async def run_background_memory_jobs(
    memory_service: Any,
    *,
    user_id: int,
    session_id: str,
    user_message: str = "",
    assistant_reply: str = "",
) -> None:
    """后台记忆管线：长期记忆、画像更新、会话压缩，三者并行执行。"""
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
        signals = evaluation["signals"]
        should_update_global = signals["global_profile"]
        should_update_course = signals["course_profile"]
        should_profile = should_update_global or should_update_course
        payload["ltm_schedule"] = ltm_schedule
        logger.info(
            "[background] 调度检查: should_ltm=%s should_profile=%s(global=%s course=%s) should_compress=%s",
            should_ltm, should_profile, should_update_global, should_update_course, should_compress,
        )

        # ── Step 2: 构建并行任务列表 ──
        tasks: list[asyncio.Task] = []

        if should_ltm:
            tasks.append(asyncio.create_task(
                _run_ltm_update(memory_service, user_id, session_id, user_message, assistant_reply, ltm_schedule),
                name="ltm_update",
            ))

        if should_profile:
            tasks.append(asyncio.create_task(
                _run_profile_update(user_id, session_id, should_update_global, should_update_course),
                name="profile_update",
            ))

        if should_compress:
            tasks.append(asyncio.create_task(
                _run_compress(memory_service, user_id, session_id),
                name="compress",
            ))

        if not tasks:
            logger.info("[background] 无后台任务需要执行，全部跳过")
            return

        # ── Step 3: 并行执行，收集结果 ──
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


async def _run_profile_update(
    user_id: int,
    session_id: str,
    should_update_global: bool,
    should_update_course: bool,
) -> dict[str, Any]:
    """执行学习者画像更新。"""
    profile_service = get_profile_service()
    global_updated = False
    course_updated = False

    if should_update_global:
        res_global = await profile_service.update_global_from_tutoring(
            user_id=user_id,
            session_id=session_id,
        )
        global_updated = res_global.get("profile_updated", False)
        logger.info("[background] 全局画像更新完成: global_updated=%s", global_updated)

    if should_update_course:
        global_profile = await profile_service.get_or_create_global_profile(user_id=user_id)
        profile_json = global_profile.profile_json or {}
        active_courses = profile_json.get("base_info", {}).get("courses", [])
        course_name = ""
        if active_courses and isinstance(active_courses, list):
            first_course = active_courses[0]
            if isinstance(first_course, dict):
                course_name = first_course.get("course", "")
            elif isinstance(first_course, str):
                course_name = first_course

        # Ensure course_name is a string, not a list or other type
        if isinstance(course_name, list):
            course_name = course_name[0] if course_name else ""
        course_name = str(course_name) if course_name else ""

        if course_name:
            res_course = await profile_service.update_course_from_tutoring(
                user_id=user_id,
                session_id=session_id,
                course_name=course_name,
            )
            course_updated = res_course.get("profile_updated", False)
            logger.info(
                "[background] 课程画像更新完成: course_name=%s course_updated=%s",
                course_name, course_updated,
            )

    status = "completed" if (global_updated or course_updated) else "skipped"
    return {
        "job": "learner_profile",
        "status": status,
        "profile_updated": global_updated or course_updated,
        "global_updated": global_updated,
        "course_updated": course_updated,
    }


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
