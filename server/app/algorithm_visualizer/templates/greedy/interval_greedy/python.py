def erase_overlap_intervals(intervals):
    if not intervals:
        return 0
    # Sort by end time
    intervals.sort(key=lambda x: x[1])
    count = 0
    end = intervals[0][1]
    for i in range(1, len(intervals)):
        if intervals[i][0] < end:
            count += 1
        else:
            end = intervals[i][1]
    return count

erase_overlap_intervals([[1, 2], [2, 3], [3, 4], [1, 3]])
