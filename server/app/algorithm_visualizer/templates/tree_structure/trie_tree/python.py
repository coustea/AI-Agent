# trie_tree 算法实现 — domain: tree_structure
class TrieNode:
    """字典树节点 — 每个节点包含子节点映射和单词结束标记"""
    def __init__(self):
        self.children = {}
        self.is_end = False


# Trie 类定义
class Trie:
    """字典树实现 — 支持插入、精确搜索、前缀搜索、删除"""

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        """插入单词 — 逐字符沿路径创建/查找节点
        时间复杂度: O(L)，L 为单词长度"""
        if not word:
            return
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True

    def search(self, word):
        """精确搜索 — 必须完整匹配且末尾 is_end 为 True
        时间复杂度: O(L)"""
        if not word:
            return False
        node = self.root
        for char in word:
            if char not in node.children:
                return False
            node = node.children[char]
        return node.is_end

    def starts_with(self, prefix):
        """前缀搜索 — 只需匹配前缀路径，不要求 is_end
        常用于: 自动补全、搜索建议
        时间复杂度: O(L)"""
        if not prefix:
            return True
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
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

    def list_words(self):
        """列出字典树中所有单词 — DFS 遍历收集"""
        result = []
# 定义 dfs 函数
        def dfs(node, prefix):
            if node.is_end:
                result.append(prefix)
            for char in sorted(node.children.keys()):
                dfs(node.children[char], prefix + char)
        dfs(self.root, "")
        return result

# 定义 trie_operations 函数
def trie_operations():
    trie = Trie()
    words = ["cat", "car", "card", "care", "dog", "deer", "deep", "do"]
    for w in words:
        trie.insert(w)
    trie.search("cat")
    trie.search("cab")
    trie.delete("car")
