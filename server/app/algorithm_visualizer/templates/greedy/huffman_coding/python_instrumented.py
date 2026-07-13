# huffman_coding 算法实现 — domain: greedy
import heapq
from visual_tracer import TreeTracer

tracer = TreeTracer()

# HuffmanNode 类定义
class HuffmanNode:
# 定义 __init__ 函数
    def __init__(self, char=None, freq=0, left=None, right=None):
        self.char = char
        self.freq = freq
        self.left = left
        self.right = right

# 定义 __lt__ 函数
    def __lt__(self, other):
        return self.freq < other.freq

def _build_huffman_nodes(root):
    """将 HuffmanNode 树转换为可视化节点列表"""
    nodes = []
    counter = [0]
    def dfs(node):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        label = f"{node.char}:{node.freq}" if node.char else f"f={node.freq}"
        node_data = {"id": node_id, "label": label}
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

# 定义 build_huffman_tree 函数
def build_huffman_tree(char_freq):
    heap = [HuffmanNode(ch, f) for ch, f in char_freq]
    heapq.heapify(heap)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
        heapq.heappush(heap, merged)
    root = heap[0] if heap else None
    if root:
        nodes = _build_huffman_nodes(root)
        tracer.init_tree(nodes, line=23)
        _visit_huffman_codes(root)
    tracer.finish(line=23)
    return root

def _visit_huffman_codes(node):
    if node is None:
        return
    node_id = _get_node_id(node)
    tracer.visit_node(node_id, line=26)
    if node.char is not None:
        return
    _visit_huffman_codes(node.left)
    _visit_huffman_codes(node.right)

_node_id_map = {}
_counter = [0]
def _get_node_id(node):
    if node not in _node_id_map:
        _node_id_map[node] = f"node-{_counter[0]}"
        _counter[0] += 1
    return _node_id_map[node]

# 定义 build_codes 函数
def build_codes(node, prefix="", codes=None):
    if codes is None:
        codes = {}
    if node is None:
        return codes
    if node.char is not None:
        codes[node.char] = prefix if prefix else "0"
        return codes
    build_codes(node.left, prefix + "0", codes)
    build_codes(node.right, prefix + "1", codes)
    return codes

# 定义 encode 函数
def encode(text, codes):
    return "".join(codes[ch] for ch in text)

# 定义 decode 函数
def decode(encoded, root):
    result = []
    node = root
    for bit in encoded:
        node = node.left if bit == "0" else node.right
        if node.char is not None:
            result.append(node.char)
            node = root
    return "".join(result)

# 定义 compression_ratio 函数
def compression_ratio(text, codes):
    original_bits = len(text) * 8
    encoded_bits = sum(len(codes[ch]) for ch in text)
    return encoded_bits / original_bits