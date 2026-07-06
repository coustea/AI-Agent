// Java VisualTracer SDK — 生成 TraceEvent JSON 事件流。
// java_adapter.py 写入临时目录与用户代码一起编译执行。
// 输出 trace.json 而非 __TRACER__: stdout 协议。

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

class VisualTracer {
    protected List<String> events = new ArrayList<>();
    protected int step = 0;
    protected String domain = "data_structure";
    protected String visualizerType = "array";

    protected void record(String eventType, String structureJson,
                          String targetsJson, String message) {
        StringBuilder sb = new StringBuilder();
        sb.append("  {\"id\": \"evt-").append(step).append("\"");
        sb.append(", \"step\": ").append(step);
        sb.append(", \"domain\": \"").append(domain).append("\"");
        sb.append(", \"visualizerType\": \"").append(visualizerType).append("\"");
        sb.append(", \"type\": \"").append(eventType).append("\"");
        sb.append(", \"state\": {\"structure\": ").append(structureJson).append("}");
        sb.append(", \"targets\": ").append(targetsJson);
        sb.append(", \"message\": ").append(message);
        sb.append(", \"line\": null, \"formula\": null}");
        events.add(sb.toString());
        step++;
    }

    public void dump(String filepath) {
        try (FileWriter fw = new FileWriter(filepath)) {
            fw.write("[\n");
            for (int i = 0; i < events.size(); i++) {
                fw.write(events.get(i));
                if (i < events.size() - 1) fw.write(",");
                fw.write("\n");
            }
            fw.write("]\n");
        } catch (IOException e) {
            System.err.println("Failed to write trace.json: " + e.getMessage());
        }
    }

    public void dump() {
        dump("trace.json");
    }
}

class ArrayTracer extends VisualTracer {
    private List<Integer> currentArray = new ArrayList<>();

    public ArrayTracer() {
        this.visualizerType = "array";
    }

    private String arrJson() {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < currentArray.size(); i++) {
            sb.append(currentArray.get(i));
            if (i < currentArray.size() - 1) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }

    public void initArray(int[] arr) {
        currentArray.clear();
        for (int v : arr) currentArray.add(v);
        record("init_array", "{\"array\": " + arrJson() + "}", "[]",
               "\"初始化数组\"");
    }

    public void compare(int i, int j) {
        int left = (i < currentArray.size()) ? currentArray.get(i) : 0;
        int right = (j < currentArray.size()) ? currentArray.get(j) : 0;
        record("compare", "{\"array\": " + arrJson() + "}",
               "[" + i + ", " + j + "]",
               "\"比较 nums[" + i + "]=" + left + " 和 nums[" + j + "]=" + right + "\"");
    }

    public void swap(int i, int j) {
        if (i < currentArray.size() && j < currentArray.size()) {
            int tmp = currentArray.get(i);
            currentArray.set(i, currentArray.get(j));
            currentArray.set(j, tmp);
        }
        record("swap", "{\"array\": " + arrJson() + "}",
               "[" + i + ", " + j + "]",
               "\"交换位置 " + i + " 和 " + j + "\"");
    }

    public void assign(int index, int value) {
        if (index < currentArray.size()) {
            currentArray.set(index, value);
        }
        record("assign", "{\"array\": " + arrJson() + "}",
               "[" + index + "]",
               "\"赋值 nums[" + index + "] = " + value + "\"");
    }

    public void markSorted(int index) {
        record("mark_sorted", "{\"array\": " + arrJson() + "}",
               "[" + index + "]",
               "\"位置 " + index + " 已归位\"");
    }

    public void movePointer(String name, int value) {
        record("move_pointer",
               "{\"array\": " + arrJson() + ", \"pointers\": {\"" + name + "\": " + value + "}}",
               "[" + value + "]",
               "\"移动指针 " + name + " -> " + value + "\"");
    }

    public void finish() {
        record("finish", "{\"array\": " + arrJson() + "}", "[]", "\"排序完成\"");
        dump();
    }
}

class StackTracer extends VisualTracer {
    private static class Item {
        String id, label, tone;
        Item(String id, String label, String tone) {
            this.id = id; this.label = label; this.tone = tone;
        }
    }
    private List<Item> items = new ArrayList<>();

    public StackTracer() {
        this.visualizerType = "stack-queue";
    }

    private String itemsJson() {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < items.size(); i++) {
            Item it = items.get(i);
            sb.append("{\"id\": \"").append(it.id).append("\", \"label\": \"")
              .append(it.label).append("\", \"tone\": \"").append(it.tone).append("\"}");
            if (i < items.size() - 1) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }

    public void initStack() {
        items.clear();
        record("init_stack", "{\"mode\": \"stack\", \"items\": " + itemsJson() + "}",
               "[]", "\"初始化空栈\"");
    }

    public void push(int value) {
        items.add(new Item("item-" + items.size(), String.valueOf(value), "default"));
        record("push", "{\"mode\": \"stack\", \"items\": " + itemsJson() + "}",
               "[" + (items.size() - 1) + "]",
               "\"入栈：" + value + "\"");
    }

    public int pop() {
        if (items.isEmpty()) return -1;
        Item it = items.remove(items.size() - 1);
        int val = Integer.parseInt(it.label);
        record("pop", "{\"mode\": \"stack\", \"items\": " + itemsJson() + "}",
               "[]", "\"出栈：" + val + "\"");
        return val;
    }

    public void highlightInput(int inputIndex) {
        record("highlight_input",
               "{\"mode\": \"stack\", \"items\": " + itemsJson() + ", \"inputIndex\": " + inputIndex + "}",
               "[" + inputIndex + "]",
               "\"处理输入位置 " + inputIndex + "\"");
    }

    public void finish() {
        boolean matched = items.isEmpty();
        record("finish", "{\"mode\": \"stack\", \"items\": " + itemsJson() + "}",
               "[]", matched ? "\"括号匹配成功！\"" : "\"括号不匹配\"");
        dump();
    }
}

class QueueTracer extends VisualTracer {
    private static class Item {
        String id, label, tone;
        Item(String id, String label, String tone) {
            this.id = id; this.label = label; this.tone = tone;
        }
    }
    private List<Item> items = new ArrayList<>();

    public QueueTracer() {
        this.visualizerType = "stack-queue";
    }

    private String itemsJson() {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < items.size(); i++) {
            Item it = items.get(i);
            sb.append("{\"id\": \"").append(it.id).append("\", \"label\": \"")
              .append(it.label).append("\", \"tone\": \"").append(it.tone).append("\"}");
            if (i < items.size() - 1) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }

    public void initQueue() {
        items.clear();
        record("init_queue", "{\"mode\": \"queue\", \"items\": " + itemsJson() + "}",
               "[]", "\"初始化空队列\"");
    }

    public void enqueue(int value) {
        items.add(new Item("item-" + items.size(), String.valueOf(value), "default"));
        record("enqueue", "{\"mode\": \"queue\", \"items\": " + itemsJson() + "}",
               "[" + (items.size() - 1) + "]",
               "\"入队：" + value + "\"");
    }

    public int dequeue() {
        if (items.isEmpty()) return -1;
        Item it = items.remove(0);
        int val = Integer.parseInt(it.label);
        record("dequeue", "{\"mode\": \"queue\", \"items\": " + itemsJson() + "}",
               "[]", "\"出队：" + val + "\"");
        return val;
    }

    public void finish() {
        record("finish", "{\"mode\": \"queue\", \"items\": " + itemsJson() + "}",
               "[]", "\"队列模拟完成\"");
        dump();
    }
}
