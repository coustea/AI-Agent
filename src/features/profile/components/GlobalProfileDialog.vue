<template>
  <Teleport to="body">
    <transition name="modal">
      <div
        v-if="isGlobalProfileVisible"
        class="modal-overlay"
        @click="closeProfile"
      >
        <div class="modal-container" @click.stop>
          <main v-if="loading" class="modal-body loading-body">
            <div class="visual-skeleton"></div>
          </main>

          <main v-else class="modal-body">
            <div class="dialog-frame">
              <button
                type="button"
                class="floating-close-btn"
                aria-label="关闭学习画像"
                @click="closeProfile"
              >
                <component :is="XIcon" class="close-icon" />
              </button>

              <div class="dialog-switcher" role="tablist" aria-label="动态特征与学习评估">
                <button
                  type="button"
                  role="tab"
                  :aria-selected="activePanel === 'profile'"
                  :class="{ active: activePanel === 'profile' }"
                  @click="activePanel = 'profile'"
                >
                  动态特征
                </button>
                <button
                  type="button"
                  role="tab"
                  :aria-selected="activePanel === 'assessment'"
                  :class="{ active: activePanel === 'assessment' }"
                  @click="activePanel = 'assessment'"
                >
                  学习评估
                </button>
              </div>

              <section v-if="activePanel === 'profile'" class="profile-visual-panel">

              <div class="visual-background">
                <span class="grid-layer"></span>
                <span class="glow glow-a"></span>
                <span class="glow glow-b"></span>
              </div>

              <div class="portrait-stage">
                <svg
                  class="connection-svg"
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                >
                  <line
                    v-for="node in orbitNodes"
                    :key="`line-${node.key}`"
                    x1="50"
                    y1="50"
                    :x2="node.x"
                    :y2="node.y"
                    class="connection-line"
                    :class="[
                      node.state,
                      {
                        'is-highlighted': hoveredNodeKey === node.key
                      }
                    ]"
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
                  :class="[
                    node.state,
                    {
                      'is-hovered': hoveredNodeKey === node.key
                    }
                  ]"
                  :style="{
                    '--x': `${node.x}%`,
                    '--y': `${node.y}%`,
                    '--delay': `${node.delay}s`
                  }"
                  @mouseenter="hoveredNodeKey = node.key"
                  @mouseleave="hoveredNodeKey = null"
                >
                  <div class="node-card">
                    <div class="node-icon">
                      {{ node.icon }}
                    </div>

                    <div class="node-info">
                      <strong>{{ node.label }}</strong>

                      <span>
                        {{ node.value || '等待画像沉淀' }}
                      </span>
                    </div>

                    <span class="node-status">
                      {{
                        node.value
                          ? '已成型'
                          : node.evidence.length
                            ? '成长中'
                            : '待采样'
                      }}
                    </span>
                  </div>

                  <transition name="popup-fade">
                    <div
                      v-if="hoveredNodeKey === node.key"
                      class="node-popup"
                      :class="node.popupPlacement"
                      @click.stop
                    >
                      <div class="popup-title">
                        <strong>{{ node.label }}</strong>
                        <span>{{ node.tip }}</span>
                      </div>

                      <p
                        v-if="node.value"
                        class="popup-value"
                      >
                        {{ node.value }}
                      </p>

                      <p
                        v-else
                        class="popup-empty"
                      >
                        该维度还没有稳定结论，需要更多对话、练习、错题和学习反馈来完善。
                      </p>

                      <div
                        v-if="node.evidence.length"
                        class="popup-evidence"
                      >
                        <span>画像依据</span>

                        <p
                          v-for="(item, index) in node.evidence.slice(0, 2)"
                          :key="index"
                        >
                          {{ item }}
                        </p>
                      </div>
                    </div>
                  </transition>
                </div>
              </div>
              </section>

              <LearningAssessmentPanel
                v-else
                class="assessment-embedded-panel"
              />
            </div>
          </main>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { XIcon } from '@lucide/vue'

import {
  getProfile,
  type ProfileData,
  type ProfileDimensionKey
} from '@/features/profile/api/profile'

import {
  isGlobalProfileVisible,
  profileRefreshTrigger
} from '@/features/profile/model/useGlobalProfile'

import type { DimensionValue } from '@/features/profile/model/profile'
import LearningAssessmentPanel from '@/features/profile/components/LearningAssessmentPanel.vue'

type PopupPlacement =
  | 'popup-above'
  | 'popup-below'
  | 'popup-left'
  | 'popup-right'

const profile = ref<ProfileData | null>(null)
const loading = ref(false)
const hoveredNodeKey = ref<ProfileDimensionKey | null>(null)
const activePanel = ref<'profile' | 'assessment'>('profile')

const DIM_CONFIG: Array<{
  key: ProfileDimensionKey
  label: string
  tip: string
  icon: string
}> = [
  {
    key: 'knowledge_level',
    label: '知识基础',
    tip: '已有知识储备与课程基础水平',
    icon: '基'
  },
  {
    key: 'cognitive_style',
    label: '认知风格',
    tip: '更适合的理解方式与讲解方式',
    icon: '认'
  },
  {
    key: 'weak_knowledge_points',
    label: '易错偏好',
    tip: '高频错误、薄弱概念与失分类型',
    icon: '错'
  },
  {
    key: 'knowledge_gap_pattern',
    label: '缺口模式',
    tip: '知识结构中的断点与前置缺失',
    icon: '缺'
  },
  {
    key: 'learning_goal_type',
    label: '目标导向',
    tip: '应试、实践、项目或系统掌握倾向',
    icon: '目'
  },
  {
    key: 'difficulty_tolerance',
    label: '难度耐受',
    tip: '可承受的学习坡度与题目难度',
    icon: '难'
  },
  {
    key: 'self_correction_ability',
    label: '自纠能力',
    tip: '发现问题、复盘问题和修正问题的能力',
    icon: '纠'
  }
]

const dimensionCards = computed(() => {
  const dimensions = (profile.value?.dimensions ?? {}) as Record<
    ProfileDimensionKey,
    DimensionValue
  >

  return DIM_CONFIG.map(config => {
    const dimensionValue = dimensions[config.key] ?? {
      value: '',
      evidence: []
    }

    return {
      key: config.key,
      label: config.label,
      tip: config.tip,
      icon: config.icon,
      value: dimensionValue.value || '',
      evidence: dimensionValue.evidence || []
    }
  })
})

const activeCount = computed(() => {
  return dimensionCards.value.filter(item => Boolean(item.value)).length
})

const getPopupPlacement = (
  x: number,
  y: number
): PopupPlacement => {
  /*
   * 顶部节点向下展开。
   * 底部节点向上展开。
   * 左侧节点向右展开。
   * 右侧节点向左展开。
   *
   * 这样弹层始终朝向画布内部，不会被四周边界裁切。
   */
  if (y <= 22) {
    return 'popup-below'
  }

  if (y >= 72) {
    return 'popup-above'
  }

  if (x <= 30) {
    return 'popup-right'
  }

  if (x >= 70) {
    return 'popup-left'
  }

  return y >= 50
    ? 'popup-above'
    : 'popup-below'
}

const orbitNodes = computed(() => {
  const radiusX = 40
  const radiusY = 35

  return dimensionCards.value.map((dimension, index) => {
    const angle = -90 + index * (360 / DIM_CONFIG.length)
    const radian = (angle * Math.PI) / 180
    const hasEvidence = dimension.evidence.length > 0

    const x = 50 + radiusX * Math.cos(radian)
    const y = 50 + radiusY * Math.sin(radian)

    return {
      ...dimension,
      x,
      y,
      delay: index * 0.12,

      state: dimension.value
        ? 'is-active'
        : hasEvidence
          ? 'is-growing'
          : 'is-pending',

      popupPlacement: getPopupPlacement(x, y)
    }
  })
})

const closeProfile = () => {
  hoveredNodeKey.value = null
  activePanel.value = 'profile'
  isGlobalProfileVisible.value = false
}

const fetchProfile = async () => {
  loading.value = true

  try {
    const response = await getProfile()
    profile.value = response.data.data
  } catch (error) {
    console.error('Failed to fetch profile', error)
    profile.value = null
  } finally {
    loading.value = false
  }
}

watch(isGlobalProfileVisible, visible => {
  if (visible) {
    activePanel.value = 'profile'
    fetchProfile()
  } else {
    hoveredNodeKey.value = null
    activePanel.value = 'profile'
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
  transition:
    transform var(--transition-base),
    opacity var(--transition-fast) ease;
}

.modal-leave-active .modal-container {
  transition:
    transform var(--transition-fast),
    opacity var(--transition-fast) ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  opacity: 0;
  transform: translateY(16px) scale(0.995);
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
  width: min(1240px, 96vw);
  height: min(820px, 92dvh);

  display: flex;
  flex-direction: column;

  overflow: hidden;

  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
}

.modal-body {
  flex: 1;
  min-height: 0;

  padding: var(--space-5);

  overflow: hidden;

  background:
    radial-gradient(
      circle at 20% 15%,
      var(--color-primary-soft),
      transparent 28%
    ),
    linear-gradient(
      180deg,
      var(--color-bg),
      var(--color-surface)
    );
}

.dialog-frame {
  position: relative;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--space-3);
}

.dialog-switcher {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-self: start;
  gap: var(--space-1);
  padding: var(--space-1);
  padding-right: 48px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
}

.dialog-switcher button {
  min-width: 96px;
  min-height: 32px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: var(--weight-bold);
  transition:
    background var(--transition-fast),
    color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.dialog-switcher button:hover {
  color: var(--color-text-strong);
  background: var(--color-bg);
}

.dialog-switcher button.active {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  box-shadow: inset 0 0 0 1px var(--color-primary-border);
}

.loading-body {
  display: grid;
  place-items: stretch;
}

.profile-visual-panel {
  position: relative;

  width: 100%;
  height: 100%;
  min-height: 0;

  overflow: hidden;

  background: rgba(255, 255, 255, 0.84);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xs);
}

.assessment-embedded-panel {
  min-height: 0;
}

.floating-close-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  z-index: 100;

  width: 34px;
  height: 34px;

  display: grid;
  place-items: center;

  padding: 0;

  color: var(--color-text-muted);
  cursor: pointer;

  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);

  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);

  box-shadow: var(--shadow-xs);

  transition:
    color var(--transition-fast),
    background var(--transition-fast),
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.floating-close-btn:hover {
  color: var(--color-text-strong);
  background: var(--color-surface);
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-sm);
}

.floating-close-btn:focus-visible {
  outline: 2px solid var(--color-primary-border);
  outline-offset: 2px;
}

.close-icon {
  width: 15px;
  height: 15px;
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
    linear-gradient(
      var(--color-border-light) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      var(--color-border-light) 1px,
      transparent 1px
    );

  background-size: 34px 34px;

  mask-image:
    radial-gradient(
      circle at center,
      #000 24%,
      transparent 78%
    );
}

.glow {
  border-radius: 50%;
  filter: blur(18px);
  opacity: 0.55;
}

.glow-a {
  top: 8%;
  left: 9%;

  width: 230px;
  height: 230px;

  background: var(--color-primary-soft);
}

.glow-b {
  top: 36%;
  right: 7%;
  left: auto;

  width: 270px;
  height: 270px;

  background: rgba(100, 180, 255, 0.14);
}

.portrait-stage {
  position: absolute;
  inset: 18px;
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

  transition:
    stroke-width var(--transition-fast),
    opacity var(--transition-fast);
}

.connection-line.is-active {
  stroke: var(--color-primary);
  opacity: 0.85;
}

.connection-line.is-growing {
  stroke: var(--color-primary);
  opacity: 0.48;
}

.connection-line.is-highlighted {
  stroke-width: 0.25;
  opacity: 1;
}

.orbit-ring {
  position: absolute;

  top: 50%;
  left: 50%;
  z-index: 1;

  border: 1px solid var(--color-border-light);
  border-radius: 50%;

  transform: translate(-50%, -50%);
  pointer-events: none;
}

.ring-outer {
  width: min(760px, 88%);
  height: min(460px, 76%);

  animation: ringFloat 12s ease-in-out infinite;
}

.ring-middle {
  width: min(550px, 65%);
  height: min(330px, 54%);

  opacity: 0.7;

  animation: ringFloat 10s ease-in-out infinite reverse;
}

.ring-inner {
  width: min(320px, 40%);
  height: min(215px, 34%);

  opacity: 0.55;
}

.profile-core {
  position: absolute;

  top: 50%;
  left: 50%;
  z-index: 4;

  width: 190px;
  height: 230px;

  display: grid;
  place-items: center;

  transform: translate(-50%, -50%);
}

.core-aura {
  position: absolute;

  width: 210px;
  height: 210px;

  background:
    radial-gradient(
      circle,
      var(--color-primary-soft) 0%,
      rgba(255, 255, 255, 0.82) 48%,
      transparent 72%
    );

  border: 1px solid var(--color-primary-border);
  border-radius: 50%;

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

  filter:
    drop-shadow(
      0 16px 28px
      rgba(32, 95, 103, 0.1)
    );
}

.avatar-head {
  width: 62px;
  height: 62px;

  background:
    linear-gradient(
      135deg,
      var(--color-surface),
      var(--color-primary-soft)
    );

  border: 1px solid var(--color-primary-border);
  border-radius: 24px 24px 28px 28px;
}

.avatar-neck {
  width: 30px;
  height: 14px;

  margin-top: -2px;

  background: var(--color-surface);

  border-right: 1px solid var(--color-primary-border);
  border-left: 1px solid var(--color-primary-border);
}

.avatar-body {
  width: 112px;
  height: 76px;

  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;

  padding:
    var(--space-4)
    var(--space-4)
    0;

  background:
    linear-gradient(
      180deg,
      var(--color-surface),
      var(--color-bg)
    );

  border: 1px solid var(--color-border-light);
  border-radius: 34px 34px 24px 24px;
}

.avatar-body span {
  display: block;

  height: 4px;

  background: var(--color-primary);
  border-radius: var(--radius-pill);
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

  bottom: -4px;
  left: 50%;
  z-index: 3;

  min-width: 104px;

  padding:
    var(--space-2)
    var(--space-3);

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

  top: var(--y);
  left: var(--x);
  z-index: 5;

  cursor: pointer;

  transform: translate(-50%, -50%);

  animation: nodeFloat 3.4s ease-in-out infinite;
  animation-delay: var(--delay);
}

.dimension-node.is-hovered {
  z-index: 50;
  animation-play-state: paused;
}

.node-card {
  width: 188px;
  min-height: 74px;

  display: grid;
  grid-template-columns: 44px 1fr;
  align-items: center;
  gap: var(--space-2_5);

  padding: var(--space-3);

  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);

  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);

  box-shadow:
    0 10px 26px
    rgba(32, 95, 103, 0.06);

  transition:
    transform var(--transition-fast),
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.dimension-node:hover .node-card {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-md);

  transform: translateY(-3px);
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

  overflow: hidden;

  color: var(--color-text-secondary);

  font-size: 11px;
  line-height: 1.35;

  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
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
  z-index: 80;

  width: 330px;

  padding:
    18px
    20px;

  background: var(--color-surface);

  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-lg);

  box-shadow:
    0 18px 48px
    rgba(32, 95, 103, 0.16);
}

/* 连接节点和详情框之间的透明悬浮区域，避免鼠标移动时弹层消失 */
.node-popup::before {
  position: absolute;
  content: '';
}

/* 上方节点：详情框向下展开 */
.popup-below {
  top: calc(100% + 14px);
  left: 50%;

  transform: translateX(-50%);
}

.popup-below::before {
  right: 0;
  bottom: 100%;
  left: 0;

  height: 16px;
}

/* 下方节点：详情框向上展开 */
.popup-above {
  bottom: calc(100% + 14px);
  left: 50%;

  transform: translateX(-50%);
}

.popup-above::before {
  top: 100%;
  right: 0;
  left: 0;

  height: 16px;
}

/* 左侧节点：详情框向右展开 */
.popup-right {
  top: 50%;
  left: calc(100% + 14px);

  transform: translateY(-50%);
}

.popup-right::before {
  top: 0;
  right: 100%;
  bottom: 0;

  width: 16px;
}

/* 右侧节点：详情框向左展开 */
.popup-left {
  top: 50%;
  right: calc(100% + 14px);

  transform: translateY(-50%);
}

.popup-left::before {
  top: 0;
  bottom: 0;
  left: 100%;

  width: 16px;
}

.popup-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;

  padding-bottom: 14px;

  border-bottom: 1px solid var(--color-border-light);
}

.popup-title strong {
  flex: 0 0 auto;

  color: var(--color-text-strong);

  font-size: 13px;
  line-height: 1.5;
}

.popup-title span {
  color: var(--color-text-muted);

  font-size: 11px;
  line-height: 1.55;
  text-align: right;
}

.popup-value,
.popup-empty {
  margin: 14px 0 0;

  color: var(--color-text);

  font-size: 12px;
  line-height: 1.7;
}

.popup-empty {
  color: var(--color-text-faint);
}

.popup-evidence {
  margin-top: 16px;
  padding-top: 14px;

  border-top: 1px dashed var(--color-border-light);
}

.popup-evidence span {
  display: block;

  margin-bottom: 8px;

  color: var(--color-primary-text);

  font-size: 10px;
  font-weight: var(--weight-bold);
}

.popup-evidence p {
  margin: 7px 0 0;

  color: var(--color-text-secondary);

  font-size: 11px;
  line-height: 1.55;
}

.popup-fade-enter-active,
.popup-fade-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.popup-below.popup-fade-enter-from,
.popup-below.popup-fade-leave-to {
  opacity: 0;

  transform:
    translateX(-50%)
    translateY(-6px);
}

.popup-above.popup-fade-enter-from,
.popup-above.popup-fade-leave-to {
  opacity: 0;

  transform:
    translateX(-50%)
    translateY(6px);
}

.popup-right.popup-fade-enter-from,
.popup-right.popup-fade-leave-to {
  opacity: 0;

  transform:
    translateY(-50%)
    translateX(-6px);
}

.popup-left.popup-fade-enter-from,
.popup-left.popup-fade-leave-to {
  opacity: 0;

  transform:
    translateY(-50%)
    translateX(6px);
}

.visual-skeleton {
  min-height: 100%;

  background:
    linear-gradient(
      90deg,
      var(--color-bg),
      var(--color-surface-hover),
      var(--color-bg)
    );

  background-size: 200% 100%;

  border-radius: var(--radius-xl);

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
    opacity: 0.82;
    transform: scale(1);
  }

  50% {
    opacity: 1;
    transform: scale(1.06);
  }
}

@keyframes ringFloat {
  0%,
  100% {
    transform:
      translate(-50%, -50%)
      rotate(0deg);
  }

  50% {
    transform:
      translate(-50%, -50%)
      rotate(1.5deg);
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
    inset: 16px;
  }

  .dimension-node {
    transform:
      translate(-50%, -50%)
      scale(0.9);
  }

  .node-card {
    width: 172px;
  }

  .node-popup {
    width: 300px;

    padding:
      17px
      18px;
  }
}

@media (max-width: 720px) {
  .modal-overlay {
    padding: var(--space-2);
  }

  .modal-container {
    height: 95dvh;

    border-radius: var(--radius-lg);
  }

  .modal-body {
    padding: var(--space-3);

    overflow-y: auto;
  }

  .profile-visual-panel {
    min-height: 760px;
  }

  .floating-close-btn {
    top: 14px;
    right: 14px;
  }

  .portrait-stage {
    position: relative;
    inset: auto;

    height: 730px;

    margin: var(--space-2);
  }

  .profile-core {
    top: 50%;

    transform:
      translate(-50%, -50%)
      scale(0.82);
  }

  .dimension-node {
    transform:
      translate(-50%, -50%)
      scale(0.75);
  }

  .node-popup {
    position: fixed;

    top: 50%;
    right: auto;
    bottom: auto;
    left: 50%;
    z-index: 1200;

    width: min(330px, calc(100vw - 32px));
    max-height: 70dvh;

    overflow-y: auto;

    transform: translate(-50%, -50%);
  }

  .node-popup::before {
    display: none;
  }

  .popup-below.popup-fade-enter-from,
  .popup-below.popup-fade-leave-to,
  .popup-above.popup-fade-enter-from,
  .popup-above.popup-fade-leave-to,
  .popup-right.popup-fade-enter-from,
  .popup-right.popup-fade-leave-to,
  .popup-left.popup-fade-enter-from,
  .popup-left.popup-fade-leave-to {
    opacity: 0;

    transform:
      translate(-50%, -48%)
      scale(0.98);
  }
}

@media (prefers-reduced-motion: reduce) {
  .dimension-node,
  .ring-outer,
  .ring-middle,
  .core-aura,
  .visual-skeleton {
    animation: none !important;
  }
}
</style>
