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

struct LinkedListNodeItem {
    std::string id;
    std::string label;
    std::string tone;
};

struct LinkedListPointerItem {
    std::string label;
    int nodeIndex;
    std::string tone;
};

static std::string list_nodes_to_json(const std::vector<LinkedListNodeItem> &nodes) {
    std::ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < nodes.size(); i++) {
        oss << "{\"id\": \"" << nodes[i].id << "\", \"label\": \""
            << nodes[i].label << "\", \"tone\": \"" << nodes[i].tone << "\"}";
        if (i < nodes.size() - 1) oss << ", ";
    }
    oss << "]";
    return oss.str();
}

static std::string list_pointers_to_json(const std::vector<LinkedListPointerItem> &pointers) {
    std::ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < pointers.size(); i++) {
        oss << "{\"label\": \"" << pointers[i].label << "\", \"nodeIndex\": "
            << pointers[i].nodeIndex << ", \"tone\": \"" << pointers[i].tone << "\"}";
        if (i < pointers.size() - 1) oss << ", ";
    }
    oss << "]";
    return oss.str();
}

class LinkedListTracer : public VisualTracer {
 private:
  std::vector<LinkedListNodeItem> _nodes;
  std::vector<LinkedListPointerItem> _pointers;

  std::string _state_json() const {
      return "{\"nodes\": " + list_nodes_to_json(_nodes) + ", \"pointers\": " + list_pointers_to_json(_pointers) + "}";
  }

 public:
  LinkedListTracer() { _visualizer_type = "linked-list"; }

  void initList(const std::vector<LinkedListNodeItem> &nodes, const std::vector<LinkedListPointerItem> &pointers = {}) {
    _nodes = nodes;
    _pointers = pointers;
    _record("init_list", _state_json(), "[]", "\"初始化链表\"");
  }

  void setVisited(int node_index, bool visited = true) {
    if (node_index >= 0 && node_index < (int)_nodes.size()) {
        _nodes[node_index].tone = visited ? "visited" : "default";
    }
    _record("set_visited", _state_json(), "[" + std::to_string(node_index) + "]",
            "\"访问节点\"");
  }

  void movePointer(const std::string &label, int node_index, const std::string &tone = "accent") {
    for (auto it = _pointers.begin(); it != _pointers.end(); ) {
        if (it->label == label) {
            it = _pointers.erase(it);
        } else {
            ++it;
        }
    }
    if (node_index >= 0) {
        _pointers.push_back({label, node_index, tone});
    }
    _record("move_pointer", _state_json(),
            node_index >= 0 ? "[" + std::to_string(node_index) + "]" : "[]",
            "\"移动指针 " + label + "\"");
  }

  void finish() {
    _record("finish", _state_json(), "[]", "\"链表操作完成\"");
    dump();
  }
};

struct GraphNodeItem {
    std::string id;
    std::string label;
    int x;
    int y;
    std::string tone;
};

static std::string graph_nodes_to_json(const std::vector<GraphNodeItem> &nodes) {
    std::ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < nodes.size(); i++) {
        oss << "{\"id\": \"" << nodes[i].id << "\", \"label\": \""
            << nodes[i].label << "\", \"x\": " << nodes[i].x
            << ", \"y\": " << nodes[i].y << ", \"tone\": \""
            << nodes[i].tone << "\"}";
        if (i < nodes.size() - 1) oss << ", ";
    }
    oss << "]";
    return oss.str();
}

class TreeTracer : public VisualTracer {
 private:
  std::vector<GraphNodeItem> _nodes;
  std::string _nodes_json() const { return graph_nodes_to_json(_nodes); }

 public:
  TreeTracer() { _visualizer_type = "tree"; }

  void initTree(const std::vector<GraphNodeItem> &nodes) {
    _nodes = nodes;
    _record("init_tree", "{\"nodes\": " + _nodes_json() + "}", "[]", "\"初始化树结构\"");
  }

  void visitNode(const std::string &node_id, bool visited = true) {
    for (size_t i = 0; i < _nodes.size(); i++) {
        if (_nodes[i].id == node_id) {
            _nodes[i].tone = visited ? "visited" : "default";
            std::string msg = "\"访问节点: " + _nodes[i].label + "\"";
            _record("visit_node", "{\"nodes\": " + _nodes_json() + "}",
                    "[\"" + node_id + "\"]", msg);
            break;
        }
    }
  }

  void finish() {
    _record("finish", "{\"nodes\": " + _nodes_json() + "}", "[]", "\"树操作完成\"");
    dump();
  }
};

class GraphTracer : public VisualTracer {
 private:
  std::vector<GraphNodeItem> _nodes;
  std::string _nodes_json() const { return graph_nodes_to_json(_nodes); }

 public:
  GraphTracer() { _visualizer_type = "graph"; }

  void initGraph(const std::vector<GraphNodeItem> &nodes) {
    _nodes = nodes;
    _record("init_graph", "{\"nodes\": " + _nodes_json() + "}", "[]", "\"初始化图结构\"");
  }

  void visitNode(const std::string &node_id, bool visited = true) {
    for (size_t i = 0; i < _nodes.size(); i++) {
        if (_nodes[i].id == node_id) {
            _nodes[i].tone = visited ? "visited" : "default";
            std::string msg = "\"访问节点: " + _nodes[i].label + "\"";
            _record("visit_node", "{\"nodes\": " + _nodes_json() + "}",
                    "[\"" + node_id + "\"]", msg);
            break;
        }
    }
  }

  void finish() {
    _record("finish", "{\"nodes\": " + _nodes_json() + "}", "[]", "\"图操作完成\"");
    dump();
  }
};

class DpTableTracer : public VisualTracer {
 private:
  std::vector<std::string> _headers;
  std::vector<std::vector<int>> _values;
  struct DpHighlight {
      int row, col;
      std::string tone;
  };
  std::vector<DpHighlight> _highlighted;

  std::string _state_json() const {
      std::ostringstream oss;
      oss << "{\"headers\": [";
      for (size_t i = 0; i < _headers.size(); i++) {
          oss << "\"" << _headers[i] << "\"";
          if (i < _headers.size() - 1) oss << ", ";
      }
      oss << "], \"values\": [";
      for (size_t i = 0; i < _values.size(); i++) {
          oss << "[";
          for (size_t j = 0; j < _values[i].size(); j++) {
              oss << _values[i][j];
              if (j < _values[i].size() - 1) oss << ", ";
          }
          oss << "]";
          if (i < _values.size() - 1) oss << ", ";
      }
      oss << "], \"highlighted\": [";
      for (size_t i = 0; i < _highlighted.size(); i++) {
          oss << "{\"row\": " << _highlighted[i].row << ", \"col\": " << _highlighted[i].col
              << ", \"tone\": \"" << _highlighted[i].tone << "\"}";
          if (i < _highlighted.size() - 1) oss << ", ";
      }
      oss << "]}";
      return oss.str();
  }

 public:
  DpTableTracer() { _visualizer_type = "dp-table"; }

  void initTable(const std::vector<std::string> &headers, int rows, int cols, int fill_value = 0) {
    _headers = headers;
    _values.assign(rows, std::vector<int>(cols, fill_value));
    _highlighted.clear();
    _record("init_table", _state_json(), "[]", "\"初始化 DP 表格\"");
  }

  void setValue(int row, int col, int value) {
    if (row >= 0 && row < (int)_values.size() && col >= 0 && col < (int)_values[row].size()) {
        _values[row][col] = value;
    }
    _record("set_value", _state_json(), "[]", "\"更新表格值\"");
  }

  void highlight(int row, int col, const std::string &tone = "active") {
    for (auto it = _highlighted.begin(); it != _highlighted.end(); ) {
        if (it->row == row && it->col == col) {
            it = _highlighted.erase(it);
        } else {
            ++it;
        }
    }
    _highlighted.push_back({row, col, tone});
    _record("highlight", _state_json(), "[]", "\"高亮单元格\"");
  }

  void clearHighlights() {
    _highlighted.clear();
    _record("clear_highlights", _state_json(), "[]", "\"清除高亮\"");
  }

  void finish() {
    _record("finish", _state_json(), "[]", "\"DP 填表完成\"");
    dump();
  }
};

#endif  // VISUAL_TRACER_HPP
