class SegmentTree:
    def __init__(self, arr):
        self.n = len(arr)
        self.tree = [0] * (4 * self.n)
        self.build(arr, 0, 0, self.n - 1)
        
    def build(self, arr, node, start, end):
        if start == end:
            self.tree[node] = arr[start]
            return
        mid = (start + end) // 2
        left_node = 2 * node + 1
        right_node = 2 * node + 2
        self.build(arr, left_node, start, mid)
        self.build(arr, right_node, mid + 1, end)
        self.tree[node] = self.tree[left_node] + self.tree[right_node]

st = SegmentTree([1, 3, 5, 7, 9, 11])
