from __future__ import annotations

from typing import Any


THRESHOLDS = {
    "hit_at_k_rate": 0.95,
    "top1_source_accuracy": 0.85,
    "cross_book_pollution_rate": 0.15,
    "route_precision_rate": 0.85,
    "candidate_recall_rate": 0.95,
    "no_result_rate": 0.01,
    "p95_ms": 800,
}


def evaluate_acceptance(aggregate: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    hit_at_k_rate = float(aggregate.get("hit_at_k_rate", 0.0))
    no_result_rate = float(aggregate.get("no_result_rate", 1.0))
    source_metrics = dict(aggregate.get("source_metrics") or {})
    latency_metrics = dict(aggregate.get("latency_metrics") or {})

    top1_source_accuracy = float(source_metrics.get("top1_source_accuracy", 0.0))
    cross_book_pollution_rate = float(source_metrics.get("cross_book_pollution_rate", 1.0))
    route_precision_rate = float(source_metrics.get("route_precision_rate", 0.0))
    candidate_recall_rate = float(source_metrics.get("candidate_recall_rate", 0.0))
    p95_ms = float(latency_metrics.get("p95_ms", float("inf")))

    if hit_at_k_rate < THRESHOLDS["hit_at_k_rate"]:
        failures.append("hit_at_k_rate")
    if top1_source_accuracy < THRESHOLDS["top1_source_accuracy"]:
        failures.append("top1_source_accuracy")
    if cross_book_pollution_rate > THRESHOLDS["cross_book_pollution_rate"]:
        failures.append("cross_book_pollution_rate")
    if route_precision_rate < THRESHOLDS["route_precision_rate"]:
        failures.append("route_precision_rate")
    if candidate_recall_rate < THRESHOLDS["candidate_recall_rate"]:
        failures.append("candidate_recall_rate")
    if no_result_rate > THRESHOLDS["no_result_rate"]:
        failures.append("no_result_rate")
    if p95_ms > THRESHOLDS["p95_ms"]:
        failures.append("p95_ms")

    return {
        "passed": not failures,
        "failures": failures,
        "thresholds": dict(THRESHOLDS),
    }
