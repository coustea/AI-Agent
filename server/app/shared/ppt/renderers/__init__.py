from app.shared.ppt.renderers.base import SlideBodyRenderer
from app.shared.ppt.renderers.teaching_white import TeachingWhiteRenderer
from app.shared.ppt.renderers.technical_atlas import TechnicalAtlasRenderer


def get_slide_body_renderer(template_id: str) -> SlideBodyRenderer:
    if template_id == "technical-atlas":
        return TechnicalAtlasRenderer()
    return TeachingWhiteRenderer()


__all__ = [
    "SlideBodyRenderer",
    "TeachingWhiteRenderer",
    "TechnicalAtlasRenderer",
    "get_slide_body_renderer",
]