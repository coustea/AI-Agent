<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  isRunActive,
  type RunState,
  type RunStep,
  type StepKind,
} from '@/features/chat/types/chatEvent'

const props = defineProps<{
  run: RunState
}>()

const active = computed(() => isRunActive(props.run))

const toolSteps = computed<RunStep[]>(() =>
  (props.run.steps || []).filter(s => s.kind !== 'thinking'),
)

// 若有非思考工具步骤，或当前正处于工具调用阶段，展示工具卡片
const hasTools = computed(() =>
  toolSteps.value.length > 0 || (active.value && props.run.phase === 'tool_calling'),
)

// 跟踪每个工具步骤的 Inspector（输入/输出详情）展开状态
const expandedStepIds = ref<Record<string, boolean>>({})

const toggleInspector = (stepId: string) => {
  expandedStepIds.value[stepId] = !expandedStepIds.value[stepId]
}

const kindMetaMap: Record<StepKind, { label: string; icon: string }> = {
  thinking: { label: '思考规划', icon: 'brain' },
  knowledge: { label: '知识检索', icon: 'book' },
  memory: { label: '学情记忆', icon: 'user' },
  vision: { label: '视觉解析', icon: 'eye' },
  document: { label: '文档研读', icon: 'file' },
  code: { label: '代码推演', icon: 'code' },
  subagent: { label: '多模态生成', icon: 'cpu' },
  tool: { label: '工具调用', icon: 'wrench' },
}

const getKindLabel = (kind: StepKind): string => (kindMetaMap[kind] || kindMetaMap.tool).label

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

const hasInspector = (step: RunStep): boolean =>
  Boolean(step.input_preview || step.output_preview || step.error)
</script>

<template>
  <div v-if="hasTools" class="tool-block-wrapper" aria-live="polite">
    <div class="tool-action-card">
      <div class="tool-card-header">
        <div class="header-left">
          <span class="tool-header-icon" aria-hidden="true">
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M13.2 9.5 9.5 13.2M10.8 7.2l1.6-1.6a2.8 2.8 0 0 0-4-4L6.8 3.2M2.8 13.2l4.4-4.4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span class="tool-card-title">
            智能体行动记录
            <span class="tool-count-badge">{{ toolSteps.length }} 项调用</span>
          </span>
        </div>

        <div v-if="active && run.phase === 'tool_calling'" class="tool-live-badge">
          <span class="pulse-ring"></span>
          <span>正在执行工具调用...</span>
        </div>
      </div>

      <div class="tool-steps-container">
        <div
          v-for="step in toolSteps"
          :key="step.step_id"
          class="tool-step-row"
          :class="[`is-${step.status}`, `kind-${step.kind}`]"
        >
          <div class="step-status-rail">
            <span v-if="step.status === 'running'" class="status-indicator is-running" title="运行中">
              <span class="spin-dot"></span>
            </span>
            <span v-else-if="step.status === 'completed'" class="status-indicator is-done" title="已完成">
              <svg viewBox="0 0 14 14" fill="none">
                <path d="M2.8 7.2 5.6 10 11.2 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <span v-else-if="step.status === 'failed'" class="status-indicator is-failed" title="调用异常">
              <svg viewBox="0 0 14 14" fill="none">
                <path d="M3.5 3.5 10.5 10.5M10.5 3.5 3.5 10.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              </svg>
            </span>
            <span v-else class="status-indicator is-idle"></span>
          </div>

          <div class="step-main-content">
            <div class="step-top-line">
              <div class="step-badge-title">
                <span class="kind-tag" :class="`is-${step.kind}`">
                  {{ getKindLabel(step.kind) }}
                </span>
                <strong class="step-title-text">{{ step.title }}</strong>
              </div>

              <div class="step-actions">
                <span v-if="step.elapsed_ms > 0" class="step-time-pill">
                  {{ formatDuration(step.elapsed_ms) }}
                </span>
                <button
                  v-if="hasInspector(step)"
                  type="button"
                  class="inspector-toggle-btn"
                  :class="{ 'is-open': expandedStepIds[step.step_id] }"
                  @click="toggleInspector(step.step_id)"
                >
                  <span>{{ expandedStepIds[step.step_id] ? '收起详情' : '参数明细' }}</span>
                  <svg viewBox="0 0 12 12" fill="none" class="toggle-arrow" aria-hidden="true">
                    <path d="M3 4.5 6 7.5 9 4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </button>
              </div>
            </div>

            <p v-if="step.subtitle" class="step-subtitle-text">{{ step.subtitle }}</p>

            <!-- 子智能体（PPT / 教学视频）进度条与子步骤 -->
            <div v-if="step.kind === 'subagent' || step.sub_steps?.length" class="subagent-progress-box">
              <div v-if="typeof step.progress === 'number'" class="progress-bar-wrap">
                <div class="progress-track">
                  <div
                    class="progress-fill"
                    :style="{ transform: `scaleX(${Math.min(1, Math.max(0.05, step.progress / 100))})` }"
                  ></div>
                </div>
                <span class="progress-label">{{ step.progress }}%</span>
              </div>

              <ul v-if="step.sub_steps?.length" class="sub-step-list">
                <li
                  v-for="sub in step.sub_steps"
                  :key="sub.id"
                  class="sub-step-item"
                  :class="`is-${sub.status}`"
                >
                  <span class="sub-dot"></span>
                  <span class="sub-title">{{ sub.title }}</span>
                </li>
              </ul>
            </div>

            <!-- 参数与结果明细面板 -->
            <div
              v-if="hasInspector(step) && expandedStepIds[step.step_id]"
              class="step-inspector-panel"
            >
              <div v-if="step.input_preview" class="inspector-section">
                <div class="section-tag">输入参数</div>
                <pre class="inspector-code">{{ step.input_preview }}</pre>
              </div>
              <div v-if="step.error" class="inspector-section is-error">
                <div class="section-tag">异常日志</div>
                <pre class="inspector-code">{{ step.error }}</pre>
              </div>
              <div v-else-if="step.output_preview" class="inspector-section">
                <div class="section-tag">输出摘要</div>
                <pre class="inspector-code">{{ step.output_preview }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tool-block-wrapper {
  margin-bottom: 0.85rem;
}

.tool-action-card {
  border-radius: 12px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.08));
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

:root.dark .tool-action-card {
  background: rgba(255, 255, 255, 0.025);
  border-color: rgba(255, 255, 255, 0.08);
}

.tool-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 0.85rem;
  background: rgba(0, 0, 0, 0.015);
  border-bottom: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.05));
}

:root.dark .tool-card-header {
  background: rgba(255, 255, 255, 0.02);
  border-bottom-color: rgba(255, 255, 255, 0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.tool-header-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 15px;
  height: 15px;
  color: var(--color-primary, #46b8b4);
}

.tool-card-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary, #334155);
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

:root.dark .tool-card-title {
  color: #e2e8f0;
}

.tool-count-badge {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.08rem 0.35rem;
  background: rgba(70, 184, 180, 0.1);
  color: var(--color-primary, #46b8b4);
  border-radius: 4px;
}

.tool-live-badge {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--color-primary, #46b8b4);
}

.pulse-ring {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary, #46b8b4);
  animation: pulse-glow 1s infinite alternate;
}

.tool-steps-container {
  padding: 0.4rem 0.85rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tool-step-row {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.35rem 0;
  border-bottom: 1px dashed var(--color-border-subtle, rgba(0, 0, 0, 0.04));
}

.tool-step-row:last-child {
  border-bottom: none;
}

:root.dark .tool-step-row {
  border-bottom-color: rgba(255, 255, 255, 0.04);
}

.step-status-rail {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0.2rem;
  flex-shrink: 0;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
}

.status-indicator.is-running {
  color: var(--color-primary, #46b8b4);
}

.spin-dot {
  width: 10px;
  height: 10px;
  border: 1.8px solid var(--color-primary, #46b8b4);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.status-indicator.is-done {
  color: #10b981;
}

.status-indicator.is-failed {
  color: #ef4444;
}

.step-main-content {
  flex: 1;
  min-width: 0;
}

.step-top-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.step-badge-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.kind-tag {
  font-size: 0.6875rem;
  font-weight: 500;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-secondary, #64748b);
  white-space: nowrap;
}

:root.dark .kind-tag {
  background: rgba(255, 255, 255, 0.08);
  color: #94a3b8;
}

.kind-tag.is-knowledge {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.kind-tag.is-vision {
  background: rgba(168, 85, 247, 0.1);
  color: #a855f7;
}

.kind-tag.is-code {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.kind-tag.is-subagent {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.step-title-text {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-primary, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:root.dark .step-title-text {
  color: #f1f5f9;
}

.step-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.step-time-pill {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--color-text-muted, #94a3b8);
}

.inspector-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  background: transparent;
  border: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.08));
  color: var(--color-text-secondary, #64748b);
  font-size: 0.6875rem;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s ease;
}

:root.dark .inspector-toggle-btn {
  border-color: rgba(255, 255, 255, 0.1);
  color: #94a3b8;
}

.inspector-toggle-btn:hover {
  background: rgba(0, 0, 0, 0.04);
  color: var(--color-primary, #46b8b4);
  border-color: var(--color-primary, #46b8b4);
}

.toggle-arrow {
  width: 10px;
  height: 10px;
  transition: transform 0.2s ease;
}

.inspector-toggle-btn.is-open .toggle-arrow {
  transform: rotate(180deg);
}

.step-subtitle-text {
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--color-text-secondary, #64748b);
}

:root.dark .step-subtitle-text {
  color: #94a3b8;
}

.subagent-progress-box {
  margin-top: 0.4rem;
  padding: 0.4rem 0.6rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 6px;
}

:root.dark .subagent-progress-box {
  background: rgba(255, 255, 255, 0.03);
}

.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-track {
  flex: 1;
  height: 4px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 2px;
  overflow: hidden;
}

:root.dark .progress-track {
  background: rgba(255, 255, 255, 0.1);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary, #46b8b4), #38bdf8);
  border-radius: 2px;
  transform-origin: left;
  transition: transform 0.3s ease;
}

.progress-label {
  font-size: 0.6875rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--color-primary, #46b8b4);
  font-weight: 600;
}

.sub-step-list {
  list-style: none;
  padding: 0;
  margin: 0.35rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.sub-step-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.6875rem;
  color: var(--color-text-muted, #94a3b8);
}

.sub-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
}

.sub-step-item.is-running {
  color: var(--color-primary, #46b8b4);
  font-weight: 500;
}

.sub-step-item.is-completed {
  color: #10b981;
}

.step-inspector-panel {
  margin-top: 0.45rem;
  padding: 0.5rem;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

:root.dark .step-inspector-panel {
  background: #0f172a;
  border-color: rgba(255, 255, 255, 0.06);
}

.section-tag {
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--color-text-secondary, #64748b);
  margin-bottom: 0.2rem;
}

.inspector-code {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.71875rem;
  line-height: 1.45;
  color: var(--color-text-primary, #334155);
  background: transparent;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 180px;
  overflow-y: auto;
}

:root.dark .inspector-code {
  color: #cbd5e1;
}

.inspector-section.is-error .section-tag {
  color: #ef4444;
}

.inspector-section.is-error .inspector-code {
  color: #ef4444;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse-glow {
  from { opacity: 0.4; }
  to { opacity: 1; }
}
</style>
