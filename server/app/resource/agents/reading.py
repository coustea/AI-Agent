"""
阅读推荐智能体 — 推荐学习资源。

流程: 构建输入 → 搜索补充 → LLM 生成推荐
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)


class ReadingResourceItem(BaseModel):
    id: int = Field(description="资源唯一ID")
    type: str = Field(description="资源类型，如 book, paper, article, documentation, practice_project")
    title: str = Field(description="资源标题")
    authors: list[str] = Field(default_factory=list, description="作者或发布机构")
    source: str = Field(default="", description="来源网站或出版方")
    url: str = Field(default="", description="资源链接")
    difficulty: str = Field(default="medium", description="难度：basic, medium, advanced")
    recommend_reason: str = Field(description="推荐理由")
    description: str = Field(default="", description="资源简介")


class LearningPathStep(BaseModel):
    step: int = Field(description="步骤序号")
    resource_id: int = Field(description="引用的资源ID")
    action: str = Field(description="学习动作或目标")


class ReadingPayload(BaseModel):
    summary: str = Field(description="本组阅读资源综述")
    resources: list[ReadingResourceItem] = Field(default_factory=list, description="推荐的资源列表")
    learning_path: list[LearningPathStep] = Field(default_factory=list, description="推荐的学习路径")



class ReadingAgent:
    """阅读推荐 Agent — 推荐拓展阅读资源。"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("reading", status="running", message="正在准备拓展阅读", progress=0)
        await self.emitter.emit_agent_action(
            "reading", "search", detail="正在搜索相关资料",
            current_step=1, total_steps=3, step_label="搜索资料", progress=15,
        )

        prompt = registry.get("resource/reading")
        input_text = self._build_input(state)

        # 搜索补充：获取已验证的真实资源链接
        search_context = await self._search_supplement(state)
        if search_context:
            input_text += f"\n\n## 已验证的真实资源\n{search_context}"

        await self.emitter.emit_agent_action(
            "reading", "filter", detail="正在筛选优质文献",
            current_step=2, total_steps=3, step_label="筛选文献", progress=45,
        )

        full_prompt = f"{prompt}\n\n{input_text}"

        try:
            result = await self.llm.ainvoke_json(
                ReadingPayload,
                full_prompt,
                temperature=0.3,
                function_name="generate_reading_resources",
                function_description="生成拓展阅读资源及学习路径",
            )
            reading_data = result.model_dump(mode="json")
            content = json.dumps(reading_data, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("[ReadingAgent] 结构化输出失败，尝试 JSON 文本解析: %s", exc)
            response = await self.llm.ainvoke(full_prompt, temperature=0.3)
            raw = response.content if hasattr(response, "content") else str(response)
            content = self._extract_json(raw)
            if not content:
                return WorkerResult(
                    success=False,
                    error=f"阅读推荐 JSON 解析失败: {exc}",
                )

        summary_data = {
            "reading_depth": state.agent_config.get("reading_depth", "course_extended"),
            "language_preference": state.agent_config.get("language_preference", "chinese"),
        }

        await self.emitter.emit_agent_action(
            "reading", "done", detail="拓展阅读推荐完成",
            current_step=3, total_steps=3, step_label="推荐完成", progress=100,
        )
        await self.emitter.emit_agent("reading", status="success", message="拓展阅读推荐完成", progress=100)
        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - 阅读推荐",
            summary="阅读推荐生成完成",
            summary_data=summary_data,
            metadata={
                "engine": "reading_json",
                "agent_id": "reading",
            },
        )

    def _build_input(self, state: WorkerState) -> str:
        parts = [f"## 学习需求\n{state.learning_need}"]

        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像摘要\n{profile_text}")

        if state.blueprint:
            parts.append(f"## 教学蓝图\n{state.blueprint.model_dump_json(indent=2)}")

        if state.instruction:
            lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
            for c in state.instruction.constraints:
                lines.append(f"- 约束: {c}")
            parts.append("\n".join(lines))

        # 阅读配置
        config = state.agent_config
        if config:
            cfg_lines = ["## 阅读配置"]
            cfg_lines.append(f"- 阅读深度: {config.get('reading_depth', 'course_extended')}")
            cfg_lines.append(f"- 最大推荐数量: {config.get('max_items', 5)}")
            cfg_lines.append(f"- 语言偏好: {config.get('language_preference', 'chinese')}")
            cfg_lines.append(f"- 生成模式: {config.get('generation_mode', 'balanced')}")
            parts.append("\n".join(cfg_lines))

        return "\n\n".join(parts)

    async def _search_supplement(self, state: WorkerState) -> str:
        """搜索外部资源作为已验证的补充上下文。"""
        max_items = state.agent_config.get("max_items", 5)
        resources: list[dict] = []

        try:
            from langchain_community.tools import DuckDuckGoSearchResults
            keywords = state.learning_need[:50].split()
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

        if not resources:
            return ""

        return json.dumps(resources, ensure_ascii=False, indent=2)

    def _extract_json(self, raw: str) -> str | None:
        """从 LLM 输出中提取 JSON。"""
        # 直接解析
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return json.dumps(data, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass

        # 去除代码围栏
        pattern = r"```(?:json)?\s*\n(.*?)```"
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass

        # 提取第一个 JSON 对象
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end + 1])
                if isinstance(data, dict):
                    return json.dumps(data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass

        return None

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
