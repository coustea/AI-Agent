/** 算法分类数据 — 与后端 template_registry.py 保持一致 */

export interface AlgorithmItem {
  key: string
  name: string
  difficulty: 'easy' | 'medium' | 'hard'
  supportedLanguages: string[]
}

export interface AlgorithmCategory {
  key: string
  label: string
  algorithms: AlgorithmItem[]
}

export const algorithmCategories: AlgorithmCategory[] = [
  {
    key: 'sorting',
    label: '排序算法',
    algorithms: [
      { key: 'bubble_sort', name: '冒泡排序', difficulty: 'easy', supportedLanguages: ['python', 'javascript', 'cpp', 'c', 'java'] },
      { key: 'selection_sort', name: '选择排序', difficulty: 'easy', supportedLanguages: ['python', 'javascript', 'cpp', 'c', 'java'] },
      { key: 'insertion_sort', name: '插入排序', difficulty: 'easy', supportedLanguages: ['python', 'javascript', 'cpp', 'c', 'java'] },
      { key: 'shell_sort', name: '希尔排序', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'quick_sort', name: '快速排序', difficulty: 'medium', supportedLanguages: ['python', 'javascript', 'cpp'] },
      { key: 'merge_sort', name: '归并排序', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'heap_sort', name: '堆排序', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'counting_sort', name: '计数排序', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'bucket_sort', name: '桶排序', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'radix_sort', name: '基数排序', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'searching',
    label: '搜索算法',
    algorithms: [
      { key: 'sequential_search', name: '顺序查找', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'binary_search', name: '二分查找', difficulty: 'easy', supportedLanguages: ['python', 'javascript', 'cpp', 'c', 'java'] },
      { key: 'interpolation_search', name: '插值查找', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'fibonacci_search', name: '斐波那契查找', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'hash_search', name: '哈希查找', difficulty: 'easy', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'base_data_structure',
    label: '基础数据结构',
    algorithms: [
      { key: 'array_base', name: '数组基础操作', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'linked_list_base', name: '链表基础操作', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'stack_base', name: '栈基础操作', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'queue_base', name: '队列基础操作', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'hash_table_base', name: '哈希表基础操作', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'heap_base', name: '堆基础操作', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'linear_structure',
    label: '线性结构',
    algorithms: [
      { key: 'double_pointers', name: '双指针', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'sliding_window', name: '滑动窗口', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'monotonic_stack', name: '单调栈', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'monotonic_queue', name: '单调队列', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'prefix_sum', name: '前缀和', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'difference_array', name: '差分数组', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'tree_structure',
    label: '树结构',
    algorithms: [
      { key: 'binary_tree_traverse', name: '二叉树前序遍历', difficulty: 'medium', supportedLanguages: ['python', 'javascript'] },
      { key: 'binary_tree_recursion', name: '二叉树递归', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'bst', name: '二叉搜索树', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'heap_tree', name: '最大堆调整', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'trie_tree', name: '前缀树 Trie', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'segment_tree', name: '线段树', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'fenwick_tree', name: '树状数组', difficulty: 'hard', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'graph_structure',
    label: '图结构',
    algorithms: [
      { key: 'graph_representation', name: '图的表示', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'graph_bfs', name: '广度优先搜索', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'graph_dfs', name: '深度优先搜索', difficulty: 'medium', supportedLanguages: ['python', 'javascript', 'cpp'] },
      { key: 'shortest_path', name: '最短路径 Dijkstra', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'topological_sort', name: '拓扑排序', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'mst_kruskal', name: '最小生成树', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'dsu_union', name: '并查集', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'string_structure',
    label: '字符串',
    algorithms: [
      { key: 'string_match_naive', name: '暴力字符串匹配', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'kmp_match', name: 'KMP 字符串匹配', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'rabin_karp', name: 'Rabin-Karp 算法', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'trie_string_search', name: 'Trie 单词检索', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'palindrome_check', name: '回文串检测', difficulty: 'easy', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'recursion_backtrack',
    label: '递归与回溯',
    algorithms: [
      { key: 'recursion_fib', name: '递归斐波那契', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'permutations', name: '全排列问题', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'subsets', name: '子集生成', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'combinations', name: '组合总和', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'n_queens', name: 'N 皇后问题', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'maze_search', name: '迷宫寻路', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'dynamic_programming',
    label: '动态规划',
    algorithms: [
      { key: 'dp_fibonacci', name: '斐波那契数 DP', difficulty: 'easy', supportedLanguages: ['python', 'javascript'] },
      { key: 'one_d_dp', name: '一维 DP', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'two_d_dp', name: '二维 DP', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'knapsack_dp', name: '0-1 背包', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'interval_dp', name: '区间 DP', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'tree_dp', name: '树形 DP', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'state_compress_dp', name: '状态压缩 DP', difficulty: 'hard', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'greedy',
    label: '贪心算法',
    algorithms: [
      { key: 'interval_greedy', name: '无重叠区间', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'stock_problem', name: '买卖股票最佳时机', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'jump_game', name: '跳跃游戏', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'huffman_coding', name: '哈夫曼树构建', difficulty: 'hard', supportedLanguages: ['python'] },
      { key: 'covering_problem', name: '集合覆盖问题', difficulty: 'hard', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'divide_conquer',
    label: '分治算法',
    algorithms: [
      { key: 'binary_divide', name: '二分思想分治', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'merge_divide', name: '归并排序分区', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'quick_partition', name: '快速选择', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'recursive_divide', name: '汉诺塔递归分解', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'bit_manipulation',
    label: '位运算',
    algorithms: [
      { key: 'basic_bit', name: '二进制位提取/设置', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'xor_trick', name: '只出现一次的数字', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'bit_mask', name: '位掩码状态转换', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'subset_enum', name: '位运算枚举子集', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
  {
    key: 'math',
    label: '数学算法',
    algorithms: [
      { key: 'gcd_euclidean', name: '最大公约数', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'quick_power', name: '数值快速幂', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'prime_sieve', name: '质数筛', difficulty: 'medium', supportedLanguages: ['python'] },
      { key: 'combination_num', name: '组合数计算', difficulty: 'easy', supportedLanguages: ['python'] },
      { key: 'mod_arithmetic', name: '同余幂运算', difficulty: 'medium', supportedLanguages: ['python'] },
    ],
  },
]

/** 根据算法 key 查找信息 */
export function findAlgorithmByKey(key: string): AlgorithmItem | undefined {
  for (const cat of algorithmCategories) {
    const alg = cat.algorithms.find((a) => a.key === key)
    if (alg) return alg
  }
  return undefined
}

/** 根据算法 key 查找所属分类 */
export function findCategoryByAlgorithmKey(key: string): AlgorithmCategory | undefined {
  return algorithmCategories.find((cat) => cat.algorithms.some((a) => a.key === key))
}
