"""学校数据导入服务。

从 Excel 文件导入高校名单到数据库。
Excel 文件已包含院校层次标签（985/211/双一流/普通本科/专科）。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.logging import get_logger
from app.infra.models import School

logger = get_logger(__name__)

# Excel 文件路径
SCHOOL_EXCEL_PATH = Path(__file__).parent.parent.parent / "docs" / "school.xlsx"


async def read_school_excel(path: Path) -> list[tuple[str, str, str]]:
    """读取高校名单 Excel，返回 (学校名称, 办学层次, 院校层次) 列表。"""
    if not path.exists():
        logger.warning("[SchoolImport] Excel 文件不存在: %s", path)
        return []

    try:
        df = pd.read_excel(path)

        # 检查必需字段
        required_cols = ["学校名称", "办学层次", "院校层次"]
        if not all(col in df.columns for col in required_cols):
            logger.error("[SchoolImport] 缺少必需字段: %s", required_cols)
            return []

        # 提取并清理数据
        result = df[required_cols].dropna(subset=["学校名称"])
        result["学校名称"] = result["学校名称"].astype(str).str.strip()
        result["办学层次"] = result["办学层次"].astype(str).str.strip()
        result["院校层次"] = result["院校层次"].astype(str).str.strip()

        return [
            (row["学校名称"], row["办学层次"], row["院校层次"])
            for _, row in result.iterrows()
        ]

    except Exception as e:
        logger.error("[SchoolImport] 读取 Excel 失败: %s", e)
        return []


async def import_schools(session: AsyncSession) -> int:
    """导入学校数据到数据库。

    Args:
        session: 数据库会话

    Returns:
        新增学校数量
    """
    schools_data = await read_school_excel(SCHOOL_EXCEL_PATH)
    if not schools_data:
        logger.info("[SchoolImport] 无学校数据需要导入")
        return 0

    count = 0
    for name, level, tier in schools_data:
        # 检查是否已存在
        stmt = select(School).where(School.name == name)
        existing = (await session.exec(stmt)).first()
        if existing:
            continue

        school = School(name=name, level=level, tier=tier)
        session.add(school)
        count += 1

    await session.commit()
    logger.info("[SchoolImport] 导入完成，新增 %d 所学校", count)
    return count
