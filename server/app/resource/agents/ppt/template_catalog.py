"""PPT 模板目录管理。

提供模板配置加载、合并和推荐功能。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.shared.paths import WORKPLACE_DIR

logger = get_logger(__name__)

# 默认模板 ID
DEFAULT_TEMPLATE_ID = "cn_ink_education"

# 模板基础目录
TEMPLATE_BASE_DIR = Path(__file__).parent.parent.parent.parent.parent / "template"

# 内置模板规格
BUILTIN_TEMPLATES: dict[str, dict[str, Any]] = {
    "cn_ink_education": {
        "name": "中国风教育教学模板",
        "description": "淡雅水墨风格的教学演示模板，适合说课、公开课、信息化教学、示范课、教育培训等场景。",
        "style": "modern_minimal",
        "template_file": "中国风.pptx",
        "config_file": "template.config.json",
    },
}


def get_builtin_template_spec(template_id: str) -> dict[str, Any] | None:
    """获取内置模板规格。

    参数：
    - template_id: 模板标识

    返回：
    - 模板规格字典，不存在时返回 None
    """
    return BUILTIN_TEMPLATES.get(template_id)


def merge_template_config(template_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """合并模板配置。

    将内置模板规格与传入配置合并，确保必要字段存在。

    参数：
    - template_id: 模板标识
    - config: 传入的配置字典

    返回：
    - 合并后的配置字典
    """
    spec = get_builtin_template_spec(template_id)
    if not spec:
        return config

    merged = dict(config)
    merged.setdefault("template_id", template_id)
    merged.setdefault("name", spec.get("name", template_id))
    merged.setdefault("description", spec.get("description", ""))
    merged.setdefault("style", spec.get("style", "modern_minimal"))
    return merged


def recommend_template_id(user_profile: dict[str, Any] | None, style: str | None) -> str | None:
    """根据用户画像和风格推荐模板。

    参数：
    - user_profile: 用户画像字典
    - style: 风格字符串

    返回：
    - 推荐的模板 ID，无法推荐时返回 None
    """
    # 目前只有默认模板，直接返回
    return DEFAULT_TEMPLATE_ID


def load_template_config(template_id: str) -> dict[str, Any]:
    """加载模板配置文件。

    参数：
    - template_id: 模板标识

    返回：
    - 模板配置字典

    抛出：
    - FileNotFoundError: 配置文件不存在
    """
    # 尝试从模板目录加载
    template_dir = TEMPLATE_BASE_DIR / f"淡雅水墨主题教育模版"
    config_path = template_dir / "template.config.json"

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return merge_template_config(template_id, config)

    # 尝试从 workplace 加载
    workplace_config = WORKPLACE_DIR / "templates" / template_id / f"{template_id}.config.json"
    if workplace_config.exists():
        with open(workplace_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        return merge_template_config(template_id, config)

    raise FileNotFoundError(f"模板配置文件不存在: {template_id}")
