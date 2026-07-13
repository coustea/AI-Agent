from visual_tracer import TreeTracer
tracer = TreeTracer()

# trie_string_search 算法实现 — domain: string_structure
class TrieNode:
# 定义 __init__ 函数
    def __init__(self):
        self.children = {}
        self.is_word = False

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

def _build_trie_nodes(root):
    """将 Trie 转换为可视化节点列表"""
    if not root:
        return []
    nodes = []
    counter = [0]

    def dfs(node, label="root"):
        if not node:
            return None
        node_id = f"node-{counter[0]}"
        counter[0] += 1
        node_data = {"id": node_id, "label": label}
        children = []
        for char, child in sorted(node.children.items()):
            child_id = dfs(child, char)
            if child_id:
                children.append(child_id)
        if children:
            node_data["children"] = children
        nodes.append(node_data)
        return node_id

    dfs(root)
    return nodes

# Trie 类定义
class Trie:
# 定义 __init__ 函数
    def __init__(self):
        self.root = TrieNode()

# 定义 insert 函数
    def insert(self, word):
        tracer.move_pointer({"word": word}, line=14)
        if not word:
            self.root.is_word = True
            return
        curr = self.root
        tracer.visit_node(_get_node_id(curr), line=15)
        for char in word:
            tracer.move_pointer({"char": char}, line=20)
            if char not in curr.children:
                curr.children[char] = TrieNode()
            curr = curr.children[char]
            tracer.visit_node(_get_node_id(curr), line=23)
        curr.is_word = True

# 定义 search 函数
    def search(self, word):
        tracer.move_pointer({"word": word}, line=26)
        if not word:
            return self.root.is_word
        curr = self.root
        tracer.visit_node(_get_node_id(curr), line=27)
        for char in word:
            tracer.move_pointer({"char": char}, line=31)
            if char not in curr.children:
                return False
            curr = curr.children[char]
            tracer.visit_node(_get_node_id(curr), line=34)
        return curr.is_word

# 定义 trie_search 函数
def trie_search(words, queries=()):
    global _node_counter, _node_map
    _node_counter = [0]
    _node_map = {}

    t = Trie()

    # 初始化可视化
    nodes = _build_trie_nodes(t.root)
    tracer.init_tree(nodes, line=38)

    for w in words:
        tracer.move_pointer({"insert": w}, line=40)
        t.insert(w)
        # 更新可视化
        nodes = _build_trie_nodes(t.root)
        tracer.init_tree(nodes, line=42)

    for query in queries:
        tracer.move_pointer({"search": query}, line=43)
        t.search(query)

    tracer.finish(line=42)
    return {query: t.search(query) for query in queries}