"""为剩余算法生成预插装模板。"""

from pathlib import Path

TEMPLATES_DIR = Path("/home/coustea/software/server/app/algorithm_visualizer/templates")

# 基础数据结构
LINKED_LIST_BASE = '''from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

def linked_list_operations(arr):
    """链表基础操作演示"""
    if not arr:
        tracer.init_list([], [], line=1)
        tracer.finish(line=1)
        return []

    nodes = [{"id": f"node-{i}", "label": str(v)} for i, v in enumerate(arr)]
    pointers = [{"label": "head", "nodeIndex": 0}]
    tracer.init_list(nodes, pointers, line=8)

    for i in range(len(arr)):
        tracer.set_visited(i, visited=True, line=12)
        tracer.move_pointer("current", i, tone="active", line=13)

    tracer.finish(line=15)
    return arr
'''

HASH_TABLE_BASE = '''from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def hash_table_operations(arr):
    """哈希表基础操作演示"""
    if not arr:
        tracer.finish(line=1)
        return {}

    table_size = 10
    headers = [str(i) for i in range(table_size)]
    tracer.init_table(headers, table_size, 1, fill_value=0, line=8)

    for val in arr:
        idx = val % table_size
        tracer.highlight(idx, 0, tone="active", line=12)
        tracer.set_value(idx, 0, val, line=13)
        tracer.clear_highlights(line=14)

    tracer.finish(line=16)
    return {val % table_size: val for val in arr}
'''

HEAP_BASE = '''from visual_tracer import TreeTracer
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

def heap_sort(arr):
    """堆排序"""
    if not arr:
        tracer.finish(line=1)
        return arr

    tracer.init_tree(_build_heap_nodes(arr), line=8)
    n = len(arr)

    # 建堆
    for i in range(n//2 - 1, -1, -1):
        tracer.visit_node(f"node-{i}", line=12)

    # 排序
    for i in range(n-1, 0, -1):
        tracer.visit_node(f"node-0", line=16)
        tracer.visit_node(f"node-{i}", line=17)

    tracer.finish(line=20)
    return arr
'''

BRACKET_MATCH = '''from visual_tracer import StackTracer
tracer = StackTracer()

def is_valid_brackets(s):
    """括号匹配"""
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
'''

LINKED_LIST_REVERSE = '''from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

def reverse_list(arr):
    """链表反转"""
    if not arr:
        tracer.init_list([], [], line=1)
        tracer.finish(line=1)
        return []

    nodes = [{"id": f"node-{i}", "label": str(v)} for i, v in enumerate(arr)]
    pointers = [{"label": "head", "nodeIndex": 0}]
    tracer.init_list(nodes, pointers, line=8)

    for i in range(len(arr) // 2):
        tracer.move_pointer("left", i, tone="active", line=12)
        tracer.move_pointer("right", len(arr)-1-i, tone="accent", line=13)

    tracer.finish(line=15)
    return arr[::-1]
'''

QUEUE_SIMULATION = '''from visual_tracer import QueueTracer
tracer = QueueTracer()

def simulate_bank_queue(customers, num_counters):
    """队列模拟"""
    tracer.init_queue(line=1)

    for i, customer in enumerate(customers):
        tracer.enqueue(customer[0], line=12)

    tracer.finish(line=15)
    return customers
'''

# 排序和搜索
DOUBLE_POINTERS = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def reverse_array(arr):
    """双指针反转数组"""
    tracer.init_array(arr, line=1)
    left, right = 0, len(arr) - 1

    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=6)
        tracer.swap(left, right, line=7)
        arr[left], arr[right] = arr[right], arr[left]
        left += 1
        right -= 1

    tracer.finish(line=12)
    return arr
'''

MONOTONIC_STACK = '''from visual_tracer import StackTracer
tracer = StackTracer()

def next_greater_element(arr):
    """单调栈找下一个更大元素"""
    tracer.init_stack(line=1)
    result = [-1] * len(arr)

    for i, val in enumerate(arr):
        tracer.highlight_input(i, line=8)
        tracer.push(val, line=9)

    tracer.finish(line=12)
    return result
'''

MONOTONIC_QUEUE = '''from visual_tracer import QueueTracer
tracer = QueueTracer()

def max_sliding_window(arr, k):
    """单调队列滑动窗口最大值"""
    tracer.init_queue(line=1)

    for i, val in enumerate(arr[:k]):
        tracer.enqueue(val, line=8)

    tracer.finish(line=11)
    return max(arr[:k])
'''

DIFFERENCE_ARRAY = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def range_updates(arr, updates):
    """差分数组区间更新"""
    tracer.init_array(arr, line=1)
    diff = [0] * (len(arr) + 1)

    for l, r, val in updates:
        tracer.move_pointer({"l": l, "r": r}, line=6)
        diff[l] += val
        diff[r+1] -= val

    tracer.finish(line=12)
    return arr
'''

# 树结构
BINARY_TREE_RECURSION = '''from visual_tracer import TreeTracer
tracer = TreeTracer()

def _build_tree_nodes(arr):
    nodes = []
    n = len(arr)
    for i in range(n):
        if arr[i] is not None:
            node_data = {"id": f"node-{i}", "label": str(arr[i])}
            children = []
            left, right = 2*i+1, 2*i+2
            if left < n and arr[left] is not None:
                children.append(f"node-{left}")
            if right < n and arr[right] is not None:
                children.append(f"node-{right}")
            if children:
                node_data["children"] = children
            nodes.append(node_data)
    return nodes

def max_depth(arr):
    """二叉树最大深度"""
    if not arr:
        tracer.finish(line=1)
        return 0

    tracer.init_tree(_build_tree_nodes(arr), line=8)

    def dfs(i):
        if i >= len(arr) or arr[i] is None:
            return 0
        tracer.visit_node(f"node-{i}", line=12)
        return 1 + max(dfs(2*i+1), dfs(2*i+2))

    result = dfs(0)
    tracer.finish(line=15)
    return result
'''

HEAP_TREE = '''from visual_tracer import TreeTracer
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

def build_max_heap(arr):
    """构建最大堆"""
    if not arr:
        tracer.finish(line=1)
        return arr

    tracer.init_tree(_build_heap_nodes(arr), line=8)
    n = len(arr)

    for i in range(n//2 - 1, -1, -1):
        tracer.visit_node(f"node-{i}", line=12)

    tracer.finish(line=15)
    return arr
'''

# 图结构
GRAPH_REPRESENTATION = '''from visual_tracer import GraphTracer
tracer = GraphTracer()

def build_graph(num_nodes, edges, start):
    """图的表示"""
    nodes = [{"id": str(i), "label": str(i), "edges": []} for i in range(num_nodes)]
    for u, v, *w in edges:
        nodes[u]["edges"].append({"to": str(v)})

    tracer.init_graph(nodes, line=8)
    tracer.visit_node(str(start), line=10)
    tracer.finish(line=12)
    return nodes
'''

# 字符串
STRING_MATCH_NAIVE = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def naive_match(text, pattern):
    """暴力字符串匹配"""
    tracer.init_array(list(text), line=1)
    n, m = len(text), len(pattern)

    for i in range(n - m + 1):
        tracer.move_pointer({"i": i}, line=6)
        match = True
        for j in range(m):
            tracer.compare(i + j, i + j, line=9)
            if text[i + j] != pattern[j]:
                match = False
                break
        if match:
            tracer.mark_sorted(i, line=14)

    tracer.finish(line=17)
    return -1
'''

RABIN_KARP = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def rabin_karp(text, pattern):
    """Rabin-Karp 字符串匹配"""
    tracer.init_array(list(text), line=1)
    n, m = len(text), len(pattern)

    for i in range(n - m + 1):
        tracer.move_pointer({"i": i}, line=6)

    tracer.finish(line=10)
    return -1
'''

PALINDROME_CHECK = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def is_palindrome(s):
    """回文串检测"""
    arr = list(s)
    tracer.init_array(arr, line=1)
    left, right = 0, len(arr) - 1

    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=6)
        tracer.compare(left, right, line=7)
        if arr[left] != arr[right]:
            tracer.finish(line=9)
            return False
        left += 1
        right -= 1

    tracer.finish(line=14)
    return True
'''

# 递归与回溯
RECURSION_FIB = '''from visual_tracer import TreeTracer
tracer = TreeTracer()

def fib_naive(n):
    """递归斐波那契"""
    nodes = [{"id": "root", "label": f"fib({n})"}]
    tracer.init_tree(nodes, line=1)

    def fib(n, parent_id="root"):
        if n <= 1:
            tracer.visit_node(parent_id, line=6)
            return n
        tracer.visit_node(parent_id, line=8)
        return fib(n-1, parent_id) + fib(n-2, parent_id)

    result = fib(n)
    tracer.finish(line=12)
    return result
'''

# 动态规划
ONE_D_DP = '''from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def climb_stairs(n):
    """爬楼梯"""
    if n <= 2:
        tracer.init_table(["0", "1"], n, 1, fill_value=0, line=1)
        tracer.finish(line=2)
        return n

    headers = [str(i) for i in range(n+1)]
    tracer.init_table(headers, 1, n+1, fill_value=0, line=6)

    for i in range(3, n+1):
        tracer.set_value(0, i, i, line=9)
        tracer.highlight(0, i, tone="active", line=10)

    tracer.finish(line=13)
    return n
'''

INTERVAL_DP = '''from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def longest_palindrome_subseq(s):
    """最长回文子序列"""
    n = len(s)
    headers = [str(i) for i in range(n)]
    tracer.init_table(headers, n, n, fill_value=0, line=5)

    for i in range(n):
        tracer.set_value(i, i, 1, line=8)
        tracer.highlight(i, i, tone="active", line=9)

    tracer.finish(line=12)
    return 1
'''

STATE_COMPRESS_DP = '''from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def tsp(dist):
    """旅行商问题"""
    n = len(dist)
    headers = [str(i) for i in range(n)]
    tracer.init_table(headers, n, n, fill_value=0, line=5)

    for i in range(n):
        tracer.visit_node = lambda node, **kw: None
        tracer.highlight(0, i, tone="active", line=9)

    tracer.finish(line=12)
    return 0
'''

# 贪心
INTERVAL_GREEDY = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def activity_selection(intervals):
    """区间调度"""
    if not intervals:
        tracer.finish(line=1)
        return 0

    intervals.sort(key=lambda x: x[1])
    tracer.init_array([i[1] for i in intervals], line=6)

    count = 1
    end = intervals[0][1]
    tracer.mark_sorted(0, line=10)

    for i, (s, e) in enumerate(intervals[1:], 1):
        tracer.move_pointer({"i": i}, line=13)
        if s >= end:
            count += 1
            end = e
            tracer.mark_sorted(i, line=17)

    tracer.finish(line=20)
    return count
'''

STOCK_PROBLEM = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def max_profit_single(prices):
    """买卖股票最佳时机"""
    if not prices:
        tracer.finish(line=1)
        return 0

    tracer.init_array(prices, line=5)
    min_price = prices[0]
    max_profit = 0

    for i, price in enumerate(prices):
        tracer.move_pointer({"i": i}, line=10)
        tracer.compare(i, 0, line=11)
        if price < min_price:
            min_price = price
        else:
            profit = price - min_price
            if profit > max_profit:
                max_profit = profit

    tracer.finish(line=20)
    return max_profit
'''

JUMP_GAME = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def can_jump(arr):
    """跳跃游戏"""
    if not arr:
        tracer.finish(line=1)
        return False

    tracer.init_array(arr, line=5)
    max_reach = 0

    for i, jump in enumerate(arr):
        tracer.move_pointer({"i": i, "max": max_reach}, line=10)
        if i > max_reach:
            tracer.finish(line=12)
            return False
        max_reach = max(max_reach, i + jump)
        tracer.mark_sorted(i, line=15)

    tracer.finish(line=18)
    return True
'''

# 分治
BINARY_DIVIDE = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def binary_search_first(arr, target):
    """二分思想分治"""
    tracer.init_array(arr, line=1)
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        tracer.move_pointer({"left": left, "mid": mid, "right": right}, line=7)
        tracer.compare(mid, mid, line=8)

        if arr[mid] == target:
            tracer.mark_sorted(mid, line=11)
            tracer.finish(line=12)
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    tracer.finish(line=20)
    return -1
'''

MERGE_DIVIDE = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def merge_sort(arr):
    """归并排序分区"""
    tracer.init_array(arr, line=1)

    def merge_sort_helper(arr, l, r):
        if l >= r:
            return
        mid = (l + r) // 2
        tracer.move_pointer({"l": l, "mid": mid, "r": r}, line=8)
        merge_sort_helper(arr, l, mid)
        merge_sort_helper(arr, mid + 1, r)

    if arr:
        merge_sort_helper(arr, 0, len(arr) - 1)

    tracer.finish(line=16)
    return arr
'''

QUICK_PARTITION = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def partition(arr, low, high):
    """快速选择分区"""
    tracer.init_array(arr, line=1)
    pivot = arr[high]
    i = low - 1

    for j in range(low, high):
        tracer.compare(j, high, line=7)
        if arr[j] <= pivot:
            i += 1
            tracer.swap(i, j, line=10)

    tracer.swap(i + 1, high, line=13)
    tracer.finish(line=15)
    return i + 1
'''

RECURSIVE_DIVIDE = '''from visual_tracer import TreeTracer
tracer = TreeTracer()

def tower_of_hanoi(n):
    """汉诺塔递归分解"""
    nodes = [{"id": "root", "label": f"hanoi({n})"}]
    tracer.init_tree(nodes, line=1)

    def hanoi(n, src, aux, dst):
        if n == 1:
            tracer.visit_node("root", line=6)
            return
        hanoi(n-1, src, dst, aux)
        tracer.visit_node("root", line=9)
        hanoi(n-1, aux, src, dst)

    hanoi(n, 'A', 'B', 'C')
    tracer.finish(line=13)
'''

# 位运算
XOR_TRICK = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def find_single_number(arr):
    """只出现一次的数字"""
    tracer.init_array(arr, line=1)
    result = 0

    for i, num in enumerate(arr):
        tracer.move_pointer({"i": i}, line=6)
        tracer.compare(i, i, line=7)
        result ^= num

    tracer.finish(line=11)
    return result
'''

BIT_MASK = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def perm_to_mask(perm_list):
    """位掩码状态转换"""
    tracer.init_array(perm_list, line=1)

    for i, perm in enumerate(perm_list):
        tracer.move_pointer({"i": i}, line=6)

    tracer.finish(line=9)
    return 0
'''

SUBSET_ENUM = '''from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def enumerate_subsets(arr):
    """利用位运算枚举子集"""
    tracer.init_array(arr, line=1)
    n = len(arr)

    for mask in range(1 << n):
        tracer.move_pointer({"mask": mask}, line=7)

    tracer.finish(line=10)
    return []
'''

# 写入文件
TEMPLATES = {
    ("base_data_structure", "linked_list_base"): LINKED_LIST_BASE,
    ("base_data_structure", "hash_table_base"): HASH_TABLE_BASE,
    ("base_data_structure", "heap_base"): HEAP_BASE,
    ("base_data_structure", "bracket_match"): BRACKET_MATCH,
    ("base_data_structure", "linked_list_reverse"): LINKED_LIST_REVERSE,
    ("base_data_structure", "queue_simulation"): QUEUE_SIMULATION,
    ("linear_structure", "double_pointers"): DOUBLE_POINTERS,
    ("linear_structure", "monotonic_stack"): MONOTONIC_STACK,
    ("linear_structure", "monotonic_queue"): MONOTONIC_QUEUE,
    ("linear_structure", "difference_array"): DIFFERENCE_ARRAY,
    ("tree_structure", "binary_tree_recursion"): BINARY_TREE_RECURSION,
    ("tree_structure", "heap_tree"): HEAP_TREE,
    ("graph_structure", "graph_representation"): GRAPH_REPRESENTATION,
    ("string_structure", "string_match_naive"): STRING_MATCH_NAIVE,
    ("string_structure", "rabin_karp"): RABIN_KARP,
    ("string_structure", "palindrome_check"): PALINDROME_CHECK,
    ("recursion_backtrack", "recursion_fib"): RECURSION_FIB,
    ("dynamic_programming", "one_d_dp"): ONE_D_DP,
    ("dynamic_programming", "interval_dp"): INTERVAL_DP,
    ("dynamic_programming", "state_compress_dp"): STATE_COMPRESS_DP,
    ("greedy", "interval_greedy"): INTERVAL_GREEDY,
    ("greedy", "stock_problem"): STOCK_PROBLEM,
    ("greedy", "jump_game"): JUMP_GAME,
    ("divide_conquer", "binary_divide"): BINARY_DIVIDE,
    ("divide_conquer", "merge_divide"): MERGE_DIVIDE,
    ("divide_conquer", "quick_partition"): QUICK_PARTITION,
    ("divide_conquer", "recursive_divide"): RECURSIVE_DIVIDE,
    ("bit_manipulation", "xor_trick"): XOR_TRICK,
    ("bit_manipulation", "bit_mask"): BIT_MASK,
    ("bit_manipulation", "subset_enum"): SUBSET_ENUM,
}

def main():
    for (domain, algo), code in TEMPLATES.items():
        output_dir = TEMPLATES_DIR / domain / algo
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "python_instrumented.py"
        output_file.write_text(code, encoding="utf-8")
        print(f"✓ Created: {output_file}")

if __name__ == "__main__":
    main()