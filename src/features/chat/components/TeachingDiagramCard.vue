<template>
  <article 
    class="diagram-card" 
    :class="{ compact: props.compact, 'is-interactive': props.compact }"
    @click="props.compact && emit('expand', props.diagram)"
  >
    <header class="card-header animate-block">
      <div>
        <p class="card-kicker">{{ typeLabel[props.diagram.graph_type] || '图解说明' }}</p>
        <h3>{{ props.diagram.title }}</h3>
        <p v-if="props.diagram.subtitle && !props.compact" class="card-subtitle">{{ props.diagram.subtitle }}</p>
      </div>
      <div v-if="!props.compact" class="header-meta">
        <span class="difficulty-badge" :class="props.diagram.difficulty">{{ difficultyLabel[props.diagram.difficulty] || props.diagram.difficulty }}</span>
        <span v-if="props.diagram.course" class="course-badge">{{ props.diagram.course }}</span>
      </div>
    </header>

    <section v-if="!props.compact" class="goal-section animate-block" style="animation-delay: 0.1s;">
      <span class="goal-label">教学目标</span>
      <p>{{ props.diagram.teaching_goal }}</p>
    </section>

    <section class="visual-section animate-block" :class="{ 'compact-visual': props.compact }" style="animation-delay: 0.2s;">
      <div class="visual-wrapper" :id="props.compact ? '' : 'capture-target'">
        <ComparisonDiagram v-if="props.diagram.graph_type === 'comparison'" :payload="props.diagram.visual_content as ComparisonPayload" />
        <FlowchartDiagram v-else-if="props.diagram.graph_type === 'flowchart'" :payload="props.diagram.visual_content as FlowchartPayload" />
        <SequenceDiagram v-else-if="props.diagram.graph_type === 'sequence'" :payload="props.diagram.visual_content as SequencePayload" />
        <FrameworkDiagram v-else-if="props.diagram.graph_type === 'framework'" :payload="props.diagram.visual_content as FrameworkPayload" />
        <SummaryDiagram v-else-if="props.diagram.graph_type === 'summary'" :payload="props.diagram.visual_content as SummaryPayload" />
        <HierarchyDiagram v-else-if="props.diagram.graph_type === 'hierarchy'" :payload="props.diagram.visual_content as HierarchyPayload" />
        <TreeDiagram v-else-if="props.diagram.graph_type === 'tree'" :payload="props.diagram.visual_content as TreePayload" />
        <GridDiagram v-else-if="props.diagram.graph_type === 'grid'" :payload="props.diagram.visual_content as GridPayload" />
        <ProtocolDiagram v-else-if="props.diagram.graph_type === 'protocol'" :payload="props.diagram.visual_content as ProtocolPayload" />
        <TimelineDiagram v-else-if="props.diagram.graph_type === 'timeline'" :payload="props.diagram.visual_content as TimelinePayload" />
      </div>
      
      <!-- Overlay for compact mode -->
      <div v-if="props.compact" class="zoom-overlay">
        <div class="zoom-icon-wrapper">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="zoom-icon">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            <line x1="11" y1="8" x2="11" y2="14"></line>
            <line x1="8" y1="11" x2="14" y2="11"></line>
          </svg>
          <span>点击查看高清大图</span>
        </div>
      </div>
    </section>

    <section v-if="!props.compact" class="teaching-section animate-block" style="animation-delay: 0.3s;">
      <div class="teaching-core">
        <span class="section-label">核心解释</span>
        <p>{{ props.diagram.teaching_content.core_explanation }}</p>
      </div>
      <div v-if="props.diagram.teaching_content.key_points.length" class="teaching-points">
        <span class="section-label">要点</span>
        <ul>
          <li v-for="point in props.diagram.teaching_content.key_points" :key="point">{{ point }}</li>
        </ul>
      </div>
      <div v-if="props.diagram.teaching_content.common_mistakes?.length" class="teaching-mistakes">
        <span class="section-label warn">常见误区</span>
        <ul>
          <li v-for="mistake in props.diagram.teaching_content.common_mistakes" :key="mistake">{{ mistake }}</li>
        </ul>
      </div>
      <div v-if="props.diagram.teaching_content.examples?.length" class="teaching-examples">
        <span class="section-label">示例</span>
        <ul>
          <li v-for="example in props.diagram.teaching_content.examples" :key="example">{{ example }}</li>
        </ul>
      </div>
    </section>

    <footer v-if="!props.compact" class="card-footer animate-block" style="animation-delay: 0.4s;">
      <span class="footer-label">一句话总结</span>
      <p>{{ props.diagram.teaching_content.summary }}</p>
    </footer>
  </article>
</template>

<script setup lang="ts">
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

import type {
  ComparisonPayload,
  FlowchartPayload,
  FrameworkPayload,
  HierarchyPayload,
  SequencePayload,
  SummaryPayload,
  TeachingDiagram,
  TreePayload,
  GridPayload,
  ProtocolPayload,
  TimelinePayload,
} from '@/features/chat/model/chat'

const props = defineProps<{
  diagram: TeachingDiagram
  compact?: boolean
}>()

const emit = defineEmits<{
  (e: 'expand', diagram: TeachingDiagram): void
}>()

const typeLabel: Record<string, string> = {
  comparison: '对比图解',
  flowchart: '流程图解',
  sequence: '时序图解',
  framework: '框架图解',
  summary: '总结图解',
  hierarchy: '层级图解',
  tree: '数据结构 - 树形结构',
  grid: '数据结构/操作系统 - 内存状态格',
  protocol: '网络协议/组成原理 - 报文格式图',
  timeline: '操作系统/组成原理 - 时间时空图',
}

const difficultyLabel: Record<string, string> = {
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高级',
}
</script>

<style scoped>
@keyframes slideUpFade {
  0% { opacity: 0; transform: translateY(12px); }
  100% { opacity: 1; transform: translateY(0); }
}

.animate-block { animation: slideUpFade 0.45s cubic-bezier(0.16, 1, 0.3, 1) both; }

.diagram-card {
  --c-primary: #3b82f6;
  --c-teal: #0d9488;
  --c-amber: #d97706;
  --c-red: var(--color-danger);
  --c-ink: var(--color-text);
  --c-muted: var(--color-text-muted);
  --c-border: var(--color-border);
  --c-bg: var(--color-bg);
  --c-white: var(--color-surface);

  display: grid;
  gap: 16px;
  padding: clamp(16px, 3vw, 24px);
  color: var(--c-ink);
  background: var(--c-white);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s;
}

.diagram-card:not(.compact):hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 20px 25px -5px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

.diagram-card.is-interactive {
  cursor: pointer;
  border: 1px solid #bfdbfe;
  box-shadow: 0 4px 15px -3px rgba(59, 130, 246, 0.1);
}

.diagram-card.is-interactive:hover {
  border-color: #3b82f6;
  box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.2);
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.card-header > div:first-child {
  min-width: 0;
}

.card-kicker {
  margin: 0 0 6px;
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

h3, p { margin: 0; }

h3 {
  color: var(--c-ink);
  font-size: clamp(19px, 3vw, 24px);
  text-wrap: balance;
  line-height: 1.3;
  word-break: break-word;
}

.card-subtitle {
  margin-top: 4px;
  color: var(--c-muted);
  font-size: 14px;
}

.header-meta {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.difficulty-badge {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.difficulty-badge.beginner {
  background: #dcfce7;
  color: #15803d;
}

.difficulty-badge.intermediate {
  background: #dbeafe;
  color: #1d4ed8;
}

.difficulty-badge.advanced {
  background: #fef3c7;
  color: #92400e;
}

.course-badge {
  padding: 3px 10px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.goal-section {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02) inset;
}

.goal-label, .section-label, .footer-label {
  flex-shrink: 0;
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 700;
}

.goal-section p, .teaching-core p {
  font-weight: 550;
  line-height: 1.5;
}

.visual-section {
  display: grid;
  gap: 12px;
  position: relative;
  background: var(--color-bg);
  border-radius: 12px;
  padding: 12px;
  border: 1px solid var(--color-border);
}

.compact-visual {
  max-height: 220px;
  overflow: hidden;
  position: relative;
  padding: 0;
}

.compact-visual .visual-wrapper {
  transform: scale(0.6);
  transform-origin: top left;
  width: 166%; /* 1 / 0.6 */
  pointer-events: none;
}

.zoom-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(255,255,255,1) 0%, rgba(255,255,255,0.4) 60%, rgba(255,255,255,0) 100%);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 24px;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 10;
}

.diagram-card.is-interactive:hover .zoom-overlay {
  opacity: 1;
}

.zoom-icon-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #3b82f6;
  color: white;
  padding: 8px 20px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
  transform: translateY(10px);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.diagram-card.is-interactive:hover .zoom-icon-wrapper {
  transform: translateY(0);
}

.zoom-icon {
  width: 18px;
  height: 18px;
}

.teaching-section {
  display: grid;
  gap: 12px;
}

.teaching-core,
.teaching-points,
.teaching-mistakes,
.teaching-examples {
  padding: 14px 16px;
  background: var(--color-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: box-shadow 0.2s ease;
}

.teaching-core:hover,
.teaching-points:hover,
.teaching-mistakes:hover,
.teaching-examples:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
}

.section-label.warn {
  color: var(--c-amber);
}

.teaching-section ul {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}

.teaching-section li {
  padding-left: 14px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--c-muted);
  position: relative;
}

.teaching-section li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 5px;
  height: 5px;
  background: var(--color-text-faint);
  border-radius: 50%;
}

.teaching-mistakes li::before {
  background: var(--c-amber);
}

.card-footer {
  padding: 14px 16px;
  background: var(--color-bg);
  border: 1px solid var(--c-border);
  border-radius: 10px;
}

.card-footer p {
  margin-top: 4px;
  font-size: 14px;
  font-weight: 550;
  line-height: 1.6;
  color: var(--c-ink);
}

.compact {
  gap: 12px;
  padding: 0;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  overflow: hidden;
}

.compact .card-header {
  align-items: start;
  padding: 16px 16px 0 16px;
}

.compact h3 {
  font-size: 18px;
}
</style>
