from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import Field

from app.shared.ppt.models import (
    AnimationKind,
    ContentShape,
    PPTPlan,
    PPTSlide,
    PPTModel,
    SlideRole,
)


class PPTLayout(PPTModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    shapes: list[ContentShape] = Field(min_length=1)
    roles: list[SlideRole] = Field(default_factory=list)
    skeleton: str = Field(min_length=1)
    animation: AnimationKind
    point_capacity: int = Field(default=6, ge=0, le=8)
    step_capacity: int = Field(default=6, ge=0, le=8)


class PPTTemplateManifest(PPTModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    family: str = Field(min_length=1)
    scheme: str = Field(pattern=r"^(light|dark)$")
    tags: list[str] = Field(default_factory=list)
    fallback_layout: str = Field(min_length=1)
    layouts: list[PPTLayout] = Field(min_length=8)


class PPTTemplate(PPTModel):
    manifest: PPTTemplateManifest
    tokens_css: str
    layouts_css: str
    motion_css: str

    @property
    def css(self) -> str:
        return "\n".join((self.tokens_css, self.layouts_css, self.motion_css))


class PPTTemplateCatalog:
    """Load trusted templates and resolve plans to capacity-safe layouts."""

    def __init__(
        self,
        template_root: Path | None = None,
    ):
        self.template_root = (
            template_root or Path(__file__).resolve().parent / "templates"
        )
        self._templates: dict[str, PPTTemplate] | None = None

    def all(self) -> tuple[PPTTemplate, ...]:
        self._ensure_loaded()
        return tuple(
            self._templates[template_id]
            for template_id in sorted(self._templates)
        )

    def get(self, template_id: str) -> PPTTemplate:
        self._ensure_loaded()
        template = self._templates.get(template_id)
        if template is not None:
            return template
        raise KeyError(f"unknown PPT template: {template_id}")

    def _ensure_loaded(self) -> None:
        if self._templates is not None:
            return
        templates: dict[str, PPTTemplate] = {}
        if self.template_root.exists():
            for directory in sorted(
                path for path in self.template_root.iterdir() if path.is_dir()
            ):
                template = self._load_directory(directory)
                if template.manifest.id in templates:
                    raise ValueError(
                        f"duplicate PPT template id: {template.manifest.id}"
                    )
                templates[template.manifest.id] = template
        if "instructional-editorial" not in templates:
            raise RuntimeError("required instructional-editorial PPT template not found")
        self._templates = templates

    @staticmethod
    def _load_directory(directory: Path) -> PPTTemplate:
        manifest_path = directory / "manifest.json"
        manifest = PPTTemplateManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        if manifest.id != directory.name:
            raise ValueError(
                f"template id {manifest.id!r} does not match directory {directory.name!r}"
            )
        layout_ids = {layout.id for layout in manifest.layouts}
        if len(layout_ids) != len(manifest.layouts):
            raise ValueError(f"duplicate layout id in {manifest.id}")
        if manifest.fallback_layout not in layout_ids:
            raise ValueError(f"fallback layout missing in {manifest.id}")
        return PPTTemplate(
            manifest=manifest,
            tokens_css=(directory / "tokens.css").read_text(encoding="utf-8"),
            layouts_css=(directory / "layouts.css").read_text(encoding="utf-8"),
            motion_css=(directory / "motion.css").read_text(encoding="utf-8"),
        )

    def resolve(
        self,
        plan: PPTPlan,
        *,
        template_id: str = "auto",
    ) -> "ResolvedPPT":
        template = (
            self._select_template(plan)
            if template_id == "auto"
            else self.get(template_id)
        )
        resolved: list[ResolvedPPTSlide] = []
        recent_skeletons: list[str] = []
        used_skeletons: set[str] = set()  # 新增：全局已使用骨架

        for index, slide in enumerate(plan.slides):
            layout = self._select_layout(
                template,
                slide,
                index=index,
                recent_skeletons=recent_skeletons,
                used_skeletons=used_skeletons,
                total_slides=len(plan.slides),
            )
            normalized = slide.model_copy(
                update={
                    "points": slide.points[: layout.point_capacity],
                    "steps": slide.steps[: layout.step_capacity],
                }
            )
            resolved.append(ResolvedPPTSlide(spec=normalized, layout=layout))
            recent_skeletons = [*recent_skeletons[-1:], layout.skeleton]
            used_skeletons.add(layout.skeleton)

        return ResolvedPPT(plan=plan, template=template, slides=tuple(resolved))

    def _select_template(self, plan: PPTPlan) -> PPTTemplate:
        preference = plan.template_preference
        shape_counts: dict[str, int] = {}
        for slide in plan.slides:
            shape_counts[slide.shape] = shape_counts.get(slide.shape, 0) + 1
        technical_weight = sum(
            shape_counts.get(shape, 0) for shape in ("system", "code", "sequence")
        )

        def score(template: PPTTemplate) -> tuple[int, str]:
            manifest = template.manifest
            value = 0
            if preference.family != "auto" and manifest.family == preference.family:
                value += 20
            if preference.scheme != "auto" and manifest.scheme == preference.scheme:
                value += 12
            if manifest.family == "technical":
                value += technical_weight * 2
            else:
                value += len(plan.slides) - technical_weight
            haystack = " ".join(manifest.tags).lower()
            value += sum(3 for word in preference.keywords if word.lower() in haystack)
            return value, manifest.id

        return max(self.all(), key=score)

    @staticmethod
    def _select_layout(
        template: PPTTemplate,
        slide: PPTSlide,
        *,
        index: int,
        recent_skeletons: list[str],
        used_skeletons: set[str],
        total_slides: int,
    ) -> PPTLayout:
        layouts = template.manifest.layouts

        # 强制章节分隔：每4页插入 section-marker
        if index > 0 and index % 4 == 0 and slide.role != "section":
            section_layout = next(
                (l for l in layouts if l.id == "section-marker"),
                None
            )
            if section_layout and slide.role in section_layout.roles:
                return section_layout

        if slide.preferred_layout:
            preferred = next(
                (
                    item
                    for item in layouts
                    if item.id == slide.preferred_layout
                    and slide.shape in item.shapes
                    and (not item.roles or slide.role in item.roles)
                ),
                None,
            )
            if preferred is not None:
                return preferred

        candidates = [
            layout
            for layout in layouts
            if slide.shape in layout.shapes
            and (not layout.roles or slide.role in layout.roles)
        ]
        if not candidates:
            candidates = [
                layout for layout in layouts if slide.shape in layout.shapes
            ]
        if not candidates:
            return next(
                layout
                for layout in layouts
                if layout.id == template.manifest.fallback_layout
            )

        def score(layout: PPTLayout) -> tuple[int, str]:
            value = 0

            # 角色匹配加分
            if slide.role in layout.roles:
                value += 20

            # 动画匹配加分
            if slide.animation == layout.animation:
                value += 8

            # 重复惩罚：最近3页用过的骨架大幅扣分
            if layout.skeleton in recent_skeletons:
                value -= 100  # 大幅提高惩罚

            # 全局未使用加分：鼓励使用新布局
            if layout.skeleton not in used_skeletons:
                value += 30

            # 章节节奏：每4页强制降低非章节页评分
            if index and index % 4 == 0 and layout.skeleton in recent_skeletons:
                value -= 50

            return value, layout.id

        return max(candidates, key=score)


@dataclass(frozen=True, slots=True)
class ResolvedPPTSlide:
    spec: PPTSlide
    layout: PPTLayout


@dataclass(frozen=True, slots=True)
class ResolvedPPT:
    plan: PPTPlan
    template: PPTTemplate
    slides: tuple[ResolvedPPTSlide, ...]


@lru_cache(maxsize=1)
def get_ppt_template_catalog() -> PPTTemplateCatalog:
    return PPTTemplateCatalog()
