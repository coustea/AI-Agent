"""周摘要构建器 — Orchestrator。

并行执行 5 个模块的章节构建，合并统计，组装最终 Markdown，
并在原始内容超出阈值时触发 LLM 精炼。"""

# 编排 5 个模块章节构建、合并统计、组装 Markdown 及可选 LLM 精炼
from __future__ import annotations

import asyncio
from datetime import datetime
from time import perf_counter

from sqlmodel.ext.asyncio.session import AsyncSession

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm
from app.infra.logging import get_logger

logger = get_logger(__name__)
from app.profile.weekly.chat import build_chat_section
from app.profile.weekly.path import build_path_section
from app.profile.weekly.quiz import build_quiz_section
from app.profile.weekly.resource import build_resource_section
from app.profile.weekly.types import DigestBuildResult, SectionResult
from app.profile.weekly.visualizer import build_visualizer_section

# 超过此字符数则触发 LLM 精炼（而非直接保存原始 Markdown）
LLM_CONDENSE_THRESHOLD = 3000


# 构建完整周度学习摘要：并行章节构建 + 统计合并 + 组装 + 可选精炼
async def build_digest(
    db: AsyncSession,
    user_id: int,
    week_start: datetime,
    week_end: datetime,
    username: str = "用户",
) -> DigestBuildResult:
    """构建完整的周度学习摘要。

    1. 并行运行 5 个模块的章节构建。
    2. 合并各模块统计。
    3. 组装完整 Markdown。
    4. 判断是否需要 LLM 精炼。

    Args:
        db: 数据库会话。
        user_id: 用户 ID。
        week_start: 周起始日期（周一 00:00）。
        week_end: 周结束日期（周日 23:59）。
        username: 用户名称，用于摘要问候。

    Returns:
        ``DigestBuildResult``，包含最终 Markdown 和汇总统计。
    """
    logger.info("Building weekly digest — user=%d week=%s~%s", user_id, week_start.date(), week_end.date())
    _t0 = perf_counter()

    # 并行构建 5 个模块的章节以缩短总耗时
    sections: list[SectionResult] = await asyncio.gather(
        build_chat_section(db, user_id, week_start, week_end),
        build_resource_section(db, user_id, week_start, week_end),
        build_path_section(db, user_id, week_start, week_end),
        build_quiz_section(db, user_id, week_start, week_end),
        build_visualizer_section(db, user_id, week_start, week_end),
    )

    _t1 = perf_counter()
    logger.info(
        "Sections built for user=%d in %.2fs — chat=%d resource=%d path=%d quiz=%d visualizer=%d",
        user_id, _t1 - _t0,
        sections[0].raw_length, sections[1].raw_length,
        sections[2].raw_length, sections[3].raw_length,
        sections[4].raw_length,
    )

    # 合并统计：先初始化各模块汇总字典
    merged_stats: dict = {
        "dialogue_turns": 0,
        "resources_generated": 0,
        "resources_completed": 0,
        "nodes_touched": 0,
        "nodes_completed": 0,
        "quiz_total": 0,
        "quiz_correct": 0,
        "accuracy": 0,
        "visualizer_runs": 0,
        "visualizer_failures": 0,
    }

    quiz_total = 0
    quiz_correct = 0
    courses_set: set[str] = set()
    total_raw_length = 0

    # 遍历各章节统计，累加并处理课程标题/测验聚合
    for sec in sections:
        total_raw_length += sec.raw_length
        for key, val in sec.stats.items():
            if key == "course_titles":
                courses_set.update(val)
            elif key == "quiz_total":
                quiz_total += val
            elif key == "quiz_correct":
                quiz_correct += val
            elif key == "accuracy":
                pass  # recalculated below
            elif key in merged_stats:
                merged_stats[key] += val

    # 根据聚合后的测验数重算正确率
    if quiz_total > 0:
        merged_stats["quiz_total"] = quiz_total
        merged_stats["quiz_correct"] = quiz_correct
        merged_stats["accuracy"] = round(quiz_correct / quiz_total * 100)

    courses_active = sorted(courses_set)

    # 组装完整 Markdown（含概览与各模块章节）
    md = _assemble_markdown(
        username=username,
        week_start=week_start,
        week_end=week_end,
        stats=merged_stats,
        sections=sections,
    )

    # LLM 精炼（仅当原始内容超过阈值时触发）
    condensed = False
    if total_raw_length > LLM_CONDENSE_THRESHOLD:
        logger.info("Raw digest length %d exceeds threshold %d — triggering LLM condense", total_raw_length, LLM_CONDENSE_THRESHOLD)
        condensed_md = await _condense_with_llm(md, username)
        # 精炼成功则替换，否则保留原始摘要
        if condensed_md:
            md = condensed_md
            condensed = True
            logger.info("LLM condense succeeded — new length %d chars", len(md))
        else:
            logger.warning("LLM condense returned empty — keeping original digest")

    _t2 = perf_counter()
    logger.info(
        "Digest built for user=%d in %.2fs — raw_length=%d final_length=%d condensed=%s",
        user_id, _t2 - _t0, total_raw_length, len(md), condensed,
    )

    return DigestBuildResult(
        markdown=md,
        stats=merged_stats,
        courses_active=courses_active,
        raw_length=total_raw_length,
    )


# 构建「## 学习概览」章节文本
def _build_overview_md(stats: dict) -> str:
    """构建 ## 学习概览 章节。"""
    lines = [f"- 辅导对话：{stats.get('dialogue_turns', 0)} 轮"]
    lines.append(f"- 资源生成：{stats.get('resources_generated', 0)} 个（{stats.get('resources_completed', 0)} 个已完成）")
    lines.append(f"- 路径学习：{stats.get('nodes_touched', 0)} 个节点（{stats.get('nodes_completed', 0)} 个已完成）")
    lines.append(f"- 答题测试：{stats.get('quiz_total', 0)} 道题（正确率 {stats.get('accuracy', 0)}%）")
    lines.append(f"- 算法可视化：{stats.get('visualizer_runs', 0)} 次（失败 {stats.get('visualizer_failures', 0)} 次）")
    return "\n".join(lines)


# 各模块章节标题与 key 的映射（顺序对应并行构建结果）
SECTION_HEADERS = [
    ("辅导对话", "chat"),
    ("资源生成", "resource"),
    ("路径学习", "path"),
    ("答题情况", "quiz"),
    ("算法可视化", "visualizer"),
]


# 将概览与各章节组装为完整 Markdown 文档
def _assemble_markdown(
    username: str,
    week_start: datetime,
    week_end: datetime,
    stats: dict,
    sections: list[SectionResult],
) -> str:
    """组装完整周摘要 Markdown。"""
    start_str = week_start.strftime("%Y-%m-%d")
    end_str = week_end.strftime("%Y-%m-%d")

    parts: list[str] = [
        f"# {username} 周度学习摘要（{start_str} ~ {end_str}）",
        "",
        "## 学习概览",
        _build_overview_md(stats),
        "",
    ]

    # 依次追加各模块章节标题与内容
    for (header_name, _), sec in zip(SECTION_HEADERS, sections):
        parts.append(f"## {header_name}")
        parts.append(sec.markdown)
        parts.append("")

    # 长期记忆章节（暂未实现）
    parts.append("## 长期记忆")
    parts.append("（待梳理）")
    parts.append("")

    return "\n".join(parts)


# 调用 LLM 精炼周摘要（仅当原始内容过多时触发）
async def _condense_with_llm(raw_md: str, username: str) -> str | None:
    """调用 LLM 精炼周摘要（仅当原始内容过多时触发）。"""
    system_prompt = (
        "你是一位学习辅助 AI 助手。用户本周产生了丰富的学习记录，"
        "你需要将以下原始周度学习摘要精炼为更简洁、可读性更高的版本，"
        "保留关键统计数据和重要结论，删除冗余细节。"
    )
    user_prompt = (
        f"请精炼以下 {username} 的周度学习摘要，保留结构和关键数据，使内容更紧凑：\n\n{raw_md}"
    )

    logger.info("Condensing digest via LLM (input length=%d chars)", len(raw_md))
    try:
        llm = get_llm()
        # 调用 LLM 生成更紧凑的摘要
        resp = await llm.ainvoke(
            [HumanMessage(content=user_prompt)],
            temperature=0.3,
            max_tokens=2048,
        )
        content = str(resp.content or "").strip()

        # 仅当输出足够长才采用精炼结果
        if content and len(content) > 50:
            logger.info("LLM condense successful — output length=%d chars", len(content))
            return content
        logger.warning("LLM condense produced too-short content (%d chars) — discarding", len(content))
    except Exception as exc:
        # 精炼失败不阻断主流程，返回 None 以保留原始摘要
        logger.exception("LLM condense failed: %s", exc)

    return None
