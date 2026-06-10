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
      <div class="topology-wrapper" :class="{ 'is-loading': submitting }">
        
        <!-- SVG Connecting Lines -->
        <svg class="topology-lines" viewBox="0 0 800 600" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="var(--cat-tutor)" />
              <stop offset="50%" stop-color="var(--cat-eval)" />
              <stop offset="100%" stop-color="var(--cat-rose)" />
            </linearGradient>
          </defs>
          <path d="M 250,300 C 350,300 400,300 500,300" class="ghost-line main-line" />
          <path d="M 150,150 C 250,150 350,300 500,300" class="ghost-line" />
          <path d="M 150,450 C 250,450 350,300 500,300" class="ghost-line" />
        </svg>

        <!-- Ghost Nodes (Unknown Prerequisites) -->
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

        <!-- The Central Destination Node -->
        <div class="destination-node" :class="{ 'is-focused': isFocused, 'has-input': goal.trim().length > 0 }">
          <div class="node-label">
            <span class="badge">学习目标</span>
            <h3>先定义你想学成什么样</h3>
          </div>
          
          <textarea
            v-model="goal"
            class="destination-input"
            placeholder="例如：系统掌握 FastAPI 高并发架构与部署"
            @focus="isFocused = true"
            @blur="isFocused = false"
            rows="3"
          />

          <transition name="fade">
            <div class="node-footer" v-if="goal.trim().length > 0">
              <button class="reverse-btn" :disabled="submitting" @click="handleSubmit">
                <span class="btn-text">{{ submitting ? '正在生成学习路径...' : '生成学习路径' }}</span>
                <span class="scan-line" v-if="submitting"></span>
              </button>
            </div>
          </transition>
        </div>

      </div>
    </div>
    
    <div class="canvas-hints" v-if="!submitting && !isFocused && !goal">
      <p>输入目标后，系统会先生成一条可执行的学习路径；进入节点后再按需生成教程、题目和辅助资源。</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createLearningPath } from '@/features/learning/api/path'
import { getErrorMessage } from '@/shared/api/http'

const router = useRouter()
const goal = ref('')
const submitting = ref(false)
const isFocused = ref(false)

const handleSubmit = async () => {
  const value = goal.value.trim()
  if (!value) {
    ElMessage.warning('请先输入终极学习目标')
    return
  }

  submitting.value = true
  try {
    const res = await createLearningPath({ goal: value, topic: value })
    const path = res.data.data
    router.push(`/path-planner/overview/${path.id}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '路线推演失败'))
    submitting.value = false
  }
}
</script>

<style scoped>
/* Blueprint Grid Canvas */
.blueprint-canvas {
  position: relative;
  min-height: calc(100vh - 64px);
  background-color: var(--color-bg);
  background-image: 
    radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 50% 80%, rgba(245, 158, 11, 0.05) 0%, transparent 50%),
    linear-gradient(rgba(99, 102, 241, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.05) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 100% 100%, 30px 30px, 30px 30px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Add a subtle vignette/glow to the canvas */
.blueprint-canvas::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(circle at center, transparent 30%, var(--color-bg) 100%);
  pointer-events: none;
  z-index: 0;
}

/* Top Nav */
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
  color: var(--cat-tutor);
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
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  border-color: var(--cat-tutor-glow);
}

/* Canvas Center Area */
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

/* SVG Lines */
.topology-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.ghost-line {
  fill: none;
  stroke: url(#line-gradient);
  stroke-width: 2;
  stroke-dasharray: 6 6;
  opacity: 0.25;
  transition: all 0.5s ease;
}

.is-loading .ghost-line {
  stroke-dasharray: 8 8;
  opacity: 0.6;
  animation: flowLine 1s linear infinite;
}

@keyframes flowLine {
  to { stroke-dashoffset: -16; }
}

/* Ghost Nodes */
.ghost-nodes {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.ghost-node {
  position: absolute;
  display: flex;
  flex-direction: row-reverse;
  align-items: center;
  gap: 12px;
  opacity: 0.4;
  transition: all 0.5s ease;
}

.is-loading .ghost-node {
  opacity: 0.9;
}

.pulse-dot {
  width: 12px;
  height: 12px;
  background: var(--color-surface);
  border: 2px solid var(--cat-tutor);
  border-radius: 50%;
  position: relative;
}

.is-loading .pulse-dot::after {
  content: '';
  position: absolute;
  top: -6px; left: -6px; right: -6px; bottom: -6px;
  border-radius: 50%;
  border: 2px solid var(--cat-tutor);
  animation: pulse 1.5s infinite;
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
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-top: 4px;
  font-weight: normal;
}

/* Central Destination Node */
.destination-node {
  position: absolute;
  top: 50%;
  left: 500px;
  transform: translate(0, -50%);
  width: 380px;
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
  top: 50%;
  left: -6px;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  background: var(--gradient-primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--cat-eval-glow);
}

.destination-node.is-focused,
.destination-node.has-input {
  border-color: var(--cat-eval);
  box-shadow: 0 15px 50px var(--cat-eval-glow);
}

.node-label {
  margin-bottom: 16px;
}

.badge {
  display: inline-block;
  background: var(--gradient-primary);
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

.destination-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--color-bg);
  border: 2px solid var(--color-border); /* Thicker and more visible border */
  border-radius: 12px;
  padding: 16px;
  resize: none;
  font-size: 1.05rem;
  color: var(--color-text);
  line-height: 1.6;
  outline: none;
  font-family: var(--font-sans);
  transition: all 0.3s ease;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}

.destination-input:focus {
  border-color: var(--cat-eval);
  background: var(--color-surface);
  box-shadow: 0 0 0 4px var(--cat-eval-soft), inset 0 2px 4px rgba(0,0,0,0.02);
}

.destination-input::placeholder {
  color: var(--color-text-muted);
  opacity: 0.8;
}

.node-footer {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px dashed var(--color-border);
}

.reverse-btn {
  position: relative;
  width: 100%;
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 14px 20px;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.2s;
}

.reverse-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px var(--cat-eval-glow);
}

.reverse-btn:disabled {
  opacity: 0.8;
  cursor: wait;
}

.btn-text {
  position: relative;
  z-index: 2;
}

.scan-line {
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
  animation: scan 1.5s infinite;
  z-index: 1;
}

@keyframes scan {
  100% { left: 200%; }
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Responsive constraints */
@media (max-width: 900px) {
  .topology-wrapper {
    transform: scale(0.8);
  }
}
@media (max-width: 600px) {
  .topology-wrapper {
    transform: scale(0.6);
  }
  .ghost-nodes {
    display: none;
  }
  .topology-lines {
    display: none;
  }
  .destination-node {
    left: 50%;
    transform: translate(-50%, -50%);
  }
}
</style>
