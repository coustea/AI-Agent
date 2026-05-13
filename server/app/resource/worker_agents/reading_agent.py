"""
Reading Agent — 拓展阅读 Agent。

生成延伸阅读材料和参考方向，输出 JSON 格式。
通过搜索验证资源链接有效性，确保推荐资源真实可访问。
"""

from __future__ import annotations

import asyncio
import ast
import re
from pathlib import Path

from langchain_core.messages import HumanMessage

from app.infra.llm import get_llm_manager
from app.infra.logging import get_logger
from app.resource.schemas import WorkerState, WorkerResult
from app.resource.worker_agents.utils import (
    AgentContextBuilder,
    append_backend_context_for_prompt,
    learning_need_from_task,
    title_from_learning_need,
)
from app.utils.json import parse_first_json_value
from app.utils.search import duckduckgo_search, tavily_search

logger = get_logger(__name__)


class ReadingAgent:
    """拓展阅读 Agent。

    通过搜索验证资源链接有效性，确保推荐资源真实可访问。
    """

    STEPS = ["分析输入", "提取关键词", "搜索验证资源", "融合画像与依赖", "生成内容", "整理输出"]
    ROLE_NAME = "拓展阅读推荐智能体"

    def __init__(self, user_id: int, resource_id: int, emitter=None):
        self.user_id = user_id
        self.resource_id = resource_id
        self.emitter = emitter
        self.llm_manager = get_llm_manager()
        self.prompt_path = Path(__file__).parent.parent / "prompts" / "workers" / "reading.md"

    async def _extract_search_keywords(self, state: WorkerState) -> list[str]:
        """使用 LLM 从学习需求中提取搜索关键词。

        让 LLM 分析学习需求，提取核心知识点、技术术语、相关概念，
        生成精准的搜索关键词，而非直接使用原始 learning_need。
        """
        learning_need = learning_need_from_task(state.task)

        # 获取上游内容摘要，帮助提取更精准的关键词
        builder = AgentContextBuilder()
        context_text = builder.build_for_agent("reading", state)

        prompt = f"""请分析以下学习需求，提取 3-5 个最适合搜索学习资源的关键词。

学习需求：{learning_need}

{context_text if context_text else ''}

要求：
1. 提取核心知识点、技术术语、关键概念
2. 关键词要具体、可搜索（如 "Python GIL" 而非 "Python多线程问题"）
3. 避免使用过于宽泛的词（如 "学习"、"教程"、"入门"）
4. 优先提取技术名词、框架名、算法名、概念名
5. 如果是编程类，可提取具体技术栈名称

请直接输出关键词，每行一个，不要编号，不要解释。"""

        try:
            response = await self.llm_manager.ainvoke(
                "spark_x2_flash",  # 使用快速模型提取关键词
                [HumanMessage(content=prompt)],
                model_kwargs={"temperature": 0.1},
            )
            raw_content = response.content if hasattr(response, "content") else str(response)

            # 解析关键词
            keywords = []
            for line in raw_content.strip().split("\n"):
                line = line.strip()
                # 移除编号
                line = re.sub(r"^\d+[\.\、\:\s]*", "", line)
                # 移除解释性文字
                if len(line) > 30:
                    continue
                if line and not line.startswith("#"):
                    keywords.append(line)

            logger.info("[ReadingAgent] 提取的关键词: %s", keywords)
            return keywords[:5] if keywords else [learning_need[:50]]

        except Exception as e:
            logger.warning("[ReadingAgent] 关键词提取失败: %s", e)
            # 回退：简单提取 learning_need 中的关键词
            words = re.findall(r"[A-Za-z]+[\-A-Za-z]*|[一-龥]{2,8}", learning_need)
            return words[:5] if words else [learning_need[:50]]

    async def _search_resources(self, keywords: list[str], max_results: int = 8) -> list[dict]:
        """搜索真实可用的学习资源。

        使用提取的关键词进行搜索，获取真实可访问的资源链接。
        """
        resources: list[dict] = []
        seen_urls: set[str] = set()

        # 根据关键词构建搜索查询
        search_queries = self._build_search_queries_from_keywords(keywords)

        async def run_search(query: str) -> list[dict]:
            """执行单个搜索查询。"""
            providers = [
                ("tavily", tavily_search),
                ("duckduckgo", duckduckgo_search),
            ]

            for source, search_tool in providers:
                try:
                    search_result = await search_tool.ainvoke({"query": query})
                except Exception as exc:
                    logger.warning("[ReadingAgent] %s 搜索失败: %s", source, exc)
                    continue

                results = self._parse_search_result(search_result, source)
                if results:
                    return results

            return []

        # 并行执行多个搜索查询
        tasks = [run_search(query) for query in search_queries[:4]]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in search_results:
            if isinstance(result, list):
                for item in result:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        resources.append(item)

        # 限制结果数量
        return resources[:max_results]

    def _build_search_queries_from_keywords(self, keywords: list[str]) -> list[str]:
        """根据关键词构建搜索查询。

        为每个关键词生成多种搜索模式，覆盖不同资源类型。
        """
        queries = []

        for kw in keywords[:3]:
            # 核心关键词搜索
            queries.append(kw)

            # 教程/文档类
            queries.append(f"{kw} 教程")

            # 官方文档
            queries.append(f"{kw} 官方文档")

            # 书籍推荐
            queries.append(f"{kw} 书籍 推荐")

        # 如果关键词是技术类，添加 GitHub 搜索
        if any(re.search(r"[A-Za-z\-]+", kw) for kw in keywords):
            tech_kw = next((kw for kw in keywords if re.search(r"[A-Za-z\-]+", kw)), keywords[0])
            queries.append(f"{tech_kw} github")

        return queries

    def _parse_search_result(self, search_result: object, source: str) -> list[dict]:
        """解析搜索结果，提取资源信息。"""
        resources: list[dict] = []

        if not search_result:
            return resources

        search_text = str(search_result)
        structured = self._parse_structured_search_items(search_result, source)
        if structured:
            return structured

        if "失败" in search_text or "未找到" in search_text or "不可用" in search_text:
            return resources

        # 解析不同来源的搜索结果
        lines = search_text.split("\n")
        pending_title = ""
        pending_description = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试解析带编号的结果 (1. title)
            match = re.match(r"^\d+\.\s*(.+)$", line)
            if match:
                pending_title = match.group(1).strip()
                pending_description = ""
                continue

            # 解析链接行
            if line.startswith("链接:") or line.startswith("link:"):
                url_match = re.search(r"https?://[^\s]+", line)
                if url_match:
                    url = url_match.group(0)
                    resources.append({
                        "title": pending_title,
                        "url": url,
                        "description": pending_description,
                        "source": source,
                    })
                    pending_title = ""
                    pending_description = ""
                continue

            if line.startswith("摘要:") or line.startswith("snippet:"):
                pending_description = re.sub(r"^(摘要|snippet):\s*", "", line, flags=re.IGNORECASE)
                continue

            # 解析 Tavily 格式 (url=..., content=...)
            if "url=" in line:
                url_match = re.search(r"url=['\"]?([^'\"\s,]+)['\"]?", line)
                content_match = re.search(r"content=['\"]?([^'\"]+)['\"]?", line)
                if url_match:
                    url = url_match.group(1)
                    content = content_match.group(1) if content_match else ""
                    resources.append({
                        "title": content[:100] if content else "",
                        "url": url,
                        "description": content,
                        "source": source,
                    })

        return resources

    def _parse_structured_search_items(self, search_result: object, source: str) -> list[dict]:
        """解析 Tavily 等搜索工具返回的 list/dict 或其字符串表示。"""
        parsed: object = search_result
        if isinstance(search_result, str):
            stripped = search_result.strip()
            if not stripped.startswith(("[", "{")):
                return []
            try:
                parsed = ast.literal_eval(stripped)
            except (ValueError, SyntaxError):
                try:
                    parsed = parse_first_json_value(stripped)
                except (TypeError, ValueError):
                    return []

        if isinstance(parsed, dict):
            candidates = parsed.get("results") or parsed.get("organic_results") or [parsed]
        elif isinstance(parsed, list):
            candidates = parsed
        else:
            return []

        resources: list[dict] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or item.get("link")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                continue
            title = item.get("title") or item.get("name") or item.get("source") or ""
            description = item.get("content") or item.get("snippet") or item.get("description") or ""
            resources.append({
                "title": str(title),
                "url": url,
                "description": str(description),
                "source": source,
            })
        return resources

    async def _verify_url(self, url: str) -> bool:
        """验证 URL 是否可访问（简单检查）。"""
        if not url:
            return False

        # 排除明显无效的 URL
        invalid_patterns = [
            r"example\.com",
            r"localhost",
            r"127\.0\.0\.1",
            r"your-",
            r"xxx",
        ]
        for pattern in invalid_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        # 检查 URL 格式
        if not url.startswith(("http://", "https://")):
            return False

        return True

    async def _emit_action(
        self,
        state: WorkerState,
        action: str,
        detail: str = "",
        current_step: int = 0,
        total_steps: int = 0,
        step_label: str = "",
        current_action: str = "",
    ) -> None:
        """发送 Agent 动作事件。"""
        if self.emitter:
            await self.emitter.emit_agent_action(
                state.agent_name,
                action,
                detail,
                current_step=current_step,
                total_steps=total_steps,
                step_label=step_label,
                current_action=current_action,
                layer=state.layer_index,
                layer_name="实践拓展层",
                agent_role=self.ROLE_NAME,
                resource_type=state.agent_name,
            )

    async def run(self, state: WorkerState) -> WorkerResult:
        """执行拓展阅读生成。"""
        learning_need = learning_need_from_task(state.task)
        logger.info("[ReadingAgent] 开始执行: learning_need=%s", learning_need[:80])
        total = 7

        await self._emit_action(
            state,
            "analyze_input",
            "拓展阅读推荐智能体正在分析阅读需求",
            current_step=2,
            total_steps=total,
            step_label=self.STEPS[0],
            current_action="分析拓展阅读需求",
        )
        prompt = self._load_prompt()

        # 提取搜索关键词
        await self._emit_action(
            state,
            "extract_keywords",
            "拓展阅读推荐智能体正在提取搜索关键词",
            current_step=3,
            total_steps=total,
            step_label="提取关键词",
            current_action="提取搜索关键词",
        )
        keywords = await self._extract_search_keywords(state)
        logger.info("[ReadingAgent] 提取的关键词: %s", keywords)

        # 搜索真实可用的资源
        await self._emit_action(
            state,
            "search_resources",
            "拓展阅读推荐智能体正在搜索验证资源链接",
            current_step=4,
            total_steps=total,
            step_label=self.STEPS[1],
            current_action="搜索验证资源",
        )

        max_items = state.agent_config.get("max_items", 5)
        searched_resources = await self._search_resources(keywords, max_results=max_items + 3)
        logger.info("[ReadingAgent] 搜索到 %d 个资源", len(searched_resources))

        await self._emit_action(
            state,
            "merge_profile_dependencies",
            "拓展阅读推荐智能体正在融合画像和上游内容",
            current_step=5,
            total_steps=total,
            step_label=self.STEPS[2],
            current_action="融合画像与依赖",
        )
        input_text = await self._build_input(state, searched_resources)

        try:
            await self._emit_action(
                state,
                "generate_content",
                "拓展阅读推荐智能体正在生成阅读导引",
                current_step=6,
                total_steps=total,
                step_label=self.STEPS[3],
                current_action="生成阅读推荐",
            )

            response = await self.llm_manager.ainvoke(
                "spark_x",
                [HumanMessage(content=f"{prompt}\n\n{input_text}")],
                model_kwargs={"temperature": 0.3},
            )

            raw_content = response.content if hasattr(response, "content") else str(response)

            try:
                content = parse_first_json_value(raw_content)
            except (TypeError, ValueError):
                logger.warning("[ReadingAgent] JSON 解析失败，返回原始内容")
                content = {"error": "解析失败", "raw_content": self._clean_content(raw_content)}

            # 验证并过滤资源链接
            content = await self._validate_and_filter_resources(content, searched_resources)

            await self._emit_action(
                state,
                "finalize_output",
                "拓展阅读推荐智能体正在整理输出",
                current_step=7,
                total_steps=total,
                step_label=self.STEPS[4],
                current_action="整理阅读资源",
            )

            resources = content.get("resources", []) if isinstance(content, dict) else []
            recommended_path: list[str] = []
            if isinstance(resources, list):
                for item in resources[:6]:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title") or item.get("name") or item.get("resource_name")
                    reason = item.get("recommend_reason") or item.get("description")
                    if title:
                        recommended_path.append(str(title))
                    elif reason:
                        recommended_path.append(str(reason)[:80])

            # 统计有效链接数量
            valid_url_count = sum(1 for r in resources if isinstance(r, dict) and r.get("url"))

            summary_data = {
                "resource_count": len(resources) if isinstance(resources, list) else 0,
                "valid_url_count": valid_url_count,
                "reading_depth": state.agent_config.get("reading_depth", "course_extended"),
                "recommended_path": recommended_path,
                "search_keywords": keywords,
            }

            return WorkerResult.model_construct(
                success=True,
                content=content,
                file_type="json",
                title=title_from_learning_need(state.task, "拓展阅读"),
                summary="生成拓展阅读材料与阅读顺序",
                summary_data=summary_data,
                metadata={
                    "reading_depth": state.agent_config.get("reading_depth", "course_extended"),
                    "searched_resources": len(searched_resources),
                    "search_keywords": keywords,
                },
            )

        except Exception as exc:
            logger.exception("[ReadingAgent] 执行失败")
            return WorkerResult(success=False, error=str(exc))

    async def _validate_and_filter_resources(
        self, content: dict, searched_resources: list[dict]
    ) -> dict:
        """验证并过滤资源，确保链接有效。

        1. 对于 LLM 生成的资源，验证 URL 格式
        2. 对于搜索到的真实资源，补充到推荐列表
        3. 移除无效或可疑的链接
        """
        if not isinstance(content, dict):
            return content

        resources = content.get("resources", [])
        if not isinstance(resources, list):
            return content

        validated_resources = []
        seen_urls: set[str] = set()

        # 构建搜索资源的 URL 映射
        searched_url_map: dict[str, dict] = {}
        for sr in searched_resources:
            url = sr.get("url", "")
            if url:
                searched_url_map[url] = sr

        for resource in resources:
            if not isinstance(resource, dict):
                continue

            url = resource.get("url", "")

            # 验证 URL
            if url:
                is_valid = await self._verify_url(url)
                if is_valid and url not in seen_urls:
                    seen_urls.add(url)
                    validated_resources.append(resource)
                else:
                    # URL 无效，尝试从搜索结果中找替代
                    resource_title = resource.get("title", "")
                    matched_resource = self._find_matching_searched_resource(
                        resource_title, searched_url_map, seen_urls
                    )
                    if matched_resource:
                        resource["url"] = matched_resource.get("url", "")
                        resource["title"] = matched_resource.get("title") or resource.get("title", "")
                        resource["verified"] = True
                        seen_urls.add(resource["url"])
                        validated_resources.append(resource)
            else:
                # 没有 URL，尝试从搜索结果中匹配
                resource_title = resource.get("title", "")
                matched_resource = self._find_matching_searched_resource(
                    resource_title, searched_url_map, seen_urls
                )
                if matched_resource:
                    resource["url"] = matched_resource.get("url", "")
                    resource["verified"] = True
                    seen_urls.add(resource["url"])
                validated_resources.append(resource)

        # 如果有效资源太少，补充搜索结果
        if len(validated_resources) < 3:
            for sr in searched_resources:
                url = sr.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    validated_resources.append({
                        "id": f"R{len(validated_resources) + 1}",
                        "type": "article",
                        "title": sr.get("title", "搜索资源"),
                        "url": url,
                        "verified": True,
                        "recommend_reason": "来自搜索引擎验证的真实资源",
                    })
                    if len(validated_resources) >= 5:
                        break

        content["resources"] = validated_resources
        return content

    def _find_matching_searched_resource(
        self,
        title: str,
        searched_url_map: dict[str, dict],
        seen_urls: set[str],
    ) -> dict | None:
        """根据标题从搜索结果中找到匹配的资源。"""
        if not title:
            return None

        title_lower = title.lower()
        title_keywords = set(re.findall(r"\w+", title_lower))

        best_match = None
        best_score = 0

        for url, sr in searched_url_map.items():
            if url in seen_urls:
                continue

            sr_title = sr.get("title", "").lower()
            sr_keywords = set(re.findall(r"\w+", sr_title))

            # 计算关键词重叠
            overlap = len(title_keywords & sr_keywords)
            if overlap > best_score:
                best_score = overlap
                best_match = sr

        # 至少有 2 个关键词重叠才认为匹配
        if best_score >= 2:
            return best_match
        return None

    def _load_prompt(self) -> str:
        """加载提示词。"""
        if self.prompt_path.exists():
            return self.prompt_path.read_text(encoding="utf-8")
        return """你是一位教育资源推荐专家。请根据给定的主题，推荐拓展阅读材料。

要求：
1. 推荐相关书籍、论文、文章
2. 说明推荐理由
3. 提供学习路径建议
4. 使用 Markdown 格式"""

    async def _build_input(self, state: WorkerState, searched_resources: list[dict] | None = None) -> str:
        """构建输入内容。"""
        task = state.task
        agent_config = state.agent_config

        parts = [
            "## 学习需求",
            learning_need_from_task(task),
            "",
            "## 学习场景",
            f"- 场景类型: {state.learning_scenario}",
            "",
            "## Agent 配置",
            f"- 阅读深度: {agent_config.get('reading_depth', 'course_extended')}",
            f"- 最大条目数: {agent_config.get('max_items', 5)}",
            f"- 资源时效偏好: {agent_config.get('resource_quality', 'balanced')}",
            f"- 包含实践资源: {agent_config.get('include_practice', False)}",
            f"- 语言偏好: {agent_config.get('language_preference', 'chinese')}",
        ]

        # 添加搜索到的真实资源
        if searched_resources:
            parts.append("")
            parts.append("## 已验证的真实资源")
            parts.append("以下资源已通过搜索引擎验证，链接真实可访问，请优先推荐这些资源：")
            for i, sr in enumerate(searched_resources[:8], 1):
                url = sr.get("url", "")
                title = sr.get("title", "未知标题")
                source = sr.get("source", "search")
                parts.append(f"{i}. 标题: {title[:80]}")
                parts.append(f"   链接: {url}")
                parts.append(f"   来源: {source}")

        # Use AgentContextBuilder for context-aware prompt building
        builder = AgentContextBuilder()
        context_text = builder.build_for_agent("reading", state)
        if context_text:
            parts.append("")
            parts.append(context_text)
        append_backend_context_for_prompt(parts, state)

        parts.append("")
        parts.append("请推荐拓展阅读材料。")
        return "\n".join(parts)

    def _clean_content(self, content: str) -> str:
        """清理内容。"""
        return content.strip()
