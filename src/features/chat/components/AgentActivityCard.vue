<template>
  <section class="agent-activity-card" :class="{ active }" aria-live="polite">
    <button class="activity-summary" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
      <span class="activity-state" :class="{ spinning: active }">
        <span v-if="active" class="activity-spinner"></span>
        <span v-else class="activity-check">✓</span>
      </span>
      <span class="activity-summary-copy">
        <strong>{{ headline }}</strong>
        <small>{{ active ? '智能协同体正在研判论据中...' : '点击展开协同研判细节' }}</small>
      </span>
      <span class="activity-toggle">{{ expanded ? '收起' : '详情' }}</span>
    </button>

    <div v-if="expanded" class="activity-list">
      <article v-for="item in activities" :key="item.activity_id" class="activity-item">
        <span class="item-dot" :class="item.status"></span>
        <div class="item-copy">
          <div class="item-title-row">
            <strong>{{ item.title }}</strong>
            <span v-if="item.detail?.duration_ms != null" class="item-duration">
              {{ formatDuration(item.detail.duration_ms) }}
            </span>
          </div>
          <p v-if="item.summary">{{ item.summary }}</p>
          <dl v-if="hasDetail(item)" class="item-detail">
            <template v-if="item.detail?.tool_name">
              <dt>工具</dt><dd>{{ item.detail.tool_name }}</dd>
            </template>
            <template v-if="item.detail?.files?.length">
              <dt>附件</dt><dd>{{ item.detail.files.join('、') }}</dd>
            </template>
            <template v-if="item.detail?.input">
              <dt>输入</dt><dd>{{ item.detail.input }}</dd>
            </template>
            <template v-if="item.detail?.output">
              <dt>结果</dt><dd class="detail-output">{{ item.detail.output }}</dd>
            </template>
            <template v-if="item.detail?.error">
              <dt>错误</dt><dd class="detail-error">{{ item.detail.error }}</dd>
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
  active: boolean
}>()

const expanded = ref(false)

const headline = computed(() => {
  if (props.active) {
    const running = [...props.activities].reverse().find(item => item.status === 'running')
    return running?.message || props.activities[props.activities.length - 1]?.message || '多智能体研判中...'
  }
  const actualActivities = props.activities.filter(item => item.kind !== 'workflow')
  const failures = actualActivities.filter(item => item.status === 'failed').length
  if (!actualActivities.length) return '协同研判已就绪'
  return failures
    ? `已聚合 ${actualActivities.length} 项成果 · ${failures} 项协同受阻`
    : `已聚合 ${actualActivities.length} 项认知成果`
})

watch(() => props.active, active => {
  if (!active) expanded.value = false
})

const formatDuration = (durationMs: number) => durationMs < 1000
  ? `${durationMs} ms`
  : `${(durationMs / 1000).toFixed(1)} s`

const hasDetail = (item: AgentActivity) => Boolean(
  item.detail?.tool_name || item.detail?.files?.length || item.detail?.input || item.detail?.output || item.detail?.error,
)
</script>

<style scoped>
.agent-activity-card {
  width: min(560px, calc(100% - 48px));
  margin-left: 48px;
  border: 1px solid color-mix(in srgb, var(--color-border) 82%, transparent);
  border-radius: 14px;
  background: color-mix(in srgb, var(--color-surface) 94%, var(--color-primary) 6%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}

.activity-summary {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  padding: 11px 13px;
  border: 0;
  background: transparent;
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}

.activity-state {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
  border-radius: 8px;
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
}

.activity-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid color-mix(in srgb, var(--color-primary) 25%, transparent);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: activity-spin 0.8s linear infinite;
}

.activity-check { font-size: 13px; font-weight: 700; }
.activity-summary-copy { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 2px; }
.activity-summary-copy strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.activity-summary-copy small { color: var(--color-text-faint); font-size: 11px; }
.activity-toggle { color: var(--color-text-secondary); font-size: 12px; }

.activity-list { padding: 0 13px 12px 47px; }
.activity-item { position: relative; display: flex; gap: 10px; padding: 10px 0; border-top: 1px solid var(--color-border); }
.item-dot { width: 8px; height: 8px; margin-top: 5px; flex: 0 0 8px; border-radius: 50%; background: var(--color-text-faint); }
.item-dot.running { background: var(--color-primary); }
.item-dot.done { background: #22c55e; }
.item-dot.failed { background: #ef4444; }
.item-copy { min-width: 0; flex: 1; }
.item-title-row { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; }
.item-duration { color: var(--color-text-faint); font-size: 11px; font-weight: 400; }
.item-copy p { margin: 3px 0 0; color: var(--color-text-secondary); font-size: 12px; }
.item-detail { display: grid; grid-template-columns: max-content 1fr; gap: 5px 10px; margin: 9px 0 0; font-size: 12px; }
.item-detail dt { color: var(--color-text-faint); }
.item-detail dd { min-width: 0; margin: 0; color: var(--color-text-secondary); overflow-wrap: anywhere; }
.detail-output { max-height: 180px; overflow: auto; white-space: pre-wrap; }
.detail-error { color: #dc2626 !important; }

@keyframes activity-spin { to { transform: rotate(360deg); } }

@media (max-width: 720px) {
  .agent-activity-card { width: 100%; margin-left: 0; }
}
</style>
