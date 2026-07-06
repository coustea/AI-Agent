// algorithm: selection_sort | language: c | domain: data_structure
#include "visual_tracer.h"

void selectionSort(int nums[], int n) {
    vt_init_array(nums, n);
    for (int i = 0; i < n; i++) {
        int min_idx = i;
        for (int j = i + 1; j < n; j++) {
            vt_compare(j, min_idx);
            if (nums[j] < nums[min_idx]) {
                min_idx = j;
            }
        }
        if (min_idx != i) {
            vt_swap(i, min_idx);
            int temp = nums[i];
            nums[i] = nums[min_idx];
            nums[min_idx] = temp;
        }
        vt_mark_sorted(i);
    }
    vt_finish();
}

int main() {
    int nums[] = {5, 3, 8, 1, 2};
    selectionSort(nums, 5);
    return 0;
}
