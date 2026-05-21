<template>
  <section class="kg-view" :class="{ compact }">
    <header v-if="!compact" class="kg-header">
      <div class="kg-title-block">
        <div class="kg-kicker">知识图谱</div>
        <h3>{{ graph.topic || '知识图谱' }}</h3>
        <p v-if="graph.summary">{{ graph.summary }}</p>
      </div>
      <div class="kg-stats" aria-label="知识图谱统计">
        <span>{{ graph.nodes.length }} 节点</span>
        <span>{{ graph.edges.length }} 关系</span>
        <span>{{ layoutText }}</span>
        <span v-if="neo4jText">{{ neo4jText }}</span>
      </div>
    </header>

    <div v-if="graph.nodes.length" class="kg-body">
      <aside v-if="!compact" class="kg-side">
        <section v-if="graph.focus_areas.length" class="kg-side-section">
          <h4>重点区域</h4>
          <div class="kg-tags">
            <span v-for="area in graph.focus_areas" :key="area">{{ area }}</span>
          </div>
        </section>

        <section class="kg-side-section">
          <h4>关系路径</h4>
          <ol v-if="relationRows.length" class="kg-relations">
            <li v-for="item in relationRows" :key="item.key">
              <b>{{ item.source }}</b>
              <span>{{ item.label }}</span>
              <b>{{ item.target }}</b>
            </li>
          </ol>
          <p v-else class="kg-muted">当前图谱以孤立知识点为主。</p>
        </section>
      </aside>

      <div class="kg-canvas">
        <VChart class="kg-chart" :option="chartOption" autoresize />
      </div>
    </div>
    <div v-else class="kg-empty">暂无可渲染的知识图谱</div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import { LegendComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, GraphChart, TooltipComponent, LegendComponent])

type LayoutMode = 'force' | 'radial' | 'hierarchy'

type GraphNode = {
  id: string
  label?: string
  name?: string
  description?: string
  category?: string
  difficulty?: string
  importance?: string
  is_weak?: boolean
  level?: number
}

type GraphEdge = {
  source: string
  target: string
  relation_type?: string
  label?: string
}

type GraphPayload = {
  topic: string
  summary: string
  layout_mode?: LayoutMode
  layout?: { mode?: LayoutMode; rank_direction?: string }
  focus_areas: string[]
  nodes: GraphNode[]
  edges: GraphEdge[]
  neo4j?: { stored?: boolean; graph_id?: string; reason?: string; error?: string }
}

const props = defineProps<{
  resultData?: any
  compact?: boolean
}>()

const unwrapPayload = (input: any): any => {
  if (!input) return {}
  if (typeof input === 'string') {
    try {
      return JSON.parse(input)
    } catch {
      return {}
    }
  }
  if (input.content != null) return unwrapPayload(input.content)
  return input
}

const graph = computed<GraphPayload>(() => {
  const raw = unwrapPayload(props.resultData)
  const nodes = Array.isArray(raw.nodes) ? raw.nodes : []
  const edges = Array.isArray(raw.edges) ? raw.edges : []
  const layoutMode = raw.layout?.mode || raw.layout_mode || 'force'
  return {
    topic: String(raw.topic || raw.title || props.resultData?.title || '知识图谱'),
    summary: String(raw.summary || props.resultData?.summary || ''),
    layout_mode: normalizeLayoutMode(layoutMode),
    layout: raw.layout || { mode: normalizeLayoutMode(layoutMode), rank_direction: 'TB' },
    focus_areas: Array.isArray(raw.focus_areas) ? raw.focus_areas.map(String) : [],
    nodes,
    edges,
    neo4j: raw.neo4j || props.resultData?.metadata?.neo4j || {},
  }
})

const normalizeLayoutMode = (value: unknown): LayoutMode => {
  if (value === 'radial' || value === 'hierarchy') return value
  return 'force'
}

const nodeLabel = (node: GraphNode | undefined) => node?.label || node?.name || node?.id || ''

const categories = [
  { name: '核心', itemStyle: { color: '#2563eb' } },
  { name: '重要', itemStyle: { color: '#059669' } },
  { name: '补充', itemStyle: { color: '#64748b' } },
  { name: '薄弱', itemStyle: { color: '#d97706' } },
]

const categoryName = (node: GraphNode) => {
  if (node.is_weak || node.category === 'weak') return '薄弱'
  if (node.category === 'core' || node.importance === 'core') return '核心'
  if (node.category === 'supplementary' || node.importance === 'supplementary') return '补充'
  return '重要'
}

const relationLabel = (edge: GraphEdge) => {
  const map: Record<string, string> = {
    prerequisite: '前置',
    extends: '扩展',
    includes: '包含',
    related: '相关',
  }
  return edge.label || map[String(edge.relation_type || 'related')] || '相关'
}

const nodeById = computed(() => {
  const map = new Map<string, GraphNode>()
  graph.value.nodes.forEach((node) => map.set(node.id, node))
  return map
})

const relationRows = computed(() =>
  graph.value.edges.slice(0, 8).map((edge, index) => ({
    key: `${edge.source}-${edge.target}-${index}`,
    source: nodeLabel(nodeById.value.get(edge.source)) || edge.source,
    target: nodeLabel(nodeById.value.get(edge.target)) || edge.target,
    label: relationLabel(edge),
  })),
)

const layoutText = computed(() => {
  const mode = graph.value.layout?.mode || graph.value.layout_mode
  if (mode === 'hierarchy') return '层级布局'
  if (mode === 'radial') return '环形布局'
  return '力导向布局'
})

const levelGroups = computed(() => {
  const groups = new Map<number, GraphNode[]>()
  graph.value.nodes.forEach((node) => {
    const level = Math.max(0, Number(node.level ?? 0))
    const group = groups.get(level) || []
    group.push(node)
    groups.set(level, group)
  })
  return groups
})

const hierarchyPosition = (node: GraphNode, index: number) => {
  const level = Math.max(0, Number(node.level ?? 0))
  const group = levelGroups.value.get(level) || [node]
  const offset = group.findIndex((item) => item.id === node.id)
  const column = offset >= 0 ? offset : index
  const spread = 180
  return {
    x: (column - (group.length - 1) / 2) * spread,
    y: level * 150,
  }
}

const chartNodes = computed(() =>
  graph.value.nodes.map((node, index) => {
    const isCore = node.category === 'core' || node.importance === 'core'
    const isWeak = node.category === 'weak' || node.is_weak
    const isSupplementary = node.category === 'supplementary' || node.importance === 'supplementary'
    const position = hierarchyPosition(node, index)
    
    let color = '#10b981'
    let borderColor = '#059669'
    let shadowColor = 'rgba(16, 185, 129, 0.2)'
    if (isCore) {
      color = '#6366f1'
      borderColor = '#4f46e5'
      shadowColor = 'rgba(99, 102, 241, 0.3)'
    } else if (isWeak) {
      color = '#ef4444'
      borderColor = '#dc2626'
      shadowColor = 'rgba(239, 68, 68, 0.3)'
    } else if (isSupplementary) {
      color = '#64748b'
      borderColor = '#475569'
      shadowColor = 'rgba(100, 116, 139, 0.15)'
    }

    return {
      id: node.id,
      name: nodeLabel(node),
      value: node.description || '',
      category: categoryName(node),
      symbolSize: props.compact ? (isCore ? 44 : 34) : (isCore ? 70 : 52),
      draggable: true,
      x: position.x,
      y: position.y,
      itemStyle: {
        color: color,
        borderColor: borderColor,
        borderWidth: 2,
        shadowBlur: 24,
        shadowColor: shadowColor,
        shadowOffsetX: 0,
        shadowOffsetY: 8
      },
      label: {
        show: true,
        width: props.compact ? 74 : 118,
        overflow: 'break',
        lineHeight: props.compact ? 15 : 17,
        fontSize: props.compact ? 10 : 12,
        fontWeight: isCore ? 700 : 600,
        color: '#1e293b',
      },
    }
  }),
)

const chartOption = computed(() => {
  const mode = graph.value.layout?.mode || graph.value.layout_mode
  const hierarchy = mode === 'hierarchy'

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      confine: true,
      borderWidth: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter(params: any) {
        if (params.dataType === 'edge') {
          return `<div style="padding: 4px 8px; font-family: sans-serif;">
            <span style="color: #94a3b8; font-size: 11px;">关系类型</span>
            <div style="font-weight: 600; color: #fff; font-size: 13px; margin-top: 2px;">
              ${params.data?.name || '相关'}
            </div>
          </div>`
        }
        
        const category = params.data?.category || ''
        let tagColor = '#10b981'
        if (category === '核心') tagColor = '#6366f1'
        else if (category === '薄弱') tagColor = '#ef4444'
        else if (category === '补充') tagColor = '#64748b'
        
        const desc = params.data?.value 
          ? `<div style="color: #cbd5e1; font-size: 12px; margin-top: 6px; line-height: 1.5; white-space: normal; max-width: 220px;">${params.data.value}</div>` 
          : ''
          
        return `<div style="padding: 8px 12px; font-family: sans-serif; min-width: 140px;">
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
            <span style="font-weight: 700; color: #fff; font-size: 14px;">${params.name}</span>
            <span style="background-color: ${tagColor}; color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">${category}</span>
          </div>
          ${desc}
        </div>`
      },
    },
    legend: props.compact
      ? undefined
      : {
          bottom: 10,
          left: 20,
          itemWidth: 10,
          itemHeight: 10,
          textStyle: { color: '#475569', fontSize: 12 },
        },
    series: [
      {
        type: 'graph',
        layout: hierarchy ? 'none' : mode === 'radial' ? 'circular' : 'force',
        roam: true,
        categories,
        data: chartNodes.value,
        links: graph.value.edges.map((edge) => {
          const type = edge.relation_type || 'related'
          let color = '#94a3b8'
          let width = 1.5
          let typeStyle = 'solid'
          
          if (type === 'prerequisite') {
            color = '#4f46e5'
            width = 2
          } else if (type === 'extends') {
            color = '#0ea5e9'
            width = 1.8
          } else if (type === 'includes') {
            color = '#10b981'
            width = 1.8
          } else if (type === 'related') {
            color = '#94a3b8'
            width = 1.2
            typeStyle = 'dashed'
          }
          
          return {
            source: edge.source,
            target: edge.target,
            name: relationLabel(edge),
            lineStyle: { 
              curveness: hierarchy ? 0 : 0.14,
              color: color,
              width: width,
              type: typeStyle
            },
          }
        }),
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 9,
        circular: {
          rotateLabel: false,
        },
        force: {
          repulsion: props.compact ? 240 : 620,
          gravity: 0.07,
          edgeLength: props.compact ? 92 : 150,
          layoutAnimation: true,
          friction: 0.15,
        },
        lineStyle: {
          color: '#94a3b8',
          width: 1.4,
          opacity: 0.78,
        },
        edgeLabel: {
          show: !props.compact,
          color: '#475569',
          fontSize: 10,
          backgroundColor: 'rgba(255,255,255,0.85)',
          padding: [2, 6],
          borderRadius: 4,
          formatter: (params: any) => params.data?.name || '',
        },
        emphasis: {
          focus: 'adjacency',
          scale: true,
          lineStyle: { width: 3, color: '#2563eb' },
        },
      },
    ],
  }
})

const neo4jText = computed(() => {
  const meta = graph.value.neo4j
  if (!meta) return ''
  if (meta.stored) return 'Neo4j 已存储'
  if (meta.reason || meta.error) return 'JSON 渲染'
  return ''
})
</script>

<style scoped>
.kg-view {
  min-height: 440px;
  border: 1px solid #dbe4f0;
  border-radius: 8px;
  background: #f8fafc;
  overflow: hidden;
}

.kg-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 22px 14px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
}

.kg-title-block {
  min-width: 0;
}

.kg-kicker {
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.kg-header h3 {
  margin: 4px 0 6px;
  color: #172033;
  font-size: 20px;
  letter-spacing: 0;
}

.kg-header p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.kg-stats {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  justify-content: flex-end;
  gap: 8px;
  min-width: 210px;
}

.kg-stats span,
.kg-tags span {
  border: 1px solid #dbe4f0;
  border-radius: 999px;
  padding: 5px 10px;
  color: #334155;
  background: #f8fafc;
  font-size: 12px;
  font-weight: 700;
}

.kg-body {
  display: grid;
  grid-template-columns: minmax(210px, 280px) minmax(0, 1fr);
  min-height: 520px;
}

.kg-side {
  border-right: 1px solid #e2e8f0;
  padding: 18px;
  background: #fff;
}

.kg-side-section + .kg-side-section {
  margin-top: 22px;
}

.kg-side h4 {
  margin: 0 0 10px;
  color: #172033;
  font-size: 13px;
  letter-spacing: 0;
}

.kg-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kg-relations {
  display: grid;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.kg-relations li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 34px;
  color: #475569;
  font-size: 12px;
}

.kg-relations b {
  min-width: 0;
  color: #0f172a;
  overflow-wrap: anywhere;
}

.kg-relations span {
  border-radius: 999px;
  padding: 3px 7px;
  color: #0369a1;
  background: #e0f2fe;
  font-size: 11px;
  font-weight: 800;
}

.kg-muted {
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
}

.kg-canvas {
  min-width: 0;
  height: 520px;
  padding: 6px 10px 14px;
  background-image: radial-gradient(circle, #cbd5e1 1px, transparent 1.5px);
  background-size: 24px 24px;
  background-color: #f8fafc;
}

.kg-chart {
  width: 100%;
  height: 100%;
}

.kg-empty {
  display: grid;
  min-height: 280px;
  place-items: center;
  color: #64748b;
}

.compact {
  min-height: 260px;
}

.compact .kg-body {
  display: block;
  min-height: 260px;
}

.compact .kg-canvas {
  height: 260px;
  padding: 0;
  background-size: 24px 24px;
}

@media (max-width: 768px) {
  .kg-header {
    flex-direction: column;
  }

  .kg-stats {
    justify-content: flex-start;
    min-width: 0;
  }

  .kg-body {
    grid-template-columns: 1fr;
  }

  .kg-side {
    border-right: 0;
    border-bottom: 1px solid #e2e8f0;
  }

  .kg-canvas {
    height: 450px;
  }
}
</style>
