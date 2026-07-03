from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_results(filepath: Path) -> dict[str, Any]:
    with filepath.open(encoding="utf-8") as file:
        return json.load(file)


def compare_single_query(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": baseline["id"],
        "query": baseline["query"],
        "category": baseline["category"],
        "hit_at_k": {
            "baseline": baseline["hit_at_k"],
            "current": current["hit_at_k"],
            "improved": current["hit_at_k"] and not baseline["hit_at_k"],
        },
        "mrr": {
            "baseline": baseline["mrr"],
            "current": current["mrr"],
            "delta": current["mrr"] - baseline["mrr"],
        },
        "avg_distance": {
            "baseline": baseline["avg_distance"],
            "current": current["avg_distance"],
            "delta": current["avg_distance"] - baseline["avg_distance"],
        },
        "first_hit_rank": {
            "baseline": baseline.get("first_hit_rank"),
            "current": current.get("first_hit_rank"),
        },
    }


def compare_results(baseline_file: Path, current_file: Path) -> dict[str, Any]:
    baseline_data = load_results(baseline_file)
    current_data = load_results(current_file)

    baseline_by_id = {row["id"]: row for row in baseline_data}
    current_by_id = {row["id"]: row for row in current_data}

    query_comparisons = [
        compare_single_query(baseline_by_id[query_id], current_by_id[query_id])
        for query_id in baseline_by_id
        if query_id in current_by_id
    ]

    improved_count = sum(1 for comparison in query_comparisons if comparison["hit_at_k"]["improved"])
    degraded_count = sum(1 for comparison in query_comparisons if comparison["mrr"]["delta"] < -0.1)

    return {
        "baseline_file": str(baseline_file),
        "current_file": str(current_file),
        "total_queries": len(query_comparisons),
        "improved_queries": improved_count,
        "degraded_queries": degraded_count,
        "comparisons": query_comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare retrieval evaluation results")
    parser.add_argument("--baseline", required=True, help="Baseline result file path")
    parser.add_argument("--current", required=True, help="Current result file path")
    parser.add_argument("--output", help="Optional output report path")
    args = parser.parse_args()

    comparison = compare_results(Path(args.baseline), Path(args.current))
    if args.output:
        output_file = Path(args.output)
        output_file.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
