from visual_tracer import TreeTracer

tracer = TreeTracer()

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def _build_tree_nodes(root):
    if not root:
        return []
    nodes = []
    counter = [0]
    def dfs(node):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node_data = {"id": node_id, "label": str(node.val)}
        children = []
        if node.left:
            left_id = dfs(node.left)
            if left_id:
                children.append(left_id)
        if node.right:
            right_id = dfs(node.right)
            if right_id:
                children.append(right_id)
        if children:
            node_data["children"] = children
        nodes.append(node_data)
        return node_id
    dfs(root)
    return nodes

def rob(root):
    if not root:
        return 0

    tracer.init_tree(_build_tree_nodes(root), line=3)

    def dfs(node):
        if not node:
            return (0, 0)
        tracer.visit_node(f"node-{id(node)}", line=9)
        left = dfs(node.left)
        right = dfs(node.right)
        rob_val = node.val + left[1] + right[1]
        not_rob_val = max(left) + max(right)
        return (rob_val, not_rob_val)

    result = max(dfs(root))
    tracer.finish(line=15)
    return result

def rob_with_path(root):
    if not root:
        return 0, []

    tracer.init_tree(_build_tree_nodes(root), line=18)

    def dfs(node):
        if not node:
            return (0, 0), []
        tracer.visit_node(f"node-{id(node)}", line=23)
        left_result, left_path = dfs(node.left)
        right_result, right_path = dfs(node.right)
        rob_val = node.val + left_result[1] + right_result[1]
        not_rob_val = max(left_result) + max(right_result)
        return (rob_val, not_rob_val), [node.val] + left_path + right_path

    result, path = dfs(root)
    tracer.finish(line=30)
    return max(result), path

def max_path_sum(root):
    max_sum = float('-inf')

    tracer.init_tree(_build_tree_nodes(root), line=33)

    def dfs(node):
        nonlocal max_sum
        if not node:
            return 0
        tracer.visit_node(f"node-{id(node)}", line=38)
        left = max(0, dfs(node.left))
        right = max(0, dfs(node.right))
        max_sum = max(max_sum, left + right + node.val)
        return max(left, right) + node.val

    dfs(root)
    tracer.finish(line=44)
    return max_sum