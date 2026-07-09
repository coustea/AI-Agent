class SegmentTree:
    """线段树 — 支持区间求和、单点更新、区间查询"""

    def __init__(self, arr):
        """初始化线段树 — 递归建树
        数组大小取 4n 保证足够空间 (最坏情况满二叉树)"""
        if not arr:
            raise ValueError("输入数组不能为空")
        self.n = len(arr)
        self.tree = [0] * (4 * self.n)
        self._build(arr, 0, 0, self.n - 1)

    def _build(self, arr, node, start, end):
        """递归建树 — 叶子节点存储原数组值，内部节点存储子树之和
        node: 当前节点在 tree 数组中的索引
        [start, end]: 当前节点负责的区间"""
        if start == end:
            self.tree[node] = arr[start]
            return
        mid = (start + end) // 2
        left_child = 2 * node + 1
        right_child = 2 * node + 2
        self._build(arr, left_child, start, mid)
        self._build(arr, right_child, mid + 1, end)
        self.tree[node] = self.tree[left_child] + self.tree[right_child]

    def update(self, idx, val):
        """单点更新 — 将 arr[idx] 修改为 val
        从根递归到叶子，回溯时更新路径上所有节点
        时间复杂度: O(log n)"""
        if idx < 0 or idx >= self.n:
            raise IndexError(f"索引 {idx} 超出范围 [0, {self.n-1}]")
        self._update(0, 0, self.n - 1, idx, val)

    def _update(self, node, start, end, idx, val):
        if start == end:
            self.tree[node] = val
            return
        mid = (start + end) // 2
        if idx <= mid:
            self._update(2 * node + 1, start, mid, idx, val)
        else:
            self._update(2 * node + 2, mid + 1, end, idx, val)
        self.tree[node] = self.tree[2 * node + 1] + self.tree[2 * node + 2]

    def query(self, l, r):
        """区间查询 — 求 [l, r] 区间之和
        三种情况: 完全包含 / 完全不相交 / 部分重叠
        时间复杂度: O(log n)"""
        if l < 0 or r >= self.n or l > r:
            raise IndexError(f"查询区间 [{l}, {r}] 无效")
        return self._query(0, 0, self.n - 1, l, r)

    def _query(self, node, start, end, l, r):
        if r < start or end < l:
            return 0
        if l <= start and end <= r:
            return self.tree[node]
        mid = (start + end) // 2
        left_sum = self._query(2 * node + 1, start, mid, l, r)
        right_sum = self._query(2 * node + 2, mid + 1, end, l, r)
        return left_sum + right_sum


arr = [2, 5, 1, 4, 8, 3, 7, 6]
st = SegmentTree(arr)

sum_0_3 = st.query(0, 3)
sum_2_5 = st.query(2, 5)
sum_4_7 = st.query(4, 7)
sum_all = st.query(0, 7)

st.update(2, 10)
st.update(5, 0)

sum_after = st.query(0, 5)
