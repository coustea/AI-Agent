// C++ VisualTracer SDK — 生成 TraceEvent JSON 事件流。
// cpp_adapter.py 写入临时目录与用户代码一起编译执行。
// 输出 trace.json 而非 __TRACER__: stdout 协议。

#ifndef VISUAL_TRACER_HPP
#define VISUAL_TRACER_HPP

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
#include <fstream>
#include <sstream>

class VisualTracer {
 protected:
  std::vector<std::string> _events;
  int _step = 0;
  std::string _domain = "data_structure";
  std::string _visualizer_type = "array";

  void _record(const std::string &event_type,
               const std::string &structure_json,
               const std::string &targets_json = "[]",
               const std::string &message = "null",
               const std::string &line = "null",
               const std::string &formula = "null") {
    std::ostringstream oss;
    oss << "  {\"id\": \"evt-" << _step << "\", \"step\": " << _step
        << ", \"domain\": \"" << _domain << "\""
        << ", \"visualizerType\": \"" << _visualizer_type << "\""
        << ", \"type\": \"" << event_type << "\""
        << ", \"state\": {\"structure\": " << structure_json << "}"
        << ", \"targets\": " << targets_json
        << ", \"message\": " << message
        << ", \"line\": " << line
        << ", \"formula\": " << formula << "}";
    _events.push_back(oss.str());
    _step++;
  }

 public:
  void dump(const std::string &filepath = "trace.json") {
    std::ofstream f(filepath);
    f << "[\n";
    for (size_t i = 0; i < _events.size(); i++) {
      f << _events[i];
      if (i < _events.size() - 1) f << ",";
      f << "\n";
    }
    f << "]\n";
    f.close();
  }
};

static std::string array_to_json(const std::vector<int> &arr) {
  std::ostringstream oss;
  oss << "[";
  for (size_t i = 0; i < arr.size(); i++) {
    oss << arr[i];
    if (i < arr.size() - 1) oss << ", ";
  }
  oss << "]";
  return oss.str();
}

class ArrayTracer : public VisualTracer {
 private:
  std::vector<int> _current_array;
  std::string _arr_json() const { return array_to_json(_current_array); }

 public:
  ArrayTracer() { _visualizer_type = "array"; }

  void initArray(const std::vector<int> &arr) {
    _current_array = arr;
    std::string msg = "\"初始化数组：[";
    for (size_t i = 0; i < arr.size(); i++) {
      msg += std::to_string(arr[i]);
      if (i < arr.size() - 1) msg += ", ";
    }
    msg += "]\"";
    _record("init_array", "{\"array\": " + _arr_json() + "}", "[]", msg);
  }

  void compare(int i, int j) {
    int left = (i < (int)_current_array.size()) ? _current_array[i] : 0;
    int right = (j < (int)_current_array.size()) ? _current_array[j] : 0;
    std::string msg = "\"比较 nums[" + std::to_string(i) + "]=" +
                      std::to_string(left) + " 和 nums[" +
                      std::to_string(j) + "]=" + std::to_string(right) + "\"";
    _record("compare", "{\"array\": " + _arr_json() + "}",
            "[" + std::to_string(i) + ", " + std::to_string(j) + "]", msg);
  }

  void swap(int i, int j) {
    if (i < (int)_current_array.size() && j < (int)_current_array.size()) {
      std::swap(_current_array[i], _current_array[j]);
    }
    std::string msg = "\"交换位置 " + std::to_string(i) + " 和 " +
                      std::to_string(j) + "\"";
    _record("swap", "{\"array\": " + _arr_json() + "}",
            "[" + std::to_string(i) + ", " + std::to_string(j) + "]", msg);
  }

  void assign(int index, int value) {
    if (index < (int)_current_array.size()) {
      _current_array[index] = value;
    }
    std::string msg = "\"赋值 nums[" + std::to_string(index) + "] = " +
                      std::to_string(value) + "\"";
    _record("assign", "{\"array\": " + _arr_json() + "}",
            "[" + std::to_string(index) + "]", msg);
  }

  void markSorted(int index) {
    std::string msg = "\"位置 " + std::to_string(index) + " 已归位\"";
    _record("mark_sorted", "{\"array\": " + _arr_json() + "}",
            "[" + std::to_string(index) + "]", msg);
  }

  void movePointer(const std::string &name, int value) {
    std::string msg = "\"移动指针 " + name + " -> " + std::to_string(value) + "\"";
    _record("move_pointer",
            "{\"array\": " + _arr_json() + ", \"pointers\": {\"" + name +
                "\": " + std::to_string(value) + "}}",
            "[" + std::to_string(value) + "]", msg);
  }

  void finish() {
    _record("finish", "{\"array\": " + _arr_json() + "}", "[]", "\"排序完成\"");
    dump();
  }
};

struct StackQueueItem {
  std::string id;
  std::string label;
  std::string tone;
};

static std::string items_to_json(const std::vector<StackQueueItem> &items) {
  std::ostringstream oss;
  oss << "[";
  for (size_t i = 0; i < items.size(); i++) {
    oss << "{\"id\": \"" << items[i].id << "\", \"label\": \""
        << items[i].label << "\", \"tone\": \"" << items[i].tone << "\"}";
    if (i < items.size() - 1) oss << ", ";
  }
  oss << "]";
  return oss.str();
}

class StackTracer : public VisualTracer {
 private:
  std::vector<StackQueueItem> _items;
  std::string _items_json() const { return items_to_json(_items); }

 public:
  StackTracer() { _visualizer_type = "stack-queue"; }

  void initStack() {
    _items.clear();
    _record("init_stack",
            "{\"mode\": \"stack\", \"items\": " + _items_json() + "}",
            "[]", "\"初始化空栈\"");
  }

  void push(int value) {
    _items.push_back({"item-" + std::to_string(_items.size()),
                      std::to_string(value), "default"});
    _record("push",
            "{\"mode\": \"stack\", \"items\": " + _items_json() + "}",
            "[" + std::to_string(_items.size() - 1) + "]",
            "\"入栈：" + std::to_string(value) + "\"");
  }

  int pop() {
    if (_items.empty()) return -1;
    int val = std::stoi(_items.back().label);
    _items.pop_back();
    _record("pop",
            "{\"mode\": \"stack\", \"items\": " + _items_json() + "}",
            "[]", "\"出栈：" + std::to_string(val) + "\"");
    return val;
  }

  void highlightInput(int input_index) {
    _record("highlight_input",
            "{\"mode\": \"stack\", \"items\": " + _items_json() +
                ", \"inputIndex\": " + std::to_string(input_index) + "}",
            "[" + std::to_string(input_index) + "]",
            "\"处理输入位置 " + std::to_string(input_index) + "\"");
  }

  void finish() {
    bool matched = _items.empty();
    _record("finish",
            "{\"mode\": \"stack\", \"items\": " + _items_json() + "}",
            "[]", matched ? "\"括号匹配成功！\"" : "\"括号不匹配\"");
    dump();
  }
};

class QueueTracer : public VisualTracer {
 private:
  std::vector<StackQueueItem> _items;
  std::string _items_json() const { return items_to_json(_items); }

 public:
  QueueTracer() { _visualizer_type = "stack-queue"; }

  void initQueue() {
    _items.clear();
    _record("init_queue",
            "{\"mode\": \"queue\", \"items\": " + _items_json() + "}",
            "[]", "\"初始化空队列\"");
  }

  void enqueue(int value) {
    _items.push_back({"item-" + std::to_string(_items.size()),
                      std::to_string(value), "default"});
    _record("enqueue",
            "{\"mode\": \"queue\", \"items\": " + _items_json() + "}",
            "[" + std::to_string(_items.size() - 1) + "]",
            "\"入队：" + std::to_string(value) + "\"");
  }

  int dequeue() {
    if (_items.empty()) return -1;
    int val = std::stoi(_items.front().label);
    _items.erase(_items.begin());
    _record("dequeue",
            "{\"mode\": \"queue\", \"items\": " + _items_json() + "}",
            "[]", "\"出队：" + std::to_string(val) + "\"");
    return val;
  }

  void finish() {
    _record("finish",
            "{\"mode\": \"queue\", \"items\": " + _items_json() + "}",
            "[]", "\"队列模拟完成\"");
    dump();
  }
};

#endif  // VISUAL_TRACER_HPP
