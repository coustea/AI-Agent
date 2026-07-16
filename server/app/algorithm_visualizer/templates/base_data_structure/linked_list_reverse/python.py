class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


def _build_linked_list(arr):
    """从数组构建链表，返回头节点。"""
    if not arr:
        return None
    head = ListNode(arr[0])
    current = head
    for value in arr[1:]:
        current.next = ListNode(value)
        current = current.next
    return head


def reverse_list(arr):
    """链表反转：依次把当前节点指向前一个节点。"""
    head = _build_linked_list(arr)
    return _reverse_nodes(head)


def _reverse_nodes(head):
    prev = None
    current = head
    while current:
        next_node = current.next
        current.next = prev
        prev = current
        current = next_node
    return prev
