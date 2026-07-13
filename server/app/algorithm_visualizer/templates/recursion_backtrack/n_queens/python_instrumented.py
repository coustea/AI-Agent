from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def solve_n_queens(n):
    """求解 n 皇后问题: 在 n×n 棋盘上放置 n 个互不攻击的皇后

    约束条件:
    - 每行恰好一个皇后
    - 每列最多一个皇后
    - 每条主对角线（row - col = 常数）最多一个皇后
    - 每条副对角线（row + col = 常数）最多一个皇后

    回溯策略:
    - 逐行尝试放置皇后
    - 用 cols/diag1/diag2 集合 O(1) 判断冲突
    - 冲突则跳过（剪枝），不冲突则放置并递归下一行
    - 递归返回后撤销放置（回溯）

    边界处理:
    - n <= 0 返回空列表
    - n = 1 返回 [["Q"]]
    - n = 2, 3 无解
    """
    if n <= 0:
        return []
    if n == 1:
        return [["Q"]]

    res = []
    board = [['.'] * n for _ in range(n)]
    cols = set()
    diag1 = set()
    diag2 = set()

    headers = [str(i) for i in range(n)]
    tracer.init_table(headers, n, n, fill_value=0, line=28)

# 定义 backtrack 函数
    def backtrack(row):
        if row == n:
            res.append(["".join(r) for r in board])
            return

        for col in range(n):
            tracer.clear_highlights(line=35)
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                tracer.highlight(row, col, tone="danger", line=36)
                continue
            tracer.highlight(row, col, tone="active", line=36)
            board[row][col] = 'Q'
            tracer.set_value(row, col, 1, line=37)
            cols.add(col)
            diag1.add(row - col)
            diag2.add(row + col)

            backtrack(row + 1)

            board[row][col] = '.'
            tracer.set_value(row, col, 0, line=43)
            cols.remove(col)
            diag1.remove(row - col)
            diag2.remove(row + col)

    backtrack(0)
    tracer.finish(line=49)
    return res