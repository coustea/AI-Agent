// algorithm: bubble_sort | language: cpp | domain: data_structure
#include "visual_tracer.hpp"
#include <vector>
#include <algorithm>

ArrayTracer tracer;

void bubbleSort(std::vector<int>& nums) {
    tracer.initArray(nums);
    int n = nums.size();
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            tracer.compare(j, j + 1);
            if (nums[j] > nums[j + 1]) {
                tracer.swap(j, j + 1);
                std::swap(nums[j], nums[j + 1]);
            }
        }
        tracer.markSorted(n - i - 1);
    }
    tracer.finish();
}

int main() {
    std::vector<int> nums = {5, 3, 8, 1, 2};
    bubbleSort(nums);
    return 0;
}
