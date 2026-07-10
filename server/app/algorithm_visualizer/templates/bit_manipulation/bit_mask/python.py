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

READ, WRITE, EXECUTE, DELETE, ADMIN = 0, 1, 2, 3, 4

user_perms = perm_to_mask([READ, WRITE])
admin_perms = perm_to_mask([READ, WRITE, EXECUTE, DELETE, ADMIN])
guest_perms = perm_to_mask([READ])

roles = {
    "user": user_perms,
    "admin": admin_perms,
    "guest": guest_perms,
}

for role, mask in roles.items():
    perms = mask_to_perm(mask)
    can_write = has_permission(mask, WRITE)
    can_delete = has_permission(mask, DELETE)

upgraded = grant_permission(user_perms, EXECUTE)
assert has_permission(upgraded, EXECUTE)
revoked = revoke_permission(upgraded, WRITE)
assert not has_permission(revoked, WRITE)
toggled = toggle_permission(revoked, DELETE)
assert has_permission(toggled, DELETE)
