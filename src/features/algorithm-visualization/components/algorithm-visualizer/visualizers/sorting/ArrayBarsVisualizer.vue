<template>
  <div class="array-bars-visualizer">
    <div class="chart-shell">
      <div
        class="operation-indicator"
        :data-operation="currentOperation"
      >
        <i class="operation-dot"></i>
        <span>{{ operationText }}</span>
      </div>

      <div class="legend">
        <span class="legend-item"><i class="legend-dot focus"></i>当前关注</span>
        <span class="legend-item"><i class="legend-dot changed"></i>数据变化</span>
        <span class="legend-item"><i class="legend-dot complete"></i>执行完成</span>
      </div>

      <svg ref="svgRef" class="chart-svg" viewBox="0 0 860 420" preserveAspectRatio="xMidYMid meet" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import gsap from 'gsap'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

interface Props {
  currentEvent: TraceEvent | null
  currentStepIndex: number
  events: TraceEvent[]
}

interface BarDatum {
  id: string
  index: number
  value: number
  tone: string
}

interface BarTransition {
  element: SVGRectElement
  fromY: number
  fromHeight: number
  toY: number
  toHeight: number
}

interface GroupTransition {
  element: SVGGElement
  fromX: number
  toX: number
}

interface ChartTransitions {
  bars: BarTransition[]
  groups: GroupTransition[]
}

const props = defineProps<Props>()

// SVG 容器引用、当前步骤的数组数据（降级到初始事件）
const svgRef = ref<SVGSVGElement | null>(null)

const currentOperation = computed(() => {
  if (props.currentEvent?.type === 'compare') return 'compare'
  if (props.currentEvent?.type === 'swap') return 'swap'
  if (props.currentEvent?.type === 'write') return 'write'
  if (props.currentEvent?.type === 'finish') return 'finish'
  return 'observe'
})

const operationText = computed(() => {
  const targets = getIndices(props.currentEvent)
  if (currentOperation.value === 'compare' && targets.length >= 2) {
    return `比较位置 ${targets[0]} 与 ${targets[1]}`
  }
  if (currentOperation.value === 'swap' && targets.length >= 2) {
    return `交换位置 ${targets[0]} 与 ${targets[1]}`
  }
  if (currentOperation.value === 'write') return '移动并写入元素'
  if (currentOperation.value === 'finish') return '排序完成'
  return '观察数组状态'
})

const activeArray = computed(() => {
  const arr = props.currentEvent?.state?.structure?.array
  if (Array.isArray(arr)) {
    return arr.map(Number).filter((item: number) => Number.isFinite(item))
  }
  const initArr = props.events[0]?.state?.structure?.array
  if (Array.isArray(initArr)) {
    return initArr.map(Number).filter((item: number) => Number.isFinite(item))
  }
  return []
})

const previousArray = computed(() => {
  if (props.currentStepIndex <= 0) return []
  const arr = props.events[props.currentStepIndex - 1]?.state?.structure?.array
  if (!Array.isArray(arr)) return []
  return arr.map(Number).filter((item: number) => Number.isFinite(item))
})

// 从事件 targets 中提取索引数组
function getIndices(event: TraceEvent | null): number[] {
  const raw = event?.targets
  if (!Array.isArray(raw)) return []
  return raw.map(Number).filter((item: number) => Number.isInteger(item))
}

function getChangedIndices(): number[] {
  if (previousArray.value.length !== activeArray.value.length) return []
  return activeArray.value.reduce<number[]>((changed, value, index) => {
    if (value !== previousArray.value[index]) changed.push(index)
    return changed
  }, [])
}

function getFocusedIndices(): number[] {
  const targets = getIndices(props.currentEvent)
  const validTargets = targets.filter(index => index >= 0 && index < activeArray.value.length)
  return validTargets.length > 0 ? validTargets : getChangedIndices()
}

function getSwapPair(): [number, number] | null {
  if (props.currentEvent?.type !== 'swap') return null
  const targets = getIndices(props.currentEvent)
    .filter(index => index >= 0 && index < activeArray.value.length)
  if (targets.length !== 2 || previousArray.value.length !== activeArray.value.length) return null
  const left = targets[0]!
  const right = targets[1]!
  if (
    previousArray.value[left] !== activeArray.value[right]
    || previousArray.value[right] !== activeArray.value[left]
  ) return null
  return [left, right]
}

// 状态帧是后端追踪协议的核心：用帧差分和 targets 表达关注位置与数据变化。
function getTone(index: number): string {
  if (props.currentEvent?.type === 'finish') return 'complete'
  if (getChangedIndices().includes(index)) return 'changed'
  if (getFocusedIndices().includes(index)) return 'focus'
  return 'default'
}

// 构建 D3 数据数组（包含值、索引、颜色主题）
function buildData(): BarDatum[] {
  return activeArray.value.map((value: number, index: number) => ({
    id: `bar-${index}`, index, value, tone: getTone(index),
  }))
}

// 用 D3 渲染柱状图，并保留变更前的几何信息以实现状态帧间的连续过渡。
function renderChart(): ChartTransitions {
  if (!svgRef.value) return { bars: [], groups: [] }
  const svg = d3.select(svgRef.value)
  const width = 860; const height = 420
  const margin = { top: 28, right: 32, bottom: 56, left: 32 }
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom
  const maxValue = Math.max(...activeArray.value, 1)
  const data = buildData()
  const previousGeometry = new Map<string, { y: number; height: number }>()
  svgRef.value.querySelectorAll<SVGGElement>('g.bar-group').forEach((group) => {
    const id = group.getAttribute('data-bar-id')
    const rect = group.querySelector<SVGRectElement>('rect.bar-rect')
    if (!id || !rect) return
    previousGeometry.set(id, {
      y: Number(rect.getAttribute('y')),
      height: Number(rect.getAttribute('height')),
    })
  })
  const transitions: ChartTransitions = { bars: [], groups: [] }
  const swapPair = getSwapPair()

  const root = svg.selectAll('g.chart-root').data([null]).join('g')
    .attr('class', 'chart-root').attr('transform', `translate(${margin.left},${margin.top})`)

  const xScale = d3.scaleBand().domain(data.map((d: BarDatum) => d.index)).range([0, innerWidth]).padding(0.18)
  const yScale = d3.scaleLinear().domain([0, maxValue]).range([innerHeight, 0])

  root.selectAll('line.baseline').data([null]).join('line').attr('class', 'baseline')
    .attr('x1', 0).attr('x2', innerWidth).attr('y1', innerHeight).attr('y2', innerHeight)
    .attr('stroke', '#dbe3ef').attr('stroke-width', 1.5)

  const groups = root.selectAll('g.bar-group').data(data, (d: BarDatum) => d.id)
    .join((enter: any) => {
      const g = enter.append('g').attr('class', 'bar-group')
      g.append('rect').attr('class', 'bar-rect')
      g.append('text').attr('class', 'bar-value')
      return g
    })
    .attr('data-bar-id', (d: BarDatum) => d.id).attr('data-tone', (d: BarDatum) => d.tone)

  const indexLayer = root.selectAll('g.index-layer').data([null]).join('g').attr('class', 'index-layer')
  indexLayer.selectAll('text.bar-index').data(data, (d: BarDatum) => d.id).join('text')
    .attr('class', 'bar-index')
    .attr('x', (d: BarDatum) => (xScale(d.index) ?? 0) + xScale.bandwidth() / 2)
    .attr('y', innerHeight + 20)
    .attr('text-anchor', 'middle')
    .text((d: BarDatum) => d.index)

  groups.each(function (this: SVGGElement, d: BarDatum) {
    const g = d3.select(this)
    const x = xScale(d.index) ?? 0; const y = yScale(d.value)
    const bw = xScale.bandwidth(); const bh = innerHeight - y
    const sourceIndex = swapPair?.[0] === d.index
      ? swapPair[1]
      : swapPair?.[1] === d.index
        ? swapPair[0]
        : null
    const sourceX = sourceIndex === null ? x : (xScale(sourceIndex) ?? x)
    const swapDirection = sourceIndex === null
      ? null
      : sourceIndex < d.index
        ? 'right'
        : 'left'
    g.attr('transform', `translate(${sourceX}, 0)`)
      .attr('data-swap-from', sourceIndex === null ? null : sourceIndex)
      .attr('data-swap-direction', swapDirection)
    if (sourceIndex !== null) {
      transitions.groups.push({ element: this, fromX: sourceX, toX: x })
    }
    const rect = this.querySelector<SVGRectElement>('rect.bar-rect')
    if (!rect) return
    const nextHeight = Math.max(bh, 20)
    const previous = previousGeometry.get(sourceIndex === null ? d.id : `bar-${sourceIndex}`)
    rect.setAttribute('x', '0')
    rect.setAttribute('y', String(y))
    rect.setAttribute('rx', '3')
    rect.setAttribute('ry', '3')
    rect.setAttribute('width', String(bw))
    rect.setAttribute('height', String(nextHeight))
    if (previous && (previous.y !== y || previous.height !== nextHeight)) {
      rect.setAttribute('y', String(previous.y))
      rect.setAttribute('height', String(previous.height))
      transitions.bars.push({
        element: rect,
        fromY: previous.y,
        fromHeight: previous.height,
        toY: y,
        toHeight: nextHeight,
      })
    }
    g.select('text.bar-value').attr('x', bw / 2).attr('y', Math.max(y - 8, 12)).attr('text-anchor', 'middle').text(d.value)
  })

  return transitions
}

// 所有状态帧都会触发动画：变化的柱子过渡，targets 或变化位置脉冲提示。
function animateStep(transitions: ChartTransitions) {
  if (!svgRef.value || !props.currentEvent) return
  const svg = svgRef.value
  const rects = Array.from(svg.querySelectorAll<SVGRectElement>('rect.bar-rect'))
  const groups = Array.from(svg.querySelectorAll<SVGGElement>('g.bar-group'))
  const targets = getFocusedIndices()
    .map((i: number) => svg.querySelector<SVGRectElement>(`g[data-bar-id="bar-${i}"] rect.bar-rect`))
    .filter((e: SVGRectElement | null): e is SVGRectElement => Boolean(e))

  gsap.killTweensOf(rects)
  gsap.killTweensOf(groups)
  gsap.set(rects, { clearProps: 'transform' })

  if (transitions.groups.length > 0) {
    const root = svg.querySelector<SVGGElement>('g.chart-root')
    transitions.groups
      .slice()
      .sort((left, right) => {
        const leftHeight = Number(left.element.querySelector('rect')?.getAttribute('height') ?? 0)
        const rightHeight = Number(right.element.querySelector('rect')?.getAttribute('height') ?? 0)
        return rightHeight - leftHeight
      })
      .forEach(({ element }) => root?.append(element))
    const indexLayer = root?.querySelector<SVGGElement>('g.index-layer')
    if (root && indexLayer) root.append(indexLayer)
  }

  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  transitions.bars.forEach(({ element, fromY, fromHeight, toY, toHeight }) => {
    gsap.fromTo(
      element,
      { attr: { y: fromY, height: fromHeight } },
      { attr: { y: toY, height: toHeight }, duration: reducedMotion ? 0 : 0.42, ease: 'power2.inOut' },
    )
  })

  transitions.groups.forEach(({ element, fromX, toX }) => {
    gsap.fromTo(
      element,
      { attr: { transform: `translate(${fromX}, 0)` } },
      { attr: { transform: `translate(${toX}, 0)` }, duration: reducedMotion ? 0 : 0.58, ease: 'power3.inOut' },
    )
  })

  if (props.currentStepIndex === 0) {
    gsap.fromTo(rects, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out', stagger: 0.04 })
    return
  }

  if (targets.length > 0) {
    gsap.fromTo(
      targets,
      { y: 0, scaleY: 1 },
      { y: -7, scaleY: 1.025, duration: reducedMotion ? 0 : 0.2, yoyo: !reducedMotion, repeat: reducedMotion ? 0 : 1, ease: 'power2.out', transformOrigin: 'center bottom' },
    )
  }
}

async function renderAndAnimate() {
  await nextTick()
  animateStep(renderChart())
}

// 步骤索引变化时重新渲染并运行动画，即使数组值不变也会展示当前关注位置。
watch(
  [() => props.currentStepIndex, () => props.currentEvent],
  renderAndAnimate,
)
onMounted(renderAndAnimate)
// 销毁前清理 GSAP 动画
onBeforeUnmount(() => { if (svgRef.value) gsap.killTweensOf(svgRef.value.querySelectorAll<SVGGElement>('g.bar-group')) })
</script>

<style scoped>
.array-bars-visualizer {
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

.operation-indicator {
  position: absolute;
  top: 12px;
  left: 14px;
  z-index: 1;
  min-height: 29px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 9px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-surface) 90%, transparent);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.operation-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-faint);
}

.operation-indicator[data-operation='compare'] .operation-dot {
  background: var(--color-primary);
}

.operation-indicator[data-operation='swap'] .operation-dot,
.operation-indicator[data-operation='write'] .operation-dot {
  background: var(--color-warning);
}

.operation-indicator[data-operation='finish'] .operation-dot {
  background: var(--color-success);
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

.legend-dot.focus {
  background: var(--color-primary);
}

.legend-dot.changed {
  background: var(--color-warning);
}

.legend-dot.complete {
  background: var(--color-success);
}

.chart-shell {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: 18px 12px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-svg {
  width: 100%;
  height: 100%;
  min-height: 240px;
}

:deep(.bar-rect) {
  fill: var(--color-border-hover);
  transition: fill 0.15s ease, opacity 0.15s ease;
}

:deep(.bar-value) {
  fill: var(--color-text-strong);
  font-size: 14px;
  font-weight: 600;
}

:deep(.bar-index) {
  fill: var(--color-text-muted);
  font-size: 11px;
  font-weight: 500;
}

:deep(.bar-group[data-tone='focus'] .bar-rect) {
  fill: var(--color-primary);
}

:deep(.bar-group[data-tone='changed'] .bar-rect) {
  fill: var(--color-warning);
}

:deep(.bar-group[data-tone='changed'][data-swap-direction='right'] .bar-rect) {
  fill: var(--color-primary);
}

:deep(.bar-group[data-tone='complete'] .bar-rect) {
  fill: var(--color-success);
}
</style>
