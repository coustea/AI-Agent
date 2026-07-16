# OUTPUT CONTRACT

输出符合 `VisualPlanDraft` 的 JSON。只为内容页生成视觉，不得为封面、学习路线或总结页生成视觉。

## 顶层结构

```json
{
  "slides": [
    { "slide_id": "s03", "visual": { ... } },
    { "slide_id": "s04", "visual": { ... } }
  ]
}
```

- `slides`：1～15 项，每项包含 `slide_id` 和 `visual`
- `slide_id`：原样保留输入故事板中的页面 ID

## visual 字段规范

`visual` 是一个带 `kind` 判别字段的对象，`kind` 只能选择以下闭集之一：{visual_families}

每种 `kind` 的完整字段如下，**不得添加或省略任何字段**：

### kind = "hierarchy"

有根、连通、无环的层级树。

```json
{
  "kind": "hierarchy",
  "nodes": [
    { "label": "根节点", "parent_index": null },
    { "label": "子节点A", "parent_index": 0 },
    { "label": "子节点B", "parent_index": 0 }
  ]
}
```

- `nodes`：1～12 项
- `label`：1～64 字符
- `parent_index`：父节点在 nodes 中的零基索引，根节点为 null；有且仅有一个根节点

### kind = "graph"

有向或无向语义图。

```json
{
  "kind": "graph",
  "directed": true,
  "nodes": [
    { "label": "节点A" },
    { "label": "节点B" }
  ],
  "edges": [
    { "source_index": 0, "target_index": 1, "label": "关系" }
  ]
}
```

- `directed`：布尔值
- `nodes`：1～12 项，每项只有 `label`（1～64 字符）
- `edges`：1～24 项；`source_index`/`target_index` 为 nodes 零基索引；`label` 默认空字符串，最长 48 字符；不允许自环

### kind = "state_machine"

有限状态机，含显式初始态和终态。

```json
{
  "kind": "state_machine",
  "states": [
    { "label": "空闲", "initial": true, "final": false },
    { "label": "运行", "initial": false, "final": false },
    { "label": "完成", "initial": false, "final": true }
  ],
  "transitions": [
    { "source_index": 0, "target_index": 1, "label": "启动" }
  ]
}
```

- `states`：2～12 项；有且仅有一个 `initial: true`；至少一个 `final: true`
- `transitions`：1～24 项；`source_index`/`target_index` 为 states 零基索引

### kind = "timeline"

基于泳道的时间线，含事件和/或消息。

```json
{
  "kind": "timeline",
  "lanes": [
    { "label": "客户端" },
    { "label": "服务器" }
  ],
  "events": [
    { "lane_index": 0, "start": 0.0, "end": 1.5, "label": "发送请求" }
  ],
  "messages": [
    { "source_lane_index": 0, "target_lane_index": 1, "at": 0.5, "label": "请求" }
  ]
}
```

- `lanes`：1～8 项，每项只有 `label`
- `events` 和 `messages` 至少有一项非空
- `events[].lane_index`：lanes 零基索引；`start` < `end`
- `messages[].source_lane_index`/`target_lane_index`：lanes 零基索引

### kind = "memory_layout"

内存布局，含段和引用。

```json
{
  "kind": "memory_layout",
  "segments": [
    { "label": "栈帧", "size": 64.0 },
    { "label": "堆", "size": 128.0 }
  ],
  "references": [
    { "source_segment_index": 0, "target_segment_index": 1, "relation": "pointer", "label": "栈指向堆" }
  ]
}
```

- `segments`：1～16 项；`size` > 0
- `references`：可选，最多 24 项；`relation` 只能是 `"pointer"` 或 `"reference"`

### kind = "data_flow"

数据流图，块之间通过命名端口连接。

```json
{
  "kind": "data_flow",
  "directed": true,
  "blocks": [
    { "label": "输入", "input_ports": [], "output_ports": ["数据"] },
    { "label": "处理", "input_ports": ["数据"], "output_ports": ["结果"] }
  ],
  "flows": [
    { "source_block_index": 0, "source_port_index": 0, "source_port_name": "数据", "target_block_index": 1, "target_port_index": 0, "target_port_name": "数据", "label": "" }
  ]
}
```

- `directed`：必须为 `true`
- `blocks`：2～12 项；每个 block 至少有一个 port（input 或 output）；port 名称在同一个 block 内唯一
- `flows`：1～24 项；`source_port_index`/`target_port_index` 和 `source_port_name`/`target_port_name` 必须指向同一个端口

### kind = "mapping"

两个集合之间的映射或函数关系。

```json
{
  "kind": "mapping",
  "mode": "function",
  "left_set_label": "输入",
  "right_set_label": "输出",
  "left_elements": ["a", "b"],
  "right_elements": ["1", "2"],
  "pairs": [
    { "source_index": 0, "target_index": 0 },
    { "source_index": 1, "target_index": 1 }
  ]
}
```

- `mode`：`"relation"` 或 `"function"`（function 模式下每个 source 最多一个 target）
- `left_elements`/`right_elements`：1～12 项
- `pairs`：1～24 项；索引为零基

### kind = "table_matrix"

语义表格，含行列高亮。

```json
{
  "kind": "table_matrix",
  "headers": ["遍历方式", "时间复杂度"],
  "rows": [
    { "cells": ["前序", "O(n)"] },
    { "cells": ["中序", "O(n)"] }
  ],
  "highlighted_row_indices": [],
  "highlighted_column_indices": []
}
```

- `headers`：1～8 项
- `rows`：1～12 项；每行 cells 数量必须等于 headers 数量
- `highlighted_row_indices`/`highlighted_column_indices`：零基索引数组

### kind = "algorithm_frames"

算法快照序列。

```json
{
  "kind": "algorithm_frames",
  "frames": [
    { "title": "初始", "cells": ["5", "3", "1"], "highlighted_cell_indices": [] },
    { "title": "第1轮", "cells": ["1", "3", "5"], "highlighted_cell_indices": [0] }
  ]
}
```

- `frames`：2～8 项
- `title`：1～32 字符
- `cells`：1～16 项，每项最长 48 字符
- `highlighted_cell_indices`：cells 零基索引数组

### kind = "circuit"

逻辑电路网络。

```json
{
  "kind": "circuit",
  "inputs": [{ "label": "A" }],
  "gates": [{ "label": "AND门", "gate_type": "AND" }],
  "outputs": [{ "label": "Q" }],
  "wires": [
    { "source_kind": "input", "source_index": 0, "target_kind": "gate", "target_index": 0 }
  ]
}
```

- `inputs`/`outputs`：1～8 项
- `gates`：可选，最多 12 项
- `wires`：1～24 项；`source_kind` 为 `"input"` 或 `"gate"`；`target_kind` 为 `"gate"` 或 `"output"`

### kind = "quantitative"

定量数据比较。

```json
{
  "kind": "quantitative",
  "x_axis": { "label": "数据规模", "unit": "n" },
  "y_axis": { "label": "耗时", "unit": "ms" },
  "series": [
    { "label": "算法A", "points": [{ "x_value": 100.0, "y_value": 5.0 }] }
  ]
}
```

- `series`：1～6 项；`points`：1～24 项

### kind = "code"

代码展示。

```json
{
  "kind": "code",
  "language": "python",
  "lines": [
    "def preorder(root):",
    "    if root is None:",
    "        return []",
    "    return [root.val] + preorder(root.left)"
  ],
  "highlighted_line_indices": [0, 3]
}
```

- `language`：1～24 字符
- `lines`：4～18 项，每项最长 120 字符；总字符数不超过 1200
- `highlighted_line_indices`：lines 零基索引数组

### kind = "formula"

公式与推导。

```json
{
  "kind": "formula",
  "expression": "T(n) = 2T(n/2) + O(n)",
  "steps": [
    { "expression": "= 2·2T(n/4) + 2O(n)", "explanation": "递归展开一层" }
  ],
  "variables": [
    { "symbol": "T", "meaning": "时间复杂度函数" }
  ]
}
```

- `expression`：1～320 字符
- `steps`：可选，最多 4 项
- `variables`：可选，最多 12 项

### kind = "composite"

多面板组合，仅在单一视觉族无法表达教学目标时使用。

```json
{
  "kind": "composite",
  "purpose": "同时展示代码和执行状态",
  "panels": [
    { "title": "代码", "width_weight": 1.0, "visual": { "kind": "code", "language": "python", "lines": ["x = 1", "y = 2", "z = x + y", "print(z)"], "highlighted_line_indices": [2] } },
    { "title": "内存", "width_weight": 1.0, "visual": { "kind": "memory_layout", "segments": [{ "label": "x", "size": 8.0 }, { "label": "y", "size": 8.0 }, { "label": "z", "size": 8.0 }], "references": [] } }
  ]
}
```

- `purpose`：1～160 字符
- `panels`：2～3 项；`width_weight` > 0；`visual` 为上述任意一种视觉类型
- 组合总语义标记数不超过 24

## 输入故事板

{storyboard}

## 课程视觉画像

{course_profile}

## 规划规则

1. 每个输入内容页必须恰好返回一次，`slide_id` 必须原样保留，不得缺失、重复或新增页面。
2. 视觉必须直接表达该页的 `question`、`claim` 与 `logic_relation`，不能只装饰标题。
3. 优先采用课程画像中的领域模型，但必须根据当前页教学语义选择最直接的 Visual IR。
4. 图、层级、状态、时序、数据流和映射必须保留显式关系；不得用一组无连接卡片代替。
5. 只输出语义内容和零基索引关系；禁止输出坐标、颜色、CSS、SVG、HTML、组件名或稳定 ID。
6. `composite` 仅在单一视觉族无法表达教学目标时使用，子面板必须互补且保持总语义标记预算。
7. 严格按上述字段规范输出，不得添加任何规范之外的字段（如 title、content、claim、question、relations 等不属于 visual 内部），也不得省略必需字段。
