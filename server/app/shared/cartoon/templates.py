"""Template discovery and contract validation for cartoon compositions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.shared.cartoon.schemas import ActionKind, TeachingLesson, VisualKind


REQUIRED_SLOTS = {"header", "stage", "state-rail", "captions", "progress"}


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
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).with_name("templates")

    def get(self, template_id: str) -> CartoonTemplate:
        root = self.root / template_id
        manifest_path = root / "manifest.json"
        if not manifest_path.is_file():
            raise ValueError(f"未知 cartoon 模板: {template_id}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("schema") != "cartoon-template/v1" or data.get("id") != template_id:
            raise ValueError(f"模板清单无效: {manifest_path}")
        files = data.get("files") or {}
        paths = {name: root / str(files.get(name, "")) for name in ("composition", "tokens", "layout", "motion")}
        if any(not path.is_file() for path in paths.values()):
            raise ValueError(f"模板缺少必需文件: {template_id}")
        slots = frozenset(data.get("slots") or [])
        if not REQUIRED_SLOTS.issubset(slots):
            raise ValueError(f"模板缺少必需槽位: {sorted(REQUIRED_SLOTS - slots)}")
        return CartoonTemplate(
            id=template_id,
            version=str(data.get("version", "0")),
            root=root,
            composition=paths["composition"],
            tokens=paths["tokens"],
            layout=paths["layout"],
            motion=paths["motion"],
            visual_kinds=frozenset(data.get("visual_kinds") or []),
            actions=frozenset(data.get("actions") or []),
            slots=slots,
        )

    def validate_lesson(self, template: CartoonTemplate, lesson: TeachingLesson) -> None:
        visual_kinds = {scene.visual_model.kind for scene in lesson.scenes}
        actions = {action.kind for scene in lesson.scenes for step in scene.steps for action in step.actions}
        missing_kinds = visual_kinds - template.visual_kinds
        missing_actions = actions - template.actions
        if missing_kinds:
            raise ValueError(f"模板 {template.id} 不支持 visual model: {sorted(missing_kinds)}")
        if missing_actions:
            raise ValueError(f"模板 {template.id} 不支持 actions: {sorted(missing_actions)}")
