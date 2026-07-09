"""
图的深度优先搜索 (DFS) — 含环检测与发现/完成时间
=====================================================

【算法概述】
DFS 是图论中最基础的遍历算法之一，沿着每条分支尽可能深入后再回溯。
本实现使用三色标记法 (WHITE/GRAY/BLACK) 进行环检测：
  - WHITE (0): 未访问
  - GRAY  (1): 正在访问（已发现但尚未完成）
  - BLACK (2): 已完成（所有后代均已处理）

【环检测原理】
当 DFS 遍历到一条边 (u, v) 时：
  - 若 v 为 GRAY，则 v 是 u 的祖先，(u,v) 是后向边 (back edge)，说明存在环
  - 若 v 为 WHITE，则递归访问 v
  - 若 v 为 BLACK，则 v 已处理完毕，(u,v) 是横叉边或前向边，无环

【时间复杂度】O(V + E)，每个顶点和每条边仅被处理一次
【空间复杂度】O(V)，递归栈深度最多为 V

【递归 vs 迭代】
递归实现代码简洁，自然表达回溯语义，但深度过大时可能栈溢出。
迭代实现用显式栈模拟，可避免栈溢出，但代码稍复杂。
本模板采用递归实现，更直观地展示 DFS 的回溯过程。
"""


graph = {
    0: [1, 2],
    1: [3, 4],
    2: [0, 5],
    3: [],
    4: [6],
    5: [6],
    6: [2],
}

labels = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G"}

WHITE, GRAY, BLACK = 0, 1, 2
color = [WHITE] * 7

discovery = [0] * 7
finish = [0] * 7
time = 0

has_cycle = False
back_edges = []

def dfs(node):
    """递归 DFS，同时进行环检测并记录发现/完成时间。"""
    global time, has_cycle

    color[node] = GRAY
    time += 1
    discovery[node] = time

    for neighbor in graph[node]:
        if color[neighbor] == WHITE:
            dfs(neighbor)
        elif color[neighbor] == GRAY:
            has_cycle = True
            back_edges.append((labels[node], labels[neighbor]))

    color[node] = BLACK
    time += 1
    finish[node] = time

for node in range(7):
    if color[node] == WHITE:
        dfs(node)

print("DFS 遍历完成")
print(f"发现时间: {discovery}")
print(f"完成时间: {finish}")
print(f"是否存在环: {'是' if has_cycle else '否'}")
if back_edges:
    print(f"后向边（环的来源）: {back_edges}")
