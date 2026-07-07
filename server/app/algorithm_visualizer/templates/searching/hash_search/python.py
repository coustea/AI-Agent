def hash_search(arr, target):
    size = len(arr) * 2
    table = [None] * size
    
    def insert(x):
        idx = x % size
        while table[idx] is not None:
            idx = (idx + 1) % size
        table[idx] = x
        
    for item in arr:
        insert(item)
        
    # Search
    idx = target % size
    while table[idx] is not None:
        if table[idx] == target:
            return idx
        idx = (idx + 1) % size
    return -1

hash_search([5, 3, 8, 1, 2], 8)
