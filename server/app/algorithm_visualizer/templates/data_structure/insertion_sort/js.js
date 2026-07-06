// algorithm: insertion_sort | language: javascript | domain: data_structure
import { ArrayTracer } from './js_tracer.js';

const tracer = new ArrayTracer();

function insertionSort(arr) {
    let nums = [...arr];
    tracer.initArray(nums);
    let n = nums.length;
    for (let i = 1; i < n; i++) {
        let key = nums[i];
        let j = i - 1;
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
    for (let i = 0; i < n; i++) {
        tracer.markSorted(i);
    }
    tracer.finish();
    return nums;
}

insertionSort([5, 3, 8, 1, 2]);
