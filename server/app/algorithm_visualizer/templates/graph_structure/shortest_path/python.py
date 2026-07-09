"""
Dijkstra 最短路径算法 — 带权有向图
=====================================
核心思想：贪心策略，每次从优先队列中取出当前距离最小的未访问节点，
         对其所有出边执行松弛操作（relaxation）。

时间复杂度：O((V + E) log V)，其中 V 为节点数，E 为边数。
           使用二叉堆（heapq）实现优先队列，每次取最小值 O(log V)，
           每条边最多触发一次松弛入队 O(E log V)，合计 O((V+E) log V)。

空间复杂度：O(V + E)，存储距离表、前驱表和优先队列。

性质：
  1. 仅适用于非负权边（负权边会导致贪心选择失效）。
  2. 每个节点最多被"确定"一次（取出时距离已是最优）。
  3. 优先队列中可能存在同一节点的多个距离副本，通过
     curr_dist > distances[u] 判断跳过已过时条目。
"""

import heapq


def dijkstra(graph, source, num_nodes):
    """Dijkstra 最短路径算法，返回距离表和前驱表。

    Args:
        graph: 邻接表，格式 {u: [(v, weight), ...]}
        source: 源节点编号
        num_nodes: 节点总数

    Returns:
        distances: 各节点到源的最短距离（不可达为 inf）
        predecessors: 最短路径前驱表（用于路径重建）
    """

    distances = {i: float('inf') for i in range(num_nodes)}
    distances[source] = 0

    predecessors = {i: None for i in range(num_nodes)}

    pq = [(0, source)]

    while pq:
        curr_dist, u = heapq.heappop(pq)

        if curr_dist > distances[u]:
            continue

        for v, weight in graph.get(u, []):
            new_dist = curr_dist + weight

            if new_dist < distances[v]:
                distances[v] = new_dist
                predecessors[v] = u
                heapq.heappush(pq, (new_dist, v))

    unreachable = [i for i in range(num_nodes) if distances[i] == float('inf')]
    if unreachable:
        print(f"不可达节点: {unreachable}")

    return distances, predecessors


def reconstruct_path(predecessors, source, target):
    """根据前驱表重建从 source 到 target 的最短路径。"""
    if predecessors[target] is None and target != source:
        return []

    path = []
    node = target
    while node is not None:
        path.append(node)
        node = predecessors[node]
    path.reverse()
    return path


graph = {
    0: [(1, 2), (2, 6)],
    1: [(3, 5)],
    2: [(3, 2), (4, 3)],
    3: [(5, 1)],
    4: [(5, 4), (6, 2)],
    5: [(6, 3)],
    6: [],
}

distances, predecessors = dijkstra(graph, 0, 7)

labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
print("最短距离:")
for i in range(7):
    d = distances[i]
    d_str = str(d) if d != float('inf') else "∞"
    print(f"  {labels[i]}({i}): {d_str}")

print("\n最短路径:")
for i in range(7):
    path = reconstruct_path(predecessors, 0, i)
    if path:
        path_str = " -> ".join(f"{labels[n]}({n})" for n in path)
        print(f"  A(0) -> {labels[i]}({i}): {path_str}, 距离={distances[i]}")
    else:
        print(f"  A(0) -> {labels[i]}({i}): 不可达")
