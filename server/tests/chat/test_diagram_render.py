"""Tests for diagram render module.

Tests the simplified Mermaid source extraction and render building.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.diagram_render import build_mermaid_render, extract_mermaid_source


class TestBuildMermaidRender:
    """Tests for build_mermaid_render function."""

    def test_build_render_with_clean_source(self) -> None:
        """Test building render from clean Mermaid source."""
        source = "flowchart TD\n    a[\"开始\"] --> b[\"结束\"]"
        render = build_mermaid_render(source)

        assert render["engine"] == "mermaid"
        assert render["format"] == "text"
        assert render["source"] == source

    def test_build_render_with_fenced_source(self) -> None:
        """Test building render from fenced Mermaid source."""
        raw = "```mermaid\nflowchart TD\n    a[\"开始\"] --> b[\"结束\"]\n```"
        render = build_mermaid_render(raw)

        assert render["engine"] == "mermaid"
        assert render["format"] == "text"
        assert render["source"] == "flowchart TD\n    a[\"开始\"] --> b[\"结束\"]"

    def test_build_render_with_sequence_diagram(self) -> None:
        """Test building render from sequence diagram."""
        source = "sequenceDiagram\n    participant A\n    A->>B: Hello"
        render = build_mermaid_render(source)

        assert render["engine"] == "mermaid"
        assert render["source"].startswith("sequenceDiagram")


class TestExtractMermaidSource:
    """Tests for extract_mermaid_source function."""

    def test_extract_clean_source(self) -> None:
        """Test extracting clean Mermaid source."""
        source = extract_mermaid_source("flowchart TD\n    a --> b")
        assert source == "flowchart TD\n    a --> b"

    def test_extract_removes_code_fence(self) -> None:
        """Test that code fences are removed."""
        source = extract_mermaid_source(
            "下面是图解：\n\n```mermaid\nflowchart TD\n    a[\"开始\"] --> b[\"结束\"]\n```\n\n请查看。"
        )
        assert source == "flowchart TD\n    a[\"开始\"] --> b[\"结束\"]"

    def test_extract_removes_mermaid_fence_without_lang(self) -> None:
        """Test that code fences without 'mermaid' lang are also handled."""
        source = extract_mermaid_source(
            "```\nflowchart TD\n    a --> b\n```"
        )
        assert source == "flowchart TD\n    a --> b"

    def test_extract_strips_leading_trailing_blank_lines(self) -> None:
        """Test that leading and trailing blank lines are stripped."""
        source = extract_mermaid_source("\n\n\nflowchart TD\n    a --> b\n\n\n")
        assert source == "flowchart TD\n    a --> b"

    def test_extract_preserves_internal_blank_lines(self) -> None:
        """Test that internal blank lines are preserved."""
        source = extract_mermaid_source("flowchart TD\n\n    a --> b\n\n    b --> c")
        assert "flowchart TD\n\n    a --> b\n\n    b --> c" in source

    def test_extract_rejects_empty_source(self) -> None:
        """Test that empty source raises ValueError."""
        with pytest.raises(ValueError, match="Mermaid 源码为空"):
            extract_mermaid_source("")

        with pytest.raises(ValueError, match="Mermaid 源码为空"):
            extract_mermaid_source("   \n\n   ")

    def test_extract_rejects_non_mermaid_text(self) -> None:
        """Test that non-Mermaid text raises ValueError."""
        with pytest.raises(ValueError, match="LLM 未返回合法 Mermaid 源码"):
            extract_mermaid_source("This is just plain text, not a diagram.")

    def test_extract_rejects_json_payload(self) -> None:
        """Test that JSON payload raises ValueError."""
        # JSON doesn't start with Mermaid keyword, so it fails that check first
        with pytest.raises(ValueError, match="LLM 未返回合法 Mermaid 源码"):
            extract_mermaid_source('{"type":"flow","spec":{"steps":[]}}')

    def test_extract_accepts_all_mermaid_diagram_types(self) -> None:
        """Test that all supported Mermaid diagram types are accepted."""
        diagram_types = [
            "flowchart TD\n    a --> b",
            "graph LR\n    a --> b",
            "sequenceDiagram\n    A->>B: Hello",
            "stateDiagram-v2\n    [*] --> Active",
            "classDiagram\n    class A",
            "erDiagram\n    USER ||--o{ ORDER",
            "block-beta\n    columns 1\n    a",
            "packet-beta\n    0-15: \"Header\"",
            "gitGraph\n    commit",
        ]
        for diagram in diagram_types:
            source = extract_mermaid_source(diagram)
            assert source.splitlines()[0].startswith(diagram.splitlines()[0].split()[0])

    def test_extract_handles_none_input(self) -> None:
        """Test that None input raises ValueError."""
        with pytest.raises(ValueError, match="Mermaid 源码为空"):
            extract_mermaid_source(None)

    def test_extract_handles_non_string_input(self) -> None:
        """Test that non-string input is converted to string."""
        # Should convert to string "123" and then reject as non-Mermaid
        with pytest.raises(ValueError):
            extract_mermaid_source(123)
