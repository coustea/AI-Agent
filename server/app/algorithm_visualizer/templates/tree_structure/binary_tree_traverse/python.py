class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def _build_tree(arr):
    """从数组构建二叉树，返回根节点。"""
    if not arr or arr[0] is None:
        return None
    nodes = [TreeNode(val) if val is not None else None for val in arr]
    child_index = 1
    for node in nodes:
        if node is None:
            continue
        if child_index < len(nodes):
            node.left = nodes[child_index]
            child_index += 1
        if child_index < len(nodes):
            node.right = nodes[child_index]
            child_index += 1
    return nodes[0]


def preorder_traversal(arr):
    """前序遍历：根、左子树、右子树。"""
    root = _build_tree(arr)
    return _preorder(root)


def _preorder(root):
    if root is None:
        return []
    result = [root.val]
    result.extend(_preorder(root.left))
    result.extend(_preorder(root.right))
    return result
