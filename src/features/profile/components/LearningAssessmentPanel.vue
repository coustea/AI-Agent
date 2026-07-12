<template>
  <section class="assessment-panel">
    <div class="assessment-shell">
      <header class="workspace-header">
        <div class="title-block">
          <span>学习评估</span>
          <h1>学习记录如何改变当前辅导策略</h1>
          <p>{{ activeWindowLabel }}</p>
        </div>

        <div class="report-controls" aria-label="生成评估报告">
          <div class="range-tabs" role="group" aria-label="选择评估范围">
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
          <Button class="primary-action" :disabled="generating" @click="triggerReportGeneration">
            <Sparkles :size="16" />
            {{ generating ? '生成中' : '生成报告' }}
          </Button>
        </div>
      </header>

      <section v-if="generating" class="generation-strip" aria-label="生成进度">
        <span
          v-for="(step, index) in generationSteps"
          :key="step"
          :class="{ done: index < currentStepIdx, current: index === currentStepIdx }"
        >
          {{ step }}
        </span>
      </section>

      <section v-if="initialLoading" class="empty-state">
        <Clock3 :size="30" />
        <h2>正在加载学习评估</h2>
        <p>正在读取报告、历史记录和当前辅导策略。</p>
      </section>

      <section v-else-if="!activeReport" class="empty-state">
        <FileCheck :size="32" />
        <h2>暂无评估报告</h2>
        <p>生成后将展示学习事实、证据质量、Markdown 报告和最新辅导策略。</p>
      </section>

      <template v-else>
        <section v-if="activeReport.status === 'failed'" class="empty-state failed">
          <AlertCircle :size="28" />
          <h2>报告生成失败</h2>
          <p>{{ activeReport.failure_code || '未知内部错误' }}</p>
          <Button variant="outline" @click="triggerReportGeneration">重新生成</Button>
        </section>

        <section v-else-if="activeReport.status !== 'ready'" class="empty-state">
          <Route :size="30" />
          <h2>报告正在生成</h2>
          <p>{{ formatDateRange(activeReport.window_start, activeReport.window_end) }}</p>
        </section>

        <template v-else-if="facts">
          <section class="assessment-intel">
            <article class="intel-lead">
              <div>
                <span class="surface-label">当前结论</span>
                <h2>{{ verdict.title }}</h2>
                <p>{{ verdict.description }}</p>
              </div>
              <div class="window-chip">
                <CalendarDays :size="16" />
                <span>{{ activeReport.range_days }} 天</span>
                <strong>{{ formatDateRange(activeReport.window_start, activeReport.window_end) }}</strong>
              </div>
            </article>

            <article class="strategy-snapshot">
              <div class="snapshot-heading">
                <Compass :size="18" />
                <h2>当前辅导策略</h2>
              </div>
              <div v-if="guidanceStrategy" class="strategy-columns">
                <div>
                  <span>重点主题</span>
                  <strong>{{ guidanceStrategy.focus_topics?.length ? guidanceStrategy.focus_topics.join('、') : '暂无' }}</strong>
                </div>
                <div>
                  <span>建议时长</span>
                  <strong>{{ guidanceStrategy.recommended_session_minutes }} 分钟</strong>
                </div>
                <div>
                  <span>近期目标</span>
                  <strong>{{ guidanceStrategy.weekly_goal || '暂无' }}</strong>
                </div>
                <div>
                  <span>辅导风格</span>
                  <strong>{{ guidanceStrategy.tutoring_style || '暂无' }}</strong>
                </div>
              </div>
              <p v-else class="quiet-copy">生成第一份学习评估后将提供建议。</p>
            </article>
          </section>

          <section class="evidence-board" aria-label="学习事实快照">
            <article
              v-for="item in coreSignals"
              :key="item.label"
              class="signal-card"
            >
              <component :is="item.icon" :size="18" />
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.detail }}</small>
            </article>
          </section>

          <section class="analysis-layout">
            <article class="panel chart-panel trend-panel">
              <div class="panel-title">
                <Clock3 :size="17" />
                <h2>每日学习时长</h2>
                <span>{{ facts.activity.total_minutes }} 分钟</span>
              </div>
              <v-chart v-if="hasDailyData" class="chart chart-line" :option="lineOption" autoresize />
              <div v-else class="empty-chart">本窗口暂无学习会话时长。</div>
            </article>

            <article class="panel chart-panel module-panel">
              <div class="panel-title">
                <ChartColumn :size="17" />
                <h2>系统使用分布</h2>
                <span>{{ totalEvents }} 次事件</span>
              </div>
              <v-chart v-if="hasModuleData" class="chart chart-pie" :option="pieOption" autoresize />
              <div v-else class="empty-chart">本窗口暂无学习事件。</div>
            </article>
          </section>

          <section class="fact-layout">
            <article class="panel">
              <div class="panel-title">
                <Layers :size="17" />
                <h2>资源与路径</h2>
              </div>
              <div class="fact-matrix">
                <div v-for="item in resourcePathFacts" :key="item.label">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                  <small>{{ item.detail }}</small>
                </div>
              </div>
            </article>

            <article class="panel">
              <div class="panel-title">
                <Target :size="17" />
                <h2>主题掌握证据</h2>
              </div>
              <div v-if="topicRows.length" class="topic-grid">
                <button
                  v-for="topic in topicRows"
                  :key="topic.topic"
                  type="button"
                  class="topic-cell"
                >
                  <span>{{ topic.topic }}</span>
                  <strong>{{ topic.enough_evidence ? percentLabel(topic.accuracy) : '数据不足' }}</strong>
                  <small>{{ topic.correct }} / {{ topic.submitted }} 题</small>
                </button>
              </div>
              <div v-else class="empty-chart">本窗口暂无可评估的答题事实。</div>
            </article>
          </section>

          <section class="panel evidence-panel">
            <div class="panel-title">
              <ShieldCheck :size="17" />
              <h2>证据质量</h2>
            </div>
            <div class="evidence-strip">
              <div>
                <span>学习活动</span>
                <strong>{{ facts.data_quality.has_activity ? '已有记录' : '暂无记录' }}</strong>
              </div>
              <div>
                <span>涉及主题</span>
                <strong>{{ facts.topics.encountered.length }} 个</strong>
              </div>
              <div>
                <span>样本不足</span>
                <strong>{{ facts.data_quality.insufficient_topics.length }} 个</strong>
              </div>
              <div>
                <span>资源反馈</span>
                <strong>{{ facts.resource_usage.feedback.helpful + facts.resource_usage.feedback.not_helpful }} 条</strong>
              </div>
            </div>
            <div v-if="facts.topics.encountered.length" class="topic-tags">
              <span
                v-for="topic in facts.topics.encountered.slice(0, 12)"
                :key="topic"
              >
                {{ topic }}
              </span>
            </div>
            <p class="evidence-note">
              {{ evidenceNote }}
            </p>
          </section>

          <section class="report-layout">
            <article v-if="activeReport.report_markdown" class="panel report-panel">
              <div class="panel-title report-title">
                <BookOpenCheck :size="18" />
                <h2>Markdown 评估报告</h2>
              </div>
              <MarkdownRenderer :content="activeReport.report_markdown" />
            </article>

            <aside class="history-rail">
              <section class="panel history-panel">
                <div class="panel-title">
                  <Layers :size="18" />
                  <h2>历史报告</h2>
                  <span>{{ totalReports }} 份</span>
                </div>

                <div v-if="historyLoading" class="empty-chart compact-empty">正在加载历史报告。</div>
                <div v-else-if="reportsHistory.length === 0" class="empty-chart compact-empty">暂无历史报告。</div>
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
                    <em>{{ statusLabel(report.status) }} / #{{ report.id }}</em>
                  </button>
                </div>

                <div v-if="totalPages > 1" class="pagination">
                  <Button variant="ghost" size="sm" :disabled="currentPage <= 1" @click="changePage(currentPage - 1)">
                    <ChevronLeft :size="15" />
                    上一页
                  </Button>
                  <span>{{ currentPage }} / {{ totalPages }}</span>
                  <Button variant="ghost" size="sm" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">
                    下一页
                    <ChevronRight :size="15" />
                  </Button>
                </div>
              </section>
            </aside>
          </section>
        </template>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Button } from '@/components/ui/button'
import {
  Activity,
  AlertCircle,
  BookOpenCheck,
  CalendarDays,
  ChartColumn,
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
} from '@lucide/vue'
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
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'

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

const activeWindowLabel = computed(() => {
  if (!activeReport.value) return `准备生成近 ${selectedRange.value} 天评估`
  const range = formatDateRange(activeReport.value.window_start, activeReport.value.window_end)
  return range ? `${activeReport.value.range_days} 天窗口 / ${range}` : `${activeReport.value.range_days} 天窗口`
})

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

const verdict = computed(() => {
  const current = facts.value
  if (!current || !current.data_quality.has_activity) {
    return {
      title: '需要更多学习记录',
      description: '当前窗口还不足以形成稳定判断，建议先完成一次资源学习或练习。',
    }
  }

  if (current.practice.submitted > 0 && current.practice.accuracy < 0.6) {
    return {
      title: '练习正确率偏低',
      description: '报告会优先定位错题主题，并把下一阶段策略收敛到薄弱知识点。',
    }
  }

  if (current.activity.total_minutes < 30) {
    return {
      title: '学习时长偏少',
      description: '已有活动记录，但会话时长不足，策略会更关注短时高频复习。',
    }
  }

  return {
    title: '学习证据已形成',
    description: '系统已记录到学习时长、模块使用和练习表现，可用于生成辅导建议。',
  }
})

const coreSignals = computed(() => {
  const current = facts.value
  return [
    {
      icon: Clock3,
      label: '学习时长',
      value: `${current?.activity.total_minutes ?? 0} 分钟`,
      detail: `活跃 ${current?.activity.active_days ?? 0} 天`,
    },
    {
      icon: Activity,
      label: '系统事件',
      value: `${totalEvents.value} 次`,
      detail: moduleSummary.value,
    },
    {
      icon: ListChecks,
      label: '练习表现',
      value: current ? accuracyLabel(current.practice.accuracy, current.practice.submitted) : '无数据',
      detail: `${current?.practice.correct ?? 0} / ${current?.practice.submitted ?? 0} 题`,
    },
    {
      icon: Route,
      label: '路径推进',
      value: current ? percentLabel(current.learning_path.completion_rate) : '0%',
      detail: `完成 ${current?.learning_path.nodes_completed ?? 0} 个节点`,
    },
  ]
})

const moduleSummary = computed(() => {
  const modules = facts.value?.activity.module_distribution ?? []
  const top = [...modules].sort((a, b) => b.count - a.count)[0]
  if (!top) return '暂无事件'
  return `${MODULE_LABELS[top.module] || top.module}最多`
})

const resourcePathFacts = computed(() => {
  const current = facts.value
  return [
    {
      label: '生成资源',
      value: current?.resource_usage.generated ?? 0,
      detail: '来自资源生成事件',
    },
    {
      label: '浏览资源',
      value: current?.resource_usage.viewed ?? 0,
      detail: '来自资源查看事件',
    },
    {
      label: '完成资源',
      value: current?.resource_usage.completed ?? 0,
      detail: '来自完成事件',
    },
    {
      label: '路径完成率',
      value: current ? percentLabel(current.learning_path.completion_rate) : '0%',
      detail: `${current?.learning_path.nodes_completed ?? 0} / ${current?.learning_path.nodes_started ?? 0} 节点`,
    },
    {
      label: '有帮助反馈',
      value: current?.resource_usage.feedback.helpful ?? 0,
      detail: '资源反馈',
    },
    {
      label: '未帮助反馈',
      value: current?.resource_usage.feedback.not_helpful ?? 0,
      detail: '资源反馈',
    },
  ]
})

const evidenceNote = computed(() => {
  const insufficient = facts.value?.data_quality.insufficient_topics ?? []
  if (insufficient.length) return `数据不足：${insufficient.join('、')}`
  if (!facts.value?.data_quality.has_activity) return '当前窗口暂无活动记录，报告会标记为数据不足。'
  return '当前窗口没有被标记为样本不足的主题。'
})

const lineOption = computed(() => {
  const daily = facts.value?.activity.daily_minutes ?? []
  return {
    grid: { top: 18, right: 16, bottom: 30, left: 38 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#c7ece8',
      textStyle: { color: '#164e52', fontSize: 12 },
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
      symbolSize: 6,
      lineStyle: { color: '#0d9488', width: 2.5 },
      itemStyle: { color: '#ffffff', borderColor: '#0d9488', borderWidth: 2 },
      areaStyle: { color: 'rgba(13, 148, 136, 0.12)' },
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
      borderColor: '#c7ece8',
      textStyle: { color: '#164e52', fontSize: 12 },
    },
    legend: {
      bottom: 0,
      icon: 'circle',
      textStyle: { color: '#475569', fontSize: 11 },
    },
    series: [{
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['50%', '44%'],
      itemStyle: {
        borderRadius: 6,
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

function accuracyLabel(value: number, submitted: number): string {
  return submitted > 0 ? percentLabel(value) : '无数据'
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
.assessment-panel {
  height: 100%;
  min-height: 0;
  overflow: auto;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-text);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
}

.assessment-shell {
  width: 100%;
  margin: 0;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

h1,
h2,
p {
  margin: 0;
}

.workspace-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-5);
  padding: 0 0 var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.title-block {
  display: grid;
  gap: var(--space-2);
}

.title-block span,
.surface-label {
  color: var(--color-primary-text);
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
}

.title-block h1 {
  max-width: 42rem;
  color: var(--color-text-strong);
  font-size: clamp(1.3rem, 2vw, 1.8rem);
  line-height: var(--leading-tight);
  font-weight: var(--weight-extrabold);
  letter-spacing: 0;
}

.title-block p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.report-controls,
.panel-title,
.snapshot-heading,
.pagination,
.window-chip {
  display: flex;
  align-items: center;
}

.report-controls {
  justify-content: flex-end;
  gap: var(--space-3);
}

.range-tabs {
  display: inline-grid;
  grid-template-columns: repeat(3, minmax(4.5rem, 1fr));
  gap: var(--space-1);
  padding: var(--space-1);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.range-tabs button,
.history-list button,
.topic-cell {
  border: 0;
  background: transparent;
  cursor: pointer;
}

.range-tabs button {
  min-height: 2.25rem;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  transition: var(--btn-transition);
}

.range-tabs button.active {
  color: var(--color-text-strong);
  background: var(--color-primary-soft);
  box-shadow: inset 0 0 0 1px var(--color-primary-border);
}

.primary-action {
  min-height: 2.45rem;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-text-strong);
  font-weight: var(--weight-extrabold);
  gap: var(--space-2);
  white-space: nowrap;
  transition: var(--btn-transition);
}

.primary-action:hover {
  background: var(--color-primary-hover);
}

.generation-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2);
}

.generation-strip span {
  min-height: 2.25rem;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.generation-strip span.done {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.generation-strip span.current {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.empty-state,
.panel,
.signal-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
}

.empty-state {
  min-height: 13rem;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--space-3);
  color: var(--color-text-secondary);
}

.empty-state h2 {
  color: var(--color-text-strong);
  font-size: var(--text-lg);
  letter-spacing: 0;
}

.empty-state.failed {
  color: var(--color-danger);
}

.assessment-intel,
.evidence-board,
.analysis-layout,
.fact-layout,
.report-layout,
.evidence-strip {
  display: grid;
  gap: var(--space-5);
}

.assessment-intel {
  grid-template-columns: minmax(0, 1.08fr) minmax(20rem, 0.92fr);
  align-items: stretch;
}

.intel-lead,
.strategy-snapshot {
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.intel-lead {
  min-height: 11rem;
  padding: var(--space-5);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, auto);
  gap: var(--space-6);
  align-items: end;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--color-primary-soft) 52%, var(--color-surface)), var(--color-surface) 62%);
}

.intel-lead h2 {
  margin-top: var(--space-3);
  color: var(--color-text-strong);
  font-size: clamp(1.25rem, 2vw, 1.75rem);
  line-height: var(--leading-tight);
  letter-spacing: 0;
}

.intel-lead p {
  max-width: 42rem;
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

.window-chip {
  align-self: end;
  justify-content: center;
  flex-direction: column;
  min-height: 7.5rem;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-primary-border);
  background: color-mix(in srgb, var(--color-surface) 80%, var(--color-primary-soft));
  text-align: center;
  color: var(--color-primary-text);
  gap: var(--space-2);
}

.window-chip span {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.window-chip strong {
  color: var(--color-text-strong);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.strategy-snapshot {
  padding: var(--space-5);
}

.snapshot-heading,
.panel-title {
  gap: var(--space-2);
  color: var(--color-primary-text);
  margin-bottom: var(--space-4);
}

.snapshot-heading h2,
.panel-title h2 {
  color: var(--color-text-strong);
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  letter-spacing: 0;
}

.panel-title span {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.strategy-columns,
.fact-matrix {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.strategy-columns div,
.fact-matrix div {
  min-height: 6rem;
  padding: var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-surface) 86%, var(--color-primary-soft));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--space-2);
}

.strategy-columns span,
.fact-matrix span,
.signal-card span,
.evidence-strip span {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.strategy-columns strong,
.fact-matrix strong,
.signal-card strong,
.evidence-strip strong {
  color: var(--color-text-strong);
  font-size: var(--text-md);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}

.fact-matrix small,
.signal-card small {
  color: var(--color-text-faint);
  font-size: var(--text-xs);
}

.quiet-copy {
  min-height: 8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  text-align: center;
}

.evidence-board {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.signal-card {
  min-height: 9rem;
  padding: var(--space-5);
  display: grid;
  gap: var(--space-2);
  align-content: space-between;
  color: var(--color-primary-text);
}

.signal-card strong {
  font-size: 1.75rem;
  line-height: 1;
}

.analysis-layout {
  grid-template-columns: minmax(0, 1.35fr) minmax(20rem, 0.65fr);
}

.fact-layout {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel {
  padding: var(--space-6);
}

.chart-panel {
  min-height: 20rem;
}

.chart {
  width: 100%;
}

.chart-line,
.chart-pie {
  height: 16rem;
}

.empty-chart {
  min-height: 7rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  font-size: var(--text-sm);
  text-align: center;
}

.compact-empty {
  min-height: 4.75rem;
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
}

.topic-cell {
  min-height: 6rem;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  text-align: left;
  display: grid;
  gap: var(--space-2);
  color: var(--color-text-strong);
  background: var(--color-surface);
  transition: var(--btn-transition);
}

.topic-cell:hover {
  border-color: var(--color-primary-border);
  background: var(--color-primary-soft);
}

.topic-cell span {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  overflow-wrap: anywhere;
}

.topic-cell strong {
  color: var(--color-primary-text);
  font-size: var(--text-lg);
}

.topic-cell small {
  color: var(--color-text-faint);
  font-size: var(--text-xs);
}

.evidence-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.evidence-strip {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.evidence-strip div {
  min-height: 5.75rem;
  padding: var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-surface) 88%, var(--color-primary-soft));
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.topic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.topic-tags span {
  padding: var(--space-1) var(--space-2\.5);
  border-radius: var(--radius-pill);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.evidence-note {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}

.report-layout {
  grid-template-columns: minmax(0, 1fr) minmax(21rem, 25rem);
  align-items: start;
}

.report-panel :deep(.markdown-renderer) {
  color: var(--color-text);
}

.history-rail {
  position: sticky;
  top: var(--space-4);
}

.history-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}

.history-list button {
  min-height: 5.25rem;
  padding: var(--space-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  text-align: left;
  display: grid;
  gap: var(--space-1\.5);
  color: var(--color-text-strong);
  background: var(--color-surface);
  transition: var(--btn-transition);
}

.history-list button:hover,
.history-list button.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.history-list strong {
  font-size: var(--text-sm);
}

.history-list span,
.history-list em {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-style: normal;
}

.pagination {
  justify-content: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

@media (max-width: 1180px) {
  .workspace-header,
  .assessment-intel,
  .analysis-layout,
  .report-layout {
    grid-template-columns: 1fr;
  }

  .report-controls {
    justify-content: flex-start;
  }

  .history-rail {
    position: static;
  }
}

@media (max-width: 900px) {
  .evidence-board,
  .evidence-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .fact-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .assessment-shell {
    padding: var(--space-4);
  }

  .report-controls,
  .intel-lead {
    grid-template-columns: 1fr;
  }

  .report-controls {
    align-items: stretch;
    flex-direction: column;
  }

  .range-tabs {
    width: 100%;
  }

  .generation-strip,
  .evidence-board,
  .strategy-columns,
  .fact-matrix,
  .topic-grid,
  .evidence-strip {
    grid-template-columns: 1fr;
  }

  .signal-card,
  .window-chip {
    min-height: auto;
  }
}
</style>
