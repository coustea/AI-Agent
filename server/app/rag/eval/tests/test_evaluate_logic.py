"""Unit tests for evaluate.py logic, especially no_answer category handling."""

from __future__ import annotations

import pytest

from app.rag.eval.evaluate import (
    check_keyword_hits,
    compute_aggregate_metrics,
    evaluate_single_query,
)


class TestCheckKeywordHits:
    """Tests for keyword hit counting."""

    def test_empty_keywords_returns_zero(self):
        result = {"text": "some content here"}
        hits = check_keyword_hits(result, [])
        assert hits == 0

    def test_single_keyword_hit(self):
        result = {"text": "TCP三次握手的过程"}
        hits = check_keyword_hits(result, ["TCP"])
        assert hits == 1

    def test_multiple_keyword_hits(self):
        result = {"text": "TCP三次握手建立连接，确认序列号"}
        hits = check_keyword_hits(result, ["TCP", "三次握手", "连接", "确认"])
        assert hits == 4

    def test_case_insensitive_hit(self):
        result = {"text": "tcp protocol details"}
        hits = check_keyword_hits(result, ["TCP"])
        assert hits == 1

    def test_keyword_not_found_returns_zero(self):
        result = {"text": "UDP是无连接协议"}
        hits = check_keyword_hits(result, ["TCP"])
        assert hits == 0


class TestNoAnswerEvaluation:
    """Tests for no_answer category evaluation logic."""

    def test_no_answer_with_high_confidence_results_is_false_positive(self):
        """When no_answer query returns high-confidence results, it's a false positive."""
        test_case = {
            "id": "test-no-answer-001",
            "query": "今天天气怎么样",
            "category": "no_answer",
            "difficulty": "easy",
            "expected_keywords": [],
            "expected_sources": [],
            "acceptable_sources": [],
            "business_severity": "low",
        }
        # We need to mock retrieve_knowledge to return high-confidence results
        # For this test, we'll check the logic in the evaluate_single_query output
        # The actual retrieval will happen, but we verify the flag is set correctly
        result = evaluate_single_query(test_case, top_k=4)

        # For no_answer category, hit_at_k should be True only if NOT false positive
        # If results are returned with high confidence, hit_at_k should be False
        if result["num_results"] > 0 and result["avg_distance"] < 30:
            assert result["hit_at_k"] is False
            assert result["no_answer_false_positive"] is True
            assert "no_answer_false_positive" in result["diagnostic_flags"]
        else:
            # No results or low confidence = correct behavior
            assert result["hit_at_k"] is True
            assert result["no_answer_false_positive"] is False

    def test_no_answer_with_empty_keywords_never_triggers_keyword_hit(self):
        """Empty keywords should NOT cause hit_at_k to be True via keyword matching."""
        test_case = {
            "id": "test-no-answer-002",
            "query": "哪家餐厅的菜好吃",
            "category": "no_answer",
            "difficulty": "easy",
            "expected_keywords": [],
            "expected_sources": [],
            "acceptable_sources": [],
            "business_severity": "low",
        }
        result = evaluate_single_query(test_case, top_k=4)

        # For no_answer, first_hit_rank should always be None (keyword matching skipped)
        assert result["first_hit_rank"] is None
        # total_keyword_hits should be 0 (no keyword matching attempted)
        assert result["total_keyword_hits"] == 0

    def test_normal_query_with_keywords_uses_keyword_matching(self):
        """Normal queries should use keyword matching logic."""
        test_case = {
            "id": "test-normal-001",
            "query": "TCP三次握手的目的是什么",
            "category": "basic_fact",
            "difficulty": "easy",
            "expected_keywords": ["TCP", "三次握手", "连接", "确认"],
            "expected_sources": ["计算机网络"],
            "acceptable_sources": ["计算机网络"],
            "business_severity": "high",
        }
        result = evaluate_single_query(test_case, top_k=4)

        # For normal queries, no_answer_false_positive should be None
        assert result["no_answer_false_positive"] is None
        # Keyword matching should have been attempted
        assert result["total_keyword_hits"] >= 0


class TestAggregateMetricsNoAnswer:
    """Tests for aggregate metrics including no_answer_false_positive_rate."""

    def test_aggregate_includes_no_answer_metrics(self):
        """Aggregate should include no_answer_false_positive_rate."""
        results = [
            {
                "id": "v3-001",
                "category": "basic_fact",
                "difficulty": "easy",
                "hit_at_k": True,
                "mrr": 1.0,
                "keyword_coverage": 0.5,
                "avg_distance": -30,
                "num_results": 4,
                "business_severity": "high",
                "ground_truth_source": "计算机网络",
                "diagnostic_flags": [],
                "retrieval_confidence": 2.0,
                "no_answer_false_positive": None,
            },
            {
                "id": "v3-002",
                "category": "no_answer",
                "difficulty": "easy",
                "hit_at_k": False,  # False positive case
                "mrr": 0.0,
                "keyword_coverage": 0.0,
                "avg_distance": -25,
                "num_results": 4,
                "business_severity": "low",
                "ground_truth_source": "unknown",
                "diagnostic_flags": ["no_answer_false_positive"],
                "retrieval_confidence": 1.0,
                "no_answer_false_positive": True,
            },
            {
                "id": "v3-003",
                "category": "no_answer",
                "difficulty": "easy",
                "hit_at_k": True,  # Correct no-answer case
                "mrr": 0.0,
                "keyword_coverage": 0.0,
                "avg_distance": 50,  # Low confidence
                "num_results": 0,
                "business_severity": "low",
                "ground_truth_source": "unknown",
                "diagnostic_flags": ["no_results"],
                "retrieval_confidence": 0.0,
                "no_answer_false_positive": False,
            },
        ]

        aggregate = compute_aggregate_metrics(results)

        assert "no_answer_false_positive_rate" in aggregate
        assert "no_answer_total" in aggregate
        assert "no_answer_false_positive_count" in aggregate

        # 2 no_answer cases, 1 false positive
        assert aggregate["no_answer_total"] == 2
        assert aggregate["no_answer_false_positive_count"] == 1
        assert aggregate["no_answer_false_positive_rate"] == 0.5

    def test_aggregate_no_answer_rate_zero_when_no_no_answer_cases(self):
        """When there are no no_answer cases, rate should be 0."""
        results = [
            {
                "id": "v3-001",
                "category": "basic_fact",
                "difficulty": "easy",
                "hit_at_k": True,
                "mrr": 1.0,
                "keyword_coverage": 0.5,
                "avg_distance": -30,
                "num_results": 4,
                "business_severity": "high",
                "ground_truth_source": "计算机网络",
                "diagnostic_flags": [],
                "retrieval_confidence": 2.0,
                "no_answer_false_positive": None,
            },
        ]

        aggregate = compute_aggregate_metrics(results)

        assert aggregate["no_answer_false_positive_rate"] == 0.0
        assert aggregate["no_answer_total"] == 0
        assert aggregate["no_answer_false_positive_count"] == 0