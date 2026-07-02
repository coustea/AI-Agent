from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.resource.agents.ppt_pipeline.schemas import DeckBrief, StaticAudit


_LOCAL_PATH = re.compile(r"(?:file://|/(?:Users|home|tmp)/|[A-Za-z]:\\)", re.IGNORECASE)
_ALLOWED_FONT_HOSTS = {
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "api.fontshare.com",
    "cdn.fontshare.com",
}


class StaticValidator:
    """Validate the immutable structure and behavior contract before rendering."""

    def validate(self, html: str, brief: DeckBrief) -> StaticAudit:
        problems: list[str] = []
        lowered = html.lower()

        if not re.match(r"\s*<!doctype html>", html, re.IGNORECASE):
            problems.append("document must start with <!DOCTYPE html>")
        if "```" in html:
            problems.append("document contains a Markdown fence")
        if _LOCAL_PATH.search(html):
            problems.append("document contains a local absolute path")

        soup = BeautifulSoup(html, "html.parser")
        if soup.html is None or soup.head is None or soup.body is None:
            problems.append("document must contain html, head, and body elements")

        viewports = soup.select(".deck-viewport")
        stages = soup.select(".deck-stage")
        slides = soup.select(".deck-stage > .slide")
        if len(viewports) != 1:
            problems.append("document must contain exactly one .deck-viewport")
        if len(stages) != 1:
            problems.append("document must contain exactly one .deck-stage")
        if viewports and stages and stages[0].parent is not viewports[0]:
            problems.append(".deck-stage must be a direct child of .deck-viewport")

        active_indexes = [
            index
            for index, slide in enumerate(slides)
            if {"active", "visible"}.issubset(set(slide.get("class", [])))
        ]
        if active_indexes != [0]:
            problems.append("only the first slide may start active and visible")
        for index, slide in enumerate(slides, start=1):
            if not slide.get_text(" ", strip=True) and not slide.select_one(
                "img, video, canvas, svg, table, pre"
            ):
                problems.append(f"slide {index} is empty")

        slide_count = len(slides)
        if slide_count == 0:
            problems.append("document contains no slides")
        elif slide_count > 16:
            problems.append(f"slide count {slide_count} must not exceed 16 hard cap")
        elif abs(slide_count - brief.target_slide_count) > 2:
            problems.append(
                f"slide count {slide_count} is outside target "
                f"{brief.target_slide_count} +/- 2"
            )

        css = "\n".join(tag.get_text() for tag in soup.find_all("style"))
        compact_css = re.sub(r"\s+", "", css).lower()
        for marker, message in (
            ("width:1920px", "stage CSS must declare width: 1920px"),
            ("height:1080px", "stage CSS must declare height: 1080px"),
            (".deck-viewport", "viewport CSS is missing"),
            (".deck-stage", "stage CSS is missing"),
            (".slide", "slide CSS is missing"),
            ("prefers-reduced-motion", "reduced-motion CSS is missing"),
        ):
            if marker not in compact_css:
                problems.append(message)

        script = "\n".join(tag.get_text() for tag in soup.find_all("script"))
        script_lower = script.lower()
        behavior_markers = {
            "SlidePresentation": "SlidePresentation controller is missing",
            "window.presentation": "window.presentation is missing",
            "keydown": "keyboard navigation is missing",
            "wheel": "wheel navigation is missing",
            "touchstart": "touch navigation is missing",
            "contenteditable": "inline editing is missing",
            "Blob": "Blob HTML download is missing",
            "createObjectURL": "download URL creation is missing",
        }
        for marker, message in behavior_markers.items():
            if marker.lower() not in script_lower:
                problems.append(message)

        for tag in soup.find_all("script", src=True):
            problems.append(f"external script is forbidden: {tag['src']}")
        for tag in soup.find_all("link", href=True):
            rel = {str(value).lower() for value in tag.get("rel", [])}
            if "stylesheet" not in rel:
                continue
            host = urlparse(tag["href"]).hostname
            if host not in _ALLOWED_FONT_HOSTS:
                problems.append(f"external stylesheet is forbidden: {tag['href']}")
        for tag in soup.select("[src]"):
            source = str(tag.get("src", "")).strip()
            if source.startswith(("http://", "https://", "//", "file:")):
                problems.append(f"external media is forbidden: {source}")
        if re.search(r"url\(\s*['\"]?https?://", css, re.IGNORECASE):
            problems.append("inline CSS contains an external asset URL")

        return StaticAudit(
            passed=not problems,
            problems=problems,
            slide_count=slide_count,
        )
