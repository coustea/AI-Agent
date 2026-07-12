# trie_string_search 算法实现 — domain: string_structure
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
        for char in word:
            if char not in curr.children:
                return False
            curr = curr.children[char]
        return curr.is_word

# 定义 trie_search 函数
def trie_search():
    t = Trie()
    words = ["algo", "algorithm", "align", "all", "also", "tree", "trie"]
    for w in words:
        t.insert(w)
    t.search("algo")
    t.search("algorithm")
    t.search("alien")
    t.search("alg")
