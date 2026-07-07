def range_updates(arr, updates):
    # Difference array setup
    diff = [0] * (len(arr) + 1)
    diff[0] = arr[0]
    for i in range(1, len(arr)):
        diff[i] = arr[i] - arr[i-1]
        
    # Apply updates: (l, r, val) -> add val to arr[l..r]
    for l, r, val in updates:
        diff[l] += val
        diff[r + 1] -= val
        
    # Rebuild array
    arr[0] = diff[0]
    for i in range(1, len(arr)):
        arr[i] = arr[i-1] + diff[i]
    return arr

range_updates([1, 2, 3, 4, 5], [(1, 3, 2), (2, 4, 1)])
