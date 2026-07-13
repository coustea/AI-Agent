from visual_tracer import TreeTracer
tracer = TreeTracer()

# bst 算法实现 — domain: tree_structure
class TreeNode:
    """BST 节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


_node_counter = [0]
_node_map = {}


def _get_node_id(node):
    """获取节点的可视化 ID"""
    if node is None:
        return None
    if node not in _node_map:
        _node_map[node] = f"node-{_node_counter[0]}"
        _node_counter[0] += 1
    return _node_map[node]


def _build_bst_nodes(root, counter=None):
    """将 BST 转换为可视化节点列表"""
    if counter is None:
        counter = [0]
    if not root:
        return []
    nodes = []

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
    node_id = _get_node_id(root)
    tracer.visit_node(node_id, line=29)
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
        node_id = _get_node_id(root)
        tracer.visit_node(node_id, line=41)
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
    node_id = _get_node_id(root)
    tracer.visit_node(node_id, line=53)
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


# 定义 bst_operations 函数
def bst_operations(arr):
    global _node_counter, _node_map
    _node_counter = [0]
    _node_map = {}

    root = None
    for v in arr:
        root = insert(root, v)

    nodes = _build_bst_nodes(root)
    tracer.init_tree(nodes, line=78)

    for v in arr[:1] if arr else []:
        search(root, v)

    if arr:
        root = delete(root, arr[0])

    tracer.finish(line=85)
    return root
