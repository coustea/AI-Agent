"""图的广度优先搜索（BFS）—— 含连通分量检测与距离计算
# graph_bfs 算法实现 — domain: graph_structure

BFS 核心思想：从起始节点出发，逐层向外扩展，先访问距离近的节点，再访问距离远的节点。
使用队列（FIFO）保证"先发现、先访问"的顺序。

时间复杂度：O(V + E)，其中 V 为顶点数，E 为边数
  - 每个顶点最多入队/出队一次 → O(V)
  - 每条边最多被检查两次（无向图） → O(E)

空间复杂度：O(V)，visited 集合 + 队列最多存储全部顶点

本示例包含 8 个节点（A-H），其中节点 H（编号7）为孤立节点，
BFS 从节点 0 出发只能访问到连通分量 {0,1,2,3,4,5,6}，
需要额外检测未访问节点并从其出发再次 BFS，从而发现第二个连通分量 {7}。
"""

graph = {
    0: [1, 2, 3],
    1: [0, 4],
    2: [0, 4, 5],
    3: [0, 5],
    4: [1, 2, 6],
    5: [2, 3, 6],
    6: [4, 5],
    7: []
}

labels = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G", 7: "H"}


def bfs(graph, start, visited, distance, parent):
    """从 start: BFS 起始节点编号
    visited: 全局已访问集合（会被修改）
    distance: 全局距离字典（会被修改）
    parent: 全局前驱字典（会被修改）

    返回：本次 BFS 访问到的节点列表（按访问顺序）
    """
    visited.add(start)
    distance[start] = 0
    parent[start] = -1

    queue = [start]
    order = []

    while queue:
        node = queue.pop(0)
        order.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                distance[neighbor] = distance[node] + 1
                parent[neighbor] = node
                queue.append(neighbor)

    return order


def bfs_all_components(graph):
    """对图执行完整 BFS，处理所有连通分量。

    当图存在不连通的部分时，单次 BFS 无法访问全部节点。
    本函数遍历所有节点，对每个未访问节点启动新的 BFS，
    从而检测并记录所有连通分量。

    返回：
        components: 各连通分量的节点列表
        distance: 各节点到其所在分量起始点的最短距离
        parent: 各节点在 BFS 树中的前驱节点
    """
    visited = set()
    distance = {}
    parent = {}
    components = []

    for node in graph:
        if node not in visited:
            component = bfs(graph, node, visited, distance, parent)
            components.append(component)

    return components, distance, parent


components, distance, parent = bfs_all_components(graph)

print(f"连通分量数量: {len(components)}")
for i, comp in enumerate(components):
    labels_str = ", ".join(labels[n] for n in comp)
    print(f"  分量 {i + 1}: [{labels_str}] (节点编号: {comp})")

print("\n节点距离与前驱信息:")
for node in sorted(graph.keys()):
    p = labels.get(parent[node], "无") if parent.get(node) is not None else "无"
    if parent.get(node) == -1:
        p = "无（起始节点）"
    print(f"  节点 {labels[node]}({node}): 距离={distance[node]}, 前驱={p}")

print("\nBFS 层级结构（按距离分组）:")
max_dist = max(distance.values())
for d in range(max_dist + 1):
    level_nodes = [n for n in sorted(graph.keys()) if distance[n] == d]
    labels_str = ", ".join(labels[n] for n in level_nodes)
    print(f"  距离 {d}: [{labels_str}]")
