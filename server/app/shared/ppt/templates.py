from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from pydantic import Field

from app.shared.ppt.models import AnimationKind, PPTModel, PPTPlan, PPTSlide, SlideType


REQUIRED_TEMPLATE_IDS = ("teaching-white", "technical-atlas")


class PPTLayout(PPTModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    type: SlideType
    animation: AnimationKind
    skeleton: str = Field(min_length=1)


class PPTTemplateManifest(PPTModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    family: Literal["teaching", "technical"]
    scheme: Literal["light", "dark"]
    tags: list[str] = Field(default_factory=list)
    layouts: list[PPTLayout] = Field(min_length=12)


class PPTTemplate(PPTModel):
    manifest: PPTTemplateManifest
    tokens_css: str
    layouts_css: str
    motion_css: str

    @property
    def css(self) -> str:
        return "\n".join(
            (
                self.tokens_css.strip(),
                self.layouts_css.strip(),
                self.motion_css.strip(),
            )
        )


class PPTTemplateCatalog:
    """只加载 teaching-white 与 technical-atlas 两套外置模板。"""

    def __init__(self, template_root: Path | None = None) -> None:
        self.template_root = template_root or Path(__file__).resolve().parent / "templates"
        self._templates: dict[str, PPTTemplate] | None = None

    def all(self) -> tuple[PPTTemplate, ...]:
        templates = self._loaded_templates()
        return tuple(templates[template_id] for template_id in REQUIRED_TEMPLATE_IDS)

    def get(self, template_id: str) -> PPTTemplate:
        templates = self._loaded_templates()
        template = templates.get(template_id)
        if template is None:
            raise KeyError(f"unknown PPT template: {template_id}")
        return template

    def resolve(self, plan: PPTPlan, *, template_id: str = "auto") -> "ResolvedPPT":
        template = self._select_template(plan) if template_id == "auto" else self.get(template_id)
        layout_map = {layout.type: layout for layout in template.manifest.layouts}

        resolved: list[ResolvedPPTSlide] = []
        for slide in plan.slides:
            layout = layout_map.get(slide.type)
            if layout is None:
                raise ValueError(
                    f"template {template.manifest.id} misses layout for slide type: {slide.type}"
                )

            normalized = slide.model_copy(update={"animation": layout.animation})
            resolved.append(ResolvedPPTSlide(spec=normalized, layout=layout))

        return ResolvedPPT(plan=plan, template=template, slides=tuple(resolved))

    def _select_template(self, plan: PPTPlan) -> PPTTemplate:
        templates = self._loaded_templates()
        preference = plan.template_preference

        if preference.family == "technical":
            return templates["technical-atlas"]
        if preference.family == "teaching":
            return templates["teaching-white"]

        if preference.scheme == "dark":
            return templates["technical-atlas"]
        if preference.scheme == "light":
            return templates["teaching-white"]

        text = " ".join(
            [
                plan.title,
                plan.subtitle,
                plan.purpose,
                plan.narrative,
                *preference.keywords,
            ]
        ).lower()

        technical_words = {
            "系统",
            "架构",
            "协议",
            "网络",
            "操作系统",
            "编译",
            "组成原理",
            "计组",
            "cpu",
            "tcp",
            "ip",
            "数据库",
            "内核",
            "进程",
            "线程",
            "缓存",
            "调度",
            "事务",
            "索引",
            "算法",
            "排序",
            "快排",
            "快速排序",
            "归并",
            "归并排序",
            "堆排序",
            "递归",
            "分治",
            "复杂度",
            "时间复杂度",
            "空间复杂度",
            "数组",
            "链表",
            "栈",
            "队列",
            "树",
            "二叉树",
            "图论",
            "图结构",
            "堆",
            "哈希",
            "指针",
            "数据结构",
            "状态机",
            "自动机",
            "有限状态机",
            "有限自动机",
        }

        if any(word.lower() in text for word in technical_words):
            return templates["technical-atlas"]

        return templates["teaching-white"]

    def _loaded_templates(self) -> dict[str, PPTTemplate]:
        self._ensure_loaded()
        if self._templates is None:
            raise RuntimeError("PPT templates are not loaded")
        return self._templates

    def _ensure_loaded(self) -> None:
        if self._templates is not None:
            return

        templates: dict[str, PPTTemplate] = {}

        for template_id in REQUIRED_TEMPLATE_IDS:
            directory = self.template_root / template_id
            if not directory.exists():
                raise RuntimeError(f"required PPT template directory not found: {directory}")

            template = self._load_directory(directory)
            if template.manifest.id != template_id:
                raise ValueError(
                    f"template directory {template_id!r} contains manifest id {template.manifest.id!r}"
                )

            templates[template_id] = template

        self._templates = templates

    @staticmethod
    def _load_directory(directory: Path) -> PPTTemplate:
        manifest_path = directory / "manifest.json"
        tokens_path = directory / "tokens.css"
        layouts_path = directory / "layouts.css"
        motion_path = directory / "motion.css"

        for path in (manifest_path, tokens_path, layouts_path, motion_path):
            if not path.exists():
                raise RuntimeError(f"PPT template file missing: {path}")

        manifest = PPTTemplateManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )

        if manifest.id != directory.name:
            raise ValueError(
                f"template id {manifest.id!r} does not match directory {directory.name!r}"
            )

        required_types = set(get_args(SlideType))
        layout_types = {layout.type for layout in manifest.layouts}
        missing_types = required_types - layout_types
        if missing_types:
            raise ValueError(
                f"template {manifest.id} misses layouts for slide types: {sorted(missing_types)}"
            )

        layout_ids = [layout.id for layout in manifest.layouts]
        if len(layout_ids) != len(set(layout_ids)):
            raise ValueError(f"duplicate layout id in template {manifest.id}")

        return PPTTemplate(
            manifest=manifest,
            tokens_css=tokens_path.read_text(encoding="utf-8"),
            layouts_css=layouts_path.read_text(encoding="utf-8"),
            motion_css=motion_path.read_text(encoding="utf-8"),
        )


@dataclass(frozen=True, slots=True)
class ResolvedPPTSlide:
    spec: PPTSlide
    layout: PPTLayout


@dataclass(frozen=True, slots=True)
class ResolvedPPT:
    plan: PPTPlan
    template: PPTTemplate
    slides: tuple[ResolvedPPTSlide, ...]


def get_ppt_template_catalog() -> PPTTemplateCatalog:
    return PPTTemplateCatalog()