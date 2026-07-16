# 本科计算机理论 PPT Visual IR 重构设计

**日期**：2026-07-16  
**状态**：已批准实施  
**范围**：`server/app/shared/ppt/` 及对应 PPT 测试  
**兼容策略**：破坏式替换，不保留旧视觉契约、转换器或缓存兼容

## 1. 目标

将 PPT 生成器从“通用教学论证图 + 指标卡”重构为面向本科计算机课程的可组合视觉模型系统。生成结果必须能直接表达树、图、状态机、进程时序、内存布局、数据通路、集合映射、矩阵、算法状态、数字电路和定量关系，而不是把“问题、前提、机制、结论”等讲课元数据伪装成领域模型。

系统不为每个知识点硬编码模板。新增知识点应组合已有模型；只有出现新的表达范式时才新增 Visual IR 类型和渲染器。

## 2. 已确认的问题

1. `VisualKind.MODEL` 只能表达通用 `nodes/edges`，且节点来自 `DeckLogicModel` 的教学论证角色，不是二叉树、PCB、TCP 状态、页表或 CPU 数据通路。
2. `VisualKind.METRICS` 把普通要点的 `label` 同时写入 `label` 和 `value`，普通文本被放大为 46px，并与左侧要点重复。
3. 整个问题句直接成为 52px 标题，长标题产生拥挤和不自然换行。
4. `lead + 4 points + visual + 本页结论 + 章节轨道` 同时出现，页面允许接近 500 字，信息密度失控。
5. “学习目标”“知识体系图谱”“课程总结”连续重复收束，教学节奏拖沓。
6. 英文枚举值被直接作为 eyebrow，内部协议泄漏到课件。
7. 单一通用图渲染器无法验证树根、状态初态、泳道归属、地址区间、矩阵尺寸或电路线网等领域不变量。

## 3. 总体架构

```text
ResourcePPT / PathPPT
  -> PPTContextAdapter
  -> DeckLogicDraft (LLM 只写课程语义)
  -> DeckLogicModel (后端分配章节和逻辑节点 ID)
  -> StoryboardCompiler (后端生成短标题、页序和内容预算)
  -> VisualPlanner (LLM 选择并填写受类型约束的领域模型)
  -> typed Visual IR validators
  -> ContentComposer (LLM 只写简短投影文案和讲稿)
  -> PPTDeck
  -> VisualRendererRegistry
  -> HTML/SVG/CSS
  -> structural QA + browser visual QA
```

`VisualPlanner` 与三个 `ContentComposer` 分段任务在故事板生成后并行执行，避免增加串行关键路径。模型输出只按页面顺序返回视觉模型，不生成页面 ID、节点 ID、SVG 坐标、颜色、CSS 或 HTML。

## 4. 课程语义层

### 4.1 课程画像

`CourseDomain` 使用以下闭集：

- `algorithms`
- `operating_systems`
- `networks`
- `computer_architecture`
- `databases`
- `compilers`
- `discrete_theory`
- `software_distributed`
- `general_cs`

`DeckLogicDraft` 由 LLM 选择一个主画像。画像只向视觉规划器提供推荐模型和术语约束，不禁止跨学科组合。

### 4.2 逻辑节点

每个 `LogicDraftNode` 新增 `title`，长度 2-24 字符。`question` 继续承载教学问题，但不再直接作为页面标题。后端分配 `lNN` ID；LLM 不生成任何内部 ID。

## 5. Visual IR 模型代数

### 5.1 叶子模型

| `kind` | 表达对象 | 关键不变量 |
|---|---|---|
| `hierarchy` | 树、目录、B/B+ 树、语法树、文件系统 | 恰好一个根；父引用有效；无环；全部可达 |
| `graph` | 网络拓扑、依赖图、资源分配图、控制流图 | 端点有效；无自环；有向性明确；边非空 |
| `state_machine` | 进程状态、协议状态、自动机、事务状态 | 恰好一个初态；至少一个终态；转换端点有效 |
| `timeline` | 时序图、泳道、Gantt、流水线、并发事件 | lane 引用有效；区间有序；消息端点有效 |
| `memory_layout` | 栈/堆、页表、缓存、记录布局、磁盘页 | 段顺序确定；尺寸为正；指针引用有效 |
| `data_flow` | CPU 数据通路、编译流水线、数据流图 | 块和端口引用有效；至少一条流；方向明确 |
| `mapping` | 集合、关系、函数、ER 映射、模式映射 | 集合和元素引用有效；函数模式下每个源至多一个像 |
| `table_matrix` | 矩阵、真值表、关系表、对比矩阵 | 行宽一致；表头与列数一致；高亮单元格有效 |
| `algorithm_frames` | 排序、查找、动态规划、图算法逐帧状态 | 至少两帧；每帧单元数受限；高亮索引有效 |
| `circuit` | 组合逻辑、时序逻辑、门电路、微体系结构连接 | 线网端点有效；输入输出存在；禁止自连接 |
| `quantitative` | 复杂度曲线、吞吐/延迟、概率、容量趋势 | 数值有限；序列点有效；轴和单位明确 |
| `code` | 可一次展示的完整教学代码 | 4-18 行；语言非空；不超过展示预算 |
| `formula` | 一个核心公式及必要推导 | 公式非空；最多 4 个步骤；变量说明受限 |

### 5.2 组合模型

`composite` 包含 2-3 个叶子模型面板，不允许递归嵌套。每个面板包含短标题和宽度权重。组合模型用于同一知识机制必须同时观察多个视角的场景，例如：

- 页面置换：`memory_layout + timeline + algorithm_frames`
- TCP 建连：`state_machine + timeline`
- B+ 树：`hierarchy + memory_layout`
- CPU 流水线：`data_flow + timeline`
- 进程调度：`state_machine + timeline`

组合不是装饰性拼贴。视觉规划器必须在 `purpose` 中说明各面板共同回答的问题；面板内容不得重复。

### 5.3 引用规则

LLM-facing 模型使用零基顺序引用，例如 `source_index`、`target_index`、`parent_index` 和 `lane_index`。后端验证后为 DOM/SVG 分配稳定 ID。这样保留此前“语义由模型负责、内部身份由后端负责”的边界。

## 6. 课程覆盖画像

| 课程 | 首选模型 | 代表验收组合 |
|---|---|---|
| 数据结构与算法 | hierarchy、graph、algorithm_frames、quantitative | 二叉搜索树插入；Dijkstra 逐帧；复杂度曲线 |
| 操作系统 | state_machine、timeline、memory_layout、graph | 进程状态与调度；分页置换；死锁资源图 |
| 计算机网络 | graph、timeline、state_machine、data_flow | TCP 握手；路由拓扑；协议栈数据流 |
| 组成原理 | data_flow、timeline、memory_layout、circuit | CPU 流水线；Cache 映射；ALU 门电路 |
| 数据库 | mapping、table_matrix、hierarchy、timeline | ER 映射；关系代数；B+ 树页布局；事务调度 |
| 编译原理 | hierarchy、state_machine、data_flow、table_matrix | AST；自动机；编译阶段；LR 分析表 |
| 离散数学/自动机 | mapping、graph、state_machine、table_matrix、formula | 集合映射；图论；DFA；真值表 |
| 软件工程/分布式 | graph、timeline、state_machine、data_flow | 组件依赖；一致性协议时序；服务状态与消息流 |

“完整覆盖”指这些基础表达范式可组合覆盖课程知识，而不是为每一个教材小节建立独立模板。

## 7. 故事板与信息密度

### 7.1 页面序列

标准序列改为：

1. 封面
2. 一页学习路线
3. 按逻辑节点连续展开的内容页
4. 一页课程总结

删除固定“本节学习目标”和固定“知识体系图谱”页面。只有课程语义确实需要时，内容页才可使用目标、地图或对比模型。总页数允许 7-18 页。

### 7.2 投影文字预算

- 内容页标题：最多 24 个字符；禁止使用完整问题句。
- `lead`：最多 72 个字符。
- `points`：最多 3 条；标签最多 12 个字符；说明最多 48 个字符。
- 可见页面不再显示固定“本页结论”页脚。
- 可见页面不再显示完整章节轨道；只显示当前章节短标签和页码。
- `detailed` 只增加讲稿深度，不增加可见信息单元或缩小字号。
- 视觉模型至少占内容舞台 58%；纯视觉页至少占 78%。

### 7.3 字号

标题字号由后端按字符长度分为固定档位，不随 viewport 连续缩放：

- 封面：64 / 56 / 48px
- 内容标题：46 / 40 / 34px
- 正文：22-26px
- 图形节点：16-20px
- 图注：15-17px

任何渲染器都不得通过把正文降到 18px 以下解决溢出。

## 8. 视觉规划器

`VisualPlanner` 接收：课程画像、页面标题、问题、主张、证据、教学输出和相邻页面摘要。它返回与内容页数量严格一致的 `VisualPlanDraft.models`。

规划规则：

1. 优先选择能表达知识对象本身的模型，不选择讲课论证关系。
2. 状态变化必须用 `state_machine` 或含它的组合；调用/通信顺序必须用 `timeline`；层级结构必须用 `hierarchy`；存储位置必须用 `memory_layout`。
3. 数字只有在可比较、带单位且支撑结论时才能使用 `quantitative`。
4. 连线是语义的一部分，关系模型不允许无边降级。
5. 无法构造合法领域模型时生成失败并报告页面序号与类型，不回退到通用卡片或空图。

## 9. 渲染架构

`VisualRendererRegistry` 以 `kind` 注册纯渲染函数。注册表必须与所有 Visual IR 叶子类型一一对应，启动时检查遗漏和重复。

`visual_renderers.py` 负责：

- 领域模型到 HTML/SVG 的确定性投影
- SVG 坐标和稳定 DOM ID
- 连接线、箭头、节点、泳道、地址、坐标轴和高亮
- 组合面板

`html.py` 只负责：

- 页面母版、封面、路线、总结
- 全局 CSS、键盘/触摸控制器和发布
- 调用渲染器注册表

渲染器不读取 `DeckLogicModel`，不推断教学语义，也不修复非法 Visual IR。

## 10. 校验与失败策略

校验分三层：

1. Pydantic 字段和长度约束。
2. 每类模型的结构不变量。
3. 页面预算校验：模型元素数量、组合面板数量、可见文字总量。

任意层失败都抛出 `PPTGenerationError("planning_visuals", ...)`，包含页面序号和模型类型。禁止：

- 生成空白视觉
- 自动改为旧 `MODEL` 或 `METRICS`
- 吞掉非法边或非法引用
- 在渲染阶段临时补节点、补边或缩小字号

## 11. 删除与迁移

直接删除：

- `VisualKind.MODEL`
- `VisualKind.METRICS`
- `VisualMetric`
- `DiagramNode` / `DiagramEdge` / `DiagramModel`
- `VisualSpec`
- `_materialize_metrics()`
- `_materialize_model()`
- 通用 `_diagram_positions()` / `_render_model()`
- 根据 `LogicNodeRole` 硬编码视觉类型的 `_slide_intent()`
- 重复章节轨道和固定“本页结论”渲染
- 提示词中“后端从逻辑链生成知识图/指标卡”的旧规则

不提供别名、兼容 validator、旧 JSON 转换或双渲染路径。

## 12. 测试与验收

### 12.1 自动化测试

1. 13 个叶子模型分别有合法 fixture 和至少一个非法 fixture。
2. 8 个课程画像各有一个代表模型；主要课程各有一个组合模型。
3. 注册表覆盖所有叶子模型，且旧 `model/metrics` 字符串不在活动契约中。
4. 故事板只有一个路线页和一个总结页，不生成固定目标页/知识图谱页。
5. 长问题不会成为标题；可见文字预算超限会在渲染前失败。
6. 每个关系模型的 HTML/SVG 都包含真实连接线或映射线。
7. fake LLM 全链路测试验证：逻辑草稿、视觉规划、三段内容并行合并、HTML 发布。

### 12.2 浏览器 QA

对至少以下 8 张代表页在 1920x1080、1440x900 和 390x844 viewport 检查缩放后的完整画面：

- 二叉树
- 进程状态 + Gantt
- TCP 握手
- CPU 流水线
- B+ 树页布局
- AST + 编译数据流
- DFA + 真值表
- 分布式一致性时序

验收指标：无溢出、无重叠、无被裁剪文本、画布非空、连接线可见、最长词不越界、标题不超过两行、内容页无重复大段文字。

## 13. 完成标准

1. 所有旧 `MODEL/METRICS` 代码和兼容路径被删除。
2. 13 个叶子模型与 `composite` 均可通过统一注册表渲染。
3. 八类本科课程画像均有自动化验收 fixture。
4. 聚焦 PPT 测试通过，Python 模块可编译。
5. 代表课件通过浏览器结构和像素 QA。
6. 生成结果只显示中文教学标签，不泄漏内部英文枚举。
7. 新代码遵循 Google Python Style：职责单一、类型完整、公共接口有 Google 风格 docstring，不保留无引用代码。
