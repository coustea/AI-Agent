"""CartoonAgent: LLM-driven Markdown DSL → HyperFrames HTML pipeline.

Core flow:
  build_prompt → generate_markdown → parse_markdown → validate_markdown
  → compose_html → validate_html → (repair if needed) → save → render
"""

from __future__ import annotations

import html as html_mod
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.infra.llm import get_llm

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "white_teaching_video"


class CartoonGenerationError(RuntimeError):
    """Raised when cartoon generation fails after max repair attempts."""

    def __init__(self, message: str, *, audit: AuditResult | None = None) -> None:
        super().__init__(message)
        self.audit = audit


@dataclass
class CartoonScene:
    index: int
    title: str
    scene_id: str
    start: float
    duration: float
    scene_type: str
    narration: str
    html: str
    timeline: str


@dataclass
class CartoonDocument:
    title: str
    duration: float
    scenes: list[CartoonScene]


@dataclass
class AuditResult:
    passed: bool
    problems: list[str] = field(default_factory=list)


@dataclass
class CartoonGenerationResult:
    markdown_path: Path
    html_path: Path
    video_path: Path | None
    audit_path: Path
    title: str
    duration: float
    scene_count: int


def _safe_scene_id(raw: str) -> str:
    """Normalize scene id: lowercase, alphanumeric + dash/underscore, no leading digit."""
    value = re.sub(r"[^a-z0-9_-]", "-", raw.strip().lower())
    if not value:
        return "scene"
    if value[0].isdigit():
        value = f"s-{value}"
    return value[:48]


def _escape_attr(value: str) -> str:
    return html_mod.escape(str(value), quote=True)


def _clean_llm_output(text: str) -> str:
    """Remove code fences that LLM may wrap around the markdown."""
    text = text.strip()
    # Remove opening ```markdown or ```md fence
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    # Remove closing ```
    text = re.sub(r"\n```\s*$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Markdown Parser
# ---------------------------------------------------------------------------


def parse_markdown(markdown_text: str) -> CartoonDocument:
    """Parse cartoon.md into a CartoonDocument using regex state machine."""
    text = markdown_text.strip()
    if not text:
        raise ValueError("Markdown 内容为空")

    # Extract title from first # heading
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if not title_match:
        raise ValueError("缺少视频标题 (# 标题)")

    title = title_match.group(1).strip()

    # Extract global @duration
    duration_match = re.search(r"@duration:\s*([\d.]+)", text)
    if not duration_match:
        raise ValueError("缺少全局 @duration")

    duration = float(duration_match.group(1))

    # Split by ## Scene headings
    scene_blocks = re.split(r"(?=^##\s+Scene\s+\d+)", text, flags=re.MULTILINE)

    scenes: list[CartoonScene] = []
    for block in scene_blocks:
        block = block.strip()
        if not block.startswith("## Scene"):
            continue

        # Extract scene header
        header_match = re.match(r"##\s+Scene\s+\d+:\s*(.+)$", block, re.MULTILINE)
        if not header_match:
            continue

        scene_title = header_match.group(1).strip()

        # Extract @id, @start, @duration, @type
        scene_id_match = re.search(r"@id:\s*(\S+)", block)
        start_match = re.search(r"@start:\s*([\d.]+)", block)
        scene_duration_match = re.search(r"@duration:\s*([\d.]+)", block)
        type_match = re.search(r"@type:\s*(\S+)", block)

        if not scene_id_match:
            raise ValueError(f"Scene '{scene_title}' 缺少 @id")
        if not start_match:
            raise ValueError(f"Scene '{scene_title}' 缺少 @start")
        if not scene_duration_match:
            raise ValueError(f"Scene '{scene_title}' 缺少 @duration")
        if not type_match:
            raise ValueError(f"Scene '{scene_title}' 缺少 @type")

        scene_id = _safe_scene_id(scene_id_match.group(1))
        start = float(start_match.group(1))
        scene_duration = float(scene_duration_match.group(1))
        scene_type = type_match.group(1).strip()

        # Extract ### Narration
        narration = ""
        narration_match = re.search(
            r"###\s+Narration\s*\n(.*?)(?=\n###\s|\Z)",
            block,
            re.DOTALL,
        )
        if narration_match:
            narration = narration_match.group(1).strip()

        # Extract ### HTML code block
        html_content = ""
        html_match = re.search(
            r"###\s+HTML\s*\n```html\s*\n(.*?)```",
            block,
            re.DOTALL,
        )
        if html_match:
            html_content = html_match.group(1).strip()

        # Extract ### Timeline code block
        timeline_content = ""
        timeline_match = re.search(
            r"###\s+Timeline\s*\n```js\s*\n(.*?)```",
            block,
            re.DOTALL,
        )
        if timeline_match:
            timeline_content = timeline_match.group(1).strip()

        scenes.append(
            CartoonScene(
                index=len(scenes),
                title=scene_title,
                scene_id=scene_id,
                start=start,
                duration=scene_duration,
                scene_type=scene_type,
                narration=narration,
                html=html_content,
                timeline=timeline_content,
            )
        )

    return CartoonDocument(title=title, duration=duration, scenes=scenes)


# ---------------------------------------------------------------------------
# Markdown Validator (18 rules)
# ---------------------------------------------------------------------------


def validate_markdown(doc: CartoonDocument, raw_markdown: str) -> AuditResult:
    """Validate parsed CartoonDocument against 18 rules."""
    problems: list[str] = []

    # Rule 1: Title non-empty
    if not doc.title.strip():
        problems.append("标题不能为空")

    # Rule 2: Global duration >= 90
    if doc.duration < 90:
        problems.append(f"总时长 {doc.duration} 秒不足，至少需要 90 秒")

    # Rule 3: Scene count 5-8
    if len(doc.scenes) < 5:
        problems.append(f"场景数量 {len(doc.scenes)} 不足，至少需要 5 个")
    elif len(doc.scenes) > 8:
        problems.append(f"场景数量 {len(doc.scenes)} 过多，最多 8 个")

    # Rule 4: Unique scene ids
    scene_ids = [scene.scene_id for scene in doc.scenes]
    duplicates = [sid for sid in set(scene_ids) if scene_ids.count(sid) > 1]
    if duplicates:
        problems.append(f"场景 id 重复: {', '.join(duplicates)}")

    # Rule 5-6: Valid start and duration
    for scene in doc.scenes:
        if scene.start < 0:
            problems.append(f"Scene '{scene.scene_id}' 的 start {scene.start} < 0")
        if scene.duration <= 0:
            problems.append(f"Scene '{scene.scene_id}' 的 duration {scene.duration} <= 0")

    # Rule 7: No time overlaps
    sorted_scenes = sorted(doc.scenes, key=lambda s: s.start)
    for i in range(len(sorted_scenes) - 1):
        current_end = sorted_scenes[i].start + sorted_scenes[i].duration
        next_start = sorted_scenes[i + 1].start
        if current_end > next_start + 0.01:
            problems.append(
                f"场景时间重叠: '{sorted_scenes[i].scene_id}' "
                f"结束于 {current_end:.1f}s，"
                f"'{sorted_scenes[i + 1].scene_id}' 开始于 {next_start:.1f}s"
            )

    # Rule 8: Last scene end not too far beyond total duration
    if doc.scenes:
        last = max(doc.scenes, key=lambda s: s.start + s.duration)
        last_end = last.start + last.duration
        if last_end > doc.duration + 15:
            problems.append(
                f"最后场景结束于 {last_end:.1f}s，"
                f"超出总时长 {doc.duration:.1f}s 太多"
            )

    # Rule 9-11: Each scene must have narration, html, timeline
    for scene in doc.scenes:
        if not scene.narration.strip():
            problems.append(f"Scene '{scene.scene_id}' 缺少 Narration")
        if not scene.html.strip():
            problems.append(f"Scene '{scene.scene_id}' 缺少 HTML")
        if not scene.timeline.strip():
            problems.append(f"Scene '{scene.scene_id}' 缺少 Timeline")

    # Rule 12: HTML banned tags
    banned_html_tags = {"section", "html", "head", "body", "main", "script"}
    for scene in doc.scenes:
        for tag in banned_html_tags:
            if re.search(rf"<{tag}[\s>]", scene.html, re.IGNORECASE):
                problems.append(
                    f"Scene '{scene.scene_id}' HTML 包含禁止标签 <{tag}>"
                )

    # Rule 13-14: Timeline banned patterns
    for scene in doc.scenes:
        if re.search(r"\bconst\s+tl\b", scene.timeline):
            problems.append(f"Scene '{scene.scene_id}' Timeline 包含 'const tl'")
        if re.search(r"window\.__timelines", scene.timeline):
            problems.append(
                f"Scene '{scene.scene_id}' Timeline 包含 'window.__timelines'"
            )

    # Rule 15: Timeline must use Runtime.xxx
    for scene in doc.scenes:
        tl_lines = [
            line.strip()
            for line in scene.timeline.split("\n")
            if line.strip() and not line.strip().startswith("//")
        ]
        non_runtime = [
            line for line in tl_lines
            if not re.match(r"Runtime\.\w+\(", line)
        ]
        if non_runtime:
            problems.append(
                f"Scene '{scene.scene_id}' Timeline 包含非 Runtime 调用: "
                f"{non_runtime[0][:60]}"
            )

    # Rule 16: T() references existing scene ids
    id_set = set(scene_ids)
    for scene in doc.scenes:
        t_refs = re.findall(r'T\("([^"]+)"', scene.timeline)
        for ref in t_refs:
            if ref not in id_set:
                problems.append(
                    f"Scene '{scene.scene_id}' T(\"{ref}\") 引用了不存在的 scene id"
                )

    # Rule 17: T() local time within scene duration
    for scene in doc.scenes:
        t_refs = re.findall(r'T\("([^"]+)",\s*([\d.]+)\)', scene.timeline)
        for ref_id, local_time_str in t_refs:
            local_time = float(local_time_str)
            ref_scene = next(
                (s for s in doc.scenes if s.scene_id == ref_id), None
            )
            if ref_scene and local_time > ref_scene.duration:
                problems.append(
                    f"Scene '{scene.scene_id}' T(\"{ref_id}\", {local_time}) "
                    f"超过 scene duration {ref_scene.duration}"
                )

    # Rule 18: Total Runtime calls >= 25
    total_runtime_calls = 0
    for scene in doc.scenes:
        calls = re.findall(r"Runtime\.\w+\(", scene.timeline)
        total_runtime_calls += len(calls)

    if total_runtime_calls < 25:
        problems.append(
            f"全视频 Runtime 调用数量 {total_runtime_calls} 不足，至少需要 25 个"
        )

    return AuditResult(passed=len(problems) == 0, problems=problems)


# ---------------------------------------------------------------------------
# HTML Composer
# ---------------------------------------------------------------------------


def compose_html(doc: CartoonDocument) -> str:
    """Compose final index.html from CartoonDocument using white_video.html template."""
    template_path = _TEMPLATE_DIR / "white_video.html"
    template = template_path.read_text(encoding="utf-8")

    # Build scenes_html
    scenes_html_parts: list[str] = []
    for scene in doc.scenes:
        scene_html = (
            f'<section\n'
            f'  id="scene-{_escape_attr(scene.scene_id)}"\n'
            f'  class="scene clip type-{_escape_attr(scene.scene_type)}"\n'
            f'  data-start="{scene.start}"\n'
            f'  data-duration="{scene.duration}"\n'
            f'  data-track-index="0"\n'
            f'>\n'
            f'  <div class="scene-shell">\n'
            f'    <header class="scene-header">\n'
            f'      <div>\n'
            f'        <span class="scene-kicker">Scene {scene.index + 1:02d}</span>\n'
            f'        <h1>{_escape_attr(scene.title)}</h1>\n'
            f'      </div>\n'
            f'      <span class="scene-time">{scene.duration:.0f}s</span>\n'
            f'    </header>\n'
            f'    <div class="scene-content">\n'
            f'      {scene.html}\n'
            f'    </div>\n'
            f'    <div class="scene-caption" id="caption-{_escape_attr(scene.scene_id)}">\n'
            f'      {_escape_attr(scene.narration)}\n'
            f'    </div>\n'
            f'  </div>\n'
            f'</section>'
        )
        scenes_html_parts.append(scene_html)

    scenes_html = "\n    ".join(scenes_html_parts)

    # Build scene_clock_json
    scene_clock = {scene.scene_id: scene.start for scene in doc.scenes}
    scene_clock_json = json.dumps(scene_clock, ensure_ascii=False)

    # Build timeline_js
    timeline_parts: list[str] = []
    for scene in doc.scenes:
        if scene.timeline.strip():
            timeline_parts.append(f"// Scene: {scene.title}")
            timeline_parts.append(scene.timeline)
    timeline_js = "\n    ".join(timeline_parts)

    # Audio placeholder (v1: empty)
    audio_html = ""

    # Replace placeholders
    result = template
    result = result.replace("{{ title }}", _escape_attr(doc.title))
    result = result.replace("{{ duration }}", str(doc.duration))
    result = result.replace("{{ scenes_html }}", scenes_html)
    result = result.replace("{{ audio_html }}", audio_html)
    result = result.replace("{{ scene_clock_json }}", scene_clock_json)
    result = result.replace("{{ timeline_js }}", timeline_js)

    return result


# ---------------------------------------------------------------------------
# HTML Validator (20 rules)
# ---------------------------------------------------------------------------


def validate_html(html_content: str, doc: CartoonDocument) -> AuditResult:
    """Validate final HTML against 20 HyperFrames and content rules."""
    problems: list[str] = []

    # Rules 1-6: HyperFrames root structure
    if 'data-composition-id="cartoon-explainer"' not in html_content:
        problems.append('缺少 data-composition-id="cartoon-explainer"')

    main_tag_match = re.search(r"<main[^>]*>", html_content)
    if main_tag_match:
        main_tag = main_tag_match.group(0)
        if 'data-start="0"' not in main_tag:
            problems.append('main 缺少 data-start="0"')
        if "data-duration" not in main_tag:
            problems.append("main 缺少 data-duration")
        if 'data-width="1920"' not in main_tag:
            problems.append('main 缺少 data-width="1920"')
        if 'data-height="1080"' not in main_tag:
            problems.append('main 缺少 data-height="1080"')
        if 'data-fps="30"' not in main_tag:
            problems.append('main 缺少 data-fps="30"')
    else:
        problems.append("缺少 <main> 标签")

    # Rules 7-10: Section attributes
    sections = re.findall(r"<section[^>]*>", html_content)
    for section_tag in sections:
        classes = re.search(r'class="([^"]*)"', section_tag)
        if classes and "scene" not in classes.group(1):
            problems.append(f"section 缺少 scene class: {section_tag[:80]}")
        if classes and "clip" not in classes.group(1):
            problems.append(f"section 缺少 clip class: {section_tag[:80]}")
        if "data-start" not in section_tag:
            problems.append(f"section 缺少 data-start: {section_tag[:80]}")
        if "data-duration" not in section_tag:
            problems.append(f"section 缺少 data-duration: {section_tag[:80]}")
        if "data-track-index" not in section_tag:
            problems.append(f"section 缺少 data-track-index: {section_tag[:80]}")

    # Rule 11: gsap.timeline({ paused: true })
    if not re.search(r"gsap\.timeline\(\s*\{\s*paused\s*:\s*true\s*\}\s*\)", html_content):
        problems.append("缺少 gsap.timeline({ paused: true })")

    # Rule 12: window.__timelines["cartoon-explainer"]
    if 'window.__timelines["cartoon-explainer"]' not in html_content:
        problems.append('缺少 window.__timelines["cartoon-explainer"] = tl')

    # Rules 13-15: Banned patterns
    if re.search(r"\bMath\.random\s*\(", html_content):
        problems.append("禁止使用 Math.random")
    if re.search(r"\bDate\.now\s*\(", html_content):
        problems.append("禁止使用 Date.now")
    if re.search(r"\bsetTimeout\s*\(", html_content):
        problems.append("禁止使用 setTimeout")

    # Rule 16: No remote http/https resources
    remote_refs = re.findall(r'(?:src|href)="https?://[^"]*"', html_content)
    if remote_refs:
        problems.append(f"存在远程资源引用: {remote_refs[0][:60]}")

    # Rule 17: No markdown fence residue
    if "```" in html_content:
        problems.append("HTML 中存在 markdown 代码围栏残留")

    # Rule 18: Duplicate ids
    all_ids = re.findall(r'\bid="([^"]+)"', html_content)
    duplicate_ids = [i for i in set(all_ids) if all_ids.count(i) > 1]
    if duplicate_ids:
        problems.append(f"存在重复 id: {', '.join(duplicate_ids[:10])}")

    # Rule 19: Runtime methods exist in runtime.js
    runtime_path = _TEMPLATE_DIR / "runtime.js"
    if runtime_path.is_file():
        runtime_content = runtime_path.read_text(encoding="utf-8")
        # Extract method names from both shorthand and function forms
        available_methods = set(re.findall(r"(\w+)\s*:\s*function\s*\(", runtime_content))
        available_methods.update(re.findall(r"(\w+)\s*\(tl,", runtime_content))

        used_methods = set(re.findall(r"Runtime\.(\w+)\(", html_content))
        unknown = used_methods - available_methods
        if unknown:
            problems.append(f"使用了不存在的 Runtime 方法: {', '.join(sorted(unknown))}")

    # Rule 20: Section time overlaps
    section_times: list[tuple[float, float, str]] = []
    for section_tag in sections:
        start_match = re.search(r'data-start="([\d.]+)"', section_tag)
        duration_match = re.search(r'data-duration="([\d.]+)"', section_tag)
        id_match = re.search(r'id="([^"]+)"', section_tag)
        if start_match and duration_match:
            s = float(start_match.group(1))
            d = float(duration_match.group(1))
            sid = id_match.group(1) if id_match else "?"
            section_times.append((s, s + d, sid))

    section_times.sort()
    for i in range(len(section_times) - 1):
        if section_times[i][1] > section_times[i + 1][0] + 0.01:
            problems.append(
                f"section 时间重叠: {section_times[i][2]} / {section_times[i + 1][2]}"
            )

    return AuditResult(passed=len(problems) == 0, problems=problems)


# ---------------------------------------------------------------------------
# CartoonAgent class
# ---------------------------------------------------------------------------


class CartoonAgent:
    """LLM-driven Markdown DSL → HyperFrames HTML pipeline."""

    MAX_REPAIR_ROUNDS = 2
    LLM_TEMPERATURE = 0.5
    LLM_MAX_TOKENS = 16384

    async def generate(
        self,
        learning_need: str,
        output_dir: Path,
        profile: dict | str | None = None,
    ) -> CartoonGenerationResult:
        """Full generation pipeline: prompt → markdown → parse → validate → compose → render."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build prompt
        prompt = self.build_prompt(learning_need, profile)

        # Generate markdown with retry
        markdown_text = await self._generate_with_retry(prompt)

        # Parse and validate with repair loop
        doc, markdown_text, audit = await self._parse_validate_repair(
            learning_need, markdown_text
        )

        # Compose HTML
        html_content = compose_html(doc)

        # Validate HTML
        html_audit = validate_html(html_content, doc)
        if not html_audit.passed:
            combined_problems = html_audit.problems
            logger.warning(
                "HTML 校验失败，尝试修复 Markdown: %s",
                "; ".join(combined_problems[:5]),
            )
            repaired = await self.repair_markdown(
                learning_need, markdown_text, combined_problems
            )
            markdown_text = _clean_llm_output(repaired)
            doc = parse_markdown(markdown_text)
            md_audit = validate_markdown(doc, markdown_text)
            if not md_audit.passed:
                raise CartoonGenerationError(
                    f"修复后 Markdown 校验仍失败: {'; '.join(md_audit.problems[:6])}",
                    audit=md_audit,
                )
            html_content = compose_html(doc)
            html_audit = validate_html(html_content, doc)
            if not html_audit.passed:
                raise CartoonGenerationError(
                    f"修复后 HTML 校验仍失败: {'; '.join(html_audit.problems[:6])}",
                    audit=html_audit,
                )

        # Save outputs
        audit = AuditResult(passed=True, problems=[])
        self.save_outputs(output_dir, markdown_text, html_content, audit)

        # Copy template assets
        self._copy_template_assets(output_dir)

        return CartoonGenerationResult(
            markdown_path=output_dir / "cartoon.md",
            html_path=output_dir / "index.html",
            video_path=None,
            audit_path=output_dir / "audit.json",
            title=doc.title,
            duration=doc.duration,
            scene_count=len(doc.scenes),
        )

    def build_prompt(
        self, learning_need: str, profile: dict | str | None = None
    ) -> str:
        """Build the full LLM prompt from template files + user input."""
        prompt_md = (_TEMPLATE_DIR / "prompt.md").read_text(encoding="utf-8")
        rules_md = (_TEMPLATE_DIR / "rules.md").read_text(encoding="utf-8")
        reference_md = (_TEMPLATE_DIR / "reference.md").read_text(encoding="utf-8")

        profile_text = ""
        if profile:
            if isinstance(profile, dict):
                profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
            else:
                profile_text = str(profile)

        parts = [
            prompt_md,
            "\n\n---\n\n## 规则\n\n" + rules_md,
            "\n\n---\n\n## 格式参考\n\n" + reference_md,
            "\n\n---\n\n## 用户学习需求\n\n" + learning_need,
        ]

        if profile_text:
            parts.append("\n\n## 用户画像\n\n" + profile_text)

        return "\n".join(parts)

    async def generate_markdown(self, prompt: str) -> str:
        """Call LLM to generate cartoon.md content."""
        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你只输出 cartoon.md 格式的 Markdown，不输出任何其他内容。"),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(
            messages,
            temperature=self.LLM_TEMPERATURE,
            max_tokens=self.LLM_MAX_TOKENS,
        )

        text = response.content if hasattr(response, "content") else str(response)
        return _clean_llm_output(text)

    async def repair_markdown(
        self,
        learning_need: str,
        markdown_text: str,
        problems: list[str],
    ) -> str:
        """Call LLM to repair broken cartoon.md."""
        rules_md = (_TEMPLATE_DIR / "rules.md").read_text(encoding="utf-8")

        prompt = (
            f"以下 cartoon.md 存在问题，请修复后返回完整 cartoon.md。\n\n"
            f"## 用户学习需求\n\n{learning_need}\n\n"
            f"## 规则\n\n{rules_md}\n\n"
            f"## 原始 cartoon.md\n\n{markdown_text}\n\n"
            f"## 问题列表\n\n"
            + "\n".join(f"- {p}" for p in problems)
            + "\n\n只返回修复后的完整 cartoon.md，不要解释，不要输出 JSON，不要代码围栏包裹全文。"
        )

        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你只输出修复后的完整 cartoon.md，不输出任何其他内容。"),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(
            messages,
            temperature=self.LLM_TEMPERATURE,
            max_tokens=self.LLM_MAX_TOKENS,
        )

        text = response.content if hasattr(response, "content") else str(response)
        return _clean_llm_output(text)

    def save_outputs(
        self,
        output_dir: Path,
        markdown_text: str,
        html_content: str,
        audit: AuditResult,
    ) -> None:
        """Save cartoon.md, index.html, and audit.json to output directory."""
        (output_dir / "cartoon.md").write_text(markdown_text, encoding="utf-8")
        (output_dir / "index.html").write_text(html_content, encoding="utf-8")

        audit_data = {
            "passed": audit.passed,
            "problems": audit.problems,
        }
        (output_dir / "audit.json").write_text(
            json.dumps(audit_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def _generate_with_retry(self, prompt: str) -> str:
        """Generate markdown with up to 2 retries on failure."""
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self.generate_markdown(prompt)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Markdown 生成失败 (attempt %d/3): %s", attempt + 1, exc
                )
        raise CartoonGenerationError(f"Markdown 生成失败: {last_error}")

    async def _parse_validate_repair(
        self,
        learning_need: str,
        markdown_text: str,
    ) -> tuple[CartoonDocument, str, AuditResult]:
        """Parse → validate → repair loop (max 2 rounds)."""
        last_doc: CartoonDocument | None = None
        last_text = markdown_text
        last_audit = AuditResult(passed=False, problems=["未开始校验"])

        for round_num in range(self.MAX_REPAIR_ROUNDS + 1):
            try:
                doc = parse_markdown(last_text)
            except ValueError as exc:
                if round_num >= self.MAX_REPAIR_ROUNDS:
                    raise CartoonGenerationError(f"Markdown 解析失败且修复次数耗尽: {exc}")
                logger.warning("Markdown 解析失败 (round %d): %s", round_num + 1, exc)
                repaired = await self.repair_markdown(
                    learning_need, last_text, [str(exc)]
                )
                last_text = _clean_llm_output(repaired)
                continue

            last_doc = doc

            audit = validate_markdown(doc, last_text)
            last_audit = audit

            if audit.passed:
                return doc, last_text, audit

            if round_num >= self.MAX_REPAIR_ROUNDS:
                raise CartoonGenerationError(
                    f"Markdown 校验失败且修复次数耗尽: {'; '.join(audit.problems[:6])}",
                    audit=audit,
                )

            logger.warning(
                "Markdown 校验失败 (round %d): %s",
                round_num + 1,
                "; ".join(audit.problems[:5]),
            )
            repaired = await self.repair_markdown(
                learning_need, last_text, audit.problems
            )
            last_text = _clean_llm_output(repaired)

        # Should not reach here, but just in case
        if last_doc is None:
            raise CartoonGenerationError("Markdown 解析持续失败")
        return last_doc, last_text, last_audit

    @staticmethod
    def _copy_template_assets(output_dir: Path) -> None:
        """Copy style.css, runtime.js, and GSAP to output directory."""
        # Copy style.css
        css_src = _TEMPLATE_DIR / "style.css"
        if css_src.is_file():
            shutil.copy2(css_src, output_dir / "style.css")

        # Copy runtime.js
        js_src = _TEMPLATE_DIR / "runtime.js"
        if js_src.is_file():
            shutil.copy2(js_src, output_dir / "runtime.js")

        # Copy GSAP
        assets_dir = output_dir / "assets" / "vendor"
        assets_dir.mkdir(parents=True, exist_ok=True)

        candidates = [
            Path(__file__).resolve().parents[4]
            / "node_modules"
            / "gsap"
            / "dist"
            / "gsap.min.js",
            Path(__file__).resolve().parents[4]
            / "video-render"
            / "node_modules"
            / "gsap"
            / "dist"
            / "gsap.min.js",
        ]

        for candidate in candidates:
            if candidate.is_file():
                shutil.copy2(candidate, assets_dir / "gsap.min.js")
                return

        raise CartoonGenerationError(
            "缺少 GSAP 运行时文件，请在项目根目录执行 npm install gsap，"
            "或在 video-render 目录安装依赖。"
        )
