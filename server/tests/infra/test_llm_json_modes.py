# -*- coding: utf-8 -*-
"""LLM JSON 输出模式集成测试。

真实调用 LLM，测试 3 种 JSON 结构化输出模式的稳定性和耗时：
  1. function_calling — Function Calling 模式（Tier 1，最稳定）
  2. json_mode        — API 保证返回合法 JSON，Pydantic 校验（Tier 2）
  3. prompt + 解析    — Prompt 注入 + parse_first_json_object（Tier 3，兜底）

测试使用系统中真实使用的复杂 Pydantic schema，按复杂度递增：
  - MemoryUpdateOutput   — 简单（4 字段，bool/float/Optional）
  - AgentQuestionSet     — 中等（嵌套 list，dict[str,str]）
  - QuizPayload          — 复杂题库（三层嵌套，model_validator，enum，pattern）
  - VideoOutline         — 视频大纲（嵌套 + model_validator，场景约束）
  - LearningPlan         — 最复杂（四层嵌套，跨模型 validator，dict 值约束）

运行方式：
  # 使用 config.yaml 中的默认模型
  RUN_LLM_JSON_MODE_TEST=1 uv run pytest tests/infra/test_llm_json_modes.py -v -s

  # 使用其他模型（如 OpenAI）覆盖配置
  RUN_LLM_JSON_MODE_TEST=1 LLM_BASE_URL=https://api.openai.com/v1 \
    LLM_API_KEY=sk-xxx LLM_MODEL=gpt-4o \
    uv run pytest tests/infra/test_llm_json_modes.py -v -s

默认跳过，避免每次 pytest 都消耗 API 额度。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.config import get
from app.infra.llm import ChatModel, _inject_json_instruction
from app.infra.utils import parse_first_json_object

# 导入系统中真实使用的 schema
from app.chat.memory.types import MemoryUpdateOutput
from app.path.schemas import AgentQuestionSet, LearningPlan
from app.resource.schemas.quiz import QuizPayload
from app.shared.video.schemas import VideoOutline

# ============ 环境控制 ============

_MODEL_CFG = get("models", {}) or {}
_BASE_URL = (
    os.getenv("LLM_BASE_URL", "")
    or (_MODEL_CFG.get("base_url", "") or "").rstrip("/")
)
_API_KEY = os.getenv("LLM_API_KEY", "") or _MODEL_CFG.get("api_key", "")
_MODEL_NAME = os.getenv("LLM_MODEL", "") or _MODEL_CFG.get("model_name", "")

# 如果环境变量未启用则跳过；如果模型配置缺失也跳过
_SKIP_REASON = None
if os.getenv("RUN_LLM_JSON_MODE_TEST") != "1":
    _SKIP_REASON = "LLM JSON 模式集成测试默认跳过；设置 RUN_LLM_JSON_MODE_TEST=1 运行。"
elif not _BASE_URL or not _API_KEY or not _MODEL_NAME:
    _SKIP_REASON = "模型配置缺失（base_url/api_key/model_name），跳过 LLM 测试"

if _SKIP_REASON:
    pytestmark = pytest.mark.skip(reason=_SKIP_REASON)


def _make_model(**overrides: Any) -> ChatModel:
    """创建测试用 ChatModel 实例。允许网络重试以应对不稳定连接。"""
    kw: dict[str, Any] = {
        "model": _MODEL_NAME,
        "api_key": _API_KEY,
        "base_url": _BASE_URL,
        "temperature": 0.1,
        "timeout": 180,
        "max_retries": 2,
    }
    kw.update(overrides)
    return ChatModel(**kw)


# ============ 测试 Prompt ============

PROMPTS: dict[type[BaseModel], list[Any]] = {
    MemoryUpdateOutput: [
        SystemMessage(content="你是一个学习记忆分析助手。分析对话内容，判断是否需要更新长期记忆。"),
        HumanMessage(content=(
            "用户说：'我以后希望你能多用图表来解释概念，我总是记不住纯文字的描述。'\n\n"
            "请判断是否需要更新长期记忆，返回 JSON。"
        )),
    ],
    AgentQuestionSet: [
        SystemMessage(content="你是一个出题助手。根据知识点生成测验题目。"),
        HumanMessage(content=(
            "请为「Python 列表推导式」生成 3 道选择题，每道包含 2-4 个选项。"
            "返回 JSON 格式的题目集。"
        )),
    ],
    QuizPayload: [
        SystemMessage(content="你是一个专业的出题助手。根据教学大纲生成结构化测验。"),
        HumanMessage(content=(
            "请为「HTTP 协议基础」生成 4 道测验题，要求：\n"
            "- 第1题：单选题(single_choice)，难度 basic，恰好4个选项(A/B/C/D)，answer为单个选项标签\n"
            "- 第2题：多选题(multiple_choice)，难度 medium，恰好4个选项(A/B/C/D)，answer为2-3个选项标签数组\n"
            "- 第3题：判断题(true_false)，难度 basic，options必须为空数组，answer为布尔值\n"
            "- 第4题：填空题(fill_blank)，难度 medium，options必须为空数组，answer为字符串\n"
            "每道题必须包含 explanation 和 knowledge_points。id从1开始递增。"
        )),
    ],
    VideoOutline: [
        SystemMessage(content="你是一个视频教学大纲规划助手。根据知识点生成视频场景大纲。"),
        HumanMessage(content=(
            "请为「Python 爬虫入门」生成视频教学大纲，要求：\n"
            "- 第1个场景 role=hook（开场引入），visual_type=title_intro\n"
            "- 第2-4个场景 role=concept（概念讲解），visual_type=concept_explain\n"
            "- 第5个场景 role=recap（总结回顾），visual_type=compare_summary\n"
            "- 每个场景必须有 scene_id、index(从1递增)、title、learning_objective、content_hint、source_ids\n"
            "注意：role 只能是 hook/concept/example/process/misconception/practice/recap 之一\n"
            "注意：visual_type 只能是 title_intro/concept_explain/process_flow/compare_summary 等之一\n"
            "返回 JSON 格式的视频大纲。"
        )),
    ],
    LearningPlan: [
        SystemMessage(content="你是一个学习路径规划助手。根据学习目标生成结构化学习路径。"),
        HumanMessage(content=(
            "请为「Python 网络爬虫从入门到实战」规划学习路径，要求：\n"
            "- 至少 2 个阶段（stage），每个有 stage_id 和 title\n"
            "- 至少 4 个学习节点（node），分布在不同阶段，每个有 node_id/stage_id/title/difficulty/priority\n"
            "- 节点之间有前置依赖关系(prerequisites)\n"
            "返回 JSON 格式的学习计划。"
        )),
    ],
}

# schema 复杂度排序（简单 → 复杂）
SCHEMA_ORDER: list[type[BaseModel]] = [
    MemoryUpdateOutput,
    AgentQuestionSet,
    QuizPayload,
    VideoOutline,
    LearningPlan,
]

# ============ 结果记录 ============


@dataclass
class ModeResult:
    """单个模式 × schema 的测试结果。"""

    mode: str
    schema_name: str
    success: bool
    latency_ms: int
    error: str = ""
    pydantic_ok: bool = False
    field_count_ok: bool = False
    detail: str = ""


_all_results: list[ModeResult] = []


def _record(result: ModeResult) -> None:
    _all_results.append(result)


# ============ 3 种模式的测试实现 ============


def _inspect_result(result: BaseModel, schema: type[BaseModel]) -> tuple[bool, bool, str]:
    """检查 Pydantic 实例的关键字段是否正常填充。"""
    pydantic_ok = True
    field_count_ok = True
    detail_parts: list[str] = []
    for fname, finfo in schema.model_fields.items():
        val = getattr(result, fname, None)
        if finfo.is_required() and val is None:
            field_count_ok = False
            detail_parts.append(f"{fname}=None(缺失)")
        elif val is not None:
            if isinstance(val, list):
                detail_parts.append(f"{fname}=list[{len(val)}]")
            elif isinstance(val, dict):
                detail_parts.append(f"{fname}=dict[{len(val)}keys]")
            elif isinstance(val, BaseModel):
                detail_parts.append(f"{fname}={type(val).__name__}")
            else:
                detail_parts.append(f"{fname}={str(val)[:40]}")
        else:
            detail_parts.append(f"{fname}=None(optional)")
    return pydantic_ok, field_count_ok, "; ".join(detail_parts)


async def _test_function_calling(schema: type[BaseModel], messages: list[Any]) -> ModeResult:
    """Tier 1: function_calling — Function Calling 模式。"""
    model = _make_model()
    t0 = time.perf_counter()
    try:
        runnable = model.with_structured_output(schema, method="function_calling")
        result = await runnable.ainvoke(messages)
        latency = round((time.perf_counter() - t0) * 1000)

        if not isinstance(result, schema):
            return ModeResult("function_calling", schema.__name__, False, latency,
                              error=f"返回类型 {type(result).__name__} ≠ {schema.__name__}")

        pydantic_ok, field_count_ok, detail = _inspect_result(result, schema)
        return ModeResult("function_calling", schema.__name__, True, latency,
                          pydantic_ok=pydantic_ok, field_count_ok=field_count_ok, detail=detail)
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000)
        return ModeResult("function_calling", schema.__name__, False, latency,
                          error=f"{type(exc).__name__}: {exc}")


async def _test_json_mode(schema: type[BaseModel], messages: list[Any]) -> ModeResult:
    """Tier 2: json_mode — API 保证返回合法 JSON，Pydantic 校验。"""
    model = _make_model()
    t0 = time.perf_counter()
    try:
        runnable = model.with_structured_output(schema, method="json_mode")
        result = await runnable.ainvoke(messages)
        latency = round((time.perf_counter() - t0) * 1000)

        if not isinstance(result, schema):
            return ModeResult("json_mode", schema.__name__, False, latency,
                              error=f"返回类型 {type(result).__name__} ≠ {schema.__name__}")

        pydantic_ok, field_count_ok, detail = _inspect_result(result, schema)
        return ModeResult("json_mode", schema.__name__, True, latency,
                          pydantic_ok=pydantic_ok, field_count_ok=field_count_ok, detail=detail)
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000)
        return ModeResult("json_mode", schema.__name__, False, latency,
                          error=f"{type(exc).__name__}: {exc}")


async def _test_prompt_fallback(schema: type[BaseModel], messages: list[Any]) -> ModeResult:
    """Tier 3: prompt 注入 + parse_first_json_object 解析。"""
    model = _make_model()
    t0 = time.perf_counter()
    try:
        injected = _inject_json_instruction(messages, schema)
        resp = await model.ainvoke(injected)
        latency = round((time.perf_counter() - t0) * 1000)

        content = getattr(resp, "content", "") or ""
        if not content.strip():
            return ModeResult("prompt", schema.__name__, False, latency, error="空响应")

        # 解析 JSON
        try:
            parsed_dict = parse_first_json_object(content)
        except Exception as parse_exc:
            return ModeResult("prompt", schema.__name__, False, latency,
                              error=f"JSON 解析失败: {parse_exc}",
                              detail=f"原始输出前200字: {content[:200]}")

        # Pydantic 校验
        try:
            result = schema.model_validate(parsed_dict)
        except Exception as val_exc:
            return ModeResult("prompt", schema.__name__, False, latency,
                              pydantic_ok=False,
                              error=f"Pydantic 校验失败: {val_exc}",
                              detail=f"解析的 dict keys: {list(parsed_dict.keys())}")

        pydantic_ok, field_count_ok, detail = _inspect_result(result, schema)
        return ModeResult("prompt", schema.__name__, True, latency,
                          pydantic_ok=pydantic_ok, field_count_ok=field_count_ok, detail=detail)
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000)
        return ModeResult("prompt", schema.__name__, False, latency,
                          error=f"{type(exc).__name__}: {exc}")


# ============ 测试函数映射 ============

MODE_TESTERS: dict[str, Any] = {
    "function_calling": _test_function_calling,
    "json_mode": _test_json_mode,
    "prompt": _test_prompt_fallback,
}

MODE_ORDER = ["function_calling", "json_mode", "prompt"]


# ============ pytest 测试用例 ============


@pytest.mark.asyncio
@pytest.mark.parametrize("schema_cls", SCHEMA_ORDER, ids=lambda s: s.__name__)
@pytest.mark.parametrize("mode", MODE_ORDER)
async def test_json_output_mode(schema_cls: type[BaseModel], mode: str) -> None:
    """测试每种模式 × 每个 schema 的 JSON 输出能力。"""
    messages = PROMPTS[schema_cls]
    tester = MODE_TESTERS[mode]
    result = await tester(schema_cls, messages)
    _record(result)

    status = "✅" if result.success else "❌"
    print(f"\n{status} {mode:15s} × {schema_cls.__name__:25s}  {result.latency_ms:5d}ms")
    if result.error:
        print(f"   错误: {result.error[:120]}")
    if result.detail and result.success:
        print(f"   详情: {result.detail[:120]}")

    if not result.success:
        pytest.skip(f"模式 {mode} 对 {schema_cls.__name__} 不可用: {result.error[:80]}")


# ============ self-repair 测试 ============


@pytest.mark.asyncio
@pytest.mark.parametrize("schema_cls", SCHEMA_ORDER, ids=lambda s: s.__name__)
async def test_self_repair(schema_cls: type[BaseModel]) -> None:
    """测试 self-repair 机制：首次失败后通过错误反馈修正。"""
    from app.infra.llm import _build_repair_prompt, _parse_json, _inject_json_instruction

    model = _make_model()
    messages = PROMPTS[schema_cls]

    # 第一步：用 prompt 模式首次生成（最容易拿到 raw_output）
    t0 = time.perf_counter()
    injected = _inject_json_instruction(messages, schema_cls)
    resp = await model.ainvoke(injected)
    first_latency = round((time.perf_counter() - t0) * 1000)
    raw_output = getattr(resp, "content", "") or ""

    # 尝试直接解析
    try:
        result = _parse_json(raw_output, schema_cls)
        # 首次就成功，无需 repair
        _record(ModeResult("self_repair", schema_cls.__name__, True, first_latency,
                           detail=f"首次即成功, 无需repair"))
        print(f"\n✅ self_repair    × {schema_cls.__name__:25s}  {first_latency}ms (首次即成功)")
        return
    except Exception:
        pass  # 首次失败，进入 repair 流程

    # 第二步：用 self-repair 修正
    for repair_i in range(2):
        repair_msgs = _build_repair_prompt(schema_cls, raw_output[:2000], "Pydantic 校验失败")
        try:
            t1 = time.perf_counter()
            resp = await model.ainvoke(repair_msgs)
            repair_latency = round((time.perf_counter() - t1) * 1000)
            repair_output = getattr(resp, "content", "") or ""
            result = _parse_json(repair_output, schema_cls)

            total_ms = first_latency + repair_latency
            _record(ModeResult("self_repair", schema_cls.__name__, True, total_ms,
                               detail=f"repair_round={repair_i + 1} 成功"))
            print(f"\n✅ self_repair    × {schema_cls.__name__:25s}  {total_ms}ms (repair 第{repair_i + 1}轮成功)")
            return
        except Exception as exc:
            raw_output = repair_output if 'repair_output' in dir() else raw_output
            print(f"\n⚠️  self_repair   × {schema_cls.__name__:25s}  repair 第{repair_i + 1}轮失败: {exc}")
            continue

    # repair 也失败
    _record(ModeResult("self_repair", schema_cls.__name__, False, first_latency,
                       error="self-repair 2轮后仍失败"))
    pytest.skip(f"self-repair 对 {schema_cls.__name__} 失败")


# ============ 汇总报告 ============


@pytest.mark.asyncio
async def test_summary_report() -> None:
    """所有模式测试完成后，输出按稳定性和耗时排序的汇总报告。"""
    if not _all_results:
        pytest.skip("没有收集到测试结果")

    print("\n" + "=" * 90)
    print("LLM JSON 输出模式测试汇总报告")
    print(f"模型: {_MODEL_NAME}  |  API: {_BASE_URL}")
    print("=" * 90)

    # ── 按模式统计 ──
    print("\n## 按模式统计（稳定性降序 → 耗时升序）\n")
    mode_stats: dict[str, dict[str, Any]] = {}
    for r in _all_results:
        if r.mode not in mode_stats:
            mode_stats[r.mode] = {"total": 0, "success": 0, "total_ms": 0, "errors": []}
        mode_stats[r.mode]["total"] += 1
        if r.success:
            mode_stats[r.mode]["success"] += 1
            mode_stats[r.mode]["total_ms"] += r.latency_ms
        else:
            mode_stats[r.mode]["errors"].append(f"{r.schema_name}: {r.error[:60]}")

    # 排序：成功率降序 → 平均耗时升序
    def mode_sort_key(mode_name: str) -> tuple:
        stats = mode_stats[mode_name]
        success_rate = stats["success"] / stats["total"] if stats["total"] else 0
        avg_ms = stats["total_ms"] / stats["success"] if stats["success"] else 999999
        return (-success_rate, avg_ms)

    sorted_modes = sorted(mode_stats.keys(), key=mode_sort_key)

    print(f"{'模式':15s} | {'成功率':>6s} | {'成功/总数':>8s} | {'平均耗时':>8s} | 备注")
    print("-" * 80)
    for mode_name in sorted_modes:
        stats = mode_stats[mode_name]
        rate = stats["success"] / stats["total"] if stats["total"] else 0
        avg_ms = stats["total_ms"] / stats["success"] if stats["success"] else 0
        remark = "✅ 推荐" if rate == 1.0 else ("⚠️ 部分可用" if rate > 0 else "❌ 不可用")
        print(f"{mode_name:15s} | {rate:5.0%}   | {stats['success']:3d}/{stats['total']:<3d}  | {avg_ms:6.0f}ms | {remark}")
        if stats["errors"]:
            for err in stats["errors"][:3]:
                print(f"                 └─ ❌ {err}")

    # ── 按 Schema 统计 ──
    print("\n## 按 Schema 统计（复杂度递增）\n")
    schema_stats: dict[str, dict[str, Any]] = {}
    for r in _all_results:
        if r.schema_name not in schema_stats:
            schema_stats[r.schema_name] = {"total": 0, "success": 0, "modes": {}}
        schema_stats[r.schema_name]["total"] += 1
        if r.success:
            schema_stats[r.schema_name]["success"] += 1
        schema_stats[r.schema_name]["modes"][r.mode] = r

    for schema_name in [s.__name__ for s in SCHEMA_ORDER]:
        if schema_name not in schema_stats:
            continue
        stats = schema_stats[schema_name]
        rate = stats["success"] / stats["total"] if stats["total"] else 0
        print(f"  {schema_name}: 成功率 {rate:.0%} ({stats['success']}/{stats['total']})")
        for mode_name in MODE_ORDER:
            r = stats["modes"].get(mode_name)
            if r is None:
                print(f"    {mode_name:15s} — 未测试")
            elif r.success:
                print(f"    {mode_name:15s} ✅ {r.latency_ms}ms  {r.detail[:60]}")
            else:
                print(f"    {mode_name:15s} ❌ {r.error[:60]}")

    # ── 最终推荐 ──
    print("\n## 推荐策略\n")
    best_modes = [m for m in sorted_modes if mode_stats[m]["success"] > 0]
    if best_modes:
        recommended = best_modes[0]
        rate = mode_stats[recommended]["success"] / mode_stats[recommended]["total"]
        avg_ms = (mode_stats[recommended]["total_ms"] / mode_stats[recommended]["success"]
                  if mode_stats[recommended]["success"] else 0)
        print(f"  首选模式: {recommended} (成功率 {rate:.0%}, 平均 {avg_ms:.0f}ms)")
        if len(best_modes) > 1:
            fallback = best_modes[1]
            rate2 = mode_stats[fallback]["success"] / mode_stats[fallback]["total"]
            print(f"  降级模式: {fallback} (成功率 {rate2:.0%})")
        print(f"\n  建议 config.yaml 配置: structured_output_strategy: \"{recommended}_first\"")
    else:
        print("  ⚠️ 所有模式均失败，请检查模型配置或 API 可用性")

    print("=" * 90)
