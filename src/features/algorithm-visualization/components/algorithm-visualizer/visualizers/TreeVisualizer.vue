<template>
  <div class="tree-visualizer">
    <div class="visualizer-meta">
      <div class="flex flex-col">
        <h3>树结构可视化</h3>
        <p>展示树节点的遍历和访问过程，实时绘制父子节点连接线。</p>
      </div>
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>
    </div>
    <div class="chart-shell">
      <div v-if="layoutNodes.length" class="tree-container">
        <!-- SVG Connection Lines -->
        <svg class="tree-links-svg">
          <line
            v-for="(link, idx) in treeLinks"
            :key="idx"
            :x1="link.x1"
            :y1="link.y1"
            :x2="link.x2"
            :y2="link.y2"
            :class="['tree-link', link.tone || 'default']"
          />
        </svg>

        <!-- Node Elements -->
        <div
          v-for="node in layoutNodes"
          :key="node.id"
          :class="['tree-node', node.tone || 'default']"
          :style="{ left: `${node.px}px`, top: `${node.py}px` }"
        >
          <span class="node-label">{{ node.label }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待树数据初始化...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
}>()

// Parse raw nodes from trace state
const rawNodes = computed(() => {
  const raw = props.currentEvent?.state?.structure?.nodes
  return Array.isArray(raw) ? raw : []
})

// Build tree mapping and links
const treeData = computed(() => {
  const nodes = rawNodes.value
  const nodeMap = new Map<string, any>()
  nodes.forEach(n => nodeMap.set(String(n.id), { ...n }))

  const links: Array<{ from: string; to: string; tone?: string }> = []
  const hasParent = new Set<string>()

  // 1. Try to find links using left/right properties
  nodes.forEach(n => {
    const idStr = String(n.id)
    if (n.left !== undefined && n.left !== null && String(n.left) !== '') {
      const leftId = String(n.left)
      links.push({ from: idStr, to: leftId, tone: n.tone === 'visited' && nodeMap.get(leftId)?.tone === 'visited' ? 'visited' : 'default' })
      hasParent.add(leftId)
    }
    if (n.right !== undefined && n.right !== null && String(n.right) !== '') {
      const rightId = String(n.right)
      links.push({ from: idStr, to: rightId, tone: n.tone === 'visited' && nodeMap.get(rightId)?.tone === 'visited' ? 'visited' : 'default' })
      hasParent.add(rightId)
    }
  })

  // 2. Fallback: If no left/right is defined (e.g. C++), build standard binary heap index connections
  if (links.length === 0 && nodes.length > 1) {
    nodes.forEach((n, idx) => {
      const idStr = String(n.id)
      const leftIdx = 2 * idx + 1
      const rightIdx = 2 * idx + 2

      if (leftIdx < nodes.length) {
        const leftId = String(nodes[leftIdx].id)
        links.push({ from: idStr, to: leftId, tone: n.tone === 'visited' && nodes[leftIdx].tone === 'visited' ? 'visited' : 'default' })
        hasParent.add(leftId)
      }
      if (rightIdx < nodes.length) {
        const rightId = String(nodes[rightIdx].id)
        links.push({ from: idStr, to: rightId, tone: n.tone === 'visited' && nodes[rightIdx].tone === 'visited' ? 'visited' : 'default' })
        hasParent.add(rightId)
      }
    })
  }

  // Find root node(s)
  const roots = nodes.map(n => String(n.id)).filter(id => !hasParent.has(id))
  return { nodeMap, links, roots }
})

// Calculate positions using In-order DFS layout to prevent overlaps and keep tree centered
const layoutNodes = computed(() => {
  const { nodeMap, links, roots } = treeData.value
  if (nodeMap.size === 0) return []

  // Create adjacency list for traversal
  const adj = new Map<string, string[]>()
  nodeMap.forEach((_, id) => adj.set(id, []))
  links.forEach(l => {
    const list = adj.get(l.from) || []
    list.push(l.to)
    adj.set(l.from, list)
  })

  const coords = new Map<string, { x: number; y: number }>()
  let currentX = 0

  function traverse(nodeId: string, depth: number) {
    const children = adj.get(nodeId) || []
    if (children[0]) traverse(children[0], depth + 1)
    coords.set(nodeId, { x: currentX++, y: depth })
    if (children[1]) traverse(children[1], depth + 1)
  }

  // Run layout for each root
  roots.forEach(r => traverse(r, 0))

  // Convert to coordinates
  const canvasWidth = 800
  const nodeCount = nodeMap.size
  const colWidth = nodeCount > 1 ? (canvasWidth - 80) / (nodeCount - 1) : 0
  const rowHeight = 52

  return Array.from(nodeMap.values()).map(n => {
    const idStr = String(n.id)
    const c = coords.get(idStr) || { x: 0, y: 0 }
    
    // Scale and center nodes horizontally
    const px = nodeCount > 1 ? 40 + c.x * colWidth : canvasWidth / 2
    const py = 30 + c.y * rowHeight

    return {
      ...n,
      px,
      py,
    }
  })
})

// Coordinates of tree link lines
const treeLinks = computed(() => {
  const { links } = treeData.value
  const nodes = layoutNodes.value
  const posMap = new Map<string, { px: number; py: number }>()
  nodes.forEach(n => posMap.set(String(n.id), { px: n.px, py: n.py }))

  return links.map(l => {
    const fromPos = posMap.get(l.from) || { px: 0, py: 0 }
    const toPos = posMap.get(l.to) || { px: 0, py: 0 }
    return {
      x1: fromPos.px,
      y1: fromPos.py,
      x2: toPos.px,
      y2: toPos.py,
      tone: l.tone,
    }
  })
})
</script>

<style scoped>
.tree-visualizer {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  background: #ffffff;
}

.visualizer-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.visualizer-meta h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.visualizer-meta p {
  margin: 2px 0 0;
  font-size: 11px;
  color: #64748b;
}

.legend {
  display: flex;
  gap: 8px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #475569;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.default {
  background: #cbd5e1;
  border: 1px solid #94a3b8;
}

.legend-dot.visited {
  background: #ecfdf5;
  border: 1px solid #10b981;
}

.chart-shell {
  min-height: 0;
  border-radius: 4px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 12px;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tree-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 240px;
}

.tree-links-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.tree-link {
  stroke: #cbd5e1;
  stroke-width: 1.5;
  transition: stroke 0.25s ease, stroke-width 0.25s ease;
}

.tree-link.visited {
  stroke: #10b981;
  stroke-width: 2.5;
}

.tree-node {
  position: absolute;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #ffffff;
  border: 1.5px solid #cbd5e1;
  font-weight: 600;
  font-size: 11px;
  color: #334155;
  transform: translate(-50%, -50%);
  transition: border-color 0.25s ease, background-color 0.25s ease, color 0.25s ease;
  z-index: 10;
}

@keyframes node-pulse {
  0% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.25); }
  100% { transform: translate(-50%, -50%) scale(1); }
}

.tree-node.visited {
  border-color: #10b981;
  background: #ecfdf5;
  color: #047857;
  animation: node-pulse 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.node-label {
  font-size: 11px;
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #94a3b8;
}
</style>
