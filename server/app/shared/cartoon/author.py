"""HTML author — generates the HyperFrames composition HTML using parallel scene agents."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.shared.cartoon.schemas import (
    CartoonVideoRequest,
    SceneBrief,
    StyleDecision,
    VideoBrief,
)

logger = get_logger(__name__)

SCENE_HTML_RE = re.compile(r"<scene-html>(.*?)</scene-html>", re.DOTALL | re.IGNORECASE)
SCENE_GSAP_RE = re.compile(r"<scene-gsap>(.*?)</scene-gsap>", re.DOTALL | re.IGNORECASE)


class HTMLAuthor:
    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    async def _generate_scene(
        self,
        *,
        request: CartoonVideoRequest,
        brief: VideoBrief,
        style: Any,
        scene: SceneBrief,
        scene_index: int,
        prev_scene: SceneBrief | None,
        next_scene: SceneBrief | None,
    ) -> tuple[str, str]:
        """Generate HTML and GSAP code for a single scene."""
        # Convert ms word timestamps to a readable seconds-based timeline for the LLM
        if scene.words:
            words_timeline = []
            for w in scene.words:
                start_sec = round(w.start_ms / 1000.0, 3)
                end_sec = round(w.end_ms / 1000.0, 3)
                words_timeline.append(f"  {start_sec}s - {end_sec}s: '{w.text}'")
            words_context = "\n".join(words_timeline)
        else:
            words_context = "  No speech word timestamps available."

        prompt = prompts.get("cartoon").render(
            "scene_html",
            request=request.model_dump_json(indent=2),
            brief=brief.model_dump_json(indent=2),
            style=style.model_dump_json(indent=2),
            scene=scene.model_dump_json(indent=2),
            scene_index=str(scene_index),
            prev_scene=prev_scene.model_dump_json(indent=2) if prev_scene else "None",
            next_scene=next_scene.model_dump_json(indent=2) if next_scene else "None",
            words_context=words_context,
        )

        response = await self.llm.ainvoke(prompt, max_tokens=4096)
        content = response if isinstance(response, str) else response.content
        content_str = str(content or "").strip()

        # Parse tags
        html_match = SCENE_HTML_RE.search(content_str)
        gsap_match = SCENE_GSAP_RE.search(content_str)

        html_part = html_match.group(1).strip() if html_match else ""
        gsap_part = gsap_match.group(1).strip() if gsap_match else ""

        # Robust fallbacks if tags are missing or improperly closed
        if not html_part:
            fallback_match = re.search(
                r"(<div\s+class=\"scene/s+clip\".*?</div>)",
                content_str,
                re.DOTALL | re.IGNORECASE,
            )
            if not fallback_match:
                fallback_match = re.search(
                    r"(<div\s+class=\"[^\"]*scene[^\"]*\".*?</div>)",
                    content_str,
                    re.DOTALL | re.IGNORECASE,
                )
            if fallback_match:
                html_part = fallback_match.group(1).strip()
            else:
                html_part = f"<!-- Failed to parse scene {scene_index} HTML -->"

        if not gsap_part:
            fallback_js = re.sub(r"<[^>]+>", "", content_str)
            gsap_part = fallback_js.strip()

        return html_part, gsap_part

    async def author(
        self,
        *,
        request: CartoonVideoRequest,
        brief: VideoBrief,
        style: StyleDecision,
    ) -> str:
        selected_style = style.selected

        # 1. Generate Base HTML Skeleton
        base_prompt = prompts.get("cartoon").render(
            "base_html",
            request=request.model_dump_json(indent=2),
            brief=brief.model_dump_json(indent=2),
            style=selected_style.model_dump_json(indent=2),
            total_duration=str(brief.total_duration),
        )
        base_response = await self.llm.ainvoke(base_prompt, max_tokens=4096)
        base_content = base_response if isinstance(base_response, str) else base_response.content
        skeleton = str(base_content or "").strip()

        # Clean outer markdown fence on base if any
        if skeleton.startswith("```"):
            skeleton = re.sub(r"^```[a-zA-Z0-9]*\n", "", skeleton)
            skeleton = re.sub(r"\n```$", "", skeleton)

        # 2. Prepare Parallel Scene Tasks
        tasks = []
        scenes = brief.scenes
        for i, scene in enumerate(scenes):
            prev_scene = scenes[i - 1] if i > 0 else None
            next_scene = scenes[i + 1] if i < len(scenes) - 1 else None
            tasks.append(
                self._generate_scene(
                    request=request,
                    brief=brief,
                    style=selected_style,
                    scene=scene,
                    scene_index=i,
                    prev_scene=prev_scene,
                    next_scene=next_scene,
                )
            )

        # 3. Execute concurrently
        results = await asyncio.gather(*tasks)

        # 4. Extract, stitch audio programmatically
        all_html_clips = []
        all_gsap_code = []
        for i, (html_part, gsap_part) in enumerate(results):
            scene = scenes[i]
            # Programmatically prepend the audio tag inside the scene div to guarantee correctness
            # Duration of audio is duration of scene minus the 0.4s tail padding
            audio_duration = round(max(0.1, scene.duration - 0.4), 3)
            audio_tag = f'\n    <audio data-start="{scene.start_time}" data-duration="{audio_duration}" data-track-index="1" data-volume="1.0" src="{scene.audio_path}"></audio>\n'
            
            # Insert right after the scene div start
            modified_html = re.sub(
                r'(<div\s+class="[^"]*scene[^"]*"[^>]*>)',
                rf'\1{audio_tag}',
                html_part,
                count=1,
                flags=re.IGNORECASE
            )
            all_html_clips.append(modified_html)
            all_gsap_code.append(gsap_part)

        stitched_html = "\n\n  ".join(all_html_clips)
        stitched_gsap = "\n\n    ".join(all_gsap_code)

        # 5. Inject into skeleton
        final_html = skeleton
        final_html = final_html.replace("<!-- [SCENES_HTML] -->", stitched_html)
        final_html = final_html.replace("// [SCENES_GSAP]", stitched_gsap)

        return final_html

