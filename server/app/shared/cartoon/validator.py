"""CLI validator — validates HyperFrames HTML structure using the official CLI linter."""

from __future__ import annotations

import asyncio
import re
from html.parser import HTMLParser
import json
from pathlib import Path

from app.shared.cartoon.schemas import StaticAudit


class _CompositionParser(HTMLParser):
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, str]] = []
        self.compositions: list[dict[str, str]] = []
        self.clips: list[tuple[str, dict[str, str]]] = []
        self.ids: list[str] = []
        self.audio_inside_clip = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("data-composition-id"):
            self.compositions.append(values)
        is_clip = (
            "clip" in values.get("class", "").split()
            or tag in {"audio", "video"}
            and "data-start" in values
        )
        if is_clip:
            self.clips.append((tag, values))
        if tag == "audio" and any(
            "clip" in ancestor.get("class", "").split()
            for ancestor in self.stack
        ):
            self.audio_inside_clip = True
        if tag not in self._VOID_TAGS:
            self.stack.append(values)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.stack:
            self.stack.pop()


def _number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def audit_hyperframes_html(content: str) -> list[str]:
    """Fast local audit for the contract violations that most often break render."""
    parser = _CompositionParser()
    try:
        parser.feed(content)
    except Exception as exc:
        return [f"HTML 解析失败: {exc}"]

    problems: list[str] = []
    if len(parser.compositions) != 1:
        problems.append("必须且只能存在一个 data-composition-id 根元素")
        composition_id = ""
    else:
        root = parser.compositions[0]
        composition_id = root.get("data-composition-id", "")
        for name in ("data-start", "data-duration", "data-width", "data-height"):
            if not root.get(name):
                problems.append(f"根元素缺少 {name}")
        if root.get("data-start") != "0":
            problems.append("根元素 data-start 必须为 0")

    duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if duplicates:
        problems.append(f"存在重复的 id: {', '.join(duplicates)}")

    tracks: dict[int, list[tuple[float, float, str]]] = {}
    for tag, attrs in parser.clips:
        clip_id = attrs.get("id", "")
        if not clip_id:
            problems.append(f"{tag} clip 缺少唯一 id")
        start = _number(attrs.get("data-start", ""))
        duration = _number(attrs.get("data-duration", ""))
        track = _number(attrs.get("data-track-index", ""))
        if start is None or start < 0:
            problems.append(f"clip {clip_id or tag} 的 data-start 无效")
        if duration is None or duration <= 0:
            problems.append(f"clip {clip_id or tag} 的 data-duration 无效")
        if track is None or not track.is_integer():
            problems.append(f"clip {clip_id or tag} 的 data-track-index 无效")
        if start is not None and duration and track is not None and track.is_integer():
            tracks.setdefault(int(track), []).append(
                (start, start + duration, clip_id or tag)
            )
        if tag == "video" and (
            "muted" not in attrs or "playsinline" not in attrs
        ):
            problems.append(f"video clip {clip_id or tag} 必须 muted playsinline")

    for track, clips in tracks.items():
        ordered = sorted(clips)
        for previous, current in zip(ordered, ordered[1:]):
            if current[0] < previous[1] - 0.001:
                problems.append(
                    f"轨道 {track} 的 clip 时间重叠: {previous[2]} / {current[2]}"
                )

    if parser.audio_inside_clip:
        problems.append("audio 必须是 composition 的直接 clip，不能嵌套在场景 clip 内")
    if not re.search(
        r"gsap\.timeline\(\s*\{\s*paused\s*:\s*true\s*\}\s*\)",
        content,
    ):
        problems.append("GSAP 主时间线必须使用 paused: true")
    if composition_id and not re.search(
        rf'window\.__timelines\s*\[\s*["\']{re.escape(composition_id)}["\']\s*\]\s*=',
        content,
    ):
        problems.append("时间线未注册到与 data-composition-id 同名的 key")

    banned_patterns: list[tuple[str, str]] = [
        (r"\bMath\.random\s*\(", "禁止使用 Math.random，动画必须可复现"),
        (r"\bDate\.now\s*\(", "禁止使用 Date.now，动画必须可复现"),
        (r"\brepeat\s*:\s*-1\b", "禁止 repeat: -1"),
        (r"\.(?:play|pause)\s*\(", "禁止调用媒体或时间线 .play()/.pause()"),
        (r"\bsetTimeout\s*\(", "禁止异步构造时间线"),
        (r"\bdata-end\s*=", "禁止 data-end，请使用 data-duration"),
        (r"\bdata-layer\s*=", "禁止 data-layer，请使用 data-track-index"),
        (
            r"\.(?:scene|clip)\s*\{[^}]*\bopacity\s*:\s*0(?:[;\s}]|$)",
            "禁止将 .scene/.clip 容器初始 opacity 设为 0",
        ),
        (
            r"\.(?:scene|clip)\s*\{[^}]*\bdisplay\s*:\s*none\b",
            "禁止对 .scene/.clip 使用 display: none",
        ),
    ]
    for pattern, message in banned_patterns:
        if re.search(pattern, content):
            problems.append(message)
    return problems


class CartoonCliValidator:
    """Validate HyperFrames HTML composition using the official CLI linter."""

    def __init__(self, timeout_seconds: int = 90) -> None:
        self.timeout_seconds = timeout_seconds

    async def validate(self, output_dir: Path) -> StaticAudit:
        """Run the hyperframes lint command on the generated index.html file."""
        html_file = output_dir / "index.html"
        if not html_file.is_file():
            return StaticAudit(
                passed=False,
                problems=[f"HTML composition file not found: {html_file}"],
                scene_count=0,
            )

        html_content = html_file.read_text(encoding="utf-8")
        scene_count = len(
            re.findall(r'class="[^"]*\bscene\b[^"]*"', html_content, re.IGNORECASE)
        )
        static_problems = audit_hyperframes_html(html_content)
        if static_problems:
            return StaticAudit(
                passed=False,
                problems=static_problems,
                scene_count=scene_count,
            )

        command = [
            "npx",
            "hyperframes",
            "lint",
            "index.html",
            "--json",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except OSError as exc:
            return StaticAudit(
                passed=False,
                problems=[f"无法启动 HyperFrames CLI: {exc}"],
                scene_count=scene_count,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return StaticAudit(
                passed=False,
                problems=[f"HyperFrames lint timed out after {self.timeout_seconds} seconds"],
                scene_count=0,
            )

        return_code = process.returncode or 0
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        problems: list[str] = []
        if return_code != 0:
            for raw_line in stdout_str.splitlines():
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                for item in payload.get("errors", []):
                    if isinstance(item, dict):
                        location = ":".join(
                            str(value)
                            for value in (item.get("line"), item.get("column"))
                            if value is not None
                        )
                        prefix = f"{location} " if location else ""
                        problems.append(f"{prefix}{item.get('message', item)}")
                    else:
                        problems.append(str(item))
            if not problems and stderr_str:
                problems.extend(stderr_str.splitlines())
            if not problems and stdout_str:
                problems.extend(stdout_str.splitlines())
            if not problems:
                problems.append(f"HyperFrames lint failed with exit code {return_code}")

        return StaticAudit(
            passed=(return_code == 0),
            problems=problems,
            scene_count=scene_count,
        )
