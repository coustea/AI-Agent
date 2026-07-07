"""RAG 检索评测脚本。

用法：
  python -m app.rag.eval --cases data/rag_eval_cases.jsonl --top-k 5

评测指标：hit@1, hit@3, hit@5, MRR, 平均耗时。

Per user: "新增 RAG 评测脚本…支持读取 jsonl 评测文件…输出 hit@1、hit@3、hit@5、MRR、平均耗时"
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from app.rag.retriever import retrieve


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def _chunk_text(chunk: Any) -> str:
    return " ".join(
        [
            getattr(chunk, "content", "") or "",
            getattr(chunk, "title", "") or "",
            getattr(chunk, "section", "") or "",
            getattr(chunk, "heading_path", "") or "",
            getattr(chunk, "source", "") or "",
        ]
    )


def _is_hit(chunk: Any, case: dict[str, Any]) -> bool:
    text = _chunk_text(chunk)

    must_contain = case.get("must_contain") or []
    if must_contain:
        # match_mode: "all"(默认,严格,避免单关键词命中虚高指标) / "any"(宽松)
        match_mode = case.get("match_mode", "all")
        if match_mode == "any":
            return any(str(keyword) in text for keyword in must_contain)
        return all(str(keyword) in text for keyword in must_contain)

    source_hint = case.get("source_hint")
    if source_hint:
        return str(source_hint) in text

    return False


async def _eval_one(case: dict[str, Any], top_k: int) -> dict[str, Any]:
    query = str(case["query"])
    course = case.get("course")

    result = await retrieve(query, course_name=course, top_k=top_k)
    chunks = result.chunks

    ranks: list[int] = []
    for idx, chunk in enumerate(chunks, 1):
        if _is_hit(chunk, case):
            ranks.append(idx)

    first_rank = ranks[0] if ranks else None

    return {
        "query": query,
        "course": course,
        "status": result.status,
        "elapsed_ms": result.elapsed_ms,
        "match_count": len(chunks),
        "hit@1": bool(first_rank and first_rank <= 1),
        "hit@3": bool(first_rank and first_rank <= 3),
        "hit@5": bool(first_rank and first_rank <= 5),
        "mrr": 1.0 / first_rank if first_rank else 0.0,
        "first_rank": first_rank,
        "top_sources": [
            {
                "source": c.source,
                "title": c.title,
                "heading_path": c.heading_path,
                "retrieval_type": c.retrieval_type,
                "score": c.score,
            }
            for c in chunks[:3]
        ],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="RAG retrieval evaluation")
    parser.add_argument("--cases", required=True, help="Path to rag_eval_cases.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    cases = _load_cases(Path(args.cases))
    if not cases:
        print("No eval cases found.")
        return

    rows = []
    for case in cases:
        row = await _eval_one(case, args.top_k)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    total = len(rows)
    hit1 = sum(1 for r in rows if r["hit@1"]) / total
    hit3 = sum(1 for r in rows if r["hit@3"]) / total
    hit5 = sum(1 for r in rows if r["hit@5"]) / total
    mrr = sum(float(r["mrr"]) for r in rows) / total
    avg_elapsed = sum(int(r["elapsed_ms"]) for r in rows) / total

    print("\n=== RAG Eval Summary ===")
    print(f"cases: {total}")
    print(f"hit@1: {hit1:.3f}")
    print(f"hit@3: {hit3:.3f}")
    print(f"hit@5: {hit5:.3f}")
    print(f"mrr: {mrr:.3f}")
    print(f"avg_elapsed_ms: {avg_elapsed:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
