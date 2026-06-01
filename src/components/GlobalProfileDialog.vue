<template>
  <el-dialog
    v-model="isGlobalProfileVisible"
    title="我的技能成长树"
    class="global-profile-dialog"
    width="900px"
    :top="'5vh'"
    :append-to-body="true"
    @open="handleOpen"
  >
    <div class="dialog-body-container">
      
      <div class="tree-wrapper" v-if="hasAuthenticData">
        <!-- ECharts Tree -->
        <v-chart 
          class="echarts-tree" 
          :option="chartOption" 
          autoresize
          @click="handleNodeClick"
        />
        
        <!-- Side Detail Panel -->
        <transition name="slide-fade">
          <div v-if="activeNode" class="side-detail-panel">
            <div class="panel-header">
              <h2 class="panel-title">{{ activeNode.title }}</h2>
              <el-icon class="close-btn" tabindex="0" aria-label="Close detail panel" @click="activeNode = null" @keyup.enter="activeNode = null"><Close /></el-icon>
            </div>
            <div class="panel-content">
              <p class="panel-summary">{{ activeNode.content }}</p>
              
              <template v-if="activeNode.evidence && activeNode.evidence.length > 0">
                <h3 class="panel-subtitle">确切证据</h3>
                <ul class="panel-evidence">
                  <li v-for="(ev, idx) in activeNode.evidence" :key="idx">{{ ev }}</li>
                </ul>
              </template>
            </div>
          </div>
        </transition>
      </div>

      <!-- Empty State -->
      <div class="profile-empty-state" v-else aria-live="polite">
        <div class="empty-visual-container">
          <div class="empty-visual">
            <el-icon aria-hidden="true"><Cpu /></el-icon>
          </div>
        </div>
        <div class="empty-text-wrap">
          <h2>待捕获画像特征</h2>
          <p>由于对话样本较少，您的动态学习画像仍在生成中。多参与学习活动，我们会为您建立更精准的画像。</p>
        </div>
      </div>
      
      <!-- Recommended Strategy Section -->
      <div class="recommended-strategy-section" v-if="recommendedStrategy.length > 0">
        <h2 class="section-heading"><el-icon aria-hidden="true"><Aim /></el-icon> 专属辅导策略</h2>
        <ul class="strategy-list">
          <li v-for="(strategy, idx) in recommendedStrategy" :key="idx">{{ strategy }}</li>
        </ul>
      </div>
      
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  Aim, Cpu, Close
} from '@element-plus/icons-vue'
import { getProfile } from '@/api/ai'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/composables/useGlobalProfile'

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { TreeChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'

use([CanvasRenderer, TreeChart, TooltipComponent])

interface ProfileNodeData {
  title: string
  content: string
  evidence: string[]
}

const treeDataRaw = ref<any>(null)
const profileCards = ref<ProfileNodeData[]>([]) 
const recommendedStrategy = ref<string[]>([])
const activeNode = ref<ProfileNodeData | null>(null)

const hasAuthenticData = computed(() => {
  return treeDataRaw.value && treeDataRaw.value.children && treeDataRaw.value.children.length > 0
})

const chartOption = computed(() => {
  if (!hasAuthenticData.value) return {}
  return {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      formatter: (params: any) => {
        // If it's a leaf node (evidence), don't show full text in tooltip as it breaks layout.
        if (!params.data.children && params.data.value) {
          return `<div style="max-width: 300px; white-space: normal;">${params.data.value}</div>`
        }
        return params.name
      }
    },
    series: [
      {
        type: 'tree',
        data: [treeDataRaw.value],
        top: '10%',
        left: '8%',
        bottom: '15%',
        right: '8%',
        symbolSize: 12,
        orient: 'bottomToTop',
        initialTreeDepth: 2,
        roam: true,
        label: {
          position: 'left',
          verticalAlign: 'middle',
          align: 'right',
          fontSize: 13,
          color: '#262626',
          backgroundColor: '#fff',
          padding: [4, 8],
          borderRadius: 4,
          borderColor: '#d9d9d9',
          borderWidth: 1,
          shadowColor: 'rgba(0,0,0,0.05)',
          shadowBlur: 4,
          shadowOffsetY: 2
        },
        leaves: {
          label: {
            position: 'right',
            verticalAlign: 'middle',
            align: 'left',
            color: '#595959',
            backgroundColor: 'transparent',
            borderColor: 'transparent',
            borderWidth: 0,
            shadowBlur: 0,
            shadowOffsetY: 0
          }
        },
        emphasis: {
          focus: 'descendant'
        },
        expandAndCollapse: true,
        animationDuration: 550,
        animationDurationUpdate: 750
      }
    ]
  }
})

const handleNodeClick = (params: any) => {
  const nodeName = params.data.name
  const card = profileCards.value.find(c => c.title === nodeName)
  if (card) {
    activeNode.value = card
  } else {
    // Clicked root or leaf
    activeNode.value = null
  }
}

const fetchProfile = async () => {
  try {
    const res = await getProfile()
    const data = res.data.data
    if (!data) return

    const profileJson = data.profile_json || {}
    const dimensions = (profileJson.dimensions || {}) as Record<string, any>
    const nextCards: ProfileNodeData[] = []
    
    const root = {
      name: '学枢平台画像',
      itemStyle: { color: '#5A52FF', borderColor: '#4338CA', borderWidth: 2 },
      symbolSize: 18,
      label: {
        fontSize: 15,
        fontWeight: 'bold',
        color: '#5A52FF',
        borderColor: '#5A52FF',
        borderWidth: 2
      },
      children: [] as any[]
    }

    const targetDimensionsKeys = [
      'knowledge_foundation',
      'learning_goal',
      'cognitive_style',
      'weakness_points',
      'mistake_preference',
      'practice_ability',
      'interaction_preference',
      'learning_history'
    ]

    const dimensionNames: Record<string, string> = {
      knowledge_foundation: '知识基础',
      learning_goal: '学习目标',
      cognitive_style: '认知风格',
      weakness_points: '薄弱点',
      mistake_preference: '易错点偏好',
      practice_ability: '实践能力',
      interaction_preference: '交互偏好',
      learning_history: '学习历史',
    }

    for (const key of targetDimensionsKeys) {
      const dim = dimensions[key]
      if (!dim) continue
      const dimData = dim as { name?: string; summary?: string; evidence?: string[]; confidence?: number }
      
      
      if (dimData.summary || (dimData.evidence && dimData.evidence.length > 0)) {
        const title = dimensionNames[key] || key
        const content = dimData.summary || '暂无详细描述'
        const evidence = dimData.evidence || []
        
        nextCards.push({
          title,
          content: content.trim(),
          evidence
        })
        
        const nodeChildren = evidence.map(ev => ({ 
          name: ev.length > 12 ? ev.substring(0, 12) + '…' : ev, 
          value: ev,
          itemStyle: { color: '#52c41a' }
        }))
        
        root.children.push({
          name: title,
          itemStyle: { color: '#1890ff' },
          children: nodeChildren
        })
      }
    }

    profileCards.value = nextCards
    treeDataRaw.value = root
    recommendedStrategy.value = (profileJson.recommended_strategy as string[]) || []
    
    if (activeNode.value) {
      const stillExists = nextCards.find(c => c.title === activeNode.value?.title)
      if (!stillExists) activeNode.value = null
    }

  } catch (e) {
    console.error('Failed to fetch profile', e)
  }
}

const handleOpen = () => {
  activeNode.value = null
  fetchProfile()
}

watch(profileRefreshTrigger, () => {
  if (isGlobalProfileVisible.value) {
    fetchProfile()
  }
})
</script>

<style>
.global-profile-dialog {
  border-radius: var(--radius-2xl) !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important;
  background: #ffffff !important;
  border: 1px solid #eaeaea !important;
}

.global-profile-dialog .el-dialog__header {
  padding: var(--space-6) var(--space-8) var(--space-4);
  margin-right: 0;
  border-bottom: 1px solid #f0f0f0;
}

.global-profile-dialog .el-dialog__title {
  font-weight: var(--weight-bold);
  font-size: 1.25rem;
  color: #1a1a1a;
  letter-spacing: -0.01em;
}

.global-profile-dialog .el-dialog__body {
  padding: var(--space-6) var(--space-8) var(--space-8) !important;
}
</style>

<style scoped>
.dialog-body-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.tree-wrapper {
  position: relative;
  width: 100%;
  height: 480px;
  background: #fafafa;
  border-radius: var(--radius-lg);
  border: 1px solid #e8e8e8;
  overflow: hidden;
}

.echarts-tree {
  width: 100%;
  height: 100%;
}

/* Side Panel */
.side-detail-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 320px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-left: 1px solid #f0f0f0;
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  z-index: 10;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid #f0f0f0;
}

.panel-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
  color: #262626;
  text-wrap: balance;
}

.close-btn {
  font-size: 1.2rem;
  color: #8c8c8c;
  cursor: pointer;
  transition: color 0.2s;
  outline: none;
}
.close-btn:hover, .close-btn:focus-visible {
  color: #f5222d;
}

.panel-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-5);
}

.panel-summary {
  margin: 0 0 var(--space-5) 0;
  font-size: 0.95rem;
  line-height: 1.6;
  color: #595959;
  word-break: break-word;
}

.panel-subtitle {
  margin: 0 0 var(--space-3) 0;
  font-size: 1rem;
  font-weight: 600;
  color: #262626;
}

.panel-evidence {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.panel-evidence li {
  position: relative;
  padding-left: 16px;
  font-size: 0.9rem;
  line-height: 1.5;
  color: #475569;
}

.panel-evidence li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #1890ff;
}

/* Animations */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.profile-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-visual-container {
  position: relative;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
}

.empty-visual {
  width: 64px;
  height: 64px;
  background: #fafafa;
  color: #d9d9d9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  border: 1px solid #f0f0f0;
}

.empty-text-wrap h2 {
  margin: 0 0 12px 0;
  color: #262626;
  font-size: 1.15rem;
  font-weight: 600;
  text-wrap: balance;
}

.empty-text-wrap p {
  margin: 0;
  color: #8c8c8c;
  font-size: 0.95rem;
  max-width: 360px;
  line-height: 1.6;
}

.section-heading {
  font-size: 1.15rem;
  font-weight: 600;
  color: #262626;
  margin: 0 0 var(--space-4) 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-wrap: balance;
}

.section-heading .el-icon {
  color: var(--color-primary);
  font-size: 1.25rem;
}

.strategy-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.strategy-list li {
  background: #f8fafc;
  border-left: 3px solid var(--color-primary);
  padding: var(--space-3) var(--space-4);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.6;
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
