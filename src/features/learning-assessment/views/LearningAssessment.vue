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
        <Button class="generate-btn" :disabled="generating" @click="triggerAssessmentGeneration">
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

    <!-- 失败状态 -->
    <section v-else-if="activeAssessment?.status === 'failed'" class="error-state">
      <AlertCircle :size="24" />
      <h2>评估生成失败</h2>
      <p>{{ activeAssessment.failure_code || '未知内部错误' }}</p>
      <Button variant="outline" @click="triggerAssessmentGeneration">重试</Button>
    </section>

    <!-- 生成中状态 -->
    <section v-else-if="activeAssessment?.status === 'generating'" class="loading-state">
      <div class="loading-spinner" />
      <p>评估正在生成中...</p>
    </section>

    <!-- 主内容 -->
    <template v-else>
      <!-- CASE 1: 用户从未生成过评估，且没有任何学习数据 -->
      <div v-if="!activeAssessment && (!dashboardData || dashboardData.evaluation_summary.event_count === 0)" class="empty-guide-card ui-card">
        <div class="empty-guide-inner">
          <div class="guide-icon-wrapper">
            <Compass :size="36" class="guide-icon" />
          </div>
          <h2>暂无评估事实，开启您的学习之旅</h2>
          <p class="guide-subtitle">为了提供精准的自适应辅导策略，系统需要积累一些您的学习足迹（如对话、浏览、练习等）。</p>
          <div class="guide-actions">
            <div class="action-card-mini" @click="navigateTo('/tutor')">
              <span class="mini-icon tutor-icon">💬</span>
              <div class="action-card-text">
                <strong>智能辅导</strong>
                <span>与 AI 导师进行学术对话</span>
              </div>
            </div>
            <div class="action-card-mini" @click="navigateTo('/resource-generator')">
              <span class="mini-icon resource-icon">💡</span>
              <div class="action-card-text">
                <strong>资源引擎</strong>
                <span>检索或生成多模态资源</span>
              </div>
            </div>
            <div class="action-card-mini" @click="navigateTo('/question-bank')">
              <span class="mini-icon question-icon">📚</span>
              <div class="action-card-text">
                <strong>学习题库</strong>
                <span>完成推荐题目和巩固练习</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- CASE 2: 用户有学习数据，但从未生成过评估报告 -->
      <div v-else-if="!activeAssessment && dashboardData" class="welcome-guide-card ui-card">
        <div class="welcome-guide-inner">
          <div class="guide-icon-wrapper">
            <Sparkles :size="36" class="guide-icon sparkles" />
          </div>
          <h2>生成您的首份学习效果评估</h2>
          <p class="guide-subtitle">系统已检测到您近期的学习足迹！点击下方按钮，系统将使用大语言模型为您深度定制自适应辅导策略与下一步学习计划。</p>
          <Button class="generate-btn large-btn" :disabled="generating" @click="triggerAssessmentGeneration">
            <Sparkles :size="18" />
            一键生成评估报告
          </Button>
          <div class="guide-preview-charts">
            <div class="preview-chart-title">您近期的学习活动趋势</div>
            <v-chart class="chart mini-chart" :option="lineOption" autoresize />
          </div>
        </div>
      </div>

      <!-- CASE 3: 正常显示已生成的评估报告 -->
      <template v-else-if="dashboardData">
        <!-- 查看历史评估提示 -->
        <div v-if="viewingHistorical" class="historical-banner">
          <History :size="14" />
          <span>正在查看历史评估（{{ formatDateRange(historicalWindow.start, historicalWindow.end) }}）</span>
          <Button variant="ghost" size="sm" @click="returnToLatest">
            返回最新
          </Button>
        </div>

        <div class="dashboard-grid">
          <!-- 左侧：图表与文字洞察主视图 -->
          <div class="dashboard-main">
            <!-- 本期结论与策略 -->
            <section class="conclusion-section ui-card conclusion-editorial">
              <div class="conclusion-card">
                <div class="conclusion-header">
                  <h2>本期结论与策略调整</h2>
                  <span class="window-badge">
                    <Calendar :size="14" />
                    {{ dashboardData.window.days }} 天
                    {{ formatDateRange(dashboardData.window.start, dashboardData.window.end) }}
                  </span>
                </div>
                <p class="conclusion-text">{{ activeAssessment?.assessment || guidanceStrategy?.conclusion || defaultConclusion }}</p>
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
                <p v-if="guidanceStrategy?.reason" class="strategy-reason">
                  <span class="reason-label">策略依据</span>
                  {{ guidanceStrategy.reason }}
                </p>
              </div>
            </section>

            <!-- 学习趋势 + 模块时长分布 -->
            <section class="charts-section">
              <div class="chart-panel-outer ui-card">
                <article class="chart-panel">
                  <div class="panel-header">
                    <h3>每日学习趋势</h3>
                  </div>
                  <v-chart class="chart" :option="lineOption" autoresize />
                </article>
              </div>
              <div class="chart-panel-outer ui-card">
                <article class="chart-panel">
                  <div class="panel-header">
                    <h3>模块学习时长分布</h3>
                  </div>
                  <v-chart class="chart" :option="pieOption" autoresize />
                </article>
              </div>
            </section>
          </div>

          <!-- 右侧：行动与历史侧边栏 -->
          <aside class="dashboard-sidebar">
            <!-- 行动计划 -->
            <section v-if="actionPlan.length" class="action-section ui-card sidebar-card">
              <div class="action-card">
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
                  </div>
                </div>
              </div>
            </section>

            <!-- 历史评估 -->
            <section class="history-section ui-card sidebar-card">
              <div class="history-card">
                <div class="section-header">
                  <History :size="16" />
                  <h3>历史评估</h3>
                  <span class="history-count">{{ totalAssessments }} 份</span>
                </div>
                <div v-if="historyLoading" class="history-loading">加载中...</div>
                <div v-else-if="assessmentsHistory.length === 0" class="history-empty">暂无历史评估</div>
                <div v-else class="history-grid">
                  <button
                    v-for="item in assessmentsHistory.slice(0, 4)"
                    :key="item.id"
                    type="button"
                    :class="{ active: activeAssessment?.id === item.id }"
                    class="history-item"
                    @click="selectAssessment(item)"
                  >
                    <strong>{{ item.range_days }} 天评估</strong>
                    <span>{{ formatDateRange(item.window_start, item.window_end) }}</span>
                  </button>
                </div>
                <div v-if="totalAssessments > 4" class="history-more">
                  <Button variant="ghost" size="sm" @click="showHistoryDrawer = true">
                    查看全部 {{ totalAssessments }} 份评估
                    <ChevronRight :size="14" />
                  </Button>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </template>
    </template>

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
                v-for="item in assessmentsHistory"
                :key="item.id"
                type="button"
                :class="{ active: activeAssessment?.id === item.id }"
                class="history-full-item"
                @click="selectAssessment(item); showHistoryDrawer = false"
              >
                <strong>{{ item.range_days }} 天评估</strong>
                <span>{{ formatDateRange(item.window_start, item.window_end) }}</span>
                <em>{{ statusLabel(item.status) }}</em>
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
import { computed, onMounted, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Compass,
  History,
  Sparkles,
  X,
} from 'lucide-vue-next'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import {
  generateAssessment,
  getLatestAssessment,
  getAssessmentDetail,
  getAssessmentsHistory,
  getAssessmentDashboard,
} from '@/features/learning-assessment/api/assessment'
import {
  getDashboard,
} from '@/features/evaluation/api/evaluation'
import type {
  ActionPlanItem,
  GuidanceStrategy,
  LearningAssessment,
} from '@/features/learning-assessment/model/assessment'
import type {
  DashboardData,
} from '@/features/evaluation/api/evaluation'
import { normalizeGuidanceStrategy } from '@/features/learning-assessment/model/assessment'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const rangeOptions = [3, 7, 14] as const
const selectedRange = ref<3 | 7 | 14>(7)
const assessmentsHistory = ref<Omit<LearningAssessment, 'assessment'>[]>([])
const activeAssessment = ref<LearningAssessment | null>(null)
const dashboardData = ref<DashboardData | null>(null)
const guidanceStrategy = ref<GuidanceStrategy | null>(null)
const generating = ref(false)
const historyLoading = ref(false)
const initialLoading = ref(true)
const currentPage = ref(1)
const totalAssessments = ref(0)
const totalPages = ref(1)
const currentStepIdx = ref(0)
const pageSize = 10
const showHistoryDrawer = ref(false)
const generationSteps = ['聚合学习事实', '校验证据质量', '生成评估报告', '更新辅导策略']

// 历史评估联动状态
const viewingHistorical = ref(false)
const historicalWindow = ref<{ start: string; end: string }>({ start: '', end: '' })

// === 路由导航 ===
const router = useRouter()
function navigateTo(path: string) {
  void router.push(path)
}

const actionPlan = computed<ActionPlanItem[]>(() => guidanceStrategy.value?.action_plan ?? [])

const defaultConclusion = computed(() => {
  if (dashboardData.value?.evaluation_summary?.event_count === 0) {
    return '当前窗口暂无学习活动记录，建议先完成一次资源学习或练习。'
  }
  return '学习证据已形成，系统已记录到学习时长、模块使用和练习表现。'
})

// 饼图颜色 (以石英紫为主的学术感冷色系搭配)
const PIE_COLORS = ['#8B5CF6', '#6366f1', '#10B981', '#F59E0B', '#3B82F6', '#EC4899']

const lineOption = computed(() => {
  const daily = dashboardData.value?.time_stats.daily_breakdown ?? []
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
      data: daily.map(item => Number((item.seconds / 60).toFixed(1))),
      type: 'line',
      smooth: true,
      symbolSize: 6,
      lineStyle: { color: '#46B8B4', width: 2.5 },
      itemStyle: { color: '#46B8B4' },
      areaStyle: { color: 'rgba(70, 184, 180, 0.1)' },
    }],
  }
})

const pieOption = computed(() => {
  const breakdown = dashboardData.value?.module_time_breakdown ?? []
  let data: any[] = breakdown
    .filter(item => item.seconds > 0)
    .map(item => ({
      name: item.module,
      value: Number((item.seconds / 60).toFixed(1)),
    }))
  
  if (data.length === 0) {
    data = [{
      name: '暂无数据',
      value: 1,
      itemStyle: { color: '#f3f4f6' }
    }]
  }

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937', fontSize: 13 },
      formatter: '{b}<br/>学习时长: {c} 分钟 ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: '#6b7280', fontSize: 12 },
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 8,
    },
    color: PIE_COLORS,
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' },
      },
      labelLine: { show: false },
      data,
    }],
  }
})

// 切换时间范围时重新加载看板数据
watch(selectedRange, () => {
  if (!initialLoading.value && !viewingHistorical.value) {
    void loadDashboard()
  }
})

async function loadDashboard(): Promise<void> {
  try {
    const response = await getDashboard(selectedRange.value)
    dashboardData.value = response.data.data
    if (dashboardData.value?.guidance_strategy) {
      guidanceStrategy.value = normalizeGuidanceStrategy(dashboardData.value.guidance_strategy as Partial<GuidanceStrategy>)
    }
  } catch (error) {
    console.error('加载看板数据失败', error)
  }
}

async function loadAssessmentsHistory(page = 1): Promise<void> {
  historyLoading.value = true
  try {
    const response = await getAssessmentsHistory(page, pageSize)
    assessmentsHistory.value = response.data.data.items
    totalAssessments.value = response.data.data.total
    totalPages.value = Math.max(1, Math.ceil(response.data.data.total / pageSize))
    currentPage.value = page
  } catch (error) {
    console.error('加载历史评估失败', error)
    toast.error('历史记录加载失败')
  } finally {
    historyLoading.value = false
  }
}

async function selectAssessment(item: Omit<LearningAssessment, 'assessment'>): Promise<void> {
  try {
    // 加载评估详情
    const detailResponse = await getAssessmentDetail(item.id)
    activeAssessment.value = detailResponse.data.data

    // 加载该评估时间窗口的看板数据
    const dashboardResponse = await getAssessmentDashboard(item.id)
    dashboardData.value = dashboardResponse.data.data
    if (dashboardData.value?.guidance_strategy) {
      guidanceStrategy.value = normalizeGuidanceStrategy(dashboardData.value.guidance_strategy as Partial<GuidanceStrategy>)
    }

    // 标记正在查看历史评估
    viewingHistorical.value = true
    historicalWindow.value = { start: item.window_start, end: item.window_end }
  } catch (error) {
    console.error('加载评估详情失败', error)
    toast.error('评估详情加载失败')
  }
}

async function returnToLatest(): Promise<void> {
  viewingHistorical.value = false
  activeAssessment.value = null
  await loadDashboard()

  // 重新获取最新评估
  try {
    const response = await getLatestAssessment()
    if (response.data.data) {
      activeAssessment.value = response.data.data
    }
  } catch (error) {
    console.error('获取最新评估失败', error)
  }
}

async function triggerAssessmentGeneration(): Promise<void> {
  generating.value = true
  currentStepIdx.value = 0
  const timer = window.setInterval(() => {
    currentStepIdx.value = Math.min(currentStepIdx.value + 1, generationSteps.length - 1)
  }, 1000)

  try {
    // POST 立即返回 generating 状态，后台异步执行 LLM 生成
    const response = await generateAssessment(selectedRange.value)
    activeAssessment.value = response.data.data
    viewingHistorical.value = false

    // 轮询直到生成完成
    const maxPolls = 60 // 最多轮询 60 次（约 60 秒）
    for (let i = 0; i < maxPolls; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      try {
        const latestResp = await getLatestAssessment()
        const latest = latestResp.data.data
        if (latest && latest.status === 'ready') {
          activeAssessment.value = latest
          toast.success('学习效果评估已生成')
          await Promise.all([
            loadAssessmentsHistory(1),
            loadDashboard(),
          ])
          return
        }
        if (latest && latest.status === 'failed') {
          activeAssessment.value = latest
          toast.error('评估生成失败')
          return
        }
      } catch {
        // 轮询失败继续
      }
    }
    toast.warning('评估生成超时，请稍后刷新查看')
  } catch (error: any) {
    if (error?.response?.status === 409) {
      toast.warning('已有评估生成中')
    } else {
      console.error('生成评估失败', error)
      toast.error('生成评估失败')
    }
  } finally {
    window.clearInterval(timer)
    generating.value = false
    currentStepIdx.value = 0
  }
}

function changePage(page: number): void {
  void loadAssessmentsHistory(page)
}

function statusLabel(status: LearningAssessment['status']): string {
  if (status === 'ready') return '已就绪'
  if (status === 'generating') return '生成中'
  return '失败'
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
    loadAssessmentsHistory(1),
    loadDashboard(),
  ])

  try {
    const response = await getLatestAssessment()
    if (response.data.data) {
      activeAssessment.value = response.data.data
      // 如果评估正在生成中，自动轮询
      if (activeAssessment.value.status === 'generating') {
        generating.value = true
        currentStepIdx.value = 1
        pollAssessmentStatus()
      }
    } else if (assessmentsHistory.value[0]?.id !== undefined) {
      const item = assessmentsHistory.value[0]
      await selectAssessment(item)
    }
  } catch (error) {
    console.error('获取最新评估失败', error)
  } finally {
    initialLoading.value = false
  }
})

/** 轮询评估生成状态，直到 ready/failed 或超时 */
async function pollAssessmentStatus(): Promise<void> {
  const maxPolls = 60
  for (let i = 0; i < maxPolls; i++) {
    await new Promise(resolve => setTimeout(resolve, 2000))
    try {
      const resp = await getLatestAssessment()
      const latest = resp.data.data
      if (latest && latest.status === 'ready') {
        activeAssessment.value = latest
        generating.value = false
        currentStepIdx.value = 0
        toast.success('学习效果评估已生成')
        await Promise.all([loadAssessmentsHistory(1), loadDashboard()])
        return
      }
      if (latest && latest.status === 'failed') {
        activeAssessment.value = latest
        generating.value = false
        currentStepIdx.value = 0
        toast.error('评估生成失败')
        return
      }
    } catch {
      // 轮询失败继续
    }
  }
  generating.value = false
  currentStepIdx.value = 0
  toast.warning('评估生成超时，请稍后刷新查看')
}
</script>

<style scoped>
.assessment-page {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* Dashboard Grid Layout (Bento Grid) */
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(320px, 3fr);
  gap: var(--space-6);
  align-items: start;
}

.dashboard-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.dashboard-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  position: sticky;
  top: var(--space-6);
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

h1, h2, h3, h4, p {
  margin: 0;
}

/* UI Card (Clean, minimal card style) */
.ui-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  transition: var(--transition-base);
}

.ui-card:hover {
  border-color: var(--color-primary-border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-light);
}

.header-left h1 {
  font-size: 1.5rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  letter-spacing: -0.02em;
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
  transition: var(--transition-fast);
}

.range-tabs button:hover {
  color: var(--color-text-strong);
  background: var(--color-bg);
}

.range-tabs button.active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: var(--shadow-xs);
}

.generate-btn {
  min-height: 2.25rem;
  gap: var(--space-2);
  background: var(--color-primary) !important;
  color: white !important;
  border: none !important;
  transition: var(--btn-transition) !important;
  font-weight: var(--weight-bold) !important;
  border-radius: var(--radius-sm) !important;
  cursor: pointer;
}

.generate-btn:hover {
  background: var(--color-text-strong) !important;
  transform: translateY(-1px);
}

.generate-btn:active {
  transform: translateY(0.5px);
}

.generate-btn:disabled {
  background: var(--color-border) !important;
  color: var(--color-text-muted) !important;
  cursor: not-allowed;
  transform: none !important;
}

/* Generation Progress with Micro-animation */
.generation-progress {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.generation-progress span {
  min-height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  transition: var(--transition-base);
  position: relative;
  overflow: hidden;
}

.generation-progress span.done {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-color: var(--color-primary-soft);
}

.generation-progress span.current {
  background: var(--color-surface);
  color: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 0 8px rgba(70, 184, 180, 0.015);
}

.generation-progress span.current::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  width: 100%;
  background: var(--color-primary);
  animation: progress-slide 1.5s infinite linear;
}

@keyframes progress-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Loading & Empty States */
.loading-state,
.empty-state,
.error-state {
  min-height: 16rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  text-align: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state .empty-icon {
  color: var(--color-text-faint);
}

.empty-state h2,
.error-state h2 {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
}

.empty-state p,
.loading-state p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.error-state {
  color: var(--color-danger);
  border-color: var(--color-danger);
  background: var(--color-danger-soft);
}

.error-state h2 {
  color: var(--color-danger);
}

/* Historical Banner */
.historical-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  border: 1px solid var(--color-border);
  font-size: var(--text-sm);
  color: var(--color-primary);
  box-shadow: var(--shadow-xs);
}

/* Conclusion Section */
.conclusion-section {
  margin-top: 0;
}

.conclusion-editorial {
  padding: var(--space-8) var(--space-8);
  border: none;
  background: linear-gradient(135deg, rgba(70, 184, 180, 0.05) 0%, rgba(70, 184, 180, 0.01) 100%);
  box-shadow: none;
}

.conclusion-card {
  display: flex;
  flex-direction: column;
}

.conclusion-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  color: var(--color-primary);
}

.conclusion-editorial .conclusion-header h2 {
  font-size: 1.5rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-primary-dark);
  letter-spacing: -0.02em;
}

.conclusion-editorial .conclusion-text {
  font-size: 1.125rem;
  line-height: 1.6;
  font-weight: 500;
  color: var(--color-text-strong);
  margin-top: var(--space-2);
}

.window-badge {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2.5);
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
  margin-bottom: var(--space-5);
}

.strategy-highlights {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
}

.highlight-item {
  padding: var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  transition: var(--transition-fast);
}

.highlight-item:hover {
  border-color: var(--color-primary-border);
  transform: translateY(-1px);
}

.highlight-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.highlight-value {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  line-height: 1.35;
  font-weight: var(--weight-semibold);
}

.strategy-reason {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

.reason-label {
  display: inline-block;
  margin-right: var(--space-1.5);
  padding: 1px var(--space-1.5);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
  vertical-align: middle;
}

/* Charts Section */
.charts-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
}

@media (max-width: 768px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
}

.chart-panel-outer {
  display: flex;
  flex-direction: column;
}

.chart-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  color: var(--color-primary);
}

.panel-header h3 {
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.chart {
  width: 100%;
  height: 14rem;
  flex: 1;
}

.chart-empty {
  min-height: 12rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  font-size: var(--text-sm);
  flex: 1;
}

/* Action Section */
.action-card {
  background: var(--color-surface);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  color: var(--color-primary);
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
  gap: var(--space-4);
  padding: var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  transition: var(--transition-fast);
}

.action-item:hover {
  border-color: var(--color-primary-border);
  background: var(--color-surface-hover);
}

.action-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
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
  line-height: 1.45;
  font-weight: var(--weight-medium);
}

.action-topic {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* History Section */
.history-card {
  background: var(--color-surface);
}

.history-loading,
.history-empty {
  min-height: 5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-faint);
  font-size: var(--text-sm);
}

.history-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}

.history-item {
  min-height: 4rem;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--space-1);
  transition: var(--transition-fast);
}

.history-item:hover {
  border-color: var(--color-primary);
  background: var(--color-surface);
  transform: translateY(-1px);
}

.history-item.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: var(--shadow-sm);
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
  margin-top: var(--space-4);
  display: flex;
  justify-content: center;
}

.history-more button {
  color: var(--color-primary) !important;
}

.history-more button:hover {
  color: var(--color-text-strong) !important;
}

/* Drawers */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
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
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border-light);
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
  transition: var(--transition-fast);
}

.drawer-close:hover {
  background: var(--color-bg);
  color: var(--color-text-strong);
}

.drawer-body {
  flex: 1;
  overflow: auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.history-full-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2.5);
}

.history-full-item {
  min-height: 4.5rem;
  padding: var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: var(--transition-fast);
}

.history-full-item:hover {
  border-color: var(--color-primary);
  background: var(--color-surface);
  transform: translateY(-1px);
}

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
  color: var(--color-primary);
  font-style: normal;
  font-weight: var(--weight-bold);
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-light);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

/* Responsive */
@media (max-width: 900px) {
  .charts-section {
    grid-template-columns: 1fr;
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

  .strategy-highlights {
    grid-template-columns: 1fr;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }
}
/* === Empty Guide States === */
.empty-guide-card, .welcome-guide-card {
  margin-top: var(--space-4);
}

.empty-guide-inner, .welcome-guide-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-10) var(--space-6);
  min-height: 20rem;
}

.guide-icon-wrapper {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
  box-shadow: 0 4px 12px rgba(70, 184, 180, 0.15);
}

.guide-icon.sparkles {
  animation: pulse-glow 2s infinite ease-in-out;
}

@keyframes pulse-glow {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.empty-guide-inner h2, .welcome-guide-inner h2 {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  margin-bottom: var(--space-2);
}

.guide-subtitle {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  max-width: 500px;
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-6);
}

.guide-actions {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
  justify-content: center;
  width: 100%;
}

.action-card-mini {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-base);
  min-width: 200px;
  text-align: left;
}

.action-card-mini:hover {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.mini-icon {
  font-size: 1.5rem;
}

.action-card-text {
  display: flex;
  flex-direction: column;
}

.action-card-text strong {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
}

.action-card-text span {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.large-btn {
  padding: var(--space-3) var(--space-8);
  font-size: var(--text-base);
  min-height: 3rem;
  margin-bottom: var(--space-8);
}

.guide-preview-charts {
  width: 100%;
  max-width: 600px;
  background: var(--color-bg);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  position: relative;
  opacity: 0.8;
  filter: grayscale(0.2);
}

.preview-chart-title {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin-bottom: var(--space-3);
}

.mini-chart {
  height: 150px !important;
}

</style>
