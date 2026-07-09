from visual_tracer import ArrayTracer

tracer = ArrayTracer()

class HashTableChaining:
    def __init__(self, size=7):
        self.size = size
        self.table = [[] for _ in range(size)]
        self.arr = [0] * size

    def _hash(self, key):
        return hash(key) % self.size

    def put(self, key, value):
        idx = self._hash(key)
        self.arr[idx] = len(self.table[idx]) + 1
        tracer.init_array(self.arr, line=9)
        tracer.move_pointer({"idx": idx}, line=11)
        for i, (k, v) in enumerate(self.table[idx]):
            if k == key:
                self.table[idx][i] = (key, value)
                tracer.assign(idx, self.arr[idx], line=14)
                return
        self.table[idx].append((key, value))
        self.arr[idx] = len(self.table[idx])
        tracer.assign(idx, self.arr[idx], line=18)

    def get(self, key):
        idx = self._hash(key)
        for k, v in self.table[idx]:
            if k == key:
                return v
        return None

    def remove(self, key):
        idx = self._hash(key)
        for i, (k, v) in enumerate(self.table[idx]):
            if k == key:
                self.table[idx].pop(i)
                self.arr[idx] = len(self.table[idx])
                tracer.assign(idx, self.arr[idx], line=30)
                return True
        return False

    def load_factor(self):
        count = sum(len(bucket) for bucket in self.table)
        return count / self.size

class HashTableLinearProbing:
    def __init__(self, size=17):
        self.size = size
        self.keys = [None] * size
        self.values = [None] * size

    def _hash(self, key):
        return hash(key) % self.size

    def _probe(self, key):
        idx = self._hash(key)
        while self.keys[idx] is not None and self.keys[idx] != key:
            idx = (idx + 1) % self.size
        return idx

    def put(self, key, value):
        if self.load_factor() > 0.7:
            return
        idx = self._probe(key)
        self.keys[idx] = key
        self.values[idx] = value

    def get(self, key):
        idx = self._probe(key)
        if self.keys[idx] == key:
            return self.values[idx]
        return None

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

tracer.finish(line=78)
tracer.dump()
