# 计算机理论教学 PPT 模板引擎重构设计

## 1. 背景

当前 PPT 引擎以固定槽位和少量双栏、三栏布局为主。主题主要改变颜色，页面普遍使用白色圆角卡片、固定页眉、分隔线和页脚，因此生成结果更接近 Web Dashboard，而不是人工设计的教学课件。

现有后端合同、Prompt、Manifest、前端类型和导出逻辑还存在角色定义、页面顺序和坐标转换不一致的问题。预览与导出分别实现布局，也会造成视觉差异和元素重叠。

本次重构不兼容旧 PPT 数据，不保留旧协议适配层。目标是建立一套面向计算机理论知识讲解的全新生成系统。

## 2. 设计目标

### 2.1 核心目标

- 视觉效果优先于 PPT 元素可编辑性。
- 前端预览与 PPTX 导出保持高度一致。
- 重点支持数据结构、操作系统、计算机网络、计算机组成原理和通用计算机理论。
- 将抽象概念、结构关系、运行过程和因果关系转换为教学图解。
- 自动选择主题与构图，并控制整套课件的视觉节奏。
- 内容过多时拆页，不通过无限缩小字号塞入单页。

### 2.2 非目标

- 不兼容历史 PPT 协议和已保存的旧 PPT 数据。
- 不把代码演示作为首批核心版式。
- 不追求首版导出内容的元素级可编辑性。
- 不让大模型直接生成元素坐标。
- 不合并 `resource` 与 `path` 的记录、详情页或持久化模型。

## 3. 总体架构

系统采用四层模板结构：

```text
Theme
  └── Master
       └── Composition
            └── Block
```

- `Theme`：定义字体、颜色、间距、图表配色、背景、线条、阴影、圆角和图片处理方式。
- `Master`：定义封面、章节、正文、总结和结束页的页面级骨架。
- `Composition`：定义一页内容的视觉构图。
- `Block`：定义文本、图片、公式、表格、图解等基础视觉元素。

完整数据流：

```text
后端 PPT 内容策划
  → SlideIntent
  → LayoutDecisionEngine
  → ResolvedSlide
  → Web Slide Renderer
  ├─ 前端预览
  └─ 高清整页快照 → PPTX
```

后端只表达教学语义和内容关系。前端负责主题选择、构图选择、排版、溢出检测和最终渲染。预览和导出共用同一个 Web 渲染结果。

## 4. 后端内容协议

### 4.1 SlideIntent

```ts
interface SlideIntent {
  id: string
  role:
    | 'cover'
    | 'section'
    | 'definition'
    | 'concept_breakdown'
    | 'hierarchy'
    | 'architecture'
    | 'state_transition'
    | 'sequence'
    | 'data_flow'
    | 'comparison'
    | 'derivation'
    | 'worked_example'
    | 'knowledge_map'
    | 'summary'
    | 'ending'
  title: string
  key_message: string
  elements: ContentElement[]
  relations?: Relation[]
  density: 'light' | 'medium' | 'dense'
  visual_hints?: {
    preferred_visual?: string
    emphasis?: string[]
    avoid?: string[]
    image_query?: string
  }
}
```

### 4.2 内容元素

`ContentElement` 支持：

- concept
- definition
- statement
- step
- entity
- metric
- hierarchy_node
- state_node
- sequence_participant
- process_node
- formula
- image
- icon
- table
- quote
- code

`code` 是辅助元素，不决定页面必须使用代码版式。

### 4.3 内容关系

`Relation` 支持：

- parent_child
- dependency
- transition
- sequence
- data_flow
- comparison
- cause_effect
- association

后端不得输出 `layout`、`slot`、`x`、`y`、`width` 或 `height`。后端应控制每页信息量，并在内容过多时主动拆页。

### 4.4 后端修改范围

统一重写以下内容：

- `server/app/resource/ppt_contract.py`
- `server/app/resource/prompts/ppt_director.md`
- `server/app/resource/templates/ppt_manifest.json`
- `server/app/resource/agents/ppt.py`
- `src/features/resource/components/ppt-engine/schema-guide.md`

合同、Prompt、Manifest 和前端类型必须使用同一组角色、元素与关系定义。`summary` 与 `ending` 位于整套 PPT 末尾，不再保留互相冲突的旧校验。

## 5. 主题系统

首批提供三套主题，并由内容自动选择。

### 5.1 technical-blueprint

适用于操作系统、计算机网络和计算机组成原理。采用蓝灰或深色背景、细网格、清晰连接线和较强结构感。

### 5.2 editorial-academic

适用于概念、定义和理论推导。强调留白、编辑式排版、弱装饰与清晰的文字层级。

### 5.3 modern-classroom

适用于通用教学、例题和总结。风格明快但克制，突出步骤、提示和记忆框架。

主题必须完整定义字体体系、字号比例、页面边距、内容网格、背景、图片处理、图表颜色、线条、箭头、阴影和圆角，不能只替换颜色变量。

## 6. Master 与核心构图

### 6.1 Master

- CoverMaster
- SectionMaster
- ContentMaster
- SummaryMaster
- EndingMaster

页眉、页脚、页码和背景由 Master 控制，并允许不同 Master 完全不显示这些元素。不得继续在播放器顶层强制绘制统一页眉、虚线和底部总结。

### 6.2 首批 Composition

1. TheoryCover
2. SectionBreak
3. DefinitionFocus
4. ConceptBreakdown
5. HierarchyMap
6. ComponentArchitecture
7. StateTransition
8. SequenceTimeline
9. DataFlow
10. ProtocolStack
11. AlgorithmProcess
12. Comparison
13. CauseEffect
14. WorkedExample
15. KnowledgeMap
16. ChapterSummary

### 6.3 学科偏好

- 数据结构：结构变化、操作过程、复杂度比较、层级关系。
- 操作系统：进程状态、调度时序、内存层级、系统调用路径。
- 计算机网络：协议栈、封装过程、报文流、通信时序。
- 计算机组成原理：部件关系、数据通路、流水线、存储层次。

## 7. Block 系统

首批 Block：

- Text
- Definition
- KeyStatement
- BigNumber
- Image
- Icon
- Formula
- Table
- HierarchyDiagram
- StateDiagram
- SequenceDiagram
- DataFlowDiagram
- ProtocolStack
- Comparison
- Timeline
- KnowledgeMap
- CodeSnippet

Block 不默认带白色背景、边框、阴影和圆角。是否形成卡片由 Composition 和 Theme 决定。

图解必须支持分支、汇合、循环、双向关系、层级、状态转换、时序和数据流。现有只能线性排列胶囊节点的图解实现不再作为主实现。

## 8. 自动选版与课件节奏

`LayoutDecisionEngine` 执行以下步骤：

1. 根据 `role` 获取候选 Composition。
2. 根据元素数量、文字长度和关系类型评分。
3. 根据学科特征调整候选权重。
4. 根据 `density` 排除无法承载内容的构图。
5. 排除与前一页重复的构图。
6. 结合整套课件节奏确定最终构图。
7. 生成包含确定坐标的 `ResolvedSlide`。
8. 执行溢出检测，必要时要求拆页。

整套课件遵循以下规则：

- 不连续使用相同 Composition。
- 每 3 至 4 页至少安排一页视觉重点页。
- 高密度页后优先安排低密度页。
- 封面、章节、总结和结束页使用不同 Master。
- 单页只表达一个主要结论。
- 正文字号不得因内容过多而无限缩小。

## 9. 素材策略

素材优先级：

1. 本地精选素材库。
2. 联网检索并下载的图片。
3. 本地图标、几何插图和程序化图解兜底。

联网素材必须先下载到服务端本地缓存，再交给前端使用。缓存记录来源 URL、作者、授权信息和查询关键词。前端不得直接依赖临时远程 URL。

素材检索失败不会终止 PPT 生成。没有可靠图片时，应优先使用结构图、流程图或几何插图，而不是显示空白占位符。

## 10. 渲染与导出

`Web Slide Renderer` 是唯一视觉渲染来源：

```text
ResolvedSlide → DOM/CSS → 预览与高清快照
```

PPTX 首版采用整页视觉保真导出：

- 等待字体、图片、公式和图表加载完成。
- 以 2 倍或 3 倍分辨率生成整页快照。
- 将快照作为整页图片写入 PPTX。
- 保持 16:9 页面比例和清晰度。
- 导出失败时返回具体页码、失败资源和失败阶段。

首版不维护第二套 PPT 原生坐标转换器。标题、正文、页码等元素的可编辑层属于后续增强，不阻塞本次重构。

## 11. 前端目录建议

```text
ppt-engine/
  model/
    slideIntent.ts
    resolvedSlide.ts
    theme.ts
    composition.ts
  themes/
    technicalBlueprint.ts
    editorialAcademic.ts
    modernClassroom.ts
  masters/
    CoverMaster.vue
    SectionMaster.vue
    ContentMaster.vue
    SummaryMaster.vue
    EndingMaster.vue
  compositions/
    ...
  blocks/
    ...
  engine/
    layoutDecisionEngine.ts
    densityAnalyzer.ts
    overflowDetector.ts
    deckRhythmPlanner.ts
    slideResolver.ts
  export/
    slideCapture.ts
    pptExporter.ts
```

目录表示职责边界，不要求一次创建所有空文件。只在对应能力落地时新增文件。

## 12. 错误处理

- 后端协议校验失败：返回具体页码、字段和违反的规则。
- 选版失败：回退到与 `role` 匹配的通用正文构图。
- 内容溢出：标记页面需要拆分，不进行无下限缩放。
- 素材失败：回退到图标或程序化图解。
- 字体失败：使用主题定义的本地安全字体。
- 单页快照失败：记录失败页并终止导出，避免生成表面成功但缺页的文件。

## 13. 分阶段实施

### 阶段一：协议重构

- 重写后端合同、Prompt 和 Manifest。
- 更新前端类型与 schema-guide。
- 删除旧角色、布局和冲突校验。
- 使用最小样例验证后端到前端的数据闭环。

### 阶段二：渲染基础

- 建立 Theme、Master、Composition 和 Block 基础接口。
- 建立 ResolvedSlide。
- 实现统一 Web Slide Renderer。
- 完成三个主题的基础 Token 与五类 Master。

### 阶段三：理论知识构图

- 完成 16 种核心 Composition。
- 优先实现状态图、时序图、层级图、协议栈和数据流图。
- 实现自动选版、密度检测和整套节奏控制。

### 阶段四：导出与素材

- 实现高清整页快照导出。
- 建立本地素材库和服务端缓存。
- 接入联网素材检索、下载和来源记录。

### 阶段五：质量控制

- 增加溢出、重复构图、字体下限、对比度和素材加载检查。
- 使用四个典型学科主题进行视觉回归验证。
- 删除确认无引用的旧 PPT 引擎实现。

## 14. 测试与验收

### 14.1 代表性样例

- TCP 三次握手生成通信时序图。
- 进程五状态模型生成状态转换图。
- OSI 与 TCP/IP 模型生成协议栈和对比图。
- 存储体系生成层级结构图。
- CPU 数据通路生成部件结构与数据流图。
- 二叉树操作生成结构变化过程图。

### 14.2 验收标准

- 不连续出现相同构图。
- 不再统一使用白色圆角卡片页面。
- 理论知识优先通过关系图和过程图表达。
- 预览与 PPTX 导出的视觉基本一致。
- 1920×1080 预览无明显遮挡和溢出。
- 正文字号保持可读，不因信息过多无限缩小。
- 外部素材失败时仍能完成生成。
- `npm run build` 通过。
- 后端 PPT 相关测试通过；项目文档列出的既有失败不纳入本次修复范围。

## 15. 实施约束

- 当前工作区存在未提交修改，实施时不得覆盖无关变更。
- 不合并 `resource` 与 `path` 的记录、详情页或持久化模型。
- 不添加旧 PPT 协议兼容代码。
- 先建立新版最小闭环，再删除确认无引用的旧实现。
- 每个阶段独立验证，避免一次性重写后难以定位问题。
