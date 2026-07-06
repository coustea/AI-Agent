// algorithm: bubble_sort | language: javascript | domain: data_structure
import { ArrayTracer } from './js_tracer.js';

const tracer = new ArrayTracer();

function bubbleSort(arr) {
    let nums = [...arr];
    tracer.initArray(nums);
    let n = nums.length;
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n - i - 1; j++) {
            tracer.compare(j, j + 1);
            if (nums[j] > nums[j + 1]) {
                tracer.swap(j, j + 1);
                let temp = nums[j];
                nums[j] = nums[j + 1];
                nums[j + 1] = temp;
            }
        }
        tracer.markSorted(n - i - 1);
    }
    tracer.finish();
    return nums;
}

bubbleSort([5, 3, 8, 1, 2]);
