from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 min_interval_cover 函数
def min_interval_cover(points, interval_len):
    tracer.init_array(points, line=1)
    if not points:
        return 0
    sorted_points = sorted(points)
    count = 1
    cover_end = sorted_points[0] + interval_len
# 循环遍历处理
    for i, p in enumerate(sorted_points):
        tracer.move_pointer({"i": i}, line=9)
        if p > cover_end:
            count += 1
            cover_end = p + interval_len
            tracer.assign(i, p, line=13)
    tracer.finish(line=15)
    return count

# 定义 set_cover_greedy 函数
def set_cover_greedy(universe, subsets):
    uncovered = set(universe)
    selected = []
# 循环条件判断
    while uncovered:
        best = max(subsets, key=lambda s: len(uncovered & s))
        selected.append(best)
        uncovered -= best
    return selected

# 定义 disk_covering 函数
def disk_covering(points, radius):
    if not points:
        return []
    sorted_points = sorted(points)
    centers = [sorted_points[0] + radius]
# 循环遍历处理
    for p in sorted_points[1:]:
        if abs(p - centers[-1]) > radius:
            centers.append(p + radius)
    return centers

points_1 = [1, 2, 3, 5, 7, 8, 9, 10, 12, 15, 17, 18]
covers = min_interval_cover(points_1, 3)

universe = {1, 2, 3, 4, 5, 6, 7, 8}
subsets = [{1, 2, 3}, {3, 4, 5}, {5, 6, 7}, {7, 8}, {1, 4, 7}]
result = set_cover_greedy(universe, subsets)

points_2 = [0, 1, 2, 5, 6, 8, 9, 10, 12, 15]
disks = disk_covering(points_2, 2)
tracer.dump()
