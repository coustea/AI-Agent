<template>
  <main class="blueprint-canvas">
    <!-- Top Nav -->
    <div class="top-nav">
      <div class="brand">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        <span>学习路径规划</span>
      </div>
      <button class="history-btn" @click="router.push('/path-planner/history')">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
        推演记录
      </button>
    </div>

    <!-- Main Workspace Grid -->
    <div class="workspace-grid">
      <!-- Left Column: Guidance & Suggestions -->
      <section class="guidance-panel">
        <div class="header-group">
          <span class="section-badge">Path Planner</span>
          <h1>反向推演最优知识路径</h1>
          <p>输入你的目标与基础，AI 会根据你的背景动态定制多阶段学习路径，并生成对应的学习课件与阶段测验。</p>
        </div>

        <div class="recommendations">
          <h3>热门学习话题</h3>
          <div class="suggestion-list">
            <button 
              class="suggestion-card" 
              type="button" 
              @click="applySuggestion('Vue3 源码解析', '深入理解 Vue3 响应式原理与编译器源码')"
            >
              <strong>深入理解 Vue3 源码</strong>
              <span>深入剖析底层响应式与编译优化机制</span>
            </button>
            <button 
              class="suggestion-card" 
              type="button" 
              @click="applySuggestion('K8s 自动化运维', '掌握 Kubernetes 集群的自动化运维与高可用部署')"
            >
              <strong>Kubernetes 自动化运维</strong>
              <span>面向生产环境的容器编排与监控体系</span>
            </button>
            <button 
              class="suggestion-card" 
              type="button" 
              @click="applySuggestion('Rust 游戏引擎', '从零构建一个基于 Rust 语言的 WebAssembly 游戏引擎')"
            >
              <strong>Rust + WebAssembly 游戏引擎</strong>
              <span>结合 Rust 安全特性与 Wasm 高性能开发</span>
            </button>
          </div>
        </div>
      </section>

      <!-- Center Flat Vertical Line -->
      <div class="center-divider"></div>

      <!-- Right Column: Structured Config Form -->
      <section class="config-panel">
        <div class="config-section">
          <h2>[ 01 // 学习意图 ]</h2>
          
          <div class="form-item">
            <label>学习主题 (Topic)</label>
            <input 
              v-model="topic" 
              type="text" 
              placeholder="例如：FastAPI / Kubernetes / Vue3"
              maxlength="40"
            />
          </div>

          <div class="form-item">
            <label>终极学习目标 (Goal)</label>
            <textarea 
              ref="textareaRef"
              v-model="goal" 
              placeholder="例如：系统掌握 FastAPI 高并发架构设计与部署，能独立维护生产级系统"
              rows="3"
              maxlength="150"
              @input="autoResize"
            ></textarea>
          </div>
        </div>

        <div class="config-section">
          <h2>[ 02 // 学习策略 ]</h2>

          <div class="form-item">
            <label>当前已掌握的基础 (Prerequisites)</label>
            <div class="tag-input-container">
              <span 
                v-for="tag in prerequisites" 
                :key="tag" 
                class="prereq-tag"
              >
                {{ tag }}
                <button type="button" @click="removePrerequisite(tag)">×</button>
              </span>
              <input 
                v-model="newPrerequisite"
                type="text" 
                placeholder="+ 输入基础回车添加"
                @keydown.enter.prevent="addPrerequisite"
              />
            </div>
          </div>

          <div class="form-item">
            <label>学习难度倾向 (Preferences)</label>
            <div class="difficulty-slider">
              <button 
                type="button"
                :class="{ active: difficulty === 'beginner' }" 
                @click="difficulty = 'beginner'"
              >
                零基础入门
              </button>
              <button 
                type="button"
                :class="{ active: difficulty === 'intermediate' }" 
                @click="difficulty = 'intermediate'"
              >
                中级进阶
              </button>
              <button 
                type="button"
                :class="{ active: difficulty === 'advanced' }" 
                @click="difficulty = 'advanced'"
              >
                极客专家
              </button>
            </div>
          </div>

          <div class="form-item inline-switch">
            <div class="switch-info">
              <strong>融合个人动态画像</strong>
              <span>智能融入您现有的 8 维用户画像数据</span>
            </div>
            <button 
              type="button"
              class="switch-btn" 
              :class="{ active: useProfile }" 
              @click="useProfile = !useProfile"
            >
              {{ useProfile ? '已开启' : '已关闭' }}
            </button>
          </div>
        </div>

        <div class="action-item">
          <button 
            class="submit-btn" 
            :disabled="isSubmitting"
            @click="handleSubmit"
          >
            <span v-if="!isSubmitting">开始生成学习路径图谱</span>
            <span v-else class="loading-spin">
              <svg class="spinner" viewBox="0 0 50 50">
                <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
              </svg>
              构建中...
            </span>
          </button>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

const router = useRouter()

// 属性数据绑定
const topic = ref('')
const goal = ref('')
const prerequisites = ref<string[]>([])
const newPrerequisite = ref('')
const difficulty = ref<'beginner' | 'intermediate' | 'advanced'>('intermediate')
const useProfile = ref(true)

const isSubmitting = ref(false)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// 文本框自动自适应高度
const autoResize = () => {
  if (!textareaRef.value) return
  textareaRef.value.style.height = 'auto'
  const scrollHeight = textareaRef.value.scrollHeight
  textareaRef.value.style.height = `${Math.min(scrollHeight, 150)}px`
}

// 应用模板建议
const applySuggestion = (selectedTopic: string, selectedGoal: string) => {
  topic.value = selectedTopic
  goal.value = selectedGoal
  nextTick(() => {
    textareaRef.value?.focus()
    autoResize()
  })
}

// 添加入参 Prerequisite 标签
const addPrerequisite = () => {
  const val = newPrerequisite.value.trim()
  if (!val) return
  if (prerequisites.value.includes(val)) {
    newPrerequisite.value = ''
    return
  }
  prerequisites.value.push(val)
  newPrerequisite.value = ''
}

// 移除 Prerequisite 标签
const removePrerequisite = (tag: string) => {
  prerequisites.value = prerequisites.value.filter(item => item !== tag)
}

const handleSubmit = async () => {
  const finalTopic = topic.value.trim()
  const finalGoal = goal.value.trim()

  if (!finalTopic) {
    toast.warning('请先输入学习主题')
    return
  }
  if (!finalGoal) {
    toast.warning('请先输入终极学习目标')
    return
  }

  isSubmitting.value = true

  // 稍微延迟，提升系统运行仪式感
  await new Promise(resolve => setTimeout(resolve, 600))

  router.push({
    path: `/path-planner/overview/new`,
    query: {
      topic: finalTopic,
      goal: finalGoal,
      current_knowledge: JSON.stringify(prerequisites.value),
      difficulty: difficulty.value,
      use_profile: useProfile.value ? 'true' : 'false'
    }
  })
}
</script>

<style scoped>
/* 纯白 glacier grid 基础背景 */
.blueprint-canvas {
  position: relative;
  min-height: calc(100vh - 64px);
  background-color: #ffffff;
  background-image:
    radial-gradient(circle at 15% 50%, rgba(70, 184, 180, 0.03) 0%, transparent 50%),
    radial-gradient(circle at 85% 30%, rgba(70, 184, 180, 0.03) 0%, transparent 50%),
    linear-gradient(rgba(70, 184, 180, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(70, 184, 180, 0.02) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 30px 30px, 30px 30px;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

.top-nav {
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  border-bottom: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text);
  font-weight: 800;
  font-size: 1.05rem;
  letter-spacing: 0.02em;
}

.brand svg {
  color: var(--color-primary);
}

.history-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: 8px 18px;
  border-radius: 0px; /* 严格直角 */
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-btn:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border-color: var(--color-primary);
}

/* 分栏大布局 */
.workspace-grid {
  flex: 1;
  display: grid;
  grid-template-cols: 1fr 1px 1.1fr;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 40px;
  gap: 40px;
  align-items: start;
}

.center-divider {
  background-color: var(--color-border-light);
  width: 1px;
  align-self: stretch;
}

/* 左侧引导栏 */
.guidance-panel {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding-top: 10px;
}

.header-group .section-badge {
  display: inline-block;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 0.75rem;
  font-weight: 800;
  padding: 4px 10px;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.header-group h1 {
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--color-text-strong);
  line-height: 1.25;
  margin: 0 0 16px 0;
  letter-spacing: -0.02em;
}

.header-group p {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
}

.recommendations h3 {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin: 0 0 16px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-card {
  text-align: left;
  background: #ffffff;
  border: 1px solid var(--color-border);
  padding: 16px;
  border-radius: 0px; /* 直角 */
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.suggestion-card:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-primary);
  transform: translateY(-1px);
}

.suggestion-card strong {
  font-size: 0.95rem;
  color: var(--color-text);
  font-weight: 700;
}

.suggestion-card span {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

/* 右侧配置栏 */
.config-panel {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding-top: 10px;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.config-section h2 {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-primary-text);
  margin: 0;
  font-weight: bold;
  letter-spacing: 0.05em;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.form-item input[type="text"],
.form-item textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 0px; /* 严格直角 */
  padding: 12px;
  font-size: 0.9rem;
  color: var(--color-text);
  background: #ffffff;
  outline: none;
  font-family: var(--font-sans);
  transition: all 0.2s ease;
}

.form-item input[type="text"]:focus,
.form-item textarea:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

/* 标签选择器 */
.tag-input-container {
  border: 1px solid var(--color-border);
  background: #ffffff;
  padding: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.tag-input-container:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.prereq-tag {
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary-text);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 3px 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 0px; /* 直角 */
  font-family: var(--font-mono);
}

.prereq-tag button {
  border: none;
  background: transparent;
  color: var(--color-primary-text);
  cursor: pointer;
  font-weight: 800;
  font-size: 0.9rem;
  padding: 0;
  line-height: 1;
}

.tag-input-container input {
  border: none !important;
  box-shadow: none !important;
  outline: none;
  padding: 4px;
  font-size: 0.85rem;
  flex: 1;
  min-width: 120px;
}

/* 难度切换胶囊滑块 */
.difficulty-slider {
  display: grid;
  grid-template-cols: 1fr 1fr 1fr;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  padding: 3px;
}

.difficulty-slider button {
  border: none;
  background: transparent;
  padding: 10px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 0px; /* 直角 */
}

.difficulty-slider button.active {
  background: #ffffff;
  color: var(--color-primary-text);
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(70, 184, 180, 0.08);
}

/* 开关选择器 */
.inline-switch {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--color-border);
  padding: 14px;
  background: var(--color-surface);
}

.switch-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.switch-info strong {
  font-size: 0.85rem;
  color: var(--color-text);
}

.switch-info span {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.switch-btn {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: 6px 14px;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  border-radius: 0px; /* 直角 */
  transition: all 0.2s ease;
}

.switch-btn.active {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border-color: var(--color-primary);
}

/* 按钮与进度 */
.action-item {
  margin-top: 10px;
}

.submit-btn {
  width: 100%;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  color: white;
  border: none;
  padding: 14px;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 0px; /* 直角 */
  box-shadow: 0 4px 12px rgba(70, 184, 180, 0.15);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(70, 184, 180, 0.25);
}

.submit-btn:disabled {
  opacity: 0.8;
  cursor: not-allowed;
}

.loading-spin {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.spinner {
  animation: rotate 2s linear infinite;
  width: 18px;
  height: 18px;
}

.spinner .path {
  stroke: white;
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
}

@keyframes rotate { 100% { transform: rotate(360deg); } }
@keyframes dash {
  0% { stroke-dasharray: 1, 150; stroke-dashoffset: 0; }
  50% { stroke-dasharray: 90, 150; stroke-dashoffset: -35; }
  100% { stroke-dasharray: 90, 150; stroke-dashoffset: -124; }
}

@media (max-width: 1024px) {
  .workspace-grid {
    grid-template-cols: 1fr;
    gap: 30px;
  }
  .center-divider {
    display: none;
  }
}
</style>