class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

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

    def search(self, word):
        if not word:
            return self.root.is_word
        curr = self.root
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

print(t.search("algo"))
print(t.search("algorithm")) # True  — 完整单词，存在
print(t.search("align"))
print(t.search("all"))
print(t.search("also"))
print(t.search("tree"))
print(t.search("trie"))
print(t.search(""))
print(t.search("alien"))
print(t.search("alg"))
print(t.search("trees"))
print(t.search("try"))
