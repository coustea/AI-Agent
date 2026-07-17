"""阅读资源的唯一结构化输出契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReadingResource(BaseModel):
    """一条可直接在资源页展示的阅读建议。"""

    model_config = ConfigDict(extra="forbid")

    type: Literal["book", "paper", "article", "documentation", "practice_project"]
    title: str = Field(min_length=1, max_length=160)
    authors: list[str] = Field(default_factory=list, max_length=6)
    url: str = Field(min_length=8, max_length=2_000)
    difficulty: Literal["basic", "medium", "advanced"]
    description: str = Field(min_length=1, max_length=360)
    recommend_reason: str = Field(min_length=1, max_length=240)

    @field_validator("title", "description", "recommend_reason")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("文本字段不能为空")
        return value

    @field_validator("authors")
    @classmethod
    def clean_authors(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value and value.strip()]

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("url must use the http or https scheme")
        return normalized


class ReadingPayload(BaseModel):
    """Reading Agent 唯一允许返回的 JSON 对象。"""

    model_config = ConfigDict(extra="forbid")

    resources: list[ReadingResource] = Field(min_length=1, max_length=10)
