<template>
  <main class="home-workspace">
    <div class="workspace-grid" v-if="dashboardData">
      <!-- === ROW 1: 推荐行动 + 画像雷达 === -->
      <BaseCard class="recommend-card span-8" padding="large">
        <div class="recommend-bg-decoration"></div>
        <div class="recommend-content">
          <div class="recommend-text-area">
            <BaseTag tone="indigo" pill class="recommend-badge-tag">
              <span class="badge-dot"></span>{{ dashboardData.recommendation.label }}
            </BaseTag>
            <h1 class="recommend-title">{{ dashboardData.recommendation.title }}</h1>
            <p class="recommend-desc">{{ dashboardData.recommendation.text }}</p>
          </div>
          <div class="recommend-action-area">
            <BaseButton size="large" class="recommend-btn" @click="goTo(dashboardData.recommendation.path)">
              <el-icon><component :is="getIconComponent(dashboardData.recommendation.icon)" /></el-icon>
              {{ dashboardData.recommendation.action }}
            </BaseButton>
          </div>
        </div>
      </BaseCard>

      <BaseCard class="radar-card span-4">
        <div class="radar-header">
          <h2 class="card-kicker">画像</h2>
          <button class="text-link" @click="goTo(dashboardData.radar.path)">{{ dashboardData.radar.link_label }}</button>
        </div>
        <div class="radar-chart-wrapper" v-loading="loading">
          <v-chart class="chart" :option="radarOption" autoresize />
        </div>
        <p class="radar-note">{{ dashboardData.radar.note }}</p>
      </BaseCard>

      <!-- === ROW 2: 功能入口 === -->
      <BaseCard class="actions-card span-12">
        <h2 class="card-kicker">功能入口</h2>
        <div class="actions-grid">
          <button
            class="action-tile"
            v-for="(action, idx) in dashboardData.quick_section.actions"
            :key="idx"
            @click="goTo(action.path)"
          >
            <div :class="['action-icon', actionIconClass(action.icon)]">
              <el-icon><component :is="getIconComponent(action.icon)" /></el-icon>
            </div>
            <div class="action-text">
              <h3>{{ action.label }}</h3>
              <p>{{ action.description }}</p>
            </div>
            <BaseTag class="action-tag" v-if="action.tag">{{ action.tag }}</BaseTag>
          </button>
        </div>
      </BaseCard>

      <BaseCard class="modules-card span-12" v-if="dashboardData.recent_modules">
        <div class="modules-header">
          <div>
            <h2 class="card-kicker">最近学习动态</h2>
            <p class="modules-desc">把资源、路径和题库拆开看，首页底部就能直接续上次的学习进度。</p>
          </div>
        </div>
        <div class="modules-grid">
          <div class="module-panel" role="button" tabindex="0" @click="goTo(resourceModulePath)">
            <div class="module-panel-top">
              <span class="module-panel-badge resource">
                <span class="module-dot resource"></span>
                资源
              </span>
              <span class="module-panel-meta">{{ resourceMeta }}</span>
            </div>
            <h3 class="module-panel-title">{{ resourceTitle }}</h3>
            <p class="module-panel-detail">{{ resourceDescription }}</p>
            <BaseButton variant="secondary" size="small" class="module-panel-btn" @click.stop="goTo(resourceModulePath)">
              查看资源详情
            </BaseButton>
          </div>

          <div class="module-panel" role="button" tabindex="0" @click="goTo(pathModulePath)">
            <div class="module-panel-top">
              <span class="module-panel-badge path">
                <span class="module-dot path"></span>
                路径
              </span>
              <span class="module-panel-meta">{{ pathMeta }}</span>
            </div>
            <h3 class="module-panel-title">{{ pathTitle }}</h3>
            <p class="module-panel-detail">{{ pathDescription }}</p>
            <BaseButton variant="secondary" size="small" class="module-panel-btn" @click.stop="goTo(pathModulePath)">
              继续路径学习
            </BaseButton>
          </div>

          <div class="module-panel" role="button" tabindex="0" @click="goTo(questionModulePath)">
            <div class="module-panel-top">
              <span class="module-panel-badge quiz">
                <span class="module-dot quiz"></span>
                题库
              </span>
              <span class="module-panel-meta">{{ questionMeta }}</span>
            </div>
            <h3 class="module-panel-title">{{ questionTitle }}</h3>
            <p class="module-panel-detail">{{ questionDescription }}</p>
            <BaseButton variant="secondary" size="small" class="module-panel-btn" @click.stop="goTo(questionModulePath)">
              进入题库练习
            </BaseButton>
          </div>
        </div>
      </BaseCard>
    </div>

    <section v-else class="home-state-panel" v-loading="loading">
      <div class="state-copy">
        <span class="state-badge">{{ loading ? '加载中' : '加载失败' }}</span>
        <h1>{{ loading ? '正在同步学习控制台' : '首页数据加载失败' }}</h1>
        <p>{{ loading ? '正在读取画像、路径、资源和学习事件...' : (loadError || '暂时无法获取数据') }}</p>
        <BaseButton v-if="!loading" class="state-btn" @click="loadData">重新加载</BaseButton>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '@/shared/ui/BaseCard.vue'
import BaseButton from '@/shared/ui/BaseButton.vue'
import BaseTag from '@/shared/ui/BaseTag.vue'

import { getHomeDashboard, type HomeDashboardData } from '@/features/dashboard/api/home'
import { getRadarChartData } from '@/features/profile/model/profileViewModel'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

import {
  ChatDotRound, DocumentCopy, EditPen, Guide, Reading, Monitor, Calendar
} from '@element-plus/icons-vue'

use([CanvasRenderer, RadarChart, TooltipComponent])

const router = useRouter()
const dashboardData = ref<HomeDashboardData | null>(null)
const loading = ref(false)
const loadError = ref('')

const goTo = (path: string) => {
  if (path) router.push(path)
}

const getIconComponent = (iconName: string) => {
  switch (iconName) {
    case 'chat': return ChatDotRound
    case 'resource': return DocumentCopy
    case 'path': return Guide
    case 'practice': return EditPen
    case 'monitor': return Monitor
    case 'reading': return Reading
    case 'calendar': return Calendar
    default: return DocumentCopy
  }
}

const actionIconClass = (iconName: string) => {
  switch (iconName) {
    case 'chat': return 'icon-blue'
    case 'resource': return 'icon-indigo'
    case 'path': return 'icon-emerald'
    case 'practice': return 'icon-amber'
    default: return 'icon-blue'
  }
}

const formatDate = (value?: string | null) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric'
  }).format(date)
}

const resourceStatusLabel = (status?: string | null) => {
  switch (status) {
    case 'pending': return '待处理'
    case 'generating': return '生成中'
    case 'processing': return '处理中'
    case 'completed': return '已完成'
    case 'failed': return '生成失败'
    default: return '可查看'
  }
}

const resourceModulePath = computed(() => {
  const latestResource = dashboardData.value?.recent_modules?.latest_resource
  return latestResource?.id ? `/resource-detail/${latestResource.id}` : '/resource-generator'
})

const resourceTitle = computed(() => (
  dashboardData.value?.recent_modules?.latest_resource?.title || '还没有最近资源，先生成一份学习材料'
))

const resourceMeta = computed(() => {
  const latestResource = dashboardData.value?.recent_modules?.latest_resource
  if (!latestResource) return '等待生成'
  const dateLabel = formatDate(latestResource.created_at)
  return dateLabel ? `${resourceStatusLabel(latestResource.status)} · ${dateLabel}` : resourceStatusLabel(latestResource.status)
})

const resourceDescription = computed(() => {
  const latestResource = dashboardData.value?.recent_modules?.latest_resource
  if (!latestResource) return '从知识点、课程或复习目标出发，生成一组可直接开始学习的材料。'
  return latestResource.status === 'completed'
    ? '上次生成的资源已经就绪，可以继续阅读、导出或回顾重点内容。'
    : '这份资源还在处理流程中，打开后可以继续查看当前进度。'
})

const pathModulePath = computed(() => {
  const activePath = dashboardData.value?.recent_modules?.active_path
  return activePath?.id ? '/path-planner' : '/path-planner'
})

const pathTitle = computed(() => (
  dashboardData.value?.recent_modules?.active_path?.current_node_title
  || dashboardData.value?.recent_modules?.active_path?.title
  || '还没有活跃路径，先生成你的学习路线'
))

const pathMeta = computed(() => {
  const activePath = dashboardData.value?.recent_modules?.active_path
  if (!activePath) return '待规划'
  return `进度 ${activePath.overall_progress}%`
})

const pathDescription = computed(() => {
  const activePath = dashboardData.value?.recent_modules?.active_path
  if (!activePath) return '系统会根据你的目标、画像和历史学习信号，安排一条可执行的阶段计划。'
  return activePath.current_node_title
    ? `当前正在推进「${activePath.current_node_title}」，可以继续节点学习或发起诊断优化。`
    : `当前路径「${activePath.title}」已经建立，可以继续推进后续节点。`
})

const questionModulePath = computed(() => '/question-bank')

const questionTitle = computed(() => (
  dashboardData.value?.recent_modules?.recommended_question?.subject
  || dashboardData.value?.recent_modules?.recent_quiz?.topic
  || '进入题库，开始下一轮专项练习'
))

const questionMeta = computed(() => {
  const recentQuiz = dashboardData.value?.recent_modules?.recent_quiz
  const recommendedQuestion = dashboardData.value?.recent_modules?.recommended_question
  if (recentQuiz) return `最近得分 ${recentQuiz.score}`
  if (recommendedQuestion?.difficulty) return recommendedQuestion.difficulty
  return '可练习'
})

const questionDescription = computed(() => {
  const recentQuiz = dashboardData.value?.recent_modules?.recent_quiz
  const recommendedQuestion = dashboardData.value?.recent_modules?.recommended_question
  if (recentQuiz) {
    return `最近一次练习主题是「${recentQuiz.topic}」，现在可以继续刷题巩固薄弱点。`
  }
  if (recommendedQuestion) {
    return `系统推荐你从「${recommendedQuestion.subject}」切入，顺手做一题保持学习节奏。`
  }
  return '题库支持检索、单题速练和模拟测试，适合用来补足当天的练习量。'
})

const radarOption = computed(() => {
  if (!dashboardData.value || !dashboardData.value.profile_score) return {}
  const rawData = getRadarChartData(dashboardData.value.profile_score)
  if (!rawData.radar) return {}
  return {
    ...rawData,
    radar: {
      ...rawData.radar,
      splitLine: { lineStyle: { color: 'rgba(203,213,225,0.4)', width: 1 } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(203,213,225,0.4)' } },
      axisName: { color: '#64748B', fontSize: 10, fontWeight: 500 }
    },
    series: [{
      type: 'radar',
      data: [{
        value: rawData.series?.[0]?.data?.[0]?.value || [],
        name: '能力得分',
        areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
        lineStyle: { color: '#4F46E5', width: 2 },
        itemStyle: { color: '#4F46E5', borderWidth: 2 }
      }]
    }]
  }
})

const loadData = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const res = await getHomeDashboard()
    dashboardData.value = res.data.data
  } catch (error) {
    console.error('Failed to load dashboard data', error)
    dashboardData.value = null
    loadError.value = '后端接口暂时不可用，请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.home-workspace {
  min-height: calc(100vh - 64px);
  padding: 28px 40px;
  background-color: var(--color-bg);
  color: var(--color-text);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  overflow-y: auto;
}

/* Grid */
.workspace-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 20px;
  max-width: 1360px;
  margin: 0 auto;
  padding-bottom: 32px;
}

.span-4 { grid-column: span 4; }
.span-8 { grid-column: span 8; }
.span-12 { grid-column: span 12; }

@media (max-width: 1024px) {
  .span-4, .span-8 { grid-column: span 12; }
}
@media (max-width: 640px) {
  .home-workspace { padding: 16px; }
  .workspace-grid { gap: 14px; }
  .actions-grid { grid-template-columns: 1fr !important; }
}

.card-kicker {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-light);
  margin: 0 0 16px 0;
  letter-spacing: 0.02em;
}

.recommend-card {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 300px;
  background: linear-gradient(135deg, var(--color-surface) 0%, #F8FAFC 100%);
  border: 1px solid rgba(79, 70, 229, 0.1) !important;
}

.recommend-bg-decoration {
  position: absolute;
  top: -50px;
  right: -50px;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(79, 70, 229, 0.08) 0%, rgba(255, 255, 255, 0) 70%);
  border-radius: 50%;
  pointer-events: none;
}

.recommend-content {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 32px;
  flex-wrap: wrap;
}

.recommend-text-area {
  flex: 1 1 300px;
}

.recommend-action-area {
  flex-shrink: 0;
}

.recommend-badge-tag {
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
}

.badge-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: var(--color-primary);
  margin-right: 4px;
}

.recommend-title {
  font-size: clamp(1.5rem, 2.5vw, 2.2rem);
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 10px 0;
  line-height: 1.3;
}

.recommend-desc {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.65;
}

/* Module Strip */
.module-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.module-dot.resource { background: var(--color-primary); }
.module-dot.path { background: var(--color-success); }
.module-dot.quiz { background: var(--color-warning); }

/* === Radar Card === */
.radar-card {
  display: flex;
  flex-direction: column;
}

.radar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.radar-header .card-kicker { margin-bottom: 0; }

.text-link {
  background: none;
  border: none;
  padding: 4px 8px;
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.8rem;
  cursor: pointer;
  transition: opacity 0.2s;
}

.text-link:hover { opacity: 0.7; }

.radar-chart-wrapper {
  flex: 1;
  min-height: 200px;
}

.chart { width: 100%; height: 100%; }

.radar-note {
  margin-top: 8px;
  font-size: 0.78rem;
  color: var(--color-text-light);
  line-height: 1.5;
  text-align: center;
}

/* === Actions Card === */
.actions-card {
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

@media (max-width: 1024px) {
  .actions-grid { grid-template-columns: repeat(2, 1fr); }
}

.action-tile {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  cursor: pointer;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
  text-align: left;
}

.action-tile:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-sm);
}

.action-tile:active { transform: scale(0.99); }

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}

.icon-blue { background: var(--color-primary-soft); color: var(--color-primary); }
.icon-indigo { background: var(--color-primary-soft); color: var(--color-primary); }
.icon-emerald { background: rgba(16, 185, 129, 0.1); color: var(--color-success); }
.icon-amber { background: rgba(245, 158, 11, 0.1); color: var(--color-warning); }

.action-text { flex: 1; min-width: 0; }

.action-text h3 {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 3px 0;
}

.action-text p {
  font-size: 0.76rem;
  color: var(--color-text-regular);
  margin: 0;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.action-tag {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  padding: 3px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* === Recent Modules === */
.modules-card {
}

.modules-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.modules-header .card-kicker {
  margin-bottom: 8px;
}

.modules-desc {
  margin: 0;
  color: var(--color-text-regular);
  font-size: 0.9rem;
  line-height: 1.6;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.module-panel {
  min-height: 188px;
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  cursor: pointer;
  text-align: left;
  transition: border-color var(--transition-base), box-shadow var(--transition-base), transform var(--transition-base);
  display: flex;
  flex-direction: column;
}

.module-panel:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.module-panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.module-panel-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}

.module-panel-badge.resource {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.module-panel-badge.path {
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
}

.module-panel-badge.quiz {
  background: rgba(245, 158, 11, 0.1);
  color: var(--color-warning);
}

.module-panel-meta {
  color: var(--color-text-light);
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
}

.module-panel-title {
  margin: 0 0 10px 0;
  color: var(--color-text);
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.45;
}

.module-panel-detail {
  margin: 0;
  color: var(--color-text-regular);
  font-size: 0.88rem;
  line-height: 1.65;
  flex: 1;
}

.module-panel-btn {
  margin-top: 20px;
  width: 100%;
  justify-content: center;
}

@media (max-width: 1024px) {
  .modules-grid {
    grid-template-columns: 1fr;
  }
}

/* === State Panel === */
.home-state-panel {
  min-height: 400px;
  max-width: 600px;
  margin: 0 auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  box-shadow: var(--shadow-sm);
}

.state-copy {
  max-width: 400px;
  text-align: center;
}

.state-badge {
  display: inline-flex;
  align-items: center;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-radius: 999px;
  padding: 4px 14px;
  font-size: 0.75rem;
  font-weight: 700;
  margin-bottom: 16px;
}

.state-copy h1 {
  margin: 0 0 10px 0;
  color: var(--color-text);
  font-size: 1.5rem;
  line-height: 1.3;
}

.state-copy p {
  margin: 0;
  color: var(--color-text-regular);
  font-size: 0.9rem;
  line-height: 1.6;
}

.state-btn {
  margin-top: 20px;
  border: none;
  background: var(--color-primary);
  color: #FFFFFF;
  border-radius: var(--radius-base);
  padding: 10px 20px;
  font-weight: 700;
  cursor: pointer;
  transition: background var(--transition-base);
}

.state-btn:hover { background: var(--color-primary-hover); }

/* Focus visible */
.recommend-btn:focus-visible,
.action-tile:focus-visible,
.module-panel:focus-visible,
.text-link:focus-visible,
.state-btn:focus-visible {
  outline: 3px solid rgba(79, 70, 229, 0.3);
  outline-offset: 2px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
</style>

