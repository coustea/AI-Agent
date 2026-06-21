<template>
  <div class="block-diagram ppt-card diagram-whiteboard">
    <p class="diagram-tag">结构图示 / {{ block.direction === 'LR' || block.direction === 'RL' ? '水平视图' : '垂直视图' }}</p>
    
    <div class="diagram-canvas-wrap">
      <div 
        class="nodes-container" 
        :class="[
          `dir-${block.direction.toLowerCase()}`, 
          { 'is-horizontal': isHorizontal }
        ]"
      >
        <template v-for="(node, idx) in block.nodes" :key="node.id">
          <div class="node-wrapper">
            <div class="ds-node">
              <div class="node-glow"></div>
              <span class="node-text">{{ node.label }}</span>
            </div>
            
            <!-- 连接指示器 (非最后一个元素) -->
            <div v-if="idx < block.nodes.length - 1" class="node-connector">
              <div class="connector-line"></div>
              <div class="connector-arrow">→</div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 边关系列表 (若有标注) -->
    <div v-if="hasEdgeLabels" class="edges-board">
      <div class="board-header">节点指向关系 (Edges)</div>
      <div class="edges-grid">
        <div 
          v-for="(edge, idx) in labeledEdges" 
          :key="`${edge.source}-${edge.target}-${idx}`"
          class="edge-pill"
        >
          <span class="node-ref">{{ edge.source }}</span>
          <span class="edge-arrow">─{{ edge.label || '指向' }}─></span>
          <span class="node-ref">{{ edge.target }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DiagramBlock } from '../../types/ppt'

const props = defineProps<{
  block: DiagramBlock
}>()

const isHorizontal = computed(() => {
  return props.block.direction === 'LR' || props.block.direction === 'RL'
})

const hasEdgeLabels = computed(() => {
  return props.block.edges && props.block.edges.some(e => e.label)
})

const labeledEdges = computed(() => {
  return props.block.edges || []
})
</script>

<style scoped>
.diagram-whiteboard {
  padding: 24px;
  background: var(--ppt-bg-secondary);
  border-radius: var(--ppt-radius-lg);
  border: 1px solid var(--ppt-border);
  box-shadow: var(--ppt-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.diagram-tag {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--ppt-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.diagram-canvas-wrap {
  background: var(--ppt-bg-tertiary);
  border-radius: var(--ppt-radius-md);
  padding: 32px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-x: auto;
  border: 1px dashed var(--ppt-border);
}

.nodes-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.nodes-container.dir-tb {
  flex-direction: column;
}

.nodes-container.dir-bt {
  flex-direction: column-reverse;
}

.nodes-container.dir-rl {
  flex-direction: row-reverse;
}

.node-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.nodes-container.dir-tb .node-wrapper,
.nodes-container.dir-bt .node-wrapper {
  flex-direction: column;
}

.ds-node {
  width: auto;
  min-width: 90px;
  height: 48px;
  padding: 0 18px;
  border-radius: 999px;
  background: var(--ppt-accent-gradient);
  border: 2px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s ease;
}

.ds-node:hover {
  transform: scale(1.05);
}

.node-glow {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 50%;
  background: rgba(255, 255, 255, 0.15);
  pointer-events: none;
}

.node-text {
  color: #FFFFFF;
  font-weight: 800;
  font-size: 1.05rem;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.node-connector {
  display: flex;
  align-items: center;
  gap: 4px;
}

.nodes-container.dir-tb .node-connector,
.nodes-container.dir-bt .node-connector {
  flex-direction: column;
}

.connector-line {
  width: 32px;
  height: 2px;
  background: var(--ppt-accent);
  opacity: 0.5;
}

.nodes-container.dir-tb .connector-line,
.nodes-container.dir-bt .connector-line {
  width: 2px;
  height: 32px;
}

.connector-arrow {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--ppt-accent);
}

.nodes-container.dir-tb .connector-arrow {
  transform: rotate(90deg);
}

.nodes-container.dir-bt .connector-arrow {
  transform: rotate(-90deg);
}

.edges-board {
  border-top: 1px dashed var(--ppt-border);
  padding-top: 16px;
}

.board-header {
  font-weight: 800;
  font-size: 0.9rem;
  color: var(--ppt-text-primary);
  margin-bottom: 12px;
}

.edges-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.edge-pill {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.05);
  border: 1px solid var(--ppt-border);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.88rem;
}

.node-ref {
  font-weight: 800;
  color: var(--ppt-accent);
}

.edge-arrow {
  font-family: var(--ppt-font-mono);
  color: var(--ppt-text-secondary);
}
</style>
