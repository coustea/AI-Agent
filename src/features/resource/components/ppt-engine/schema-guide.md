# PptEngine Data-Driven JSON Schema Protocol

为了实现高灵活度的排版布局，前端已从“扁平死板的固定页面模版”升级为**“数据驱动的插槽区块架构 (Layout + Slots + Blocks)”**。

AI 或后端在生成 PPT 数据时，必须严格遵守以下嵌套的 JSON 结构规范：

## 核心架构
每页幻灯片 (Slide) 不再固定其具体业务类型，而是通过以下三个层级组合：
1. **Layout (布局)**：定义页面的区域划分（如左右分屏、中心聚焦、网格排列等）。
2. **Slots (插槽)**：Layout 所划分出的具体容器区域（如 `left`, `right`, `main`）。
3. **Blocks (区块)**：填充在 Slot 中的最小原子级富文本或展示组件（如 `Heading`, `Text`, `Callout`, `Formula`）。

## JSON 示例结构

```json
{
  "template_id": "theme-logic-blue",
  "topic": "系统架构设计",
  "author": "AI 助手",
  "slides": [
    {
      "id": "slide-1",
      "layout": "SplitScreen",
      "layoutConfig": {
        "ratio": "4:6"
      },
      "slots": {
        "left": [
          { "id": "b1", "type": "Heading", "level": 1, "content": "核心原理" },
          { "id": "b2", "type": "Text", "content": "采用数据劫持与发布订阅模式..." }
        ],
        "right": [
          { "id": "b3", "type": "Callout", "intent": "info", "icon": "💡", "content": "这极大地提升了开发效率" },
          { "id": "b4", "type": "Code", "language": "javascript", "code": "const state = reactive({})" }
        ]
      }
    }
  ]
}
```

## 支持的 Layout 类型与对应的 Slots

1. **`FocusTitle`**：中心聚焦布局（适合封面、重点标题页）
   - Slots: `main`

2. **`SplitScreen`**：分屏布局（适合并排对比或图文组合）
   - config: `{ ratio: string }`（如 `"4:6"`, `"5:5"`, `"6:4"`）
   - Slots: `left`, `right`

3. **`BentoGrid`**：便当盒智能网格（适合多卡片信息展示）
   - Slots: `main`（内部 Blocks 会被 CSS Grid 自动流式布局成卡片形式）

4. **`LayerStack`**：垂直分层堆栈（适合架构图层或递进推演）
   - Slots: `main`（垂直等距或自适应堆叠排列）

## 支持的 Block 组件字典

每个 Block 必须包含 `id` 和 `type` 字段，以及其专属的数据字段：

- **Heading** (`type: "Heading"`)
  - `level`: 1, 2, 3
  - `content`: 标题文本
- **Text** (`type: "Text"`)
  - `content`: 正文内容
  - `format`: (可选) "markdown" 或 "plain"
- **Callout** (`type: "Callout"`)
  - `intent`: "info", "warning", "success", "danger"
  - `icon`: Emoji 图标 (如 "💡", "⚠️")
  - `content`: 提示内容
- **Code** (`type: "Code"`)
  - `language`: 代码语言 (如 "python", "javascript")
  - `code`: 具体代码片段
  - `highlightLines`: (可选) 高亮行号数组，如 `[1, 3]`
- **BigNumber** (`type: "BigNumber"`)
  - `number`: 核心数字 (如 "99.9")
  - `unit`: (可选) 单位 (如 "%")
  - `label`: 说明标签 (如 "系统可用性")
- **Formula** (`type: "Formula"`)
  - `formula`: LaTeX 公式字符串
- **Timeline** (`type: "Timeline"`)
  - `steps`: 数组，包含 `{ title, description, time }`
- **Terminal** (`type: "Terminal"`)
  - `command`: (可选) 执行的命令
  - `output`: 终端输出文本
