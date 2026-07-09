def binary_insertion_sort(arr):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        lo, hi = 0, i
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid] <= key:
                lo = mid + 1
            else:
                hi = mid
        for j in range(i, lo, -1):
            arr[j] = arr[j - 1]
        arr[lo] = key
    return arr

def insertion_sort(arr):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        while j >= 0 and key < arr[j]:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

def shell_insertion(arr, gap):
    n = len(arr)
    for i in range(gap, n):
        key = arr[i]
        j = i
        while j >= gap and arr[j - gap] > key:
            arr[j] = arr[j - gap]
            j -= gap
        arr[j] = key
    return arr

datasets = [
    [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60],
    [5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8, 3, -2, 6],
    [42, 42, 17, 17, 63, 63, 8, 8, 91, 91, 25, 25, 56, 56, 34],
    [1, 3, 5, 7, 9, 2, 4, 6, 8, 6, 10, 12, 14, 11, 13, 15],
]

for data in datasets:
    r1 = insertion_sort(data[:])
    r2 = binary_insertion_sort(data[:])
    assert r1 == r2
