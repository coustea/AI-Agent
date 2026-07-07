def fibonacci_search(arr, target):
    n = len(arr)
    # Generate Fibonacci numbers
    fib = [0, 1]
    while fib[-1] < n:
        fib.append(fib[-1] + fib[-2])
    k = len(fib) - 1
    # Pad the array
    padded = arr + [arr[-1]] * (fib[k] - n)
    
    offset = -1
    while fib[k] > 1:
        i = min(offset + fib[k-2], n - 1)
        if padded[i] < target:
            k = k - 1
            offset = i
        elif padded[i] > target:
            k = k - 2
        else:
            return i
    if fib[k-1] and padded[offset + 1] == target:
        return offset + 1
    return -1

fibonacci_search([1, 3, 5, 7, 9, 11, 13, 15, 17], 13)
