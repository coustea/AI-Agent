# binary_tree_recursion 算法实现 — domain: tree_structure
class TreeNode:
    """二叉树节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def max_depth(root):
    """求树的最大深度 — 最基础的递归
    递推: depth = 1 + max(左子树深度, 右子树深度)
    边界: 空树深度为 0"""
    if not root:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))


def count_nodes(root):
    """统计节点总数
    递推: count = 1 + 左子树节点数 + 右子树节点数
    边界: 空树节点数为 0"""
    if not root:
        return 0
    return 1 + count_nodes(root.left) + count_nodes(root.right)


def has_path_sum(root, target):
    """判断是否存在 根到叶子 路径，使路径上节点值之和等于 target
    递推: 在子树中寻找 target - root.val
    边界: 叶子节点时判断剩余值是否恰好为 0"""
    if not root:
        return False
    if not root.left and not root.right:
        return root.val == target
    remaining = target - root.val
    return has_path_sum(root.left, remaining) or has_path_sum(root.right, remaining)


def invert_tree(root):
    """翻转二叉树 (镜像) — 经典递归操作
    递推: 交换左右子树，再分别翻转左右子树
    边界: 空树无需翻转"""
    if not root:
        return None
    root.left, root.right = root.right, root.left
    invert_tree(root.left)
    invert_tree(root.right)
    return root


def is_balanced(root):
    """判断是否为平衡二叉树 (左右子树高度差 <= 1)
    利用辅助函数同时返回高度和平衡状态，避免重复计算
    时间复杂度: O(n)"""
# 定义 check 函数
    def check(node):
        if not node:
            return 0, True
        left_h, left_bal = check(node.left)
        right_h, right_bal = check(node.right)
        height = 1 + max(left_h, right_h)
        balanced = left_bal and right_bal and abs(left_h - right_h) <= 1
        return height, balanced
    _, result = check(root)
    return result


root = TreeNode(5,
    TreeNode(3,
        TreeNode(1,
            TreeNode(0),
            TreeNode(2)),
        TreeNode(4)),
    TreeNode(8,
        TreeNode(7,
            TreeNode(6),
            None),
        TreeNode(10,
            TreeNode(9),
            TreeNode(12,
                TreeNode(11),
                None))))

depth = max_depth(root)
total = count_nodes(root)
path_ok = has_path_sum(root, 9)
balanced = is_balanced(root)
invert_tree(root)
