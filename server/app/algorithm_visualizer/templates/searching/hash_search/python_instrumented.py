from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def hash_search(arr, target):
    tracer.init_array(arr, line=1)
    if not arr:
        tracer.finish(line=2)
        return -1
    size = len(arr) * 2
    table = [None] * size
    tracer.init_array([0] * size, line=5)

# 定义 hash_func 函数
    def hash_func(x):
        return x % size

# 定义 insert 函数
    def insert(x):
        idx = hash_func(x)
        while table[idx] is not None:
            tracer.move_pointer({"probe": idx}, line=14)
            idx = (idx + 1) % size
        table[idx] = x
        tracer.assign(idx, x, line=16)

    for item in arr:
        tracer.move_pointer({"insert": item}, line=18)
        insert(item)

    idx = hash_func(target)
    tracer.move_pointer({"search": target}, line=21)
    while table[idx] is not None:
        tracer.compare(idx, idx, line=23)
        if table[idx] == target:
            tracer.mark_sorted(idx, line=24)
            tracer.finish(line=24)
            return idx
        idx = (idx + 1) % size
    tracer.finish(line=26)
    return -1

# 定义 hash_search_with_probes 函数
def hash_search_with_probes(arr, target):
    tracer.init_array(arr, line=28)
    if not arr:
        tracer.finish(line=30)
        return -1, 0
    size = len(arr) * 2
    table = [None] * size
    tracer.init_array([0] * size, line=33)

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
        tracer.move_pointer({"probe": probes}, line=51)
        if table[idx] == target:
            tracer.mark_sorted(idx, line=53)
            tracer.finish(line=53)
            return idx, probes
        idx = (idx + 1) % size
    tracer.finish(line=56)
    return -1, probes

# 定义 hash_search_double 函数
def hash_search_double(arr, target):
    tracer.init_array(arr, line=58)
    if not arr:
        tracer.finish(line=60)
        return -1
    size = len(arr) * 2
    table = [None] * size
    tracer.init_array([0] * size, line=63)

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
            tracer.move_pointer({"probe": idx}, line=77)
            idx = (idx + step) % size
        table[idx] = x
        tracer.assign(idx, x, line=79)

    for item in arr:
        insert(item)

    idx = hash1(target)
    step = hash2(target)
    while table[idx] is not None:
        tracer.compare(idx, idx, line=86)
        if table[idx] == target:
            tracer.mark_sorted(idx, line=88)
            tracer.finish(line=88)
            return idx
        idx = (idx + step) % size
    tracer.finish(line=90)
    return -1
