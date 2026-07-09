def get_bit(n, i):
    return (n >> i) & 1

def set_bit(n, i):
    return n | (1 << i)

def clear_bit(n, i):
    return n & ~(1 << i)

def toggle_bit(n, i):
    return n ^ (1 << i)

def count_bits(n):
    count = 0
    while n:
        count += n & 1
        n >>= 1
    return count

def reverse_bits(n, bit_len=32):
    result = 0
    for i in range(bit_len):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result

def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0

nums = [42, 255, 0, 1, 1024, 7, 128, 31, 63, 1023]
for n in nums:
    bits = [get_bit(n, i) for i in range(8)]
    bit_count = count_bits(n)
    is_pow2 = is_power_of_two(n)
    rev = reverse_bits(n, 8)
    toggled = toggle_bit(n, 3)
    cleared = clear_bit(n, 0)
