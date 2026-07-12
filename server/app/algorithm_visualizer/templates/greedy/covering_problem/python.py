# covering_problem 算法实现 — domain: greedy
"""集合覆盖问题可视化模板"""


def min_interval_cover(points, interval_len):
    """
    最小区间覆盖问题（贪心算法）

    Args:
        points: 点的列表
        interval_len: 每个区间能覆盖的长度

    Returns:
        覆盖所有点所需的最小区间数
    """
    if not points:
        return 0

    # 排序点集
    sorted_points = sorted(points)

    # 贪心策略：每次尽可能延伸覆盖范围
    count = 1
    cover_end = sorted_points[0] + interval_len

    for i, p in enumerate(sorted_points[1:], 1):
        if p > cover_end:
            # 当前区间无法覆盖，开启新区间
            count += 1
            cover_end = p + interval_len

    return count


def set_cover_greedy(universe, subsets):
    """
    集合覆盖问题（贪心近似算法）

    Args:
        universe: 全集元素列表
        subsets: 子集列表

    Returns:
        选中的子集列表
    """
    uncovered = set(universe)
    selected = []

    while uncovered:
        # 贪心选择：每次选择覆盖最多未覆盖元素的子集
        best = max(subsets, key=lambda s: len(uncovered & s))
        selected.append(best)
        uncovered -= best

    return selected


def disk_covering(points, radius):
    """
    圆盘覆盖问题

    Args:
        points: 点的列表
        radius: 每个圆盘的半径

    Returns:
        圆心位置列表
    """
    if not points:
        return []

    sorted_points = sorted(points)
    centers = [sorted_points[0] + radius]

    for p in sorted_points[1:]:
        if abs(p - centers[-1]) > radius:
            centers.append(p + radius)

    return centers