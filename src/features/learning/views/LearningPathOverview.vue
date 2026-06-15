<template>
  <main class="path-dashboard">
    <BaseCard v-if="loading" class="state-card">正在加载学习路径...</BaseCard>
    <BaseCard v-else-if="!path" class="state-card">
      <p>还没有可用的学习路径。</p>
      <BaseButton variant="primary" @click="router.push('/path-planner')">去创建</BaseButton>
    </BaseCard>

    <div v-else-if="isGenerating" class="generating-screen">
        <div class="generating-content">
        <div class="cube-loader">
          <div class="cube cube1"></div>
          <div class="cube cube2"></div>
          <div class="cube cube4"></div>
          <div class="cube cube3"></div>
        </div>
        <h2>正在生成学习路径</h2>
        <p class="generating-subtitle">系统会先整理阶段与节点，完成后你就可以按节点开始学习。</p>
        <div class="message-log">
          <transition-group name="list">
            <div v-for="(msg, i) in generatingMessages" :key="i" class="log-msg">
              <span class="dot"></span> {{ msg }}
            </div>
          </transition-group>
        </div>
      </div>
    </div>

    <div v-else class="dashboard-grid">
      
      <!-- Top Row: Overview Stats -->
      <header class="dashboard-header">
        <div class="header-main-info">
          <div class="title-area">
            <span class="page-kicker">学习驾驶舱 | 路径总览</span>
            <h1>{{ path.title }}</h1>
            <p>{{ path.goal }}</p>
          </div>
          <div class="header-actions">
            <BaseButton variant="secondary" @click="router.push('/path-planner/history')">路径历史</BaseButton>
            <BaseButton variant="secondary" @click="router.push('/path-resource-history')">资源记录</BaseButton>
            <BaseButton variant="primary" @click="router.push('/path-planner')">重新规划</BaseButton>
          </div>
        </div>
        
        <div class="stats-row">
          <div class="stat-box">
            <label><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></svg> 总进度</label>
            <strong class="text-primary">{{ path.overall_progress }}%</strong>
          </div>
          <div class="stat-box">
            <label><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> 预计耗时</label>
            <strong>{{ path.eta_days }} 天</strong>
          </div>
          <div class="stat-box">
            <label><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg> 学习阶段</label>
            <strong>{{ path.stages.length }} 个</strong>
          </div>
          <div class="stat-box">
            <label><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg> 知识节点</label>
            <strong>{{ path.nodes.length }} 个</strong>
          </div>
          <div class="stat-box">
            <label><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg> 当前节点</label>
            <strong>{{ currentNode?.title || '等待开始' }}</strong>
          </div>
          <div class="stat-box progress-box">
            <div class="progress-track">
              <i :style="{ width: `${path.overall_progress}%` }"></i>
            </div>
          </div>
        </div>
      </header>

      <!-- Evaluation Banner (if any) -->
      <EvaluationBanner :evaluation="evaluation" class="dashboard-banner" />

      <!-- Main Body: High density panels -->
      <div class="dashboard-body">
        <!-- Skill Tree / Graph (full width) -->
        <section class="dashboard-graph">
          <div class="graph-card">
            <div class="card-header">
              <div class="header-text">
                <h3>学习路径节点</h3>
                <p>先看整条路径，再点击节点进入教程、测验和专项巩固。</p>
              </div>
              <div class="legend">
                <span class="legend-item"><i class="dot indigo"></i> 当前可学</span>
                <span class="legend-item"><i class="dot emerald"></i> 已掌握</span>
                <span class="legend-item"><i class="dot slate"></i> 未解锁</span>
              </div>
            </div>
            
            <div class="tree-wrapper">
              <PathSkillTree 
                :stages="path.stages" 
                :nodes="path.nodes" 
                @node-click="handleNodeClick" 
              />
            </div>
          </div>
        </section>

      </div>

      <!-- Drawer for node details -->
      <NodeDetailDrawer 
        v-model="drawerVisible" 
        :node="selectedNode" 
      />

    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onActivated, onDeactivated, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import BaseCard from '@/shared/ui/BaseCard.vue'
import BaseButton from '@/shared/ui/BaseButton.vue'
import PathSkillTree from '@/features/learning/components/PathSkillTree.vue'
import EvaluationBanner from '@/features/learning/components/EvaluationBanner.vue'
import NodeDetailDrawer from '@/features/learning/components/NodeDetailDrawer.vue'

import { getCurrentLearningPath, getLearningPathById, getLearningEvaluation } from '@/features/learning/api/path'
import type { LearningPathOverview, PathLearningEvaluationResponse, LearningPathNode } from '@/features/learning/model/path'
import { getErrorMessage } from '@/shared/api/http'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const path = ref<LearningPathOverview | null>(null)
const evaluation = ref<PathLearningEvaluationResponse | null>(null)

const drawerVisible = ref(false)
const selectedNode = ref<LearningPathNode | null>(null)

const isGenerating = ref(false)
const generatingMessages = ref<string[]>([])
let eventSource: EventSource | null = null

const currentNode = computed(() => {
  if (!path.value) return null
  return path.value.nodes.find((node) => node.node_id === path.value?.current_node_key)
    ?? path.value.nodes.find((node) => ['available', 'in_progress', 'remediation'].includes(node.status))
    ?? null
})

const handlePathEvent = (e: MessageEvent) => {
  try {
    const data = JSON.parse(e.data)
    if (data.message && !generatingMessages.value.includes(data.message)) {
      generatingMessages.value.push(data.message)
      if (generatingMessages.value.length > 4) {
        generatingMessages.value.shift()
      }
    }
    if (data.event_type === 'path.done') {
      eventSource?.close()
      setTimeout(() => {
        loadPath()
      }, 1000)
    }
  } catch (err) {}
}

const startSSE = (pathId: number) => {
  const token = localStorage.getItem('token') || ''
  eventSource = new EventSource(`/api/v1/ai/path-plan/${pathId}/events?token=${encodeURIComponent(token)}`)
  
  eventSource.onmessage = handlePathEvent
  eventSource.addEventListener('path.step', handlePathEvent)
  eventSource.addEventListener('path.done', handlePathEvent)
}

onDeactivated(() => {
})

onActivated(() => {
  if (isGenerating.value && path.value) {
    const currentId = path.value.id
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      startSSE(currentId)
    }
  }
})

onBeforeUnmount(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
})


const loadPath = async () => {
  loading.value = true
  try {
    const rawId = String(route.params.id || '')
    const paramId = Number(rawId || 0)
    const shouldLoadSpecificPath = Boolean(rawId && rawId !== 'latest' && Number.isFinite(paramId) && paramId > 0)

    let currentPathId = 0

    if (shouldLoadSpecificPath) {
      const res = await getLearningPathById(paramId)
      path.value = res.data.data
      currentPathId = path.value.id
    } else {
      const res = await getCurrentLearningPath()
      const current = res.data.data
      if (!current) {
        path.value = null
        return
      }
      path.value = current
      currentPathId = current.id
      if (rawId === 'latest') {
        router.replace(`/path-planner/overview/${current.id}`)
      }
    }

    if (path.value.status === 'generating') {
      isGenerating.value = true
      generatingMessages.value = ['已创建路径记录，正在拆解阶段与节点']
      startSSE(currentPathId)
    } else {
      isGenerating.value = false
      if (currentPathId > 0) {
        loadEvaluation(currentPathId)
      }
    }

  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载学习路径失败'))
  } finally {
    loading.value = false
  }
}

const loadEvaluation = async (pathId: number) => {
  try {
    const res = await getLearningEvaluation(pathId)
    evaluation.value = res.data.data
  } catch (error) {
    console.error('Failed to load evaluation', error)
  }
}

const handleNodeClick = (node: LearningPathNode) => {
  selectedNode.value = node
  drawerVisible.value = true
}

watch(
  () => route.params.id,
  () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    generatingMessages.value = []
    isGenerating.value = false
    loadPath()
  }
)

onMounted(loadPath)
</script>

<style scoped>
.path-dashboard {
  /* --- Deep Page Colorization (Amber Theme) --- */
  --color-primary: var(--cat-path);
  --color-primary-hover: #D97706; /* Amber 600 */
  --color-primary-soft: var(--cat-path-soft);
  --color-primary-border: #FCD34D; /* Amber 300 */
  --color-primary-text: #B45309; /* Amber 700 */
  --gradient-primary: var(--gradient-path);

  min-height: calc(100vh - 64px);
  padding: 24px;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
}

.generating-screen {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  min-height: 60vh;
}

.generating-content {
  text-align: center;
  max-width: 400px;
}

.generating-content h2 {
  font-size: 1.5rem;
  margin: 24px 0 8px;
  background: var(--gradient-path);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.generating-subtitle {
  color: var(--color-text-muted);
  margin-bottom: 32px;
}

.message-log {
  text-align: left;
  background: var(--color-bg);
  padding: 16px 24px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  height: 160px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.log-msg {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text);
  font-size: 0.9rem;
  margin: 4px 0;
  opacity: 0.8;
}

.log-msg:last-child {
  opacity: 1;
  color: var(--cat-path);
  font-weight: 600;
}

.log-msg .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}
.list-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}
.list-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

.cube-loader {
  width: 60px;
  height: 60px;
  margin: 0 auto;
  position: relative;
  transform: rotateZ(45deg);
}
.cube {
  float: left;
  width: 50%;
  height: 50%;
  position: relative;
  transform: scale(1.1);
}
.cube:before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background-color: var(--cat-path);
  animation: cube-loader 2.76s infinite linear both;
  transform-origin: 100% 100%;
}
.cube2 { transform: scale(1.1) rotateZ(90deg); }
.cube3 { transform: scale(1.1) rotateZ(180deg); }
.cube4 { transform: scale(1.1) rotateZ(270deg); }
.cube2:before { animation-delay: 0.3s; }
.cube3:before { animation-delay: 0.6s; }
.cube4:before { animation-delay: 0.9s; }
@keyframes cube-loader {
  0%, 10% { transform: perspective(140px) rotateX(-180deg); opacity: 0; }
  25%, 75% { transform: perspective(140px) rotateX(0deg); opacity: 1; }
  90%, 100% { transform: perspective(140px) rotateY(180deg); opacity: 0; }
}

.dashboard-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  flex: 1;
}

/* Header */
.dashboard-header {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.header-main-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-kicker {
  display: block;
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--cat-path);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 8px;
}

.title-area h1 {
  margin: 0 0 4px;
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.title-area p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text-muted);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stats-row {
  display: flex;
  gap: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
  align-items: center;
}

.stat-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-box label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-box strong {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text);
}

.text-primary {
  color: var(--cat-path) !important;
}

.progress-box {
  flex: 1;
  max-width: 300px;
  margin-left: auto;
  justify-content: center;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: var(--color-bg);
  border-radius: 999px;
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}

.progress-track i {
  display: block;
  height: 100%;
  background: var(--gradient-path);
  border-radius: 999px;
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.progress-track i::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.4) 50%, rgba(255,255,255,0) 100%);
  transform: translateX(-100%);
  animation: shimmer 2.5s infinite;
}

@keyframes shimmer {
  100% { transform: translateX(100%); }
}

.dashboard-banner {
  margin: 0;
}

/* Dashboard Body */
.dashboard-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
}

.dashboard-graph {
  display: flex;
  flex-direction: column;
}

.graph-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 600px;
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg);
}

.header-text h3 {
  margin: 0 0 4px;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
}

.header-text p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.legend {
  display: flex;
  gap: 16px;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.dot.indigo { background: #6366f1; }
.dot.emerald { background: #10b981; }
.dot.slate { background: #94a3b8; }

.tree-wrapper {
  flex: 1;
  position: relative;
}

.state-card {
  max-width: 880px;
  margin: 40px auto 0;
  padding: 40px;
  text-align: center;
}

/* Responsive */
@media (max-width: 1200px) {
  .graph-card {
    min-height: 500px;
  }
}

@media (max-width: 768px) {
  .header-main-info {
    flex-direction: column;
    gap: 16px;
  }
  .stats-row {
    flex-wrap: wrap;
  }
  .progress-box {
    margin-left: 0;
    min-width: 100%;
  }
}
</style>
