function queueSimulation(operations) {
  const queue = [];
  const result = [];
  for (const [op, val] of operations) {
    if (op === 'enqueue') {
      queue.push(val);
      result.push([...queue]);
    } else if (op === 'dequeue') {
      if (queue.length > 0) {
        queue.shift();
      }
      result.push([...queue]);
    }
  }
  return result;
}

queueSimulation([["enqueue", 10], ["enqueue", 20], ["dequeue", null], ["enqueue", 30]]);