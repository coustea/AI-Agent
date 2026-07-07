class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def rob(root):
    def dfs(node):
        if not node:
            return (0, 0) # (rob_this, not_rob_this)
        left = dfs(node.left)
        right = dfs(node.right)
        # If we rob this node, we cannot rob its children
        rob_val = node.val + left[1] + right[1]
        # If we don't rob this node, we can choose to rob or not rob its children
        not_rob_val = max(left) + max(right)
        return (rob_val, not_rob_val)
        
    root = TreeNode(3, TreeNode(2, None, TreeNode(3)), TreeNode(3, None, TreeNode(1)))
    return max(dfs(root))

rob(None)
