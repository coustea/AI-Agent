def bit_operations(n):
    # Extract lower 8 bits
    bits = []
    for i in range(8):
        # Check if i-th bit is set
        bits.append((n >> i) & 1)
    return bits

bit_operations(42)
