// algorithm: binary_search | language: javascript | domain: data_structure
import { ArrayTracer } from './js_tracer.js';

const tracer = new ArrayTracer();

function binarySearch(arr, target) {
    let nums = [...arr];
    tracer.initArray(nums);
    let low = 0;
    let high = nums.length - 1;
    while (low <= high) {
        let mid = Math.floor((low + high) / 2);
        tracer.movePointer({ low, mid, high });
        tracer.compare(mid, mid);
        if (nums[mid] === target) {
            tracer.finish();
            return mid;
        } else if (nums[mid] < target) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    tracer.finish();
    return -1;
}

binarySearch([1, 2, 3, 5, 8], 5);
