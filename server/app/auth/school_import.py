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

# 获取当前模块的日志记录器
logger = get_logger(__name__)

# Excel 文件路径：server/docs/school.xlsx
SCHOOL_EXCEL_PATH = Path(__file__).parent.parent.parent / "docs" / "school.xlsx"


async def read_school_excel(path: Path) -> list[tuple[str, str, str]]:
    """读取高校名单 Excel 文件。

    解析 Excel 中的学校名称、办学层次、院校层次字段，
    返回清理后的数据列表。

    Args:
        path: Excel 文件路径

    Returns:
        (学校名称, 办学层次, 院校层次) 元组列表，读取失败返回空列表
    """
    if not path.exists():
        logger.warning("[SchoolImport] Excel 文件不存在: %s", path)
        return []

    try:
        # 使用 pandas 读取 Excel 文件
        df = pd.read_excel(path)

        # 检查必需的列是否存在
        required_cols = ["学校名称", "办学层次", "院校层次"]
        if not all(col in df.columns for col in required_cols):
            logger.error("[SchoolImport] 缺少必需字段: %s", required_cols)
            return []

        # 提取所需列，删除学校名称为空的行，并清理字符串两端空白
        result = df[required_cols].dropna(subset=["学校名称"])
        result["学校名称"] = result["学校名称"].astype(str).str.strip()
        result["办学层次"] = result["办学层次"].astype(str).str.strip()
        result["院校层次"] = result["院校层次"].astype(str).str.strip()

        # 将 DataFrame 转为元组列表
        return [
            (row["学校名称"], row["办学层次"], row["院校层次"])
            for _, row in result.iterrows()
        ]

    except Exception as e:
        logger.error("[SchoolImport] 读取 Excel 失败: %s", e)
        return []


async def import_schools(session: AsyncSession) -> int:
    """导入学校数据到数据库。

    使用批量查询避免逐行网络往返，只插入不存在的学校记录。

    Args:
        session: 数据库会话

    Returns:
        新增学校数量
    """
    # 从 Excel 读取学校数据
    schools_data = await read_school_excel(SCHOOL_EXCEL_PATH)
    if not schools_data:
        logger.info("[SchoolImport] 无学校数据需要导入")
        return 0

    # 查询数据库中已存在的学校名称（避免重复插入）
    existing_names: set[str] = {
        school.name for school in (await session.exec(select(School))).scalars().all()
    }

    # 过滤出数据库中不存在的新学校
    new_schools = [
        School(name=name, level=level, tier=tier)
        for name, level, tier in schools_data
        if name not in existing_names
    ]
    if not new_schools:
        logger.info("[SchoolImport] 学校数据已存在，跳过导入")
        return 0

    # 批量插入新学校记录
    session.add_all(new_schools)
    await session.commit()
    logger.info("[SchoolImport] 导入完成，新增 %d 所学校", len(new_schools))
    return len(new_schools)
