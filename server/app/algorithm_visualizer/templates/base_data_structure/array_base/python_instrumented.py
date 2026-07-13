from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# 数组基础操作演示
# 数组(Array)：连续内存空间中存储相同类型元素的线性数据结构
# 特性：随机访问 O(1)，插入/删除 O(n)，查找 O(n)
# 适用场景：需要频繁按索引访问、数据量已知且较少插入删除的场景
# array_base 算法实现 — domain: base_data_structure


# 定义 array_operations 函数
def array_operations(arr):
    # 复制输入，避免修改调用方的数据
    arr = list(arr)
    tracer.init_array(arr, line=9)
    if not arr:
        tracer.finish(line=12)
        return arr

    # ========== 1. 随机访问 — O(1) ==========
    # 数组最大的优势：通过索引直接访问任意元素
    idx = min(4, len(arr) - 1)
    tracer.move_pointer({"access": idx}, line=16)
    val_at_4 = arr[idx]

    # ========== 2. 线性查找 — O(n) ==========
    # 在无序数组中查找目标值，最坏情况需遍历全部元素
    target = 8
    found_idx = -1
    for i in range(len(arr)):
        tracer.move_pointer({"i": i}, line=23)
        tracer.compare(i, i, line=24)
        if arr[i] == target:
            found_idx = i
            tracer.mark_sorted(i, line=26)
            break

    # ========== 3. 更新元素 — O(1) ==========
    # 通过索引直接修改，无需移动其他元素
    if len(arr) > 2:
        tracer.move_pointer({"update": 2}, line=30)
        arr[2] = 15
        tracer.assign(2, 15, line=31)

    # ========== 4. 插入元素 — O(n) ==========
    # 在指定位置插入需要移动后续所有元素
    insert_pos = min(5, len(arr))
    insert_val = 20
    tracer.move_pointer({"insert": insert_pos}, line=35)
    arr.insert(insert_pos, insert_val)
    tracer.init_array(arr, line=37)

    # ========== 5. 删除元素 — O(n) ==========
    # 删除指定位置元素需要移动后续所有元素向前补位
    delete_pos = min(3, len(arr) - 1)
    tracer.move_pointer({"delete": delete_pos}, line=41)
    if delete_pos < len(arr):
        removed = arr.pop(delete_pos)
        tracer.init_array(arr, line=43)

    # ========== 6. 查找最小值 — O(n) ==========
    # 遍历整个数组找到最小值及其索引
    min_idx = 0
    tracer.move_pointer({"min_idx": min_idx}, line=46)
    for i in range(1, len(arr)):
        tracer.move_pointer({"i": i}, line=48)
        tracer.compare(i, min_idx, line=49)
        if arr[i] < arr[min_idx]:
            min_idx = i

    # ========== 7. 交换两个元素 — O(1) ==========
    # 交换最小值到数组头部（选择排序的思路）
    tracer.swap(0, min_idx, line=53)
    arr[0], arr[min_idx] = arr[min_idx], arr[0]
    tracer.mark_sorted(0, line=54)

    tracer.finish(line=56)
    return arr