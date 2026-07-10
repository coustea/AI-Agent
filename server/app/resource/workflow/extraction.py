"""Markdown 核心内容提取工具。

替代旧的盲切片逻辑 _split_handoff_materials()，基于 Prompt 规范的结构化格式提取语义完整的内容块。

设计原则：
- 二级标题（## ）作为提取锚点
- 提取结果保持语义完整
- 配置参数驱动提取行为
"""

from __future__ import annotations

import re
from typing import Literal

from app.infra.logging import get_logger

logger = get_logger(__name__)

# Content Agent 各结构对应的二级标题序列
CONTENT_SECTION_MAP: dict[str, list[str]] = {
    "progressive": ["## 概述", "## 核心概念", "## 应用场景", "## 总结"],
    "summary_first": ["## 核心要点", "## 概念精解", "## 复习建议"],
    "exam_points": ["## 高频考点", "## 复习策略"],
    "case_driven": ["## 引入案例", "## 概念解析", "## 原理透视", "## 总结"],
}

# Code Agent 固定的二级标题序列
CODE_SECTIONS: list[str] = ["## 案例目标", "## 完整代码", "## 关键解释"]

# 提取参数默认值
DEFAULT_MAX_BLOCKS = 12
DEFAULT_BLOCK_LIMIT = 2400
DEFAULT_TOTAL_LIMIT = 12000


def extract_core_content(
    markdown: str,
    agent_id: str,
    config: dict,
    *,
    max_blocks: int = DEFAULT_MAX_BLOCKS,
    block_limit: int = DEFAULT_BLOCK_LIMIT,
    total_limit: int = DEFAULT_TOTAL_LIMIT,
) -> list[str]:
    """提取 Markdown 核心内容，替代盲切片。

    Args:
        markdown: Agent 生成的原始 Markdown
        agent_id: content / code
        config: Agent 配置参数（如 structure, depth_level, output_style）
        max_blocks: 最多返回多少块
        block_limit: 单块最大字符数
        total_limit: 总字符数上限

    Returns:
        核心内容块列表，语义完整
    """
    if not markdown or not markdown.strip():
        return []

    # 按字符数截断
    content = markdown.strip()[:total_limit]

    if agent_id == "content":
        return _extract_content_sections(content, config, max_blocks, block_limit)
    elif agent_id == "code":
        return _extract_code_sections(content, config, max_blocks, block_limit)
    else:
        # 其他 agent（mindmap, quiz, reading）回退到段落切片
        return _fallback_paragraph_split(content, max_blocks, block_limit)


def _extract_content_sections(
    markdown: str,
    config: dict,
    max_blocks: int,
    block_limit: int,
) -> list[str]:
    """Content Agent 内容提取。

    提取策略：
    - 根据 structure 参数选择对应的二级标题
    - 提取完整段落内容
    - 对概念单元（### ）提取定义+类比部分
    """
    structure = config.get("structure", "progressive")
    if structure not in CONTENT_SECTION_MAP:
        structure = "progressive"

    target_sections = CONTENT_SECTION_MAP[structure]
    blocks: list[str] = []

    # 遍历每个目标二级标题
    for section_title in target_sections:
        section_content = _extract_section(markdown, section_title)
        if not section_content:
            continue

        # 如果是"核心概念"或"概念精解"，进一步提取概念单元的定义+类比
        if section_title in ("## 核心概念", "## 概念精解", "## 高频考点"):
            concept_blocks = _extract_concept_summaries(section_content, block_limit)
            blocks.extend(concept_blocks)
        else:
            # 其他段落直接保留（可能需要截断）
            truncated = _truncate_block(section_content, block_limit)
            if truncated:
                blocks.append(truncated)

        if len(blocks) >= max_blocks:
            break

    return blocks[:max_blocks]


def _extract_code_sections(
    markdown: str,
    config: dict,
    max_blocks: int,
    block_limit: int,
) -> list[str]:
    """Code Agent 内容提取。

    提取策略：
    - 提取案例目标
    - 提取完整代码块（保持完整，不做截断）
    - 提取关键解释
    """
    blocks: list[str] = []

    # 1. 案例目标
    goal_content = _extract_section(markdown, "## 案例目标")
    if goal_content:
        truncated = _truncate_block(goal_content, block_limit)
        if truncated:
            blocks.append(truncated)

    # 2. 完整代码（提取所有代码块）
    code_blocks = _extract_code_blocks(markdown)
    for code_block in code_blocks:
        # 代码块不做截断，保持完整
        if len(blocks) < max_blocks:
            blocks.append(code_block)

    # 3. 关键解释
    explanation_content = _extract_section(markdown, "## 关键解释")
    if explanation_content and len(blocks) < max_blocks:
        truncated = _truncate_block(explanation_content, block_limit)
        if truncated:
            blocks.append(truncated)

    return blocks[:max_blocks]


def _extract_section(markdown: str, section_title: str) -> str:
    """提取指定二级标题下的完整内容。

    从 `section_title` 开始，到下一个二级标题或文档结束。

    Args:
        markdown: 完整 Markdown 文档
        section_title: 二级标题（如 "## 概述"）

    Returns:
        该段落的内容（不包含标题本身）
    """
    lines = markdown.splitlines()
    in_section = False
    section_lines: list[str] = []

    # 构建匹配模式：## 标题名（允许前后空格）
    pattern = rf"^##\s*{re.escape(section_title[3:].strip())}\s*$"

    for line in lines:
        # 检测目标段落开始
        if re.match(pattern, line.strip()):
            in_section = True
            continue

        # 已在目标段落中
        if in_section:
            # 遇到新的二级标题，段落结束
            if line.strip().startswith("## "):
                break
            section_lines.append(line)

    content = "\n".join(section_lines).strip()
    return content


def _extract_concept_summaries(markdown: str, block_limit: int) -> list[str]:
    """从概念段落中提取各概念单元的定义+类比摘要。

    识别 `### 概念名` 开头的单元，提取其定义和类比部分。

    Args:
        markdown: 概念段落的 Markdown 内容
        block_limit: 单块最大字符数

    Returns:
        概念摘要列表
    """
    blocks: list[str] = []

    # 按 ### 切分概念单元
    concept_pattern = r"^###\s+.+$"
    lines = markdown.splitlines()

    current_concept: list[str] = []
    concept_name = ""

    for line in lines:
        if re.match(concept_pattern, line.strip()):
            # 新概念单元开始，保存上一个
            if current_concept and concept_name:
                summary = _build_concept_summary(concept_name, current_concept, block_limit)
                if summary:
                    blocks.append(summary)
            # 重置
            concept_name = line.strip()[4:].strip()  # 去掉 "### "
            current_concept = []
        else:
            current_concept.append(line)

    # 处理最后一个概念
    if current_concept and concept_name:
        summary = _build_concept_summary(concept_name, current_concept, block_limit)
        if summary:
            blocks.append(summary)

    return blocks


def _build_concept_summary(name: str, lines: list[str], block_limit: int) -> str | None:
    """构建概念摘要：概念名 + 定义 + 类比。

    Args:
        name: 概念名称
        lines: 概念单元的内容行
        block_limit: 最大字符数

    Returns:
        概念摘要字符串
    """
    content = "\n".join(lines).strip()

    # 提取定义（**定义**：xxx）
    definition_match = re.search(r"\*\*定义\*\*[：:]\s*(.+?)(?=\n\n|\n\*\*|\Z)", content, re.DOTALL)
    definition = definition_match.group(1).strip() if definition_match else ""

    # 提取类比（**类比**：xxx）
    analogy_match = re.search(r"\*\*类比\*\*[：:]\s*(.+?)(?=\n\n|\n\*\*|\Z)", content, re.DOTALL)
    analogy = analogy_match.group(1).strip() if analogy_match else ""

    # 构建摘要
    parts = [f"### {name}"]
    if definition:
        parts.append(f"**定义**：{definition}")
    if analogy:
        parts.append(f"**类比**：{analogy}")

    summary = "\n\n".join(parts)
    if len(summary) > block_limit:
        summary = summary[:block_limit]

    return summary if summary.strip() else None


def _extract_code_blocks(markdown: str) -> list[str]:
    """提取所有代码块。

    Args:
        markdown: Markdown 文档

    Returns:
        代码块列表（包含围栏和语言标识）
    """
    pattern = r"```[\w]*\n.*?```"
    matches = re.findall(pattern, markdown, re.DOTALL)
    return [m.strip() for m in matches if m.strip()]


def _truncate_block(text: str, limit: int) -> str | None:
    """截断内容块到指定长度，尝试在句子边界截断。

    Args:
        text: 原始文本
        limit: 最大字符数

    Returns:
        截断后的文本，如果为空返回 None
    """
    if not text:
        return None

    if len(text) <= limit:
        return text

    # 尝试在句子边界截断
    truncated = text[:limit]
    last_period = max(
        truncated.rfind("。"),
        truncated.rfind("."),
        truncated.rfind("！"),
        truncated.rfind("？"),
    )

    if last_period > limit * 0.7:
        truncated = truncated[: last_period + 1]

    return truncated.strip() if truncated.strip() else None


def _fallback_paragraph_split(
    markdown: str,
    max_blocks: int,
    block_limit: int,
) -> list[str]:
    """回退方案：按段落切片（用于 mindmap/quiz/reading 等 Agent）。

    Args:
        markdown: Markdown 内容
        max_blocks: 最大块数
        block_limit: 单块最大字符数

    Returns:
        内容块列表
    """
    chunks: list[str] = []
    current = ""

    for paragraph in markdown.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > block_limit:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks[:max_blocks]


__all__ = [
    "extract_core_content",
    "CONTENT_SECTION_MAP",
    "CODE_SECTIONS",
]