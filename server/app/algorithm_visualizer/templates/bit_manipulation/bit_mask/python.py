def apply_mask(state, mask, action):
    if action == "set":
        return state | mask
    elif action == "clear":
        return state & ~mask
    elif action == "toggle":
        return state ^ mask
    return state

apply_mask(5, 2, "set")
