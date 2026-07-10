from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 get_bit 函数
def get_bit(n, i):
    return (n >> i) & 1

# 定义 set_bit 函数
def set_bit(n, i):
    return n | (1 << i)

# 定义 clear_bit 函数
def clear_bit(n, i):
    return n & ~(1 << i)

# 定义 toggle_bit 函数
def toggle_bit(n, i):
    return n ^ (1 << i)

# 定义 count_bits 函数
def count_bits(n):
    arr = [n]
    tracer.init_array(arr, line=13)
    count = 0
# 循环条件判断
    while n:
        count += n & 1
        n >>= 1
        arr[0] = n
        tracer.assign(0, n, line=17)
    tracer.finish(line=19)
    return count

# 定义 reverse_bits 函数
def reverse_bits(n, bit_len=32):
    result = 0
# 循环遍历处理
    for i in range(bit_len):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result

# 定义 is_power_of_two 函数
def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0

nums = [42, 255, 0, 1, 1024, 7, 128, 31, 63, 1023]
# 循环遍历处理
for n in nums:
    bits = [get_bit(n, i) for i in range(8)]
    bit_count = count_bits(n)
    is_pow2 = is_power_of_two(n)
    rev = reverse_bits(n, 8)
    toggled = toggle_bit(n, 3)
    cleared = clear_bit(n, 0)
tracer.dump()
