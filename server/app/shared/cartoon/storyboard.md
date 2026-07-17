# OUTPUT CONTRACT

输出符合 `_StoryboardDraft` 的 JSON。只输出本规范声明的字段；默认字段可省略，不得用 `null` 代替空值。

## 顶层结构

```json
{
  "title": "课程标题",
  "scenes": [ ... ]
}
```

- `title`：课程标题应直接点明学习主题，不使用内部流程或生成阶段术语
- `scenes`：{{scene_count}} 个场景，深度为 {{lesson_depth}}，信息密度为 {{density}}。场景数量必须严格为 {{scene_count}} 个，不得多一个或少一个。

## scenes 字段规范

每个场景只允许以下三个字段：

```json
{
  "title": "场景标题",
  "teaching_goal": "本场景要让学生理解什么",
  "grammar": "concept"
}
```

- `title`：简洁的学习者可见标题；不得出现 orient、model、trace、教学目标、学生能够等内部标签
- `teaching_goal`：用一句话描述本场景的教学目标
- `grammar`：只能选择以下四种之一：
  - `"concept"`：用公式、关键词和层次关系建立直觉，不要把同义词堆叠成空卡片列表
  - `"model"`：展示容器、槽位、端口、指针和真实关系
  - `"trace"`：展示同一批实体在操作前后的迁移、插入、删除或更新
  - `"evidence"`：用短代码执行、复杂度对比、实验结果或决策关系提供证据

## 教学顺序约束

1. 第一幕使用 `"concept"`，明确学习者要理解的核心问题。
2. 整套分镜必须包含至少三种不同的 grammar，优先覆盖 `"concept"`、`"model"`、`"trace"`。
3. 最后一幕使用 `"concept"` 或 `"model"`，收束可迁移的判断方法。
4. 每幕只承担一个清晰的教学推进任务，不重复标题或目标。
5. 每幕的 `teaching_goal` 必须能导向一个可观察的画面结论：公式或不变量、结构关系、过程状态变化、或可比较的证据；不要写成泛泛的"理解概念"或"掌握方法"。

## 4 场景示例

```json
{
  "title": "二叉树核心机制与高频考点",
  "scenes": [
    {"title": "二叉树性质与遍历核心公式", "teaching_goal": "建立节点数与深度的数学约束直觉", "grammar": "concept"},
    {"title": "非递归中序遍历的栈执行模型", "teaching_goal": "展示栈容器与指针在遍历中的协作关系", "grammar": "model"},
    {"title": "AVL树插入与旋转调整过程", "teaching_goal": "追踪节点插入引发失衡后四种旋转操作的指针迁移", "grammar": "trace"},
    {"title": "线索化与哈夫曼树的应试判定", "teaching_goal": "通过WPL计算验证提供决策证据", "grammar": "evidence"}
  ]
}
```

## 禁止输出

不得输出坐标、CSS、动画选择器、解释文字或 scenes 之外的字段。
