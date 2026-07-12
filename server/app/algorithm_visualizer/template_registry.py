"""算法模板注册表。管理算法元信息和模板代码。
 * service.py 调用 get_all_algorithms / get_algorithm_info / get_template_code / LANGUAGES。"""

from __future__ import annotations

import os
from typing import Any, Dict, List

# 模板根目录
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 支持的语言列表（未来可扩展：java, cpp, javascript 等）
LANGUAGES: List[Dict[str, str]] = [
    {"key": "python", "label": "Python", "extension": "py"},
]

# 语言 key → 干净模板文件名映射（新增语言时需在此添加文件名规则）
_LANGUAGE_FILE_MAP: Dict[str, str] = {
    "python": "python.py",
}

# 算法元信息注册表
ALGORITHMS: Dict[str, Dict[str, Any]] = {
    # 1. 基础数据结构 (base_data_structure)
    "array_base": {
        "domain": "base_data_structure",
        "name": "数组基础操作",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "assign", "finish"]
    },
    "linked_list_base": {
        "domain": "base_data_structure",
        "name": "链表基础操作",
        "visualizer_type": "linked-list",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_list", "move_pointer", "add_node", "remove_node", "finish"]
    },
    "stack_base": {
        "domain": "base_data_structure",
        "name": "栈基础操作",
        "visualizer_type": "stack-queue",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_stack", "push", "pop", "finish"]
    },
    "queue_base": {
        "domain": "base_data_structure",
        "name": "队列基础操作",
        "visualizer_type": "stack-queue",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_queue", "enqueue", "dequeue", "finish"]
    },
    "hash_table_base": {
        "domain": "base_data_structure",
        "name": "哈希表基础操作",
        "visualizer_type": "dp-table",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "heap_base": {
        "domain": "base_data_structure",
        "name": "堆基础操作",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },

    # 2. 排序算法 (sorting)
    "bubble_sort": {
        "domain": "sorting",
        "name": "冒泡排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "swap", "mark_sorted", "finish"]
    },
    "selection_sort": {
        "domain": "sorting",
        "name": "选择排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "swap", "mark_sorted", "finish"]
    },
    "insertion_sort": {
        "domain": "sorting",
        "name": "插入排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "assign", "mark_sorted", "finish"]
    },
    "shell_sort": {
        "domain": "sorting",
        "name": "希尔排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "assign", "finish"]
    },
    "quick_sort": {
        "domain": "sorting",
        "name": "快速排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "swap", "assign", "mark_sorted", "finish"]
    },
    "merge_sort": {
        "domain": "sorting",
        "name": "归并排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "assign", "finish"]
    },
    "heap_sort": {
        "domain": "sorting",
        "name": "堆排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "swap", "finish"]
    },
    "counting_sort": {
        "domain": "sorting",
        "name": "计数排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "bucket_sort": {
        "domain": "sorting",
        "name": "桶排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "radix_sort": {
        "domain": "sorting",
        "name": "基数排序",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },

    # 3. 查找算法 (searching)
    "sequential_search": {
        "domain": "searching",
        "name": "顺序查找",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "binary_search": {
        "domain": "searching",
        "name": "二分查找",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "interpolation_search": {
        "domain": "searching",
        "name": "插值查找",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "fibonacci_search": {
        "domain": "searching",
        "name": "斐波那契查找",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "hash_search": {
        "domain": "searching",
        "name": "哈希查找",
        "visualizer_type": "dp-table",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_table", "highlight", "clear_highlights", "finish"]
    },

    # 4. 线性结构算法 (linear_structure)
    "double_pointers": {
        "domain": "linear_structure",
        "name": "双指针 (反转数组)",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "swap", "move_pointer", "finish"]
    },
    "sliding_window": {
        "domain": "linear_structure",
        "name": "滑动窗口 (最大连续子数组和)",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "move_pointer", "finish"]
    },
    "monotonic_stack": {
        "domain": "linear_structure",
        "name": "单调栈 (下一个更大元素)",
        "visualizer_type": "stack-queue",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_stack", "push", "pop", "finish"]
    },
    "monotonic_queue": {
        "domain": "linear_structure",
        "name": "单调队列 (滑动窗口最大值)",
        "visualizer_type": "stack-queue",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_queue", "enqueue", "dequeue", "finish"]
    },
    "prefix_sum": {
        "domain": "linear_structure",
        "name": "前缀和 (区域和检索)",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "difference_array": {
        "domain": "linear_structure",
        "name": "差分数组 (区间加法)",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },

    # 5. 树结构算法 (tree_structure)
    "binary_tree_traverse": {
        "domain": "tree_structure",
        "name": "二叉树前序遍历",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "binary_tree_recursion": {
        "domain": "tree_structure",
        "name": "二叉树递归 (求最大深度)",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "bst": {
        "domain": "tree_structure",
        "name": "二叉搜索树 (插入与查找)",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "heap_tree": {
        "domain": "tree_structure",
        "name": "最大堆调整过程",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "trie_tree": {
        "domain": "tree_structure",
        "name": "前缀树 (Trie)",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "segment_tree": {
        "domain": "tree_structure",
        "name": "线段树 (构建与区间查询)",
        "visualizer_type": "tree",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "fenwick_tree": {
        "domain": "tree_structure",
        "name": "树状数组 (单点更新与前缀和)",
        "visualizer_type": "tree",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },

    # 6. 图结构算法 (graph_structure)
    "graph_representation": {
        "domain": "graph_structure",
        "name": "图的表示 (邻接表/邻接矩阵)",
        "visualizer_type": "graph",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },
    "graph_bfs": {
        "domain": "graph_structure",
        "name": "图的广度优先搜索 (BFS)",
        "visualizer_type": "graph",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },
    "graph_dfs": {
        "domain": "graph_structure",
        "name": "图的深度优先搜索 (DFS)",
        "visualizer_type": "graph",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },
    "shortest_path": {
        "domain": "graph_structure",
        "name": "最短路径 (Dijkstra)",
        "visualizer_type": "graph",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },
    "topological_sort": {
        "domain": "graph_structure",
        "name": "拓扑排序 (Kahn算法)",
        "visualizer_type": "graph",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },
    "mst_kruskal": {
        "domain": "graph_structure",
        "name": "最小生成树 (Kruskal)",
        "visualizer_type": "graph",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },
    "dsu_union": {
        "domain": "graph_structure",
        "name": "并查集 (合并与路径压缩)",
        "visualizer_type": "graph",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_graph", "visit_node", "finish"]
    },

    # 7. 字符串算法 (string_structure)
    "string_match_naive": {
        "domain": "string_structure",
        "name": "暴力字符串匹配",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "kmp_match": {
        "domain": "string_structure",
        "name": "KMP 字符串匹配",
        "visualizer_type": "array",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "rabin_karp": {
        "domain": "string_structure",
        "name": "Rabin-Karp 算法",
        "visualizer_type": "array",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "trie_string_search": {
        "domain": "string_structure",
        "name": "Trie 单词检索",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "palindrome_check": {
        "domain": "string_structure",
        "name": "回文串检测 (双指针)",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },

    # 8. 递归与回溯 (recursion_backtrack)
    "recursion_fib": {
        "domain": "recursion_backtrack",
        "name": "递归斐波那契",
        "visualizer_type": "tree",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "permutations": {
        "domain": "recursion_backtrack",
        "name": "全排列问题",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "subsets": {
        "domain": "recursion_backtrack",
        "name": "子集生成",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "combinations": {
        "domain": "recursion_backtrack",
        "name": "组合总和",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "n_queens": {
        "domain": "recursion_backtrack",
        "name": "N 皇后问题",
        "visualizer_type": "dp-table",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "maze_search": {
        "domain": "recursion_backtrack",
        "name": "迷宫寻路 (回溯法)",
        "visualizer_type": "dp-table",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },

    # 9. 动态规划 (dynamic_programming)
    "dp_fibonacci": {
        "domain": "dynamic_programming",
        "name": "斐波那契数 DP 填表",
        "visualizer_type": "dp-table",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"],
    },
    "one_d_dp": {
        "domain": "dynamic_programming",
        "name": "一维 DP (爬楼梯)",
        "visualizer_type": "dp-table",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "two_d_dp": {
        "domain": "dynamic_programming",
        "name": "二维 DP (最小路径和)",
        "visualizer_type": "dp-table",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "knapsack_dp": {
        "domain": "dynamic_programming",
        "name": "0-1 背包问题",
        "visualizer_type": "dp-table",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "interval_dp": {
        "domain": "dynamic_programming",
        "name": "区间 DP (最长回文子序列)",
        "visualizer_type": "dp-table",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "tree_dp": {
        "domain": "dynamic_programming",
        "name": "树形 DP (打家劫舍 III)",
        "visualizer_type": "tree",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "state_compress_dp": {
        "domain": "dynamic_programming",
        "name": "状态压缩 DP (旅行商 TSP 问题)",
        "visualizer_type": "dp-table",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },

    # 10. 贪心算法 (greedy)
    "interval_greedy": {
        "domain": "greedy",
        "name": "无重叠区间 (区间调度)",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "finish"]
    },
    "stock_problem": {
        "domain": "greedy",
        "name": "买卖股票的最佳时机",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "jump_game": {
        "domain": "greedy",
        "name": "跳跃游戏",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "move_pointer", "finish"]
    },
    "huffman_coding": {
        "domain": "greedy",
        "name": "哈夫曼树构建",
        "visualizer_type": "tree",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },
    "covering_problem": {
        "domain": "greedy",
        "name": "集合覆盖问题",
        "visualizer_type": "array",
        "difficulty": "hard",
        "supported_languages": ["python"],
        "required_events": ["init_array", "move_pointer", "mark_sorted", "finish"]
    },

    # 11. 分治算法 (divide_conquer)
    "binary_divide": {
        "domain": "divide_conquer",
        "name": "二分思想分治",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
    },
    "merge_divide": {
        "domain": "divide_conquer",
        "name": "归并排序分区",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "assign", "finish"]
    },
    "quick_partition": {
        "domain": "divide_conquer",
        "name": "快速选择 (第K大元素)",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "swap", "finish"]
    },
    "recursive_divide": {
        "domain": "divide_conquer",
        "name": "汉诺塔递归分解",
        "visualizer_type": "tree",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_tree", "visit_node", "finish"]
    },

    # 12. 位运算 (bit_manipulation)
    "basic_bit": {
        "domain": "bit_manipulation",
        "name": "二进制位提取/设置",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "move_pointer", "assign", "finish"]
    },
    "xor_trick": {
        "domain": "bit_manipulation",
        "name": "只出现一次的数字 (异或)",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "compare", "finish"]
    },
    "bit_mask": {
        "domain": "bit_manipulation",
        "name": "位掩码状态转换",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "subset_enum": {
        "domain": "bit_manipulation",
        "name": "利用位运算枚举子集",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },

    # 13. 数学算法 (math)
    "gcd_euclidean": {
        "domain": "math",
        "name": "最大公约数 (欧几里得)",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "quick_power": {
        "domain": "math",
        "name": "数值快速幂",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "prime_sieve": {
        "domain": "math",
        "name": "埃拉托斯特尼筛法 (质数筛)",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    },
    "combination_num": {
        "domain": "math",
        "name": "组合数计算 (杨辉三角)",
        "visualizer_type": "dp-table",
        "difficulty": "easy",
        "supported_languages": ["python"],
        "required_events": ["init_table", "set_value", "highlight", "clear_highlights", "finish"]
    },
    "mod_arithmetic": {
        "domain": "math",
        "name": "同余幂运算",
        "visualizer_type": "array",
        "difficulty": "medium",
        "supported_languages": ["python"],
        "required_events": ["init_array", "assign", "finish"]
    }
}


# 按 domain 过滤并返回所有算法信息列表
def get_all_algorithms(domain: str = "all") -> List[Dict[str, Any]]:
    """获取指定 domain 下的所有算法信息列表。支持 domain="all"。"""
    result = []
    for key, info in ALGORITHMS.items():
        if domain == "all" or info["domain"] == domain:
            result.append({"key": key, **info})
    return result


# 根据算法 key 获取单个算法的元信息
def get_algorithm_info(algorithm_key: str) -> Dict[str, Any]:
    """获取单个算法的元信息，不存在则抛出 ValueError。"""
    info = ALGORITHMS.get(algorithm_key)
    if not info:
        raise ValueError(f"不支持的算法: {algorithm_key}")
    return {"key": algorithm_key, **info}


# 读取干净模板代码（不含 tracer 调用）
def get_template_code(algorithm_key: str, language: str) -> str:
    """读取并返回指定算法+语言的干净模板代码（无 tracer 调用）。"""
    info = get_algorithm_info(algorithm_key)
    if language not in info["supported_languages"]:
        raise ValueError(f"算法 {algorithm_key} 不支持语言 {language}")

    filename = _LANGUAGE_FILE_MAP.get(language)
    if not filename:
        raise ValueError(f"不支持的语言: {language}")

    filepath = os.path.join(_TEMPLATES_DIR, info["domain"], algorithm_key, filename)
    if not os.path.isfile(filepath):
        raise ValueError(f"模板文件不存在: {algorithm_key}/{language}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# get_instrumented_template_code 已删除，改由 CodeInstrumenter 缓存引擎统一处理


_DEFAULT_DATA_MAP = {
    # 1. Base Data Structures
    "array_base": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "linked_list_base": {"arr": [1, 2, 3, 4, 5]},
    "stack_base": {"operations": [["enqueue", 10], ["enqueue", 20], ["dequeue", None], ["enqueue", 30]]},
    "queue_base": {"operations": [["enqueue", 10], ["enqueue", 20], ["dequeue", None], ["enqueue", 30]]},
    "hash_table_base": {"arr": [5, 3, 8, 1, 2]},
    "heap_base": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    
    # 2. Sorting
    "bubble_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "selection_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "insertion_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "shell_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "quick_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "merge_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "heap_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "counting_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "bucket_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "radix_sort": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    
    # 3. Searching
    "sequential_search": {"arr": [1, 2, 3, 5, 8], "target": 5},
    "binary_search": {"arr": [1, 2, 3, 5, 8], "target": 5},
    "interpolation_search": {"arr": [1, 2, 3, 5, 8], "target": 5},
    "fibonacci_search": {"arr": [1, 2, 3, 5, 8], "target": 5},
    "hash_search": {"arr": [5, 3, 8, 1, 2], "target": 8},
    
    # 4. Linear Structures
    "double_pointers": {"arr": [1, 2, 3, 5, 8], "target": 8},
    "sliding_window": {"arr": [1, 4, 2, 10, 2, 3, 1, 0, 20], "k": 4},
    "monotonic_stack": {"arr": [2, 1, 2, 4, 3]},
    "monotonic_queue": {"arr": [1, 3, -1, -3, 5, 3, 6, 7], "k": 3},
    "prefix_sum": {"arr": [1, 2, 3, 4, 5], "left": 1, "right": 3},
    "difference_array": {"arr": [1, 2, 3, 4, 5], "updates": [[1, 3, 2], [2, 4, 1]]},
    
    # 5. Trees
    "binary_tree_traverse": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    "binary_tree_recursion": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    "bst": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    "heap_tree": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    "trie_tree": {"words": ["cat", "car"]},
    "segment_tree": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    "fenwick_tree": {"arr": [1, 2, 3, 4, 5, 6, 7]},
    
    # 6. Graphs
    "graph_representation": {"num_nodes": 6, "edges": [[0, 1, 1], [0, 2, 1], [1, 3, 1], [1, 4, 1], [2, 5, 1]], "start": 0},
    "graph_bfs": {"num_nodes": 6, "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]], "start": 0},
    "graph_dfs": {"num_nodes": 6, "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]], "start": 0},
    "shortest_path": {"num_nodes": 6, "edges": [[0, 1, 5], [0, 2, 1], [1, 2, 2], [1, 3, 3], [1, 4, 20], [2, 4, 12], [3, 4, 2], [3, 5, 6], [4, 5, 1]], "start": 0},
    "topological_sort": {"num_nodes": 6, "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]], "start": 0},
    "mst_kruskal": {"num_nodes": 6, "edges": [[0, 1, 6], [0, 2, 1], [0, 3, 5], [1, 2, 5], [1, 4, 3], [2, 3, 5], [2, 4, 6], [2, 5, 4], [3, 5, 2], [4, 5, 6]]},
    "dsu_union": {"num_nodes": 6, "edges": [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5]], "start": 0},
    
    # 7. Strings
    "string_match_naive": {"text": "abacaabadcabacaba", "pattern": "abacaba"},
    "kmp_match": {"text": "abacaabadcabacaba", "pattern": "abacaba"},
    "rabin_karp": {"text": "abacaabadcabacaba", "pattern": "abacaba"},
    "trie_string_search": {"words": ["cat", "car"]},
    "palindrome_check": {"s": "racecar"},
    
    # 8. Recursion & Backtrack
    "recursion_fib": {"n": 6},
    "permutations": {"arr": [1, 2, 3]},
    "subsets": {"arr": [1, 2, 3]},
    "combinations": {"candidates": [2, 3, 6, 7], "target": 7},
    "n_queens": {"n": 4},
    "maze_search": {"maze": [[0, 1, 0, 0], [0, 0, 0, 1], [1, 0, 1, 0], [0, 0, 0, 0]]},
    
    # 9. DP
    "dp_fibonacci": {"n": 6},
    "one_d_dp": {"n": 6},
    "two_d_dp": {"grid": [[1, 3, 1], [1, 5, 1], [4, 2, 1]]},
    "knapsack_dp": {"weights": [2, 3, 4, 5], "values": [3, 4, 5, 6], "capacity": 5},
    "interval_dp": {"s": "racecar"},
    "tree_dp": {"arr": [3, 2, 3, None, 3, None, 1]},
    "state_compress_dp": {"dist": [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]},
    
    # 10. Greedy
    "interval_greedy": {"intervals": [[1, 2], [2, 3], [3, 4], [1, 3]]},
    "stock_problem": {"prices": [7, 1, 5, 3, 6, 4]},
    "jump_game": {"arr": [2, 3, 1, 1, 4]},
    "huffman_coding": {"char_freq": [["a", 5], ["b", 9], ["c", 12], ["d", 13], ["e", 16], ["f", 45]]},
    "covering_problem": {"points": [1.2, 2.5, 3.8, 4.0, 5.5], "interval_len": 2.0},
    
    # 11. Divide & Conquer
    "binary_divide": {"arr": [1, 2, 3, 5, 8], "target": 5},
    "merge_divide": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "quick_partition": {"arr": [6, 1, 8, 3, 9, 2, 5, 7, 4]},
    "recursive_divide": {"n": 3},
    
    # 12. Bit Manipulation
    "basic_bit": {"n": 42, "operations": [["get", 2], ["set", 3], ["clear", 1], ["toggle", 4]]},
    "xor_trick": {"arr": [1, 2, 3]},
    "bit_mask": {"perm_list": [0, 1, 2]},
    "subset_enum": {"arr": [1, 2, 3]},
    
    # 13. Math
    "gcd_euclidean": {"a": 48, "b": 18},
    "quick_power": {"base": 2, "exp": 10},
    "prime_sieve": {"n": 6},
    "combination_num": {"n": 6},
    "mod_arithmetic": {"base": 2, "exp": 10, "m": 1000},
}


def build_default_data(algorithm: str) -> dict:
    """根据算法模板返回前端默认数据。"""
    return _DEFAULT_DATA_MAP.get(algorithm, {})
