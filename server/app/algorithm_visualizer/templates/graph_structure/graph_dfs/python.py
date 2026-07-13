"""
# graph_dfs 算法实现 — domain: graph_structure
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


def dfs_graph(num_nodes, edges, start=0):
    """递归 DFS，返回遍历顺序和无向图环检测结果。"""
    graph = {node: [] for node in range(num_nodes)}
    for left, right, *_ in edges:
        graph[left].append(right)
        graph[right].append(left)

    visited = [False] * num_nodes
    order = []
    back_edges = []

    def visit(node, parent):
        visited[node] = True
        order.append(node)
        for neighbor in graph[node]:
            if not visited[neighbor]:
                visit(neighbor, node)
            elif neighbor != parent and [neighbor, node] not in back_edges:
                back_edges.append([node, neighbor])

    if 0 <= start < num_nodes:
        visit(start, -1)

    return {
        "order": order,
        "has_cycle": bool(back_edges),
        "back_edges": back_edges,
    }
