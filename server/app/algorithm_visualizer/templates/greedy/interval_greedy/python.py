# interval_greedy 算法实现 — domain: greedy
def activity_selection(intervals):
    sorted_intervals = sorted(intervals, key=lambda x: x[1])
    selected = [sorted_intervals[0]]
    for interval in sorted_intervals[1:]:
        if interval[0] >= selected[-1][1]:
            selected.append(interval)
    return selected

# 定义 min_meeting_rooms 函数
def min_meeting_rooms(intervals):
    starts = sorted(s for s, e in intervals)
    ends = sorted(e for s, e in intervals)
    rooms = 0
    end_ptr = 0
    for start in starts:
        if start < ends[end_ptr]:
            rooms += 1
        else:
            end_ptr += 1
    return rooms

# 定义 erase_overlap 函数
def erase_overlap(intervals):
    if not intervals:
        return 0
    sorted_intervals = sorted(intervals, key=lambda x: x[1])
    count = 0
    end = sorted_intervals[0][1]
    for interval in sorted_intervals[1:]:
        if interval[0] < end:
            count += 1
        else:
            end = interval[1]
    return count

# 定义 partition_labels 函数
def partition_labels(s):
    last = {c: i for i, c in enumerate(s)}
    result = []
    start = end = 0
    for i, c in enumerate(s):
        end = max(end, last[c])
        if i == end:
            result.append(i - start + 1)
            start = i + 1
    return result

intervals_1 = [(1, 3), (2, 5), (4, 7), (6, 9), (8, 10)]
selected = activity_selection(intervals_1)

intervals_2 = [(0, 30), (5, 10), (15, 20), (10, 15), (20, 25)]
rooms = min_meeting_rooms(intervals_2)

intervals_3 = [(1, 2), (2, 3), (3, 4), (1, 3)]
erased = erase_overlap(intervals_3)

labels = partition_labels("ababcbacadefegdehijhklij")
