# Resource 与 Learning Path 前端重构设计

日期：2026-07-04  
状态：已确认

## 1. 背景

`src/features/resource` 与 `src/features/learning-path` 当前共有约 1.9 万行
Vue/TypeScript。主要问题不是目录层级不足，而是现有 Module 的职责和归属不清：

- `ResourceGenerating.vue`、`LearningPathOverview.vue`、`LearningPathNode.vue`
  同时承担请求、实时事件、状态推导、交互和视觉实现。
- 通用内容渲染器位于 `resource/components`，导致 `learning-path`
  反向依赖独立资源业务。
- `resource/api/resource-history.ts` 导出路径资源类型，两个领域的数据 Interface
  发生交叉。
- `ResourceGeneratorConstants.ts` 同时承载 Agent 元数据、标签、场景和请求构造，
  Implementation 缺乏 Locality。
- 个性化设置页使用自制模拟预览，与最终资源卡片的结构不同。
- 页面级 CSS 和巨型 scoped style 让视觉修改散落在多个调用方。

项目其他 Feature 已形成稳定骨架：

```text
feature/
├─ api/
├─ components/
├─ composables/  # 仅复杂流程需要
├─ model/
└─ views/
```

本次沿用该骨架，只在 `components` 内按页面场景分组。不会引入一套仅供
Resource 与 Learning Path 使用的 `pages / generation / library / workspace`
平行架构。

## 2. 目标

1. 保持项目现有 `api / components / composables / model / views` 结构。
2. `views` 保持为路由页面，复杂视觉区域进入 `components`。
3. 请求、实时事件和跨区域流程状态进入领域内 composable。
4. 目录提供上下文，文件名保持简短。
5. 把无业务归属的学习内容渲染能力迁到共享深 Module。
6. 保持 Resource 与 Learning Path 的请求、事件、记录、详情和持久化模型独立。
7. 个性化设置和最终结果使用同一个资源摘要卡片。
8. 保留现有 URL 与路由名称，直接更新内部引用，不保留兼容转发文件。

## 3. 非目标

- 不修改后端 Interface、数据库和持久化模型。
- 不合并 Resource 与 Learning Path 的记录、详情或实时事件。
- 不重构其他 Feature 的大页面。
- 不引入只有一个 Adapter 的 repository、port 或 adapter 空壳层。
- 不为了文件变短而拆出纯转发的浅 Module。
- 不在本次建立新的前端测试框架。
- 不实施尚处于独立设计阶段的统一 Markdown Worker。

## 4. 结构与命名原则

- 顶层目录遵守项目现有约定，不把 `views` 改名为 `pages`。
- 路由页面保留现有业务名称，例如 `ResourceGenerator.vue`。
- 子目录表达场景，文件名不重复目录语义，例如
  `components/generator/Settings.vue`。
- Vue Module 使用清晰名词，如 `Card.vue`、`Roadmap.vue`、`Progress.vue`。
- composable 使用 `useXxx.ts`，只隐藏确实复杂的流程 Implementation。
- Model 文件沿用项目的领域命名方式，如 `resource.ts`、`resourceEvent.ts`。
- 删除 `View`、`Wrapper`、`Manager`、`Helper` 等不能增加语义的后缀。
- 每次抽取都执行删除测试：删除后若复杂度会扩散回多个调用方，Module 才有足够
  Depth；否则保留在调用方。

## 5. 目标结构

### 5.1 Resource

```text
src/features/resource/
├─ api/
│  ├─ resource.ts
│  └─ history.ts
├─ components/
│  ├─ generator/
│  │  ├─ Input.vue
│  │  ├─ Settings.vue
│  │  └─ Progress.vue
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
│  ├─ progress/
│  │  ├─ Summary.vue
│  │  ├─ Flow.vue
│  │  ├─ Agent.vue
│  │  ├─ Detail.vue
│  │  ├─ Logs.vue
│  │  └─ Outputs.vue
│  └─ result/
│     ├─ Bundle.vue
│     └─ Card.vue
├─ composables/
│  ├─ useGeneration.ts
│  └─ useResourceEvents.ts
├─ model/
│  ├─ resource.ts
│  ├─ resourceEvent.ts
│  └─ catalog.ts
└─ views/
   ├─ ResourceGenerator.vue
   ├─ ResourceHistory.vue
   └─ ResourceDetail.vue
```

`settings` 与 `progress` 中的文件是预期分解方向，不要求机械地全部创建。只有具备
独立交互、状态协议或可验证视觉职责的 Module 才会落成文件。

### 5.2 Learning Path

```text
src/features/learning-path/
├─ api/
│  ├─ path.ts
│  └─ resource.ts
├─ components/
│  ├─ entry/
│  │  └─ Form.vue
│  ├─ overview/
│  │  ├─ Roadmap.vue
│  │  ├─ NodePanel.vue
│  │  ├─ Summary.vue
│  │  └─ Evaluation.vue
│  └─ node/
│     ├─ Tutorial.vue
│     ├─ Toc.vue
│     ├─ Quiz.vue
│     └─ Resources.vue
├─ composables/
│  ├─ usePlanner.ts
│  ├─ useWorkspace.ts
│  ├─ useStudy.ts
│  └─ usePathEvents.ts
├─ model/
│  ├─ path.ts
│  └─ pathEvent.ts
└─ views/
   ├─ LearningPathEntry.vue
   ├─ LearningPathOverview.vue
   ├─ LearningPathNode.vue
   ├─ LearningPathHistory.vue
   ├─ PathResourceHistory.vue
   └─ PathResourceDetail.vue
```

### 5.3 Shared content

```text
src/shared/content/
├─ PreviewDialog.vue
├─ Frame.vue
├─ artifact.ts
└─ renderers/
   ├─ Article.vue
   ├─ MindMap.vue
   ├─ Code.vue
   ├─ Quiz.vue
   ├─ Reading.vue
   ├─ Slides.vue
   └─ Video.vue
```

学校搜索实际只由注册资料和个人资料使用，迁到现有 Profile 领域：

```text
src/features/profile/
├─ api/
│  ├─ profile.ts
│  └─ school.ts
└─ model/
   ├─ profile.ts
   └─ school.ts
```

## 6. Module 设计

### 6.1 Resource 生成流程

`views/ResourceGenerator.vue` 是路由装配页面，负责：

- 装配 `Input`、`Settings`、`Progress`、`Bundle` 和 `PreviewDialog`；
- 接收路由恢复参数；
- 根据 `useGeneration()` 暴露的阶段切换当前区域；
- 转发用户动作。

`useGeneration()` 是生成流程的深 Module。其 Interface 包含：

- 当前阶段、输入、场景、启用 Agent 和配置；
- DAG 节点、总体进度、已生成资源和最终资源包；
- `submitInput()`、`start()`、`restore()`、`reset()`；
- `pause()`、`resume()` 和 `dispose()`；
- 可展示的错误与警告。

轮询、SSE、恢复、事件归并、终态获取和清理保留在 Implementation 内。页面不再认识
interval、EventSource、run ID 或事件归并顺序。

`useResourceEvents()` 仍是 Resource 专属事件 Adapter，不与 Path 共享。

### 6.2 设置与统一结果卡片

`generator/Settings.vue` 负责设置页布局与表单协议。具备独立配置逻辑的 Agent 表单
进入 `settings/`；简单配置可以继续保留在 `Settings.vue`，避免浅 Module。

页面视觉调整为克制的产品配置界面：

- 移除大型营销式标题和过重场景卡片；
- 场景选择与 Agent 切换改为紧凑控件；
- 左侧编辑当前 Agent 参数；
- 右侧展示当前 Agent 对应的 `result/Card.vue`；
- 设置态与最终结果的卡片 DOM、封面、标题、摘要、标签、状态和底部动作一致；
- 设置态只改变数据和状态文案，不建立假的文档、代码编辑器或幻灯片截图。

`result/Card.vue` 是摘要卡片 Module，`result/Bundle.vue` 负责结果集合布局。
`shared/content/renderers/*` 是打开后的完整内容 Module，二者 Interface 不重叠。
不会增加含义模糊的 `ResourceResult.vue`。

### 6.3 生成进度

`generator/Progress.vue` 组合运行摘要、工作流、详情、日志和产物区域。原有计算按职责
迁移到具备足够 Depth 的 Module：

- `Summary`：总体进度、运行数、已交付数、最新消息和错误。
- `Flow`：真实 DAG 布局、连接关系和节点选择。
- `Agent`：单个节点的状态、进度和摘要。
- `Detail`：输入、输出、metrics、耗时和最近事件。
- `Logs`：后端事件日志。
- `Outputs`：已生成产物入口。

工作流拓扑和状态语义继续遵守
`resource-generating-workflow-design.md`，本次只改善 Locality，不改变后端协议。

### 6.4 Learning Path

`LearningPathEntry.vue` 装配 `entry/Form.vue`，`usePlanner()` 处理输入、提交和跳转。

`LearningPathOverview.vue` 装配 `overview/*`，`useWorkspace()` 集中处理：

- 路径加载和生成恢复；
- 节点状态、阶段分组和摘要推导；
- 节点选择、进入学习和主教程生成；
- Path 专属实时事件订阅；
- 页面卸载和 keep-alive 恢复。

`LearningPathNode.vue` 装配 `node/*`，`useStudy()` 集中处理学习空间加载、教程生成、
测验提交、学习跟踪和节点跳转。

历史与详情页面只有在存在重复或复杂视觉区域时才继续拆分，不追求所有 View 行数一致。

### 6.5 Shared content

`shared/content` 是 Resource 与 Path 唯一共享的内容展示 Module。其 Interface 是标准化
learning artifact，不包含资源记录 ID、路径节点 ID、请求方法或持久化信息。

- `PreviewDialog`：单个弹窗壳，根据 artifact 类型选择 renderer。
- `Frame`：统一标题、状态、内容表面与安全空态。
- `artifact.ts`：定义输入类型并执行归一化。
- `renderers/*`：只展示内容，不请求 Resource 或 Path 数据。

`Article.vue` 复用现有 `shared/ui/MarkdownRenderer.vue`，不会建立新的 Markdown
解析流程。若 `Frame` 仅剩样式透传、不能通过删除测试，则把样式留在 renderer 内，
不保留该文件。

## 7. 数据隔离

```text
resource api ──> resource model ──> useGeneration ──> resource views
                                      │
                                      └──> shared/content（仅展示 artifact）

path api ─────> path model ─────> useWorkspace/useStudy ──> path views
                                      │
                                      └──> shared/content（仅展示 artifact）
```

明确禁止：

- `resource/api` 导入 `learning-path/model`；
- `learning-path/api` 导入 `resource/api` 的记录类型；
- shared content 导入任一领域的 API、route 或记录 Model；
- Resource 与 Path 共用事件类型或事件 composable。

路径资源列表与详情类型迁回 `learning-path/model/path.ts`。

## 8. 路由策略

以下 URL 与现有 route name 均保持不变：

- `/resource-generator`
- `/resource-detail/:id`
- `/resource-history`
- `/path-planner`
- `/path-planner/overview/:id?`
- `/path-planner/node/:nodeId`
- `/path-planner/history`
- `/path-resource-history`
- `/path-resource/:id`

路由继续导入 `views/`。`MainLayout` keep-alive、Profile 导航和 learning tracker
只有在文件引用改变时才同步更新，不进行无关重命名。

## 9. 错误与生命周期

- Resource SSE 断开：停止实时动画并调用 Resource 状态 Interface 恢复。
- Path SSE 断开：调用 Path 详情 Interface 恢复，不读取 Resource 状态。
- 详情或列表请求失败：由所属 View 显示错误和重试入口。
- PPT 模板列表失败：退化为“自动推荐”，不阻断其他资源设置。
- artifact 不完整：共享 renderer 显示安全空态，不伪造内容。
- 未知 artifact 类型：显示“不支持的内容类型”。
- route 参数非法：停止请求并提供返回入口。
- `keep-alive` 停用：暂停轮询和事件连接；重新激活后按业务状态恢复。
- 卸载：清理计时器、SSE、ResizeObserver、窗口监听和延迟任务。

## 10. 迁移与删除

主要直接迁移：

| 当前文件 | 目标文件 |
|---|---|
| `views/ResourceInput.vue` | `components/generator/Input.vue` |
| `views/ResourcePersonalize.vue` | `components/generator/Settings.vue` + 必要的 `components/settings/*` |
| `views/ResourceGenerating.vue` | `components/generator/Progress.vue` + 必要的 `components/progress/*` |
| `components/ResourceBundleView.vue` | `components/result/Bundle.vue` + `components/result/Card.vue` |
| `components/ResourcePreviewDialog.vue` | `shared/content/PreviewDialog.vue` |
| `components/ResourceCardWrapper.vue` | `shared/content/Frame.vue`，仅在通过删除测试时保留 |
| `components/*View.vue` | `shared/content/renderers/*` |
| `components/resourceViewUtils.ts` | `shared/content/artifact.ts` |
| `model/ResourceGeneratorConstants.ts` | `model/catalog.ts` |
| `model/useResourceEvents.ts` | `composables/useResourceEvents.ts` |
| `api/resource-history.ts` | `api/history.ts` |
| `learning-path/api/path-resource.ts` | `learning-path/api/resource.ts` |
| `learning-path/model/usePathEvents.ts` | `learning-path/composables/usePathEvents.ts` |
| `learning-path/components/EvaluationBanner.vue` | `learning-path/components/overview/Evaluation.vue` |

以下路由 View 保留原名和目录，只缩减其 Implementation：

- Resource：`ResourceGenerator.vue`、`ResourceHistory.vue`、`ResourceDetail.vue`
- Learning Path：全部现有 `views/*.vue`

迁移完成后删除：

- 已迁移的旧文件；
- `resource-generator.css` 中已归位到所属 Module 的规则；文件为空后删除；
- Resource 与 Path 之间的业务交叉导入；
- `.DS_Store`；
- 兼容转发文件和无调用 Module。

保留并迁移用户当前对 `ResourcePersonalize.vue` 和
`ResourceGeneratorConstants.ts` 的未提交修改，不用 Git 版本覆盖。

## 11. 验证策略

前端当前没有测试基础设施，本次不额外引入。验证分四层：

1. `npm run build`：TypeScript、Vue SFC 与生产构建。
2. `git diff --check`：空白和冲突标记。
3. 静态 Seam 检查：
   - 路由仍从 `features/*/views` 导入；
   - Learning Path 不再导入 Resource 的 API、Model 或业务 Vue；
   - shared content 不导入 Resource/Path API；
   - 不存在已迁移旧文件的引用或兼容转发。
4. 浏览器回归：
   - Resource 输入、设置、生成中、结果、详情、历史；
   - 设置预览卡与最终 `result/Card.vue` 结构一致；
   - Path 创建、生成恢复、总览、节点学习、测验、资源列表与详情；
   - Resource 与 Path 内容都能打开共享 renderer；
   - 375、768、1024、1440px 无横向溢出；
   - 键盘焦点、错误态、空态和 reduced motion 可用。

## 12. 验收标准

1. URL、route name 与所有路由行为保持不变。
2. 顶层目录遵守项目已有 `api / components / composables / model / views` 约定。
3. Resource 与 Path 不再互相导入 API、记录类型或业务 Vue。
4. 两个领域只通过 `shared/content` 复用内容展示。
5. Resource 设置预览与最终结果复用同一个 `result/Card.vue`。
6. 不再存在假的 Agent 内容截图式预览。
7. 超大 Vue 的复杂职责被迁到有 Depth 的 Module，且没有纯转发浅 Module。
8. 已迁移旧文件、`.DS_Store` 和兼容文件全部删除。
9. 用户未提交的设置与 Agent 配置修改被完整保留。
10. 构建、静态 Seam 检查、diff 检查和浏览器回归全部通过。
