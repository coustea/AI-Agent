"""算法可视化沙箱执行服务。

执行流程：
1. 校验语言和算法模板是否匹配
2. 读取干净模板代码
3. LLM 自动插装（带缓存）
4. 自动追加 tracer.dump() 调用
5. 复制 SDK + 写入插装代码
6. 编译运行
7. 读取 trace.json
8. 校验 required_events
9. 返回事件流
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

import ast
from app.algorithm_visualizer.instrumenter import get_instrumenter
from app.algorithm_visualizer.template_registry import (
    get_algorithm_info,
    get_template_code,
    build_default_data,
)
from app.infra.logging import get_logger

logger = get_logger(__name__)

# Tracer SDK 文件目录
SDK_DIR = Path(__file__).parent / "tracer_sdks"


# 算法可视化运行自定义异常
class VisualizerRunError(Exception):
    """算法可视化运行错误。"""

    def __init__(self, message: str, error_type: str = "VISUALIZER_RUN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type


# 运行时编译/运行配置数据结构
@dataclass
class RuntimeConfig:
    sdk_source_filename: str
    sdk_target_filename: str
    user_code_filename: str
    compile_cmd: List[str]
    run_cmd: List[str]


# 沙箱执行入口：校验输入 → 插装 → 编译运行 → 解析 trace → 校验事件流
async def run_visualization_in_sandbox(
    language: str,
    code: str,
    algorithm: str,
    visualizer_type: str,
    domain: str,
    input_data: Optional[str] = None,
) -> Dict[str, Any]:
    """运行用户提交的可视化代码，返回 TraceEvent[]。

    如果 code 不包含 tracer 调用，自动进行 LLM 插装。
    如果 code 已包含 tracer 调用，直接执行。
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

    # ── 自动插装 ──────────────────────────────────────────────────
    instrumented_code = await _auto_instrument(
        code=code,
        algorithm=algorithm,
        algorithm_info=algorithm_info,
        language=language,
    )

    # ── 自动追加 tracer.dump() ────────────────────────────────────────
    final_code = _ensure_dump_call(instrumented_code, language, algorithm)

    # 创建临时沙箱目录，在其中编译执行代码
    with tempfile.TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)

        # 根据语言获取编译/运行配置
        runtime = build_runtime_config(language=language, code=final_code)

        # 复制 Tracer SDK 并写入用户代码到临时目录
        copy_sdk(runtime=runtime, run_dir=run_dir)
        write_user_code(runtime=runtime, run_dir=run_dir, code=final_code)

        # 对有编译需求的语言（C++/Java/C）执行编译
        if runtime.compile_cmd:
            compile_result = await run_process(
                cmd=runtime.compile_cmd,
                cwd=run_dir,
                input_data=None,
                timeout=15.0,
            )

            # 编译失败则抛出异常
            if compile_result["returncode"] != 0:
                raise VisualizerRunError(
                    "代码编译错误：\n" + pick_error_message(compile_result),
                    "COMPILE_ERROR",
                )

        # 执行用户代码（Python/JS 直接运行，C++/Java/C 运行编译产物）
        run_result = await run_process(
            cmd=runtime.run_cmd,
            cwd=run_dir,
            input_data=input_data,
            timeout=3.0,
        )

        # 运行时错误检查
        if run_result["returncode"] != 0:
            raise VisualizerRunError(
                "代码运行出错：\n" + pick_error_message(run_result),
                "RUNTIME_ERROR",
            )

        # 验证 trace.json 文件是否存在
        trace_file = run_dir / "trace.json"
        if not trace_file.exists():
            raise VisualizerRunError(
                "运行成功但未生成 trace.json。请确认代码来自算法可视化模板，并保留 tracer.finish() / vt_finish() / tracer.dump() 调用。",
                "TRACE_FILE_MISSING",
            )

        # 读取 trace.json 并检查文件大小
        raw = trace_file.read_text(encoding="utf-8")
        if len(raw) > 10 * 1024 * 1024:
            raise VisualizerRunError(
                "trace.json 文件过大（超过 10MB），可能存在异常。",
                "TRACE_JSON_INVALID",
            )

        # 解析 JSON 事件流
        try:
            events = json.loads(raw)
        except Exception as e:
            raise VisualizerRunError(
                f"trace.json 解析失败：{str(e)}",
                "TRACE_JSON_INVALID",
            ) from e

        # 校验事件流非空
        if not isinstance(events, list) or len(events) == 0:
            raise VisualizerRunError(
                "可视化追踪事件流为空，没有录制到有效步骤。",
                "TRACE_EVENT_EMPTY",
            )

        # 兼容 visualizer_type 字段命名并校验事件完整性
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


# ---------------------------------------------------------------------------
# 快速路径：预插装模板
# ---------------------------------------------------------------------------

# _try_pre_instrumented 已删除，改由 CodeInstrumenter 统一缓存管理


# ---------------------------------------------------------------------------
# 自动插装
# ---------------------------------------------------------------------------

async def _auto_instrument(
    code: str,
    algorithm: str,
    algorithm_info: dict[str, Any],
    language: str,
) -> str:
    """如果代码不包含 tracer 调用，自动进行 LLM 插装。

    对于模板代码（干净模板），直接从缓存或预插装结果获取。
    对于用户自定义代码（无 tracer），调用 LLM 自动插装。

    Returns:
        插装后的代码（或原始代码，如果已包含 tracer 或插装失败）
    """
    # 检测代码是否已包含 tracer 调用
    if _has_tracer_calls(code, language):
        logger.info("[Visualizer] 代码已包含 tracer 调用，跳过插装: algorithm=%s", algorithm)
        return code

    # 仅 Python 支持自动插装
    if language != "python":
        logger.warning(
            "[Visualizer] 代码缺少 tracer 调用，但 %s 暂不支持自动插装: algorithm=%s",
            language,
            algorithm,
        )
        return code

    # 判断是否为模板代码（与注册表中的干净模板匹配）
    clean_template_code = get_template_code(algorithm, language)
    is_template_code = (code.strip() == clean_template_code.strip())

    if is_template_code:
        # 模板代码：优先尝试读取预插装模板文件
        pre_instrumented = _try_pre_instrumented_template(algorithm, language)
        if pre_instrumented:
            logger.info("[Visualizer] 模板代码使用预插装版本: algorithm=%s", algorithm)
            return pre_instrumented

        # 没有预插装文件，尝试缓存
        instrumenter = get_instrumenter()
        result = await instrumenter.instrument(
            clean_code=code,
            algorithm_name=algorithm,
            visualizer_type=algorithm_info.get("visualizer_type", "array"),
            required_events=algorithm_info.get("required_events", []),
            language=language,
        )
        if result.error:
            logger.error(
                "[Visualizer] 模板自动插装失败: algorithm=%s error=%s",
                algorithm,
                result.error,
            )
            raise VisualizerRunError(
                f"模板插装失败：{result.error}。",
                "INSTRUMENTATION_FAILED",
            )
        logger.info(
            "[Visualizer] 模板缓存插装成功: algorithm=%s cached=%s",
            algorithm,
            result.cached,
        )
        return result.code

    # 用户自定义代码：调用插装引擎
    instrumenter = get_instrumenter()
    result = await instrumenter.instrument(
        clean_code=code,
        algorithm_name=algorithm,
        visualizer_type=algorithm_info.get("visualizer_type", "array"),
        required_events=algorithm_info.get("required_events", []),
        language=language,
    )

    if result.error:
        logger.error(
            "[Visualizer] 自定义代码自动插装失败: algorithm=%s error=%s",
            algorithm,
            result.error,
        )
        raise VisualizerRunError(
            f"自动插装失败：{result.error}。请手动添加 tracer 调用后重试。",
            "INSTRUMENTATION_FAILED",
        )

    logger.info(
        "[Visualizer] 自定义代码自动插装成功: algorithm=%s cached=%s",
        algorithm,
        result.cached,
    )
    return result.code


def _try_pre_instrumented_template(algorithm: str, language: str) -> str | None:
    """尝试读取预插装模板文件。

    模板目录结构：
    templates/{domain}/{algorithm}/python_instrumented.py

    Returns:
        预插装代码，或 None（文件不存在）
    """
    try:
        algorithm_info = get_algorithm_info(algorithm)
        domain = algorithm_info["domain"]
        filename = f"{language}_instrumented.py"

        filepath = SDK_DIR.parent / "templates" / domain / algorithm / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("[Visualizer] 读取预插装模板失败: algorithm=%s error=%s", algorithm, e)

    return None


def _has_tracer_calls(code: str, language: str) -> bool:
    """检测代码是否已包含 tracer 调用。"""
    if language == "python":
        # 检查 Python tracer 导入
        return bool(
            re.search(r"from\s+visual_tracer\s+import", code)
            or re.search(r"import\s+visual_tracer", code)
        )

    return False


_ENTRY_FUNCTIONS = {
    # 1. Base Data Structures
    "array_base": "array_operations",
    "linked_list_base": "linked_list_operations",
    "stack_base": "stack_operations",
    "queue_base": "queue_operations",
    "hash_table_base": "hash_table_operations",
    "heap_base": "heap_sort",
    
    # 2. Sorting
    "bubble_sort": "bubble_sort_with_bounds",
    "selection_sort": "selection_sort",
    "insertion_sort": "insertion_sort",
    "shell_sort": "shell_sort",
    "quick_sort": "quick_sort",
    "merge_sort": "merge_sort_wrapper",
    "heap_sort": "heap_sort",
    "counting_sort": "counting_sort",
    "bucket_sort": "bucket_sort",
    "radix_sort": "radix_sort",
    
    # 3. Searching
    "sequential_search": "sequential_search",
    "binary_search": "binary_search",
    "interpolation_search": "interpolation_search",
    "fibonacci_search": "fibonacci_search",
    "hash_search": "hash_search",
    
    # 4. Linear Structures
    "double_pointers": "reverse_array",
    "sliding_window": "max_subarray_sum",
    "monotonic_stack": "next_greater_elements",
    "monotonic_queue": "max_sliding_window",
    "prefix_sum": "prefix_sum_operations",
    "difference_array": "range_updates",
    
    # 5. Trees
    "binary_tree_traverse": "preorder_traversal",
    "binary_tree_recursion": "max_depth",
    "bst": "bst_operations",
    "heap_tree": "build_max_heap",
    "trie_tree": "trie_operations",
    "segment_tree": "segment_tree_operations",
    "fenwick_tree": "fenwick_tree_operations",
    
    # 6. Graphs
    "graph_representation": "build_graph",
    "graph_bfs": "bfs_all_components",
    "graph_dfs": "dfs",
    "shortest_path": "dijkstra",
    "topological_sort": "topological_sort",
    "mst_kruskal": "kruskal",
    "dsu_union": "dsu_operations",
    
    # 7. Strings
    "string_match_naive": "naive_match",
    "kmp_match": "kmp_search",
    "rabin_karp": "rabin_karp",
    "trie_string_search": "trie_search",
    "palindrome_check": "is_palindrome",
    
    # 8. Recursion & Backtrack
    "recursion_fib": "fib_trace",
    "permutations": "permute",
    "subsets": "subsets",
    "combinations": "combination_sum",
    "n_queens": "solve_n_queens",
    "maze_search": "solve_maze",
    
    # 9. DP
    "dp_fibonacci": "fibonacci",
    "one_d_dp": "climb_stairs",
    "two_d_dp": "min_path_sum",
    "knapsack_dp": "knapsack",
    "interval_dp": "longest_palindrome_subseq",
    "tree_dp": "rob",
    "state_compress_dp": "tsp",
    
    # 10. Greedy
    "interval_greedy": "activity_selection",
    "stock_problem": "max_profit_single",
    "jump_game": "can_jump",
    "huffman_coding": "build_huffman_tree",
    "covering_problem": "min_interval_cover",
    
    # 11. Divide & Conquer
    "binary_divide": "binary_search_first",
    "merge_divide": "merge_sort",
    "quick_partition": "partition",
    "recursive_divide": "tower_of_hanoi",
    
    # 12. Bit Manipulation
    "basic_bit": "count_bits",
    "xor_trick": "find_single_number",
    "bit_mask": "perm_to_mask",
    "subset_enum": "enumerate_subsets",
    
    # 13. Math
    "gcd_euclidean": "gcd",
    "quick_power": "quick_pow",
    "prime_sieve": "sieve_of_eratosthenes",
    "combination_num": "pascals_triangle",
    "mod_arithmetic": "mod_pow",
}


def find_entry_function(code: str, algorithm_key: str) -> str:
    """Find the main entry function in the python code based on the algorithm key."""
    try:
        tree = ast.parse(code)
        funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        if not funcs:
            return ""
            
        # 0. Check pre-defined functions map
        if algorithm_key in _ENTRY_FUNCTIONS:
            mapped_func = _ENTRY_FUNCTIONS[algorithm_key]
            if mapped_func in funcs:
                return mapped_func
                
        # 1. Exact match
        if algorithm_key in funcs:
            return algorithm_key
            
        # 2. Key contains "base" -> search for key_operations (e.g. stack_base -> stack_operations)
        if "base" in algorithm_key:
            prefix = algorithm_key.split("_")[0]
            op_name = f"{prefix}_operations"
            if op_name in funcs:
                return op_name
                
        # 3. Fuzzy prefix/contains match (e.g. bubble_sort -> bubble_sort_with_bounds)
        clean_key = algorithm_key.replace("_base", "").replace("_dp", "")
        first_word = clean_key.split("_")[0]
        
        # Look for a function containing clean_key
        for f in funcs:
            if clean_key in f:
                return f
        # Look for a function starting with first_word
        for f in funcs:
            if f.startswith(first_word):
                return f
                
        # 4. Fallback: the first defined function that doesn't start with "_"
        for f in funcs:
            if not f.startswith("_"):
                return f
                
        return funcs[0]
    except Exception:
        pass
    return ""


def append_dynamic_runner(code: str, algorithm_key: str, default_data: dict) -> str:
    """Append a dynamic sys.stdin parser and execution block to Python code."""
    entry_function = find_entry_function(code, algorithm_key)
    tracer_var = _find_tracer_var(code) or "tracer"
    
    # Format the default data JSON
    import json
    default_data_str = json.dumps(default_data, ensure_ascii=False)
    
    runner_template = f"""

# Dynamic Entry Point Appended by Sandbox
if __name__ == "__main__":
    import sys
    import json
    
    null = None
    true = True
    false = False
    
    def _sandbox_build_linked_list(arr):
        if not arr: return None
        node_cls = globals().get("ListNode") or globals().get("Node")
        if not node_cls:
            class ListNode:
                def __init__(self, val=0, next=None):
                    self.val = val
                    self.next = next
            node_cls = ListNode
        head = node_cls(arr[0])
        curr = head
        for val in arr[1:]:
            curr.next = node_cls(val)
            curr = curr.next
        return head

    def _sandbox_build_tree(arr):
        if not arr: return None
        node_cls = globals().get("TreeNode") or globals().get("Node")
        if not node_cls:
            class TreeNode:
                def __init__(self, val=0, left=None, right=None):
                    self.val = val
                    self.left = left
                    self.right = right
            node_cls = TreeNode
        nodes = [node_cls(val) if val is not None else None for val in arr]
        if not nodes: return None
        queue = [nodes[0]]
        i = 1
        while queue and i < len(nodes):
            curr = queue.pop(0)
            if curr:
                if i < len(nodes):
                    curr.left = nodes[i]
                    if nodes[i]: queue.append(nodes[i])
                    i += 1
                if i < len(nodes):
                    curr.right = nodes[i]
                    if nodes[i]: queue.append(nodes[i])
                    i += 1
        return nodes[0]

    def _sandbox_build_graph(num_nodes, edges, is_directed=False):
        weighted = False
        if edges and len(edges[0]) > 2:
            weighted = True
        
        graph = {{i: [] for i in range(num_nodes)}}
        for edge in edges:
            if len(edge) >= 2:
                u, v = edge[0], edge[1]
                w = edge[2] if len(edge) > 2 else 1
                if weighted:
                    graph[u].append((v, w))
                    if not is_directed:
                        graph[v].append((u, w))
                else:
                    graph[u].append(v)
                    if not is_directed:
                        graph[v].append(u)
        return graph

    try:
        input_str = sys.stdin.read().strip()
        input_data = json.loads(input_str) if input_str else {{}}
    except Exception:
        input_data = {{}}

    default_data = {default_data_str}
    data = {{**default_data, **input_data}}
    
    if "nodes" in globals() and isinstance(globals()["nodes"], list):
        class DynamicList(list):
            def __getitem__(self, index):
                if isinstance(index, int):
                    while index >= len(self):
                        self.append({{"id": f"node-{{len(self)}}", "label": f"State {{len(self)}}", "tone": "default"}})
                return super().__getitem__(index)
        globals()["nodes"] = DynamicList(globals()["nodes"])
    
    entry_name = "{entry_function}"
    func = globals().get(entry_name)
    if not func:
        import inspect
        funcs = [obj for name, obj in globals().items() if inspect.isfunction(obj) and not name.startswith("_")]
        if funcs:
            funcs.sort(key=lambda f: f.__code__.co_firstlineno)
            func = funcs[-1]

    if func:
        import inspect
        sig = inspect.signature(func)
        kwargs = {{}}
        aliases = {{
            "universe": ["states_needed", "arr", "nums"],
            "subsets": ["stations"],
            "points": ["arr", "nums"],
            "interval_len": ["k", "radius"],
            "radius": ["k", "interval_len"],
            "s": ["string", "text", "pattern", "s"],
            "source": ["start", "source_node", "source", "node"],
            "node": ["start", "source_node", "source", "node"],
            "candidates": ["arr", "nums", "candidates"],
            "data": ["arr", "nums", "data"],
            "m": ["mod", "m"],
        }}
        
        # Determine num_nodes if needed
        num_nodes = data.get("num_nodes", 0)
        if not num_nodes and "edges" in data:
            max_node = -1
            for edge in data["edges"]:
                if len(edge) >= 2:
                    max_node = max(max_node, edge[0], edge[1])
            num_nodes = max_node + 1
            
        _sandbox_root = None
        _sandbox_graph = None
        
        # Build tree root if root/tree in parameters
        if any(p in ("root", "tree") for p in sig.parameters) and "arr" in data:
            _sandbox_root = _sandbox_build_tree(data["arr"])
            
        # Build graph if graph data present
        if "edges" in data or "graph" in globals():
            is_directed = (entry_name in ("dijkstra", "shortest_path"))
            if "edges" in data:
                _sandbox_graph = _sandbox_build_graph(num_nodes, data["edges"], is_directed)
            else:
                _sandbox_graph = globals().get("graph")

        for param_name, param in sig.parameters.items():
            if param_name in ("root", "tree"):
                kwargs[param_name] = _sandbox_root
            elif param_name in ("head", "node") and "arr" in data:
                kwargs[param_name] = _sandbox_build_linked_list(data["arr"])
            elif param_name == "graph":
                kwargs[param_name] = _sandbox_graph
            elif param_name in data:
                kwargs[param_name] = data[param_name]
            else:
                matched = False
                for alias in aliases.get(param_name, []):
                    if alias in data:
                        kwargs[param_name] = data[alias]
                        matched = True
                        break
                if not matched and param.default is not inspect.Parameter.empty:
                    pass
                elif not matched and param_name == "arr" and "nums" in data:
                    kwargs[param_name] = data["nums"]
                elif not matched and param_name == "nums" and "arr" in data:
                    kwargs[param_name] = data["arr"]
                elif not matched and param_name in ("lo", "left"):
                    kwargs[param_name] = 0
                elif not matched and param_name in ("hi", "right") and "arr" in data:
                    kwargs[param_name] = len(data["arr"]) - 1
                elif not matched and param_name == "gaps":
                    kwargs[param_name] = [4, 2, 1]
                elif not matched and param_name == "n" and "arr" in data:
                    kwargs[param_name] = len(data["arr"])
                elif not matched and param_name in globals():
                    kwargs[param_name] = globals()[param_name]

        # Rebuild tree visualizer states if needed
        if "build_id_map" in globals() and _sandbox_root:
            if "_node_id_map" in globals():
                g = globals()["_node_id_map"]
                if isinstance(g, dict): g.clear()
            if "_idx" in globals():
                g = globals()["_idx"]
                if isinstance(g, list) and len(g) > 0: g[0] = 0
            globals()["build_id_map"](_sandbox_root)
            
        if "build_tree_nodes" in globals() and _sandbox_root and "{tracer_var}" in globals():
            if "_counter" in globals():
                g = globals()["_counter"]
                if isinstance(g, list) and len(g) > 0: g[0] = 0
            if "_nodes" in globals() and isinstance(globals()["_nodes"], list):
                globals()["_nodes"].clear()
                globals()["build_tree_nodes"](_sandbox_root)
                globals()["{tracer_var}"].init_tree(globals()["_nodes"])
            else:
                nodes_list = []
                try:
                    globals()["build_tree_nodes"](_sandbox_root, nodes_list)
                    globals()["{tracer_var}"].init_tree(nodes_list)
                except Exception:
                    try:
                        globals()["build_tree_nodes"](_sandbox_root)
                    except Exception:
                        pass
                        
        # Rebuild graph visualizer if GraphTracer and graph present
        graph_tracer = None
        for name, obj in list(globals().items()):
            if obj.__class__.__name__ == "GraphTracer":
                graph_tracer = obj
                break
        if graph_tracer is not None and _sandbox_graph is not None:
            nodes_list = []
            for i in range(num_nodes):
                node_edges = []
                for item in _sandbox_graph[i]:
                    if isinstance(item, tuple):
                        node_edges.append({{"to": str(item[0]), "weight": item[1]}})
                    else:
                        node_edges.append({{"to": str(item)}})
                label = str(i)
                if "labels" in globals():
                    labels_obj = globals()["labels"]
                    if isinstance(labels_obj, dict) and i in labels_obj:
                        label = labels_obj[i]
                    elif isinstance(labels_obj, list) and i < len(labels_obj):
                        label = labels_obj[i]
                nodes_list.append({{"id": str(i), "label": label, "edges": node_edges}})
            graph_tracer.init_graph(nodes_list)

        func(**kwargs)
        
    # Dynamically find the active tracer instance
    active_tracer = None
    for name, obj in list(globals().items()):
        if hasattr(obj, "_events") and hasattr(obj, "finish") and hasattr(obj, "dump"):
            if len(obj._events) > 0:
                active_tracer = obj
                break
                
    if not active_tracer:
        for name, obj in list(globals().items()):
            if hasattr(obj, "_events") and hasattr(obj, "finish") and hasattr(obj, "dump"):
                active_tracer = obj
                break
                
    if active_tracer:
        try:
            active_tracer.finish()
        except Exception:
            pass
        active_tracer.dump()
"""
    return code + runner_template


def _ensure_dump_call(code: str, language: str, algorithm_key: str) -> str:
    """确保代码末尾有动态执行流及 dump 调用。"""
    if language != "python":
        return code
        
    default_data = build_default_data(algorithm_key)
    return append_dynamic_runner(code, algorithm_key, default_data)


def _find_tracer_var(code: str) -> str | None:
    """从 Python 代码中找到 tracer 变量名。"""
    tracer_classes = ("ArrayTracer", "StackTracer", "QueueTracer",
                      "LinkedListTracer", "TreeTracer", "GraphTracer", "DpTableTracer")
    for cls in tracer_classes:
        match = re.search(rf"(\w+)\s*=\s*{cls}\s*\(", code)
        if match:
            return match.group(1)
    return None


# ---------------------------------------------------------------------------
# 运行时配置
# ---------------------------------------------------------------------------

def build_runtime_config(language: str, code: str) -> RuntimeConfig:
    """根据语言构建编译和运行配置。

    当前仅支持 Python。未来扩展时，在此添加其他语言的配置：
    - java: compile_cmd=['javac', 'Main.java'], run_cmd=['java', 'Main']
    - cpp: compile_cmd=['g++', '-o', 'main', 'main.cpp'], run_cmd=['./main']
    - javascript: run_cmd=['node', 'main.js'] (无需编译)
    """

    if language == "python":
        return RuntimeConfig(
            sdk_source_filename="python_tracer.py",
            sdk_target_filename="visual_tracer.py",
            user_code_filename="main.py",
            compile_cmd=[],  # Python 无需编译
            run_cmd=[sys.executable, "main.py"],
        )

    # 未来扩展其他语言时，在此添加 elif 分支
    # elif language == "java":
    #     ...
    # elif language == "cpp":
    #     ...

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
