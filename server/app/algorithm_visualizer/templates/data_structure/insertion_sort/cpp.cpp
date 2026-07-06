// algorithm: insertion_sort | language: cpp | domain: data_structure
#include "visual_tracer.hpp"
#include <vector>

ArrayTracer tracer;

void insertionSort(std::vector<int>& nums) {
    tracer.initArray(nums);
    int n = nums.size();
    for (int i = 1; i < n; i++) {
        int key = nums[i];
        int j = i - 1;
        while (j >= 0) {
            tracer.compare(j, j + 1);
            if (nums[j] > key) {
                tracer.assign(j + 1, nums[j]);
                nums[j + 1] = nums[j];
                j--;
            } else {
                break;
            }
        }
        tracer.assign(j + 1, key);
        nums[j + 1] = key;
    }
    for (int i = 0; i < n; i++) {
        tracer.markSorted(i);
    }
    tracer.finish();
}

int main() {
    std::vector<int> nums = {5, 3, 8, 1, 2};
    insertionSort(nums);
    return 0;
}
