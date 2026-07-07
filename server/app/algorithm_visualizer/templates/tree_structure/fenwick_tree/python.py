class FenwickTree:
    def __init__(self, size):
        self.tree = [0] * (size + 1)
        
    def update(self, idx, val):
        while idx < len(self.tree):
            self.tree[idx] += val
            idx += idx & (-idx)
            
    def query(self, idx):
        s = 0
        while idx > 0:
            s += self.tree[idx]
            idx -= idx & (-idx)
        return s

ft = FenwickTree(6)
for i, x in enumerate([1, 3, 5, 7, 9, 11]):
    ft.update(i + 1, x)
ft.query(4)
