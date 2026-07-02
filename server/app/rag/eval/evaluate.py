from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.rag.eval.benchmark_metrics import build_diagnostics_summary, compute_source_metrics
from app.rag.knowledge import retrieve_knowledge
from app.rag.knowledge_router import route_query_sources


EVAL_ROOT = Path(__file__).resolve().parent
DATASETS_DIR = EVAL_ROOT / "datasets"
REPORTS_DIR = EVAL_ROOT / "reports"
RESULTS_DIR = EVAL_ROOT / "results"
DEFAULT_CASES_PATH = EVAL_ROOT / "benchmark_v2" / "cases.json"
DEFAULT_TIMESTAMP = "2026-06-21"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run knowledge retrieval evaluation")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to evaluation cases JSON")
    parser.add_argument("--label", default="default", help="Output label suffix")
    parser.add_argument("--top-k", type=int, default=4, help="Top-K retrieval cutoff")
    return parser.parse_args(argv)


def load_test_cases(test_file: Path | None = None) -> list[dict[str, Any]]:
    target = Path(test_file) if test_file is not None else DEFAULT_CASES_PATH
    if not target.is_absolute():
        target = Path.cwd() / target
    if target.is_dir():
        aggregated: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for child in sorted(target.glob("*.json")):
            with child.open(encoding="utf-8") as file:
                cases = json.load(file)
            if not isinstance(cases, list):
                raise ValueError(f"Test cases file must contain a list: {child}")
            for case in cases:
                case_id = str(case.get("id") or "").strip()
                if case_id in seen_ids:
                    raise ValueError(f"Duplicate test case id: {case_id}")
                if case_id:
                    seen_ids.add(case_id)
                aggregated.append(case)
        return aggregated

    with target.open(encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list):
        raise ValueError(f"Test cases file must contain a list: {target}")
    return cases


def check_keyword_hits(result: dict[str, Any], expected_keywords: list[str]) -> int:
    text = str(result.get("text") or "").lower()
    return sum(1 for keyword in expected_keywords if keyword.lower() in text)


def evaluate_single_query(test_case: dict[str, Any], top_k: int = 4) -> dict[str, Any]:
    query = test_case["query"]
    expected_keywords = list(test_case["expected_keywords"])
    retrieval_course_name = test_case.get("ground_truth_source")
    reporting_course_name = retrieval_course_name or (list(test_case.get("expected_sources") or []) or [None])[0]
    category = test_case.get("category", "")
    is_no_answer = category == "no_answer"

    route = route_query_sources(query, course_name=retrieval_course_name)
    results = retrieve_knowledge(query, top_k=top_k, course_name=retrieval_course_name)

    total_keyword_hits = 0
    first_hit_rank: int | None = None

    # For no_answer category: check if system incorrectly returns confident results
    # A false positive occurs when the system returns results for a query that should have no answer
    no_answer_false_positive = False
    if is_no_answer:
        # no_answer queries should not return confident results
        # If results are returned, check if they are high-confidence
        if results:
            # Calculate confidence of returned results
            distances = [abs(result.get("distance", 999)) for result in results]
            avg_distance = sum(distances) / len(distances) if distances else 999.0
            # Low distance (high similarity) = false positive
            # Threshold: avg_distance < 30 indicates confident retrieval (false positive)
            no_answer_false_positive = avg_distance < 30
    else:
        # Normal queries: use keyword matching
        for index, result in enumerate(results, start=1):
            keyword_hits = check_keyword_hits(result, expected_keywords)
            total_keyword_hits += keyword_hits
            if keyword_hits >= len(expected_keywords) * 0.3 and first_hit_rank is None:
                first_hit_rank = index

    hit_at_k = first_hit_rank is not None if not is_no_answer else not no_answer_false_positive
    mrr = 1.0 / first_hit_rank if first_hit_rank else 0.0
    keyword_coverage = (
        total_keyword_hits / (len(expected_keywords) * len(results))
        if expected_keywords and results
        else 0.0
    )
    distances = [result.get("distance", 999) for result in results]
    avg_distance = sum(distances) / len(distances) if distances else 999.0

    confidence = 0.0
    if len(results) >= 2:
        scores = [abs(result.get("distance", 0.0)) for result in results[:5]]
        top1 = scores[0]
        avg_rest = sum(scores[1:]) / len(scores[1:]) if len(scores) > 1 else top1
        confidence = top1 / avg_rest if avg_rest > 0 else 0.0

    expected_sources = list(test_case.get("expected_sources", []))
    acceptable_sources = list(test_case.get("acceptable_sources", []))
    result_sources = [result.get("metadata", {}).get("source", "") for result in results]
    diagnostic_flags: list[str] = []
    if not results:
        diagnostic_flags.append("no_results")
    if is_no_answer and no_answer_false_positive:
        diagnostic_flags.append("no_answer_false_positive")
    if expected_sources and result_sources and not any(
        any(expected_source in source for expected_source in expected_sources)
        for source in result_sources
    ):
        diagnostic_flags.append("candidate_miss")
    if expected_sources and any(
        source and not any(expected_source in source for expected_source in expected_sources)
        for source in result_sources
    ):
        diagnostic_flags.append("cross_book_pollution")
    if route.source_filter and route.applied_filter_scope == "strict" and expected_sources:
        if not any(
            any(expected_source in routed_source or routed_source in expected_source for expected_source in expected_sources)
            for routed_source in route.source_filter
        ):
            diagnostic_flags.append("route_mismatch")

    return {
        "id": test_case["id"],
        "query": query,
        "category": category,
        "difficulty": test_case["difficulty"],
        "ground_truth_source": reporting_course_name,
        "num_results": len(results),
        "hit_at_k": hit_at_k,
        "first_hit_rank": first_hit_rank,
        "mrr": mrr,
        "keyword_coverage": keyword_coverage,
        "avg_distance": avg_distance,
        "total_keyword_hits": total_keyword_hits,
        "expected_keyword_count": len(expected_keywords),
        "retrieval_confidence": confidence,
        "retrieval_modes": [result.get("retrieval_mode") for result in results],
        "top_result_snippet": (results[0].get("text") or "")[:200] if results else "",
        "result_sources": result_sources,
        "expected_sources": expected_sources,
        "acceptable_sources": acceptable_sources,
        "business_severity": test_case.get("business_severity", "medium"),
        "route_source_filter": list(route.source_filter or []),
        "route_mode": route.route_mode,
        "route_confidence": route.route_confidence,
        "route_applied_scope": route.applied_filter_scope,
        "route_filter_size": len(route.source_filter or ()),
        "route_matched_terms": list(route.matched_terms or ()),
        "diagnostic_flags": diagnostic_flags,
        "no_answer_false_positive": no_answer_false_positive if is_no_answer else None,
    }


def compute_aggregate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total_queries = len(results)
    if total_queries == 0:
        return {}

    hit_at_k_count = sum(1 for result in results if result["hit_at_k"])
    total_mrr = sum(result["mrr"] for result in results)
    total_keyword_coverage = sum(result["keyword_coverage"] for result in results)
    total_avg_distance = sum(result["avg_distance"] for result in results)
    no_result_count = sum(1 for result in results if int(result.get("num_results", 0)) == 0)

    by_difficulty: dict[str, dict[str, float]] = {}
    by_category: dict[str, dict[str, float]] = {}
    by_business_severity: dict[str, dict[str, float]] = {}
    by_course: dict[str, dict[str, float]] = {}
    diagnostic_flag_counts: dict[str, int] = {}
    for result in results:
        difficulty = result["difficulty"]
        category = result["category"]
        for bucket, key in ((by_difficulty, difficulty), (by_category, category)):
            if key not in bucket:
                bucket[key] = {"count": 0, "hit": 0, "mrr": 0.0}
            bucket[key]["count"] += 1
            if result["hit_at_k"]:
                bucket[key]["hit"] += 1
            bucket[key]["mrr"] += result["mrr"]

        severity = str(result.get("business_severity") or "medium")
        if severity not in by_business_severity:
            by_business_severity[severity] = {"count": 0, "hit": 0, "mrr": 0.0}
        by_business_severity[severity]["count"] += 1
        if result["hit_at_k"]:
            by_business_severity[severity]["hit"] += 1
        by_business_severity[severity]["mrr"] += result["mrr"]

        course = str(result.get("ground_truth_source") or "unknown")
        if course not in by_course:
            by_course[course] = {"count": 0, "hit": 0, "mrr": 0.0, "no_result": 0}
        by_course[course]["count"] += 1
        if result["hit_at_k"]:
            by_course[course]["hit"] += 1
        by_course[course]["mrr"] += result["mrr"]
        if int(result.get("num_results", 0)) == 0:
            by_course[course]["no_result"] += 1

        for flag in result.get("diagnostic_flags", []):
            diagnostic_flag_counts[flag] = diagnostic_flag_counts.get(flag, 0) + 1

    confidences = [
        result.get("retrieval_confidence", 0.0)
        for result in results
        if result.get("retrieval_confidence")
    ]
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    low_confidence_rate = (
        sum(1 for confidence in confidences if confidence < 1.4) / len(confidences)
        if confidences
        else 0.0
    )

    # Calculate no_answer_false_positive_rate
    no_answer_cases = [r for r in results if r.get("category") == "no_answer"]
    no_answer_total = len(no_answer_cases)
    no_answer_false_positive_count = sum(
        1 for r in no_answer_cases if r.get("no_answer_false_positive") is True
    )
    no_answer_false_positive_rate = (
        no_answer_false_positive_count / no_answer_total if no_answer_total > 0 else 0.0
    )

    return {
        "total_queries": total_queries,
        "hit_at_k_rate": hit_at_k_count / total_queries,
        "mean_mrr": total_mrr / total_queries,
        "mean_keyword_coverage": total_keyword_coverage / total_queries,
        "mean_avg_distance": total_avg_distance / total_queries,
        "no_result_rate": no_result_count / total_queries,
        "mean_confidence": mean_confidence,
        "low_confidence_rate": low_confidence_rate,
        "no_answer_false_positive_rate": no_answer_false_positive_rate,
        "no_answer_total": no_answer_total,
        "no_answer_false_positive_count": no_answer_false_positive_count,
        "by_difficulty": {
            key: {
                "hit_rate": value["hit"] / value["count"],
                "mrr": value["mrr"] / value["count"],
            }
            for key, value in by_difficulty.items()
        },
        "by_category": {
            key: {
                "hit_rate": value["hit"] / value["count"],
                "mrr": value["mrr"] / value["count"],
            }
            for key, value in by_category.items()
        },
        "by_business_severity": {
            key: {
                "hit_rate": value["hit"] / value["count"],
                "mrr": value["mrr"] / value["count"],
            }
            for key, value in by_business_severity.items()
        },
        "by_course": {
            key: {
                "count": int(value["count"]),
                "hit_rate": value["hit"] / value["count"],
                "mrr": value["mrr"] / value["count"],
                "no_result_rate": value["no_result"] / value["count"],
            }
            for key, value in by_course.items()
        },
        "diagnostic_flag_counts": diagnostic_flag_counts,
    }


def save_results(
    detailed_results: list[dict[str, Any]],
    aggregate: dict[str, Any],
    label: str = "default",
) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)

    source_metrics = dict(aggregate.get("source_metrics") or {})
    if source_metrics and "diagnostics" not in aggregate:
        aggregate["diagnostics"] = build_diagnostics_summary(aggregate, source_metrics)

    detailed_file = RESULTS_DIR / f"detailed_{label}_{DEFAULT_TIMESTAMP}.json"
    aggregate_file = RESULTS_DIR / f"aggregate_{label}_{DEFAULT_TIMESTAMP}.json"

    detailed_file.write_text(json.dumps(detailed_results, ensure_ascii=False, indent=2), encoding="utf-8")
    aggregate_file.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    test_cases = load_test_cases(Path(args.cases) if args.cases else None)
    detailed_results = [evaluate_single_query(test_case, top_k=args.top_k) for test_case in test_cases]
    aggregate = compute_aggregate_metrics(detailed_results)
    source_metrics = compute_source_metrics(detailed_results)
    aggregate["source_metrics"] = source_metrics
    aggregate["diagnostics"] = build_diagnostics_summary(aggregate, source_metrics)
    save_results(detailed_results, aggregate, label=args.label)


if __name__ == "__main__":
    main()
