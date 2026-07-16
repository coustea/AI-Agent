# OUTPUT CONTRACT

输出符合 `_SceneDraft` 的 JSON。严格按以下字段规范输出，不得添加或省略任何字段。

当前场景使用 {{grammar}} 视觉语法，需要 {{beat_count}} 个教学节拍、{{state_count}} 个连续状态，最多 {{entity_limit}} 个稳定实体，信息密度为 {{density}}。

## 顶层结构

```json
{
  "entities": [ ... ],
  "states": [ ... ],
  "beats": [ ... ]
}
```

## entities 字段规范

稳定对象，贯穿整幕不变。2～{{entity_limit}} 个。

```json
{
  "label": "实体名称",
  "kind": "container",
  "detail": "补充说明",
  "initial_value": "",
  "orientation": "vertical",
  "tone": "primary"
}
```

- `label`：1～28 字符
- `kind`：只能选择以下之一：
  - `"container"`：容器，可包含其他实体
  - `"slot"`：槽位
  - `"token"`：令牌/数据项
  - `"pointer"`：指针/引用
  - `"port"`：端口
  - `"term"`：术语/概念
  - `"code"`：代码片段
  - `"metric"`：度量值
- `detail`：可选，最长 72 字符
- `initial_value`：可选，最长 200 字符；kind=code 时放函数签名或关键代码片段（不超过 200 字符），kind=metric 时放初始度量值
- `orientation`：`"vertical"` | `"horizontal"` | `"radial"`，默认 `"vertical"`
- `tone`：`"primary"` | `"secondary"` | `"accent"` | `"warning"`，默认 `"primary"`

## states 字段规范

连续状态序列。{{state_count}} 个（即 beat_count + 1 个）。

```json
{
  "label": "状态名称",
  "annotation": "状态说明",
  "placements": [ ... ],
  "relations": [ ... ]
}
```

- `label`：1～42 字符
- `annotation`：可选，最长 72 字符
- `placements`：2～9 项，**必须恰好覆盖全部实体一次**
- `relations`：可选，最多 18 项

### placements 字段

```json
{
  "entity_index": 0,
  "container_index": null,
  "slot": null,
  "region": "main",
  "visible": true,
  "value": "",
  "status": "idle"
}
```

- `entity_index`：entities 零基索引，0～8
- `container_index`：可选，只能指向 kind=container 的实体索引；slot 存在时必填
- `slot`：可选，容器内语义顺序，0～15
- `region`：`"main"` | `"input"` | `"output"` | `"left"` | `"right"` | `"top"` | `"bottom"` | `"code"` | `"result"`
- `visible`：布尔值
- `value`：可选，最长 200 字符；code 实体可放当前高亮行，metric 实体放数值变化
- `status`：`"idle"` | `"active"` | `"success"` | `"warning"` | `"error"`

### relations 字段

```json
{
  "source_index": 0,
  "target_index": 1,
  "label": "关系描述",
  "directed": true,
  "tone": "primary"
}
```

- `source_index`/`target_index`：entities 零基索引；不允许自环
- `label`：可选，最长 30 字符
- `directed`：布尔值，默认 true
- `tone`：`"primary"` | `"secondary"` | `"accent"` | `"warning"`

## beats 字段规范

教学节拍，形成严格状态链。{{beat_count}} 个。

```json
{
  "claim": "本节拍的教学主张",
  "narration": "16到60个中文字符的旁白",
  "caption": "屏幕上正在发生的事",
  "before_state_index": 0,
  "after_state_index": 1,
  "transition": { ... },
  "focus_entity_indexes": [0, 1]
}
```

- `claim`：1～72 字符
- `narration`：16～60 个中文字符，只解释当前变化
- `caption`：1～30 字符，概括屏幕上正在发生的事
- `before_state_index`/`after_state_index`：states 零基索引；第 0 个节拍 (0,1)，第 1 个 (1,2)，依次类推
- `focus_entity_indexes`：1～6 个 entities 零基索引

### transition 字段

```json
{
  "kind": "reveal",
  "entity_indexes": [0],
  "relation_label": ""
}
```

- `kind`：只能选择以下之一：
  - `"reveal"`：揭示/显示
  - `"move"`：移动
  - `"insert"`：插入
  - `"remove"`：移除
  - `"update"`：更新值或状态
  - `"connect"`：建立连接
  - `"disconnect"`：断开连接
  - `"execute"`：执行操作
  - `"compare"`：比较
- `entity_indexes`：1～6 个 entities 零基索引
- `relation_label`：可选，最长 30 字符

## 核心规则

1. entities 是贯穿整幕的稳定对象；状态只能改变对象的容器归属、槽位、区域、可见性、值、状态或关系，不能为每个状态重建对象。
2. 每个 state 的 placements 必须恰好覆盖全部实体一次。
3. container_index 只能指向 kind=container 的实体；slot 表示容器内部的语义顺序，不是像素坐标。
4. beats 必须形成严格状态链：第 0 个节拍从状态 0 到 1，第 1 个从 1 到 2，依次类推。
5. 每个节拍的前后状态必须有真实语义变化。只改变 focus、透明度或强调色无效。
6. narration 使用 16 到 60 个中文字符，只解释当前变化；caption 使用不超过 30 个字符概括屏幕上正在发生的事。
7. claim、narration、caption 与可见变化一一对应，不得讲解画面中不存在的操作。

## 语法约束（必须严格遵守，否则校验失败）

- concept：**至少包含 2 个 kind=term 的实体**；通过 visible、region、relation 的变化建立概念结构。
- model：**必须包含 1 个 kind=container 和至少 1 个 kind=slot/pointer/port 的实体**；明确组成和约束。
- trace：**必须包含 1 个 kind=container 和 1 个 kind=token 的实体**；至少 1 个节拍使用 move/insert/remove/update/execute 转场；通过 container_index、slot、visible、value 展示操作前后差异。
- evidence：**必须包含 1 个 kind=code 或至少 2 个 kind=metric 的实体**；使用 code、metric、term 与 value/status 变化展示执行或比较证据。

## 禁止输出

不得输出坐标、尺寸、CSS、HTML、GSAP、选择器或内部 ID。所有引用只使用零基索引。
