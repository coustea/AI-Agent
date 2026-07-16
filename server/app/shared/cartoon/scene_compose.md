# OUTPUT CONTRACT

输出符合 `_SceneDraft` 的 JSON。只输出这里声明的字段；不要输出 `states`、`placements`、`relations`、实体 ID、状态 ID、位置、容器、区域、颜色或样式字段。

当前场景使用 {{grammar}} 视觉语法，需要恰好 {{beat_count}} 个教学节拍，最多 {{entity_limit}} 个稳定实体，信息密度为 {{density}}。后端会根据节拍确定性编译全部状态、布局、连线和动画；模型只负责教学语义。

## 顶层结构

```json
{
  "entities": [ ... ],
  "beats": [ ... ]
}
```

## entities

稳定对象，贯穿整幕不变。2～{{entity_limit}} 项。

```json
{"label":"实体名称","kind":"container"}
```

- `label`：1～28 字符。
- `kind` 只能是 `container`、`slot`、`token`、`pointer`、`port`、`term`、`code`、`metric`。
- 不要为每一步重新创建实体；实体的出现、移动、更新和连接由 beats 表达。

## beats

严格 {{beat_count}} 项，数组顺序就是教学和动画顺序。

```json
{
  "narration":"16到40个中文字符的旁白，只解释当前变化",
  "caption":"屏幕动作概括",
  "transition":{"kind":"reveal","entity_indexes":[0]},
  "focus_entity_indexes":[0]
}
```

- `narration`：16～40 字符。
- `caption`：1～30 字符。
- `entity_indexes` 与 `focus_entity_indexes`：entities 的零基索引，各数组内不得重复。
- `transition.kind` 只能是 `reveal`、`move`、`insert`、`remove`、`update`、`connect`、`disconnect`、`execute`、`compare`。
- 每个 beat 必须选择能表达真实教学动作的 transition；不要只改旁白或焦点。

## 视觉语法约束

- `concept`：至少两个 `term`，用 reveal、compare、connect 等讲清概念与边界。
- `model`：至少一个 `container`，以及一个 `slot`、`pointer` 或 `port`；用 insert、move、connect 表达组成关系。
- `trace`：至少一个 `container` 和一个 `token`；至少一个 transition 必须是 `move`、`insert`、`remove`、`update` 或 `execute`。
- `evidence`：至少一个 `code`，或至少两个 `metric`；用 execute、update、compare 展示证据。

## 完整 JSON 示例

```json
{
  "entities":[
    {"label":"调用栈","kind":"container"},
    {"label":"当前节点","kind":"token"},
    {"label":"访问结果","kind":"token"}
  ],
  "beats":[
    {
      "narration":"先把根节点放入调用栈，明确本轮访问的起点。",
      "caption":"根节点入栈",
      "transition":{"kind":"insert","entity_indexes":[1]},
      "focus_entity_indexes":[0,1]
    },
    {
      "narration":"执行访问操作后，将节点值写入当前的遍历结果序列。",
      "caption":"记录节点值",
      "transition":{"kind":"execute","entity_indexes":[1,2]},
      "focus_entity_indexes":[1,2]
    },
    {
      "narration":"随后移动到下一待处理节点，继续保持同一条执行链。",
      "caption":"推进到下一节点",
      "transition":{"kind":"move","entity_indexes":[1]},
      "focus_entity_indexes":[0,1]
    }
  ]
}
```

只输出一个 JSON 对象，不要 Markdown、解释或额外字段。
