"""Python VisualTracer SDK — 生成 TraceEvent JSON 事件流。
 * python_adapter.py 写入临时目录与用户代码一起执行。
 * 替代旧 PYTHON_TRACER_SDK 字符串常量。
 * 输出 trace.json 而非 __TRACER__: stdout 协议。"""

import json
from typing import Any, Dict, List, Optional


class VisualTracer:
    """Multi-domain algorithm visualization tracer for Python."""

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []
        self._step: int = 0
        self._domain: str = "data_structure"
        self._visualizer_type: str = "array"

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
            "state": {"structure": state_structure},
            "targets": targets or [],
            "message": message,
            "line": line,
            "formula": formula,
        }
        self._events.append(event)
        self._step += 1

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

    def init_stack(self, line: Optional[int] = None) -> None:
        self._items = []
        self._record("init_stack", {"mode": "stack", "items": self._snapshot()}, message="初始化空栈", line=line)

    def push(self, value: Any, line: Optional[int] = None) -> None:
        self._items.append({"value": value, "tone": "default"})
        self._record("push", {"mode": "stack", "items": self._snapshot()},
                      targets=[len(self._items) - 1], message=f"入栈：{value}", line=line)

    def pop(self, line: Optional[int] = None) -> Any:
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

    def init_queue(self, line: Optional[int] = None) -> None:
        self._items = []
        self._record("init_queue", {"mode": "queue", "items": self._snapshot()}, message="初始化空队列", line=line)

    def enqueue(self, value: Any, line: Optional[int] = None) -> None:
        self._items.append({"value": value, "tone": "default"})
        self._record("enqueue", {"mode": "queue", "items": self._snapshot()},
                      targets=[len(self._items) - 1], message=f"入队：{value}", line=line)

    def dequeue(self, line: Optional[int] = None) -> Any:
        if self._items:
            item = self._items.pop(0)
            self._record("dequeue", {"mode": "queue", "items": self._snapshot()}, message=f"出队：{item['value']}", line=line)
            return item["value"]
        return None

    def finish(self, line: Optional[int] = None) -> None:
        self._record("finish", {"mode": "queue", "items": self._snapshot()}, message="队列模拟完成", line=line)
