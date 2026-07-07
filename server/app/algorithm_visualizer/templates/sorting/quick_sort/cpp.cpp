#include <vector>
#include <algorithm>

void quickSort(std::vector<int>& nums, int left, int right) {
    if (left >= right) return;
    int i = left, j = right;
    int pivot = nums[left];
    while (i < j) {
        while (i < j && nums[j] >= pivot) j--;
        while (i < j && nums[i] <= pivot) i++;
        if (i < j) std::swap(nums[i], nums[j]);
    }
    nums[left] = nums[i];
    nums[i] = pivot;
    quickSort(nums, left, i - 1);
    quickSort(nums, i + 1, right);
}

int main() {
    std::vector<int> nums = {6, 1, 8, 3, 9, 2, 5, 7, 4};
    quickSort(nums, 0, nums.size() - 1);
    return 0;
}