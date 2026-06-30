"""LeetCode 编程题爬虫。"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests


@dataclass
class ProgrammingProblem:
    """统一的编程题数据模型。"""

    question_id: str
    source: str
    platform_question_id: str
    title: str
    title_en: str | None = None
    content: str = ""
    difficulty: str | None = None
    subject: str | None = None
    code_templates: dict[str, str] = field(default_factory=dict)
    supported_languages: list[str] = field(default_factory=list)
    example_test_cases: list[dict[str, Any]] = field(default_factory=list)
    test_cases: list[dict[str, Any]] = field(default_factory=list)
    time_limit: int | None = None
    memory_limit: int | None = None
    tags: list[str] = field(default_factory=list)
    knowledge_points: list[str] = field(default_factory=list)
    acceptance_rate: float | None = None
    total_submissions: int | None = None
    total_accepted: int | None = None
    url: str | None = None
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
            "raw_record": self.raw_record,
        }


class LeetCodeCrawler:
    """LeetCode 中文站爬虫。"""

    BASE_URL = "https://leetcode.cn"

    def __init__(self, output_dir: str | Path = "./leetcode", delay: float = 2.0):
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
            "Referer": "https://leetcode.cn/problemset/",
            "Origin": "https://leetcode.cn",
        })

    def save(self, problems: list[ProgrammingProblem], filename: str | None = None) -> Path:
        """保存爬取的题目到 JSON 文件。"""
        if filename is None:
            filename = f"leetcode_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        data = [p.to_dict() for p in problems]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[Crawler] 已保存 {len(problems)} 道题到 {filepath}")
        return filepath

    def _get_problem_data(self, title_slug: str) -> dict[str, Any]:
        """获取题目详细数据（包含官方题解）。"""
        url = f"{self.BASE_URL}/graphql"
        query = {
            "query": """
            query questionData($titleSlug: String!) {
              question(titleSlug: $titleSlug) {
                questionId
                title
                titleSlug
                content
                translatedTitle
                translatedContent
                difficulty
                stats
                codeSnippets {
                  lang
                  langSlug
                  code
                }
                topicTags {
                  name
                  slug
                  translatedName
                }
                exampleTestcases
                sampleTestCase
                solution {
                  id
                  title
                  content
                  url
                }
              }
            }
            """,
            "variables": {"titleSlug": title_slug},
            "operationName": "questionData",
        }
        resp = self.session.post(url, json=query, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("question", {})

    def _parse_test_cases(self, detail: dict[str, Any]) -> list[dict[str, Any]]:
        """解析示例测试用例。"""
        test_cases = []
        example_testcases = detail.get("exampleTestcases", "")
        if example_testcases:
            lines = example_testcases.strip().split("\n")
            i = 0
            while i < len(lines) - 1:
                inp = lines[i].strip()
                out = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if inp and out:
                    test_cases.append({
                        "input": inp,
                        "output": out,
                        "explanation": "",
                    })
                    i += 2
                else:
                    i += 1
        return test_cases

    def _parse_code_templates(self, detail: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
        """解析代码模板。"""
        templates = {}
        languages = []
        snippets = detail.get("codeSnippets", [])
        for snippet in snippets:
            lang = snippet.get("langSlug", "")
            code = snippet.get("code", "")
            if lang and code:
                templates[lang] = code
                languages.append(lang)
        return templates, languages

    def _parse_stats(self, stats_str: str | None) -> tuple[float | None, int | None, int | None]:
        """解析统计信息。"""
        if not stats_str:
            return None, None, None
        try:
            stats = json.loads(stats_str)
            total = stats.get("totalSubmissionRaw", 0)
            accepted = stats.get("totalAcceptedRaw", 0)
            rate = (accepted / total * 100) if total > 0 else None
            return rate, total, accepted
        except Exception:
            return None, None, None

    def crawl(self, limit: int | None = None) -> list[ProgrammingProblem]:
        """爬取 LeetCode 题目。"""
        problems: list[ProgrammingProblem] = []
        target_limit = limit or 999999

        print(f"[LeetCode] 开始爬取题目...")

        # 获取题目列表
        try:
            url = f"{self.BASE_URL}/api/problems/all/"
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            all_problems = data.get("stat_status_pairs", [])
            print(f"[LeetCode] 获取到 {len(all_problems)} 道题目")
        except Exception as exc:
            print(f"[LeetCode] 获取列表失败: {exc}")
            return problems

        for i, item in enumerate(all_problems):
            if len(problems) >= target_limit:
                break

            stat = item.get("stat", {})
            frontend_id = stat.get("frontend_question_id", "")
            title_slug = stat.get("question__title_slug", "")

            if not title_slug:
                continue

            # 跳过付费题
            if item.get("paid_only", False):
                print(f"  [跳过] 付费题: {frontend_id}")
                continue

            try:
                detail = self._get_problem_data(title_slug)
                time.sleep(self.delay)
            except Exception as exc:
                print(f"  [错误] 获取详情失败: {title_slug} - {exc}")
                continue

            if not detail:
                continue

            # 解析内容
            content = detail.get("translatedContent") or detail.get("content", "")
            title = detail.get("translatedTitle") or detail.get("title", "")
            title_en = detail.get("title", "")

            # 解析代码模板
            templates, languages = self._parse_code_templates(detail)

            # 解析测试用例
            test_cases = self._parse_test_cases(detail)

            # 解析统计
            stats_str = detail.get("stats")
            rate, total, accepted = self._parse_stats(stats_str)

            # 解析标签
            tags = []
            knowledge_points = []
            for tag in detail.get("topicTags", []):
                tag_name = tag.get("translatedName") or tag.get("name", "")
                if tag_name:
                    tags.append(tag_name)
                    knowledge_points.append(tag_name)

            difficulty_map = {"Easy": "简单", "Medium": "中等", "Hard": "困难"}
            raw_difficulty = item.get("difficulty", {})
            if isinstance(raw_difficulty, dict):
                difficulty_level = raw_difficulty.get("level", "")
            else:
                difficulty_level = raw_difficulty
            difficulty = difficulty_map.get(difficulty_level, difficulty_level)

            problem = ProgrammingProblem(
                question_id=f"lc_{frontend_id}",
                source="leetcode",
                platform_question_id=str(frontend_id),
                title=title,
                title_en=title_en,
                content=content,
                difficulty=difficulty,
                subject="算法",
                code_templates=templates,
                supported_languages=languages,
                example_test_cases=test_cases,
                test_cases=[],
                time_limit=1000,
                memory_limit=256,
                tags=tags,
                knowledge_points=knowledge_points,
                acceptance_rate=rate,
                total_submissions=total,
                total_accepted=accepted,
                url=f"https://leetcode.cn/problems/{title_slug}/",
                raw_record={"detail": detail, "list_item": item},
            )
            solution_count = 1 if detail.get("solution") else 0
            has_solution = "✓题解" if solution_count else ""
            print(f"  [OK] {frontend_id}. {title} ({difficulty}) {has_solution} - 标签: {', '.join(tags[:3])}")

        print(f"[LeetCode] 爬取完成，共 {len(problems)} 道题")
        return problems


def main():
    """命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="LeetCode 题目爬虫")
    parser.add_argument("-n", "--limit", type=int, default=None, help="最多爬取题目数")
    parser.add_argument("-d", "--delay", type=float, default=2.0, help="请求间隔(秒)")
    parser.add_argument("-o", "--output", type=str, default="./leetcode", help="输出目录")
    args = parser.parse_args()

    crawler = LeetCodeCrawler(output_dir=args.output, delay=args.delay)
    problems = crawler.crawl(limit=args.limit)
    if problems:
        crawler.save(problems, filename="leetcode_problems.json")


if __name__ == "__main__":
    main()
