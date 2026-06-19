"""Semantic Markdown chunker that respects document structure.

Two-stage pipeline:
  Stage 1 — Split by heading hierarchy (## then ###), protecting code blocks and tables.
  Stage 2 — Backward-merge orphan chunks (< CHUNK_MIN_SIZE) into the previous chunk.
            Hard termination if merged chunk exceeds CHUNK_MAX_SIZE (no re-split).

Additional features:
  - Code block / table protection: ```...``` and |...| rows are indivisible.
  - Context prepending for standalone code/table chunks.
  - Heading path strategy: heading added as [当前章节上下文：{heading}] when HEADING_IN_BODY is True.
  - Sliding window overlap between consecutive chunks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.documents import Document

import rag_config


# ---------------------------------------------------------------------------
# Internal segment type
# ---------------------------------------------------------------------------

@dataclass
class _Segment:
    """A contiguous piece of markdown produced during Stage 1 splitting."""

    type: str  # "text" | "code" | "table"
    text: str
    heading_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)


def _extract_code_blocks(text: str) -> list[_Segment]:
    """Split *text* into alternating text/code segments, preserving fences."""
    segments: list[_Segment] = []
    parts = _CODE_FENCE_RE.split(text)
    # parts[0] is before the first ```, parts[1] is the language tag + code
    # inside the first code block, parts[2] is text between blocks, etc.
    inside_code = False
    for part in parts:
        if not inside_code:
            # This is regular text (or the very first piece).
            if part:
                segments.append(_Segment(type="text", text=part))
            inside_code = True
        else:
            # This is inside a code block — reattach the ``` delimiters.
            code_body = "```" + part
            # The closing ``` is consumed by the next split; find it.
            # Because we split on ^```, *part* contains everything up to the
            # next ``` (or end of text).  We need to check whether this block
            # is closed.
            if code_body.rstrip().endswith("```"):
                # Already closed — the trailing ``` is part of *part*.
                segments.append(_Segment(type="code", text=code_body))
            else:
                # Unclosed code block — add a closing fence and treat as code.
                segments.append(_Segment(type="code", text=code_body + "\n```"))
            inside_code = False
    return segments


def _is_table_row(line: str) -> bool:
    """Return True if *line* looks like a Markdown table row."""
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _protect_tables_and_code(text: str) -> list[_Segment]:
    """Split *text* into segments where code blocks and tables are atomic.

    Code blocks (```...```) are identified first and extracted as indivisible
    ``_Segment(type="code")`` entries.  Within the remaining text spans, runs
    of consecutive table rows (``|...|``) are grouped into
    ``_Segment(type="table")`` entries.  Everything else is ``type="text"``.
    """
    # Step 1: extract code blocks.
    after_code = _extract_code_blocks(text)

    # Step 2: within each text segment, group table rows.
    result: list[_Segment] = []
    for seg in after_code:
        if seg.type != "text":
            result.append(seg)
            continue

        lines = seg.text.split("\n")
        buf: list[str] = []
        in_table = False

        def flush_buf(buf_type: str) -> None:
            if buf:
                result.append(_Segment(type=buf_type, text="\n".join(buf)))
                buf.clear()

        for line in lines:
            if _is_table_row(line):
                if not in_table:
                    flush_buf("text")
                    in_table = True
                buf.append(line)
            else:
                if in_table:
                    flush_buf("table")
                    in_table = False
                buf.append(line)

        # Flush remaining buffer.
        flush_buf("table" if in_table else "text")

    return result


def _split_heading_line(line: str, heading_prefix: str) -> str | None:
    """Return the heading title if *line* is a heading of the given level."""
    # Must start with the prefix followed by a space (or end-of-line).
    if line.startswith(heading_prefix):
        rest = line[len(heading_prefix):]
        if not rest or rest[0] == " ":
            return rest.strip()
    return None


# ---------------------------------------------------------------------------
# Stage 1 — Heading-based split
# ---------------------------------------------------------------------------

def _split_by_headings(
    segments: list[_Segment],
    heading_prefix: str,
) -> list[_Segment]:
    """Split segments at lines that match *heading_prefix*.

    Each heading opens a new group.  The heading text is recorded in
    ``heading_path`` and propagated to children.
    """
    result: list[_Segment] = []
    # Inherit heading_path from the first segment so that a second pass
    # (e.g. splitting on ### after ##) does not reset it to empty.
    current_heading = segments[0].heading_path if segments else ""

    for seg in segments:
        if seg.type != "text":
            # Code / table segments: keep existing heading_path if set,
            # otherwise inherit current_heading.
            if not seg.heading_path:
                seg.heading_path = current_heading
            result.append(seg)
            # Update current_heading so subsequent segments inherit it.
            if seg.heading_path:
                current_heading = seg.heading_path
            continue

        lines = seg.text.split("\n")
        buf: list[str] = []

        def flush() -> None:
            if buf:
                body = "\n".join(buf).strip()
                if body:
                    result.append(_Segment(
                        type="text",
                        text=body,
                        heading_path=current_heading,
                    ))
                buf.clear()

        for line in lines:
            title = _split_heading_line(line.strip(), heading_prefix)
            if title is not None:
                flush()
                # Build hierarchical heading path.
                if current_heading:
                    current_heading = f"{current_heading} > {title}"
                else:
                    current_heading = title
                # Include the heading line itself in the new chunk.
                buf.append(line)
            else:
                buf.append(line)

        flush()

    return result


# ---------------------------------------------------------------------------
# Stage 2 — Merge orphan chunks
# ---------------------------------------------------------------------------

def _merge_orphans(segments: list[_Segment], min_size: int, max_size: int) -> list[_Segment]:
    """Backward-merge short segments into the previous one.

    If the merged result would exceed *max_size*, we still merge but
    do **not** re-split — this is the hard-termination rule.
    """
    if not segments:
        return []

    merged: list[_Segment] = [segments[0]]

    for seg in segments[1:]:
        prev = merged[-1]
        if len(seg.text.strip()) < min_size and prev.type == "text":
            # Merge into previous.
            combined = prev.text.rstrip("\n") + "\n\n" + seg.text.strip()
            prev.text = combined
            # If the orphan had a different heading, keep the parent's path.
        else:
            merged.append(seg)

    return merged


# ---------------------------------------------------------------------------
# Context prepending for standalone blocks
# ---------------------------------------------------------------------------

def _prepend_context(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepend 1-2 preceding paragraphs to standalone code/table chunks."""
    for i, chunk in enumerate(chunks):
        if not chunk.get("is_standalone_block"):
            continue
        # Gather preceding text paragraphs.
        context_parts: list[str] = []
        for j in range(i - 1, -1, -1):
            prev = chunks[j]
            if prev.get("is_standalone_block"):
                break
            text = prev.get("body", "")
            # Take up to 2 paragraphs.
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in reversed(paras):
                context_parts.insert(0, p)
                if len(context_parts) >= 2:
                    break
            if len(context_parts) >= 2:
                break
        if context_parts:
            prefix = "\n\n".join(context_parts) + "\n\n"
            chunk["body"] = prefix + chunk["body"]
    return chunks


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------

def _apply_overlap(chunks: list[dict[str, Any]], overlap: int) -> list[dict[str, Any]]:
    """Prepend *overlap* characters from the tail of the previous chunk."""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    for i in range(1, len(chunks)):
        prev_body = chunks[i - 1]["body"]
        tail = prev_body[-overlap:] if len(prev_body) > overlap else prev_body
        chunks[i]["body"] = tail + "\n" + chunks[i]["body"]

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class MarkdownSplitter:
    """Semantic Markdown chunker with heading-aware splitting."""

    def __init__(
        self,
        max_size: int = rag_config.CHUNK_MAX_SIZE,
        min_size: int = rag_config.CHUNK_MIN_SIZE,
        overlap: int = rag_config.CHUNK_OVERLAP,
        heading_in_body: bool = rag_config.HEADING_IN_BODY,
        primary_heading: str = rag_config.PRIMARY_SPLIT_HEADING,
        secondary_heading: str = rag_config.SECONDARY_SPLIT_HEADING,
    ) -> None:
        self.max_size = max_size
        self.min_size = min_size
        self.overlap = overlap
        self.heading_in_body = heading_in_body
        self.primary_heading = primary_heading
        self.secondary_heading = secondary_heading

    # ---- internal pipeline ------------------------------------------------

    def _segments_to_chunks(self, segments: list[_Segment], source: str) -> list[dict[str, Any]]:
        """Convert segments to intermediate chunk dicts, splitting oversized text."""
        chunks: list[dict[str, Any]] = []
        idx = 0

        for seg in segments:
            is_standalone = seg.type in ("code", "table")
            text = seg.text.strip()
            if not text:
                continue

            if is_standalone and len(text) > self.max_size:
                # Oversized code/table becomes a standalone chunk.
                chunks.append({
                    "body": text,
                    "is_standalone_block": True,
                    "heading_path": seg.heading_path,
                    "chunk_index": idx,
                })
                idx += 1
            elif is_standalone:
                # Fits within limit — still mark as standalone for context prepending.
                chunks.append({
                    "body": text,
                    "is_standalone_block": True,
                    "heading_path": seg.heading_path,
                    "chunk_index": idx,
                })
                idx += 1
            else:
                # Regular text — may need to split if oversized.
                parts = self._split_oversized_text(text, seg.heading_path)
                for part_body, part_heading in parts:
                    chunks.append({
                        "body": part_body,
                        "is_standalone_block": False,
                        "heading_path": part_heading,
                        "chunk_index": idx,
                    })
                    idx += 1

        return chunks

    def _split_oversized_text(self, text: str, heading_path: str) -> list[tuple[str, str]]:
        """Split an oversized text segment at paragraph boundaries."""
        if len(text) <= self.max_size:
            return [(text, heading_path)]

        parts: list[tuple[str, str]] = []
        paragraphs = text.split("\n\n")
        buf = ""

        for para in paragraphs:
            candidate = (buf + "\n\n" + para).strip() if buf else para.strip()
            if len(candidate) > self.max_size and buf:
                parts.append((buf.strip(), heading_path))
                buf = para
            else:
                buf = candidate

        if buf.strip():
            parts.append((buf.strip(), heading_path))

        return parts

    def _build_heading_path(self, heading: str) -> str:
        """Format the heading context string."""
        if self.heading_in_body and heading:
            return f"[当前章节上下文：{heading}]"
        return ""

    # ---- public methods ---------------------------------------------------

    def split_text(self, text: str, source: str = "") -> list[Document]:
        """Split *text* into semantically-aware ``Document`` chunks."""
        if not text or not text.strip():
            return []

        # Stage 1a: protect code blocks and tables.
        segments = _protect_tables_and_code(text)

        # Stage 1b: split by primary heading (##).
        segments = _split_by_headings(segments, self.primary_heading)

        # Stage 1c: split by secondary heading (###).
        segments = _split_by_headings(segments, self.secondary_heading)

        # Stage 2: merge orphan chunks.
        segments = _merge_orphans(segments, self.min_size, self.max_size)

        # Convert segments to intermediate chunks.
        chunks = self._segments_to_chunks(segments, source)

        # Prepend context to standalone blocks.
        chunks = _prepend_context(chunks)

        # Apply sliding-window overlap.
        chunks = _apply_overlap(chunks, self.overlap)

        # Build final Document objects.
        documents: list[Document] = []
        for chunk in chunks:
            heading = chunk.get("heading_path", "")
            body = chunk["body"]

            # Prepend heading context into body.
            heading_prefix = self._build_heading_path(heading)
            if heading_prefix:
                body = heading_prefix + "\n" + body

            # Determine section_title and parent_section from heading_path.
            section_title = heading
            parent_section = ""
            if ">" in heading:
                parts = heading.split(">")
                section_title = parts[-1].strip()
                parent_section = ">".join(parts[:-1]).strip()

            metadata: dict[str, Any] = {
                "chunk_index": chunk.get("chunk_index", 0),
                "heading_path": heading,
                "section_title": section_title,
                "parent_section": parent_section,
            }
            if source:
                metadata["source"] = source
            if chunk.get("is_standalone_block"):
                metadata["is_standalone_block"] = True

            documents.append(Document(page_content=body, metadata=metadata))

        # Re-index chunks sequentially.
        for i, doc in enumerate(documents):
            doc.metadata["chunk_index"] = i

        return documents

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split a list of ``Document`` objects, preserving source metadata."""
        result: list[Document] = []
        for doc in documents:
            source = doc.metadata.get("source", "")
            chunks = self.split_text(doc.page_content, source=source)
            # Merge original metadata (source metadata takes precedence for
            # keys that already existed on the original document).
            for chunk in chunks:
                for key, value in doc.metadata.items():
                    if key not in chunk.metadata:
                        chunk.metadata[key] = value
            result.extend(chunks)
        return result
