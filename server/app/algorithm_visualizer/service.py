"""算法可视化沙箱执行服务。

当前阶段设计：
1. 不接入 LLM。
2. 不自动插装用户普通代码。
3. 用户代码必须来自算法模板，或至少必须手动包含 tracer 调用。
4. 后端只做：
   - 校验语言和算法模板是否匹配
   - 复制对应语言 SDK
   - 编译运行
   - 读取 trace.json
   - 校验 required_events
   - 返回事件流
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.algorithm_visualizer.template_registry import get_algorithm_info

SDK_DIR = Path(__file__).parent / "tracer_sdks"


class VisualizerRunError(Exception):
    """算法可视化运行错误。"""

    def __init__(self, message: str, error_type: str = "VISUALIZER_RUN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type


@dataclass
class RuntimeConfig:
    sdk_source_filename: str
    sdk_target_filename: str
    user_code_filename: str
    compile_cmd: List[str]
    run_cmd: List[str]


async def run_visualization_in_sandbox(
    language: str,
    code: str,
    algorithm: str,
    visualizer_type: str,
    domain: str,
    input_data: Optional[str] = None,
) -> Dict[str, Any]:
    """运行用户提交的可视化代码，返回 TraceEvent[]。

    当前阶段不做 LLM 插装。
    code 必须已经包含 tracer 调用，并且正常生成 trace.json。
    """

    language = (language or "").strip()
    algorithm = (algorithm or "").strip()
    code = code or ""

    if not language:
        raise VisualizerRunError("请先选择编程语言。", "MISSING_LANGUAGE")

    if not algorithm:
        raise VisualizerRunError("请先选择算法模板。", "MISSING_ALGORITHM")

    if not code.strip():
        raise VisualizerRunError("请填写或粘贴算法可视化代码。", "MISSING_CODE")

    try:
        algorithm_info = get_algorithm_info(algorithm)
    except ValueError as e:
        raise VisualizerRunError(str(e), "UNSUPPORTED_ALGORITHM") from e

    supported_languages = algorithm_info.get("supported_languages", [])
    if language not in supported_languages:
        raise VisualizerRunError(
            f"算法 {algorithm} 不支持语言 {language}，请选择支持的语言：{', '.join(supported_languages)}。",
            "UNSUPPORTED_LANGUAGE",
        )

    expected_visualizer_type = algorithm_info.get("visualizer_type")
    if visualizer_type and visualizer_type != expected_visualizer_type:
        raise VisualizerRunError(
            f"算法 {algorithm} 的可视化类型应为 {expected_visualizer_type}，当前收到 {visualizer_type}。",
            "VISUALIZER_TYPE_MISMATCH",
        )

    visualizer_type = expected_visualizer_type

    with tempfile.TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)

        runtime = build_runtime_config(language=language, code=code)

        copy_sdk(runtime=runtime, run_dir=run_dir)
        write_user_code(runtime=runtime, run_dir=run_dir, code=code)

        if runtime.compile_cmd:
            compile_result = await run_process(
                cmd=runtime.compile_cmd,
                cwd=run_dir,
                input_data=None,
                timeout=15.0,
            )

            if compile_result["returncode"] != 0:
                raise VisualizerRunError(
                    "代码编译错误：\n" + pick_error_message(compile_result),
                    "COMPILE_ERROR",
                )

        run_result = await run_process(
            cmd=runtime.run_cmd,
            cwd=run_dir,
            input_data=input_data,
            timeout=3.0,
        )

        if run_result["returncode"] != 0:
            raise VisualizerRunError(
                "代码运行出错：\n" + pick_error_message(run_result),
                "RUNTIME_ERROR",
            )

        trace_file = run_dir / "trace.json"
        if not trace_file.exists():
            raise VisualizerRunError(
                "运行成功但未生成 trace.json。请确认代码来自算法可视化模板，并保留 tracer.finish() / vt_finish() / tracer.dump() 调用。",
                "TRACE_FILE_MISSING",
            )

        raw = trace_file.read_text(encoding="utf-8")
        if len(raw) > 10 * 1024 * 1024:
            raise VisualizerRunError(
                "trace.json 文件过大（超过 10MB），可能存在异常。",
                "TRACE_JSON_INVALID",
            )

        try:
            events = json.loads(raw)
        except Exception as e:
            raise VisualizerRunError(
                f"trace.json 解析失败：{str(e)}",
                "TRACE_JSON_INVALID",
            ) from e

        if not isinstance(events, list) or len(events) == 0:
            raise VisualizerRunError(
                "可视化追踪事件流为空，没有录制到有效步骤。",
                "TRACE_EVENT_EMPTY",
            )

        normalize_event_visualizer_type(events)

        validate_event_stream(
            events=events,
            visualizer_type=visualizer_type,
            required_events=algorithm_info.get("required_events", []),
        )

        return {
            "domain": algorithm_info.get("domain", domain),
            "algorithm": algorithm,
            "visualizerType": visualizer_type,
            "language": language,
            "events": events,
            "result": None,
            "summary": f"执行成功，共产生 {len(events)} 步可视化操作。",
            "stdout": run_result["stdout"],
        }


def build_runtime_config(language: str, code: str) -> RuntimeConfig:
    """根据语言构建编译和运行配置。"""

    if language == "python":
        return RuntimeConfig(
            sdk_source_filename="python_tracer.py",
            sdk_target_filename="visual_tracer.py",
            user_code_filename="main.py",
            compile_cmd=[],
            run_cmd=[sys.executable, "main.py"],
        )

    if language == "javascript":
        if not shutil.which("node"):
            raise VisualizerRunError(
                "系统未检测到 Node.js，无法运行 JavaScript 代码。",
                "RUNTIME_NOT_FOUND",
            )

        return RuntimeConfig(
            sdk_source_filename="js_tracer.js",
            sdk_target_filename="js_tracer.js",
            user_code_filename="main.js",
            compile_cmd=[],
            run_cmd=["node", "main.js"],
        )

    if language == "cpp":
        if not shutil.which("g++"):
            raise VisualizerRunError(
                "系统未检测到 g++ 编译器，无法编译运行 C++ 代码。",
                "RUNTIME_NOT_FOUND",
            )

        return RuntimeConfig(
            sdk_source_filename="cpp_tracer.hpp",
            sdk_target_filename="visual_tracer.hpp",
            user_code_filename="main.cpp",
            compile_cmd=["g++", "-std=c++17", "main.cpp", "-o", "main"],
            run_cmd=["./main"],
        )

    if language == "c":
        if not shutil.which("gcc"):
            raise VisualizerRunError(
                "系统未检测到 gcc 编译器，无法编译运行 C 代码。",
                "RUNTIME_NOT_FOUND",
            )

        return RuntimeConfig(
            sdk_source_filename="c_tracer.h",
            sdk_target_filename="visual_tracer.h",
            user_code_filename="main.c",
            compile_cmd=["gcc", "main.c", "-o", "main"],
            run_cmd=["./main"],
        )

    if language == "java":
        if not shutil.which("javac") or not shutil.which("java"):
            raise VisualizerRunError(
                "系统未检测到 Java JDK（javac/java），无法编译运行 Java 代码。",
                "RUNTIME_NOT_FOUND",
            )

        class_name = detect_java_class_name(code)
        user_code_filename = f"{class_name}.java"

        return RuntimeConfig(
            sdk_source_filename="VisualTracer.java",
            sdk_target_filename="VisualTracer.java",
            user_code_filename=user_code_filename,
            compile_cmd=["javac", user_code_filename, "VisualTracer.java"],
            run_cmd=["java", class_name],
        )

    raise VisualizerRunError(f"不支持的编程语言：{language}", "UNSUPPORTED_LANGUAGE")


def copy_sdk(runtime: RuntimeConfig, run_dir: Path) -> None:
    """复制对应语言 Tracer SDK 到临时运行目录。"""

    sdk_src_path = SDK_DIR / runtime.sdk_source_filename
    if not sdk_src_path.exists():
        raise VisualizerRunError(
            f"Tracer SDK 缺失：{runtime.sdk_source_filename}",
            "TRACER_SDK_MISSING",
        )

    shutil.copy(str(sdk_src_path), str(run_dir / runtime.sdk_target_filename))


def write_user_code(runtime: RuntimeConfig, run_dir: Path, code: str) -> None:
    """写入用户代码。"""

    with open(run_dir / runtime.user_code_filename, "w", encoding="utf-8") as f:
        f.write(code)


async def run_process(
    cmd: List[str],
    cwd: Path,
    input_data: Optional[str],
    timeout: float,
) -> Dict[str, Any]:
    """执行编译或运行命令。"""

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        stdin=asyncio.subprocess.PIPE if input_data is not None else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(
                input=input_data.encode("utf-8") if input_data is not None else None
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as e:
        proc.kill()
        raise VisualizerRunError(
            "代码执行超时，可能存在死循环或递归无法结束。",
            "TIMEOUT",
        ) from e

    return {
        "returncode": proc.returncode,
        "stdout": stdout.decode("utf-8", errors="ignore"),
        "stderr": stderr.decode("utf-8", errors="ignore"),
    }


def detect_java_class_name(code: str) -> str:
    """检测 Java 主类名。"""

    public_match = re.search(r"public\s+class\s+(\w+)", code)
    if public_match:
        return public_match.group(1)

    class_match = re.search(r"class\s+(\w+)", code)
    if class_match:
        return class_match.group(1)

    return "Solution"


def normalize_event_visualizer_type(events: List[Dict[str, Any]]) -> None:
    """兼容事件字段 visualizerType / visualizer_type。

    前端统一使用 visualizerType。
    """

    for event in events:
        if "visualizer_type" in event and "visualizerType" not in event:
            event["visualizerType"] = event.pop("visualizer_type")


def validate_event_stream(
    events: List[Dict[str, Any]],
    visualizer_type: str,
    required_events: List[str],
) -> None:
    """校验事件流是否符合算法模板要求。"""

    actual_types = {event.get("type") for event in events if event.get("type")}

    missing_events = [
        event_type for event_type in required_events
        if event_type not in actual_types
    ]

    if missing_events:
        raise VisualizerRunError(
            "代码已运行，但生成的可视化事件不完整，缺少事件："
            + ", ".join(missing_events)
            + "。请检查是否使用了正确的算法模板，并保留必要 tracer 调用。",
            "TRACE_EVENT_INVALID",
        )

    invalid_visualizer_events = [
        event for event in events
        if event.get("visualizerType") is not None
        and event.get("visualizerType") != visualizer_type
    ]

    if invalid_visualizer_events:
        raise VisualizerRunError(
            f"事件流的 visualizerType 与算法模板不一致，应为 {visualizer_type}。",
            "TRACE_VISUALIZER_TYPE_INVALID",
        )


def pick_error_message(result: Dict[str, Any]) -> str:
    """优先返回 stderr，其次 stdout。"""

    return result.get("stderr") or result.get("stdout") or "未知错误"
