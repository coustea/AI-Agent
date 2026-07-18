# 教学图解 Mermaid 输出参考

本文档是 tutor_agent.md 的参考附录。图解由模型直接生成 Mermaid 源码，服务端校验后用 Mermaid 渲染为 PNG。

## 顶层结构

`<diagram>` 内必须是合法 JSON，Mermaid 源码放在 JSON 字符串 `mermaid_source` 中，换行写作 `\n`。
使用 `mermaid_source` 时不要输出旧版 `visual_content` 字段；图的全部结构直接写入 Mermaid，避免重复生成和格式修复。

```json
{
  "graph_type": "comparison|flowchart|sequence|framework|summary|hierarchy|tree|grid|protocol|timeline",
  "title": "中文主标题",
  "subtitle": "中文副标题（可选）",
  "teaching_goal": "教学目标",
  "course": "课程名称（可选）",
  "difficulty": "beginner|intermediate|advanced",
  "mermaid_source": "flowchart TB\n    A[开始] --> B[结束]",
  "teaching_content": {
    "core_explanation": "核心解释",
    "key_points": ["要点1", "要点2"],
    "common_mistakes": ["误区1"],
    "examples": ["示例1"],
    "summary": "一句话总结"
  }
}
```

## 类型选择

| graph_type | Mermaid 声明 | 推荐场景 |
|:---|:---|:---|
| `comparison` | `flowchart TB` 或 `flowchart LR` | 概念、方案、协议对比 |
| `flowchart` | `flowchart TB` | 算法、状态流、处理步骤 |
| `sequence` | `sequenceDiagram` | 握手、调用链、交互时序 |
| `framework` | `mindmap` 或 `flowchart TB` | 知识框架、概念脉络 |
| `summary` | `flowchart TB` | 总结卡片、重点归纳 |
| `hierarchy` | `flowchart TB` | 分类与层级关系 |
| `tree` | `flowchart TB` | 树形数据结构 |
| `grid` | `block-beta` 或 `flowchart LR` | 数组、内存、网格 |
| `protocol` | `block-beta` 或 `flowchart LR` | 报文与协议字段 |
| `timeline` | `timeline` 或 `gantt` | 生命周期、调度时间线 |

## 排版规则

- 图中文字尽量使用中文；协议名、类名、代码标识等专有名词可保留英文。
- 对比图有 3 项时放在同一排；有 4 项时排成上二下二。可通过两个 `subgraph` 行容器组织。
- 流程图默认使用 `flowchart TB`，节点保持 2-8 个，分支边必须写清条件。
- 时序图使用 `sequenceDiagram`，参与者 2-5 个，禁止无意义自环。
- 单个节点建议不超过 30 个汉字；较长说明使用 `<br/>` 换行。
- 节点文字采用“短标题 + 一行关键说明”，避免把整段回答塞进一个节点。
- 主流程保持明显的阅读方向；辅助关系使用虚线或无箭头连线，避免线条交叉。
- 同一层级节点尽量长度相近，让 Mermaid 自动布局更均衡。
- 所有节点 ID 只使用 ASCII 字母与数字，显示文字放在引号中，例如 `N1["中文文字"]`。
- 不使用 `click` 指令、外部链接、图片或自定义脚本。
- 不要在 `mermaid_source` 中使用 Markdown 代码围栏。

## 示例

### 对比图

```text
flowchart TB
  subgraph R1[ ]
    direction LR
    A["TCP<br/>可靠、有序、面向连接"]
    B["UDP<br/>轻量、快速、无连接"]
  end
  A ~~~ B
```

### 流程图

```text
flowchart TB
  N1["客户端：发送 SYN"] --> N2["服务端：返回 SYN + ACK"]
  N2 --> N3["客户端：确认 ACK"]
```

### 时序图

```text
sequenceDiagram
  participant C as 客户端
  participant S as 服务端
  C->>S: 发送 SYN
  S-->>C: 返回 SYN + ACK
  C->>S: 确认 ACK
```

## 输出前自检

- JSON 是否合法，源码中的换行和双引号是否正确转义？
- `mermaid_source` 第一行是否是受支持的 Mermaid 图类型声明？
- 图解是否紧扣学生问题，所有文字是否清晰、简洁并尽量中文化？
- 对比、流程、时序的布局是否符合内容关系？
- `teaching_content` 是否包含核心解释、要点和总结？
