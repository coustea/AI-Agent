# huffman_coding 算法实现 — domain: greedy
import heapq

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

# 定义 build_huffman_tree 函数
def build_huffman_tree(char_freq):
    heap = [HuffmanNode(ch, f) for ch, f in char_freq]
    heapq.heapify(heap)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        merged = HuffmanNode(freq=left.freq + right.freq, left=left, right=right)
        heapq.heappush(heap, merged)
    return heap[0] if heap else None

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

char_freq = [('a', 45), ('b', 13), ('c', 12), ('d', 16), ('e', 9), ('f', 5)]
tree = build_huffman_tree(char_freq)
codes = build_codes(tree)
encoded = encode("abcdef", codes)
decoded = decode(encoded, tree)
assert decoded == "abcdef"

ratio = compression_ratio("aabbccddeeff", codes)
