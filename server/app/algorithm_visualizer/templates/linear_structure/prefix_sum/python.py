class PrefixSum:
    def __init__(self, arr):
        self.prefix = [0] * (len(arr) + 1)
        for i in range(len(arr)):
            self.prefix[i + 1] = self.prefix[i] + arr[i]
            
    def range_query(self, left, right):
        return self.prefix[right + 1] - self.prefix[left]

p = PrefixSum([1, 2, 3, 5, 8])
p.range_query(1, 3)
