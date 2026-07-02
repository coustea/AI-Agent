"""阅读智能体 — 基于教学蓝图生成拓展阅读材料（使用搜索获取真实 URL）。

支持重试：首次生成资源不足时自动重试一次，合并两次结果。
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    assigned_outline_ids,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)

# 重试配置
MAX_RETRY_ATTEMPTS = 2  # 最多运行次数（首次 + 1 次重试）
MIN_RESOURCES_THRESHOLD = 2  # 低于此数量触发重试


class ReadingResource(BaseModel):
    """单个阅读资源：书籍/论文/文章/文档/实践项目。"""
    id: str = Field(description="资源编号，如 R1")
    type: str = Field(description="资源类型，如 book/paper/article/documentation/practice_project")
    title: str = Field(description="资源标题")
    authors: list[str] = Field(default_factory=list)
    url: str = Field(description="资源链接，必须是有效的 http/https URL")
    language: str = "中文"
    difficulty: str = "medium"
    suitable_for: str = ""
    related_knowledge_points: list[str] = Field(default_factory=list)
    description: str = ""
    recommend_reason: str = ""
    how_to_use: str = ""
    estimated_time: str = ""
    note: str = ""


class ReadingPathStep(BaseModel):
    """阅读路径中的一个步骤。"""
    step: int
    title: str
    description: str = ""
    resource_ids: list[str] = Field(default_factory=list)
    goal: str = ""


class ReadingPayload(BaseModel):
    """LLM 结构化输出模型：完整拓展阅读推荐。"""
    title: str = "拓展阅读推荐"
    summary: str = ""
    resources: list[ReadingResource] = Field(default_factory=list)
    learning_path: list[ReadingPathStep] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)


@register_agent
class ReadingAgent(BaseResourceAgent):
    """基于教学蓝图生成拓展阅读材料。"""

    agent_id = "reading"
    agent_name = "阅读生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        parts = build_resource_context(input_data)
        input_text = "\n\n".join(parts)
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_reading(
            input_text=input_text,
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        try:
            reading_data = json.loads(result.content)
            resource_titles = [
                item.get("title")
                for item in reading_data.get("resources", [])
                if isinstance(item, dict) and item.get("title")
            ]
        except Exception:
            resource_titles = []
        outline_ids = assigned_outline_ids(input_data.teaching_plan, "reading")
        handoff = build_basic_handoff(
            source_agent="reading",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            covered_outline_ids=outline_ids,
            examples=resource_titles[:6],
        )
        result.downstream_context = handoff
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        parts = build_node_context(input_data)
        input_text = "\n\n".join(parts)
        result = await self._generate_reading(
            input_text=input_text,
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emitter.send(self.agent_id, "completed" if result.success else "failed", result.summary if result.success else (result.error or f"{self.agent_name}生成失败"), 100 if result.success else 0)
        return result

    async def _generate_reading(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
        """内部方法 — 使用搜索获取真实 URL，然后生成拓展阅读推荐。

        流程：
        1. 根据知识点构建搜索查询
        2. 使用 Tavily/DuckDuckGo 搜索获取真实 URL
        3. 基于搜索结果生成阅读推荐
        4. 资源不足时自动重试一次，合并两次结果
        """
        reading_depth = config.get("reading_depth") or config.get("reading_type") or "course_extended"
        min_items = max(2, config.get("min_items", 3))  # 至少 2-3 条
        max_items = config.get("max_items", 5)
        language_preference = config.get("language_preference") or "chinese"

        await self.emitter.send(self.agent_id, "running", "正在搜索相关阅读资源...", 25)

        # 步骤 1: 构建搜索查询
        search_queries = self._build_search_queries(input_text, title_prefix, language_preference)
        logger.info(
            "Agent[reading] 步骤: 构建搜索查询 queries=%d min_items=%d",
            len(search_queries), min_items
        )

        # 步骤 2: 执行搜索获取真实 URL
        search_results = await self._search_resources(search_queries, min_items)

        # 步骤 3: 带重试的 LLM 生成阅读推荐
        best_data: dict | None = None
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            is_retry = attempt > 1
            if is_retry:
                await self.emitter.send(
                    self.agent_id, "running",
                    f"首次生成资源不足，正在第 {attempt} 次重试...", 55,
                )
                # 重试时重新搜索以获取更多素材
                retry_queries = self._build_retry_queries(input_text, title_prefix, language_preference)
                extra_results = await self._search_resources(retry_queries, min_items)
                # 合并搜索结果并去重
                existing_urls = {r.get("url") for r in search_results}
                for r in extra_results:
                    if r.get("url") and r["url"] not in existing_urls:
                        search_results.append(r)
                        existing_urls.add(r["url"])
                logger.info(
                    "Agent[reading] 重试: 合并搜索结果 total=%d", len(search_results)
                )

            if not search_results:
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.warning("Agent[reading] 搜索结果为空，准备重试")
                    continue
                return AgentResult(
                    success=False,
                    error=f"搜索结果为空，无法生成阅读资源（已重试 {attempt} 次）",
                    title=f"{title_prefix} - 拓展阅读",
                    summary="搜索资源失败",
                    file_type="json",
                    metadata={"agent_id": "reading", "error_type": "empty_search_results"},
                )

            prompt = prompts.get("resource").get("reading")
            enhanced_input = self._build_enhanced_input(
                search_results, input_text, config,
                is_retry=is_retry,
            )

            logger.info(
                "Agent[reading] 步骤: 调用 LLM 生成阅读推荐 (attempt=%d/%d), search_results=%d",
                attempt, MAX_RETRY_ATTEMPTS, len(search_results),
            )
            await self.emitter.send(
                self.agent_id, "running",
                f"正在调用AI大模型提炼拓展阅读推荐（第 {attempt} 次）...",
                60 if not is_retry else 70,
            )
            result = await self.llm.ainvoke_json(
                ReadingPayload,
                f"{prompt}\n\n{enhanced_input}",
                temperature=INFERENCE_TEMPERATURE,
            )
            attempt_data = result.model_dump(mode="json")
            attempt_resources = attempt_data.get("resources", [])

            if best_data is None:
                best_data = attempt_data
            else:
                # 合并两次结果：去重并追加新资源
                best_data = _merge_reading_results(best_data, attempt_data)

            merged_count = len(best_data.get("resources", []))
            logger.info(
                "Agent[reading] attempt=%d resources=%d merged_total=%d",
                attempt, len(attempt_resources), merged_count,
            )

            # 资源充足则提前结束
            if merged_count >= min_items:
                break

        if best_data is None:
            return AgentResult(
                success=False,
                error="阅读资源生成失败：多次尝试均未产出结果",
                title=f"{title_prefix} - 拓展阅读",
                summary="生成失败",
                file_type="json",
                metadata={"agent_id": "reading", "error_type": "all_attempts_failed"},
            )

        # 最终校验：合并后仍不足则返回失败
        resources = best_data.get("resources", [])
        if not resources:
            return AgentResult(
                success=False,
                error="阅读资源生成失败：合并后仍无有效资源",
                title=f"{title_prefix} - 拓展阅读",
                summary="生成失败",
                file_type="json",
                metadata={"agent_id": "reading", "error_type": "no_resources_after_merge"},
            )

        content = json.dumps(best_data, ensure_ascii=False, indent=2)
        logger.info(
            "Agent[reading] 步骤: 阅读资源生成完成, resources=%d path_steps=%d",
            len(resources),
            len(best_data.get("learning_path", [])),
        )

        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=best_data.get("title") or f"{title_prefix} - 拓展阅读",
            summary=best_data.get("summary") or f"生成 {len(resources)} 条拓展阅读材料",
            metrics={
                "resource_count": len(resources),
                "search_results_used": len(search_results),
                "reading_depth": reading_depth,
                "language_preference": language_preference,
            },
            metadata={
                "agent_id": "reading",
                "reading_depth": reading_depth,
                "min_items": min_items,
                "max_items": max_items,
                "language_preference": language_preference,
                "search_queries": search_queries[:3],
            },
        )

    def _build_retry_queries(
        self,
        input_text: str,
        title_prefix: str,
        language_preference: str,
    ) -> list[str]:
        """构建重试时的差异化搜索查询，避免与首次查询重复。"""
        queries = []
        if language_preference == "chinese":
            queries.append(f"{title_prefix} 入门指南 推荐")
            queries.append(f"{title_prefix} 实战项目 案例")
        else:
            queries.append(f"{title_prefix} beginner guide recommended")
            queries.append(f"{title_prefix} hands-on project tutorial")
        queries.append(f"{title_prefix} 拓展阅读 书单")
        return queries[:3]

    def _build_search_queries(
        self,
        input_text: str,
        title_prefix: str,
        language_preference: str
    ) -> list[str]:
        """构建搜索查询列表。"""
        queries = []

        # 从输入文本中提取关键知识点
        # 使用标题作为主要查询
        queries.append(f"{title_prefix} 教程")
        queries.append(f"{title_prefix} 学习资源")

        # 根据语言偏好调整查询
        if language_preference == "chinese":
            queries.append(f"{title_prefix} 中文教程")
        else:
            queries.append(f"{title_prefix} tutorial")

        return queries[:5]  # 最多 5 个查询

    async def _search_resources(
        self,
        queries: list[str],
        min_items: int
    ) -> list[dict]:
        """执行搜索获取真实资源 URL。"""
        results = []

        for query in queries:
            try:
                # 使用基类内置的统一搜索工具调用
                search_text = await self.search(query)

                # 解析搜索结果
                parsed = self._parse_search_results(search_text)
                results.extend(parsed)

                logger.info(
                    "Agent[reading] 搜索完成: query=%s results=%d",
                    query, len(parsed)
                )

                # 如果已经获取足够的资源，停止搜索
                if len(results) >= min_items * 2:
                    break

            except Exception as e:
                logger.warning("Agent[reading] 搜索异常: query=%s error=%s", query, e)
                continue

        # 去重（按 URL）
        unique_results = []
        seen_urls = set()
        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                unique_results.append(result)
                seen_urls.add(url)

        return unique_results

    def _parse_search_results(self, search_text: str) -> list[dict]:
        """解析搜索结果文本为结构化数据。"""
        results = []

        # 搜索结果格式："{index}. {title}\n   链接: {url}\n   摘要: {snippet}"
        lines = search_text.split("\n")

        current_result = {}
        for line in lines:
            line = line.strip()

            # 匹配标题行（数字开头）
            if line and line[0].isdigit() and ". " in line:
                if current_result and current_result.get("url"):
                    results.append(current_result)
                current_result = {}
                # 提取标题
                title = line.split(". ", 1)[-1]
                current_result["title"] = title

            # 匹配链接行
            elif "链接:" in line or "链接 :" in line:
                url = line.split("链接:")[-1].split("链接 :")[-1].strip()
                if url.startswith("http"):
                    current_result["url"] = url

            # 匹配摘要行
            elif "摘要:" in line or "摘要 :" in line:
                snippet = line.split("摘要:")[-1].split("摘要 :")[-1].strip()
                current_result["snippet"] = snippet

        # 添加最后一个结果
        if current_result and current_result.get("url"):
            results.append(current_result)

        return results

    def _build_enhanced_input(
        self,
        search_results: list[dict],
        original_input: str,
        config: dict,
        is_retry: bool = False,
    ) -> str:
        """构建增强的输入，包含真实搜索结果。"""
        parts = [original_input]

        # 添加搜索结果作为真实资源来源
        parts.append("\n## 搜索获取的真实资源（必须使用这些 URL）")
        if is_retry:
            parts.append("这是重试生成，请务必产出更多高质量阅读资源，避免与已有资源重复。\n")
        parts.append("以下是搜索到的真实学习资源，请基于这些资源生成阅读推荐：\n")

        for i, result in enumerate(search_results[:10], 1):
            title = result.get("title", "未知标题")
            url = result.get("url", "")
            snippet = result.get("snippet", "")

            parts.append(f"{i}. **{title}**")
            parts.append(f"   - URL: {url}")
            if snippet:
                parts.append(f"   - 摘要: {snippet[:200]}")
            parts.append("")

        # 添加明确要求
        min_items = max(2, config.get("min_items", 3))
        parts.append(f"\n**重要要求**：")
        parts.append(f"1. 必须生成至少 {min_items} 条阅读资源")
        parts.append(f"2. 每条资源的 URL 必须来自上面的搜索结果（真实 URL）")
        parts.append(f"3. 不要虚构或生成假的 URL")
        parts.append(f"4. 资源类型要多样化：书籍、论文、文章、文档、实践项目等")
        parts.append(f"5. 每条资源必须包含可点击跳转的完整 http/https URL")
        if is_retry:
            parts.append(f"6. 【重试】请确保生成足够数量的资源，不要遗漏")

        return "\n".join(parts)


def _merge_reading_results(primary: dict, secondary: dict) -> dict:
    """合并两次阅读生成结果，去重并保留完整资源。

    Args:
        primary: 首次生成结果（作为基础）
        secondary: 重试生成结果（追加到 primary）

    Returns:
        合并后的结果字典
    """
    # 合并 resources：按 URL 去重
    primary_resources = primary.get("resources", [])
    secondary_resources = secondary.get("resources", [])

    existing_urls = {r.get("url", "").strip().lower() for r in primary_resources if r.get("url")}
    existing_titles = {r.get("title", "").strip().lower() for r in primary_resources if r.get("title")}

    # 重新编号追加的资源
    max_id = 0
    for r in primary_resources:
        rid = r.get("id", "R0")
        try:
            num = int(rid.replace("R", ""))
            max_id = max(max_id, num)
        except (ValueError, AttributeError):
            pass

    for r in secondary_resources:
        url = r.get("url", "").strip().lower()
        title = r.get("title", "").strip().lower()
        # URL 或标题重复则跳过
        if url and url in existing_urls:
            continue
        if title and title in existing_titles:
            continue
        # 重新编号
        max_id += 1
        r["id"] = f"R{max_id}"
        primary_resources.append(r)
        if url:
            existing_urls.add(url)
        if title:
            existing_titles.add(title)

    primary["resources"] = primary_resources

    # 合并 learning_path：追加新步骤
    primary_path = primary.get("learning_path", [])
    secondary_path = secondary.get("learning_path", [])
    if secondary_path:
        max_step = max((s.get("step", 0) for s in primary_path), default=0)
        for step in secondary_path:
            max_step += 1
            step["step"] = max_step
            primary_path.append(step)
        primary["learning_path"] = primary_path

    # 合并 follow_up_suggestions：去重追加
    primary_suggestions = primary.get("follow_up_suggestions", [])
    secondary_suggestions = secondary.get("follow_up_suggestions", [])
    existing_suggestions = set(primary_suggestions)
    for s in secondary_suggestions:
        if s not in existing_suggestions:
            primary_suggestions.append(s)
            existing_suggestions.add(s)
    primary["follow_up_suggestions"] = primary_suggestions

    # 更新 summary
    primary["summary"] = (
        primary.get("summary", "")
        or secondary.get("summary", "")
        or f"生成 {len(primary_resources)} 条拓展阅读材料"
    )

    return primary
