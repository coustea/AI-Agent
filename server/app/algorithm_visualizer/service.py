import os
import re
import sys
import json
import tempfile
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from fastapi import HTTPException

def APIException(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)

# Define the Tracer SDK code for each language
PYTHON_TRACER_SDK = """
import json
import sys

class BaseTracer:
    @staticmethod
    def _emit(action_type, payload=None):
        msg = {"type": action_type}
        if payload is not None:
            msg["payload"] = payload
        print(f"__TRACER__:{json.dumps(msg)}")
        sys.stdout.flush()

    @classmethod
    def clear(cls):
        cls._emit("CLEAR")

class ArrayTracer(BaseTracer):
    @classmethod
    def init(cls, array):
        cls._emit("INIT", {"visualizerType": "1D_ARRAY", "array": array})

    @classmethod
    def compare(cls, i, j):
        cls._emit("COMPARE", [i, j])

    @classmethod
    def swap(cls, i, j):
        cls._emit("SWAP", [i, j])

    @classmethod
    def update(cls, index, value):
        cls._emit("UPDATE", {"index": index, "value": value})

    @classmethod
    def set_value(cls, index, value):
        cls.update(index, value)

    @classmethod
    def mark_answer(cls, index):
        cls._emit("MARK_ANSWER", index)

    @classmethod
    def markAnswer(cls, index):
        cls.mark_answer(index)

    @classmethod
    def highlight(cls, indices, tone="active"):
        cls._emit("HIGHLIGHT", {"indices": indices, "tone": tone})

class TreeTracer(BaseTracer):
    @classmethod
    def init(cls):
        cls._emit("INIT", {"visualizerType": "TREE"})

    @classmethod
    def add_node(cls, node_id, val, x=0, y=0):
        cls._emit("ADD_NODE", {"id": node_id, "val": val, "x": x, "y": y})

    @classmethod
    def connect(cls, parent_id, child_id):
        cls._emit("ADD_EDGE", {"from": parent_id, "to": child_id})

    @classmethod
    def visit(cls, node_id):
        cls._emit("VISIT_NODE", {"id": node_id})

    @classmethod
    def leave(cls, node_id):
        cls._emit("LEAVE_NODE", {"id": node_id})

class GraphTracer(BaseTracer):
    @classmethod
    def init(cls):
        cls._emit("INIT", {"visualizerType": "GRAPH"})

    @classmethod
    def add_node(cls, node_id, val, x=0, y=0):
        cls._emit("ADD_NODE", {"id": node_id, "val": val, "x": x, "y": y})

    @classmethod
    def add_edge(cls, from_id, to_id, weight=None):
        payload = {"from": from_id, "to": to_id}
        if weight is not None:
            payload["weight"] = weight
        cls._emit("ADD_EDGE", payload)

    @classmethod
    def visit(cls, node_id):
        cls._emit("VISIT_NODE", {"id": node_id})

    @classmethod
    def leave(cls, node_id):
        cls._emit("LEAVE_NODE", {"id": node_id})

Tracer = ArrayTracer
"""

CPP_TRACER_SDK = """#pragma once
#include <iostream>
#include <vector>
#include <string>

class BaseTracer {
protected:
    static void emit(const std::string& type, const std::string& payload_json = "") {
        std::cout << "__TRACER__:{\\\"type\\\":\\\"" << type << "\\\"";
        if (!payload_json.empty()) {
            std::cout << ",\\\"payload\\\":" << payload_json;
        }
        std::cout << "}" << std::endl;
    }
public:
    static void clear() {
        emit("CLEAR");
    }
};

class ArrayTracer : public BaseTracer {
public:
    static void init(const std::vector<int>& array) {
        std::string arr_str = "[";
        for (size_t i = 0; i < array.size(); ++i) {
            arr_str += std::to_string(array[i]);
            if (i < array.size() - 1) arr_str += ",";
        }
        arr_str += "]";
        emit("INIT", "{\\\"visualizerType\\\":\\\"1D_ARRAY\\\",\\\"array\\\":" + arr_str + "}");
    }

    static void compare(int i, int j) {
        emit("COMPARE", "[" + std::to_string(i) + "," + std::to_string(j) + "]");
    }

    static void swap(int i, int j) {
        emit("SWAP", "[" + std::to_string(i) + "," + std::to_string(j) + "]");
    }

    static void update(int index, int value) {
        emit("UPDATE", "{\\\"index\\":" + std::to_string(index) + ",\\\"value\\\":" + std::to_string(value) + "}");
    }

    static void setValue(int index, int value) {
        update(index, value);
    }

    static void highlight(const std::vector<int>& indices, const std::string& tone = "active") {
        std::string indices_str = "[";
        for (size_t i = 0; i < indices.size(); ++i) {
            indices_str += std::to_string(indices[i]);
            if (i < indices.size() - 1) indices_str += ",";
        }
        indices_str += "]";
        emit("HIGHLIGHT", "{\\\"indices\\\":" + indices_str + ",\\\"tone\\\":\\\"" + tone + "\\\"}");
    }

    static void mark_answer(int index) {
        emit("MARK_ANSWER", std::to_string(index));
    }

    static void markAnswer(int index) {
        mark_answer(index);
    }
};

class TreeTracer : public BaseTracer {
public:
    static void init() {
        emit("INIT", "{\\\"visualizerType\\\":\\\"TREE\\\"}");
    }

    static void addNode(const std::string& id, int val, int x = 0, int y = 0) {
        emit("ADD_NODE", "{\\\"id\\\":\\\"" + id + "\\\",\\\"val\\\":" + std::to_string(val) + ",\\\"x\\\":" + std::to_string(x) + ",\\\"y\\\":" + std::to_string(y) + "}");
    }

    static void connect(const std::string& parent_id, const std::string& child_id) {
        emit("ADD_EDGE", "{\\\"from\\\":\\\"" + parent_id + "\\\",\\\"to\\\":\\\"" + child_id + "\\\"}");
    }

    static void visit(const std::string& node_id) {
        emit("VISIT_NODE", "{\\\"id\\\":\\\"" + node_id + "\\\"}");
    }

    static void leave(const std::string& node_id) {
        emit("LEAVE_NODE", "{\\\"id\\\":\\\"" + node_id + "\\\"}");
    }
};

class GraphTracer : public BaseTracer {
public:
    static void init() {
        emit("INIT", "{\\\"visualizerType\\\":\\\"GRAPH\\\"}");
    }

    static void addNode(const std::string& id, int val, int x = 0, int y = 0) {
        emit("ADD_NODE", "{\\\"id\\\":\\\"" + id + "\\\",\\\"val\\\":" + std::to_string(val) + ",\\\"x\\\":" + std::to_string(x) + ",\\\"y\\\":" + std::to_string(y) + "}");
    }

    static void addEdge(const std::string& from_id, const std::string& to_id) {
        emit("ADD_EDGE", "{\\\"from\\\":\\\"" + from_id + "\\\",\\\"to\\\":\\\"" + to_id + "\\\"}");
    }

    static void addEdge(const std::string& from_id, const std::string& to_id, double weight) {
        emit("ADD_EDGE", "{\\\"from\\\":\\\"" + from_id + "\\\",\\\"to\\\":\\\"" + to_id + "\\\",\\\"weight\\\":" + std::to_string(weight) + "}");
    }

    static void visit(const std::string& node_id) {
        emit("VISIT_NODE", "{\\\"id\\\":\\\"" + node_id + "\\\"}");
    }

    static void leave(const std::string& node_id) {
        emit("LEAVE_NODE", "{\\\"id\\\":\\\"" + node_id + "\\\"}");
    }
};

// Compatibility alias
class Tracer : public ArrayTracer {};
"""

JAVA_TRACER_SDK = """
public class Tracer extends ArrayTracer {}

class BaseTracer {
    protected static void emit(String type, String payloadJson) {
        System.out.print("__TRACER__:{\\"type\\":\\"" + type + "\\"");
        if (payloadJson != null && !payloadJson.isEmpty()) {
            System.out.print(",\\"payload\\":" + payloadJson);
        }
        System.out.println("}");
        System.out.flush();
    }

    public static void clear() {
        emit("CLEAR", null);
    }
}

class ArrayTracer extends BaseTracer {
    public static void init(int[] array) {
        StringBuilder arrStr = new StringBuilder("[");
        for (int i = 0; i < array.length; i++) {
            arrStr.append(array[i]);
            if (i < array.length - 1) arrStr.append(",");
        }
        arrStr.append("]");
        emit("INIT", "{\\"visualizerType\\":\\"1D_ARRAY\\",\\"array\\":" + arrStr.toString() + "}");
    }

    public static void compare(int i, int j) {
        emit("COMPARE", "[" + i + "," + j + "]");
    }

    public static void swap(int i, int j) {
        emit("SWAP", "[" + i + "," + j + "]");
    }

    public static void update(int index, int value) {
        emit("UPDATE", "{\\"index\\":" + index + ",\\"value\\":" + value + "}");
    }

    public static void setValue(int index, int value) {
        update(index, value);
    }

    public static void highlight(int[] indices, String tone) {
        StringBuilder indicesStr = new StringBuilder("[");
        for (int i = 0; i < indices.length; i++) {
            indicesStr.append(indices[i]);
            if (i < indices.length - 1) indicesStr.append(",");
        }
        indicesStr.append("]");
        emit("HIGHLIGHT", "{\\"indices\\":" + indicesStr.toString() + ",\\"tone\\":\\"" + tone + "\\"}");
    }

    public static void mark_answer(int index) {
        emit("MARK_ANSWER", String.valueOf(index));
    }

    public static void markAnswer(int index) {
        mark_answer(index);
    }
}

class TreeTracer extends BaseTracer {
    public static void init() {
        emit("INIT", "{\\"visualizerType\\":\\"TREE\\"}");
    }

    public static void addNode(String id, int val) {
        addNode(id, val, 0, 0);
    }

    public static void addNode(String id, int val, int x, int y) {
        emit("ADD_NODE", "{\\"id\\":\\"" + id + "\\",\\"val\\":" + val + ",\\"x\\":" + x + ",\\"y\\":" + y + "}");
    }

    public static void connect(String parentId, String childId) {
        emit("ADD_EDGE", "{\\"from\\":\\"" + parentId + "\\",\\"to\\":\\"" + childId + "\\"}");
    }

    public static void visit(String id) {
        emit("VISIT_NODE", "{\\"id\\":\\"" + id + "\\"}");
    }

    public static void leave(String id) {
        emit("LEAVE_NODE", "{\\"id\\":\\"" + id + "\\"}");
    }
}

class GraphTracer extends BaseTracer {
    public static void init() {
        emit("INIT", "{\\"visualizerType\\":\\"GRAPH\\"}");
    }

    public static void addNode(String id, int val) {
        addNode(id, val, 0, 0);
    }

    public static void addNode(String id, int val, int x, int y) {
        emit("ADD_NODE", "{\\"id\\":\\"" + id + "\\",\\"val\\":" + val + ",\\"x\\":" + x + ",\\"y\\":" + y + "}");
    }

    public static void addEdge(String fromId, String toId) {
        emit("ADD_EDGE", "{\\"from\\":\\"" + fromId + "\\",\\"to\\":\\"" + toId + "\\"}");
    }

    public static void addEdge(String fromId, String toId, double weight) {
        emit("ADD_EDGE", "{\\"from\\":\\"" + fromId + "\\",\\"to\\":\\"" + toId + "\\",\\"weight\\":" + weight + "}");
    }

    public static void visit(String id) {
        emit("VISIT_NODE", "{\\"id\\":\\"" + id + "\\"}");
    }

    public static void leave(String id) {
        emit("LEAVE_NODE", "{\\"id\\":\\"" + id + "\\"}");
    }
}
"""

async def run_in_sandbox(language: str, code: str, parsed_input: List[int]) -> str:
    """Executes the user's algorithm code inside a secure sandbox (temporary directory) with compiler limits."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Define files path
        if language == "python":
            # Prepend tracer, inject input_data, and write Python file
            full_code = PYTHON_TRACER_SDK + f"\ninput_data = {parsed_input}\n\n" + code
            
            # Detect function and call it if user didn't write execution call
            if "def " in code and not re.search(r'^\w+\(input_data\)', code, re.MULTILINE):
                match = re.search(r'^def\s+(\w+)\s*\(', code, re.MULTILINE)
                if match:
                    func_name = match.group(1)
                    full_code += f"\n\n{func_name}(input_data)\n"
            
            filepath = os.path.join(temp_dir, "script.py")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_code)

            # Exec Python script
            cmd = [sys.executable, "script.py"]
            return await execute_command(cmd, temp_dir)

        elif language in ("cpp", "c"):
            # Write Tracer.h
            with open(os.path.join(temp_dir, "Tracer.h"), "w", encoding="utf-8") as f:
                f.write(CPP_TRACER_SDK)

            # Inject includes and input_data
            cpp_arr = ", ".join(map(str, parsed_input))
            injections = (
                f'#include "Tracer.h"\n'
                f'#include <vector>\n'
                f'#include <string>\n'
                f'#include <iostream>\n'
                f'using namespace std;\n'
                f'vector<int> input_data = {{{cpp_arr}}};\n\n'
            )
            
            full_code = injections + code
            
            # Wrap standard templates inside main() if main doesn't exist
            if "int main(" not in code:
                # Detect top level function name
                match = re.search(r'^\s*(vector<int>|void|int|int\*)\s+(\w+)\s*\(', code, re.MULTILINE)
                if match:
                    func_name = match.group(2)
                    full_code += (
                        f"\n\nint main() {{\n"
                        f"    Tracer::init(input_data);\n"
                        f"    {func_name}(input_data);\n"
                        f"    Tracer::clear();\n"
                        f"    return 0;\n"
                        f"}}\n"
                    )
            
            filepath = os.path.join(temp_dir, "solution.cpp")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_code)

            # Compile C++ code
            compile_cmd = ["g++", "-O2", "solution.cpp", "-o", "solution"]
            try:
                await compile_command(compile_cmd, temp_dir, timeout=5.0, error_prefix="C++ 编译错误")
            except FileNotFoundError:
                raise APIException("C++ 编译失败: 未在系统 PATH 中找到 g++ 编译器。")

            # Run C++ compiled executable
            exe_path = "solution.exe" if sys.platform == "win32" else "./solution"
            return await execute_command([exe_path], temp_dir)

        elif language == "java":
            # Write Tracer.java next to solution
            with open(os.path.join(temp_dir, "Tracer.java"), "w", encoding="utf-8") as f:
                f.write(JAVA_TRACER_SDK)

            # Detect class name in java code
            match = re.search(r'class\s+(\w+)', code)
            class_name = match.group(1) if match else "Solution"
            
            java_arr = ", ".join(map(str, parsed_input))
            
            if "class " not in code:
                # Wrap custom java code inside class
                injections = (
                    f"import java.util.*;\n"
                    f"public class {class_name} {{\n"
                    f"    public static int[] input_data = new int[]{{{java_arr}}};\n"
                    f"    {code}\n"
                )
                
                # Check for method name to call in main
                method_match = re.search(r'(public|private|static|\s)\s+(\w+\[\]|void|int|int\[\])\s+(\w+)\s*\(', code)
                if method_match:
                    method_name = method_match.group(3)
                    injections += (
                        f"    public static void main(String[] args) {{\n"
                        f"        {class_name} solver = new {class_name}();\n"
                        f"        Tracer.init(input_data);\n"
                        f"        solver.{method_name}(input_data);\n"
                        f"        Tracer.clear();\n"
                        f"    }}\n"
                    )
                injections += "}\n"
                full_code = injections
            else:
                # Full class provided by user, inject static variable right after class opening brace
                class_pos = code.find(f"class {class_name}")
                if class_pos != -1:
                    brace_pos = code.find("{", class_pos)
                    if brace_pos != -1:
                        injection = f"\n    public static int[] input_data = new int[]{{{java_arr}}};\n"
                        full_code = code[:brace_pos+1] + injection + code[brace_pos+1:]
                    else:
                        full_code = code
                else:
                    full_code = code

            filepath = os.path.join(temp_dir, f"{class_name}.java")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_code)

            # Compile Java files
            compile_cmd = ["javac", f"{class_name}.java", "Tracer.java"]
            try:
                await compile_command(compile_cmd, temp_dir, timeout=5.0, error_prefix="Java 编译错误")
            except FileNotFoundError:
                raise APIException("Java 编译失败: 未在系统 PATH 中找到 javac 编译器。")

            # Run Java compiled solution
            return await execute_command(["java", class_name], temp_dir)

        else:
            raise APIException(f"不支持的语言沙箱: {language}")

def _run_subprocess(cmd: List[str], cwd: str, timeout: float) -> subprocess.CompletedProcess:
    """Synchronous subprocess runner — safe to call from any event loop via run_in_executor."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


async def compile_command(
    cmd: List[str],
    temp_dir: str,
    timeout: float,
    error_prefix: str,
) -> None:
    """Runs a compiler command in a thread pool (Windows-safe). Raises APIException on failure."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _run_subprocess, cmd, temp_dir, timeout)
    except subprocess.TimeoutExpired:
        raise APIException(f"{error_prefix}：编译超时。")
    if result.returncode != 0:
        error_msg = (
            result.stderr.decode("utf-8", errors="ignore")
            or result.stdout.decode("utf-8", errors="ignore")
        )
        raise APIException(f"{error_prefix}：\n{error_msg}")


async def execute_command(cmd: List[str], temp_dir: str) -> str:
    """Runs a subprocess command in a thread pool (Windows-safe) with timeout checks."""
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, _run_subprocess, cmd, temp_dir, 3.0)
    except subprocess.TimeoutExpired:
        raise APIException("代码执行超时 (最大执行时间限制为 3000ms)，可能包含死循环。")
    if result.returncode != 0:
        runtime_err = (
            result.stderr.decode("utf-8", errors="ignore")
            or result.stdout.decode("utf-8", errors="ignore")
        )
        raise APIException(f"运行时错误：\n{runtime_err}")
    return result.stdout.decode("utf-8", errors="ignore")

def parse_input_array(input_str: str) -> List[int]:
    """Parses input data string from user (e.g. '[5, 2, 8, 1, 3]') to list of integers."""
    try:
        parsed = json.loads(input_str)
        if not isinstance(parsed, list):
            raise APIException("运行数据格式不正确：必须为类似 [5, 2, 8, 1, 3] 的 JSON 数组。")
        return [int(x) for x in parsed]
    except Exception:
        raise APIException("运行数据格式不正确：必须为类似 [5, 2, 8, 1, 3] 的 JSON 数组。")

def assemble_payload(language: str, code: str, input_str: str, execution_stdout: str) -> Dict[str, Any]:
    """Processes tracer stdout output, extracts actions, simulates states, and assembles frontend visual steps."""
    # Find all actions starting with __TRACER__:
    action_lines = re.findall(r'^__TRACER__:(.+)$', execution_stdout, re.MULTILINE)
    
    actions = []
    for idx, line in enumerate(action_lines):
        try:
            actions.append(json.loads(line.strip()))
        except Exception:
            # Skip invalid JSON prints
            continue

    if not actions:
        raise APIException("代码运行完毕，但未产生任何可视化追踪记录。请检查是否调用了 Tracer SDK 方法。")

    # Detect visualizer type from first INIT action
    visualizer_type = "1D_ARRAY"
    if actions:
        first_payload = actions[0].get("payload")
        if isinstance(first_payload, dict):
            visualizer_type = first_payload.get("visualizerType", "1D_ARRAY").upper()
            if visualizer_type == "ARRAY":
                visualizer_type = "1D_ARRAY"

    # Initialise parser states
    current_array = []
    current_nodes = []
    current_edges = []
    steps = []
    
    # Process actions sequentially
    for idx, act in enumerate(actions):
        act_type = act.get("type", "").upper()
        payload = act.get("payload")
        
        step_id = f"step-{idx}"
        step_type = act_type.lower()
        targets = []
        description = ""
        step_payload = {}
        
        if act_type == "INIT":
            if visualizer_type == "1D_ARRAY":
                current_array = list(payload.get("array", []))
                description = f"初始化数组：{current_array}"
                step_payload = {
                    "array": list(current_array)
                }
            else:
                current_nodes = []
                current_edges = []
                description = f"初始化 {visualizer_type} 可视化结构。"
                step_payload = {
                    "nodes": [],
                    "edges": []
                }
        elif act_type == "COMPARE":
            # payload is [i, j]
            if isinstance(payload, list) and len(payload) == 2:
                i, j = payload[0], payload[1]
                targets = [f"bar-{i}", f"bar-{j}"]
                if i < len(current_array) and j < len(current_array):
                    description = f"比较下标 {i} (值 {current_array[i]}) 和下标 {j} (值 {current_array[j]})"
                else:
                    description = f"比较下标 {i} 和 {j}"
                step_payload = {
                    "array": list(current_array),
                    "indices": [i, j]
                }
        elif act_type == "HIGHLIGHT":
            # payload is {"indices": [...], "tone": "..."}
            indices = payload.get("indices", [])
            tone = payload.get("tone", "active")
            targets = [f"bar-{idx}" for idx in indices]
            description = f"高亮下标 {indices}，色调为 {tone}"
            step_payload = {
                "array": list(current_array),
                "indices": indices,
                "tone": tone
            }
        elif act_type == "SWAP":
            # payload is [i, j]
            if isinstance(payload, list) and len(payload) == 2:
                i, j = payload[0], payload[1]
                targets = [f"bar-{i}", f"bar-{j}"]
                
                # Perform the swap on our simulated array
                if i < len(current_array) and j < len(current_array):
                    val_i, val_j = current_array[i], current_array[j]
                    current_array[i], current_array[j] = val_j, val_i
                    description = f"交换下标 {i} (值 {val_i}) 和下标 {j} (值 {val_j}) 的位置"
                else:
                    description = f"交换下标 {i} 和 {j} 的位置"
                
                step_payload = {
                    "array": list(current_array),
                    "indices": [i, j],
                    "from": i,
                    "to": j
                }
        elif act_type in ("SET_VALUE", "UPDATE"):
            # payload is {"index": idx, "value": val}
            index = payload.get("index")
            value = payload.get("value")
            targets = [f"bar-{index}"]
            if index is not None and index < len(current_array):
                old_val = current_array[index]
                current_array[index] = value
                description = f"将下标 {index} 处的值从 {old_val} 更新为 {value}"
            else:
                description = f"将下标 {index} 处的值更新为 {value}"
            step_payload = {
                "array": list(current_array),
                "index": index,
                "value": value
            }
        elif act_type == "MARK_ANSWER":
            # payload is integer index
            sorted_idx = int(payload)
            targets = [f"bar-{sorted_idx}"]
            description = f"下标 {sorted_idx} 处的值已归位。"
            step_payload = {
                "array": list(current_array),
                "sortedIndex": sorted_idx
            }
            # map it to frontend expected mark-answer type
            step_type = "mark-answer"
        elif act_type == "ADD_NODE":
            # payload is {"id": node_id, "val": val, "x": x, "y": y}
            node_id = payload.get("id")
            val = payload.get("val")
            x = payload.get("x", 0)
            y = payload.get("y", 0)
            node = {
                "id": node_id,
                "label": str(val) if val is not None else "",
                "x": x,
                "y": y,
                "tone": "default"
            }
            # Avoid duplicate node id
            current_nodes = [n for n in current_nodes if n["id"] != node_id]
            current_nodes.append(node)
            targets = [node_id]
            description = f"在图中添加顶点 {node_id} (值 {val})"
            step_payload = {
                "nodes": list(current_nodes),
                "edges": list(current_edges)
            }
        elif act_type == "ADD_EDGE":
            # payload is {"from": from_id, "to": to_id, "weight": weight}
            from_id = payload.get("from")
            to_id = payload.get("to")
            weight = payload.get("weight")
            edge = {
                "from": from_id,
                "to": to_id,
                "tone": "default"
            }
            if weight is not None:
                edge["weight"] = weight
            # Avoid duplicate edges
            current_edges = [e for e in current_edges if not (e["from"] == from_id and e["to"] == to_id)]
            current_edges.append(edge)
            targets = [f"edge-{from_id}-{to_id}"]
            description = f"连接边 {from_id} -> {to_id}"
            if weight is not None:
                description += f" (权重: {weight})"
            step_payload = {
                "nodes": list(current_nodes),
                "edges": list(current_edges)
            }
        elif act_type == "VISIT_NODE":
            # payload is {"id": node_id}
            node_id = payload.get("id")
            for n in current_nodes:
                if n["id"] == node_id:
                    n["tone"] = "visited"
            targets = [node_id]
            description = f"访问顶点 {node_id}"
            step_payload = {
                "nodes": list(current_nodes),
                "edges": list(current_edges)
            }
        elif act_type == "LEAVE_NODE":
            # payload is {"id": node_id}
            node_id = payload.get("id")
            for n in current_nodes:
                if n["id"] == node_id:
                    n["tone"] = "default"
            targets = [node_id]
            description = f"离开顶点 {node_id}"
            step_payload = {
                "nodes": list(current_nodes),
                "edges": list(current_edges)
            }
        elif act_type == "CLEAR":
            description = "清除所有高亮/访问状态"
            if visualizer_type == "1D_ARRAY":
                step_payload = {
                    "array": list(current_array)
                }
            else:
                for n in current_nodes:
                    n["tone"] = "default"
                for e in current_edges:
                    e["tone"] = "default"
                step_payload = {
                    "nodes": list(current_nodes),
                    "edges": list(current_edges)
                }
        else:
            description = f"执行动作：{act_type}"
            if visualizer_type == "1D_ARRAY":
                step_payload = {
                    "array": list(current_array)
                }
            else:
                step_payload = {
                    "nodes": list(current_nodes),
                    "edges": list(current_edges)
                }

        steps.append({
            "id": step_id,
            "type": step_type,
            "targets": targets,
            "description": description,
            "codeLine": idx + 1,
            "duration": 500,
            "variables": {
                "array": list(current_array) if visualizer_type == "1D_ARRAY" else [],
                "nodes": list(current_nodes),
                "edges": list(current_edges)
            },
            "payload": step_payload
        })

    # Prepare response payload
    if visualizer_type == "1D_ARRAY":
        init_state = {
            "array": actions[0].get("payload", {}).get("array", []) if actions[0].get("type") == "INIT" else []
        }
        final_state = {
            "array": current_array
        }
    else:
        init_state = {
            "nodes": [],
            "edges": []
        }
        final_state = {
            "nodes": current_nodes,
            "edges": current_edges
        }

    return {
        "title": "算法运行可视化（沙箱动态生成）",
        "visualizerType": visualizer_type,
        "language": language,
        "code": code,
        "input": input_str,
        "initialState": init_state,
        "steps": steps,
        "finalState": final_state,
        "summary": f"动态执行成功，数据结构类型为 {visualizer_type}，共捕获到 {len(steps)} 个算法可视化操作步骤。"
    }

async def generate_visualization(language: str, code: str, input_str: str) -> Dict[str, Any]:
    """Top-level entry service coordinating input parsing, compilation, execution and payload generation."""
    parsed_input = parse_input_array(input_str)
    stdout_output = await run_in_sandbox(language, code, parsed_input)
    return assemble_payload(language, code, input_str, stdout_output)
