"""Semantic Markdown chunker that respects document structure."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.documents import Document

# Import from the new config module
from app.rag import config as rag_config


@dataclass
class _Segment:
    type: str
    text: str
    heading_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _HeadingMatch:
    level: int
    title: str
    chapter_title: str = ""
    section_title: str = ""
    subsection_title: str = ""
    chapter_no: str = ""
    section_no: str = ""
    subsection_no: str = ""


_CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)
_TEXTBOOK_CHAPTER_RE = re.compile(r"^第\s*([0-9一二三四五六七八九十百零]+)\s*章\s+(.+)$")
_TEXTBOOK_SECTION_RE = re.compile(r"^第\s*([0-9一二三四五六七八九十百零]+)\s*节\s+(.+)$")
_TEXTBOOK_DECIMAL_RE = re.compile(r"^(\d+(?:\.\d+){0,2})\s+(.+)$")


def _extract_code_blocks(text: str) -> list[_Segment]:
    segments: list[_Segment] = []
    parts = _CODE_FENCE_RE.split(text)
    inside_code = False
    for part in parts:
        if not inside_code:
            if part:
                segments.append(_Segment(type="text", text=part))
            inside_code = True
        else:
            code_body = "```" + part
            if code_body.rstrip().endswith("```"):
                segments.append(_Segment(type="code", text=code_body))
            else:
                segments.append(_Segment(type="code", text=code_body + "\n```"))
            inside_code = False
    return segments


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _protect_tables_and_code(text: str) -> list[_Segment]:
    after_code = _extract_code_blocks(text)
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

        flush_buf("table" if in_table else "text")

    return result


def _build_heading_match(level: int, title: str) -> _HeadingMatch:
    title = title.strip()
    chapter_match = _TEXTBOOK_CHAPTER_RE.match(title)
    if chapter_match:
        return _HeadingMatch(
            level=1,
            title=title,
            chapter_title=title,
            chapter_no=chapter_match.group(1),
        )

    section_match = _TEXTBOOK_SECTION_RE.match(title)
    if section_match:
        return _HeadingMatch(
            level=2,
            title=title,
            section_title=title,
        )

    decimal_match = _TEXTBOOK_DECIMAL_RE.match(title)
    if decimal_match:
        number = decimal_match.group(1)
        parts = number.split(".")
        if len(parts) == 1:
            return _HeadingMatch(level=1, title=title, chapter_title=title, chapter_no=parts[0])
        if len(parts) == 2:
            return _HeadingMatch(
                level=2,
                title=title,
                section_title=title,
                chapter_no=parts[0],
                section_no=number,
            )
        return _HeadingMatch(
            level=3,
            title=title,
            subsection_title=title,
            chapter_no=parts[0],
            section_no=".".join(parts[:2]),
            subsection_no=number,
        )

    return _HeadingMatch(level=level, title=title)


def _parse_hash_heading(line: str, heading_prefix: str) -> _HeadingMatch | None:
    if not line.startswith(heading_prefix):
        return None
    rest = line[len(heading_prefix) :]
    if rest and rest[0] != " ":
        return None
    title = rest.strip()
    if not title:
        return None

    # 修复：如果标题行过长（超过50字符），可能是标题和正文混在一起
    # 教材的正常章节标题通常不超过30字符（如"第3章 Java语言基础"）
    if len(title) > 50:
        # 尝试在常见分隔符处截断（空格、逗号、句号）
        for i, char in enumerate(title[:50]):
            if char in ' ，。！？.!?' and i > 15 and i < 40:
                title = title[:i].strip()
                break

        # 如果截断后还超过50，硬截断
        if len(title) > 50:
            # 只保留章节编号和前几个词
            match = re.match(r'^第\s*[0-9一二三四五六七八九十百零]+\s*章\s+', title)
            if match:
                # 保留章节编号 + 前几个词
                chapter_part = match.group(0)
                rest_words = title[len(chapter_part):].split()[:5]
                title = chapter_part + ' '.join(rest_words)
            else:
                # 没有章节编号，取前30字符
                title = title[:30]

    level = heading_prefix.count("#")
    return _build_heading_match(level, title)


def _parse_textbook_heading(line: str) -> _HeadingMatch | None:
    stripped = line.strip()
    if not stripped:
        return None
    if _TEXTBOOK_CHAPTER_RE.match(stripped) or _TEXTBOOK_SECTION_RE.match(stripped) or _TEXTBOOK_DECIMAL_RE.match(stripped):
        return _build_heading_match(2, stripped)
    return None


def _join_heading_parts(parts: list[str]) -> str:
    return " > ".join(part for part in parts if part)


def _split_by_headings(segments: list[_Segment], heading_prefix: str) -> list[_Segment]:
    result: list[_Segment] = []

    for seg in segments:
        heading_parts = [part.strip() for part in seg.heading_path.split(">") if part.strip()]
        current_heading = seg.heading_path
        current_meta = dict(seg.metadata or {})

        if seg.type != "text":
            result.append(seg)
            continue

        lines = seg.text.split("\n")
        buf: list[str] = []

        def flush() -> None:
            if not buf:
                return
            body = "\n".join(buf).strip()
            if body:
                result.append(
                    _Segment(
                        type="text",
                        text=body,
                        heading_path=current_heading,
                        metadata=dict(current_meta),
                    )
                )
            buf.clear()

        for line in lines:
            stripped = line.strip()
            heading_match = _parse_hash_heading(stripped, heading_prefix)
            if heading_match is None and heading_prefix == rag_config.PRIMARY_SPLIT_HEADING:
                heading_match = _parse_textbook_heading(stripped)

            if heading_match is None:
                buf.append(line)
                continue

            flush()
            level = min(max(heading_match.level, 1), 3)
            heading_parts = heading_parts[: max(level - 1, 0)] + [heading_match.title]
            current_heading = _join_heading_parts(heading_parts)

            current_meta = dict(current_meta)
            if level == 1:
                current_meta.update(
                    {
                        "chapter_title": heading_match.chapter_title or heading_match.title,
                        "section_title": "",
                        "subsection_title": "",
                        "chapter_no": heading_match.chapter_no,
                        "section_no": "",
                        "subsection_no": "",
                    }
                )
            elif level == 2:
                current_meta.update(
                    {
                        "chapter_title": current_meta.get("chapter_title", ""),
                        "section_title": heading_match.section_title or heading_match.title,
                        "subsection_title": "",
                        "chapter_no": heading_match.chapter_no or current_meta.get("chapter_no", ""),
                        "section_no": heading_match.section_no or current_meta.get("section_no", ""),
                        "subsection_no": "",
                    }
                )
            else:
                current_meta.update(
                    {
                        "chapter_title": current_meta.get("chapter_title", ""),
                        "section_title": current_meta.get("section_title", ""),
                        "subsection_title": heading_match.subsection_title or heading_match.title,
                        "chapter_no": heading_match.chapter_no or current_meta.get("chapter_no", ""),
                        "section_no": heading_match.section_no or current_meta.get("section_no", ""),
                        "subsection_no": heading_match.subsection_no or current_meta.get("subsection_no", ""),
                    }
                )

            buf.append(line)

        flush()

    return result


def _merge_orphans(segments: list[_Segment], min_size: int, max_size: int) -> list[_Segment]:
    if not segments:
        return []

    merged: list[_Segment] = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        same_heading = prev.heading_path == seg.heading_path
        if len(seg.text.strip()) < min_size and prev.type == "text" and same_heading:
            combined = prev.text.rstrip("\n") + "\n\n" + seg.text.strip()
            if len(combined) > max_size * 1.5:
                merged.append(seg)
            else:
                prev.text = combined
        else:
            merged.append(seg)

    return merged


def _prepend_context(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, chunk in enumerate(chunks):
        if not chunk.get("is_standalone_block"):
            continue
        context_parts: list[str] = []
        for j in range(i - 1, -1, -1):
            prev = chunks[j]
            if prev.get("is_standalone_block") or prev.get("heading_path") != chunk.get("heading_path"):
                break
            paras = [p.strip() for p in str(prev.get("body", "")).split("\n\n") if p.strip()]
            for paragraph in reversed(paras):
                context_parts.insert(0, paragraph)
                if len(context_parts) >= 2:
                    break
            if len(context_parts) >= 2:
                break
        if context_parts:
            chunk["body"] = "\n\n".join(context_parts) + "\n\n" + chunk["body"]
    return chunks


def _apply_overlap(chunks: list[dict[str, Any]], overlap: int) -> list[dict[str, Any]]:
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    for i in range(1, len(chunks)):
        if chunks[i - 1].get("heading_path") != chunks[i].get("heading_path"):
            continue
        prev_body = chunks[i - 1]["body"]
        tail = prev_body[-overlap:] if len(prev_body) > overlap else prev_body
        chunks[i]["body"] = tail + "\n" + chunks[i]["body"]

    return chunks


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

    def _segments_to_chunks(self, segments: list[_Segment], source: str) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        idx = 0

        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue

            base = {
                "heading_path": seg.heading_path,
                "chapter_title": str(seg.metadata.get("chapter_title", "") or ""),
                "section_title": str(seg.metadata.get("section_title", "") or ""),
                "subsection_title": str(seg.metadata.get("subsection_title", "") or ""),
                "chapter_no": str(seg.metadata.get("chapter_no", "") or ""),
                "section_no": str(seg.metadata.get("section_no", "") or ""),
                "subsection_no": str(seg.metadata.get("subsection_no", "") or ""),
            }

            if seg.type in ("code", "table"):
                chunks.append({**base, "body": text, "is_standalone_block": True, "chunk_index": idx})
                idx += 1
                continue

            for part_body, part_heading in self._split_oversized_text(text, seg.heading_path):
                chunks.append({**base, "body": part_body, "heading_path": part_heading, "is_standalone_block": False, "chunk_index": idx})
                idx += 1

        return chunks

    def _split_oversized_text(self, text: str, heading_path: str) -> list[tuple[str, str]]:
        if len(text) <= self.max_size:
            return [(text, heading_path)]

        parts: list[tuple[str, str]] = []
        paragraphs = text.split("\n\n")
        buf = ""

        for para in paragraphs:
            candidate = (buf + "\n\n" + para).strip() if buf else para.strip()
            if len(para) > self.max_size:
                if buf:
                    parts.append((buf.strip(), heading_path))
                    buf = ""
                parts.extend(self._split_at_sentences(para, heading_path))
            elif len(candidate) > self.max_size and buf:
                parts.append((buf.strip(), heading_path))
                buf = para
            else:
                buf = candidate

        if buf.strip():
            if len(buf) > self.max_size:
                parts.extend(self._split_at_sentences(buf, heading_path))
            else:
                parts.append((buf.strip(), heading_path))

        return parts

    def _split_at_sentences(self, text: str, heading_path: str) -> list[tuple[str, str]]:
        if len(text) <= self.max_size:
            return [(text, heading_path)]

        parts: list[tuple[str, str]] = []
        sentences = re.split(r"([。！？\n.!?]+)", text)
        buf = ""

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
            candidate = (buf + sentence).strip()
            if len(candidate) > self.max_size and buf:
                parts.append((buf.strip(), heading_path))
                buf = sentence
            else:
                buf = candidate

        if len(sentences) % 2 == 1 and sentences[-1]:
            buf = (buf + sentences[-1]).strip()

        if buf.strip():
            if len(buf) > self.max_size:
                for i in range(0, len(buf), self.max_size):
                    parts.append((buf[i : i + self.max_size], heading_path))
            else:
                parts.append((buf.strip(), heading_path))

        return parts

    def _build_chunk_metadata(self, chunk: dict[str, Any], source: str) -> dict[str, Any]:
        heading = str(chunk.get("heading_path", "") or "")
        subsection_title = str(chunk.get("subsection_title", "") or "")
        section_title = str(chunk.get("section_title", "") or "")
        chapter_title = str(chunk.get("chapter_title", "") or "")

        leaf_title = subsection_title or section_title or heading
        parent_section = ""
        if ">" in heading:
            parts = [part.strip() for part in heading.split(">")]
            parent_section = " > ".join(parts[:-1])

        metadata: dict[str, Any] = {
            "chunk_index": int(chunk.get("chunk_index", 0)),
            "heading_path": heading,
            "section_title": leaf_title,
            "parent_section": parent_section,
            "chapter_title": chapter_title,
            "subsection_title": subsection_title,
            "chapter_no": str(chunk.get("chapter_no", "") or ""),
            "section_no": str(chunk.get("section_no", "") or ""),
            "subsection_no": str(chunk.get("subsection_no", "") or ""),
        }
        if source:
            metadata["source"] = source
        if chunk.get("is_standalone_block"):
            metadata["is_standalone_block"] = True
        return metadata

    def _build_heading_prefix(self, heading: str) -> str:
        if self.heading_in_body and heading:
            return f"[当前章节上下文：{heading}]"
        return ""

    def split_text(self, text: str, source: str = "") -> list[Document]:
        if not text or not text.strip():
            return []

        segments = _protect_tables_and_code(text)
        segments = _split_by_headings(segments, self.primary_heading)
        segments = _split_by_headings(segments, self.secondary_heading)
        segments = _merge_orphans(segments, self.min_size, self.max_size)

        chunks = self._segments_to_chunks(segments, source)
        chunks = _prepend_context(chunks)
        chunks = _apply_overlap(chunks, self.overlap)

        documents: list[Document] = []
        for chunk in chunks:
            body = chunk["body"]
            heading_prefix = self._build_heading_prefix(chunk.get("heading_path", ""))
            if heading_prefix:
                body = heading_prefix + "\n" + body
            documents.append(Document(page_content=body, metadata=self._build_chunk_metadata(chunk, source)))

        for i, doc in enumerate(documents):
            doc.metadata["chunk_index"] = i

        return documents

    def split_documents(self, documents: list[Document]) -> list[Document]:
        result: list[Document] = []
        for doc in documents:
            source = doc.metadata.get("source", "")
            chunks = self.split_text(doc.page_content, source=source)
            for chunk in chunks:
                for key, value in doc.metadata.items():
                    if key not in chunk.metadata:
                        chunk.metadata[key] = value
            result.extend(chunks)
        return result
