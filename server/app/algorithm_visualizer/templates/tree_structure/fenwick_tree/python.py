# fenwick_tree 算法实现 — domain: tree_structure
class FenwickTree:
    """树状数组 — 高效的前缀和结构"""

    def __init__(self, size):
        """初始化 — tree[0] 不使用，有效索引 1..size
        注意: Fenwick Tree 的索引从 1 开始"""
        if size <= 0:
            raise ValueError("树状数组大小必须 > 0")
        self.n = size
        self.tree = [0] * (size + 1)

    def update(self, idx, delta):
        """单点更新 — 在位置 idx 加上 delta
        沿 lowbit 路径向上传播，更新所有包含 idx 的节点
        时间复杂度: O(log n)"""
        if idx < 1 or idx > self.n:
            raise IndexError(f"索引 {idx} 超出范围 [1, {self.n}]")
        while idx <= self.n:
            self.tree[idx] += delta
            idx += idx & (-idx)

    def prefix_sum(self, idx):
        """前缀查询 — 求 [1, idx] 区间之和
        沿 lowbit 路径向前累加，收集所有覆盖区间的值
        复杂度: O(log n)"""
        if idx < 0:
            return 0
        if idx > self.n:
            idx = self.n
        s = 0
        while idx > 0:
            s += self.tree[idx]
            idx -= idx & (-idx)
        return s

    def range_sum(self, l, r):
        """区间查询 — 求 [l, r] 区间之和
        利用前缀和之差: sum(l,r) = prefix(r) - prefix(l-1)
        复杂度: O(log n)"""
        if l > r:
            return 0
        if l < 1:
            l = 1
        return self.prefix_sum(r) - self.prefix_sum(l - 1)

    def point_query(self, idx):
        """单点查询 — 获取位置 idx 的原始值
        等价于 range_sum(idx, idx)"""
        return self.range_sum(idx, idx)

# 定义 fenwick_tree_operations 函数
def fenwick_tree_operations():
    data = [2, 5, 1, 4, 8, 3, 7, 6]
    ft = FenwickTree(len(data))
    for i, val in enumerate(data, 1):
        ft.update(i, val)
