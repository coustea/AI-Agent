from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.rag.eval.evaluate import check_keyword_hits, load_test_cases
from app.rag.knowledge import (
    _matches_source_filter,
    _metadata_key,
    retrieve_dense_knowledge,
    retrieve_sparse_knowledge,
)
from app.rag.knowledge_router import route_query_sources


DEFAULT_CASES_PATH = Path(__file__).resolve().parent / "datasets" / "test_cases_408.json"
DEFAULT_K_VALUES = [20, 40, 60, 80, 100, 120]


def _rrf_merge(
    dense_rows: list[dict[str, Any]],
    sparse_rows: list[dict[str, Any]],
    k: int,
    top_k: int = 4,
    source_filter: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    merged_scores: dict[tuple[str, str], dict[str, Any]] = {}
    for rows in (dense_rows, sparse_rows):
        for item in rows:
            metadata = dict(item.get("metadata") or {})
            key = _metadata_key(metadata)
            score = 1.0 / (k + int(item.get("rank") or 0))
            existing = merged_scores.get(key)
            if existing is None:
                merged_scores[key] = {"item": {**item, "metadata": metadata}, "score": score}
            else:
                existing["score"] += score
                if item.get("rank", 9999) < existing["item"].get("rank", 9999):
                    existing["item"] = {**item, "metadata": metadata}

    ordered = sorted(
        merged_scores.values(),
        key=lambda row: (
            0 if _matches_source_filter(row["item"].get("metadata") or {}, source_filter) else 1,
            -row["score"],
        ),
    )

    result: list[dict[str, Any]] = []
    for index, candidate in enumerate(ordered[:top_k], start=1):
        item = dict(candidate["item"])
        item["rank"] = index
        item["rrf_score"] = candidate["score"]
        result.append(item)
    return result


def evaluate_single_query_with_k(
    test_case: dict[str, Any],
    rrf_k: int,
    top_k: int = 4,
) -> dict[str, Any]:
    query = test_case["query"]
    expected_keywords = test_case["expected_keywords"]
    course_name = test_case.get("ground_truth_source")
    route = route_query_sources(query, course_name=course_name)
    candidate_k = max(top_k * 2, 8)
    dense_rows = retrieve_dense_knowledge(route.query, top_k=candidate_k, source_filter=route.source_filter)
    sparse_rows = retrieve_sparse_knowledge(route.query, top_k=candidate_k, source_filter=route.source_filter)
    results = _rrf_merge(dense_rows, sparse_rows, k=rrf_k, top_k=top_k, source_filter=route.source_filter)

    total_keyword_hits = 0
    first_hit_rank: int | None = None
    for index, result in enumerate(results, start=1):
        keyword_hits = check_keyword_hits(result, expected_keywords)
        total_keyword_hits += keyword_hits
        if keyword_hits >= len(expected_keywords) * 0.3 and first_hit_rank is None:
            first_hit_rank = index

    return {
        "id": test_case["id"],
        "query": query,
        "category": test_case.get("category", ""),
        "hit_at_k": first_hit_rank is not None,
        "first_hit_rank": first_hit_rank,
        "mrr": 1.0 / first_hit_rank if first_hit_rank else 0.0,
        "keyword_coverage": total_keyword_hits / (len(expected_keywords) * len(results)) if results else 0.0,
        "total_keyword_hits": total_keyword_hits,
        "avg_rrf_score": sum(row.get("rrf_score", 0) for row in results) / len(results) if results else 0.0,
        "num_results": len(results),
        "num_dense": len(dense_rows),
        "num_sparse": len(sparse_rows),
    }


def sweep_rrf_parameters(test_file: Path, k_values: list[int], top_k: int = 4) -> dict[str, Any]:
    test_cases = load_test_cases(test_file)
    sweep_results: list[dict[str, Any]] = []

    for k in k_values:
        query_results = [evaluate_single_query_with_k(case, rrf_k=k, top_k=top_k) for case in test_cases]
        hit_rate = sum(1 for row in query_results if row["hit_at_k"]) / len(query_results) if query_results else 0.0
        mean_mrr = sum(row["mrr"] for row in query_results) / len(query_results) if query_results else 0.0
        total_kw_hits = sum(row["total_keyword_hits"] for row in query_results)
        total_expected = sum(len(case.get("expected_keywords", [])) for case in test_cases) * top_k
        kw_coverage = total_kw_hits / total_expected if total_expected else 0.0
        mean_rrf_score = sum(row["avg_rrf_score"] for row in query_results) / len(query_results) if query_results else 0.0

        sweep_results.append(
            {
                "rrf_k": k,
                "total_queries": len(query_results),
                "hit_rate": hit_rate,
                "mean_mrr": mean_mrr,
                "keyword_coverage": kw_coverage,
                "mean_rrf_score": mean_rrf_score,
                "query_results": query_results,
            }
        )

    best = max(sweep_results, key=lambda row: row["hit_rate"])
    return {
        "k_values": k_values,
        "top_k": top_k,
        "sweep_results": sweep_results,
        "best_k": best["rrf_k"],
        "best_hit_rate": best["hit_rate"],
        "best_mrr": best["mean_mrr"],
        "current_k": 60,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep RRF k values")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Test cases file")
    parser.add_argument("--k-values", nargs="+", type=int, default=DEFAULT_K_VALUES, help="RRF k values")
    parser.add_argument("--top-k", type=int, default=4, help="Top-K retrieval count")
    parser.add_argument("--output", help="Optional output JSON file")
    args = parser.parse_args()

    sweep_data = sweep_rrf_parameters(Path(args.cases), args.k_values, args.top_k)
    if args.output:
        Path(args.output).write_text(json.dumps(sweep_data, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(sweep_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
