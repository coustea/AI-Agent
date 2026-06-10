"""题库数据自动导入服务。

项目启动时从 quiz/final/ 目录的 JSON 文件将题目导入到 quiz_questions 表。
仅在表为空时执行导入，避免重复写入。
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import QuizQuestion

logger = get_logger(__name__)

QUIZ_DIR = Path(__file__).parent.parent.parent / "quiz" / "final"
QUIZ_BANK_SUBDIR = "408题库"

BATCH_SIZE = 200


async def _load_quiz_files() -> list[tuple[dict, str]]:
    """扫描题库目录，返回 (题目dict, 文件相对路径) 列表。"""
    bank_dir = QUIZ_DIR / QUIZ_BANK_SUBDIR
    if not bank_dir.exists():
        logger.warning("[QuizImport] 题库目录不存在: %s", bank_dir)
        return []

    results: list[tuple[dict, str]] = []
    for json_file in sorted(bank_dir.rglob("*.json")):
        rel_path = json_file.relative_to(QUIZ_DIR).as_posix()
        if any(skip in rel_path for skip in ("fixed_output", ".omc", "state")):
            continue
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    results.append((item, rel_path))
        except Exception as exc:
            logger.warning("[QuizImport] 读取文件失败: %s — %s", rel_path, exc)

    return results


def _to_model(item: dict, source_file: str) -> QuizQuestion | None:
    """将 JSON 题目记录转换为 QuizQuestion ORM 对象。"""
    question_id = item.get("id", "")
    if not question_id:
        return None

    content = item.get("content", "")
    if not content or not content.strip():
        return None

    return QuizQuestion(
        question_id=str(question_id),
        source=item.get("source"),
        subject=item.get("subject", ""),
        subject_en=item.get("subject_en"),
        question_type=item.get("type", "选择题"),
        difficulty=item.get("difficulty"),
        bloom_level=item.get("bloom_level"),
        content=content,
        options_json=item.get("options"),
        answer=item.get("answer"),
        analysis=item.get("analysis"),
        knowledge_points=item.get("knowledge_points") or [],
        tags=item.get("tags") or [],
        language=item.get("language"),
        split=item.get("split"),
        source_file=source_file,
        raw_record=item,
    )


async def import_quiz_bank(session: AsyncSession) -> int:
    """导入题库到数据库。仅在表为空时执行。

    Args:
        session: 数据库会话

    Returns:
        新增题目数量
    """
    count = (await session.exec(
        select(func.count()).select_from(QuizQuestion)
    )).scalar() or 0

    if count > 0:
        logger.info("[QuizImport] 题库已有 %d 条数据，跳过导入", count)
        return 0

    raw_items = await _load_quiz_files()
    if not raw_items:
        logger.info("[QuizImport] 无题库数据需要导入")
        return 0

    logger.info("[QuizImport] 发现 %d 条题目，开始导入", len(raw_items))

    imported = 0
    batch: list[QuizQuestion] = []

    for item, rel_path in raw_items:
        model = _to_model(item, rel_path)
        if model is None:
            continue
        batch.append(model)

        if len(batch) >= BATCH_SIZE:
            session.add_all(batch)
            await session.commit()
            imported += len(batch)
            batch = []

    if batch:
        session.add_all(batch)
        await session.commit()
        imported += len(batch)

    logger.info("[QuizImport] 导入完成，新增 %d 条题目", imported)
    return imported
