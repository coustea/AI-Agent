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

    headers = [str(c) for c in range(n)]
    tracer.init_table(headers, rows=n, cols=n, fill_value="", line=1)

    def backtrack(row):
        if row == n:
            res.append(["".join(r) for r in board])
            tracer.finish(line=30)
            return

        for col in range(n):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                tracer.highlight(row, col, tone="conflict", line=42)
                tracer.clear_highlights(line=43)
                continue
            board[row][col] = 'Q'
            cols.add(col)
            diag1.add(row - col)
            diag2.add(row + col)
            tracer.set_value(row, col, "Q", line=45)
            tracer.highlight(row, col, tone="active", line=46)

            backtrack(row + 1)

            board[row][col] = '.'
            cols.remove(col)
            diag1.remove(row - col)
            diag2.remove(row + col)
            tracer.set_value(row, col, "", line=52)
            tracer.clear_highlights(line=53)

    backtrack(0)
    if not res:
        tracer.finish(line=1)
    return res

result = solve_n_queens(8)
print(f"8 皇后问题共 {len(result)} 个解")
for i, sol in enumerate(result[:3]):
    print(f"解 {i+1}:")
    for row in sol:
        print(f"  {row}")
tracer.dump()
