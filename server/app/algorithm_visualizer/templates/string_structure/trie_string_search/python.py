class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()
    def insert(self, w):
        curr = self.root
        for char in w:
            if char not in curr.children:
                curr.children[char] = TrieNode()
            curr = curr.children[char]
        curr.is_word = True
    def search(self, w):
        curr = self.root
        for char in w:
            if char not in curr.children:
                return False
            curr = curr.children[char]
        return curr.is_word

t = Trie()
t.insert("apple")
t.search("apple")
