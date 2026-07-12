# bit_mask 算法实现 — domain: bit_manipulation
def perm_to_mask(perm_list):
    mask = 0
    for p in perm_list:
        mask |= (1 << p)
    return mask

# 定义 mask_to_perm 函数
def mask_to_perm(mask):
    perms = []
    i = 0
    while mask:
        if mask & 1:
            perms.append(i)
        mask >>= 1
        i += 1
    return perms

# 定义 has_permission 函数
def has_permission(mask, perm):
    return bool(mask & (1 << perm))

# 定义 grant_permission 函数
def grant_permission(mask, perm):
    return mask | (1 << perm)

# 定义 revoke_permission 函数
def revoke_permission(mask, perm):
    return mask & ~(1 << perm)

# 定义 toggle_permission 函数
def toggle_permission(mask, perm):
    return mask ^ (1 << perm)
