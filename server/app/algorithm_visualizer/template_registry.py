"""算法模板注册表。管理算法元信息和模板代码。
 * service.py 调用 get_all_algorithms / get_algorithm_info / get_template_code / LANGUAGES。"""

from __future__ import annotations

import os
from typing import Any, Dict, List

# 模板根目录
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# 支持的语言列表
LANGUAGES: List[Dict[str, str]] = [
    {"key": "python", "label": "Python", "extension": "py"},
    {"key": "javascript", "label": "JavaScript", "extension": "js"},
    {"key": "cpp", "label": "C++", "extension": "cpp"},
    {"key": "java", "label": "Java", "extension": "java"},
    {"key": "c", "label": "C", "extension": "c"},
]

# 语言 key → 模板文件名
_LANGUAGE_FILE_MAP: Dict[str, str] = {
    "python": "python.py",
    "javascript": "js.js",
    "cpp": "cpp.cpp",
    "java": "java.java",
    "c": "c.c",
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
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_array", "compare", "swap", "mark_sorted", "finish"]
    },
    "selection_sort": {
        "domain": "sorting",
        "name": "选择排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
        "required_events": ["init_array", "compare", "swap", "mark_sorted", "finish"]
    },
    "insertion_sort": {
        "domain": "sorting",
        "name": "插入排序",
        "visualizer_type": "array",
        "difficulty": "easy",
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
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
        "supported_languages": ["python", "javascript", "cpp"],
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
        "supported_languages": ["python", "javascript", "cpp", "c", "java"],
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
        "supported_languages": ["python", "javascript"],
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
        "supported_languages": ["python", "javascript", "cpp"],
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
        "supported_languages": ["python", "javascript"],
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
        "required_events": ["init_array", "compare", "move_pointer", "finish"]
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
        "required_events": ["init_array", "finish"]
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
        "required_events": ["init_array", "assign", "finish"]
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


def get_all_algorithms(domain: str = "all") -> List[Dict[str, Any]]:
    """获取指定 domain 下的所有算法信息列表。支持 domain="all"。"""
    result = []
    for key, info in ALGORITHMS.items():
        if domain == "all" or info["domain"] == domain:
            result.append({"key": key, **info})
    return result


def get_algorithm_info(algorithm_key: str) -> Dict[str, Any]:
    """获取单个算法的元信息，不存在则抛出 ValueError。"""
    info = ALGORITHMS.get(algorithm_key)
    if not info:
        raise ValueError(f"不支持的算法: {algorithm_key}")
    return {"key": algorithm_key, **info}


def get_template_code(algorithm_key: str, language: str) -> str:
    """读取并返回指定算法+语言的模板代码。"""
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
