from visual_tracer import TreeTracer

tracer = TreeTracer()


class TrieNode:
    """字典树节点"""
    def __init__(self):
        self.children = {}
        self.is_end = False


class Trie:
    """字典树实现"""
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        if not word:
            return
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True

    def search(self, word):
        if not word:
            return False
        node = self.root
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end

    def starts_with(self, prefix):
        if not prefix:
            return True
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
        return True

    def delete(self, word):
        if not word:
            return False
        node = self.root
        path = [(self.root, word[0] if word else '')]
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
            path.append((node, char))
        if not node.is_end:
            return False
        if node.children:
            node.is_end = False
            return True
        for i in range(len(path) - 1, 0, -1):
            parent_node, char = path[i - 1][0], path[i][1]
            child_node = path[i][0]
            if child_node.children or child_node.is_end:
                break
            del parent_node.children[char]
        return True


trie = Trie()
words = ["cat", "car", "card", "care", "dog", "deer", "deep", "do"]
for w in words:
    trie.insert(w)

nodes = []
_counter = [0]

def build_trie_nodes(trie_node, label="root"):
    if not trie_node:
        return None
    nid = f"node-{_counter[0]}"
    _counter[0] += 1
    children = []
    for ch in sorted(trie_node.children.keys()):
        child_id = build_trie_nodes(trie_node.children[ch], ch)
        if child_id:
            children.append(child_id)
    display_label = label
    if trie_node.is_end and label != "root":
        display_label = label + "*"
    nodes.append({"id": nid, "label": display_label, "children": children})
    return nid

build_trie_nodes(trie.root)
tracer.init_tree(nodes, line=109)

_node_id_map = {}
_idx = [0]

def build_id_map(trie_node):
    if not trie_node:
        return
    nid = f"node-{_idx[0]}"
    _idx[0] += 1
    _node_id_map[id(trie_node)] = nid
    for ch in sorted(trie_node.children.keys()):
        build_id_map(trie_node.children[ch])

build_id_map(trie.root)

node = trie.root
for ch in "cat":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "car":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "card":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "care":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "dog":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "deer":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "deep":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

node = trie.root
for ch in "do":
    if ch in node.children:
        node = node.children[ch]
        tracer.visit_node(_node_id_map[id(node)], line=25)

tracer.finish(line=131)
tracer.dump()
