from visual_tracer import TreeTracer

tracer = TreeTracer()


class FenwickTree:
    """树状数组 — 高效的前缀和结构"""

    def __init__(self, size):
        if size <= 0:
            raise ValueError("树状数组大小必须 > 0")
        self.n = size
        self.tree = [0] * (size + 1)

    def update(self, idx, delta):
        if idx < 1 or idx > self.n:
            raise IndexError(f"索引 {idx} 超出范围")
        while idx <= self.n:
            self.tree[idx] += delta
            idx += idx & (-idx)

    def prefix_sum(self, idx):
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
        if l > r:
            return 0
        if l < 1:
            l = 1
        return self.prefix_sum(r) - self.prefix_sum(l - 1)


def lowbit(x):
    return x & (-x)

def build_fenwick_nodes(n, tree):
    nodes = []
    for i in range(1, n + 1):
        children = []
        for j in range(i - lowbit(i) + 1, i):
            if j + lowbit(j) == i:
                children.append(f"node-{j}")
        label = f"{i}:{tree[i]}"
        nodes.append({"id": f"node-{i}", "label": label, "children": children})
    return nodes


ft = FenwickTree(10)
data = [3, 7, 1, 9, 5, 2, 8, 4, 6, 10]
for i, val in enumerate(data, 1):
    ft.update(i, val)

nodes = build_fenwick_nodes(10, ft.tree)
tracer.init_tree(nodes, line=79)

ft2 = FenwickTree(10)

def update_instrumented(i, delta):
    while i <= ft2.n:
        ft2.tree[i] += delta
        tracer.visit_node(f"node-{i}", line=28)
        i += i & (-i)

for i, val in enumerate(data, 1):
    update_instrumented(i, val)

tracer.finish(line=81)
tracer.dump()
