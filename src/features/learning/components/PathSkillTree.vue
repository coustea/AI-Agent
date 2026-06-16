<template>
  <div class="timeline-container scroll-y">
    <div v-for="(stage, stageIdx) in stages" :key="stage.stage_id" class="stage-section">
      <!-- Stage Header -->
      <div class="stage-header">
        <div class="stage-badge">阶段 {{ stageIdx + 1 }}</div>
        <div class="stage-info">
          <h4>{{ stage.title }}</h4>
          <p>{{ stage.description }}</p>
        </div>
      </div>

      <!-- Nodes list within this stage -->
      <div class="nodes-list">
        <div 
          v-for="node in getStageNodes(stage.stage_id)" 
          :key="node.node_id" 
          class="node-card"
          :class="[node.status, { 'active-pulse': isActive(node.status) }]"
          @click="handleNodeClick(node)"
        >
          <!-- Left Timeline Line & Status Icon -->
          <div class="node-indicator">
            <div class="status-icon">
              <!-- Completed Checkmark -->
              <svg v-if="isCompleted(node.status)" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="icon-check"><polyline points="20 6 9 17 4 12"/></svg>
              <!-- Locked Lock -->
              <svg v-else-if="node.status === 'locked'" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="icon-lock"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              <!-- Available / In Progress Dot -->
              <span v-else class="pulse-dot"></span>
            </div>
            <div class="timeline-line"></div>
          </div>

          <!-- Node Details Card -->
          <div class="node-content">
            <div class="node-meta">
              <span class="step-num">STEP {{ node.priority }}</span>
              <span v-if="node.estimated_minutes" class="duration-badge">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="duration-icon"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                {{ node.estimated_minutes }} min
              </span>
              <span v-if="node.difficulty" class="difficulty-badge" :class="node.difficulty">{{ node.difficulty }}</span>
            </div>
            
            <h5 class="node-title">{{ node.title }}</h5>
            <p v-if="node.mastery_target" class="node-desc">{{ node.mastery_target }}</p>
            <p v-else-if="node.recommendation_reason" class="node-desc">{{ node.recommendation_reason }}</p>
            
            <!-- Active CTA button -->
            <div v-if="isActive(node.status)" class="node-cta">
              <span class="cta-text">开始学习</span>
              <svg class="cta-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { LearningPathNode, LearningPathStage } from '@/features/learning/model/path'

const props = defineProps({
  stages: {
    type: Array as PropType<LearningPathStage[]>,
    required: true,
  },
  nodes: {
    type: Array as PropType<LearningPathNode[]>,
    required: true,
  },
})

const emit = defineEmits<{
  (e: 'node-click', node: LearningPathNode): void
}>()

// Filter and sort nodes belonging to a specific stage by priority
const getStageNodes = (stageId: string) => {
  return props.nodes
    .filter(n => n.stage_id === stageId)
    .sort((a, b) => a.priority - b.priority)
}

const isCompleted = (status: string) => {
  return ['completed', 'completed_with_gaps'].includes(status)
}

const isActive = (status: string) => {
  return ['available', 'in_progress', 'remediation', 'reinforced'].includes(status)
}

const handleNodeClick = (node: LearningPathNode) => {
  if (node.status !== 'locked') {
    emit('node-click', node)
  }
}
</script>

<style scoped>
.timeline-container {
  padding: 24px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.stage-section {
  margin-bottom: 32px;
}

.stage-section:last-child {
  margin-bottom: 0;
}

.stage-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.stage-badge {
  background: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18);
}

.stage-info h4 {
  margin: 0 0 4px;
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--color-text);
}

.stage-info p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 0; /* Continuous vertical timeline */
  padding-left: 20px;
}

.node-card {
  display: flex;
  gap: 20px;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding: 16px;
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  margin-bottom: 4px;
}

/* Locked nodes are not clickable */
.node-card.locked {
  cursor: not-allowed;
  opacity: 0.65;
}

.node-card:not(.locked):hover {
  background: var(--color-bg);
  border-color: var(--color-border);
}

.node-card:not(.locked):hover .node-content {
  transform: translateX(4px);
}

/* Timeline Indicator & Line */
.node-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.status-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  transition: all 0.3s ease;
  background: var(--color-surface);
  border: 2px solid var(--color-border);
}

/* Completed styles */
.node-card.completed .status-icon,
.node-card.completed_with_gaps .status-icon {
  background: #10b981; /* Emerald */
  border-color: #10b981;
  color: #fff;
}

/* Locked styles */
.node-card.locked .status-icon {
  background: var(--color-bg);
  border-color: var(--color-border);
  color: var(--color-text-muted);
}

/* Active styles */
.node-card:not(.locked):not(.completed):not(.completed_with_gaps) .status-icon {
  border-color: #2563eb;
  color: #2563eb;
}

.pulse-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #2563eb;
}

.active-pulse .pulse-dot {
  animation: pulse-animation 2s infinite;
}

@keyframes pulse-animation {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.45);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 8px rgba(37, 99, 235, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0);
  }
}

.timeline-line {
  position: absolute;
  top: 28px;
  bottom: -28px;
  width: 2px;
  background: var(--color-border);
  z-index: 1;
}

.nodes-list > .node-card:last-child .timeline-line {
  display: none; /* No line after the last node in the stage */
}

/* Node Content Details */
.node-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.node-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.step-num {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--color-text-muted);
  letter-spacing: 0.05em;
}

.node-card.in_progress .step-num,
.node-card.available .step-num {
  color: #2563eb;
}

.duration-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.difficulty-badge {
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid transparent;
}
.difficulty-badge.beginner { background: rgba(16, 185, 129, 0.1); color: #059669; border-color: rgba(16, 185, 129, 0.2); }
.difficulty-badge.intermediate { background: rgba(37, 99, 235, 0.1); color: #2563eb; border-color: rgba(37, 99, 235, 0.2); }
.difficulty-badge.advanced { background: rgba(124, 58, 237, 0.1); color: #7c3aed; border-color: rgba(124, 58, 237, 0.2); }

.node-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  transition: color 0.2s ease;
}

.node-card:not(.locked):hover .node-title {
  color: #2563eb;
}

.node-desc {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.4;
}

/* Active CTA Arrow */
.node-cta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  color: #2563eb;
  opacity: 0.8;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.node-card:hover .node-cta {
  opacity: 1;
  transform: translateX(2px);
}

.cta-arrow {
  transition: transform 0.2s ease;
}
.node-card:hover .cta-arrow {
  transform: translateX(2px);
}
</style>
