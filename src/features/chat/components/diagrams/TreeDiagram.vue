<template>
  <div class="tree-diagram">
    <div class="tree-bg-grid"></div>
    <div class="tree-container">
      <svg
        :viewBox="`0 0 600 ${svgHeight}`"
        class="tree-svg"
      >
        <defs>
          <!-- Nice subtle drop shadow for circles and rects -->
          <filter id="node-shadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.15" />
          </filter>
          
          <!-- Node Gradients -->
          <!-- Standard Tech Blue Gradient -->
          <linearGradient id="grad-blue" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0ea5e9" />
            <stop offset="100%" stop-color="#0284c7" />
          </linearGradient>
          
          <!-- Red Node Gradient (Red-Black Trees) -->
          <linearGradient id="grad-red" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#f43f5e" />
            <stop offset="100%" stop-color="#be123c" />
          </linearGradient>
          
          <!-- Black Node Gradient (Red-Black Trees) -->
          <linearGradient id="grad-black" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#3f3f46" />
            <stop offset="100%" stop-color="#18181b" />
          </linearGradient>
          
          <!-- Highlight Node Gradient -->
          <linearGradient id="grad-highlight" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#f59e0b" />
            <stop offset="100%" stop-color="#d97706" />
          </linearGradient>
          
          <!-- Line Gradient -->
          <linearGradient id="line-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="var(--color-border-hover, #64748b)" />
            <stop offset="100%" stop-color="var(--color-border, #94a3b8)" />
          </linearGradient>
        </defs>

        <!-- Connection Lines -->
        <g class="edges-group">
          <line 
            v-for="edge in layoutEdges" 
            :key="edge.id" 
            class="tree-edge" 
            :x1="edge.x1" 
            :y1="edge.y1" 
            :x2="edge.x2" 
            :y2="edge.y2"
            :data-level="edge.level"
            :style="{ strokeDasharray: edge.length, strokeDashoffset: edge.length }"
            stroke="url(#line-grad)"
            stroke-width="2.5"
          />
        </g>
        
        <!-- Nodes Group -->
        <g 
          v-for="node in layoutNodes" 
          :key="node.id" 
          class="node-group"
          :data-level="node.level"
          :class="[`node-type-${node.type || 'normal'}`]"
        >
          <!-- Circle for non-null nodes -->
          <circle 
            v-if="node.type !== 'null'"
            :cx="node.x" 
            :cy="node.y" 
            :r="22" 
            :fill="getNodeFill(node.type)" 
            class="node-circle"
            filter="url(#node-shadow)"
          />
          <!-- Rect for null nodes (sentinels) -->
          <rect 
            v-else
            :x="node.x - 12" 
            :y="node.y - 12" 
            :width="24" 
            :height="24" 
            :rx="4"
            class="node-rect-null"
            filter="url(#node-shadow)"
          />
          
          <!-- Node Label -->
          <text 
            :x="node.x" 
            :y="node.y" 
            class="node-label"
            :class="{ 'label-null': node.type === 'null' }"
            dominant-baseline="central" 
            text-anchor="middle"
          >
            {{ node.label }}
          </text>
          
          <!-- Node Detail (e.g. height, balance factor, etc.) -->
          <text 
            v-if="node.detail" 
            :x="node.x" 
            :y="node.y + 36" 
            class="node-detail" 
            text-anchor="middle"
          >
            {{ node.detail }}
          </text>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreePayload, TreeDiagramNode } from '@/features/chat/types/chat'

const props = defineProps<{
  payload: TreePayload
}>()

interface LayoutNode extends TreeDiagramNode {
  x: number
  y: number
  level: number
}

interface LayoutEdge {
  id: string
  x1: number
  y1: number
  x2: number
  y2: number
  level: number
  length: number
}

// 节点 ID → 原始数据的快速查找表
const nodeMap = computed(() => {
  const map = new Map<string, TreeDiagramNode>()
  if (props.payload?.nodes) {
    props.payload.nodes.forEach(node => {
      map.set(node.id, node)
    })
  }
  return map
})

// 递归遍历树结构，计算每个节点的 (x, y) 坐标
const layoutNodes = computed(() => {
  const result: LayoutNode[] = []
  if (!props.payload || !props.payload.root_id) return result

  const map = nodeMap.value
  const visited = new Set<string>()

  const traverse = (nodeId: string, x: number, y: number, level: number) => {
    // Avoid infinite recursion if there is a cycle
    if (visited.has(nodeId)) return
    visited.add(nodeId)

    const node = map.get(nodeId)
    if (!node) return

    result.push({
      ...node,
      x,
      y,
      level
    })

    // Horizontal offset decreases by half for each level (level 0 deltaX = 130px)
    const deltaX = 130 * Math.pow(0.5, level)

    if (node.left_id) {
      traverse(node.left_id, x - deltaX, y + 80, level + 1)
    }
    if (node.right_id) {
      traverse(node.right_id, x + deltaX, y + 80, level + 1)
    }
  }

  traverse(props.payload.root_id, 300, 45, 0)
  return result
})

// 计算父子节点之间的连接线坐标
const layoutEdges = computed(() => {
  const edges: LayoutEdge[] = []
  const map = new Map<string, LayoutNode>()
  layoutNodes.value.forEach(n => {
    map.set(n.id, n)
  })

  layoutNodes.value.forEach(parent => {
    if (parent.left_id) {
      const child = map.get(parent.left_id)
      if (child) {
        const dx = child.x - parent.x
        const dy = child.y - parent.y
        const length = Math.sqrt(dx * dx + dy * dy)
        edges.push({
          id: `${parent.id}-${child.id}`,
          x1: parent.x,
          y1: parent.y,
          x2: child.x,
          y2: child.y,
          level: child.level,
          length
        })
      }
    }
    if (parent.right_id) {
      const child = map.get(parent.right_id)
      if (child) {
        const dx = child.x - parent.x
        const dy = child.y - parent.y
        const length = Math.sqrt(dx * dx + dy * dy)
        edges.push({
          id: `${parent.id}-${child.id}`,
          x1: parent.x,
          y1: parent.y,
          x2: child.x,
          y2: child.y,
          level: child.level,
          length
        })
      }
    }
  })

  return edges
})

// 树的最大深度
const maxDepth = computed(() => {
  if (layoutNodes.value.length === 0) return 0
  return Math.max(...layoutNodes.value.map(n => n.level))
})

const svgHeight = computed(() => {
  return maxDepth.value * 80 + 100
})

const getNodeFill = (type: string | null | undefined) => {
  if (type === 'red') return 'url(#grad-red)'
  if (type === 'black') return 'url(#grad-black)'
  if (type === 'highlight') return 'url(#grad-highlight)'
  return 'url(#grad-blue)'
}
</script>

<style scoped>
.tree-diagram {
  position: relative;
  width: 100%;
  overflow-x: auto;
  padding: 32px 16px;
  background: linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface-hover) 100%);
  border-radius: 16px;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.02);
  display: flex;
  justify-content: center;
}

.tree-bg-grid {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-size: 20px 20px;
  background-image: radial-gradient(circle, var(--color-border-hover) 1px, transparent 1px);
  opacity: 0.4;
  pointer-events: none;
  border-radius: 16px;
  z-index: 0;
}

.tree-container {
  position: relative;
  z-index: 1;
  min-width: 600px;
  width: 100%;
  max-width: 600px;
  display: flex;
  justify-content: center;
}

.tree-svg {
  width: 100%;
  max-width: 600px;
  height: auto;
  overflow: visible;
}

/* Connection lines */
.tree-edge {
  stroke-linecap: round;
  transition: all 0.3s ease;
  opacity: 0.85;
  /* Line drawing animation */
  stroke-dasharray: 1000;
  stroke-dashoffset: 1000;
  animation: draw-edge 1.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  will-change: transform, opacity;
}

@keyframes draw-edge {
  to {
    stroke-dashoffset: 0;
  }
}

/* Stagger line animations by level */
.tree-edge[data-level="1"] { animation-delay: 0.1s; }
.tree-edge[data-level="2"] { animation-delay: 0.3s; }
.tree-edge[data-level="3"] { animation-delay: 0.5s; }
.tree-edge[data-level="4"] { animation-delay: 0.7s; }
.tree-edge[data-level="5"] { animation-delay: 0.9s; }

/* Node groups */
.node-group {
  opacity: 0;
  transform-box: fill-box;
  transform-origin: center;
  animation: fade-in-node 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
  will-change: transform, opacity;
  backface-visibility: hidden;
}

@keyframes fade-in-node {
  from {
    opacity: 0;
    transform: scale(0.5);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Stagger node animations by level */
.node-group[data-level="0"] { animation-delay: 0s; }
.node-group[data-level="1"] { animation-delay: 0.2s; }
.node-group[data-level="2"] { animation-delay: 0.4s; }
.node-group[data-level="3"] { animation-delay: 0.6s; }
.node-group[data-level="4"] { animation-delay: 0.8s; }
.node-group[data-level="5"] { animation-delay: 1.0s; }

/* Circle design */
.node-circle {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  will-change: transform;
  backface-visibility: hidden;
}

.node-group:hover .node-circle {
  transform: scale(1.12);
  filter: drop-shadow(0 8px 12px rgba(14, 165, 233, 0.3));
}

/* Rect design for null pointers */
.node-rect-null {
  fill: var(--color-surface, #ffffff);
  stroke: var(--color-text-secondary, #94a3b8);
  stroke-width: 2px;
  stroke-dasharray: 4, 3;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
}

.node-group:hover .node-rect-null {
  transform: scale(1.12);
  stroke: var(--color-info, #0ea5e9);
  fill: var(--color-surface-hover, #f8fafc);
}

/* Node Label */
.node-label {
  fill: #ffffff;
  font-size: 13px;
  font-weight: 700;
  user-select: none;
  pointer-events: none;
  font-family: system-ui, -apple-system, sans-serif;
}

.label-null {
  fill: var(--color-text-secondary, #94a3b8);
  font-size: 10px;
  font-weight: 800;
}

.node-group:hover .label-null {
  fill: var(--color-info, #0ea5e9);
}

/* Node detail text (e.g. height, balance factor) */
.node-detail {
  fill: var(--color-text-secondary, #64748b);
  font-size: 11px;
  font-weight: 600;
  user-select: none;
  pointer-events: none;
  font-family: system-ui, -apple-system, sans-serif;
}
</style>
