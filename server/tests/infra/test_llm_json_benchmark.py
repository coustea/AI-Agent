from __future__ import annotations

from scripts.benchmark_llm_json_output import (
    BenchmarkRecord,
    aggregate_records,
    choose_default_strategy,
)


def test_aggregate_records_computes_success_rates_and_latency_percentiles() -> None:
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
    assert row.validation_success_rate == 2 / 3
    assert row.first_try_success_rate == 2 / 3
    assert row.p50_latency_ms == 2000.0
    assert row.p95_latency_ms == 3000.0
    assert row.schema_validation_error_count == 1


def test_choose_default_strategy_prefers_success_before_latency() -> None:
    summary = {
        ("AgentLearningPathPlan", "fast_but_flaky"): {
            "validation_success_rate": 0.80,
            "first_try_success_rate": 0.80,
            "p95_latency_ms": 5000.0,
            "unsupported_count": 0,
        },
        ("AgentLearningPathPlan", "slower_stable"): {
            "validation_success_rate": 1.0,
            "first_try_success_rate": 1.0,
            "p95_latency_ms": 9000.0,
            "unsupported_count": 0,
        },
    }

    assert choose_default_strategy("AgentLearningPathPlan", summary) == "slower_stable"


def test_choose_default_strategy_rejects_unsupported_json_schema() -> None:
    summary = {
        ("ExecutionPlan", "json_schema_response_format"): {
            "validation_success_rate": 1.0,
            "first_try_success_rate": 1.0,
            "p95_latency_ms": 1000.0,
            "unsupported_count": 1,
        },
        ("ExecutionPlan", "json_object_schema_prompt"): {
            "validation_success_rate": 0.95,
            "first_try_success_rate": 0.95,
            "p95_latency_ms": 2000.0,
            "unsupported_count": 0,
        },
    }

    assert choose_default_strategy("ExecutionPlan", summary) == "json_object_schema_prompt"
