"""Shared prompt loading utilities.

```
ModulePromptLoader  — loads .md files from one module's prompts/ directory
PromptRegistry      — central singleton that owns all module loaders
prompts             — the global PromptRegistry instance
```

Usage::

    from app.infra.prompts import prompts

    prompts.get("chat").render("tutor_system", session_summary_context=...)
    prompts.get("resource").get("ppt")
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger

logger = get_logger(__name__)

_PLACEHOLDER_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")


class ModulePromptLoader:
    """Load prompt files for a single owning module."""

    def __init__(self, prompt_dir: Path, *, module_name: str) -> None:
        self.prompt_dir = Path(prompt_dir)
        self.module_name = module_name
        self._store: dict[str, str] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load_all(self) -> None:
        if self._loaded:
            return

        if not self.prompt_dir.exists():
            logger.error(
                "[PromptLoader] %s prompt 目录不存在: %s",
                self.module_name,
                self.prompt_dir,
            )
            self._loaded = True
            return

        count = 0
        for md_file in sorted(self.prompt_dir.rglob("*.md")):
            key = self._file_to_key(md_file)
            try:
                content = md_file.read_text(encoding="utf-8")
                self._store[key] = content
                self._meta[key] = {
                    "path": str(md_file.relative_to(self.prompt_dir)),
                    "size": len(content),
                    "status": "ok",
                }
                count += 1
            except Exception as exc:
                logger.error(
                    "[PromptLoader] %s 加载失败: %s -> %s",
                    self.module_name,
                    key,
                    exc,
                )
                self._meta[key] = {
                    "path": str(md_file.relative_to(self.prompt_dir)),
                    "size": 0,
                    "status": f"error: {exc}",
                }

        self._loaded = True
        logger.info(
            "[PromptLoader] %s 加载完成: %d 个 prompt",
            self.module_name,
            count,
        )

    def get(self, key: str) -> str:
        if not self._loaded:
            self.load_all()

        text = self._store.get(key)
        if text is None:
            logger.warning(
                "[PromptLoader] %s prompt 不存在: %s",
                self.module_name,
                key,
            )
            return ""
        return text

    def render(self, key: str, **kwargs: Any) -> str:
        return self.render_text(self.get(key), prompt_key=key, **kwargs)

    def render_text(self, text: str, *, prompt_key: str, **kwargs: Any) -> str:
        if not text or not kwargs:
            return text

        missing: set[str] = set()

        def _replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in kwargs:
                missing.add(name)
                return match.group(0)
            value = kwargs[name]
            return "" if value is None else str(value)

        rendered = _PLACEHOLDER_RE.sub(_replace, text)
        if missing:
            logger.error(
                "[PromptLoader] 模板变量缺失: %s/%s -> %s",
                self.module_name,
                prompt_key,
                ", ".join(sorted(missing)),
            )
        return rendered

    def list(self) -> list[str]:
        if not self._loaded:
            self.load_all()
        return sorted(self._store.keys())

    def status(self) -> dict[str, dict[str, Any]]:
        if not self._loaded:
            self.load_all()
        return dict(self._meta)

    def _file_to_key(self, path: Path) -> str:
        rel = path.relative_to(self.prompt_dir)
        parts = list(rel.parts)
        parts[-1] = parts[-1].removesuffix(".md")
        return "/".join(parts)


class PromptRegistry:
    """Central registry that owns a ModulePromptLoader per business module."""

    def __init__(self) -> None:
        self._loaders: dict[str, ModulePromptLoader] = {}

    def register(self, module_name: str, prompt_dir: Path) -> ModulePromptLoader:
        loader = ModulePromptLoader(prompt_dir, module_name=module_name)
        self._loaders[module_name] = loader
        return loader

    def get(self, module_name: str) -> ModulePromptLoader:
        loader = self._loaders.get(module_name)
        if loader is None:
            raise KeyError(
                f"Prompt module '{module_name}' not registered. "
                f"Available: {sorted(self._loaders)}"
            )
        return loader

    def warm_all(self) -> None:
        for loader in self._loaders.values():
            loader.load_all()

    def status(self) -> dict[str, dict[str, dict[str, Any]]]:
        return {name: loader.status() for name, loader in self._loaders.items()}


# ---------------------------------------------------------------------------
# Global singleton — auto-registers all known modules
# ---------------------------------------------------------------------------
_PROMPTS_PKG_DIR = Path(__file__).resolve().parent   # app/infra/prompts/
_APP_DIR = _PROMPTS_PKG_DIR.parent.parent             # app/

prompts = PromptRegistry()
prompts.register("chat", _APP_DIR / "chat" / "prompts")
prompts.register("chat_memory", _APP_DIR / "chat" / "memory" / "prompts")
prompts.register("resource", _APP_DIR / "resource" / "prompts")
prompts.register("path", _APP_DIR / "path" / "prompts")
prompts.register("profile", _APP_DIR / "profile" / "prompts")
prompts.register("quiz", _APP_DIR / "quiz" / "prompts")
