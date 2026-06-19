"""Tests for markdown_splitter — semantic Markdown chunking."""

from langchain_core.documents import Document

from markdown_splitter import (
    MarkdownSplitter,
    _extract_code_blocks,
    _protect_tables_and_code,
)


# ---------------------------------------------------------------------------
# TestProtectCodeBlocksAndTables
# ---------------------------------------------------------------------------

class TestProtectCodeBlocksAndTables:
    """Code blocks and tables must never be split across chunks."""

    def test_code_block_not_split(self):
        text = "前导文字\n```python\nprint('hello')\n```\n后续文字"
        segments = _protect_tables_and_code(text)
        code_segs = [s for s in segments if s.type == "code"]
        assert len(code_segs) == 1
        assert "print('hello')" in code_segs[0].text
        assert code_segs[0].text.count("```") == 2  # opening + closing

    def test_table_not_split(self):
        text = "说明文字\n| A | B |\n|---|---|\n| 1 | 2 |\n更多文字"
        segments = _protect_tables_and_code(text)
        table_segs = [s for s in segments if s.type == "table"]
        assert len(table_segs) == 1
        assert "| A | B |" in table_segs[0].text
        assert "| 1 | 2 |" in table_segs[0].text

    def test_multiple_code_blocks(self):
        text = (
            "第一段\n```js\nconsole.log(1)\n```\n中间\n"
            "```js\nconsole.log(2)\n```"
        )
        segments = _protect_tables_and_code(text)
        code_segs = [s for s in segments if s.type == "code"]
        assert len(code_segs) == 2

    def test_plain_text_passthrough(self):
        text = "这是普通文本，没有代码块也没有表格。"
        segments = _protect_tables_and_code(text)
        assert len(segments) == 1
        assert segments[0].type == "text"
        assert segments[0].text == text


# ---------------------------------------------------------------------------
# TestSplitByHeadings
# ---------------------------------------------------------------------------

class TestSplitByHeadings:
    """Heading-based splitting behaviour."""

    def test_splits_on_h2(self):
        splitter = MarkdownSplitter()
        text = (
            "## 第一节\n"
            + "这是第一节的内容，" * 20
            + "\n## 第二节\n"
            + "这是第二节的内容，" * 20
        )
        docs = splitter.split_text(text)
        assert len(docs) >= 2
        # Each chunk should mention its heading.
        bodies = [d.page_content for d in docs]
        assert any("第一节" in b for b in bodies)
        assert any("第二节" in b for b in bodies)

    def test_preserves_heading_in_chunk(self):
        splitter = MarkdownSplitter()
        text = "## 算法基础\n排序算法是计算机科学的基础。"
        docs = splitter.split_text(text)
        assert len(docs) >= 1
        assert "算法基础" in docs[0].page_content

    def test_empty_input(self):
        splitter = MarkdownSplitter()
        docs = splitter.split_text("")
        assert docs == []


# ---------------------------------------------------------------------------
# TestMergeOrphanChunks
# ---------------------------------------------------------------------------

class TestMergeOrphanChunks:
    """Short (orphan) chunks are merged backward."""

    def test_short_chunk_merged_with_previous(self):
        splitter = MarkdownSplitter(min_size=100)
        # The short trailing text should be merged into the first chunk.
        text = (
            "## 导论\n"
            + "这是一段很长的正文内容，" * 30
            + "\n## 尾巴\n短"
        )
        docs = splitter.split_text(text)
        # The "短" orphan should be merged, so we should not have a chunk
        # whose body is just "短" or close to it.
        for doc in docs:
            assert len(doc.page_content.strip()) > 1 or len(docs) == 1

    def test_no_merge_when_all_above_min(self):
        splitter = MarkdownSplitter(min_size=5)
        text = "## 第一节\n这是一段足够长的内容，超过了最小阈值。\n## 第二节\n这也是一段足够长的内容。"
        docs = splitter.split_text(text)
        assert len(docs) >= 2

    def test_merged_chunk_exceeds_max_but_no_resplit(self):
        splitter = MarkdownSplitter(max_size=200, min_size=10)
        # Create a scenario: a large chunk followed by a small orphan.
        # After merging the orphan, the combined text may exceed max_size,
        # but it must NOT be re-split.
        text = (
            "## 大段\n"
            + "内容" * 60  # ~120 chars
            + "\n## 孤儿\n短文本"
        )
        docs = splitter.split_text(text)
        # No chunk should be re-split just because of the merge.
        # Verify that no chunk contains only "短文本" in isolation.
        standalone_orphan = any(
            doc.page_content.strip().endswith("短文本")
            and len(doc.page_content) < 30
            for doc in docs
        )
        # The orphan was merged, so there should be no tiny standalone chunk.
        assert not standalone_orphan


# ---------------------------------------------------------------------------
# TestPrependContextToStandaloneBlocks
# ---------------------------------------------------------------------------

class TestPrependContextToStandaloneBlocks:
    """Standalone code/table chunks get preceding text prepended."""

    def test_code_block_gets_preceding_text(self):
        splitter = MarkdownSplitter(heading_in_body=False)
        # Oversized code block to trigger standalone.
        code_body = "x = 1\n" * 200  # well over max_size
        text = f"这是一段前言说明。\n```python\n{code_body}```"
        docs = splitter.split_text(text)
        standalone = [d for d in docs if d.metadata.get("is_standalone_block")]
        assert len(standalone) >= 1
        # The standalone chunk should have the preceding paragraph prepended.
        assert "前言说明" in standalone[0].page_content

    def test_non_standalone_unchanged(self):
        splitter = MarkdownSplitter(heading_in_body=False)
        text = "## 简介\n这是普通文字。"
        docs = splitter.split_text(text)
        for doc in docs:
            assert not doc.metadata.get("is_standalone_block", False)


# ---------------------------------------------------------------------------
# TestMarkdownMarkdownSplitter
# ---------------------------------------------------------------------------

class TestMarkdownMarkdownSplitter:
    """Integration tests for the full MarkdownSplitter pipeline."""

    def test_basic_split(self):
        splitter = MarkdownSplitter()
        text = (
            "## 变量\n"
            + "变量是存储数据的容器，在程序中用于保存和传递信息。" * 10
            + "\n\n## 函数\n"
            + "函数是可复用的代码块，能够封装逻辑提高复用性。" * 10
        )
        docs = splitter.split_text(text)
        assert len(docs) >= 2

    def test_heading_path_in_metadata(self):
        splitter = MarkdownSplitter()
        text = "## 数据结构\n### 栈\n栈是后进先出的数据结构。"
        docs = splitter.split_text(text)
        # At least one chunk should have a heading_path mentioning 数据结构.
        assert any("数据结构" in d.metadata.get("heading_path", "") for d in docs)

    def test_heading_in_body_format(self):
        """Heading context uses [当前章节上下文：{heading}], not `>` prefix."""
        splitter = MarkdownSplitter(heading_in_body=True)
        text = "## 操作系统\n操作系统管理硬件资源。"
        docs = splitter.split_text(text)
        assert len(docs) >= 1
        assert "[当前章节上下文：操作系统]" in docs[0].page_content
        # Must NOT use blockquote `>` prefix.
        assert ">" not in docs[0].page_content.split("[当前章节上下文")[0]

    def test_code_block_integrity(self):
        """No unmatched ``` in any chunk."""
        splitter = MarkdownSplitter()
        text = (
            "## 示例\n"
            "下面是代码示例：\n\n"
            "```python\n"
            "def hello():\n"
            "    print('hi')\n"
            "```\n\n"
            "代码解释。"
        )
        docs = splitter.split_text(text)
        for doc in docs:
            fence_count = doc.page_content.count("```")
            # Each chunk must have 0 or 2 fences (balanced).
            assert fence_count == 0 or fence_count == 2, (
                f"Unmatched fences in chunk: {doc.page_content!r}"
            )

    def test_split_documents_preserves_source_metadata(self):
        splitter = MarkdownSplitter()
        original = Document(
            page_content="## 测试\n内容",
            metadata={"source": "book.md", "custom_key": "custom_value"},
        )
        docs = splitter.split_documents([original])
        assert len(docs) >= 1
        for doc in docs:
            assert doc.metadata.get("source") == "book.md"
            assert doc.metadata.get("custom_key") == "custom_value"
