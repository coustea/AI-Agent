from __future__ import annotations

from scripts.benchmark_llm_json_output import (
    BenchmarkRecord,
    BenchmarkSummary,
    aggregate_records,
    choose_default_strategy,
)


def test_aggregate_records_computes_success_rate_and_latency_percentiles() -> None:
    records = [
        BenchmarkRecord(
            schema="ExecutionPlan",
            strategy="json_object_schema_prompt",
            prompt_id="resource_python_spider",
            run_index=0,
            ok=True,
            latency_ms=1000.0,
            error_type="",
            error_message="",
            output_chars=300,
        ),
        BenchmarkRecord(
            schema="ExecutionPlan",
            strategy="json_object_schema_prompt",
            prompt_id="resource_python_spider",
            run_index=1,
            ok=True,
            latency_ms=2000.0,
            error_type="",
            error_message="",
            output_chars=320,
        ),
        BenchmarkRecord(
            schema="ExecutionPlan",
            strategy="json_object_schema_prompt",
            prompt_id="resource_python_spider",
            run_index=2,
            ok=False,
            latency_ms=3000.0,
            error_type="schema_validation_error",
            error_message="missing blueprint",
            output_chars=120,
        ),
    ]

    summary = aggregate_records(records)

    row = summary[("ExecutionPlan", "json_object_schema_prompt")]
    assert row.attempts == 3
    assert row.success_rate == 2 / 3
    assert row.p50_latency_ms == 2000.0
    assert row.p95_latency_ms == 3000.0
    assert row.schema_validation_error_count == 1


def test_choose_default_strategy_prefers_success_before_latency() -> None:
    summary = {
        ("AgentLearningPathPlan", "fast_but_flaky"): BenchmarkSummary(
            schema="AgentLearningPathPlan",
            strategy="fast_but_flaky",
            attempts=10,
            success_rate=0.80,
            p50_latency_ms=4000.0,
            p95_latency_ms=5000.0,
            avg_latency_ms=4200.0,
            parse_error_count=0,
            schema_validation_error_count=0,
            api_error_count=0,
            empty_response_count=0,
            unsupported_count=0,
        ),
        ("AgentLearningPathPlan", "slower_stable"): BenchmarkSummary(
            schema="AgentLearningPathPlan",
            strategy="slower_stable",
            attempts=10,
            success_rate=1.0,
            p50_latency_ms=8000.0,
            p95_latency_ms=9000.0,
            avg_latency_ms=8500.0,
            parse_error_count=0,
            schema_validation_error_count=0,
            api_error_count=0,
            empty_response_count=0,
            unsupported_count=0,
        ),
    }

    assert choose_default_strategy("AgentLearningPathPlan", summary) == "slower_stable"


def test_choose_default_strategy_rejects_unsupported_json_schema() -> None:
    summary = {
        ("ExecutionPlan", "json_schema_response_format"): BenchmarkSummary(
            schema="ExecutionPlan",
            strategy="json_schema_response_format",
            attempts=5,
            success_rate=1.0,
            p50_latency_ms=900.0,
            p95_latency_ms=1000.0,
            avg_latency_ms=950.0,
            parse_error_count=0,
            schema_validation_error_count=0,
            api_error_count=0,
            empty_response_count=0,
            unsupported_count=1,
        ),
        ("ExecutionPlan", "json_object_schema_prompt"): BenchmarkSummary(
            schema="ExecutionPlan",
            strategy="json_object_schema_prompt",
            attempts=5,
            success_rate=0.95,
            p50_latency_ms=1800.0,
            p95_latency_ms=2000.0,
            avg_latency_ms=1900.0,
            parse_error_count=0,
            schema_validation_error_count=0,
            api_error_count=0,
            empty_response_count=0,
            unsupported_count=0,
        ),
    }

    assert choose_default_strategy("ExecutionPlan", summary) == "json_object_schema_prompt"
