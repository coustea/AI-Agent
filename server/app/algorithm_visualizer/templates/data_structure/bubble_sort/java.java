// algorithm: bubble_sort | language: java | domain: data_structure
public class Solution {
    public static void main(String[] args) {
        ArrayTracer tracer = new ArrayTracer();
        int[] nums = {5, 3, 8, 1, 2};
        tracer.initArray(nums);
        int n = nums.length;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n - i - 1; j++) {
                tracer.compare(j, j + 1);
                if (nums[j] > nums[j + 1]) {
                    tracer.swap(j, j + 1);
                    int temp = nums[j];
                    nums[j] = nums[j + 1];
                    nums[j + 1] = temp;
                }
            }
            tracer.markSorted(n - i - 1);
        }
        tracer.finish();
    }
}
