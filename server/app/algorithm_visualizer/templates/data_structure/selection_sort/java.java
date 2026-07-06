// algorithm: selection_sort | language: java | domain: data_structure
public class Solution {
    public static void main(String[] args) {
        ArrayTracer tracer = new ArrayTracer();
        int[] nums = {5, 3, 8, 1, 2};
        tracer.initArray(nums);
        int n = nums.length;
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
                int temp = nums[i];
                nums[i] = nums[minIdx];
                nums[minIdx] = temp;
            }
            tracer.markSorted(i);
        }
        tracer.finish();
    }
}
