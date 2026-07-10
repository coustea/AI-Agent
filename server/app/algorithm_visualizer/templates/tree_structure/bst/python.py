# bst 算法实现 — domain: tree_structure
class TreeNode:
    """BST 节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def insert(root, val):
    """向 BST 中插入值 — 递归找到正确位置
    若 val < 当前节点，插入左子树；否则插入右子树
    时间复杂度: O(h)，h 为树高"""
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    elif val > root.val:
        root.right = insert(root.right, val)
    return root


def search(root, val):
    """在 BST 中搜索值 — 类似二分查找
    找到返回 True，否则返回 False
    时间复杂度: O(h)"""
    if not root:
        return False
    if val == root.val:
        return True
    elif val < root.val:
        return search(root.left, val)
    else:
        return search(root.right, val)


def find_min(root):
    """找到 BST 中的最小值节点 — 一直往左走
    用于删除操作中寻找后继节点"""
    while root.left:
        root = root.left
    return root


def delete(root, val):
    """从 BST 中删除值 — 三种情况:
    1. 叶子节点: 直接删除
    2. 只有一个子节点: 用子节点替代
    3. 两个子节点: 用中序后继替代，再递归删除后继
    时间复杂度: O(h)"""
    if not root:
        return None
    if val < root.val:
        root.left = delete(root.left, val)
    elif val > root.val:
        root.right = delete(root.right, val)
    else:
        if not root.left and not root.right:
            return None
        elif not root.left:
            return root.right
        elif not root.right:
            return root.left
        else:
            successor = find_min(root.right)
            root.val = successor.val
            root.right = delete(root.right, successor.val)
    return root


def inorder(root):
    """中序遍历 BST — 得到升序序列，验证 BST 正确性"""
    if not root:
        return []
    return inorder(root.left) + [root.val] + inorder(root.right)


root = None
values = [50, 30, 70, 20, 40, 60, 80, 10, 35, 65]
for v in values:
    root = insert(root, v)

sorted_result = inorder(root)

found_40 = search(root, 40)
found_55 = search(root, 55)

root = delete(root, 10)
root = delete(root, 30)
root = delete(root, 80)

after_delete = inorder(root)
