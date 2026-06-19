"""TutorAgent 后台任务 — 长期记忆和画像更新。

职责：
  - run_background_memory_jobs: 对话轮次结束后的后台记忆管线
  - 检查是否需要更新长期记忆 / 学习者画像
  - 持久化记忆更新事件
"""

from __future__ import annotations

import re
from typing import Any

from app.chat.agent.state import TutorAgentState
from app.chat.memory.service import get_chat_memory_service
from app.infra.logging import get_logger
from app.profile.service import get_profile_service

logger = get_logger(__name__)


async def run_background_memory_jobs(
    memory_service: Any,
    *,
    user_id: int,
    session_id: str,
    turn_id: int,
    user_message: str,
    assistant_reply: str,
    turn_index: int = 0,
) -> None:
    """后台记忆管线：长期记忆和画像更新。

    Args:
        memory_service: 记忆服务实例
        user_id: 用户ID
        session_id: 会话ID
        turn_id: 轮次ID
        user_message: 用户消息
        assistant_reply: 助手回复
        turn_index: 轮次索引
    """
    state: TutorAgentState = {
        "user_id": user_id,
        "session_id": session_id,
        "turn_id": turn_id,
    }

    await _persist_turn_event(
        memory_service, state,
        "memory.update.start",
        {"stage": "background_post_turn", "turn_index": turn_index},
    )

    job = "none"
    status = "skipped"
    payload: dict[str, Any] = {}

    try:
        should_ltm, ltm_schedule = await memory_service.should_update_long_term_memory(
            user_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
        payload["ltm_schedule"] = ltm_schedule

        if should_ltm:
            job = "long_term_memory"
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
            payload["ltm_result"] = ltm_result
        else:
            # 检查画像更新
            profile_service = get_profile_service()
            turn_text = f"{user_message}\n{assistant_reply}"

            # 全局画像触发模式
            global_patterns = [
                r"(喜欢|习惯|偏好|擅长|感兴趣|反感|讨厌|更愿意|认知|风格|学习方式)",
                r"(节奏|速度|时间|每天|太快|太慢|稍微|快一点|慢一点|进度|频繁)",
                r"(实践|动手|写代码|做题|编程|实验|实战|练习|编码|Debug)",
            ]
            # 课程画像触发模式
            course_patterns = [
                r"(这门课|操作系统|数据库|计网|网络|计组|算法|数据结构|高数|线代)",
                r"(进程|线程|锁|事务|索引|内存|虚拟内存|调度|TCP|IP|握手|矩阵|导数|概念)",
                r"(薄弱|搞错|出错|卡住|记不住|混淆|搞不清|老是错|不会做|不懂|理解不了)",
                r"(基础|掌握|熟悉|了解|懂了|不明白|难度|简单|困难|稍微深点)",
            ]

            should_update_global = any(re.search(p, turn_text) for p in global_patterns)
            should_update_course = any(re.search(p, turn_text) for p in course_patterns)

            logger.info(
                "[background] 画像更新检查: should_update_global=%s should_update_course=%s",
                should_update_global, should_update_course
            )

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

                if course_name:
                    res_course = await profile_service.update_course_from_tutoring(
                        user_id=user_id,
                        session_id=session_id,
                        course_name=course_name,
                    )
                    course_updated = res_course.get("profile_updated", False)
                    logger.info(
                        "[background] 课程画像更新完成: course_name=%s course_updated=%s",
                        course_name, course_updated
                    )

            job = "learner_profile"
            status = "completed" if (global_updated or course_updated) else "skipped"
            payload["profile_updated"] = global_updated or course_updated
            payload["global_updated"] = global_updated
            payload["course_updated"] = course_updated

        await _persist_turn_event(
            memory_service, state,
            "memory.update.done",
            {"job": job, "status": status, **payload},
        )

    except Exception as exc:
        logger.error("[background] 后台记忆任务失败: %s", exc)
        await _persist_turn_event(
            memory_service, state,
            "memory.update.done",
            {"job": job, "status": "error", "error": str(exc), **payload},
        )


async def _persist_turn_event(
    memory_service: Any,
    state: TutorAgentState,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """持久化轮次事件。"""
    turn_id = state.get("turn_id")
    if not turn_id:
        return
    try:
        await memory_service.append_turn_event(
            user_id=state.get("user_id", 0),
            session_id=state.get("session_id", ""),
            turn_id=turn_id,
            event_type=event_type,
            payload=payload or {},
        )
    except Exception as exc:
        logger.warning("[background] 持久化事件失败: %s", exc)