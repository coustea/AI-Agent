# prefix_sum 算法实现 — domain: linear_structure
class PrefixSum:
# 定义 __init__ 函数
    def __init__(self, arr):
        n = len(arr)
        if n == 0:
            self.prefix = [0]
            self._arr = []
            return
        self.prefix = [0] * (n + 1)
        for i in range(n):
            self.prefix[i + 1] = self.prefix[i] + arr[i]
        self._arr = arr

# 定义 range_query 函数
    def range_query(self, left, right):
        if left < 0 or right >= len(self._arr) or left > right:
            return 0
        return self.prefix[right + 1] - self.prefix[left]

# 定义 prefix_at 函数
    def prefix_at(self, index):
        if index < 0 or index > len(self._arr):
            return 0
        return self.prefix[index]

# PrefixSum2D 类定义
class PrefixSum2D:
# 定义 __init__ 函数
    def __init__(self, grid):
        if not grid or not grid[0]:
            self.prefix = [[0]]
            self._grid = []
            return
        m, n = len(grid), len(grid[0])
        self.prefix = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            for j in range(n):
                self.prefix[i + 1][j + 1] = (grid[i][j]
                    + self.prefix[i][j + 1]
                    + self.prefix[i + 1][j]
                    - self.prefix[i][j])
        self._grid = grid

# 定义 range_query 函数
    def range_query(self, r1, c1, r2, c2):
        return (self.prefix[r2 + 1][c2 + 1]
            - self.prefix[r1][c2 + 1]
            - self.prefix[r2 + 1][c1]
            + self.prefix[r1][c1])

# 定义 range_sum_brute 函数
def range_sum_brute(arr, left, right):
    return sum(arr[left:right + 1])

# 定义 prefix_sum_operations 函数
def prefix_sum_operations(arr):
    ps = PrefixSum(arr)
    ps.range_query(1, 3)
