# Resource 与 Learning Path 前端重构设计

日期：2026-07-04  
状态：待确认

## 1. 背景

`src/features/resource` 与 `src/features/learning-path` 当前共有约 1.9 万行 Vue/TypeScript。
主要问题不是文件数量，而是职责和归属不清：

- `ResourceGenerating.vue`、`LearningPathOverview.vue`、`LearningPathNode.vue` 等页面同时承担请求、实时事件、状态推导、交互和视觉实现。
- 通用内容渲染器位于 `resource/components`，导致 `learning-path` 反向依赖独立资源业务。
- `resource/api/resource-history.ts` 同时导出路径资源类型，两个领域的数据接口发生交叉。
- `views`、`components`、`model` 只表达技术类型，不能说明用户流程。
- `*View.vue`、`ResourceGeneratorConstants.ts` 等名称含糊或过长。
- 个性化设置页使用自制模拟预览，与最终资源卡片的结构不同。
- 页面级 CSS 和巨型 scoped style 让视觉修改缺少 locality。

## 2. 目标

1. 以用户流程组织目录，文件名短且能结合目录直接理解。
2. 路由页面只负责装配和路由参数，不直接实现完整业务流程。
3. 将请求、实时事件和流程状态放进领域内 composable。
4. 将可复用视觉区域拆成职责明确的 Vue 模块。
5. 把无业务归属的学习内容渲染能力迁到共享深模块。
6. 保持 `resource` 与 `learning-path` 的请求、事件、记录、详情和持久化模型独立。
7. 个性化设置和最终结果使用同一个资源摘要卡片。
8. 保留现有 URL，直接更新内部引用，不保留旧文件或兼容转发。

## 3. 非目标

- 不修改后端接口、数据库和持久化模型。
- 不合并资源生成与路径规划的实时事件。
- 不统一两种资源记录或详情数据结构。
- 不修改现有 URL。
- 不引入 repository、port 或 adapter 等只有单一实现的空壳层。
- 不在本次建立新的前端测试框架。
- 不实施尚处于独立设计阶段的统一 Markdown Worker。

## 4. 命名规则

- 目录表达上下文，文件名不重复目录语义。
- 路由入口使用简短的 `*Page.vue`。
- Vue 展示模块使用名词，如 `Card.vue`、`Roadmap.vue`。
- composable 使用动词语义，如 `useGeneration.ts`、`useWorkspace.ts`。
- 不使用 `View`、`Wrapper`、`Manager`、`Helper` 等含糊后缀。
- 仅在脱离目录后会产生歧义时保留领域词。

例如使用 `resource/generation/Settings.vue`，不使用
`ResourceGenerationPersonalizationSettingsView.vue`。

## 5. 目标结构

```text
src/features/resource/
├─ pages/
│  ├─ GeneratePage.vue
│  ├─ LibraryPage.vue
│  └─ DetailPage.vue
├─ generation/
│  ├─ Prompt.vue
│  ├─ Settings.vue
│  ├─ Progress.vue
│  ├─ useGeneration.ts
│  ├─ useEvents.ts
│  ├─ catalog.ts
│  ├─ settings/
│  │  ├─ Scenario.vue
│  │  ├─ AgentTabs.vue
│  │  ├─ Content.vue
│  │  ├─ MindMap.vue
│  │  ├─ Code.vue
│  │  ├─ Quiz.vue
│  │  ├─ Reading.vue
│  │  ├─ Slides.vue
│  │  └─ Video.vue
│  └─ progress/
│     ├─ Summary.vue
│     ├─ Flow.vue
│     ├─ AgentCard.vue
│     ├─ AgentDetail.vue
│     ├─ Logs.vue
│     └─ Outputs.vue
├─ library/
│  ├─ Gallery.vue
│  └─ Card.vue
├─ api/
│  ├─ generation.ts
│  └─ library.ts
└─ model/
   ├─ types.ts
   └─ events.ts
```

```text
src/features/learning-path/
├─ pages/
│  ├─ CreatePage.vue
│  ├─ OverviewPage.vue
│  ├─ NodePage.vue
│  ├─ HistoryPage.vue
│  ├─ ResourceListPage.vue
│  └─ ResourcePage.vue
├─ planner/
│  ├─ GoalForm.vue
│  ├─ usePlanner.ts
│  └─ useEvents.ts
├─ workspace/
│  ├─ Roadmap.vue
│  ├─ NodePanel.vue
│  ├─ Summary.vue
│  ├─ Evaluation.vue
│  └─ useWorkspace.ts
├─ study/
│  ├─ Tutorial.vue
│  ├─ Toc.vue
│  ├─ Quiz.vue
│  ├─ Resources.vue
│  └─ useStudy.ts
├─ api/
│  ├─ path.ts
│  └─ resources.ts
└─ model/
   ├─ types.ts
   └─ events.ts
```

```text
src/shared/content/
├─ PreviewDialog.vue
├─ Frame.vue
├─ artifact.ts
└─ renderers/
   ├─ Article.vue
   ├─ MindMap.vue
   ├─ CodeLab.vue
   ├─ Quiz.vue
   ├─ Reading.vue
   ├─ Slides.vue
   └─ Video.vue
```

学校搜索不属于资源生成，迁移为：

```text
src/shared/school/
├─ api.ts
└─ types.ts
```

## 6. 模块设计

### 6.1 Resource generation

`GeneratePage.vue` 是生成流程的装配页面。它只负责：

- 装配 `Prompt`、`Settings`、`Progress`、`Gallery` 和 `PreviewDialog`；
- 把路由恢复参数交给 `useGeneration()`；
- 根据 composable 暴露的阶段选择当前页面区域；
- 转发用户动作。

`useGeneration()` 是生成流程的深模块。其 interface 包含：

- 当前阶段、输入、场景、启用 Agent 和配置；
- DAG 节点、总体进度、已生成资源和最终资源包；
- `submitPrompt()`、`start()`、`restore()`、`reset()`；
- `pause()`、`resume()` 和 `dispose()` 生命周期操作；
- 可展示错误与警告。

轮询、SSE、恢复、事件归并、终态获取和清理全部留在该 implementation 内。
页面不再认识 interval、EventSource、run ID 或事件归并顺序。

`useEvents()` 继续是 Resource 专属事件 adapter，不与 Path 共享。

### 6.2 Resource settings

`Settings.vue` 负责设置页布局和 v-model 协议。每种 Agent 表单进入
`settings/` 中对应模块，接收该 Agent 的配置并发出更新。

设置页调整为克制的产品配置界面：

- 移除大型营销式标题和过重场景卡片；
- 场景选择和 Agent 切换改为紧凑控件；
- 左侧编辑当前 Agent 参数；
- 右侧展示当前 Agent 的 `library/Card.vue`；
- 卡片 DOM、封面、标题、摘要、标签、状态和底部动作与最终 Gallery 完全一致；
- 设置态只改变数据和状态文案，不建立假的文档、代码编辑器或幻灯片截图。

因此 `library/Card.vue` 是摘要卡片模块，而 `shared/content/renderers/*` 是打开后的完整内容模块，
二者职责不重叠。

### 6.3 Resource progress

`Progress.vue` 只组合运行摘要、工作流、详情、日志和产物区域。原来的计算按职责归位：

- `Summary`：总体进度、运行数、已交付数、最新消息和错误。
- `Flow`：真实 DAG 布局、连接关系和节点选择。
- `AgentCard`：单个节点的状态、进度和摘要。
- `AgentDetail`：输入、输出、metrics、耗时和最近事件。
- `Logs`：后端事件日志。
- `Outputs`：已生成产物入口。

工作流拓扑和状态语义继续遵守既有
`resource-generating-workflow-design.md`，本次只改变代码 locality，不改变后端协议。

### 6.4 Learning Path planner and workspace

`CreatePage.vue` 装配 `GoalForm`。`usePlanner()` 处理输入、提交与跳转数据，不保留模拟业务状态。

`OverviewPage.vue` 装配 `Roadmap`、`NodePanel`、`Summary` 和 `Evaluation`。
`useWorkspace()` 集中处理：

- 路径加载与生成恢复；
- 节点状态、阶段分组和摘要推导；
- 节点选择、进入学习和主教程生成；
- Path 专属实时事件订阅；
- 页面卸载和 keep-alive 恢复。

`NodePage.vue` 装配教程、目录、测验和资源入口。
`useStudy()` 集中处理学习空间加载、教程生成、测验提交、学习跟踪和节点跳转。

### 6.5 Shared content

`shared/content` 是 Resource 与 Path 唯一共享的内容展示深模块。它的 interface 是标准化的
learning artifact，不包含资源记录 ID、路径节点 ID、请求方法或持久化信息。

- `PreviewDialog`：按 artifact 类型选择 renderer。
- `Frame`：统一标题、状态、内容表面和空态。
- `artifact.ts`：定义输入类型并执行安全归一化。
- `renderers/*`：只展示内容，不发起 Resource 或 Path 请求。

未来统一 Markdown 渲染器完成后，`Article.vue` 和其他需要 Markdown 的 renderer 只消费那个
公共入口，不自行实现新的解析器。本次不复制或扩展 Markdown 解析逻辑。

## 7. 数据隔离

```text
resource api ──> resource model ──> useGeneration ──> resource pages
                                      │
                                      └──> shared/content（仅展示 artifact）

path api ─────> path model ─────> useWorkspace/useStudy ──> path pages
                                      │
                                      └──> shared/content（仅展示 artifact）
```

明确禁止：

- `resource/api` 导入 `learning-path/model`；
- `learning-path/api` 导入 `resource/api` 的记录类型；
- shared content 导入任一领域的 API、route 或记录模型；
- Resource 与 Path 共用事件类型或事件 composable。

路径资源列表类型迁回 `learning-path/model/types.ts`，不再由
`resource/api/library.ts` 导出。

## 8. 路由策略

现有 URL 全部保持：

- `/resource-generator`
- `/resource-detail/:id`
- `/resource-history`
- `/path-planner`
- `/path-planner/overview/:id?`
- `/path-planner/node/:nodeId`
- `/path-planner/history`
- `/path-resource-history`
- `/path-resource/:id`

路由 import 更新到 `pages/`。内部 route name 和 Vue `defineOptions` 统一为简明名称，并同步更新
`MainLayout` keep-alive、profile 导航和 learning tracker。不会保留旧 Vue 文件作为转发层。

## 9. 错误与生命周期

- Resource SSE 断开：停止实时动画并调用 Resource 状态接口恢复，不推断失败原因。
- Path SSE 断开：调用 Path 详情接口恢复，不读取 Resource 状态。
- 详情或列表请求失败：由所属页面显示明确错误和重试入口。
- PPT 模板列表失败：仅退化为“自动推荐”，不阻断其他资源设置。
- artifact 不完整：共享 renderer 显示安全空态，不伪造内容。
- 未知 artifact 类型：显示“不支持的内容类型”，不落入错误 renderer。
- route 参数非法：页面停止请求并提供返回入口。
- `keep-alive` 停用：暂停轮询和事件连接；重新激活后按业务状态恢复。
- 卸载：清理计时器、SSE、ResizeObserver、窗口监听和延迟任务。

## 10. 迁移与删除

主要直接迁移：

| 当前文件 | 目标文件 |
|---|---|
| `views/ResourceGenerator.vue` | `pages/GeneratePage.vue` |
| `views/ResourceInput.vue` | `generation/Prompt.vue` |
| `views/ResourcePersonalize.vue` | `generation/Settings.vue` + `generation/settings/*` |
| `views/ResourceGenerating.vue` | `generation/Progress.vue` + `generation/progress/*` |
| `views/ResourceHistory.vue` | `pages/LibraryPage.vue` |
| `views/ResourceDetail.vue` | `pages/DetailPage.vue` |
| `components/ResourceBundleView.vue` | `library/Gallery.vue` + `library/Card.vue` |
| `components/ResourcePreviewDialog.vue` | `shared/content/PreviewDialog.vue` |
| `components/ResourceCardWrapper.vue` | `shared/content/Frame.vue` |
| `components/*View.vue` | `shared/content/renderers/*` |
| `components/resourceViewUtils.ts` | `shared/content/artifact.ts` |
| `model/ResourceGeneratorConstants.ts` | `generation/catalog.ts` |
| `model/resource.ts` | `model/types.ts` |
| `api/resource.ts` | `api/generation.ts` |
| `api/resource-history.ts` | `api/library.ts` |
| `views/LearningPathEntry.vue` | `pages/CreatePage.vue` |
| `views/LearningPathOverview.vue` | `pages/OverviewPage.vue` + `workspace/*` |
| `views/LearningPathNode.vue` | `pages/NodePage.vue` + `study/*` |
| `views/LearningPathHistory.vue` | `pages/HistoryPage.vue` |
| `views/PathResourceHistory.vue` | `pages/ResourceListPage.vue` |
| `views/PathResourceDetail.vue` | `pages/ResourcePage.vue` |
| `components/EvaluationBanner.vue` | `workspace/Evaluation.vue` |
| `model/path.ts` | `model/types.ts` |
| `api/path-resource.ts` | `api/resources.ts` |

迁移完成后删除：

- 两个旧 `views/` 目录；
- Resource 旧 `components/` 和 `model` 中已被迁移的文件；
- `resource-generator.css`；
- 两个 `.DS_Store`；
- 所有旧路径兼容文件和无调用模块。

保留并迁移用户当前对 `ResourcePersonalize.vue` 和
`ResourceGeneratorConstants.ts` 的未提交业务修改，不用 Git 版本覆盖。

## 11. 验证策略

前端当前没有测试基础设施，本次不额外引入。验证分四层：

1. `npm run build`：TypeScript、Vue SFC 与生产构建。
2. `git diff --check`：空白和冲突标记。
3. 静态边界检查：
   - 不存在 `features/resource/views` 或 `features/learning-path/views` import；
   - learning-path 不再导入 resource 的 API、model 或业务 Vue；
   - shared content 不导入 Resource/Path API；
   - 不存在旧文件名和兼容转发。
4. 浏览器回归：
   - Resource 输入、设置、生成中、结果、详情、历史；
   - 设置预览卡与最终 Gallery 卡片结构一致；
   - Path 创建、生成恢复、总览、节点学习、测验、资源列表与详情；
   - Resource/Path 内容都能打开共享 renderer；
   - 375、768、1024、1440px 无横向溢出；
   - 键盘焦点、错误态、空态和 reduced motion 可用。

## 12. 验收标准

1. URL 不变，所有路由可达。
2. 路由页面只承担装配和路由交互。
3. Resource 与 Path 不再互相导入 API、记录类型或业务页面。
4. 两个领域只通过 `shared/content` 复用内容展示。
5. Resource 设置预览与最终结果复用同一个 `library/Card.vue`。
6. 不再存在假的 Agent 内容截图式预览。
7. 超大 Vue 文件被拆成按场景聚合的短模块，且没有纯转发浅模块。
8. 旧目录、旧命名、`.DS_Store` 和兼容文件全部删除。
9. 用户未提交的设置与 Agent 配置修改被完整保留。
10. 构建、静态边界检查、diff 检查和浏览器回归全部通过。
