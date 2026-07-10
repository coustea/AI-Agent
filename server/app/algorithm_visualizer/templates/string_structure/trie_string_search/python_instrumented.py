from visual_tracer import TreeTracer

tracer = TreeTracer()


# TrieNode 类定义
class TrieNode:
# 定义 __init__ 函数
    def __init__(self):
        self.children = {}
        self.is_word = False

# Trie 类定义
class Trie:
# 定义 __init__ 函数
    def __init__(self):
        self.root = TrieNode()

# 定义 insert 函数
    def insert(self, word):
        if not word:
            self.root.is_word = True
            return
        curr = self.root
# 循环遍历处理
        for char in word:
            if char not in curr.children:
                curr.children[char] = TrieNode()
            curr = curr.children[char]
        curr.is_word = True

# 定义 search 函数
    def search(self, word):
        if not word:
            return self.root.is_word
        curr = self.root
# 循环遍历处理
        for char in word:
            if char not in curr.children:
                return False
            curr = curr.children[char]
        return curr.is_word

t = Trie()
t.insert("algorithm")
t.insert("algo")
t.insert("align")
t.insert("all")
t.insert("also")
t.insert("tree")
t.insert("trie")
t.insert("")

nodes = []
_counter = [0]

def build_trie_nodes(trie_node, label="root"):
    """递归构建 tracer 节点列表，按字符排序保证确定性顺序。"""
    if not trie_node:
        return None
    nid = f"node-{_counter[0]}"
    _counter[0] += 1
    children = []
# 循环遍历处理
    for ch in sorted(trie_node.children.keys()):
        child_id = build_trie_nodes(trie_node.children[ch], ch)
        if child_id:
            children.append(child_id)
    display_label = label
    if trie_node.is_word and label != "root":
        display_label = label + "*"
    nodes.append({"id": nid, "label": display_label, "children": children})
    return nid

build_trie_nodes(t.root)
tracer.init_tree(nodes, line=51)

_node_id_map = {}
_idx = [0]

def build_id_map(trie_node):
    """递归映射，顺序与 build_trie_nodes 一致（按字符排序）。"""
    if not trie_node:
        return
    nid = f"node-{_idx[0]}"
    _idx[0] += 1
    _node_id_map[id(trie_node)] = nid
# 循环遍历处理
    for ch in sorted(trie_node.children.keys()):
        build_id_map(trie_node.children[ch])

build_id_map(t.root)

def visit_insert(word):
    """回放插入路径：沿已建好的 trie 逐字符访问节点。"""
    if not word:
        return
    curr = t.root
# 循环遍历处理
    for char in word:
        if char in curr.children:
            curr = curr.children[char]
            tracer.visit_node(_node_id_map[id(curr)], line=36)

visit_insert("algorithm")
visit_insert("algo")
visit_insert("align")
visit_insert("all")
visit_insert("also")
visit_insert("tree")
visit_insert("trie")

def visit_search(word, found):
    """回放搜索路径：found=True 表示单词存在，False 表示不存在。
    对于不存在的单词，沿已存在的前缀路径访问，在断开处标记 visited=False。"""
    if not word:
        return
    curr = t.root
# 循环遍历处理
    for char in word:
        if char in curr.children:
            curr = curr.children[char]
            tracer.visit_node(_node_id_map[id(curr)], line=47)
        else:
            break

visit_search("algo", True)
visit_search("algorithm", True)
visit_search("align", True)
visit_search("all", True)
visit_search("also", True)
visit_search("tree", True)
visit_search("trie", True)

visit_search("alien", False)
visit_search("alg", False)
visit_search("trees", False)
visit_search("try", False)

tracer.finish(line=73)
tracer.dump()
