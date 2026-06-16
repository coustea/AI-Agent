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
    success_rate: float
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
            success_rate=success_count / attempts if attempts else 0.0,
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

    best_success = max(float(_summary_value(row, "success_rate")) for _, row in rows)
    if best_success < 0.90:
        return None

    candidates = [
        (strategy, row)
        for strategy, row in rows
        if best_success - float(_summary_value(row, "success_rate")) <= 0.05
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
                success=row.success_rate,
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
