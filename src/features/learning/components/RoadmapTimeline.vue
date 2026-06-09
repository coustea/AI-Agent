<template>
  <div class="roadmap-timeline">
    <div v-for="(stage, stageIndex) in groupedStages" :key="stage.stage_id" class="roadmap-stage">
      
      <div class="stage-header">
        <div class="stage-dot"></div>
        <div class="stage-info">
          <span class="stage-kicker">Stage {{ stageIndex + 1 }}</span>
          <h2>{{ stage.title }}</h2>
          <p>{{ stage.description }}</p>
        </div>
      </div>

      <div class="stage-nodes">
        <BaseCard
          v-for="node in stage.nodes"
          :key="node.id"
          hoverable
          class="roadmap-node-card"
          :class="[node.status]"
          @click="handleNodeClick(node)"
        >
          <div class="node-connector">
            <div class="node-dot" :class="node.status"></div>
          </div>

          <div class="node-content">
            <div class="node-head">
              <strong>{{ node.title }}</strong>
              <BaseTag pill :tone="statusTone(node.status)">{{ statusText(node.status) }}</BaseTag>
            </div>

            <p>{{ node.mastery_target || node.recommendation_reason || '进入节点后开始学习。' }}</p>

            <div class="node-meta">
              <span v-if="node.estimated_minutes">⏱ {{ node.estimated_minutes }} 分钟</span>
              <span v-if="node.difficulty">💪 {{ node.difficulty }}</span>
              <span v-if="node.prerequisites && node.prerequisites.length > 0">
                🔗 依赖 {{ node.prerequisites.length }} 个前置节点
              </span>
            </div>
          </div>
        </BaseCard>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PropType } from 'vue'
import BaseCard from '@/shared/ui/BaseCard.vue'
import BaseTag from '@/shared/ui/BaseTag.vue'
import type { LearningPathStage, LearningPathNode } from '@/features/learning/model/path'

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
  (e: 'node-click', nodeId: number): void
}>()

const groupedStages = computed(() => {
  const nodeMap = new Map<string, LearningPathNode[]>()
  for (const node of props.nodes) {
    if (!nodeMap.has(node.stage_id)) nodeMap.set(node.stage_id, [])
    nodeMap.get(node.stage_id)!.push(node)
  }
  return props.stages.map((stage) => ({
    ...stage,
    nodes: (nodeMap.get(stage.stage_id) || []).slice().sort((a, b) => a.priority - b.priority),
  }))
})

const handleNodeClick = (node: LearningPathNode) => {
  emit('node-click', node.id)
}

const statusText = (status: string) => {
  switch (status) {
    case 'available': return '可学习'
    case 'locked': return '未解锁'
    case 'completed': return '已通过'
    case 'completed_with_gaps': return '带缺口完成'
    default: return status
  }
}

const statusTone = (status: string): "indigo" | "emerald" | "slate" => {
  switch (status) {
    case 'available': return 'indigo'
    case 'completed': 
    case 'completed_with_gaps': return 'emerald'
    case 'locked': return 'slate'
    default: return 'slate'
  }
}
</script>

<style scoped>
.roadmap-timeline {
  display: flex;
  flex-direction: column;
  padding: 10px 0;
}

.roadmap-stage {
  position: relative;
  margin-bottom: 32px;
}

.roadmap-stage:last-child {
  margin-bottom: 0;
}

/* Stage Header */
.stage-header {
  position: relative;
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.stage-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 4px solid var(--color-primary);
  z-index: 2;
  margin-top: 4px;
}

.stage-info {
  flex: 1;
}

.stage-kicker {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.stage-info h2 {
  margin: 0 0 6px;
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

.stage-info p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

/* Nodes & Timeline Track */
.stage-nodes {
  position: relative;
  padding-left: 40px; /* Space for the track */
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-nodes::before {
  content: '';
  position: absolute;
  top: -40px; /* Connect to stage dot */
  bottom: 0;
  left: 7px; /* Align with center of 16px stage dot */
  width: 2px;
  background: var(--color-border);
  z-index: 1;
}

.roadmap-node-card {
  position: relative;
  width: 100%;
  text-align: left;
  padding: 20px;
  cursor: pointer;
  border-left: 4px solid transparent;
  overflow: visible; /* To allow connector to break out if needed */
}

/* Connect the node card to the main track */
.node-connector {
  position: absolute;
  left: -40px;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 2px;
  background: var(--color-border);
  z-index: 1;
}

.node-dot {
  position: absolute;
  left: 6px; /* Align perfectly on the vertical track */
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  z-index: 2;
  transition: all var(--transition-base);
}

.node-dot.available {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.node-dot.completed,
.node-dot.completed_with_gaps {
  border-color: var(--color-success);
  background: var(--color-success);
}

.roadmap-node-card.available {
  border-left-color: var(--color-primary);
}

.roadmap-node-card.completed,
.roadmap-node-card.completed_with_gaps {
  border-left-color: var(--color-success);
}

.roadmap-node-card.locked {
  opacity: 0.6;
  cursor: not-allowed;
}

.roadmap-node-card:hover .node-dot.available {
  background: var(--color-primary);
  transform: translate(-50%, -50%) scale(1.2);
}

.node-content {
  position: relative;
  z-index: 2;
}

.node-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.node-head strong {
  color: var(--color-text);
  font-size: 1.1rem;
  font-weight: 600;
}

.node-content p {
  margin: 0 0 12px;
  line-height: 1.6;
  font-size: 0.95rem;
  color: var(--color-text-muted);
}

.node-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-faint);
}

@media (max-width: 640px) {
  .stage-header {
    gap: 16px;
  }
  .stage-nodes {
    padding-left: 24px;
  }
  .stage-nodes::before {
    left: 7px;
  }
  .node-connector {
    left: -24px;
    width: 20px;
  }
}
</style>
