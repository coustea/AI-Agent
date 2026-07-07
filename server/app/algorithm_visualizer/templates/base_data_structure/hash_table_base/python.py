def hash_table_operations():
    # Simple Hash Table simulation
    size = 10
    table = [None] * size
    
    def insert(key, val):
        hash_val = key % size
        # Linear probing
        for i in range(size):
            idx = (hash_val + i) % size
            if table[idx] is None or table[idx][0] == key:
                table[idx] = (key, val)
                return idx
        return -1

    insert(5, "apple")
    insert(15, "banana")
    insert(8, "cherry")
    return table

hash_table_operations()
