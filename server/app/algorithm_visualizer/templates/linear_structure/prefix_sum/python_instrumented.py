from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# prefix_sum 算法实现 — domain: linear_structure
class PrefixSum:
# 定义 __init__ 函数
    def __init__(self, arr):
        n = len(arr)
        tracer.init_array(arr, line=4)
        if n == 0:
            self.prefix = [0]
            self._arr = []
            tracer.finish(line=8)
            return
        self.prefix = [0] * (n + 1)
        tracer.init_array(self.prefix, line=10)
        for i in range(n):
            tracer.move_pointer({"i": i}, line=12)
            self.prefix[i + 1] = self.prefix[i] + arr[i]
            tracer.assign(i + 1, self.prefix[i + 1], line=12)
        self._arr = arr

# 定义 range_query 函数
    def range_query(self, left, right):
        tracer.move_pointer({"left": left, "right": right}, line=16)
        if left < 0 or right >= len(self._arr) or left > right:
            tracer.finish(line=18)
            return 0
        tracer.highlight(left, tone="active", line=19)
        tracer.highlight(right + 1, tone="active", line=19)
        result = self.prefix[right + 1] - self.prefix[left]
        tracer.clear_highlights(line=19)
        tracer.finish(line=19)
        return result

# 定义 prefix_at 函数
    def prefix_at(self, index):
        tracer.move_pointer({"index": index}, line=22)
        if index < 0 or index > len(self._arr):
            tracer.finish(line=24)
            return 0
        tracer.highlight(index, tone="active", line=25)
        tracer.clear_highlights(line=25)
        tracer.finish(line=25)
        return self.prefix[index]

# PrefixSum2D 类定义
class PrefixSum2D:
# 定义 __init__ 函数
    def __init__(self, grid):
        from visual_tracer import DpTableTracer
        global tracer
        tracer = DpTableTracer()

        if not grid or not grid[0]:
            self.prefix = [[0]]
            self._grid = []
            tracer.finish(line=33)
            return
        m, n = len(grid), len(grid[0])
        headers = [str(j) for j in range(n + 1)]
        tracer.init_table(headers, [[0] * (n + 1) for _ in range(m + 1)], m + 1, n + 1, fill_value=0, line=36)
        self.prefix = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            tracer.move_pointer({"row": i}, line=38)
            for j in range(n):
                tracer.move_pointer({"col": j}, line=39)
                self.prefix[i + 1][j + 1] = (grid[i][j]
                    + self.prefix[i][j + 1]
                    + self.prefix[i + 1][j]
                    - self.prefix[i][j])
                tracer.set_value(i + 1, j + 1, self.prefix[i + 1][j + 1], line=42)
        self._grid = grid

# 定义 range_query 函数
    def range_query(self, r1, c1, r2, c2):
        tracer.move_pointer({"r1": r1, "c1": c1, "r2": r2, "c2": c2}, line=46)
        tracer.highlight(r2 + 1, c2 + 1, tone="active", line=47)
        tracer.highlight(r1, c2 + 1, tone="danger", line=48)
        tracer.highlight(r2 + 1, c1, tone="danger", line=49)
        tracer.highlight(r1, c1, tone="active", line=50)
        result = (self.prefix[r2 + 1][c2 + 1]
            - self.prefix[r1][c2 + 1]
            - self.prefix[r2 + 1][c1]
            + self.prefix[r1][c1])
        tracer.clear_highlights(line=50)
        tracer.finish(line=50)
        return result

# 定义 range_sum_brute 函数
def range_sum_brute(arr, left, right):
    tracer.init_array(arr, line=53)
    tracer.move_pointer({"left": left, "right": right}, line=54)
    for i in range(left, right + 1):
        tracer.highlight(i, tone="active", line=54)
    tracer.clear_highlights(line=54)
    tracer.finish(line=54)
    return sum(arr[left:right + 1])

# 定义 prefix_sum_operations 函数
def prefix_sum_operations(arr):
    ps = PrefixSum(arr)
    ps.range_query(1, 3)
    tracer.finish(line=59)