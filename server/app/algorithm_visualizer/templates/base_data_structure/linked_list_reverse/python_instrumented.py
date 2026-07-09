from visual_tracer import LinkedListTracer

tracer = LinkedListTracer()

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def list_to_nodes(arr):
    head = None
    for v in reversed(arr):
        head = ListNode(v, head)
    return head

def nodes_to_list(head):
    result = []
    while head:
        result.append(head.val)
        head = head.next
    return result

def reverse_list(head):
    nodes = [{"id": f"node-{i}", "label": str(v), "tone": "default"} for i, v in enumerate(nodes_to_list(head))]
    tracer.init_list(nodes, [tracer._pointers[0] if tracer._pointers else {"label": "curr", "nodeIndex": 0, "tone": "accent"}], line=16)
    prev = None
    curr = head
    idx = 0
    while curr:
        tracer.move_pointer("curr", idx, line=21)
        next_node = curr.next
        curr.next = prev
        prev = curr
        curr = next_node
        if prev:
            tracer.set_visited(idx, True, line=27)
        idx += 1
    tracer.finish(line=30)
    return prev

def reverse_k_group(head, k):
    def get_kth(curr, k):
        while curr and k > 0:
            curr = curr.next
            k -= 1
        return curr
    dummy = ListNode(0, head)
    group_prev = dummy
    while True:
        kth = get_kth(group_prev, k)
        if not kth:
            break
        group_next = kth.next
        prev = kth.next
        curr = group_prev.next
        while curr != group_next:
            tmp = curr.next
            curr.next = prev
            prev = curr
            curr = tmp
        tmp = group_prev.next
        group_prev.next = kth
        group_prev = tmp
    return dummy.next

def reverse_between(head, left, right):
    dummy = ListNode(0, head)
    prev = dummy
    for _ in range(left - 1):
        prev = prev.next
    curr = prev.next
    for _ in range(right - left):
        tmp = curr.next
        curr.next = tmp.next
        tmp.next = prev.next
        prev.next = tmp
    return dummy.next

def reverse_recursive(head):
    if not head or not head.next:
        return head
    new_head = reverse_recursive(head.next)
    head.next.next = head
    head.next = None
    return new_head

head = list_to_nodes([1, 2, 3, 4, 5, 6, 7, 8])
r1 = nodes_to_list(reverse_list(list_to_nodes([1, 2, 3, 4, 5, 6, 7, 8])))
r2 = nodes_to_list(reverse_k_group(list_to_nodes([1, 2, 3, 4, 5, 6, 7, 8]), 3))
r3 = nodes_to_list(reverse_between(list_to_nodes([1, 2, 3, 4, 5, 6, 7, 8]), 2, 5))
r4 = nodes_to_list(reverse_recursive(list_to_nodes([1, 2, 3, 4, 5, 6, 7, 8])))
tracer.dump()
