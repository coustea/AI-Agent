from visual_tracer import TreeTracer

tracer = TreeTracer()


# TreeNode 类定义
class TreeNode:
    """BST 节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def insert(root, val):
    """向 BST 中插入值"""
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    elif val > root.val:
        root.right = insert(root.right, val)
    return root


def search(root, val):
    """在 BST 中搜索值"""
    if not root:
        return False
    if val == root.val:
        return True
    elif val < root.val:
        return search(root.left, val)
    else:
        return search(root.right, val)


def find_min(root):
    """找到 BST 中的最小值节点"""
    while root.left:
        root = root.left
    return root


def delete(root, val):
    """从 BST 中删除值"""
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


# 定义 build_tree_nodes 函数
def build_tree_nodes(root):
    nodes = []
    counter = [0]
# 定义 walk 函数
    def walk(node):
        if not node:
            return None
        nid = f"node-{counter[0]}"
        counter[0] += 1
        children = []
        left_id = walk(node.left)
        if left_id:
            children.append(left_id)
        right_id = walk(node.right)
        if right_id:
            children.append(right_id)
        nodes.append({"id": nid, "label": str(node.val), "children": children})
        return nid
    walk(root)
    return nodes


root = None
values = [50, 30, 70, 20, 40, 60, 80, 10, 35, 65]
# 循环遍历处理
for v in values:
    root = insert(root, v)

nodes = build_tree_nodes(root)
tracer.init_tree(nodes, line=82)

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

build_id_map(root)

# 定义 inorder_visit 函数
def inorder_visit(node):
    if not node:
        return
    inorder_visit(node.left)
    tracer.visit_node(_node_id_map[id(node)], line=77)
    inorder_visit(node.right)

inorder_visit(root)

search(root, 40)
search(root, 55)

root = delete(root, 10)
root = delete(root, 30)
root = delete(root, 80)

tracer.finish(line=97)
tracer.dump()
