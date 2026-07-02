from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict


ASSET_DIR = Path(__file__).with_name("assets")


class FrontendSlidesAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viewport_css: str
    html_contract: str
    animation_guide: str
    safe_presets: list[dict[str, object]]
    bold_templates: list[dict[str, object]]


@lru_cache(maxsize=1)
def load_frontend_slides_assets() -> FrontendSlidesAssets:
    catalog = json.loads(
        (ASSET_DIR / "style-catalog.json").read_text(encoding="utf-8")
    )
    return FrontendSlidesAssets(
        viewport_css=(ASSET_DIR / "viewport-base.css").read_text(encoding="utf-8"),
        html_contract=(ASSET_DIR / "html-contract.md").read_text(encoding="utf-8"),
        animation_guide=(ASSET_DIR / "animation-guide.md").read_text(
            encoding="utf-8"
        ),
        safe_presets=catalog["safe_presets"],
        bold_templates=catalog["bold_templates"],
    )
