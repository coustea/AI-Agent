// algorithm: binary_search | language: cpp | domain: data_structure
#include "visual_tracer.hpp"
#include <vector>

ArrayTracer tracer;

int binarySearch(std::vector<int>& nums, int target) {
    tracer.initArray(nums);
    int low = 0, high = (int)nums.size() - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        tracer.movePointer("mid", mid);
        tracer.compare(mid, mid);
        if (nums[mid] == target) {
            tracer.finish();
            return mid;
        } else if (nums[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    tracer.finish();
    return -1;
}

int main() {
    std::vector<int> nums = {1, 2, 3, 5, 8};
    binarySearch(nums, 5);
    return 0;
}
