<template>
  <div ref="graphContainerRef" class="path-graph-container">
    <!-- 底层 SVG 画布 -->
    <svg class="connections-canvas">
      <defs>
        <!-- 渐变线定义 -->
        <linearGradient id="active-grad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#46b8b4" />
          <stop offset="100%" stop-color="#6366f1" />
        </linearGradient>

        <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#cbd5e1" />
        </marker>
        <marker id="arrow-active" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#6366f1" />
        </marker>
      </defs>

      <!-- 关系连线 -->
      <g class="lines-group">
        <path
          v-for="(link, idx) in connectorPaths"
          :key="idx"
          :d="link.path"
          :class="{ 'active-line': link.isActive, 'locked-line': link.isLocked }"
          :stroke="link.isActive ? 'url(#active-grad)' : link.isCompleted ? '#10b981' : '#cbd5e1'"
          fill="none"
          :stroke-width="link.isActive ? 2.5 : 1.5"
          :marker-end="link.isActive ? 'url(#arrow-active)' : 'url(#arrow)'"
        />
      </g>
    </svg>

    <!-- 阶段垂直容器列表 -->
    <div class="stages-flow">
      <article
        v-for="stage in stageGridData"
        :key="stage.stageId"
        :id="`stage-block-${stage.stageId}`"
        class="stage-card-block"
      >
        <header class="stage-block-header">
          <h3>{{ stage.title }}</h3>
          <span class="stage-node-count">{{ stage.nodes.length }} 知识节点</span>
        </header>

        <!-- 网格化节点板 -->
        <div class="node-grid-flow" :style="{ gridTemplateColumns: `repeat(${stage.maxCol + 1}, minmax(180px, 1fr))` }">
          <div
            v-for="colIdx in (stage.maxCol + 1)"
            :key="colIdx"
            class="grid-column"
          >
            <button
              v-for="node in getColumnNodes(stage.nodes, colIdx - 1)"
              :key="node.id"
              :data-node-id="node.node_id"
              class="node-flow-card"
              :class="[
                node.status,
                {
                  active: currentNode?.id === node.id,
                  selected: selectedNodeId === node.id
                }
              ]"
              type="button"
              @mouseenter="$emit('node-hover', node)"
              @click="$emit('node-click', node)"
            >
              <!-- 卡片状态竖条 -->
              <i class="status-strip"></i>

              <div class="node-card-body">
                <div class="node-card-meta">
                  <span class="priority-tag">P{{ node.priority }}</span>
                  <span class="difficulty-tag">{{ node.difficulty || '常规' }}</span>
                </div>
                <strong>{{ node.title }}</strong>
                <div class="node-card-footer">
                  <span class="status-label">{{ statusText(node.status) }}</span>
                  <span v-if="node.prerequisites?.length" class="prereq-pill">
                    {{ node.prerequisites.length }} 个前置
                  </span>
                </div>
              </div>
            </button>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import type { LearningPathStage, LearningPathNode } from '@/features/learning-path/model/path'

interface LinkPath {
  path: string
  isActive: boolean
  isCompleted: boolean
  isLocked: boolean
}

const props = defineProps<{
  stages: LearningPathStage[]
  nodes: LearningPathNode[]
  currentNode: LearningPathNode | null
  selectedNodeId: number | null
}>()

const emit = defineEmits<{
  (e: 'node-click', node: LearningPathNode): void
  (e: 'node-hover', node: LearningPathNode): void
}>()

const graphContainerRef = ref<HTMLElement | null>(null)
const connectorPaths = ref<LinkPath[]>([])

// 1. 自动计算网格深度位置 (拓扑深度计算列)
const nodeColumnMap = computed(() => {
  const colMap = new Map<string, number>()
  const visiting = new Set<string>()

  const getCol = (nodeKey: string): number => {
    if (colMap.has(nodeKey)) return colMap.get(nodeKey)!
    if (visiting.has(nodeKey)) {
      return 0
    }
    visiting.add(nodeKey)

    const node = props.nodes.find(n => n.node_id === nodeKey)
    if (!node || !node.prerequisites || node.prerequisites.length === 0) {
      visiting.delete(nodeKey)
      colMap.set(nodeKey, 0)
      return 0
    }
    const prevCols = node.prerequisites.map(p => getCol(p))
    const col = Math.max(...prevCols) + 1
    visiting.delete(nodeKey)
    colMap.set(nodeKey, col)
    return col
  }

  props.nodes.forEach(n => getCol(n.node_id))
  return colMap
})

// 2. 阶段网格组织数据
const stageGridData = computed(() => {
  return props.stages.map(stage => {
    const stageNodes = props.nodes
      .filter(n => n.stage_id === stage.stage_id)
      .map(node => ({
        ...node,
        col: nodeColumnMap.value.get(node.node_id) || 0
      }))
      .sort((a, b) => (a.priority || 0) - (b.priority || 0))

    const maxCol = stageNodes.reduce((max, n) => Math.max(max, n.col), 0)

    return {
      stageId: stage.stage_id,
      title: stage.title,
      nodes: stageNodes,
      maxCol
    }
  })
})

const getColumnNodes = (nodes: any[], colIdx: number) => {
  return nodes.filter(n => n.col === colIdx)
}

const statusText = (status: string) => {
  const map: Record<string, string> = {
    locked: '未解锁',
    available: '可学习',
    in_progress: '学习中',
    remediation: '补救中',
    reinforced: '强化中',
    completed: '已通关',
    completed_with_gaps: '通关有缺口'
  }
  return map[status] || status
}

// 3. 计算贝塞尔连接线
const updateConnectorPaths = async () => {
  await nextTick()
  if (!graphContainerRef.value) return

  const containerRect = graphContainerRef.value.getBoundingClientRect()
  const paths: LinkPath[] = []

  props.nodes.forEach(node => {
    if (!node.prerequisites || node.prerequisites.length === 0) return

    const targetEl = graphContainerRef.value?.querySelector(`[data-node-id="${node.node_id}"]`) as HTMLElement
    if (!targetEl) return

    const targetRect = targetEl.getBoundingClientRect()
    const tX = targetRect.left - containerRect.left
    const tY = targetRect.top - containerRect.top + targetRect.height / 2

    node.prerequisites.forEach(prereqKey => {
      const sourceEl = graphContainerRef.value?.querySelector(`[data-node-id="${prereqKey}"]`) as HTMLElement
      if (!sourceEl) return

      const sourceNode = props.nodes.find(n => n.node_id === prereqKey)
      const sourceRect = sourceEl.getBoundingClientRect()
      const sX = sourceRect.left - containerRect.left + sourceRect.width
      const sY = sourceRect.top - containerRect.top + sourceRect.height / 2

      // 计算贝塞尔控制点
      const cX1 = sX + (tX - sX) * 0.45
      const cY1 = sY
      const cX2 = sX + (tX - sX) * 0.55
      const cY2 = tY

      const pathStr = `M ${sX} ${sY} C ${cX1} ${cY1}, ${cX2} ${cY2}, ${tX} ${tY}`

      // 是否为活跃流向线 (通往当前学习节点)
      const isActive = node.status === 'in_progress' || node.status === 'remediation' || node.status === 'reinforced'
      const isCompleted = sourceNode?.status === 'completed' && (node.status === 'completed' || node.status === 'completed_with_gaps')
      const isLocked = node.status === 'locked'

      paths.push({
        path: pathStr,
        isActive,
        isCompleted,
        isLocked
      })
    })
  })

  connectorPaths.value = paths
}

// 监听容器变动和数据变动
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    updateConnectorPaths()
  })
  if (graphContainerRef.value) {
    resizeObserver.observe(graphContainerRef.value)
  }
  updateConnectorPaths()
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

watch(() => [props.nodes, props.currentNode], () => {
  setTimeout(updateConnectorPaths, 80)
}, { deep: true })
</script>

<style scoped>
.path-graph-container {
  position: relative;
  width: 100%;
  min-height: 400px;
}
.connections-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}
.stages-flow {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 32px;
}
.stage-card-block {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.015);
}
.stage-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.stage-block-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text, #173b42);
  font-weight: 850;
}
.stage-node-count {
  font-size: 12px;
  color: var(--color-text-secondary, #58747a);
  font-weight: 600;
}
.node-grid-flow {
  display: grid;
  gap: 24px;
  align-items: center;
}
.grid-column {
  display: grid;
  gap: 16px;
  align-content: center;
}
.node-flow-card {
  position: relative;
  display: flex;
  text-align: left;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.01);
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  padding: 0;
  overflow: hidden;
}

/* 状态边框定制 */
.node-flow-card.locked {
  opacity: 0.65;
  border-style: dashed;
}
.node-flow-card.available {
  border-color: var(--color-primary-border, #b9dedc);
}
.node-flow-card.in_progress,
.node-flow-card.remediation,
.node-flow-card.reinforced {
  border-color: #6366f1;
  box-shadow: 0 0 0 1px #6366f1, 0 8px 24px rgba(99, 102, 241, 0.08);
}
.node-flow-card.completed,
.node-flow-card.completed_with_gaps {
  border-color: #86efac;
  background: var(--color-success-soft, #e8f7f2);
}

.node-flow-card:hover:not(.locked) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
  border-color: var(--color-primary, #46b8b4);
}

/* 状态条 */
.status-strip {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #cbd5e1;
}
.available .status-strip { background: var(--color-primary, #46b8b4); }
.in_progress .status-strip,
.remediation .status-strip,
.reinforced .status-strip { background: #6366f1; }
.completed .status-strip,
.completed_with_gaps .status-strip { background: var(--color-success, #329a82); }

.node-card-body {
  flex: 1;
  padding: 14px 16px;
  min-width: 0;
}
.node-card-meta {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}
.priority-tag {
  font-family: monospace;
  font-size: 10px;
  font-weight: 800;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--color-text-secondary, #58747a);
}
.difficulty-tag {
  font-size: 10px;
  font-weight: 700;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--color-text-secondary, #58747a);
}
.node-card-body strong {
  display: block;
  font-size: 14px;
  color: var(--color-text, #173b42);
  line-height: 1.4;
  margin-bottom: 10px;
  font-weight: 800;
}
.node-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.status-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-secondary, #58747a);
}
.in_progress .status-label { color: #6366f1; }
.completed .status-label { color: var(--color-success, #329a82); }

.prereq-pill {
  font-size: 10px;
  font-weight: 700;
  background: rgba(203, 213, 225, 0.4);
  padding: 1px 6px;
  border-radius: 99px;
  color: var(--color-text-secondary, #58747a);
}

/* 动画连线 */
@keyframes stroke-flow {
  to {
    stroke-dashoffset: -20;
  }
}
.active-line {
  stroke-dasharray: 6, 4;
  animation: stroke-flow 1.2s linear infinite;
}
.locked-line {
  stroke-dasharray: 4, 4;
  opacity: 0.4;
}
</style>
