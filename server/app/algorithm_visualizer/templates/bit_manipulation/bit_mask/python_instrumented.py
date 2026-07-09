from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def perm_to_mask(perm_list):
    mask = 0
    for p in perm_list:
        mask |= (1 << p)
    return mask

def mask_to_perm(mask):
    perms = []
    i = 0
    while mask:
        if mask & 1:
            perms.append(i)
        mask >>= 1
        i += 1
    return perms

def has_permission(mask, perm):
    return bool(mask & (1 << perm))

def grant_permission(mask, perm):
    return mask | (1 << perm)

def revoke_permission(mask, perm):
    return mask & ~(1 << perm)

def toggle_permission(mask, perm):
    return mask ^ (1 << perm)

READ, WRITE, EXECUTE, DELETE, ADMIN = 0, 1, 2, 3, 4

user_perms = perm_to_mask([READ, WRITE])
admin_perms = perm_to_mask([READ, WRITE, EXECUTE, DELETE, ADMIN])
guest_perms = perm_to_mask([READ])

arr = [user_perms, admin_perms, guest_perms]
tracer.init_array(arr, line=31)

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
arr[0] = upgraded
tracer.assign(0, upgraded, line=44)
assert has_permission(upgraded, EXECUTE)
revoked = revoke_permission(upgraded, WRITE)
arr[0] = revoked
tracer.assign(0, revoked, line=47)
assert not has_permission(revoked, WRITE)
toggled = toggle_permission(revoked, DELETE)
arr[0] = toggled
tracer.assign(0, toggled, line=50)
assert has_permission(toggled, DELETE)

tracer.finish(line=52)
tracer.dump()
