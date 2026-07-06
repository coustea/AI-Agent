"""算法可视化沙箱执行服务。

在临时目录中准备 SDK + 用户代码，编译执行，读取 trace.json 返回事件流。
不依赖用户目录或认证系统。
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

# Tracer SDK 目录
SDK_DIR = Path(__file__).parent / "tracer_sdks"


async def run_visualization_in_sandbox(
    language: str,
    code: str,
    algorithm: str,
    visualizer_type: str,
    domain: str,
) -> Dict[str, Any]:
    """多语言沙箱执行服务。

    1. 创建临时目录。
    2. 复制对应语言的 VisualTracer SDK 到该目录。
    3. 写入用户代码。
    4. 执行编译（若需）和运行，设置超时防死循环。
    5. 读取 trace.json 还原为事件列表。
    6. 清理临时目录。

    Args:
        language: 编程语言 key (python/javascript/cpp/c/java)。
        code: 用户编辑后的代码。
        algorithm: 算法 key (bubble_sort 等)。
        visualizer_type: 可视化器类型 (array/stack-queue 等)。
        domain: 领域 (当前固定 data_structure)。

    Returns:
        包含 events 列表的字典。

    Raises:
        Exception: 编译错误、运行错误、超时或 trace.json 缺失。
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)

        # 根据语言配置 SDK 文件名、用户代码文件名、编译/运行命令
        sdk_source_filename = ""
        sdk_target_filename = ""
        user_code_filename = ""
        compile_cmd: list[str] = []
        run_cmd: list[str] = []

        if language == "python":
            sdk_source_filename = "python_tracer.py"
            sdk_target_filename = "visual_tracer.py"
            user_code_filename = "main.py"
            run_cmd = [sys.executable, "main.py"]

        elif language == "javascript":
            if not shutil.which("node"):
                raise Exception(
                    "系统未检测到 Node.js，无法运行 JavaScript 代码。"
                )
            sdk_source_filename = "js_tracer.js"
            sdk_target_filename = "js_tracer.js"
            user_code_filename = "main.js"
            run_cmd = ["node", "main.js"]

        elif language == "cpp":
            if not shutil.which("g++"):
                raise Exception(
                    "系统未检测到 g++ 编译器，无法编译运行 C++ 代码。"
                )
            sdk_source_filename = "cpp_tracer.hpp"
            sdk_target_filename = "visual_tracer.hpp"
            user_code_filename = "main.cpp"
            compile_cmd = ["g++", "-std=c++17", "main.cpp", "-o", "main"]
            run_cmd = ["./main"]

        elif language == "c":
            if not shutil.which("gcc"):
                raise Exception(
                    "系统未检测到 gcc 编译器，无法编译运行 C 代码。"
                )
            sdk_source_filename = "c_tracer.h"
            sdk_target_filename = "visual_tracer.h"
            user_code_filename = "main.c"
            compile_cmd = ["gcc", "main.c", "-o", "main"]
            run_cmd = ["./main"]

        elif language == "java":
            if not shutil.which("javac") or not shutil.which("java"):
                raise Exception(
                    "系统未检测到 Java JDK (javac/java)，无法编译运行 Java 代码。"
                )
            sdk_source_filename = "VisualTracer.java"
            sdk_target_filename = "VisualTracer.java"
            # 动态匹配 Java 类名，防止编译失败
            match = re.search(r"public\s+class\s+(\w+)", code)
            class_name = match.group(1) if match else "Solution"
            user_code_filename = f"{class_name}.java"
            compile_cmd = ["javac", user_code_filename, "VisualTracer.java"]
            run_cmd = ["java", class_name]

        else:
            raise Exception(f"不支持的编程语言：{language}")

        # 准备 SDK 文件
        sdk_src_path = SDK_DIR / sdk_source_filename
        if not sdk_src_path.exists():
            raise Exception(f"Tracer SDK 缺失：{sdk_source_filename}")
        shutil.copy(str(sdk_src_path), str(run_dir / sdk_target_filename))

        # 写入用户代码
        with open(run_dir / user_code_filename, "w", encoding="utf-8") as f:
            f.write(code)

        # 编译（若需）
        if compile_cmd:
            proc = await asyncio.create_subprocess_exec(
                *compile_cmd,
                cwd=str(run_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=5.0
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise Exception("代码编译超时")
            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="ignore") or stdout.decode(
                    "utf-8", errors="ignore"
                )
                raise Exception(f"代码编译错误：\n{err_msg}")

        # 执行
        proc = await asyncio.create_subprocess_exec(
            *run_cmd,
            cwd=str(run_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=3.0
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise Exception(
                "代码执行超时（最长运行限制为 3000ms），可能包含死循环。"
            )
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="ignore") or stdout.decode(
                "utf-8", errors="ignore"
            )
            raise Exception(f"代码运行出错：\n{err_msg}")

        # 读取 trace.json
        trace_file = run_dir / "trace.json"
        if not trace_file.exists():
            raise Exception(
                "运行成功但未生成 trace.json 事件流文件，"
                "请确保代码包含 tracer.finish() / vt_finish() 调用并正常执行。"
            )
        with open(trace_file, "r", encoding="utf-8") as f:
            events = json.load(f)
        if not isinstance(events, list) or len(events) == 0:
            raise Exception("可视化追踪事件流为空，没有录制到有效的步骤。")

        return {
            "domain": domain,
            "algorithm": algorithm,
            "visualizer_type": visualizer_type,
            "language": language,
            "events": events,
            "result": None,
            "summary": f"执行成功，共产生 {len(events)} 步可视化操作。",
        }
