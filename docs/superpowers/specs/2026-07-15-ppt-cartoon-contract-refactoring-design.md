# PPT 与 Cartoon 契约重构设计文档

**日期**: 2026-07-15
**状态**: 设计阶段
**范围**: `server/app/shared/ppt/`, `server/app/shared/cartoon/`, `server/app/resource/agent_preferences.py`, `src/features/resource/`

---

## 1. 设计目标

### 1.1 核心目标

建立严格的 LLM/后端边界：

```text
LLM 只生成教学内容
        ↓
后端确定性补齐 ID / 布局 / 图表 / 时间轴
        ↓
渲染器只消费已验证的内部模型
```

**禁止**：
- 让 LLM 生成渲染器结构、跨对象 ID、时间轴、历史字段
- 在 `server/app/infra/llm.py` 中添加 PPT/Cartoon 业务修复逻辑
- 保留任何旧契约兼容层

### 1.2 非目标

- 不修改测试文件
- 不做旧缓存兼容

---

## 2. 第一组：PPT 契约重构

### 2.1 固化两层模型边界

**文件**: `server/app/shared/ppt/models.py`

**现状分析**：
- `DeckLogicDraft`、`PPTSectionDraft` 是 LLM 输出模型，不包含渲染字段
- `DeckLogicModel`、`PPTDeck`、`VisualSpec` 是后端内部模型
- 两层边界已建立，需确认无残留

**修改**：
1. 确认 `SlideContentDraft` 只包含教学内容字段：
   - `lead: str` — 导语
   - `points: list[SlidePoint]` — 要点卡片
   - `takeaway: str` — 本页结论
   - 条件性字段：`code`/`code_language`（仅代码页）、`formula`/`formula_steps`（仅公式页）

2. `VisualSpec` 保持不变，它由后端 `_materialize_visual()` 确定性生成：
   - `kind: VisualKind`
   - `caption: str` — 图表标题（后端生成）
   - `metrics: list[VisualMetric]` — 指标卡（后端从 points 派生）
   - `model: DiagramModel | None` — 关系图（后端从 question/claim/teaching_goal 派生）
   - `code`/`formula` — LLM 输出的代码/公式内容

### 2.2 清理旧视觉 JSON 提示词残留

**文件**: `server/app/shared/ppt/section_compose.md`

**现状**：已明确禁止输出 `visual`、`nodes`、`edges`、`metrics`，无需修改。

**验证**：确认 `logic_model.md` 提示词无残留要求。

### 2.3 解决 PPT 页面下半部分留白

**根因**：
- `VisualSpec` 和 `PPTSlide` 没有携带"内容密度"信息
- CSS 中 `.slide-main` 的 `min-height:0` 允许内容区过度收缩
- 图表、代码区没有填满可用高度的规则

**修改（模型层）**: `server/app/shared/ppt/models.py`

在 `SlideBrief` 和 `PPTSlide` 中添加内容密度字段：

```python
class SlideBrief(PPTModel):
    # ... 现有字段 ...
    density: Literal["concise", "standard", "detailed"] = "standard"
```

**修改（渲染层）**: `server/app/shared/ppt/html.py`

在 `BASE_CSS` 中建立"内容密度—布局"全局规则：

```css
/* 内容页使用可伸缩主内容区，占可用高度约 70% 以上 */
.slide-main {
  min-height: 480px;
}

/* 图解、指标和代码区必须填充主舞台 */
.visual {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 320px;
}

.diagram-wrap,
.code-panel,
.formula-panel,
.metrics {
  flex: 1;
  min-height: 0;
}

/* 卡片、流程、对比表根据项目数量自动增高 */
.points {
  min-height: 120px;
}

/* 只有封面和章节页允许显著留白 */
.kind-cover .slide-main,
.kind-roadmap .slide-main,
.kind-summary .slide-main {
  min-height: auto;
}
```

**修改（生成器层）**: `server/app/shared/ppt/generator.py`

在 `_compile_storyboard()` 中传递 density：

```python
briefs.append(
    SlideBrief(
        # ... 现有字段 ...
        density=context.preferences.density,
    )
)
```

### 2.4 降低首次 JSON 校验失败率

**现状**：已实现以下措施：
- `section_compose.md` 明确"禁止 Markdown 代码围栏，禁止额外字段"
- 控制 section 并发数为 3（`_SECTION_COUNT = 3`）
- 每个 section 提示词只携带该 section 的语义事实（`_section_brief_payload` 已实现）

**无需额外修改**。

---

## 3. 第二组：Cartoon 教学视频契约重构

### 3.1 后端拥有分镜骨架

**文件**: `server/app/shared/cartoon/planner.py`, `server/app/shared/cartoon/storyboard.md`

**现状分析**：
- `CartoonStoryboardDraft` 只要求 `title`、`course`、`scenes[{title, objective}]`
- `_scene_blueprint()` 已确定性分配 `teaching_function`、`layout`、`visual_kind`、`animation_mode`
- 但 `scene_compose.md` 仍向 LLM 传递这些字段（通过 `SceneComposePromptContext`）

**修改（planner.py）**：

删除 `_scene_specification()` 中对后端字段的传递：

```python
@staticmethod
def _scene_specification(scene: StoryboardScene) -> str:
    """只传递教学语义，不泄露内部场景身份。"""
    return json.dumps(
        {
            "title": scene.title,
            "objective": scene.objective,
            # 删除 teaching_function, layout, visual_kind, animation_mode
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
```

**修改（scene_compose.md）**：

删除固定分镜上下文中的字段说明，改为：

```markdown
## 分镜上下文

下面的分镜仅用于确定本幕讲什么。后端会合并 `id`、`teaching_function`、`layout` 等，**禁止在输出中重复**。

**教学语义**：
- `title`: 本幕标题
- `objective`: 本幕教学目标
```

### 3.2 用"讲解深度"彻底替代"设计时长/播放节奏"

**现状**：已正确实现。

- `LessonDepth` 枚举：`focused | standard | deep`
- `lesson_profile()` 返回 `scene_count`、`steps_per_scene`、`narration_min`、`narration_max`
- 视频时长完全由 TTS 计算决定，无空白停留

**验证点**：
- 前端 `resource.ts` 中 `cartoon` 配置只有 `visual_density`、`lesson_depth`、`voice`
- `agent_preferences.py` 中 cartoon 配置正确

### 3.3 收紧单幕 JSON

**文件**: `server/app/shared/cartoon/schemas.py`, `server/app/shared/cartoon/scene_compose.md`

**现状**：`scene_composition_contract()` 已根据场景动态生成 schema。

**修改（scene_compose.md）**：

明确字段白名单和禁用条件：

```markdown
## 字段白名单

`visual` 字段：
- `kind`: 必须等于当前 `visual_kind`
- `items`: 1～{{item_limit}} 个对象
- `edges`: 静态场景可选，动态场景禁止
- `states`: 动态场景必须 3～4 个，静态场景禁止
- `code`: 仅当 `visual_kind=code` 时允许且必须输出；其他画面禁止输出
- `formula`: 仅当 `visual_kind=formula` 时允许且必须输出；其他画面禁止输出

## 禁止字段

- `id` 在 `items`、`edges`、`states` 中：使用零基索引
- `teaching_function`、`layout`、`visual_kind`、`animation_mode`：后端分配
- 任何未在白名单中列出的字段
```

**验证（schemas.py）**：
- `SceneVisualDraft` 的 `code` 字段只在 `VisualKind.CODE` 时 `min_length=1`
- `formula` 字段只在 `VisualKind.FORMULA` 时 `min_length=1`

### 3.4 修复音频、字幕和节奏

**文件**: `server/app/shared/cartoon/planner.py`, `server/app/shared/cartoon/compiler.py`

**修改（planner.py）**：

缩短节奏参数：

```python
_TIMELINE_RHYTHM = {"lead": 100, "gap": 48, "settle": 120}
```

**修改（compiler.py）**：

修复字幕区域和对比度：

```css
.caption {
  position: absolute;
  z-index: 10;
  bottom: 40px;  /* 从 30px 增加到 40px，确保底部安全区 */
  left: 300px;
  right: 300px;
  /* ... 其他样式 ... */
}

.caption span {
  /* ... 现有样式 ... */
  background: rgba(255, 255, 255, 0.98);  /* 增强背景不透明度 */
  color: #101828;  /* 确保对比度 */
}
```

### 3.5 消除 HyperFrames 时间轴结构问题（场景拆分）

**文件**: `server/app/shared/cartoon/compiler.py`

**目标**：将单一 `index.html` 拆分为：

```text
index.html
└── compositions/
    ├── scene-01.html
    ├── scene-02.html
    └── ...
```

**修改（compiler.py）**：

```python
class CartoonCompiler:
    def compile(self, lesson: TeachingLesson, plan: CompositionPlan) -> str:
        """编译主组合文件，引用独立场景文件。"""
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        compositions_dir = self.output_dir / "compositions"
        compositions_dir.mkdir(exist_ok=True)

        # 编译每个独立场景文件
        scene_links = []
        for timed_scene in plan.scenes:
            scene = timed_scene.scene
            scene_filename = f"scene-{scene.id}.html"
            scene_path = compositions_dir / scene_filename
            scene_html = self._compile_scene_file(lesson, timed_scene)
            scene_path.write_text(scene_html, encoding="utf-8")
            scene_links.append(f'<link rel="composition" href="compositions/{scene_filename}">')

        # 主组合文件
        scenes_html = "\n".join(scene_links)
        return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1920, height=1080">
  <title>{html.escape(lesson.title, quote=True)}</title>
  <style>{_CSS}</style>
</head>
<body>
  <main id="root" data-composition-id="{COMPOSITION_ID}" data-start="0" data-duration="{_seconds(plan.total_duration_ms)}" data-width="1920" data-height="1080">
    <div class="composition-background" aria-hidden="true"></div>
    {scenes_html}
    {_captions_html(plan)}
    {_audio_html(plan)}
    <footer data-slot="progress"><span data-progress-fill></span></footer>
  </main>
  <script src="assets/vendor/gsap.min.js"></script>
  <script>{_diagram_runtime(lesson)}{_motion_runtime()}const tl=gsap.timeline({{paused:true}});{_timeline(plan)}window.__timelines['{COMPOSITION_ID}']=tl;</script>
</body>
</html>'''

    def _compile_scene_file(self, lesson: TeachingLesson, timed_scene: TimedScene) -> str:
        """编译单个场景 HTML 文件，包含独立的动画时间轴。"""
        scene = timed_scene.scene
        scene_html = _scene_html(timed_scene, len(lesson.scenes), lesson.course)
        return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <style>{_SCENE_CSS}</style>
</head>
<body>
  {scene_html}
  <script src="../assets/vendor/gsap.min.js"></script>
  <script>
    (function() {{
      const tl_{scene.id} = gsap.timeline({{paused: true}});
      {_scene_timeline_scene(timed_scene)}
      window.__sceneTimelines = window.__sceneTimelines || {{}};
      window.__sceneTimelines['{scene.id}'] = tl_{scene.id};
    }})();
  </script>
</body>
</html>'''

    def _scene_timeline_scene(self, timed_scene: TimedScene) -> str:
        """生成单个场景的时间轴代码。"""
        lines = []
        scene_id = timed_scene.scene.id
        start = _seconds(timed_scene.start_ms)
        selector = f'[data-scene-id="{scene_id}"]'

        lines.append(f"tl.set('{selector}', {{autoAlpha: 1}}, 0);")
        lines.append(f"tl.from('{selector} .scene-header > *', {{y: 22, autoAlpha: 0, duration: 0.38, stagger: 0.06, ease: 'power3.out'}}, 0);")
        # ... 其余时间轴逻辑

        return "\n".join(lines)

    def write(self, lesson: TeachingLesson, plan: CompositionPlan, output_dir: Path) -> Path:
        """写入组合文件和独立场景文件。"""
        self._validate_audio_assets(plan, output_dir)
        self.output_dir = output_dir
        content = self.compile(lesson, plan)
        path = output_dir / "index.html"
        path.write_text(content, encoding="utf-8")
        return path
```

**新增场景专用 CSS**：

```python
_SCENE_CSS = r'''
.scene {
  position: absolute;
  inset: 0;
  /* ... 与现有场景样式一致 ... */
}
/* 其余场景样式从 _CSS 中提取 */
'''
```

---

## 4. 第三组：删除旧配置与完成前后端收口

### 4.1 全仓删除 `pace`、`target_duration` 相关字段

**现状**：前端代码中已无这些字段。

**验证点**：
- `server/app/resource/agent_preferences.py`：cartoon 配置只有 `visual_density`、`lesson_depth`
- `src/features/resource/model/resource.ts`：`cartoon` 配置字段正确
- `src/features/resource/model/catalog.ts`：`SCENARIO_DEFAULTS` 中所有场景预设使用 `lesson_depth`

**无需修改**，仅验证。

### 4.2 不做旧缓存兼容

**现状**：缓存版本号为 `v2`、`v3`（`useGeneration.ts` 中）。

**策略**：保持现有版本号，旧 `sessionStorage` 自然失效。

### 4.3 资源运行页展示实际阶段

**现状**：前端从后端事件 `phase` 字段读取并展示。

**无需修改**。

---

## 5. 第四组：验证与清理

### 5.1 编译验证

```bash
cd /Users/apple/Code/software/server
uv run python -m compileall -q app/shared/ppt app/shared/cartoon app/resource

cd /Users/apple/Code/software
npm run build
```

### 5.2 手工验证（完整范围）

#### PPT 验证

生成一份 PPT（任意主题），检查：

1. **首次 JSON 不依赖 repair**
2. **没有因 `visual/nodes/metrics` 格式不一致失败**
3. **页面下半部分留白问题是否解决**
   - 内容页主内容区占可用高度 70% 以上
   - 图表、代码区填充主舞台
   - 只有封面和章节页允许显著留白

#### Cartoon 验证

生成一份 `standard` 深度的 Cartoon，检查：

1. **首次 storyboard 不因动态幕数量失败**
2. **最终视频无音频重叠**（`AUDIO_GUARD_MS` 约束）
3. **字幕不遮挡结论，底部对比度合格**
   - 字幕区域独立底部安全区
   - 本幕结论显示在主舞台总结卡中
4. **HyperFrames lint 无警告**
   - 无 `duplicate_audio_track`
   - 无 `timeline_track_too_dense`（场景拆分后）
5. **`focused / standard / deep` 内容深度和时长有明显差异**

### 5.3 清理旧代码

删除：
- 任何仍存在的"兼容旧 JSON 格式"的转换分支
- 已失去引用的旧 schema 字段
- 无消费的字段（如 Cartoon 中未被使用的字段）

---

## 6. 实施顺序

1. **PPT 模型层修改**（`models.py`）
2. **PPT 渲染层修改**（`html.py`）
3. **PPT 生成器层修改**（`generator.py`）
4. **Cartoon planner 修改**（`planner.py`）
5. **Cartoon compiler 修改**（`compiler.py`）
6. **Cartoon 提示词清理**（`storyboard.md`, `scene_compose.md`）
7. **编译验证**
8. **手工验证**
9. **清理旧代码**

---

## 7. 风险与缓解

### 7.1 场景拆分可能影响 HyperFrames 渲染

**风险**：HyperFrames 可能不支持 `<link rel="composition">` 方式引用子组合。

**缓解**：如果 HyperFrames 不支持，改用内联方式但拆分时间轴逻辑：

```html
<!-- index.html -->
<main>
  <section id="scene-01" data-scene-file="compositions/scene-01.html">...</section>
</main>
```

### 7.2 CSS 布局变更可能影响现有 PPT 视觉

**风险**：新 CSS 规则可能导致已生成的 PPT 视觉不一致。

**缓解**：此设计针对新生成的 PPT，不影响已生成的静态 HTML。

---

## 8. 成功标准

1. PPT 首次 JSON 校验成功率 > 95%
2. PPT 页面下半部分留白问题解决
3. Cartoon 首次 storyboard 校验成功率 > 95%
4. Cartoon 视频无音频重叠
5. Cartoon 字幕对比度合格，不遮挡结论
6. HyperFrames lint 无 `duplicate_audio_track` 和 `timeline_track_too_dense` 警告
7. 无旧契约兼容层代码残留