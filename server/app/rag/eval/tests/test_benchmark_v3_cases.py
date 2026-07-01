from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


CASES_PATH = Path(__file__).resolve().parents[1] / "benchmark_v3" / "cases.json"


REQUIRED_FIELDS = {
    "id",
    "query",
    "category",
    "difficulty",
    "expected_keywords",
    "expected_sources",
    "acceptable_sources",
    "business_severity",
}


REQUIRED_CATEGORIES = {
    "basic_fact",
    "concept_explanation",
    "mechanism_explanation",
    "procedure_or_algorithm",
    "cross_chapter_reasoning",
    "ambiguous_routing",
    "cross_book_pollution",
    "no_answer",
    "noisy_user_query",
    "mixed_language",
}


REQUIRED_DIFFICULTIES = {"easy", "medium", "hard"}
REQUIRED_SEVERITIES = {"low", "medium", "high"}


def load_cases() -> list[dict[str, Any]]:
    assert CASES_PATH.exists(), f"missing benchmark file: {CASES_PATH}"
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def test_benchmark_v3_has_enough_cases():
    cases = load_cases()
    assert len(cases) >= 80


def test_benchmark_v3_case_ids_are_unique_and_prefixed():
    cases = load_cases()
    ids = [case.get("id") for case in cases]
    assert len(ids) == len(set(ids))
    assert all(isinstance(case_id, str) and case_id.startswith("v3-") for case_id in ids)


def test_benchmark_v3_cases_have_required_fields_and_types():
    cases = load_cases()
    for case in cases:
        missing = REQUIRED_FIELDS - set(case)
        assert not missing, f"{case.get('id')} missing fields: {sorted(missing)}"
        assert isinstance(case["query"], str) and case["query"].strip()
        assert isinstance(case["category"], str) and case["category"] in REQUIRED_CATEGORIES
        assert isinstance(case["difficulty"], str) and case["difficulty"] in REQUIRED_DIFFICULTIES
        assert isinstance(case["business_severity"], str) and case["business_severity"] in REQUIRED_SEVERITIES
        assert isinstance(case["expected_keywords"], list)
        assert isinstance(case["expected_sources"], list)
        assert isinstance(case["acceptable_sources"], list)
        assert all(isinstance(item, str) and item.strip() for item in case["expected_keywords"])
        assert all(isinstance(item, str) and item.strip() for item in case["expected_sources"])
        assert all(isinstance(item, str) and item.strip() for item in case["acceptable_sources"])


def test_benchmark_v3_has_required_distribution():
    cases = load_cases()
    categories = Counter(case["category"] for case in cases)
    difficulties = Counter(case["difficulty"] for case in cases)
    severities = Counter(case["business_severity"] for case in cases)

    for category in REQUIRED_CATEGORIES:
        assert categories[category] >= 5, f"category too small: {category}={categories[category]}"

    assert difficulties["easy"] >= 15
    assert difficulties["medium"] >= 35
    assert difficulties["hard"] >= 20
    assert severities["high"] >= 25


def test_benchmark_v3_covers_core_sources():
    cases = load_cases()
    all_sources = "\n".join(
        source
        for case in cases
        for source in case.get("expected_sources", []) + case.get("acceptable_sources", [])
    )
    required_source_terms = [
        "计算机网络",
        "操作系统",
        "数据结构",
        "计算机组成原理",
        "Java",
        "Python",
        "数据库",
    ]
    for term in required_source_terms:
        assert term in all_sources, f"missing source coverage for {term}"


def test_no_answer_cases_have_empty_expected_sources():
    cases = load_cases()
    no_answer_cases = [case for case in cases if case["category"] == "no_answer"]
    assert len(no_answer_cases) >= 5
    for case in no_answer_cases:
        assert case["expected_sources"] == []
        assert case["acceptable_sources"] == []
        assert case["expected_keywords"] == []
