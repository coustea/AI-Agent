def find_single_number(nums):
    xor = 0
    for x in nums:
        xor ^= x
    return xor

find_single_number([4, 1, 2, 1, 2])
