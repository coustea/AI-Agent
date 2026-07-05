from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.chat.agent.background import run_background_memory_jobs


@pytest.mark.asyncio
async def test_run_background_memory_jobs_global_signal():
    memory_service = MagicMock()
    memory_service.compress_session = AsyncMock(return_value=None)
    memory_service.update_long_term_memory = AsyncMock(return_value={"updated": False, "analyzed": False})
    memory_service.evaluate_post_turn_jobs = AsyncMock(return_value={
        "should_ltm": False,
        "ltm_schedule": {"signal_detected": False},
        "should_profile": True,  # 画像需要更新
        "profile_schedule": {"signal_detected": True},
        "should_compress": False,
        "signals": {"ltm": False, "global_profile": True, "course_profile": False},
    })

    mock_profile_service = MagicMock()
    mock_profile_service.infer_profile_from_tutoring = AsyncMock(return_value={"profile_updated": True})
    mock_profile_service.infer_course_profile_from_tutoring = AsyncMock(return_value={"profile_updated": False})

    mock_global_profile = MagicMock()
    mock_global_profile.profile_json = {
        "base_info": {
            "courses": ["OS"]
        }
    }
    mock_profile_service.get_profile = AsyncMock(return_value=mock_global_profile)

    with patch("app.chat.agent.background.get_profile_service", return_value=mock_profile_service):
        await run_background_memory_jobs(
            memory_service,
            user_id=1,
            session_id="session-uuid",
            user_message="我喜欢实践动手写代码",
            assistant_reply="很好，多写代码可以提升能力",
        )

        mock_profile_service.infer_profile_from_tutoring.assert_called_once_with(
            user_id=1,
            session_id="session-uuid"
        )
        mock_profile_service.infer_course_profile_from_tutoring.assert_not_called()


@pytest.mark.asyncio
async def test_run_background_memory_jobs_course_signal():
    memory_service = MagicMock()
    memory_service.compress_session = AsyncMock(return_value=None)
    memory_service.update_long_term_memory = AsyncMock(return_value={"updated": False, "analyzed": False})
    memory_service.evaluate_post_turn_jobs = AsyncMock(return_value={
        "should_ltm": False,
        "ltm_schedule": {"signal_detected": False},
        "should_profile": True,  # 画像需要更新
        "profile_schedule": {"signal_detected": True},
        "should_compress": False,
        "signals": {"ltm": False, "global_profile": False, "course_profile": True},
    })

    mock_profile_service = MagicMock()
    mock_profile_service.infer_profile_from_tutoring = AsyncMock(return_value={"profile_updated": False})
    mock_profile_service.infer_course_profile_from_tutoring = AsyncMock(return_value={"profile_updated": True})

    mock_global_profile = MagicMock()
    mock_global_profile.profile_json = {
        "base_info": {
            "courses": ["OS"]
        }
    }
    mock_profile_service.get_profile = AsyncMock(return_value=mock_global_profile)

    with patch("app.chat.agent.background.get_profile_service", return_value=mock_profile_service):
        await run_background_memory_jobs(
            memory_service,
            user_id=1,
            session_id="session-uuid",
            user_message="我对操作系统的进程调度不太理解",
            assistant_reply="进程调度是操作系统的核心概念",
        )

        mock_profile_service.infer_profile_from_tutoring.assert_not_called()
        mock_profile_service.infer_course_profile_from_tutoring.assert_called_once_with(
            user_id=1,
            session_id="session-uuid",
            course_name="OS",
        )


@pytest.mark.asyncio
async def test_run_background_memory_jobs_both_signals():
    memory_service = MagicMock()
    memory_service.compress_session = AsyncMock(return_value=None)
    memory_service.update_long_term_memory = AsyncMock(return_value={"updated": False, "analyzed": False})
    memory_service.evaluate_post_turn_jobs = AsyncMock(return_value={
        "should_ltm": False,
        "ltm_schedule": {"signal_detected": False},
        "should_profile": True,  # 画像需要更新
        "profile_schedule": {"signal_detected": True},
        "should_compress": False,
        "signals": {"ltm": False, "global_profile": True, "course_profile": True},
    })

    mock_profile_service = MagicMock()
    mock_profile_service.infer_profile_from_tutoring = AsyncMock(return_value={"profile_updated": True})
    mock_profile_service.infer_course_profile_from_tutoring = AsyncMock(return_value={"profile_updated": True})

    mock_global_profile = MagicMock()
    mock_global_profile.profile_json = {
        "base_info": {
            "courses": ["OS"]
        }
    }
    mock_profile_service.get_profile = AsyncMock(return_value=mock_global_profile)

    with patch("app.chat.agent.background.get_profile_service", return_value=mock_profile_service):
        await run_background_memory_jobs(
            memory_service,
            user_id=1,
            session_id="session-uuid",
            user_message="我特别喜欢这种快速的节奏，但对进程调度还是有薄弱点",
            assistant_reply="好的，我们会根据你的偏好继续学习",
        )

        mock_profile_service.infer_profile_from_tutoring.assert_called_once_with(
            user_id=1,
            session_id="session-uuid"
        )
        mock_profile_service.infer_course_profile_from_tutoring.assert_called_once_with(
            user_id=1,
            session_id="session-uuid",
            course_name="OS",
        )


@pytest.mark.asyncio
async def test_run_background_memory_jobs_no_signals():
    memory_service = MagicMock()
    memory_service.compress_session = AsyncMock(return_value=None)
    memory_service.update_long_term_memory = AsyncMock(return_value={"updated": False, "analyzed": False})
    memory_service.evaluate_post_turn_jobs = AsyncMock(return_value={
        "should_ltm": False,
        "ltm_schedule": {"signal_detected": False},
        "should_profile": False,  # 画像不需要更新
        "profile_schedule": {"signal_detected": False},
        "should_compress": False,
        "signals": {"ltm": False, "global_profile": False, "course_profile": False},
    })

    mock_profile_service = MagicMock()
    mock_profile_service.infer_profile_from_tutoring = AsyncMock()
    mock_profile_service.infer_course_profile_from_tutoring = AsyncMock()

    with patch("app.chat.agent.background.get_profile_service", return_value=mock_profile_service):
        await run_background_memory_jobs(
            memory_service,
            user_id=1,
            session_id="session-uuid",
            user_message="你好，今天天气不错",
            assistant_reply="是的，天气很好",
        )

        mock_profile_service.infer_profile_from_tutoring.assert_not_called()
        mock_profile_service.infer_course_profile_from_tutoring.assert_not_called()
