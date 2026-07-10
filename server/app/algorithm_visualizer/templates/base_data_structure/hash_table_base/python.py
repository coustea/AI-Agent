# hash_table_base 算法实现 — domain: base_data_structure
class HashTableChaining:
# 定义 __init__ 函数
    def __init__(self, size=7):
        self.size = size
        self.table = [[] for _ in range(size)]

# 定义 _hash 函数
    def _hash(self, key):
        return hash(key) % self.size

# 定义 put 函数
    def put(self, key, value):
        idx = self._hash(key)
        for i, (k, v) in enumerate(self.table[idx]):
            if k == key:
                self.table[idx][i] = (key, value)
                return
        self.table[idx].append((key, value))

# 定义 get 函数
    def get(self, key):
        idx = self._hash(key)
        for k, v in self.table[idx]:
            if k == key:
                return v
        return None

# 定义 remove 函数
    def remove(self, key):
        idx = self._hash(key)
        for i, (k, v) in enumerate(self.table[idx]):
            if k == key:
                self.table[idx].pop(i)
                return True
        return False

# 定义 load_factor 函数
    def load_factor(self):
        count = sum(len(bucket) for bucket in self.table)
        return count / self.size

# HashTableLinearProbing 类定义
class HashTableLinearProbing:
# 定义 __init__ 函数
    def __init__(self, size=17):
        self.size = size
        self.keys = [None] * size
        self.values = [None] * size

# 定义 _hash 函数
    def _hash(self, key):
        return hash(key) % self.size

# 定义 _probe 函数
    def _probe(self, key):
        idx = self._hash(key)
        while self.keys[idx] is not None and self.keys[idx] != key:
            idx = (idx + 1) % self.size
        return idx

# 定义 put 函数
    def put(self, key, value):
        if self.load_factor() > 0.7:
            return
        idx = self._probe(key)
        self.keys[idx] = key
        self.values[idx] = value

# 定义 get 函数
    def get(self, key):
        idx = self._probe(key)
        if self.keys[idx] == key:
            return self.values[idx]
        return None

# 定义 load_factor 函数
    def load_factor(self):
        return sum(1 for k in self.keys if k is not None) / self.size

ht_chain = HashTableChaining()
for k, v in [("apple", 1), ("banana", 2), ("cherry", 3), ("date", 4), ("elderberry", 5), ("fig", 6), ("grape", 7)]:
    ht_chain.put(k, v)
assert ht_chain.get("cherry") == 3
ht_chain.remove("date")
assert ht_chain.get("date") is None
lf = ht_chain.load_factor()

ht_probe = HashTableLinearProbing()
for k, v in [("apple", 1), ("banana", 2), ("cherry", 3), ("date", 4), ("fig", 5)]:
    ht_probe.put(k, v)
assert ht_probe.get("banana") == 2
