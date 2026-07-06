// algorithm: selection_sort | language: javascript | domain: data_structure
import { ArrayTracer } from './js_tracer.js';

const tracer = new ArrayTracer();

function selectionSort(arr) {
    let nums = [...arr];
    tracer.initArray(nums);
    let n = nums.length;
    for (let i = 0; i < n; i++) {
        let minIdx = i;
        for (let j = i + 1; j < n; j++) {
            tracer.compare(j, minIdx);
            if (nums[j] < nums[minIdx]) {
                minIdx = j;
            }
        }
        if (minIdx !== i) {
            tracer.swap(i, minIdx);
            let temp = nums[i];
            nums[i] = nums[minIdx];
            nums[minIdx] = temp;
        }
        tracer.markSorted(i);
    }
    tracer.finish();
    return nums;
}

selectionSort([5, 3, 8, 1, 2]);
