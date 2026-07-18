from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.quiz.service import QuizReviewService


def test_analysis_prompt_counts_key_intermediate_values_as_process() -> None:
    messages = QuizReviewService()._build_messages(
        question_type="分析题",
        question_content="计算调度周转时间",
        standard_answer="给出调度顺序和各项计算",
        user_answer="给出调度顺序、关键中间结果和最终结果",
        knowledge_points=["进程调度"],
    )

    prompt = messages[0]["content"]
    assert "不要求机械重复题干数据或逐项展开相同的算术代入" in prompt
    assert "不得把已经给出算法顺序、公式或关键中间结果的答案认定为“仅写出最终结果”" in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("score", "is_correct"),
    [(59, False), (60, True), (80, True)],
)
async def test_review_uses_sixty_point_pass_boundary(score: int, is_correct: bool) -> None:
    llm = AsyncMock()
    llm.ainvoke_json.return_value = {
        "score": score,
        "feedback": "评分完成",
        "improvement_hints": ["建议1", "建议2", "建议3", "建议4"],
    }

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="分析题",
            question_content="分析死锁条件",
            standard_answer="互斥,请求保持,不可剥夺,循环等待",
            user_answer="作答内容",
            knowledge_points=["死锁"],
        )

    assert result["score"] == score
    assert result["is_correct"] is is_correct
    assert result["improvement_hints"] == ["建议1", "建议2", "建议3"]


@pytest.mark.asyncio
async def test_review_falls_back_to_keyword_coverage_when_llm_fails() -> None:
    llm = AsyncMock()
    llm.ainvoke_json.side_effect = RuntimeError("provider unavailable")

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="分析题",
            question_content="分析死锁条件",
            standard_answer="互斥,请求保持,不可剥夺,循环等待",
            user_answer="互斥和请求保持是其中两个条件",
        )

    assert result["score"] == 60
    assert result["is_correct"] is True


@pytest.mark.asyncio
async def test_review_fallback_scores_empty_answer_as_zero() -> None:
    llm = AsyncMock()
    llm.ainvoke_json.side_effect = RuntimeError("provider unavailable")

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="分析题",
            question_content="分析死锁条件",
            standard_answer="互斥,请求保持,不可剥夺,循环等待",
            user_answer="",
        )

    assert result["score"] == 0
    assert result["is_correct"] is False
    llm.ainvoke_json.assert_not_called()


@pytest.mark.asyncio
async def test_review_timeout_uses_fallback_without_hanging() -> None:
    llm = AsyncMock()

    async def never_finishes(*_args, **_kwargs):
        await asyncio.sleep(10)

    llm.ainvoke_json.side_effect = never_finishes

    with (
        patch("app.quiz.service.get_llm", return_value=llm),
        patch("app.quiz.service.QUIZ_REVIEW_TIMEOUT_SECONDS", 0.01),
    ):
        result = await QuizReviewService().review(
            question_type="分析题",
            question_content="分析死锁条件",
            standard_answer="互斥,请求保持,不可剥夺,循环等待",
            user_answer="互斥和请求保持是其中两个条件",
        )

    assert result["score"] == 60
    assert result["is_correct"] is True


@pytest.mark.asyncio
async def test_fill_blank_exact_match_skips_llm() -> None:
    llm = AsyncMock()
    llm.ainvoke_json = AsyncMock()

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="填空题",
            question_content="操作系统的英文缩写是？",
            standard_answer="OS",
            user_answer=" os ",
        )

    assert result["score"] == 100
    assert result["is_correct"] is True
    assert result["feedback"] == "答案正确"
    llm.ainvoke_json.assert_not_called()


@pytest.mark.asyncio
async def test_fill_blank_multi_blank_and_alternatives_skip_llm() -> None:
    llm = AsyncMock()
    llm.ainvoke_json = AsyncMock()

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="fill_blank",
            question_content="填写概念",
            standard_answer="进程/process，线程",
            user_answer="process, 线程",
        )

    assert result["score"] == 100
    assert result["is_correct"] is True
    llm.ainvoke_json.assert_not_called()


@pytest.mark.asyncio
async def test_fill_blank_mismatch_skips_llm_and_scores_zero() -> None:
    llm = AsyncMock()
    llm.ainvoke_json = AsyncMock()

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="填空题",
            question_content="操作系统的英文缩写是？",
            standard_answer="OS",
            user_answer="Windows",
        )

    assert result["score"] == 0
    assert result["is_correct"] is False
    llm.ainvoke_json.assert_not_called()


@pytest.mark.asyncio
async def test_empty_answer_skips_llm() -> None:
    llm = AsyncMock()
    llm.ainvoke_json = AsyncMock()

    with patch("app.quiz.service.get_llm", return_value=llm):
        result = await QuizReviewService().review(
            question_type="分析题",
            question_content="分析死锁条件",
            standard_answer="互斥,请求保持,不可剥夺,循环等待",
            user_answer="   ",
        )

    assert result["score"] == 0
    assert result["is_correct"] is False
    assert result["feedback"] == "本题未作答"
    llm.ainvoke_json.assert_not_called()


@pytest.mark.asyncio
async def test_review_batch_preserves_order_and_mixes_rule_with_llm() -> None:
    llm = AsyncMock()
    llm.ainvoke_json.return_value = {
        "score": 88,
        "feedback": "分析题评分完成",
        "improvement_hints": ["建议"],
    }

    service = QuizReviewService(concurrency=2)
    with patch("app.quiz.service.get_llm", return_value=llm):
        results = await service.review_batch(
            [
                {
                    "question_id": "fill-1",
                    "question_type": "填空题",
                    "question_content": "缩写",
                    "standard_answer": "OS",
                    "user_answer": "OS",
                    "knowledge_points": [],
                },
                {
                    "question_id": "analysis-1",
                    "question_type": "分析题",
                    "question_content": "分析",
                    "standard_answer": "标准",
                    "user_answer": "用户作答内容",
                    "knowledge_points": ["调度"],
                },
                {
                    "question_id": "fill-2",
                    "question_type": "填空题",
                    "question_content": "缩写2",
                    "standard_answer": "PCB",
                    "user_answer": "wrong",
                    "knowledge_points": [],
                },
            ]
        )

    assert [item["question_id"] for item in results] == ["fill-1", "analysis-1", "fill-2"]
    assert results[0]["score"] == 100
    assert results[1]["score"] == 88
    assert results[2]["score"] == 0
    assert llm.ainvoke_json.await_count == 1


@pytest.mark.asyncio
async def test_review_batch_limits_llm_concurrency() -> None:
    llm = AsyncMock()
    active = 0
    max_active = 0

    async def slow_json(*_args, **_kwargs):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return {
            "score": 70,
            "feedback": "ok",
            "improvement_hints": [],
        }

    llm.ainvoke_json.side_effect = slow_json
    service = QuizReviewService(concurrency=2)

    with patch("app.quiz.service.get_llm", return_value=llm):
        results = await service.review_batch(
            [
                {
                    "question_id": f"a-{i}",
                    "question_type": "分析题",
                    "question_content": f"题{i}",
                    "standard_answer": "标准",
                    "user_answer": f"答案{i}",
                    "knowledge_points": [],
                }
                for i in range(5)
            ]
        )

    assert len(results) == 5
    assert max_active <= 2
    assert llm.ainvoke_json.await_count == 5
