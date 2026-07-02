# Benchmark V3 Quality Audit

## Summary

- **Dataset:** `app/rag/eval/benchmark_v3/cases.json`
- **Case count:** 88 cases (minimum required: 80)
- **Evaluation command:** `uv run python -m app.rag.eval.evaluate --cases app/rag/eval/benchmark_v3/cases.json --label benchmark_v3_final --top-k 4`
- **Result file:** `app/rag/eval/results/aggregate_benchmark_v3_final_2026-06-21.json`

## Score

**Current score: 72.86/100**

### Scoring Rubric

| Component | Weight | V3 Final Value | Score Contribution |
| --- | ---: | ---: | ---: |
| Hit@4 | 20 points | 0.7955 | 15.91 |
| Mean MRR | 20 points | 0.7311 | 14.62 |
| Top1 source accuracy | 20 points | 0.8295 | 16.59 |
| Candidate recall rate | 15 points | 0.8409 | 12.61 |
| Cross-book pollution control | 15 points | 0.1250 pollution | 13.12 |
| No-answer correctness | 10 points | 1.0000 false positive | **0.00** |
| **Total** | **100** | | **72.86** |

### Formula

```text
score =
  hit_at_k_rate * 20
  + mean_mrr * 20
  + top1_source_accuracy * 20
  + candidate_recall_rate * 15
  + (1 - cross_book_pollution_rate) * 15
  + (1 - no_answer_false_positive_rate) * 10
```

### Critical Finding: No-Answer False Positive Rate = 100%

**All 6 no_answer test cases returned high-confidence results, triggering false positives.**

This means the system cannot distinguish between knowledge-domain queries and out-of-domain queries (weather, restaurants, movies, sports, recipes). The retrieval engine returns results for any query, even those completely outside the knowledge base scope.

**Impact:** This is a critical quality issue that must be addressed before production use.

## Quality Gate Assessment

| Gate | Threshold | Actual | Status |
| --- | ---: | ---: | ---: |
| Hit@4 | >= 0.85 | 0.7955 | ❌ **FAIL** |
| Mean MRR | >= 0.70 | 0.7311 | ✅ PASS |
| Top1 source accuracy | >= 0.75 | 0.8295 | ✅ PASS |
| Cross-book pollution rate | <= 0.20 | 0.1250 | ✅ PASS |
| Candidate recall rate | >= 0.80 | 0.8409 | ✅ PASS |
| No-result rate | <= 0.10 | 0.0 | ✅ PASS |
| No-answer false positive rate | <= 0.30 | **1.0000** | ❌ **FAIL** |

**Overall: 2 quality gates FAILED (Hit@4 and No-answer FP rate).**

## Failure Analysis - Worst 10 Cases (from detailed_benchmark_v3_final_2026-06-21.json)

The following 10 cases had the lowest MRR (0.0):

### 1. v3-co-concept-001: "什么是Cache缓存"
- **Category:** concept_explanation
- **Expected Sources:** 计算机组成原理
- **Result Sources:** Redis设计与实现 (incorrect)
- **Diagnostic Flags:** candidate_miss, cross_book_pollution
- **Likely Cause:** "Cache" keyword routed to Redis book instead of 计算机组成原理

### 2. v3-net-mech-003: "TCP四次挥手的过程"
- **Category:** mechanism_explanation
- **Expected Sources:** 计算机网络
- **Result Sources:** 计算机网络 (correct book)
- **Diagnostic Flags:** none
- **Likely Cause:** Retrieved snippets did not match keyword threshold for FIN/连接释放

### 3. v3-net-mech-005: "TCP流量控制是如何实现的"
- **Category:** mechanism_explanation
- **Expected Sources:** 计算机网络
- **Result Sources:** 计算机网络 (correct book)
- **Diagnostic Flags:** none
- **Likely Cause:** Retrieved snippets lacked sufficient keyword hits for 流量控制/滑动窗口

### 4. v3-os-mech-003: "页面置换算法如何工作"
- **Category:** mechanism_explanation
- **Expected Sources:** 操作系统
- **Result Sources:** 算法（第4版） (incorrect)
- **Diagnostic Flags:** candidate_miss, cross_book_pollution, route_mismatch
- **Likely Cause:** "算法" keyword prominence caused routing to 算法 book

### 5. v3-os-mech-004: "文件系统是如何管理磁盘空间的"
- **Category:** mechanism_explanation
- **Expected Sources:** 操作系统
- **Result Sources:** 计算机网络 (incorrect)
- **Diagnostic Flags:** candidate_miss, cross_book_pollution, route_mismatch
- **Likely Cause:** Routing mismatch - file system query routed to networking book

### 6. v3-ds-mech-002: "快速排序算法的执行过程"
- **Category:** mechanism_explanation
- **Expected Sources:** 数据结构
- **Result Sources:** 算法（第4版） (incorrect)
- **Diagnostic Flags:** candidate_miss, cross_book_pollution
- **Likely Cause:** Query routed to 算法 book instead of 数据结构

### 7. v3-net-amb-004: "缓存的作用"
- **Category:** ambiguous_routing
- **Expected Sources:** 计算机组成原理
- **Result Sources:** Redis设计与实现 (incorrect)
- **Diagnostic Flags:** candidate_miss, cross_book_pollution, route_mismatch
- **Likely Cause:** "缓存" keyword routed to Redis/MySQL books instead of 计算机组成原理

### 8. v3-co-poll-001: "CPU的性能指标有哪些"
- **Category:** cross_book_pollution
- **Expected Sources:** 计算机组成原理
- **Result Sources:** 计算机组成原理 (correct book)
- **Diagnostic Flags:** none
- **Likely Cause:** Snippets did not match keyword threshold (CPU, 性能, 主频, 指令集)

### 9. v3-net-noans-001: "今天天气怎么样"
- **Category:** no_answer
- **Expected Sources:** [] (should have no results)
- **Result Sources:** 操作系统导论-OSTEP, 计算机网络自顶向下方法
- **Diagnostic Flags:** **no_answer_false_positive**
- **Likely Cause:** System returned high-confidence results for out-of-domain query about weather

### 10. v3-net-noans-002: "哪家餐厅的菜好吃"
- **Category:** no_answer
- **Expected Sources:** [] (should have no results)
- **Result Sources:** 数据库系统概念, 心理学书
- **Diagnostic Flags:** **no_answer_false_positive**
- **Likely Cause:** System returned high-confidence results for out-of-domain restaurant query

## No-Answer False Positive Analysis

**All 6 no_answer cases failed:**

| Case ID | Query | False Positive | avg_distance |
| --- | --- | ---: | ---: |
| v3-net-noans-001 | 今天天气怎么样 | ✅ Yes | < 30 (high confidence) |
| v3-net-noans-002 | 哪家餐厅的菜好吃 | ✅ Yes | < 30 (high confidence) |
| v3-net-noans-003 | 最新的股票行情如何 | ✅ Yes | < 30 (high confidence) |
| v3-net-noans-004 | 如何做红烧肉 | ✅ Yes | < 30 (high confidence) |
| v3-net-noans-005 | 世界杯什么时候开始 | ✅ Yes | < 30 (high confidence) |
| v3-net-noans-006 | 推荐一部好看的电影 | ✅ Yes | < 30 (high confidence) |

**Root Cause:** The retrieval system lacks a confidence threshold for refusing to answer. When queries contain common words or semantic vectors that match any book content, the system returns results regardless of domain relevance.

**Expected Behavior:** For no_answer queries:
- Return empty results or very low-confidence results (avg_distance > 30)
- Hit@K should be True (indicating correct refusal), not False

## Category Performance Breakdown (from aggregate_benchmark_v3_final)

| Category | Hit Rate | MRR | Cases | Notes |
| --- | ---: | ---: | ---: | --- |
| basic_fact | 1.000 | 0.854 | 8 | Best performance |
| concept_explanation | 0.933 | 0.833 | 10 | Good |
| procedure_or_algorithm | 1.000 | 0.875 | 8 | Good |
| cross_chapter_reasoning | 1.000 | 0.938 | 7 | Good |
| cross_book_pollution | 0.875 | 0.875 | 7 | Acceptable |
| ambiguous_routing | 0.875 | 0.750 | 7 | Needs routing fix |
| noisy_user_query | 0.875 | 0.812 | 7 | Needs normalization |
| mechanism_explanation | **0.615** | **0.615** | 10 | **Worst normal category** |
| mixed_language | **0.500** | **0.500** | 6 | Needs English term handling |
| no_answer | **0.000** | **0.000** | 6 | **Critical failure - 100% FP** |

## Diagnostic Summary (from aggregate_benchmark_v3_final)

**Primary Bottleneck:** `route` (as reported in diagnostics.primary_bottleneck)

**Diagnostic Flags Count:**
- `cross_book_pollution`: 15 cases (17.0%)
- `candidate_miss`: 8 cases (9.1%)
- `route_mismatch`: 6 cases (6.8%)
- `no_answer_false_positive`: 6 cases (6.8% - all no_answer cases)

**Root Causes Identified:**

1. **No-answer detection missing:** System has no mechanism to refuse out-of-domain queries
2. **Routing precision issues:** 6 route_mismatch cases indicate LLM routing choosing wrong sources
3. **Cross-domain keyword confusion:** Terms like "缓存", "算法" appear in multiple books causing wrong routing
4. **Mechanism explanation weakness:** Complex mechanism queries fail keyword matching threshold

## Recommendations

### Priority 1: Add No-Answer Detection (Critical - blocks quality gate)

- **Problem:** 100% false positive rate on no_answer queries
- **Fix:** Implement domain confidence scoring:
  1. Add a "domain relevance" check before returning results
  2. If route.confidence < threshold AND avg_distance < threshold AND no strong term hits → return empty
  3. Add "out-of-domain" keywords list for common non-KB topics (weather, food, sports, movies)
- **Expected Impact:** Reduce no_answer_false_positive_rate to < 0.30

### Priority 2: Routing Precision Improvement

- **Problem:** 6 route_mismatch + 15 cross_book_pollution cases
- **Fix:** 
  1. Disambiguate shared terms (缓存→计算机组成原理, 算法→数据结构/操作系统 not 算法书)
  2. Add domain-specific stopword handling
  3. When LLM routing confidence < 0.85, fallback to keyword routing with broader filter
- **Expected Impact:** Reduce cross_book_pollution_rate to < 0.10

### Priority 3: Mechanism Explanation Query Enhancement

- **Problem:** mechanism_explanation hit_rate = 0.615 (lowest normal category)
- **Fix:** Improve query expansion for mechanism questions:
  1. Add synonyms for common mechanism terms
  2. Lower keyword hit threshold for hard mechanism queries
- **Expected Impact:** Increase mechanism_explanation hit_rate to > 0.80

### Priority 4: Mixed-Language Normalization

- **Problem:** mixed_language hit_rate = 0.500
- **Fix:** Map English terms to Chinese equivalents in preprocessing:
  - cache → 缓存
  - binary tree → 二叉树
  - virtual memory → 虚拟内存
- **Expected Impact:** Increase mixed_language hit_rate to > 0.75

## Next Work Items

1. **Implement no-answer refusal logic** in `knowledge.py` - add confidence threshold check
2. **Update source registry** with disambiguation rules for cross-domain terms
3. **Add query expansion** for mechanism explanation queries
4. **Implement English-to-Chinese term normalization** in query preprocessing

## Conclusion

The V3 benchmark with 88 diverse cases reveals a **72.86/100** quality score, with **2 critical quality gate failures**:

1. **Hit@4 rate (0.7955 < 0.85)** - Below threshold due to mechanism/mixed-language/no_answer failures
2. **No-answer false positive rate (1.0000 > 0.30)** - System cannot refuse out-of-domain queries

The most critical issue is the **100% no_answer false positive rate** - the system returns confident results for queries completely outside the knowledge base scope (weather, restaurants, movies, sports, recipes). This must be fixed before the system can be safely deployed.

**Recommendation:** Implement domain confidence scoring and no-answer detection as the highest priority fix. This alone could improve the score from 72.86 to 82.86 (+10 points).