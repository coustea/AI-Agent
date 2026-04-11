from datetime import datetime
from sqlalchemy import Text, Column
from sqlmodel import SQLModel, Field


class GeneratedResource(SQLModel, table=True):
    """生成资源记录表：存储每次资源生成的结果"""
    __tablename__ = "generated_resources"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    course: str = Field(max_length=200)
    gap: str = Field(sa_column=Column(Text))
    need: str = Field(default="review", max_length=50)
    extra: str | None = Field(default=None, sa_column=Column(Text))

    # 各 Agent 的输出结果 (JSON)
    mindmap_result: str | None = Field(default=None, sa_column=Column(Text))
    content_result: str | None = Field(default=None, sa_column=Column(Text))
    code_result: str | None = Field(default=None, sa_column=Column(Text))
    quiz_result: str | None = Field(default=None, sa_column=Column(Text))
    reading_result: str | None = Field(default=None, sa_column=Column(Text))
    media_result: str | None = Field(default=None, sa_column=Column(Text))
    ppt_result: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.now)
