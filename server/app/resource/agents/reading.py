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
    build_node_context,
    build_resource_context,
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


# LLM 输出包装类（ainvoke_json 要求 BaseModel 子类）
class ReadingPayload(BaseModel):
    """阅读资源列表 — LLM 结构化输出容器。"""
    resources: list[ReadingResource] = Field(description="推荐的阅读资源列表")


@register_agent
class ReadingAgent(BaseResourceAgent):
    """基于教学蓝图生成拓展阅读材料。"""

    agent_id = "reading"
    agent_name = "拓展阅读"

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
        reading_depth = config.get("reading_depth") or "course_extended"
        max_items = config.get("max_items", 5)
        min_items = max(2, max_items // 2)  # 至少生成 max_items 的一半
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
        best_resources: list[ReadingResource] | None = None
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
                f"正在提炼拓展阅读推荐（第 {attempt} 次）...",
                60 if not is_retry else 70,
            )
            result = await self.llm.ainvoke_json(
                ReadingPayload,
                f"{prompt}\n\n{enhanced_input}",
                temperature=INFERENCE_TEMPERATURE,
            )
            attempt_resources = result.resources

            if best_resources is None:
                best_resources = list(attempt_resources)
            else:
                # 合并两次结果：去重并追加新资源
                best_resources = _merge_reading_resources(best_resources, list(attempt_resources))

            merged_count = len(best_resources)
            logger.info(
                "Agent[reading] attempt=%d resources=%d merged_total=%d",
                attempt, len(attempt_resources), merged_count,
            )

            # 资源充足则提前结束
            if merged_count >= min_items:
                break

        if best_resources is None:
            return AgentResult(
                success=False,
                error="阅读资源生成失败：多次尝试均未产出结果",
                title=f"{title_prefix} - 拓展阅读",
                summary="生成失败",
                file_type="json",
                metadata={"agent_id": "reading", "error_type": "all_attempts_failed"},
            )

        # 最终校验：合并后仍不足则返回失败
        if not best_resources:
            return AgentResult(
                success=False,
                error="阅读资源生成失败：合并后仍无有效资源",
                title=f"{title_prefix} - 拓展阅读",
                summary="生成失败",
                file_type="json",
                metadata={"agent_id": "reading", "error_type": "no_resources_after_merge"},
            )

        # 序列化为 JSON
        content = json.dumps(
            [r.model_dump(mode="json") for r in best_resources],
            ensure_ascii=False,
            indent=2,
        )
        logger.info(
            "Agent[reading] 步骤: 阅读资源生成完成, resources=%d",
            len(best_resources),
        )

        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - 拓展阅读",
            summary=f"生成 {len(best_resources)} 条拓展阅读材料",
            metrics={
                "resource_count": len(best_resources),
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
        max_items = config.get("max_items", 5)
        min_items = max(2, max_items // 2)
        parts.append(f"\n**重要要求**：")
        parts.append(f"1. 必须生成至少 {min_items} 条阅读资源")
        parts.append(f"2. 每条资源的 URL 必须来自上面的搜索结果（真实 URL）")
        parts.append(f"3. 不要虚构或生成假的 URL")
        parts.append(f"4. 资源类型要多样化：书籍、论文、文章、文档、实践项目等")
        parts.append(f"5. 每条资源必须包含可点击跳转的完整 http/https URL")
        parts.append(
            f"6. 【严禁】resources 为空数组 []。"
            f"你必须生成至少 {min_items} 条阅读资源，缺少任何一条都是错误。"
        )
        if is_retry:
            parts.append(
                "7. 【错误反馈】你上一次返回了 resources: []（空数组），这是严重错误。"
                "resources 绝不能为空数组 []，必须包含至少一条阅读资源。"
            )

        return "\n".join(parts)


def _merge_reading_resources(
    primary: list[ReadingResource],
    secondary: list[ReadingResource],
) -> list[ReadingResource]:
    """合并两次阅读生成结果，去重并保留完整资源。

    Args:
        primary: 首次生成结果（作为基础）
        secondary: 重试生成结果（追加到 primary）

    Returns:
        合并后的资源列表
    """
    # 按 URL 和 title 去重
    existing_urls = {r.url.strip().lower() for r in primary if r.url}
    existing_titles = {r.title.strip().lower() for r in primary if r.title}

    # 重新编号追加的资源
    max_id_num = 0
    for r in primary:
        if r.id.startswith("R"):
            try:
                num = int(r.id[1:])
                max_id_num = max(max_id_num, num)
            except ValueError:
                pass

    merged = list(primary)
    for r in secondary:
        url_lower = r.url.strip().lower() if r.url else ""
        title_lower = r.title.strip().lower() if r.title else ""

        # 去重检查
        if url_lower and url_lower in existing_urls:
            continue
        if title_lower and title_lower in existing_titles:
            continue

        # 重新编号
        max_id_num += 1
        new_id = f"R{max_id_num}"

        # 创建新的资源对象（更新 id）
        merged_resource = ReadingResource(
            id=new_id,
            type=r.type,
            title=r.title,
            authors=r.authors,
            url=r.url,
            language=r.language,
            difficulty=r.difficulty,
            suitable_for=r.suitable_for,
            related_knowledge_points=r.related_knowledge_points,
            description=r.description,
            recommend_reason=r.recommend_reason,
            how_to_use=r.how_to_use,
            estimated_time=r.estimated_time,
            note=r.note,
        )
        merged.append(merged_resource)

        if url_lower:
            existing_urls.add(url_lower)
        if title_lower:
            existing_titles.add(title_lower)

    return merged
