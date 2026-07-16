<template>
  <article
    class="diagram-card"
    :class="{ compact: props.compact, 'visual-only': props.visualOnly, 'is-interactive': props.compact }"
    :role="props.compact ? 'button' : undefined"
    :tabindex="props.compact ? 0 : undefined"
    @click="handleExpand"
    @keydown.enter.prevent="handleExpand"
    @keydown.space.prevent="handleExpand"
  >
    <div v-if="fallback" class="diagram-image-fallback" role="status">
      <p>图片生成失败，已展示图解</p>
      <button
        v-if="fallback.retryable"
        type="button"
        :disabled="retrying"
        @click.stop="emit('retry')"
      >{{ retrying ? '正在重新生成图片…' : '重新生成图片' }}</button>
    </div>
    <header v-if="!props.visualOnly" class="diagram-header">
      <div class="diagram-heading-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <rect x="3" y="4" width="7" height="6" rx="1.5" />
          <rect x="14" y="4" width="7" height="6" rx="1.5" />
          <rect x="8.5" y="15" width="7" height="5" rx="1.5" />
          <path d="M6.5 10v2h11v-2M12 12v3" />
        </svg>
      </div>

      <div class="diagram-heading-copy">
        <p class="diagram-kicker">{{ typeLabel[displayDiagram.graph_type] || '教学图解' }}</p>
        <h3>{{ displayDiagram.title }}</h3>
        <p v-if="displayDiagram.subtitle" class="diagram-subtitle">{{ displayDiagram.subtitle }}</p>
      </div>

      <div v-if="!props.compact" class="diagram-meta">
        <span v-if="displayDiagram.course" class="meta-chip">{{ displayDiagram.course }}</span>
        <span class="meta-chip" :class="`is-${displayDiagram.difficulty}`">
          {{ difficultyLabel[displayDiagram.difficulty] || displayDiagram.difficulty }}
        </span>
      </div>
    </header>

    <div class="diagram-layout">
      <section class="visual-panel" :class="{ 'is-compact': props.compact }">
        <div v-if="!props.compact" class="visual-toolbar">
          <span>结构视图</span>
          <span>{{ visualHint }}</span>
        </div>

        <div class="visual-viewport">
          <div class="visual-wrapper" :id="props.compact ? undefined : 'capture-target'">
            <ComparisonDiagram v-if="displayDiagram.graph_type === 'comparison'" :payload="displayDiagram.visual_content as ComparisonPayload" />
            <FlowchartDiagram v-else-if="displayDiagram.graph_type === 'flowchart'" :payload="displayDiagram.visual_content as FlowchartPayload" />
            <SequenceDiagram v-else-if="displayDiagram.graph_type === 'sequence'" :payload="displayDiagram.visual_content as SequencePayload" />
            <FrameworkDiagram v-else-if="displayDiagram.graph_type === 'framework'" :payload="displayDiagram.visual_content as FrameworkPayload" />
            <SummaryDiagram v-else-if="displayDiagram.graph_type === 'summary'" :payload="displayDiagram.visual_content as SummaryPayload" />
            <HierarchyDiagram v-else-if="displayDiagram.graph_type === 'hierarchy'" :payload="displayDiagram.visual_content as HierarchyPayload" />
            <TreeDiagram v-else-if="displayDiagram.graph_type === 'tree'" :payload="displayDiagram.visual_content as TreePayload" />
            <GridDiagram v-else-if="displayDiagram.graph_type === 'grid'" :payload="displayDiagram.visual_content as GridPayload" />
            <ProtocolDiagram v-else-if="displayDiagram.graph_type === 'protocol'" :payload="displayDiagram.visual_content as ProtocolPayload" />
            <TimelineDiagram v-else-if="displayDiagram.graph_type === 'timeline'" :payload="displayDiagram.visual_content as TimelinePayload" />
          </div>
        </div>

        <div v-if="props.compact" class="compact-fade" aria-hidden="true"></div>
        <div v-if="props.compact" class="compact-action">
          <span>展开查看完整图解与讲解</span>
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M7 5h8v8M14.5 5.5 6 14" />
          </svg>
        </div>
      </section>

      <aside v-if="!props.compact && !props.visualOnly" class="teaching-panel">
        <section v-if="displayDiagram.teaching_goal" class="teaching-block teaching-goal">
          <span class="section-index">01</span>
          <div>
            <h4>先明确学习目标</h4>
            <p>{{ displayDiagram.teaching_goal }}</p>
          </div>
        </section>

        <section class="teaching-block teaching-core">
          <span class="section-index">02</span>
          <div>
            <h4>核心解释</h4>
            <p>{{ displayDiagram.teaching_content.core_explanation }}</p>
          </div>
        </section>

        <section v-if="keyPoints.length" class="teaching-list-block">
          <h4>理解这张图时抓住</h4>
          <ol>
            <li v-for="point in keyPoints" :key="point">{{ point }}</li>
          </ol>
        </section>

        <section v-if="commonMistakes.length" class="teaching-list-block is-warning">
          <h4>容易混淆</h4>
          <ul>
            <li v-for="mistake in commonMistakes" :key="mistake">{{ mistake }}</li>
          </ul>
        </section>

        <section v-if="examples.length" class="teaching-list-block">
          <h4>结合示例</h4>
          <ul>
            <li v-for="example in examples" :key="example">{{ example }}</li>
          </ul>
        </section>
      </aside>
    </div>

    <footer v-if="!props.compact && !props.visualOnly && displayDiagram.teaching_content.summary" class="diagram-summary">
      <span>一句话带走</span>
      <p>{{ displayDiagram.teaching_content.summary }}</p>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ComparisonDiagram from './diagrams/ComparisonDiagram.vue'
import FlowchartDiagram from './diagrams/FlowchartDiagram.vue'
import SequenceDiagram from './diagrams/SequenceDiagram.vue'
import FrameworkDiagram from './diagrams/FrameworkDiagram.vue'
import SummaryDiagram from './diagrams/SummaryDiagram.vue'
import HierarchyDiagram from './diagrams/HierarchyDiagram.vue'
import TreeDiagram from './diagrams/TreeDiagram.vue'
import GridDiagram from './diagrams/GridDiagram.vue'
import ProtocolDiagram from './diagrams/ProtocolDiagram.vue'
import TimelineDiagram from './diagrams/TimelineDiagram.vue'

// 卡片的类型标签映射
const typeLabel: Record<string, string> = {
  comparison: '对比图解',
  flowchart: '流程图解',
  sequence: '时序图解',
  framework: '框架图解',
  summary: '总结图解',
  hierarchy: '层级图解',
  tree: '树形结构',
  grid: '状态网格',
  protocol: '协议结构',
  timeline: '时间轴图解',
}

const visualHintMap: Record<string, string> = {
  comparison: '横向比较关键差异',
  flowchart: '沿箭头理解执行路径',
  sequence: '按时间顺序阅读交互',
  framework: '从整体进入局部结构',
  summary: '围绕核心概念展开',
  hierarchy: '从上到下理解层级',
  tree: '关注父子节点关系',
  grid: '观察状态与位置变化',
  protocol: '按字段顺序理解结构',
  timeline: '沿时间轴观察变化',
}

const difficultyLabel: Record<string, string> = {
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高级',
}

import type {
  ComparisonPayload,
  FlowchartPayload,
  FrameworkPayload,
  HierarchyPayload,
  SequencePayload,
  SummaryPayload,
  TeachingDiagram, StructuredTeachingDiagram, TeachingDiagramFallback,
  TreePayload,
  GridPayload,
  ProtocolPayload,
  TimelinePayload,
} from '@/features/chat/types/chat'

const props = defineProps<{
  diagram: TeachingDiagram
  compact?: boolean
  retrying?: boolean
  visualOnly?: boolean
}>()

const emit = defineEmits<{
  (e: 'expand', diagram: TeachingDiagram): void
  (e: 'retry'): void
}>()

// 当前图解的视觉提示文本
const fallback = computed(() => props.diagram.kind === 'fallback' ? props.diagram as TeachingDiagramFallback : null)
const displayDiagram = computed<StructuredTeachingDiagram>(() => fallback.value?.diagram ?? props.diagram as StructuredTeachingDiagram)
const visualHint = computed(() => visualHintMap[displayDiagram.value.graph_type] || '结合图形理解知识结构')
const keyPoints = computed(() => displayDiagram.value.teaching_content?.key_points || [])
const commonMistakes = computed(() => displayDiagram.value.teaching_content?.common_mistakes || [])
const examples = computed(() => displayDiagram.value.teaching_content?.examples || [])

// compact 模式下点击展开完整图解
const handleExpand = () => {
  if (props.compact) emit('expand', fallback.value?.diagram ?? props.diagram)
}
</script>

<style scoped>
.diagram-image-fallback {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
}

.diagram-image-fallback p { margin: 0; font-size: 14px; }
.diagram-image-fallback button { padding: 6px 10px; color: #92400e; background: #fff; border: 1px solid #f59e0b; border-radius: 6px; cursor: pointer; }
.diagram-image-fallback button:disabled { cursor: wait; opacity: .65; }

.diagram-card {
  --diagram-blue: #2563eb;
  --diagram-blue-soft: #eff6ff;
  --diagram-ink: var(--color-text);
  --diagram-muted: var(--color-text-muted);
  --diagram-border: var(--color-border);
  --diagram-surface: var(--color-surface);
  --diagram-bg: var(--color-bg);

  display: grid;
  gap: 16px;
  width: 100%;
  padding: 20px;
  color: var(--diagram-ink);
  background: var(--diagram-surface);
  border: 1px solid var(--diagram-border);
  border-radius: 12px;
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.07);
}

.diagram-card.compact {
  gap: 0;
  padding: 0;
  overflow: hidden;
  border-radius: 10px;
  box-shadow: 0 7px 24px rgba(15, 23, 42, 0.07);
}

.diagram-card.visual-only {
  gap: 0;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.diagram-card.is-interactive {
  cursor: pointer;
  outline: none;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.diagram-card.is-interactive:hover,
.diagram-card.is-interactive:focus-visible {
  border-color: color-mix(in srgb, var(--diagram-blue) 42%, var(--diagram-border));
  box-shadow: 0 12px 32px rgba(37, 99, 235, 0.12);
  transform: translateY(-1px);
}

.diagram-header {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
}

.compact .diagram-header {
  padding: 16px 17px 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--diagram-border) 72%, transparent);
}

.diagram-heading-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  color: var(--diagram-blue);
  background: var(--diagram-blue-soft);
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.diagram-heading-mark svg {
  width: 21px;
  height: 21px;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.45;
}

.diagram-heading-copy {
  min-width: 0;
}

.diagram-kicker {
  margin: 0 0 3px;
  color: var(--diagram-blue);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.1em;
}

.diagram-heading-copy h3 {
  margin: 0;
  color: var(--diagram-ink);
  font-size: clamp(17px, 2vw, 22px);
  font-weight: 720;
  line-height: 1.35;
  text-wrap: balance;
  word-break: break-word;
}

.compact .diagram-heading-copy h3 {
  overflow: hidden;
  font-size: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diagram-subtitle {
  margin: 4px 0 0;
  color: var(--diagram-muted);
  font-size: 12px;
  line-height: 1.5;
}

.compact .diagram-subtitle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diagram-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-chip {
  padding: 4px 8px;
  color: var(--color-text-secondary);
  background: var(--diagram-bg);
  border: 1px solid var(--diagram-border);
  border-radius: 5px;
  font-size: 10px;
  font-weight: 650;
  white-space: nowrap;
}

.meta-chip.is-beginner { color: #15803d; background: #f0fdf4; border-color: #bbf7d0; }
.meta-chip.is-intermediate { color: #1d4ed8; background: #eff6ff; border-color: #bfdbfe; }
.meta-chip.is-advanced { color: #a16207; background: #fffbeb; border-color: #fde68a; }

.diagram-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(280px, 0.8fr);
  gap: 16px;
  align-items: start;
}

.compact .diagram-layout {
  display: block;
}

.visual-only .diagram-layout {
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
}

.visual-panel {
  position: relative;
  min-width: 0;
  overflow: hidden;
  background:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    #fbfdff;
  background-size: 24px 24px;
  border: 1px solid var(--diagram-border);
  border-radius: 9px;
}

.compact .visual-panel {
  border: 0;
  border-radius: 0;
}

.visual-only .visual-panel {
  border-radius: 10px;
}

.visual-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 12px;
  color: var(--color-text-faint);
  background: rgba(255, 255, 255, 0.82);
  border-bottom: 1px solid var(--diagram-border);
  font-size: 10px;
}

.visual-toolbar span:first-child {
  color: var(--color-text-secondary);
  font-weight: 680;
}

.visual-viewport {
  min-height: 360px;
  padding: 16px;
  overflow: auto;
}

.compact .visual-viewport {
  min-height: 250px;
  max-height: 290px;
  padding: 12px;
  overflow: hidden;
}

.visual-only .visual-viewport {
  min-height: min(72vh, 720px);
  padding: 24px;
}

.visual-wrapper {
  width: 100%;
  min-width: 0;
}

.compact .visual-wrapper {
  pointer-events: none;
  transform: scale(0.88);
  transform-origin: top center;
}

.compact-fade {
  position: absolute;
  inset: auto 0 0;
  height: 92px;
  background: linear-gradient(to bottom, transparent, rgba(255, 255, 255, 0.96) 76%);
  pointer-events: none;
}

.compact-action {
  position: absolute;
  right: 14px;
  bottom: 12px;
  left: 14px;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 38px;
  padding: 8px 11px;
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid color-mix(in srgb, var(--diagram-blue) 22%, var(--diagram-border));
  border-radius: 7px;
  box-shadow: 0 5px 18px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(8px);
  font-size: 12px;
  font-weight: 650;
}

.compact-action svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
  stroke: var(--diagram-blue);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.6;
}

.teaching-panel {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.teaching-block {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  padding: 12px;
  background: var(--diagram-surface);
  border: 1px solid var(--diagram-border);
  border-radius: 8px;
}

.teaching-goal {
  background: color-mix(in srgb, var(--diagram-blue-soft) 55%, var(--diagram-surface));
  border-color: #dbeafe;
}

.section-index {
  color: var(--diagram-blue);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  line-height: 1.7;
}

.teaching-block h4,
.teaching-list-block h4 {
  margin: 0 0 5px;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.teaching-block p {
  margin: 0;
  color: var(--diagram-muted);
  font-size: 12px;
  line-height: 1.65;
}

.teaching-list-block {
  padding: 12px;
  background: var(--diagram-bg);
  border: 1px solid var(--diagram-border);
  border-radius: 8px;
}

.teaching-list-block.is-warning {
  background: #fffbeb;
  border-color: #fde68a;
}

.teaching-list-block ol,
.teaching-list-block ul {
  display: grid;
  gap: 6px;
  margin: 0;
  padding-left: 18px;
}

.teaching-list-block li {
  color: var(--diagram-muted);
  font-size: 11px;
  line-height: 1.55;
}

.diagram-summary {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  padding: 13px 14px;
  background: #f8fafc;
  border-left: 3px solid var(--diagram-blue);
}

.diagram-summary span {
  color: var(--diagram-blue);
  font-size: 11px;
  font-weight: 750;
}

.diagram-summary p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 580;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .diagram-layout {
    grid-template-columns: 1fr;
  }

  .visual-viewport {
    min-height: 300px;
  }
}

@media (max-width: 620px) {
  .diagram-card:not(.compact) {
    padding: 14px;
  }

  .diagram-header {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .diagram-meta {
    grid-column: 2;
    justify-self: start;
    flex-wrap: wrap;
  }

  .compact .diagram-header {
    grid-template-columns: 34px minmax(0, 1fr);
    padding: 13px;
  }

  .compact .diagram-heading-mark {
    width: 32px;
    height: 32px;
  }

  .compact .visual-viewport {
    min-height: 220px;
    max-height: 260px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .diagram-card.is-interactive {
    transition: none;
  }
}
</style>
