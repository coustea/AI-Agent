def hanoi(n, source, target, auxiliary):
    steps = []
    def move(n, src, tgt, aux):
        if n > 0:
            move(n - 1, src, aux, tgt)
            steps.append((src, tgt))
            move(n - 1, aux, tgt, src)
    move(n, source, target, auxiliary)
    return steps

hanoi(3, 'A', 'C', 'B')
