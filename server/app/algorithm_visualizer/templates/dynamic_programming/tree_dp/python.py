class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def rob(root):
    if not root:
        return 0

    def dfs(node):
        if not node:
            return (0, 0)
        left = dfs(node.left)
        right = dfs(node.right)
        rob_val = node.val + left[1] + right[1]
        not_rob_val = max(left) + max(right)
        return (rob_val, not_rob_val)

    result = max(dfs(root))
    return result

def rob_with_path(root):
    if not root:
        return 0, []

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

def max_path_sum(root):
    max_sum = float('-inf')

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
assert rob(root1) == 14

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
assert rob(root2) == 9

mps = max_path_sum(root2)
assert mps > 0
