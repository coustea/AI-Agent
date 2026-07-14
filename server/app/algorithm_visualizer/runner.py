"""动态运行器：为沙箱执行生成 Python 入口点代码。

将用户代码与 JSON 输入数据桥接，自动解析参数、构建数据结构、调用入口函数。
"""

from __future__ import annotations

import ast
import json
import re
from typing import Dict, Any

from app.algorithm_visualizer.template_registry import (
    ENTRY_POINTS,
    build_default_data,
)


def find_entry_function(code: str, algorithm_key: str) -> str:
    """根据算法 key 在代码中查找入口函数名。"""
    try:
        tree = ast.parse(code)
        funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
        if not funcs:
            return ""

        # 优先使用注册表中的入口函数映射
        if algorithm_key in ENTRY_POINTS:
            mapped_func = ENTRY_POINTS[algorithm_key]
            if mapped_func in funcs:
                return mapped_func

        # 精确匹配
        if algorithm_key in funcs:
            return algorithm_key

        # 包含 "base" 的算法查找 xxx_operations
        if "base" in algorithm_key:
            prefix = algorithm_key.split("_")[0]
            op_name = f"{prefix}_operations"
            if op_name in funcs:
                return op_name

        # 模糊匹配：包含关键词或前缀
        clean_key = algorithm_key.replace("_base", "").replace("_dp", "")
        first_word = clean_key.split("_")[0]

        for f in funcs:
            if clean_key in f:
                return f
        for f in funcs:
            if f.startswith(first_word):
                return f

        # 回退：第一个非私有函数
        for f in funcs:
            if not f.startswith("_"):
                return f

        return funcs[0]
    except Exception:
        return ""


def find_tracer_var(code: str) -> str | None:
    """从 Python 代码中找到 tracer 变量名。"""
    tracer_classes = (
        "ArrayTracer", "StackTracer", "QueueTracer",
        "LinkedListTracer", "TreeTracer", "GraphTracer", "DpTableTracer"
    )
    for cls in tracer_classes:
        match = re.search(rf"(\w+)\s*=\s*{cls}\s*\(", code)
        if match:
            return match.group(1)
    return None


def append_dynamic_runner(code: str, algorithm_key: str) -> str:
    """在代码末尾追加动态执行块。

    生成的代码会：
    1. 从 stdin 读取 JSON 输入数据
    2. 合并默认数据
    3. 根据参数签名构建链表、树、图等数据结构
    4. 调用入口函数
    5. 调用 tracer.finish() 和 tracer.dump()
    """
    entry_function = find_entry_function(code, algorithm_key)
    tracer_var = find_tracer_var(code) or "tracer"
    default_data = build_default_data(algorithm_key)
    default_data_str = json.dumps(default_data, ensure_ascii=False)

    runner = f"""

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

        num_nodes = data.get("num_nodes", 0)
        if not num_nodes and "edges" in data:
            max_node = -1
            for edge in data["edges"]:
                if len(edge) >= 2:
                    max_node = max(max_node, edge[0], edge[1])
            num_nodes = max_node + 1

        _sandbox_root = None
        _sandbox_graph = None

        if any(p in ("root", "tree") for p in sig.parameters) and "arr" in data:
            _sandbox_root = _sandbox_build_tree(data["arr"])

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
    return code + runner