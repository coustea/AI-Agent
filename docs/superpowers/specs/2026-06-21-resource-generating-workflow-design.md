# ResourceGenerating 多智能体工作流设计

## 目标

重构独立资源生成页面 `ResourceGenerating.vue`，让用户能准确理解后端多智能体工作流、当前执行位置、各 Agent 的产物状态以及失败后的影响。页面采用克制、专业的工程执行台风格，移除偏概念化的 AI 装饰。

本次仅修改 standalone `resource` 生成体验，不修改 `path` 的记录、详情页、接口或持久化模型。

## 后端拓扑映射

页面严格映射 `server/app/resource/workflow/graph.py`：

1. `planning`：根据学习需求、场景、画像和已选 Agent 生成教学计划。
2. `worker_node × N`：Content、Mindmap、Quiz、Reading、Code 等基础资源 Agent 并行执行。
3. `merge_workers`：Coordinator 汇总基础资源成功/失败数量并检查大纲覆盖。
4. `ppt_node`、`video_node`：被选择时作为聚合 Agent 并行执行；未选择时不渲染对应卡片。
5. `merge_aggregation` 与 `save_node`：Bundle 等待聚合节点完成，计算终态并交付资源包。

PPT 和 Video 必须是聚合阶段的一等工作流卡片，不放入基础 Agent 网格，也不以小型附属元素呈现。

## 信息架构

页面从上到下分为三层：

### 1. 运行摘要

- 标题使用“资源生成工作流”。
- 展示总体进度、正在运行的 Agent 数量、已交付资源数量。
- 显示当前最重要的一条执行消息。
- 提供“运行日志”次要操作。
- 生成失败时在摘要下方显示包含恢复建议的错误提示。

### 2. 工作流执行台

工作流按真实依赖从左到右、从上到下阅读：

- Planning 起点卡片。
- 基础资源并行区，动态展示用户已选择的基础 Agent。
- Coordinator 汇总关卡。
- 聚合资源区，动态展示 PPT、Video 完整卡片。
- Bundle 交付终点。

阶段之间使用简单的实线、箭头或阶段分隔表达依赖。连接线不做发光、粒子流动或轨道动画。小屏幕下改为单列纵向流程，避免横向滚动。

每张 Agent 卡片至少包含：

- Lucide/Element Plus 同风格 SVG 图标，不使用 emoji。
- Agent 名称与角色说明。
- 文本状态和状态图形，不能只依赖颜色。
- 当前阶段或最近消息。
- 数字进度与稳定占位的进度条。
- 完成后显示产物就绪；失败时显示简短原因。

PPT 卡片说明其输入为教学计划和基础资源 handoff，输出为教学课件。Video 卡片说明其输入为教学计划和基础资源 handoff，输出为讲解视频配置与分镜。

### 3. Agent 详情

点击工作流卡片打开右侧详情面板。面板保留并重新组织现有信息：

- 当前任务、进度、运行耗时、最近更新时间。
- 输入与输出摘要。
- 后端上报的 metrics。
- 最近 SSE 事件日志。

关闭按钮具有可访问名称；卡片支持键盘聚焦和 Enter/Space 激活。底部“已交付资源”区域只保留简洁产物列表，避免与主工作流卡片重复表达完整状态。

## 视觉系统

采用“克制的工程执行台”方向：

- 背景：中性浅灰工作区。
- 表面：白色或接近白色卡片，细边框，仅使用一档轻阴影。
- 主色：现有产品资源蓝，用于运行态、焦点和主要进度。
- 成功、警告、失败使用可访问的绿、橙、红语义色，并始终配合文字或图标。
- 字体延续项目现有字体变量，不引入网络字体。
- 采用 4/8px 间距体系，卡片圆角和图标尺寸统一。
- 移除径向渐变、玻璃模糊、霓虹发光、环形轨道、装饰性英文 eyebrow 和 emoji 图标。

交互过渡控制在 150–250ms，仅用于焦点、详情面板和状态切换。`prefers-reduced-motion: reduce` 下关闭非必要动画。

## 状态与数据规则

前端继续消费现有 `dagNodeStates`、`visibleWorkflowNodes`、`generatedResources` 和 SSE 事件，不新增后端协议。

状态映射：

- `waiting`：等待上游或等待调度。
- `running`：显示阶段、消息和进度。
- `success`：显示已完成或产物就绪。
- `failed`：显示受阻及后端消息。
- `skipped`：显示未执行，不伪装为成功。

特殊规则：

- 未选择 PPT 或 Video 时不渲染相应卡片，Bundle 从 Coordinator 直接进入打包阶段。
- 同时选择 PPT 和 Video 时，两张卡片并列并表达并行关系。
- 部分 Agent 失败时保留成功产物，并让 Bundle 终态与后端 `partial_completed` 语义一致。
- 空日志显示明确等待状态，不制造模拟日志。
- 卡片顺序以用户选择和后端拓扑为准，不因运行状态动态重排，避免页面跳动。

## 组件边界

本轮优先在 `ResourceGenerating.vue` 内完成结构重组，复用 `ResourceGeneratorConstants.ts` 与现有 props/events。若实现后单文件职责仍过重，可提取纯展示组件，但不扩大到其他 resource 页面。

不修改用户当前对 `ResourceGenerator.vue` 的未提交改动，除非类型或调用契约验证证明必须做最小兼容调整。

## 错误处理与可访问性

- 错误信息说明失败原因和用户可采取的动作。
- 所有可点击卡片使用语义按钮行为、可见焦点环和至少 44px 点击区域。
- 动态状态区域使用合适的 `aria-live`，避免每条日志抢占焦点。
- 正文和状态文本满足 WCAG AA 对比度目标。
- 375px、768px、1024px、1440px 宽度无横向滚动。

## 验证

实施完成后执行：

```bash
npm run build
```

并人工核对以下状态：

1. 仅选择基础 Agent。
2. 选择 PPT、不选择 Video。
3. 选择 Video、不选择 PPT。
4. 同时选择 PPT 和 Video。
5. 基础 Agent 或聚合 Agent 部分失败。
6. 移动端单列、键盘导航和 reduced-motion。

