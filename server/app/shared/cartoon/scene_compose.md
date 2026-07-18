# 场景语义输出契约

当前场景 mode 为 `{{mode}}`，拓扑为 `{{topology}}`，信息密度为 {{density}}。`objects`、`steps` 和每个 step 的 `actions` 数量由内容决定，不设上限；应尽量提供有教学意义的对象和操作，但字段缺失或数组为空时编译器会补齐最小可播放结构。只输出一个 JSON 对象，不要 Markdown、解释、坐标、CSS、ID、完整状态快照或样式。

```json
{
  "mode": "{{mode}}",
  "topology": "{{topology}}",
  "objects": [
    {"name": "source", "label": "输入", "role": "container", "capacity": 2},
    {"name": "tokenA", "label": "任务 A", "role": "token", "value": "A"},
    {"name": "worker", "label": "处理器", "role": "process"}
  ],
  "steps": {{example_steps}}
}
```

对象角色只能为 `container`、`node`、`process`、`token`、`pointer`、`port`、`marker`。`container.capacity` 是非负整数，0 或省略表示没有固定槽位；其他对象即使多给 capacity 也会由编译器忽略。`name`、`label`、`value` 只要能表达对象即可，不设字符上限。

动作是画面变化的唯一来源，`verb` 只能为：

- `reveal`：对象出现；pointer 可以带 `target`，编译器会在可能时建立锚点。
- `focus`、`settle`：强调或确认对象状态。
- `place`、`move`：对象进入容器、槽位、锚点或区域；可以提供 `target`、`slot` 或 `region` 的任意组合，编译器会自动选择可播放的落点。指针优先锚定到 `target`。
- `remove`：对象移出当前结构或离场。
- `connect`、`disconnect`：建立或拆除从 subject 指向 target 的关系；缺少或无效 target 时按幂等空操作处理。
- `update`：修改可见值或状态；缺少 value/state 时保留对象当前值。
- `compare`、`traverse`：让 subject 与 target 进入可观察状态；缺少 target 时只处理 subject。

要求（这些是生成约定，不是额外的拒绝条件）：

1. 每个 step 最好包含一个或多个动作，不限制动作数量；缺少动作时系统会补一个可播放的 reveal，并保留每个动作的中间状态按顺序播放。
2. `narration` 不设字符上限，建议解释动作背后的因果。
3. 过程性内容优先使用 `place`、`move`、`connect`、`traverse`、`update` 或 `remove` 显示状态流动。
4. `comparison` 和 `evidence` 可以通过值、关系或状态变化增强表达。
5. 不要产生“标题 + 大段文字”的对象；对象标签短，具体公式、值、状态放到 `value` 和 `update` 中。
6. `update.state` 只表示视觉强调，只能使用 `idle`、`active`、`success`、`warning`、`error`。业务状态（例如“运行中”“阻塞”“等待 I/O”）请写入 `value`；编译器会把英文 `running`/`processing` 映射为 `active`，把 `blocked` 映射为 `warning`，其他未知状态忽略。
7. `move.region` 使用标准区域值；未知区域会回退到主区域。
8. `subject`、`target`、`slot`、`region`、`value`、`state` 可以按动作需要省略；缺少或无法解析的 `subject` 会回退到当前场景的第一个对象，缺少或无法解析的 `target` 会被忽略，多余字段、重复动作和重复关系会被编译器尽量归一化后继续生成。
