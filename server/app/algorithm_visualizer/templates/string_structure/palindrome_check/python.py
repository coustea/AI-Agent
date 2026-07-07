def is_palindrome(s):
    # Filter non-alphanumeric
    cleaned = "".join(char.lower() for char in s if char.isalnum())
    left = 0
    right = len(cleaned) - 1
    while left < right:
        if cleaned[left] != cleaned[right]:
            return False
        left += 1
        right -= 1
    return True

is_palindrome("A man, a plan, a canal: Panama")
