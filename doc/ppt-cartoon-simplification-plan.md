# PPT / Cartoon 代码审查与简化方案

日期：2026-11-08。状态：待审核，尚未实施代码修改。

## 1. 结论

保留现有方向：PPT 使用 PptxGenJS，视频使用 HyperFrames CLI，Agent 可以通过 Bash 编写、执行和修复作品，skills 统一放在 `server/skills/`。

当前需要解决的重点是交付正确性和职责混杂。两个生成器已经有独立工作目录、独立消息列表和工具调用循环，不需要重新引入一套 Agent 框架。建议将它们整理成“初始化依赖 → 准备本次运行 → 模型与工具循环 → 确定性构建和审查 → 返回产物”，直接删除无调用的通用子 Agent 实现、重复配置及旧格式解析。

最优先修复：

1. Cartoon 的 `system` 参数完全没有进入模型请求。
2. Cartoon 的视觉审查只要求成功调用过一次 `view_image`，与最终视频没有关联。
3. 两个 Agent 都把“看图调用成功”和“画面审查通过”混为一谈。
4. 视频字幕、分辨率、场景数量和源文件与成片的一致性没有充分校验。
5. 前端视频组件仍解析多种旧结构，并把未探测的分辨率默认显示为 1920×1080。

## 2. 阅读范围和验证依据

已阅读：

- `server/app/shared/ppt/` 全部 Python 源码。
- `server/app/shared/cartoon/` 全部 Python 源码。
- 共同依赖：工具注册、Bash、图片理解、路径处理、skills 加载、通用 subagent。
- 调用方：chat 工具与 hooks，resource 和 path 的 PPT / Cartoon 适配器、结果校验与序列化。
- 前端：`ArtifactRenderer.vue`、`Slides.vue`、`Video.vue`，资源配置类型和预设。
- 本地 `server/skills/pptx/SKILL.md`、HyperFrames CLI skill、skills 部署说明。
- 本地 `/Users/apple/Code/Python/learn-claude-code/` 的 s02、s04、s05 循环实现与相关中文说明。

当前 `ppt/agent.py` 为 161 行，`cartoon/agent.py` 为 206 行；Cartoon 的 resource/path 适配器合计 328 行。简化应减少重复状态、分支和契约转换，不以拆成更多文件或压缩成单行代码为目标。

已执行以下测试，结果 **16 passed**：

```bash
cd server
rtk proxy uv run pytest tests/shared/test_ppt_agent.py tests/shared/test_cartoon_agent.py tests/resource/test_ppt_agent_pipeline.py -q --tb=short
```

另用临时目录、假模型和假 ffprobe 输出复现了：

- 给 `_agent_loop` 传入 `system=SYSTEM`，捕获的首次请求消息角色仍然只有 `['user']`。
- `_collect_artifact` 接受只有 `WEBVTT\n` 的字幕文件；假探测结果为 320×240 时仍成功；`result.json` 自报的 999 个场景原样进入产物。

这些是代码路径验证，不是真实视频质量验证。本轮未调用付费模型、Edge TTS、实际 PPT 转换或视频渲染，也未修改业务源码、测试或既有文档。

## 3. 当前调用关系

```text
chat/tools.py ─────────── shared/{ppt,cartoon}/tool.py ─┐
resource/agents/{ppt,cartoon}.py ──────────────────────┼→ 专业生成器
path/{ppt,cartoon}.py ─────────────────────────────────┘    │
                                                          ├→ 独立消息与工作目录
                                                          ├→ 文件工具 / Bash / view_image
                                                          ├→ load_skill → server/skills/
                                                          └→ CLI 构建与产物检查
```

PPT 当前路径：`deck.cjs → deck.pptx → OOXML 校验 → LibreOffice PDF → PNG → 逐页看图`。已有重新渲染、页数核对和文件哈希关联，值得保留其正确性保障。

Cartoon 当前路径：模型自行调用工具后，Python 只检查四个非空文件、字幕文件头和 ffprobe 的音视频流。代码没有强制执行最终 HyperFrames 构建，也没有绑定最终 MP4 的视觉检查。

## 4. 已确认的问题

### 4.1 P1：Cartoon 系统提示词没有发送

位置：`server/app/shared/cartoon/agent.py:97`、`:119`、`:193`。

`generate()` 只传入 user 消息，`_agent_loop()` 虽声明 `system` 参数，却既不读取它，也不添加 system 消息。CLI 路径、必须使用真实旁白、输出文件约定、视觉修复等要求因此没有作为系统提示发送。

修改：在运行准备阶段一次性构造 `[system, user]`；循环只接收完整的 `messages`，删除独立的 `system` 参数。补一个断言实际模型请求内容的测试，不能只检查调用参数名称。

### 4.2 P1：视觉审查门槛不能证明交付质量

位置：`shared/cartoon/agent.py:137`、`:144`；`shared/ppt/agent.py:98`；`shared/tools/builtin/view_image.py`。

- Cartoon 只记录工具名，查看任何图片一次即可满足条件；之后修改 HTML、音频、截图或 MP4 不会失效。
- PPT 确实要求查看当前 PPTX 对应的全部预览图，不能把它描述成完全没有视觉校验。
- 但 PPT 只检查工具有没有报错。即使视觉模型返回“文字严重溢出”，页面仍会加入 `reviewed`，生成模型随后可以直接交付。
- Cartoon 的“两轮视觉修复”只写在提示词里，代码没有对应修复计数。

修改：由交付流程枚举应审查的真实页面/成片帧，主动执行审查；审查返回明确的 `passed` 和 `issues`，调用失败、格式错误或存在阻断问题均不得交付。保留正常的自由看图工具供创作过程中使用，最终检查不能依赖模型是否主动调用它。

### 4.3 P1：视频产物存在但内容不完整也能通过

位置：`shared/cartoon/agent.py:162`；`shared/cartoon/schemas.py:66`。

当前只验证 `WEBVTT` 前缀，没有验证字幕条目、文本和时间范围；只确认音频流存在，不能证明不是静音、旁白完整或字幕同步；未检查视频尺寸；场景数直接相信模型写的 `result.json`。源文件改动后也没有代码保证重新构建 MP4。

`CartoonResourceMetadata.quality_passed` 默认恒为 `True`，上层模型校验只是补齐这个默认值，不能证明质量经过验证。

修改：最终交付前由程序重新执行固定 CLI 构建，检查实际音视频参数、字幕条目和时间范围，再检查从最终 MP4 解码的帧。删除恒真质量字段。旁白存在、非全静音和语义正确是不同层面的检查，不能用一个布尔值全部代替。

### 4.4 P2：运行状态含猜测信息，观察回调可能使任务失败

位置：`shared/ppt/agent.py:91`、`:128`；`shared/cartoon/agent.py:66`、`:125`；`resource/agents/ppt.py:29`；`resource/agents/cartoon.py:35`；`resource/agents/base.py:67`。

- 百分比按模型轮数增加，不能代表渲染进度。
- Cartoon 用命令包含 `render` 等字符串猜阶段，甚至直接显示“1080p”。
- Resource Cartoon 没有传入实际 `progress`，只轮播预设心跳文案。
- Resource PPT 同时上报工具进度和固定 70% 心跳，两路消息可能相互覆盖。
- 两个生成器直接 await 观察回调；回调抛异常会中断生成，完成时回调失败也可能把已有产物变成失败结果。

修改：上报真实的模型调用、工具开始/结束、构建、审查、完成/失败事件。SSE、中文标签和状态存储留在调用方钩子中；观察失败只记录日志，取消必须继续传播。心跳仅用于保活，不轮播业务阶段。

### 4.5 P2：PPT 偏好重复，部分契约相互冲突

位置：`shared/ppt/schemas.py:9`；`shared/ppt/agent.py:42`；`src/features/resource/model/resource.ts:109`。

- `explanation_style` 和 `narrative_style` 语义重复；`focus` 和 `emphasis` 语义重复。
- 前端实际使用 `narrative_style`、`density`、`emphasis`。默认附加 `explanation_style='concept'` 会与用户选择的叙事方式一起传给模型。
- `include_speaker_notes=False` 与系统提示词无条件要求添加备注相冲突。
- `template` 没有对应的模板解析或选择实现，只作为普通提示数据存在，不应视为已经实现的模板功能。

修改：当前产品仅保留前端已使用的三个偏好字段；固定要求教学备注。删除重复字段和没有产品入口的模板、备注开关，直接更新调用方，不提供旧字段别名。

### 4.6 P2：Cartoon 参数和适配器保留宽松兜底

位置：`shared/cartoon/schemas.py:12`、`:43`；`shared/cartoon/tool.py:38`；`resource/agents/cartoon.py:113`、`:128`；`path/cartoon.py:119`。

- `extra='ignore'` 会静默忽略错误或旧配置；resource 又先过滤一遍字段。
- `voice` 在工具参数中是任意字符串，非法值被悄悄转为 teacher。
- `CartoonInput` 只包装 `brief + output_dir`，没有增加约束或独立业务意义。
- 上游素材已经是 `DownstreamContext`，却继续接受任意对象、字典和字符串并逐级兜底。
- 两个适配器重复 `_safe_username`；当前清洗还可能让不同原始名称映射为同一个目录名。应在路径边界统一校验，不重复修改用户标识。

修改：输入改成显式 `brief, output_dir`；配置拒绝额外字段；voice 使用现有 Literal 范围；素材按已声明类型读取；路径由调用方使用已校验身份生成。

### 4.7 P2：前端保留旧格式解析，并展示未经确认的信息

位置：`src/shared/content/renderers/Video.vue:61`、`:93`；`Slides.vue:27`；`ArtifactRenderer.vue:28`。

- Video 同时解析 JSON 字符串、`content.metadata`、`public_url`、`video_url`、毫秒和秒等多种形状。
- 当前 resource 的 `_item_to_dto()` 和 path 的 DTO 均输出 `metadata`。数据库的 `metadata_json` 是存储字段，不需要继续泄漏给展示组件。
- Video 在没有尺寸字段时直接展示 1920×1080；后端又未验证该尺寸，容易显示错误信息。
- 后端返回 `captions_url`，播放器没有字幕 track 或字幕下载入口。
- Slides 残留 `.deck-status`、`.deck-page`、`.icon-button`、`.nav-primary` 等模板未使用样式。

修改：按当前接口直接读取 `metadata`，采用明确的 PPT / Video 展示类型；移除旧结构、旧字段与旧风格映射。尺寸读取实际探测值；提供 VTT 下载/可切换字幕，烧录字幕的视频默认不重复开启外挂字幕。

### 4.8 P2：部署要求在请求开始时没有得到验证

位置：`shared/ppt/agent.py:58`；`shared/cartoon/agent.py:29`；根 `package.json`；`server/skills/README.md`。

两个生成器假定后端部署目录的祖先存在项目根 `node_modules`。HyperFrames 在 `devDependencies` 中，因此只安装生产依赖的部署会缺少视频 CLI。技能里的可选图标依赖也不等于项目实际声明了这些依赖。

修改：明确唯一部署布局，执行必要依赖的部署冒烟检查；任务开始时缺少核心命令/技能直接返回具体错误。后端运行必需的 HyperFrames 应纳入运行依赖。不要让模型在任务中安装环境，也不要新增一套依赖管理平台。

### 4.9 Bash 的实际执行边界需要写清楚

位置：`shared/tools/builtin/bash.py`；`shared/tools/sandbox.py`。

现有 Bash 使用宿主环境变量和进程权限，cwd 不是系统沙箱，几个危险字符串也不构成隔离。文件工具的路径约束不能限制 Bash 的绝对路径访问。

方案继续保留 Bash/CLI。若运行环境接收不可信内容，权限隔离由部署的进程或容器边界承担；不要继续叠加命令字符串黑名单，也不要为了“封装渲染”隐藏 Bash 的真实能力。这是当前执行边界的说明，不把隔离平台扩展为本次重构项目。

## 5. 简化后的实现设计

### 5.1 保留两个专业 Agent，chat 循环保持独立

chat 用现有两个工具调用专业生成器，只接收摘要和产物引用。PPT / Cartoon 的创作消息、长命令输出和视觉报告不写进聊天历史。

参考 learn-claude-code 的原则：s02 的直接工具分派，s04 的子任务上下文隔离，s05 的技能描述常驻、正文按需加载。不要照搬示例的全局变量、SDK 消息格式或无法表示失败的结束方式。

两个模块采用相同的入口形状：

```text
PPTAgent(...固定依赖...).generate(brief, output_dir, on_event=...)
CartoonAgent(...固定依赖...).generate(brief, output_dir, on_event=...)
```

实例只保存模型客户端、模型配置、skill loader 和系统提示等固定依赖。`messages`、工作目录、工具表、审查结果、修复次数都属于本次调用，不能放进共享实例。

构造函数不创建工作目录、不渲染、不持有用户上下文。当前 PPT 已部分符合这个方向，不需要把所有东西从 `generate()` 强行移进构造函数。

### 5.2 循环与交付分开，以顺序执行减少状态

建议的主流程：

```text
准备 workdir、完整 messages、绑定目录的工具表
  ↓
运行模型/工具循环，直到模型本轮停止调用工具
  ↓
用固定 CLI 从当前源文件重新构建交付物
  ↓
校验文件与媒体信息 → 生成实际页面/成片帧 → 视觉审查
  ├─ 通过：立即返回 Artifact
  └─ 失败：将具体问题追加到 messages，进入下一次修复
```

- 首次制作加最多两轮修复；总时限和总模型轮数覆盖完整任务，不能每次修复重置预算。
- 内部循环只接收准备好的消息、模型依赖、工具表、剩余轮数和观察函数。只负责模型调用、顺序执行工具、追加结果、报告事件。
- 输出目录和业务 brief 不进入模型循环签名；产物构建、校验、错误回灌由 `generate()` 编排。
- 两个短循环可分别留在本模块；暂不新增 `BaseAgent`、通用 `Harness`、插件式 validator、事件总线或可选 deliver 回调。
- 模型主动停止不等于成功。成功只由交付流程产生。

这能删除 PPT 当前的 `prepared_hash/source_hash/previews/reviewed/pdf_hash` 交错状态：最终阶段不允许 Agent 修改文件，构建后直接审查并返回，失败则重新完整构建。前提是同一工作目录没有并发或后台写入；若实施时仍允许这种写入，不能直接删除现有版本绑定检查。

两类任务继续顺序执行文件、截图和渲染工具。不要并行调用同一目录的多个写入任务。

### 5.3 文件组织保持小规模

```text
shared/ppt/
  __init__.py
  agent.py       # 固定依赖、单次运行准备、编排、短工具循环
  delivery.py    # 从源码构建、校验、逐页审查
  schemas.py     # Brief、Preferences、Artifact、领域错误
  tool.py        # chat 的薄入口

shared/cartoon/
  __init__.py
  agent.py       # 与 PPT 相同的职责边界
  delivery.py    # CLI 构建、媒体与字幕校验、成片抽帧审查
  schemas.py     # Brief、Config、Artifact、发布元数据、领域错误
  tool.py        # chat 的薄入口
  tts.py         # 保留真实语音工具和取消清理
```

只拆出确实承担构建/校验职责的 `delivery.py`。它直接调用现有 Bash 和图片工具，不再逐层套 service、manager、repository 或抽象渲染接口。短提示词可继续放在 `agent.py`，不为几行文本新增加载器。

### 5.4 PPT 最终交付

1. 执行当前 `deck.cjs`，生成 `deck.pptx`，检查退出码。
2. 执行已安装 skill 的 OOXML 校验脚本。
3. 使用本次独立 LibreOffice profile 转 PDF，再通过 Poppler 输出逐页 PNG。
4. 检查 PPTX、PDF 和预览页数及非空文件。
5. 程序逐页调用图片工具，要求检查文字、溢出、遮挡、图表、可读性与教学内容。
6. 将视觉响应中的 JSON 验证为最小结果 `{passed: boolean, issues: string[]}`；格式不合法不能当成通过。失败页和具体问题回传给生成模型修复。
7. 全部通过才返回 `PPTArtifact`。同一任务的修复不新增并行创作实例。

模型在创作阶段仍能自由运行 Bash、预览和看图。应用负责最后一次可信构建，避免仅凭“模型说已执行”交付。

### 5.5 Cartoon 最终交付

1. 从当前 HTML、本地媒体和旁白运行已安装 HyperFrames 的检查与最终渲染。具体命令以锁定版本的本地帮助为准，复用现有 Bash，不编写新的浏览器渲染器。
2. 用 ffprobe 读取实际宽高、时长与音视频流；明确执行现有工具承诺的 1920×1080 要求，或同步修改工具描述和产品契约，不能只改显示文案。
3. VTT 至少有一条非空文本 cue；每条时间合法、开始小于结束、时间单调且落在成片时长内。目标时长是偏好，不把默认 120 秒当成必须精确相等的条件。
4. 保留 TTS 生成成功记录及实际时长，检查最终音频可解码且不是全静音。音轨存在不能替代这一步；语义和发音正确仍需抽听验收，不宣称由 ffprobe 保证。
5. 用最小审查清单提供场景时间段，不再接受一个无法核验的 `scene_count`。可将现有 `result.json` 改为 `title + scenes[{start,end}]`，数量由合法条目推导，并与源作品实际时间轴和成片时长核对。它只用于抽帧覆盖，不扩展为布局/动画中间语言。
6. 从最终 MP4 解码各场景中间帧及转场前后帧；复杂运动补充中间采样。HTML snapshot 用于创作调试，不能代替成片检查。
7. 使用与 PPT 相同的最小审查结果形状。问题回灌后重新构建；修复预算耗尽就失败。

宽高和时长来自探测，场景清单与源时间轴的核对来自交付校验。抽帧能检查覆盖到的画面，不能保证每一帧、所有讲解事实和音画同步都绝对正确。

### 5.6 事件采用一个可选回调

使用一个小事件结构和一个 `on_event` 回调即可。必要字段为 `kind`、实际步骤/工具名称、工具调用 ID、成功/失败及简短信息；仅在有可测总量时提供完成数与总数，例如已检查 3/8 页。

循环只报告 `model_start/end`、`tool_start/end`；交付函数报告 `build/review` 的开始和结束。中文标签、SSE 写入、前端状态更新由外部钩子处理，不把消息发送代码放进循环。

适配关系：chat 转为现有子步骤；resource 转为现有运行快照；path 接入本域的运行状态。普通观察异常不影响任务，`CancelledError` 不吞掉。SSE 保活与业务事件分开。

不建立跨模块状态中心，不为两类子 Agent 新建另一套 SSE。调用方尚未完成持久化时，子 Agent 完成事件也不能提前把整个资源任务标成完成。

### 5.7 产物、调用方和前端契约

生成器返回文件路径、标题和真实统计；发布 URL 在现有 artifact/metadata 转换处集中生成。Cartoon 的三个调用方复用同一个元数据构造逻辑，删除重复 URL、时长转换，不新增通用 publisher。

| PPT 元数据 | Video 元数据 |
|---|---|
| `pptx_url` | `video_url` |
| `pdf_url` | `preview_url`，保留当前 HTML 预览能力 |
| `preview_urls` | `captions_url` |
| `slide_count` | `scene_count` |
| `file_size` | `duration_seconds`、实际 `width` / `height` |

resource/path 继续保存各自的数据记录、目录和详情页，只复用生成器和产物字段。chat 的输出目录由 chat 调用方提供，避免工具内部拼接 `resources/chat_*` 这样的业务目录。

前端按两个业务 API 现有 `metadata` 结构读取，无需兼容数据库字段名或旧 content 嵌套。chat 的产物卡仍由 chat hooks 提取；若要提供 PPT 逐页预览，应同步保留 `preview_urls`，当前 `_extract_artifact()` 仅留下标量会丢弃这个数组，不能只改组件。

## 6. 删除和保留清单

以下均为计划，本文没有执行删除。

| 对象 | 处理方式与依据 |
|---|---|
| `shared/tools/subagent.py` | 删除。仓库运行代码没有调用方，只有定义和导出；内部还向 `build_builtin_tools` 传入已不存在的 `include_bash/include_view_image/include_glob_grep` 参数，调用即失败。专业 PPT/Cartoon 工具不依赖它。 |
| `CopySkillTemplateArgs` / `build_copy_skill_template_tool` | 删除定义和导出。全仓库仅定义与导出，没有调用；且 `only` 未执行限制、源路径未校验边界。模板复制可用现有 Bash，没必要修复一个不用的抽象。 |
| `sandbox.py` 的 `resolve/safe_path/truncate` 别名 | 删除及移除导出。当前调用均使用正式名称。保留路径检查和截断本体。 |
| `build_ppt_subagent_tool = build_ppt_tool` | 删除别名，chat 同步改用 `build_ppt_tool`。它目前有真实调用，不能只删定义。 |
| Cartoon `_agent_loop` 的 `_T`、可选 `deliver`、`required_tools`、无 deliver 文本返回分支、`partial` | 随明确的创作循环和交付流程替换。实际生产只有一个调用形态，不需要伪通用能力。 |
| `CartoonInput` | 删除，所有调用方直接传入 brief 与 output_dir。 |
| Cartoon `schema_version`、恒真 `quality_passed`、重复的恒真 `has_audio` | 删除无消费者的版本/质量标记。音轨要求由交付检查保证，不靠默认字段声明。 |
| `CartoonArtifact.output_dir` | 若按本方案仍无独立消费者则删除；已有文件路径包含其目录，不额外复制保存。 |
| PPT `explanation_style/focus/template/include_speaker_notes` | 删除，保留当前产品的三个偏好字段及固定备注要求。 |
| Cartoon 适配器的任意类型兜底、重复用户名清洗、单次调用的 `_result/_failure` 包装 | 按类型收紧并就近合并；内容较长的输入映射可保留 `_brief`，不机械内联所有函数。 |
| 前端旧结构解析、旧视频风格映射、Slides 未使用 CSS | 前后端同步修改后删除，无旧格式 fallback。 |
| `python-pptx` | 不按“生成引擎换了”直接卸载。`markitdown[pptx]` 仍需要解析能力，skills 部署说明已明确。顶层重复声明是否可去除要核对依赖锁，不删除解析功能。 |
| `server/skills/pptx` 官方脚本及许可证 | 保留。不要把运行时按需加载或 CLI 调用的文件当作无 Python import 的死代码。 |
| `Tool`、`ToolRegistry`、`load_skill`、`view_image`、Bash、TTS | 保留。均有实际调用且职责明确；TTS 的失败/取消清理值得保留。 |
| `docs/superpowers/` 历史方案 | 不自动删除。其内容不能作为当前实现依据；是否归档属于文档整理，不混入代码删除。 |

类型注解和中文 docstring 一并补齐；修正 PPT 类注释中的 `python-pptx` 和 `_prepare` 的英文说明。不做全仓库无关格式化。

## 7. 实施顺序与验收

| 步骤 | 修改范围 | 验收重点 |
|---|---|---|
| 1. 修复请求与参数契约 | 两个 schemas、Cartoon 请求构造、chat/resource/path 调用方 | system 真正进入请求；无旧别名；非法配置明确失败；独立调用不共享运行状态。 |
| 2. 分离创作和交付 | 两个 agent、两个 delivery、必要的图片审查接入 | Bash 顺序执行；最终源码重新构建；审查失败会修复；总预算不被重置；保留取消传播。 |
| 3. 对齐事件和输出 | 两个 tool、resource/path 适配器、chat hooks | 实际工具和构建步骤可观察；没有假百分比；观察错误不改变任务结果；父任务完成与子任务完成区分。 |
| 4. 删除旧代码、对齐前端 | tools 导出、无调用 subagent、模板复制、展示组件和类型 | 当前 metadata 直接消费；预览、下载、字幕正常；resource/path 记录与详情页仍各自独立。 |
| 5. 验证运行环境 | 依赖声明、skills 部署说明和聚焦测试 | 在后端部署环境真实生成 PPT 和视频，确认文件能打开、中文可读、旁白可听。 |

应新增或更新的行为测试：

- 捕获模型请求，确认 system + user 和工具结果链完整。
- 最终审查报告有严重问题、调用失败或格式不合法时，不能交付。
- 修改源文件后，交付时确实重新构建；PPT 所有页、视频所有必需采样点都被审查。
- VTT 空条目、越界时间、缺少音轨、错误尺寸、错误场景清单均失败。
- 修复超过两轮、总轮数耗尽、超时和取消都有明确终态，Bash 子进程被终止。
- 观察回调失败不丢失有效产物；两次并发生成的消息和目录互不污染。
- 三个入口获得相同的产物字段，PPT 下载/预览与 MP4 播放/字幕在前端可用。

执行相关后端测试和 `npm run build`，再做真实产物冒烟：一份含中文、原生图表和备注的多页 PPT；一段有真实旁白、字幕和转场的视频。必须查看 PPT 每页和视频成片抽帧，并抽听音频。Mock 测试通过不代表 LibreOffice、字体、浏览器、TTS 和编码环境已经可用。

实施完成标准：删除清单落地、没有兼容入口、两个 Agent 的循环可独立阅读、交付检查可明确解释、前后端字段一致、真实产物验证通过。无需为了架构统一新增通用 Agent 框架。
