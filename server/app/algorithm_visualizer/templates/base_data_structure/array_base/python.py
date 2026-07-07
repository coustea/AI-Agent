def array_operations():
    arr = [1, 2, 3, 4, 5]
    # Update element
    arr[2] = 10
    # Search element
    target = 4
    found_idx = -1
    for i in range(len(arr)):
        if arr[i] == target:
            found_idx = i
            break
    return arr, found_idx

array_operations()
