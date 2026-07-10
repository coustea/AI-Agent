# linked_list_base 算法实现 — domain: base_data_structure
class ListNode:
# 定义 __init__ 函数
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

# DoublyListNode 类定义
class DoublyListNode:
# 定义 __init__ 函数
    def __init__(self, val=0, prev=None, next=None):
        self.val = val
        self.prev = prev
        self.next = next

# 定义 build_singly_linked 函数
def build_singly_linked(arr):
    head = None
    for v in reversed(arr):
        head = ListNode(v, head)
    return head

# 定义 build_doubly_linked 函数
def build_doubly_linked(arr):
    dummy = DoublyListNode()
    curr = dummy
    for v in arr:
        node = DoublyListNode(v, curr)
        curr.next = node
        curr = node
    return dummy.next

# 定义 detect_cycle 函数
def detect_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False

# 定义 merge_two_lists 函数
def merge_two_lists(l1, l2):
    dummy = ListNode()
    tail = dummy
    while l1 and l2:
        if l1.val <= l2.val:
            tail.next = l1
            l1 = l1.next
        else:
            tail.next = l2
            l2 = l2.next
        tail = tail.next
    tail.next = l1 or l2
    return dummy.next

# 定义 middle_node 函数
def middle_node(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow

l1 = build_singly_linked([1, 3, 5, 7, 9])
l2 = build_singly_linked([2, 4, 6, 8, 10])
merged = merge_two_lists(l1, l2)

no_cycle = detect_cycle(build_singly_linked([1, 2, 3, 4, 5]))

head = build_singly_linked([1, 2, 3, 4, 5, 6, 7])
mid = middle_node(head).val
