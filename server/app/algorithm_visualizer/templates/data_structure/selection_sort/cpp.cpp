// algorithm: selection_sort | language: cpp | domain: data_structure
#include "visual_tracer.hpp"
#include <vector>
#include <algorithm>

ArrayTracer tracer;

void selectionSort(std::vector<int>& nums) {
    tracer.initArray(nums);
    int n = nums.size();
    for (int i = 0; i < n; i++) {
        int minIdx = i;
        for (int j = i + 1; j < n; j++) {
            tracer.compare(j, minIdx);
            if (nums[j] < nums[minIdx]) {
                minIdx = j;
            }
        }
        if (minIdx != i) {
            tracer.swap(i, minIdx);
            std::swap(nums[i], nums[minIdx]);
        }
        tracer.markSorted(i);
    }
    tracer.finish();
}

int main() {
    std::vector<int> nums = {5, 3, 8, 1, 2};
    selectionSort(nums);
    return 0;
}
