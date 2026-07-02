from __future__ import annotations

import functools
import tempfile
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator, Literal

from playwright.async_api import Browser, Error as PlaywrightError, async_playwright

from app.infra.logging import get_logger
from app.shared.ppt.schemas import (
    DeckBrief,
    VisualAudit,
    VisualQAProblem,
)

logger = get_logger(__name__)


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _serve_html(html: str) -> Iterator[str]:
    with tempfile.TemporaryDirectory(prefix="ppt-visual-qa-") as directory:
        Path(directory, "index.html").write_text(html, encoding="utf-8")
        handler = functools.partial(_QuietHandler, directory=directory)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/index.html"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class BrowserVisualQA:
    """Render every slide at desktop and phone viewports before publication."""

    VIEWPORTS = (
        ("desktop", 1280, 720, False),
        ("mobile", 390, 844, True),
    )

    async def audit(self, html: str, brief: DeckBrief) -> VisualAudit:
        del brief
        problems: list[VisualQAProblem] = []
        try:
            with _serve_html(html) as url:
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=True)
                    try:
                        for viewport, width, height, is_mobile in self.VIEWPORTS:
                            problems.extend(
                                await self._audit_viewport(
                                    browser,
                                    url,
                                    viewport=viewport,
                                    width=width,
                                    height=height,
                                    is_mobile=is_mobile,
                                )
                            )
                    finally:
                        await browser.close()
        except PlaywrightError as exc:
            logger.error("PPT browser QA could not launch Chromium: %s", exc)
            problems.append(
                self._problem(
                    "desktop",
                    0,
                    "other",
                    f"Chromium is unavailable: {exc}",
                )
            )
        except Exception as exc:
            logger.exception("PPT browser QA failed")
            problems.append(
                self._problem("desktop", 0, "other", f"visual QA failed: {exc}")
            )

        return VisualAudit(
            passed=not any(problem.severity == "critical" for problem in problems),
            problems=problems,
        )

    async def _audit_viewport(
        self,
        browser: Browser,
        url: str,
        *,
        viewport: Literal["desktop", "mobile"],
        width: int,
        height: int,
        is_mobile: bool,
    ) -> list[VisualQAProblem]:
        problems: list[VisualQAProblem] = []
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            is_mobile=is_mobile,
            has_touch=is_mobile,
        )
        page = await context.new_page()
        runtime_errors: list[str] = []
        page.on("pageerror", lambda error: runtime_errors.append(str(error)))
        page.on(
            "console",
            lambda message: runtime_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        try:
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(250)
            for error in runtime_errors:
                problems.append(
                    self._problem(viewport, 0, "script_error", error)
                )

            geometry = await page.evaluate(
                """() => {
                    const stage = document.querySelector('.deck-stage');
                    if (!stage) return null;
                    const rect = stage.getBoundingClientRect();
                    const expected = Math.min(innerWidth / 1920, innerHeight / 1080);
                    return {
                        width: rect.width,
                        height: rect.height,
                        expectedWidth: 1920 * expected,
                        expectedHeight: 1080 * expected
                    };
                }"""
            )
            if geometry is None or any(
                abs(geometry[key] - geometry[expected]) > 3
                for key, expected in (
                    ("width", "expectedWidth"),
                    ("height", "expectedHeight"),
                )
            ):
                problems.append(
                    self._problem(
                        viewport,
                        0,
                        "stage_geometry",
                        f"fixed 1920x1080 stage is not scaled to {width}x{height}",
                    )
                )

            slide_count = await page.locator(".deck-stage > .slide").count()
            for index in range(slide_count):
                await page.evaluate(
                    """index => {
                        if (window.presentation?.showSlide) {
                            window.presentation.showSlide(index);
                            return;
                        }
                        document.querySelectorAll('.slide').forEach((slide, i) => {
                            slide.classList.toggle('active', i === index);
                            slide.classList.toggle('visible', i === index);
                        });
                    }""",
                    index,
                )
                await page.wait_for_timeout(120)
                inspection = await page.locator(
                    ".deck-stage > .slide"
                ).nth(index).evaluate(
                    """slide => {
                        const visible = [...slide.querySelectorAll(
                            'h1,h2,h3,h4,p,li,td,th,pre,code,img,video,canvas,svg'
                        )].filter(el => {
                            const style = getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            return style.visibility !== 'hidden' &&
                                style.display !== 'none' &&
                                Number(style.opacity) > 0 &&
                                rect.width > 1 && rect.height > 1;
                        });
                        const slideRect = slide.getBoundingClientRect();
                        const overflow = visible.some(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.left < slideRect.left - 2 ||
                                rect.top < slideRect.top - 2 ||
                                rect.right > slideRect.right + 2 ||
                                rect.bottom > slideRect.bottom + 2;
                        });
                        const tooSmall = visible.some(el => {
                            if (['IMG','VIDEO','CANVAS','SVG'].includes(el.tagName)) return false;
                            return parseFloat(getComputedStyle(el).fontSize) < 16;
                        });
                        const leaves = visible.filter(
                            el => !visible.some(other => other !== el && el.contains(other))
                        );
                        let overlap = false;
                        for (let i = 0; i < leaves.length && !overlap; i++) {
                            const a = leaves[i].getBoundingClientRect();
                            for (let j = i + 1; j < leaves.length; j++) {
                                const b = leaves[j].getBoundingClientRect();
                                const area = Math.max(0, Math.min(a.right, b.right) -
                                    Math.max(a.left, b.left)) *
                                    Math.max(0, Math.min(a.bottom, b.bottom) -
                                    Math.max(a.top, b.top));
                                if (area > 100) { overlap = true; break; }
                            }
                        }
                        return {
                            blank: visible.length === 0 && !slide.innerText.trim(),
                            overflow,
                            tooSmall,
                            overlap
                        };
                    }"""
                )
                for flag, problem_type, summary in (
                    ("blank", "empty", "slide has no visible content"),
                    ("overflow", "overflow", "content escapes slide bounds"),
                    ("tooSmall", "font_size", "text is smaller than 16px"),
                    ("overlap", "overlap", "visible content overlaps"),
                ):
                    if inspection[flag]:
                        problems.append(
                            self._problem(viewport, index, problem_type, summary)
                        )

            if viewport == "desktop" and slide_count > 1:
                await page.evaluate("window.presentation.showSlide(0)")
                await page.keyboard.press("ArrowRight")
                await page.wait_for_timeout(80)
                second_active = await page.locator(
                    ".deck-stage > .slide"
                ).nth(1).evaluate(
                    "slide => slide.classList.contains('active')"
                )
                if not second_active:
                    problems.append(
                        self._problem(
                            viewport,
                            0,
                            "navigation",
                            "ArrowRight does not advance the deck",
                        )
                    )
        finally:
            await context.close()
        return problems

    @staticmethod
    def _problem(
        viewport: Literal["desktop", "mobile"],
        slide_index: int,
        problem_type: str,
        summary: str,
    ) -> VisualQAProblem:
        return VisualQAProblem(
            slide_index=slide_index,
            viewport=viewport,
            problem_type=problem_type,
            element_summary=summary,
            severity="critical",
        )
