# OUTPUT CONTRACT

输出符合 `_SceneDraft` 的 JSON。只输出这里声明的字段；不要输出 `states`、`placements`、`relations`、实体 ID、状态 ID、位置、容器、区域、颜色、样式、实体类型或焦点字段。

当前场景使用 {{grammar}} 视觉语法，目标为 {{beat_count}} 个教学节拍、最多 {{entity_limit}} 个稳定实体，信息密度为 {{density}}。后端会根据节拍确定性编译全部状态、布局、连线和动画；模型只负责教学语义。

## 顶层结构

```json
{
  "entities": [ ... ],
  "beats": [ ... ]
}
```

## entities

稳定对象，贯穿整幕不变。保持精简；只声明讲清当前变化所需的实体。

```json
["实体名称", "另一个稳定对象"]
```

- 每项是稳定实体的完整名称；不要输出对象、ID、类型、位置或序号。
- 名称必须精确复用于 `beats.targets`，不要为每一步重新创建实体。
- 后端根据场景语法生成视觉类型、状态、布局、连线和动画。

## beats

以 {{beat_count}} 项为目标，数组顺序就是教学和动画顺序。

```json
{
  "narration":"旁白只解释当前变化，完整表达因果关系",
  "action":"reveal",
  "targets":["实体名称"]
}
```

- `narration`：完整解释当前变化；不设字符上限，系统会按语音时长拆分字幕。
- `action` 只能是 `reveal`、`move`、`insert`、`remove`、`update`、`connect`、`disconnect`、`execute`、`compare`。
- `targets` 是 `entities` 中已有名称的数组，必须逐字一致，各项不得重复。
- 每个 beat 必须选择能表达真实教学动作的 action；不要只改旁白。

## 视觉语法指导

- `concept`：选择用于比较和建立关联的核心术语，配合 reveal、compare、connect 讲清概念与边界。
- `model`：选择真实结构中的对象与关系，例如节点、栈、队列、端口或指针；后端负责映射视觉类型。
- `trace`：选择同一过程中的输入、当前对象与结果，优先使用 move、insert、remove、update、execute 表达推进。
- `evidence`：选择可执行步骤、指标或结果，配合 execute、update、compare 展示证据。

这些语法是构图指导，不要为了凑齐某种实体类型而添加与课程主题无关的对象。

## 完整 JSON 示例

```json
{
  "entities":[
    "调用栈",
    "当前节点",
    "访问结果"
  ],
  "beats":[
    {
      "narration":"先把根节点放入调用栈，明确本轮访问的起点。",
      "action":"insert",
      "targets":["调用栈","当前节点"]
    },
    {
      "narration":"执行访问操作后，将节点值写入当前的遍历结果序列。",
      "action":"execute",
      "targets":["当前节点","访问结果"]
    },
    {
      "narration":"随后移动到下一待处理节点，继续保持同一条执行链。",
      "action":"move",
      "targets":["当前节点"]
    }
  ]
}
```

只输出一个 JSON 对象，不要 Markdown、解释或额外字段。
