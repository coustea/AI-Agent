"""Sweep RRF constant k to find optimal value for this corpus."""

import sys
from pathlib import Path

# Add server dir to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.tools.knowledge import (
    retrieve_dense_knowledge,
    retrieve_sparse_knowledge,
    _metadata_key,
    route_query_sources,
)
from eval.knowledge_retrieval.evaluate import load_test_cases, check_keyword_hits

K_VALUES = [10, 20, 30, 40, 60, 100]


def _rrf_merge(dense_rows, sparse_rows, k, top_k=4, source_filter=None):
    """Manually merge with a specific k value for sweep testing."""
    from app.chat.tools.knowledge import _matches_source_filter
    merged_scores: dict = {}
    for rows in (dense_rows, sparse_rows):
        for item in rows:
            metadata = dict(item.get("metadata") or {})
            key = _metadata_key(metadata)
            score = 1.0 / (k + int(item.get("rank") or 0))
            existing = merged_scores.get(key)
            if existing is None:
                merged_scores[key] = {"item": item, "score": score}
            else:
                existing["score"] += score

    ordered = sorted(
        merged_scores.values(),
        key=lambda x: (
            0 if _matches_source_filter(x["item"].get("metadata") or {}, source_filter) else 1,
            -x["score"],
        ),
    )
    return ordered[:top_k]


def sweep():
    test_cases = load_test_cases()
    print(f"Testing {len(test_cases)} cases with k ∈ {K_VALUES}\n")

    for k in K_VALUES:
        hits = 0
        total_keywords = 0
        matched_keywords = 0

        for case in test_cases:
            query = case["query"]
            route = route_query_sources(query, course_name=case.get("ground_truth_source"))
            dense = retrieve_dense_knowledge(route.query, top_k=8, source_filter=route.source_filter)
            sparse = retrieve_sparse_knowledge(route.query, top_k=8, source_filter=route.source_filter)

            results = _rrf_merge(dense, sparse, k, top_k=4, source_filter=route.source_filter)
            # check_keyword_hits expects a dict with "text" key, so pass each result properly
            kw_hits = 0
            for r in results:
                item = r.get("item", {})
                kw_hits += check_keyword_hits(item, case.get("expected_keywords", []))
            if kw_hits > 0:
                hits += 1
            matched_keywords += kw_hits
            total_keywords += len(case.get("expected_keywords", []))

        hit_rate = hits / len(test_cases) if test_cases else 0
        kw_rate = matched_keywords / total_keywords if total_keywords else 0
        print(f"k={k:3d}  Hit@4={hit_rate:.2f}  KeywordCoverage={kw_rate:.2f}")


if __name__ == "__main__":
    sweep()
