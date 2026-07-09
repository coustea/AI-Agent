from visual_tracer import TreeTracer
import heapq

tracer = TreeTracer()

class HuffmanNode:
    def __init__(self, char=None, freq=0, left=None, right=None):
        self.char = char
        self.freq = freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(char_freq):
    heap = [HuffmanNode(ch, f) for ch, f in char_freq]
    heapq.heapify(heap)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
        heapq.heappush(heap, merged)
    return heap[0] if heap else None

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

def tree_to_tracer_nodes(node, counter=[0]):
    if node is None:
        return None
    nid = f"node-{counter[0]}"
    counter[0] += 1
    label = f"{node.char}:{node.freq}" if node.char else str(node.freq)
    children = []
    left_id = tree_to_tracer_nodes(node.left, counter)
    if left_id:
        children.append(left_id)
    right_id = tree_to_tracer_nodes(node.right, counter)
    if right_id:
        children.append(right_id)
    tracer._nodes.append({"id": nid, "label": label, "children": children})
    return nid

def encode(text, codes):
    return "".join(codes[ch] for ch in text)

def decode(encoded, root):
    result = []
    node = root
    for bit in encoded:
        node = node.left if bit == "0" else node.right
        if node.char is not None:
            result.append(node.char)
            node = root
    return "".join(result)

def compression_ratio(text, codes):
    original_bits = len(text) * 8
    encoded_bits = sum(len(codes[ch]) for ch in text)
    return encoded_bits / original_bits

char_freq = [('a', 45), ('b', 13), ('c', 12), ('d', 16), ('e', 9), ('f', 5)]
tree = build_huffman_tree(char_freq)
counter = [0]
tracer._nodes = []
tree_to_tracer_nodes(tree, counter)
tracer.init_tree(tracer._nodes, line=25)
for n in tracer._nodes:
    tracer.visit_node(n["id"], line=27)
codes = build_codes(tree)
encoded = encode("abcdef", codes)
decoded = decode(encoded, tree)
assert decoded == "abcdef"

ratio = compression_ratio("aabbccddeeff", codes)
tracer.finish(line=72)
tracer.dump()
