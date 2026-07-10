# shell_sort 算法实现 — domain: sorting
def knuth_gaps(n):
    gaps = []
    k = 1
    while (3 ** k - 1) // 2 < n // 3:
        gaps.append((3 ** k - 1) // 2)
        k += 1
    gaps.reverse()
    return gaps if gaps else [1]

# 定义 sedgewick_gaps 函数
def sedgewick_gaps(n):
    gaps = []
    i = 0
    while True:
        if i == 0:
            g = 1
        elif i % 2 == 0:
            g = 9 * (4 ** (i // 2)) - 9 * (2 ** (i // 2)) + 1
        else:
            g = (4 ** ((i + 1) // 2)) - 3 * (2 ** ((i + 1) // 2)) + 1
        if g >= n:
            break
        gaps.append(g)
        i += 1
    gaps = [g for g in gaps if g > 0]
    gaps.reverse()
    return gaps if gaps else [1]

# 定义 hibbard_gaps 函数
def hibbard_gaps(n):
    gaps = []
    k = 1
    while (2 ** k - 1) < n:
        gaps.append(2 ** k - 1)
        k += 1
    gaps.reverse()
    return gaps if gaps else [1]

# 定义 shell_sort_with_gaps 函数
def shell_sort_with_gaps(arr, gaps):
    n = len(arr)
    for gap in gaps:
        for i in range(gap, n):
            temp = arr[i]
            j = i
            while j >= gap and arr[j - gap] > temp:
                arr[j] = arr[j - gap]
                j -= gap
            arr[j] = temp
    return arr

# 定义 shell_sort 函数
def shell_sort(arr):
    gaps = knuth_gaps(len(arr))
    return shell_sort_with_gaps(arr, gaps)

datasets = [
    [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60],
    [5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8, 3, -2, 6],
    [42, 42, 17, 17, 63, 63, 8, 8, 91, 91, 25, 25, 56, 56, 34],
    [99, 88, 77, 66, 55, 44, 33, 22, 11, 1, 2, 3, 4, 5, 6, 7],
]

for data in datasets:
    r1 = shell_sort_with_gaps(data[:], knuth_gaps(len(data)))
    r2 = shell_sort_with_gaps(data[:], sedgewick_gaps(len(data)))
    r3 = shell_sort_with_gaps(data[:], hibbard_gaps(len(data)))
    assert r1 == r2 == r3 == sorted(data)
