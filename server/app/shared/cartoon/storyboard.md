# OUTPUT CONTRACT

输出符合 `_StoryboardDraft` 的 JSON。严格按以下字段规范输出，不得添加或省略任何字段。

## 顶层结构

```json
{
  "title": "课程标题",
  "course": "计算机类本科课程",
  "scenes": [ ... ]
}
```

- `title`：1～72 字符
- `course`：1～40 字符，默认 "计算机类本科课程"
- `scenes`：{{scene_count}} 个场景，深度为 {{lesson_depth}}，信息密度为 {{density}}

## scenes 字段规范

每个场景只允许以下三个字段：

```json
{
  "title": "场景标题",
  "teaching_goal": "本场景要让学生理解什么",
  "grammar": "concept"
}
```

- `title`：1～54 字符，面向学习者，不得出现 orient、model、trace、教学目标、学生能够等内部标签
- `teaching_goal`：1～100 字符，描述本场景的教学目标
- `grammar`：只能选择以下四种之一：
  - `"concept"`：用类比、关键词和层次关系建立直觉，不做卡片列表
  - `"model"`：展示容器、槽位、端口、指针和真实关系
  - `"trace"`：展示同一批实体在操作前后的迁移、插入、删除或更新
  - `"evidence"`：用短代码执行、复杂度对比、实验结果或决策关系提供证据

## 教学顺序约束

1. 第一幕使用 `"concept"`，明确学习者要理解的核心问题。
2. 整套分镜必须同时包含 `"concept"`、`"model"`、`"trace"`、`"evidence"`。
3. 最后一幕使用 `"concept"` 或 `"model"`，收束可迁移的判断方法。
4. 每幕只承担一个清晰的教学推进任务，不重复标题或目标。

## 禁止输出

不得输出坐标、CSS、动画选择器、解释文字或 scenes 之外的字段。
