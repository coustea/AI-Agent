"""Python VisualTracer SDK — 生成 TraceEvent JSON 事件流。
 * python_adapter.py 写入临时目录与用户代码一起执行。
 * 替代旧 PYTHON_TRACER_SDK 字符串常量。
 * 输出 trace.json 而非 __TRACER__: stdout 协议。"""

import copy
import json
from typing import Any, Dict, List, Optional


class VisualTracer:
    """Multi-domain algorithm visualization tracer for Python."""

    def __init__(self, visualizer_type: str = "array") -> None:
        self._events: List[Dict[str, Any]] = []
        self._step: int = 0
        self._domain: str = "data_structure"
        self._visualizer_type: str = visualizer_type

    def _record(
        self,
        event_type: str,
        state_structure: Dict[str, Any],
        targets: Optional[List[Any]] = None,
        message: Optional[str] = None,
        line: Optional[int] = None,
        formula: Optional[str] = None,
    ) -> None:
        event: Dict[str, Any] = {
            "id": f"evt-{self._step}",
            "step": self._step,
            "domain": self._domain,
            "visualizerType": self._visualizer_type,
            "type": event_type,
            "state": {"structure": copy.deepcopy(state_structure)},
            "targets": copy.deepcopy(targets) if targets else [],
            "message": message,
            "line": line,
            "formula": formula,
        }
        self._events.append(event)
        self._step += 1

    @property
    def events(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._events)

    def snapshot(
        self,
        event_type: str,
        state_structure: Dict[str, Any],
        targets: Optional[List[Any]] = None,
        message: Optional[str] = None,
        line: Optional[int] = None,
        formula: Optional[str] = None,
    ) -> None:
        self._record(
            event_type,
            state_structure,
            targets=targets,
            message=message,
            line=line,
            formula=formula,
        )

    def to_payload(self) -> List[Dict[str, Any]]:
        return self.events

    def dump(self, filepath: str = "trace.json") -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._events, f, ensure_ascii=False, indent=2)


class ArrayTracer(VisualTracer):
    """Array algorithm tracer — bubble sort, selection sort, etc."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "array"
        self._current_array: List[Any] = []

    def init_array(self, array: List[Any], line: Optional[int] = None) -> None:
        self._current_array = list(array)
        self._record("init_array", {"array": list(self._current_array)},
                      message=f"初始化数组：{list(self._current_array)}", line=line)

    def compare(self, i: int, j: int, line: Optional[int] = None) -> None:
        left = self._current_array[i] if i < len(self._current_array) else "?"
        right = self._current_array[j] if j < len(self._current_array) else "?"
        self._record("compare", {"array": list(self._current_array)},
                      targets=[i, j], message=f"比较 nums[{i}]={left} 和 nums[{j}]={right}", line=line)

    def swap(self, i: int, j: int, line: Optional[int] = None) -> None:
        if i < len(self._current_array) and j < len(self._current_array):
            self._current_array[i], self._current_array[j] = self._current_array[j], self._current_array[i]
        self._record("swap", {"array": list(self._current_array)},
                      targets=[i, j], message=f"交换位置 {i} 和 {j}", line=line)

    def assign(self, index: int, value: Any, line: Optional[int] = None) -> None:
        if index < len(self._current_array):
            self._current_array[index] = value
        self._record("assign", {"array": list(self._current_array)},
                      targets=[index], message=f"赋值 nums[{index}] = {value}", line=line)

    def mark_sorted(self, index: int, line: Optional[int] = None) -> None:
        self._record("mark_sorted", {"array": list(self._current_array)},
                      targets=[index], message=f"位置 {index} 已归位", line=line)

    def move_pointer(self, pointers: Dict[str, int], line: Optional[int] = None) -> None:
        self._record("move_pointer", {"array": list(self._current_array), "pointers": pointers},
                      targets=list(pointers.values()), message=f"移动指针：{pointers}", line=line)

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"array": list(self._current_array)}, message="排序完成", line=line)


class StackTracer(VisualTracer):
    """Stack algorithm tracer — bracket matching, etc."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "stack-queue"
        self._items: List[Dict[str, Any]] = []

    def _snapshot(self) -> List[Dict[str, Any]]:
        return [{"id": f"item-{i}", "label": str(it["value"]), "tone": it.get("tone", "default")}
                for i, it in enumerate(self._items)]

    def init_stack(self, *args, **kwargs) -> None:
        line = kwargs.get("line")
        items = None
        for arg in args:
            if isinstance(arg, list):
                items = arg
            elif isinstance(arg, int) and line is None:
                line = arg
        self._items = []
        if items:
            for val in items:
                self._items.append({"value": val, "tone": "default"})
        self._record("init_stack", {"mode": "stack", "items": self._snapshot()}, message="初始化栈结构", line=line)

    def push(self, value: Any, line: Optional[int] = None) -> None:
        self._items.append({"value": value, "tone": "default"})
        self._record("push", {"mode": "stack", "items": self._snapshot()},
                      targets=[len(self._items) - 1], message=f"入栈：{value}", line=line)

    def pop(self, *args, line: Optional[int] = None) -> Any:
        if self._items:
            item = self._items.pop()
            self._record("pop", {"mode": "stack", "items": self._snapshot()}, message=f"出栈：{item['value']}", line=line)
            return item["value"]
        return None

    def highlight_input(self, input_index: int, line: Optional[int] = None) -> None:
        self._record("highlight_input", {"mode": "stack", "items": self._snapshot(), "inputIndex": input_index},
                      targets=[input_index], message=f"处理输入位置 {input_index}", line=line)

    def finish(self, line: Optional[int] = None) -> None:
        matched = len(self._items) == 0
        self._record("finish", {"mode": "stack", "items": self._snapshot()},
                      message="括号匹配成功！" if matched else "括号不匹配", line=line)


class QueueTracer(VisualTracer):
    """Queue algorithm tracer — queue simulation, BFS, etc."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "stack-queue"
        self._items: List[Dict[str, Any]] = []

    def _snapshot(self) -> List[Dict[str, Any]]:
        return [{"id": f"item-{i}", "label": str(it["value"]), "tone": it.get("tone", "default")}
                for i, it in enumerate(self._items)]

    def init_queue(self, *args, **kwargs) -> None:
        line = kwargs.get("line")
        items = None
        for arg in args:
            if isinstance(arg, list):
                items = arg
            elif isinstance(arg, int) and line is None:
                line = arg
        self._items = []
        if items:
            for val in items:
                self._items.append({"value": val, "tone": "default"})
        self._record("init_queue", {"mode": "queue", "items": self._snapshot()}, message="初始化队列结构", line=line)

    def enqueue(self, value: Any, line: Optional[int] = None) -> None:
        self._items.append({"value": value, "tone": "default"})
        self._record("enqueue", {"mode": "queue", "items": self._snapshot()},
                      targets=[len(self._items) - 1], message=f"入队：{value}", line=line)

    def dequeue(self, *args, line: Optional[int] = None) -> Any:
        if self._items:
            item = self._items.pop(0)
            self._record("dequeue", {"mode": "queue", "items": self._snapshot()}, message=f"出队：{item['value']}", line=line)
            return item["value"]
        return None

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"mode": "queue", "items": self._snapshot()}, message="队列模拟完成", line=line)


class LinkedListTracer(VisualTracer):
    """Linked list algorithm tracer."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "linked-list"
        self._nodes: List[Dict[str, Any]] = []
        self._pointers: List[Dict[str, Any]] = []

    def init_list(self, nodes: List[Dict[str, Any]], pointers: Optional[List[Dict[str, Any]]] = None, line: Optional[int] = None) -> None:
        self._nodes = [dict(n) for n in nodes]
        self._pointers = [dict(p) for p in pointers] if pointers else []
        self._record("init_list", {"nodes": list(self._nodes), "pointers": list(self._pointers)},
                      message="初始化链表", line=line)

    def set_visited(self, node_index: int, visited: bool = True, line: Optional[int] = None) -> None:
        if 0 <= node_index < len(self._nodes):
            self._nodes[node_index]["tone"] = "visited" if visited else "default"
        self._record("set_visited", {"nodes": list(self._nodes), "pointers": list(self._pointers)},
                      targets=[node_index], message=f"访问节点: {self._nodes[node_index]['label']}", line=line)

    def move_pointer(self, label: str, node_index: int, tone: str = "accent", line: Optional[int] = None) -> None:
        self._pointers = [p for p in self._pointers if p["label"] != label]
        if node_index is not None:
            self._pointers.append({"label": label, "nodeIndex": node_index, "tone": tone})
        self._record("move_pointer", {"nodes": list(self._nodes), "pointers": list(self._pointers)},
                      targets=[node_index] if node_index is not None else [],
                      message=f"移动指针 {label} 指向节点 {node_index}", line=line)

    def add_node(self, label: str, tone: str = "default", line: Optional[int] = None) -> int:
        node_id = f"node-{len(self._nodes)}"
        self._nodes.append({"id": node_id, "label": label, "tone": tone})
        node_idx = len(self._nodes) - 1
        self._record("add_node", {"nodes": list(self._nodes), "pointers": list(self._pointers)},
                      targets=[node_idx], message=f"添加节点 {label}", line=line)
        return node_idx

    def remove_node(self, node_index: int, line: Optional[int] = None) -> None:
        if 0 <= node_index < len(self._nodes):
            removed = self._nodes.pop(node_index)
            # Shift nodeIndex for all pointers referencing indexes after node_index
            for p in self._pointers:
                idx = p.get("nodeIndex")
                if idx is not None and idx > node_index:
                    p["nodeIndex"] = idx - 1
                elif idx == node_index:
                    p["nodeIndex"] = None
            self._pointers = [p for p in self._pointers if p.get("nodeIndex") is not None]
            self._record("remove_node", {"nodes": list(self._nodes), "pointers": list(self._pointers)},
                          message=f"删除节点 {removed['label']}", line=line)

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"nodes": list(self._nodes), "pointers": list(self._pointers)}, message="链表操作完成", line=line)


class TreeTracer(VisualTracer):
    """Tree algorithm tracer."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "tree"
        self._nodes: List[Dict[str, Any]] = []

    def init_tree(self, nodes: List[Dict[str, Any]], line: Optional[int] = None) -> None:
        self._nodes = [dict(n) for n in nodes]
        self._record("init_tree", {"nodes": list(self._nodes)}, message="初始化树结构", line=line)

    def visit_node(self, node_id: str, visited: bool = True, line: Optional[int] = None) -> None:
        for node in self._nodes:
            if node["id"] == node_id:
                node["tone"] = "visited" if visited else "default"
                self._record("visit_node", {"nodes": list(self._nodes)}, targets=[node_id], message=f"访问节点: {node['label']}", line=line)
                break

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"nodes": list(self._nodes)}, message="树操作完成", line=line)


class GraphTracer(VisualTracer):
    """Graph algorithm tracer."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "graph"
        self._nodes: List[Dict[str, Any]] = []

    def init_graph(self, nodes: List[Dict[str, Any]], line: Optional[int] = None) -> None:
        self._nodes = [dict(n) for n in nodes]
        self._record("init_graph", {"nodes": list(self._nodes)}, message="初始化图结构", line=line)

    def visit_node(self, node_id: str, visited: bool = True, line: Optional[int] = None) -> None:
        for node in self._nodes:
            if node["id"] == node_id:
                node["tone"] = "visited" if visited else "default"
                self._record("visit_node", {"nodes": list(self._nodes)}, targets=[node_id], message=f"访问节点: {node['label']}", line=line)
                break

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"nodes": list(self._nodes)}, message="图操作完成", line=line)


class DpTableTracer(VisualTracer):
    """DP table algorithm tracer."""

    def __init__(self) -> None:
        super().__init__()
        self._visualizer_type = "dp-table"
        self._headers: List[str] = []
        self._values: List[List[Any]] = []
        self._highlighted: List[Dict[str, Any]] = []

    def init_table(self, *args, **kwargs) -> None:
        line = kwargs.get("line")
        headers = kwargs.get("headers")
        fill_value = kwargs.get("fill_value", 0)
        rows = kwargs.get("rows")
        cols = kwargs.get("cols")
        
        positional_ints = []
        for arg in args:
            if isinstance(arg, list):
                headers = arg
            elif isinstance(arg, int):
                positional_ints.append(arg)
            elif arg is not None:
                fill_value = arg
                
        if len(positional_ints) == 3 and line is None:
            line = positional_ints[2]
            positional_ints = positional_ints[:2]
            
        if rows is None and len(positional_ints) > 0:
            rows = positional_ints[0]
            positional_ints = positional_ints[1:]
            
        if cols is None and len(positional_ints) > 0:
            cols = positional_ints[0]
            
        if rows is None: rows = 1
        if cols is None: cols = 1
        
        try: rows = int(rows)
        except Exception: rows = 1
        try: cols = int(cols)
        except Exception: cols = 1
        
        self._headers = [str(h) for h in headers] if headers else [str(i) for i in range(cols)]
        self._values = [[fill_value] * cols for _ in range(rows)]
        self._highlighted = []
        self._record("init_table", {"headers": list(self._headers), "values": list(self._values), "highlighted": list(self._highlighted)},
                      message="初始化 DP 表格", line=line)

    def set_value(self, row: Any, col: Any, value: Any, line: Optional[int] = None) -> None:
        if isinstance(row, str) and row in self._headers:
            row = self._headers.index(row)
        if isinstance(col, str) and col in self._headers:
            col = self._headers.index(col)
        try: row = int(row)
        except Exception: row = 0
        try: col = int(col)
        except Exception: col = 0

        if 0 <= row < len(self._values) and 0 <= col < len(self._values[row]):
            self._values[row][col] = value
        self._record("set_value", {"headers": list(self._headers), "values": list(self._values), "highlighted": list(self._highlighted)},
                      message=f"更新表格值 dp[{row}][{col}] = {value}", line=line)

    def highlight(self, row: Any, col: Any, tone: str = "active", line: Optional[int] = None) -> None:
        if isinstance(row, str) and row in self._headers:
            row = self._headers.index(row)
        if isinstance(col, str) and col in self._headers:
            col = self._headers.index(col)
        try: row = int(row)
        except Exception: row = 0
        try: col = int(col)
        except Exception: col = 0

        self._highlighted = [item for item in self._highlighted if not (item["row"] == row and item["col"] == col)]
        self._highlighted.append({"row": row, "col": col, "tone": tone})
        self._record("highlight", {"headers": list(self._headers), "values": list(self._values), "highlighted": list(self._highlighted)},
                      message=f"高亮单元格 dp[{row}][{col}] ({tone})", line=line)

    def clear_highlights(self, line: Optional[int] = None) -> None:
        self._highlighted = []
        self._record("clear_highlights", {"headers": list(self._headers), "values": list(self._values), "highlighted": list(self._highlighted)},
                      message="清除所有高亮", line=line)

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"headers": list(self._headers), "values": list(self._values), "highlighted": list(self._highlighted)},
                      message="DP 填表完成", line=line)
