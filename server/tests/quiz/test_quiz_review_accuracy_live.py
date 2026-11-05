"""分析题/填空题评阅准确性实测试（会调用真实 LLM）。

运行：
  cd server
  PYTHONPATH=. uv run pytest tests/quiz/test_quiz_review_accuracy_live.py -q -s
"""

from __future__ import annotations

import asyncio
import os

import pytest

from app.quiz.service import QuizReviewService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_TESTS") != "1",
    reason="Live LLM tests disabled; set RUN_LIVE_TESTS=1 to run.",
)

# 这些 case 关注「分数是否落在合理区间」，允许模型有一定波动。
ACCURACY_CASES = [
    {
        "id": "fill_exact",
        "question_type": "填空题",
        "question_content": "操作系统的英文缩写是？",
        "standard_answer": "OS",
        "user_answer": "os",
        "score_min": 100,
        "score_max": 100,
        "expect_correct": True,
    },
    {
        "id": "fill_wrong",
        "question_type": "填空题",
        "question_content": "操作系统的英文缩写是？",
        "standard_answer": "OS",
        "user_answer": "Windows",
        "score_min": 0,
        "score_max": 0,
        "expect_correct": False,
    },
    {
        "id": "analysis_empty",
        "question_type": "分析题",
        "question_content": "简述死锁产生的四个必要条件。",
        "standard_answer": "互斥、请求与保持、不可剥夺、循环等待",
        "user_answer": "",
        "score_min": 0,
        "score_max": 0,
        "expect_correct": False,
    },
    {
        "id": "analysis_full_cover",
        "question_type": "分析题",
        "question_content": "简述死锁产生的四个必要条件。",
        "standard_answer": "互斥、请求与保持、不可剥夺、循环等待",
        "user_answer": (
            "死锁需要四个条件同时成立："
            "1. 互斥：资源同一时刻只能被一个进程使用；"
            "2. 请求与保持：进程已占有资源同时再申请其他资源；"
            "3. 不可剥夺：已分配资源不能被强制抢走；"
            "4. 循环等待：存在进程-资源环形等待链。"
        ),
        "score_min": 80,
        "score_max": 100,
        "expect_correct": True,
    },
    {
        "id": "analysis_partial",
        "question_type": "分析题",
        "question_content": "简述死锁产生的四个必要条件。",
        "standard_answer": "互斥、请求与保持、不可剥夺、循环等待",
        "user_answer": "死锁要满足互斥和循环等待这两个条件。",
        "score_min": 40,
        "score_max": 79,
        "expect_correct": None,  # 边界附近允许对/错波动
    },
    {
        "id": "analysis_wrong",
        "question_type": "分析题",
        "question_content": "简述死锁产生的四个必要条件。",
        "standard_answer": "互斥、请求与保持、不可剥夺、循环等待",
        "user_answer": "死锁就是进程执行太慢，CPU 利用率太低导致的。",
        "score_min": 0,
        "score_max": 55,
        "expect_correct": False,
    },
    {
        "id": "analysis_process_ok_result_wrong",
        "question_type": "分析题",
        "question_content": (
            "有三个进程 P1/P2/P3 到达时间分别为 0/1/2，服务时间分别为 5/3/1，"
            "采用 FCFS，求平均周转时间。"
        ),
        "standard_answer": (
            "调度顺序 P1→P2→P3；完成时间 5/8/9；周转 5/7/7；平均周转 (5+7+7)/3=6.33"
        ),
        "user_answer": (
            "采用 FCFS，按到达顺序调度：P1、P2、P3。"
            "P1 完成时间=5，周转=5；P2 完成=8，周转=7；P3 完成=9，周转=7。"
            "平均周转时间我算成 8。"
        ),
        "score_min": 60,
        "score_max": 85,
        "expect_correct": True,
    },
    {
        "id": "analysis_final_only",
        "question_type": "分析题",
        "question_content": (
            "有三个进程 P1/P2/P3 到达时间分别为 0/1/2，服务时间分别为 5/3/1，"
            "采用 FCFS，求平均周转时间。"
        ),
        "standard_answer": (
            "调度顺序 P1→P2→P3；完成时间 5/8/9；周转 5/7/7；平均周转 (5+7+7)/3=6.33"
        ),
        "user_answer": "6.33",
        "score_min": 30,
        "score_max": 59,
        "expect_correct": False,
    },
]


@pytest.mark.asyncio
async def test_quiz_review_accuracy_live() -> None:
    service = QuizReviewService(concurrency=2)
    rows: list[dict] = []

    # 串行测更稳定，避免上游限流干扰结论
    for case in ACCURACY_CASES:
        result = await service.review(
            question_type=case["question_type"],
            question_content=case["question_content"],
            standard_answer=case["standard_answer"],
            user_answer=case["user_answer"],
            knowledge_points=["操作系统"],
        )
        score = int(result["score"])
        ok_range = case["score_min"] <= score <= case["score_max"]
        ok_flag = True
        if case["expect_correct"] is True:
            ok_flag = result["is_correct"] is True
        elif case["expect_correct"] is False:
            ok_flag = result["is_correct"] is False

        rows.append(
            {
                "id": case["id"],
                "score": score,
                "is_correct": result["is_correct"],
                "expect": f"{case['score_min']}-{case['score_max']}",
                "feedback": (result.get("feedback") or "")[:80],
                "pass": ok_range and ok_flag,
            }
        )

    print("\n=== Quiz Review Accuracy Report ===")
    for row in rows:
        mark = "PASS" if row["pass"] else "FAIL"
        print(
            f"[{mark}] {row['id']}: score={row['score']} "
            f"(expect {row['expect']}) correct={row['is_correct']} | {row['feedback']}"
        )

    failed = [row["id"] for row in rows if not row["pass"]]
    assert not failed, f"accuracy cases failed: {failed}"


@pytest.mark.asyncio
async def test_quiz_review_batch_multi_analysis_consistency_live() -> None:
    """多题一次评阅时，好/坏答案相对排序应合理。"""
    service = QuizReviewService(concurrency=2)
    items = [
        {
            "question_id": "good",
            "question_type": "分析题",
            "question_content": "简述死锁四个必要条件。",
            "standard_answer": "互斥、请求与保持、不可剥夺、循环等待",
            "user_answer": "互斥、请求与保持、不可剥夺、循环等待四个条件同时成立才会死锁。",
            "knowledge_points": ["操作系统"],
        },
        {
            "question_id": "bad",
            "question_type": "分析题",
            "question_content": "简述死锁四个必要条件。",
            "standard_answer": "互斥、请求与保持、不可剥夺、循环等待",
            "user_answer": "死锁就是内存不够用。",
            "knowledge_points": ["操作系统"],
        },
    ]
    results = await service.review_batch(items)
    by_id = {item["question_id"]: item for item in results}
    print(
        "\n[batch] good=",
        by_id["good"]["score"],
        by_id["good"].get("feedback"),
        "| bad=",
        by_id["bad"]["score"],
        by_id["bad"].get("feedback"),
    )
    assert by_id["good"]["score"] >= 70
    assert by_id["bad"]["score"] <= 55
    assert by_id["good"]["score"] - by_id["bad"]["score"] >= 20
