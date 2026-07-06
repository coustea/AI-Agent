/* C VisualTracer SDK — 生成 TraceEvent JSON 事件流。
 * c_adapter.py 写入临时目录与用户代码一起编译执行。
 * 输出 trace.json 而非 __TRACER__: stdout 协议。*/

#ifndef VISUAL_TRACER_H
#define VISUAL_TRACER_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ===== 内部状态 ===== */

typedef struct {
    int *array;
    int array_len;
    int array_cap;
} vt_state_t;

static vt_state_t vt_global = {NULL, 0, 0};

/* ===== 内部辅助 ===== */

static void vt_ensure_cap(int needed) {
    if (needed <= vt_global.array_cap) return;
    int new_cap = vt_global.array_cap == 0 ? 16 : vt_global.array_cap * 2;
    while (new_cap < needed) new_cap *= 2;
    vt_global.array = (int *)realloc(vt_global.array, new_cap * sizeof(int));
    vt_global.array_cap = new_cap;
}

static int vt_step = 0;
static FILE *vt_json_file = NULL;

static void vt_open_json(void) {
    if (!vt_json_file) {
        vt_json_file = fopen("trace.json", "w");
        if (vt_json_file) {
            fprintf(vt_json_file, "[\n");
        }
    }
}

static void vt_close_json(void) {
    if (vt_json_file) {
        /* Remove trailing comma from last event */
        fseek(vt_json_file, -2, SEEK_CUR);
        fprintf(vt_json_file, "\n]\n");
        fclose(vt_json_file);
        vt_json_file = NULL;
    }
}

static void vt_write_array_json(FILE *f, const int *arr, int len) {
    fprintf(f, "[");
    for (int i = 0; i < len; i++) {
        fprintf(f, "%d", arr[i]);
        if (i < len - 1) fprintf(f, ", ");
    }
    fprintf(f, "]");
}

/* ===== 数组 API ===== */

static void vt_init_array(const int *arr, int len) {
    vt_ensure_cap(len);
    memcpy(vt_global.array, arr, len * sizeof(int));
    vt_global.array_len = len;

    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"init_array\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, arr, len);
    fprintf(vt_json_file, "}}, \"targets\": [], \"message\": \"初始化数组\", "
        "\"line\": null, \"formula\": null},\n");
    vt_step++;
}

static void vt_compare(int i, int j) {
    vt_open_json();
    int left = (i < vt_global.array_len) ? vt_global.array[i] : 0;
    int right = (j < vt_global.array_len) ? vt_global.array[j] : 0;
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"compare\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, vt_global.array, vt_global.array_len);
    fprintf(vt_json_file,
        "}}, \"targets\": [%d, %d], "
        "\"message\": \"比较 nums[%d]=%d 和 nums[%d]=%d\", "
        "\"line\": null, \"formula\": null},\n",
        i, j, i, left, j, right);
    vt_step++;
}

static void vt_swap(int i, int j) {
    if (i < vt_global.array_len && j < vt_global.array_len) {
        int tmp = vt_global.array[i];
        vt_global.array[i] = vt_global.array[j];
        vt_global.array[j] = tmp;
    }
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"swap\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, vt_global.array, vt_global.array_len);
    fprintf(vt_json_file,
        "}}, \"targets\": [%d, %d], "
        "\"message\": \"交换位置 %d 和 %d\", "
        "\"line\": null, \"formula\": null},\n",
        i, j, i, j);
    vt_step++;
}

static void vt_assign(int index, int value) {
    if (index < vt_global.array_len) {
        vt_global.array[index] = value;
    }
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"assign\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, vt_global.array, vt_global.array_len);
    fprintf(vt_json_file,
        "}}, \"targets\": [%d], "
        "\"message\": \"赋值 nums[%d] = %d\", "
        "\"line\": null, \"formula\": null},\n",
        index, index, value);
    vt_step++;
}

static void vt_mark_sorted(int index) {
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"mark_sorted\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, vt_global.array, vt_global.array_len);
    fprintf(vt_json_file,
        "}}, \"targets\": [%d], "
        "\"message\": \"位置 %d 已归位\", "
        "\"line\": null, \"formula\": null},\n",
        index, index);
    vt_step++;
}

static void vt_move_pointer(const char *name, int value) {
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"move_pointer\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, vt_global.array, vt_global.array_len);
    fprintf(vt_json_file,
        ", \"pointers\": {\"%s\": %d}}}, \"targets\": [%d], "
        "\"message\": \"移动指针 %s -> %d\", "
        "\"line\": null, \"formula\": null},\n",
        name, value, value, name, value);
    vt_step++;
}

static void vt_finish(void) {
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"array\", \"type\": \"finish\", "
        "\"state\": {\"structure\": {\"array\": ",
        vt_step, vt_step);
    vt_write_array_json(vt_json_file, vt_global.array, vt_global.array_len);
    fprintf(vt_json_file,
        "}}, \"targets\": [], "
        "\"message\": \"排序完成\", "
        "\"line\": null, \"formula\": null},\n");
    vt_step++;
    vt_close_json();
}

/* ===== 栈/队列 API ===== */

typedef struct {
    char label[32];
    char tone[16];
} vt_item_t;

static vt_item_t *vt_items = NULL;
static int vt_items_len = 0;
static int vt_items_cap = 0;
static char vt_sq_mode[8] = "stack";

static void vt_ensure_items_cap(int needed) {
    if (needed <= vt_items_cap) return;
    int new_cap = vt_items_cap == 0 ? 16 : vt_items_cap * 2;
    while (new_cap < needed) new_cap *= 2;
    vt_items = (vt_item_t *)realloc(vt_items, new_cap * sizeof(vt_item_t));
    vt_items_cap = new_cap;
}

static void vt_write_items_json(FILE *f) {
    fprintf(f, "[");
    for (int i = 0; i < vt_items_len; i++) {
        fprintf(f, "{\"id\": \"item-%d\", \"label\": \"%s\", \"tone\": \"%s\"}",
                i, vt_items[i].label, vt_items[i].tone);
        if (i < vt_items_len - 1) fprintf(f, ", ");
    }
    fprintf(f, "]");
}

static void vt_init_stack(void) {
    vt_items_len = 0;
    strcpy(vt_sq_mode, "stack");
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"init_stack\", "
        "\"state\": {\"structure\": {\"mode\": \"stack\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [], \"message\": \"初始化空栈\", "
        "\"line\": null, \"formula\": null},\n");
    vt_step++;
}

static void vt_push(int value) {
    vt_ensure_items_cap(vt_items_len + 1);
    snprintf(vt_items[vt_items_len].label, 32, "%d", value);
    strcpy(vt_items[vt_items_len].tone, "default");
    vt_items_len++;
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"push\", "
        "\"state\": {\"structure\": {\"mode\": \"stack\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [%d], "
        "\"message\": \"入栈：%d\", "
        "\"line\": null, \"formula\": null},\n",
        vt_items_len - 1, value);
    vt_step++;
}

static int vt_pop(void) {
    if (vt_items_len <= 0) return -1;
    vt_items_len--;
    int val = atoi(vt_items[vt_items_len].label);
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"pop\", "
        "\"state\": {\"structure\": {\"mode\": \"stack\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [], "
        "\"message\": \"出栈：%d\", "
        "\"line\": null, \"formula\": null},\n",
        val);
    vt_step++;
    return val;
}

static void vt_highlight_input(int input_index) {
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"highlight_input\", "
        "\"state\": {\"structure\": {\"mode\": \"stack\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, ", \"inputIndex\": %d}}, \"targets\": [%d], "
        "\"message\": \"处理输入位置 %d\", "
        "\"line\": null, \"formula\": null},\n",
        input_index, input_index, input_index);
    vt_step++;
}

static void vt_init_queue(void) {
    vt_items_len = 0;
    strcpy(vt_sq_mode, "queue");
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"init_queue\", "
        "\"state\": {\"structure\": {\"mode\": \"queue\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [], \"message\": \"初始化空队列\", "
        "\"line\": null, \"formula\": null},\n");
    vt_step++;
}

static void vt_enqueue(int value) {
    vt_ensure_items_cap(vt_items_len + 1);
    snprintf(vt_items[vt_items_len].label, 32, "%d", value);
    strcpy(vt_items[vt_items_len].tone, "default");
    vt_items_len++;
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"enqueue\", "
        "\"state\": {\"structure\": {\"mode\": \"queue\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [%d], "
        "\"message\": \"入队：%d\", "
        "\"line\": null, \"formula\": null},\n",
        vt_items_len - 1, value);
    vt_step++;
}

static int vt_dequeue(void) {
    if (vt_items_len <= 0) return -1;
    int val = atoi(vt_items[0].label);
    for (int i = 1; i < vt_items_len; i++) {
        vt_items[i - 1] = vt_items[i];
    }
    vt_items_len--;
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"dequeue\", "
        "\"state\": {\"structure\": {\"mode\": \"queue\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [], "
        "\"message\": \"出队：%d\", "
        "\"line\": null, \"formula\": null},\n",
        val);
    vt_step++;
    return val;
}

static void vt_stack_finish(void) {
    int matched = (vt_items_len == 0);
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"finish\", "
        "\"state\": {\"structure\": {\"mode\": \"%s\", \"items\": ",
        vt_step, vt_step, vt_sq_mode);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [], "
        "\"message\": \"%s\", "
        "\"line\": null, \"formula\": null},\n",
        matched ? "括号匹配成功！" : "括号不匹配");
    vt_step++;
    vt_close_json();
}

static void vt_queue_finish(void) {
    vt_open_json();
    fprintf(vt_json_file,
        "  {\"id\": \"evt-%d\", \"step\": %d, \"domain\": \"data_structure\", "
        "\"visualizerType\": \"stack-queue\", \"type\": \"finish\", "
        "\"state\": {\"structure\": {\"mode\": \"queue\", \"items\": ",
        vt_step, vt_step);
    vt_write_items_json(vt_json_file);
    fprintf(vt_json_file, "}}, \"targets\": [], "
        "\"message\": \"队列模拟完成\", "
        "\"line\": null, \"formula\": null},\n");
    vt_step++;
    vt_close_json();
}

#endif /* VISUAL_TRACER_H */
