def tower_of_hanoi(n, source='A', target='C', auxiliary='B'):
    moves = []
    def hanoi(n, src, tgt, aux):
        if n == 1:
            moves.append((src, tgt))
            return
        hanoi(n - 1, src, aux, tgt)
        moves.append((src, tgt))
        hanoi(n - 1, aux, tgt, src)
    hanoi(n, source, target, auxiliary)
    return moves

def power_decomposition(n):
    if n == 0:
        return []
    result = []
    exp = 0
    while (1 << exp) <= n:
        if n & (1 << exp):
            result.append(exp)
        exp += 1
    return result

def max_subarray_divide(arr, left, right):
    if left == right:
        return arr[left]
    mid = (left + right) // 2
    left_max = max_subarray_divide(arr, left, mid)
    right_max = max_subarray_divide(arr, mid + 1, right)
    cross_left = float('-inf')
    curr = 0
    for i in range(mid, left - 1, -1):
        curr += arr[i]
        cross_left = max(cross_left, curr)
    cross_right = float('-inf')
    curr = 0
    for i in range(mid + 1, right + 1):
        curr += arr[i]
        cross_right = max(cross_right, curr)
    return max(left_max, right_max, cross_left + cross_right)

def merge_sort_count(arr):
    if len(arr) <= 1:
        return arr, 0
    mid = len(arr) // 2
    left, inv_l = merge_sort_count(arr[:mid])
    right, inv_r = merge_sort_count(arr[mid:])
    merged, inv_m = [], 0
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            inv_m += len(left) - i
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged, inv_l + inv_r + inv_m

hanoi_4 = tower_of_hanoi(4)
assert len(hanoi_4) == 15

pows = power_decomposition(42)

arr = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
max_sub = max_subarray_divide(arr, 0, len(arr) - 1)

sorted_arr, inversions = merge_sort_count([3, 1, 4, 1, 5, 9, 2, 6])
