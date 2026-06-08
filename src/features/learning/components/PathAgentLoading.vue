<template>
  <div class="path-agent-loading glass-panel">
    <div class="loading-header">
      <span class="eyebrow">多智能体协同网络</span>
      <h2>{{ latestMessage || '正在初始化学习路径构建...' }}</h2>
    </div>

    <div class="loading-dashboard-grid">
      <!-- 左侧：SVG 动画区域 -->
      <div class="animation-col">
        <div class="animation-container">
          <svg viewBox="0 0 400 300" width="100%" height="280" class="agent-svg">
            <!-- 连线轨道 -->
            <g class="tracks">
              <!-- 画像 -> 核心 -->
              <line x1="80" y1="150" x2="200" y2="150" class="track-line" :class="{ active: status === 'preparing' }" />
              <!-- 检索 -> 核心 -->
              <line x1="200" y1="70" x2="200" y2="150" class="track-line" :class="{ active: status === 'researching' }" />
              <!-- 规划 -> 核心 -->
              <line x1="200" y1="230" x2="200" y2="150" class="track-line" :class="{ active: ['planning', 'analyzing', 'strategizing'].includes(status) }" />
              <!-- 校验 -> 核心 -->
              <line x1="320" y1="150" x2="200" y2="150" class="track-line" :class="{ active: status === 'validating' }" />
            </g>

            <!-- 轨道流动粒子 -->
            <g class="pulses">
              <!-- 画像 -> 核心 -->
              <circle r="4" fill="var(--tone-blue)" class="pulse-dot" :class="{ active: status === 'preparing' }">
                <animateMotion dur="1.5s" repeatCount="indefinite" path="M 80 150 L 200 150" />
              </circle>
              <!-- 检索 -> 核心 -->
              <circle r="4" fill="#0d9488" class="pulse-dot" :class="{ active: status === 'researching' }">
                <animateMotion dur="1.5s" repeatCount="indefinite" path="M 200 70 L 200 150" />
              </circle>
              <!-- 规划 -> 核心 -->
              <circle r="4" fill="var(--color-primary)" class="pulse-dot" :class="{ active: ['planning', 'analyzing', 'strategizing'].includes(status) }">
                <animateMotion dur="1.5s" repeatCount="indefinite" path="M 200 230 L 200 150" />
              </circle>
              <!-- 校验 -> 核心 -->
              <circle r="4" fill="var(--color-success)" class="pulse-dot" :class="{ active: status === 'validating' }">
                <animateMotion dur="1.5s" repeatCount="indefinite" path="M 320 150 L 200 150" />
              </circle>
            </g>

            <!-- 检索雷达波 -->
            <circle
              v-if="status === 'researching'"
              cx="200"
              cy="70"
              r="24"
              fill="none"
              stroke="#0d9488"
              stroke-width="1"
              class="radar-ring"
            />

            <!-- 校验扫射光 -->
            <line
              v-if="status === 'validating'"
              x1="160"
              y1="110"
              x2="240"
              y2="110"
              stroke="var(--color-success)"
              stroke-width="2"
              class="scanner-bar"
            />

            <!-- 核心图谱核心 (Center Core) -->
            <g class="node core-node" :class="{ active: ['planning', 'analyzing', 'strategizing', 'validating'].includes(status) }">
              <circle cx="200" cy="150" r="28" class="core-glow" />
              <circle cx="200" cy="150" r="22" class="core-inner" />
              <!-- 核心内部网络微粒 -->
              <circle cx="192" cy="144" r="3" fill="#ffffff" />
              <circle cx="208" cy="146" r="2" fill="#ffffff" />
              <circle cx="202" cy="158" r="3" fill="#ffffff" />
              <line x1="192" y1="144" x2="208" y2="146" stroke="#ffffff" stroke-width="0.5" />
              <line x1="208" y1="146" x2="202" y2="158" stroke="#ffffff" stroke-width="0.5" />
              <line x1="202" y1="158" x2="192" y2="144" stroke="#ffffff" stroke-width="0.5" />
            </g>

            <!-- 画像智能体 (Left) -->
            <g class="node agent-node blue-node" :class="{ active: status === 'preparing', idle: status && status !== 'preparing' }">
              <circle cx="80" cy="150" r="20" class="node-bg" />
              <circle cx="80" cy="150" r="16" class="node-border" />
              <!-- 人物剪影 -->
              <circle cx="80" cy="146" r="4" fill="var(--tone-blue)" />
              <path d="M74 156 A6 6 0 0 1 86 156 Z" fill="var(--tone-blue)" />
            </g>

            <!-- 检索智能体 (Top) -->
            <g class="node agent-node teal-node" :class="{ active: status === 'researching', idle: status && status !== 'researching' }">
              <circle cx="200" cy="70" r="20" class="node-bg" />
              <circle cx="200" cy="70" r="16" class="node-border" />
              <!-- 放大镜 -->
              <circle cx="198" cy="68" r="3.5" stroke="#0d9488" stroke-width="1.5" fill="none" />
              <line x1="201" y1="71" x2="205" y2="75" stroke="#0d9488" stroke-width="1.5" stroke-linecap="round" />
            </g>

            <!-- 规划智能体 (Bottom) -->
            <g class="node agent-node indigo-node" :class="{ active: ['planning', 'analyzing', 'strategizing'].includes(status), idle: status && !['planning', 'analyzing', 'strategizing'].includes(status) }">
              <circle cx="200" cy="230" r="20" class="node-bg" />
              <circle cx="200" cy="230" r="16" class="node-border" />
              <!-- 分支连线 -->
              <circle cx="194" cy="234" r="2" fill="var(--color-primary)" />
              <circle cx="206" cy="234" r="2" fill="var(--color-primary)" />
              <circle cx="200" cy="224" r="2.5" fill="var(--color-primary)" />
              <line x1="194" y1="234" x2="200" y2="224" stroke="var(--color-primary)" stroke-width="1" />
              <line x1="206" y1="234" x2="200" y2="224" stroke="var(--color-primary)" stroke-width="1" />
            </g>

            <!-- 校验智能体 (Right) -->
            <g class="node agent-node emerald-node" :class="{ active: status === 'validating', idle: status && status !== 'validating' }">
              <circle cx="320" cy="150" r="20" class="node-bg" />
              <circle cx="320" cy="150" r="16" class="node-border" />
              <!-- 勾选图标 -->
              <path d="M315 150 L319 154 L326 146" fill="none" stroke="var(--color-success)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </g>
          </svg>
        </div>
      </div>

      <!-- 右侧：进度条与状态卡片 -->
      <div class="status-col">
        <div class="progress-details">
          <div class="progress-info-row">
            <span class="status-badge" :class="status">{{ statusLabel }}</span>
            <strong class="pct-num">{{ progressPct }}%</strong>
          </div>
          <el-progress
            :percentage="progressPct"
            :stroke-width="10"
            :show-text="false"
            :color="progressBarColor"
            class="custom-progress"
          />
          <div class="stepper-track">
            <span
              v-for="step in steps"
              :key="step.key"
              class="step-indicator"
              :class="{ active: status === step.key, done: isStepCompleted(step.key) }"
            >
              {{ step.label }}
            </span>
          </div>
        </div>

        <div class="agent-status-cards">
          <div class="agent-card" :class="{ active: status === 'preparing' }">
            <div class="agent-card-header">
              <el-icon><User /></el-icon>
              <span>画像分析智能体</span>
              <el-tag v-if="status === 'preparing'" size="small" effect="plain" type="primary" class="flash-tag">运行中</el-tag>
              <el-icon v-else-if="isStepCompleted('preparing')" class="text-success"><Select /></el-icon>
            </div>
            <p>提取认知偏好与基础背景，构建诊断模型</p>
          </div>
          
          <div class="agent-card" :class="{ active: status === 'researching' }">
            <div class="agent-card-header">
              <el-icon><Search /></el-icon>
              <span>联网检索智能体</span>
              <el-tag v-if="status === 'researching'" size="small" effect="plain" type="primary" class="flash-tag">运行中</el-tag>
              <el-icon v-else-if="isStepCompleted('researching')" class="text-success"><Select /></el-icon>
            </div>
            <p>实时检索技术动态，扩充并考证相关知识点</p>
          </div>

          <div class="agent-card" :class="{ active: ['planning', 'analyzing', 'strategizing'].includes(status) }">
            <div class="agent-card-header">
              <el-icon><Connection /></el-icon>
              <span>拓扑编排智能体</span>
              <el-tag v-if="['planning', 'analyzing', 'strategizing'].includes(status)" size="small" effect="plain" type="primary" class="flash-tag">运行中</el-tag>
              <el-icon v-else-if="isStepCompleted('strategizing')" class="text-success"><Select /></el-icon>
            </div>
            <p>基于依赖关系生成无环图并裁剪策略</p>
          </div>

          <div class="agent-card" :class="{ active: status === 'validating' }">
            <div class="agent-card-header">
              <el-icon><Checked /></el-icon>
              <span>质量校验智能体</span>
              <el-tag v-if="status === 'validating'" size="small" effect="plain" type="primary" class="flash-tag">运行中</el-tag>
              <el-icon v-else-if="isStepCompleted('validating')" class="text-success"><Select /></el-icon>
            </div>
            <p>双重验证图谱连通性，激活学习地图</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, Search, Connection, Checked, Select } from '@element-plus/icons-vue'

const props = defineProps<{
  status: string
  progress: number
  latestMessage: string
}>()

const steps = [
  { key: 'preparing', label: '画像读取' },
  { key: 'researching', label: '文献检索' },
  { key: 'planning', label: '路线编排' },
  { key: 'strategizing', label: '策略制定' },
  { key: 'validating', label: '拓扑校验' }
]

const progressPct = computed(() => {
  const p = Number(props.progress)
  if (!Number.isFinite(p) || p <= 0) return 8
  return Math.max(8, Math.min(100, Math.round(p)))
})

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '准备中',
    preparing: '画像诊断中',
    planning: '任务排布中',
    researching: '互联网检索中',
    analyzing: '拓扑分析中',
    strategizing: '个性化剪裁中',
    validating: '依赖关系校验中',
    completed: '生成完成',
    failed: '生成失败'
  }
  return map[props.status] || props.status || 'AI 规划中'
})

const progressBarColor = [
  { color: '#3b82f6', percentage: 25 },
  { color: '#0d9488', percentage: 50 },
  { color: '#4f46e5', percentage: 75 },
  { color: '#10b981', percentage: 100 }
]

function isStepCompleted(stepKey: string) {
  const order = ['preparing', 'researching', 'planning', 'analyzing', 'strategizing', 'validating', 'completed']
  const currentIdx = order.indexOf(props.status)
  const stepIdx = order.indexOf(stepKey)
  return currentIdx > stepIdx
}
</script>

<style scoped>
.path-agent-loading {
  max-width: 1000px;
  margin: 64px auto 0;
  padding: 36px 40px;
  text-align: left;
}

.glass-panel {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-2xl);
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.loading-header {
  text-align: center;
  margin-bottom: 32px;
}

.eyebrow {
  display: inline-block;
  color: var(--color-primary);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

h2 {
  font-size: var(--text-lg);
  color: var(--color-text);
  font-weight: var(--weight-bold);
  margin: 0;
}

.loading-dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  align-items: stretch;
}

/* SVG 动画排版 */
.animation-col {
  display: flex;
}

.animation-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  padding: 16px;
}

.agent-svg {
  max-width: 440px;
}

/* 连线和微粒轨道样式 */
.track-line {
  stroke: var(--color-border);
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
}

.track-line.active {
  stroke: var(--color-primary-border);
  stroke-width: 2;
  animation: lineDashFlow 1s linear infinite;
}

@keyframes lineDashFlow {
  to {
    stroke-dashoffset: -16;
  }
}

.pulse-dot {
  display: none;
}
.pulse-dot.active {
  display: block;
}

/* 节点动效 */
.node {
  transition: all 0.4s ease;
}

.node .node-bg {
  fill: #ffffff;
  stroke: var(--color-border);
  stroke-width: 1;
}

.node .node-border {
  fill: transparent;
  stroke: var(--color-border-hover);
  stroke-width: 1;
}

/* 画像节点活动态 */
.blue-node.active .node-bg {
  stroke: var(--tone-blue);
  fill: rgba(37, 99, 235, 0.06);
}
.blue-node.active .node-border {
  stroke: var(--tone-blue);
  animation: pulseRipple 1.8s infinite;
}

/* 检索节点活动态 */
.teal-node.active .node-bg {
  stroke: #0d9488;
  fill: rgba(13, 148, 136, 0.06);
}
.teal-node.active .node-border {
  stroke: #0d9488;
  animation: pulseRipple 1.8s infinite;
}

/* 规划节点活动态 */
.indigo-node.active .node-bg {
  stroke: var(--color-primary);
  fill: rgba(79, 70, 229, 0.06);
}
.indigo-node.active .node-border {
  stroke: var(--color-primary);
  animation: pulseRipple 1.8s infinite;
}

/* 校验节点活动态 */
.emerald-node.active .node-bg {
  stroke: var(--color-success);
  fill: rgba(16, 185, 129, 0.06);
}
.emerald-node.active .node-border {
  stroke: var(--color-success);
  animation: pulseRipple 1.8s infinite;
}

/* 节点在闲置时的透明度 */
.node.idle {
  opacity: 0.35;
}

/* 核心图谱节点动效 */
.core-node .core-glow {
  fill: rgba(79, 70, 229, 0.1);
  stroke: rgba(79, 70, 229, 0.05);
  stroke-width: 1;
}
.core-node .core-inner {
  fill: var(--color-primary);
  stroke: var(--color-primary-hover);
  stroke-width: 2;
}

.core-node.active .core-glow {
  animation: coreGlowPulse 2s ease-in-out infinite alternate;
}

@keyframes coreGlowPulse {
  0% { fill: rgba(79, 70, 229, 0.08); transform: scale(0.96); transform-origin: 200px 150px; }
  100% { fill: rgba(79, 70, 229, 0.22); transform: scale(1.06); transform-origin: 200px 150px; }
}

@keyframes pulseRipple {
  0% { stroke-width: 1; transform: scale(1); transform-origin: inherit; opacity: 1; }
  100% { stroke-width: 4; transform: scale(1.3); transform-origin: inherit; opacity: 0; }
}

/* 蓝色画像节点 transform-origin */
.blue-node { transform-origin: 80px 150px; }
.teal-node { transform-origin: 200px 70px; }
.indigo-node { transform-origin: 200px 230px; }
.emerald-node { transform-origin: 320px 150px; }

/* 检索雷达动画 */
.radar-ring {
  transform-origin: 200px 70px;
  animation: radarScan 1.6s ease-out infinite;
}

@keyframes radarScan {
  0% { transform: scale(0.8); opacity: 1; }
  100% { transform: scale(1.6); opacity: 0; }
}

/* 校验扫射条动画 */
.scanner-bar {
  animation: scanMove 2s ease-in-out infinite alternate;
}

@keyframes scanMove {
  0% { transform: translateY(-20px); opacity: 0.8; }
  100% { transform: translateY(20px); opacity: 0.8; }
}

/* 进度条与底部指引 */
.status-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.progress-details {
  max-width: 100%;
}

.progress-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-badge {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}
.status-badge.researching { background: rgba(13, 148, 136, 0.08); color: #0d9488; }
.status-badge.preparing { background: rgba(37, 99, 235, 0.08); color: var(--tone-blue); }
.status-badge.validating { background: rgba(16, 185, 129, 0.08); color: var(--color-success); }
.status-badge.planning, .status-badge.strategizing { background: rgba(79, 70, 229, 0.08); color: var(--color-primary); }

.pct-num {
  font-size: var(--text-lg);
  font-weight: var(--weight-extrabold);
  color: var(--color-primary);
}

.custom-progress {
  margin-bottom: 20px;
}

:deep(.custom-progress .el-progress-bar__runway) {
  background-color: var(--color-border-light) !important;
  border-radius: var(--radius-pill) !important;
}

/* 步骤底轨 */
.stepper-track {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--color-border-light);
  padding-top: 14px;
}

.step-indicator {
  font-size: var(--text-xs);
  color: var(--color-text-faint);
  font-weight: var(--weight-medium);
  transition: color 0.3s ease;
  position: relative;
}

.step-indicator.active {
  color: var(--color-primary);
  font-weight: var(--weight-bold);
}

.step-indicator.done {
  color: var(--color-success);
  font-weight: var(--weight-bold);
}

.step-indicator.done::after {
  content: '✓';
  margin-left: 2px;
  font-size: 10px;
}

/* 右侧：智能体状态卡片 */
.agent-status-cards {
  display: grid;
  gap: 12px;
}

.agent-card {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-lg);
  padding: 16px;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0.6;
  box-shadow: 0 4px 12px -4px rgba(0, 0, 0, 0.03);
}

.agent-card.active {
  background: rgba(255, 255, 255, 0.85);
  border-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 12px 24px -6px rgba(0, 0, 0, 0.08);
  opacity: 1;
  transform: translateX(-4px);
}

.agent-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  margin-bottom: 8px;
}

.agent-card p {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin: 0;
  padding-left: 24px;
}

.flash-tag {
  animation: pulseOpacity 1.5s infinite;
  margin-left: auto;
}

@keyframes pulseOpacity {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.text-success {
  color: var(--color-success);
  margin-left: auto;
}

@media (max-width: 960px) {
  .loading-dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
