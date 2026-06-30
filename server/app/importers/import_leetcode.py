"""导入 LeetCode 编程题。

数据: data/leetcode_problems.json
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import func
from sqlmodel import select

from app.infra.database import init_db, session_scope
from app.infra.logging import get_logger
from app.infra.models import ProgrammingQuestion

logger = get_logger(__name__)

DATA_FILE = Path(__file__).parent / "data/leetcode_problems.json"


async def import_leetcode() -> int:
    """导入编程题。有数据跳过，无数据导入。

    注意：此函数由 init_db() 的 _seed_initial_data() 调用，
    数据库已初始化，无需再次调用 init_db()。
    """

    if not DATA_FILE.exists():
        logger.warning("[LeetCode] 文件不存在: %s", DATA_FILE)
        return 0

    async with session_scope() as session:
        cnt = (await session.exec(
            select(func.count()).select_from(ProgrammingQuestion)
        )).one() or 0

        if cnt > 0:
            logger.info("[LeetCode] 已存在 %d 条，跳过", cnt)
            return 0

        return _load_json(session)


def _load_json(session) -> int:
    """从 JSON 加载。"""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        logger.warning("[LeetCode] 格式错误")
        return 0

    logger.info("[LeetCode] 共 %d 题", len(data))
    qs = []
    for item in data:
        qid = item.get("question_id")
        if not qid:
            continue
        diff = item.get("difficulty")
        if isinstance(diff, int):
            diff = {1: "简单", 2: "中等", 3: "困难"}.get(diff, "中等")
        qs.append(ProgrammingQuestion(
            question_id=qid, source=item.get("source", "leetcode"),
            platform_question_id=str(item.get("platform_question_id") or ""),
            title=item.get("title", ""), title_en=item.get("title_en"),
            content=item.get("content", ""), difficulty=diff,
            subject=item.get("subject", "算法"),
            code_templates=item.get("code_templates"),
            supported_languages=item.get("supported_languages"),
            example_test_cases=item.get("example_test_cases"),
            test_cases=item.get("test_cases"), time_limit=item.get("time_limit"),
            memory_limit=item.get("memory_limit"), tags=item.get("tags"),
            knowledge_points=item.get("knowledge_points"),
            acceptance_rate=item.get("acceptance_rate"),
            total_submissions=item.get("total_submissions"),
            total_accepted=item.get("total_accepted"), url=item.get("url"),
            raw_record=item.get("raw_record"),
        ))

    session.add_all(qs)
    logger.info("[LeetCode] 导入 %d 题", len(qs))
    return len(qs)


if __name__ == "__main__":
    imported = asyncio.run(import_leetcode())
    print(f"导入 {imported} 道编程题")