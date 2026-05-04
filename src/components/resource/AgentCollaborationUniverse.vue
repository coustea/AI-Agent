<template>
  <div class="collaboration-universe light-theme">
    <!-- 背景装饰：网格 -->
    <div class="universe-background">
      <div class="blueprint-grid"></div>
    </div>

    <!-- SVG 连线层 -->
    <svg class="connections-layer" ref="svgRef">
      <defs>
        <!-- 连线渐变 -->
        <linearGradient id="beam-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="rgba(59, 130, 246, 0.4)" />
          <stop offset="100%" stop-color="rgba(59, 130, 246, 0.05)" />
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
        <circle v-if="states[agentId] === 'running'" r="4" fill="#3B82F6" filter="url(#glow)">
          <animateMotion 
            :path="getLinkPath(agentId)" 
            dur="1.2s" 
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
            <div class="core-inner">
              <el-icon class="core-icon"><Operation /></el-icon>
            </div>
            <div class="core-waves">
              <span></span><span></span><span></span>
            </div>
          </div>
          <div class="master-info">
            <h3 class="master-title">SYSTEM ORCHESTRATOR</h3>
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
                  <span class="wi-name">{{ getAgentMeta(agentId).name }}</span>
                  <span class="wi-step" v-if="getProgress(agentId).total > 0">
                    {{ getProgress(agentId).current }}/{{ getProgress(agentId).total }}
                  </span>
                </div>
                <div class="wi-label">{{ getProgress(agentId).label || '等待指令…' }}</div>
              </div>
            </div>

            <!-- 实时思考流 (仅在运行时显示) -->
            <div class="thinking-stream" v-if="states[agentId] === 'running'">
              <div class="stream-line"></div>
              <div class="stream-text">{{ getProgress(agentId).detail || '正在处理上下文数据…' }}</div>
            </div>

            <!-- 进度条 (底部) -->
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

// 获取连线路径 (垂直布局：从顶部中心到各节点)
const getLinkPath = (agentId: string) => {
  const idx = props.workerAgents.indexOf(agentId)
  if (idx === -1 || !containerSize.width) return ''
  
  // 假设 Orchestrator 在 (width/2, 120)
  const startX = containerSize.width / 2
  const startY = 120
  
  // 获取 Worker 节点位置
  const total = props.workerAgents.length
  const cols = total > 3 ? 3 : total
  const col = idx % cols
  const row = Math.floor(idx / cols)
  
  const endX = (containerSize.width / (cols + 1)) * (col + 1)
  const endY = 320 + row * 180
  
  // 贝塞尔曲线，增加科技感
  const cp1y = startY + (endY - startY) * 0.5
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
.collaboration-universe {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 700px;
  background: #FFFFFF;
  overflow-y: auto;
  overflow-x: hidden;
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
    radial-gradient(#E2E8F0 1.5px, transparent 1.5px),
    linear-gradient(rgba(226, 232, 240, 0.4) 1px, transparent 1px),
    linear-gradient(90deg, rgba(226, 232, 240, 0.4) 1px, transparent 1px);
  background-size: 40px 40px, 40px 40px, 40px 40px;
  opacity: 0.6;
}

/* 连线层 */
.connections-layer {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 1000px;
  z-index: 2;
  pointer-events: none;
}

.connection-path {
  fill: none;
  stroke: #E2E8F0;
  stroke-width: 2;
  stroke-dasharray: 6, 6;
  transition: stroke 1s ease, stroke-width 1s ease, stroke-dasharray 1s ease, opacity 1s ease;
}

.connection-path.is-active {
  stroke: #3B82F6;
  stroke-dasharray: none;
  stroke-width: 2.5;
  opacity: 0.4;
}

/* 布局结构 */
.blueprint-layout {
  position: relative;
  z-index: 10;
  max-width: 1200px;
  margin: 0 auto;
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 80px;
}

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
  gap: 20px;
  text-align: center;
}

.master-core {
  position: relative;
  width: 100px;
  height: 100px;
  background: #0F172A;
  border-radius: 28px;
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.1);
}

.core-inner {
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 18px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #FFFFFF;
  font-size: 2.2rem;
}

.core-waves span {
  position: absolute;
  inset: -10px;
  border: 2px solid rgba(59, 130, 246, 0.4);
  border-radius: 36px;
  animation: waveRipple 3s infinite cubic-bezier(0, 0.2, 0.8, 1);
}
.core-waves span:nth-child(2) { animation-delay: -1s; }
.core-waves span:nth-child(3) { animation-delay: -2s; }

@keyframes waveRipple {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.6); opacity: 0; }
}

.master-title {
  font-size: 1.1rem;
  font-weight: 900;
  color: #0F172A;
  letter-spacing: 0.15em;
  margin: 0;
}

.master-status {
  font-size: 0.95rem;
  color: #64748B;
  margin: 8px 0 0;
  max-width: 400px;
  font-weight: 500;
}

/* Workers Grid */
.workers-grid-layout {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 40px 30px;
  width: 100%;
}

.worker-node-container {
  perspective: 1000px;
}

.worker-node-box {
  position: relative;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.4s, background-color 0.4s, box-shadow 0.4s, opacity 0.4s;
  overflow: hidden;
}

.pending .worker-node-box { opacity: 0.6; transform: scale(0.95); background: #F8FAFC; }
.running .worker-node-box { 
  border-color: #3B82F6; 
  box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.1); 
  transform: translateY(-5px);
}
.success .worker-node-box { border-color: #10B981; background: #F0FDF4; }

/* 状态灯 */
.status-indicator {
  position: absolute;
  top: 24px; right: 24px;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #CBD5E1;
}
.running .status-indicator { background: #3B82F6; box-shadow: 0 0 10px #3B82F6; animation: blink 1s infinite; }
.success .status-indicator { background: #10B981; }

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.worker-main-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.worker-icon-box {
  width: 52px; height: 52px;
  background: #F1F5F9;
  border-radius: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #64748B;
  font-size: 1.5rem;
  transition: background-color 0.3s, color 0.3s;
}
.running .worker-icon-box { background: #3B82F6; color: #FFFFFF; }
.success .worker-icon-box { background: #10B981; color: #FFFFFF; }

.worker-info { flex: 1; min-width: 0; }
.wi-top { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
.wi-name { font-weight: 800; font-size: 1.05rem; color: #0F172A; }
.wi-step { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #3B82F6; font-weight: 700; }
.wi-label { font-size: 0.9rem; color: #64748B; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.running .wi-label { color: #3B82F6; }

/* 思考流动效 */
.thinking-stream {
  margin-top: 16px;
  padding: 12px;
  background: #F8FAFC;
  border-radius: 12px;
  position: relative;
}

.stream-line {
  position: absolute;
  top: 0; left: 12px; right: 12px; height: 2px;
  background: linear-gradient(90deg, transparent, #3B82F6, transparent);
  animation: streamMove 2s infinite linear;
}

@keyframes streamMove {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.stream-text {
  font-size: 0.75rem;
  color: #475569;
  line-height: 1.4;
  font-family: 'JetBrains Mono', monospace;
}

/* 进度条 */
.worker-progress-bar {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 4px;
  background: #F1F5F9;
}
.bar-fill {
  height: 100%;
  background: #3B82F6;
  transition: width 0.5s ease;
}
.success .bar-fill { background: #10B981; }

.icon-fade-enter-active, .icon-fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.icon-fade-enter-from, .icon-fade-leave-to { opacity: 0; transform: scale(0.5) rotate(-45deg); }

.pulse-glow {
  animation: masterPulse 4s infinite ease-in-out;
}
@keyframes masterPulse {
  0%, 100% { box-shadow: 0 10px 30px rgba(15, 23, 42, 0.1); }
  50% { box-shadow: 0 10px 50px rgba(59, 130, 246, 0.2); }
}

@media (max-width: 900px) {
  .workers-grid-layout { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .workers-grid-layout { grid-template-columns: 1fr; }
}
</style>
