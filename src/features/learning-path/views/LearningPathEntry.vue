<template>
  <main class="blueprint-canvas">
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

    <div class="canvas-center">
      <div class="topology-wrapper">
        <svg class="topology-lines" viewBox="0 0 800 600" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#4f46e5" />
              <stop offset="50%" stop-color="#0ea5e9" />
              <stop offset="100%" stop-color="#3b82f6" />
            </linearGradient>
          </defs>
          <path d="M 250,300 C 350,300 400,300 500,300" class="ghost-line main-line" />
          <path d="M 150,150 C 250,150 350,300 500,300" class="ghost-line" />
          <path d="M 150,450 C 250,450 350,300 500,300" class="ghost-line" />
        </svg>

        <div class="ghost-nodes">
          <div class="ghost-node" style="top: 150px; left: 150px; transform: translate(-100%, -50%);">
            <span class="pulse-dot"></span>
            <div class="ghost-text">基础原理依赖<br><small>AI 自动推导中...</small></div>
          </div>
          <div class="ghost-node" style="top: 300px; left: 250px; transform: translate(-100%, -50%);">
            <span class="pulse-dot"></span>
            <div class="ghost-text">核心组件分支<br><small>计算图谱权重...</small></div>
          </div>
          <div class="ghost-node" style="top: 450px; left: 150px; transform: translate(-100%, -50%);">
            <span class="pulse-dot"></span>
            <div class="ghost-text">先决环境准备<br><small>匹配个体熟练度...</small></div>
          </div>
        </div>

        <div class="destination-node" :class="{ 'is-focused': isFocused, 'has-input': goal.trim().length > 0 }">
          <div class="node-label">
            <span class="badge">终极目标</span>
            <h3>你想达到什么高度？</h3>
          </div>

          <div class="input-wrapper">
            <textarea
              ref="textareaRef"
              v-model="goal"
              class="destination-input"
              placeholder="例如：系统掌握 FastAPI 高并发架构与部署..."
              :maxlength="maxLength"
              @focus="isFocused = true"
              @blur="isFocused = false"
              @input="autoResize"
              @keydown.enter.exact.prevent="handleSubmit"
              rows="2"
            />
            <div class="input-footer" v-show="isFocused || goal.trim().length > 0">
              <span class="hint-text">↵ 提交 / Shift + ↵ 换行</span>
              <span class="char-count" :class="{ 'is-near-limit': goal.length > maxLength * 0.9 }">
                {{ goal.length }} / {{ maxLength }}
              </span>
            </div>
          </div>

          <transition name="fade-slide">
            <div class="suggestions" v-if="isFocused && goal.trim().length === 0">
              <span class="suggestion-tag" @click.stop="applySuggestion('从零构建一个基于 Rust 的 WebAssembly 游戏引擎')">Rust + Wasm 引擎</span>
              <span class="suggestion-tag" @click.stop="applySuggestion('掌握 Kubernetes 集群的自动化运维与监控')">K8s 自动化运维</span>
              <span class="suggestion-tag" @click.stop="applySuggestion('深入理解 Vue3 响应式原理与编译器源码')">Vue3 源码解析</span>
            </div>
          </transition>

          <transition name="fade">
            <div class="node-footer" v-if="goal.trim().length > 0">
              <button 
                class="reverse-btn" 
                :class="{ 'is-loading': isSubmitting }"
                :disabled="isSubmitting"
                @click="handleSubmit"
              >
                <span class="btn-text" v-if="!isSubmitting">生成学习路径图谱</span>
                <span class="btn-text" v-else>
                  <svg class="spinner" viewBox="0 0 50 50"><circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle></svg>
                  构建中...
                </span>
              </button>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <div class="canvas-hints" v-if="!isFocused && !goal">
      <p>输入你的终极学习目标，AI 将反向逆推所需的知识节点，为你构建一条可执行的最优学习图谱。</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const goal = ref('')
const isFocused = ref(false)
const isSubmitting = ref(false)
const maxLength = 100 // 目标长度限制
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// 文本框自动调整高度
const autoResize = () => {
  if (!textareaRef.value) return
  textareaRef.value.style.height = 'auto'
  // 设置最大高度限制，防止超出卡片
  const scrollHeight = textareaRef.value.scrollHeight
  textareaRef.value.style.height = `${Math.min(scrollHeight, 120)}px`
}

// 应用快捷建议
const applySuggestion = (text: string) => {
  goal.value = text
  nextTick(() => {
    textareaRef.value?.focus()
    autoResize()
  })
}

const handleSubmit = async () => {
  const value = goal.value.trim()
  if (!value) {
    ElMessage.warning('请先输入终极学习目标')
    textareaRef.value?.focus()
    return
  }

  isSubmitting.value = true

  // 模拟极短的计算延迟，增强 AI "思考" 的仪式感
  await new Promise(resolve => setTimeout(resolve, 600))

  router.push({
    path: `/path-planner/overview/new`,
    query: { goal: value }
  })
  
  // 如果需要保持本页状态，这里可以不置为 false；因为直接路由跳转了
  // isSubmitting.value = false 
}
</script>

<style scoped>
/* 原有的全局和画布样式保持不变 */
.blueprint-canvas {
  position: relative;
  min-height: calc(100vh - 64px);
  background-color: var(--color-bg);
  background-image:
    radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 50% 80%, rgba(14, 165, 233, 0.08) 0%, transparent 50%),
    linear-gradient(rgba(79, 70, 229, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79, 70, 229, 0.03) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 100% 100%, 30px 30px, 30px 30px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.blueprint-canvas::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(circle at center, transparent 30%, var(--color-bg) 100%);
  pointer-events: none;
  z-index: 0;
}

.top-nav {
  position: relative;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 40px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text);
  font-weight: 800;
  font-size: 1.1rem;
  letter-spacing: 0.05em;
}

.brand svg {
  color: #4f46e5;
}

.history-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.history-btn:hover {
  background: #e0e7ff;
  color: #4f46e5;
  border-color: #a5b4fc;
}

.canvas-center {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.topology-wrapper {
  position: relative;
  width: 800px;
  height: 600px;
}

.topology-lines, .ghost-nodes {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
}

.ghost-line {
  fill: none;
  stroke: url(#line-gradient);
  stroke-width: 2;
  stroke-dasharray: 6 6;
  opacity: 0.4;
  animation: flowLine 2s linear infinite;
}

@keyframes flowLine {
  to { stroke-dashoffset: -16; }
}

.ghost-node {
  position: absolute;
  display: flex;
  flex-direction: row-reverse;
  align-items: center;
  gap: 12px;
  opacity: 0.6;
}

.pulse-dot {
  width: 12px; height: 12px;
  background: var(--color-surface);
  border: 2px solid #4f46e5;
  border-radius: 50%;
  position: relative;
}

.pulse-dot::after {
  content: '';
  position: absolute;
  top: -6px; left: -6px; right: -6px; bottom: -6px;
  border-radius: 50%;
  border: 2px solid #4f46e5;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(2); opacity: 0; }
}

.ghost-text {
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-align: right;
}

.ghost-text small {
  display: block;
  font-size: 0.75rem;
  background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-top: 4px;
  font-weight: normal;
}

.destination-node {
  position: absolute;
  top: 50%; left: 500px;
  transform: translate(0, -50%);
  width: 420px; /* 稍微加宽一点适应更多内容 */
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  z-index: 10;
}

.destination-node::before {
  content: '';
  position: absolute;
  top: 50%; left: -6px;
  transform: translateY(-50%);
  width: 12px; height: 12px;
  background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(79, 70, 229, 0.4);
}

.destination-node.is-focused,
.destination-node.has-input {
  border-color: #4f46e5;
  box-shadow: 0 15px 50px rgba(79, 70, 229, 0.15);
}

.node-label { margin-bottom: 16px; }

.badge {
  display: inline-block;
  background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%);
  color: white;
  font-size: 0.7rem;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.node-label h3 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--color-text);
  font-weight: 800;
}

/* === 新增/优化的输入框样式 === */
.input-wrapper {
  position: relative;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  border-radius: 12px;
  transition: all 0.3s ease;
  overflow: hidden;
}

.destination-node.is-focused .input-wrapper {
  border-color: #4f46e5;
  background: var(--color-surface);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.15);
}

.destination-input {
  width: 100%;
  box-sizing: border-box;
  background: transparent;
  border: none;
  padding: 16px;
  resize: none;
  font-size: 1.05rem;
  color: var(--color-text);
  line-height: 1.6;
  outline: none;
  font-family: var(--font-sans);
  min-height: 70px;
}

.destination-input::placeholder {
  color: var(--color-text-muted);
  opacity: 0.6;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  padding: 8px 16px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  background: rgba(0,0,0,0.02);
  border-top: 1px solid var(--color-border);
}

.char-count.is-near-limit {
  color: #ef4444;
  font-weight: bold;
}

/* 快捷标签 */
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.suggestion-tag {
  font-size: 0.8rem;
  padding: 4px 10px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-tag:hover {
  background: #e0e7ff;
  color: #4f46e5;
  border-color: #a5b4fc;
}

/* 按钮样式优化 */
.node-footer {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed var(--color-border);
}

.reverse-btn {
  position: relative;
  width: 100%;
  background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%);
  color: white;
  border: none;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.2s;
  display: flex;
  justify-content: center;
  align-items: center;
}

.reverse-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3);
}

.reverse-btn:disabled {
  opacity: 0.8;
  cursor: not-allowed;
}

.btn-text {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Loading 动画 */
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

.canvas-hints {
  position: absolute;
  bottom: 40px;
  left: 0;
  width: 100%;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.95rem;
  font-weight: 500;
  z-index: 1;
}

/* 动画效果 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-slide-enter-active, .fade-slide-leave-active {
  transition: all 0.3s ease;
}
.fade-slide-enter-from, .fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}

@media (max-width: 900px) {
  .topology-wrapper { transform: scale(0.8); }
}
@media (max-width: 600px) {
  .topology-wrapper { transform: scale(0.6); }
  .ghost-nodes, .topology-lines { display: none; }
  .destination-node { left: 50%; transform: translate(-50%, -50%); width: 90%; }
}
</style>