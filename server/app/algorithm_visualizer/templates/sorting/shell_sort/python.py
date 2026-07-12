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
