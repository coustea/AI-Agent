function quickSort(nums, left, right) {
  if (left >= right) return;
  let i = left, j = right;
  let pivot = nums[left];
  while (i < j) {
    while (i < j && nums[j] >= pivot) j--;
    while (i < j && nums[i] <= pivot) i++;
    if (i < j) {
      [nums[i], nums[j]] = [nums[j], nums[i]];
    }
  }
  nums[left] = nums[i];
  nums[i] = pivot;
  quickSort(nums, left, i - 1);
  quickSort(nums, i + 1, right);
}
const arr = [6, 1, 8, 3, 9, 2, 5, 7, 4];
quickSort(arr, 0, arr.length - 1);