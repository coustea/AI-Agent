from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# basic_bit 算法实现 — domain: bit_manipulation
"""位操作可视化模板 — 将整数的二进制位展示为 32 位数组"""


def visualize_bit_operations(n, operations):
    """
    位操作可视化

    Args:
        n: 要操作的整数
        operations: 操作列表，如 [("get", 2), ("set", 3), ("clear", 1), ("toggle", 4)]

    Returns:
        操作后的二进制位数组
    """
    # 将整数转换为 32 位二进制数组（低位在前）
    bits = [(n >> i) & 1 for i in range(32)]
    tracer.init_array(bits, line=17)

    # 执行位操作并可视化
    for op, i in operations:
        if op == "get":
            # 获取第 i 位（高亮显示）
            bit_value = bits[i]
            tracer.move_pointer({"bit": i}, line=22)
        elif op == "set":
            # 将第 i 位设置为 1
            bits[i] = 1
            tracer.assign(i, 1, line=25)
        elif op == "clear":
            # 将第 i 位清零
            bits[i] = 0
            tracer.assign(i, 0, line=28)
        elif op == "toggle":
            # 切换第 i 位
            bits[i] = 1 - bits[i]
            tracer.assign(i, bits[i], line=31)

    tracer.finish(line=33)
    return bits


def get_bit(n, i):
    """获取整数 n 的第 i 位（从 0 开始，低位为 0）"""
    return (n >> i) & 1


def set_bit(n, i):
    """将整数 n 的第 i 位设置为 1"""
    return n | (1 << i)


def clear_bit(n, i):
    """将整数 n 的第 i 位清零"""
    return n & ~(1 << i)


def toggle_bit(n, i):
    """切换整数 n 的第 i 位"""
    return n ^ (1 << i)


def count_bits(n):
    """统计整数 n 中 1 的个数"""
    count = 0
    while n:
        count += n & 1
        n >>= 1
    return count


def reverse_bits(n, bit_len=32):
    """反转整数 n 的二进制位"""
    result = 0
    for i in range(bit_len):
        result = (result << 1) | (n & 1)
        n >>= 1
    return result


def is_power_of_two(n):
    """判断 n 是否为 2 的幂"""
    return n > 0 and (n & (n - 1)) == 0