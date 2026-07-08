<template>
  <Teleport to="body">
    <transition name="modal">
      <div
          v-if="isGlobalProfileVisible"
          class="modal-overlay"
          @click="isGlobalProfileVisible = false"
      >
        <div class="modal-container" @click.stop>
          <header class="modal-header">
            <div class="header-left">
              <span class="header-kicker">LEARNING PROFILE</span>
              <h2>动态学习画像</h2>
              <p>系统将根据学习行为逐步完善 7 个核心维度，不提前展示缺乏依据的固定结论。</p>
            </div>

            <button class="modal-close-btn" @click="isGlobalProfileVisible = false">
              <component :is="XIcon" class="close-icon" />
            </button>
          </header>

          <main v-if="loading" class="modal-body loading-body">
            <div class="visual-skeleton"></div>
          </main>

          <main v-else class="modal-body">
            <section class="profile-visual-panel">
              <div class="visual-background">
                <span class="grid-layer"></span>
                <span class="glow glow-a"></span>
                <span class="glow glow-b"></span>
              </div>

              <div class="panel-top">
                <div>
                  <span class="panel-eyebrow">七维学习画像</span>
                  <h3>{{ portraitStage.title }}</h3>
                </div>
                <span class="stage-pill">{{ portraitStage.name }}</span>
              </div>

              <div class="portrait-stage">
                <svg class="connection-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
                  <line
                      v-for="node in orbitNodes"
                      :key="`line-${node.key}`"
                      x1="50"
                      y1="50"
                      :x2="node.x"
                      :y2="node.y"
                      class="connection-line"
                      :class="node.state"
                  />
                </svg>

                <div class="orbit-ring ring-outer"></div>
                <div class="orbit-ring ring-middle"></div>
                <div class="orbit-ring ring-inner"></div>

                <div class="profile-core">
                  <div class="core-aura"></div>
                  <div class="avatar-shell">
                    <div class="avatar-head"></div>
                    <div class="avatar-neck"></div>
                    <div class="avatar-body">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>

                  <div class="core-text">
                    <strong>{{ activeCount }}/7</strong>
                    <span>维度已成型</span>
                  </div>
                </div>

                <div
                    v-for="node in orbitNodes"
                    :key="node.key"
                    class="dimension-node"
                    :class="[node.state, { 'is-hovered': hoveredNodeKey === node.key }]"
                    :style="{
                    '--x': `${node.x}%`,
                    '--y': `${node.y}%`,
                    '--delay': `${node.delay}s`
                  }"
                    @mouseenter="hoveredNodeKey = node.key"
                    @mouseleave="hoveredNodeKey = null"
                >
                  <div class="node-card">
                    <div class="node-icon">{{ node.icon }}</div>

                    <div class="node-info">
                      <strong>{{ node.label }}</strong>
                      <span>{{ node.value || '等待画像沉淀' }}</span>
                    </div>

                    <span class="node-status">
                      {{ node.value ? '已成型' : node.evidence.length ? '成长中' : '待采样' }}
                    </span>
                  </div>

                  <transition name="popup-fade">
                    <div
                        v-if="hoveredNodeKey === node.key"
                        class="node-popup"
                        @click.stop
                    >
                      <div class="popup-title">
                        <strong>{{ node.label }}</strong>
                        <span>{{ node.tip }}</span>
                      </div>

                      <p v-if="node.value" class="popup-value">
                        {{ node.value }}
                      </p>
                      <p v-else class="popup-empty">
                        该维度还没有稳定结论，需要更多对话、练习、错题和学习反馈来完善。
                      </p>

                      <div v-if="node.evidence.length" class="popup-evidence">
                        <span>画像依据</span>
                        <p v-for="(item, index) in node.evidence.slice(0, 2)" :key="index">
                          {{ item }}
                        </p>
                      </div>
                    </div>
                  </transition>
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { XIcon } from '@lucide/vue'
import { getProfile, type ProfileData, type ProfileDimensionKey } from '@/features/profile/api/profile'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/features/profile/model/useGlobalProfile'
import type { DimensionValue } from '@/features/profile/model/profile'

const profile = ref<ProfileData | null>(null)
const loading = ref(false)
const hoveredNodeKey = ref<string | null>(null)

const DIM_CONFIG: Array<{
  key: ProfileDimensionKey
  label: string
  tip: string
  icon: string
}> = [
  { key: 'knowledge_level', label: '知识基础', tip: '已有知识储备与课程基础水平', icon: '基' },
  { key: 'cognitive_style', label: '认知风格', tip: '更适合的理解方式与讲解方式', icon: '认' },
  { key: 'weak_knowledge_points', label: '易错偏好', tip: '高频错误、薄弱概念与失分类型', icon: '错' },
  { key: 'knowledge_gap_pattern', label: '缺口模式', tip: '知识结构中的断点与前置缺失', icon: '缺' },
  { key: 'learning_goal_type', label: '目标导向', tip: '应试、实践、项目或系统掌握倾向', icon: '目' },
  { key: 'difficulty_tolerance', label: '难度耐受', tip: '可承受的学习坡度与题目难度', icon: '难' },
  { key: 'self_correction_ability', label: '自纠能力', tip: '发现问题、复盘问题和修正问题的能力', icon: '纠' }
]

const dimensionCards = computed(() => {
  const dims = (profile.value?.dimensions ?? {}) as Record<ProfileDimensionKey, DimensionValue>

  return DIM_CONFIG.map(config => {
    const valObj = dims[config.key] || { value: '', evidence: [] }

    return {
      key: config.key,
      label: config.label,
      tip: config.tip,
      icon: config.icon,
      value: valObj.value || '',
      evidence: valObj.evidence || []
    }
  })
})

const activeCount = computed(() => dimensionCards.value.filter(item => item.value).length)

const portraitStage = computed(() => {
  if (activeCount.value === 0) {
    return { name: '初始化采样', title: '画像正在从学习行为中生成' }
  }

  if (activeCount.value <= 2) {
    return { name: '画像萌芽期', title: '部分学习特征开始成型' }
  }

  if (activeCount.value <= 5) {
    return { name: '画像成长中', title: '核心学习画像正在完善' }
  }

  return { name: '画像已稳定', title: '七维学习画像趋于完整' }
})

const orbitNodes = computed(() => {
  const radiusX = 41
  const radiusY = 35

  return dimensionCards.value.map((dim, index) => {
    const angle = -90 + index * (360 / DIM_CONFIG.length)
    const radian = (angle * Math.PI) / 180
    const hasEvidence = dim.evidence.length > 0

    return {
      ...dim,
      x: 50 + radiusX * Math.cos(radian),
      y: 50 + radiusY * Math.sin(radian),
      delay: index * 0.12,
      state: dim.value ? 'is-active' : hasEvidence ? 'is-growing' : 'is-pending'
    }
  })
})

const fetchProfile = async () => {
  loading.value = true

  try {
    const res = await getProfile()
    profile.value = res.data.data
  } catch (error) {
    console.error('Failed to fetch profile', error)
    profile.value = null
  } finally {
    loading.value = false
  }
}

watch(isGlobalProfileVisible, newVal => {
  if (newVal) {
    fetchProfile()
  }
})

watch(profileRefreshTrigger, () => {
  if (isGlobalProfileVisible.value) {
    fetchProfile()
  }
})
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-fast) ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container {
  transition: transform var(--transition-base), opacity var(--transition-fast) ease;
}

.modal-leave-active .modal-container {
  transition: transform var(--transition-fast), opacity var(--transition-fast) ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: translateY(16px) scale(0.995);
  opacity: 0;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-5);
  background: rgba(18, 38, 46, 0.24);
  backdrop-filter: blur(12px);
}

.modal-container {
  width: min(1120px, 95vw);
  height: min(760px, 90dvh);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.modal-header {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6) var(--space-4);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border-light);
}

.header-kicker {
  display: inline-flex;
  align-items: center;
  color: var(--color-primary-text);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: var(--weight-bold);
  letter-spacing: 0.12em;
}

.header-left h2 {
  margin: var(--space-1) 0 var(--space-0_5);
  color: var(--color-text-strong);
  font-size: var(--text-lg);
  font-weight: var(--weight-extrabold);
  letter-spacing: -0.03em;
}

.header-left p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.modal-close-btn {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  transition: var(--btn-transition);
  cursor: pointer;
}

.modal-close-btn:hover {
  color: var(--color-text-strong);
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
}

.close-icon {
  width: 15px;
  height: 15px;
}

.modal-body {
  flex: 1;
  min-height: 0;
  padding: var(--space-5) var(--space-6) var(--space-6);
  background:
      radial-gradient(circle at 20% 15%, var(--color-primary-soft), transparent 28%),
      linear-gradient(180deg, var(--color-bg), var(--color-surface));
  overflow: hidden;
}

.profile-visual-panel {
  position: relative;
  height: 100%;
  min-height: 560px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xs);
}

.visual-background,
.grid-layer,
.glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-layer {
  opacity: 0.42;
  background-image:
      linear-gradient(var(--color-border-light) 1px, transparent 1px),
      linear-gradient(90deg, var(--color-border-light) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: radial-gradient(circle at center, #000 24%, transparent 78%);
}

.glow {
  border-radius: 50%;
  filter: blur(18px);
  opacity: 0.55;
}

.glow-a {
  left: 10%;
  top: 10%;
  width: 220px;
  height: 220px;
  background: var(--color-primary-soft);
}

.glow-b {
  left: auto;
  right: 8%;
  top: 38%;
  width: 260px;
  height: 260px;
  background: rgba(100, 180, 255, 0.14);
}

.panel-top {
  position: relative;
  z-index: 5;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-5) 0;
}

.panel-eyebrow {
  color: var(--color-primary-text);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: var(--weight-bold);
  letter-spacing: 0.12em;
}

.panel-top h3 {
  margin: var(--space-1) 0 0;
  color: var(--color-text-strong);
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
}

.stage-pill {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 var(--space-3);
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: var(--weight-bold);
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-pill);
}

.portrait-stage {
  position: absolute;
  inset: 64px var(--space-5) var(--space-5);
}

.connection-svg {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.connection-line {
  stroke: var(--color-border-hover);
  stroke-width: 0.16;
  stroke-dasharray: 1.2 1.8;
  opacity: 0.5;
}

.connection-line.is-active {
  stroke: var(--color-primary);
  opacity: 0.85;
}

.connection-line.is-growing {
  stroke: var(--color-primary);
  opacity: 0.48;
}

.orbit-ring {
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 1;
  border-radius: 50%;
  border: 1px solid var(--color-border-light);
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.ring-outer {
  width: min(720px, 88%);
  height: min(440px, 76%);
  animation: ringFloat 12s ease-in-out infinite;
}

.ring-middle {
  width: min(520px, 65%);
  height: min(320px, 54%);
  opacity: 0.7;
  animation: ringFloat 10s ease-in-out infinite reverse;
}

.ring-inner {
  width: min(310px, 40%);
  height: min(210px, 34%);
  opacity: 0.55;
}

.profile-core {
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 4;
  width: 190px;
  height: 230px;
  transform: translate(-50%, -50%);
  display: grid;
  place-items: center;
}

.core-aura {
  position: absolute;
  width: 210px;
  height: 210px;
  border-radius: 50%;
  background:
      radial-gradient(circle, var(--color-primary-soft) 0%, rgba(255, 255, 255, 0.82) 48%, transparent 72%);
  border: 1px solid var(--color-primary-border);
  animation: auraPulse 3.8s ease-in-out infinite;
}

.avatar-shell {
  position: relative;
  z-index: 2;
  width: 120px;
  height: 154px;
  display: flex;
  flex-direction: column;
  align-items: center;
  filter: drop-shadow(0 16px 28px rgba(32, 95, 103, 0.1));
}

.avatar-head {
  width: 62px;
  height: 62px;
  border-radius: 24px 24px 28px 28px;
  background:
      linear-gradient(135deg, var(--color-surface), var(--color-primary-soft));
  border: 1px solid var(--color-primary-border);
}

.avatar-neck {
  width: 30px;
  height: 14px;
  margin-top: -2px;
  background: var(--color-surface);
  border-left: 1px solid var(--color-primary-border);
  border-right: 1px solid var(--color-primary-border);
}

.avatar-body {
  width: 112px;
  height: 76px;
  padding: var(--space-4) var(--space-4) 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
  align-items: center;
  border-radius: 34px 34px 24px 24px;
  background:
      linear-gradient(180deg, var(--color-surface), var(--color-bg));
  border: 1px solid var(--color-border-light);
}

.avatar-body span {
  display: block;
  height: 4px;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
}

.avatar-body span:nth-child(1) {
  width: 64px;
}

.avatar-body span:nth-child(2) {
  width: 46px;
  opacity: 0.7;
}

.avatar-body span:nth-child(3) {
  width: 28px;
  opacity: 0.45;
}

.core-text {
  position: absolute;
  z-index: 3;
  left: 50%;
  bottom: -4px;
  min-width: 104px;
  padding: var(--space-2) var(--space-3);
  text-align: center;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-xs);
  transform: translateX(-50%);
}

.core-text strong {
  display: block;
  color: var(--color-text-strong);
  font-family: var(--font-mono);
  font-size: 16px;
  line-height: 1;
}

.core-text span {
  display: block;
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 11px;
  white-space: nowrap;
}

.dimension-node {
  position: absolute;
  left: var(--x);
  top: var(--y);
  z-index: 5;
  transform: translate(-50%, -50%);
  animation: nodeFloat 3.4s ease-in-out infinite;
  animation-delay: var(--delay);
  cursor: pointer;
}

.dimension-node.is-hovered {
  z-index: 20;
  animation-play-state: paused;
}

.node-card {
  width: 188px;
  min-height: 74px;
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: var(--space-2_5);
  align-items: center;
  padding: var(--space-3);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: 0 10px 26px rgba(32, 95, 103, 0.06);
  transition: transform var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.dimension-node:hover .node-card {
  transform: translateY(-3px);
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-md);
}

.node-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: var(--color-text-muted);
  font-size: 17px;
  font-weight: var(--weight-extrabold);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 16px;
}

.is-active .node-icon {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
}

.is-growing .node-icon {
  color: var(--color-primary-text);
  background: rgba(255, 255, 255, 0.9);
  border-color: var(--color-primary-border);
}

.node-info {
  min-width: 0;
}

.node-info strong {
  display: block;
  color: var(--color-text-strong);
  font-size: 13px;
  font-weight: var(--weight-bold);
}

.node-info span {
  display: -webkit-box;
  margin-top: 3px;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 1.35;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.is-pending .node-info span {
  color: var(--color-text-faint);
}

.node-status {
  grid-column: 1 / -1;
  justify-self: start;
  height: 20px;
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-2);
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: var(--weight-bold);
  background: var(--color-bg);
  border-radius: var(--radius-pill);
}

.is-active .node-status {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
}

.is-growing .node-status {
  color: var(--color-primary-text);
  background: rgba(70, 184, 180, 0.12);
}

.node-popup {
  position: absolute;
  left: 50%;
  top: calc(100% + 10px);
  width: 260px;
  padding: var(--space-3) var(--space-3_5);
  background: var(--color-surface);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  transform: translateX(-50%);
}

.popup-title {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
}

.popup-title strong {
  color: var(--color-text-strong);
  font-size: 12px;
}

.popup-title span {
  color: var(--color-text-muted);
  font-size: 10px;
  text-align: right;
}

.popup-value,
.popup-empty {
  margin: var(--space-2) 0 0;
  color: var(--color-text);
  font-size: 12px;
  line-height: var(--leading-normal);
}

.popup-empty {
  color: var(--color-text-faint);
}

.popup-evidence {
  margin-top: var(--space-2_5);
  padding-top: var(--space-2);
  border-top: 1px dashed var(--color-border-light);
}

.popup-evidence span {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-primary-text);
  font-size: 10px;
  font-weight: var(--weight-bold);
}

.popup-evidence p {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 1.4;
}

.popup-fade-enter-active {
  transition: all 0.2s cubic-bezier(0.32, 0.72, 0, 1);
}

.popup-fade-leave-active {
  transition: all 0.14s cubic-bezier(0.32, 0.72, 0, 1);
}

.popup-fade-enter-from,
.popup-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-5px);
}

.loading-body {
  display: grid;
  place-items: stretch;
}

.visual-skeleton {
  min-height: 560px;
  border-radius: var(--radius-xl);
  background:
      linear-gradient(90deg, var(--color-bg), var(--color-surface-hover), var(--color-bg));
  background-size: 200% 100%;
  animation: skeleton 1.5s ease-in-out infinite;
}

@keyframes nodeFloat {
  0%,
  100% {
    margin-top: 0;
  }

  50% {
    margin-top: -8px;
  }
}

@keyframes auraPulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.82;
  }

  50% {
    transform: scale(1.06);
    opacity: 1;
  }
}

@keyframes ringFloat {
  0%,
  100% {
    transform: translate(-50%, -50%) rotate(0deg);
  }

  50% {
    transform: translate(-50%, -50%) rotate(1.5deg);
  }
}

@keyframes skeleton {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -100% 0;
  }
}

@media (max-width: 980px) {
  .modal-container {
    width: 96vw;
    height: 92dvh;
  }

  .portrait-stage {
    inset: 72px var(--space-4) var(--space-4);
  }

  .dimension-node {
    transform: translate(-50%, -50%) scale(0.92);
  }

  .node-card {
    width: 172px;
  }
}

@media (max-width: 720px) {
  .modal-overlay {
    padding: var(--space-2);
  }

  .modal-container {
    height: 94dvh;
    border-radius: var(--radius-lg);
  }

  .modal-header {
    padding: var(--space-4);
  }

  .modal-body {
    padding: var(--space-4);
    overflow-y: auto;
  }

  .profile-visual-panel {
    min-height: 760px;
  }

  .portrait-stage {
    position: relative;
    inset: auto;
    height: 670px;
    margin: var(--space-4);
  }

  .panel-top {
    flex-direction: column;
    padding: var(--space-4) var(--space-4) 0;
  }

  .profile-core {
    top: 48%;
    transform: translate(-50%, -50%) scale(0.86);
  }

  .dimension-node {
    transform: translate(-50%, -50%) scale(0.82);
  }

  .node-popup {
    width: 230px;
  }
}
</style>