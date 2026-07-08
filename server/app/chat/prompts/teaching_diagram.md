# 教学图解 JSON 结构参考

本文档是 tutor_agent.md 的参考附录，定义了 `<diagram>` 标签内 JSON 的结构规范。
LLM 在输出图解时必须严格遵循此结构。

## 顶层结构

```json
{
  "graph_type": "comparison|flowchart|sequence|framework|summary|hierarchy|tree|grid|protocol|timeline",
  "title": "主标题",
  "subtitle": "副标题（可选）",
  "teaching_goal": "教学目标",
  "course": "课程名称（可选）",
  "difficulty": "beginner|intermediate|advanced",
  "visual_content": { /* 结构由 graph_type 决定 */ },
  "teaching_content": {
    "core_explanation": "核心解释",
    "key_points": ["要点1", "要点2"],
    "common_mistakes": ["误区1"],
    "examples": ["示例1"],
    "summary": "一句话总结"
  }
}
```

## graph_type 选择规则

| 绘图类型 | 推荐场景 | 约束限制 |
|:---|:---|:---|
| `comparison` | 区分易混概念、双实体对比 | 必须包含 left_entity, right_entity 及 2-8 个对比维度 |
| `flowchart` | 展示算法、状态流、处理步骤 | 2-6 个节点 |
| `sequence` | 交互时序、握手协议 | 2-5 个 actor，3-8 条消息，**禁止自环**（from ≠ to） |
| `framework` | 知识树、章节知识脉络大纲 | 2-6 个模块，每模块 1-8 个小项 |
| `summary` | 必要条件、核心定律、多卡片卡包 | 2-8 张总结卡片 |
| `hierarchy` | 分类体系、多叉树结构关系 | 2-6 个分支，children 只能为单层字符串数组 |
| `tree` | 树形数据结构、二叉树 | 提供 root_id 和平铺的 nodes 列表 |
| `grid` | 数组、连续内存、网格矩阵 | 支持 horizontal, vertical, matrix 布局 |
| `protocol` | 协议帧格式、报文首部字段 | 支持 vertical 或 horizontal_split |
| `timeline` | 并发执行时间轨道、CPU 调度 | 包含 tracks 及各轨道的 blocks |

## 各 graph_type 的 visual_content 结构

### comparison（对比图）

```json
{
  "left_entity": { "name": "实体A", "core_label": "标签A", "short_desc": "描述A" },
  "right_entity": { "name": "实体B", "core_label": "标签B", "short_desc": "描述B" },
  "dimensions": [
    { "name": "维度1", "left": "A的值", "right": "B的值" }
  ],
  "visual_summary": { "left_keyword": "A关键词", "right_keyword": "B关键词", "center_conclusion": "结论" }
}
```

### flowchart（流程图）

```json
{
  "direction": "vertical|horizontal",
  "nodes": [
    { "id": "n1", "title": "开始", "short_desc": "描述", "type": "start|process|decision|end|danger" }
  ],
  "edges": [
    { "from": "n1", "to": "n2", "label": "标签（可选）" }
  ]
}
```

### sequence（时序图）

```json
{
  "actors": ["参与者1", "参与者2"],
  "messages": [
    { "from": "参与者1", "to": "参与者2", "label": "消息标签", "detail": "详细说明（可选）" }
  ]
}
```

**严禁自环消息**：`from` 和 `to` 不能相同。

### framework（知识框架图）

```json
{
  "center": "中心主题",
  "modules": [
    { "title": "模块1", "items": ["知识点1", "知识点2"] }
  ]
}
```

### summary（总结卡片图）

```json
{
  "cards": [
    { "title": "卡片标题", "short_desc": "卡片描述" }
  ]
}
```

### hierarchy（层级概括图）

```json
{
  "root": "根节点名称",
  "branches": [
    { "title": "分支标题", "children": ["子项1", "子项2"] }
  ]
}
```

### tree（二叉树图）

```json
{
  "root_id": "root",
  "nodes": [
    { "id": "root", "label": "1", "left_id": "l1", "right_id": "r1", "type": "normal|highlight|null", "detail": "说明（可选）" }
  ]
}
```

### grid（网格/内存/指针图）

```json
{
  "layout": "horizontal|vertical|matrix",
  "cols": 4,
  "cells": [
    { "index": 0, "label": "值", "status": "normal|active|empty|pointer", "pointer": "指针名（可选）", "detail": "说明（可选）" }
  ]
}
```

### protocol（协议字段图）

```json
{
  "orientation": "vertical|horizontal_split",
  "fields": [
    { "name": "字段名", "detail": "说明", "width_ratio": 1, "highlight": false }
  ]
}
```

### timeline（时序轴/生命周期图）

```json
{
  "axis_label": "时间单位",
  "tracks": [
    {
      "track_name": "轨道名称",
      "blocks": [
        { "label": "事件", "start": 0, "duration": 5, "status": "normal|active|idle|stall" }
      ]
    }
  ]
}
```

## 质量检查

输出 `<diagram>` 前自检：
- graph_type 是否与问题内容匹配？
- visual_content 结构是否符合对应 graph_type 的规范？
- sequence 类型是否有自环消息？
- 图解的主题、标题和所有内容是否严格来自学生问题和回答？
- teaching_content 是否包含完整的 core_explanation、key_points、summary？

## 约束

- **图解必须紧扣学生问题的主题**：严禁偏题生成与问题无关的图解
- `sequence` 类型绝对禁止自环消息（from 与 to 相同，前端会崩溃）
- 节点/消息数量应控制在推荐范围内，过多会导致移动端显示错位
- 叶节点文字应精炼，不超过 15 字
