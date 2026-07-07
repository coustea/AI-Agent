import fs from 'fs';

class VisualTracer {
  constructor() {
    this._events = [];
    this._step = 0;
    this._domain = 'data_structure';
    this._visualizerType = 'array';
  }
  _record(eventType, stateStructure, opts = {}) {
    this._events.push({
      id: `evt-${this._step}`, step: this._step, domain: this._domain,
      visualizerType: this._visualizerType, type: eventType,
      state: { structure: stateStructure }, targets: opts.targets || [],
      message: opts.message || null, line: opts.line || null, formula: opts.formula || null,
    });
    this._step++;
  }
  dump(filepath = 'trace.json') {
    fs.writeFileSync(filepath, JSON.stringify(this._events, null, 2), 'utf-8');
  }
}

class ArrayTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'array';
    this._currentArray = [];
  }
  initArray(arr, opts = {}) {
    this._currentArray = [...arr];
    this._record('init_array', { array: [...this._currentArray] }, { message: `初始化数组：[${this._currentArray.join(', ')}]`, ...opts });
  }
  compare(i, j, opts = {}) {
    const left = this._currentArray[i] ?? '?';
    const right = this._currentArray[j] ?? '?';
    this._record('compare', { array: [...this._currentArray] }, { targets: [i, j], message: `比较 nums[${i}]=${left} 和 nums[${j}]=${right}`, ...opts });
  }
  swap(i, j, opts = {}) {
    if (i < this._currentArray.length && j < this._currentArray.length) {
      [this._currentArray[i], this._currentArray[j]] = [this._currentArray[j], this._currentArray[i]];
    }
    this._record('swap', { array: [...this._currentArray] }, { targets: [i, j], message: `交换位置 ${i} 和 ${j}`, ...opts });
  }
  assign(index, value, opts = {}) {
    if (index < this._currentArray.length) this._currentArray[index] = value;
    this._record('assign', { array: [...this._currentArray] }, { targets: [index], message: `赋值 nums[${index}] = ${value}`, ...opts });
  }
  markSorted(index, opts = {}) {
    this._record('mark_sorted', { array: [...this._currentArray] }, { targets: [index], message: `位置 ${index} 已归位`, ...opts });
  }
  movePointer(pointers, opts = {}) {
    this._record('move_pointer', { array: [...this._currentArray], pointers }, { targets: Object.values(pointers), message: `移动指针：${JSON.stringify(pointers)}`, ...opts });
  }
  finish(opts = {}) {
    this._record('finish', { array: [...this._currentArray] }, { message: '排序完成', ...opts });
    this.dump();
  }
}

class StackTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'stack-queue';
    this._items = [];
  }
  _snapshot() {
    return this._items.map((it, i) => ({
      id: `item-${i}`,
      label: String(it.value),
      tone: it.tone || 'default'
    }));
  }
  initStack(opts = {}) {
    this._items = [];
    this._record('init_stack', { mode: 'stack', items: this._snapshot() }, { message: '初始化空栈', ...opts });
  }
  push(value, opts = {}) {
    this._items.push({ value, tone: 'default' });
    this._record('push', { mode: 'stack', items: this._snapshot() }, { targets: [this._items.length - 1], message: `入栈：${value}`, ...opts });
  }
  pop(opts = {}) {
    if (this._items.length === 0) return null;
    const item = this._items.pop();
    this._record('pop', { mode: 'stack', items: this._snapshot() }, { message: `出栈：${item.value}`, ...opts });
    return item.value;
  }
  highlightInput(inputIndex, opts = {}) {
    this._record('highlight_input', { mode: 'stack', items: this._snapshot(), inputIndex }, { targets: [inputIndex], message: `处理输入位置 ${inputIndex}`, ...opts });
  }
  finish(opts = {}) {
    const matched = this._items.length === 0;
    this._record('finish', { mode: 'stack', items: this._snapshot() }, { message: matched ? '括号匹配成功！' : '括号不匹配', ...opts });
    this.dump();
  }
}

class QueueTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'stack-queue';
    this._items = [];
  }
  _snapshot() {
    return this._items.map((it, i) => ({
      id: `item-${i}`,
      label: String(it.value),
      tone: it.tone || 'default'
    }));
  }
  initQueue(opts = {}) {
    this._items = [];
    this._record('init_queue', { mode: 'queue', items: this._snapshot() }, { message: '初始化空队列', ...opts });
  }
  enqueue(value, opts = {}) {
    this._items.push({ value, tone: 'default' });
    this._record('enqueue', { mode: 'queue', items: this._snapshot() }, { targets: [this._items.length - 1], message: `入队：${value}`, ...opts });
  }
  dequeue(opts = {}) {
    if (this._items.length === 0) return null;
    const item = this._items.shift();
    this._record('dequeue', { mode: 'queue', items: this._snapshot() }, { message: `出队：${item.value}`, ...opts });
    return item.value;
  }
  finish(opts = {}) {
    this._record('finish', { mode: 'queue', items: this._snapshot() }, { message: '队列模拟完成', ...opts });
    this.dump();
  }
}

class LinkedListTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'linked-list';
    this._nodes = [];
    this._pointers = [];
  }
  initList(nodes, pointers = [], opts = {}) {
    this._nodes = nodes.map(n => ({ ...n }));
    this._pointers = pointers.map(p => ({ ...p }));
    this._record('init_list', { nodes: [...this._nodes], pointers: [...this._pointers] }, { message: '初始化链表', ...opts });
  }
  setVisited(nodeIndex, visited = true, opts = {}) {
    if (nodeIndex >= 0 && nodeIndex < this._nodes.length) {
      this._nodes[nodeIndex].tone = visited ? 'visited' : 'default';
    }
    this._record('set_visited', { nodes: [...this._nodes], pointers: [...this._pointers] }, { targets: [nodeIndex], message: `访问节点: ${this._nodes[nodeIndex]?.label}`, ...opts });
  }
  movePointer(label, nodeIndex, tone = 'accent', opts = {}) {
    this._pointers = this._pointers.filter(p => p.label !== label);
    if (nodeIndex !== null && nodeIndex !== undefined) {
      this._pointers.push({ label, nodeIndex, tone });
    }
    this._record('move_pointer', { nodes: [...this._nodes], pointers: [...this._pointers] }, { targets: nodeIndex !== null ? [nodeIndex] : [], message: `移动指针 ${label} 指向节点 ${nodeIndex}`, ...opts });
  }
  addNode(label, tone = 'default', opts = {}) {
    const nodeId = `node-${this._nodes.length}`;
    this._nodes.push({ id: nodeId, label, tone });
    const nodeIdx = this._nodes.length - 1;
    this._record('add_node', { nodes: [...this._nodes], pointers: [...this._pointers] }, { targets: [nodeIdx], message: `添加节点 ${label}`, ...opts });
    return nodeIdx;
  }
  removeNode(nodeIndex, opts = {}) {
    if (nodeIndex >= 0 && nodeIndex < this._nodes.length) {
      const removed = this._nodes.splice(nodeIndex, 1)[0];
      for (const p of this._pointers) {
        if (p.nodeIndex > nodeIndex) {
          p.nodeIndex--;
        } else if (p.nodeIndex === nodeIndex) {
          p.nodeIndex = null;
        }
      }
      this._pointers = this._pointers.filter(p => p.nodeIndex !== null);
      this._record('remove_node', { nodes: [...this._nodes], pointers: [...this._pointers] }, { message: `删除节点 ${removed.label}`, ...opts });
    }
  }
  finish(opts = {}) {
    this._record('finish', { nodes: [...this._nodes], pointers: [...this._pointers] }, { message: '链表操作完成', ...opts });
    this.dump();
  }
}

class TreeTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'tree';
    this._nodes = [];
  }
  initTree(nodes, opts = {}) {
    this._nodes = nodes.map(n => ({ ...n }));
    this._record('init_tree', { nodes: [...this._nodes] }, { message: '初始化树结构', ...opts });
  }
  visitNode(nodeId, visited = true, opts = {}) {
    for (const node of this._nodes) {
      if (node.id === nodeId) {
        node.tone = visited ? 'visited' : 'default';
        this._record('visit_node', { nodes: [...this._nodes] }, { targets: [nodeId], message: `访问节点: ${node.label}`, ...opts });
        break;
      }
    }
  }
  finish(opts = {}) {
    this._record('finish', { nodes: [...this._nodes] }, { message: '树操作完成', ...opts });
    this.dump();
  }
}

class GraphTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'graph';
    this._nodes = [];
  }
  initGraph(nodes, opts = {}) {
    this._nodes = nodes.map(n => ({ ...n }));
    this._record('init_graph', { nodes: [...this._nodes] }, { message: '初始化图结构', ...opts });
  }
  visitNode(nodeId, visited = true, opts = {}) {
    for (const node of this._nodes) {
      if (node.id === nodeId) {
        node.tone = visited ? 'visited' : 'default';
        this._record('visit_node', { nodes: [...this._nodes] }, { targets: [nodeId], message: `访问节点: ${node.label}`, ...opts });
        break;
      }
    }
  }
  finish(opts = {}) {
    this._record('finish', { nodes: [...this._nodes] }, { message: '图操作完成', ...opts });
    this.dump();
  }
}

class DpTableTracer extends VisualTracer {
  constructor() {
    super();
    this._visualizerType = 'dp-table';
    this._headers = [];
    this._values = [];
    this._highlighted = [];
  }
  initTable(headers, rows, cols, fillValue = 0, opts = {}) {
    this._headers = [...headers];
    this._values = Array.from({ length: rows }, () => Array(cols).fill(fillValue));
    this._highlighted = [];
    this._record('init_table', { headers: [...this._headers], values: [...this._values], highlighted: [...this._highlighted] }, { message: '初始化 DP 表格', ...opts });
  }
  setValue(row, col, value, opts = {}) {
    if (row >= 0 && row < this._values.length && col >= 0 && col < this._values[row].length) {
      this._values[row][col] = value;
    }
    this._record('set_value', { headers: [...this._headers], values: [...this._values], highlighted: [...this._highlighted] }, { message: `更新表格值 dp[${row}][${col}] = ${value}`, ...opts });
  }
  highlight(row, col, tone = 'active', opts = {}) {
    this._highlighted = this._highlighted.filter(item => !(item.row === row && item.col === col));
    this._highlighted.push({ row, col, tone });
    this._record('highlight', { headers: [...this._headers], values: [...this._values], highlighted: [...this._highlighted] }, { message: `高亮单元格 dp[${row}][${col}] (${tone})`, ...opts });
  }
  clearHighlights(opts = {}) {
    this._highlighted = [];
    this._record('clear_highlights', { headers: [...this._headers], values: [...this._values], highlighted: [...this._highlighted] }, { message: '清除所有高亮', ...opts });
  }
  finish(opts = {}) {
    this._record('finish', { headers: [...this._headers], values: [...this._values], highlighted: [...this._highlighted] }, { message: 'DP 填表完成', ...opts });
    this.dump();
  }
}

export { VisualTracer, ArrayTracer, StackTracer, QueueTracer, LinkedListTracer, TreeTracer, GraphTracer, DpTableTracer };

