# PptEngine 新教学课件协议

前端 PPT 引擎只接受本文定义的计算机教学课件 JSON 协议，并直接校验结构化 JSON。

## 顶层结构

```json
{
  "template_id": "algorithm-walkthrough",
  "theme_id": "logic-blue",
  "title": "快速排序的分区机制",
  "audience": "计算机专业大二学生",
  "slides": [
    {
      "id": "slide-01",
      "chapter_id": "partition-basics",
      "role": "cover",
      "title": "分区让基准值左右有序分离",
      "subtitle": "从一次 partition 看递归为何能收敛",
      "layout": "HeroCover",
      "layout_config": null,
      "slots": {
        "main": [
          {
            "block_id": "cover-summary",
            "type": "Text",
            "content": "一次分区会把小于 pivot 的元素移到左边，把大于 pivot 的元素移到右边。",
            "format": "plain"
          },
          {
            "block_id": "cover-goal",
            "type": "KeyPoint",
            "label": "目标",
            "content": "看懂指针移动与交换条件"
          }
        ]
      },
      "takeaway": "先分区，再递归处理左右子区间。",
      "speaker_notes": "先让学生口头描述 pivot 左右两侧应满足的性质，再进入代码与状态变化。",
      "source_refs": ["content", "code"]
    }
  ]
}
```

## 顶层字段

- `template_id`: `cs-concept | algorithm-walkthrough | system-architecture | debugging-lab | project-case`
- `theme_id`: `logic-blue | paper-light | lab-light`
- `title`: 整套课件标题
- `audience`: 受众描述
- `slides`: 6–16 页新版幻灯片数组

## 幻灯片字段

每页必须包含：

- `id`
- `chapter_id`
- `role`
- `title`
- `layout`
- `layout_config`（可为 `null`）
- `slots`
- `takeaway`
- `speaker_notes`
- `source_refs`

支持的 `role`：

- `cover`
- `objectives`
- `concept`
- `mechanism`
- `example`
- `architecture`
- `workflow`
- `symptom`
- `diagnosis`
- `code_demo`
- `implementation`
- `tradeoff`
- `practice`
- `summary`

## 支持的 Layout 与 Slots

- `HeroCover` → `main`
- `LearningMap` → `map`, `objectives`
- `ConceptExplain` → `concept`, `example`
- `CardGrid` → `featured`, `cards`
- `CodeLab` → `code`, `explanation`, `result`
- `FlowTrace` → `trace`, `explanation`, `invariant`
- `ArchitectureCanvas` → `diagram`, `explanation`
- `CompareMatrix` → `comparison`, `takeaway`
- `PracticeChallenge` → `challenge`, `checkpoint`

前端会严格校验 slot 名称是否与 layout 对应；不匹配就直接判定为无效协议。

## 支持的 Block 类型

- `Text`
- `Callout`
- `Code`
- `Terminal`
- `Formula`
- `KeyPoint`
- `Diagram`
- `Table`
- `CardList`
- `CodeAnnotation`
- `TraceStep`
- `Practice`

所有 block 必须使用 `block_id`，不再接受旧的 `id`。

### 关键字段约定

- `Code.highlight_lines`: 高亮行号数组
- `CodeAnnotation.items`: `[{ line, content }]`
- `TraceStep.steps`: `[{ title, detail, state_change: { name, before, after } }]`
- `Practice`: `{ question, difficulty, hints, checkpoint }`
- `Diagram`: `{ direction, nodes, edges }`
- `Table`: `{ columns, rows }`

## 前端行为约束

- 只要缺少 `template_id/theme_id/title/audience/slides` 任一关键字段，就拒绝渲染。
- 旧协议字段如 `topic`、`author`、`metadata.background_override`、`layoutConfig`、`highlightLines` 不再被解释。
- 新协议校验失败时，资源卡片在挂载 `PptView.vue` 前被记录并省略，不渲染替代内容。
