// algorithm: bubble_sort | language: c | domain: data_structure
#include "visual_tracer.h"

void bubbleSort(int nums[], int n) {
    vt_init_array(nums, n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            vt_compare(j, j + 1);
            if (nums[j] > nums[j + 1]) {
                vt_swap(j, j + 1);
                int temp = nums[j];
                nums[j] = nums[j + 1];
                nums[j + 1] = temp;
            }
        }
        vt_mark_sorted(n - i - 1);
    }
    vt_finish();
}

int main() {
    int nums[] = {5, 3, 8, 1, 2};
    bubbleSort(nums, 5);
    return 0;
}
