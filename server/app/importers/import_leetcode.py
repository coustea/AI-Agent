"""导入 LeetCode 编程题到数据库。

运行方式：
    cd server
    uv run python app/importers/import_leetcode.py
"""

import json
import asyncio
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine, init_db, session_scope
from app.infra.models import ProgrammingQuestion
from app.infra.logging import get_logger

logger = get_logger(__name__)

DATA_FILE = Path(__file__).parent / "programming/crawlers/leetcode/leetcode_problems.json"


async def import_leetcode_questions():
    """导入 LeetCode 题目到数据库。"""
    await init_db()

    # 创建表（如果不存在）
    from sqlmodel import SQLModel
    from app.infra.database import engine
    from sqlalchemy.ext.asyncio import AsyncSession

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    with open(DATA_FILE, encoding="utf-8") as f:
        questions = json.load(f)

    logger.info("[Import] 共 %d 道题目", len(questions))

    async with session_scope() as session:
        existing = await session.exec(select(ProgrammingQuestion))
        existing_ids = {q.question_id for q in existing.all()}

        new_questions = []
        for item in questions:
            question_id = item.get("question_id")
            if not question_id or question_id in existing_ids:
                continue

            # 难度转换
            difficulty = item.get("difficulty")
            if isinstance(difficulty, int):
                difficulty_map = {1: "简单", 2: "中等", 3: "困难"}
                difficulty = difficulty_map.get(difficulty, "中等")

            question = ProgrammingQuestion(
                question_id=question_id,
                source=item.get("source", "leetcode"),
                platform_question_id=str(item.get("platform_question_id") or ""),
                title=item.get("title", ""),
                title_en=item.get("title_en"),
                content=item.get("content", ""),
                difficulty=difficulty,
                subject=item.get("subject", "算法"),
                code_templates=item.get("code_templates"),
                supported_languages=item.get("supported_languages"),
                example_test_cases=item.get("example_test_cases"),
                test_cases=item.get("test_cases"),
                time_limit=item.get("time_limit"),
                memory_limit=item.get("memory_limit"),
                tags=item.get("tags"),
                knowledge_points=item.get("knowledge_points"),
                acceptance_rate=item.get("acceptance_rate"),
                total_submissions=item.get("total_submissions"),
                total_accepted=item.get("total_accepted"),
                url=item.get("url"),
            )
            new_questions.append(question)

        if not new_questions:
            logger.info("[Import] 无新题目需要导入")
            return 0

        batch_size = 50
        imported = 0
        for i in range(0, len(new_questions), batch_size):
            batch = new_questions[i:i + batch_size]
            session.add_all(batch)
            await session.commit()
            imported += len(batch)

        logger.info("[Import] 导入完成，新增 %d 道题目", imported)
        return imported


if __name__ == "__main__":
    imported = asyncio.run(import_leetcode_questions())
    print(f"导入完成：新增 {imported} 道题目")