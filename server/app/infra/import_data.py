"""种子数据导入服务。

启动时由 _seed_initial_data() 调用，分别检查学校、408题库数据是否为空，为空则导入。

数据目录: app/infra/data/
"""

# 本模块负责在数据库为空时导入种子数据：408 题库与学校信息
import asyncio
import json
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import func
from sqlmodel import select

from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import QuizQuestion, School

logger = get_logger(__name__)

_DATA_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# 408 题库导入
# ---------------------------------------------------------------------------

QUIZ_DIR = _DATA_DIR / "quiz"

TYPE_MAP = {
    "选择题": "single_choice", "单选题": "single_choice",
    "判断题": "judge", "填空题": "fill_blank", "分析题": "analysis",
}


# 导入 408 题库：已有数据则跳过，否则读取 JSON 文件导入
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
        return _load_quiz_files(session, files)


# 遍历题库文件逐个导入，单文件失败不影响整体
def _load_quiz_files(session, files) -> int:
    """批量导入题库文件。"""
    total = 0
    for f in files:
        subj = f.parent.name
        logger.info("[Quiz] 处理: %s/%s", subj, f.name)
        try:
            total += _load_quiz_file(session, f, subj)
        except Exception as e:
            logger.error("[Quiz] %s 失败: %s", f.name, e)

    logger.info("[Quiz] 导入完成，共 %d 题", total)
    return total


# 解析单个题库 JSON 文件并构造 QuizQuestion 记录
def _load_quiz_file(session, f: Path, subj: str) -> int:
    """导入单个题库文件。"""
    data = json.loads(f.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return 0

    qs = []
    for item in data:
        qid = item.get("id")
        if not qid:
            continue
        t = TYPE_MAP.get(item.get("type"), "single_choice")
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


# ---------------------------------------------------------------------------
# 学校数据导入
# ---------------------------------------------------------------------------

SCHOOL_XLSX = _DATA_DIR / "school.xlsx"


# 导入学校数据：已有数据则跳过，否则读取 Excel 导入
async def import_schools() -> int:
    """导入学校。有数据跳过，无数据导入。

    注意：此函数由 init_db() 的 _seed_initial_data() 调用，
    数据库已初始化，无需再次调用 init_db()。
    """

    if not SCHOOL_XLSX.exists():
        logger.warning("[Schools] 文件不存在: %s", SCHOOL_XLSX)
        return 0

    async with session_scope() as session:
        cnt = (await session.exec(
            select(func.count()).select_from(School)
        )).one() or 0

        if cnt > 0:
            logger.info("[Schools] 已存在 %d 条，跳过", cnt)
            return 0

        return _load_xlsx(session)


# 从 Excel 工作簿解析表头与行数据，构造 School 记录
def _load_xlsx(session) -> int:
    """从 Excel 加载学校数据。"""
    wb = load_workbook(SCHOOL_XLSX, data_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    if not rows:
        return 0

    # 解析表头
    hdr = [str(h).lower().strip() if h else "" for h in rows[0]]
    n_col = l_col = t_col = None
    for i, c in enumerate(hdr):
        if c in ("学校名称", "学校", "名称", "name"):
            n_col = i
        elif c in ("办学层次", "层次", "level"):
            l_col = i
        elif c in ("院校层次", "等级", "tier"):
            t_col = i

    if n_col is None:
        n_col, l_col, t_col = 0, 1, 2
        data = rows
    else:
        data = rows[1:]

    schools = []
    for r in data:
        if not r or all(c is None for c in r):
            continue
        name = str(r[n_col]).strip() if r[n_col] else None
        if not name:
            continue
        level = str(r[l_col]).strip() if l_col and r[l_col] else None
        tier = str(r[t_col]).strip() if t_col and r[t_col] else None
        schools.append(School(name=name, level=level, tier=tier))

    session.add_all(schools)
    logger.info("[Schools] 导入 %d 所", len(schools))
    return len(schools)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _total = asyncio.run(import_schools()) + asyncio.run(import_408_quiz())
    print(f"导入完成: {_total} 条")
