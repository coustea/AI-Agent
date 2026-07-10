from visual_tracer import TreeTracer

tracer = TreeTracer()

# TreeNode 类定义
class TreeNode:
# 定义 __init__ 函数
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

root1 = TreeNode(3,
    TreeNode(2,
        None,
        TreeNode(3,
            TreeNode(4),
            TreeNode(5)
        )
    ),
    TreeNode(3,
        None,
        TreeNode(1)
    )
)

_nodes = []
_counter = [0]

# 定义 build_tree_nodes 函数
def build_tree_nodes(node):
    if not node:
        return None
    nid = f"node-{_counter[0]}"
    _counter[0] += 1
    children = []
    left_id = build_tree_nodes(node.left)
    if left_id:
        children.append(left_id)
    right_id = build_tree_nodes(node.right)
    if right_id:
        children.append(right_id)
    _nodes.append({"id": nid, "label": str(node.val), "children": children})
    return nid

build_tree_nodes(root1)
tracer.init_tree(_nodes, line=7)

_node_id_map = {}
_idx = [0]

# 定义 build_id_map 函数
def build_id_map(node):
    if not node:
        return
    nid = f"node-{_idx[0]}"
    _idx[0] += 1
    _node_id_map[id(node)] = nid
    build_id_map(node.left)
    build_id_map(node.right)

build_id_map(root1)

# 定义 rob 函数
def rob(root):
    if not root:
        return 0

# 定义 dfs 函数
    def dfs(node):
        if not node:
            return (0, 0)
        tracer.visit_node(_node_id_map[id(node)], line=35)
        left = dfs(node.left)
        right = dfs(node.right)
        rob_val = node.val + left[1] + right[1]
        not_rob_val = max(left) + max(right)
        return (rob_val, not_rob_val)

    result = max(dfs(root))
    return result

# 定义 rob_with_path 函数
def rob_with_path(root):
    if not root:
        return 0, []

# 定义 dfs 函数
    def dfs(node):
        if not node:
            return (0, 0), []
        left_result, left_path = dfs(node.left)
        right_result, right_path = dfs(node.right)
        rob_val = node.val + left_result[1] + right_result[1]
        not_rob_val = max(left_result) + max(right_result)
        return (rob_val, not_rob_val), [node.val] + left_path + right_path

    result, path = dfs(root)
    return max(result), path

# 定义 max_path_sum 函数
def max_path_sum(root):
    max_sum = float('-inf')

# 定义 dfs 函数
    def dfs(node):
        nonlocal max_sum
        if not node:
            return 0
        left = max(0, dfs(node.left))
        right = max(0, dfs(node.right))
        max_sum = max(max_sum, left + right + node.val)
        return max(left, right) + node.val

    dfs(root)
    return max_sum

rob(root1)

root2 = TreeNode(3,
    TreeNode(4,
        TreeNode(1),
        TreeNode(3)
    ),
    TreeNode(5,
        None,
        TreeNode(1)
    )
)
rob_with_path(root2)
max_path_sum(root2)
tracer.finish(line=70)
tracer.dump()
