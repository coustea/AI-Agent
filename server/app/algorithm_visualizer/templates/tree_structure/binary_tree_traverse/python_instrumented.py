from visual_tracer import TreeTracer
tracer = TreeTracer()

# binary_tree_traverse 算法实现 — domain: tree_structure
class TreeNode:
    """二叉树节点定义"""
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def _build_tree_nodes(root, counter=None):
    """将二叉树转换为可视化节点列表"""
    if counter is None:
        counter = [0]
    if not root:
        return None
    node_id = f"node-{counter[0]}"
    counter[0] += 1
    node_data = {"id": node_id, "label": str(root.val)}
    children = []
    if root.left:
        left_id = _build_tree_nodes(root.left, counter)
        if left_id:
            children.append(left_id)
    if root.right:
        right_id = _build_tree_nodes(root.right, counter)
        if right_id:
            children.append(right_id)
    if children:
        node_data["children"] = children
    return node_id, node_data


def _collect_nodes(root, nodes, counter):
    """收集所有节点"""
    if not root:
        return None
    node_id, node_data = _build_tree_nodes(root, counter)
    nodes.append(node_data)
    return node_id


_node_counter = [0]
_node_map = {}


def _get_node_id(node):
    """获取节点的可视化 ID"""
    if node not in _node_map:
        _node_map[node] = f"node-{_node_counter[0]}"
        _node_counter[0] += 1
    return _node_map[node]


def preorder_traversal(root):
    """前序遍历: 根 -> 左 -> 右
    常用于: 树的序列化、表达式前缀表示"""
    if not root:
        return []
    nodes = []
    counter = [0]

    def build_nodes(node):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node_data = {"id": node_id, "label": str(node.val)}
        children = []
        if node.left:
            left_id = build_nodes(node.left)
            if left_id:
                children.append(left_id)
        if node.right:
            right_id = build_nodes(node.right)
            if right_id:
                children.append(right_id)
        if children:
            node_data["children"] = children
        nodes.append(node_data)
        return node_id

    build_nodes(root)
    tracer.init_tree(nodes, line=10)

    def dfs(node):
        if not node:
            return []
        node_id = _get_node_id(node)
        tracer.visit_node(node_id, line=15)
        result = [node.val]
        result.extend(dfs(node.left))
        result.extend(dfs(node.right))
        return result

    result = dfs(root)
    tracer.finish(line=18)
    return result


def inorder_traversal(root):
    """中序遍历: 左 -> 根 -> 右
    常用于: BST 中序遍历得到有序序列"""
    if not root:
        return []
    nodes = []
    counter = [0]

    def build_nodes(node):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node_data = {"id": node_id, "label": str(node.val)}
        children = []
        if node.left:
            left_id = build_nodes(node.left)
            if left_id:
                children.append(left_id)
        if node.right:
            right_id = build_nodes(node.right)
            if right_id:
                children.append(right_id)
        if children:
            node_data["children"] = children
        nodes.append(node_data)
        return node_id

    build_nodes(root)
    tracer.init_tree(nodes, line=21)

    def dfs(node):
        if not node:
            return []
        result = dfs(node.left)
        node_id = _get_node_id(node)
        tracer.visit_node(node_id, line=27)
        result.append(node.val)
        result.extend(dfs(node.right))
        return result

    result = dfs(root)
    tracer.finish(line=30)
    return result


def postorder_traversal(root):
    """后序遍历: 左 -> 右 -> 根
    常用于: 释放树内存、计算目录大小"""
    if not root:
        return []
    nodes = []
    counter = [0]

    def build_nodes(node):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node_data = {"id": node_id, "label": str(node.val)}
        children = []
        if node.left:
            left_id = build_nodes(node.left)
            if left_id:
                children.append(left_id)
        if node.right:
            right_id = build_nodes(node.right)
            if right_id:
                children.append(right_id)
        if children:
            node_data["children"] = children
        nodes.append(node_data)
        return node_id

    build_nodes(root)
    tracer.init_tree(nodes, line=32)

    def dfs(node):
        if not node:
            return []
        result = dfs(node.left)
        result.extend(dfs(node.right))
        node_id = _get_node_id(node)
        tracer.visit_node(node_id, line=39)
        result.append(node.val)
        return result

    result = dfs(root)
    tracer.finish(line=40)
    return result


def levelorder_traversal(root):
    """层序遍历: 逐层从左到右访问 (BFS)
    常用于: 求树的最大宽度、按层处理节点"""
    if not root:
        return []
    from collections import deque

    nodes = []
    counter = [0]

    def build_nodes(node):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node_data = {"id": node_id, "label": str(node.val)}
        children = []
        if node.left:
            left_id = build_nodes(node.left)
            if left_id:
                children.append(left_id)
        if node.right:
            right_id = build_nodes(node.right)
            if right_id:
                children.append(right_id)
        if children:
            node_data["children"] = children
        nodes.append(node_data)
        return node_id

    build_nodes(root)
    tracer.init_tree(nodes, line=43)

    result = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        node_id = _get_node_id(node)
        tracer.visit_node(node_id, line=52)
        result.append(node.val)
        if node.left:
            queue.append(node.left)
        if node.right:
            queue.append(node.right)

    tracer.finish(line=58)
    return result
