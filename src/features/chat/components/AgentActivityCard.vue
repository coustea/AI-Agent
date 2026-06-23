<template>
  <section v-if="visibleActivities.length" class="thinking-block" :class="{ 'is-active': isActive }" aria-live="polite">
    <button
      class="thinking-summary"
      type="button"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <span class="thinking-state" aria-hidden="true">
        <span v-if="isActive" class="thinking-dots">
          <i></i><i></i><i></i>
        </span>
        <span v-else-if="hasFailure" class="thinking-failed">×</span>
        <span v-else class="thinking-check">✓</span>
      </span>

      <span class="thinking-copy">
        <strong>{{ headline }}</strong>
        <small v-if="summaryLine">{{ summaryLine }}</small>
      </span>

      <span class="thinking-toggle">
        {{ expanded ? '收起' : '查看过程' }}
        <span class="toggle-chevron" :class="{ expanded }">⌄</span>
      </span>
    </button>

    <div v-if="expanded" class="activity-list">
      <article v-for="item in visibleActivities" :key="item.activity_id" class="activity-item">
        <span class="activity-rail" :class="item.status">
          <span></span>
        </span>

        <div class="activity-copy">
          <div class="activity-heading">
            <strong>{{ item.title }}</strong>
            <span v-if="item.detail?.duration_ms != null" class="activity-duration">
              {{ formatDuration(item.detail.duration_ms) }}
            </span>
          </div>

          <p v-if="getActivitySummary(item)">{{ getActivitySummary(item) }}</p>

          <dl v-if="hasDetail(item)" class="activity-detail">
            <template v-if="item.detail?.tool_name || item.tool_name">
              <dt>工具</dt><dd>{{ item.detail?.tool_name || item.tool_name }}</dd>
            </template>
            <template v-if="item.detail?.files?.length">
              <dt>文件</dt><dd>{{ item.detail.files.join('、') }}</dd>
            </template>
            <template v-if="item.detail?.output">
              <dt>结果</dt><dd class="detail-output">{{ item.detail.output }}</dd>
            </template>
            <template v-if="item.detail?.error">
              <dt>异常</dt><dd class="detail-error">{{ item.detail.error }}</dd>
            </template>
          </dl>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AgentActivity } from '@/features/chat/model/chat'

const props = defineProps<{
  activities: AgentActivity[]
}>()

const expanded = ref(false)

const visibleActivities = computed(() => props.activities.filter(item => (
  Boolean(item.activity_id?.trim()) && Boolean(item.title?.trim())
)))

const currentActivity = computed(() => (
  [...visibleActivities.value].reverse().find(item => item.status === 'running')
  || visibleActivities.value[visibleActivities.value.length - 1]
))

const isActive = computed(() => visibleActivities.value.some(item => item.status === 'running'))
const hasFailure = computed(() => visibleActivities.value.some(item => item.status === 'failed'))

const headline = computed(() => currentActivity.value?.title || '')

const summaryLine = computed(() => {
  const summary = currentActivity.value?.summary || currentActivity.value?.message || ''
  return summary === currentActivity.value?.title ? '' : summary
})

watch(isActive, active => {
  if (!active) expanded.value = false
})

const getActivitySummary = (item: AgentActivity) => item.summary || item.message

const formatDuration = (durationMs: number) => durationMs < 1000
  ? `${durationMs} ms`
  : `${(durationMs / 1000).toFixed(1)} s`

const hasDetail = (item: AgentActivity) => Boolean(
  item.detail?.tool_name
  || item.tool_name
  || item.detail?.files?.length
  || item.detail?.output
  || item.detail?.error,
)
</script>

<style scoped>
.thinking-block {
  width: min(620px, 100%);
  overflow: hidden;
  color: var(--color-text);
  background: var(--color-surface);
  border: 1px solid color-mix(in srgb, var(--color-border) 76%, transparent);
  border-radius: 14px;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.035);
}

.thinking-summary {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  min-height: 56px;
  padding: 10px 13px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.thinking-summary:hover {
  background: color-mix(in srgb, var(--color-bg) 64%, transparent);
}

.thinking-state {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex: 0 0 26px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.thinking-dots {
  display: flex;
  align-items: center;
  gap: 2px;
}

.thinking-dots i {
  width: 3px;
  height: 3px;
  background: currentColor;
  border-radius: 50%;
  animation: thinking-pulse 1.15s ease-in-out infinite;
}

.thinking-dots i:nth-child(2) { animation-delay: 0.16s; }
.thinking-dots i:nth-child(3) { animation-delay: 0.32s; }
.thinking-check,
.thinking-failed { font-size: 13px; font-weight: 700; }

.thinking-failed { color: var(--color-danger); }

.thinking-copy {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.thinking-copy strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thinking-copy small {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.thinking-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 11px;
}

.toggle-chevron {
  display: inline-block;
  font-size: 14px;
  line-height: 1;
  transition: transform 160ms ease;
}

.toggle-chevron.expanded { transform: rotate(180deg); }

.activity-list {
  padding: 0 13px 12px 49px;
  border-top: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
}

.activity-item {
  position: relative;
  display: flex;
  gap: 10px;
  padding: 11px 0 3px;
}

.activity-rail {
  position: relative;
  width: 10px;
  flex: 0 0 10px;
}

.activity-rail::after {
  position: absolute;
  top: 13px;
  bottom: -12px;
  left: 4px;
  width: 1px;
  background: var(--color-border);
  content: '';
}

.activity-item:last-child .activity-rail::after { display: none; }

.activity-rail span {
  position: relative;
  z-index: 1;
  display: block;
  width: 8px;
  height: 8px;
  margin-top: 4px;
  background: var(--color-text-faint);
  border: 2px solid var(--color-surface);
  border-radius: 50%;
  box-shadow: 0 0 0 1px var(--color-border);
}

.activity-rail.running span { background: var(--color-text-secondary); }
.activity-rail.failed span { background: var(--color-danger); }
.activity-copy { min-width: 0; flex: 1; }

.activity-heading {
  display: flex;
  align-items: baseline;
  gap: 7px;
  min-width: 0;
}

.activity-heading strong {
  overflow: hidden;
  flex: 1;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-duration {
  flex: 0 0 auto;
  color: var(--color-text-faint);
  font-size: 10px;
}

.activity-copy p {
  margin: 3px 0 0;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.5;
}

.activity-detail {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 5px 9px;
  margin: 8px 0 0;
  padding: 8px 10px;
  background: var(--color-bg);
  border-radius: 8px;
  font-size: 11px;
}

.activity-detail dt { color: var(--color-text-faint); }
.activity-detail dd { min-width: 0; margin: 0; color: var(--color-text-secondary); overflow-wrap: anywhere; }
.detail-output { max-height: 140px; overflow: auto; white-space: pre-wrap; }
.detail-error { color: var(--color-danger) !important; }

@keyframes thinking-pulse {
  0%, 70%, 100% { opacity: 0.25; transform: translateY(0); }
  35% { opacity: 1; transform: translateY(-2px); }
}

@media (max-width: 720px) {
  .thinking-block { width: 100%; }
  .thinking-toggle { font-size: 0; }
  .thinking-toggle .toggle-chevron { font-size: 14px; }
  .activity-list { padding-left: 18px; }
}
</style>
