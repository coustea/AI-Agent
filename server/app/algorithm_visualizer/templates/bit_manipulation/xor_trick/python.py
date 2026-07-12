# xor_trick 算法实现 — domain: bit_manipulation
def find_single_number(nums):
    xor = 0
    for x in nums:
        xor ^= x
    return xor

# 定义 find_two_singles 函数
def find_two_singles(nums):
    xor = 0
    for x in nums:
        xor ^= x
    rightmost = xor & (-xor)
    a = b = 0
    for x in nums:
        if x & rightmost:
            a ^= x
        else:
            b ^= x
    return a, b

# 定义 find_single_iii 函数
def find_single_iii(nums):
    ones, twos = 0, 0
    for x in nums:
        ones = (ones ^ x) & ~twos
        twos = (twos ^ x) & ~ones
    return ones

# 定义 xor_swap 函数
def xor_swap(a, b):
    a ^= b
    b ^= a
    a ^= b
    return a, b

# 定义 xor_encode_decode 函数
def xor_encode_decode(data, key):
    return [d ^ key for d in data]
