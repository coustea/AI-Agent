<template>
  <div class="assessment-page">
    <header class="page-header">
      <div class="header-left">
        <h1>学习评估</h1>
        <p class="header-subtitle">学习记录如何改变当前辅导策略</p>
      </div>
      <div class="header-actions">
        <div class="range-tabs">
          <button
            v-for="days in rangeOptions"
            :key="days"
            type="button"
            :class="{ active: selectedRange === days }"
            @click="selectedRange = days"
          >
            {{ days }} 天
          </button>
        </div>
        <Button class="generate-btn" :disabled="generating" @click="triggerReportGeneration">
          <Sparkles :size="16" />
          {{ generating ? '生成中' : '生成报告' }}
        </Button>
      </div>
    </header>

    <!-- 生成进度条 -->
    <section v-if="generating" class="generation-progress">
      <span
        v-for="(step, index) in generationSteps"
        :key="step"
        :class="{ done: index < currentStepIdx, current: index === currentStepIdx }"
      >
        {{ step }}
      </span>
    </section>

    <!-- 加载状态 -->
    <section v-if="initialLoading" class="empty-state">
      <Clock3 :size="28" />
      <h2>正在加载学习评估</h2>
      <p>正在读取报告、历史记录和当前辅导策略。</p>
    </section>

    <!-- 无报告状态 -->
    <section v-else-if="!activeReport" class="empty-state">
      <FileCheck :size="28" />
      <h2>暂无评估报告</h2>
      <p>点击「生成报告」创建第一份学习效果评估。</p>
    </section>

    <!-- 失败状态 -->
    <section v-else-if="activeReport.status === 'failed'" class="empty-state failed">
      <AlertCircle :size="24" />
      <h2>报告生成失败</h2>
      <p>{{ activeReport.failure_code || '未知内部错误' }}</p>
      <Button variant="outline" @click="triggerReportGeneration">重新生成</Button>
    </section>

    <!-- 生成中状态 -->
    <section v-else-if="activeReport.status !== 'ready'" class="empty-state">
      <Route :size="28" />
      <h2>报告正在生成</h2>
      <p>{{ formatDateRange(activeReport.window_start, activeReport.window_end) }}</p>
    </section>

    <!-- 正常内容 -->
    <template v-else-if="facts">
      <!-- 横向指标行 -->
      <section class="metrics-row">
        <div class="metric-item">
          <Clock3 :size="16" class="metric-icon" />
          <div class="metric-content">
            <span class="metric-label">学习时长</span>
            <strong class="metric-value">{{ facts.activity.total_minutes }} 分钟</strong>
            <span class="metric-detail">活跃 {{ facts.activity.active_days }} 天</span>
          </div>
        </div>
        <div class="metric-item">
          <Activity :size="16" class="metric-icon" />
          <div class="metric-content">
            <span class="metric-label">系统事件</span>
            <strong class="metric-value">{{ totalEvents }} 次</strong>
            <span class="metric-detail">{{ moduleSummary }}</span>
          </div>
        </div>
        <div class="metric-item">
          <ListChecks :size="16" class="metric-icon" />
          <div class="metric-content">
            <span class="metric-label">练习表现</span>
            <strong class="metric-value">{{ practiceAccuracyLabel }}</strong>
            <span class="metric-detail">{{ facts.practice.correct }} / {{ facts.practice.submitted }} 题</span>
          </div>
        </div>
        <div class="metric-item">
          <Layers :size="16" class="metric-icon" />
          <div class="metric-content">
            <span class="metric-label">资源统计</span>
            <strong class="metric-value">生成 {{ facts.resource_usage.generated }}</strong>
            <span class="metric-detail">浏览 {{ facts.resource_usage.viewed }} / 完成 {{ facts.resource_usage.completed }}</span>
          </div>
        </div>
        <div class="metric-item">
          <Route :size="16" class="metric-icon" />
          <div class="metric-content">
            <span class="metric-label">路径推进</span>
            <strong class="metric-value">{{ percentLabel(facts.learning_path.completion_rate) }}</strong>
            <span class="metric-detail">完成 {{ facts.learning_path.nodes_completed }} 节点</span>
          </div>
        </div>
      </section>

      <!-- 图表区域 -->
      <section class="charts-section">
        <article class="chart-block">
          <div class="block-header">
            <Clock3 :size="16" />
            <h3>每日学习时长趋势</h3>
          </div>
          <v-chart v-if="hasDailyData" class="chart chart-line" :option="lineOption" autoresize />
          <div v-else class="empty-chart">本窗口暂无学习会话时长记录</div>
        </article>

        <article class="chart-block">
          <div class="block-header">
            <ChartColumn :size="16" />
            <h3>功能使用占比</h3>
          </div>
          <v-chart v-if="hasModuleData" class="chart chart-pie" :option="pieOption" autoresize />
          <div v-else class="empty-chart">本窗口暂无学习事件记录</div>
        </article>
      </section>

      <!-- 主题掌握证据 -->
      <section class="topics-section">
        <div class="section-header">
          <Target :size="16" />
          <h3>主题掌握证据</h3>
        </div>
        <div v-if="topicRows.length" class="topics-grid">
          <button
            v-for="topic in topicRows"
            :key="topic.topic"
            type="button"
            class="topic-cell"
          >
            <span class="topic-name">{{ topic.topic }}</span>
            <strong class="topic-accuracy">
              {{ topic.enough_evidence ? percentLabel(topic.accuracy) : '数据不足' }}
            </strong>
            <span class="topic-detail">{{ topic.correct }} / {{ topic.submitted }} 题</span>
          </button>
        </div>
        <div v-else class="empty-chart">本窗口暂无可评估的答题事实</div>
      </section>

      <!-- 当前辅导策略 -->
      <section class="strategy-section">
        <div class="section-header">
          <Compass :size="16" />
          <h3>当前辅导策略</h3>
        </div>
        <div v-if="guidanceStrategy" class="strategy-grid">
          <div class="strategy-item">
            <span class="strategy-label">重点主题</span>
            <strong class="strategy-value">
              {{ guidanceStrategy.focus_topics?.length ? guidanceStrategy.focus_topics.join('、') : '暂无' }}
            </strong>
          </div>
          <div class="strategy-item">
            <span class="strategy-label">建议时长</span>
            <strong class="strategy-value">{{ guidanceStrategy.recommended_session_minutes }} 分钟</strong>
          </div>
          <div class="strategy-item">
            <span class="strategy-label">近期目标</span>
            <strong class="strategy-value">{{ guidanceStrategy.weekly_goal || '暂无' }}</strong>
          </div>
          <div class="strategy-item">
            <span class="strategy-label">辅导风格</span>
            <strong class="strategy-value">{{ guidanceStrategy.tutoring_style || '暂无' }}</strong>
          </div>
        </div>
        <p v-else class="strategy-empty">生成第一份学习评估后将提供建议。</p>
      </section>

      <!-- 证据质量 -->
      <section class="quality-section">
        <div class="section-header">
          <ShieldCheck :size="16" />
          <h3>证据质量</h3>
        </div>
        <div class="quality-metrics">
          <div class="quality-item">
            <span class="quality-label">学习活动</span>
            <strong class="quality-value">{{ facts.data_quality.has_activity ? '已有记录' : '暂无记录' }}</strong>
          </div>
          <div class="quality-item">
            <span class="quality-label">涉及主题</span>
            <strong class="quality-value">{{ facts.topics.encountered.length }} 个</strong>
          </div>
          <div class="quality-item">
            <span class="quality-label">样本不足</span>
            <strong class="quality-value">{{ facts.data_quality.insufficient_topics.length }} 个</strong>
          </div>
          <div class="quality-item">
            <span class="quality-label">资源反馈</span>
            <strong class="quality-value">{{ facts.resource_usage.feedback.helpful + facts.resource_usage.feedback.not_helpful }} 条</strong>
          </div>
        </div>
        <div v-if="facts.topics.encountered.length" class="topic-tags">
          <span v-for="topic in facts.topics.encountered.slice(0, 12)" :key="topic">
            {{ topic }}
          </span>
        </div>
        <p class="quality-note">{{ evidenceNote }}</p>
      </section>

      <!-- 历史报告 -->
      <section class="history-section">
        <div class="section-header">
          <Layers :size="16" />
          <h3>历史报告</h3>
          <span class="history-count">{{ totalReports }} 份</span>
        </div>
        <div v-if="historyLoading" class="empty-chart">正在加载历史报告...</div>
        <div v-else-if="reportsHistory.length === 0" class="empty-chart">暂无历史报告</div>
        <div v-else class="history-list">
          <button
            v-for="report in reportsHistory"
            :key="report.id"
            type="button"
            :class="{ active: activeReport?.id === report.id }"
            @click="selectReport(report.id)"
          >
            <strong>{{ report.range_days }} 天评估</strong>
            <span>{{ formatDateRange(report.window_start, report.window_end) }}</span>
            <em>{{ statusLabel(report.status) }}</em>
          </button>
        </div>
        <div v-if="totalPages > 1" class="pagination">
          <Button variant="ghost" size="sm" :disabled="currentPage <= 1" @click="changePage(currentPage - 1)">
            <ChevronLeft :size="14" />
            上一页
          </Button>
          <span>{{ currentPage }} / {{ totalPages }}</span>
          <Button variant="ghost" size="sm" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">
            下一页
            <ChevronRight :size="14" />
          </Button>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import {
  Activity,
  AlertCircle,
  BookOpenCheck,
  ChartColumn,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Compass,
  FileCheck,
  Layers,
  ListChecks,
  Route,
  ShieldCheck,
  Sparkles,
  Target,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import {
  generateAssessmentReport,
  getGuidanceStrategy,
  getLatestReport,
  getReportDetail,
  getReportsHistory,
} from '@/features/learning-assessment/api/assessment'
import type {
  AssessmentFacts,
  FactsTopicPractice,
  GuidanceStrategy,
  LearningAssessmentReport,
} from '@/features/learning-assessment/model/assessment'
import { normalizeGuidanceStrategy } from '@/features/learning-assessment/model/assessment'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
])

const rangeOptions = [7, 14, 30] as const
const selectedRange = ref<7 | 14 | 30>(7)
const reportsHistory = ref<Omit<LearningAssessmentReport, 'facts_snapshot' | 'report_markdown'>[]>([])
const activeReport = ref<LearningAssessmentReport | null>(null)
const guidanceStrategy = ref<GuidanceStrategy | null>(null)
const generating = ref(false)
const historyLoading = ref(false)
const initialLoading = ref(true)
const currentPage = ref(1)
const totalReports = ref(0)
const totalPages = ref(1)
const currentStepIdx = ref(0)
const pageSize = 10
const generationSteps = ['聚合学习事实', '校验证据质量', '生成评估报告', '更新辅导策略']

const MODULE_LABELS: Record<string, string> = {
  chat: 'AI 辅导',
  quiz: '题库练习',
  path: '学习路径',
  resource: '学习资源',
  visualizer: '算法可视化',
}

const facts = computed<AssessmentFacts | null>(() => activeReport.value?.facts_snapshot ?? null)

const totalEvents = computed(() => (
  facts.value?.activity.module_distribution.reduce((sum, item) => sum + item.count, 0) ?? 0
))

const hasDailyData = computed(() => (
  (facts.value?.activity.daily_minutes ?? []).some(item => item.minutes > 0)
))

const hasModuleData = computed(() => (
  (facts.value?.activity.module_distribution ?? []).some(item => item.count > 0)
))

const topicRows = computed<FactsTopicPractice[]>(() => (
  [...(facts.value?.practice.by_topic ?? [])]
    .sort((a, b) => b.submitted - a.submitted)
    .slice(0, 8)
))

const moduleSummary = computed(() => {
  const modules = facts.value?.activity.module_distribution ?? []
  const top = [...modules].sort((a, b) => b.count - a.count)[0]
  if (!top) return '暂无事件'
  return `${MODULE_LABELS[top.module] || top.module}最多`
})

const practiceAccuracyLabel = computed(() => {
  const current = facts.value
  if (!current || current.practice.submitted === 0) return '无数据'
  return percentLabel(current.practice.accuracy)
})

const evidenceNote = computed(() => {
  const insufficient = facts.value?.data_quality.insufficient_topics ?? []
  if (insufficient.length) return `数据不足：${insufficient.join('、')}`
  if (!facts.value?.data_quality.has_activity) return '当前窗口暂无活动记录。'
  return '当前窗口没有被标记为样本不足的主题。'
})

const lineOption = computed(() => {
  const daily = facts.value?.activity.daily_minutes ?? []
  return {
    grid: { top: 20, right: 16, bottom: 28, left: 40 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b', fontSize: 12 },
      formatter: '{b}<br/>学习时长: {c} 分钟',
    },
    xAxis: {
      type: 'category',
      data: daily.map(item => formatShortDate(item.date)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 11 },
    },
    series: [{
      data: daily.map(item => item.minutes),
      type: 'line',
      smooth: true,
      symbolSize: 5,
      lineStyle: { color: '#0d9488', width: 2 },
      itemStyle: { color: '#0d9488' },
      areaStyle: { color: 'rgba(13, 148, 136, 0.1)' },
    }],
  }
})

const pieOption = computed(() => {
  const modules = facts.value?.activity.module_distribution ?? []
  return {
    color: ['#0d9488', '#2563eb', '#f59e0b', '#10b981', '#64748b'],
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 次 ({d}%)',
      backgroundColor: '#ffffff',
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b', fontSize: 12 },
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      textStyle: { color: '#475569', fontSize: 11 },
    },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '42%'],
      itemStyle: {
        borderRadius: 4,
        borderColor: '#ffffff',
        borderWidth: 2,
      },
      label: { show: false },
      data: modules
        .filter(item => item.count > 0)
        .map(item => ({ value: item.count, name: MODULE_LABELS[item.module] || item.module })),
    }],
  }
})

async function loadGuidanceStrategy(): Promise<void> {
  try {
    const response = await getGuidanceStrategy()
    guidanceStrategy.value = normalizeGuidanceStrategy(response.data.data.guidance_strategy)
  } catch (error) {
    console.error('加载辅导策略失败', error)
  }
}

async function loadReportsHistory(page = 1): Promise<void> {
  historyLoading.value = true
  try {
    const response = await getReportsHistory(page, pageSize)
    reportsHistory.value = response.data.data.items
    totalReports.value = response.data.data.total
    totalPages.value = Math.max(1, Math.ceil(response.data.data.total / pageSize))
    currentPage.value = page
  } catch (error) {
    console.error('加载历史评估报告失败', error)
    toast.error('历史记录加载失败')
  } finally {
    historyLoading.value = false
  }
}

async function selectReport(reportId: number): Promise<void> {
  try {
    const response = await getReportDetail(reportId)
    activeReport.value = response.data.data
  } catch (error) {
    console.error('加载报告详情失败', error)
    toast.error('报告详情加载失败')
  }
}

async function triggerReportGeneration(): Promise<void> {
  generating.value = true
  currentStepIdx.value = 0
  const timer = window.setInterval(() => {
    currentStepIdx.value = Math.min(currentStepIdx.value + 1, generationSteps.length - 1)
  }, 1000)

  try {
    const response = await generateAssessmentReport(selectedRange.value)
    activeReport.value = response.data.data
    toast.success('学习效果评估报告已生成')
    await Promise.all([
      loadReportsHistory(1),
      loadGuidanceStrategy(),
    ])
  } catch (error: any) {
    if (error?.response?.status === 409) {
      toast.warning('已有报告生成中')
    } else {
      console.error('生成评估报告失败', error)
      toast.error('生成报告失败')
    }
  } finally {
    window.clearInterval(timer)
    generating.value = false
    currentStepIdx.value = 0
  }
}

function changePage(page: number): void {
  void loadReportsHistory(page)
}

function statusLabel(status: LearningAssessmentReport['status']): string {
  if (status === 'ready') return '已就绪'
  if (status === 'generating') return '生成中'
  return '失败'
}

function percentLabel(value: number): string {
  return `${Math.round(value * 100)}%`
}

function formatShortDate(value: string): string {
  const parts = value.split('-')
  return parts.length === 3 ? `${parts[1]}-${parts[2]}` : value
}

function formatDateRange(start: string, end: string): string {
  if (!start || !end) return ''
  const startDate = new Date(start)
  const endDate = new Date(end)
  return `${startDate.getMonth() + 1}月${startDate.getDate()}日 - ${endDate.getMonth() + 1}月${endDate.getDate()}日`
}

onMounted(async () => {
  initialLoading.value = true
  await Promise.all([
    loadReportsHistory(1),
    loadGuidanceStrategy(),
  ])

  try {
    const response = await getLatestReport()
    if (response.data.data) {
      activeReport.value = response.data.data
    } else if (reportsHistory.value[0]?.id !== undefined) {
      await selectReport(reportsHistory.value[0].id)
    }
  } catch (error) {
    console.error('获取最新评估报告失败', error)
  } finally {
    initialLoading.value = false
  }
})
</script>

<style scoped>
.assessment-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

h1, h2, h3, p {
  margin: 0;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.header-left h1 {
  font-size: 1.5rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  letter-spacing: 0;
}

.header-subtitle {
  margin-top: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.range-tabs {
  display: inline-flex;
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.range-tabs button {
  min-width: 4rem;
  min-height: 2rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.range-tabs button:hover {
  color: var(--color-text-strong);
  background: var(--color-bg);
}

.range-tabs button.active {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  box-shadow: inset 0 0 0 1px var(--color-primary-border);
}

.generate-btn {
  min-height: 2.25rem;
  gap: var(--space-2);
}

/* Generation Progress */
.generation-progress {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}

.generation-progress span {
  min-height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.generation-progress span.done {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.generation-progress span.current {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

/* Empty State */
.empty-state {
  min-height: 12rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  text-align: center;
  color: var(--color-text-secondary);
}

.empty-state h2 {
  font-size: var(--text-lg);
  color: var(--color-text-strong);
}

.empty-state.failed {
  color: var(--color-danger);
}

/* Metrics Row */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-3);
}

.metric-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.metric-icon {
  flex-shrink: 0;
  color: var(--color-primary-text);
  margin-top: 2px;
}

.metric-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.metric-value {
  font-size: var(--text-md);
  color: var(--color-text-strong);
  line-height: 1.2;
}

.metric-detail {
  font-size: var(--text-xs);
  color: var(--color-text-faint);
}

/* Charts Section */
.charts-section {
  display: grid;
  grid-template-columns: 1.4fr 0.6fr;
  gap: var(--space-4);
}

.chart-block {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: var(--space-4);
}

.block-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  color: var(--color-primary-text);
}

.block-header h3 {
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.chart {
  width: 100%;
}

.chart-line,
.chart-pie {
  height: 14rem;
}

.empty-chart {
  min-height: 6rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  font-size: var(--text-sm);
}

/* Section Header */
.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  color: var(--color-primary-text);
}

.section-header h3 {
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.history-count {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

/* Topics Section */
.topics-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: var(--space-4);
}

.topics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.topic-cell {
  min-height: 5.5rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  transition: all var(--transition-fast);
}

.topic-cell:hover {
  border-color: var(--color-primary-border);
  background: var(--color-primary-soft);
}

.topic-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  overflow-wrap: anywhere;
}

.topic-accuracy {
  font-size: var(--text-lg);
  color: var(--color-primary-text);
}

.topic-detail {
  font-size: var(--text-xs);
  color: var(--color-text-faint);
}

/* Strategy Section */
.strategy-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: var(--space-4);
}

.strategy-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.strategy-item {
  min-height: 5rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-surface) 88%, var(--color-primary-soft));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-1);
}

.strategy-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.strategy-value {
  font-size: var(--text-md);
  color: var(--color-text-strong);
  line-height: 1.3;
}

.strategy-empty {
  min-height: 6rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
}

/* Quality Section */
.quality-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: var(--space-4);
}

.quality-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.quality-item {
  min-height: 4.5rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-surface) 88%, var(--color-primary-soft));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.quality-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.quality-value {
  font-size: var(--text-md);
  color: var(--color-text-strong);
}

.topic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.topic-tags span {
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.quality-note {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

/* History Section */
.history-section {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  padding: var(--space-4);
}

.history-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.history-list button {
  min-height: 4rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: all var(--transition-fast);
}

.history-list button:hover,
.history-list button.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.history-list strong {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
}

.history-list span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.history-list em {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-style: normal;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Responsive */
@media (max-width: 1024px) {
  .charts-section {
    grid-template-columns: 1fr;
  }

  .metrics-row {
    grid-template-columns: repeat(3, 1fr);
  }

  .strategy-grid,
  .quality-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .assessment-page {
    padding: var(--space-4);
  }

  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    flex-wrap: wrap;
  }

  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .topics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .history-list {
    grid-template-columns: 1fr;
  }

  .generation-progress {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .metrics-row {
    grid-template-columns: 1fr;
  }

  .strategy-grid,
  .quality-metrics,
  .topics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
