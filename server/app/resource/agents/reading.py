"""
阅读推荐 Agent — 搜索并推荐学习资源。

6 步流程: 分析 → 融合 → 提取关键词 → 搜索资源 → 验证筛选 → 整理输出
"""

from __future__ import annotations

import json
import re

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.agents.base import Agent
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


class ReadingAgent(Agent):
    """阅读推荐 Agent。"""

    AGENT_NAME = "reading"
    ROLE_NAME = "阅读推荐智能体"
    STEPS = ["分析输入", "融合画像与依赖", "提取搜索关键词", "搜索资源", "验证筛选", "整理输出"]

    def _default_template_values(self) -> dict[str, str]:
        return {
            "reading_depth": "course_extended",
            "max_items": "5",
            "resource_quality": "balanced",
            "include_practice_instruction": "包含实践资源",
            "language_preference": "chinese",
        }

    def _resolve_template_variables(self, variables: set, state: WorkerState) -> dict[str, str]:
        """Reading Agent 特殊变量解析。"""
        result = super()._resolve_template_variables(variables, state)
        config = state.agent_config or {}

        if "include_practice_instruction" in variables:
            result["include_practice_instruction"] = "包含实践练习资源" if config.get("include_practice", True) else "不包含实践资源"

        return result

    async def _generate(self, state: WorkerState, prompt: str, input_text: str) -> WorkerResult:
        llm = get_llm_manager()

        # Step 3: 提取搜索关键词
        await self._emit(
            state, "extract_keywords", f"{self.ROLE_NAME}正在提取搜索关键词",
            step=3, total=7, step_label=self.STEPS[2],
        )
        keywords = await self._extract_keywords(llm, state, input_text)

        # Step 4: 搜索资源
        await self._emit(
            state, "search_resources", f"{self.ROLE_NAME}正在搜索学习资源",
            step=4, total=7, step_label=self.STEPS[3],
        )
        raw_resources = await self._search_resources(keywords, state)

        # Step 5: 验证筛选
        await self._emit(
            state, "validate_filter", f"{self.ROLE_NAME}正在验证和筛选资源",
            step=5, total=7, step_label=self.STEPS[4],
        )
        filtered = self._validate_and_filter(raw_resources, state)

        # Step 6: 整理输出
        await self._emit(
            state, "finalize_output", f"{self.ROLE_NAME}正在整理输出 ({len(filtered)} 条资源)",
            step=6, total=7, step_label=self.STEPS[5],
        )

        content = json.dumps(filtered, ensure_ascii=False, indent=2)

        summary_data = {
            "total_items": len(filtered),
            "reading_depth": state.agent_config.get("reading_depth", "course_extended"),
            "language_preference": state.agent_config.get("language_preference", "chinese"),
        }

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=self._title(state, "阅读推荐"),
            summary=f"推荐 {len(filtered)} 条学习资源",
            summary_data=summary_data,
            metadata={
                "engine": "reading_json",
                "total_items": len(filtered),
                "keywords_used": keywords,
                "agent_id": "reading",
            },
        )

    async def _extract_keywords(self, llm, state: WorkerState, input_text: str) -> list[str]:
        """使用 LLM 提取搜索关键词。"""
        lang_pref = state.agent_config.get("language_preference", "chinese")
        prompt_text = (
            f"请从以下学习需求中提取 3-5 个用于搜索学习资源的关键词。\n"
            f"语言偏好: {lang_pref}\n\n"
            f"{input_text}\n\n"
            f"请以 JSON 数组格式输出关键词，例如: [\"关键词1\", \"关键词2\"]"
        )

        try:
            response = await llm.generate(prompt_text, model_kwargs={"temperature": 0.2})
            raw = response.content if hasattr(response, "content") else str(response)
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                keywords = json.loads(match.group())
                if isinstance(keywords, list):
                    return [str(k) for k in keywords][:5]
        except Exception as exc:
            logger.warning("[ReadingAgent] 关键词提取失败: %s", exc)

        need = state.task.get("learning_need", "") or ""
        return [need[:20]] if need else ["学习资源"]

    async def _search_resources(self, keywords: list[str], state: WorkerState) -> list[dict]:
        """搜索外部学习资源。"""
        max_items = state.agent_config.get("max_items", 5)
        resources: list[dict] = []

        try:
            from langchain_community.tools import DuckDuckGoSearchResults
            for kw in keywords[:3]:
                if len(resources) >= max_items:
                    break
                search = DuckDuckGoSearchResults(max_results=max_items)
                results = search.run(kw)
                if isinstance(results, str):
                    items = self._parse_ddg_results(results)
                    resources.extend(items[:max_items - len(resources)])
        except ImportError:
            logger.warning("[ReadingAgent] DuckDuckGo 工具未安装，跳过搜索")
        except Exception as exc:
            logger.warning("[ReadingAgent] 搜索失败: %s", exc)

        if len(resources) < max_items:
            llm_recs = await self._llm_recommend(keywords, state, max_items - len(resources))
            resources.extend(llm_recs)

        return resources[:max_items]

    async def _llm_recommend(self, keywords: list[str], state: WorkerState, count: int) -> list[dict]:
        """使用 LLM 推荐学习资源 (搜索不足时的补充)。"""
        llm = get_llm_manager()
        lang_pref = state.agent_config.get("language_preference", "chinese")
        quality = state.agent_config.get("resource_quality", "balanced")

        prompt_text = (
            f"请推荐 {count} 个与以下关键词相关的学习资源 (书籍、论文、在线课程等)。\n"
            f"关键词: {', '.join(keywords)}\n"
            f"语言偏好: {lang_pref}\n"
            f"资源质量: {quality}\n\n"
            f"请以 JSON 数组格式输出，每项包含 title, author, type, description, url 字段。"
        )

        try:
            response = await llm.generate(prompt_text, model_kwargs={"temperature": 0.3})
            raw = response.content if hasattr(response, "content") else str(response)
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                items = json.loads(match.group())
                if isinstance(items, list):
                    return items[:count]
        except Exception as exc:
            logger.warning("[ReadingAgent] LLM 推荐失败: %s", exc)

        return []

    def _validate_and_filter(self, resources: list[dict], state: WorkerState) -> list[dict]:
        """验证和筛选资源。"""
        include_practice = state.agent_config.get("include_practice", True)
        filtered = []

        for r in resources:
            if not isinstance(r, dict):
                continue
            if not r.get("title"):
                continue
            if not include_practice and r.get("type") in ("练习", "实践", "practice"):
                continue
            filtered.append(r)

        return filtered

    def _parse_ddg_results(self, results_str: str) -> list[dict]:
        """解析 DuckDuckGo 搜索结果字符串。"""
        items: list[dict] = []
        entries = re.split(r",\s*(?=snippet:)", results_str)
        for entry in entries:
            title_match = re.search(r"title:\s*(.*?)(?:,\s*link:|$)", entry)
            link_match = re.search(r"link:\s*(.*?)(?:,\s*snippet:|$)", entry)
            snippet_match = re.search(r"snippet:\s*(.*?)$", entry)

            if title_match:
                items.append({
                    "title": title_match.group(1).strip(),
                    "url": link_match.group(1).strip() if link_match else "",
                    "description": snippet_match.group(1).strip() if snippet_match else "",
                    "type": "web",
                })
        return items

    def _input_suffix(self) -> str:
        return "请推荐学习资源。"