<template>
  <section
    v-if="visibleActivities.length"
    class="process-panel"
    :class="{ 'is-running': isActive, 'has-failure': hasFailure }"
    aria-live="polite"
  >
    <button
      class="process-summary"
      type="button"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <span class="process-symbol" aria-hidden="true">
        <span v-if="isActive" class="process-orbit">
          <i></i>
          <i></i>
        </span>
        <span v-else-if="hasFailure" class="process-result process-result--failed">!</span>
        <span v-else class="process-result">✓</span>
      </span>

      <span class="process-copy">
        <span class="process-eyebrow">
          <span>{{ isActive ? '正在处理' : hasFailure ? '处理完成，部分步骤异常' : '处理过程' }}</span>
          <span class="process-count">{{ completedCount }}/{{ visibleActivities.length }}</span>
        </span>
        <strong>{{ headline }}</strong>
        <small v-if="summaryLine">{{ summaryLine }}</small>
      </span>

      <span class="process-toggle">
        {{ expanded ? '收起' : '详情' }}
        <svg viewBox="0 0 20 20" aria-hidden="true" :class="{ expanded }">
          <path d="m6 8 4 4 4-4" />
        </svg>
      </span>
    </button>

    <div v-if="isActive" class="process-progress" aria-hidden="true">
      <span></span>
    </div>

    <Transition name="process-expand">
      <div v-if="expanded" class="activity-list">
        <article
          v-for="(item, index) in visibleActivities"
          :key="item.activity_id"
          class="activity-item"
          :class="`is-${item.status}`"
        >
          <div class="activity-index" aria-hidden="true">
            <span v-if="item.status === 'done'">✓</span>
            <span v-else-if="item.status === 'failed'">!</span>
            <span v-else class="activity-spinner"></span>
          </div>

          <div class="activity-copy">
            <div class="activity-heading">
              <div>
                <span class="activity-kind">{{ kindLabel(item.kind) }}</span>
                <strong>{{ item.title }}</strong>
              </div>
              <span v-if="item.detail?.duration_ms != null" class="activity-duration">
                {{ formatDuration(item.detail.duration_ms) }}
              </span>
            </div>

            <p v-if="getActivitySummary(item)">{{ getActivitySummary(item) }}</p>

            <dl v-if="hasDetail(item)" class="activity-detail">
              <template v-if="item.detail?.files?.length">
                <dt>处理对象</dt>
                <dd>{{ item.detail.files.join('、') }}</dd>
              </template>
              <template v-if="item.detail?.input">
                <dt>输入</dt>
                <dd>{{ item.detail.input }}</dd>
              </template>
              <template v-if="item.detail?.output">
                <dt>结果摘要</dt>
                <dd class="detail-output">{{ item.detail.output }}</dd>
              </template>
              <template v-if="item.detail?.error">
                <dt>异常</dt>
                <dd class="detail-error">{{ item.detail.error }}</dd>
              </template>
            </dl>
          </div>

          <span v-if="index < visibleActivities.length - 1" class="activity-line" aria-hidden="true"></span>
        </article>
      </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AgentActivity } from '@/features/chat/views/tutorUtils'

const props = defineProps<{
  activities: AgentActivity[]
}>()

const expanded = ref(false)

// 过滤掉无 activity_id 或空 title 的无效活动
const visibleActivities = computed(() => props.activities.filter(item => (
  Boolean(item.activity_id?.trim()) && Boolean(item.title?.trim())
)))

// 当前正在运行或最新的活动
const currentActivity = computed(() => (
  [...visibleActivities.value].reverse().find(item => item.status === 'running')
  || visibleActivities.value[visibleActivities.value.length - 1]
))

// 是否有活动正在运行
const isActive = computed(() => visibleActivities.value.some(item => item.status === 'running'))
const hasFailure = computed(() => visibleActivities.value.some(item => item.status === 'failed'))
// 已完成（非 running）的活动数量
const completedCount = computed(() => visibleActivities.value.filter(item => item.status !== 'running').length)

const headline = computed(() => currentActivity.value?.message || currentActivity.value?.title || '正在准备回答')

const summaryLine = computed(() => {
  const item = currentActivity.value
  if (!item) return ''
  const summary = item.summary || item.detail?.input || ''
  return summary === item.title || summary === item.message ? '' : summary
})

// 新活动开始时自动折叠详情面板
watch(isActive, active => {
  if (active && visibleActivities.value.length <= 1) expanded.value = false
})

const kindLabel = (kind: AgentActivity['kind']) => ({
  agent: 'Agent',
  tool: '工具',
  attachment: '附件',
  workflow: '流程',
}[kind] || '步骤')

const getActivitySummary = (item: AgentActivity) => item.summary || item.message || item.detail?.input || ''

const formatDuration = (durationMs: number) => durationMs < 1000
  ? `${Math.round(durationMs)} ms`
  : `${(durationMs / 1000).toFixed(1)} s`

const hasDetail = (item: AgentActivity) => Boolean(
  item.detail?.files?.length
  || item.detail?.input
  || item.detail?.output
  || item.detail?.error,
)
</script>

<style scoped>
.process-panel {
  width: min(680px, 100%);
  overflow: hidden;
  color: var(--color-text);
  background: transparent;
  border: 0;
  border-radius: 8px;
  box-shadow: none;
}

.process-panel.is-running {
  color: var(--color-text-secondary);
}

.process-panel.has-failure {
  color: var(--color-danger);
}

.process-summary {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 42px;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.process-summary:hover {
  color: var(--color-text);
}

.process-symbol {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  color: #2563eb;
  background: transparent;
  border: 0;
  border-radius: 999px;
}

.process-orbit {
  position: relative;
  width: 15px;
  height: 15px;
}

.process-orbit i {
  position: absolute;
  inset: 4px;
  background: currentColor;
  border-radius: 50%;
  animation: process-breathe 1.08s ease-in-out infinite;
}

.process-orbit i:last-child {
  inset: 1px;
  background: transparent;
  border: 1px solid currentColor;
  opacity: 0.28;
  animation-duration: 1.08s;
}

.process-result {
  font-size: 14px;
  font-weight: 750;
}

.process-result--failed {
  color: var(--color-danger);
}

.process-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1px;
}

.process-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-faint);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
}

.process-count {
  font-variant-numeric: tabular-nums;
  letter-spacing: normal;
}

.process-copy strong {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-weight: 520;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.process-copy small {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.process-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.process-toggle svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
  transition: transform 180ms ease;
}

.process-toggle svg.expanded {
  transform: rotate(180deg);
}

.process-progress {
  display: none;
}

.process-progress span {
  display: block;
  width: 42%;
  height: 100%;
  background: linear-gradient(90deg, transparent, #2563eb, transparent);
  animation: process-scan 1.45s ease-in-out infinite;
}

.activity-list {
  margin-left: 9px;
  padding: 4px 0 8px 19px;
  border-left: 1px solid color-mix(in srgb, var(--color-border) 78%, transparent);
}

.activity-item {
  position: relative;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  padding: 11px 0 5px;
}

.activity-index {
  position: relative;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 10px;
  font-weight: 750;
}

.activity-item.is-done .activity-index {
  color: #15803d;
  border-color: color-mix(in srgb, #15803d 28%, var(--color-border));
  background: color-mix(in srgb, #15803d 6%, var(--color-surface));
}

.activity-item.is-failed .activity-index {
  color: var(--color-danger);
  border-color: color-mix(in srgb, var(--color-danger) 28%, var(--color-border));
}

.activity-line {
  position: absolute;
  top: 31px;
  bottom: -11px;
  left: 9px;
  width: 1px;
  background: var(--color-border);
}

.activity-spinner {
  width: 9px;
  height: 9px;
  border: 1.5px solid color-mix(in srgb, #2563eb 26%, transparent);
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: process-spin 0.8s linear infinite;
}

.activity-copy {
  min-width: 0;
}

.activity-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.activity-heading > div {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 7px;
}

.activity-kind {
  flex: 0 0 auto;
  padding: 2px 5px;
  color: var(--color-text-faint);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 9px;
  line-height: 1.2;
}

.activity-heading strong {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 620;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-duration {
  flex: 0 0 auto;
  color: var(--color-text-faint);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.activity-copy p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.55;
}

.activity-detail {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 6px 10px;
  margin: 8px 0 0;
  padding: 9px 10px;
  background: var(--color-bg);
  border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
  border-radius: 6px;
  font-size: 11px;
}

.activity-detail dt {
  color: var(--color-text-faint);
}

.activity-detail dd {
  min-width: 0;
  margin: 0;
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}

.detail-output {
  max-height: 130px;
  overflow: auto;
  white-space: pre-wrap;
}

.detail-error {
  color: var(--color-danger) !important;
}

.process-expand-enter-active,
.process-expand-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
  transform-origin: top;
}

.process-expand-enter-from,
.process-expand-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@keyframes process-spin {
  to { transform: rotate(360deg); }
}

@keyframes process-breathe {
  0%, 100% {
    opacity: 0.42;
    transform: scale(0.72);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes process-scan {
  from { transform: translateX(-120%); }
  to { transform: translateX(340%); }
}

@media (max-width: 720px) {
  .process-panel { width: 100%; }
  .process-summary { grid-template-columns: 24px minmax(0, 1fr) 18px; }
  .process-toggle { font-size: 0; }
  .process-toggle svg { width: 17px; height: 17px; }
  .activity-list { padding-left: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .process-orbit i,
  .activity-spinner,
  .process-progress span {
    animation: none;
  }
}
</style>
