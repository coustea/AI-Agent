from __future__ import annotations

from typing import Any


def compute_source_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    source_scored_results = [
        result for result in results if result.get("category") != "no_answer" and result.get("expected_sources")
    ]
    total = len(source_scored_results)
    if total == 0:
        return {
            "top1_source_accuracy": 0.0,
            "cross_book_pollution_rate": 0.0,
            "route_precision_rate": 0.0,
            "candidate_recall_rate": 0.0,
        }

    top1_hits = 0
    total_sources = 0
    polluted_sources = 0
    route_precision_hits = 0
    candidate_recall_hits = 0
    for item in source_scored_results:
        expected = item.get("expected_sources") or []
        acceptable = item.get("acceptable_sources") or expected
        returned = item.get("result_sources") or []
        routed = item.get("route_source_filter") or []
        if returned and any(expected_source in returned[0] for expected_source in expected):
            top1_hits += 1
        if returned and any(any(acceptable_source in source for acceptable_source in acceptable) for source in returned):
            candidate_recall_hits += 1
        if routed and expected and any(
            any(expected_source in routed_source or routed_source in expected_source for expected_source in expected)
            for routed_source in routed
        ):
            route_precision_hits += 1
        total_sources += len(returned)
        polluted_sources += sum(
            1 for source in returned if expected and not any(expected_source in source for expected_source in expected)
        )

    return {
        "top1_source_accuracy": top1_hits / total,
        "cross_book_pollution_rate": polluted_sources / total_sources if total_sources else 0.0,
        "route_precision_rate": route_precision_hits / total,
        "candidate_recall_rate": candidate_recall_hits / total,
    }


def build_diagnostics_summary(
    aggregate: dict[str, Any],
    source_metrics: dict[str, float],
) -> dict[str, Any]:
    reasons: list[str] = []
    primary_bottleneck = "overall"

    route_precision_rate = float(source_metrics.get("route_precision_rate", 0.0))
    candidate_recall_rate = float(source_metrics.get("candidate_recall_rate", 0.0))
    cross_book_pollution_rate = float(source_metrics.get("cross_book_pollution_rate", 0.0))
    hit_at_k_rate = float(aggregate.get("answerable_hit_at_k_rate", aggregate.get("hit_at_k_rate", 0.0)))
    no_answer_false_positive_rate = float(aggregate.get("no_answer_false_positive_rate", 0.0))

    if no_answer_false_positive_rate > 0.3:
        reasons.append("no_answer_false_positive_rate")
    if route_precision_rate < 0.85:
        reasons.append("route_precision_rate")
    if candidate_recall_rate < 0.95:
        reasons.append("candidate_recall_rate")
    if cross_book_pollution_rate > 0.15:
        reasons.append("cross_book_pollution_rate")
    if hit_at_k_rate < 0.95:
        reasons.append("hit_at_k_rate")

    if "no_answer_false_positive_rate" in reasons:
        primary_bottleneck = "no_answer"
    elif "route_precision_rate" in reasons:
        primary_bottleneck = "route"
    elif "candidate_recall_rate" in reasons:
        primary_bottleneck = "candidate_recall"
    elif "cross_book_pollution_rate" in reasons:
        primary_bottleneck = "contamination"
    elif reasons:
        primary_bottleneck = "overall"

    return {
        "primary_bottleneck": primary_bottleneck,
        "reasons": reasons,
    }
