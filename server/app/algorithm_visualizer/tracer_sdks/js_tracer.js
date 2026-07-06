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

export { VisualTracer, ArrayTracer, StackTracer, QueueTracer };

