<template>
  <div class="tree-visualizer">
    <div class="chart-shell">
      <div
        v-if="activeNode"
        class="current-status"
      >
        <span class="status-marker"></span>
        当前节点 {{ activeNode.label }}
      </div>

      <div class="legend">
        <span class="legend-item"><i class="legend-dot default"></i>默认</span>
        <span class="legend-item"><i class="legend-dot visited"></i>已访问</span>
        <span class="legend-item"><i class="legend-dot active"></i>当前</span>
      </div>

      <div v-if="layoutNodes.length" ref="containerRef" class="tree-container" :class="{ 'with-sequence': traversalSequence.length > 0 }" @transitionend="handleTransitionEvent">
        <svg
          class="tree-links-svg"
          viewBox="0 0 1000 600"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <line
            v-for="(link, idx) in treeLinks"
            :key="idx"
            :x1="link.x1"
            :y1="link.y1"
            :x2="link.x2"
            :y2="link.y2"
            :class="['tree-link', link.tone || 'default', { visible: link.isVisible }]"
          />
        </svg>

        <div
          v-for="node in layoutNodes"
          :key="node.id"
          :class="['tree-node', node.isVisited ? 'visited' : (node.tone || 'default'), { active: node.isActive, visible: reachableNodes.has(String(node.id)) }]"
          :data-node-id="node.id"
          :style="{ left: `${node.leftPercent}%`, top: `${node.topPercent}%` }"
        >
          <span class="node-label">{{ node.label }}</span>
        </div>
      </div>
      <div v-else class="empty-state">等待树数据初始化...</div>

      <!-- 整体遍历序列展示 -->
      <div v-if="traversalSequence.length > 0" class="sequence-panel">
        <div class="sequence-title">遍历序列 (Result Sequence)</div>
        <div class="sequence-list">
          <transition-group name="list">
            <span
              v-for="(val, idx) in traversalSequence"
              :key="val + '-' + idx"
              class="sequence-item"
              :class="{ latest: idx === traversalSequence.length - 1 }"
            >
              {{ val }}
            </span>
          </transition-group>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { TraceEvent, VisualNode } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
  onStepComplete?: () => void
}>()

// 从 trace state 解析原始树节点
const rawNodes = computed(() => {
  const raw = props.currentEvent?.state?.structure?.nodes
  return Array.isArray(raw) ? raw as VisualNode[] : []
})

const activeNodeIds = computed(() => new Set(
  (props.currentEvent?.targets ?? []).map(target => String(target)),
))

const activeNode = computed(() => rawNodes.value.find(node => activeNodeIds.value.has(String(node.id))) ?? null)

// 计算当前通过已构建边可达的所有节点集合
const reachableNodes = computed(() => {
  const nodes = rawNodes.value
  const reachable = new Set<string>()
  if (nodes.length === 0) return reachable

  // 处于活动状态的 targets 节点始终可视，以对齐代码步骤
  activeNodeIds.value.forEach(id => reachable.add(String(id)))

  // 根节点（首个节点 node-0）始终是可达的起点
  const rootId = 'node-0'
  reachable.add(rootId)

  const queue = [rootId]
  const nodeMap = new Map<string, any>()
  nodes.forEach(n => nodeMap.set(String(n.id), n))

  while (queue.length > 0) {
    const currentId = queue.shift()!
    const node = nodeMap.get(currentId)
    if (!node) continue

    if (node.left && node.left_constructed !== false) {
      const leftId = String(node.left)
      if (!reachable.has(leftId)) {
        reachable.add(leftId)
        queue.push(leftId)
      }
    }
    if (node.right && node.right_constructed !== false) {
      const rightId = String(node.right)
      if (!reachable.has(rightId)) {
        reachable.add(rightId)
        queue.push(rightId)
      }
    }
  }
  return reachable
})

// 提取当前步骤之前（包含当前步骤）所有被访问过的高亮目标节点的序列
const traversalSequence = computed(() => {
  const sequence: string[] = []
  const seenNodeIds = new Set<string>()
  const maxStep = Math.min(props.currentStepIndex, props.events.length - 1)
  
  for (let i = 0; i <= maxStep; i++) {
    const event = props.events[i]
    if (!event) continue
    
    // 只在遍历阶段收集遍历序列
    const phase = event.state?.structure?.phase
    if (phase !== 'traversal') continue

    const targets = event.targets ?? []
    const nodes = event.state?.structure?.nodes ?? []
    
    targets.forEach(targetId => {
      const targetIdStr = String(targetId)
      if (!seenNodeIds.has(targetIdStr)) {
        const node = nodes.find((n: any) => String(n.id) === targetIdStr)
        if (node && node.label !== undefined) {
          seenNodeIds.add(targetIdStr)
          sequence.push(String(node.label))
        }
      }
    })
  }
  return sequence
})

// 构建树节点映射和父子连接关系
const treeData = computed(() => {
  const nodes = rawNodes.value
  const nodeMap = new Map<string, VisualNode>()
  nodes.forEach(n => nodeMap.set(String(n.id), { ...n }))

  const links: Array<{ from: string; to: string; tone?: string }> = []
  const hasParent = new Set<string>()

  // 优先用 left/right/children 字段构建父子连接
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
    if (Array.isArray(n.children)) {
      n.children.forEach((childId) => {
        const cId = String(childId)
        links.push({ from: idStr, to: cId, tone: n.tone === 'visited' && nodeMap.get(cId)?.tone === 'visited' ? 'visited' : 'default' })
        hasParent.add(cId)
      })
    }
  })

  // 降级方案：没有 left/right 时按二叉堆索引构建链接
  if (links.length === 0 && nodes.length > 1) {
    nodes.forEach((n, idx) => {
      const idStr = String(n.id)
      const leftIdx = 2 * idx + 1
      const rightIdx = 2 * idx + 2

      if (leftIdx < nodes.length) {
        const leftNode = nodes[leftIdx]!
        const leftId = String(leftNode.id)
        links.push({ from: idStr, to: leftId, tone: n.tone === 'visited' && leftNode.tone === 'visited' ? 'visited' : 'default' })
        hasParent.add(leftId)
      }
      if (rightIdx < nodes.length) {
        const rightNode = nodes[rightIdx]!
        const rightId = String(rightNode.id)
        links.push({ from: idStr, to: rightId, tone: n.tone === 'visited' && rightNode.tone === 'visited' ? 'visited' : 'default' })
        hasParent.add(rightId)
      }
    })
  }

  // 找到根节点（没有被其他节点作为子节点的节点）
  const roots = nodes.map(n => String(n.id)).filter(id => !hasParent.has(id))
  return { nodeMap, links, roots }
})

// 叶节点先均匀分布，父节点取子节点的水平中心，保持层级稳定且避免重叠。
const layoutNodes = computed(() => {
  const { nodeMap, links, roots } = treeData.value
  if (nodeMap.size === 0) return []

  // 构建邻接表用于 DFS 遍历
  const adj = new Map<string, string[]>()
  nodeMap.forEach((_, id) => adj.set(id, []))
  links.forEach(l => {
    const list = adj.get(l.from) || []
    list.push(l.to)
    adj.set(l.from, list)
  })

  const coords = new Map<string, { leaf: number; depth: number }>()
  const traversed = new Set<string>()
  let leafIndex = 0

  function traverse(nodeId: string, depth: number): number {
    if (traversed.has(nodeId)) return coords.get(nodeId)?.leaf ?? leafIndex
    traversed.add(nodeId)
    const children = (adj.get(nodeId) || []).filter(childId => nodeMap.has(childId))
    const childPositions = children.map(childId => traverse(childId, depth + 1))
    const leaf = childPositions.length > 0
      ? childPositions.reduce((sum, value) => sum + value, 0) / childPositions.length
      : leafIndex++
    coords.set(nodeId, { leaf, depth })
    return leaf
  }

  roots.forEach(r => traverse(r, 0))
  nodeMap.forEach((_, id) => {
    if (!traversed.has(id)) traverse(id, 0)
  })

  const maxDepth = Math.max(...Array.from(coords.values()).map(coord => coord.depth), 0)
  const leafCount = Math.max(leafIndex, 1)
  const verticalSpan = maxDepth === 0 ? 0 : Math.min(420, maxDepth * 142)
  const rowHeight = maxDepth === 0 ? 0 : verticalSpan / maxDepth
  const startY = (600 - verticalSpan) / 2

  return Array.from(nodeMap.values()).map(n => {
    const idStr = String(n.id)
    const coord = coords.get(idStr) || { leaf: 0, depth: 0 }
    const x = leafCount > 1 ? 80 + (coord.leaf / (leafCount - 1)) * 840 : 500
    const y = startY + coord.depth * rowHeight
    const isVisited = traversalSequence.value.includes(String(n.label))

    return {
      ...n,
      x,
      y,
      leftPercent: x / 10,
      topPercent: y / 6,
      isActive: activeNodeIds.value.has(idStr),
      isVisited,
    }
  })
})

// 计算树连接线的 SVG 坐标
const treeLinks = computed(() => {
  const { links, nodeMap } = treeData.value
  const nodes = layoutNodes.value
  const posMap = new Map<string, { x: number; y: number; isActive: boolean }>()
  nodes.forEach(n => posMap.set(String(n.id), { x: n.x, y: n.y, isActive: n.isActive }))

  return links.map(l => {
    const fromPos = posMap.get(l.from) || { x: 0, y: 0, isActive: false }
    const toPos = posMap.get(l.to) || { x: 0, y: 0, isActive: false }
    
    // 确定该子链接在当前步骤中是否已构建
    const parentNode = rawNodes.value.find(n => String(n.id) === l.from)
    const isLeft = parentNode?.left !== undefined && String(parentNode.left) === l.to
    const isConstructed = parentNode ? (isLeft ? (parentNode as any).left_constructed !== false : (parentNode as any).right_constructed !== false) : true
    
    let linkTone = 'default'
    if (isConstructed) {
      if (traversalSequence.value.length > 0) {
        const isFromVisited = traversalSequence.value.includes(String(nodeMap.get(l.from)?.label))
        const isToVisited = traversalSequence.value.includes(String(nodeMap.get(l.to)?.label))
        linkTone = isFromVisited && isToVisited ? 'visited' : 'default'
      } else {
        linkTone = 'visited'
      }
    } else {
      linkTone = 'unconstructed'
    }
    
    const isVisible = reachableNodes.value.has(l.from) && reachableNodes.value.has(l.to)

    return {
      x1: fromPos.x,
      y1: fromPos.y,
      x2: toPos.x,
      y2: toPos.y,
      tone: linkTone === 'visited' && (fromPos.isActive || toPos.isActive) ? 'active' : linkTone,
      isVisible,
    }
  })
})

// 动画完成通知：监听 CSS transitionend 事件，防抖后调用 onStepComplete
const containerRef = ref<HTMLElement | null>(null)
let transitionDebounceTimer: ReturnType<typeof setTimeout> | null = null
let hasActiveTransition = false

function onTransitionEnd() {
  if (transitionDebounceTimer !== null) {
    clearTimeout(transitionDebounceTimer)
  }
  transitionDebounceTimer = setTimeout(() => {
    hasActiveTransition = false
    props.onStepComplete?.()
  }, 60)
}

function handleTransitionEvent() {
  hasActiveTransition = true
  onTransitionEnd()
}

watch(
  [() => props.currentStepIndex, () => props.currentEvent],
  () => {
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    if (reducedMotion || !containerRef.value) {
      requestAnimationFrame(() => {
        if (!hasActiveTransition) {
          props.onStepComplete?.()
        }
      })
      return
    }
    if (transitionDebounceTimer !== null) {
      clearTimeout(transitionDebounceTimer)
    }
    transitionDebounceTimer = setTimeout(() => {
      hasActiveTransition = false
      props.onStepComplete?.()
    }, 350)
  },
)

onBeforeUnmount(() => {
  if (transitionDebounceTimer !== null) {
    clearTimeout(transitionDebounceTimer)
  }
})
</script>

<style scoped>
.tree-visualizer {
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
  background: var(--color-surface);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-dot.default {
  background: var(--color-surface);
  border: 1px solid var(--color-border-hover);
}

.legend-dot.visited {
  background: var(--color-success-soft);
  border: 1px solid var(--color-success);
}

.legend-dot.active {
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
}

.current-status {
  position: absolute;
  top: 12px;
  left: 14px;
  z-index: 2;
  min-height: 29px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 9px;
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-strong);
  font-size: 12px;
  font-weight: 700;
}

.status-marker {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
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
  stroke: var(--color-border-hover);
  stroke-width: 1.75;
  vector-effect: non-scaling-stroke;
  opacity: 0;
  pointer-events: none;
  transition: stroke 0.25s ease, opacity 0.3s ease;
}

.tree-link.visible {
  opacity: 1;
  pointer-events: auto;
}

.tree-link.visible.unconstructed {
  opacity: 0.35;
}

.tree-link.visited {
  stroke: var(--color-success);
  stroke-width: 2.5;
}

.tree-link.active {
  stroke: var(--color-primary);
  stroke-width: 3;
}

.tree-node {
  position: absolute;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1.5px solid var(--color-border-hover);
  font-weight: 750;
  font-size: 13px;
  color: var(--color-text-strong);
  transform: translate(-50%, -50%);
  opacity: 0;
  pointer-events: none;
  transition:
    border-color 0.2s ease,
    background-color 0.2s ease,
    color 0.2s ease,
    opacity 0.3s ease;
  z-index: 1;
}

.tree-node.visible {
  opacity: 1;
  pointer-events: auto;
}

.tree-node.visited {
  border-color: var(--color-success);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.tree-node.active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-surface);
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--color-primary) 16%, transparent);
}

.node-label {
  max-width: 34px;
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  height: 100%;
  min-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-faint);
}

@media (prefers-reduced-motion: reduce) {
  .tree-link,
  .tree-node {
    transition: none;
  }
}

.tree-container {
  transition: height 0.25s ease;
}

.tree-container.with-sequence {
  height: calc(100% - 62px);
}

.sequence-panel {
  position: absolute;
  bottom: 12px;
  left: 12px;
  right: 12px;
  z-index: 10;
  padding: 8px 12px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.sequence-title {
  font-size: 10px;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.sequence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.sequence-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 4px;
  border-radius: var(--radius-xs);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border-light);
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-secondary);
  transition: all 0.2s ease;
}

.sequence-item.latest {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
  color: var(--color-primary-text);
  transform: scale(1.05);
}

/* 序列元素滑入动画 */
.list-enter-active,
.list-leave-active {
  transition: all 0.25s ease;
}
.list-enter-from {
  opacity: 0;
  transform: translateY(6px) scale(0.9);
}
.list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
.tree-link.unconstructed {
  stroke: var(--color-border);
  stroke-width: 1;
  stroke-dasharray: 3 3;
  opacity: 0;
}
</style>
