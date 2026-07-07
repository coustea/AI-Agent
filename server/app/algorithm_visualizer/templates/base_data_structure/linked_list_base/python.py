class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def list_operations():
    # Create head
    head = ListNode(1)
    # Insert node
    node2 = ListNode(2)
    head.next = node2
    # Insert node at end
    node3 = ListNode(3)
    node2.next = node3
    # Delete node
    head.next = node3
    return head

list_operations()
