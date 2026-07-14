"""批量预插装脚本：为所有算法模板生成插装缓存。

由于 LLM 需要代理支持，此脚本手动为算法添加 tracer 调用。
"""

import json
import hashlib
from pathlib import Path
from typing import Any

# Tracer SDK 导入模板
ARRAY_TRACER = "from visual_tracer import ArrayTracer\ntracer = ArrayTracer()\n"
STACK_TRACER = "from visual_tracer import StackTracer\ntracer = StackTracer()\n"
QUEUE_TRACER = "from visual_tracer import QueueTracer\ntracer = QueueTracer()\n"
TREE_TRACER = "from visual_tracer import TreeTracer\ntracer = TreeTracer()\n"
GRAPH_TRACER = "from visual_tracer import GraphTracer\ntracer = GraphTracer()\n"
DP_TABLE_TRACER = "from visual_tracer import DpTableTracer\ntracer = DpTableTracer()\n"
LINKED_LIST_TRACER = "from visual_tracer import LinkedListTracer\ntracer = LinkedListTracer()\n"

# 基础数据结构预插装模板
PRE_INSTRUMENTED = {
    # base_data_structure
    "array_base": """from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# 数组基础操作演示
def array_operations(arr):
    arr = list(arr)
    if not arr:
        tracer.init_array([], line=1)
        tracer.finish(line=1)
        return arr

    tracer.init_array(arr, line=8)

    # 1. 随机访问
    tracer.move_pointer({"access": min(4, len(arr) - 1)}, line=17)
    val_at_4 = arr[min(4, len(arr) - 1)]

    # 2. 线性查找
    target = 8
    found_idx = -1
    for i in range(len(arr)):
        tracer.move_pointer({"search": i}, line=23)
        tracer.compare(i, target, line=24)
        if arr[i] == target:
            found_idx = i
            tracer.mark_sorted(i, line=25)
            break

    # 3. 更新元素
    if len(arr) > 2:
        tracer.assign(2, 15, line=31)
        arr[2] = 15

    # 4. 插入元素
    insert_pos = min(5, len(arr))
    insert_val = 20
    tracer.move_pointer({"insert": insert_pos}, line=35)
    arr.insert(insert_pos, insert_val)
    tracer.init_array(arr, line=37)

    # 5. 删除元素
    delete_pos = min(3, len(arr) - 1)
    if delete_pos < len(arr):
        tracer.move_pointer({"delete": delete_pos}, line=41)
        removed = arr.pop(delete_pos)
        tracer.init_array(arr, line=43)

    # 6. 查找最小值
    min_idx = 0
    for i in range(1, len(arr)):
        tracer.compare(i, min_idx, line=49)
        if arr[i] < arr[min_idx]:
            min_idx = i

    # 7. 交换
    tracer.swap(0, min_idx, line=54)
    arr[0], arr[min_idx] = arr[min_idx], arr[0]

    tracer.finish(line=56)
    return arr
""",
    "stack_base": """from visual_tracer import StackTracer
tracer = StackTracer()

# 栈基础操作演示
def stack_operations(operations):
    stack = []
    tracer.init_stack(line=1)

    for i, (operation, value) in enumerate(operations):
        tracer.highlight_input(i, line=12)
        if operation == "push":
            tracer.push(value, line=13)
            stack.append(value)
        elif operation == "pop" and stack:
            tracer.pop(line=15)
            stack.pop()
        elif operation == "clear":
            stack.clear()
            tracer.init_stack(line=17)

    tracer.finish(line=18)
    return stack, len(stack)
""",
    "queue_base": """from visual_tracer import QueueTracer
tracer = QueueTracer()

# 队列基础操作演示
def queue_operations(operations):
    queue = []
    tracer.init_queue(line=1)

    for i, (operation, value) in enumerate(operations):
        tracer.highlight_input(i, line=12)
        if operation == "enqueue":
            tracer.enqueue(value, line=13)
            queue.append(value)
        elif operation == "dequeue" and queue:
            tracer.dequeue(line=15)
            queue.pop(0)
        elif operation == "clear":
            queue.clear()
            tracer.init_queue(line=17)

    tracer.finish(line=18)
    return queue, len(queue)
""",
    "linked_list_base": """from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

# 链表基础操作演示
def linked_list_operations(arr):
    if not arr:
        tracer.init_list([], [], line=1)
        tracer.finish(line=1)
        return []

    # 构建节点列表
    nodes = [{"id": f"node-{i}", "label": str(v)} for i, v in enumerate(arr)]
    pointers = [{"label": "head", "nodeIndex": 0}]
    tracer.init_list(nodes, pointers, line=8)

    # 遍历链表
    for i in range(len(arr)):
        tracer.move_pointer("current", i, tone="active", line=12)
        tracer.set_visited(i, visited=True, line=13)

    tracer.finish(line=15)
    return arr
""",
    "hash_table_base": """from visual_tracer import DpTableTracer
tracer = DpTableTracer()

# 哈希表基础操作演示
def hash_table_operations(arr):
    if not arr:
        tracer.finish(line=1)
        return {}

    # 构建哈希表
    table_size = 10
    headers = [str(i) for i in range(table_size)]
    tracer.init_table(headers, table_size, 1, fill_value=0, line=8)

    # 插入元素
    for val in arr:
        idx = val % table_size
        tracer.highlight(idx, 0, tone="active", line=12)
        tracer.set_value(idx, 0, val, line=13)
        tracer.clear_highlights(line=14)

    tracer.finish(line=16)
    return {val % table_size: val for val in arr}
""",
    "heap_base": """from visual_tracer import TreeTracer
tracer = TreeTracer()

def _build_heap_nodes(arr):
    nodes = []
    n = len(arr)
    for i in range(n):
        node_data = {"id": f"node-{i}", "label": str(arr[i])}
        children = []
        left, right = 2*i+1, 2*i+2
        if left < n:
            children.append(f"node-{left}")
        if right < n:
            children.append(f"node-{right}")
        if children:
            node_data["children"] = children
        nodes.append(node_data)
    return nodes

# 堆基础操作演示
def heap_sort(arr):
    if not arr:
        tracer.finish(line=1)
        return arr

    tracer.init_tree(_build_heap_nodes(arr), line=8)

    # 建堆
    n = len(arr)
    for i in range(n//2 - 1, -1, -1):
        tracer.visit_node(f"node-{i}", line=12)

    tracer.finish(line=15)
    return arr
""",
    "bracket_match": """from visual_tracer import StackTracer
tracer = StackTracer()

# 括号匹配
def is_valid_brackets(s):
    stack = []
    tracer.init_stack(line=1)
    pairs = {')': '(', ']': '[', '}': '{'}

    for i, ch in enumerate(s):
        tracer.highlight_input(i, line=12)
        if ch in pairs.values():
            tracer.push(ch, line=13)
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                tracer.pop(line=15)
                tracer.finish(line=16)
                return False
            tracer.pop(line=18)
            stack.pop()

    tracer.finish(line=21)
    return len(stack) == 0
""",
    "linked_list_reverse": """from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

# 链表反转
def reverse_list(arr):
    if not arr:
        tracer.init_list([], [], line=1)
        tracer.finish(line=1)
        return []

    nodes = [{"id": f"node-{i}", "label": str(v)} for i, v in enumerate(arr)]
    pointers = [{"label": "head", "nodeIndex": 0}]
    tracer.init_list(nodes, pointers, line=8)

    # 反转过程
    prev, curr = -1, 0
    tracer.snapshot({"prev": prev, "curr": curr}, line=12)

    tracer.finish(line=15)
    return arr[::-1]
""",
    "queue_simulation": """from visual_tracer import QueueTracer
tracer = QueueTracer()

# 队列模拟（银行排队）
def simulate_bank_queue(customers, num_counters):
    tracer.init_queue(line=1)

    # 模拟队列操作
    for customer in customers:
        tracer.enqueue(customer[0], line=12)

    tracer.finish(line=15)
    return customers
""",
}


def compute_hash(code: str, visualizer_type: str, required_events: list[str]) -> str:
    raw = f"{code}\0{visualizer_type}\0{','.join(sorted(required_events))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_pre_instrumented_cache() -> dict:
    """构建预插装缓存。"""
    from app.algorithm_visualizer.template_registry import get_algorithm_info, get_template_code, ALGORITHMS

    cache = {}

    # 加载已有缓存
    cache_path = Path(__file__).parent / "instrumentation_cache.json"
    if cache_path.exists():
        with open(cache_path) as f:
            existing = json.load(f)
            cache.update(existing)

    # 添加预插装模板
    for algo_key, instrumented_code in PRE_INSTRUMENTED.items():
        info = get_algorithm_info(algo_key)
        clean_code = get_template_code(algo_key, 'python')
        hash_key = compute_hash(clean_code, info['visualizer_type'], info.get('required_events', []))

        cache[hash_key] = {
            "code": instrumented_code,
            "error": None
        }
        print(f"Added pre-instrumented: {algo_key}")

    return cache


if __name__ == "__main__":
    cache = build_pre_instrumented_cache()
    cache_path = Path(__file__).parent / "instrumentation_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(cache)} entries to cache")