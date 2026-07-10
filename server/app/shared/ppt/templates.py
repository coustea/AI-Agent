from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from pydantic import Field

from app.shared.ppt.models import (
    AnimationKind,
    PPTModel,
    PPTPlan,
    PPTSlide,
    SlideType,
)


class PPTLayout(PPTModel):
    id: str = Field(
        pattern=r"^[a-z0-9-]+$"
    )

    name: str = Field(min_length=1)
    type: SlideType

    animation: AnimationKind = "reveal"

    skeleton: str = Field(
        default="default",
        min_length=1,
        max_length=48,
    )


class PPTTemplateManifest(PPTModel):
    id: str = Field(
        pattern=r"^[a-z0-9-]+$"
    )

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)

    family: Literal[
        "teaching",
        "technical",
    ]

    scheme: Literal[
        "light",
        "dark",
    ]

    tags: list[str] = Field(
        default_factory=list
    )

    layouts: list[PPTLayout] = Field(
        min_length=12
    )


class PPTTemplate(PPTModel):
    manifest: PPTTemplateManifest

    tokens_css: str
    layouts_css: str
    motion_css: str

    @property
    def css(self) -> str:
        return "\n".join(
            (
                self.tokens_css,
                self.layouts_css,
                self.motion_css,
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedPPTSlide:
    spec: PPTSlide
    layout: PPTLayout


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedPPT:
    plan: PPTPlan
    template: PPTTemplate
    slides: tuple[ResolvedPPTSlide, ...]


class PPTTemplateCatalog:
    """
    自动发现模板目录。

    模板根目录下的每一个子目录都是一套模板。
    不再在后端写死 teaching-white 或 tech-blueprint。
    """

    def __init__(
        self,
        template_root: Path | None = None,
    ) -> None:
        self.template_root = (
            template_root
            or Path(__file__).resolve().parent
            / "templates"
        )

        self._templates: (
            dict[str, PPTTemplate] | None
        ) = None

    def all(
        self,
    ) -> tuple[PPTTemplate, ...]:
        return tuple(
            self._loaded().values()
        )

    def get(
        self,
        template_id: str,
    ) -> PPTTemplate:
        try:
            return self._loaded()[
                template_id
            ]

        except KeyError as exc:
            raise KeyError(
                f"unknown PPT template: "
                f"{template_id}"
            ) from exc

    def resolve(
        self,
        plan: PPTPlan,
        *,
        template_id: str = "auto",
    ) -> ResolvedPPT:
        template = (
            self._select(plan)
            if template_id == "auto"
            else self.get(template_id)
        )

        layouts = {
            layout.type: layout
            for layout in template.manifest.layouts
        }

        resolved_slides: list[
            ResolvedPPTSlide
        ] = []

        for slide in plan.slides:
            layout = layouts[
                slide.type
            ]

            normalized_slide = (
                slide.model_copy(
                    update={
                        "animation": (
                            layout.animation
                        )
                    }
                )
            )

            resolved_slides.append(
                ResolvedPPTSlide(
                    spec=normalized_slide,
                    layout=layout,
                )
            )

        return ResolvedPPT(
            plan=plan,
            template=template,
            slides=tuple(resolved_slides),
        )

    def _select(
        self,
        plan: PPTPlan,
    ) -> PPTTemplate:
        templates = list(
            self._loaded().values()
        )

        preference = (
            plan.template_preference
        )

        candidates = templates

        if preference.family != "auto":
            matched = [
                template
                for template in candidates
                if (
                    template.manifest.family
                    == preference.family
                )
            ]

            if matched:
                candidates = matched

        if preference.scheme != "auto":
            matched = [
                template
                for template in candidates
                if (
                    template.manifest.scheme
                    == preference.scheme
                )
            ]

            if matched:
                candidates = matched

        keyword_text = " ".join(
            preference.keywords
        ).lower()

        if keyword_text:
            ranked = sorted(
                candidates,
                key=lambda template: sum(
                    tag.lower() in keyword_text
                    for tag
                    in template.manifest.tags
                ),
                reverse=True,
            )

            return ranked[0]

        return candidates[0]

    def _loaded(
        self,
    ) -> dict[str, PPTTemplate]:
        if self._templates is None:
            self._templates = (
                self._discover()
            )

        return self._templates

    def _discover(
        self,
    ) -> dict[str, PPTTemplate]:
        if not self.template_root.exists():
            raise RuntimeError(
                "PPT template root not found: "
                f"{self.template_root}"
            )

        templates: dict[
            str,
            PPTTemplate,
        ] = {}

        directories = sorted(
            path
            for path
            in self.template_root.iterdir()
            if path.is_dir()
        )

        for directory in directories:
            manifest_path = (
                directory
                / "manifest.json"
            )

            if not manifest_path.exists():
                continue

            template = (
                self._load_directory(
                    directory
                )
            )

            template_id = (
                template.manifest.id
            )

            if template_id in templates:
                raise ValueError(
                    "duplicate PPT template id: "
                    f"{template_id}"
                )

            templates[template_id] = (
                template
            )

        if not templates:
            raise RuntimeError(
                "no valid PPT templates found"
            )

        return templates

    @staticmethod
    def _load_directory(
        directory: Path,
    ) -> PPTTemplate:
        paths = {
            filename: directory / filename
            for filename in (
                "manifest.json",
                "tokens.css",
                "layouts.css",
                "motion.css",
            )
        }

        missing_files = [
            filename
            for filename, path in paths.items()
            if not path.exists()
        ]

        if missing_files:
            raise RuntimeError(
                f"template {directory.name} "
                f"misses files: {missing_files}"
            )

        manifest = (
            PPTTemplateManifest
            .model_validate_json(
                paths["manifest.json"]
                .read_text(
                    encoding="utf-8"
                )
            )
        )

        if manifest.id != directory.name:
            raise ValueError(
                "template directory name "
                "must equal manifest id"
            )

        required_types = set(
            get_args(SlideType)
        )

        actual_types = {
            layout.type
            for layout in manifest.layouts
        }

        missing_types = (
            required_types
            - actual_types
        )

        if missing_types:
            raise ValueError(
                f"template {manifest.id} "
                "misses layouts: "
                f"{sorted(missing_types)}"
            )

        if (
            len(actual_types)
            != len(manifest.layouts)
        ):
            raise ValueError(
                f"template {manifest.id} "
                "contains duplicate slide types"
            )

        return PPTTemplate(
            manifest=manifest,
            tokens_css=(
                paths["tokens.css"]
                .read_text(
                    encoding="utf-8"
                )
            ),
            layouts_css=(
                paths["layouts.css"]
                .read_text(
                    encoding="utf-8"
                )
            ),
            motion_css=(
                paths["motion.css"]
                .read_text(
                    encoding="utf-8"
                )
            ),
        )


def get_ppt_template_catalog(
) -> PPTTemplateCatalog:
    return PPTTemplateCatalog()