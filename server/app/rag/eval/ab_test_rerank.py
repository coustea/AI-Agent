from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import app.config
from app.rag.eval.evaluate import load_test_cases
from app.rag.knowledge import retrieve_knowledge


DEFAULT_CASES_PATH = Path(__file__).resolve().parent / "datasets" / "test_cases_extended.json"


def evaluate_with_config(
    test_cases: list[dict[str, Any]],
    rerank_enabled: bool,
    top_k: int = 4,
) -> dict[str, Any]:
    original = app.config.KB_RERANK_ENABLED
    app.config.KB_RERANK_ENABLED = rerank_enabled

    try:
        results: list[dict[str, Any]] = []
        total_time = 0.0

        for case in test_cases:
            query = case["query"]
            expected_keywords = case["expected_keywords"]
            course_name = case.get("ground_truth_source")

            start = time.perf_counter()
            retrieved = retrieve_knowledge(query, top_k=top_k, course_name=course_name)
            elapsed = time.perf_counter() - start
            total_time += elapsed

            hit = False
            for result in retrieved:
                text = result.get("text", "").lower()
                keyword_hits = sum(1 for keyword in expected_keywords if keyword.lower() in text)
                if keyword_hits >= len(expected_keywords) * 0.3:
                    hit = True
                    break

            results.append(
                {
                    "id": case["id"],
                    "query": query,
                    "hit_at_k": hit,
                    "num_results": len(retrieved),
                    "has_rerank_score": bool(retrieved and "rerank_score" in retrieved[0]),
                    "retrieval_modes": [row.get("retrieval_mode") for row in retrieved[:3]],
                }
            )

        hit_rate = sum(1 for row in results if row["hit_at_k"]) / len(results) if results else 0.0
        avg_time = total_time / len(test_cases) if test_cases else 0.0

        return {
            "rerank_enabled": rerank_enabled,
            "total_queries": len(results),
            "hit_rate": hit_rate,
            "avg_latency_ms": avg_time * 1000,
            "total_time_s": total_time,
            "results": results,
        }
    finally:
        app.config.KB_RERANK_ENABLED = original


def ab_test(test_file: Path, top_k: int = 4) -> dict[str, Any]:
    test_cases = load_test_cases(test_file)
    result_a = evaluate_with_config(test_cases, rerank_enabled=False, top_k=top_k)
    result_b = evaluate_with_config(test_cases, rerank_enabled=True, top_k=top_k)

    hit_delta = (result_b["hit_rate"] - result_a["hit_rate"]) * 100
    latency_delta = result_b["avg_latency_ms"] - result_a["avg_latency_ms"]
    quality_improved = result_b["hit_rate"] > result_a["hit_rate"]
    latency_acceptable = latency_delta <= 30

    return {
        "group_a": result_a,
        "group_b": result_b,
        "comparison": {
            "hit_rate_delta_pct": hit_delta,
            "latency_delta_ms": latency_delta,
            "latency_increase_pct": (latency_delta / result_a["avg_latency_ms"] * 100)
            if result_a["avg_latency_ms"] > 0
            else 0,
            "quality_improved": quality_improved,
            "latency_acceptable": latency_acceptable,
        },
        "recommendation": {
            "enable_rerank": quality_improved and latency_acceptable,
            "reason": "质量提升且延迟可接受" if (quality_improved and latency_acceptable) else "需要权衡质量和延迟",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rerank A/B evaluation")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Test cases file")
    parser.add_argument("--output", help="Optional output JSON file")
    parser.add_argument("--top-k", type=int, default=4, help="Top-K retrieval count")
    args = parser.parse_args()

    result = ab_test(Path(args.cases), top_k=args.top_k)
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
