from visual_tracer import TreeTracer

tracer = TreeTracer()


# SegmentTree 类定义
class SegmentTree:
    """线段树 — 支持区间求和、单点更新、区间查询"""

# 定义 __init__ 函数
    def __init__(self, arr):
        if not arr:
            raise ValueError("输入数组不能为空")
        self.n = len(arr)
        self.tree = [0] * (4 * self.n)
        self._build(arr, 0, 0, self.n - 1)

# 定义 _build 函数
    def _build(self, arr, node, start, end):
        if start == end:
            self.tree[node] = arr[start]
            return
        mid = (start + end) // 2
        left_child = 2 * node + 1
        right_child = 2 * node + 2
        self._build(arr, left_child, start, mid)
        self._build(arr, right_child, mid + 1, end)
        self.tree[node] = self.tree[left_child] + self.tree[right_child]

# 定义 update 函数
    def update(self, idx, val):
        if idx < 0 or idx >= self.n:
            raise IndexError(f"索引 {idx} 超出范围")
        self._update(0, 0, self.n - 1, idx, val)

# 定义 _update 函数
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

# 定义 query 函数
    def query(self, l, r):
        if l < 0 or r >= self.n or l > r:
            raise IndexError(f"查询区间 [{l}, {r}] 无效")
        return self._query(0, 0, self.n - 1, l, r)

# 定义 _query 函数
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

# 定义 find_max_node 函数
def find_max_node(st_obj, node, start, end):
    if start == end:
        return node
    mid = (start + end) // 2
    left_max = find_max_node(st_obj, 2 * node + 1, start, mid)
    right_max = find_max_node(st_obj, 2 * node + 2, mid + 1, end)
    return max(left_max, right_max)

max_node = find_max_node(st, 0, 0, st.n - 1)

nodes = []
# 循环遍历处理
for i in range(max_node + 1):
    children = []
    left = 2 * i + 1
    right = 2 * i + 2
    if left <= max_node:
        children.append(f"node-{left}")
    if right <= max_node:
        children.append(f"node-{right}")
    label = str(st.tree[i])
    nodes.append({"id": f"node-{i}", "label": label, "children": children})

tracer.init_tree(nodes, line=87)

# 定义 visit_build 函数
def visit_build(node, start, end):
    tracer.visit_node(f"node-{node}", line=19)
    if start == end:
        return
    mid = (start + end) // 2
    visit_build(2 * node + 1, start, mid)
    visit_build(2 * node + 2, mid + 1, end)

visit_build(0, 0, st.n - 1)

tracer.finish(line=87)
tracer.dump()
