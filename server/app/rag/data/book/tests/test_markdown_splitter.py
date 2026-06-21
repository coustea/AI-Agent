"""Tests for markdown_splitter semantic chunking."""

from langchain_core.documents import Document

from markdown_splitter import MarkdownSplitter, _protect_tables_and_code


class TestProtectCodeBlocksAndTables:
    def test_code_block_not_split(self):
        text = "Intro\n```python\nprint('hello')\n```\nOutro"
        segments = _protect_tables_and_code(text)
        code_segments = [segment for segment in segments if segment.type == "code"]
        assert len(code_segments) == 1
        assert "print('hello')" in code_segments[0].text
        assert code_segments[0].text.count("```") == 2

    def test_table_not_split(self):
        text = "Before\n| A | B |\n|---|---|\n| 1 | 2 |\nAfter"
        segments = _protect_tables_and_code(text)
        table_segments = [segment for segment in segments if segment.type == "table"]
        assert len(table_segments) == 1
        assert "| A | B |" in table_segments[0].text
        assert "| 1 | 2 |" in table_segments[0].text


class TestMarkdownSplitter:
    def test_basic_split(self):
        splitter = MarkdownSplitter()
        text = (
            "## Variables\n"
            + "Variables store values used during program execution. " * 10
            + "\n\n## Functions\n"
            + "Functions package reusable program logic. " * 10
        )
        docs = splitter.split_text(text)
        assert len(docs) >= 2

    def test_heading_path_in_metadata(self):
        splitter = MarkdownSplitter()
        text = "## Data Structures\n### Stack\nA stack is a LIFO data structure."
        docs = splitter.split_text(text)
        assert any("Data Structures" in doc.metadata.get("heading_path", "") for doc in docs)

    def test_heading_in_body_format(self):
        splitter = MarkdownSplitter(heading_in_body=True, overlap=0)
        text = "## Operating System\nOperating systems manage hardware resources."
        docs = splitter.split_text(text)
        assert len(docs) >= 1
        assert "[当前章节上下文：Operating System]" in docs[0].page_content

    def test_code_block_integrity(self):
        splitter = MarkdownSplitter()
        text = (
            "## Example\n"
            "Code sample below.\n\n"
            "```python\n"
            "def hello():\n"
            "    print('hi')\n"
            "```\n\n"
            "Explanation."
        )
        docs = splitter.split_text(text)
        for doc in docs:
            fence_count = doc.page_content.count("```")
            assert fence_count in (0, 2)

    def test_split_documents_preserves_source_metadata(self):
        splitter = MarkdownSplitter()
        original = Document(
            page_content="## Test\nContent",
            metadata={"source": "book.md", "custom_key": "custom_value"},
        )
        docs = splitter.split_documents([original])
        assert len(docs) >= 1
        for doc in docs:
            assert doc.metadata.get("source") == "book.md"
            assert doc.metadata.get("custom_key") == "custom_value"

    def test_sibling_headings_do_not_chain_together(self):
        splitter = MarkdownSplitter(heading_in_body=False, overlap=0)
        text = (
            "## Chapter 3 Java Basics\n"
            + ("Intro paragraph. " * 10)
            + "\n\n"
            "### 3.1 Main Class Structure\n"
            + ("This section explains the main class structure. " * 8)
            + "\n\n### 3.2 Primitive Types\n"
            + ("This section explains primitive types. " * 8)
            + "\n\n### 3.3 Variables and Constants\n"
            + ("This section explains variables and constants. " * 8)
        )
        docs = splitter.split_text(text)
        heading_paths = [doc.metadata.get("heading_path", "") for doc in docs]

        assert any("3.1 Main Class Structure" in item for item in heading_paths)
        assert any("3.2 Primitive Types" in item for item in heading_paths)
        assert any("3.3 Variables and Constants" in item for item in heading_paths)
        assert not any(
            "3.1 Main Class Structure > 3.2 Primitive Types" in item
            or "3.2 Primitive Types > 3.3 Variables and Constants" in item
            for item in heading_paths
        )


def test_split_text_sets_section_title_and_parent_section():
    splitter = MarkdownSplitter(heading_in_body=False, overlap=0, min_size=10)
    docs = splitter.split_text(
        "## 第三章 进程管理\n\n### 3.2 进程调度\n调度负责选择下一个运行进程。",
        source="os.final.md",
    )

    assert any(doc.metadata.get("heading_path") == "第三章 进程管理 > 3.2 进程调度" for doc in docs)
    assert any(doc.metadata.get("section_title") == "3.2 进程调度" for doc in docs)
    assert any(doc.metadata.get("parent_section") == "第三章 进程管理" for doc in docs)
    assert all(doc.metadata.get("source") == "os.final.md" for doc in docs)
