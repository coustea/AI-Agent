"""Markdown → PPTPlan 编译器。

将 LLM 输出的 Markdown 格式课件大纲编译为 PPTPlan 结构化对象，
供下游 PPTHTMLRenderer 渲染为 HTML。

设计原则：
- LLM 只需输出自然 Markdown，不要求 JSON
- 编译器负责解析、校验、补默认值
- 兼容现有 PPTHTMLRenderer，不改变渲染逻辑
"""

from __future__ import annotations

import re
from typing import Any

from app.infra.logging import get_logger
from app.shared.ppt.models import (
    AnimationKind,
    ComparisonSide,
    ContentShape,
    DensityMode,
    KeyPoint,
    MatrixCell,
    HierarchyNode,
    TimelineEvent,
    ProcessStep,
    PPTPlan,
    PPTSlide,
    PPTTemplatePreference,
    SlideRole,
    SystemNode,
)

logger = get_logger(__name__)

# ── 允许值映射 ──────────────────────────────────────────────────────────

VALID_ROLES: set[str] = {"cover", "section", "hook", "explain", "derive", "case", "practice", "summary", "closing"}
VALID_SHAPES: set[str] = {
    "statement", "concept", "sequence", "comparison", "system",
    "code", "formula", "quiz", "misconception", "hierarchy", "timeline", "matrix",
}
VALID_ANIMATIONS: set[str] = {"reveal", "focus", "trace", "compare", "build", "resolve"}
VALID_DENSITIES: set[str] = {"speaker_led", "reading_first"}

ROLE_ALIASES: dict[str, str] = {
    "开": "cover", "封面": "cover", "导言": "cover",
    "节": "section", "章节": "section", "分隔": "section",
    "问": "hook", "引入": "hook", "提问": "hook",
    "讲": "explain", "讲解": "explain", "概念": "explain",
    "推": "derive", "推导": "derive", "演进": "derive",
    "例": "case", "案例": "case", "实例": "case",
    "练": "practice", "练习": "practice", "测验": "practice",
    "总": "summary", "总结": "summary", "回顾": "summary",
    "结": "closing", "收束": "closing", "结尾": "closing",
}

SHAPE_ALIASES: dict[str, str] = {
    "结论": "statement", "大字报": "statement", "论点": "statement",
    "概念": "concept", "要点": "concept",
    "步骤": "sequence", "流程": "sequence", "过程": "sequence",
    "对比": "comparison", "比较": "comparison", "双栏": "comparison",
    "系统": "system", "架构": "system", "关系": "system",
    "代码": "code",
    "公式": "formula", "推导式": "formula",
    "测验": "quiz", "题目": "quiz", "答题": "quiz",
    "误区": "misconception", "纠错": "misconception",
    "层级": "hierarchy", "树形": "hierarchy", "层次": "hierarchy",
    "时间线": "timeline", "时序": "timeline",
    "矩阵": "matrix", "表格": "matrix",
}

ANIMATION_ALIASES: dict[str, str] = {
    "出现": "reveal", "淡入": "reveal",
    "聚焦": "focus", "强调": "focus",
    "追踪": "trace", "跟踪": "trace",
    "对比": "compare",
    "构建": "build", "逐步": "build",
    "揭晓": "resolve", "揭示": "resolve",
}


# ── 辅助函数 ────────────────────────────────────────────────────────────

def _normalize_enum(raw: str, valid: set[str], aliases: dict[str, str]) -> str:
    """将中文别名或英文值规范化为合法枚举值。"""
    s = raw.strip().lower()
    if s in valid:
        return s
    if s in aliases:
        return aliases[s]
    # 模糊匹配：别名 key 包含
    for key, value in aliases.items():
        if key in s or s in key:
            return value
    return ""


def _clamp_text(text: str, max_len: int) -> str:
    return text.strip()[:max_len]


# ── Slide 块解析 ────────────────────────────────────────────────────────

# 匹配 --- 分隔的幻灯片块
_SLIDE_SPLIT = re.compile(r"\n{0,2}^---\s*$", re.MULTILINE)

# 匹配第一行元数据: ## [role|shape|animation] 标题
_META_LINE = re.compile(
    r"^##\s+"                        # ## 开头
    r"(?:\[([^\]]*)\]\s*)?"          # 可选 [role|shape|animation]
    r"(.+?)$"                        # 标题
    , re.MULTILINE
)

# 匹配行内元数据: > role=explain shape=concept animation=reveal
_INLINE_META = re.compile(r">\s*(.+)$", re.MULTILINE)


def _parse_slide_block(block: str, index: int) -> PPTSlide | None:
    """解析单个 Markdown 幻灯片块为 PPTSlide。"""
    block = block.strip()
    if not block:
        return None

    # ── 提取元数据 ──
    role = ""
    shape = ""
    animation = ""
    title = ""

    # 从 ## [meta] Title 行提取
    meta_match = _META_LINE.match(block)
    if meta_match:
        meta_raw = meta_match.group(1) or ""
        title = meta_match.group(2).strip()
        # 解析 [role|shape|animation] 或 [role/shape/animation]
        if meta_raw:
            parts = re.split(r"[|/]", meta_raw)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if not role and _normalize_enum(part, VALID_ROLES, ROLE_ALIASES):
                    role = _normalize_enum(part, VALID_ROLES, ROLE_ALIASES)
                elif not shape and _normalize_enum(part, VALID_SHAPES, SHAPE_ALIASES):
                    shape = _normalize_enum(part, VALID_SHAPES, SHAPE_ALIASES)
                elif not animation and _normalize_enum(part, VALID_ANIMATIONS, ANIMATION_ALIASES):
                    animation = _normalize_enum(part, VALID_ANIMATIONS, ANIMATION_ALIASES)

    # 从 > 行内元数据提取（覆盖或补充）
    for m in _INLINE_META.finditer(block):
        line = m.group(1)
        for kv in re.findall(r"(\w+)=([^\s,]+)", line):
            k, v = kv[0].lower(), kv[1]
            if k == "role" and not role:
                role = _normalize_enum(v, VALID_ROLES, ROLE_ALIASES)
            elif k == "shape" and not shape:
                shape = _normalize_enum(v, VALID_SHAPES, SHAPE_ALIASES)
            elif k in ("animation", "anim") and not animation:
                animation = _normalize_enum(v, VALID_ANIMATIONS, ANIMATION_ALIASES)

    # 如果没有 ## 标题行，取第一行非空非元数据行作为标题
    if not title:
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            if line.startswith("#"):
                title = re.sub(r"^#+\s*", "", line).strip()
                break
            title = line
            break

    # ── 去除元数据行，取内容区 ──
    content_lines = []
    for line in block.splitlines():
        stripped = line.strip()
        # 跳过 ## 标题行
        if stripped.startswith("## ") and meta_match and stripped == meta_match.group(0).strip():
            continue
        # 跳过 > 元数据行
        if stripped.startswith(">") and any(
            f"{k}=" in stripped for k in ("role", "shape", "animation", "anim")
        ):
            continue
        content_lines.append(line)
    content = "\n".join(content_lines).strip()

    # ── 默认值推断 ──
    if not role:
        if index == 0:
            role = "cover"
        else:
            role = "explain"
    if not shape:
        shape = _infer_shape(role, content)
    if not animation:
        animation = _infer_animation(shape)

    # ── 提取结构化内容 ──
    statement = _extract_statement(content)
    takeaway = _extract_takeaway(content)
    points = _extract_points(content)
    steps = _extract_steps(content)
    code, code_language = _extract_code(content)
    formula = _extract_formula(content)
    question, answer = _extract_quiz(content)
    comparison = _extract_comparison(content)
    nodes = _extract_nodes(content)
    hierarchy = _extract_hierarchy(content)
    timeline = _extract_timeline(content)
    matrix = _extract_matrix(content)
    speaker_notes = _extract_speaker_notes(content)

    return PPTSlide(
        role=role,  # type: ignore[arg-type]
        shape=shape,  # type: ignore[arg-type]
        title=_clamp_text(title, 54),
        statement=_clamp_text(statement, 150) if statement else "",
        takeaway=_clamp_text(takeaway, 140) if takeaway else "",
        points=points[:6],
        steps=steps[:6],
        comparison=comparison[:2] if comparison else [],
        nodes=nodes[:8],
        code=code[:1800] if code else "",
        code_language=code_language or "",
        formula=formula[:160] if formula else "",
        question=question[:160] if question else "",
        answer=answer[:180] if answer else "",
        hierarchy=hierarchy[:10],
        timeline=timeline[:8],
        matrix=matrix[:20],
        animation=animation,  # type: ignore[arg-type]
        speaker_notes=speaker_notes[:500] if speaker_notes else "",
    )


# ── 内容提取函数 ────────────────────────────────────────────────────────

def _extract_statement(content: str) -> str:
    """提取 **核心论点：** 值 或 **核心论点：值** 行。"""
    for line in content.splitlines():
        line = line.strip()
        # 格式1: **核心论点：** 值（加粗只包裹标签，最常见）
        m = re.match(r"\*\*(?:核心论点|论点|statement)[:：]\*\*\s*(.+?)\*\*\s*$", line)
        if m:
            return m.group(1).strip()
        m = re.match(r"\*\*(?:核心论点|论点|statement)[:：]\*\*\s*(.+)$", line)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"\*\*\s*$", "", text).strip()
            return text
        # 格式2: **核心论点：值**（加粗包裹标签+值）
        m = re.match(r"\*\*(?:核心论点|论点|statement)[:：]\s*(.+?)\*\*\s*$", line)
        if m:
            return m.group(1).strip()
        m = re.match(r"\*\*(?:核心论点|论点|statement)[:：]\s*(.+)$", line)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"\*\*\s*$", "", text).strip()
            return text
    return ""


def _extract_takeaway(content: str) -> str:
    """提取 **总结金句：** 值 或 **总结金句：值** 行。"""
    for line in content.splitlines():
        line = line.strip()
        # 格式1: **总结金句：** 值（加粗只包裹标签，最常见）
        m = re.match(r"\*\*(?:总结金句|金句|takeaway)[:：]\*\*\s*(.+?)\*\*\s*$", line)
        if m:
            return m.group(1).strip()
        m = re.match(r"\*\*(?:总结金句|金句|takeaway)[:：]\*\*\s*(.+)$", line)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"\*\*\s*$", "", text).strip()
            return text
        # 格式2: **总结金句：值**（加粗包裹标签+值）
        m = re.match(r"\*\*(?:总结金句|金句|takeaway)[:：]\s*(.+?)\*\*\s*$", line)
        if m:
            return m.group(1).strip()
        m = re.match(r"\*\*(?:总结金句|金句|takeaway)[:：]\s*(.+)$", line)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"\*\*\s*$", "", text).strip()
            return text
    return ""


def _extract_points(content: str) -> list[KeyPoint]:
    """提取 - **标签**：detail 或 - **标签：** detail 格式的要点。"""
    points: list[KeyPoint] = []
    for line in content.splitlines():
        line = line.strip()
        # 同时接受两种写法：冒号在加粗外（**标签**：detail）
        # 或加粗内（**标签：** detail，与 slide_outline.md 模板示例一致）
        m = re.match(r"[-*]\s+\*\*(.+?)[:：]?\*\*[:：]?\s*(.+)", line)
        if m:
            label = m.group(1).strip()[:28]
            detail = m.group(2).strip()[:200]
            points.append(KeyPoint(label=label, detail=detail))
            continue
        # 也支持 - 标签：detail（无加粗）
        m = re.match(r"[-*]\s+([^*:\n]+)[:：]\s*(.+)", line)
        if m and not line.startswith("- *"):  # 避免和 comparison 混淆
            label = m.group(1).strip()[:28]
            detail = m.group(2).strip()[:200]
            if len(label) < 20:  # 短标签才当作要点
                points.append(KeyPoint(label=label, detail=detail))
    return points


def _extract_steps(content: str) -> list[ProcessStep]:
    """提取 1. **标题**：detail 或 1. **标题：** detail 格式的步骤。"""
    steps: list[ProcessStep] = []
    for line in content.splitlines():
        line = line.strip()
        # 同 _extract_points：冒号可在加粗外或加粗内
        m = re.match(r"\d+\.\s+\*\*(.+?)[:：]?\*\*[:：]?\s*(.+)", line)
        if m:
            steps.append(ProcessStep(
                title=m.group(1).strip()[:32],
                detail=m.group(2).strip()[:200],
            ))
            continue
        # 也支持 1. 标题：detail（无加粗）
        m = re.match(r"\d+\.\s+(.+?)[:：]\s*(.+)", line)
        if m:
            steps.append(ProcessStep(
                title=m.group(1).strip()[:32],
                detail=m.group(2).strip()[:200],
            ))
    return steps


def _extract_code(content: str) -> tuple[str, str]:
    """提取 ```language ... ``` 代码块。"""
    m = re.search(r"```(\w*)\n(.*?)```", content, re.DOTALL)
    if m:
        return m.group(2).strip(), m.group(1) or ""
    return "", ""


def _extract_formula(content: str) -> str:
    """提取 $$ ... $$ 或 $ ... $ 公式。"""
    # 块级公式
    m = re.search(r"\$\$\s*(.+?)\s*\$\$", content, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 行内公式（取第一个非空的）
    m = re.search(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", content)
    if m:
        return m.group(1).strip()
    # 兼容 \[ ... \]
    m = re.search(r"\\\[(.+?)\\\]", content, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _extract_quiz(content: str) -> tuple[str, str]:
    """提取 **问题** 和 **答案**。"""
    question = ""
    answer = ""
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r"\*\*(?:问题|题目|question)[:：]\s*(.+)", line)
        if m:
            question = m.group(1).strip()
            continue
        m = re.match(r"\*\*(?:答案|answer)[:：]\s*(.+)", line)
        if m:
            answer = m.group(1).strip()
    return question, answer


def _extract_comparison(content: str) -> list[ComparisonSide]:
    """提取对比内容：### 左侧标题 / ### 右侧标题 下面的列表。"""
    sides: list[ComparisonSide] = []
    current_title = ""
    current_points: list[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        # 检测 ### 标题作为分栏标记
        m = re.match(r"###\s+(.+)", stripped)
        if m:
            # 保存前一个 side
            if current_title and current_points:
                sides.append(ComparisonSide(
                    title=current_title[:32],
                    points=current_points[:6],
                ))
            current_title = m.group(1).strip()
            current_points = []
            continue
        # 在 ### 标题下收集 - 列表项
        if current_title:
            m = re.match(r"[-*]\s+(.+)", stripped)
            if m:
                current_points.append(m.group(1).strip()[:100])

    # 最后一个 side
    if current_title and current_points:
        sides.append(ComparisonSide(
            title=current_title[:32],
            points=current_points[:6],
        ))

    return sides[:4]


def _extract_nodes(content: str) -> list[SystemNode]:
    """提取系统架构节点：- **id** | 标签：detail。"""
    nodes: list[SystemNode] = []
    for line in content.splitlines():
        line = line.strip()
        # - **scheduler** | 调度器：核心决策模块...
        m = re.match(r"[-*]\s+\*\*(\w+)\*\*\s*[|｜]\s*(.+?)[:：]\s*(.+)", line)
        if m:
            nodes.append(SystemNode(
                id=m.group(1)[:24],
                label=m.group(2).strip()[:24],
                detail=m.group(3).strip()[:120],
            ))
            continue
        # - **id**：标签 — detail
        m = re.match(r"[-*]\s+\*\*(\w+)\*\*[:：]\s*(.+?)[—\-]\s*(.+)", line)
        if m:
            nodes.append(SystemNode(
                id=m.group(1)[:24],
                label=m.group(2).strip()[:24],
                detail=m.group(3).strip()[:120],
            ))
    return nodes


def _extract_hierarchy(content: str) -> list[HierarchyNode]:
    """提取层级结构：- **id** | level-N | 标签：detail。"""
    items: list[HierarchyNode] = []
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r"[-*]\s+\*\*(\w+)\*\*\s*[|｜]\s*(\d+)\s*[|｜]\s*(.+?)[:：]\s*(.+)", line)
        if m:
            items.append(HierarchyNode(
                id=m.group(1)[:24],
                label=m.group(3).strip()[:28],
                detail=m.group(4).strip()[:120],
                level=int(m.group(2)),
            ))
    return items


def _extract_timeline(content: str) -> list[TimelineEvent]:
    """提取时间线：- **时间** | 标题：detail。"""
    events: list[TimelineEvent] = []
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r"[-*]\s+\*\*(.+?)\*\*\s*[|｜]\s*(.+?)[:：]\s*(.+)", line)
        if m:
            events.append(TimelineEvent(
                time=m.group(1).strip()[:20],
                title=m.group(2).strip()[:32],
                detail=m.group(3).strip()[:120],
            ))
    return events


def _extract_matrix(content: str) -> list[MatrixCell]:
    """提取矩阵表格：| 行 | 列 | 内容 |。"""
    cells: list[MatrixCell] = []
    for line in content.splitlines():
        line = line.strip()
        # 跳过分隔行 |---|---|
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        parts = [p.strip() for p in line.split("|")]
        # 过滤首尾空元素
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            try:
                row = int(parts[0])
                col = int(parts[1])
                content_text = parts[2][:100]
                highlight = content_text.endswith("*")
                if highlight:
                    content_text = content_text.rstrip("*").strip()
                cells.append(MatrixCell(row=row, col=col, content=content_text, highlight=highlight))
            except ValueError:
                continue
    return cells


def _extract_speaker_notes(content: str) -> str:
    """提取 > 讲稿：... 行（非元数据的 > 行）。"""
    notes: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(">"):
            continue
        # 跳过元数据行
        if any(f"{k}=" in stripped for k in ("role", "shape", "animation", "anim")):
            continue
        note = stripped.lstrip(">").strip()
        if note:
            notes.append(note)
    return " ".join(notes)


# ── 推断函数 ────────────────────────────────────────────────────────────

def _infer_shape(role: str, content: str) -> str:
    """根据 role 和内容推断 shape。"""
    # role → 默认 shape
    role_defaults: dict[str, str] = {
        "cover": "statement",
        "section": "statement",
        "hook": "statement",
        "explain": "concept",
        "derive": "sequence",
        "case": "comparison",
        "practice": "quiz",
        "summary": "concept",
        "closing": "statement",
    }
    # 内容特征推断
    if "```" in content:
        return "code"
    if "$$" in content or "\\[" in content:
        return "formula"
    if re.search(r"\d+\.\s+", content):
        return "sequence"
    if content.count("### ") >= 2:
        return "comparison"

    return role_defaults.get(role, "concept")


def _infer_animation(shape: str) -> str:
    """根据 shape 推断动画。"""
    defaults: dict[str, str] = {
        "statement": "reveal",
        "concept": "reveal",
        "sequence": "trace",
        "comparison": "compare",
        "system": "build",
        "code": "build",
        "formula": "build",
        "quiz": "resolve",
        "misconception": "resolve",
        "hierarchy": "build",
        "timeline": "trace",
        "matrix": "reveal",
    }
    return defaults.get(shape, "reveal")


# ── 主编译函数 ──────────────────────────────────────────────────────────

def compile_ppt_plan(
    markdown: str,
    *,
    title: str = "",
    subtitle: str = "",
    density: str = "reading_first",
    audience: str = "",
    template_family: str = "auto",
    template_scheme: str = "auto",
) -> PPTPlan:
    """将 Markdown 课件大纲编译为 PPTPlan。

    Markdown 格式规范见 app/shared/ppt/prompts/slide_outline.md。

    Args:
        markdown: LLM 输出的 Markdown 格式课件内容
        title: 课件标题（如果 Markdown 中没有指定）
        subtitle: 副标题
        density: 密度模式 speaker_led / reading_first
        audience: 目标受众
        template_family: 模板族 auto/editorial/technical
        template_scheme: 配色 auto/light/dark

    Returns:
        校验后的 PPTPlan 实例
    """
    # ── 提取全局元数据 ──
    plan_title = title
    plan_subtitle = subtitle
    plan_purpose = ""
    plan_audience = audience
    plan_narrative = ""
    plan_density = density if density in VALID_DENSITIES else "reading_first"
    plan_keywords: list[str] = []

    # 从首部 # 标题提取
    for line in markdown.splitlines():
        stripped = line.strip()
        m = re.match(r"^#\s+(.+)$", stripped)
        if m:
            if not plan_title:
                plan_title = m.group(1).strip()[:64]
            continue
        m = re.match(r"^\*\*(?:副标题|subtitle)[:：]\s*\*\*(.+?)(?:\*\*)?$", stripped)
        if m and not plan_subtitle:
            plan_subtitle = m.group(1).strip()[:120]
            continue
        m = re.match(r"^\*\*(?:教学目的|目的|purpose)[:：]\s*\*\*(.+?)(?:\*\*)?$", stripped)
        if m and not plan_purpose:
            plan_purpose = m.group(1).strip()[:180]
            continue
        m = re.match(r"^\*\*(?:目标受众|受众|audience)[:：]\s*\*\*(.+?)(?:\*\*)?$", stripped)
        if m and not plan_audience:
            plan_audience = m.group(1).strip()[:120]
            continue
        m = re.match(r"^\*\*(?:叙事主线|主线|narrative)[:：]\s*\*\*(.+?)(?:\*\*)?$", stripped)
        if m and not plan_narrative:
            plan_narrative = m.group(1).strip()[:500]
            continue
        m = re.match(r"^\*\*(?:关键词|keywords)[:：]\s*\*\*(.+?)(?:\*\*)?$", stripped)
        if m:
            plan_keywords = [k.strip() for k in m.group(1).split(",") if k.strip()][:6]
            continue
        break  # 遇到非元数据行停止

    # ── 分割幻灯片块 ──
    blocks = _SLIDE_SPLIT.split(markdown)
    slides: list[PPTSlide] = []

    for index, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue
        # 跳过全局元数据区（第一个块如果不是 ## 开头）
        if index == 0 and not re.match(r"^##\s+", block, re.MULTILINE) and "#" in block:
            # 可能是全局标题区，检查是否有 ## 段落
            if not re.search(r"^##\s+", block, re.MULTILINE):
                continue

        slide = _parse_slide_block(block, len(slides))
        if slide is not None:
            slides.append(slide)

    # ── 兜底校验和修正 ──
    if not slides:
        # 至少生成一个最简 cover
        slides.append(PPTSlide(
            role="cover",
            shape="statement",
            title=plan_title or "教学课件",
            statement=plan_title or "教学课件",
            animation="reveal",
        ))

    # 首页必须是 cover
    if slides[0].role != "cover":
        slides[0] = slides[0].model_copy(update={"role": "cover"})

    # 末页必须是 summary 或 closing
    if slides[-1].role not in ("summary", "closing"):
        slides[-1] = slides[-1].model_copy(update={"role": "summary"})

    # 长课件自动插入 section 分隔
    slides = _insert_section_markers(slides)

    # 相邻页 shape 去重
    slides = _dedup_adjacent_shapes(slides)

    # shape 多样化：至少 5 种不同 shape
    slides = _ensure_shape_diversity(slides)

    # ── 构建 PPTPlan ──
    return PPTPlan(
        title=plan_title or "教学课件",
        subtitle=plan_subtitle,
        purpose=plan_purpose or f"讲解{plan_title}",
        audience=plan_audience or "学习者",
        density=plan_density,  # type: ignore[arg-type]
        narrative=plan_narrative or f"围绕{plan_title}展开系统性讲解",
        language="zh-CN",
        template_preference=PPTTemplatePreference(
            family=template_family,  # type: ignore[arg-type]
            scheme=template_scheme,  # type: ignore[arg-type]
            keywords=plan_keywords,
        ),
        slides=slides,
    )


def _insert_section_markers(slides: list[PPTSlide]) -> list[PPTSlide]:
    """每 4-5 页自动插入 section 分隔（如果缺失）。"""
    if len(slides) <= 6:
        return slides

    result: list[PPTSlide] = []
    since_section = 0
    section_count = 0

    for i, slide in enumerate(slides):
        if slide.role == "section":
            since_section = 0
            section_count += 1
        else:
            since_section += 1

        result.append(slide)

        # 每 5 页且不是最后一页，插入 section
        # 但当前页已是 summary/closing 时不再追加分隔，避免在总结与收尾之间插入无意义"第N部分"
        if since_section >= 5 and i < len(slides) - 1 and slide.role not in ("summary", "closing"):
            result.append(PPTSlide(
                role="section",
                shape="statement",
                title=f"第{section_count + 2}部分",
                statement=f"第{section_count + 2}部分",
                animation="focus",
            ))
            since_section = 0
            section_count += 1

    return result


def _dedup_adjacent_shapes(slides: list[PPTSlide]) -> list[PPTSlide]:
    """相邻页面 shape 去重：如果相邻两页 shape 相同，调整第二页。"""
    alternative_shapes: dict[str, list[str]] = {
        "statement": ["concept"],
        "concept": ["statement", "comparison"],
        "sequence": ["concept", "comparison"],
        "comparison": ["concept", "statement"],
        "system": ["concept", "hierarchy"],
        "code": ["concept", "sequence"],
        "formula": ["concept", "statement"],
        "quiz": ["misconception", "concept"],
        "misconception": ["comparison", "concept"],
        "hierarchy": ["system", "concept"],
        "timeline": ["sequence", "concept"],
        "matrix": ["comparison", "concept"],
    }

    result = list(slides)
    # 结构性页面（cover/section/summary/closing）按 role 渲染，shape 应保持声明的 statement：
    # 否则"封面 + 首节"同为 statement 会把首节改成 concept，连锁把紧跟其后的真实 concept
    # 内容页挤成 statement，并可能让 section 页错误地按 concept 布局渲染。
    structural = {"cover", "section", "summary", "closing"}
    for i in range(1, len(result)):
        if result[i].role in structural:
            continue
        if result[i].shape == result[i - 1].shape:
            alts = alternative_shapes.get(result[i].shape, ["concept"])
            # 选一个和前页不同的
            for alt in alts:
                if alt != result[i - 1].shape:
                    result[i] = result[i].model_copy(update={"shape": alt})
                    break

    return result


def _ensure_shape_diversity(slides: list[PPTSlide]) -> list[PPTSlide]:
    """确保至少有 5 种不同 shape，不够时替换中间页。"""
    MIN_SHAPES = 5

    # 可用于替换的 shape，优先选不强制要求结构化内容的 shape
    # statement 只需要 statement 文本，concept 只需要 points
    candidate_shapes = [
        "statement", "concept", "comparison",
        "sequence", "code", "formula", "system", "quiz",
    ]

    used_shapes = {s.shape for s in slides}
    if len(used_shapes) >= MIN_SHAPES:
        return slides

    # 需要补充的 shape 数量
    needed = MIN_SHAPES - len(used_shapes)
    available = [s for s in candidate_shapes if s not in used_shapes]

    # 选择可替换的中间页（跳过 cover、section、summary、closing）
    replaceable_indices = [
        i for i, s in enumerate(slides)
        if s.role == "explain" and len(used_shapes) < MIN_SHAPES
    ]

    for idx in replaceable_indices:
        if needed <= 0 or not available:
            break
        new_shape = available.pop(0)
        slides[idx] = slides[idx].model_copy(update={"shape": new_shape})
        used_shapes.add(new_shape)
        needed -= 1

    return slides
