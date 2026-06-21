## Context

在目前的路径规划看板中，界面采取了三栏并排（左侧菜单、中间节点长列表、右侧指标卡片堆叠）的设计。同时，由于数据填充原因，同一个节点的详细描述文本在三个不同区域中重复渲染（阶段描述、节点卡片描述、侧边栏当前推进描述），加上狭窄的水平宽度，造成极度拥挤、杂乱的视觉灾难。

为了给用户提供专业、高级且具备呼吸感的 AI 学习仪表盘，本设计将整个主页面推倒重构，采用“双栏聚焦看板（Sleek Split Dashboard）”布局，隔离总览与细节，消除一切文字冗余，并对指标面板进行 Tab 化整合。

## Goals / Non-Goals

**Goals:**
- **推倒重构为双栏布局**：左栏为 Timeline 形式的大纲目录（不渲染描述文字，保持极简），右栏为选中节点的专属工作区（唯一展示长描述和行动按钮的区域）。
- **Tab 化控制台**：将右栏底部原先堆叠的指标整合为 Tab 切换面板（学习信号、诊断文献、路线总结），消除垂直滚动。
- **渲染检索证据**：在“诊断文献” Tab 中，提取后端的 `search_evidence` 数组，渲染为文献引用卡片。
- **SVG 智能体动效**：通过 SVG 与 CSS 帧动画直观联动后端任务状态，废弃简陋的控制台日志列表。

**Non-Goals:**
- 不改变任何后端 API 的响应字段和参数格式。
- 不引入外部动画 JS 库，完全依赖轻量级 SVG + CSS 帧动画。

## Decisions

### 1. 布局重构：双栏自适应网格
- **方案**：将看板网格定义为 `grid-template-columns: 320px minmax(0, 1fr); gap: 24px;`。
  - **左栏 (Syllabus Roadmap)**：宽度固定为 320px，用于展示阶段大纲和节点 Timeline。左栏仅展示 `node.title`，完全隐藏 `node.mastery_target` 或描述文字，腾出空间。
  - **右栏 (Study Station)**：自适应剩余宽度，采用大卡片设计展示当前节点的详细信息与操作。
- **理由**：双栏设计大幅增加了左右两侧的水平拉伸空间，消除了因三栏并列导致的文本密集折行。

### 2. 状态通信与组件重构
- **方案**：为了保证重构后的代码可读性，将抽取以下两个子组件：
  - [NEW] [PathStartHub.vue](file:///Users/apple/Code/software/src/learning/components/PathStartHub.vue)：处理目标输入及推荐模板。
  - [NEW] [PathAgentLoading.vue](file:///Users/apple/Code/software/src/learning/components/PathAgentLoading.vue)：处理生成中的 SVG 多智能体节点动画。
- 考虑到左栏 Roadmap 与右栏 Study Station 在折叠、选择节点时存在高频的状态共享，我们选择**在 `LearnPath.vue` 中直接实现双栏模板**，而不是做过度拆分。右栏下方的“诊断文献”等子面板可以通过条件渲染渲染，保证事件绑定的直观性。

### 3. 文献卡片渲染
- **方案**：在“诊断文献” Tab 下，读取 `coursePath.search_evidence`，将其渲染为一个 CSS Grid 网格。每个卡片显示文献标题（`title`）、检索来源（`tool`）、摘要（`snippet`），并在悬停时显示渐变边框和指向链接的点击手势。

## Risks / Trade-offs

- **[Risk] 左栏节点文字过长导致超出限制** → **Mitigation**: 对左栏大纲中的节点标题应用 CSS `text-overflow: ellipsis; white-space: nowrap;` 配合 `title` 悬停提示，确保大纲一目了然。
- **[Risk] 无活跃路线时如何展示** → **Mitigation**: 仍然复用 `PathStartHub.vue` 以居中发光大卡片形式呈现，与双栏看板的无路线状态无缝隔离开。
