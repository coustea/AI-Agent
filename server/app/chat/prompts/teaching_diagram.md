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

- **默认只画 1 个连续的核心视觉**。能用一棵树、一条流程、一组对比或一个时序讲清时，不要创建额外 `subgraph`。
- 只有当两个关系类型无法在同一视觉中清楚表达时，才增加第 2 个视觉；“知识点很多”“想讲得全面”不是增加视觉组的理由。
- 先确定本轮唯一的学习重点，再围绕它保留 3-8 个核心节点。定义、性质、示例、误区等未被画出的知识继续完整写入 `teaching_content`，不要为了覆盖它们而增加图块。
- 不要把“性质列表、结构示例、插入流程、横向对比”同时塞进一张 PNG，也不要用多个 `subgraph` 充当文字章节容器。
- 图解必须有真实结构感：树、流程、对比、层级关系要用节点和连线表达；不要只输出“核心解释/关键要点”两个大文字框。
- 硬性禁止在 `mermaid_source` 中使用“核心解释”“关键要点”“核心要点”“必须掌握”作为大容器节点标题；这些文字属于 `teaching_content`，不属于图的主体。
- Mermaid 节点必须表达具体对象、步骤或关系，例如“根节点 13 黑”“叔叔节点为红”“左旋修复”“NIL 叶子”。不要输出“Key idea”“总结”“解释”这类抽象占位节点。
- 如果主题是树、图、链表、堆、红黑树等数据结构，默认只画 1 个结构实例。性质写入节点的短标签或 `teaching_content`，不要单独再画性质清单。
- 如果主题是红黑树，默认直接画 5-9 个树节点和必要的 NIL 叶子，用颜色/短标签体现规则；只有学生明确问“结构与调整如何对应”时，才增加第 2 个小流程。不要同时画性质、结构、插入流程和对比。
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
