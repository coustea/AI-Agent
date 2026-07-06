// algorithm: insertion_sort | language: c | domain: data_structure
#include "visual_tracer.h"

void insertionSort(int nums[], int n) {
    vt_init_array(nums, n);
    for (int i = 1; i < n; i++) {
        int key = nums[i];
        int j = i - 1;
        while (j >= 0) {
            vt_compare(j, j + 1);
            if (nums[j] > key) {
                vt_assign(j + 1, nums[j]);
                nums[j + 1] = nums[j];
                j--;
            } else {
                break;
            }
        }
        vt_assign(j + 1, key);
        nums[j + 1] = key;
    }
    for (int i = 0; i < n; i++) {
        vt_mark_sorted(i);
    }
    vt_finish();
}

int main() {
    int nums[] = {5, 3, 8, 1, 2};
    insertionSort(nums, 5);
    return 0;
}
