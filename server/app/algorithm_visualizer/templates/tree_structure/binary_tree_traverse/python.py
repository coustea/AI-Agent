# binary_tree_traverse 算法实现 — domain: tree_structure
class TreeNode:
    """二叉树节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def preorder_traversal(root):
    """前序遍历: 根 -> 左 -> 右
    常用于: 树的序列化、表达式前缀表示"""
    if not root:
        return []
    result = [root.val]
    result.extend(preorder_traversal(root.left))
    result.extend(preorder_traversal(root.right))
    return result


def inorder_traversal(root):
    """中序遍历: 左 -> 根 -> 右
    常用于: BST 中序遍历得到有序序列"""
    if not root:
        return []
    result = inorder_traversal(root.left)
    result.append(root.val)
    result.extend(inorder_traversal(root.right))
    return result


def postorder_traversal(root):
    """后序遍历: 左 -> 右 -> 根
    常用于: 释放树内存、计算目录大小"""
    if not root:
        return []
    result = postorder_traversal(root.left)
    result.extend(postorder_traversal(root.right))
    result.append(root.val)
    return result


def levelorder_traversal(root):
    """层序遍历: 逐层从左到右访问 (BFS)
    常用于: 求树的最大宽度、按层处理节点"""
    if not root:
        return []
    from collections import deque
    result = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        result.append(node.val)
        if node.left:
            queue.append(node.left)
        if node.right:
            queue.append(node.right)
    return result
