// algorithm: binary_search | language: java | domain: data_structure
public class Solution {
    public static void main(String[] args) {
        ArrayTracer tracer = new ArrayTracer();
        int[] nums = {1, 2, 3, 5, 8};
        int target = 5;
        tracer.initArray(nums);
        int low = 0, high = nums.length - 1;
        while (low <= high) {
            int mid = (low + high) / 2;
            tracer.movePointer("mid", mid);
            tracer.compare(mid, mid);
            if (nums[mid] == target) {
                tracer.finish();
                return;
            } else if (nums[mid] < target) {
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        tracer.finish();
    }
}
