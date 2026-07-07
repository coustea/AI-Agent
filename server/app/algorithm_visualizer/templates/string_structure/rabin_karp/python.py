def rabin_karp(text, pattern):
    d = 256
    q = 101 # Prime number
    m = len(pattern)
    n = len(text)
    p = 0 # hash value for pattern
    t = 0 # hash value for text
    h = 1
    
    for i in range(m-1):
        h = (h * d) % q
        
    for i in range(m):
        p = (d * p + ord(pattern[i])) % q
        t = (d * t + ord(text[i])) % q
        
    res = []
    for i in range(n - m + 1):
        if p == t:
            if text[i : i+m] == pattern:
                res.append(i)
        if i < n - m:
            t = (d * (t - ord(text[i]) * h) + ord(text[i + m])) % q
            if t < 0:
                t = t + q
    return res

rabin_karp("abacaabadcabacaba", "abacaba")
