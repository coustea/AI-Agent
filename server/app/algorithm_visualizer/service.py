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


async def instrument_code_with_llm(
    language: str,
    code: str,
    algorithm: str,
    visualizer_type: str,
) -> str:
    """使用 LLM 自动为用户提交的裸算法代码插装可视化 Tracer 调用。"""
    from app.infra.llm import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    SPECS = {
        "array": {
            "python": """from visual_tracer import ArrayTracer
tracer = ArrayTracer()
tracer.init_array(arr)
tracer.compare(i, j)
tracer.swap(i, j)
tracer.assign(index, value)
tracer.mark_sorted(index)
tracer.move_pointer(pointers_dict) # e.g. tracer.move_pointer({"i": i, "j": j})
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code""",
            "javascript": """import { ArrayTracer } from './js_tracer.js';
const tracer = new ArrayTracer();
tracer.initArray(arr);
tracer.compare(i, j);
tracer.swap(i, j);
tracer.assign(index, value);
tracer.markSorted(index);
tracer.movePointer(pointers); # e.g. tracer.movePointer({"i": i, "j": j})
tracer.finish();""",
            "cpp": """#include "visual_tracer.hpp"
ArrayTracer tracer;
tracer.initArray(arr);
tracer.compare(i, j);
tracer.swap(i, j);
tracer.assign(index, value);
tracer.markSorted(index);
tracer.movePointer(name_str, value);
tracer.finish();""",
            "c": """#include "visual_tracer.h"
vt_init_array(arr, len);
vt_compare(i, j);
vt_swap(i, j);
vt_assign(index, value);
vt_mark_sorted(index);
vt_move_pointer(name, value);
vt_finish();""",
            "java": """ArrayTracer tracer = new ArrayTracer();
tracer.initArray(arr);
tracer.compare(i, j);
tracer.swap(i, j);
tracer.assign(index, value);
tracer.markSorted(index);
tracer.movePointer(name, value);
tracer.finish();"""
        },
        "stack-queue": {
            "python": """# Stack:
from visual_tracer import StackTracer
tracer = StackTracer()
tracer.init_stack()
tracer.push(val)
tracer.pop()
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code

# Queue:
from visual_tracer import QueueTracer
tracer = QueueTracer()
tracer.init_queue()
tracer.enqueue(val)
tracer.dequeue()
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code""",
            "javascript": """# Stack:
import { StackTracer } from './js_tracer.js';
const tracer = new StackTracer();
tracer.initStack();
tracer.push(val);
tracer.pop();
tracer.finish();

# Queue:
import { QueueTracer } from './js_tracer.js';
const tracer = new QueueTracer();
tracer.initQueue();
tracer.enqueue(val);
tracer.dequeue();
tracer.finish();""",
            "cpp": """# Stack:
#include "visual_tracer.hpp"
StackTracer tracer;
tracer.initStack();
tracer.push(val);
tracer.pop();
tracer.finish();

# Queue:
#include "visual_tracer.hpp"
QueueTracer tracer;
tracer.initQueue();
tracer.enqueue(val);
tracer.dequeue();
tracer.finish();""",
            "c": """# Stack:
#include "visual_tracer.h"
vt_init_stack();
vt_push(val);
vt_pop();
vt_finish();

# Queue:
#include "visual_tracer.h"
vt_init_queue();
vt_enqueue(val);
vt_dequeue();
vt_finish();""",
            "java": """# Stack:
StackTracer tracer = new StackTracer();
tracer.initStack();
tracer.push(val);
tracer.pop();
tracer.finish();

# Queue:
QueueTracer tracer = new QueueTracer();
tracer.initQueue();
tracer.enqueue(val);
tracer.dequeue();
tracer.finish();"""
        },
        "linked-list": {
            "python": """from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

# Usage spec:
# 1. Initialize with nodes and pointers list of dicts.
# nodes: list of {"id": str, "label": str, "tone": str}
# pointers: list of {"label": str, "nodeIndex": int, "tone": str}
nodes = [{"id": f"node-{i}", "label": str(val), "tone": "default"} for i, val in enumerate(initial_values)]
pointers = [{"label": "head", "nodeIndex": 0, "tone": "accent"}]
tracer.init_list(nodes, pointers)

# 2. Operations:
tracer.move_pointer(label_str, node_index) # node_index is int index or None
tracer.set_visited(node_index, True)
tracer.add_node(label_str, tone="default") # returns new nodeIndex
tracer.remove_node(node_index)
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code""",
            "javascript": """import { LinkedListTracer } from './js_tracer.js';
const tracer = new LinkedListTracer();

// Usage spec:
// 1. Initialize with nodes and pointers:
// nodes: list of {id: string, label: string, tone: string}
// pointers: list of {label: string, nodeIndex: number, tone: string}
const nodes = [{id: "node-0", label: "1", tone: "default"}];
const pointers = [{label: "head", nodeIndex: 0, tone: "accent"}];
tracer.initList(nodes, pointers);

// 2. Operations:
tracer.movePointer(label_str, node_index); // node_index is number index or null
tracer.setVisited(node_index, true);
tracer.addNode(label_str, tone); // returns new nodeIndex
tracer.removeNode(node_index);
tracer.finish();""",
            "cpp": """#include "visual_tracer.hpp"
LinkedListTracer tracer;

// Usage spec:
// 1. Initialize with nodes and pointers:
// nodes: std::vector<LinkedListNodeItem> containing {id_str, label_str, tone_str}
// pointers: std::vector<LinkedListPointerItem> containing {label_str, node_idx, tone_str}
std::vector<LinkedListNodeItem> nodes = {{"node-0", "1", "default"}};
std::vector<LinkedListPointerItem> pointers = {{"head", 0, "accent"}};
tracer.initList(nodes, pointers);

// 2. Operations:
tracer.movePointer(label_str, node_index); // node_index is int or -1
tracer.setVisited(node_index, true);
tracer.addNode(label_str, tone_str); // returns new nodeIndex
tracer.removeNode(node_index);
tracer.finish();""",
            "java": """LinkedListTracer tracer = new LinkedListTracer();
// Java equivalent of C++ LinkedListTracer (camelCase methods)"""
        },
        "tree": {
            "python": """from visual_tracer import TreeTracer
tracer = TreeTracer()

# Usage spec:
# 1. Initialize tree nodes.
# nodes: list of {"id": str, "label": str, "left": str/None, "right": str/None, "tone": str}
nodes = [{"id": "1", "label": "1", "left": "2", "right": "3", "tone": "default"}]
tracer.init_tree(nodes)

# 2. Operations:
tracer.visit_node(node_id_str, True)
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code""",
            "javascript": """import { TreeTracer } from './js_tracer.js';
const tracer = new TreeTracer();
const nodes = [{id: "1", label: "1", left: "2", right: "3", tone: "default"}];
tracer.initTree(nodes);
tracer.visitNode(node_id_str, true);
tracer.finish();""",
            "cpp": """#include "visual_tracer.hpp"
TreeTracer tracer;
// nodes: std::vector<TreeNodeItem> containing {id_str, label_str, left_id_str, right_id_str, tone_str}
std::vector<TreeNodeItem> nodes = {{"1", "1", "2", "3", "default"}};
tracer.initTree(nodes);
tracer.visitNode(node_id_str, true);
tracer.finish();"""
        },
        "graph": {
            "python": """from visual_tracer import GraphTracer
tracer = GraphTracer()

# Usage spec:
# 1. Initialize graph nodes.
# nodes: list of {"id": str, "label": str, "x": int, "y": int, "tone": str}
nodes = [{"id": str(i), "label": str(i), "x": 0, "y": 0, "tone": "default"} for i in range(N)]
tracer.init_graph(nodes)

# 2. Operations:
tracer.visit_node(node_id_str, True)
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code""",
            "javascript": """import { GraphTracer } from './js_tracer.js';
const tracer = new GraphTracer();
const nodes = [{id: "0", label: "0", x: 0, y: 0, tone: "default"}];
tracer.initGraph(nodes);
tracer.visitNode(node_id_str, true);
tracer.finish();""",
            "cpp": """#include "visual_tracer.hpp"
GraphTracer tracer;
// nodes: std::vector<GraphNodeItem> containing {id_str, label_str, x, y, tone_str}
std::vector<GraphNodeItem> nodes;
for (int i = 0; i < N; i++) {
    nodes.push_back({std::to_string(i), std::to_string(i), 0, 0, "default"});
}
tracer.initGraph(nodes);
tracer.visitNode(node_id_str, true); // node_id_str is std::string!
tracer.finish();"""
        },
        "dp-table": {
            "python": """from visual_tracer import DpTableTracer
tracer = DpTableTracer()
tracer.init_table(headers_list, num_rows, num_cols, fill_value=0)
tracer.set_value(row, col, value)
tracer.highlight(row, col, tone="active")
tracer.clear_highlights()
tracer.finish()
tracer.dump() # Must call tracer.dump() at the very end of code""",
            "javascript": """import { DpTableTracer } from './js_tracer.js';
const tracer = new DpTableTracer();
tracer.initTable(headers_list, num_rows, num_cols, 0);
tracer.setValue(row, col, value);
tracer.highlight(row, col, "active");
tracer.clearHighlights();
tracer.finish();""",
            "cpp": """#include "visual_tracer.hpp"
DpTableTracer tracer;
tracer.initTable(headers_list, num_rows, num_cols, 0);
tracer.setValue(row, col, value);
tracer.highlight(row, col, "active");
tracer.clearHighlights();
tracer.finish();"""
        }
    }

    system_prompt = (
        "You are an expert algorithm visualization code writer. Your task is to instrument the user's plain code "
        "with visualization tracer instructions using the specified Tracer class and API specs.\n\n"
        "Return ONLY the instrumented code inside standard markdown code block. Do not include any explanations or extra text."
    )

    spec = SPECS.get(visualizer_type, {}).get(language, "")
    if not spec:
        spec = f"Please use standard {visualizer_type} tracer with camelCase or snake_case methods corresponding to the {language} language."

    prompt = f"""You are given a plain algorithm code. Please instrument this code with the appropriate tracer calls.

Language: {language}
Algorithm: {algorithm}
Visualizer Type: {visualizer_type}

[Visualizer API and Usage Specs for {language} {visualizer_type}]
{spec}

[Instructions]
- Do NOT rewrite or change the algorithm's logic. Only insert the tracer calls.
- You MUST define and initialize the tracer instance variable exactly named `tracer` globally (at the top level of the file, outside any class or function), so it is globally accessible.
- Ensure the instrumented code compiles/runs successfully.
- For tree and graph visualizers, the node ID arguments MUST be strings (e.g. convert integer node indices to string like `str(node)` or `std::to_string(node)`).
- For linked-list visualizers, do NOT find node indices by traversing links (like `temp = temp.next`) because links are mutated during algorithm execution and will cause AttributeError/NullPointerException. Instead, define a list/array named `nodes_list` at the start of the function and populate it with the original node references (e.g. traverse the linked list once to append all node objects to `nodes_list`), then initialize `tracer` (e.g. mapping `nodes_list` elements to dict/object format for `tracer.init_list(nodes, pointers)`), and in the loop find a node's index via reference lookup (e.g. `nodes_list.index(curr)` in Python, or pointer comparison in C++).
- In Python, you must call `tracer.dump()` at the very end of the code.
- In C++, C, JavaScript, Java, make sure the imports or includes (like `#include "visual_tracer.hpp"`) are correctly added.

User Plain Code:
```{language}
{code}
```

Please output the fully instrumented code inside a standard markdown code block. Do not write any other explanation or text.
"""

    llm = get_llm()
    resp = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=prompt)])
    content = getattr(resp, "content", "") or ""
    match = re.search(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


async def run_visualization_in_sandbox(
    language: str,
    code: str,
    algorithm: str,
    visualizer_type: str,
    domain: str,
) -> Dict[str, Any]:
    # 始终调用 LLM 进行自动插装，不兼容任何旧版已手动插装的 Tracer 代码
    try:
        code = await instrument_code_with_llm(
            language=language,
            code=code,
            algorithm=algorithm,
            visualizer_type=visualizer_type,
        )
    except Exception as e:
        raise Exception(f"自动分析并插装代码失败: {str(e)}")
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
                    proc.communicate(), timeout=15.0
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
