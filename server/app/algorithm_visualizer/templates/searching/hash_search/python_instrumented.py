from visual_tracer import DpTableTracer

tracer = DpTableTracer()

def hash_search(arr, target):
    if not arr:
        return -1
    size = len(arr) * 2
    table = [None] * size
    headers = [str(i) for i in range(size)]
    tracer.init_table(headers, rows=1, cols=size, fill_value="", line=4)

    def hash_func(x):
        return x % size

    def insert(x):
        idx = hash_func(x)
        while table[idx] is not None:
            tracer.highlight(0, idx, tone="collision", line=10)
            idx = (idx + 1) % size
        table[idx] = x
        tracer.set_value(0, idx, str(x), line=13)
        tracer.clear_highlights(line=14)

    for item in arr:
        insert(item)

    idx = hash_func(target)
    while table[idx] is not None:
        tracer.highlight(0, idx, tone="search", line=19)
        if table[idx] == target:
            tracer.clear_highlights(line=21)
            tracer.finish(line=22)
            return idx
        tracer.clear_highlights(line=24)
        idx = (idx + 1) % size
    tracer.finish(line=26)
    return -1

def hash_search_with_probes(arr, target):
    if not arr:
        return -1, 0
    size = len(arr) * 2
    table = [None] * size

    def hash_func(x):
        return x % size

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

def hash_search_double(arr, target):
    if not arr:
        return -1
    size = len(arr) * 2
    while size < len(arr) * 2:
        size *= 2
    table = [None] * size

    def hash1(x):
        return x % size

    def hash2(x):
        return 1 + (x % (size - 1))

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

data = [34, 7, 23, 32, 5, 62, 78, 1, 15, 49, 91, 56, 3, 88, 17]
hash_search(data, 62)
hash_search(data, 99)

idx, probes = hash_search_with_probes(data, 62)
idx2 = hash_search_double(data, 62)

data2 = [11, 22, 33, 44, 55, 66, 77, 88, 99, 10, 20, 30, 40, 50, 60]
hash_search(data2, 33)
hash_search(data2, 100)
tracer.dump()
