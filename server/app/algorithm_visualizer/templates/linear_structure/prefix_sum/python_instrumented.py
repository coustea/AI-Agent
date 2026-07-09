from visual_tracer import ArrayTracer

tracer = ArrayTracer()

class PrefixSum:
    def __init__(self, arr):
        n = len(arr)
        if n == 0:
            self.prefix = [0]
            self._arr = []
            return
        self.prefix = [0] * (n + 1)
        tracer.init_array(arr, line=4)
        for i in range(n):
            self.prefix[i + 1] = self.prefix[i] + arr[i]
            tracer.assign(i, self.prefix[i + 1], line=10)
        self._arr = arr

    def range_query(self, left, right):
        if left < 0 or right >= len(self._arr) or left > right:
            return 0
        return self.prefix[right + 1] - self.prefix[left]

    def prefix_at(self, index):
        if index < 0 or index > len(self._arr):
            return 0
        return self.prefix[index]

class PrefixSum2D:
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

    def range_query(self, r1, c1, r2, c2):
        return (self.prefix[r2 + 1][c2 + 1]
            - self.prefix[r1][c2 + 1]
            - self.prefix[r2 + 1][c1]
            + self.prefix[r1][c1])

def range_sum_brute(arr, left, right):
    return sum(arr[left:right + 1])

data = [2, 5, -3, 7, 1, 4, 6, -2, 8, 3, 9, -1, 5, -4, 11]
ps = PrefixSum(data)
ps.range_query(2, 8)
ps.range_query(0, 14)
ps.prefix_at(5)

grid = [
    [1, 2, 3, 4, 5],
    [6, 7, 8, 9, 10],
    [11, 12, 13, 14, 15],
    [16, 17, 18, 19, 20],
]
ps2d = PrefixSum2D(grid)
ps2d.range_query(1, 1, 2, 3)
ps2d.range_query(0, 0, 3, 4)
tracer.finish(line=30)
tracer.dump()
