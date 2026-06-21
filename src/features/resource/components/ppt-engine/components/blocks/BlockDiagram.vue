<template>
  <div class="block-diagram">
    <div class="nodes" :class="`dir-${block.direction.toLowerCase()}`">
      <div v-for="node in block.nodes" :key="node.id" class="node">{{ node.label }}</div>
    </div>
    <div class="edges">
      <div v-for="(edge, index) in block.edges" :key="`${edge.source}-${edge.target}-${index}`" class="edge">
        <span>{{ edge.source }}</span>
        <span class="arrow">→</span>
        <span>{{ edge.target }}</span>
        <span v-if="edge.label" class="edge-label">{{ edge.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DiagramBlock } from '../../types/ppt'

defineProps<{
  block: DiagramBlock
}>()
</script>

<style scoped>
.block-diagram {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.nodes {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.node {
  padding: 12px 16px;
  border-radius: 14px;
  background: var(--ppt-bg-tertiary);
  border: 1px solid var(--ppt-border);
  font-weight: 700;
  color: var(--ppt-text-primary);
}

.edges {
  display: grid;
  gap: 8px;
}

.edge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
  color: var(--ppt-text-secondary);
}

.arrow {
  color: var(--ppt-accent);
  font-weight: 800;
}

.edge-label {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--ppt-badge-bg);
  color: var(--ppt-badge-text);
}
</style>
