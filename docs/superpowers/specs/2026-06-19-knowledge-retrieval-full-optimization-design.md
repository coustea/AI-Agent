# Knowledge Retrieval Full Optimization Design (v3.5)

> Date: 2026-06-19
> Status: Spec Review
> Scope: Semantic chunking, hybrid routing, query rewrite, RRF tuning + quality monitoring
> Constraint: Optimize within existing architecture (bge-m3 + Chroma + BM25), no new external services beyond local Ollama

## Problem Statement

Current knowledge retrieval system has critical quality issues:
- Cross-book pollution rate: **73.97%** — nearly 3 out of 4 results come from wrong textbooks
- Top-1 source accuracy: **45%** — the most relevant result is wrong more than half the time
- Hard query hit rate: **0%** for IO operations, annotations, JDBC/Database categories
- Query routing covers **only Java** — 25+ other textbooks have no routing
- Chunking uses naive 500-char hard split — no respect for Markdown structure
- Query rewriting has only **3 hardcoded synonym rules**
- No retrieval quality monitoring beyond one-off eval runs

## Optimization Order (by ROI)

1. Semantic chunking → rebuild Chroma index (foundation)
2. Full-course hybrid routing + source filtering
3. Query rewrite enhancement (Retrieval-aware Rewrite)
4. RRF parameter tuning + snippet truncation + quality monitoring

---

## Section 1: Semantic Chunking (v3)

### Problem

`RecursiveCharacterTextSplitter` with 500-char chunks and 50-char overlap does not respect Markdown structure. Chunks frequently break mid-sentence, mid-paragraph, or mid-section, degrading both embedding quality and BM25 matching.

### Design

**1.1 Two-stage chunking pipeline**

- **Stage 1: Structural physical split** — split by `##` → `###` heading hierarchy, strictly protecting code blocks and table boundaries
- **Stage 2: Orphan chunk fallback merge** — backward scan, merge chunks < 100 chars into the previous adjacent chunk. Even if merged result exceeds 800 chars, do NOT re-trigger splitting (hard termination, prevents infinite loops)

**1.2 Code block and table protection + prepend context**

- Code blocks (` ```...``` `) and tables (`|...|` rows) are indivisible units
- When a code block/table exceeds 800 chars and must become its own chunk, **force-prepend context**: copy 1-2 natural paragraphs of explanatory text from immediately before the code block/table into the chunk's beginning
- This ensures pure-code/pure-table chunks carry natural language semantics for embedding models and BM25

**1.3 Sliding window overlap**

- When forced to split at paragraph boundaries, retain 100-200 chars overlap (default 150)
- Overlap size configurable

**1.4 Heading path strategy**

- Metadata fields: `heading_path`, `section_title`, `parent_section` — used by BM25 search text assembly and post-retrieval rerank reference
- Body prepend: use natural language format `[当前章节上下文：第三章 进程管理 - 3.2 进程调度]` — NOT `>` or other symbols that may confuse embedding models
- Config option `heading_in_body: true/false` for A/B testing effectiveness
- Default: `heading_in_body: true`

**1.5 Chunk size constraints**

- Max: 800 chars (Stage 2 merge may slightly exceed — hard terminate, no re-split)
- Min: 100 chars (below this → merge with previous chunk)
- Overlap: 100-200 chars (default 150)

**1.6 Configurable parameters**

All chunking parameters in `rag_config.py`:
```python
CHUNK_MAX_SIZE = 800
CHUNK_MIN_SIZE = 100
CHUNK_OVERLAP = 150
HEADING_IN_BODY = True
PRIMARY_SPLIT_HEADING = "##"
SECONDARY_SPLIT_HEADING = "###"
```

### Expected outcome

Chunk completeness significantly improved → better embedding semantics → better BM25 matching → hard query hit rate improvement.

---

## Section 2: Full-Course Hybrid Routing + Source Filtering (v2)

### Problem

Only Java has routing rules. All other 25+ textbooks' queries search the entire mixed corpus, causing 73.97% cross-book pollution.

### Design

**2.1 Two-stage hybrid routing (Hybrid Routing)**

**Stage 1: LLM intent identification (primary router)**
- Use local Ollama with lightweight fast model (e.g., `qwen2.5:1.5b`), Temperature=0
- Prompt provides complete list of 26 textbooks, asks model to select 1-3 most relevant with confidence scores
- LLM routing latency target: < 200ms (1.5b model + short prompt)
- If all LLM-returned course confidence scores are below threshold → fall through to Stage 2

**Stage 2: Weighted keyword matching (fallback router)**
- Activated when LLM is unavailable (Ollama not running) or confidence is insufficient
- Guarantees routing result in all cases, never falls back to unfiltered full-corpus search

**2.2 Keyword weighting (TF-IDF inspired)**

Each keyword carries a weight instead of equal votes:
- **Exclusive strong feature words** (weight 2.0): e.g., `TCP`→Computer Networking, `Redis`→Redis, `Vue`→Vue.js, `JVM`→Java
- **Medium discriminative words** (weight 1.0): e.g., `索引`→Database, `装饰器`→Python
- **Cross-domain high-frequency words** (weight 0.5): e.g., `进程`, `线程`, `内存`, `测试`

Scoring formula: `score = sum(matched keyword weights)` — no division by total keyword count

Multi-label activation: score > fixed threshold (e.g., 3.0) → add course to filter list

This ensures "MySQL 的 B+ 树" activates both Database (MySQL 2.0 + 索引 1.0 = 3.0) and Data Structures (B+树 1.0 + 红黑树 1.0 = 2.0).

**2.3 Course linkage (Prerequisite Linkage)**

Define sibling relationships in config:
```yaml
knowledge:
  course_linkage:
    算法: [数据结构]
    数据结构: [算法]
    Java: [数据结构]
    数据库: [数据结构, 操作系统]
    计算机组成原理: [操作系统]
```

When routing identifies a course, automatically add linked courses to source_filter.

**2.4 Config structure**

```yaml
knowledge:
  course_routing:
    计算机网络:
      keywords:
        TCP: 2.0
        UDP: 2.0
        HTTP: 2.0
        DNS: 2.0
        路由: 1.0
        子网掩码: 1.5
        进程: 0.5
    # ... other courses
  course_linkage:
    算法: [数据结构]
    # ...
  routing:
    llm_model: "qwen2.5:1.5b"
    llm_confidence_threshold: 0.6
    keyword_score_threshold: 3.0
```

**2.5 Source filtering consistency**

Dense and sparse retrieval use the same source_filter + canonical identity matching.

### Expected outcome

Cross-book pollution rate < 20%, top-1 source accuracy > 80%.

---

## Section 3: Query Rewrite Enhancement (v3.5)

### Problem

Only 3 hardcoded synonym rules. Hard query hit rate is 0%. But naive LLM rewrite has latency multiplier, precision dilution, and small-model format instability risks.

### Design

**3.1 Retrieval-aware Rewrite flow**

```
User query
    ↓
LRU cache hit? → YES → use cached result
    ↓ NO
Exclusive word / hardcoded rule hit? → YES → direct retrieval (fast path)
    ↓ NO
Original query retrieval (dense + sparse + RRF)
    ↓
Retrieval Confidence = top1_score / mean(top5_scores)
    ↓
confidence >= 1.4? → YES → return directly (quality sufficient)
    ↓ NO
Rewrite Effectiveness Cache lookup
    ↓
Historical rewrite gain for this query pattern < threshold? → YES → skip rewrite, return current results
    ↓ NO
LLM rewrite (max 3 variants)
    ↓
Quality filtering (similarity > 0.6 OR hits textbook terminology DB → keep, else discard)
    ↓
Parallel retrieval (asyncio.gather, within remaining time budget)
    ↓
RRF fusion (Original ×1.5 Boost, Rewrite ×1.0)
    ↓
Record rewrite effectiveness to Effectiveness Cache
    ↓
Return results
```

**3.2 Retrieval Confidence metric**

Use `top1 / mean(top5)` ratio instead of absolute score threshold. Different embedding models have different score scales — relative ranking is more stable.

- >= 1.4: top1 clearly leads, result is trustworthy
- < 1.4: retrieval is uncertain, rewrite needed as recovery

**3.3 Quality dual filtering**

- cosine_similarity(original, rewrite) > 0.6 → keep
- OR rewrite hits textbook terminology DB (`GC`, `ACID`, `B+树`, `JVM`, `CAP`, etc.) → keep
- Prevents both over-generalization (`TCP TIME_WAIT` → `网络协议`) and false kills on semantically related but lexically different rewrites (`B+树` → `数据库索引结构`)

**3.4 Rewrite Effectiveness Cache**

Record per-query-pattern rewrite gain (recall improvement %). Patterns with historical gain below threshold are skipped in future. System gets smarter over time.

**3.5 Time budget mode**

Total budget: 800ms. Consumed time is subtracted from budget, remaining time dynamically allocated to subsequent steps. Fast rewrite → more time for retrieval.

**3.6 Short query handling**

Use token count < 2 (not char length) as skip condition. But if short query hits professional terminology dictionary (e.g., `GC` → `垃圾回收机制, JVM GC`), rewrite is still allowed.

**3.7 Rewrite variants: max 3**

Covering three dimensions: synonyms, hypernyms, textbook terminology.

**3.8 Prompt + Ollama JSON Schema**

Simplified terminology conversion Prompt:
```
你是术语转换器。将口语化输入转为教材标准搜索关键词。
如果输入已是严谨术语，直接返回原词。最多生成3个变体。
```

Ollama `format: "json"` enforces structured output: `{"rewrites": ["关键词1", "关键词2", "关键词3"]}`

**3.9 Rewrite cache**

LRU cache for rewrite results. Same query does not repeat LLM call.

### Expected outcome

LLM call volume reduced by 50-80%, hard query hit rate 40-60%, zero quality degradation for precise queries, end-to-end latency increase < 500ms.

---

## Section 4: RRF Tuning + Snippet Truncation + Quality Monitoring

### Problem

RRF constant k=60 is untested default; snippet truncation at 700 chars ignores semantic boundaries; no ongoing retrieval quality monitoring.

### Design

**4.1 RRF parameter tuning**

- Test k ∈ {10, 20, 30, 40, 60, 100} on existing eval dataset, select value optimizing Hit@4 and MRR
- top_k from fixed 4 to configurable (1-8): precise routing → top_k=4 sufficient; full-corpus search → may need top_k=6

**4.2 Semantic snippet truncation**

- Replace 700-char hard cut with semantic boundary truncation:
  - Prefer truncation at sentence-ending punctuation (`。`, `！`, `？`, `\n`)
  - If no punctuation within 700 chars, extend to nearest sentence end (max 900 chars)
  - If punctuation comes too early (< 500 chars), continue to next sentence end
- Truncation range: 500-900 chars, ensuring complete sentences

**4.3 Retrieval quality monitoring**

Continuous monitoring metrics in eval framework:
- **Recall@K**: proportion of queries where correct source appears in top K results
- **MRR**: mean reciprocal rank of correct sources
- **Hit@K**: proportion of queries with at least one correct source recalled
- **Cross-book pollution rate**: proportion of results from wrong textbooks
- **Retrieval confidence distribution**: statistical distribution of top1/mean(top5)

Expand eval test cases to all courses (currently only 20 Java cases).

Run eval comparison against baseline after each optimization, quantifying improvement.

**4.4 Config centralization**

```yaml
knowledge:
  retrieval:
    rrf_k: 60  # updated after tuning
    default_top_k: 4
    snippet_min: 500
    snippet_max: 900
    confidence_threshold: 1.4
    rewrite_budget_ms: 800
```

### Expected outcome

RRF parameters fitted to this corpus improve ranking quality, snippet completeness improved, retrieval quality quantitatively trackable.

---

## Baseline Metrics (pre-optimization)

| Metric | Value |
|--------|-------|
| Hit@4 | 0.40 |
| MRR | 0.2625 |
| Hard query hit rate | 0.20 |
| Top-1 source accuracy | 0.45 |
| Cross-book pollution rate | 73.97% |

## Target Metrics (post-optimization)

| Metric | Target |
|--------|--------|
| Hit@4 | > 0.75 |
| MRR | > 0.65 |
| Hard query hit rate | > 0.40 |
| Top-1 source accuracy | > 0.80 |
| Cross-book pollution rate | < 0.20 |
