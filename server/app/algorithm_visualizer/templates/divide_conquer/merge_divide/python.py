def merge_sort_divide(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort_divide(arr[:mid])
    right = merge_sort_divide(arr[mid:])
    
    # Merge
    res = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            res.append(left[i])
            i += 1
        else:
            res.append(right[j])
            j += 1
    res.extend(left[i:])
    res.extend(right[j:])
    return res

merge_sort_divide([5, 3, 8, 1, 2])
