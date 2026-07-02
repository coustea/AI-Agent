"""导入学校数据。

数据: school.xlsx
"""

import asyncio
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import func
from sqlmodel import select

from app.infra.database import init_db, session_scope
from app.infra.logging import get_logger
from app.infra.models import School

logger = get_logger(__name__)

XLSX = Path(__file__).parent / "data/school.xlsx"


async def import_schools() -> int:
    """导入学校。有数据跳过，无数据导入。

    注意：此函数由 init_db() 的 _seed_initial_data() 调用，
    数据库已初始化，无需再次调用 init_db()。
    """

    if not XLSX.exists():
        logger.warning("[Schools] 文件不存在: %s", XLSX)
        return 0

    async with session_scope() as session:
        cnt = (await session.exec(
            select(func.count()).select_from(School)
        )).one() or 0

        if cnt > 0:
            logger.info("[Schools] 已存在 %d 条，跳过", cnt)
            return 0

        return _load_xlsx(session)


def _load_xlsx(session) -> int:
    """从 Excel 加载。"""
    wb = load_workbook(XLSX, data_only=True)
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


if __name__ == "__main__":
    imported = asyncio.run(import_schools())
    print(f"导入 {imported} 所学校")