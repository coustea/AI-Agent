// algorithm: binary_search | language: c | domain: data_structure
#include "visual_tracer.h"

int binarySearch(int nums[], int n, int target) {
    vt_init_array(nums, n);
    int low = 0, high = n - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        vt_move_pointer("mid", mid);
        vt_compare(mid, mid);
        if (nums[mid] == target) {
            vt_finish();
            return mid;
        } else if (nums[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    vt_finish();
    return -1;
}

int main() {
    int nums[] = {1, 2, 3, 5, 8};
    binarySearch(nums, 5, 5);
    return 0;
}
