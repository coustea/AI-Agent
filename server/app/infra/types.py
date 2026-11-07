"""数据库类型与时间工具。

MySQL 的 DATETIME 不保存时区，读回来是 naive datetime。项目内部统一用
aware UTC，因此所有时间列都走 UtcDateTime：写入时归一化为 UTC 去掉 tzinfo，
读出时补回 UTC tzinfo。这样 Python 侧永远拿到 aware UTC，可以直接做减法、
比较和 astimezone。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects import mysql
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """当前 UTC 时间（aware）。"""
    return datetime.now(timezone.utc)


class UtcDateTime(TypeDecorator):
    """统一按 UTC 存取的 datetime 列。

    MySQL 侧用 DATETIME(6) 保留微秒（PG 的 timestamptz 有微秒精度，降级会丢
    排序稳定性）。写入前转成 UTC naive，读出后补回 UTC tzinfo。
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        if dialect.name == "mysql":
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
