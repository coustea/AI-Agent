<template>
  <div class="composition hierarchy-map">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="canvas-container ppt-card">
      <svg class="tree-svg" viewBox="0 0 800 450">
        <!-- Lines -->
        <g class="edges">
          <line
            v-for="(edge, idx) in edges"
            :key="`edge-${idx}`"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            stroke="var(--ppt-accent)"
            stroke-width="2"
            stroke-dasharray="4"
          />
        </g>
        <!-- Nodes -->
        <g class="nodes">
          <g
            v-for="node in positionedNodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
          >
            <rect
              x="-60"
              y="-20"
              width="120"
              height="40"
              rx="6"
              fill="var(--ppt-bg-secondary)"
              stroke="var(--ppt-accent)"
              stroke-width="2"
              class="node-rect"
            />
            <text
              text-anchor="middle"
              dominant-baseline="middle"
              fill="var(--ppt-text-primary)"
              font-size="12"
              font-weight="bold"
            >
              {{ node.label }}
            </text>
          </g>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResolvedSlide } from '../model/resolvedSlide'

const props = defineProps<{ slide: ResolvedSlide }>()

interface TreeNode {
  id: string
  label: string
  parent?: string
  children: string[]
  level?: number
  x?: number
  y?: number
}

const positionedNodes = computed(() => {
  const elements = props.slide.elements
  const relations = props.slide.relations || []

  // Build node list
  const nodeMap = new Map<string, TreeNode>()
  elements.forEach(el => {
    const id = el.label || el.content || ''
    nodeMap.set(id, { id, label: el.content || '', children: [] })
  })

  // Add relations
  relations.forEach(rel => {
    if (rel.type === 'parent_child') {
      const parentNode = nodeMap.get(rel.source)
      const childNode = nodeMap.get(rel.target)
      if (parentNode && childNode) {
        parentNode.children.push(rel.target)
        childNode.parent = rel.source
      }
    }
  })

  // Find root nodes (no parent)
  const roots: string[] = []
  nodeMap.forEach((node, id) => {
    if (!node.parent) {
      roots.push(id)
    }
  })

  // Simple BFS / DFS to assign levels and position
  const levels: string[][] = []
  const assignLevels = (id: string, lvl: number) => {
    const node = nodeMap.get(id)
    if (!node) return
    node.level = lvl
    if (!levels[lvl]) levels[lvl] = []
    levels[lvl].push(id)
    node.children.forEach(childId => assignLevels(childId, lvl + 1))
  }

  roots.forEach(rootId => assignLevels(rootId, 0))

  const finalNodes: Array<TreeNode & { x: number; y: number }> = []

  // Assign x, y coordinates
  const height = 400
  const width = 800
  const totalLevels = levels.length

  levels.forEach((lvlIds, lvlIdx) => {
    const count = lvlIds.length
    const y = ((lvlIdx + 0.5) / (totalLevels || 1)) * height + 25
    lvlIds.forEach((id, idx) => {
      const x = ((idx + 0.5) / count) * width
      const node = nodeMap.get(id)
      if (node) {
        node.x = x
        node.y = y
        finalNodes.push({ ...node, x, y })
      }
    })
  })

  return finalNodes
})

const edges = computed(() => {
  const result: Array<{ x1: number; y1: number; x2: number; y2: number }> = []
  const nodes = positionedNodes.value
  const nodeMap = new Map<string, typeof nodes[0]>()
  nodes.forEach(n => nodeMap.set(n.id, n))

  nodes.forEach(node => {
    node.children.forEach(childId => {
      const child = nodeMap.get(childId)
      if (child) {
        result.push({
          x1: node.x,
          y1: node.y + 20,
          x2: child.x,
          y2: child.y - 20,
        })
      }
    })
  })

  return result
})
</script>

<style scoped>
.hierarchy-map {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
}
.subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  margin-bottom: 24px;
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.canvas-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 10px;
  background: var(--ppt-bg-secondary);
}
.tree-svg {
  width: 100%;
  height: 100%;
  max-height: 380px;
}
.node-rect {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}
</style>
