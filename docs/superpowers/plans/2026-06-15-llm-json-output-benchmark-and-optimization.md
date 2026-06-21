# LLM JSON Output Benchmark And Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find the fastest and most stable structured JSON output method for `ExecutionPlan` and `AgentLearningPathPlan`, then optimize `Llm.ainvoke_json` based on measured data.

**Architecture:** Add a repeatable real-model benchmark harness before changing production behavior. The harness compares tool calling, JSON object mode, JSON schema response format, plain text extraction, and compact JSON prompting on the same schemas and prompts, then writes machine-readable results. Production changes must preserve fallback behavior and must not add model concurrency limiting.

**Tech Stack:** Python 3, FastAPI backend, LangChain `ChatOpenAI`, Pydantic v2, pytest, existing `app.infra.llm.Llm`, existing `config.yaml` model settings.

---

## File Structure

- Create: `server/scripts/benchmark_llm_json_output.py`
  - Command-line benchmark harness using the real configured text model.
  - Runs multiple JSON output strategies against `ExecutionPlan` and `AgentLearningPathPlan`.
  - Writes JSONL raw records and a Markdown summary.
- Create: `server/tests/infra/test_llm_json_benchmark.py`
  - Unit tests for benchmark metric aggregation and strategy selection logic without calling the real model.
- Modify: `server/app/infra/llm.py`
  - Only after benchmark data exists.
  - Add strategy selection and tier timing logs.
  - Remove speculative concurrency throttling if present.
- Modify: `server/config.yaml`
  - Add `models.structured_output_strategy` only after benchmark data justifies the default.
  - Do not add `models.concurrency`.

## Benchmark Methods

Compare these methods:

1. `tool_calling_enhanced`
   - Current tool calling path.
   - Uses function schema plus the existing schema-enhanced prompt.
2. `json_object_schema_prompt`
   - `response_format={"type": "json_object"}` plus full JSON schema prompt.
3. `plain_schema_prompt`
   - No API structured-output feature.
   - Full JSON schema prompt plus local JSON extraction.
4. `json_schema_response_format`
   - `response_format={"type":"json_schema", "json_schema": ...}`.
   - Mark as unsupported when the endpoint rejects the request.
5. `json_object_compact_prompt`
   - `response_format={"type":"json_object"}` plus compact field contract, not the full schema.

Collect these metrics per schema and strategy:

- `attempts`
- `first_try_success_rate`
- `validation_success_rate`
- `p50_latency_ms`
- `p95_latency_ms`
- `avg_latency_ms`
- `parse_error_count`
- `schema_validation_error_count`
- `api_error_count`
- `empty_response_count`
- `unsupported_count`

Selection rule:

1. Prefer the highest `first_try_success_rate`.
2. If two strategies differ by less than 5 percentage points, prefer lower `p95_latency_ms`.
3. If one strategy has any `unsupported_count`, do not choose it as default.
4. If no strategy reaches 90 percent validation success in the smoke benchmark, do not change production defaults. Keep the fallback waterfall and add timing logs only.

## Task 1: Add Benchmark Unit Tests

**Files:**
- Create: `server/tests/infra/test_llm_json_benchmark.py`
- Create later in Task 2: `server/scripts/benchmark_llm_json_output.py`

- [ ] **Step 1: Write the failing tests**

Create `server/tests/infra/test_llm_json_benchmark.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_json_benchmark.py -q
```

Expected: fail during import because `server/scripts/benchmark_llm_json_output.py` does not exist yet.

- [ ] **Step 3: Keep the failing test unstaged until the harness exists**

Do not commit a red test. Leave `server/tests/infra/test_llm_json_benchmark.py` in the working tree and continue to Task 2.

## Task 2: Add Real-Model Benchmark Harness

**Files:**
- Create: `server/scripts/benchmark_llm_json_output.py`
- Test: `server/tests/infra/test_llm_json_benchmark.py`

- [ ] **Step 1: Create the benchmark harness**

Create `server/scripts/benchmark_llm_json_output.py`:

```python
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from langchain_core.messages import HumanMessage

from app.infra.llm import (
    Llm,
    _collect_schema_root_candidates,
    _flatten_nested_config,
    _iter_json_objects,
    _simplify_anyof_refs,
)
from app.infra.utils import parse_first_json_object, parse_first_json_value
from app.path.schemas import AgentLearningPathPlan
from app.resource.schemas import ExecutionPlan


@dataclass(frozen=True)
class BenchmarkPrompt:
    prompt_id: str
    schema: type
    input_data: str
    max_tokens: int | None = None


@dataclass(frozen=True)
class BenchmarkRecord:
    schema: str
    strategy: str
    prompt_id: str
    run_index: int
    ok: bool
    latency_ms: float
    error_type: str
    error_message: str
    output_chars: int


@dataclass(frozen=True)
class BenchmarkSummary:
    schema: str
    strategy: str
    attempts: int
    first_try_success_rate: float
    validation_success_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    avg_latency_ms: float
    parse_error_count: int
    schema_validation_error_count: int
    api_error_count: int
    empty_response_count: int
    unsupported_count: int


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = round((len(ordered) - 1) * percentile)
    return ordered[rank]


def aggregate_records(records: list[BenchmarkRecord]) -> dict[tuple[str, str], BenchmarkSummary]:
    grouped: dict[tuple[str, str], list[BenchmarkRecord]] = {}
    for record in records:
        grouped.setdefault((record.schema, record.strategy), []).append(record)

    result: dict[tuple[str, str], BenchmarkSummary] = {}
    for key, items in grouped.items():
        latencies = [item.latency_ms for item in items]
        success_count = sum(1 for item in items if item.ok)
        attempts = len(items)
        result[key] = BenchmarkSummary(
            schema=key[0],
            strategy=key[1],
            attempts=attempts,
            first_try_success_rate=success_count / attempts if attempts else 0.0,
            validation_success_rate=success_count / attempts if attempts else 0.0,
            p50_latency_ms=_percentile(latencies, 0.50),
            p95_latency_ms=_percentile(latencies, 0.95),
            avg_latency_ms=statistics.fmean(latencies) if latencies else 0.0,
            parse_error_count=sum(1 for item in items if item.error_type == "parse_error"),
            schema_validation_error_count=sum(1 for item in items if item.error_type == "schema_validation_error"),
            api_error_count=sum(1 for item in items if item.error_type == "api_error"),
            empty_response_count=sum(1 for item in items if item.error_type == "empty_response"),
            unsupported_count=sum(1 for item in items if item.error_type == "unsupported"),
        )
    return result


def _summary_value(row: BenchmarkSummary | dict[str, Any], name: str) -> Any:
    if isinstance(row, BenchmarkSummary):
        return getattr(row, name)
    return row[name]


def choose_default_strategy(schema_name: str, summary: dict[tuple[str, str], BenchmarkSummary | dict[str, Any]]) -> str | None:
    rows: list[tuple[str, BenchmarkSummary | dict[str, Any]]] = [
        (strategy, row)
        for (schema, strategy), row in summary.items()
        if schema == schema_name and _summary_value(row, "unsupported_count") == 0
    ]
    if not rows:
        return None

    best_success = max(float(_summary_value(row, "first_try_success_rate")) for _, row in rows)
    if best_success < 0.90:
        return None

    candidates = [
        (strategy, row)
        for strategy, row in rows
        if best_success - float(_summary_value(row, "first_try_success_rate")) <= 0.05
    ]
    candidates.sort(key=lambda item: float(_summary_value(item[1], "p95_latency_ms")))
    return candidates[0][0]


def build_prompts() -> list[BenchmarkPrompt]:
    resource_base = (
        "你是多智能体学习资源系统的 Planning Agent。"
        "请根据学习需求生成教学蓝图 blueprint，并为 reading、quiz、ppt 三个 agent 生成 agent_instructions。"
        "\n\n## 学习需求\n我想快速了解并上手 Python 爬虫，主要抓取静态网页数据。"
        "\n\n## 学习场景\nself_study"
        "\n\n## 学习者画像\n有 Python 基础，但不了解 HTTP、HTML 解析和反爬。"
        "\n\n## 需要生成的资源类型\nreading, quiz, ppt"
    )
    path_base = (
        "你是学习路径规划 Agent。请输出完整学习路径。"
        "\n\n## 目标\n4 周内掌握 Python 爬虫，从 HTTP 基础到 requests、BeautifulSoup、数据保存。"
        "\n\n## 用户画像\n有 Python 入门经验，每天可学习 45 分钟，偏好项目驱动。"
        "\n\n## 搜索参考\n入门路径通常包括 HTTP 基础、HTML/CSS 选择器、requests、BeautifulSoup、异常处理、robots 与速率限制、CSV/JSON 保存。"
        "\n\n要求：生成 3 到 5 个阶段，8 到 12 个节点。节点 prerequisites 使用 node_id。"
    )
    return [
        BenchmarkPrompt("resource_python_spider", ExecutionPlan, resource_base, max_tokens=2048),
        BenchmarkPrompt(
            "resource_network_basics",
            ExecutionPlan,
            resource_base.replace("Python 爬虫", "计算机网络基础").replace("HTTP、HTML 解析和反爬", "TCP/IP、DNS、HTTP"),
            max_tokens=2048,
        ),
        BenchmarkPrompt("path_python_spider", AgentLearningPathPlan, path_base, max_tokens=4096),
        BenchmarkPrompt(
            "path_vue_frontend",
            AgentLearningPathPlan,
            path_base.replace("Python 爬虫", "Vue 3 前端开发").replace("requests、BeautifulSoup、数据保存", "组件、路由、状态管理、API 调用").replace("HTTP 基础、HTML/CSS 选择器、requests、BeautifulSoup、异常处理、robots 与速率限制、CSV/JSON 保存", "HTML/CSS、TypeScript、Vue SFC、Vue Router、Pinia、接口联调"),
            max_tokens=4096,
        ),
    ]


def _full_schema_messages(prompt: BenchmarkPrompt) -> list[HumanMessage]:
    schema_text = json.dumps(prompt.schema.model_json_schema(), ensure_ascii=False, indent=2)
    required = prompt.schema.model_json_schema().get("required", [])
    return [
        HumanMessage(
            content=(
                f"{prompt.input_data}\n\n"
                "[FORMAT INSTRUCTION]\n"
                "Return exactly one valid JSON object. Do not include markdown or explanations.\n"
                f"The root object must contain these required fields: {', '.join(required)}.\n"
                "The JSON object must match this schema:\n"
                f"{schema_text}"
            )
        )
    ]


def _compact_messages(prompt: BenchmarkPrompt) -> list[HumanMessage]:
    if prompt.schema is ExecutionPlan:
        contract = (
            "Return JSON with keys blueprint, agent_instructions, personalization_summary. "
            "blueprint must include topic, learner_goal, prerequisite_concepts, core_concepts, difficult_points, "
            "concept_relations, example_scenarios, practice_targets, resource_guidance. "
            "agent_instructions must be an array of objects with agent_id, focus, difficulty, personalization_notes, constraints."
        )
    elif prompt.schema is AgentLearningPathPlan:
        contract = (
            "Return JSON with keys title, eta_days, confidence, stages, nodes. "
            "stages must be an array of objects with stage_id, title, description. "
            "nodes must be an array of objects with node_id, stage_id, title, prerequisites, mastery_target, "
            "estimated_minutes, difficulty, recommendation_reason, priority. "
            "resource_policy is optional."
        )
    else:
        contract = "Return one JSON object matching the requested schema."
    return [
        HumanMessage(
            content=(
                f"{prompt.input_data}\n\n"
                "[FORMAT INSTRUCTION]\n"
                "Return exactly one valid JSON object. Do not include markdown or explanations.\n"
                f"{contract}"
            )
        )
    ]


def _validate_content(schema: type, content: str) -> Any:
    if not content.strip():
        raise ValueError("empty_response")
    try:
        data = parse_first_json_object(content)
    except Exception:
        candidates = _collect_schema_root_candidates(content, schema)
        if not candidates:
            candidates = _iter_json_objects(content)
        if not candidates:
            raise
        data = candidates[0]
    data = _flatten_nested_config(data, schema)
    return schema.model_validate(data)


def _clean_tool_args(args: Any) -> Any:
    if isinstance(args, dict):
        return {key: _clean_tool_args(value) for key, value in args.items()}
    if isinstance(args, list):
        return [_clean_tool_args(value) for value in args]
    if isinstance(args, str):
        stripped = args.strip()
        if "{" in stripped or "[" in stripped:
            try:
                parsed = parse_first_json_value(stripped)
            except Exception:
                return args
            if isinstance(parsed, (dict, list)):
                return _clean_tool_args(parsed)
    return args


async def run_tool_calling_enhanced(llm: Llm, prompt: BenchmarkPrompt) -> tuple[Any, int]:
    model = llm._bind_text_model(max_tokens=prompt.max_tokens)
    name = prompt.schema.__name__
    tools = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": f"Return {name}",
                "parameters": _simplify_anyof_refs(prompt.schema.model_json_schema()),
            },
        }
    ]
    runnable = model.bind_tools(tools, tool_choice={"type": "function", "function": {"name": name}})
    response = await runnable.ainvoke(_full_schema_messages(prompt))
    tool_calls = getattr(response, "tool_calls", []) or []
    for tool_call in tool_calls:
        args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
        if isinstance(args, str):
            args = json.loads(args)
        data = _flatten_nested_config(_clean_tool_args(args), prompt.schema)
        return prompt.schema.model_validate(data), len(json.dumps(data, ensure_ascii=False, default=str))
    content = getattr(response, "content", "") or ""
    return _validate_content(prompt.schema, content), len(content)


async def run_json_object_schema_prompt(llm: Llm, prompt: BenchmarkPrompt) -> tuple[Any, int]:
    model = llm._bind_text_model(max_tokens=prompt.max_tokens).bind(response_format={"type": "json_object"})
    response = await model.ainvoke(_full_schema_messages(prompt))
    content = getattr(response, "content", "") or ""
    return _validate_content(prompt.schema, content), len(content)


async def run_plain_schema_prompt(llm: Llm, prompt: BenchmarkPrompt) -> tuple[Any, int]:
    model = llm._bind_text_model(max_tokens=prompt.max_tokens)
    response = await model.ainvoke(_full_schema_messages(prompt))
    content = getattr(response, "content", "") or ""
    return _validate_content(prompt.schema, content), len(content)


async def run_json_schema_response_format(llm: Llm, prompt: BenchmarkPrompt) -> tuple[Any, int]:
    model = llm._bind_text_model(max_tokens=prompt.max_tokens).bind(
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": prompt.schema.__name__,
                "schema": prompt.schema.model_json_schema(),
                "strict": True,
            },
        }
    )
    response = await model.ainvoke(_compact_messages(prompt))
    content = getattr(response, "content", "") or ""
    return _validate_content(prompt.schema, content), len(content)


async def run_json_object_compact_prompt(llm: Llm, prompt: BenchmarkPrompt) -> tuple[Any, int]:
    model = llm._bind_text_model(max_tokens=prompt.max_tokens).bind(response_format={"type": "json_object"})
    response = await model.ainvoke(_compact_messages(prompt))
    content = getattr(response, "content", "") or ""
    return _validate_content(prompt.schema, content), len(content)


STRATEGIES: dict[str, Callable[[Llm, BenchmarkPrompt], Any]] = {
    "tool_calling_enhanced": run_tool_calling_enhanced,
    "json_object_schema_prompt": run_json_object_schema_prompt,
    "plain_schema_prompt": run_plain_schema_prompt,
    "json_schema_response_format": run_json_schema_response_format,
    "json_object_compact_prompt": run_json_object_compact_prompt,
}


def classify_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "response_format" in message and "json_schema" in message:
        return "unsupported"
    if "unsupported" in message and "json" in message:
        return "unsupported"
    if "empty_response" in message or "empty" in message:
        return "empty_response"
    if "validation" in type(exc).__name__.lower() or "field required" in message or "missing" in message:
        return "schema_validation_error"
    if "json" in type(exc).__name__.lower() or "decode" in message or "parse" in message:
        return "parse_error"
    return "api_error"


async def run_one(llm: Llm, strategy: str, prompt: BenchmarkPrompt, run_index: int) -> BenchmarkRecord:
    start = time.perf_counter()
    output_chars = 0
    try:
        _, output_chars = await STRATEGIES[strategy](llm, prompt)
        ok = True
        error_type = ""
        error_message = ""
    except Exception as exc:
        ok = False
        error_type = classify_error(exc)
        error_message = str(exc)[:500]
    latency_ms = (time.perf_counter() - start) * 1000
    return BenchmarkRecord(
        schema=prompt.schema.__name__,
        strategy=strategy,
        prompt_id=prompt.prompt_id,
        run_index=run_index,
        ok=ok,
        latency_ms=latency_ms,
        error_type=error_type,
        error_message=error_message,
        output_chars=output_chars,
    )


def write_markdown_summary(path: Path, summary: dict[tuple[str, str], BenchmarkSummary]) -> None:
    lines = [
        "# LLM JSON Output Benchmark Summary",
        "",
        "| Schema | Strategy | Attempts | Success | p50 ms | p95 ms | Parse Errors | Schema Errors | API Errors | Unsupported |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in sorted(summary):
        row = summary[key]
        lines.append(
            "| {schema} | {strategy} | {attempts} | {success:.0%} | {p50:.0f} | {p95:.0f} | {parse} | {schema_errors} | {api} | {unsupported} |".format(
                schema=row.schema,
                strategy=row.strategy,
                attempts=row.attempts,
                success=row.validation_success_rate,
                p50=row.p50_latency_ms,
                p95=row.p95_latency_ms,
                parse=row.parse_error_count,
                schema_errors=row.schema_validation_error_count,
                api=row.api_error_count,
                unsupported=row.unsupported_count,
            )
        )
    lines.append("")
    for schema_name in sorted({schema for schema, _ in summary}):
        chosen = choose_default_strategy(schema_name, summary)
        lines.append(f"- Recommended `{schema_name}` default: `{chosen or 'keep_existing_waterfall'}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out-dir", default="tmp/llm-json-benchmark")
    parser.add_argument("--strategy", action="append", choices=sorted(STRATEGIES))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    strategies = args.strategy or list(STRATEGIES)
    prompts = build_prompts()
    llm = Llm()

    records: list[BenchmarkRecord] = []
    jsonl_path = out_dir / "records.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fp:
        for prompt in prompts:
            for strategy in strategies:
                for run_index in range(args.runs):
                    record = await run_one(llm, strategy, prompt, run_index)
                    records.append(record)
                    fp.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
                    fp.flush()
                    status = "OK" if record.ok else record.error_type
                    print(
                        f"{record.schema} {record.strategy} {record.prompt_id} run={run_index} "
                        f"{status} {record.latency_ms:.0f}ms"
                    )

    summary = aggregate_records(records)
    (out_dir / "summary.json").write_text(
        json.dumps({f"{schema}:{strategy}": asdict(row) for (schema, strategy), row in summary.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_summary(out_dir / "summary.md", summary)
    print(f"Wrote {jsonl_path}")
    print(f"Wrote {out_dir / 'summary.md'}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run the unit test**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_json_benchmark.py -q
```

Expected: pass.

- [ ] **Step 3: Commit the benchmark harness**

```bash
cd /Users/apple/Code/software
rtk git add server/scripts/benchmark_llm_json_output.py server/tests/infra/test_llm_json_benchmark.py
rtk git commit -m "test: add llm json output benchmark"
```

## Task 3: Run Smoke Benchmark And Capture Results

**Files:**
- Read: `server/config.yaml`
- Generate: `server/tmp/llm-json-benchmark/records.jsonl`
- Generate: `server/tmp/llm-json-benchmark/summary.json`
- Generate: `server/tmp/llm-json-benchmark/summary.md`

- [ ] **Step 1: Run the smoke benchmark**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run python scripts/benchmark_llm_json_output.py --runs 3 --out-dir tmp/llm-json-benchmark
```

Expected:

- The command completes.
- `tmp/llm-json-benchmark/records.jsonl` exists.
- `tmp/llm-json-benchmark/summary.md` exists.
- Each strategy has records for `ExecutionPlan` and `AgentLearningPathPlan`.

- [ ] **Step 2: Inspect the summary**

Run:

```bash
cd /Users/apple/Code/software/server
rtk sed -n '1,220p' tmp/llm-json-benchmark/summary.md
```

Expected: a Markdown table showing success rates and latency for all strategies.

- [ ] **Step 3: Decide whether to expand the benchmark**

Use this decision:

- If the best strategy for both schemas has at least 90 percent success and clearly lower p95 latency, continue to Task 4.
- If any top strategy has less than 90 percent success, run a larger benchmark before touching production code:

```bash
cd /Users/apple/Code/software/server
rtk uv run python scripts/benchmark_llm_json_output.py --runs 10 --out-dir tmp/llm-json-benchmark-runs10
```

Expected: the larger benchmark confirms or overturns the smoke result.

- [ ] **Step 4: Do not commit raw benchmark output unless requested**

Keep `server/tmp/llm-json-benchmark*` untracked. It is evidence for the change, not source code.

## Task 4: Add Strategy Unit Tests For `ainvoke_json`

**Files:**
- Modify: `server/tests/infra/test_llm_gateway.py`
- Modify later in Task 5: `server/app/infra/llm.py`

- [ ] **Step 1: Write tests for strategy order and no concurrency behavior**

In `server/tests/infra/test_llm_gateway.py`, ensure the fake model records `bind` and `bind_tools` calls. Add these tests:

```python
@pytest.mark.asyncio
async def test_ainvoke_json_json_first_uses_json_mode_before_tool_calling() -> None:
    llm = Llm()
    fake = _FakeModel(text='{"name": "Eve", "score": 99}')
    llm._text_model = fake
    llm._structured_output_strategy = "json_first"

    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Eve", score=99)
    assert fake.bind_calls[-1] == {"response_format": {"type": "json_object"}}
    assert fake.bound_tools is None


@pytest.mark.asyncio
async def test_ainvoke_json_tool_first_keeps_existing_order() -> None:
    llm = Llm()
    fake = _FakeModel(
        tool_calls=[{"name": "submit_score", "args": {"name": "Alice", "score": 92}}],
    )
    llm._text_model = fake
    llm._structured_output_strategy = "tool_first"

    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Alice", score=92)
    assert fake.bound_tools is not None
    assert fake.bind_calls == []


def test_llm_does_not_read_or_create_concurrency_limit(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", _CapturedChatOpenAI)

    config = {
        "models": {
            "model_name": "generalv3.5",
            "api_key": "test-key",
            "base_url": "https://spark-api-open.xf-yun.com/v1/chat/completions",
            "concurrency": 7,
            "timeout": 120,
            "max_retries": 1,
        }
    }

    def _fake_get(path: str, default=None):
        if path == "models":
            return config["models"]
        if path == "models.vision":
            return {}
        return default

    monkeypatch.setattr(llm_module, "get", _fake_get)

    llm = Llm()

    assert not hasattr(llm, "_text_semaphore")
```

- [ ] **Step 2: Run tests to verify they fail against current speculative implementation**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_gateway.py -q
```

Expected:

- Strategy tests may pass if `json_first` already exists.
- `test_llm_does_not_read_or_create_concurrency_limit` fails if speculative semaphore logic still exists.

- [ ] **Step 3: Commit tests**

```bash
cd /Users/apple/Code/software
rtk git add server/tests/infra/test_llm_gateway.py
rtk git commit -m "test: lock llm json strategy behavior"
```

## Task 5: Optimize `Llm.ainvoke_json` Based On Benchmark Results

**Files:**
- Modify: `server/app/infra/llm.py`
- Modify: `server/config.yaml`
- Test: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Remove concurrency limiting from `Llm`**

In `server/app/infra/llm.py`:

- Remove `import asyncio` if it is only used for `Semaphore`.
- Remove `self._text_semaphore`.
- Remove reading `models.concurrency`.
- Remove `_ainvoke_with_limit`.
- Make `ainvoke` call `runnable.ainvoke(...)` directly.
- Make `astream` call `runnable.astream(...)` directly.
- Make `ainvoke_json` call `fallback_model.ainvoke(...)`, `runnable.ainvoke(...)`, and `model.ainvoke(...)` directly.

The resulting `ainvoke` should look like:

```python
    async def ainvoke(
        self,
        input_data,
        *,
        model: Any | None = None,
        temperature: float = INFERENCE_TEMPERATURE,
        max_tokens: int | None = None,
    ) -> Any:
        runnable = self._bind_text_model(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return await runnable.ainvoke(input_data)
```

- [ ] **Step 2: Add strategy resolution without hard-coding a guess**

Keep:

```python
    def _resolve_structured_output_strategy(self) -> str:
        strategy = self._structured_output_strategy or "auto"
        if strategy in {"tool_first", "json_first"}:
            return strategy
        if strategy != "auto":
            logger.warning("[LLM] 未知 structured_output_strategy=%s，回退 auto", strategy)
        return "tool_first"
```

If the benchmark proves `json_object_schema_prompt` or `json_object_compact_prompt` is best for both core schemas, then and only then change the final line to:

```python
        return "json_first"
```

If the benchmark differs by schema, do not make `auto` global. Add a schema-aware resolver:

```python
    def _resolve_structured_output_strategy(self, schema: type) -> str:
        strategy = self._structured_output_strategy or "auto"
        if strategy in {"tool_first", "json_first"}:
            return strategy
        if strategy != "auto":
            logger.warning("[LLM] 未知 structured_output_strategy=%s，回退 auto", strategy)
        schema_name = schema.__name__
        schema_overrides = {
            "ExecutionPlan": "json_first",
            "AgentLearningPathPlan": "tool_first",
        }
        return schema_overrides.get(schema_name, "tool_first")
```

Replace the override values with the actual benchmark winners.

- [ ] **Step 3: Add tier timing logs**

Inside `ainvoke_json`, wrap each tier with `time.perf_counter()`. Add `import time`.

Use this helper inside `ainvoke_json`:

```python
        def _elapsed_ms(start: float) -> int:
            return round((time.perf_counter() - start) * 1000)
```

For each tier start:

```python
            tier_start = time.perf_counter()
```

For each tier success:

```python
                    logger.info(
                        "[LLM] ainvoke_json tier_success schema=%s strategy=%s tier=%s duration_ms=%d",
                        schema.__name__, strategy, "json_mode_first", _elapsed_ms(tier_start),
                    )
```

For each tier failure:

```python
                logger.warning(
                    "[LLM] ainvoke_json tier_failed schema=%s strategy=%s tier=%s duration_ms=%d error=%s: %s",
                    schema.__name__, strategy, "json_mode_first", _elapsed_ms(tier_start), type(exc).__name__, exc,
                )
```

- [ ] **Step 4: Preserve fallback order**

The final order must be:

```text
if strategy == "json_first":
    Tier 0: JSON mode
    if success: return

Tier 1: Tool calling
if success: return

if JSON mode has not been attempted:
    Tier 2: JSON mode
    if success: return

Tier 3: Plain text plus local extraction
if success: return

raise ServiceError with all tier errors
```

Do not run JSON mode twice when `json_first` already attempted it.

- [ ] **Step 5: Add config only if benchmark supports it**

In `server/config.yaml`, add:

```yaml
models:
  structured_output_strategy: "auto"
```

Do not add:

```yaml
models:
  concurrency: 7
```

- [ ] **Step 6: Run unit tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_gateway.py tests/infra/test_llm_json_benchmark.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit production optimization**

```bash
cd /Users/apple/Code/software
rtk git add server/app/infra/llm.py server/config.yaml server/tests/infra/test_llm_gateway.py
rtk git commit -m "fix: optimize llm json output strategy"
```

## Task 6: Verify Resource And Path Domains Separately

**Files:**
- Read: `server/app/resource/agents/planning.py`
- Read: `server/app/path/planner.py`
- Test: existing backend tests

- [ ] **Step 1: Run resource-domain tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/resource/test_agent_integration.py -q
```

Expected: pass.

- [ ] **Step 2: Run path-domain tests that are not known stale imports**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/path/test_resource_policy.py -q
```

Expected: pass unless it hits a pre-existing stale import from `app.path.agents.planner`.

- [ ] **Step 3: Do not merge resource and path persistence or detail models**

Confirm the production change only touches `Llm.ainvoke_json` and config strategy. It must not merge:

- standalone resource generation records
- learning-path planning records
- detail pages
- persistence models

## Task 7: Manual Acceptance Test With Logs

**Files:**
- Read logs emitted by backend
- Generate one resource plan and one path plan through the app or API

- [ ] **Step 1: Start backend**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run fastapi dev app/main.py --port 9999
```

Expected: backend starts on port 9999.

- [ ] **Step 2: Trigger standalone multi-agent resource generation**

Use the existing frontend or API flow to create one standalone resource generation request for:

```text
我想快速了解并上手 Python 爬虫，主要抓取静态网页数据
```

Expected logs include one `ainvoke_json tier_success` line for `ExecutionPlan`.

- [ ] **Step 3: Trigger learning path planning**

Use the existing frontend or API flow to create one learning path for:

```text
4 周内掌握 Python 爬虫，从 HTTP 基础到 requests、BeautifulSoup、数据保存
```

Expected logs include one `ainvoke_json tier_success` line for `AgentLearningPathPlan`.

- [ ] **Step 4: Confirm first-tier success in logs**

If the benchmark-selected default is `json_first`, expected log shape:

```text
[LLM] ainvoke_json tier_success schema=ExecutionPlan strategy=json_first tier=json_mode_first duration_ms=...
[LLM] ainvoke_json tier_success schema=AgentLearningPathPlan strategy=json_first tier=json_mode_first duration_ms=...
```

If the benchmark-selected default is `tool_first`, expected log shape:

```text
[LLM] ainvoke_json tier_success schema=ExecutionPlan strategy=tool_first tier=tool_calling duration_ms=...
[LLM] ainvoke_json tier_success schema=AgentLearningPathPlan strategy=tool_first tier=tool_calling duration_ms=...
```

If most real requests fall through to Tier 2 or Tier 3, do not claim the optimization worked. Return to Task 3 and expand benchmark prompts.

## Self-Review

- Spec coverage: The plan includes real-model benchmark, multiple JSON output methods, stability and latency metrics, data-based strategy selection, production optimization, and domain-specific verification for resource and path.
- Placeholder scan: The plan contains concrete files, commands, code, expected outcomes, and decision rules. It avoids open-ended implementation placeholders.
- Type consistency: `BenchmarkRecord`, `BenchmarkSummary`, `aggregate_records`, and `choose_default_strategy` names match across tests and implementation. Production strategy names match `json_first` and `tool_first`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-llm-json-output-benchmark-and-optimization.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
