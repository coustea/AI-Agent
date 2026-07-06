"""导入 408 题库。

科目: 数据结构与算法、计算机组成原理、计算机网络、操作系统
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import func
from sqlmodel import select

from app.infra.database import init_db, session_scope
from app.infra.logging import get_logger
from app.infra.models import QuizQuestion

logger = get_logger(__name__)

QUIZ_DIR = Path(__file__).parent / "data/quiz"

TYPE_MAP = {
    "选择题": "single_choice", "单选题": "single_choice", "多选题": "multiple_choice",
    "判断题": "judge", "填空题": "fill_blank", "简答题": "short_answer",
    "分析题": "analysis", "综合题": "comprehensive",
}


async def import_408_quiz() -> int:
    """导入 408 题库。有数据跳过，无数据导入。

    注意：此函数由 init_db() 的 _seed_initial_data() 调用，
    数据库已初始化，无需再次调用 init_db()。
    """

    if not QUIZ_DIR.exists():
        logger.error("[Quiz] 目录不存在: %s", QUIZ_DIR)
        return 0

    async with session_scope() as session:
        cnt = (await session.exec(
            select(func.count()).select_from(QuizQuestion)
        )).one() or 0

        if cnt > 0:
            logger.info("[Quiz] 已存在 %d 条，跳过", cnt)
            return 0

        files = list(QUIZ_DIR.rglob("*.json"))
        if not files:
            logger.error("[Quiz] 无 JSON 文件")
            return 0

        logger.info("[Quiz] 开始导入 %d 个文件", len(files))
        return _load_files(session, files)


def _load_files(session, files) -> int:
    """批量导入文件。"""
    total = 0
    for f in files:
        subj = f.parent.name
        logger.info("[Quiz] 处理: %s/%s", subj, f.name)
        try:
            total += _load_file(session, f, subj)
        except Exception as e:
            logger.error("[Quiz] %s 失败: %s", f.name, e)

    logger.info("[Quiz] 导入完成，共 %d 题", total)
    return total


def _load_file(session, f: Path, subj: str) -> int:
    """导入单个文件。"""
    data = json.loads(f.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return 0

    qs = []
    for item in data:
        qid = item.get("id")
        if not qid:
            continue
        t = TYPE_MAP.get(item.get("type", "选择题"), "single_choice")
        qs.append(QuizQuestion(
            question_id=qid, source="408", subject=item.get("subject", subj),
            question_type=t, difficulty=item.get("difficulty"),
            content=item.get("content", ""), options_json=item.get("options"),
            answer=item.get("answer"), analysis=item.get("analysis"),
            knowledge_points=item.get("knowledge_points"), tags=item.get("tags"),
            language=item.get("language", "zh"), split=item.get("split", "train"),
        ))

    session.add_all(qs)
    return len(qs)


if __name__ == "__main__":
    imported = asyncio.run(import_408_quiz())
    print(f"导入 {imported} 道题目")