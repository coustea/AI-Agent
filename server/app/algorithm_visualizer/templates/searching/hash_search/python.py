def hash_search(arr, target):
    if not arr:
        return -1
    size = len(arr) * 2
    table = [None] * size

# 定义 hash_func 函数
    def hash_func(x):
        return x % size

# 定义 insert 函数
    def insert(x):
        idx = hash_func(x)
        while table[idx] is not None:
            idx = (idx + 1) % size
        table[idx] = x

    for item in arr:
        insert(item)

    idx = hash_func(target)
    while table[idx] is not None:
        if table[idx] == target:
            return idx
        idx = (idx + 1) % size
    return -1

# 定义 hash_search_with_probes 函数
def hash_search_with_probes(arr, target):
    if not arr:
        return -1, 0
    size = len(arr) * 2
    table = [None] * size

# 定义 hash_func 函数
    def hash_func(x):
        return x % size

# 定义 insert 函数
    def insert(x):
        idx = hash_func(x)
        while table[idx] is not None:
            idx = (idx + 1) % size
        table[idx] = x

    for item in arr:
        insert(item)

    idx = hash_func(target)
    probes = 0
    while table[idx] is not None:
        probes += 1
        if table[idx] == target:
            return idx, probes
        idx = (idx + 1) % size
    return -1, probes

# 定义 hash_search_double 函数
def hash_search_double(arr, target):
    if not arr:
        return -1
    size = len(arr) * 2
    table = [None] * size

# 定义 hash1 函数
    def hash1(x):
        return x % size

# 定义 hash2 函数
    def hash2(x):
        return 1 + (x % (size - 1))

# 定义 insert 函数
    def insert(x):
        idx = hash1(x)
        step = hash2(x)
        while table[idx] is not None:
            idx = (idx + step) % size
        table[idx] = x

    for item in arr:
        insert(item)

    idx = hash1(target)
    step = hash2(target)
    while table[idx] is not None:
        if table[idx] == target:
            return idx
        idx = (idx + step) % size
    return -1
