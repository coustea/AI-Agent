"""Template discovery and strict contract validation for cartoon compositions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.shared.cartoon.schemas import (
    ACTION_KINDS,
    VISUAL_KINDS,
    TeachingLesson,
)


REQUIRED_SLOTS = frozenset(
    {
        "header",
        "stage",
        "state-rail",
        "captions",
        "progress",
    }
)

_REQUIRED_FILES = (
    "composition",
    "tokens",
    "layout",
    "motion",
)


@dataclass(frozen=True)
class CartoonTemplate:
    id: str
    version: str
    root: Path
    composition: Path
    tokens: Path
    layout: Path
    motion: Path
    visual_kinds: frozenset[str]
    actions: frozenset[str]
    slots: frozenset[str]


class CartoonTemplateCatalog:
    def __init__(
        self,
        root: Path | None = None,
    ) -> None:
        self.root = (
            root
            or Path(__file__).with_name(
                "templates"
            )
        ).resolve()

    def get(
        self,
        template_id: str,
    ) -> CartoonTemplate:
        root = (
            self.root
            / template_id
        ).resolve()

        try:
            root.relative_to(
                self.root
            )
        except ValueError as exc:
            raise ValueError(
                "非法 cartoon 模板路径: "
                f"{template_id}"
            ) from exc

        manifest_path = (
            root
            / "manifest.json"
        )

        if not manifest_path.is_file():
            raise ValueError(
                "未知 cartoon 模板: "
                f"{template_id}"
            )

        try:
            data = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "模板清单不是有效 JSON: "
                f"{manifest_path}: {exc}"
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "模板清单必须是 JSON object: "
                f"{manifest_path}"
            )

        if (
            data.get("schema")
            != "cartoon-template/v1"
        ):
            raise ValueError(
                "模板 schema 无效: "
                f"{manifest_path}"
            )

        if (
            data.get("id")
            != template_id
        ):
            raise ValueError(
                "模板 id 与目录不一致: "
                f"{manifest_path}"
            )

        files = data.get(
            "files"
        )

        if not isinstance(
            files,
            dict,
        ):
            raise ValueError(
                "模板 files 字段无效: "
                f"{manifest_path}"
            )

        paths = {
            name: self._resolve_template_file(
                root,
                files.get(name),
                name,
            )
            for name
            in _REQUIRED_FILES
        }

        slots = self._string_set(
            data.get("slots"),
            "slots",
        )

        missing_slots = (
            REQUIRED_SLOTS
            - slots
        )

        if missing_slots:
            raise ValueError(
                "模板缺少必需槽位: "
                f"{sorted(missing_slots)}"
            )

        visual_kinds = self._string_set(
            data.get(
                "visual_kinds"
            ),
            "visual_kinds",
        )

        actions = self._string_set(
            data.get("actions"),
            "actions",
        )

        unknown_visual_kinds = (
            visual_kinds
            - set(VISUAL_KINDS)
        )

        unknown_actions = (
            actions
            - set(ACTION_KINDS)
        )

        if unknown_visual_kinds:
            raise ValueError(
                "模板声明了未知 visual kind: "
                f"{sorted(unknown_visual_kinds)}"
            )

        if unknown_actions:
            raise ValueError(
                "模板声明了未知 action: "
                f"{sorted(unknown_actions)}"
            )

        if not visual_kinds:
            raise ValueError(
                "模板 visual_kinds 不能为空"
            )

        if not actions:
            raise ValueError(
                "模板 actions 不能为空"
            )

        version = str(
            data.get("version")
            or ""
        ).strip()

        if not version:
            raise ValueError(
                "模板 version 不能为空: "
                f"{manifest_path}"
            )

        return CartoonTemplate(
            id=template_id,
            version=version,
            root=root,
            composition=(
                paths["composition"]
            ),
            tokens=paths["tokens"],
            layout=paths["layout"],
            motion=paths["motion"],
            visual_kinds=(
                visual_kinds
            ),
            actions=actions,
            slots=slots,
        )

    def validate_lesson(
        self,
        template: CartoonTemplate,
        lesson: TeachingLesson,
    ) -> None:
        visual_kinds = {
            scene.visual_model.kind
            for scene in lesson.scenes
        }

        actions = {
            action.kind
            for scene in lesson.scenes
            for step in scene.steps
            for action in step.actions
        }

        missing_kinds = (
            visual_kinds
            - template.visual_kinds
        )

        missing_actions = (
            actions
            - template.actions
        )

        if missing_kinds:
            raise ValueError(
                f"模板 {template.id} "
                "不支持 visual model: "
                f"{sorted(missing_kinds)}"
            )

        if missing_actions:
            raise ValueError(
                f"模板 {template.id} "
                "不支持 actions: "
                f"{sorted(missing_actions)}"
            )

    @staticmethod
    def _resolve_template_file(
        root: Path,
        raw_value: Any,
        field_name: str,
    ) -> Path:
        if (
            not isinstance(
                raw_value,
                str,
            )
            or not raw_value.strip()
        ):
            raise ValueError(
                "模板缺少文件配置: "
                f"{field_name}"
            )

        path = (
            root
            / raw_value
        ).resolve()

        try:
            path.relative_to(
                root
            )
        except ValueError as exc:
            raise ValueError(
                "模板文件越界: "
                f"{field_name}={raw_value}"
            ) from exc

        if not path.is_file():
            raise ValueError(
                "模板文件不存在: "
                f"{path}"
            )

        return path

    @staticmethod
    def _string_set(
        value: Any,
        field_name: str,
    ) -> frozenset[str]:
        if (
            not isinstance(
                value,
                list,
            )
            or any(
                not isinstance(
                    item,
                    str,
                )
                for item
                in value
            )
        ):
            raise ValueError(
                f"模板 {field_name} "
                "必须是字符串数组"
            )

        normalized = [
            item.strip()
            for item in value
        ]

        if any(
            not item
            for item
            in normalized
        ):
            raise ValueError(
                f"模板 {field_name} "
                "不能包含空字符串"
            )

        if (
            len(normalized)
            != len(set(normalized))
        ):
            raise ValueError(
                f"模板 {field_name} "
                "包含重复值"
            )

        return frozenset(
            normalized
        )