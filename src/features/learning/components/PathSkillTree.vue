<template>
  <div class="roadmap-track scroll-x">
    <div 
      v-for="(stage, stageIdx) in stages" 
      :key="stage.stage_id" 
      class="stage-column-wrapper"
    >
      <!-- Stage Column Container -->
      <div class="stage-column">
        <!-- Stage Header -->
        <div class="stage-column-header">
          <span class="stage-number">STAGE 0{{ stageIdx + 1 }}</span>
          <h4>{{ stage.title }}</h4>
        </div>
        
        <!-- Nodes stack in this stage -->
        <div class="nodes-stack">
          <div
            v-for="node in getStageNodes(stage.stage_id)"
            :key="node.node_id"
            class="roadmap-node-card"
            :class="[node.status, { 'active': isActive(node.status) }]"
            @click="handleNodeClick(node)"
          >
            <!-- Left border colored status indicator -->
            <div class="card-status-bar" :class="node.status"></div>
            
            <div class="node-main-info">
              <div class="node-top-row">
                <span class="step-label">STEP {{ node.priority }}</span>
                <span v-if="node.difficulty" class="node-difficulty" :class="node.difficulty">
                  {{ difficultyText(node.difficulty) }}
                </span>
              </div>
              
              <h5 class="node-title">{{ node.title }}</h5>
              
              <div class="node-status-row">
                <span class="status-desc" :class="node.status">{{ statusText(node.status) }}</span>
                <!-- Status icon / dot -->
                <div class="status-dot-icon" :class="node.status">
                  <svg v-if="isCompleted(node.status)" xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  <svg v-else-if="node.status === 'locked'" xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  <span v-else class="pulse-indicator"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Stage Linker Arrow (not shown for the last stage) -->
      <div v-if="stageIdx < stages.length - 1" class="stage-linker">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
          <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
        </svg>
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
  emit('node-click', node)
}

const difficultyText = (diff?: string | null) => {
  if (diff === 'beginner') return '入门'
  if (diff === 'intermediate') return '中级'
  if (diff === 'advanced') return '高级'
  return diff || '常规'
}

const statusText = (status: string) => {
  switch (status) {
    case 'available': return '可开始'
    case 'in_progress': return '学习中'
    case 'remediation': return '专项巩固中'
    case 'completed': return '已掌握'
    case 'completed_with_gaps': return '带缺口掌握'
    case 'locked': return '未解锁'
    default: return status
  }
}
</script>

<style scoped>
.roadmap-track {
  display: flex;
  gap: 0;
  padding: 16px 8px;
  overflow-x: auto;
  align-items: flex-start;
  width: 100%;
}

/* Scrollbar customization for horizontal track */
.roadmap-track::-webkit-scrollbar {
  height: 8px;
}
.roadmap-track::-webkit-scrollbar-track {
  background: var(--color-bg);
  border-radius: 999px;
}
.roadmap-track::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 999px;
}
.roadmap-track::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}

.stage-column-wrapper {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.stage-column {
  width: 300px;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.stage-column:hover {
  background: rgba(255, 255, 255, 0.6);
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-md);
}

.stage-column-header {
  border-bottom: 2px solid var(--color-primary-soft);
  padding-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stage-number {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--color-primary);
  letter-spacing: 0.08em;
}

.stage-column-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: var(--color-text-strong);
  line-height: 1.35;
}

.nodes-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.roadmap-node-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px;
  cursor: pointer;
  position: relative;
  display: flex;
  flex-direction: column;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}

.roadmap-node-card:hover:not(.locked) {
  transform: translateY(-2px);
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-sm);
}

.roadmap-node-card.locked {
  cursor: not-allowed;
  opacity: 0.7;
  background: var(--color-bg);
}

/* Left vertical indicator stripe */
.card-status-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--color-border);
}
.card-status-bar.completed {
  background: var(--color-success);
}
.card-status-bar.completed_with_gaps {
  background: var(--color-danger);
}
.card-status-bar.in_progress,
.card-status-bar.remediation,
.card-status-bar.reinforced {
  background: var(--color-primary);
}
.card-status-bar.available {
  background: var(--color-primary-border);
}

.node-main-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.step-label {
  font-size: 0.65rem;
  font-weight: 800;
  color: var(--color-text-muted);
  letter-spacing: 0.02em;
}

.roadmap-node-card.active .step-label {
  color: var(--color-primary);
}

.node-difficulty {
  font-size: 0.65rem;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
}
.node-difficulty.beginner {
  background: rgba(16, 185, 129, 0.08);
  color: #10b981;
}
.node-difficulty.intermediate {
  background: rgba(245, 158, 11, 0.08);
  color: #f59e0b;
}
.node-difficulty.advanced {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.node-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.4;
}

.roadmap-node-card:hover:not(.locked) .node-title {
  color: var(--color-primary);
}

.node-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
  border-top: 1px solid var(--color-border-light);
  padding-top: 8px;
}

.status-desc {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted);
}
.status-desc.completed {
  color: var(--color-success);
}
.status-desc.completed_with_gaps {
  color: var(--color-danger);
}
.status-desc.in_progress,
.status-desc.remediation,
.status-desc.reinforced {
  color: var(--color-primary);
}

.status-dot-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  background: var(--color-bg);
}

.status-dot-icon.completed {
  background: var(--color-success);
  border-color: var(--color-success);
  color: white;
}

.status-dot-icon.completed_with_gaps {
  background: var(--color-danger);
  border-color: var(--color-danger);
  color: white;
}

.status-dot-icon.in_progress,
.status-dot-icon.remediation,
.status-dot-icon.reinforced,
.status-dot-icon.available {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.pulse-indicator {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse-ring-anim 2s infinite;
}

@keyframes pulse-ring-anim {
  0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4); }
  70% { transform: scale(1.15); box-shadow: 0 0 0 5px rgba(79, 70, 229, 0); }
  100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
}

/* Connecting link arrow between stages */
.stage-linker {
  padding: 0 12px;
  color: var(--color-border-hover);
  animation: bounce-x 2.5s infinite ease-in-out;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes bounce-x {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(4px); }
}
</style>
