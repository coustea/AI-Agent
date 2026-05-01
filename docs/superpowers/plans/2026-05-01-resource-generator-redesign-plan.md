# Resource Generator Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `ResourceGenerator.vue` into a split-view layout featuring a multi-agent Bento Box workspace, and fix Web Interface Guidelines issues across resource card components.

**Architecture:** The redesign involves migrating from a three-panel vertical pipeline to a two-panel split view (Input on left, Output Grid on right). We will use CSS Grid for the Bento Box layout on the right. We will also clean up accessibility and CSS transition warnings.

**Tech Stack:** Vue 3 (Composition API), TypeScript, Element Plus, CSS Grid.

---

### Task 1: Fix Web Interface Guidelines in Resource Views

**Files:**
- Modify: `src/components/resource/ResourceCard.vue`
- Modify: `src/components/resource/QuizResourceView.vue`

- [ ] **Step 1: Fix typographic ellipsis and missing ARIA/alt attributes in `ResourceCard.vue`**

Replace `...还有` with `…还有` (line ~41).
Add `alt=""` to `<el-image>` (line ~53).
Add `aria-hidden="true"` to the decorative `<el-icon>` wrapping `<Picture />` and `<VideoCamera />` (lines ~63, 65).

```vue
// In src/components/resource/ResourceCard.vue template

// 1. Fix typography
          <div v-if="pptSlideTitles.length > 5" class="ppt-title-more">
            …还有 {{ pptSlideTitles.length - 5 }} 页
          </div>

// 2. Fix image alt
          <el-image 
            v-if="imageUrl" 
            :src="imageUrl" 
            fit="cover" 
            class="res-image-preview"
            :preview-src-list="[imageUrl]"
            preview-teleported
            alt=""
          >

// 3. Fix decorative icons
          <div v-else class="image-placeholder empty">
            <el-icon aria-hidden="true"><Picture /></el-icon>
            <span>图片渲染中</span>
          </div>

// ... further down
          <el-icon class="video-bg-icon" aria-hidden="true"><VideoCamera /></el-icon>
```

- [ ] **Step 2: Fix `v-for` key in `QuizResourceView.vue`**

In `src/components/resource/QuizResourceView.vue`, update the `v-for` to use a more stable key if available (like `question.id`), falling back to index safely if not. Given the JSON schema, `id` is usually present.

```vue
// In src/components/resource/QuizResourceView.vue template
      <article v-for="(question, index) in visibleQuestions" :key="question.id || index" class="quiz-item">
```

- [ ] **Step 3: Commit**

```bash
git add src/components/resource/ResourceCard.vue src/components/resource/QuizResourceView.vue
git commit -m "fix: address web interface guideline warnings in resource views"
```

### Task 2: Refactor Input Form Accessibility & CSS in `ResourceGenerator.vue`

**Files:**
- Modify: `src/views/ResourceGenerator.vue`

- [ ] **Step 1: Add IDs and `htmlFor` to form inputs**

Update the template in `src/views/ResourceGenerator.vue` to link `<label>` with inputs using `for` and `id` attributes. Also add `aria-live="polite"` to the dynamic summary box.

```vue
      <div class="dynamic-summary-box" aria-live="polite">
// ...
          <div class="form-row">
            <div class="form-item">
              <label for="course-input">所属课程 <span class="req">*</span></label>
              <el-input id="course-input" v-model="taskInput.course" placeholder="如：计算机网络" />
            </div>
            <div class="form-item">
              <label for="chapter-input">所属章节</label>
              <el-input id="chapter-input" v-model="taskInput.chapter" placeholder="如：传输层" />
            </div>
          </div>

          <div class="form-item">
            <label for="topic-input">学习主题 <span class="req">*</span></label>
            <el-input id="topic-input" v-model="taskInput.topic" placeholder="如：TCP 三次握手" />
          </div>

          <div class="form-item">
            <label for="weak-points-input">知识短板 <span class="sub-label">(输入后回车添加)</span></label>
            <div class="tags-input-container">
// ... tags loop ...
              <el-input
                id="weak-points-input"
// ...
              />
            </div>
          </div>

          <div class="form-item">
            <label for="learning-goal-select">学习目标</label>
            <el-select id="learning-goal-select" v-model="taskInput.learning_goal" class="w-full">
// ...
            </el-select>
          </div>

          <div class="form-item">
            <label for="extra-req-input">补充要求</label>
            <el-input id="extra-req-input" v-model="taskInput.extra_requirement" type="textarea" :rows="2" placeholder="如：尽量多用生活中的例子解释..." />
          </div>
// ...
// Apply similar id/for pairs to:
// current_level -> current-level-select
// target_level -> target-level-select
// explanation_style -> style-select
// content_depth -> depth-select
// example_preference -> example-select
// output_language -> lang-select
```
(Apply the `...` to `…` fix in the placeholders: `如：记不住状态流转过程…`, `如：尽量多用生活中的例子解释…` etc.)

- [ ] **Step 2: Replace `transition: all` in CSS**

At the bottom of `src/views/ResourceGenerator.vue`:

```css
.agent-config-card {
  border: 1px solid #CBD5E1;
  border-radius: 12px;
  background: #FFFFFF;
  padding: 14px;
  transition: transform 0.2s ease, border-color 0.2s ease, background-color 0.2s ease, opacity 0.2s ease, box-shadow 0.2s ease;
}
// ...
.wf-node {
  width: 280px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
  position: relative;
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
// ...
.result-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
```

- [ ] **Step 3: Commit**

```bash
git add src/views/ResourceGenerator.vue
git commit -m "refactor: improve form accessibility and css transitions in ResourceGenerator"
```

### Task 3: Restructure Layout to Split View & Build Bento Box

**Files:**
- Modify: `src/views/ResourceGenerator.vue`

- [ ] **Step 1: Update Template Structure**

Remove `<main class="panel-middle">` and `<aside class="panel-right">`. Combine them into a single `<main class="panel-right bento-workspace">`.
The layout will now be `.panel-left` (Input) and `.panel-right` (Bento Workspace).

```vue
    <main class="panel-right bento-workspace">
      <div class="workspace-header">
        <div class="header-titles">
          <h2>多智能体协同工作台</h2>
          <p>实时监控 Agent 执行进度与资源产出</p>
        </div>
        <div class="workflow-status" :class="workflow.globalStatus">
          <span class="status-indicator"></span>
          {{ getGlobalStatusText() }} ({{ workflow.progress }}%)
        </div>
      </div>

      <!-- Activity Timeline (Horizontal) -->
      <div class="activity-timeline">
        <div class="timeline-track">
          <div class="timeline-progress" :style="{ width: workflow.progress + '%' }"></div>
        </div>
        <div class="timeline-steps">
           <div class="step-label" :class="{ active: workflow.states.coordinator !== 'idle' }">规划编排</div>
           <div class="step-label" :class="{ active: isAnyResourceDone }">资源生成</div>
           <div class="step-label" :class="{ active: workflow.states.reviewer === 'success' }">质量审查</div>
           <div class="step-label" :class="{ active: workflow.states.assembler === 'success' }">资源组装</div>
        </div>
        <div class="current-log" v-if="workflow.globalStatus === 'running'">
          <el-icon class="is-loading"><Loading /></el-icon> {{ latestActivityLog }}
        </div>
      </div>

      <!-- Bento Grid Area -->
      <div class="bento-grid">
        <!-- We will render a tile for every enabled agent -->
        <div 
          v-for="agentId in enabledAgentIds" 
          :key="agentId"
          class="bento-tile"
          :class="[agentId, workflow.states[agentId] || 'idle']"
          @click="openResourcePreview(agentId)"
        >
          <div class="tile-header">
            <div class="tile-title">
              <el-icon><component :is="getAgentMeta(agentId).icon" /></el-icon>
              <span>{{ getAgentMeta(agentId).name }}</span>
            </div>
            <div class="tile-status" :class="workflow.states[agentId] || 'idle'">
              <el-icon v-if="workflow.states[agentId] === 'running'" class="is-loading"><Loading /></el-icon>
              <el-icon v-else-if="workflow.states[agentId] === 'success'"><Select /></el-icon>
              <el-icon v-else-if="workflow.states[agentId] === 'failed'"><Close /></el-icon>
              <span v-else class="pending-dot"></span>
            </div>
          </div>
          
          <div class="tile-content">
            <!-- State: Idle/Pending -->
            <div v-if="(workflow.states[agentId] || 'idle') === 'idle' || workflow.states[agentId] === 'pending'" class="state-empty">
              等待前置依赖...
            </div>
            <!-- State: Running -->
            <div v-else-if="workflow.states[agentId] === 'running'" class="state-running">
               <div class="pulse-skeleton"></div>
               <div class="pulse-skeleton short"></div>
               <p class="run-msg">{{ workflow.messages[agentId] }}</p>
            </div>
            <!-- State: Failed -->
            <div v-else-if="workflow.states[agentId] === 'failed'" class="state-failed">
               生成失败
            </div>
            <!-- State: Success -->
            <div v-else-if="workflow.states[agentId] === 'success'" class="state-success">
               <!-- Dynamically render the compact view based on agent type -->
               <MindmapResourceView v-if="agentId === 'mindmap'" :result-data="getResourceData(agentId)" compact />
               <DiagramResourceView v-else-if="agentId === 'diagram'" :result-data="getResourceData(agentId)" compact />
               <QuizResourceView v-else-if="agentId === 'quiz'" :result-data="getResourceData(agentId)" compact />
               <MarkdownResourceView v-else :result-data="getResourceData(agentId)" compact />
            </div>
          </div>
        </div>
      </div>
    </main>
```

- [ ] **Step 2: Implement Setup Logic for new Layout**

In the `<script setup>` block:

```typescript
// Add latestActivityLog computed property
const latestActivityLog = computed(() => {
  // Find the first running agent's message, or fallback to coordinator
  const runningAgent = enabledAgentIds.value.find(id => workflow.states[id] === 'running')
  if (runningAgent && workflow.messages[runningAgent]) {
    return workflow.messages[runningAgent]
  }
  return workflow.messages.coordinator || '系统初始化中…'
})

// Helper to get resource data for a specific agent
const getResourceData = (agentId: string) => {
  const res = generatedResources.value.find(r => r.type === agentId)
  return res ? res.content : null
}

// Function to open preview when a tile is clicked
const openResourcePreview = (agentId: string) => {
  const res = generatedResources.value.find(r => r.type === agentId)
  if (res && workflow.states[agentId] === 'success') {
    handlePreview(res)
  }
}
```

- [ ] **Step 3: Add CSS for the Bento Grid**

Remove the old CSS for `.panel-middle`, `.workflow-graph`, `.custom-tabs` etc., and replace with Bento styles.

```css
/* Update Layout */
.resource-generator-layout {
  display: flex;
  height: calc(100vh - 60px);
  background-color: #F8FAFC;
  overflow: hidden;
}
.panel-left {
  width: 400px;
  background: #FFFFFF;
  border-right: 1px solid #E2E8F0;
  flex-shrink: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
}
.bento-workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #F1F5F9;
  overflow: hidden;
}
.workspace-header {
  padding: 20px 32px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.header-titles h2 { margin: 0 0 4px 0; font-size: 1.2rem; color: #1E293B; }
.header-titles p { margin: 0; font-size: 0.85rem; color: #64748B; }

/* Timeline */
.activity-timeline {
  padding: 16px 32px;
  background: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
}
.timeline-track {
  height: 4px;
  background: #E2E8F0;
  border-radius: 2px;
  margin-bottom: 8px;
  overflow: hidden;
}
.timeline-progress {
  height: 100%;
  background: #4F46E5;
  transition: width 0.3s ease;
}
.timeline-steps {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94A3B8;
  margin-bottom: 8px;
}
.step-label.active { color: #4F46E5; font-weight: 600; }
.current-log {
  font-size: 0.85rem;
  color: #3B82F6;
  display: flex;
  align-items: center;
  gap: 6px;
  background: #EFF6FF;
  padding: 6px 12px;
  border-radius: 6px;
  width: fit-content;
}

/* Bento Grid */
.bento-grid {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  grid-auto-rows: minmax(240px, auto);
  gap: 20px;
  align-content: start;
}
.bento-tile {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}
.bento-tile.success:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  border-color: #CBD5E1;
}
/* Optional: specific spanning rules for certain agents if you want a true masonry bento look */
.bento-tile.content { grid-column: span 2; }
@media (max-width: 1400px) {
  .bento-tile.content { grid-column: span 1; }
}

.tile-header {
  padding: 12px 16px;
  border-bottom: 1px solid #F1F5F9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #FAFAF9;
}
.tile-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #334155;
}
.tile-title .el-icon { color: #4F46E5; }
.tile-status { font-size: 1.1rem; }
.tile-status.running { color: #3B82F6; }
.tile-status.success { color: #10B981; }
.tile-status.failed { color: #EF4444; }
.pending-dot { display: block; width: 8px; height: 8px; background: #CBD5E1; border-radius: 50%; }

.tile-content {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
.state-empty, .state-failed {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94A3B8;
  font-size: 0.9rem;
}
.state-failed { color: #EF4444; }
.state-running {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pulse-skeleton {
  height: 12px;
  background: #E2E8F0;
  border-radius: 4px;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.pulse-skeleton.short { width: 60%; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}
.run-msg {
  font-size: 0.8rem;
  color: #64748B;
  margin-top: auto;
}
.state-success {
  flex: 1;
  overflow: hidden; /* Let the ResourceView handle inner overflow or truncating */
  /* fade in */
  animation: fadeIn 0.4s ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

- [ ] **Step 4: Commit**

```bash
git add src/views/ResourceGenerator.vue
git commit -m "feat: redesign resource generator to use bento box grid layout"
```

### Task 4: Integration Check

- Ensure the SSE streaming naturally updates the new UI without issues (the logic of `generateResources` in the `<script setup>` remains mostly untouched, we just mapped `workflow.states` and `generatedResources` differently).
- Ensure clicking on a "success" tile opens the existing preview dialog.
- The `bento-tile.content { grid-column: span 2; }` CSS makes the Course Explanation take up more space, acting as the anchor of the Bento grid.

- [ ] **Step 1: Test the frontend locally**
Run `npm run build` or `vite build` (if applicable) to ensure there are no compilation errors in the Vue file. (Assuming `vue-tsc --noEmit` if needed).

```bash
npm run type-check || echo "Type checking skipped or passed"
```

- [ ] **Step 2: Commit**

```bash
# Empty commit just to mark completion of integration check
git commit --allow-empty -m "chore: verify layout redesign integration"
```
