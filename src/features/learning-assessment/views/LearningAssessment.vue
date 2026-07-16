<template>
  <div class="assessment-page">
    <header class="page-header">
      <div class="header-left">
        <h1>学习评估</h1>
        <p class="header-subtitle">基于学习记录的自适应辅导策略调整</p>
      </div>
      <div class="header-actions">
        <div class="range-tabs" role="group" aria-label="评估时间范围">
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
          {{ generating ? '生成中' : '重新评估' }}
        </Button>
      </div>
    </header>

    <!-- 生成进度 -->
    <section v-if="generating" class="generation-progress" aria-label="生成进度">
      <span
        v-for="(step, index) in generationSteps"
        :key="step"
        :class="{ done: index < currentStepIdx, current: index === currentStepIdx }"
      >
        {{ step }}
      </span>
    </section>

    <!-- 加载状态 -->
    <section v-if="initialLoading" class="loading-state">
      <div class="loading-spinner" />
      <p>正在加载学习评估数据...</p>
    </section>

    <!-- 无报告状态 -->
    <section v-else-if="!activeReport" class="empty-state">
      <FileCheck :size="32" class="empty-icon" />
      <h2>暂无评估报告</h2>
      <p>点击「重新评估」开始生成第一份学习效果评估报告</p>
    </section>

    <!-- 失败状态 -->
    <section v-else-if="activeReport.status === 'failed'" class="error-state">
      <AlertCircle :size="24" />
      <h2>报告生成失败</h2>
      <p>{{ activeReport.failure_code || '未知内部错误' }}</p>
      <Button variant="outline" @click="triggerReportGeneration">重试</Button>
    </section>

    <!-- 生成中状态 -->
    <section v-else-if="activeReport.status !== 'ready'" class="loading-state">
      <div class="loading-spinner" />
      <p>报告正在生成中...</p>
    </section>

    <!-- 主内容 -->
    <template v-else-if="facts">
      <!-- 本期结论与策略 -->
      <section class="conclusion-section">
        <div class="conclusion-card">
          <div class="conclusion-header">
            <ShieldCheck :size="18" />
            <h2>本期结论与策略调整</h2>
            <span class="window-badge">
              <Calendar :size="14" />
              {{ activeReport.range_days }} 天
              {{ formatDateRange(activeReport.window_start, activeReport.window_end) }}
            </span>
          </div>
          <p class="conclusion-text">{{ guidanceStrategy?.conclusion || defaultConclusion }}</p>
          <div v-if="guidanceStrategy" class="strategy-highlights">
            <div class="highlight-item">
              <span class="highlight-label">重点主题</span>
              <strong class="highlight-value">
                {{ guidanceStrategy.focus_topics?.length ? guidanceStrategy.focus_topics.join('、') : '暂无' }}
              </strong>
            </div>
            <div class="highlight-item">
              <span class="highlight-label">建议时长</span>
              <strong class="highlight-value">{{ guidanceStrategy.recommended_session_minutes }} 分钟/次</strong>
            </div>
            <div class="highlight-item">
              <span class="highlight-label">辅导方式</span>
              <strong class="highlight-value">{{ guidanceStrategy.tutoring_style || '暂无' }}</strong>
            </div>
          </div>
        </div>
      </section>

      <!-- 核心指标 -->
      <section class="metrics-section" aria-label="核心学习指标">
        <div class="metric-card">
          <Clock :size="18" class="metric-icon" />
          <div class="metric-body">
            <span class="metric-label">学习时长</span>
            <strong class="metric-value">{{ facts.activity.total_minutes }}</strong>
            <span class="metric-unit">分钟</span>
          </div>
          <span class="metric-sub">活跃 {{ facts.activity.active_days }} 天</span>
        </div>
        <div class="metric-card">
          <ListChecks :size="18" class="metric-icon" />
          <div class="metric-body">
            <span class="metric-label">练习正确率</span>
            <strong class="metric-value">{{ percentLabel(facts.practice.accuracy) }}</strong>
          </div>
          <span class="metric-sub">完成 {{ facts.practice.correct }}/{{ facts.practice.submitted }} 题</span>
        </div>
        <div class="metric-card">
          <Route :size="18" class="metric-icon" />
          <div class="metric-body">
            <span class="metric-label">路径完成率</span>
            <strong class="metric-value">{{ percentLabel(facts.learning_path.completion_rate) }}</strong>
          </div>
          <span class="metric-sub">完成 {{ facts.learning_path.nodes_completed }} 节点</span>
        </div>
        <div class="metric-card">
          <Target :size="18" class="metric-icon" />
          <div class="metric-body">
            <span class="metric-label">涉及主题</span>
            <strong class="metric-value">{{ facts.topics.encountered.length }}</strong>
            <span class="metric-unit">个</span>
          </div>
          <span class="metric-sub">{{ topicsSummary }}</span>
        </div>
      </section>

      <!-- 学习趋势 + 主题掌握 -->
      <section class="analysis-section">
        <article class="chart-panel">
          <div class="panel-header">
            <Clock :size="16" />
            <h3>每日学习趋势</h3>
          </div>
          <v-chart v-if="hasDailyData" class="chart" :option="lineOption" autoresize />
          <div v-else class="chart-empty">本窗口暂无学习时长记录</div>
        </article>
        <article class="topics-panel">
          <div class="panel-header">
            <Target :size="16" />
            <h3>主题掌握情况</h3>
          </div>
          <div v-if="topicRows.length" class="topic-bars">
            <div
              v-for="topic in topicRows.slice(0, 5)"
              :key="topic.topic"
              class="topic-bar"
            >
              <div class="topic-info">
                <span class="topic-name">{{ topic.topic }}</span>
                <span class="topic-stats">{{ topic.correct }}/{{ topic.submitted }} 题</span>
              </div>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{ width: `${topic.accuracy * 100}%` }"
                  :class="{ weak: topic.accuracy < 0.6, moderate: topic.accuracy >= 0.6 && topic.accuracy < 0.8 }"
                />
              </div>
              <strong class="topic-accuracy" :class="{ weak: topic.accuracy < 0.6 }">
                {{ topic.enough_evidence ? percentLabel(topic.accuracy) : '数据不足' }}
              </strong>
            </div>
          </div>
          <div v-else class="chart-empty">本窗口暂无练习记录</div>
        </article>
      </section>

      <!-- 行动计划 -->
      <section v-if="actionPlan.length" class="action-section">
        <div class="section-header">
          <Compass :size="16" />
          <h3>下一阶段学习计划</h3>
        </div>
        <div class="action-list">
          <div
            v-for="(action, index) in actionPlan"
            :key="index"
            class="action-item"
          >
            <span class="action-index">{{ index + 1 }}</span>
            <div class="action-content">
              <p class="action-description">{{ action.description }}</p>
              <span class="action-topic">{{ action.topic }}</span>
            </div>
            <RouterLink :to="action.link" class="action-link">
              <span>{{ actionTypeLabel(action.action_type) }}</span>
              <ArrowRight :size="14" />
            </RouterLink>
          </div>
        </div>
      </section>

      <!-- 详细数据入口 -->
      <section class="detail-entry">
        <Button variant="outline" @click="showDetailDrawer = true">
          <Layers :size="16" />
          查看完整评估数据
        </Button>
      </section>

      <!-- 历史报告 -->
      <section class="history-section">
        <div class="section-header">
          <History :size="16" />
          <h3>历史报告</h3>
          <span class="history-count">{{ totalReports }} 份</span>
        </div>
        <div v-if="historyLoading" class="history-loading">加载中...</div>
        <div v-else-if="reportsHistory.length === 0" class="history-empty">暂无历史报告</div>
        <div v-else class="history-grid">
          <button
            v-for="report in reportsHistory.slice(0, 4)"
            :key="report.id"
            type="button"
            :class="{ active: activeReport?.id === report.id }"
            class="history-item"
            @click="selectReport(report.id)"
          >
            <strong>{{ report.range_days }} 天评估</strong>
            <span>{{ formatDateRange(report.window_start, report.window_end) }}</span>
          </button>
        </div>
        <div v-if="totalReports > 4" class="history-more">
          <Button variant="ghost" size="sm" @click="showHistoryDrawer = true">
            查看全部 {{ totalReports }} 份报告
            <ChevronRight :size="14" />
          </Button>
        </div>
      </section>
    </template>

    <!-- 详细数据抽屉 -->
    <Teleport to="body">
      <div v-if="showDetailDrawer" class="drawer-overlay" @click.self="showDetailDrawer = false">
        <div class="drawer-panel">
          <header class="drawer-header">
            <h2>完整评估数据</h2>
            <button type="button" class="drawer-close" @click="showDetailDrawer = false">
              <X :size="20" />
            </button>
          </header>
          <div class="drawer-body">
            <template v-if="facts">
              <!-- 资源与路径详情 -->
              <article class="detail-block">
                <h4>资源使用统计</h4>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span>生成资源</span>
                    <strong>{{ facts.resource_usage.generated }}</strong>
                  </div>
                  <div class="detail-item">
                    <span>浏览资源</span>
                    <strong>{{ facts.resource_usage.viewed }}</strong>
                  </div>
                  <div class="detail-item">
                    <span>完成资源</span>
                    <strong>{{ facts.resource_usage.completed }}</strong>
                  </div>
                  <div class="detail-item">
                    <span>有帮助反馈</span>
                    <strong>{{ facts.resource_usage.feedback.helpful }}</strong>
                  </div>
                </div>
              </article>

              <!-- 学习路径详情 -->
              <article class="detail-block">
                <h4>学习路径进度</h4>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span>开始节点</span>
                    <strong>{{ facts.learning_path.nodes_started }}</strong>
                  </div>
                  <div class="detail-item">
                    <span>完成节点</span>
                    <strong>{{ facts.learning_path.nodes_completed }}</strong>
                  </div>
                  <div class="detail-item">
                    <span>完成率</span>
                    <strong>{{ percentLabel(facts.learning_path.completion_rate) }}</strong>
                  </div>
                </div>
              </article>

              <!-- 证据质量 -->
              <article class="detail-block">
                <h4>证据质量</h4>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span>学习活动</span>
                    <strong>{{ facts.data_quality.has_activity ? '已有记录' : '暂无记录' }}</strong>
                  </div>
                  <div class="detail-item">
                    <span>样本不足主题</span>
                    <strong>{{ facts.data_quality.insufficient_topics.length }} 个</strong>
                  </div>
                </div>
                <p v-if="facts.data_quality.insufficient_topics.length" class="detail-note">
                  数据不足：{{ facts.data_quality.insufficient_topics.join('、') }}
                </p>
              </article>

              <!-- 涉及主题标签 -->
              <article v-if="facts.topics.encountered.length" class="detail-block">
                <h4>涉及主题</h4>
                <div class="topic-tags">
                  <span v-for="topic in facts.topics.encountered" :key="topic" class="topic-tag">
                    {{ topic }}
                  </span>
                </div>
              </article>
            </template>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 历史报告抽屉 -->
    <Teleport to="body">
      <div v-if="showHistoryDrawer" class="drawer-overlay" @click.self="showHistoryDrawer = false">
        <div class="drawer-panel">
          <header class="drawer-header">
            <h2>历史报告</h2>
            <button type="button" class="drawer-close" @click="showHistoryDrawer = false">
              <X :size="20" />
            </button>
          </header>
          <div class="drawer-body">
            <div v-if="historyLoading" class="history-loading">加载中...</div>
            <div v-else class="history-full-list">
              <button
                v-for="report in reportsHistory"
                :key="report.id"
                type="button"
                :class="{ active: activeReport?.id === report.id }"
                class="history-full-item"
                @click="selectReport(report.id); showHistoryDrawer = false"
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
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { RouterLink } from 'vue-router'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  FileCheck,
  History,
  Layers,
  ListChecks,
  Route,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import {
  generateAssessmentReport,
  getGuidanceStrategy,
  getLatestReport,
  getReportDetail,
  getReportsHistory,
} from '@/features/learning-assessment/api/assessment'
import type {
  ActionPlanItem,
  AssessmentFacts,
  FactsTopicPractice,
  GuidanceStrategy,
  LearningAssessmentReport,
} from '@/features/learning-assessment/model/assessment'
import { normalizeGuidanceStrategy } from '@/features/learning-assessment/model/assessment'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const rangeOptions = [3, 7, 14] as const
const selectedRange = ref<3 | 7 | 14>(7)
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
const showDetailDrawer = ref(false)
const showHistoryDrawer = ref(false)
const generationSteps = ['聚合学习事实', '校验证据质量', '生成评估报告', '更新辅导策略']

const facts = computed<AssessmentFacts | null>(() => activeReport.value?.facts_snapshot ?? null)

const actionPlan = computed<ActionPlanItem[]>(() => guidanceStrategy.value?.action_plan ?? [])

const defaultConclusion = computed(() => {
  if (!facts.value) return '暂无学习数据，开始学习后将生成个性化评估。'
  if (!facts.value.data_quality.has_activity) {
    return '当前窗口暂无学习活动记录，建议先完成一次资源学习或练习。'
  }
  return '学习证据已形成，系统已记录到学习时长、模块使用和练习表现。'
})

const hasDailyData = computed(() => (
  (facts.value?.activity.daily_minutes ?? []).some(item => item.minutes > 0)
))

const topicRows = computed<FactsTopicPractice[]>(() => (
  [...(facts.value?.practice.by_topic ?? [])]
    .sort((a, b) => b.submitted - a.submitted)
))

const topicsSummary = computed(() => {
  const topics = facts.value?.topics.encountered ?? []
  if (topics.length === 0) return '暂无主题'
  if (topics.length <= 3) return topics.join('、')
  return `${topics.slice(0, 3).join('、')} 等`
})

const lineOption = computed(() => {
  const daily = facts.value?.activity.daily_minutes ?? []
  return {
    grid: { top: 24, right: 20, bottom: 32, left: 44 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937', fontSize: 13 },
      formatter: '{b}<br/>学习时长: {c} 分钟',
    },
    xAxis: {
      type: 'category',
      data: daily.map(item => formatShortDate(item.date)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f3f4f6', type: 'dashed' } },
      axisLabel: { color: '#6b7280', fontSize: 12 },
    },
    series: [{
      data: daily.map(item => item.minutes),
      type: 'line',
      smooth: true,
      symbolSize: 6,
      lineStyle: { color: '#0d9488', width: 2.5 },
      itemStyle: { color: '#0d9488' },
      areaStyle: { color: 'rgba(13, 148, 136, 0.1)' },
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

function actionTypeLabel(type: ActionPlanItem['action_type']): string {
  const labels: Record<string, string> = {
    review: '开始复习',
    practice: '进入练习',
    quiz: '开始测验',
  }
  return labels[type] || '开始学习'
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
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

h1, h2, h3, h4, p {
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
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.range-tabs button {
  min-width: 3.5rem;
  min-height: 2rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
  transition: all 0.15s ease;
}

.range-tabs button:hover {
  color: var(--color-text-strong);
  background: var(--color-bg);
}

.range-tabs button.active {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
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
  min-height: 2.25rem;
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
  border-color: transparent;
}

.generation-progress span.current {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border-color: transparent;
}

/* Loading & Empty States */
.loading-state,
.empty-state,
.error-state {
  min-height: 14rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  text-align: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state .empty-icon {
  color: var(--color-text-muted);
}

.empty-state h2,
.error-state h2 {
  font-size: var(--text-lg);
  color: var(--color-text-strong);
}

.empty-state p,
.loading-state p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.error-state {
  color: var(--color-danger);
}

.error-state h2 {
  color: var(--color-danger);
}

/* Conclusion Section */
.conclusion-section {
  margin-top: var(--space-1);
}

.conclusion-card {
  padding: var(--space-5);
  background: linear-gradient(135deg, var(--color-primary-soft) 0%, var(--color-surface) 40%);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-lg);
}

.conclusion-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  color: var(--color-primary-text);
}

.conclusion-header h2 {
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.window-badge {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-weight: var(--weight-bold);
}

.conclusion-text {
  font-size: var(--text-base);
  color: var(--color-text-strong);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-4);
}

.strategy-highlights {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.highlight-item {
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.highlight-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.highlight-value {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  line-height: 1.3;
}

/* Metrics Section */
.metrics-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.metric-card {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.metric-icon {
  color: var(--color-primary-text);
}

.metric-body {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
  flex-wrap: wrap;
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.metric-value {
  font-size: 1.5rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  line-height: 1;
}

.metric-unit {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.metric-sub {
  font-size: var(--text-xs);
  color: var(--color-text-faint);
}

/* Analysis Section */
.analysis-section {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-4);
}

.chart-panel,
.topics-panel {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  color: var(--color-primary-text);
}

.panel-header h3 {
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.chart {
  width: 100%;
  height: 12rem;
}

.chart-empty {
  min-height: 10rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  font-size: var(--text-sm);
}

/* Topic Bars */
.topic-bars {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.topic-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 80px;
  grid-template-rows: auto auto;
  gap: var(--space-1) var(--space-2);
  align-items: center;
}

.topic-info {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.topic-name {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  font-weight: var(--weight-bold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topic-stats {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.bar-track {
  height: 6px;
  background: var(--color-border-light);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.bar-fill.weak {
  background: var(--color-danger);
}

.bar-fill.moderate {
  background: var(--color-warning);
}

.topic-accuracy {
  grid-column: 2;
  grid-row: 1 / 3;
  align-self: center;
  font-size: var(--text-base);
  color: var(--color-primary-text);
  text-align: right;
}

.topic-accuracy.weak {
  color: var(--color-danger);
}

/* Action Section */
.action-section {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
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

.action-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.action-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.action-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  flex-shrink: 0;
}

.action-content {
  min-width: 0;
  flex: 1;
}

.action-description {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  line-height: 1.4;
}

.action-topic {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.action-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: white;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-decoration: none;
  transition: background 0.15s ease;
}

.action-link:hover {
  background: var(--color-primary-hover);
}

/* Detail Entry */
.detail-entry {
  display: flex;
  justify-content: center;
}

/* History Section */
.history-section {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.history-loading,
.history-empty {
  min-height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  font-size: var(--text-sm);
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}

.history-item {
  min-height: 4.5rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  transition: all 0.15s ease;
}

.history-item:hover,
.history-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.history-item strong {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
}

.history-item span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.history-more {
  margin-top: var(--space-3);
  display: flex;
  justify-content: center;
}

/* Drawers */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: min(420px, 100%);
  background: var(--color-surface);
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.25s ease;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.drawer-header h2 {
  font-size: var(--text-lg);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.drawer-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.drawer-close:hover {
  background: var(--color-bg);
  color: var(--color-text-strong);
}

.drawer-body {
  flex: 1;
  overflow: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.detail-block h4 {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  margin-bottom: var(--space-3);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.detail-item {
  padding: var(--space-3);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.detail-item span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.detail-item strong {
  font-size: var(--text-base);
  color: var(--color-text-strong);
}

.detail-note {
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

.topic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.topic-tag {
  padding: var(--space-1) var(--space-2);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  border-radius: var(--radius-pill);
}

.history-full-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.history-full-item {
  min-height: 4rem;
  padding: var(--space-3);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: all 0.15s ease;
}

.history-full-item:hover,
.history-full-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.history-full-item strong {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
}

.history-full-item span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.history-full-item em {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-style: normal;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Responsive */
@media (max-width: 900px) {
  .analysis-section {
    grid-template-columns: 1fr;
  }

  .metrics-section {
    grid-template-columns: repeat(2, 1fr);
  }

  .strategy-highlights {
    grid-template-columns: repeat(2, 1fr);
  }

  .history-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
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

  .range-tabs {
    width: 100%;
    justify-content: stretch;
  }

  .range-tabs button {
    flex: 1;
  }

  .generate-btn {
    flex: 1;
    justify-content: center;
  }

  .generation-progress {
    grid-template-columns: repeat(2, 1fr);
  }

  .metrics-section {
    grid-template-columns: 1fr;
  }

  .strategy-highlights {
    grid-template-columns: 1fr;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }

  .topic-bar {
    grid-template-columns: 1fr;
    gap: var(--space-1);
  }

  .topic-accuracy {
    grid-column: 1;
    text-align: left;
  }
}
</style>
