const graph = {
  0: [1, 2],
  1: [0, 3, 4],
  2: [0, 5],
  3: [1],
  4: [1],
  5: [2]
};
const visited = new Array(6).fill(false);

function dfs(node) {
  visited[node] = true;
  for (const nextNode of graph[node]) {
    if (!visited[nextNode]) {
      dfs(nextNode);
    }
  }
}

dfs(0);