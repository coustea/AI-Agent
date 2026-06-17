"""知识检索评测脚本。

评测指标：
- Hit@K: Top-K结果中是否包含相关文档（命中率）
- MRR: Mean Reciprocal Rank（第一个相关结果的平均排名倒数）
- 关键词命中率: 检索结果中包含期望关键词的比例
- 平均距离分数: 检索结果的向量距离统计

运行方式：
cd server && uv run python eval/knowledge_retrieval/evaluate.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 添加 server 目录到 path
server_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(server_dir))

from app.chat.tools.knowledge import (
    format_knowledge_context,
    retrieve_dense_knowledge,
    retrieve_sparse_knowledge,
    retrieve_knowledge,
)


def load_test_cases() -> list[dict[str, Any]]:
    """加载测试用例。"""
    test_file = Path(__file__).parent / "test_cases.json"
    with open(test_file, encoding="utf-8") as f:
        return json.load(f)


def check_keyword_hits(
    result: dict[str, Any],
    expected_keywords: list[str],
) -> int:
    """检查检索结果中包含多少期望关键词。"""
    text = str(result.get("text") or "").lower()
    hits = 0
    for kw in expected_keywords:
        if kw.lower() in text:
            hits += 1
    return hits


def evaluate_single_query(
    test_case: dict[str, Any],
    top_k: int = 4,
) -> dict[str, Any]:
    """评估单个查询的检索质量。"""
    query = test_case["query"]
    expected_keywords = test_case["expected_keywords"]

    # 执行检索
    results = retrieve_knowledge(query, top_k=top_k)

    # 计算指标
    total_keyword_hits = 0
    first_hit_rank = None

    for idx, result in enumerate(results, 1):
        keyword_hits = check_keyword_hits(result, expected_keywords)
        total_keyword_hits += keyword_hits
        if keyword_hits >= len(expected_keywords) * 0.3:  # 至少命中30%关键词视为相关
            if first_hit_rank is None:
                first_hit_rank = idx

    # Hit@K: 是否找到相关文档
    hit_at_k = first_hit_rank is not None

    # MRR: 第一个相关结果的排名倒数
    mrr = 1.0 / first_hit_rank if first_hit_rank else 0.0

    # 关键词覆盖率
    keyword_coverage = total_keyword_hits / (len(expected_keywords) * len(results)) if results else 0.0

    # 平均距离
    distances = [r.get("distance", 999) for r in results]
    avg_distance = sum(distances) / len(distances) if distances else 999

    return {
        "id": test_case["id"],
        "query": query,
        "category": test_case["category"],
        "difficulty": test_case["difficulty"],
        "num_results": len(results),
        "hit_at_k": hit_at_k,
        "first_hit_rank": first_hit_rank,
        "mrr": mrr,
        "keyword_coverage": keyword_coverage,
        "avg_distance": avg_distance,
        "total_keyword_hits": total_keyword_hits,
        "expected_keyword_count": len(expected_keywords),
        "retrieval_modes": [r.get("retrieval_mode") for r in results],
        "top_result_snippet": (results[0].get("text") or "")[:200] if results else "",
        "result_sources": [r.get("metadata", {}).get("source", "") for r in results],
        "expected_sources": test_case.get("expected_sources", []),
    }


def print_detailed_result(result: dict[str, Any]) -> None:
    """打印单个查询的详细结果。"""
    print(f"\n{'='*60}")
    print(f"查询 #{result['id']}: {result['query']}")
    print(f"分类: {result['category']} | 难度: {result['difficulty']}")
    print(f"{'='*60}")
    print(f"检索结果数: {result['num_results']}")
    print(f"Hit@K: {'✓' if result['hit_at_k'] else '✗'}")
    if result['first_hit_rank']:
        print(f"首个相关结果排名: #{result['first_hit_rank']}")
    print(f"MRR: {result['mrr']:.4f}")
    print(f"关键词覆盖率: {result['keyword_coverage']:.2%}")
    print(f"平均距离: {result['avg_distance']:.4f}")
    print(f"检索模式分布: {result['retrieval_modes']}")
    if result['top_result_snippet']:
        print(f"\nTop-1 检索片段预览:\n{result['top_result_snippet']}...")


def compute_aggregate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """计算聚合指标。"""
    n = len(results)
    if n == 0:
        return {}

    hit_at_k_count = sum(1 for r in results if r["hit_at_k"])
    total_mrr = sum(r["mrr"] for r in results)
    total_keyword_coverage = sum(r["keyword_coverage"] for r in results)
    total_avg_distance = sum(r["avg_distance"] for r in results)

    # 按难度分组统计
    by_difficulty: dict[str, dict[str, Any]] = {}
    for r in results:
        diff = r["difficulty"]
        if diff not in by_difficulty:
            by_difficulty[diff] = {"count": 0, "hit": 0, "mrr": 0.0}
        by_difficulty[diff]["count"] += 1
        if r["hit_at_k"]:
            by_difficulty[diff]["hit"] += 1
        by_difficulty[diff]["mrr"] += r["mrr"]

    # 按分类分组统计
    by_category: dict[str, dict[str, Any]] = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "hit": 0, "mrr": 0.0}
        by_category[cat]["count"] += 1
        if r["hit_at_k"]:
            by_category[cat]["hit"] += 1
        by_category[cat]["mrr"] += r["mrr"]

    return {
        "total_queries": n,
        "hit_at_k_rate": hit_at_k_count / n,
        "mean_mrr": total_mrr / n,
        "mean_keyword_coverage": total_keyword_coverage / n,
        "mean_avg_distance": total_avg_distance / n,
        "by_difficulty": {
            k: {
                "hit_rate": v["hit"] / v["count"],
                "mrr": v["mrr"] / v["count"],
            }
            for k, v in by_difficulty.items()
        },
        "by_category": {
            k: {
                "hit_rate": v["hit"] / v["count"],
                "mrr": v["mrr"] / v["count"],
            }
            for k, v in by_category.items()
        },
    }


def compute_source_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    """计算源正确率和污染率指标。"""
    total = len(results)
    if total == 0:
        return {"top1_source_accuracy": 0.0, "cross_book_pollution_rate": 0.0}

    top1_hits = 0
    total_sources = 0
    polluted_sources = 0
    for item in results:
        expected = item.get("expected_sources") or []
        returned = item.get("result_sources") or []
        if returned and any(expected_source in returned[0] for expected_source in expected):
            top1_hits += 1
        total_sources += len(returned)
        polluted_sources += sum(
            1 for source in returned if expected and not any(expected_source in source for expected_source in expected)
        )
    return {
        "top1_source_accuracy": top1_hits / total,
        "cross_book_pollution_rate": polluted_sources / total_sources if total_sources else 0.0,
    }


def print_aggregate_report(agg: dict[str, Any], source_metrics: dict[str, float] | None = None) -> None:
    """打印聚合报告。"""
    print(f"\n{'='*60}")
    print("聚合评测报告")
    print(f"{'='*60}")
    print(f"总查询数: {agg['total_queries']}")
    print(f"\n核心指标:")
    print(f"  Hit@K 命中率: {agg['hit_at_k_rate']:.2%}")
    print(f"  Mean MRR: {agg['mean_mrr']:.4f}")
    print(f"  平均关键词覆盖率: {agg['mean_keyword_coverage']:.2%}")
    print(f"  平均向量距离: {agg['mean_avg_distance']:.4f}")

    if source_metrics:
        print(f"\n源正确性指标:")
        print(f"  Top-1 源准确率: {source_metrics['top1_source_accuracy']:.2%}")
        print(f"  跨书污染率: {source_metrics['cross_book_pollution_rate']:.2%}")

    print(f"\n按难度统计:")
    for diff, stats in agg["by_difficulty"].items():
        print(f"  {diff}: Hit率={stats['hit_rate']:.2%}, MRR={stats['mrr']:.4f}")

    print(f"\n按分类统计:")
    for cat, stats in agg["by_category"].items():
        print(f"  {cat}: Hit率={stats['hit_rate']:.2%}, MRR={stats['mrr']:.4f}")

    # 评级
    hit_rate = agg["hit_at_k_rate"]
    if hit_rate >= 0.9:
        grade = "优秀 (A)"
    elif hit_rate >= 0.75:
        grade = "良好 (B)"
    elif hit_rate >= 0.6:
        grade = "中等 (C)"
    elif hit_rate >= 0.4:
        grade = "待改进 (D)"
    else:
        grade = "较差 (F)"

    print(f"\n综合评级: {grade}")
    print(f"{'='*60}")


def save_results(
    detailed_results: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> None:
    """保存评测结果到文件。"""
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)

    timestamp = "2026-06-16"

    # 保存详细结果
    detailed_file = output_dir / f"detailed_{timestamp}.json"
    with open(detailed_file, "w", encoding="utf-8") as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)

    # 保存聚合结果
    aggregate_file = output_dir / f"aggregate_{timestamp}.json"
    with open(aggregate_file, "w", encoding="utf-8") as f:
        json.dump(aggregate, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存:")
    print(f"  详细结果: {detailed_file}")
    print(f"  聚合结果: {aggregate_file}")


def main() -> None:
    """运行评测主流程。"""
    print("=" * 60)
    print("知识检索评测 - Java知识库")
    print("=" * 60)

    test_cases = load_test_cases()
    print(f"加载测试用例: {len(test_cases)} 个")

    top_k = 4
    print(f"检索 Top-K: {top_k}")

    detailed_results: list[dict[str, Any]] = []

    for test_case in test_cases:
        result = evaluate_single_query(test_case, top_k=top_k)
        detailed_results.append(result)
        print_detailed_result(result)

    aggregate = compute_aggregate_metrics(detailed_results)
    source_metrics = compute_source_metrics(detailed_results)
    aggregate["source_metrics"] = source_metrics
    print_aggregate_report(aggregate, source_metrics)

    save_results(detailed_results, aggregate)


if __name__ == "__main__":
    main()