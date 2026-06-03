<template>
  <article class="diagram-card" :class="{ compact: props.compact }">
    <header class="card-header animate-block">
      <div>
        <p class="card-kicker">{{ typeLabel }}</p>
        <h3>{{ props.diagram.title }}</h3>
        <p v-if="props.diagram.subtitle && !props.compact" class="card-subtitle">{{ props.diagram.subtitle }}</p>
      </div>
      <div v-if="!props.compact" class="header-meta">
        <span class="difficulty-badge" :class="props.diagram.difficulty">{{ difficultyLabel }}</span>
        <span v-if="props.diagram.course" class="course-badge">{{ props.diagram.course }}</span>
      </div>
    </header>

    <section v-if="!props.compact" class="goal-section animate-block" style="animation-delay: 0.1s;">
      <span class="goal-label">教学目标</span>
      <p>{{ props.diagram.teaching_goal }}</p>
    </section>

    <section class="visual-section animate-block" style="animation-delay: 0.2s;">
      <ComparisonDiagram v-if="props.diagram.graph_type === 'comparison'" :payload="props.diagram.visual_content as ComparisonPayload" />
      <FlowchartDiagram v-else-if="props.diagram.graph_type === 'flowchart'" :payload="props.diagram.visual_content as FlowchartPayload" />
      <SequenceDiagram v-else-if="props.diagram.graph_type === 'sequence'" :payload="props.diagram.visual_content as SequencePayload" />
      <FrameworkDiagram v-else-if="props.diagram.graph_type === 'framework'" :payload="props.diagram.visual_content as FrameworkPayload" />
      <SummaryDiagram v-else-if="props.diagram.graph_type === 'summary'" :payload="props.diagram.visual_content as SummaryPayload" />
      <HierarchyDiagram v-else-if="props.diagram.graph_type === 'hierarchy'" :payload="props.diagram.visual_content as HierarchyPayload" />
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

import type {
  ComparisonPayload,
  FlowchartPayload,
  FrameworkPayload,
  HierarchyPayload,
  SequencePayload,
  SummaryPayload,
  TeachingDiagram,
} from '@/chat/types/chat'

const props = defineProps<{
  diagram: TeachingDiagram
  compact?: boolean
}>()

const typeLabel: Record<string, string> = {
  comparison: '对比图板',
  flowchart: '流程图板',
  sequence: '时序图板',
  framework: '框架图板',
  summary: '总结图板',
  hierarchy: '层级图板',
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
  --c-red: #ef4444;
  --c-ink: #0f172a;
  --c-muted: #64748b;
  --c-border: rgba(226, 232, 240, 0.8);
  --c-bg: rgba(255, 255, 255, 0.6);
  --c-glass: rgba(255, 255, 255, 0.85);

  display: grid;
  gap: 16px;
  padding: clamp(16px, 3vw, 24px);
  color: var(--c-ink);
  background: var(--c-glass);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 0 0 1px rgba(255, 255, 255, 0.5) inset;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.diagram-card:not(.compact):hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 20px 25px -5px rgba(0, 0, 0, 0.06), 0 0 0 1px rgba(255, 255, 255, 0.5) inset;
  transform: translateY(-2px);
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
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.goal-section {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.8) 0%, rgba(250, 250, 250, 0.5) 100%);
  border: 1px solid rgba(191, 219, 254, 0.5);
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
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: background 0.2s ease;
}

.teaching-core:hover,
.teaching-points:hover,
.teaching-mistakes:hover,
.teaching-examples:hover {
  background: rgba(255, 255, 255, 0.95);
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
  background: #94a3b8;
  border-radius: 50%;
}

.teaching-mistakes li::before {
  background: var(--c-amber);
}

.card-footer {
  padding: 14px 16px;
  background: linear-gradient(to right, rgba(248, 250, 252, 0.8), rgba(241, 245, 249, 0.4));
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
  padding: 14px;
  border: 0;
  box-shadow: none;
}

.compact .card-header {
  align-items: start;
}

.compact h3 {
  font-size: 18px;
}

.compact .card-kicker {
  display: none;
}

@media (max-width: 640px) {
  .card-header {
    flex-direction: column;
    align-items: start;
  }
}

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
