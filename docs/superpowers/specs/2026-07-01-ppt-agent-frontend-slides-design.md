# PPTAgent Frontend Slides 重构设计

## 目标

将资源生成中的 PPTAgent 重构为多智能体 HTML 演示文稿流水线。最终产物是一个可直接在浏览器运行的单 HTML 文件，生成和验收规则以 `frontend-slides` skill 为唯一依据。

本次重构不兼容旧 PPT 数据结构，不保留旧主题配置、版式枚举、slot/block 契约或静态 HTML 拼装器。前端同步删除旧配置和旧播放器遗留，只负责安全地展示生成后的 HTML。

## 已确认的产品决策

- 当前只提供自动生成模式，不让用户选择风格。
- 系统内部仍比较三条设计方向：安全预设、bold template、自定义 wildcard，然后自动选择最适合的一条。
- 最终直接生成 HTML，不生成中间 PPT JSON，也不导出 `.pptx`。
- 密度、用途、受众、篇幅和视觉气质由智能体从学习需求、教学计划和上游交接内容中推断。
- HTML 默认包含键盘、鼠标滚轮、触摸导航、页码/进度、动效、减少动态效果支持和浏览器内文本编辑。
- 生成结果必须经过静态校验和真实浏览器视觉验收；不合格时允许一次定向修复，仍不合格则任务失败。
- `resource` 和 `path` 可共享 PPTAgent 基础设施，但继续使用各自的记录、详情页和持久化流程。

## 非目标

- 本期不提供用户挑选三张风格预览的交互。
- 本期不支持导出 PowerPoint 文件。
- 本期不支持把用户上传的 `.pptx` 转为 HTML。
- 本期不增加在线部署或 PDF 导出入口。
- 本期不为旧 PPT 配置、旧 PPT JSON 或旧前端播放器提供迁移和兼容逻辑。

## 总体架构

`PPTAgent` 保留为工作流使用的外观入口，内部改为四阶段流水线：

```text
上游教学内容
  -> BriefPlanner
  -> StyleDirector
  -> HTMLAuthor
  -> StaticValidator
  -> BrowserVisualQA
  -> [一次 RepairAgent 修复并重新验收]
  -> HTML 文件与最小结果元数据
```

### 1. BriefPlanner

输入：

- 用户学习需求
- 教学计划
- 已完成资源的上游交接内容
- 当前资源标题和章节上下文

输出 `DeckBrief`：

- `purpose`
- `audience`
- `density`: `speaker_led` 或 `reading_first`
- `target_slide_count`
- `narrative`
- `required_points`
- `language`
- `mood`

该结构只描述生成意图，不描述页面布局，也不是旧 PPT 内容模型的替代品。

### 2. StyleDirector

StyleDirector 使用项目内的精简风格目录进行自动决策。目录来自 `frontend-slides` 的 safe presets 和 bold template selection index，但作为项目代码的一部分维护，运行时不读取用户主目录。

每次生成内部评估三种候选：

1. 与内容匹配的安全预设。
2. 与用途、正式度、密度和气质匹配的 bold template。
3. 一个上下文定制 wildcard。

输出 `StyleDecision`：

- `name`
- `source`: `preset`、`bold_template` 或 `custom`
- `rationale`
- `design_recipe`
- `font_urls`
- `density`

只把获胜方向交给 HTMLAuthor，不生成或保存三份预览 HTML。这样保留 skill 的设计比较原则，同时符合当前“一次生成”的产品选择。

### 3. HTMLAuthor

HTMLAuthor 接收 `DeckBrief`、`StyleDecision` 和完整教学内容，直接输出最终 HTML 字符串。它不输出 Markdown 代码围栏，不输出 JSON，不调用旧 renderer。

项目内提示词必须包含并约束以下 `frontend-slides` 规则：

- 单 HTML 文件，CSS 和 JavaScript 全部内联。
- 所有幻灯片使用 `.slide`。
- 使用固定 1920×1080 `.deck-stage`，整体等比缩放到视口。
- 小屏只 letterbox/pillarbox，不重排幻灯片内容。
- 完整嵌入项目内保存的 `viewport-base.css`。
- 使用 `.active` / `.visible` 控制 `visibility`、`opacity` 和 `pointer-events`，不得用 `display` 切换幻灯片。
- 使用 Google Fonts 或 Fontshare 字体，不使用 Arial、Inter、Roboto 或系统字体作为视觉字体。
- 提供键盘、Space、PageUp/PageDown、滚轮和触摸导航。
- 提供页码或进度反馈。
- 默认提供编辑热区、`E` 键编辑模式、`contenteditable` 和 `Ctrl/Cmd+S` 下载当前 HTML。
- 提供 `prefers-reduced-motion`。
- CSS 按清晰 section comment 分段。
- 不允许滚动、内容溢出、面板遮挡或小到不可读的文字。
- 低密度遵循一页一个核心观点；高密度使用清晰网格、表格或注释，并在拥挤时拆页。
- 不生成通用紫色渐变、同质化卡片墙或无上下文装饰。

由于结果会在 sandbox iframe 中运行，编辑保存采用 Blob 下载，不依赖服务端覆盖接口或同源 `localStorage`。

### 4. StaticValidator

静态校验使用 HTML 解析器，不用字符串猜测结构。校验至少包括：

- 存在且仅存在一个完整 HTML 文档。
- 存在 `.deck-viewport` 和 1920×1080 `.deck-stage`。
- 至少一张 `.slide`，且首张具有 `active`。
- 每张 slide 有可见文本或可见媒体内容。
- 包含完整固定舞台基础 CSS 的关键规则。
- 包含导航、缩放、触摸、滚轮、编辑和保存行为。
- 包含 `prefers-reduced-motion`。
- 不含 Markdown 围栏。
- 不引用本机绝对路径。
- 不包含外部脚本；只允许字体样式表网络请求。
- slide 数量与 `DeckBrief` 的目标范围一致。

校验失败会产生结构化问题列表，供 RepairAgent 精确修复。

### 5. BrowserVisualQA

Playwright 在本地 HTTP 上打开临时 HTML，并在桌面 `1280×720` 和手机视口各检查一次。固定舞台应在两种视口中保持 16:9 并完整缩放。

每张 slide 检查：

- 页面脚本无异常。
- slide 可激活且其他 slide 不可交互。
- stage 和 slide 尺寸符合固定舞台规则。
- 内容没有超出 1920×1080 边界。
- 文本元素没有被裁切。
- 主要内容块没有明显重叠。
- slide 不是空白页。
- 字体达到可读下限。
- 键盘导航可以前进和后退。

QA 输出 `VisualAudit`，包含失败 slide、问题类型和元素摘要。首轮失败时 RepairAgent 获得原 HTML、静态问题和视觉问题，最多修复一次。第二轮失败直接抛出生成错误，不发布有缺陷的文件。

## 项目内规则资产

重构后项目持有自身的 PPT 生成规则，不从个人 skill 目录动态读取：

- 固定舞台 CSS。
- HTML 功能契约。
- safe preset 风格目录。
- bold template 精简选择目录。
- 动效选择指导。

这些文件是生成输入和校验基准，不是旧 renderer 模板。HTML 的具体页面结构仍由 HTMLAuthor 根据内容和获胜风格生成。

## 数据契约

### 请求配置

删除以下旧字段及其前后端类型：

- `theme_id`
- `template_id`
- `explanation_style`
- `visual_emphasis`
- 其他只服务旧 JSON renderer 的 PPT 属性

`AgentConfigs.ppt` 保留为空且 `extra="forbid"` 的配置对象，用于维持不同资源类型统一的请求形状。这不是旧配置兼容层；当前版本没有用户可调 PPT 参数。

### 结果元数据

PPTAgent 只返回：

- `file_type: "html"`
- `html_file_path`
- `html_url`
- `slide_count`
- `style_name`
- `density`
- `file_size`

不返回 `PPTDocument`、slides JSON、theme、layout、slot 或 block 数据。

## 删除范围

后端删除：

- 旧 `ppt_contract.py`
- 旧 `ppt_manifest.json`
- 旧静态 `HTMLSlideGenerator`
- 旧 `ppt_director.md` / `ppt_chapter.md` 及其 JSON 生成提示
- 旧 PPT schema、layout、slot、block、theme 和 renderer 相关代码
- 已跳过且只验证旧 PPT 结构的测试
- 未被新流水线使用的 PPT 辅助代码

前端删除：

- 旧 PPT engine 目录及其组件、converter、renderer、types 和文档
- PPT 个性化页中的主题、讲解方式、视觉重点等旧控件
- 对旧 PPT JSON、旧 theme 和旧 layout 的类型与分支
- 未使用的 PPT 常量、样式和资源

前端保留：

- 一个职责单一的 `PptView.vue`
- 从结果元数据取得 HTML URL 的逻辑
- 加载、失败和重试展示
- sandbox iframe 展示

## API 与安全

- 删除匿名写入生成 HTML 的 `PUT /resources/public/{resource_id}/html` 接口。
- 只保留读取生成结果所需的路由。
- iframe 使用 sandbox，允许演示脚本和文件下载，但不授予同源权限。
- 生成 HTML 不允许外部脚本、不允许访问父页面 DOM、不允许本机绝对路径。
- 服务端文件名由资源 ID 或安全 slug 生成，不使用模型输出作为路径。
- HTML 只在静态和浏览器验收都通过后原子写入最终位置。

## 工作流与持久化边界

资源工作流继续通过当前 PPT 节点调用 `PPTAgent.generate()`。学习路径如果复用该 Agent，也只能接收其返回结果，再由自己的服务和模型持久化。

本次不移动、不合并：

- standalone resource 记录
- learning path 资源记录
- 两类详情页
- 两类状态推进和失败处理

共享范围只限生成器、规则资产和 QA 基础设施。

## 错误处理

- Brief 或 Style 结构化输出无法解析：当前生成任务失败，保留明确阶段名和可诊断原因。
- HTMLAuthor 输出不完整：进入一次 RepairAgent；仍不完整则失败。
- 静态校验失败：将结构化问题交给 RepairAgent。
- Playwright 启动失败：视为环境配置错误并失败，不静默跳过视觉 QA。
- 视觉 QA 失败：一次修复后仍失败则不写最终文件。
- 文件写入失败：清理临时文件，不返回可访问 URL。
- 所有错误继续走现有 resource/path 各自的任务失败机制。

## 测试策略

### 单元测试

- `DeckBrief` 和 `StyleDecision` 严格 schema。
- 风格候选始终包含 safe、bold 和 wildcard 三类，并只选择一个结果。
- HTML 静态校验覆盖缺少 stage、错误 slide 切换、外部脚本、本机路径、缺少编辑/导航等失败。
- 结果元数据只包含新字段。
- 请求 schema 拒绝所有旧 PPT 配置字段。

### 流水线测试

- 使用可控的 LLM 假实现验证四阶段调用顺序和上下文传递。
- 首轮 HTML 不合格时只调用一次 RepairAgent。
- 第二次不合格时不写最终文件。
- 合格时原子落盘并返回正确 slide 数量、style 和 density。

### 浏览器测试

- 使用最小合格 fixture 验证桌面和手机视口的固定舞台缩放。
- 验证下一页/上一页键盘导航。
- 验证溢出、空白页和明显重叠会被识别。

### 集成验证

- 运行 PPT 相关后端测试。
- 运行 resource 请求和工作流相关测试。
- 运行前端 `npm run build`。
- 启动 FastAPI 与 Vite，生成一份真实 PPT 资源并在浏览器检查加载、翻页、编辑和下载。

## 验收标准

1. 代码库中不存在旧 PPT JSON 合约、旧静态 renderer 或旧前端 PPT engine。
2. 前后端不存在 `theme_id`、`template_id`、`explanation_style`、`visual_emphasis` 等旧 PPT 配置。
3. PPTAgent 通过多个职责明确的智能体阶段生成一个完整 HTML 文件。
4. 每份 HTML 固定为 1920×1080 舞台，桌面和手机均只等比缩放。
5. 每份 HTML 具备导航、动效、减少动态效果和内联编辑/下载能力。
6. 每份发布结果均通过静态校验和 Playwright 视觉 QA。
7. 首轮失败最多修复一次，失败结果不会被发布。
8. 前端只通过 sandbox iframe 展示 HTML，不提供匿名覆盖接口。
9. standalone resource 与 learning path 的记录、页面和持久化仍完全分离。
10. 后端目标测试与前端构建通过。
