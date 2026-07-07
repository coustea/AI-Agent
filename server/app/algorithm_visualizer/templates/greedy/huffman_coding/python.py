import heapq

class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None
        
    def __lt__(self, other):
        return self.freq < other.freq

def build_huffman_tree(char_freqs):
    pq = [HuffmanNode(char, freq) for char, freq in char_freqs.items()]
    heapq.heapify(pq)
    
    while len(pq) > 1:
        left = heapq.heappop(pq)
        right = heapq.heappop(pq)
        parent = HuffmanNode(None, left.freq + right.freq)
        parent.left = left
        parent.right = right
        heapq.heappush(pq, parent)
        
    return pq[0]

build_huffman_tree({'a': 5, 'b': 9, 'c': 12, 'd': 13, 'e': 16, 'f': 45})
