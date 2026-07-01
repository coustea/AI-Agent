# Benchmark V3

This dataset is the expanded retrieval-quality benchmark for the local knowledge base.

## Case Count

Minimum: 80 cases (current: 81)

## Case Taxonomy

- `basic_fact`: direct lookup (8 cases)
- `concept_explanation`: concept definition or explanation (10 cases)
- `mechanism_explanation`: asks how a mechanism works (10 cases)
- `procedure_or_algorithm`: asks for steps or algorithms (8 cases)
- `cross_chapter_reasoning`: requires connecting nearby concepts (7 cases)
- `ambiguous_routing`: query can match multiple sources and tests routing (7 cases)
- `cross_book_pollution`: query is vulnerable to off-topic retrieval (7 cases)
- `no_answer`: should not confidently retrieve a source (6 cases)
- `noisy_user_query`: typo, shorthand, or casual user wording (7 cases)
- `mixed_language`: Chinese query mixed with English technical terms (6 cases)

## Difficulty Distribution

- easy: 17 cases
- medium: 40 cases
- hard: 24 cases

## Severity Distribution

- high: 42 cases
- medium: 33 cases
- low: 6 cases (all no_answer)

## Source Coverage

- 计算机网络: 18 cases
- 操作系统: 14 cases
- 数据结构: 12 cases
- 计算机组成原理: 6 cases
- Java: 10 cases
- Python: 1 case (needs expansion)
- 数据库: 4 cases (needs expansion)
- Cross-source/no_answer: remaining cases

## Run

```bash
# Validate dataset structure
uv run pytest app/rag/eval/tests/test_benchmark_v3_cases.py -q

# Run full evaluation
uv run python -m app.rag.eval.evaluate --cases app/rag/eval/benchmark_v3/cases.json --label benchmark_v3 --top-k 4
```

## Quality Gate

- Hit@4 >= 0.85
- Mean MRR >= 0.70
- Top1 source accuracy >= 0.75
- Cross-book pollution rate <= 0.20
- Candidate recall rate >= 0.80
- No-result rate <= 0.10

If any gate fails, do not tune retrieval inside this benchmark task. Record the failure in the audit report.

## Notes

This benchmark tests retrieval quality across:
1. Core 408 subjects (计算机网络, 操作系统, 数据结构, 计算机组成原理)
2. Programming languages (Java, Python)
3. Database concepts
4. Various query patterns (formal, noisy, mixed-language)
5. Routing ambiguity and cross-book pollution scenarios