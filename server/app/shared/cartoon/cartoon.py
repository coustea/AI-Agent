"""Generic computer-theory animation video generation pipeline.

The LLM outputs a constrained Markdown DSL. The backend parses and validates
the DSL, wraps every scene into a shared HTML video template, copies runtime
assets, and lets HyperFrames render the result.

This module keeps the existing cartoon package naming for compatibility with
the current route/module structure, but its content goal is computer-theory
animation video generation rather than comic-style video generation.
"""

from __future__ import annotations

import html as html_mod
import json
import re
import shutil
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from app.infra.logging import get_logger
from app.infra.llm import get_llm

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates" / "white_teaching_video"
_COMPOSITION_ID = "theory-video"


@dataclass
class AuditResult:
    passed: bool
    problems: list[str] = field(default_factory=list)


class CartoonGenerationError(RuntimeError):
    def __init__(self, message: str, *, audit: AuditResult | None = None) -> None:
        super().__init__(message)
        self.audit = audit


@dataclass(frozen=True)
class CartoonScene:
    index: int
    title: str
    scene_id: str
    start: float
    duration: float
    scene_type: str
    layout: str
    focus: str
    narration: str
    html: str
    timeline: str


@dataclass(frozen=True)
class CartoonVideoDocument:
    title: str
    duration: float
    course: str
    topic: str
    scenes: list[CartoonScene]


@dataclass(frozen=True)
class CartoonGenerationResult:
    markdown_path: Path
    html_path: Path
    video_path: Path | None
    audit_path: Path
    title: str
    duration: float
    scene_count: int


@dataclass(frozen=True)
class ParsedSceneHTML:
    tags: list[str]
    ids: list[str]
    classes: set[str]
    visible_text: str
    event_attrs: list[str]
    remote_refs: list[str]
    javascript_refs: list[str]


@dataclass(frozen=True)
class ParsedTimeline:
    statements: list[str]
    runtime_methods: list[str]
    selector_ids: set[str]
    time_refs: list[tuple[str, float]]
    forbidden_hits: list[str]


class SceneHTMLParser(HTMLParser):
    """Parse LLM generated scene HTML as a fragment.

    The validator must separate HTML structure from visible text. Never scan
    raw HTML as source code, because normal attributes such as class="tree-node"
    are not user-visible content and must not be treated as code.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.ids: list[str] = []
        self.classes: set[str] = set()
        self.visible_text_parts: list[str] = []
        self.event_attrs: list[str] = []
        self.remote_refs: list[str] = []
        self.javascript_refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower().strip()
        if tag:
            self.tags.append(tag)

        for raw_name, raw_value in attrs:
            name = raw_name.lower().strip()
            value = raw_value or ""

            if name == "id" and value:
                self.ids.append(value)

            if name == "class" and value:
                self.classes.update(item.strip() for item in value.split() if item.strip())

            if name.startswith("on"):
                self.event_attrs.append(name)

            if name in {"src", "href", "xlink:href"}:
                if re.search(r"https?://", value, re.IGNORECASE):
                    self.remote_refs.append(value)
                if re.search(r"javascript\s*:", value, re.IGNORECASE):
                    self.javascript_refs.append(value)

            if re.search(r"javascript\s*:", value, re.IGNORECASE):
                self.javascript_refs.append(value)

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.visible_text_parts.append(text)

    def result(self) -> ParsedSceneHTML:
        visible_text = html_mod.unescape(" ".join(self.visible_text_parts))
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        return ParsedSceneHTML(
            tags=self.tags,
            ids=self.ids,
            classes=self.classes,
            visible_text=visible_text,
            event_attrs=self.event_attrs,
            remote_refs=self.remote_refs,
            javascript_refs=self.javascript_refs,
        )


_ALLOWED_SCENE_TYPES = {
    "problem",
    "model",
    "mechanism",
    "trace",
    "state",
    "contrast",
    "recap",
}

_ALLOWED_LAYOUTS = {
    "hero",
    "mechanism",
    "trace",
    "state-sync",
    "compare",
    "recap",
    "structure",
    "flow",
}

_BANNED_HTML_TAGS = {
    "section",
    "html",
    "head",
    "body",
    "main",
    "script",
    "iframe",
    "object",
    "embed",
    "link",
    "meta",
    "style",
    "canvas",
    "video",
    "audio",
    "img",
    "pre",
    "code",
}

_BANNED_CODE_CLASSES = {
    "code-board",
    "source-code",
    "code-editor",
    "code-line",
    "line-number",
    "active-line",
    "hljs",
    "language-python",
    "language-java",
    "language-cpp",
    "language-c",
    "language-javascript",
    "language-js",
}

_BANNED_CODE_TEXT_PATTERNS = {
    r"\bdef\s+[A-Za-z_]\w*\s*\(": "Python 函数定义",
    r"\bfunction\s+[A-Za-z_]\w*\s*\(": "JavaScript 函数定义",
    r"\breturn\s+[^，。；;\n]{1,80}": "return 语句",
    r"\bconsole\.log\s*\(": "console.log",
    r"\bSystem\.out\.println\s*\(": "System.out.println",
    r"#\s*include\s*<[^>]+>": "#include",
    r"\bpublic\s+class\s+[A-Za-z_]\w*": "Java 类定义",
    r"\bimport\s+[A-Za-z_][\w.]*": "import 语句",
    r"\b(for|while|if|else)\s*\([^)]*\)\s*\{": "代码控制结构",
    r"[{}]\s*(//|/\*)": "源码注释片段",
}

_OBJECT_CLASSES = {
    "concept-node",
    "state-badge",
    "data-token",
    "data-slot",
    "queue-slot",
    "stack-layer",
    "tree-node",
    "graph-node",
    "graph-edge",
    "hash-bucket",
    "process-card",
    "cpu-core",
    "memory-frame",
    "page-card",
    "disk-block",
    "interrupt-signal",
    "host-node",
    "packet",
    "router-node",
    "ack-badge",
    "window-bar",
    "table-grid",
    "btree-node",
    "index-page",
    "transaction-block",
    "lock-tag",
    "log-entry",
    "source-token",
    "lexer-box",
    "parser-stack",
    "syntax-node",
    "automata-state",
    "flow-arrow",
    "arrow-path",
    "timeline-track",
    "step-chip",
    "rule-bubble",
    "state-panel",
    "hint-bubble",
}

_DYNAMIC_METHODS = {
    "spawn",
    "move",
    "moveTo",
    "transfer",
    "connect",
    "drawPath",
    "switchState",
    "setText",
    "updateList",
    "updateTable",
    "markStep",
    "advanceTrack",
    "sendPacket",
    "returnAck",
    "replaceFrame",
    "insertNode",
    "rotateTree",
    "cameraZoom",
    "cameraPan",
    "cameraFocus",
}

_STATE_METHODS = {
    "switchState",
    "setText",
    "updateList",
    "updateTable",
    "markStep",
    "advanceTrack",
    "replaceFrame",
}

_CAMERA_METHODS = {
    "cameraZoom",
    "cameraPan",
    "cameraFocus",
    "cameraReset",
    "sceneIn",
    "sceneOut",
}

_TRACE_MOTION_METHODS = {
    "move",
    "moveTo",
    "transfer",
    "drawPath",
    "connect",
    "sendPacket",
    "returnAck",
    "insertNode",
    "replaceFrame",
}

_TIMELINE_FORBIDDEN_PATTERNS = {
    r"\bconst\s+tl\b": "const tl",
    r"window\.__timelines": "window.__timelines",
    r"\bgsap\.": "gsap",
    r"\bdocument\.": "document",
    r"\bMath\.random\s*\(": "Math.random",
    r"\bDate\.now\s*\(": "Date.now",
    r"\bsetTimeout\s*\(": "setTimeout",
    r"https?://": "远程链接",
    r"</script": "</script>",
    r"```": "Markdown 代码围栏",
}


def _safe_scene_id(raw: str) -> str:
    value = re.sub(r"[^a-z0-9_-]", "-", raw.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-_")
    if not value:
        return "scene"
    if value[0].isdigit():
        value = f"s-{value}"
    return value[:48]


def _escape_text(value: str) -> str:
    return html_mod.escape(str(value), quote=False)


def _escape_attr(value: str) -> str:
    return html_mod.escape(str(value), quote=True)


def _clean_llm_output(text: str) -> str:
    text = str(text or "").strip()
    fenced_match = re.match(
        r"^```(?:markdown|md)?\s*\n(?P<body>[\s\S]*?)\n```\s*$",
        text,
        re.IGNORECASE,
    )
    if fenced_match:
        return fenced_match.group("body").strip()
    return text


def _read_directive(block: str, name: str, default: str | None = None) -> str | None:
    match = re.search(rf"^@{re.escape(name)}:\s*(.+?)\s*$", block, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return default


def _read_section(block: str, title: str, next_titles: tuple[str, ...]) -> str:
    next_pattern = "|".join(re.escape(item) for item in next_titles)
    pattern = rf"###\s+{re.escape(title)}\s*\n(?P<body>[\s\S]*?)(?=\n###\s+(?:{next_pattern})\s*\n|\Z)"
    match = re.search(pattern, block, re.IGNORECASE)
    return match.group("body").strip() if match else ""


def _read_fenced_section(block: str, title: str, lang: str) -> str:
    match = re.search(
        rf"###\s+{re.escape(title)}\s*\n```{re.escape(lang)}\s*\n(?P<body>[\s\S]*?)\n```",
        block,
        re.IGNORECASE,
    )
    return match.group("body").strip() if match else ""


def _strip_js_comments(code: str) -> str:
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)
    return code


def _split_js_statements(code: str) -> list[str]:
    cleaned = _strip_js_comments(code)
    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    escape = False
    depth = 0

    for char in cleaned:
        buffer.append(char)

        if escape:
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if quote:
            if char == quote:
                quote = None
            continue

        if char in {"'", '"', "`"}:
            quote = char
            continue

        if char in "([{":
            depth += 1
            continue

        if char in ")]}":
            depth = max(0, depth - 1)
            continue

        if char == ";" and depth == 0:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement[:-1].strip())
            buffer = []

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)

    return [item for item in statements if item]


def _runtime_calls(code: str) -> list[str]:
    return re.findall(r"\bRuntime\.(\w+)\s*\(", code)


def _extract_selector_ids_from_timeline(timeline: str) -> set[str]:
    ids: set[str] = set()
    for selector in re.findall(r'["\']([^"\']*#[^"\']+)["\']', timeline):
        for item in re.findall(r"#([A-Za-z0-9_-]+)", selector):
            ids.add(item)
    return ids


def _extract_t_refs(timeline: str) -> list[tuple[str, float]]:
    refs: list[tuple[str, float]] = []
    for scene_id, local_time_text in re.findall(
        r'T\(\s*["\']([^"\']+)["\']\s*,\s*([\d.]+)\s*\)',
        timeline,
    ):
        try:
            refs.append((scene_id, float(local_time_text)))
        except ValueError:
            refs.append((scene_id, -1.0))
    return refs


def _parse_scene_html(scene_html: str) -> ParsedSceneHTML:
    parser = SceneHTMLParser()
    try:
        parser.feed(scene_html)
        parser.close()
    except Exception:
        logger.warning("Scene HTML parser failed; using partial parse result", exc_info=True)
    return parser.result()


def _parse_timeline(timeline: str) -> ParsedTimeline:
    statements = _split_js_statements(timeline)
    runtime_methods = _runtime_calls(timeline)
    selector_ids = _extract_selector_ids_from_timeline(timeline)
    time_refs = _extract_t_refs(timeline)

    forbidden_hits: list[str] = []
    for pattern, label in _TIMELINE_FORBIDDEN_PATTERNS.items():
        if re.search(pattern, timeline, re.IGNORECASE):
            forbidden_hits.append(label)

    return ParsedTimeline(
        statements=statements,
        runtime_methods=runtime_methods,
        selector_ids=selector_ids,
        time_refs=time_refs,
        forbidden_hits=forbidden_hits,
    )


def _detect_code_tendency(parsed_html: ParsedSceneHTML, narration: str) -> list[str]:
    """Detect actual source-code presentation without scanning raw HTML.

    The detector checks only explicit code component class names and visible
    text. It intentionally ignores raw HTML attributes such as class="tree-node",
    so normal HTML will not be confused with source code.
    """

    problems: list[str] = []

    code_classes = sorted(parsed_html.classes & _BANNED_CODE_CLASSES)
    for class_name in code_classes:
        problems.append(f"代码展示类名: {class_name}")

    text_for_check = f"{parsed_html.visible_text}\n{narration}"
    for pattern, label in _BANNED_CODE_TEXT_PATTERNS.items():
        if re.search(pattern, text_for_check, re.IGNORECASE):
            problems.append(label)

    return problems


def _validate_narration(scene: CartoonScene) -> list[str]:
    problems: list[str] = []
    narration = scene.narration.strip()

    if not narration:
        problems.append(f"Scene '{scene.scene_id}' 缺少 Narration")
        return problems

    if len(narration) < 18:
        problems.append(f"Scene '{scene.scene_id}' Narration 太短，必须解释机制")
        return problems

    if scene.scene_type in {"mechanism", "trace", "state"} and len(narration) < 28:
        problems.append(f"Scene '{scene.scene_id}' Narration 过短，核心过程场景必须解释机制原因")

    return problems


def _validate_scene_html(scene: CartoonScene, parsed_html: ParsedSceneHTML) -> list[str]:
    problems: list[str] = []

    if not scene.html.strip():
        problems.append(f"Scene '{scene.scene_id}' 缺少 HTML")
        return problems

    for tag in parsed_html.tags:
        if tag in _BANNED_HTML_TAGS:
            problems.append(f"Scene '{scene.scene_id}' HTML 包含禁止标签 <{tag}>")

    for attr in parsed_html.event_attrs:
        problems.append(f"Scene '{scene.scene_id}' HTML 包含事件属性 {attr}")

    if parsed_html.remote_refs:
        problems.append(f"Scene '{scene.scene_id}' HTML 包含远程资源链接")

    if parsed_html.javascript_refs:
        problems.append(f"Scene '{scene.scene_id}' HTML 包含 javascript:")

    if "```" in scene.html:
        problems.append(f"Scene '{scene.scene_id}' HTML 包含 Markdown 代码围栏残留")

    for label in _detect_code_tendency(parsed_html, scene.narration):
        problems.append(f"Scene '{scene.scene_id}' 包含代码讲解倾向: {label}")

    for item_id in parsed_html.ids:
        expected_prefix = f"{scene.scene_id}-"
        if not item_id.startswith(expected_prefix):
            problems.append(f"Scene '{scene.scene_id}' 内部 id '{item_id}' 未使用 scene 前缀")

    if not (parsed_html.classes & _OBJECT_CLASSES):
        problems.append(f"Scene '{scene.scene_id}' 缺少理论动画对象类")

    return problems


def _validate_scene_timeline(
    scene: CartoonScene,
    parsed_html: ParsedSceneHTML,
    parsed_timeline: ParsedTimeline,
    scene_ids: set[str],
    scenes_by_id: dict[str, CartoonScene],
) -> list[str]:
    problems: list[str] = []

    if not scene.timeline.strip():
        problems.append(f"Scene '{scene.scene_id}' 缺少 Timeline")
        return problems

    for label in parsed_timeline.forbidden_hits:
        problems.append(f"Scene '{scene.scene_id}' Timeline 包含禁止内容: {label}")

    for statement in parsed_timeline.statements:
        if not re.match(r"^Runtime\.\w+\s*\(", statement, re.DOTALL):
            problems.append(f"Scene '{scene.scene_id}' Timeline 包含非 Runtime 调用: {statement[:80]}")
        if "\n" in statement:
            problems.append(f"Scene '{scene.scene_id}' Runtime 调用必须单行书写")

    calls = parsed_timeline.runtime_methods

    if len(calls) < 4:
        problems.append(f"Scene '{scene.scene_id}' Runtime 调用数量不足，每个 scene 至少 4 个")

    call_set = set(calls)

    if scene.scene_type in {"mechanism", "trace", "state"} and not (call_set & _DYNAMIC_METHODS):
        problems.append(f"Scene '{scene.scene_id}' 必须包含动态机制动作")

    if scene.scene_type == "state" and not (call_set & _STATE_METHODS):
        problems.append(f"Scene '{scene.scene_id}' 是 state 场景，必须包含状态同步动作")

    if scene.scene_type == "trace" and not (call_set & _TRACE_MOTION_METHODS):
        problems.append(f"Scene '{scene.scene_id}' 是 trace 场景，必须有对象移动、路径绘制或连线变化")

    valid_ids = set(parsed_html.ids) | {
        f"scene-{scene.scene_id}",
        f"caption-{scene.scene_id}",
        f"camera-{scene.scene_id}",
    }

    for used_id in sorted(parsed_timeline.selector_ids):
        if used_id not in valid_ids:
            problems.append(f"Scene '{scene.scene_id}' Timeline selector 引用了不存在的 id: #{used_id}")

    for ref_id, local_time in parsed_timeline.time_refs:
        if ref_id not in scene_ids:
            problems.append(f"Scene '{scene.scene_id}' T(\"{ref_id}\") 引用了不存在的 scene id")
            continue

        ref_scene = scenes_by_id.get(ref_id)
        if ref_scene and local_time > ref_scene.duration + 0.01:
            problems.append(f"Scene '{scene.scene_id}' T(\"{ref_id}\", {local_time}) 超过 scene duration")

        if local_time < 0:
            problems.append(f"Scene '{scene.scene_id}' T(\"{ref_id}\") 使用了非法时间")

    return problems


def parse_markdown(markdown_text: str) -> CartoonVideoDocument:
    text = markdown_text.strip()
    if not text:
        raise ValueError("Markdown 内容为空")

    title_match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if not title_match:
        raise ValueError("缺少视频标题 (# 标题)")
    title = title_match.group(1).strip()

    duration_raw = _read_directive(text, "duration")
    if not duration_raw:
        raise ValueError("缺少全局 @duration")

    try:
        duration = float(duration_raw)
    except ValueError as exc:
        raise ValueError(f"全局 @duration 不是有效数字: {duration_raw}") from exc

    course = _read_directive(text, "course", "计算机理论") or "计算机理论"
    topic = _read_directive(text, "topic", title) or title

    scene_blocks = re.split(r"(?=^##\s+Scene\s+\d+\s*:)", text, flags=re.MULTILINE)
    scenes: list[CartoonScene] = []

    for block in scene_blocks:
        block = block.strip()
        if not block.startswith("## Scene"):
            continue

        header_match = re.match(r"##\s+Scene\s+\d+\s*:\s*(.+?)\s*$", block, re.MULTILINE)
        if not header_match:
            raise ValueError("存在 Scene 标题格式错误，应为 ## Scene N: 场景标题")
        scene_title = header_match.group(1).strip()

        raw_scene_id = _read_directive(block, "id")
        raw_start = _read_directive(block, "start")
        raw_duration = _read_directive(block, "duration")
        scene_type = _read_directive(block, "type")
        layout = _read_directive(block, "layout", scene_type or "mechanism")
        focus = _read_directive(block, "focus", "核心对象") or "核心对象"

        if not raw_scene_id:
            raise ValueError(f"Scene '{scene_title}' 缺少 @id")
        if not raw_start:
            raise ValueError(f"Scene '{scene_title}' 缺少 @start")
        if not raw_duration:
            raise ValueError(f"Scene '{scene_title}' 缺少 @duration")
        if not scene_type:
            raise ValueError(f"Scene '{scene_title}' 缺少 @type")

        try:
            start = float(raw_start)
            scene_duration = float(raw_duration)
        except ValueError as exc:
            raise ValueError(f"Scene '{scene_title}' 的 @start 或 @duration 不是有效数字") from exc

        scenes.append(
            CartoonScene(
                index=len(scenes),
                title=scene_title,
                scene_id=_safe_scene_id(raw_scene_id),
                start=start,
                duration=scene_duration,
                scene_type=scene_type.strip(),
                layout=(layout or "mechanism").strip(),
                focus=focus.strip(),
                narration=_read_section(block, "Narration", ("HTML", "Timeline")),
                html=_read_fenced_section(block, "HTML", "html"),
                timeline=_read_fenced_section(block, "Timeline", "js"),
            )
        )

    if not scenes:
        raise ValueError("没有解析到任何 Scene")

    return CartoonVideoDocument(
        title=title,
        duration=duration,
        course=course,
        topic=topic,
        scenes=scenes,
    )


def validate_markdown(doc: CartoonVideoDocument, raw_markdown: str) -> AuditResult:
    problems: list[str] = []

    if not doc.title.strip():
        problems.append("标题不能为空")

    if doc.duration < 60:
        problems.append(f"总时长 {doc.duration} 秒不足，至少需要 60 秒")

    if doc.duration > 600:
        problems.append(f"总时长 {doc.duration} 秒过长，最多 600 秒")

    if len(doc.scenes) < 5:
        problems.append(f"场景数量 {len(doc.scenes)} 不足，至少需要 5 个")
    elif len(doc.scenes) > 8:
        problems.append(f"场景数量 {len(doc.scenes)} 过多，最多 8 个")

    scene_types = [scene.scene_type for scene in doc.scenes]
    if "mechanism" not in scene_types:
        problems.append("缺少 mechanism 场景，理论视频必须解释核心机制")
    if "trace" not in scene_types:
        problems.append("缺少 trace 场景，理论视频必须展示过程追踪动画")
    if "recap" not in scene_types:
        problems.append("缺少 recap 场景，理论视频必须有结构化总结")

    scene_ids = [scene.scene_id for scene in doc.scenes]
    scene_id_set = set(scene_ids)
    scenes_by_id = {scene.scene_id: scene for scene in doc.scenes}
    duplicates = [sid for sid in scene_id_set if scene_ids.count(sid) > 1]
    if duplicates:
        problems.append(f"场景 id 重复: {', '.join(duplicates)}")

    parsed_html_by_scene: dict[str, ParsedSceneHTML] = {}
    parsed_timeline_by_scene: dict[str, ParsedTimeline] = {}

    for scene in doc.scenes:
        parsed_html_by_scene[scene.scene_id] = _parse_scene_html(scene.html)
        parsed_timeline_by_scene[scene.scene_id] = _parse_timeline(scene.timeline)

        if scene.scene_type not in _ALLOWED_SCENE_TYPES:
            problems.append(f"Scene '{scene.scene_id}' type 无效: {scene.scene_type}")

        if scene.layout not in _ALLOWED_LAYOUTS:
            problems.append(f"Scene '{scene.scene_id}' layout 无效: {scene.layout}")

        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,47}", scene.scene_id):
            problems.append(f"Scene id '{scene.scene_id}' 不合法")

        if scene.start < 0:
            problems.append(f"Scene '{scene.scene_id}' 的 start {scene.start} < 0")

        if scene.duration < 8:
            problems.append(f"Scene '{scene.scene_id}' duration 太短，至少 8 秒")

        problems.extend(_validate_narration(scene))

    sorted_scenes = sorted(doc.scenes, key=lambda item: item.start)
    if sorted_scenes and abs(sorted_scenes[0].start) > 0.01:
        problems.append("第一个 Scene 必须从 0 秒开始")

    for index in range(len(sorted_scenes) - 1):
        current = sorted_scenes[index]
        next_scene = sorted_scenes[index + 1]
        current_end = current.start + current.duration
        next_start = next_scene.start

        if current_end > next_start + 0.01:
            problems.append(f"场景时间重叠: {current.scene_id} / {next_scene.scene_id}")

        if next_start - current_end > 4:
            problems.append(f"场景间空白过长: {current.scene_id} / {next_scene.scene_id}")

    if doc.scenes:
        last = max(doc.scenes, key=lambda item: item.start + item.duration)
        last_end = last.start + last.duration
        if last_end > doc.duration + 8:
            problems.append(f"最后场景结束于 {last_end:.1f}s，超出总时长 {doc.duration:.1f}s 太多")
        if doc.duration - last_end > 10:
            problems.append(f"视频总时长 {doc.duration:.1f}s 与最后场景结束 {last_end:.1f}s 差距过大")

    all_inner_ids: list[str] = []
    total_runtime_calls = 0
    all_methods: list[str] = []
    layouts: list[str] = []

    for scene in doc.scenes:
        parsed_html = parsed_html_by_scene[scene.scene_id]
        parsed_timeline = parsed_timeline_by_scene[scene.scene_id]

        layouts.append(scene.layout)
        all_inner_ids.extend(parsed_html.ids)
        total_runtime_calls += len(parsed_timeline.runtime_methods)
        all_methods.extend(parsed_timeline.runtime_methods)

        problems.extend(_validate_scene_html(scene, parsed_html))
        problems.extend(
            _validate_scene_timeline(
                scene=scene,
                parsed_html=parsed_html,
                parsed_timeline=parsed_timeline,
                scene_ids=scene_id_set,
                scenes_by_id=scenes_by_id,
            )
        )

    duplicate_inner_ids = [item for item in set(all_inner_ids) if all_inner_ids.count(item) > 1]
    if duplicate_inner_ids:
        problems.append(f"scene HTML 内部存在重复 id: {', '.join(duplicate_inner_ids[:10])}")

    if total_runtime_calls < 35:
        problems.append(f"全视频 Runtime 调用数量 {total_runtime_calls} 不足，至少需要 35 个")

    method_set = set(all_methods)
    action_families = [
        {"reveal", "fadeIn", "popIn", "slideIn", "sceneIn"},
        {"move", "moveTo", "transfer", "sendPacket", "returnAck", "insertNode", "replaceFrame"},
        {"highlight", "pulse", "focus", "spotlight", "compare"},
        {"switchState", "setText", "updateList", "updateTable", "markStep", "advanceTrack"},
        {"connect", "drawPath"},
        _CAMERA_METHODS,
        {"caption"},
    ]

    family_hits = sum(1 for family in action_families if method_set & family)
    if family_hits < 5:
        problems.append("动画动作类型不足，至少需要出现 5 类动作")

    if len(set(layouts)) < 3 and len(doc.scenes) >= 5:
        problems.append("布局过于单一，至少需要 3 种镜头布局")

    if not (method_set & _CAMERA_METHODS):
        problems.append("缺少镜头语言，至少使用 cameraZoom/cameraPan/cameraFocus/sceneIn/sceneOut 之一")

    return AuditResult(passed=len(problems) == 0, problems=problems)


def compose_html(doc: CartoonVideoDocument) -> str:
    template_path = _TEMPLATE_DIR / "white_video.html"
    template = template_path.read_text(encoding="utf-8")

    scenes_html_parts: list[str] = []
    total_scenes = len(doc.scenes)

    for scene in doc.scenes:
        scene_html = (
            f'<section\n'
            f'  id="scene-{_escape_attr(scene.scene_id)}"\n'
            f'  class="scene clip scene-{_escape_attr(scene.scene_id)} type-{_escape_attr(scene.scene_type)} layout-{_escape_attr(scene.layout)}"\n'
            f'  data-start="{scene.start}"\n'
            f'  data-duration="{scene.duration}"\n'
            f'  data-track-index="0"\n'
            f'>\n'
            f'  <div class="scene-shell">\n'
            f'    <div class="scene-meta">\n'
            f'      <span class="scene-kind">{_escape_text(scene.scene_type.upper())}</span>\n'
            f'      <span class="scene-count">Scene {scene.index + 1:02d} / {total_scenes:02d}</span>\n'
            f'    </div>\n'
            f'    <header class="scene-header">\n'
            f'      <div class="scene-title-wrap">\n'
            f'        <span class="scene-course">{_escape_text(doc.course)}</span>\n'
            f'        <h1>{_escape_text(scene.title)}</h1>\n'
            f'      </div>\n'
            f'      <div class="scene-focus">{_escape_text(scene.focus)}</div>\n'
            f'    </header>\n'
            f'    <div class="scene-camera" id="camera-{_escape_attr(scene.scene_id)}">\n'
            f'      <div class="scene-content">\n'
            f'        {scene.html}\n'
            f'      </div>\n'
            f'    </div>\n'
            f'    <div class="scene-caption" id="caption-{_escape_attr(scene.scene_id)}">\n'
            f'      {_escape_text(scene.narration)}\n'
            f'    </div>\n'
            f'  </div>\n'
            f'</section>'
        )
        scenes_html_parts.append(scene_html)

    scene_clock = {scene.scene_id: scene.start for scene in doc.scenes}
    timeline_js = "\n    ".join(
        f"// Scene {scene.index + 1}: {scene.title}\n{scene.timeline.strip()}"
        for scene in doc.scenes
    )

    result = template
    result = result.replace("{{ title }}", _escape_text(doc.title))
    result = result.replace("{{ course }}", _escape_text(doc.course))
    result = result.replace("{{ topic }}", _escape_text(doc.topic))
    result = result.replace("{{ duration }}", str(doc.duration))
    result = result.replace("{{ composition_id }}", _COMPOSITION_ID)
    result = result.replace("{{ scenes_html }}", "\n    ".join(scenes_html_parts))
    result = result.replace("{{ audio_html }}", "")
    result = result.replace("{{ scene_clock_json }}", json.dumps(scene_clock, ensure_ascii=False))
    result = result.replace("{{ timeline_js }}", timeline_js)
    return result


def validate_html(html_content: str, doc: CartoonVideoDocument) -> AuditResult:
    problems: list[str] = []

    if f'data-composition-id="{_COMPOSITION_ID}"' not in html_content:
        problems.append(f'缺少 data-composition-id="{_COMPOSITION_ID}"')

    main_tag_match = re.search(r"<main[^>]*>", html_content)
    if not main_tag_match:
        problems.append("缺少 <main> 标签")
    else:
        main_tag = main_tag_match.group(0)
        for marker, message in {
            'data-start="0"': 'main 缺少 data-start="0"',
            "data-duration": "main 缺少 data-duration",
            'data-width="1920"': 'main 缺少 data-width="1920"',
            'data-height="1080"': 'main 缺少 data-height="1080"',
            'data-fps="30"': 'main 缺少 data-fps="30"',
        }.items():
            if marker not in main_tag:
                problems.append(message)

    sections = re.findall(r"<section[^>]*>", html_content)
    if len(sections) != len(doc.scenes):
        problems.append(f"section 数量 {len(sections)} 与 Markdown scene 数量 {len(doc.scenes)} 不一致")

    for section_tag in sections:
        classes = re.search(r'class="([^"]*)"', section_tag)
        class_text = classes.group(1) if classes else ""

        if "scene" not in class_text.split():
            problems.append(f"section 缺少 scene class: {section_tag[:120]}")
        if "clip" not in class_text.split():
            problems.append(f"section 缺少 clip class: {section_tag[:120]}")
        if "data-start" not in section_tag:
            problems.append(f"section 缺少 data-start: {section_tag[:120]}")
        if "data-duration" not in section_tag:
            problems.append(f"section 缺少 data-duration: {section_tag[:120]}")
        if "data-track-index" not in section_tag:
            problems.append(f"section 缺少 data-track-index: {section_tag[:120]}")

    if not re.search(r"gsap\.timeline\(\s*\{\s*paused\s*:\s*true\s*\}\s*\)", html_content):
        problems.append("缺少 gsap.timeline({ paused: true })")

    if f'window.__timelines["{_COMPOSITION_ID}"]' not in html_content:
        problems.append(f'缺少 window.__timelines["{_COMPOSITION_ID}"] = tl')

    for pattern, label in {
        r"\bMath\.random\s*\(": "Math.random",
        r"\bDate\.now\s*\(": "Date.now",
        r"\bsetTimeout\s*\(": "setTimeout",
        r'(?:src|href)\s*=\s*"https?://[^"]*"': "远程资源引用",
        r"\son\w+\s*=": "事件属性 onxxx",
        r"javascript\s*:": "javascript:",
        r"```": "Markdown 代码围栏残留",
    }.items():
        if re.search(pattern, html_content, re.IGNORECASE):
            problems.append(f"HTML 中存在禁止内容: {label}")

    all_ids = re.findall(r'\bid="([^"]+)"', html_content)
    duplicate_ids = [item for item in set(all_ids) if all_ids.count(item) > 1]
    if duplicate_ids:
        problems.append(f"存在重复 id: {', '.join(duplicate_ids[:10])}")

    runtime_path = _TEMPLATE_DIR / "runtime.js"
    if runtime_path.is_file():
        runtime_content = runtime_path.read_text(encoding="utf-8")
        available_methods = set(re.findall(r"^\s*(\w+)\s*\(\s*tl\s*,", runtime_content, re.MULTILINE))
        used_methods = set(re.findall(r"Runtime\.(\w+)\s*\(", html_content))
        unknown = used_methods - available_methods
        if unknown:
            problems.append(f"使用了不存在的 Runtime 方法: {', '.join(sorted(unknown))}")
    else:
        problems.append("模板 runtime.js 不存在，无法校验 Runtime 方法")

    section_times: list[tuple[float, float, str]] = []
    for section_tag in sections:
        start_match = re.search(r'data-start="([\d.]+)"', section_tag)
        duration_match = re.search(r'data-duration="([\d.]+)"', section_tag)
        id_match = re.search(r'id="([^"]+)"', section_tag)

        if start_match and duration_match:
            start = float(start_match.group(1))
            duration = float(duration_match.group(1))
            section_id = id_match.group(1) if id_match else "?"
            section_times.append((start, start + duration, section_id))

    section_times.sort()
    for index in range(len(section_times) - 1):
        if section_times[index][1] > section_times[index + 1][0] + 0.01:
            problems.append(f"section 时间重叠: {section_times[index][2]} / {section_times[index + 1][2]}")

    return AuditResult(passed=len(problems) == 0, problems=problems)


class CartoonVideoAgent:
    MAX_REPAIR_ROUNDS = 2
    LLM_TEMPERATURE = 0.45
    LLM_MAX_TOKENS = 18000

    async def generate(
        self,
        learning_need: str,
        output_dir: Path,
        profile: dict[str, Any],
        target_duration: int | None = None,
    ) -> CartoonGenerationResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        prompt = self.build_prompt(
            learning_need=learning_need,
            profile=profile,
            target_duration=target_duration,
        )
        markdown_text = await self._generate_with_retry(prompt)

        doc, markdown_text, md_audit = await self._parse_validate_repair(
            learning_need=learning_need,
            markdown_text=markdown_text,
            target_duration=target_duration,
        )

        html_content = compose_html(doc)
        html_audit = validate_html(html_content, doc)
        if not html_audit.passed:
            doc, markdown_text, html_content, html_audit = await self._repair_html_via_markdown(
                learning_need=learning_need,
                markdown_text=markdown_text,
                problems=html_audit.problems,
                target_duration=target_duration,
            )

        self.save_outputs(
            output_dir=output_dir,
            markdown_text=markdown_text,
            html_content=html_content,
            audit=AuditResult(passed=True, problems=[]),
            audit_payload={
                "passed": True,
                "title": doc.title,
                "course": doc.course,
                "topic": doc.topic,
                "duration": doc.duration,
                "scene_count": len(doc.scenes),
                "composition_id": _COMPOSITION_ID,
                "stages": {
                    "markdown_validation": {
                        "passed": md_audit.passed,
                        "problems": md_audit.problems,
                    },
                    "html_validation": {
                        "passed": html_audit.passed,
                        "problems": html_audit.problems,
                    },
                },
            },
        )
        self._copy_template_assets(output_dir)

        return CartoonGenerationResult(
            markdown_path=output_dir / "theory_video.md",
            html_path=output_dir / "index.html",
            video_path=None,
            audit_path=output_dir / "audit.json",
            title=doc.title,
            duration=doc.duration,
            scene_count=len(doc.scenes),
        )

    def build_prompt(
        self,
        learning_need: str,
        profile: dict[str, Any],
        target_duration: int | None = None,
    ) -> str:
        prompt_md = (_TEMPLATE_DIR / "prompt.md").read_text(encoding="utf-8")
        rules_md = (_TEMPLATE_DIR / "rules.md").read_text(encoding="utf-8")
        reference_md = (_TEMPLATE_DIR / "reference.md").read_text(encoding="utf-8")
        profile_text = json.dumps(profile or {}, ensure_ascii=False, indent=2)

        duration_text = (
            f"请生成约 {target_duration} 秒的视频，全局 @duration 应接近该值。"
            if target_duration
            else "请生成 90 到 150 秒（1分半到2分半）的视频，根据内容复杂度灵活调整，全局 @duration 应接近该范围。"
        )

        return "\n\n".join(
            [
                prompt_md,
                "---\n\n## DSL 规则\n\n" + rules_md,
                "---\n\n## 输出参考\n\n" + reference_md,
                "---\n\n## 用户学习需求\n\n" + learning_need.strip(),
                "---\n\n## 用户画像与学习偏好\n\n" + profile_text,
                "---\n\n## 目标视频时长\n\n" + duration_text,
            ]
        )

    async def generate_markdown(self, prompt: str) -> str:
        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你只输出 theory_video.md 格式的 Markdown，不输出解释、JSON 或代码围栏包裹全文。"),
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
        target_duration: int | None = None,
    ) -> str:
        rules_md = (_TEMPLATE_DIR / "rules.md").read_text(encoding="utf-8")
        reference_md = (_TEMPLATE_DIR / "reference.md").read_text(encoding="utf-8")
        duration_rule = (
            f"目标视频时长约 {target_duration} 秒。"
            if target_duration
            else "目标视频时长为 90 到 150 秒（1分半到2分半），根据内容灵活调整，允许范围 60 到 600 秒。"
        )

        prompt = (
            "以下 theory_video.md 不符合通用计算机理论动画视频规范，请修复后返回完整 theory_video.md。\n\n"
            f"## 用户学习需求\n\n{learning_need}\n\n"
            f"## 目标时长\n\n{duration_rule}\n\n"
            f"## DSL 规则\n\n{rules_md}\n\n"
            f"## 输出参考\n\n{reference_md}\n\n"
            f"## 原始 theory_video.md\n\n{markdown_text}\n\n"
            "## 问题列表\n\n"
            + "\n".join(f"- {p}" for p in problems)
            + "\n\n只返回修复后的完整 theory_video.md，不要解释，不要输出 JSON，不要代码围栏包裹全文。"
        )

        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="你只输出修复后的完整 theory_video.md，不输出任何解释。"),
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
        audit_payload: dict[str, Any] | None = None,
    ) -> None:
        (output_dir / "theory_video.md").write_text(markdown_text, encoding="utf-8")
        (output_dir / "index.html").write_text(html_content, encoding="utf-8")
        payload = audit_payload or {"passed": audit.passed, "problems": audit.problems}
        (output_dir / "audit.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def _generate_with_retry(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self.generate_markdown(prompt)
            except Exception as exc:
                last_error = exc
                logger.warning("Theory Markdown 生成失败 (attempt %d/3): %s", attempt + 1, exc)

        raise CartoonGenerationError(f"Theory Markdown 生成失败: {last_error}")

    async def _parse_validate_repair(
        self,
        learning_need: str,
        markdown_text: str,
        target_duration: int | None = None,
    ) -> tuple[CartoonVideoDocument, str, AuditResult]:
        last_text = markdown_text
        last_audit = AuditResult(passed=False, problems=[])

        for round_num in range(self.MAX_REPAIR_ROUNDS + 1):
            try:
                doc = parse_markdown(last_text)
            except ValueError as exc:
                last_audit = AuditResult(passed=False, problems=[str(exc)])
                if round_num >= self.MAX_REPAIR_ROUNDS:
                    raise CartoonGenerationError(f"Markdown 解析失败且修复次数耗尽: {exc}", audit=last_audit)

                last_text = await self.repair_markdown(
                    learning_need=learning_need,
                    markdown_text=last_text,
                    problems=[str(exc)],
                    target_duration=target_duration,
                )
                last_text = _clean_llm_output(last_text)
                continue

            audit = validate_markdown(doc, last_text)
            if audit.passed:
                return doc, last_text, audit

            last_audit = audit
            if round_num >= self.MAX_REPAIR_ROUNDS:
                raise CartoonGenerationError(
                    f"Markdown 校验失败且修复次数耗尽: {'; '.join(audit.problems[:8])}",
                    audit=audit,
                )

            logger.warning("Markdown 校验失败 (round %d): %s", round_num + 1, "; ".join(audit.problems[:6]))
            last_text = await self.repair_markdown(
                learning_need=learning_need,
                markdown_text=last_text,
                problems=audit.problems,
                target_duration=target_duration,
            )
            last_text = _clean_llm_output(last_text)

        raise CartoonGenerationError("Markdown 解析持续失败", audit=last_audit)

    async def _repair_html_via_markdown(
        self,
        learning_need: str,
        markdown_text: str,
        problems: list[str],
        target_duration: int | None = None,
    ) -> tuple[CartoonVideoDocument, str, str, AuditResult]:
        last_text = markdown_text
        last_audit = AuditResult(passed=False, problems=problems)

        for round_num in range(self.MAX_REPAIR_ROUNDS):
            logger.warning(
                "HTML 校验失败，尝试修复 Markdown (round %d): %s",
                round_num + 1,
                "; ".join(last_audit.problems[:6]),
            )
            last_text = await self.repair_markdown(
                learning_need=learning_need,
                markdown_text=last_text,
                problems=last_audit.problems,
                target_duration=target_duration,
            )
            last_text = _clean_llm_output(last_text)

            doc = parse_markdown(last_text)
            md_audit = validate_markdown(doc, last_text)
            if not md_audit.passed:
                last_audit = md_audit
                continue

            html_content = compose_html(doc)
            html_audit = validate_html(html_content, doc)
            if html_audit.passed:
                return doc, last_text, html_content, html_audit

            last_audit = html_audit

        raise CartoonGenerationError(
            f"修复后 HTML 校验仍失败: {'; '.join(last_audit.problems[:8])}",
            audit=last_audit,
        )

    @staticmethod
    def _copy_template_assets(output_dir: Path) -> None:
        for name in ("style.css", "runtime.js"):
            src = _TEMPLATE_DIR / name
            if src.is_file():
                shutil.copy2(src, output_dir / name)
            else:
                raise CartoonGenerationError(f"模板资源不存在: {src}")

        assets_dir = output_dir / "assets" / "vendor"
        assets_dir.mkdir(parents=True, exist_ok=True)

        roots: list[Path] = [Path.cwd()]
        current = Path(__file__).resolve()
        for index in range(1, min(8, len(current.parents))):
            roots.append(current.parents[index])

        candidates: list[Path] = []
        for root in roots:
            candidates.extend(
                [
                    root / "node_modules" / "gsap" / "dist" / "gsap.min.js",
                    root / "video-render" / "node_modules" / "gsap" / "dist" / "gsap.min.js",
                    root / "frontend" / "node_modules" / "gsap" / "dist" / "gsap.min.js",
                ]
            )

        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve() if candidate.exists() else candidate
            if resolved in seen:
                continue
            seen.add(resolved)

            if candidate.is_file():
                shutil.copy2(candidate, assets_dir / "gsap.min.js")
                return

        raise CartoonGenerationError(
            "缺少 GSAP 运行时文件，请在项目根目录或 video-render 目录执行 npm install gsap。"
        )