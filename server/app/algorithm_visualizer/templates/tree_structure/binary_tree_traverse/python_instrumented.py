from visual_tracer import TreeTracer

tracer = TreeTracer()


class TreeNode:
    """二叉树节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


nodes = []
_counter = [0]

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


root = TreeNode(1,
    TreeNode(2,
        TreeNode(4,
            TreeNode(8),
            TreeNode(9)),
        TreeNode(5,
            TreeNode(10),
            None)),
    TreeNode(3,
        TreeNode(6,
            TreeNode(11,
                TreeNode(14),
                None),
            None),
        TreeNode(7,
            TreeNode(12),
            TreeNode(13,
                None,
                TreeNode(15)))))

build_tree_nodes(root)
tracer.init_tree(nodes, line=57)

_node_id_map = {}
_idx = [0]

def build_id_map(node):
    if not node:
        return
    nid = f"node-{_idx[0]}"
    _idx[0] += 1
    _node_id_map[id(node)] = nid
    build_id_map(node.left)
    build_id_map(node.right)

build_id_map(root)

def preorder_traversal(root):
    """前序遍历: 根 -> 左 -> 右"""
    if not root:
        return []
    tracer.visit_node(_node_id_map[id(root)], line=21)
    result = [root.val]
    result.extend(preorder_traversal(root.left))
    result.extend(preorder_traversal(root.right))
    return result

preorder_traversal(root)
tracer.finish(line=71)
tracer.dump()
