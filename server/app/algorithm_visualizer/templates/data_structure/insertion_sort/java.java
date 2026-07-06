// algorithm: insertion_sort | language: java | domain: data_structure
public class Solution {
    public static void main(String[] args) {
        ArrayTracer tracer = new ArrayTracer();
        int[] nums = {5, 3, 8, 1, 2};
        tracer.initArray(nums);
        int n = nums.length;
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
}
