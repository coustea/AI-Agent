"""
PPT 演示文稿生成 Agent。
通过结构化输出 + 本地渲染生成 PPT 文件。
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Optional, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from app.infra.llm import get_deepseek_llm
from app.infra.logging import get_logger
from app.resource.agents.ppt.renderer import ensure_template_available, render_ppt_plan_to_file
from app.resource.agents.ppt.template_catalog import (
    DEFAULT_TEMPLATE_ID,
    get_builtin_template_spec,
    merge_template_config,
    recommend_template_id,
)
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

_VISUAL_KEYWORDS = ("视觉", "图解", "图像", "示意", "案例驱动")
_SEQUENTIAL_KEYWORDS = ("顺序", "逻辑", "步骤", "推理", "序列")
_GLOBAL_KEYWORDS = ("整体", "全局", "宏观", "综合", "框架")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
_MIN_SLIDES = 6
_MAX_SLIDES = 10


class PptSlidePlan(BaseModel):
    """单页 PPT 结构化输出。取消了 Literal 限制以适配多模板。"""

    title: str = Field(description="页面标题")
    section: str = Field(description="模板分区")
    page_role: str = Field(description="模板页型")
    slots: dict[str, str] = Field(description="与模板 slot 对应的文本内容")
    speaker_notes: str = Field(description="讲者备注")

    @model_validator(mode="after")
    def _validate_slide(self) -> "PptSlidePlan":
        self.title = self.title.strip()
        self.speaker_notes = self.speaker_notes.strip()
        cleaned_slots = {
            str(key).strip(): str(value).strip()
            for key, value in self.slots.items()
            if str(key).strip() and str(value).strip()
        }
        if not self.title:
            raise ValueError("slide.title 不能为空")
        if not cleaned_slots:
            raise ValueError("slide.slots 不能为空")
        if not self.speaker_notes:
            raise ValueError("每一页都必须提供 speaker_notes")
        self.slots = cleaned_slots
        return self


class PptPlanOutput(BaseModel):
    """模板友好的 PPT JSON 输出。"""

    presentation_title: str = Field(description="整份演示文稿标题")
    template_id: str = Field(default=DEFAULT_TEMPLATE_ID, description="模板标识")
    slides: list[PptSlidePlan] = Field(description="按渲染顺序排列的幻灯片列表")

    @model_validator(mode="after")
    def _validate_plan(self) -> "PptPlanOutput":
        self.presentation_title = self.presentation_title.strip()
        if not self.presentation_title:
            raise ValueError("presentation_title 不能为空")
        if len(self.slides) < _MIN_SLIDES:
            raise ValueError(f"至少需要 {_MIN_SLIDES} 页")
        if len(self.slides) > _MAX_SLIDES:
            raise ValueError(f"页数不能超过 {_MAX_SLIDES} 页")
        return self


class PptState(TypedDict, total=False):
    """PPT 生成的专属状态字段。"""

    major: str
    course: str
    topic: str
    gap: str
    user_profile: dict[str, Any]
    shared_memory: dict[str, Any]
    messages: list[Any]
    is_valid: bool
    validation_feedback: str
    retry_count: int
    max_retries: int
    error: Optional[str]
    slide_count: int
    speaker_notes: str
    file_path: Optional[str]
    slide_titles: list[str]
    style: str
    template_id: str
    template_source_url: str
    template_config_url: str
    ppt_plan: dict[str, Any]
    ppt_plan_json: str
    render_ready: bool


def _select_ppt_style(cognitive_style: str | None) -> str:
    """根据认知风格选择更贴近学习体验的视觉主题。"""
    style = (cognitive_style or "").strip()
    if any(keyword in style for keyword in _VISUAL_KEYWORDS):
        return "creative_bold"
    if any(keyword in style for keyword in _SEQUENTIAL_KEYWORDS):
        return "corporate_blue"
    if any(keyword in style for keyword in _GLOBAL_KEYWORDS):
        return "nature_green"
    return "modern_minimal"


def _check_slide_plan_quality(plan: dict[str, Any]) -> tuple[bool, str, int]:
    """对 PPT 结构化计划做最低质量校验。"""
    if not isinstance(plan, dict):
        return False, "未检测到可用的 PPT JSON 计划。", 0
    raw_slides = plan.get("slides", [])
    raw_slide_count = len(raw_slides) if isinstance(raw_slides, list) else 0

    try:
        validated = PptPlanOutput.model_validate(plan)
    except Exception as exc:
        message = str(exc)
        if f"至少需要 {_MIN_SLIDES} 页" in message:
            return False, f"PPT 页数不足，至少需要 {_MIN_SLIDES} 页。", raw_slide_count
        if f"页数不能超过 {_MAX_SLIDES} 页" in message:
            return False, f"PPT 页数过多，最多允许 {_MAX_SLIDES} 页。", raw_slide_count
        return False, f"PPT JSON 计划校验失败：{exc}", raw_slide_count

    slides = validated.slides
    slide_count = len(slides)
    if slide_count < _MIN_SLIDES:
        return False, f"PPT 页数不足，至少需要 {_MIN_SLIDES} 页。", slide_count
    if slide_count > _MAX_SLIDES:
        return False, f"PPT 页数过多，最多允许 {_MAX_SLIDES} 页。", slide_count

    for slide in slides:
        if len(slide.speaker_notes.strip()) < 6:
            return False, f"页面《{slide.title}》讲者备注过短。", slide_count

    return True, "", slide_count


def _render_plan_summary(plan: dict[str, Any]) -> str:
    """把结构化计划渲染为可读文本，便于结果兜底展示。"""
    slides = plan.get("slides", []) if isinstance(plan, dict) else []
    lines = [f"# {plan.get('presentation_title', '演示文稿')}"]
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        lines.append(f"## {slide.get('title', '未命名页面')}")
        slots = slide.get("slots", {})
        if isinstance(slots, dict):
            for key, value in slots.items():
                if key == "title":
                    continue
                lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict[str, Any]:
    """从模型文本中提取 JSON 对象。"""
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("模型返回为空，无法提取 PPT JSON 计划")

    # 尝试提取 ```json ... ``` 代码块
    match = _JSON_FENCE_RE.search(raw)
    if match:
        raw = match.group(1).strip()

    # 如果不是以 { 开头，尝试找到第一个 { 和最后一个 }
    if not raw.startswith("{"):
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]

    if not raw.startswith("{"):
        raise ValueError(f"无法从响应中提取 JSON 对象，响应内容: {raw[:200]}...")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败: {exc}, 内容: {raw[:200]}...") from exc

    if not isinstance(parsed, dict):
        raise ValueError("模型返回的 JSON 顶层不是对象")
    return parsed


def _default_title_for_role(page_role: str) -> str:
    mapping = {
        "cover": "封面",
        "table_of_contents": "目录",
        "hero_image_split": "图文概览",
        "icon_process_row": "流程拆解",
        "hex_cycle": "要素关系",
        "target_illustration": "目标推进",
        "road_timeline": "学习路径",
        "concentric_focus": "重点聚焦",
        "three_columns": "三要点",
        "four_cards": "核心模块",
        "three_steps": "步骤说明",
        "three_bullets": "关键结论",
        "two_cards": "对比分析",
        "single_text": "知识讲解",
    }
    return mapping.get(page_role, "未命名页面")


def _normalize_plan_dict(plan: dict[str, Any]) -> dict[str, Any]:
    """将回退模式下较松散的 JSON 计划整理成 PptPlanOutput 兼容格式。"""
    if not isinstance(plan, dict):
        return {}

    normalized = dict(plan)
    raw_slides = normalized.get("slides")
    if not isinstance(raw_slides, list):
        return normalized

    fixed_slides: list[dict[str, Any]] = []
    for item in raw_slides:
        if not isinstance(item, dict):
            continue
        slide = dict(item)
        slots = slide.get("slots")
        slots = dict(slots) if isinstance(slots, dict) else {}
        page_role = str(slide.get("page_role", "")).strip()
        section = str(slide.get("section", "")).strip()

        if not section:
            section = "learning"

        title = str(slide.get("title", "")).strip() or str(slots.get("title", "")).strip()
        if not title:
            title = _default_title_for_role(page_role)

        # 确保 slots 非空
        if not slots:
            slots = {"title": title, "body": "内容待补充"}

        slide["title"] = title
        slide["section"] = section
        slide["slots"] = slots
        slide["page_role"] = page_role or "single_text"

        # 确保 speaker_notes 存在
        if not slide.get("speaker_notes"):
            slide["speaker_notes"] = f"讲解{title}相关内容"

        fixed_slides.append(slide)

    normalized["slides"] = fixed_slides
    return normalized


class PptAgent:
    """PPT 演示文稿生成 Agent（纯结构化输出 + 本地渲染）。"""

    structured_output_schema = PptPlanOutput

    def __init__(self) -> None:
        self.name = "PptAgent"
        self.agent_dir = Path(__file__).parent
        self.state_schema = PptState
        self.temperature = 0.2
        self.llm = get_deepseek_llm(temperature=0.2, streaming=False, max_tokens=4000)
        self.prompt_template = ""
        self._graph = None
        self._load_prompt()

    def _load_prompt(self) -> None:
        """加载 prompt 模板。"""
        prompt_path = self.agent_dir / "prompt.md"
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")
            logger.info("[%s] 加载 prompt: %s", self.name, prompt_path)
        else:
            logger.warning("[%s] prompt 文件不存在: %s", self.name, prompt_path)

    def _load_template_config(self, template_id: str) -> dict:
        """加载本地的模板配置文件。"""
        candidate_paths = [
            WORKPLACE_DIR / "templates" / template_id / f"{template_id}.config.json",
            WORKPLACE_DIR / "templates" / template_id / "template.config.json",
            WORKPLACE_DIR / f"{template_id}.config.json",
            self.agent_dir / f"{template_id}.config.json",
        ]
        for path in candidate_paths:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return merge_template_config(template_id, json.load(f))
        raise FileNotFoundError(f"未找到模板配置文件: {template_id}.config.json")

    def _build_dynamic_prompt_parts(self, config: dict) -> dict[str, str]:
        """将 JSON 配置转换为注入 Prompt 的字符串。"""
        roles_list = []
        slot_rules = []

        for slide_def in config.get("slide_definitions", []):
            role = slide_def.get("page_role", "unknown")
            summary = slide_def.get("summary", "")
            roles_list.append(f"- `{role}`: {summary}")

            slots = [s.get("name") for s in slide_def.get("slots", [])]
            if slots:
                slot_rules.append(f"- `{role}`: 需要并仅限使用这些槽位 -> {', '.join([f'`{s}`' for s in slots])}")

        unique_roles = list(dict.fromkeys(roles_list))
        unique_rules = list(dict.fromkeys(slot_rules))

        return {
            "template_name": config.get("name", "未命名模板"),
            "template_description": config.get("description", ""),
            "template_roles_definition": "\n".join(unique_roles),
            "template_slot_rules": "\n".join(unique_rules)
        }

    @staticmethod
    def _resolve_template_selection(
        *,
        requested_template_id: str,
        template_source_url: str,
        user_profile: dict[str, Any],
        style: str,
    ) -> str:
        normalized = str(requested_template_id or "").strip()
        has_custom_source = bool(str(template_source_url or "").strip())
        if has_custom_source:
            return normalized or "custom_online_template"
        if normalized and normalized not in {"cn_ink_education", "auto"}:
            return normalized
        return recommend_template_id(user_profile, style) or DEFAULT_TEMPLATE_ID

    async def _ensure_graph(self) -> None:
        """确保图已构建。"""
        if self._graph is None:
            self._graph = await self._build_graph()

    async def _build_graph(self):
        """使用 LangGraph 显式编排：生成 -> 校验 -> 渲染。"""
        graph = StateGraph(self.state_schema)
        graph.add_node("agent", self._agent_node)
        graph.add_node("validate", self._validate_node)
        graph.add_node("render", self._render_node)

        graph.add_edge(START, "agent")
        graph.add_edge("agent", "validate")
        graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            path_map={"retry": "agent", "render": "render", "end": END},
        )
        graph.add_edge("render", END)
        return graph.compile()

    def _route_after_validate(self, state: Any) -> str:
        """校验后决定重试、渲染或结束。"""
        if state.get("error"):
            return "end"
        if state.get("is_valid", False) and state.get("render_ready", False):
            return "render"
        if state.get("retry_count", 0) < state.get("max_retries", 2):
            return "retry"
        return "end"

    async def _agent_node(self, state: Any) -> dict:
        """Agent 节点：调用 LLM 生成结构化计划。"""
        from app.config import LLM_TIMEOUT

        messages = self._build_messages(state)
        structured_llm = self.llm.with_structured_output(self.structured_output_schema)

        try:
            result = await asyncio.wait_for(
                structured_llm.ainvoke(messages),
                timeout=LLM_TIMEOUT,
            )
            return {"ppt_plan": result.model_dump(), "error": None}
        except asyncio.TimeoutError:
            logger.error("[%s] LLM 调用超时", self.name)
            return {"error": "LLM 调用超时", "is_valid": False}
        except Exception as exc:
            error_text = str(exc)
            if "response_format type is unavailable" not in error_text:
                raise

            logger.warning(
                "[%s] structured_output 不可用，回退到 JSON 文本生成: %s",
                self.name,
                error_text,
            )
            fallback_messages = list(messages) + [
                HumanMessage(
                    content=(
                        "structured_output 当前不可用。"
                        "请直接输出一个合法 JSON 对象，不要使用 Markdown 代码块，不要添加解释文字。"
                        "JSON 必须满足以下结构：\n"
                        "{\n"
                        '  "presentation_title": "演示文稿标题",\n'
                        f'  "template_id": "{DEFAULT_TEMPLATE_ID}",\n'
                        '  "slides": [\n'
                        "    {\n"
                        '      "title": "页面标题",\n'
                        '      "section": "learning",\n'
                        '      "page_role": "single_text",\n'
                        '      "slots": {"title": "标题", "body": "内容"},\n'
                        '      "speaker_notes": "讲者备注"\n'
                        "    }\n"
                        "  ]\n"
                        "}\n"
                        "必须包含至少 6 页 slides。"
                    )
                )
            ]
            raw_response = await asyncio.wait_for(
                self.llm.ainvoke(fallback_messages),
                timeout=LLM_TIMEOUT,
            )
            raw_content = getattr(raw_response, "content", raw_response)
            logger.info("[%s] LLM 原始响应长度: %d", self.name, len(str(raw_content)))
            try:
                plan = _normalize_plan_dict(_extract_json_object(raw_content))
                validated = self.structured_output_schema.model_validate(plan)
                return {"ppt_plan": validated.model_dump(), "error": None}
            except Exception as parse_exc:
                logger.error("[%s] JSON 解析或验证失败: %s", self.name, parse_exc)
                return {"error": str(parse_exc), "is_valid": False, "ppt_plan": {}}

    def _build_messages(self, state: Any) -> list:
        """构建消息列表。"""
        system_prompt = self._build_system_message(state)
        human_message = self._build_initial_human_message(state)

        from langchain_core.messages import HumanMessage, SystemMessage
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_message),
        ]

    async def _validate_node(self, state: Any) -> dict:
        """校验节点：仅验证结构化计划质量，不做渲染。"""
        ppt_plan = state.get("ppt_plan") or {}
        retry_count = int(state.get("retry_count", 0))
        max_retries = int(state.get("max_retries", 2))

        quality_ok, quality_feedback, inferred_slide_count = _check_slide_plan_quality(ppt_plan)
        if not quality_ok:
            logger.warning("[PptAgent] PPT JSON 计划质量不足: %s", quality_feedback)
            next_retry_count = retry_count + 1
            exhausted = next_retry_count >= max_retries
            return {
                "is_valid": False,
                "validation_feedback": quality_feedback,
                "file_path": None,
                "slide_count": inferred_slide_count,
                "slide_titles": [],
                "ppt_plan": ppt_plan or {},
                "ppt_plan_json": json.dumps(ppt_plan or {}, ensure_ascii=False),
                "render_ready": False,
                "retry_count": next_retry_count,
                "error": quality_feedback if exhausted else None,
            }

        ppt_plan_json = json.dumps(ppt_plan, ensure_ascii=False, indent=2)
        return {
            "is_valid": True,
            "validation_feedback": "",
            "file_path": None,
            "slide_count": inferred_slide_count,
            "slide_titles": [slide.get("title", "") for slide in ppt_plan.get("slides", [])],
            "ppt_plan": ppt_plan,
            "ppt_plan_json": ppt_plan_json,
            "render_ready": True,
            "error": None,
        }

    async def _render_node(self, state: Any) -> dict:
        """渲染节点：把已校验的 JSON 计划落盘为 PPT。"""
        ppt_plan_json = state.get("ppt_plan_json", "")
        template_id = state.get("template_id", DEFAULT_TEMPLATE_ID)
        template_source_url = state.get("template_source_url", "")
        template_config_url = state.get("template_config_url", "")
        style = state.get("style", "modern_minimal")
        logger.info("[PptAgent] 开始基于模板 [%s] 直接渲染 PPT", template_id)
        try:
            data = render_ppt_plan_to_file(
                topic=state.get("topic", "教学演示"),
                ppt_plan_json=ppt_plan_json,
                template_id=template_id,
                template_source_url=template_source_url,
                template_config_url=template_config_url,
                style=style,
            )
        except Exception as exc:
            logger.error("[PptAgent] 自动保存 PPT 失败: %s", exc, exc_info=exc)
            return {
                "error": f"PPT 计划已生成，但保存 PPT 失败：{exc}",
                "is_valid": False,
                "render_ready": False,
            }

        if data.get("error"):
            message = str(data["error"])
            logger.error("[PptAgent] 渲染器返回错误: %s", message)
            return {
                "error": message,
                "is_valid": False,
                "render_ready": False,
                "validation_feedback": message,
            }

        file_path = data.get("file_path")
        slide_count = int(data.get("slide_count", 0) or 0)
        slide_titles = list(data.get("slide_titles", []) or [])
        logger.info("[PptAgent] 渲染完成，文件路径: %s", file_path)
        return {
            "file_path": file_path,
            "slide_count": slide_count,
            "slide_titles": slide_titles,
            "render_ready": False,
            "is_valid": bool(file_path),
            "validation_feedback": "" if file_path else "未检测到 PPT 文件路径。",
            "error": None if file_path else "未检测到 PPT 文件路径。",
        }

    def _extract_memory(self, shared_memory: dict[str, Any]) -> str:
        """黑板记忆：从前置 Agent 输出中提取关键上下文。"""
        ctx = ""
        if "content" in shared_memory:
            content_data = shared_memory["content"]
            outline = content_data.get("outline", "")
            if outline:
                ctx += f"【参考内容大纲】\n{outline}\n"
        if "mindmap" in shared_memory:
            mindmap_data = shared_memory["mindmap"]
            file_path = mindmap_data.get("file_path", "")
            if file_path:
                ctx += f"【知识拓扑图】\n已生成思维导图: {file_path}\n"
        return ctx

    def _format_user_profile(self, profile: dict[str, Any]) -> str:
        if not profile:
            return ""
        parts = []
        if profile.get("cognitive_style"):
            parts.append(f"- 认知风格: {profile['cognitive_style']}")
        return "\n".join(parts)

    def _build_system_message(self, state: Any) -> str:
        user_profile = state.get("user_profile", {})
        template_id = state.get("template_id", DEFAULT_TEMPLATE_ID)
        template_source_url = str(state.get("template_source_url") or "").strip()
        template_config_url = str(state.get("template_config_url") or "").strip()

        try:
            ensure_template_available(
                template_id=template_id,
                template_source_url=template_source_url,
                template_config_url=template_config_url,
            )
            config = self._load_template_config(template_id)
            dynamic_parts = self._build_dynamic_prompt_parts(config)
        except Exception as e:
            spec = get_builtin_template_spec(template_id) or {}
            builtin_config = spec.get("config") if isinstance(spec.get("config"), dict) else {}
            if builtin_config:
                logger.warning("模板文件未就绪，使用内置模板目录配置构建提示词: %s", template_id)
                dynamic_parts = self._build_dynamic_prompt_parts(builtin_config)
            else:
                logger.error(f"加载模板配置失败: {e}")
                dynamic_parts = {
                    "template_name": template_id,
                    "template_description": "通用教育模板",
                    "template_roles_definition": "- cover: 封面\n- table_of_contents: 目录\n- single_text: 单正文",
                    "template_slot_rules": "- cover: 必须包含 title\n- single_text: 必须包含 title, body"
                }

        system_prompt = self.prompt_template.format(
            major=state.get("major", "通用"),
            course=state.get("course", ""),
            topic=state.get("topic", ""),
            gap=state.get("gap", ""),
            cognitive_style=user_profile.get("cognitive_style", "通用"),
            **dynamic_parts
        )
        system_prompt = self._append_context_to_prompt(system_prompt, state)
        return system_prompt

    def _append_context_to_prompt(self, prompt: str, state: Any) -> str:
        """追加上下文到 prompt。"""
        shared_memory = state.get("shared_memory", {})
        memory_context = self._extract_memory(shared_memory)
        if memory_context:
            prompt += f"\n\n## 前置上下文\n\n{memory_context}"
        return prompt

    def _build_initial_human_message(self, state: Any) -> str:
        topic = state.get("topic", "")
        template_id = state.get("template_id", DEFAULT_TEMPLATE_ID)
        retry_count = int(state.get("retry_count", 0))
        validation_feedback = str(state.get("validation_feedback", "")).strip()
        retry_hint = ""
        if retry_count > 0 and validation_feedback:
            retry_hint = (
                f"\n上一次输出未通过校验：{validation_feedback}"
                "\n请修正后重新生成完整 JSON。"
            )
        return (
            f"请为主题 '{topic}' 生成与动态教育模板匹配的 PPT JSON 计划。"
            f" 当前模板标识为 '{template_id}'。"
            f" 整份 PPT 必须保持 {_MIN_SLIDES}-{_MAX_SLIDES} 页。"
            " 不要输出 Markdown，也不要自己声明 file_path。"
            f"{retry_hint}"
        )

    async def generate_ppt(
        self,
        topic: str,
        course: str = "",
        major: str = "通用",
        gap: str = "",
        user_profile: dict = None,
        shared_memory: dict = None,
        template_id: str = "auto",
        template_source_url: str = "",
        template_config_url: str = "",
    ) -> dict[str, Any]:
        profile_data = user_profile or {}
        preferred_style = _select_ppt_style(profile_data.get("cognitive_style"))
        resolved_template_id = self._resolve_template_selection(
            requested_template_id=template_id,
            template_source_url=template_source_url,
            user_profile=profile_data,
            style=preferred_style,
        )
        template_spec = get_builtin_template_spec(resolved_template_id) or {}
        resolved_style = str(template_spec.get("style") or preferred_style).strip() or preferred_style
        logger.info(
            "[PptAgent] 收到生成请求: topic=%s requested_template=%s resolved_template=%s",
            topic,
            template_id,
            resolved_template_id,
        )
        await self._ensure_graph()

        initial_state: PptState = {
            "major": major,
            "course": course,
            "topic": topic,
            "gap": gap,
            "user_profile": profile_data,
            "shared_memory": shared_memory or {},
            "template_id": resolved_template_id,
            "template_source_url": template_source_url or "",
            "template_config_url": template_config_url or "",
            "messages": [],
            "slide_titles": [],
            "style": resolved_style,
            "ppt_plan": {},
            "ppt_plan_json": "",
            "render_ready": False,
            "is_valid": False,
            "validation_feedback": "",
            "retry_count": 0,
            "max_retries": 2,
            "error": None,
        }

        try:
            logger.info("[PptAgent] 开始执行 PPT 工作流: structured_output=DeepSeek")
            result = await self._graph.ainvoke(initial_state, {"recursion_limit": 15})
            logger.info(
                "[PptAgent] PPT 工作流完成: is_valid=%s file_path=%s slide_count=%s",
                result.get("is_valid"),
                result.get("file_path"),
                result.get("slide_count"),
            )
        except Exception as exc:
            logger.error("[PptAgent] 工作流执行失败: %s", exc)
            return {
                "success": False,
                "content": "",
                "file_path": None,
                "slide_count": 0,
                "ppt_plan": {},
                "ppt_plan_json": "",
                "speaker_notes": "",
                "error": str(exc),
            }

        ppt_plan = result.get("ppt_plan") or {}
        rendered_content = _render_plan_summary(ppt_plan) if ppt_plan else ""
        file_path = result.get("file_path")

        return {
            "success": bool(file_path),
            "content": rendered_content,
            "file_path": file_path,
            "slide_count": result.get("slide_count", len(ppt_plan.get("slides", [])) if isinstance(ppt_plan, dict) else 0),
            "ppt_plan": ppt_plan,
            "ppt_plan_json": result.get("ppt_plan_json") or json.dumps(ppt_plan, ensure_ascii=False, indent=2),
            "slide_titles": result.get("slide_titles", []),
            "style": resolved_style,
            "template_id": resolved_template_id,
            "speaker_notes": "\n\n".join(
                slide.get("speaker_notes", "")
                for slide in ppt_plan.get("slides", [])
                if isinstance(slide, dict) and slide.get("speaker_notes")
            ) if isinstance(ppt_plan, dict) else "",
            "error": result.get("error") or (None if file_path else result.get("validation_feedback")),
        }


if __name__ == "__main__":
    agent = PptAgent()

    async def main():
        await agent._ensure_graph()

        result = await agent.generate_ppt(
            topic="进程调度算法详解",
            course="操作系统",
            major="计算机科学",
            gap="对FCFS、SJF、RR三种调度算法的原理和区别理解不清晰",
            user_profile={"cognitive_style": "偏逻辑推理"},
            shared_memory={
                "content": {
                    "outline": """
一、进程调度基础
  - 调度的必要性：多进程竞争CPU
  - 调度目标：公平性、吞吐量、响应时间
  - 调度时机：创建、终止、阻塞、时间片用完

二、先来先服务 FCFS
  - 原理：按到达顺序执行
  - 特点：非抢占、简单
  - 缺点：护航效应

三、短作业优先 SJF
  - 原理：选择预估时间最短的进程
  - 特点：平均等待时间最优
  - 缺点：长进程饥饿、需预知时间

四、时间片轮转 RR
  - 原理：为每个进程分配时间片
  - 特点：抢占式、公平
  - 时间片大小的权衡

五、算法对比与选择
  - 批处理系统 vs 分时系统
  - 性能指标对比
"""
                },
            },
            template_id="cn_ink_education"
        )

        print("=" * 60)
        print("[PPT 生成结果]")
        print("=" * 60)
        print(f"成功: {result['success']}")
        print(f"文件路径: {result['file_path']}")
        print(f"幻灯片数量: {result['slide_count']}")
        print(f"幻灯片标题: {result['slide_titles']}")

        if result.get("error"):
            print("\n[错误信息]")
            print(result["error"])
        else:
            print("\n[生成完成，请打开 PPT 文件查看]")

    asyncio.run(main())
