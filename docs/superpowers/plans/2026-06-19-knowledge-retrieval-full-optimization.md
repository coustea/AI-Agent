# Knowledge Retrieval Full Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Optimize the knowledge retrieval system within the existing bge-m3 + Chroma + BM25 architecture to reduce cross-book pollution from 74% to <20% and improve hard query hit rate from 0% to >40%.

**Architecture:** Four-layer optimization: (1) semantic Markdown chunking replaces naive character splitting, (2) two-stage hybrid routing (LLM + weighted keywords) replaces Java-only regex routing, (3) retrieval-aware query rewrite replaces hardcoded synonym rules, (4) RRF tuning + semantic snippet truncation + quality monitoring.

**Tech Stack:** Python 3.12, LangChain, Chroma, Ollama (bge-m3 + qwen2.5:1.5b), BM25, asyncio, pytest

---

## File Structure

### New files
- `server/data/book/markdown_splitter.py` — semantic Markdown chunking with code/table protection
- `server/app/chat/tools/knowledge_router.py` — two-stage hybrid routing (LLM + weighted keywords)
- `server/app/chat/tools/knowledge_rewrite.py` — retrieval-aware query rewrite with effectiveness cache
- `server/data/book/tests/test_markdown_splitter.py` — tests for semantic chunking
- `server/tests/chat/test_knowledge_router.py` — tests for hybrid routing
- `server/tests/chat/test_knowledge_rewrite.py` — tests for query rewrite

### Modified files
- `server/data/book/rag_config.py` — add chunking config constants
- `server/data/book/build_chroma.py` — use MarkdownMarkdownSplitter instead of RecursiveCharacterTextSplitter
- `server/app/chat/tools/knowledge.py` — integrate router, rewrite, semantic truncation; remove inline routing/rewrite logic
- `server/app/config.py` — add new config constants for routing, rewrite, retrieval
- `server/config.yaml` — add course_routing, course_linkage, routing, rewrite, retrieval config sections
- `server/eval/knowledge_retrieval/test_cases.json` — expand to all courses (add 40+ test cases)
- `server/eval/knowledge_retrieval/evaluate.py` — add retrieval confidence metric, expand source metrics

---

## Task 1: Semantic Markdown Chunking

**Files:**
- Create: `server/data/book/markdown_splitter.py`
- Create: `server/data/book/tests/test_markdown_splitter.py`
- Modify: `server/data/book/rag_config.py`

- [ ] **Step 1: Update rag_config.py with chunking parameters**

```python
# server/data/book/rag_config.py — add after existing constants

# ============ 语义分块配置 ============
CHUNK_MAX_SIZE = 800
CHUNK_MIN_SIZE = 100
CHUNK_OVERLAP = 150
HEADING_IN_BODY = True
PRIMARY_SPLIT_HEADING = "##"
SECONDARY_SPLIT_HEADING = "###"
```

- [ ] **Step 2: Write failing tests for MarkdownMarkdownSplitter**

Create `server/data/book/tests/test_markdown_splitter.py`:

```python
"""Tests for semantic Markdown chunking with code/table protection."""

import pytest
from markdown_splitter import (
    MarkdownMarkdownSplitter,
    _split_by_headings,
    _protect_code_blocks_and_tables,
    _merge_orphan_chunks,
    _prepend_context_to_standalone_blocks,
)


# ---- _protect_code_blocks_and_tables ----

class TestProtectCodeBlocksAndTables:
    def test_code_block_not_split(self):
        text = "Before\n```python\nprint('hello')\nprint('world')\n```\nAfter"
        segments = _protect_code_blocks_and_tables(text)
        code_segments = [s for s in segments if s["type"] == "code"]
        assert len(code_segments) == 1
        assert "print('hello')" in code_segments[0]["text"]
        assert "print('world')" in code_segments[0]["text"]

    def test_table_not_split(self):
        text = "Before\n| A | B |\n|---|---|\n| 1 | 2 |\nAfter"
        segments = _protect_code_blocks_and_tables(text)
        table_segments = [s for s in segments if s["type"] == "table"]
        assert len(table_segments) == 1
        assert "| A | B |" in table_segments[0]["text"]

    def test_multiple_code_blocks(self):
        text = "```java\ncode1\n```\nText\n```python\ncode2\n```"
        segments = _protect_code_blocks_and_tables(text)
        code_segments = [s for s in segments if s["type"] == "code"]
        assert len(code_segments) == 2

    def test_plain_text_passes_through(self):
        text = "Just some plain text here."
        segments = _protect_code_blocks_and_tables(text)
        assert len(segments) == 1
        assert segments[0]["type"] == "text"


# ---- _split_by_headings ----

class TestSplitByHeadings:
    def test_splits_on_h2(self):
        text = "## Section 1\nContent 1\n## Section 2\nContent 2"
        chunks = _split_by_headings(text, heading_level="##")
        assert len(chunks) >= 2

    def test_preserves_heading_in_chunk(self):
        text = "## Section 1\nContent 1"
        chunks = _split_by_headings(text, heading_level="##")
        assert any("Section 1" in c["text"] for c in chunks)

    def test_empty_input(self):
        assert _split_by_headings("", heading_level="##") == []


# ---- _merge_orphan_chunks ----

class TestMergeOrphanChunks:
    def test_short_chunk_merged_with_previous(self):
        chunks = [
            {"text": "A" * 200, "heading_path": "Ch1 > S1", "metadata": {}},
            {"text": "Short", "heading_path": "Ch1 > S2", "metadata": {}},
        ]
        merged = _merge_orphan_chunks(chunks, min_size=100)
        assert len(merged) == 1
        assert "Short" in merged[0]["text"]

    def test_no_merge_when_all_above_min(self):
        chunks = [
            {"text": "A" * 200, "heading_path": "Ch1 > S1", "metadata": {}},
            {"text": "B" * 200, "heading_path": "Ch1 > S2", "metadata": {}},
        ]
        merged = _merge_orphan_chunks(chunks, min_size=100)
        assert len(merged) == 2

    def test_merged_chunk_exceeds_max_but_no_resplit(self):
        chunks = [
            {"text": "A" * 700, "heading_path": "Ch1 > S1", "metadata": {}},
            {"text": "B" * 50, "heading_path": "Ch1 > S2", "metadata": {}},
        ]
        merged = _merge_orphan_chunks(chunks, min_size=100, max_size=800)
        assert len(merged) == 1
        # Exceeds 800 but no re-split
        assert len(merged[0]["text"]) > 800


# ---- _prepend_context_to_standalone_blocks ----

class TestPrependContextToStandaloneBlocks:
    def test_code_block_gets_preceding_text(self):
        chunks = [
            {"text": "This explains the code below.", "heading_path": "Ch1 > S1", "metadata": {}},
            {"text": "```python\nprint('hello')\n```", "heading_path": "Ch1 > S1", "metadata": {"is_standalone_block": True}},
        ]
        result = _prepend_context_to_standalone_blocks(chunks)
        assert "This explains the code below." in result[-1]["text"]

    def test_non_standalone_block_unchanged(self):
        chunks = [
            {"text": "Normal text chunk.", "heading_path": "Ch1 > S1", "metadata": {}},
        ]
        result = _prepend_context_to_standalone_blocks(chunks)
        assert result[0]["text"] == "Normal text chunk."


# ---- MarkdownMarkdownSplitter (integration) ----

class TestMarkdownMarkdownSplitter:
    def test_basic_split(self):
        splitter = MarkdownMarkdownSplitter(
            max_chunk_size=800,
            min_chunk_size=100,
            overlap=150,
            heading_in_body=True,
        )
        text = "## Chapter 1\n\nFirst section content with enough text to be a valid chunk on its own. " * 5
        docs = splitter.split_text(text)
        assert len(docs) >= 1

    def test_heading_path_in_metadata(self):
        splitter = MarkdownMarkdownSplitter(heading_in_body=True)
        text = "## Chapter 1\n\n### Section 1.1\n\nContent here. " * 10
        docs = splitter.split_text(text)
        assert any(d.metadata.get("heading_path") for d in docs)

    def test_heading_in_body_format(self):
        splitter = MarkdownMarkdownSplitter(heading_in_body=True)
        text = "## 第三章 进程管理\n\n### 3.2 进程调度\n\n调度算法内容。 " * 10
        docs = splitter.split_text(text)
        body_texts = [d.page_content for d in docs]
        # Should use [当前章节上下文：...] format, not > format
        for t in body_texts:
            if "章节上下文" in t:
                assert not t.startswith(">")

    def test_code_block_integrity(self):
        splitter = MarkdownMarkdownSplitter(max_chunk_size=800)
        code = "```java\n" + "System.out.println(\"line\");\n" * 50 + "```"
        text = f"## Code Section\n\nExplanation.\n\n{code}"
        docs = splitter.split_text(text)
        # Code block should not be split across chunks
        for doc in docs:
            content = doc.page_content
            if "```" in content:
                # Count opening and closing fences
                opens = content.count("```")
                assert opens % 2 == 0, f"Unmatched code fence in chunk: {content[:100]}"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd server && uv run pytest data/book/tests/test_markdown_splitter.py -v`
Expected: FAIL — `markdown_splitter` module not found

- [ ] **Step 4: Implement MarkdownMarkdownSplitter**

Create `server/data/book/markdown_splitter.py`:

```python
"""Semantic Markdown chunking with code/table protection.

Two-stage pipeline:
  1. Structural split by heading hierarchy, protecting code blocks and tables
  2. Backward merge of orphan chunks (< min_size) into previous chunk

When a code block or table exceeds max_chunk_size and becomes a standalone chunk,
1-2 preceding paragraphs are prepended as context for embedding quality.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from langchain_core.documents import Document


# Regex patterns
_CODE_BLOCK_RE = re.compile(r"(```[\s\S]*?```)", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_SENTENCE_END_RE = re.compile(r"[。！？\n]")


@dataclass
class _Segment:
    type: str  # "text", "code", "table"
    text: str
    heading_path: str = ""
    metadata: dict = field(default_factory=dict)


def _find_table_blocks(text: str) -> list[tuple[int, int]]:
    """Find start/end positions of Markdown table blocks."""
    lines = text.split("\n")
    blocks: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if _TABLE_ROW_RE.match(lines[i].strip()):
            start = i
            while i < len(lines) and (_TABLE_ROW_RE.match(lines[i].strip()) or lines[i].strip().startswith("|") and "---" in lines[i]):
                i += 1
            blocks.append((start, i))
        else:
            i += 1
    return blocks


def _protect_code_blocks_and_tables(text: str) -> list[_Segment]:
    """Split text into segments, keeping code blocks and tables as indivisible units."""
    # First extract code blocks
    code_spans: list[tuple[int, int]] = []
    for m in _CODE_BLOCK_RE.finditer(text):
        code_spans.append((m.start(), m.end()))

    # Extract table spans
    table_spans: list[tuple[int, int]] = []
    table_blocks = _find_table_blocks(text)
    for start_line, end_line in table_blocks:
        char_pos = 0
        line_starts: list[int] = []
        for idx, line in enumerate(text.split("\n")):
            line_starts.append(char_pos)
            char_pos += len(line) + 1
        if start_line < len(line_starts) and end_line <= len(line_starts):
            s = line_starts[start_line]
            e = line_starts[end_line - 1] + len(text.split("\n")[end_line - 1]) if end_line - 1 < len(text.split("\n")) else len(text)
            table_spans.append((s, e))

    # Merge all protected spans
    protected = sorted(code_spans + table_spans, key=lambda x: x[0])

    segments: list[_Segment] = []
    prev_end = 0
    for start, end in protected:
        if start > prev_end:
            plain = text[prev_end:start].strip()
            if plain:
                segments.append(_Segment(type="text", text=plain))
        block_text = text[start:end].strip()
        if block_text.startswith("```"):
            segments.append(_Segment(type="code", text=block_text))
        else:
            segments.append(_Segment(type="table", text=block_text))
        prev_end = end

    if prev_end < len(text):
        remaining = text[prev_end:].strip()
        if remaining:
            segments.append(_Segment(type="text", text=remaining))

    if not segments and text.strip():
        segments.append(_Segment(type="text", text=text.strip()))

    return segments


def _split_by_headings(text: str, heading_level: str = "##") -> list[dict]:
    """Split text by heading level, returning chunks with heading paths."""
    if not text.strip():
        return []

    pattern = re.compile(rf"^{re.escape(heading_level)}\s+(.+)$", re.MULTILINE)
    splits = list(pattern.finditer(text))

    if not splits:
        return [{"text": text, "heading_path": "", "metadata": {}}]

    chunks: list[dict] = []
    # Content before first heading
    preamble = text[:splits[0].start()].strip()
    if preamble:
        chunks.append({"text": preamble, "heading_path": "", "metadata": {}})

    for i, match in enumerate(splits):
        title = match.group(1).strip()
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({"text": chunk_text, "heading_path": title, "metadata": {}})

    return chunks


def _merge_orphan_chunks(
    chunks: list[dict],
    min_size: int = 100,
    max_size: int = 800,
) -> list[dict]:
    """Backward merge chunks smaller than min_size into previous chunk.

    Merged chunks may exceed max_size — this is intentional (hard termination
    to prevent infinite re-split loops).
    """
    if not chunks:
        return []

    merged: list[dict] = [dict(chunks[0])]
    for chunk in chunks[1:]:
        if len(chunk["text"]) < min_size and merged:
            # Merge into previous chunk
            prev = merged[-1]
            prev["text"] = prev["text"] + "\n\n" + chunk["text"]
            if chunk.get("heading_path"):
                prev["heading_path"] = prev.get("heading_path", "") + " + " + chunk["heading_path"]
        else:
            merged.append(dict(chunk))
    return merged


def _prepend_context_to_standalone_blocks(chunks: list[dict]) -> list[dict]:
    """When a code block or table is a standalone chunk, prepend 1-2 paragraphs
    of explanatory text from the preceding chunk for embedding context."""
    result: list[dict] = []
    for i, chunk in enumerate(chunks):
        if chunk.get("metadata", {}).get("is_standalone_block") and i > 0:
            prev_text = chunks[i - 1].get("text", "")
            # Extract 1-2 paragraphs (split by double newline)
            paragraphs = [p.strip() for p in prev_text.split("\n\n") if p.strip()]
            context = "\n\n".join(paragraphs[-2:]) if paragraphs else ""
            new_chunk = dict(chunk)
            new_chunk["text"] = context + "\n\n" + chunk["text"] if context else chunk["text"]
            result.append(new_chunk)
        else:
            result.append(dict(chunk))
    return result


def _add_heading_to_body(chunks: list[dict], heading_in_body: bool) -> list[dict]:
    """Prepend heading path to chunk body text in natural language format."""
    if not heading_in_body:
        return chunks
    result: list[dict] = []
    for chunk in chunks:
        heading = chunk.get("heading_path", "")
        if heading:
            new_chunk = dict(chunk)
            new_chunk["text"] = f"[当前章节上下文：{heading}]\n\n{chunk['text']}"
            result.append(new_chunk)
        else:
            result.append(dict(chunk))
    return result


def _apply_overlap(chunks: list[dict], overlap: int) -> list[dict]:
    """Add overlap between consecutive chunks by appending tail of previous chunk."""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    result: list[dict] = []
    for i, chunk in enumerate(chunks):
        new_chunk = dict(chunk)
        if i > 0:
            prev_tail = chunks[i - 1]["text"][-overlap:]
            new_chunk["text"] = prev_tail + "\n\n" + chunk["text"]
        result.append(new_chunk)
    return result


class MarkdownMarkdownSplitter:
    """Semantic Markdown chunker with code/table protection.

    Two-stage pipeline:
      Stage 1: Split by heading hierarchy, protecting code blocks and tables
      Stage 2: Backward merge orphan chunks, then prepend context to standalone blocks
    """

    def __init__(
        self,
        max_chunk_size: int = 800,
        min_chunk_size: int = 100,
        overlap: int = 150,
        heading_in_body: bool = True,
        primary_heading: str = "##",
        secondary_heading: str = "###",
    ) -> None:
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.heading_in_body = heading_in_body
        self.primary_heading = primary_heading
        self.secondary_heading = secondary_heading

    def split_text(self, text: str, source: str = "") -> list[Document]:
        """Split Markdown text into semantic chunks."""
        if not text.strip():
            return []

        # Stage 1: Split by primary heading
        primary_chunks = _split_by_headings(text, self.primary_heading)

        # For oversized primary chunks, split by secondary heading
        refined: list[dict] = []
        for chunk in primary_chunks:
            if len(chunk["text"]) > self.max_chunk_size:
                # Protect code blocks and tables first
                segments = _protect_code_blocks_and_tables(chunk["text"])
                for seg in segments:
                    if seg.type in ("code", "table") and len(seg.text) > self.max_chunk_size:
                        # Standalone block — mark for context prepending
                        refined.append({
                            "text": seg.text,
                            "heading_path": chunk.get("heading_path", ""),
                            "metadata": {"is_standalone_block": True},
                        })
                    elif seg.type in ("code", "table"):
                        refined.append({
                            "text": seg.text,
                            "heading_path": chunk.get("heading_path", ""),
                            "metadata": {},
                        })
                    else:
                        # Text segment — try secondary heading split
                        sub_chunks = _split_by_headings(seg.text, self.secondary_heading)
                        parent_path = chunk.get("heading_path", "")
                        for sc in sub_chunks:
                            sc["heading_path"] = f"{parent_path} - {sc['heading_path']}" if parent_path and sc.get("heading_path") else sc.get("heading_path", "") or parent_path
                            refined.append(sc)
            else:
                refined.append(chunk)

        # Stage 2: Merge orphan chunks (backward scan)
        merged = _merge_orphan_chunks(refined, min_size=self.min_chunk_size, max_size=self.max_chunk_size)

        # Prepend context to standalone code/table blocks
        with_context = _prepend_context_to_standalone_blocks(merged)

        # Add heading path to body text
        with_heading = _add_heading_to_body(with_context, self.heading_in_body)

        # Apply overlap
        with_overlap = _apply_overlap(with_heading, self.overlap)

        # Convert to Document objects
        documents: list[Document] = []
        for i, chunk in enumerate(with_overlap):
            metadata = dict(chunk.get("metadata", {}))
            metadata["chunk_index"] = i
            if chunk.get("heading_path"):
                metadata["heading_path"] = chunk["heading_path"]
                metadata["section_title"] = chunk["heading_path"].split(" - ")[-1] if " - " in chunk["heading_path"] else chunk["heading_path"]
                metadata["parent_section"] = " - ".join(chunk["heading_path"].split(" - ")[:-1]) if " - " in chunk["heading_path"] else ""
            if source:
                metadata["source"] = source
            documents.append(Document(page_content=chunk["text"], metadata=metadata))

        return documents

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split a list of Documents, preserving source metadata."""
        all_chunks: list[Document] = []
        for doc in documents:
            source = doc.metadata.get("source", "")
            chunks = self.split_text(doc.page_content, source=source)
            # Preserve original metadata not overwritten by splitter
            for chunk in chunks:
                for key, value in doc.metadata.items():
                    if key not in chunk.metadata:
                        chunk.metadata[key] = value
            all_chunks.extend(chunks)
        return all_chunks
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd server && uv run pytest data/book/tests/test_markdown_splitter.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/data/book/markdown_splitter.py server/data/book/tests/test_markdown_splitter.py server/data/book/rag_config.py
git commit -m "feat: add semantic Markdown chunker with code/table protection"
```

---

## Task 2: Integrate Semantic Chunking into Build Pipeline

**Files:**
- Modify: `server/data/book/build_chroma.py`
- Modify: `server/data/book/tests/test_build_chroma.py`

- [ ] **Step 1: Update build_chroma.py to use MarkdownMarkdownSplitter**

Replace the `split_documents` function and update imports in `server/data/book/build_chroma.py`:

```python
# Replace line 7 import:
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# With:
from markdown_splitter import MarkdownMarkdownSplitter

# Replace line 9 import:
# from rag_config import CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, DOCS_DIR, DOCS_GLOB, EMBED_BATCH_SIZE
# With:
from rag_config import (
    CHROMA_DIR, CHUNK_MAX_SIZE, CHUNK_MIN_SIZE, CHUNK_OVERLAP,
    DOCS_DIR, DOCS_GLOB, EMBED_BATCH_SIZE, HEADING_IN_BODY,
)

# Replace split_documents function (lines 37-42):
def split_documents(raw_documents):
    splitter = MarkdownMarkdownSplitter(
        max_chunk_size=CHUNK_MAX_SIZE,
        min_chunk_size=CHUNK_MIN_SIZE,
        overlap=CHUNK_OVERLAP,
        heading_in_body=HEADING_IN_BODY,
    )
    return splitter.split_documents(raw_documents)
```

- [ ] **Step 2: Update test_build_chroma.py for new splitter**

In `server/data/book/tests/test_build_chroma.py`, update any test that references `RecursiveCharacterTextSplitter` or `CHUNK_SIZE`/`CHUNK_OVERLAP` to use `MarkdownMarkdownSplitter` and `CHUNK_MAX_SIZE`/`CHUNK_MIN_SIZE`/`CHUNK_OVERLAP`.

- [ ] **Step 3: Run existing tests**

Run: `cd server && uv run pytest data/book/tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Rebuild Chroma index**

Run: `cd server/data/book && uv run python build_chroma.py`
Expected: Prints "Indexed N documents into M chunks" with M likely different from before (chunks now respect Markdown structure)

- [ ] **Step 5: Run knowledge retrieval eval to establish new baseline**

Run: `cd server && uv run python eval/knowledge_retrieval/evaluate.py`
Expected: Record new metrics — chunk quality should improve, especially for structured content

- [ ] **Step 6: Commit**

```bash
git add server/data/book/build_chroma.py server/data/book/tests/test_build_chroma.py
git commit -m "feat: integrate semantic Markdown chunker into Chroma build pipeline"
```

---

## Task 3: Two-Stage Hybrid Routing

**Files:**
- Create: `server/app/chat/tools/knowledge_router.py`
- Create: `server/tests/chat/test_knowledge_router.py`
- Modify: `server/config.yaml`
- Modify: `server/app/config.py`

- [ ] **Step 1: Add routing config to config.yaml**

Add to `server/config.yaml` under the `knowledge:` section:

```yaml
knowledge:
  enabled: true
  collection: "langchain"
  embed_model: "bge-m3:latest"
  top_k: 4
  ollama_base_url: "http://127.0.0.1:11434"
  course_routing:
    Java:
      Java: 2.0
      JVM: 2.0
      JDK: 2.0
      JRE: 1.5
      Spring: 2.0
      MyBatis: 2.0
      JDBC: 2.0
      Servlet: 2.0
      面向对象: 1.0
      多线程: 1.0
      集合框架: 1.0
      异常处理: 0.5
      泛型: 1.0
      反射: 1.0
      注解: 1.0
      进程: 0.5
      线程: 0.5
      内存: 0.5
    计算机网络:
      TCP: 2.0
      UDP: 2.0
      HTTP: 2.0
      DNS: 2.0
      OSI: 2.0
      IP: 1.5
      子网掩码: 1.5
      路由协议: 1.5
      三次握手: 1.5
      四次挥手: 1.5
      网络层: 1.0
      传输层: 1.0
      应用层: 1.0
      进程: 0.5
    操作系统:
      操作系统: 2.0
      进程调度: 2.0
      死锁: 2.0
      内存管理: 2.0
      虚拟内存: 2.0
      页面置换: 2.0
      进程: 1.0
      线程: 1.0
      调度算法: 1.5
      信号量: 1.5
      管道: 1.0
      内存: 0.5
    数据结构:
      数据结构: 2.0
      链表: 2.0
      栈: 1.5
      队列: 1.5
      二叉树: 2.0
      红黑树: 2.0
      AVL: 2.0
      哈希表: 1.5
      图: 1.0
      排序算法: 1.0
      B+树: 1.5
      进程: 0.5
    数据库:
      数据库: 2.0
      SQL: 2.0
      MySQL: 2.0
      索引: 1.5
      事务: 1.5
      范式: 1.5
      ER图: 1.5
      触发器: 1.5
      存储过程: 1.5
      B+树: 1.0
      进程: 0.5
    Python:
      Python: 2.0
      pip: 2.0
      Django: 2.0
      Flask: 2.0
      列表推导: 2.0
      装饰器: 2.0
      生成器: 1.5
      迭代器: 1.0
      面向对象: 0.5
    Redis:
      Redis: 2.0
      缓存: 1.5
      键值: 1.5
      持久化: 1.5
      哨兵: 2.0
      集群: 1.0
      线程: 0.5
    Vue:
      Vue: 2.0
      组件: 1.0
      路由: 1.0
      Vuex: 2.0
      Pinia: 2.0
      生命周期: 1.0
      虚拟DOM: 1.5
    算法:
      算法: 2.0
      动态规划: 2.0
      贪心: 1.5
      分治: 1.5
      回溯: 1.5
      时间复杂度: 1.0
      空间复杂度: 1.0
    计算机组成原理:
      计算机组成: 2.0
      CPU: 2.0
      指令集: 2.0
      流水线: 2.0
      Cache: 2.0
      总线: 1.5
      寻址: 1.5
      内存: 0.5
    软件工程:
      软件工程: 2.0
      需求分析: 1.5
      UML: 2.0
      敏捷: 1.5
      设计模式: 1.0
      测试: 0.5
    高等数学:
      微积分: 2.0
      导数: 2.0
      积分: 2.0
      极限: 2.0
      矩阵: 1.0
    线性代数:
      矩阵: 2.0
      行列式: 2.0
      线性方程组: 2.0
      特征值: 2.0
      向量空间: 2.0
    概率论:
      概率: 2.0
      期望: 2.0
      方差: 2.0
      分布: 1.5
      贝叶斯: 2.0
  course_linkage:
    算法: [数据结构]
    数据结构: [算法]
    Java: [数据结构]
    数据库: [数据结构, 操作系统]
    计算机组成原理: [操作系统]
    高等数学: [线性代数, 概率论]
  routing:
    llm_model: "qwen2.5:1.5b"
    llm_confidence_threshold: 0.6
    keyword_score_threshold: 3.0
```

- [ ] **Step 2: Add routing config constants to config.py**

Add to `server/app/config.py` after the existing knowledge config section (after line 120):

```python
# ============ 知识库路由配置 ============
KB_COURSE_ROUTING: dict = get("knowledge.course_routing", {})
KB_COURSE_LINKAGE: dict = get("knowledge.course_linkage", {})
KB_ROUTING_LLM_MODEL: str = get("knowledge.routing.llm_model", "qwen2.5:1.5b")
KB_ROUTING_LLM_CONFIDENCE: float = get("knowledge.routing.llm_confidence_threshold", 0.6)
KB_ROUTING_KEYWORD_THRESHOLD: float = get("knowledge.routing.keyword_score_threshold", 3.0)
```

- [ ] **Step 3: Write failing tests for knowledge_router.py**

Create `server/tests/chat/test_knowledge_router.py`:

```python
"""Tests for two-stage hybrid routing (LLM + weighted keywords)."""

import pytest
from unittest.mock import patch, MagicMock
from knowledge_router import (
    route_query_sources,
    _keyword_route,
    _llm_route,
    _expand_with_linkage,
    QueryRouteResult,
)


class TestKeywordRoute:
    def test_exclusive_word_high_score(self):
        result = _keyword_route("Redis持久化机制")
        assert "Redis" in [c["course"] for c in result]

    def test_cross_domain_word_low_weight(self):
        result = _keyword_route("进程和线程的区别")
        # "进程" and "线程" are cross-domain (weight 0.5), should not strongly route
        courses = [c["course"] for c in result]
        # Should include OS (进程 weight 1.0 there) but not dominate
        assert any(c in courses for c in ["操作系统"])

    def test_multi_course_activation(self):
        result = _keyword_route("MySQL的B+树索引")
        courses = [c["course"] for c in result]
        assert "数据库" in courses
        assert "数据结构" in courses

    def test_no_match_returns_empty(self):
        result = _keyword_route("今天天气怎么样")
        assert result == []

    def test_score_calculation(self):
        result = _keyword_route("JVM GC")
        java_entry = next((c for c in result if c["course"] == "Java"), None)
        assert java_entry is not None
        assert java_entry["score"] >= 3.0  # JVM(2.0) alone exceeds threshold


class TestExpandWithLinkage:
    def test_linkage_adds_related_courses(self):
        courses = [{"course": "算法", "score": 5.0, "confidence": 0.9}]
        expanded = _expand_with_linkage(courses)
        course_names = [c["course"] for c in expanded]
        assert "数据结构" in course_names

    def test_no_linkage_for_unlinked_course(self):
        courses = [{"course": "Redis", "score": 5.0, "confidence": 0.9}]
        expanded = _expand_with_linkage(courses)
        assert len(expanded) == 1


class TestRouteQuerySources:
    def test_java_query_routes_to_java(self):
        result = route_query_sources("Java多线程怎么创建")
        assert result.source_filter is not None
        assert any("Java" in s for s in result.source_filter)

    def test_network_query_routes_to_network(self):
        result = route_query_sources("TCP三次握手的过程")
        assert result.source_filter is not None

    def test_ambiguous_query_gets_multiple_courses(self):
        result = route_query_sources("MySQL的B+树索引")
        assert result.source_filter is not None
        assert len(result.source_filter) >= 2

    @patch("knowledge_router._llm_route", return_value=[])
    def test_fallback_to_keyword_when_llm_fails(self, mock_llm):
        result = route_query_sources("Redis缓存穿透")
        assert result.source_filter is not None
        assert any("Redis" in s for s in result.source_filter)

    def test_no_match_returns_none_filter(self):
        result = route_query_sources("今天吃什么")
        assert result.source_filter is None
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd server && uv run pytest tests/chat/test_knowledge_router.py -v`
Expected: FAIL — `knowledge_router` module not found

- [ ] **Step 5: Implement knowledge_router.py**

Create `server/app/chat/tools/knowledge_router.py`:

```python
"""Two-stage hybrid routing for knowledge retrieval.

Stage 1: LLM intent identification (primary) — uses lightweight local model
Stage 2: Weighted keyword matching (fallback) — TF-IDF inspired scoring

Course linkage expands source_filter to include related textbooks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import (
    KB_COURSE_ROUTING,
    KB_COURSE_LINKAGE,
    KB_ROUTING_LLM_MODEL,
    KB_ROUTING_LLM_CONFIDENCE,
    KB_ROUTING_KEYWORD_THRESHOLD,
    KB_OLLAMA_BASE_URL,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

# Source name mapping: config key → canonical book title substring
_COURSE_SOURCE_MAP: dict[str, str] = {
    "Java": "Java从入门到精通",
    "计算机网络": "计算机网络",
    "操作系统": "计算机操作系统",
    "数据结构": "数据结构",
    "数据库": "数据库系统概念",
    "Python": "Python编程",
    "Redis": "Redis设计与实现",
    "Vue": "Vue.js",
    "算法": "算法",
    "计算机组成原理": "计算机组成原理",
    "软件工程": "软件工程",
    "高等数学": "高等数学",
    "线性代数": "线性代数",
    "概率论": "概率论",
}


@dataclass(frozen=True)
class _CourseScore:
    course: str
    score: float
    confidence: float = 1.0


@dataclass(frozen=True)
class QueryRouteResult:
    query: str
    source_filter: tuple[str, ...] | None = None


def _keyword_route(query: str) -> list[_CourseScore]:
    """Weighted keyword matching with TF-IDF inspired scoring.

    Each keyword has a weight: exclusive words (2.0), medium (1.0-1.5),
    cross-domain (0.5). Score = sum of matched keyword weights.
    Courses with score >= threshold are returned.
    """
    if not KB_COURSE_ROUTING:
        return []

    results: list[_CourseScore] = []
    query_lower = query.lower()

    for course, keywords in KB_COURSE_ROUTING.items():
        if not isinstance(keywords, dict):
            continue
        score = 0.0
        for keyword, weight in keywords.items():
            if isinstance(weight, (int, float)) and re.search(re.escape(keyword.lower()), query_lower):
                score += float(weight)
        if score >= KB_ROUTING_KEYWORD_THRESHOLD:
            results.append(_CourseScore(course=course, score=score))

    results.sort(key=lambda x: x.score, reverse=True)
    return results


def _llm_route(query: str) -> list[_CourseScore]:
    """LLM intent identification using lightweight local model.

    Returns list of course scores with confidence. Falls back gracefully
    on any error (timeout, Ollama not running, parse failure).
    """
    if not KB_COURSE_ROUTING:
        return []

    course_list = list(KB_COURSE_ROUTING.keys())
    prompt = (
        f"你是课程分类专家。请从以下教材中选择与问题最相关的1-3本，返回JSON格式。\n"
        f"教材列表：{', '.join(course_list)}\n"
        f"问题：{query}\n"
        f'返回格式：{{"courses": [{{"name": "教材名", "confidence": 0.9}}]}}'
    )

    try:
        resp = httpx.post(
            f"{KB_OLLAMA_BASE_URL}/api/generate",
            json={
                "model": KB_ROUTING_LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": 200},
            },
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_response = data.get("response", "")
        parsed = json.loads(raw_response)
        courses_raw = parsed.get("courses", [])

        results: list[_CourseScore] = []
        for c in courses_raw:
            name = str(c.get("name", "")).strip()
            confidence = float(c.get("confidence", 0.5))
            # Match to known course names (fuzzy)
            matched = None
            for known in course_list:
                if known.lower() in name.lower() or name.lower() in known.lower():
                    matched = known
                    break
            if matched and confidence >= KB_ROUTING_LLM_CONFIDENCE:
                results.append(_CourseScore(course=matched, score=confidence * 5.0, confidence=confidence))
        return results
    except Exception:
        logger.debug("[knowledge_router] LLM routing failed, falling back to keywords")
        return []


def _expand_with_linkage(courses: list[_CourseScore]) -> list[_CourseScore]:
    """Expand course list with prerequisite/sibling linkages."""
    if not KB_COURSE_LINKAGE:
        return courses

    existing = {c.course for c in courses}
    expanded = list(courses)
    for course_score in courses:
        linked = KB_COURSE_LINKAGE.get(course_score.course, [])
        for linked_course in linked:
            if linked_course not in existing and linked_course in _COURSE_SOURCE_MAP:
                expanded.append(_CourseScore(
                    course=linked_course,
                    score=course_score.score * 0.5,
                    confidence=course_score.confidence * 0.7,
                ))
                existing.add(linked_course)
    return expanded


def _courses_to_source_filter(courses: list[_CourseScore]) -> tuple[str, ...] | None:
    """Convert course scores to source filter tuple using _COURSE_SOURCE_MAP."""
    if not courses:
        return None
    sources: list[str] = []
    for cs in courses:
        source = _COURSE_SOURCE_MAP.get(cs.course)
        if source and source not in sources:
            sources.append(source)
    return tuple(sources) if sources else None


def route_query_sources(query: str, course_name: str | None = None) -> QueryRouteResult:
    """Two-stage hybrid routing: LLM (primary) + weighted keywords (fallback).

    1. Try LLM intent identification
    2. If LLM fails or low confidence, use keyword matching
    3. Expand with course linkage
    4. Convert to source_filter
    """
    normalized_query = (query or "").strip()
    normalized_course_name = (course_name or "").strip()
    routing_text = " ".join(part for part in (normalized_course_name, normalized_query) if part)

    if not routing_text:
        return QueryRouteResult(query=normalized_query, source_filter=None)

    # If course_name directly maps to a course, use it as strong signal
    if normalized_course_name:
        for course_key, source_name in _COURSE_SOURCE_MAP.items():
            if course_key.lower() in normalized_course_name.lower():
                courses = [_CourseScore(course=course_key, score=10.0, confidence=1.0)]
                expanded = _expand_with_linkage(courses)
                return QueryRouteResult(
                    query=normalized_query,
                    source_filter=_courses_to_source_filter(expanded),
                )

    # Stage 1: LLM routing
    llm_results = _llm_route(routing_text)
    if llm_results:
        expanded = _expand_with_linkage(llm_results)
        source_filter = _courses_to_source_filter(expanded)
        if source_filter:
            return QueryRouteResult(query=normalized_query, source_filter=source_filter)

    # Stage 2: Keyword fallback
    keyword_results = _keyword_route(routing_text)
    if keyword_results:
        expanded = _expand_with_linkage(keyword_results)
        source_filter = _courses_to_source_filter(expanded)
        if source_filter:
            return QueryRouteResult(query=normalized_query, source_filter=source_filter)

    return QueryRouteResult(query=normalized_query, source_filter=None)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && uv run pytest tests/chat/test_knowledge_router.py -v`
Expected: All tests PASS (LLM-dependent tests may need Ollama running; keyword tests should pass regardless)

- [ ] **Step 7: Commit**

```bash
git add server/app/chat/tools/knowledge_router.py server/tests/chat/test_knowledge_router.py server/config.yaml server/app/config.py
git commit -m "feat: add two-stage hybrid routing with LLM + weighted keywords"
```

---

## Task 4: Integrate Router into knowledge.py

**Files:**
- Modify: `server/app/chat/tools/knowledge.py`
- Modify: `server/tests/chat/test_knowledge_retrieval.py`

- [ ] **Step 1: Replace inline routing in knowledge.py**

In `server/app/chat/tools/knowledge.py`:

1. Add import at top:
```python
from app.chat.tools.knowledge_router import route_query_sources as _hybrid_route, QueryRouteResult
```

2. Remove the old `_JAVA_QUERY_RE`, `_JAVA_SOURCE_FILTER` constants (lines 59-60)

3. Replace the `route_query_sources` function (lines 71-76) with a delegation:
```python
def route_query_sources(query: str, course_name: str | None = None) -> QueryRouteResult:
    """Route query to relevant source textbooks using hybrid routing."""
    return _hybrid_route(query, course_name=course_name)
```

4. Keep the `QueryRouteResult` dataclass import from `knowledge_router` — remove the local definition (lines 65-68)

- [ ] **Step 2: Update test_knowledge_retrieval.py**

Update `test_route_query_sources_routes_java_queries_to_exact_java_book_source` to work with the new router. The test should still verify that Java queries get routed to Java source, but now through the hybrid router.

Also update `test_retrieve_knowledge_forwards_course_name_and_routed_source_filter` to work with the new routing.

- [ ] **Step 3: Run all knowledge tests**

Run: `cd server && uv run pytest tests/chat/test_knowledge_retrieval.py tests/chat/test_knowledge_router.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add server/app/chat/tools/knowledge.py server/tests/chat/test_knowledge_retrieval.py
git commit -m "feat: integrate hybrid router into knowledge retrieval pipeline"
```

---

## Task 5: Retrieval-Aware Query Rewrite

**Files:**
- Create: `server/app/chat/tools/knowledge_rewrite.py`
- Create: `server/tests/chat/test_knowledge_rewrite.py`
- Modify: `server/config.yaml`
- Modify: `server/app/config.py`

- [ ] **Step 1: Add rewrite config to config.yaml**

Add under `knowledge:` section:

```yaml
  rewrite:
    enabled: true
    llm_model: "qwen2.5:1.5b"
    max_variants: 3
    similarity_threshold: 0.6
    confidence_threshold: 1.4
    budget_ms: 800
    effectiveness_cache_size: 200
```

- [ ] **Step 2: Add rewrite config constants to config.py**

Add to `server/app/config.py`:

```python
# ============ 知识库查询改写配置 ============
KB_REWRITE_ENABLED: bool = get("knowledge.rewrite.enabled", True)
KB_REWRITE_LLM_MODEL: str = get("knowledge.rewrite.llm_model", "qwen2.5:1.5b")
KB_REWRITE_MAX_VARIANTS: int = get("knowledge.rewrite.max_variants", 3)
KB_REWRITE_SIMILARITY_THRESHOLD: float = get("knowledge.rewrite.similarity_threshold", 0.6)
KB_REWRITE_CONFIDENCE_THRESHOLD: float = get("knowledge.rewrite.confidence_threshold", 1.4)
KB_REWRITE_BUDGET_MS: int = get("knowledge.rewrite.budget_ms", 800)
KB_REWRITE_EFFECTIVENESS_CACHE_SIZE: int = get("knowledge.rewrite.effectiveness_cache_size", 200)
```

- [ ] **Step 3: Write failing tests for knowledge_rewrite.py**

Create `server/tests/chat/test_knowledge_rewrite.py`:

```python
"""Tests for retrieval-aware query rewrite."""

import pytest
from unittest.mock import patch, MagicMock
from knowledge_rewrite import (
    compute_retrieval_confidence,
    should_trigger_rewrite,
    rewrite_query_with_llm,
    filter_rewrite_variants,
    RewriteEffectivenessCache,
)


class TestRetrievalConfidence:
    def test_high_confidence_when_top1_leads(self):
        rows = [
            {"distance": 0.2},
            {"distance": 0.6},
            {"distance": 0.65},
            {"distance": 0.7},
            {"distance": 0.75},
        ]
        confidence = compute_retrieval_confidence(rows)
        assert confidence >= 1.4

    def test_low_confidence_when_scores_clustered(self):
        rows = [
            {"distance": 0.6},
            {"distance": 0.61},
            {"distance": 0.62},
            {"distance": 0.63},
            {"distance": 0.64},
        ]
        confidence = compute_retrieval_confidence(rows)
        assert confidence < 1.4

    def test_empty_rows(self):
        confidence = compute_retrieval_confidence([])
        assert confidence == 0.0

    def test_single_row(self):
        confidence = compute_retrieval_confidence([{"distance": 0.5}])
        assert confidence == 0.0  # Need at least 2 rows


class TestShouldTriggerRewrite:
    def test_skip_when_exclusive_word_hit(self):
        assert should_trigger_rewrite("Redis缓存穿透", exclusive_words=["Redis"]) is False

    def test_skip_when_hardcoded_rule_hit(self):
        assert should_trigger_rewrite("tcp三次握手", hardcoded_rules=["tcp"]) is False

    def test_trigger_when_no_fast_path(self):
        assert should_trigger_rewrite("程序卡住不动了") is True

    def test_short_query_in_terminology_dict(self):
        assert should_trigger_rewrite("GC", terminology_dict={"GC": True}) is True

    def test_short_query_not_in_dict(self):
        # "GC" has 1 token, < 2, but not in dict
        assert should_trigger_rewrite("GC", terminology_dict={}) is False


class TestFilterRewriteVariants:
    def test_keep_similar_variant(self):
        original = "死锁"
        variants = ["死锁 进程阻塞", "线程挂起", "网络协议"]
        # Mock similarity: first two > 0.6, last < 0.6
        with patch("knowledge_rewrite._compute_similarity", side_effect=[0.8, 0.7, 0.3]):
            filtered = filter_rewrite_variants(original, variants, terminology_db={"ACID": True})
        assert "死锁 进程阻塞" in filtered
        assert "网络协议" not in filtered

    def test_keep_terminology_db_hit_even_with_low_similarity(self):
        original = "B+树"
        variants = ["数据库索引结构"]
        with patch("knowledge_rewrite._compute_similarity", return_value=0.4):
            with patch("knowledge_rewrite._hits_terminology_db", return_value=True):
                filtered = filter_rewrite_variants(original, variants, terminology_db={"B+树": True})
        assert "数据库索引结构" in filtered


class TestRewriteEffectivenessCache:
    def test_record_and_check_effectiveness(self):
        cache = RewriteEffectivenessCache(maxsize=10)
        cache.record("GC", gain=0.35)
        assert cache.is_effective("GC") is True

    def test_ineffective_pattern_skipped(self):
        cache = RewriteEffectivenessCache(maxsize=10)
        cache.record("TCP", gain=0.02)
        assert cache.is_effective("TCP") is False

    def test_unknown_pattern_not_in_cache(self):
        cache = RewriteEffectivenessCache(maxsize=10)
        assert cache.is_effective("unknown") is True  # Unknown = allow rewrite
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd server && uv run pytest tests/chat/test_knowledge_rewrite.py -v`
Expected: FAIL — `knowledge_rewrite` module not found

- [ ] **Step 5: Implement knowledge_rewrite.py**

Create `server/app/chat/tools/knowledge_rewrite.py`:

```python
"""Retrieval-aware query rewrite for knowledge retrieval.

Flow: original query → retrieve → confidence check → (if low) LLM rewrite → parallel retrieve → RRF fusion

Key design decisions:
- Rewrite is a RECOVERY mechanism, not default path
- Original query always participates with 1.5x boost in RRF
- Quality filtering: similarity > 0.6 OR terminology DB hit
- Time budget mode: 800ms total, dynamically allocated
- Effectiveness cache: skip rewrite for patterns with historically low gain
"""

from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from typing import Any

import httpx

from app.config import (
    KB_REWRITE_ENABLED,
    KB_REWRITE_LLM_MODEL,
    KB_REWRITE_MAX_VARIANTS,
    KB_REWRITE_SIMILARITY_THRESHOLD,
    KB_REWRITE_CONFIDENCE_THRESHOLD,
    KB_REWRITE_BUDGET_MS,
    KB_REWRITE_EFFECTIVENESS_CACHE_SIZE,
    KB_OLLAMA_BASE_URL,
    KB_COURSE_ROUTING,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

# Professional terminology dictionary for short-query handling
_TERMINOLOGY_DB: dict[str, bool] = {
    "GC": True, "JVM": True, "JDK": True, "JRE": True,
    "ACID": True, "CAP": True, "TCP": True, "UDP": True,
    "HTTP": True, "DNS": True, "SQL": True, "OS": True,
    "OOM": True, "API": True, "ORM": True, "MVC": True,
    "B+树": True, "B树": True, "AVL": True,
}

# Exclusive words from routing config (weight >= 2.0)
_EXCLUSIVE_WORDS: set[str] = set()
for _course, keywords in KB_COURSE_ROUTING.items():
    if isinstance(keywords, dict):
        for kw, weight in keywords.items():
            if isinstance(weight, (int, float)) and float(weight) >= 2.0:
                _EXCLUSIVE_WORDS.add(kw.lower())


def compute_retrieval_confidence(rows: list[dict[str, Any]]) -> float:
    """Compute retrieval confidence as top1_score / mean(top5_scores).

    Uses relative ranking instead of absolute score threshold,
    which is more stable across different embedding models.
    """
    if len(rows) < 2:
        return 0.0

    # For dense: distance is similarity (higher = better for relevance_score)
    # For sparse: distance is -score (lower = better)
    # We use absolute value and take top5 by best relevance
    scores = [abs(row.get("distance", 0.0)) for row in rows[:5]]
    if not scores or scores[0] == 0:
        return 0.0

    top1 = scores[0]
    avg_rest = sum(scores[1:]) / len(scores[1:]) if len(scores) > 1 else top1
    if avg_rest == 0:
        return float("inf")
    return top1 / avg_rest


def _count_tokens(text: str) -> int:
    """Count meaningful tokens in text (Chinese chars + ASCII words)."""
    chinese = len(re.findall(r"[一-鿿]", text))
    ascii_words = len(re.findall(r"[A-Za-z0-9+#.-]+", text))
    return chinese + ascii_words


def should_trigger_rewrite(
    query: str,
    *,
    exclusive_words: set[str] | None = None,
    hardcoded_rules: list[str] | None = None,
    terminology_dict: dict[str, bool] | None = None,
) -> bool:
    """Determine if query rewrite should be triggered.

    Skip rewrite when:
    - Query hits exclusive word (already precise)
    - Query hits hardcoded rewrite rule (fast path)
    - Query is too short (< 2 tokens) and not in terminology dict
    """
    if not KB_REWRITE_ENABLED:
        return False

    query_lower = query.lower()
    excl = exclusive_words or _EXCLUSIVE_WORDS

    # Check exclusive words
    for word in excl:
        if word in query_lower:
            return False

    # Check hardcoded rules
    if hardcoded_rules:
        for rule in hardcoded_rules:
            if rule.lower() in query_lower:
                return False

    # Check token count
    token_count = _count_tokens(query)
    if token_count < 2:
        term_dict = terminology_dict or _TERMINOLOGY_DB
        # Short query in terminology dict → allow rewrite
        if query.strip() in term_dict:
            return True
        return False

    return True


def _compute_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between two texts using embedding.

    Falls back to character overlap ratio if embedding fails.
    """
    # Simple character-level Jaccard as fallback
    set1 = set(text1.lower())
    set2 = set(text2.lower())
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


def _hits_terminology_db(text: str, terminology_db: dict[str, bool] | None = None) -> bool:
    """Check if text contains any term from the terminology database."""
    term_dict = terminology_db or _TERMINOLOGY_DB
    for term in term_dict:
        if term.lower() in text.lower():
            return True
    return False


def filter_rewrite_variants(
    original: str,
    variants: list[str],
    *,
    terminology_db: dict[str, bool] | None = None,
) -> list[str]:
    """Filter rewrite variants by quality: similarity > threshold OR terminology DB hit."""
    filtered: list[str] = []
    for variant in variants:
        sim = _compute_similarity(original, variant)
        if sim >= KB_REWRITE_SIMILARITY_THRESHOLD:
            filtered.append(variant)
        elif _hits_terminology_db(variant, terminology_db):
            filtered.append(variant)
        else:
            logger.debug("[knowledge_rewrite] Discarded variant '%s' (sim=%.2f)", variant, sim)
    return filtered


def rewrite_query_with_llm(query: str, *, max_variants: int | None = None) -> list[str]:
    """Use LLM to rewrite query into textbook-standard search terms.

    Returns list of rewrite variants (max 3). Uses Ollama JSON schema
    for structured output.
    """
    n = max_variants or KB_REWRITE_MAX_VARIANTS
    prompt = (
        "你是术语转换器。将口语化输入转为教材标准搜索关键词。\n"
        "如果输入已是严谨术语，直接返回原词。最多生成3个变体。\n"
        f"输入：{query}"
    )

    try:
        start = time.monotonic()
        resp = httpx.post(
            f"{KB_OLLAMA_BASE_URL}/api/generate",
            json={
                "model": KB_REWRITE_LLM_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0, "num_predict": 100},
            },
            timeout=0.3,  # 300ms hard limit
        )
        elapsed = time.monotonic() - start
        logger.debug("[knowledge_rewrite] LLM rewrite took %.0fms", elapsed * 1000)

        resp.raise_for_status()
        data = resp.json()
        raw = data.get("response", "")
        parsed = json.loads(raw)
        rewrites = parsed.get("rewrites", [])
        if isinstance(rewrites, list):
            return [str(r).strip() for r in rewrites[:n] if str(r).strip()]
    except Exception:
        logger.debug("[knowledge_rewrite] LLM rewrite failed or timed out")
    return []


class RewriteEffectivenessCache:
    """Track per-query-pattern rewrite effectiveness.

    Patterns with historically low gain are skipped in future.
    """

    def __init__(self, maxsize: int = KB_REWRITE_EFFECTIVENESS_CACHE_SIZE) -> None:
        self._cache: dict[str, float] = {}
        self._maxsize = maxsize
        self._gain_threshold = 0.05  # 5% minimum improvement

    def record(self, query_pattern: str, *, gain: float) -> None:
        """Record rewrite gain for a query pattern."""
        if len(self._cache) >= self._maxsize:
            # Evict oldest entry
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[query_pattern] = gain

    def is_effective(self, query_pattern: str) -> bool:
        """Check if rewrite has been historically effective for this pattern.

        Returns True if pattern is unknown (allow rewrite) or has good gain.
        Returns False if pattern has historically low gain.
        """
        gain = self._cache.get(query_pattern)
        if gain is None:
            return True  # Unknown = allow
        return gain >= self._gain_threshold


# Module-level effectiveness cache
_effectiveness_cache = RewriteEffectivenessCache()


def get_effectiveness_cache() -> RewriteEffectivenessCache:
    return _effectiveness_cache
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && uv run pytest tests/chat/test_knowledge_rewrite.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add server/app/chat/tools/knowledge_rewrite.py server/tests/chat/test_knowledge_rewrite.py server/config.yaml server/app/config.py
git commit -m "feat: add retrieval-aware query rewrite with effectiveness cache"
```

---

## Task 6: Integrate Rewrite into knowledge.py Retrieval Pipeline

**Files:**
- Modify: `server/app/chat/tools/knowledge.py`

- [ ] **Step 1: Add rewrite integration to retrieve_knowledge**

In `server/app/chat/tools/knowledge.py`, modify `retrieve_knowledge` function to implement the retrieval-aware rewrite flow:

1. Add imports:
```python
from app.chat.tools.knowledge_rewrite import (
    compute_retrieval_confidence,
    should_trigger_rewrite,
    rewrite_query_with_llm,
    filter_rewrite_variants,
    get_effectiveness_cache,
)
```

2. Replace `retrieve_knowledge` function (lines 623-658) with:

```python
def retrieve_knowledge(
    query: str,
    *,
    course_name: str | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Hybrid retrieval with retrieval-aware query rewrite.

    Flow: route → retrieve → confidence check → (if low) rewrite → parallel retrieve → RRF fusion
    """
    normalized_query = (query or "").strip()
    if not normalized_query:
        return []

    effective_top_k = top_k or KB_TOP_K
    route = route_query_sources(normalized_query, course_name=course_name)

    # Initial retrieval with original query
    candidate_k = max(effective_top_k * 2, KB_TOP_K)
    dense_rows = retrieve_dense_knowledge(
        route.query,
        top_k=candidate_k,
        source_filter=route.source_filter,
    )
    sparse_rows = retrieve_sparse_knowledge(
        route.query,
        top_k=candidate_k,
        source_filter=route.source_filter,
    )

    # Check retrieval confidence
    all_initial = dense_rows + sparse_rows
    confidence = compute_retrieval_confidence(all_initial)

    if confidence >= KB_REWRITE_CONFIDENCE_THRESHOLD or not should_trigger_rewrite(normalized_query):
        # Quality sufficient or rewrite not needed — merge and return
        if not dense_rows and not sparse_rows:
            return []
        return merge_ranked_results(
            route.query,
            dense_rows=dense_rows,
            sparse_rows=sparse_rows,
            top_k=effective_top_k,
            source_filter=route.source_filter,
        )

    # Low confidence — try rewrite
    eff_cache = get_effectiveness_cache()
    if not eff_cache.is_effective(normalized_query):
        # Historically ineffective — skip rewrite
        if not dense_rows and not sparse_rows:
            return []
        return merge_ranked_results(
            route.query,
            dense_rows=dense_rows,
            sparse_rows=sparse_rows,
            top_k=effective_top_k,
            source_filter=route.source_filter,
        )

    # LLM rewrite
    variants = rewrite_query_with_llm(normalized_query)
    filtered_variants = filter_rewrite_variants(normalized_query, variants)

    if not filtered_variants:
        # No valid rewrites — return initial results
        if not dense_rows and not sparse_rows:
            return []
        return merge_ranked_results(
            route.query,
            dense_rows=dense_rows,
            sparse_rows=sparse_rows,
            top_k=effective_top_k,
            source_filter=route.source_filter,
        )

    # Parallel retrieval for rewrite variants
    rewrite_dense: list[dict[str, Any]] = []
    rewrite_sparse: list[dict[str, Any]] = []

    for variant in filtered_variants:
        v_dense = retrieve_dense_knowledge(variant, top_k=effective_top_k, source_filter=route.source_filter)
        v_sparse = retrieve_sparse_knowledge(variant, top_k=effective_top_k, source_filter=route.source_filter)
        rewrite_dense.extend(v_dense)
        rewrite_sparse.extend(v_sparse)

    # RRF fusion with original query boost (1.5x)
    all_dense = dense_rows + rewrite_dense
    all_sparse = sparse_rows + rewrite_sparse

    if not all_dense and not all_sparse:
        return []

    # Mark original query results for boost
    for row in dense_rows:
        row["_is_original"] = True
    for row in sparse_rows:
        row["_is_original"] = True

    result = merge_ranked_results(
        route.query,
        dense_rows=all_dense,
        sparse_rows=all_sparse,
        top_k=effective_top_k,
        source_filter=route.source_filter,
        original_boost=1.5,
    )

    # Record effectiveness (compare with initial results)
    initial_result = merge_ranked_results(
        route.query,
        dense_rows=dense_rows,
        sparse_rows=sparse_rows,
        top_k=effective_top_k,
        source_filter=route.source_filter,
    )
    if initial_result and result:
        initial_best = abs(initial_result[0].get("distance", 0))
        rewritten_best = abs(result[0].get("distance", 0))
        if initial_best > 0:
            gain = (rewritten_best - initial_best) / initial_best
            eff_cache.record(normalized_query, gain=gain)

    return result
```

3. Update `merge_ranked_results` to support `original_boost` parameter:

Add `original_boost: float = 1.0` parameter to `merge_ranked_results` signature, and modify the score accumulation:

```python
def merge_ranked_results(
    query: str,
    *,
    dense_rows: list[dict[str, Any]],
    sparse_rows: list[dict[str, Any]],
    top_k: int | None = None,
    source_filter: tuple[str, ...] | None = None,
    original_boost: float = 1.0,
) -> list[dict[str, Any]]:
```

In the score accumulation loop, apply boost:
```python
for rows in (dense_rows, sparse_rows):
    for item in rows:
        metadata = dict(item.get("metadata") or {})
        key = _metadata_key(metadata)
        score = _rrf_score(int(item.get("rank") or 0))
        # Apply boost to original query results
        if item.get("_is_original"):
            score *= original_boost
        # ... rest of existing logic
```

- [ ] **Step 2: Run all knowledge tests**

Run: `cd server && uv run pytest tests/chat/test_knowledge_retrieval.py tests/chat/test_knowledge_router.py tests/chat/test_knowledge_rewrite.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add server/app/chat/tools/knowledge.py
git commit -m "feat: integrate retrieval-aware query rewrite into knowledge pipeline"
```

---

## Task 7: RRF Tuning + Semantic Snippet Truncation

**Files:**
- Modify: `server/app/chat/tools/knowledge.py`
- Modify: `server/app/config.py`
- Modify: `server/config.yaml`

- [ ] **Step 1: Add retrieval config to config.yaml**

Add under `knowledge:` section:

```yaml
  retrieval:
    rrf_k: 60
    default_top_k: 4
    snippet_min: 500
    snippet_max: 900
```

- [ ] **Step 2: Add retrieval config constants to config.py**

```python
# ============ 知识库检索配置 ============
KB_RRF_K: int = get("knowledge.retrieval.rrf_k", 60)
KB_SNIPPET_MIN: int = get("knowledge.retrieval.snippet_min", 500)
KB_SNIPPET_MAX: int = get("knowledge.retrieval.snippet_max", 900)
```

- [ ] **Step 3: Update _rrf_score to use configurable constant**

In `knowledge.py`, replace:
```python
def _rrf_score(rank: int, constant: int = 60) -> float:
```
With:
```python
def _rrf_score(rank: int, constant: int | None = None) -> float:
    return 1.0 / ((constant or KB_RRF_K) + rank)
```

- [ ] **Step 4: Implement semantic snippet truncation**

In `knowledge.py`, replace the snippet truncation in `format_knowledge_context` (lines 689-691):

```python
# Replace:
# snippet = str(item.get("text") or "").replace("\r", " ").replace("\n", " ").strip()
# if len(snippet) > 700:
#     snippet = snippet[:700].rstrip() + "..."

# With:
snippet = _semantic_truncate(
    str(item.get("text") or "").replace("\r", " ").replace("\n", " ").strip(),
    min_len=KB_SNIPPET_MIN,
    max_len=KB_SNIPPET_MAX,
)
```

Add the `_semantic_truncate` function:

```python
def _semantic_truncate(text: str, *, min_len: int = 500, max_len: int = 900) -> str:
    """Truncate text at semantic boundaries (sentence endings).

    Prefers truncation at sentence-ending punctuation.
    Falls back to max_len hard cut if no boundary found.
    """
    if len(text) <= min_len:
        return text

    # Find sentence-ending positions between min_len and max_len
    search_start = min_len
    search_end = min(max_len, len(text))

    for i in range(search_start, search_end):
        if text[i] in "。！？\n":
            return text[:i + 1].rstrip()

    # No sentence boundary found — hard cut at max_len
    if len(text) > max_len:
        return text[:max_len].rstrip() + "..."
    return text
```

- [ ] **Step 5: Run tests**

Run: `cd server && uv run pytest tests/chat/test_knowledge_retrieval.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/app/chat/tools/knowledge.py server/app/config.py server/config.yaml
git commit -m "feat: add configurable RRF constant and semantic snippet truncation"
```

---

## Task 8: Expand Eval Test Cases to All Courses

**Files:**
- Modify: `server/eval/knowledge_retrieval/test_cases.json`
- Modify: `server/eval/knowledge_retrieval/evaluate.py`

- [ ] **Step 1: Add test cases for all major courses**

Add 40+ new test cases to `test_cases.json` covering:
- 计算机网络 (5 cases): TCP三次握手, UDP特点, HTTP请求方法, DNS解析, 子网掩码计算
- 操作系统 (5 cases): 进程调度算法, 死锁条件, 虚拟内存, 页面置换, 信号量
- 数据结构 (5 cases): 二叉树遍历, 链表操作, 栈的应用, 哈希表冲突, 排序算法比较
- 数据库 (5 cases): SQL查询, 事务ACID, 索引类型, 范式, 存储过程
- Python (3 cases): 装饰器, 列表推导, 生成器
- Redis (3 cases): 持久化机制, 缓存穿透, 哨兵模式
- Vue (2 cases): 组件生命周期, 路由守卫
- 算法 (3 cases): 动态规划, 贪心算法, 时间复杂度分析
- 计算机组成原理 (3 cases): Cache映射, 流水线, 指令集
- 软件工程 (2 cases): UML图, 敏捷开发
- 高等数学 (2 cases): 导数, 积分
- 概率论 (2 cases): 贝叶斯, 期望方差

Each case follows the existing format with `id`, `query`, `category`, `difficulty`, `expected_keywords`, `ground_truth_source`, `expected_sources`, `notes`.

- [ ] **Step 2: Add retrieval confidence metric to evaluate.py**

Add to `evaluate_single_query`:
```python
# Compute retrieval confidence
confidence = 0.0
if len(results) >= 2:
    scores = [abs(r.get("distance", 0.0)) for r in results[:5]]
    top1 = scores[0]
    avg_rest = sum(scores[1:]) / len(scores[1:]) if len(scores) > 1 else top1
    confidence = top1 / avg_rest if avg_rest > 0 else 0.0
result["retrieval_confidence"] = confidence
```

Add to `compute_aggregate_metrics`:
```python
confidences = [r.get("retrieval_confidence", 0.0) for r in results if r.get("retrieval_confidence")]
aggregate["mean_confidence"] = sum(confidences) / len(confidences) if confidences else 0.0
aggregate["low_confidence_rate"] = sum(1 for c in confidences if c < 1.4) / len(confidences) if confidences else 0.0
```

- [ ] **Step 3: Run full eval**

Run: `cd server && uv run python eval/knowledge_retrieval/evaluate.py`
Expected: Results for all courses, with new confidence metrics

- [ ] **Step 4: Commit**

```bash
git add server/eval/knowledge_retrieval/test_cases.json server/eval/knowledge_retrieval/evaluate.py
git commit -m "feat: expand eval test cases to all courses and add confidence metrics"
```

---

## Task 9: RRF Parameter Sweep

**Files:**
- Create: `server/eval/knowledge_retrieval/sweep_rrf.py`

- [ ] **Step 1: Write RRF sweep script**

Create `server/eval/knowledge_retrieval/sweep_rrf.py`:

```python
"""Sweep RRF constant k to find optimal value for this corpus."""

import sys
from pathlib import Path

# Add server dir to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.tools.knowledge import (
    retrieve_dense_knowledge,
    retrieve_sparse_knowledge,
    merge_ranked_results,
    route_query_sources,
    _rrf_score,
)
from eval.knowledge_retrieval.evaluate import load_test_cases, check_keyword_hits

K_VALUES = [10, 20, 30, 40, 60, 100]


def sweep():
    test_cases = load_test_cases()
    print(f"Testing {len(test_cases)} cases with k ∈ {K_VALUES}\n")

    for k in K_VALUES:
        hits = 0
        total_keywords = 0
        matched_keywords = 0

        for case in test_cases:
            query = case["query"]
            route = route_query_sources(query, course_name=case.get("ground_truth_source"))
            dense = retrieve_dense_knowledge(route.query, top_k=8, source_filter=route.source_filter)
            sparse = retrieve_sparse_knowledge(route.query, top_k=8, source_filter=route.source_filter)

            # Manually merge with this k value
            merged_scores: dict = {}
            for rows in (dense, sparse):
                for item in rows:
                    from app.chat.tools.knowledge import _metadata_key
                    key = _metadata_key(item.get("metadata", {}))
                    score = 1.0 / (k + int(item.get("rank", 0)))
                    if key in merged_scores:
                        merged_scores[key]["score"] += score
                    else:
                        merged_scores[key] = {"item": item, "score": score}

            ordered = sorted(merged_scores.values(), key=lambda x: -x["score"])[:4]
            result_text = " ".join(o["item"].get("text", "") for o in ordered)
            kw_hits = check_keyword_hits(result_text, case.get("expected_keywords", []))
            if kw_hits > 0:
                hits += 1
            matched_keywords += kw_hits
            total_keywords += len(case.get("expected_keywords", []))

        hit_rate = hits / len(test_cases) if test_cases else 0
        kw_rate = matched_keywords / total_keywords if total_keywords else 0
        print(f"k={k:3d}  Hit@4={hit_rate:.2f}  KeywordCoverage={kw_rate:.2f}")


if __name__ == "__main__":
    sweep()
```

- [ ] **Step 2: Run sweep**

Run: `cd server && uv run python eval/knowledge_retrieval/sweep_rrf.py`
Expected: Table of Hit@4 and keyword coverage for each k value

- [ ] **Step 3: Update config.yaml with optimal k**

Update `knowledge.retrieval.rrf_k` in `server/config.yaml` with the best k value from the sweep.

- [ ] **Step 4: Commit**

```bash
git add server/eval/knowledge_retrieval/sweep_rrf.py server/config.yaml
git commit -m "feat: add RRF parameter sweep and apply optimal k value"
```

---

## Task 10: Final Integration Test + Baseline Comparison

**Files:**
- Modify: `server/eval/knowledge_retrieval/evaluate.py`

- [ ] **Step 1: Run full eval with all optimizations**

Run: `cd server && uv run python eval/knowledge_retrieval/evaluate.py`
Expected: Improved metrics across all courses

- [ ] **Step 2: Compare with baseline**

Manually compare new metrics against baseline:
- Hit@4: 0.40 → target > 0.75
- MRR: 0.2625 → target > 0.65
- Hard query hit rate: 0.20 → target > 0.40
- Top-1 source accuracy: 0.45 → target > 0.80
- Cross-book pollution rate: 73.97% → target < 20%

- [ ] **Step 3: Run all tests**

Run: `cd server && uv run pytest tests/chat/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "feat: complete knowledge retrieval full optimization — semantic chunking, hybrid routing, retrieval-aware rewrite, RRF tuning"
```
