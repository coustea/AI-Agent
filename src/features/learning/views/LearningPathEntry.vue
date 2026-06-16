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
            @keydown.enter.prevent="handleSubmit"
          />

          <transition name="fade">
            <div class="node-footer" v-if="goal.trim().length > 0">
              <button class="reverse-btn" @click="handleSubmit">
                <span class="btn-text">生成学习路径</span>
              </button>
            </div>
          </transition>
        </div>

      </div>
    </div>

    <div class="canvas-hints" v-if="!isFocused && !goal">
      <p>输入目标后，系统会先生成一条可执行的学习路径；进入节点后再按需生成教程、题目和辅助资源。</p>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const goal = ref('')
const isFocused = ref(false)

const handleSubmit = () => {
  const value = goal.value.trim()
  if (!value) {
    ElMessage.warning('请先输入终极学习目标')
    return
  }

  // 核心优化：直接带参数无缝切换到 Overview 的生成态路由
  router.push({
    path: `/path-planner/overview/new`,
    query: { goal: value }
  })
}
</script>

<style scoped>
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
  opacity: 0.4;
  animation: flowLine 2s linear infinite;
}

@keyframes flowLine {
  to { stroke-dashoffset: -16; }
}

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
  opacity: 0.6;
}

.pulse-dot {
  width: 12px;
  height: 12px;
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
  background: linear-gradient(135deg, #4f46e5 0%, #0ea5e9 100%);
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(79, 70, 229, 0.4);
}

.destination-node.is-focused,
.destination-node.has-input {
  border-color: #4f46e5;
  box-shadow: 0 15px 50px rgba(79, 70, 229, 0.15);
}

.node-label {
  margin-bottom: 16px;
}

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

.destination-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
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
  border-color: #4f46e5;
  background: var(--color-surface);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.15), inset 0 2px 4px rgba(0,0,0,0.02);
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
}

.reverse-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3);
}

.btn-text {
  position: relative;
  z-index: 2;
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

@media (max-width: 900px) {
  .topology-wrapper { transform: scale(0.8); }
}
@media (max-width: 600px) {
  .topology-wrapper { transform: scale(0.6); }
  .ghost-nodes { display: none; }
  .topology-lines { display: none; }
  .destination-node { left: 50%; transform: translate(-50%, -50%); }
}
</style>