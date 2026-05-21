"""Prompt 注册中心。

职责：
- 启动时从 app/prompts/ 目录预加载所有 prompt 文件
- 提供统一的 prompt 获取和渲染接口
- 运行期间不重新加载，只有重启才重新读取

目录结构：
    app/prompts/
    ├── chat/
    │   └── system.md
    ├── resource/
    │   ├── code.md
    │   └── ...
    └── memory/
        ├── profile.md
        └── ...

使用方式：
    from app.prompts import registry

    text = registry.get("chat/system")
    rendered = registry.render("memory/profile", name="Alice")
    keys = registry.list()
    info = registry.status()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.infra.logging import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent


class PromptRegistry:
    """Prompt 注册中心，启动时预加载所有 prompt 文件到内存。"""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._meta: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load_all(self) -> None:
        """扫描 app/prompts/ 下所有 .md 文件并加载到内存。"""
        if self._loaded:
            return

        if not _PROMPTS_DIR.exists():
            logger.error("[PromptRegistry] prompts 目录不存在: %s", _PROMPTS_DIR)
            self._loaded = True
            return

        count = 0
        for md_file in sorted(_PROMPTS_DIR.rglob("*.md")):
            key = self._file_to_key(md_file)
            try:
                content = md_file.read_text(encoding="utf-8")
                self._store[key] = content
                self._meta[key] = {
                    "path": str(md_file.relative_to(_PROMPTS_DIR)),
                    "size": len(content),
                    "status": "ok",
                }
                count += 1
            except Exception as e:
                logger.error("[PromptRegistry] 加载失败: %s → %s", key, e)
                self._meta[key] = {
                    "path": str(md_file.relative_to(_PROMPTS_DIR)),
                    "size": 0,
                    "status": f"error: {e}",
                }

        self._loaded = True
        logger.info("[PromptRegistry] 加载完成: %d 个 prompt", count)

    def get(self, key: str) -> str:
        """获取 prompt 原始文本。

        Args:
            key: prompt 键名，格式 "module/name"，如 "chat/system"。

        Returns:
            prompt 文本内容，不存在则返回空字符串并打警告日志。
        """
        if not self._loaded:
            self.load_all()

        text = self._store.get(key)
        if text is None:
            logger.warning("[PromptRegistry] prompt 不存在: %s", key)
            return ""
        return text

    def render(self, key: str, **kwargs: Any) -> str:
        """获取 prompt 并填充模板变量。

        Args:
            key: prompt 键名。
            **kwargs: 模板变量。

        Returns:
            填充后的文本。
        """
        text = self.get(key)
        if not text or not kwargs:
            return text
        try:
            return text.format(**kwargs)
        except KeyError as e:
            logger.error("[PromptRegistry] 模板变量缺失: %s → %s", key, e)
            return text

    def list(self) -> list[str]:
        """返回所有已加载的 prompt 键名。"""
        if not self._loaded:
            self.load_all()
        return sorted(self._store.keys())

    def status(self) -> dict[str, dict[str, Any]]:
        """返回每个 prompt 的加载状态详情。"""
        if not self._loaded:
            self.load_all()
        return dict(self._meta)

    def _file_to_key(self, path: Path) -> str:
        """将文件路径转为键名，如 prompts/chat/system.md → chat/system。"""
        rel = path.relative_to(_PROMPTS_DIR)
        parts = list(rel.parts)
        parts[-1] = parts[-1].removesuffix(".md")
        return "/".join(parts)


# 模块级单例
registry = PromptRegistry()


def init_prompts() -> None:
    """初始化 prompt 注册中心，由 main.py 启动时调用。"""
    registry.load_all()
