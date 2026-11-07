<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
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
const steps = computed(() => props.run.steps || [])
const artifacts = computed(() => props.run.artifacts || [])
const sources = computed(() => props.run.sources || [])

// 用户是否手动切换过展开/收起状态；未手动切换时：运行中展开，完成后且已有回答正文时默认收起为摘要条
const userToggled = ref<boolean | null>(null)
const expandedStepIds = ref<Record<string, boolean>>({})

const isTimelineExpanded = computed(() => {
  if (userToggled.value !== null) return userToggled.value
  if (active.value) return true
  if (props.run.status === 'failed' || props.run.status === 'interrupted') return true
  return !props.run.content
})

const toggleTimeline = () => {
  userToggled.value = !isTimelineExpanded.value
}

const toggleStepDetail = (stepId: string) => {
  expandedStepIds.value[stepId] = !expandedStepIds.value[stepId]
}

// 实时计时器：运行中每 200ms 刷新一次总耗时
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
  }, 200)
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

const totalDurationText = computed(() => {
  const ms = active.value
    ? Math.max(liveTickMs.value, props.run.total_elapsed_ms || 0)
    : props.run.total_elapsed_ms || liveTickMs.value
  return formatDuration(ms)
})

const kindBadgeMap: Record<StepKind, { label: string; tone: string }> = {
  thinking: { label: '思考规划', tone: 'indigo' },
  knowledge: { label: '知识检索', tone: 'blue' },
  memory: { label: '学习档案', tone: 'teal' },
  vision: { label: '视觉理解', tone: 'amber' },
  document: { label: '文档阅读', tone: 'cyan' },
  code: { label: '代码执行', tone: 'slate' },
  subagent: { label: '多模态生成', tone: 'purple' },
  tool: { label: '工具调用', tone: 'slate' },
}

const getKindMeta = (kind: StepKind) => kindBadgeMap[kind] || kindBadgeMap.tool

const hasStepInspector = (step: RunStep): boolean =>
  Boolean(step.input_preview || step.output_preview || step.error)

const headerTitle = computed(() => {
  if (active.value) {
    return props.run.phase_label || '正在处理...'
  }
  if (props.run.status === 'cancelled') return '已停止生成'
  if (props.run.status === 'failed') return props.run.phase_label || '执行失败'
  if (props.run.status === 'interrupted') return '运行已中断'
  const toolCount = steps.value.filter(s => s.kind !== 'thinking').length
  if (toolCount > 0) {
    return `已完成思考与 ${toolCount} 项工具调用`
  }
  return '已完成思考与回答生成'
})
</script>

<template>
  <section class="agent-run-container" aria-live="polite">
    <!-- 1. Agent 实时状态与步骤时间线卡片 -->
    <div
      v-if="active || steps.length > 0 || run.status === 'cancelled'"
      class="agent-workflow-card"
      :class="[`is-${run.status}`, { 'is-active': active }]"
    >
      <header
        class="workflow-header"
        :class="{ 'is-clickable': steps.length > 0 }"
        @click="steps.length > 0 && toggleTimeline()"
      >
        <div class="header-left">
          <span v-if="active" class="status-indicator is-running" aria-hidden="true">
            <span class="pulse-ring"></span>
            <span class="pulse-dot"></span>
          </span>
          <span
            v-else-if="run.status === 'completed'"
            class="status-indicator is-completed"
            aria-hidden="true"
          >
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M3.5 8.2 6.6 11.3 12.5 4.8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <span
            v-else
            class="status-indicator is-warning"
            aria-hidden="true"
          >
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M8 5v3.8M8 11.3h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </span>

          <span class="phase-title">{{ headerTitle }}</span>
        </div>

        <div class="header-right">
          <span v-if="steps.length > 0" class="step-count-pill">
            {{ steps.length }} 个步骤
          </span>
          <span v-if="totalDurationText" class="elapsed-pill">
            {{ totalDurationText }}
          </span>
          <button
            v-if="steps.length > 0"
            type="button"
            class="collapse-chevron-btn"
            :class="{ 'is-open': isTimelineExpanded }"
            :aria-expanded="isTimelineExpanded"
            aria-label="展开或收起执行步骤"
          >
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M4.5 6.2 8 9.8l3.5-3.6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
        </div>
      </header>

      <!-- 步骤时间线列表 -->
      <div v-if="steps.length > 0 && isTimelineExpanded" class="workflow-timeline">
        <div
          v-for="(step, idx) in steps"
          :key="step.step_id"
          class="timeline-step"
          :class="[`step-${step.status}`, `kind-${step.kind}`]"
        >
          <div class="step-rail">
            <span class="step-node">
              <span v-if="step.status === 'running'" class="node-spinner"></span>
              <svg v-else-if="step.status === 'completed'" viewBox="0 0 12 12" fill="none">
                <path d="M2.5 6.2 5 8.6 9.5 3.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span v-else class="node-dot"></span>
            </span>
            <span v-if="idx < steps.length - 1" class="step-connector"></span>
          </div>

          <div class="step-body">
            <div class="step-main-row">
              <div class="step-title-group">
                <span class="kind-badge" :class="`tone-${getKindMeta(step.kind).tone}`">
                  {{ getKindMeta(step.kind).label }}
                </span>
                <strong class="step-title">{{ step.title }}</strong>
              </div>

              <div class="step-meta-group">
                <span v-if="step.status === 'running'" class="step-live-tag">执行中</span>
                <span v-else-if="step.status === 'failed'" class="step-fail-tag">失败</span>
                <span v-if="step.elapsed_ms > 0" class="step-duration">
                  {{ formatDuration(step.elapsed_ms) }}
                </span>
                <button
                  v-if="hasStepInspector(step)"
                  type="button"
                  class="inspector-toggle-btn"
                  @click.stop="toggleStepDetail(step.step_id)"
                >
                  {{ expandedStepIds[step.step_id] ? '收起详情' : '查看详情' }}
                </button>
              </div>
            </div>

            <p v-if="step.subtitle" class="step-subtitle">{{ step.subtitle }}</p>

            <!-- 子智能体（PPT / 教学视频）进度条与内部实时子步骤 -->
            <div
              v-if="step.kind === 'subagent' || step.sub_steps?.length"
              class="subagent-box"
            >
              <div v-if="typeof step.progress === 'number'" class="subagent-progress-row">
                <div class="subagent-progress-bar">
                  <div
                    class="subagent-progress-fill"
                    :style="{ width: `${Math.min(100, Math.max(5, step.progress))}%` }"
                  ></div>
                </div>
                <span class="subagent-progress-pct">{{ step.progress }}%</span>
              </div>

              <ul v-if="step.sub_steps?.length" class="sub-step-list">
                <li
                  v-for="sub in step.sub_steps"
                  :key="sub.id"
                  class="sub-step-item"
                  :class="`is-${sub.status}`"
                >
                  <span class="sub-step-dot"></span>
                  <span class="sub-step-text">{{ sub.title }}</span>
                </li>
              </ul>
            </div>

            <!-- 工具参数与输出详情面板 -->
            <div
              v-if="hasStepInspector(step) && expandedStepIds[step.step_id]"
              class="step-inspector"
            >
              <div v-if="step.input_preview" class="inspector-block">
                <span class="inspector-label">输入参数 ({{ step.tool_name || step.kind }})</span>
                <pre>{{ step.input_preview }}</pre>
              </div>
              <div v-if="step.error" class="inspector-block is-error">
                <span class="inspector-label">异常信息</span>
                <pre>{{ step.error }}</pre>
              </div>
              <div v-else-if="step.output_preview" class="inspector-block">
                <span class="inspector-label">返回结果摘要</span>
                <pre>{{ step.output_preview }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 多模态生成产物卡片（教学视频 / PPT 课件） -->
    <div v-if="artifacts.length > 0" class="artifacts-list">
      <article
        v-for="artifact in artifacts"
        :key="artifact.id"
        class="artifact-card"
      >
        <div class="artifact-header">
          <div class="artifact-title-wrap">
            <span class="artifact-badge">
              {{ artifact.kind === 'video' ? '教学动画视频' : 'PPT 演示课件' }}
            </span>
            <strong class="artifact-title">{{ artifact.title }}</strong>
          </div>
          <div class="artifact-links">
            <a
              v-if="artifact.preview_url"
              :href="artifact.preview_url"
              target="_blank"
              rel="noopener noreferrer"
              class="artifact-btn is-secondary"
            >
              在线预览
            </a>
            <a
              :href="artifact.url"
              target="_blank"
              rel="noopener noreferrer"
              class="artifact-btn is-primary"
            >
              {{ artifact.kind === 'ppt' ? '下载 PPTX' : '下载视频' }}
            </a>
          </div>
        </div>

        <video
          v-if="artifact.kind === 'video'"
          :src="artifact.url"
          controls
          preload="metadata"
          class="artifact-video"
        />
      </article>
    </div>

    <!-- 3. 知识库参考来源条 -->
    <div v-if="sources.length > 0 && !active" class="sources-strip">
      <span class="sources-label">参考教材与资料：</span>
      <div class="sources-chips">
        <span
          v-for="(src, idx) in sources"
          :key="`${src.title}-${idx}`"
          class="source-chip"
          :title="src.summary || src.heading || src.title"
        >
          {{ src.title || src.source }}{{ src.heading ? ` · ${src.heading}` : '' }}
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.agent-run-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 4px 0 8px;
  font-size: 13px;
}

.agent-workflow-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.agent-workflow-card.is-active {
  background: linear-gradient(180deg, #f8fbff 0%, #f8fafc 100%);
  border-color: #cbd5e1;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}

.workflow-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 13px;
  user-select: none;
}

.workflow-header.is-clickable {
  cursor: pointer;
}

.workflow-header.is-clickable:hover {
  background: rgba(241, 245, 249, 0.7);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  flex: 1;
}

.status-indicator {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-indicator.is-running {
  color: #2563eb;
}

.pulse-ring {
  position: absolute;
  inset: 1px;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.22);
  animation: agent-pulse 1.5s ease-out infinite;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2563eb;
}

@keyframes agent-pulse {
  0% {
    transform: scale(0.7);
    opacity: 0.9;
  }
  100% {
    transform: scale(1.75);
    opacity: 0;
  }
}

.status-indicator.is-completed {
  background: #dcfce7;
  color: #15803d;
}

.status-indicator.is-completed svg,
.status-indicator.is-warning svg {
  width: 12px;
  height: 12px;
}

.status-indicator.is-warning {
  background: #fef3c7;
  color: #b45309;
}

.phase-title {
  color: #1e293b;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.step-count-pill,
.elapsed-pill {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  background: #eef2f6;
}

.elapsed-pill {
  font-variant-numeric: tabular-nums;
}

.collapse-chevron-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.15s ease;
}

.collapse-chevron-btn.is-open {
  transform: rotate(180deg);
}

.workflow-timeline {
  padding: 6px 14px 12px;
  border-top: 1px solid #e2e8f0;
  background: #ffffff;
}

.timeline-step {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  gap: 9px;
}

.step-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 4px;
}

.step-node {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #f1f5f9;
  color: #64748b;
  flex-shrink: 0;
}

.timeline-step.step-running .step-node {
  background: #dbeafe;
  color: #2563eb;
}

.timeline-step.step-completed .step-node {
  background: #e0f2fe;
  color: #0284c7;
}

.timeline-step.step-failed .step-node {
  background: #fee2e2;
  color: #dc2626;
}

.step-node svg {
  width: 10px;
  height: 10px;
}

.node-spinner {
  width: 9px;
  height: 9px;
  border: 1.6px solid rgba(37, 99, 235, 0.25);
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: step-spin 0.75s linear infinite;
}

@keyframes step-spin {
  to {
    transform: rotate(360deg);
  }
}

.node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.step-connector {
  flex: 1;
  width: 1.5px;
  min-height: 12px;
  margin: 3px 0;
  background: #e2e8f0;
}

.step-body {
  padding: 2px 0 10px;
  min-width: 0;
}

.timeline-step:last-child .step-body {
  padding-bottom: 2px;
}

.step-main-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.step-title-group {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.kind-badge {
  padding: 1px 6px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.tone-indigo {
  background: #eef2ff;
  color: #4338ca;
}

.tone-blue {
  background: #eff6ff;
  color: #1d4ed8;
}

.tone-teal {
  background: #f0fdfa;
  color: #0f766e;
}

.tone-amber {
  background: #fffbeb;
  color: #b45309;
}

.tone-cyan {
  background: #ecfeff;
  color: #0e7490;
}

.tone-purple {
  background: #f5f3ff;
  color: #6d28d9;
}

.tone-slate {
  background: #f1f5f9;
  color: #334155;
}

.step-title {
  color: #1e293b;
  font-size: 12.5px;
  font-weight: 600;
}

.step-meta-group {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.step-live-tag {
  color: #2563eb;
  font-weight: 600;
}

.step-fail-tag {
  color: #dc2626;
  font-weight: 600;
}

.step-duration {
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

.inspector-toggle-btn {
  padding: 1px 6px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  cursor: pointer;
}

.inspector-toggle-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.step-subtitle {
  margin: 3px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
  word-break: break-word;
}

.subagent-box {
  margin-top: 7px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.subagent-progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.subagent-progress-bar {
  flex: 1;
  height: 5px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.subagent-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #2563eb);
  border-radius: 999px;
  transition: width 0.25s ease;
}

.subagent-progress-pct {
  color: #475569;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sub-step-list {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sub-step-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: #64748b;
}

.sub-step-item.is-running {
  color: #1d4ed8;
  font-weight: 600;
}

.sub-step-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.step-inspector {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inspector-block {
  padding: 7px 9px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.inspector-block.is-error {
  background: #fef2f2;
  border-color: #fecaca;
}

.inspector-label {
  display: block;
  margin-bottom: 3px;
  font-size: 10.5px;
  font-weight: 600;
  color: #64748b;
}

.inspector-block pre {
  margin: 0;
  font-family: var(--font-mono, monospace);
  font-size: 11.5px;
  line-height: 1.45;
  color: #334155;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: 180px;
  overflow-y: auto;
}

.artifacts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.artifact-card {
  padding: 13px 15px;
  background: #ffffff;
  border: 1px solid #dbe3ec;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.artifact-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.artifact-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.artifact-badge {
  padding: 2px 8px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 600;
}

.artifact-title {
  color: #0f172a;
  font-size: 13.5px;
  font-weight: 600;
}

.artifact-links {
  display: flex;
  align-items: center;
  gap: 8px;
}

.artifact-btn {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s ease;
}

.artifact-btn.is-primary {
  background: #1e293b;
  color: #ffffff;
}

.artifact-btn.is-primary:hover {
  background: #0f172a;
}

.artifact-btn.is-secondary {
  background: #f1f5f9;
  color: #334155;
}

.artifact-btn.is-secondary:hover {
  background: #e2e8f0;
}

.artifact-video {
  width: 100%;
  max-height: 420px;
  margin-top: 10px;
  border-radius: 8px;
  background: #0f172a;
  display: block;
}

.sources-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 2px 0;
}

.sources-label {
  font-size: 11.5px;
  color: #64748b;
  font-weight: 500;
}

.sources-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.source-chip {
  padding: 2px 8px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  color: #475569;
  font-size: 11px;
}
</style>
