<template>
  <div class="graph-visualizer">
    <div class="chart-shell">
      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>未访问</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
      </div>

      <div v-if="layoutNodes.length" class="graph-container">
        <svg class="graph-links-svg">
          <line
            v-for="(edge, idx) in graphEdges"
            :key="idx"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            :class="['graph-edge', edge.tone || 'default']"
          />
        </svg>

        <div
          v-for="node in layoutNodes"
          :key="node.id"
          :class="['graph-node', node.tone || 'default']"
          :style="{ left: `${node.px}px`, top: `${node.py}px` }"
        >
          <span>{{ node.label }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待图数据初始化...</div>
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

// 从 trace step 解析图节点
const rawNodes = computed(() => {
  const raw = props.currentEvent?.state?.structure?.nodes
  return Array.isArray(raw) ? raw : []
})

// 构建图的边列表（优先使用节点声明的 edges，否则用默认拓扑）
const edgesList = computed(() => {
  const nodes = rawNodes.value
  if (nodes.length <= 1) return []

  const connections: Array<{ u: string; v: string }> = []
  
  let hasExplicitEdges = false
  nodes.forEach(n => {
    if (Array.isArray(n.edges)) {
      hasExplicitEdges = true
      n.edges.forEach((edge: any) => {
        if (edge && edge.to !== undefined) {
          connections.push({ u: String(n.id), v: String(edge.to) })
        }
      })
    }
  })

  if (hasExplicitEdges) {
    return connections
  }

  // 6 节点默认图：标准搜索测试图的环形+交叉边
  if (nodes.length === 6) {
    const defaultEdges = [
      { u: '0', v: '1' },
      { u: '0', v: '2' },
      { u: '1', v: '3' },
      { u: '1', v: '4' },
      { u: '2', v: '5' },
      { u: '3', v: '4' }, // Add cycle helper
      { u: '4', v: '5' }  // Add cycle helper
    ]
    return defaultEdges.filter(e => {
      return nodes.some(n => String(n.id) === e.u) && nodes.some(n => String(n.id) === e.v)
    })
  }

  // 通用降级：按索引构建环形+交叉边
  for (let i = 0; i < nodes.length; i++) {
    const next = (i + 1) % nodes.length
    connections.push({ u: String(nodes[i].id), v: String(nodes[next].id) })
    if (i + 2 < nodes.length) {
      connections.push({ u: String(nodes[i].id), v: String(nodes[i + 2].id) })
    }
  }
  return connections
})

// 使用圆形布局计算节点坐标（防止重叠）
const layoutNodes = computed(() => {
  const nodes = rawNodes.value
  if (nodes.length === 0) return []

  const canvasWidth = 800
  const canvasHeight = 240
  const centerX = canvasWidth / 2
  const centerY = canvasHeight / 2
  // 圆形布局半径
  const radius = 84

  return nodes.map((n, idx) => {
    // 如果后端已提供自定义坐标，优先使用
    if (n.x && n.y) {
      return {
        ...n,
        px: n.x,
        py: n.y
      }
    }

    // 圆形分布角度计算
    const angle = (idx * 2 * Math.PI) / nodes.length - Math.PI / 2
    const px = centerX + radius * Math.cos(angle)
    const py = centerY + radius * Math.sin(angle)

    return {
      ...n,
      px,
      py
    }
  })
})

// 计算图边的起点/终点 SVG 坐标
const graphEdges = computed(() => {
  const nodes = layoutNodes.value
  const edges = edgesList.value
  const posMap = new Map<string, { px: number; py: number; tone?: string }>()
  nodes.forEach(n => posMap.set(String(n.id), { px: n.px, py: n.py, tone: n.tone }))

  return edges.map(e => {
    const uPos = posMap.get(e.u) || { px: 0, py: 0, tone: 'default' }
    const vPos = posMap.get(e.v) || { px: 0, py: 0, tone: 'default' }
    
    // 两端节点都已访问时高亮该边（表示遍历路径）
    const isVisitedPath = uPos.tone === 'visited' && vPos.tone === 'visited'

    return {
      x1: uPos.px,
      y1: uPos.py,
      x2: vPos.px,
      y2: vPos.py,
      tone: isVisitedPath ? 'visited' : 'default'
    }
  })
})
</script>

<style scoped>
.graph-visualizer {
  height: 100%;
  min-height: 0;
  display: flex;
  padding: 12px;
  background: transparent;
}

.legend {
  position: absolute;
  top: 12px;
  right: 14px;
  z-index: 1;
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-surface) 82%, transparent);
  backdrop-filter: blur(6px);
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
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 12px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 240px;
}

.graph-links-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.graph-edge {
  stroke: #cbd5e1;
  stroke-width: 1.5;
  transition: stroke 0.25s ease, stroke-width 0.25s ease;
}

.graph-edge.visited {
  stroke: #10b981;
  stroke-width: 2.5;
}

.graph-node {
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

.graph-node.visited {
  border-color: #10b981;
  background: #ecfdf5;
  color: #047857;
  animation: node-pulse 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
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
