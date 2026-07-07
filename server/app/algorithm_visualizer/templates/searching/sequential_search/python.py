def sequential_search(arr, target):
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1

sequential_search([5, 3, 8, 1, 2], 8)
