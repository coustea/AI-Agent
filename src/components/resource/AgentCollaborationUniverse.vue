<template>
  <div class="collaboration-universe technical-theme">
    <!-- 背景装饰：网格 -->
    <div class="universe-background">
      <div class="blueprint-grid"></div>
    </div>

    <!-- SVG 连线层 -->
    <svg class="connections-layer" ref="svgRef">
      <defs>
        <!-- 连线渐变 -->
        <linearGradient id="beam-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="rgba(99, 102, 241, 0.4)" />
          <stop offset="100%" stop-color="rgba(99, 102, 241, 0.05)" />
        </linearGradient>
        
        <!-- 活跃状态流光过滤器 -->
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>

      <!-- 动态连线 -->
      <g v-for="agentId in workerAgents" :key="'link-' + agentId">
        <path 
          :d="getLinkPath(agentId)" 
          class="connection-path"
          :class="{ 'is-active': states[agentId] === 'running' || states[agentId] === 'success' }"
        />
        <!-- 流动的光束粒子 -->
        <circle v-if="states[agentId] === 'running'" r="3" fill="#6366F1" filter="url(#glow)">
          <animateMotion 
            :path="getLinkPath(agentId)" 
            dur="1.5s" 
            repeatCount="indefinite" 
            rotate="auto"
          />
        </circle>
      </g>
    </svg>

    <!-- 主容器：垂直布局 -->
    <div class="blueprint-layout">
      
      <!-- Orchestrator Header -->
      <div class="orchestrator-section">
        <div class="master-node-wrapper" ref="masterRef">
          <div class="master-core pulse-glow">
            <div class="frame-corners-small top-left"></div>
            <div class="frame-corners-small top-right"></div>
            <div class="frame-corners-small bottom-left"></div>
            <div class="frame-corners-small bottom-right"></div>
            
            <div class="core-inner">
              <el-icon class="core-icon"><Operation /></el-icon>
            </div>
            <div class="core-waves">
              <span></span><span></span><span></span>
            </div>
          </div>
          <div class="master-info">
            <h3 class="master-title">CORE_ORCHESTRATOR // ALPHA</h3>
            <p class="master-status">{{ orchestratorMessage }}</p>
          </div>
        </div>
      </div>

      <!-- Worker Layers -->
      <div class="workers-grid-layout">
        <div 
          v-for="agentId in workerAgents" 
          :key="agentId"
          class="worker-node-container"
          :class="[states[agentId] || 'pending', { 'has-artifact': results[agentId] }]"
        >
          <div class="worker-node-box">
            <div class="frame-corners-tiny top-left"></div>
            <div class="frame-corners-tiny top-right"></div>
            <div class="frame-corners-tiny bottom-left"></div>
            <div class="frame-corners-tiny bottom-right"></div>

            <!-- 状态指示灯 -->
            <div class="status-indicator"></div>
            
            <div class="worker-main-row">
              <div class="worker-icon-box">
                <transition name="icon-fade" mode="out-in">
                  <el-icon v-if="states[agentId] === 'success'"><Check /></el-icon>
                  <component v-else :is="getAgentMeta(agentId).icon" />
                </transition>
              </div>
              <div class="worker-info">
                <div class="wi-top">
                  <span class="wi-name">{{ getAgentMeta(agentId).name.toUpperCase() }}</span>
                  <span class="wi-step" v-if="getProgress(agentId).total > 0">
                    [{{ getProgress(agentId).current }}/{{ getProgress(agentId).total }}]
                  </span>
                </div>
                <div class="wi-label">{{ getProgress(agentId).label || 'WAITING_CMD...' }}</div>
              </div>
            </div>

            <!-- 实时思考流 -->
            <div class="thinking-stream" v-if="states[agentId] === 'running'">
              <div class="stream-line"></div>
              <div class="stream-text">LOG_STREAM: {{ getProgress(agentId).detail || 'PROCESSING_CONTEXT_DATA...' }}</div>
            </div>

            <!-- 进度条 -->
            <div class="worker-progress-bar">
              <div class="bar-fill" :style="getBarWidth(agentId)"></div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { Operation, Check } from '@element-plus/icons-vue'

interface AgentProgress {
  current: number
  total: number
  label: string
  detail: string
}

const props = defineProps<{
  workerAgents: string[]
  states: Record<string, string>
  messages: Record<string, string>
  payloads: Record<string, any>
  orchestratorMessage: string
  getAgentMeta: (id: string) => any
  results: Record<string, any>
}>()

const svgRef = ref<SVGSVGElement | null>(null)
const containerSize = reactive({ width: 0, height: 0 })

// 获取连线路径
const getLinkPath = (agentId: string) => {
  const idx = props.workerAgents.indexOf(agentId)
  if (idx === -1 || !containerSize.width) return ''
  
  const startX = containerSize.width / 2
  const startY = 120
  
  const total = props.workerAgents.length
  const cols = total > 3 ? 3 : total
  const col = idx % cols
  const row = Math.floor(idx / cols)
  
  const endX = (containerSize.width / (cols + 1)) * (col + 1)
  const endY = 320 + row * 180
  
  const cp1y = startY + (endY - startY) * 0.4
  return `M ${startX} ${startY} C ${startX} ${cp1y}, ${endX} ${cp1y}, ${endX} ${endY}`
}

const getProgress = (agentId: string): AgentProgress => {
  const p = props.payloads[agentId] || {}
  return {
    current: p.current_step || 0,
    total: p.total_steps || 0,
    label: p.step_label || props.messages[agentId] || '',
    detail: p.detail || ''
  }
}

const getBarWidth = (agentId: string) => {
  if (props.states[agentId] === 'success') return { width: '100%' }
  const prog = getProgress(agentId)
  if (prog.total === 0) return { width: '0%' }
  return { width: `${(prog.current / prog.total) * 100}%` }
}

const updateSize = () => {
  if (svgRef.value) {
    containerSize.width = svgRef.value.clientWidth
    containerSize.height = svgRef.value.clientHeight
  }
}

onMounted(() => {
  updateSize()
  window.addEventListener('resize', updateSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateSize)
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.collaboration-universe {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 700px;
  background: #F5F3FF;
  overflow-y: auto;
  overflow-x: hidden;
  --primary: #6366F1;
  --accent: #059669;
}

/* 蓝图网格背景 */
.universe-background {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.blueprint-grid {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(99, 102, 241, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.05) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 1;
}

/* 连线层 */
.connections-layer {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 1200px;
  z-index: 2;
  pointer-events: none;
}

.connection-path {
  fill: none;
  stroke: rgba(99, 102, 241, 0.15);
  stroke-width: 1.5;
  stroke-dasharray: 4, 4;
  transition: all 1s ease;
}

.connection-path.is-active {
  stroke: var(--primary);
  stroke-dasharray: none;
  stroke-width: 2;
  opacity: 0.3;
}

/* 布局结构 */
.blueprint-layout {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: 80px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 100px;
}

/* 拐角装饰 */
.frame-corners-small, .frame-corners-tiny {
  position: absolute;
  border: 2px solid var(--primary);
  pointer-events: none;
  opacity: 0.8;
}

.frame-corners-small { width: 12px; height: 12px; }
.frame-corners-tiny { width: 8px; height: 8px; border-width: 1.5px; }

.top-left { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.top-right { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bottom-left { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.bottom-right { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

/* Orchestrator */
.orchestrator-section {
  display: flex;
  justify-content: center;
  width: 100%;
}

.master-node-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  text-align: center;
}

.master-core {
  position: relative;
  width: 90px;
  height: 90px;
  background: #1E1B4B;
  border-radius: 4px;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.2);
}

.core-inner {
  width: 54px;
  height: 54px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #FFFFFF;
  font-size: 2rem;
}

.core-waves span {
  position: absolute;
  inset: -15px;
  border: 1px solid rgba(99, 102, 241, 0.3);
  border-radius: 4px;
  animation: waveRipple 4s infinite cubic-bezier(0, 0.2, 0.8, 1);
}
.core-waves span:nth-child(2) { animation-delay: -1.3s; }
.core-waves span:nth-child(3) { animation-delay: -2.6s; }

@keyframes waveRipple {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.5); opacity: 0; }
}

.master-title {
  font-family: 'Share Tech Mono', monospace;
  font-size: 1.2rem;
  font-weight: normal;
  color: #1E1B4B;
  letter-spacing: 2px;
  margin: 0;
}

.master-status {
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  color: #64748B;
  margin: 10px 0 0;
  max-width: 450px;
  line-height: 1.5;
}

/* Workers Grid */
.workers-grid-layout {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px 32px;
  width: 100%;
}

.worker-node-box {
  position: relative;
  background: #FFFFFF;
  border: 1px solid #E0E7FF;
  border-radius: 4px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.05);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}

.pending .worker-node-box { opacity: 0.5; transform: scale(0.98); }
.running .worker-node-box { 
  border-color: var(--primary); 
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.15); 
  transform: translateY(-8px);
}
.success .worker-node-box { border-color: var(--accent); background: rgba(5, 150, 105, 0.02); }

/* 状态灯 */
.status-indicator {
  position: absolute;
  top: 16px; right: 16px;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #CBD5E1;
}
.running .status-indicator { background: var(--primary); box-shadow: 0 0 8px var(--primary); animation: blink 1s infinite; }
.success .status-indicator { background: var(--accent); box-shadow: 0 0 8px var(--accent); }

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.worker-main-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.worker-icon-box {
  width: 48px; height: 48px;
  background: #F1F5F9;
  border-radius: 4px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #64748B;
  font-size: 1.4rem;
  transition: all 0.3s;
}
.running .worker-icon-box { background: var(--primary); color: #FFFFFF; box-shadow: 0 0 15px rgba(99, 102, 241, 0.3); }
.success .worker-icon-box { background: var(--accent); color: #FFFFFF; }

.worker-info { flex: 1; min-width: 0; }
.wi-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.wi-name { font-family: 'Share Tech Mono', monospace; font-weight: normal; font-size: 1rem; color: #1E1B4B; letter-spacing: 1px; }
.wi-step { font-family: 'Share Tech Mono', monospace; font-size: 0.75rem; color: var(--primary); }
.wi-label { font-family: 'Fira Code', monospace; font-size: 0.8rem; color: #64748B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.running .wi-label { color: var(--primary); }

/* 思考流动效 */
.thinking-stream {
  margin-top: 16px;
  padding: 10px 12px;
  background: #F8FAFC;
  border-radius: 2px;
  position: relative;
  border-left: 2px solid var(--primary);
}

.stream-line {
  position: absolute;
  top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--primary), transparent);
  animation: streamMove 2s infinite linear;
}

@keyframes streamMove {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.stream-text {
  font-size: 0.7rem;
  color: #475569;
  line-height: 1.4;
  font-family: 'Fira Code', monospace;
  text-transform: uppercase;
}

/* 进度条 */
.worker-progress-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  background: #F1F5F9;
}
.bar-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.6s ease;
  box-shadow: 0 0 10px var(--primary);
}
.success .bar-fill { background: var(--accent); box-shadow: 0 0 10px var(--accent); }

.pulse-glow {
  animation: masterPulse 5s infinite ease-in-out;
}
@keyframes masterPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}

@media (max-width: 900px) {
  .workers-grid-layout { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .workers-grid-layout { grid-template-columns: 1fr; }
}
</style>
