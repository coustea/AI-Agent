from visual_tracer import TreeTracer

tracer = TreeTracer()


# TreeNode 类定义
class TreeNode:
    """二叉树节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


nodes = []
_counter = [0]

# 定义 build_tree_nodes 函数
def build_tree_nodes(root):
    if not root:
        return None
    nid = f"node-{_counter[0]}"
    _counter[0] += 1
    children = []
    left_id = build_tree_nodes(root.left)
    if left_id:
        children.append(left_id)
    right_id = build_tree_nodes(root.right)
    if right_id:
        children.append(right_id)
    nodes.append({"id": nid, "label": str(root.val), "children": children})
    return nid


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

build_tree_nodes(root)
tracer.init_tree(nodes, line=55)

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

def max_depth(root):
    """求树的最大深度 — 最基础的递归"""
    if not root:
        return 0
    tracer.visit_node(_node_id_map[id(root)], line=21)
    return 1 + max(max_depth(root.left), max_depth(root.right))

max_depth(root)
tracer.finish(line=71)
tracer.dump()
