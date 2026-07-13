from visual_tracer import TreeTracer
tracer = TreeTracer()

# trie_tree 算法实现 — domain: tree_structure
class TrieNode:
    """字典树节点 — 每个节点包含子节点映射和单词结束标记"""
    def __init__(self):
        self.children = {}
        self.is_end = False


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
    """字典树实现 — 支持插入、精确搜索、前缀搜索、删除"""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        """插入单词 — 逐字符沿路径创建/查找节点
        时间复杂度: O(L)，L 为单词长度"""
        tracer.move_pointer({"word": word}, line=16)
        if not word:
            return
        node = self.root
        tracer.visit_node(_get_node_id(node), line=17)
        for char in word:
            tracer.move_pointer({"char": char}, line=22)
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            tracer.visit_node(_get_node_id(node), line=25)
        node.is_end = True

    def search(self, word):
        """精确搜索 — 必须完整匹配且末尾 is_end 为 True
        时间复杂度: O(L)"""
        tracer.move_pointer({"word": word}, line=28)
        if not word:
            return False
        node = self.root
        tracer.visit_node(_get_node_id(node), line=29)
        for char in word:
            tracer.move_pointer({"char": char}, line=34)
            if char not in node.children:
                return False
            node = node.children[char]
            tracer.visit_node(_get_node_id(node), line=37)
        return node.is_end

    def starts_with(self, prefix):
        """前缀搜索 — 只需匹配前缀路径，不要求 is_end
        常用于: 自动补全、搜索建议
        时间复杂度: O(L)"""
        tracer.move_pointer({"prefix": prefix}, line=40)
        if not prefix:
            return True
        node = self.root
        tracer.visit_node(_get_node_id(node), line=41)
        for char in prefix:
            tracer.move_pointer({"char": char}, line=46)
            if char not in node.children:
                return False
            node = node.children[char]
            tracer.visit_node(_get_node_id(node), line=49)
        return True

    def _find_node(self, word):
        """辅助: 找到单词末尾对应的节点，不存在返回 None"""
        node = self.root
        for char in word:
            if char not in node.children:
                return None
            node = node.children[char]
        return node

    def delete(self, word):
        """删除单词 — 三种情况:
        1. 单词不存在: 无操作
        2. 单词是其他单词的前缀: 仅取消 is_end 标记
        3. 单词有独立分支: 删除不共享的节点
        时间复杂度: O(L)"""
        tracer.move_pointer({"delete": word}, line=62)
        if not word:
            return False
        node = self.root
        path = [(self.root, word[0] if word else '')]
        tracer.visit_node(_get_node_id(node), line=63)
        for char in word:
            tracer.move_pointer({"char": char}, line=71)
            if char not in node.children:
                return False
            node = node.children[char]
            tracer.visit_node(_get_node_id(node), line=74)
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

    def list_words(self):
        """列出字典树中所有单词 — DFS 遍历收集"""
        result = []
# 定义 dfs 函数
        def dfs(node, prefix):
            tracer.visit_node(_get_node_id(node), line=94)
            if node.is_end:
                result.append(prefix)
            for char in sorted(node.children.keys()):
                dfs(node.children[char], prefix + char)
        dfs(self.root, "")
        return result

# 定义 trie_operations 函数
def trie_operations(words, queries=()):
    global _node_counter, _node_map
    _node_counter = [0]
    _node_map = {}

    trie = Trie()

    # 初始化可视化
    nodes = _build_trie_nodes(trie.root)
    tracer.init_tree(nodes, line=103)

    for w in words:
        tracer.move_pointer({"insert": w}, line=105)
        trie.insert(w)
        # 更新可视化
        nodes = _build_trie_nodes(trie.root)
        tracer.init_tree(nodes, line=107)

    for query in queries:
        tracer.move_pointer({"search": query}, line=108)
        trie.search(query)

    tracer.finish(line=110)
    return {
        "words": trie.list_words(),
        "queries": {query: trie.search(query) for query in queries},
    }