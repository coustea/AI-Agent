<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  isRunActive,
  type RunState,
  type RunStep,
} from '@/features/chat/types/chatEvent'

const props = defineProps<{
  run: RunState
}>()

const active = computed(() => isRunActive(props.run))
const thinkingSteps = computed<RunStep[]>(() =>
  (props.run.steps || []).filter(s => s.kind === 'thinking'),
)

// 当有思考步骤，或者当前正处于思考阶段时展示思考卡片
const hasThinking = computed(() =>
  thinkingSteps.value.length > 0 || (active.value && props.run.phase === 'thinking'),
)

// 用户手动切换展开/折叠状态；null 表示采用系统智能默认策略
const userToggled = ref<boolean | null>(null)

// 智能折叠策略：
// 1. 如果用户手动切换过，听从用户的意愿；
// 2. 思考中且尚未输出回答正文时：默认展开；
// 3. 一旦开始输出正文或回答完成：自动折叠为单行轻量胶囊，聚焦正文阅读。
const isExpanded = computed(() => {
  if (userToggled.value !== null) return userToggled.value
  if (active.value) {
    if (Boolean(props.run.content?.trim())) {
      return false
    }
    return true
  }
  return false
})

const toggleExpanded = () => {
  userToggled.value = !isExpanded.value
}

// 实时计时器：运行中平滑刷新
const liveTickMs = ref(0)
let timerId: ReturnType<typeof setInterval> | null = null
let localStartMs = Date.now()

const stopTimer = () => {
  if (timerId !== null) {
    clearInterval(timerId)
    timerId = null
  }
}

const startTimer = () => {
  stopTimer()
  const baseElapsed = props.run.total_elapsed_ms || 0
  localStartMs = Date.now() - baseElapsed
  liveTickMs.value = baseElapsed
  timerId = setInterval(() => {
    liveTickMs.value = Math.max(baseElapsed, Date.now() - localStartMs)
  }, 120)
}

watch(
  active,
  (isActive) => {
    if (isActive) {
      startTimer()
    } else {
      stopTimer()
      liveTickMs.value = props.run.total_elapsed_ms || liveTickMs.value
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopTimer()
})

const formatDuration = (ms?: number | null): string => {
  const val = Math.max(0, Number(ms || 0))
  if (!val) return ''
  if (val < 1000) return `${val}ms`
  const sec = val / 1000
  if (sec < 60) return `${sec.toFixed(1)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}

const thinkingDurationText = computed(() => {
  // 累计所有思考步骤的耗时，若正在思考中则使用实时计时
  const totalStepMs = thinkingSteps.value.reduce((acc, cur) => acc + (cur.elapsed_ms || 0), 0)
  if (active.value && props.run.phase === 'thinking') {
    return formatDuration(Math.max(liveTickMs.value, totalStepMs))
  }
  return formatDuration(totalStepMs || props.run.total_elapsed_ms || 0)
})

const currentRunningStep = computed(() =>
  thinkingSteps.value.find(s => s.status === 'running'),
)

const summaryText = computed(() => {
  if (active.value && props.run.phase === 'thinking') {
    return currentRunningStep.value?.title || props.run.phase_label || '正在深度思考与规划方案...'
  }
  const count = thinkingSteps.value.length
  if (count > 0) {
    return `已深度思考 · ${count} 轮推演`
  }
  return '已完成深度思考'
})
</script>

<template>
  <div v-if="hasThinking" class="thinking-block-wrapper" aria-live="polite">
    <div
      class="thinking-card"
      :class="{
        'is-active': active && run.phase === 'thinking',
        'is-collapsed': !isExpanded,
        'is-expanded': isExpanded,
      }"
    >
      <!-- 胶囊头部栏（可点击折叠/展开） -->
      <button
        type="button"
        class="thinking-header-btn"
        :aria-expanded="isExpanded"
        @click="toggleExpanded"
      >
        <div class="header-left">
          <!-- 思考中动态脉冲或完成态微光勾选 -->
          <span v-if="active && run.phase === 'thinking'" class="thinking-icon is-spinning" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.6" stroke-dasharray="10 20" stroke-linecap="round" />
            </svg>
          </span>
          <span v-else class="thinking-icon is-done" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M3.5 8.2 6.6 11.3 12.5 4.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>

          <span class="thinking-summary" :class="{ 'is-shimmer': active && run.phase === 'thinking' }">
            {{ summaryText }}
          </span>
        </div>

        <div class="header-right">
          <span v-if="thinkingDurationText" class="thinking-duration-pill">
            {{ thinkingDurationText }}
          </span>
          <span class="chevron-icon" :class="{ 'is-open': isExpanded }" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M4.5 6.2 8 9.8l3.5-3.6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
        </div>
      </button>

      <!-- 展开后的思考过程推演列表 -->
      <div v-if="isExpanded && thinkingSteps.length > 0" class="thinking-content">
        <ol class="thinking-steps-list">
          <li
            v-for="(step, idx) in thinkingSteps"
            :key="step.step_id || idx"
            class="thinking-step-item"
            :class="`is-${step.status}`"
          >
            <div class="step-marker">
              <span v-if="step.status === 'running'" class="marker-dot is-pulse"></span>
              <span v-else-if="step.status === 'completed'" class="marker-dot is-check">✓</span>
              <span v-else class="marker-dot">{{ idx + 1 }}</span>
            </div>
            <div class="step-detail">
              <div class="step-heading">
                <strong class="step-title">{{ step.title }}</strong>
                <span v-if="step.elapsed_ms > 0" class="step-time">
                  {{ formatDuration(step.elapsed_ms) }}
                </span>
              </div>
              <p v-if="step.subtitle" class="step-desc">{{ step.subtitle }}</p>
            </div>
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>

<style scoped>
.thinking-block-wrapper {
  margin-bottom: 0.75rem;
}

.thinking-card {
  border-radius: 12px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.06));
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

:root.dark .thinking-card {
  background: rgba(255, 255, 255, 0.02);
  border-color: rgba(255, 255, 255, 0.08);
}

.thinking-card.is-active {
  border-color: rgba(70, 184, 180, 0.35);
  background: rgba(70, 184, 180, 0.03);
  box-shadow: 0 0 16px rgba(70, 184, 180, 0.08);
}

.thinking-card.is-collapsed {
  background: rgba(70, 184, 180, 0.04);
  border-color: rgba(70, 184, 180, 0.12);
}

:root.dark .thinking-card.is-collapsed {
  background: rgba(70, 184, 180, 0.06);
  border-color: rgba(70, 184, 180, 0.16);
}

.thinking-header-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 0.85rem;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: inherit;
}

.thinking-header-btn:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.thinking-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.thinking-icon.is-spinning {
  color: var(--color-primary, #46b8b4);
  animation: spin-pulse 1.4s linear infinite;
}

.thinking-icon.is-done {
  color: var(--color-primary, #46b8b4);
}

.thinking-summary {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-secondary, #64748b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.thinking-card.is-active .thinking-summary {
  color: var(--color-text-primary, #1e293b);
}

:root.dark .thinking-card.is-active .thinking-summary {
  color: #f1f5f9;
}

.thinking-summary.is-shimmer {
  background: linear-gradient(90deg, var(--color-primary, #46b8b4) 0%, #38bdf8 50%, var(--color-primary, #46b8b4) 100%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: shimmer-text 2s linear infinite;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.thinking-duration-pill {
  font-size: 0.75rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--color-text-muted, #94a3b8);
  padding: 0.1rem 0.4rem;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 4px;
}

:root.dark .thinking-duration-pill {
  background: rgba(255, 255, 255, 0.05);
}

.chevron-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  color: var(--color-text-muted, #94a3b8);
  transition: transform 0.2s ease;
}

.chevron-icon.is-open {
  transform: rotate(180deg);
}

.thinking-content {
  border-top: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.05));
  padding: 0.65rem 0.95rem 0.8rem;
  background: rgba(0, 0, 0, 0.01);
}

:root.dark .thinking-content {
  border-top-color: rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.15);
}

.thinking-steps-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.thinking-step-item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
}

.step-marker {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.04);
  color: var(--color-text-muted, #94a3b8);
  font-size: 0.6875rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

:root.dark .step-marker {
  background: rgba(255, 255, 255, 0.06);
}

.thinking-step-item.is-running .step-marker {
  background: rgba(70, 184, 180, 0.15);
  color: var(--color-primary, #46b8b4);
}

.marker-dot.is-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary, #46b8b4);
  animation: pulse-dot 1s ease-in-out infinite;
}

.marker-dot.is-check {
  color: var(--color-primary, #46b8b4);
  font-size: 0.75rem;
}

.step-detail {
  flex: 1;
  min-width: 0;
}

.step-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

.step-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary, #334155);
}

:root.dark .step-title {
  color: #e2e8f0;
}

.step-time {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--color-text-muted, #94a3b8);
}

.step-desc {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--color-text-secondary, #64748b);
}

:root.dark .step-desc {
  color: #94a3b8;
}

@keyframes spin-pulse {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse-dot {
  0%, 100% { transform: scale(0.8); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
}

@keyframes shimmer-text {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
