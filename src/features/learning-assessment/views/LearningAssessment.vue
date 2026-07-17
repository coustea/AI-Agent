<template>
  <main class="assessment-page">
    <header class="page-header">
      <div class="header-copy">
        <span class="eyebrow">LEARNING REVIEW</span>
        <h1>学习评估</h1>
        <p>用学习趋势、模块投入和阶段结论，帮助你快速判断下一步该学什么。</p>
      </div>

      <div class="header-actions">
        <Button
          class="generate-button"
          :disabled="generating"
          @click="triggerAssessmentGeneration"
        >
          <Sparkles :size="16" />
          {{ generating ? '生成中' : '重新评估' }}
        </Button>
      </div>
    </header>

    <section
      v-if="generating"
      class="generation-progress"
      aria-label="评估生成进度"
    >
      <div
        v-for="(step, index) in generationSteps"
        :key="step"
        class="progress-step"
        :class="{
          done: index < currentStepIdx,
          current: index === currentStepIdx,
        }"
      >
        <span class="step-index">
          <CheckCircle2 v-if="index < currentStepIdx" :size="15" />
          <template v-else>{{ index + 1 }}</template>
        </span>
        <span>{{ step }}</span>
      </div>
    </section>

    <section v-if="initialLoading" class="state-panel">
      <div class="loading-spinner" />
      <h2>正在整理学习记录</h2>
      <p>系统正在加载近期学习趋势、资源使用和评估结果。</p>
    </section>

    <section
      v-else-if="activeAssessment?.status === 'failed'"
      class="state-panel error-panel"
    >
      <AlertCircle :size="28" />
      <h2>评估生成失败</h2>
      <p>{{ activeAssessment.failure_code || '评估服务暂时不可用，请稍后重试。' }}</p>
      <Button variant="outline" @click="triggerAssessmentGeneration">
        <RefreshCw :size="15" />
        重新生成
      </Button>
    </section>

    <section
      v-else-if="activeAssessment?.status === 'generating'"
      class="state-panel"
    >
      <div class="loading-spinner" />
      <h2>评估正在生成</h2>
      <p>模型正在汇总学习证据并生成阶段结论。</p>
    </section>

    <template v-else>
      <section
        v-if="!activeAssessment && !hasLearningEvidence"
        class="empty-guide"
      >
        <div class="empty-visual">
          <Compass :size="34" />
        </div>

        <div class="empty-copy">
          <span class="section-kicker">暂无学习证据</span>
          <h2>先完成一次真实学习，再生成评估</h2>
          <p>
            系统需要从辅导对话、资源学习和练习记录中提取事实，才能给出可信的学习结论。
          </p>
        </div>

        <div class="guide-actions">
          <button type="button" @click="navigateTo('/tutor')">
            <MessageCircle :size="19" />
            <span>
              <strong>智能辅导</strong>
              <small>进行一次课程问答</small>
            </span>
          </button>

          <button type="button" @click="navigateTo('/resource-generator')">
            <Lightbulb :size="19" />
            <span>
              <strong>资源生成</strong>
              <small>生成并学习课程资源</small>
            </span>
          </button>

          <button type="button" @click="navigateTo('/question-bank')">
            <BookOpen :size="19" />
            <span>
              <strong>题库练习</strong>
              <small>完成一次巩固练习</small>
            </span>
          </button>
        </div>
      </section>

      <section
        v-else-if="!activeAssessment && recentAssessments.length === 0 && dashboardData"
        class="first-report-guide"
      >
        <div class="first-report-copy">
          <span class="section-kicker">学习事实已形成</span>
          <h2>生成第一份学习效果评估</h2>
          <p>
            当前已经积累 {{ eventCount }} 条学习事件。生成评估后，系统会给出阶段结论、重点主题和下一步学习计划。
          </p>
          <Button
            class="generate-button large"
            :disabled="generating"
            @click="triggerAssessmentGeneration"
          >
            <Sparkles :size="17" />
            生成评估报告
          </Button>
        </div>

        <div class="first-report-chart">
          <div class="preview-header">
            <span>近期学习趋势</span>
            <strong>{{ totalStudyMinutes }} 分钟</strong>
          </div>
          <div class="preview-chart-box">
            <v-chart class="chart" :option="lineOption" autoresize />
          </div>
        </div>
      </section>

      <template v-else-if="dashboardData">
        <section v-if="recentAssessments.length" class="report-history-bar">
          <div class="current-report-mark">
            <div class="history-icon-box">
              <FileClock :size="18" />
            </div>
            <div>
              <span>{{ viewingHistorical ? '正在查看历史报告' : '当前报告' }}</span>
              <strong>{{ currentReportTitle }}</strong>
            </div>
          </div>

          <div class="recent-report-list" aria-label="最近评估">
            <button
              v-for="(item, index) in recentAssessments.slice(0, 4)"
              :key="item.id"
              type="button"
              :class="{
                active:
                  (!viewingHistorical && !!activeAssessment && index === 0) ||
                  (viewingHistorical && activeAssessment?.id === item.id),
              }"
              @click="openRecentAssessment(item, index)"
            >
              <strong>{{ index === 0 ? '最新' : '历史' }}</strong>
              <span>{{ formatCompactDate(item.created_at) }}</span>
            </button>
          </div>

          <button type="button" class="history-entry" @click="openHistoryDrawer">
            <History :size="16" />
            历史报告
            <span>{{ totalAssessments }}</span>
          </button>
        </section>

        <section class="report-overview">
          <article class="overview-copy">
            <div class="overview-heading">
              <div>
                <span class="section-kicker">阶段结论</span>
                <h2>本期学习表现</h2>
              </div>

              <span class="date-badge">
                <CalendarDays :size="14" />
                {{ displayDateRange }}
              </span>
            </div>

            <p class="assessment-text">
              {{ displayConclusion }}
            </p>

            <div class="overview-footnote">
              <Target :size="15" />
              <span>{{ strategyReasonText }}</span>
            </div>
          </article>

          <div class="metric-grid">
            <article class="metric-item">
              <span class="metric-icon"><Clock3 :size="17" /></span>
              <div>
                <strong>{{ totalStudyMinutes }}</strong>
                <span>学习分钟</span>
              </div>
            </article>

            <article class="metric-item">
              <span class="metric-icon"><CalendarDays :size="17" /></span>
              <div>
                <strong>{{ activeStudyDays }}</strong>
                <span>活跃天数</span>
              </div>
            </article>

            <article class="metric-item">
              <span class="metric-icon"><Activity :size="17" /></span>
              <div>
                <strong>{{ averageDailyMinutes }}</strong>
                <span>日均分钟</span>
              </div>
            </article>

            <article class="metric-item metric-topic">
              <span class="metric-icon"><Layers3 :size="17" /></span>
              <div>
                <strong>{{ topModuleName }}</strong>
                <span>投入最多模块</span>
              </div>
            </article>
          </div>
        </section>

        <section class="visual-analysis">
          <article class="trend-panel analysis-panel">
            <header class="panel-heading">
              <div>
                <span class="section-kicker">学习趋势</span>
                <h3>每日学习时长</h3>
              </div>
              <p>{{ trendInsight }}</p>
            </header>

            <div class="trend-chart-box">
              <v-chart class="chart" :option="lineOption" autoresize />
            </div>
          </article>

          <article class="module-panel analysis-panel">
            <header class="panel-heading compact">
              <div>
                <span class="section-kicker">投入结构</span>
                <h3>模块时长分布</h3>
              </div>
            </header>

            <div class="module-chart-box">
              <v-chart class="chart" :option="pieOption" autoresize />
            </div>

            <div v-if="moduleRanking.length" class="module-ranking">
              <div
                v-for="module in moduleRanking"
                :key="module.name"
                class="module-row"
              >
                <span
                  class="module-dot"
                  :style="{ backgroundColor: module.color }"
                />
                <span class="module-name">{{ module.name }}</span>
                <strong>{{ module.minutes }} 分钟</strong>
                <em>{{ module.percent }}%</em>
              </div>
            </div>

            <p v-else class="module-empty">当前周期暂无模块学习时长。</p>
          </article>
        </section>

        <section class="strategy-layout">
          <article class="strategy-panel">
            <header class="section-heading">
              <div>
                <span class="section-kicker">自适应策略</span>
                <h3>下一阶段应如何调整</h3>
              </div>
              <BarChart3 :size="20" />
            </header>

            <div class="strategy-facts">
              <div>
                <span>重点主题</span>
                <strong>{{ focusTopicsText }}</strong>
              </div>
              <div>
                <span>建议时长</span>
                <strong>{{ recommendedMinutesText }}</strong>
              </div>
              <div>
                <span>辅导方式</span>
                <strong>{{ tutoringStyleText }}</strong>
              </div>
            </div>
          </article>

          <article class="plan-panel">
            <header class="section-heading">
              <div>
                <span class="section-kicker">行动计划</span>
                <h3>下一阶段学习任务</h3>
              </div>
              <Compass :size="20" />
            </header>

            <div v-if="actionPlan.length" class="plan-list">
              <div
                v-for="(action, index) in actionPlan"
                :key="`${action.topic}-${index}`"
                class="plan-item"
              >
                <span class="plan-index">{{ String(index + 1).padStart(2, '0') }}</span>
                <div>
                  <strong>{{ action.topic || `学习任务 ${index + 1}` }}</strong>
                  <p>{{ action.description }}</p>
                </div>
              </div>
            </div>

            <p v-else class="plan-empty">当前评估暂未生成具体行动计划。</p>
          </article>
        </section>
      </template>
    </template>

    <Teleport to="body">
      <div
        v-if="showHistoryDrawer"
        class="drawer-overlay"
        @click.self="showHistoryDrawer = false"
      >
        <aside class="drawer-panel" aria-label="历史评估报告">
          <header class="drawer-header">
            <div>
              <span>ASSESSMENT HISTORY</span>
              <h2>历史评估</h2>
              <p>按生成时间查看过去的学习结论。</p>
            </div>
            <button
              type="button"
              class="drawer-close"
              aria-label="关闭历史评估"
              @click="showHistoryDrawer = false"
            >
              <X :size="19" />
            </button>
          </header>

          <div class="drawer-body">
            <div v-if="historyLoading" class="drawer-loading">
              <div class="loading-spinner small" />
              <span>正在加载历史报告</span>
            </div>

            <div v-else-if="historyItems.length" class="history-full-list">
              <button
                v-for="item in historyItems"
                :key="item.id"
                type="button"
                class="history-full-item"
                :class="[
                  { active: activeAssessment?.id === item.id },
                  `status-${item.status}`,
                ]"
                @click="selectAssessmentFromDrawer(item)"
              >
                <span class="history-status-dot" />

                <div class="history-item-main">
                  <div class="history-item-heading">
                    <strong>学习评估</strong>
                    <span>{{ statusLabel(item.status) }}</span>
                  </div>
                  <time>{{ formatDateTime(item.created_at) }}</time>
                </div>

                <ChevronRight :size="16" />
              </button>
            </div>

            <div v-else class="drawer-empty">暂无历史评估报告。</div>
          </div>

          <footer v-if="totalPages > 1" class="drawer-pagination">
            <button
              type="button"
              :disabled="currentPage <= 1 || historyLoading"
              @click="changePage(currentPage - 1)"
            >
              <ChevronLeft :size="15" />
              上一页
            </button>

            <span>{{ currentPage }} / {{ totalPages }}</span>

            <button
              type="button"
              :disabled="currentPage >= totalPages || historyLoading"
              @click="changePage(currentPage + 1)"
            >
              下一页
              <ChevronRight :size="15" />
            </button>
          </footer>
        </aside>
      </div>
    </Teleport>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import {
  Activity,
  AlertCircle,
  BarChart3,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Compass,
  FileClock,
  History,
  Layers3,
  Lightbulb,
  MessageCircle,
  RefreshCw,
  Sparkles,
  Target,
  X,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components'
import {
  generateAssessment,
  getLatestAssessment,
  getAssessmentDetail,
  getAssessmentsHistory,
  getAssessmentDashboard,
} from '@/features/learning-assessment/api/assessment'
import { getDashboard } from '@/features/evaluation/api/evaluation'
import type {
  ActionPlanItem,
  GuidanceStrategy,
  LearningAssessment,
} from '@/features/learning-assessment/model/assessment'
import type { DashboardData } from '@/features/evaluation/api/evaluation'
import { normalizeGuidanceStrategy } from '@/features/learning-assessment/model/assessment'

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
])

type AssessmentSummary = Omit<LearningAssessment, 'assessment'>

interface ModuleRankItem {
  name: string
  minutes: number
  percent: number
  color: string
}

const recentAssessments = ref<AssessmentSummary[]>([])
const historyItems = ref<AssessmentSummary[]>([])
const activeAssessment = ref<LearningAssessment | null>(null)
const dashboardData = ref<DashboardData | null>(null)
const guidanceStrategy = ref<GuidanceStrategy | null>(null)
const generating = ref(false)
const historyLoading = ref(false)
const initialLoading = ref(true)
const viewingHistorical = ref(false)
const currentPage = ref(1)
const totalAssessments = ref(0)
const totalPages = ref(1)
const currentStepIdx = ref(0)
const showHistoryDrawer = ref(false)

const historyPageSize = 8
const generationSteps = [
  '聚合学习事实',
  '校验证据质量',
  '生成评估结论',
  '更新辅导策略',
]

const PIE_COLORS = [
  '#287f78',
  '#5573c8',
  '#d58a43',
  '#7c6bc3',
  '#4e9a74',
  '#c65f70',
]

const router = useRouter()

function navigateTo(path: string): void {
  void router.push(path)
}

const actionPlan = computed<ActionPlanItem[]>(() => {
  return guidanceStrategy.value?.action_plan ?? []
})

const hasLearningEvidence = computed(() => {
  return (dashboardData.value?.evaluation_summary?.event_count ?? 0) > 0
})

const eventCount = computed(() => {
  return dashboardData.value?.evaluation_summary?.event_count ?? 0
})

const dailyBreakdown = computed(() => {
  return dashboardData.value?.time_stats?.daily_breakdown ?? []
})

const moduleBreakdown = computed(() => {
  return dashboardData.value?.module_time_breakdown ?? []
})

const totalStudyMinutes = computed(() => {
  const totalSeconds = dailyBreakdown.value.reduce(
    (sum, item) => sum + Number(item.seconds || 0),
    0,
  )
  return Math.round(totalSeconds / 60)
})

const activeStudyDays = computed(() => {
  return dailyBreakdown.value.filter(item => Number(item.seconds || 0) > 0).length
})

const averageDailyMinutes = computed(() => {
  if (activeStudyDays.value === 0) return 0
  return Math.round(totalStudyMinutes.value / activeStudyDays.value)
})

const topModuleName = computed(() => {
  const top = [...moduleBreakdown.value]
    .filter(item => Number(item.seconds || 0) > 0)
    .sort((a, b) => Number(b.seconds || 0) - Number(a.seconds || 0))[0]
  return top?.module || '暂无'
})

const moduleRanking = computed<ModuleRankItem[]>(() => {
  const positiveItems = [...moduleBreakdown.value]
    .filter(item => Number(item.seconds || 0) > 0)
    .sort((a, b) => Number(b.seconds || 0) - Number(a.seconds || 0))

  const totalSeconds = positiveItems.reduce(
    (sum, item) => sum + Number(item.seconds || 0),
    0,
  )

  return positiveItems.slice(0, 5).map((item, index) => ({
    name: item.module,
    minutes: Math.round(Number(item.seconds || 0) / 60),
    percent:
      totalSeconds > 0
        ? Math.round((Number(item.seconds || 0) / totalSeconds) * 100)
        : 0,
    color: PIE_COLORS[index % PIE_COLORS.length],
  }))
})

const currentReportTitle = computed(() => {
  if (!activeAssessment.value) {
    return '学习评估'
  }

  return viewingHistorical.value ? '历史评估' : '最新评估'
})

const displayDateRange = computed(() => {
  const windowData = dashboardData.value?.window
  if (!windowData) return '7 天窗口'
  return formatDateRange(windowData.start, windowData.end)
})

const displayConclusion = computed(() => {
  return (
    activeAssessment.value?.assessment ||
    guidanceStrategy.value?.conclusion ||
    defaultConclusion.value
  )
})

const defaultConclusion = computed(() => {
  if (!hasLearningEvidence.value) {
    return '当前时间窗口暂无学习活动记录，建议先完成一次资源学习、辅导对话或练习。'
  }

  return `当前窗口共记录 ${eventCount.value} 条学习事件，系统已经形成基础学习证据，可结合下方趋势和模块投入安排下一阶段学习。`
})

const strategyReasonText = computed(() => {
  return (
    guidanceStrategy.value?.reason ||
    '策略依据来自当前时间窗口内的学习时长、模块投入和练习行为。'
  )
})

const focusTopicsText = computed(() => {
  const topics = guidanceStrategy.value?.focus_topics ?? []
  return topics.length ? topics.join('、') : '保持当前重点课程'
})

const recommendedMinutesText = computed(() => {
  const minutes = guidanceStrategy.value?.recommended_session_minutes
  return minutes ? `${minutes} 分钟 / 次` : '30 分钟 / 次'
})

const tutoringStyleText = computed(() => {
  return guidanceStrategy.value?.tutoring_style || '讲解与练习结合'
})

const trendInsight = computed(() => {
  const validDays = dailyBreakdown.value.filter(
    item => Number(item.seconds || 0) > 0,
  )

  if (!validDays.length) {
    return '当前周期暂无学习时长，完成学习后这里会展示趋势变化。'
  }

  const peak = [...validDays].sort(
    (a, b) => Number(b.seconds || 0) - Number(a.seconds || 0),
  )[0]

  return `本周期累计 ${totalStudyMinutes.value} 分钟，${formatShortDate(peak.date)} 达到峰值 ${Math.round(Number(peak.seconds || 0) / 60)} 分钟。`
})

const lineOption = computed(() => {
  const daily = dailyBreakdown.value

  return {
    animationDuration: 500,
    grid: { top: 32, right: 18, bottom: 30, left: 42 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.98)',
      borderColor: '#dce3ea',
      borderWidth: 1,
      padding: [9, 11],
      textStyle: { color: '#253449', fontSize: 12 },
      formatter: '{b}<br/>学习时长：{c} 分钟',
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: daily.map(item => formatShortDate(item.date)),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dfe5ec' } },
      axisLabel: { color: '#7d8999', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: '#8a95a4', fontSize: 11 },
      splitLine: { lineStyle: { color: '#edf1f5', type: 'dashed' } },
    },
    series: [
      {
        data: daily.map(item => Number((Number(item.seconds || 0) / 60).toFixed(1))),
        type: 'line',
        smooth: 0.35,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: daily.length <= 14,
        lineStyle: { color: '#287f78', width: 3 },
        itemStyle: {
          color: '#ffffff',
          borderColor: '#287f78',
          borderWidth: 2,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(40,127,120,0.22)' },
              { offset: 1, color: 'rgba(40,127,120,0.01)' },
            ],
          },
        },
      },
    ],
  }
})

const pieOption = computed(() => {
  const data = moduleRanking.value.length
    ? moduleRanking.value.map(item => ({
        name: item.name,
        value: item.minutes,
        itemStyle: { color: item.color },
      }))
    : [
        {
          name: '暂无数据',
          value: 1,
          itemStyle: { color: '#edf1f4' },
        },
      ]

  return {
    animationDuration: 500,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.98)',
      borderColor: '#dce3ea',
      borderWidth: 1,
      textStyle: { color: '#253449', fontSize: 12 },
      formatter: moduleRanking.value.length
        ? '{b}<br/>学习时长：{c} 分钟（{d}%）'
        : '暂无模块学习数据',
    },
    title: {
      text: `${totalStudyMinutes.value}`,
      subtext: '总分钟',
      left: 'center',
      top: '39%',
      textAlign: 'center',
      textStyle: {
        color: '#223148',
        fontSize: 23,
        fontWeight: 750,
      },
      subtextStyle: {
        color: '#8a95a4',
        fontSize: 10,
        lineHeight: 18,
      },
    },
    series: [
      {
        type: 'pie',
        radius: ['62%', '84%'],
        center: ['50%', '50%'],
        minAngle: 4,
        avoidLabelOverlap: true,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 3,
        },
        emphasis: {
          scaleSize: 5,
        },
        data,
      },
    ],
  }
})

async function loadDashboard(): Promise<void> {
  try {
    const response = await getDashboard(7)
    dashboardData.value = response.data.data
    syncGuidanceStrategy()
  } catch (error) {
    console.error('加载学习评估看板失败', error)
    toast.error('学习评估数据加载失败')
  }
}

function syncGuidanceStrategy(): void {
  const rawStrategy = dashboardData.value?.guidance_strategy
  guidanceStrategy.value = rawStrategy
    ? normalizeGuidanceStrategy(rawStrategy as Partial<GuidanceStrategy>)
    : null
}

async function loadRecentAssessments(): Promise<void> {
  try {
    const response = await getAssessmentsHistory(1, 5)
    recentAssessments.value = response.data.data.items
    totalAssessments.value = response.data.data.total
  } catch (error) {
    console.error('加载最近评估失败', error)
  }
}

async function loadHistoryPage(page = 1): Promise<void> {
  historyLoading.value = true

  try {
    const response = await getAssessmentsHistory(page, historyPageSize)
    historyItems.value = response.data.data.items
    totalAssessments.value = response.data.data.total
    totalPages.value = Math.max(
      1,
      Math.ceil(response.data.data.total / historyPageSize),
    )
    currentPage.value = page
  } catch (error) {
    console.error('加载历史评估失败', error)
    toast.error('历史评估加载失败')
  } finally {
    historyLoading.value = false
  }
}

async function openHistoryDrawer(): Promise<void> {
  showHistoryDrawer.value = true
  await loadHistoryPage(1)
}

async function openRecentAssessment(
  item: AssessmentSummary,
  index: number,
): Promise<void> {
  if (index === 0) {
    await returnToLatest()
    return
  }

  await selectAssessment(item)
}

async function selectAssessment(item: AssessmentSummary): Promise<void> {
  try {
    const [detailResponse, dashboardResponse] = await Promise.all([
      getAssessmentDetail(item.id),
      getAssessmentDashboard(item.id),
    ])

    activeAssessment.value = detailResponse.data.data
    dashboardData.value = dashboardResponse.data.data
    viewingHistorical.value = true
    syncGuidanceStrategy()
  } catch (error) {
    console.error('加载评估详情失败', error)
    toast.error('评估详情加载失败')
  }
}

async function selectAssessmentFromDrawer(item: AssessmentSummary): Promise<void> {
  await selectAssessment(item)
  showHistoryDrawer.value = false
}

async function returnToLatest(): Promise<void> {
  viewingHistorical.value = false

  try {
    const response = await getLatestAssessment()
    activeAssessment.value = response.data.data ?? null

    await loadDashboard()
  } catch (error) {
    console.error('获取最新评估失败', error)
    toast.error('最新评估加载失败')
  }
}

async function triggerAssessmentGeneration(): Promise<void> {
  generating.value = true
  currentStepIdx.value = 0

  const progressTimer = window.setInterval(() => {
    currentStepIdx.value = Math.min(
      currentStepIdx.value + 1,
      generationSteps.length - 1,
    )
  }, 1100)

  try {
    const response = await generateAssessment()
    activeAssessment.value = response.data.data
    viewingHistorical.value = false

    const result = await waitForAssessmentResult()

    if (result === 'ready') {
      toast.success('学习评估已生成')
      await Promise.all([loadRecentAssessments(), loadDashboard()])
    } else if (result === 'failed') {
      toast.error('评估生成失败')
    } else {
      toast.warning('评估生成时间较长，请稍后刷新查看')
    }
  } catch (error: any) {
    if (error?.response?.status === 409) {
      toast.warning('已有评估任务正在生成')
    } else {
      console.error('生成评估失败', error)
      toast.error('生成评估失败')
    }
  } finally {
    window.clearInterval(progressTimer)
    generating.value = false
    currentStepIdx.value = 0
  }
}

async function waitForAssessmentResult(): Promise<'ready' | 'failed' | 'timeout'> {
  const maxPolls = 60

  for (let index = 0; index < maxPolls; index += 1) {
    await delay(1000)

    try {
      const response = await getLatestAssessment()
      const latest = response.data.data

      if (!latest) continue

      activeAssessment.value = latest

      if (latest.status === 'ready') return 'ready'
      if (latest.status === 'failed') return 'failed'
    } catch {
      // 单次轮询失败时继续等待。
    }
  }

  return 'timeout'
}

async function pollAssessmentStatus(): Promise<void> {
  generating.value = true
  currentStepIdx.value = 1

  const result = await waitForAssessmentResult()

  generating.value = false
  currentStepIdx.value = 0

  if (result === 'ready') {
    toast.success('学习评估已生成')
    await Promise.all([loadRecentAssessments(), loadDashboard()])
  } else if (result === 'failed') {
    toast.error('评估生成失败')
  } else {
    toast.warning('评估生成时间较长，请稍后刷新查看')
  }
}

function delay(milliseconds: number): Promise<void> {
  return new Promise(resolve => window.setTimeout(resolve, milliseconds))
}

function changePage(page: number): void {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  void loadHistoryPage(page)
}

function statusLabel(status: LearningAssessment['status']): string {
  if (status === 'ready') return '已完成'
  if (status === 'generating') return '生成中'
  return '生成失败'
}

function formatShortDate(value: string): string {
  const parts = value.split('-')
  return parts.length === 3 ? `${parts[1]}-${parts[2]}` : value
}

function formatCompactDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'
  return `${date.getMonth() + 1}/${date.getDate()}`
}

function formatDateRange(start: string, end: string): string {
  if (!start || !end) return '时间范围未知'

  const startDate = new Date(start)
  const endDate = new Date(end)

  if (
    Number.isNaN(startDate.getTime()) ||
    Number.isNaN(endDate.getTime())
  ) {
    return '时间范围未知'
  }

  return `${startDate.getMonth() + 1}月${startDate.getDate()}日 - ${endDate.getMonth() + 1}月${endDate.getDate()}日`
}

function formatDateTime(value: string): string {
  if (!value) return '时间未知'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间未知'

  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')

  return `${month}月${day}日 ${hours}:${minutes}`
}

onMounted(async () => {
  initialLoading.value = true

  await Promise.all([loadRecentAssessments(), loadDashboard()])

  try {
    const response = await getLatestAssessment()
    activeAssessment.value = response.data.data ?? null

    if (activeAssessment.value?.status === 'generating') {
      void pollAssessmentStatus()
    } else if (!activeAssessment.value && recentAssessments.value[0]) {
      await selectAssessment(recentAssessments.value[0])
    }
  } catch (error) {
    console.error('获取最新评估失败', error)
  } finally {
    initialLoading.value = false
  }
})
</script>

<style scoped>
.assessment-page,
.assessment-page * {
  box-sizing: border-box;
}

.assessment-page {
  width: min(1180px, 100%);
  margin: 0 auto;
  padding: 28px 28px 64px;
  color: var(--color-text-strong, #182235);
}

h1,
h2,
h3,
p {
  margin: 0;
}

button {
  font: inherit;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--color-border-light, #e7ebf0);
}

.header-copy {
  min-width: 0;
}

.eyebrow,
.section-kicker {
  display: block;
  color: var(--color-primary, #287f78);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  line-height: 1.4;
}

.header-copy h1 {
  margin-top: 5px;
  color: var(--color-text-strong, #182235);
  font-size: 28px;
  font-weight: 850;
  letter-spacing: -0.035em;
  line-height: 1.2;
}

.header-copy p {
  margin-top: 7px;
  color: var(--color-text-secondary, #6f7b8d);
  font-size: 13px;
  line-height: 1.6;
}

.header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
}

.generate-button {
  min-height: 38px;
  gap: 7px;
  border: 0 !important;
  border-radius: 7px !important;
  color: #ffffff !important;
  background: var(--color-primary, #287f78) !important;
  font-size: 12px;
  font-weight: 800 !important;
  box-shadow: none !important;
}

.generate-button:hover {
  background: #206e68 !important;
}

.generate-button:disabled {
  color: #9aa4af !important;
  background: #e5e9ed !important;
}

.generate-button.large {
  min-height: 42px;
  padding: 0 18px;
  margin-top: 22px;
}

.generation-progress {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.progress-step {
  position: relative;
  display: flex;
  min-height: 44px;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  overflow: hidden;
  border: 1px solid var(--color-border, #dce3ea);
  border-radius: 8px;
  color: var(--color-text-muted, #8994a3);
  background: #ffffff;
  font-size: 11px;
  font-weight: 700;
}

.step-index {
  display: grid;
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  place-items: center;
  border-radius: 50%;
  color: #758194;
  background: #f0f3f6;
  font-size: 10px;
}

.progress-step.done {
  border-color: #cce3de;
  color: #286f68;
  background: #f4faf8;
}

.progress-step.done .step-index,
.progress-step.current .step-index {
  color: #ffffff;
  background: var(--color-primary, #287f78);
}

.progress-step.current {
  border-color: var(--color-primary, #287f78);
  color: var(--color-primary, #287f78);
}

.progress-step.current::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--color-primary, #287f78);
  content: '';
  animation: progress-move 1.4s ease-in-out infinite;
  transform-origin: left;
}

.state-panel {
  display: flex;
  min-height: 360px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 24px;
  border: 1px solid var(--color-border, #dce3ea);
  border-radius: 10px;
  background: #ffffff;
  text-align: center;
}

.state-panel h2 {
  color: var(--color-text-strong, #182235);
  font-size: 17px;
  font-weight: 800;
}

.state-panel p {
  max-width: 460px;
  color: var(--color-text-secondary, #6f7b8d);
  font-size: 12px;
  line-height: 1.6;
}

.error-panel {
  color: #b64d5e;
  border-color: #edcbd1;
  background: #fffafb;
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 2px solid #e2e7ec;
  border-top-color: var(--color-primary, #287f78);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner.small {
  width: 22px;
  height: 22px;
}

.empty-guide,
.first-report-guide {
  display: grid;
  margin-top: 24px;
  border: 1px solid var(--color-border, #dce3ea);
  border-radius: 10px;
  background: #ffffff;
}

.empty-guide {
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 24px;
  padding: 34px;
}

.empty-visual {
  display: grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border: 1px solid #cde2de;
  border-radius: 18px;
  color: var(--color-primary, #287f78);
  background: #f1f8f7;
}

.empty-copy h2,
.first-report-copy h2 {
  margin-top: 6px;
  color: var(--color-text-strong, #182235);
  font-size: 22px;
  font-weight: 850;
  letter-spacing: -0.025em;
}

.empty-copy p,
.first-report-copy p {
  max-width: 650px;
  margin-top: 10px;
  color: var(--color-text-secondary, #6f7b8d);
  font-size: 13px;
  line-height: 1.75;
}

.guide-actions {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 4px;
}

.guide-actions button {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 14px;
  border: 1px solid #e1e6eb;
  border-radius: 8px;
  color: #435268;
  background: #fafbfc;
  text-align: left;
  cursor: pointer;
  transition: 160ms ease;
}

.guide-actions button:hover {
  border-color: #a9cbc6;
  color: var(--color-primary, #287f78);
  background: #f4faf8;
}

.guide-actions button > span {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.guide-actions strong {
  font-size: 12px;
  font-weight: 800;
}

.guide-actions small {
  color: #8a95a4;
  font-size: 10px;
}

.first-report-guide {
  grid-template-columns: minmax(0, 0.9fr) minmax(420px, 1.1fr);
  align-items: center;
  gap: 34px;
  padding: 34px;
}

.first-report-chart {
  min-width: 0;
  padding: 16px 18px 8px;
  border: 1px solid #e3e8ed;
  border-radius: 9px;
  background: #fafcfd;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #748092;
  font-size: 11px;
}

.preview-header strong {
  color: #26354a;
  font-size: 13px;
}

.preview-chart-box {
  height: 190px;
}

.report-history-bar {
  display: flex;
  min-height: 64px;
  align-items: center;
  gap: 18px;
  margin-top: 20px;
  padding: 10px 12px;
  border: 1px solid var(--color-border, #dce3ea);
  border-radius: 9px;
  background: #ffffff;
}

.current-report-mark {
  display: flex;
  min-width: 190px;
  align-items: center;
  gap: 10px;
  padding-right: 18px;
  border-right: 1px solid #e7ebef;
}

.history-icon-box {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border-radius: 8px;
  color: var(--color-primary, #287f78);
  background: #edf7f5;
}

.current-report-mark > div:last-child {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.current-report-mark span {
  color: #8a95a4;
  font-size: 9px;
  font-weight: 700;
}

.current-report-mark strong {
  overflow: hidden;
  color: #26354a;
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-report-list {
  display: flex;
  min-width: 0;
  flex: 1;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.recent-report-list::-webkit-scrollbar {
  display: none;
}

.recent-report-list button {
  display: flex;
  min-width: 74px;
  height: 38px;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #778396;
  background: #f6f8fa;
  cursor: pointer;
}

.recent-report-list button:hover {
  border-color: #c7d9d6;
  background: #f3f8f7;
}

.recent-report-list button.active {
  border-color: #9fc7c1;
  color: var(--color-primary, #287f78);
  background: #edf7f5;
}

.recent-report-list strong {
  font-size: 10px;
  font-weight: 800;
}

.recent-report-list span {
  margin-top: 2px;
  font-size: 9px;
}

.history-entry {
  display: inline-flex;
  height: 36px;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  padding: 0 11px;
  border: 1px solid #dbe2e8;
  border-radius: 7px;
  color: #5d6b7d;
  background: #ffffff;
  font-size: 10px;
  font-weight: 750;
  cursor: pointer;
}

.history-entry:hover {
  border-color: #a9c9c4;
  color: var(--color-primary, #287f78);
}

.history-entry span {
  display: grid;
  min-width: 18px;
  height: 18px;
  place-items: center;
  border-radius: 9px;
  color: #748092;
  background: #f0f3f6;
  font-size: 9px;
}

.report-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.75fr);
  gap: 18px;
  margin-top: 18px;
}

.overview-copy,
.metric-grid,
.analysis-panel,
.strategy-panel,
.plan-panel {
  border: 1px solid var(--color-border, #dce3ea);
  border-radius: 10px;
  background: #ffffff;
}

.overview-copy {
  padding: 26px 28px;
  background:
    linear-gradient(135deg, rgba(40, 127, 120, 0.07), rgba(40, 127, 120, 0) 58%),
    #ffffff;
}

.overview-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.overview-heading h2 {
  margin-top: 5px;
  color: #182235;
  font-size: 23px;
  font-weight: 850;
  letter-spacing: -0.03em;
}

.date-badge {
  display: inline-flex;
  min-height: 30px;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  padding: 0 9px;
  border: 1px solid #dce4e8;
  border-radius: 7px;
  color: #687588;
  background: rgba(255, 255, 255, 0.78);
  font-size: 10px;
  font-weight: 700;
}

.assessment-text {
  margin-top: 22px;
  color: #27354a;
  font-size: 17px;
  font-weight: 520;
  line-height: 1.85;
}

.overview-footnote {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(40, 127, 120, 0.14);
  color: #6f7d8f;
  font-size: 11px;
  line-height: 1.65;
}

.overview-footnote svg {
  flex: 0 0 auto;
  margin-top: 1px;
  color: var(--color-primary, #287f78);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  overflow: hidden;
}

.metric-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 11px;
  padding: 20px;
  border-right: 1px solid #edf0f3;
  border-bottom: 1px solid #edf0f3;
}

.metric-item:nth-child(2n) {
  border-right: 0;
}

.metric-item:nth-last-child(-n + 2) {
  border-bottom: 0;
}

.metric-icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border-radius: 8px;
  color: var(--color-primary, #287f78);
  background: #eef7f5;
}

.metric-item > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.metric-item strong {
  overflow: hidden;
  color: #243247;
  font-size: 20px;
  font-weight: 850;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-topic strong {
  font-size: 13px;
  line-height: 1.35;
}

.metric-item span:last-child {
  color: #8792a1;
  font-size: 9px;
  font-weight: 650;
}

.visual-analysis {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(340px, 0.75fr);
  gap: 18px;
  margin-top: 18px;
}

.analysis-panel {
  min-width: 0;
  padding: 22px;
}

.panel-heading,
.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.panel-heading h3,
.section-heading h3 {
  margin-top: 4px;
  color: #243247;
  font-size: 16px;
  font-weight: 820;
  letter-spacing: -0.015em;
}

.panel-heading > p {
  max-width: 330px;
  color: #7c8797;
  font-size: 10px;
  line-height: 1.55;
  text-align: right;
}

.trend-chart-box {
  height: 310px;
  margin-top: 8px;
}

.module-chart-box {
  height: 184px;
  margin-top: 3px;
}

.module-ranking {
  display: flex;
  flex-direction: column;
  gap: 9px;
  margin-top: 8px;
  padding-top: 14px;
  border-top: 1px solid #edf0f3;
}

.module-row {
  display: grid;
  grid-template-columns: 7px minmax(0, 1fr) auto 34px;
  align-items: center;
  gap: 7px;
  color: #687588;
  font-size: 10px;
}

.module-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.module-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.module-row strong {
  color: #344359;
  font-size: 10px;
  font-weight: 750;
}

.module-row em {
  color: #98a2af;
  font-size: 9px;
  font-style: normal;
  text-align: right;
}

.module-empty,
.plan-empty {
  padding: 22px 0;
  color: #929dab;
  font-size: 11px;
  text-align: center;
}

.strategy-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 18px;
  margin-top: 18px;
}

.strategy-panel,
.plan-panel {
  padding: 22px;
}

.section-heading > svg {
  color: var(--color-primary, #287f78);
}

.strategy-facts {
  display: flex;
  flex-direction: column;
  margin-top: 18px;
}

.strategy-facts > div {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 18px;
  padding: 15px 0;
  border-bottom: 1px solid #edf0f3;
}

.strategy-facts > div:last-child {
  border-bottom: 0;
}

.strategy-facts span {
  color: #8994a3;
  font-size: 10px;
  font-weight: 700;
}

.strategy-facts strong {
  color: #344359;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.55;
}

.plan-list {
  display: flex;
  flex-direction: column;
  margin-top: 13px;
}

.plan-item {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid #edf0f3;
}

.plan-item:last-child {
  border-bottom: 0;
}

.plan-index {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 1px solid #cfe1de;
  border-radius: 8px;
  color: var(--color-primary, #287f78);
  background: #f3f9f8;
  font-size: 9px;
  font-weight: 800;
}

.plan-item strong {
  color: #2c3a4f;
  font-size: 12px;
  font-weight: 800;
}

.plan-item p {
  margin-top: 5px;
  color: #748092;
  font-size: 11px;
  line-height: 1.65;
}

.chart {
  width: 100%;
  height: 100%;
}

.drawer-overlay {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: flex;
  justify-content: flex-end;
  background: rgba(18, 27, 40, 0.38);
  backdrop-filter: blur(3px);
}

.drawer-panel {
  display: flex;
  width: min(420px, 100%);
  height: 100%;
  flex-direction: column;
  background: #ffffff;
  box-shadow: -16px 0 48px rgba(25, 35, 50, 0.14);
  animation: drawer-in 220ms ease-out;
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 25px 24px 20px;
  border-bottom: 1px solid #e7ebef;
}

.drawer-header > div > span {
  color: var(--color-primary, #287f78);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.drawer-header h2 {
  margin-top: 5px;
  color: #202f43;
  font-size: 21px;
  font-weight: 850;
}

.drawer-header p {
  margin-top: 5px;
  color: #8390a0;
  font-size: 10px;
}

.drawer-close {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  place-items: center;
  border: 1px solid #e0e5ea;
  border-radius: 7px;
  color: #6e7a8c;
  background: #ffffff;
  cursor: pointer;
}

.drawer-close:hover {
  color: #26354a;
  background: #f5f7f9;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px;
}

.drawer-loading,
.drawer-empty {
  display: flex;
  min-height: 200px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #8792a1;
  font-size: 11px;
}

.history-full-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-full-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) 18px;
  gap: 10px;
  align-items: center;
  min-height: 82px;
  padding: 13px 13px;
  border: 1px solid #e1e6eb;
  border-radius: 8px;
  color: #7a8696;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: 150ms ease;
}

.history-full-item:hover {
  border-color: #b5d1cd;
  background: #f8fbfa;
}

.history-full-item.active {
  border-color: #8ebdb6;
  background: #f0f8f6;
}

.history-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #a7b0bb;
}

.history-full-item.status-ready .history-status-dot {
  background: #278777;
}

.history-full-item.status-generating .history-status-dot {
  background: #5573c8;
  box-shadow: 0 0 0 4px rgba(85, 115, 200, 0.12);
}

.history-full-item.status-failed .history-status-dot {
  background: #c65f70;
}

.history-item-main {
  min-width: 0;
}

.history-item-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-item-heading strong {
  color: #2b394e;
  font-size: 12px;
  font-weight: 800;
}

.history-item-heading span {
  color: #718092;
  font-size: 9px;
  font-weight: 700;
}

.history-item-main p {
  margin-top: 6px;
  color: #7d8999;
  font-size: 10px;
}

.history-item-main time {
  display: block;
  margin-top: 3px;
  color: #9aa3af;
  font-size: 9px;
}

.drawer-pagination {
  display: flex;
  min-height: 62px;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 18px;
  border-top: 1px solid #e7ebef;
}

.drawer-pagination button {
  display: inline-flex;
  height: 32px;
  align-items: center;
  gap: 5px;
  padding: 0 9px;
  border: 1px solid #dce2e8;
  border-radius: 6px;
  color: #5f6d80;
  background: #ffffff;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
}

.drawer-pagination button:disabled {
  color: #a8b0ba;
  background: #f5f6f7;
  cursor: not-allowed;
}

.drawer-pagination > span {
  color: #7f8a99;
  font-size: 10px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes progress-move {
  0% {
    transform: scaleX(0);
    transform-origin: left;
  }
  50% {
    transform: scaleX(1);
    transform-origin: left;
  }
  51% {
    transform-origin: right;
  }
  100% {
    transform: scaleX(0);
    transform-origin: right;
  }
}

@keyframes drawer-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

@media (max-width: 980px) {
  .report-overview,
  .visual-analysis,
  .strategy-layout,
  .first-report-guide {
    grid-template-columns: 1fr;
  }

  .first-report-guide {
    gap: 24px;
  }

  .report-history-bar {
    flex-wrap: wrap;
  }

  .current-report-mark {
    border-right: 0;
  }

  .recent-report-list {
    order: 3;
    width: 100%;
    flex-basis: 100%;
  }
}

@media (max-width: 720px) {
  .assessment-page {
    padding: 20px 14px 44px;
  }

  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .generation-progress {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .empty-guide {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .guide-actions {
    grid-template-columns: 1fr;
  }

  .first-report-guide {
    padding: 24px;
  }

  .first-report-chart {
    min-width: 0;
  }

  .report-overview {
    margin-top: 14px;
  }

  .overview-copy,
  .analysis-panel,
  .strategy-panel,
  .plan-panel {
    padding: 19px;
  }

  .overview-heading {
    flex-direction: column;
  }

  .date-badge {
    align-self: flex-start;
  }

  .assessment-text {
    font-size: 15px;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .metric-item,
  .metric-item:nth-child(2n),
  .metric-item:nth-last-child(-n + 2) {
    border-right: 0;
    border-bottom: 1px solid #edf0f3;
  }

  .metric-item:last-child {
    border-bottom: 0;
  }

  .panel-heading {
    flex-direction: column;
  }

  .panel-heading > p {
    max-width: none;
    text-align: left;
  }

  .trend-chart-box {
    height: 260px;
  }
}

@media (max-width: 480px) {
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .generate-button {
    width: 100%;
  }

  .generation-progress {
    grid-template-columns: 1fr;
  }

  .report-history-bar {
    align-items: stretch;
  }

  .current-report-mark {
    width: 100%;
  }

  .history-entry {
    justify-content: center;
    width: 100%;
  }

  .module-row {
    grid-template-columns: 7px minmax(0, 1fr) auto;
  }

  .module-row em {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .assessment-page *,
  .assessment-page *::before,
  .assessment-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
