"""最小知识库质量评估。

使用新 retrieve() 接口，不依赖旧混合检索或路由。
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.rag.retriever import retrieve

logger = get_logger(__name__)

EVAL_ROOT = Path(__file__).resolve().parent
DEFAULT_CASES_PATH = EVAL_ROOT / "benchmark_v3" / "cases.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run knowledge retrieval evaluation")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to evaluation cases JSON")
    parser.add_argument("--top-k", type=int, default=4, help="Top-K retrieval cutoff")
    return parser.parse_args(argv)


def load_test_cases(test_file: Path | None = None) -> list[dict[str, Any]]:
    target = Path(test_file) if test_file is not None else DEFAULT_CASES_PATH
    if not target.is_absolute():
        target = Path.cwd() / target
    with target.open(encoding="utf-8") as f:
        cases = json.load(f)
    if not isinstance(cases, list):
        raise ValueError(f"Test cases file must contain a list: {target}")
    return cases


async def evaluate_single_query(test_case: dict[str, Any], top_k: int = 4) -> dict[str, Any]:
    query = test_case["query"]
    course_name = test_case.get("course_name")
    expected_source_keywords = list(test_case.get("expected_source_keywords", []))
    expected_content_keywords = list(test_case.get("expected_content_keywords", []))

    result = await retrieve(query, course_name=course_name, top_k=top_k)

    # 来源命中率
    source_hit = False
    if expected_source_keywords and result.chunks:
        for chunk in result.chunks:
            for keyword in expected_source_keywords:
                if keyword.lower() in chunk.source.lower() or keyword.lower() in chunk.title.lower():
                    source_hit = True
                    break

    # 内容关键词覆盖率
    content_keyword_hits = 0
    if expected_content_keywords and result.chunks:
        all_text = " ".join(chunk.content for chunk in result.chunks).lower()
        content_keyword_hits = sum(1 for kw in expected_content_keywords if kw.lower() in all_text)
    content_coverage = content_keyword_hits / len(expected_content_keywords) if expected_content_keywords else 0.0

    return {
        "id": test_case.get("id", ""),
        "query": query,
        "course_name": course_name,
        "status": result.status,
        "num_results": len(result.chunks),
        "source_hit": source_hit,
        "content_keyword_hits": content_keyword_hits,
        "content_coverage": content_coverage,
        "elapsed_ms": result.elapsed_ms,
        "sources": [{"source": c.source, "title": c.title} for c in result.chunks],
    }


async def run_evaluation(cases_path: Path, top_k: int = 4) -> dict[str, Any]:
    test_cases = load_test_cases(cases_path)
    detailed = []
    for case in test_cases:
        result = await evaluate_single_query(case, top_k=top_k)
        detailed.append(result)

    total = len(detailed)
    if total == 0:
        return {"total_queries": 0}

    source_hit_count = sum(1 for r in detailed if r["source_hit"])
    avg_coverage = sum(r["content_coverage"] for r in detailed) / total
    ok_count = sum(1 for r in detailed if r["status"] == "ok")

    aggregate = {
        "total_queries": total,
        "success_rate": ok_count / total,
        "source_hit_rate": source_hit_count / total,
        "mean_content_coverage": avg_coverage,
    }

    # 保存结果
    results_dir = EVAL_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "detailed.json").write_text(
        json.dumps(detailed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return aggregate


def main() -> None:
    args = parse_args()
    aggregate = asyncio.run(run_evaluation(Path(args.cases), top_k=args.top_k))
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
