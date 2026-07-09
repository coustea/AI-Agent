from visual_tracer import ArrayTracer

tracer = ArrayTracer()



def array_operations():
    arr = [3, 7, 1, 9, 4, 6, 2, 8, 5, 10, 0, 11]
    tracer.init_array(arr, line=10)

    val_at_4 = arr[4]
    tracer.compare(4, 4, line=14)

    target = 8
    found_idx = -1
    for i in range(len(arr)):
        tracer.compare(i, i, line=20)
        if arr[i] == target:
            found_idx = i
            break

    arr[2] = 15
    tracer.assign(2, 15, line=26)

    insert_pos = 5
    insert_val = 20
    arr.append(0)
    tracer.assign(len(arr) - 1, 0, line=32)
    for i in range(len(arr) - 1, insert_pos, -1):
        arr[i] = arr[i - 1]
        tracer.assign(i, arr[i], line=34)
    arr[insert_pos] = insert_val
    tracer.assign(insert_pos, insert_val, line=36)

    delete_pos = 3
    if delete_pos < len(arr):
        removed = arr.pop(delete_pos)
        for i in range(delete_pos, len(arr)):
            tracer.assign(i, arr[i], line=43)

    min_idx = 0
    for i in range(1, len(arr)):
        tracer.compare(i, min_idx, line=49)
        if arr[i] < arr[min_idx]:
            min_idx = i

    arr[0], arr[min_idx] = arr[min_idx], arr[0]
    tracer.assign(0, arr[0], line=55)
    tracer.assign(min_idx, arr[min_idx], line=56)

    tracer.finish(line=58)
    return arr


array_operations()
tracer.dump()
