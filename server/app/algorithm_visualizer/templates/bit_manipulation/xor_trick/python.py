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

datasets = [
    [4, 1, 2, 1, 2],
    [17, 5, 17, 3, 5, 7, 7],
    [1, 1, 2, 2, 3, 3, 99],
    [10, 20, 10, 30, 20, 40],
]

for nums in datasets:
    if len(nums) % 2 == 1:
        s = find_single_number(nums)
    else:
        a, b = find_two_singles(nums)

message = [72, 101, 108, 108, 111]
key = 42
encoded = xor_encode_decode(message, key)
decoded = xor_encode_decode(encoded, key)
assert decoded == message
