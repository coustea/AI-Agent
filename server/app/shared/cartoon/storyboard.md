# 输出契约

只输出符合以下字段结构的 JSON，不要 Markdown 或解释。课程深度为 {{lesson_depth}}，信息密度为 {{density}}。成片目标时长约 {{target_duration_seconds}} 秒，建议控制在 {{scene_guidance}} 幕左右；主题简单时可以更少，不能为了凑时长重复概念。每一幕会独立生成配音、字幕、质量采样和渲染，因此应只保留一个清晰问题，后续每幕建议约 {{step_guidance}} 个有因果差异的教学步骤。超出建议时只要内容完整正确即可，系统不会因幕数或时长拒绝该 JSON。

```json
{
  "title": "课程标题",
  "scenes": {{example_scenes}}
}
```

`mode` 只能为：

- `concept`：建立定义、条件、公式或不变量，不做文字卡片清单。
- `mechanism`：展示部件、边界、接口或组成关系。
- `execution`：适合播放状态如何随操作推进。
- `comparison`：让两种策略、状态或结果在同一时间轴上可比较。
- `evidence`：以复杂度、计数、输出或判定结果验证结论。

`topology` 只能为：`hierarchical`、`network`、`flow`、`sequence`、`grid`、`spatial`。它决定画面组织关系，不是装饰标签：树/层级使用 `hierarchical`，依赖或通信使用 `network`，输入—处理—输出使用 `flow`，时间或步骤使用 `sequence`，矩阵和状态表使用 `grid`，公式与概念关系使用 `spatial`。

教学弧线：

1. 第一幕建议使用 `concept` 建立共同语境。
2. 可以自由选择 mode；过程性内容优先使用 `mechanism` 或 `execution`。
3. 最后一幕可以使用 `concept`、`comparison` 或 `evidence` 收束。
4. 建议每幕聚焦一个主要问题。
5. 优先让同一对象在一幕中保持身份，并通过状态改变推进讲解。
6. 用有限的场景覆盖完整教学弧线；每幕随后只会获得有限的旁白和操作预算，因此标题与教学目标必须具体且不重复。

禁止输出坐标、CSS、动画、对象 ID、字段之外的内容，或任何课程内部流程标签。
