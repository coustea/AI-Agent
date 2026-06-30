"""编程题爬虫基类与统一数据模型。"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


@dataclass
class ProgrammingProblem:
    """统一的编程题数据模型。"""

    question_id: str
    source: str  # leetcode / luogu / nowcoder
    platform_question_id: str
    title: str
    title_en: str | None = None
    content: str = ""
    difficulty: str | None = None
    subject: str | None = None
    # 代码模板: {language: str}
    code_templates: dict[str, str] = field(default_factory=dict)
    supported_languages: list[str] = field(default_factory=list)
    # 示例测试用例
    example_test_cases: list[dict[str, Any]] = field(default_factory=list)
    # 隐藏测试用例(判题用)
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    time_limit: int | None = None  # ms
    memory_limit: int | None = None  # MB
    tags: list[str] = field(default_factory=list)
    knowledge_points: list[str] = field(default_factory=list)
    acceptance_rate: float | None = None
    total_submissions: int | None = None
    total_accepted: int | None = None
    url: str | None = None
    solution: dict[str, Any] = field(default_factory=dict)  # 官方题解
    raw_record: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "source": self.source,
            "platform_question_id": self.platform_question_id,
            "title": self.title,
            "title_en": self.title_en,
            "content": self.content,
            "difficulty": self.difficulty,
            "subject": self.subject,
            "code_templates": self.code_templates,
            "supported_languages": self.supported_languages,
            "example_test_cases": self.example_test_cases,
            "test_cases": self.test_cases,
            "time_limit": self.time_limit,
            "memory_limit": self.memory_limit,
            "tags": self.tags,
            "knowledge_points": self.knowledge_points,
            "acceptance_rate": self.acceptance_rate,
            "total_submissions": self.total_submissions,
            "total_accepted": self.total_accepted,
            "url": self.url,
            "solution": self.solution,
            "raw_record": self.raw_record,
        }


class BaseCrawler(ABC):
    """爬虫基类。"""

    def __init__(self, output_dir: str | Path, delay: float = 1.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    @abstractmethod
    def crawl(self, limit: int | None = None) -> list[ProgrammingProblem]:
        """爬取题目，返回题目列表。"""

    def save(self, problems: list[ProgrammingProblem], filename: str | None = None) -> Path:
        """保存爬取的题目到 JSON 文件。"""
        if filename is None:
            filename = f"{self.source_name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        data = [p.to_dict() for p in problems]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[Crawler] 已保存 {len(problems)} 道题到 {filepath}")
        return filepath

    @property
    @abstractmethod
    def source_name(self) -> str:
        """来源平台名称。"""
