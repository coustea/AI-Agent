<template>
  <div class="page-container">
    <section class="eval-header">
      <div>
        <p class="eyebrow">学习效果评估</p>
        <h2 class="title">多维学习状态报告</h2>
        <p class="subtitle">结合练习表现、资源完成度和学习反馈，持续校准后续计划。</p>
      </div>
      <el-button :icon="RefreshRight" :loading="loading" type="primary" @click="loadSummary">
        刷新评估
      </el-button>
    </section>

    <el-alert
      v-if="error"
      class="state-alert"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    />

    <el-skeleton v-if="loading && !summary" animated :rows="8" />

    <template v-else>
      <el-row :gutter="24">
        <el-col :xs="24" :lg="8">
          <section class="score-card">
            <el-progress
              type="dashboard"
              :percentage="score"
              :stroke-width="12"
              :color="scoreColors"
            >
              <template #default="{ percentage }">
                <div class="score-text">
                  <span class="score-num">{{ percentage }}</span>
                  <span class="score-unit">综合评分</span>
                </div>
              </template>

<script setup lang="ts">
import {
  Calendar,
  DataAnalysis,
  Medal,
  RefreshRight,
  TrendCharts,
} from '@element-plus/icons-vue'

import { computed, onMounted, ref } from 'vue'

import { getEvaluationSummary, type EvaluationSummary, type LearningEventItem } from '@/api/ai'

const loading = ref(false)

const error = ref('')

const summary = ref<EvaluationSummary | null>(null)

const score = computed(() => {
  if (!summary.value) return 0
  if (summary.value.average_score !== null) return Math.round(summary.value.average_score)
  if (summary.value.event_count > 0) return Math.min(100, 55 + summary.value.completed_resources * 8)
  return 0
})

const scoreLabel = computed(() => {
  if (summary.value?.event_count === 0) return '等待学习数据'
  if (score.value >= 85) return '学习状态：优秀'
  if (score.value >= 70) return '学习状态：稳定'
  if (score.value >= 50) return '学习状态：需巩固'
  return '学习状态：待启动'
})

const scoreTagType = computed(() => {
  if (score.value >= 85) return 'success'
  if (score.value >= 60) return 'warning'
  return 'info'
})

const displayMetrics = computed(() => summary.value?.metrics ?? [
  { label: '平均测验分', value: '暂无', trend: 'stable' },
  { label: '完成资源', value: '0', trend: 'stable' },
  { label: '活跃学习', value: '0 分钟', trend: 'stable' },
])

const recentEvents = computed<LearningEventItem[]>(() => summary.value?.recent_events ?? [])

const weakTopics = computed(() => summary.value?.weak_topics ?? [])

const preferredResources = computed(() => summary.value?.preferred_resources ?? [])

const recommendations = computed(() => summary.value?.recommendations ?? ['完成一次练习或资源学习后，这里会生成更具体的建议。'])

const scoreColors = [
  { color: '#f56c6c', percentage: 40 },
  { color: '#e6a23c', percentage: 65 },
  { color: '#5cb87a', percentage: 80 },
  { color: '#1989fa', percentage: 100 },
]

onMounted(loadSummary)

declare function withDefaults<T, D>(props: T, defaults: D): T;

const loadSummary = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await getEvaluationSummary()
    summary.value = res.data.data
  } catch (err) {
    error.value = err instanceof Error ? err.message : '评估数据加载失败'
  } finally {
    loading.value = false
  }
}

const trendLabel = (trend: string) => {
  if (trend === 'up') return '提升中'
  if (trend === 'down') return '需关注'
  return '稳定'
}

const eventLabel = (eventType: string) => {
  const labels: Record<string, string> = {
    resource_viewed: '查看资源',
    resource_completed: '完成资源',
    quiz_submitted: '提交练习',
    path_feedback: '路径反馈',
    tutor_helpful: '辅导反馈',
    resource_feedback: '资源反馈',
  }
  return labels[eventType] || eventType
}

const formatDate = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.page-container { min-height: 100vh; background: var(--color-bg); padding: var(--space-8); }
.eval-header { max-width: 1120px; margin: 0 auto var(--space-6); display: flex; justify-content: space-between; align-items: flex-end; gap: var(--space-5); }
.eyebrow { margin: 0 0 var(--space-2); font-size: 0.78rem; font-weight: var(--weight-extrabold); color: var(--color-info); text-transform: uppercase; letter-spacing: 0.08em; }
.title { font-size: 1.9rem; color: var(--color-text); margin: 0 0 var(--space-2); }
.subtitle { color: var(--color-text-muted); margin: 0; }
.state-alert { max-width: 1120px; margin: 0 auto var(--space-5); }
.score-card { background: var(--color-surface); padding: 28px; border-radius: var(--radius-lg); text-align: center; border: 1px solid var(--color-border); display: flex; flex-direction: column; align-items: center; gap: 18px; }
.score-text { display: flex; flex-direction: column; }
.score-num { font-size: 2.8rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.score-unit { font-size: 0.875rem; color: var(--color-text-muted); margin-top: -5px; }
.metrics-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-4); }
.metric-card { border-radius: var(--radius-lg); border: 1px solid var(--color-border); }
.metric-header { display: flex; justify-content: space-between; align-items: center; font-weight: var(--weight-bold); font-size: 0.9rem; }
.metric-body { display: flex; flex-direction: column; gap: var(--space-2); }
.metric-body strong { font-size: 1.5rem; color: var(--color-text); }
.metric-body span { color: var(--color-text-muted); font-size: 0.86rem; }
.eval-sections { max-width: 1120px; margin: var(--space-6) auto 0; display: flex; flex-direction: column; gap: var(--space-5); }
.section-box { background: var(--color-surface); padding: var(--space-6); border-radius: var(--radius-lg); border: 1px solid var(--color-border); }
.section-box.highlight { background: var(--color-primary-soft); border-color: var(--color-primary-border); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4); }
.section-title { font-size: 1.05rem; margin: 0 0 var(--space-4); display: flex; align-items: center; gap: var(--space-2); color: var(--color-text); }
.section-header .section-title { margin: 0; }
.insight-grid { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr); gap: var(--space-5); }
.ai-report { line-height: 1.8; color: #374151; font-size: 0.95rem; }
.ai-report p { margin: 0 0 10px; }
.tag-group { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.mt-4 { margin-top: var(--space-4); }
.score-cell { font-weight: var(--weight-extrabold); color: var(--color-text); }
.score-cell.weak { color: #DC2626; }

@media (max-width: 960px) {
  .page-container { padding: var(--space-5); }
  .eval-header { align-items: flex-start; flex-direction: column; }
  .metrics-grid, .insight-grid { grid-template-columns: 1fr; }
}
</style>
