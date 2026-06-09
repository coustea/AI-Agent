<template>
  <div class="skill-tree-container">
    <v-chart class="chart" :option="chartOption" @click="handleNodeClick" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PropType } from 'vue'
import { use } from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { LearningPathNode, LearningPathStage } from '@/features/learning/model/path'

use([GraphChart, TooltipComponent, TitleComponent, CanvasRenderer])

const props = defineProps({
  stages: {
    type: Array as PropType<LearningPathStage[]>,
    required: true,
  },
  nodes: {
    type: Array as PropType<LearningPathNode[]>,
    required: true,
  },
})

const emit = defineEmits<{
  (e: 'node-click', node: LearningPathNode): void
}>()

const chartOption = computed(() => {
  const chartNodes: any[] = []
  const chartLinks: any[] = []
  
  // Group nodes by stage to calculate positions
  const nodesByStage = new Map<string, LearningPathNode[]>()
  for (const n of props.nodes) {
    if (!nodesByStage.has(n.stage_id)) nodesByStage.set(n.stage_id, [])
    nodesByStage.get(n.stage_id)!.push(n)
  }

  const stageIds = props.stages.map(s => s.stage_id)
  
  // Categories for legend / colors
  const categories = [
    { name: 'available', itemStyle: { color: '#6366f1' } }, // Indigo
    { name: 'completed', itemStyle: { color: '#10b981' } }, // Emerald
    { name: 'locked', itemStyle: { color: '#94a3b8' } },    // Slate
    { name: 'completed_with_gaps', itemStyle: { color: '#f59e0b' } }, // Amber
  ]

  // Build nodes
  for (const node of props.nodes) {
    const stageIndex = stageIds.indexOf(node.stage_id)
    const stageNodes = nodesByStage.get(node.stage_id) || []
    // Sort by priority to ensure consistent y positioning
    stageNodes.sort((a, b) => a.priority - b.priority)
    const nodeIndex = stageNodes.findIndex(n => n.node_id === node.node_id)
    const totalInStage = stageNodes.length
    
    // Calculate deterministic X, Y for layout: 'none'
    // X is based on stage progress (left to right)
    const x = stageIndex * 300
    // Y is centered vertically within the stage
    const y = (nodeIndex - (totalInStage - 1) / 2) * 100

    // Parse status to category
    let categoryIdx = 2 // locked
    if (node.status === 'available') categoryIdx = 0
    else if (node.status === 'completed') categoryIdx = 1
    else if (node.status === 'completed_with_gaps') categoryIdx = 3

    chartNodes.push({
      id: node.node_id,
      name: node.title,
      value: node.mastery_target,
      x,
      y,
      symbolSize: 40,
      category: categoryIdx,
      label: {
        show: true,
        position: 'bottom',
        formatter: '{b}',
        color: 'inherit',
        fontSize: 12,
        fontWeight: 'bold',
      },
      // Keep raw node data for click handler
      rawNode: node
    })

    // Build links from prerequisites
    if (node.prerequisites && node.prerequisites.length > 0) {
      for (const prereq of node.prerequisites) {
        // Line drawn from prerequisite -> this node
        chartLinks.push({
          source: prereq,
          target: node.node_id,
          lineStyle: {
            width: 2,
            curveness: 0.2,
            opacity: 0.6
          }
        })
      }
    } else if (stageIndex > 0) {
      // If no explicit prereqs, loosely link to the previous stage's nodes
      const prevStageId = stageIds[stageIndex - 1] as string
      const prevNodes = nodesByStage.get(prevStageId) || []
      if (prevNodes.length > 0 && prevNodes[0]) {
        // Link to the first node of previous stage just to keep graph connected
        chartLinks.push({
          source: prevNodes[0].node_id,
          target: node.node_id,
          lineStyle: { type: 'dashed', width: 1, curveness: 0.2, opacity: 0.3 }
        })
      }
    }
  }

  return {
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const n = params.data.rawNode as LearningPathNode
          return `<strong>${n.title}</strong><br/>
                  状态: ${n.status}<br/>
                  难度: ${n.difficulty || '未知'}<br/>
                  ${n.estimated_minutes ? `耗时: ${n.estimated_minutes}分钟<br/>` : ''}
                  <em>${n.mastery_target || n.recommendation_reason || ''}</em>`
        }
        return ''
      }
    },
    categories,
    series: [
      {
        type: 'graph',
        layout: 'none',
        data: chartNodes,
        links: chartLinks,
        roam: true, // Allow zoom and pan
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 8],
        labelLayout: {
          hideOverlap: true
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2,
          shadowBlur: 10,
          shadowColor: 'rgba(0,0,0,0.1)'
        }
      }
    ]
  }
})

const handleNodeClick = (params: any) => {
  if (params.dataType === 'node' && params.data.rawNode) {
    emit('node-click', params.data.rawNode as LearningPathNode)
  }
}
</script>

<style scoped>
.skill-tree-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.chart {
  width: 100%;
  height: 100%;
}
</style>
