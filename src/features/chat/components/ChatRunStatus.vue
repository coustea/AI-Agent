<script setup lang="ts">
import { computed } from 'vue'
import { isRunActive, type RunConnection, type RunState, type StepStatus } from '@/features/chat/types/chatRun'

const props = defineProps<{ run: RunState; connection?: RunConnection }>()
const active = computed(() => isRunActive(props.run))
const disconnected = computed(() => active.value && props.connection !== 'connected')
const stepLabels: Record<StepStatus, string> = {
  running: '执行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已停止',
}
const connectionLabels: Record<RunConnection, string> = {
  connecting: '正在连接，等待最新状态',
  connected: '',
  reconnecting: '连接中断，正在重连；以下为最后收到的状态',
  closed: '连接已关闭，请重新打开会话获取最新状态',
}
const duration = (ms: number): string => `${(ms / 1000).toFixed(1)} 秒`
</script>

<template>
  <section class="run-status" aria-label="智能体运行状态">
    <p v-if="disconnected" class="connection-note" role="status">
      {{ connectionLabels[connection || 'connecting'] }}
    </p>
    <div class="status-heading" role="status">
      <span class="status-dot" :class="{ running: active && !disconnected, failed: run.status === 'failed' }"></span>
      <strong>{{ disconnected ? '最后状态：' : '' }}{{ run.phase_label }}</strong>
      <span v-if="run.total_elapsed_ms" class="duration">{{ duration(run.total_elapsed_ms) }}</span>
    </div>
    <details v-if="run.steps.length" class="run-steps">
      <summary>执行记录 · {{ run.steps.length }} 次调用</summary>
      <ol>
        <li v-for="step in run.steps" :key="step.step_id">
          <div class="step-heading">
            <strong>{{ step.title }}</strong>
            <span :class="{ error: step.status === 'failed' }">{{ stepLabels[step.status] }}</span>
            <span v-if="step.elapsed_ms" class="duration">{{ duration(step.elapsed_ms) }}</span>
          </div>
          <p v-if="step.subtitle">{{ step.subtitle }}</p>
          <ul v-if="step.sub_steps.length" class="activity-log">
            <li v-for="activity in step.sub_steps" :key="activity.id">{{ activity.title }}</li>
          </ul>
          <details v-if="step.input_preview || step.output_preview || step.error" class="call-details">
            <summary>{{ step.tool_name }} · 参数与结果</summary>
            <template v-if="step.input_preview">
              <span>输入参数</span>
              <pre>{{ step.input_preview }}</pre>
            </template>
            <template v-if="step.error || step.output_preview">
              <span>{{ step.error ? '执行错误' : '输出结果' }}</span>
              <pre :class="{ error: step.error }">{{ step.error || step.output_preview }}</pre>
            </template>
          </details>
        </li>
      </ol>
    </details>
  </section>
</template>

<style scoped>
.run-status {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border-subtle);
  border-radius: 10px;
  color: var(--color-text-secondary);
  font-size: 0.8125rem;
}
.status-heading, .step-heading {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.5rem;
}
strong { color: var(--color-text-primary); font-weight: 600; }
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.status-dot.running { background: var(--color-primary); animation: pulse 1s ease-in-out infinite alternate; }
.status-dot.failed, .error { color: #ef4444; }
.duration { margin-left: auto; font-variant-numeric: tabular-nums; }
.connection-note { color: var(--color-text-primary); margin: 0 0 0.5rem; }
summary { cursor: pointer; padding: 0.4rem 0; }
.run-steps { margin-top: 0.35rem; }
ol { margin: 0.25rem 0; padding-left: 1.25rem; }
ol > li { padding: 0.5rem 0; }
p { margin: 0.25rem 0; }
.activity-log { padding-left: 1rem; margin: 0.4rem 0; }
.call-details { margin-top: 0.25rem; }
pre {
  margin: 0.25rem 0 0.5rem;
  padding: 0.5rem;
  background: var(--color-surface);
  border-radius: 6px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 180px;
  overflow-y: auto;
}
@keyframes pulse { from { opacity: 0.4; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .status-dot.running { animation: none; } }
</style>
