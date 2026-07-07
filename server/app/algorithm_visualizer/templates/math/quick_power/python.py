def my_pow(x, n):
    if n < 0:
        x = 1 / x
        n = -n
    pow_val = 1
    curr = x
    while n > 0:
        if n % 2 == 1:
            pow_val *= curr
        curr *= curr
        n //= 2
    return pow_val

my_pow(2, 10)
