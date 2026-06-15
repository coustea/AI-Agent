<template>
  <main class="home-workspace">
    <div class="workspace-grid" v-if="recommendationData && profileRadarData">
      <!-- 第一行：学习总览 + 画像雷达 -->
      <BaseCard class="overview-card span-8" padding="large">
        <div class="overview-decoration"></div>
        <div class="overview-main">
          <div class="overview-copy">
            <BaseTag tone="indigo" pill class="overview-badge">
              <span class="badge-dot"></span>{{ recommendationData.recommendation.label || '智能推荐' }}
            </BaseTag>
            <h1>今天，从哪里继续？</h1>
            <p class="overview-desc">
              根据你的画像分数、学习路径进度和最近练习表现，系统已整理好下一步学习建议。
            </p>
          </div>
          <div class="date-panel">
            <span>{{ todayText }}</span>
            <strong>{{ todayWeekday }}</strong>
          </div>
        </div>

        <div class="primary-task">
          <div class="task-info">
            <span class="section-label">主推荐任务</span>
            <h2>{{ recommendationData.recommendation.title }}</h2>
            <p>{{ recommendationData.recommendation.text }}</p>
          </div>
          <BaseButton size="large" class="primary-task-btn" @click="goTo(recommendationData.recommendation.path)">
            <el-icon><component :is="getIconComponent(recommendationData.recommendation.icon)" /></el-icon>
            {{ recommendationData.recommendation.action }}
          </BaseButton>
        </div>

        <div class="overview-stats">
          <div class="overview-stat" v-for="item in overviewStats" :key="item.label">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </div>
        </div>
      </BaseCard>

      <BaseCard class="radar-card span-4" padding="large">
        <div class="radar-header">
          <div>
            <span class="section-label">学习画像</span>
            <h2>画像雷达图</h2>
          </div>
          <button class="text-link" @click="goTo(profilePath)">
            {{ profileRadarData.radar?.link_label || '完整画像' }}
          </button>
        </div>

        <div class="radar-chart-wrapper" v-loading="loading">
          <v-chart class="chart" :option="radarOption" autoresize />
        </div>

        <p class="radar-note">
          {{ profileRadarData.radar?.note || `综合画像分 ${profileScore}，薄弱方向：${weakAreaText}` }}
        </p>
      </BaseCard>

      <!-- 第二行：继续学习 + 今日建议/每日挑战 -->
      <BaseCard class="continue-card span-8">
        <div class="card-head">
          <div>
            <span class="section-label">学习进度</span>
            <h2>继续学习</h2>
          </div>
          <button class="text-link" @click="goTo('/path-planner')">查看全部</button>
        </div>

        <div class="study-table">
          <div class="study-table-head">
            <span>学习项</span>
            <span>进度</span>
            <span>上次学习</span>
            <span>操作</span>
          </div>
          <div class="study-row" v-for="item in continueItems" :key="item.title">
            <div class="study-title-cell">
              <div :class="['study-icon', item.tone]">
                <el-icon><component :is="getIconComponent(item.icon)" /></el-icon>
              </div>
              <div>
                <strong>{{ item.title }}</strong>
                <span>{{ item.category }}</span>
              </div>
            </div>
            <div class="progress-cell">
              <div class="mini-progress"><i :style="{ width: item.progress + '%' }"></i></div>
              <span>{{ item.progress }}%</span>
            </div>
            <span class="last-time">{{ item.lastTime }}</span>
            <button class="row-action" @click="goTo(item.path)">继续学习</button>
          </div>
        </div>
      </BaseCard>

      <aside class="side-stack span-4">
        <BaseCard class="suggestion-card">
          <div class="card-head compact">
            <div>
              <span class="section-label">画像驱动</span>
              <h2>今日建议</h2>
            </div>
          </div>
          <div class="suggestion-list">
            <button
              class="suggestion-item"
              v-for="item in todaySuggestions"
              :key="item.title"
              @click="goTo(item.path)"
            >
              <span :class="['suggestion-dot', item.tone]"></span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.reason }}</p>
              </div>
              <span class="chevron">›</span>
            </button>
          </div>
        </BaseCard>

        <BaseCard class="challenge-card">
          <div class="challenge-top">
            <div>
              <span class="section-label">每日挑战</span>
              <h2>{{ dailyChallenge.title }}</h2>
            </div>
            <BaseTag>{{ dailyChallenge.difficulty }}</BaseTag>
          </div>
          <p>{{ dailyChallenge.reason }}</p>
          <div class="challenge-meta">
            <span>预计 {{ dailyChallenge.minutes }} 分钟</span>
            <span>{{ dailyChallenge.source }}</span>
          </div>
          <BaseButton class="challenge-btn" size="small" @click="goTo('/question-bank')">开始挑战</BaseButton>
        </BaseCard>
      </aside>

      <!-- 第三行：最近生成 + 快速开始 -->
      <BaseCard class="recent-card span-8">
        <div class="card-head">
          <div>
            <span class="section-label">资源产物</span>
            <h2>最近生成</h2>
          </div>
          <button class="text-link" @click="goTo('/resource-generator')">进入资源工坊</button>
        </div>

        <div class="resource-table">
          <div class="resource-table-head">
            <span>名称</span>
            <span>类型</span>
            <span>来源智能体</span>
            <span>生成时间</span>
            <span>操作</span>
          </div>
          <div class="resource-row" v-for="item in recentGeneratedItems" :key="item.title">
            <strong>{{ item.title }}</strong>
            <span>{{ item.type }}</span>
            <span>{{ item.agent }}</span>
            <span>{{ item.time }}</span>
            <button class="row-action" @click="goTo(item.path)">打开</button>
          </div>
        </div>
      </BaseCard>

      <BaseCard class="quick-card span-4">
        <div class="card-head compact">
          <div>
            <span class="section-label">操作入口</span>
            <h2>快速开始</h2>
          </div>
        </div>
        <div class="quick-list">
          <button
            class="quick-item"
            v-for="action in quickActions"
            :key="action.label"
            @click="goTo(action.path)"
          >
            <div :class="['quick-icon', actionIconClass(action.icon)]">
              <el-icon><component :is="getIconComponent(action.icon)" /></el-icon>
            </div>
            <div>
              <strong>{{ action.label }}</strong>
              <p>{{ action.description }}</p>
            </div>
            <span class="chevron">›</span>
          </button>
        </div>
      </BaseCard>

    </div>

    <section v-else class="home-state-panel" v-loading="loading">
      <div class="state-copy">
        <span class="state-badge">{{ loading ? '加载中' : '加载失败' }}</span>
        <h1>{{ loading ? '正在同步学习控制台' : '首页数据加载失败' }}</h1>
        <p>{{ loading ? '正在读取画像、路径、资源和学习事件...' : (loadError || '暂时无法获取数据') }}</p>
        <BaseButton v-if="!loading" class="state-btn" @click="loadAllData">重新加载</BaseButton>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import BaseCard from '@/shared/ui/BaseCard.vue'
import BaseButton from '@/shared/ui/BaseButton.vue'
import BaseTag from '@/shared/ui/BaseTag.vue'

import {
  getRecommendation,
  getProfileRadar,
  getContinueLearning,
  getQuickActions,
  getRecentResources,
  getDailyChallenge,
  getStudyStats,
  type RecommendationData,
  type ProfileRadarData,
  type ContinueLearningData,
  type QuickActionsData,
  type RecentResourceItem,
  type DailyChallengeData,
  type StudyStatsData,
  type HomeActionItem,
} from '@/features/dashboard/api/home'
import { getRadarChartData } from '@/features/profile/model/profileViewModel'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

import {
  ChatDotRound,
  DocumentCopy,
  EditPen,
  Guide,
  Monitor,
  Reading
} from '@element-plus/icons-vue'

use([CanvasRenderer, RadarChart, TooltipComponent])

interface ContinueItem {
  title: string
  category: string
  progress: number
  lastTime: string
  path: string
  icon: string
  tone: string
}

interface SuggestionItem {
  title: string
  reason: string
  path: string
  tone: string
}

interface ResourceItem {
  title: string
  type: string
  agent: string
  time: string
  path: string
}

const router = useRouter()
const route = useRoute()

const recommendationData = ref<RecommendationData | null>(null)
const profileRadarData = ref<ProfileRadarData | null>(null)
const continueLearningData = ref<ContinueLearningData | null>(null)
const quickActionsData = ref<QuickActionsData | null>(null)
const recentResourcesData = ref<RecentResourceItem[]>([])
const dailyChallengeData = ref<DailyChallengeData | null>(null)
const studyStatsData = ref<StudyStatsData | null>(null)
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
    default: return DocumentCopy
  }
}

const actionIconClass = (iconName: string) => {
  switch (iconName) {
    case 'chat': return 'icon-blue'
    case 'resource': return 'icon-indigo'
    case 'path': return 'icon-emerald'
    case 'practice': return 'icon-amber'
    case 'monitor': return 'icon-purple'
    default: return 'icon-blue'
  }
}

const clampPercent = (value: unknown, fallback = 0) => {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return fallback
  const normalized = numberValue <= 1 ? numberValue * 100 : numberValue
  return Math.max(0, Math.min(100, Math.round(normalized)))
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

const formatDateTime = (value?: string | null) => {
  if (!value) return '暂无记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '暂无记录'

  const now = new Date()
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const time = new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date)

  const isSameDay = (a: Date, b: Date) => (
    a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate()
  )

  if (isSameDay(date, now)) return `今天 ${time}`
  if (isSameDay(date, yesterday)) return `昨天 ${time}`
  return `${formatDate(value)} ${time}`
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

const todayText = computed(() => new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric'
}).format(new Date()))

const todayWeekday = computed(() => new Intl.DateTimeFormat('zh-CN', {
  weekday: 'long'
}).format(new Date()))

// removed activeDashboardTab

const modelProvider = computed(() => 'DeepSeek')

const profilePath = computed(() => profileRadarData.value?.radar?.path || '/profile')

const radarSource = computed<any>(() => {
  if (!profileRadarData.value) return null
  return getRadarChartData(profileRadarData.value)
})

const radarValues = computed<number[]>(() => {
  const rawValues = radarSource.value?.series?.[0]?.data?.[0]?.value
  if (!Array.isArray(rawValues)) return []
  return rawValues.map((item: unknown) => clampPercent(item))
})

const radarOption = computed(() => {
  const rawData = radarSource.value
  if (!rawData?.radar) return {}

  return {
    ...rawData,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: 'rgba(226, 232, 240, 0.95)',
      textStyle: { color: '#334155', fontSize: 12 }
    },
    radar: {
      ...rawData.radar,
      radius: '64%',
      center: ['50%', '52%'],
      splitNumber: 4,
      splitLine: { lineStyle: { color: 'rgba(203, 213, 225, 0.55)', width: 1 } },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(248, 250, 252, 0.85)', 'rgba(239, 246, 255, 0.65)']
        }
      },
      axisLine: { lineStyle: { color: 'rgba(203, 213, 225, 0.55)' } },
      axisName: { color: '#64748B', fontSize: 11, fontWeight: 600 }
    },
    series: [{
      type: 'radar',
      data: [{
        value: rawData.series?.[0]?.data?.[0]?.value || [],
        name: '能力得分',
        areaStyle: { color: 'rgba(79, 70, 229, 0.16)' },
        lineStyle: { color: '#4F46E5', width: 2 },
        itemStyle: { color: '#4F46E5', borderColor: '#ffffff', borderWidth: 2 },
        symbolSize: 5
      }]
    }]
  }
})

const profileScore = computed(() => {
  const raw = profileRadarData.value as any
  const candidate = raw?.overall_score ?? raw?.total_score ?? raw?.score ?? raw?.profile_score ?? raw?.composite_score
  if (candidate !== undefined && candidate !== null) return clampPercent(candidate, 82)

  const values = radarValues.value
  if (!values.length) return 82
  return clampPercent(values.reduce((sum, value) => sum + value, 0) / values.length, 82)
})

const profileDimensions = computed(() => {
  const fallback = [
    { name: '知识掌握度', score: 76 },
    { name: '学习活跃度', score: 88 },
    { name: '路径完成度', score: 64 },
    { name: '资源匹配度', score: 91 }
  ]

  const indicators = radarSource.value?.radar?.indicator
  if (!Array.isArray(indicators) || !radarValues.value.length) return fallback

  return fallback.map((item, index) => ({
    name: indicators[index]?.name || item.name,
    score: radarValues.value[index] ?? item.score
  }))
})

const weakAreas = computed(() => {
  const backendWeakAreas = profileRadarData.value?.weak_areas
  if (Array.isArray(backendWeakAreas) && backendWeakAreas.length) {
    return backendWeakAreas.slice(0, 3).map((item: unknown) => String(item))
  }

  const lowDimensions = profileDimensions.value
    .filter(item => item.score < 75)
    .sort((a, b) => a.score - b.score)
    .map(item => item.name)

  return lowDimensions.length ? lowDimensions.slice(0, 2) : ['图论', '动态规划']
})

const weakAreaText = computed(() => weakAreas.value.join(' / '))

const overviewStats = computed(() => {
  const stats = studyStatsData.value
  return [
    { label: '本周学习', value: `${stats?.weekly_days ?? 5} 天` },
    { label: '累计学习', value: `${stats?.total_hours ?? 27} 小时` },
    { label: '待完成节点', value: `${stats?.pending_nodes ?? 3} 个` },
    { label: '今日建议', value: `${stats?.today_suggestions ?? 4} 条` }
  ]
})

const pathModulePath = computed(() => '/path-planner')

const nodeLastTime = (node: any, activePath: any): string => {
  if (node.completed_at) return formatDateTime(node.completed_at)
  if (node.started_at) return formatDateTime(node.started_at)
  return formatDateTime(activePath?.last_learned_at || activePath?.updated_at)
}

const continueItems = computed<ContinueItem[]>(() => {
  const data = continueLearningData.value
  const activePath = data?.active_path
  const nodes = data?.nodes || []

  if (!activePath && !nodes.length) {
    return [
      { title: '快速排序', category: '算法 / 排序算法', progress: 68, lastTime: '今天 09:32', path: '/path-planner', icon: 'path', tone: 'tone-indigo' },
      { title: '图的遍历', category: '数据结构 / 图', progress: 42, lastTime: '昨天 20:15', path: '/path-planner', icon: 'reading', tone: 'tone-emerald' },
      { title: '动态规划', category: '算法进阶', progress: 25, lastTime: '5月20日 15:40', path: '/path-planner', icon: 'practice', tone: 'tone-amber' }
    ]
  }

  const items: ContinueItem[] = []

  if (activePath) {
    items.push({
      title: activePath.current_node_title || activePath.title || '继续当前学习路径',
      category: activePath.title || '学习路径',
      progress: clampPercent(activePath.overall_progress, 0),
      lastTime: formatDateTime(activePath.last_learned_at || activePath.updated_at),
      path: pathModulePath.value,
      icon: 'path',
      tone: 'tone-emerald'
    })
  }

  for (const node of nodes) {
    if (items.some(item => item.title === node.title)) continue
    const progress = node.progress ?? 0
    const isCompleted = progress >= 100
    items.push({
      title: node.title,
      category: activePath?.title || '学习路径',
      progress,
      lastTime: nodeLastTime(node, activePath),
      path: pathModulePath.value,
      icon: isCompleted ? 'reading' : 'path',
      tone: isCompleted ? 'tone-indigo' : 'tone-emerald',
    })
  }

  return items.slice(0, 5)
})

const todaySuggestions = computed<SuggestionItem[]>(() => {
  const backendSuggestions = quickActionsData.value?.today_suggestions
  if (Array.isArray(backendSuggestions) && backendSuggestions.length) {
    return backendSuggestions.slice(0, 3).map((item: any, index: number) => ({
      title: item.title || item.label || '学习建议',
      reason: item.reason || item.description || '根据当前画像自动推荐',
      path: item.path || '/path-planner',
      tone: ['blue', 'amber', 'green'][index] || 'blue'
    }))
  }

  const mainTitle = recommendationData.value?.recommendation?.title || '当前学习任务'
  const weakArea = weakAreas.value[0] || '薄弱知识点'
  return [
    {
      title: `继续学习「${mainTitle}」`,
      reason: `画像分 ${profileScore.value}，建议优先推进当前主线任务`,
      path: recommendationData.value?.recommendation?.path || '/path-planner',
      tone: 'blue'
    },
    {
      title: `完成「${weakArea}」专项练习`,
      reason: `${weakArea} 维度偏弱，需要通过题目巩固`,
      path: '/question-bank',
      tone: 'amber'
    },
    {
      title: '复习最近错题与生成资料',
      reason: '用错题和资源回顾保持知识稳定度',
      path: '/mistake-book',
      tone: 'green'
    }
  ]
})

const dailyChallenge = computed(() => {
  const challenge = dailyChallengeData.value
  if (challenge) {
    return {
      title: challenge.subject || '二叉树层序遍历',
      difficulty: challenge.difficulty || '中等',
      minutes: challenge.estimated_minutes || 12,
      source: challenge.source || '题库推荐',
      reason: challenge.reason || `推荐你从「${challenge.subject}」切入，保持每日练习节奏。`
    }
  }
  return {
    title: '二叉树层序遍历',
    difficulty: '中等',
    minutes: 12,
    source: '画像推荐',
    reason: `根据你的薄弱方向「${weakAreaText.value}」生成今日挑战。`
  }
})

const quickActions = computed<HomeActionItem[]>(() => {
  const actions = quickActionsData.value?.actions || []
  if (actions.length) return actions.slice(0, 6)

  return [
    { label: '新建对话辅导', description: '向智能体提问或获取学习指导', path: '/chat', icon: 'chat' },
    { label: '进入资源工坊', description: '生成文档、题库、代码和图解', path: '/resource-generator', icon: 'resource' },
    { label: '开始智能测评', description: '评估知识掌握情况', path: '/assessment', icon: 'practice' },
    { label: '规划学习路径', description: '定制你的阶段学习计划', path: '/path-planner', icon: 'path' },
    { label: '查看错题本', description: '复习历史错题与薄弱点', path: '/mistake-book', icon: 'reading' },
    { label: '查看我的画像', description: '查看画像雷达和维度分析', path: profilePath.value, icon: 'monitor' }
  ]
})

const recentGeneratedItems = computed<ResourceItem[]>(() => {
  const list = recentResourcesData.value
  if (list.length) {
    return list.slice(0, 4).map((item: any) => ({
      title: item.title || item.name || '未命名资源',
      type: item.type || item.resource_type || resourceStatusLabel(item.status),
      agent: item.agent || item.source_agent || '资源生成智能体',
      time: formatDateTime(item.created_at || item.updated_at),
      path: item.id ? `/resource-detail/${item.id}` : '/resource-generator'
    }))
  }

  return [
    { title: '快速排序代码实现与测试', type: '代码文件', agent: '代码智造师', time: '今天 10:18', path: '/resource-generator' },
    { title: '排序算法对比分析', type: '文档', agent: '知识分析师', time: '昨天 20:07', path: '/resource-generator' },
    { title: '图的遍历可视化演示', type: '可视化', agent: '可视化工匠', time: '昨天 19:44', path: '/resource-generator' },
    { title: '动态规划经典题汇总', type: '题库', agent: '测评专家', time: '5月20日 16:02', path: '/question-bank' }
  ]
})

const loadAllData = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [
      recRes,
      radarRes,
      continueRes,
      actionsRes,
      resourcesRes,
      challengeRes,
      statsRes,
    ] = await Promise.all([
      getRecommendation(),
      getProfileRadar(),
      getContinueLearning(),
      getQuickActions(),
      getRecentResources(),
      getDailyChallenge(),
      getStudyStats(),
    ])

    recommendationData.value = recRes.data.data
    profileRadarData.value = radarRes.data.data
    continueLearningData.value = continueRes.data.data
    quickActionsData.value = actionsRes.data.data
    recentResourcesData.value = resourcesRes.data.data ?? []
    dailyChallengeData.value = challengeRes.data.data ?? null
    studyStatsData.value = statsRes.data.data
  } catch (error) {
    console.error('Failed to load dashboard data', error)
    recommendationData.value = null
    profileRadarData.value = null
    loadError.value = '后端接口暂时不可用，请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(loadAllData)

// 每次路由切换到 dashboard 页面时自动刷新数据
watch(
  () => route.path,
  (newPath) => {
    if (newPath === '/dashboard') {
      loadAllData()
    }
  }
)
</script>

<style scoped>
.home-workspace {
  min-height: calc(100vh - var(--navbar-height, 64px));
  padding: var(--space-6) var(--space-8) var(--space-8);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  overflow-y: auto;
}

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--space-5);
  max-width: var(--page-max-width, 1400px);
  margin: 0 auto;
  padding-bottom: var(--space-8);
}

.span-4 { grid-column: span 4; }
.span-8 { grid-column: span 8; }
.span-12 { grid-column: span 12; }

.top-status {
  min-height: 44px;
  padding: 0 var(--space-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.breadcrumb-area,
.system-status,
.status-pill {
  display: inline-flex;
  align-items: center;
}

.breadcrumb-area { gap: 8px; }
.breadcrumb-area strong { color: var(--color-text); }
.slash { color: var(--color-text-light); }

.home-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--color-primary);
  box-shadow: 0 0 0 4px var(--color-primary-soft);
}

.system-status { gap: 10px; flex-wrap: wrap; justify-content: flex-end; }

.status-pill {
  min-height: 28px;
  padding: 0 var(--space-2\.5);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 6px;
  background: var(--color-success);
}

.overview-card,
.radar-card,
.continue-card,
.recent-card,
.quick-card,
.suggestion-card,
.challenge-card {
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04) !important;
}

.overview-card {
  position: relative;
  min-height: 320px;
  overflow: hidden;
  background: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
}

.overview-decoration {
  position: absolute;
  right: -80px;
  top: -90px;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(79, 70, 229, 0.12) 0%, rgba(79, 70, 229, 0) 68%);
  pointer-events: none;
}

.overview-main,
.primary-task,
.overview-stats,
.card-head,
.challenge-top,
.agent-title-row,
.dimension-meta,
.study-table-head,
.study-row,
.resource-table-head,
.resource-row {
  position: relative;
  z-index: 1;
}

.overview-main {
  display: flex;
  justify-content: space-between;
  gap: var(--space-6);
  align-items: flex-start;
  margin-bottom: var(--space-7);
}

.overview-copy h1 {
  margin: var(--space-3) 0 var(--space-2\.5);
  color: var(--color-text-strong);
  font-size: clamp(var(--text-2xl), 3vw, var(--text-3xl));
  line-height: 1.15;
  font-weight: var(--weight-extrabold);
  letter-spacing: -0.04em;
}

.overview-desc {
  max-width: 680px;
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
}

.overview-badge {
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.12);
}

.badge-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  margin-right: 5px;
}

.date-panel {
  min-width: 150px;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid var(--color-border-light);
  text-align: right;
}

.date-panel span,
.date-panel strong {
  display: block;
}

.date-panel span {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  margin-bottom: var(--space-1);
}

.date-panel strong {
  color: var(--color-text-strong);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
}

.primary-task {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.78);
}

.task-info h2 {
  margin: var(--space-1\.5) 0 var(--space-2);
  color: var(--color-text-strong);
  font-size: var(--text-xl);
  line-height: 1.3;
}

.task-info p {
  margin: 0;
  max-width: 640px;
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
}

.section-label {
  display: inline-flex;
  align-items: center;
  color: var(--color-primary);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.primary-task-btn {
  min-width: 138px;
  flex-shrink: 0;
  justify-content: center;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-2\.5);
  margin-top: var(--space-5);
}

.overview-stat {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.75);
}

.overview-stat strong,
.overview-stat span {
  display: block;
}

.overview-stat strong {
  color: var(--color-primary);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  margin-bottom: var(--space-0\.5);
}

.overview-stat span {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.radar-card {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.radar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
  position: relative;
  z-index: 1;
}

.radar-header h2 {
  margin: 5px 0 0;
  color: var(--color-text);
  font-size: 1.08rem;
  line-height: 1.35;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.card-head.compact { margin-bottom: 10px; }

.card-head h2,
.challenge-top h2 {
  margin: var(--space-1\.5) 0 0;
  color: var(--color-text-strong);
  font-size: var(--text-lg);
  line-height: 1.3;
}

.text-link {
  border: none;
  background: transparent;
  padding: var(--space-1) var(--space-0\.5);
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
  transition: opacity 150ms ease;
}

.text-link:hover,
.row-action:hover { opacity: 0.72; }

.radar-chart-wrapper {
  flex: 1;
  min-height: 228px;
  margin-top: 4px;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
}

.chart {
  width: 100%;
  height: 100%;
  min-height: 228px;
}

.radar-note {
  margin: var(--space-3) 0 0;
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.bar-track,
.mini-progress,
.agent-progress {
  height: 7px;
  border-radius: 999px;
  background: #edf1f7;
  overflow: hidden;
}

.bar-track i,
.mini-progress i,
.agent-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-primary), #818cf8);
}

.continue-card,
.recent-card,
.quick-card,
.suggestion-card,
.challenge-card {
  background: #ffffff;
}

.study-table,
.resource-table {
  display: grid;
  gap: 4px;
}

.study-table-head,
.study-row {
  display: grid;
  grid-template-columns: minmax(260px, 1.55fr) minmax(140px, 0.75fr) minmax(110px, 0.65fr) 82px;
  gap: 16px;
  align-items: center;
}

.study-table-head,
.resource-table-head {
  padding: 0 var(--space-3) var(--space-2\.5);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  border-bottom: 1px solid var(--color-border-light);
  letter-spacing: 0.03em;
}

.study-row,
.resource-row {
  min-height: 64px;
  padding: 10px 12px;
  border-radius: 14px;
  transition: background var(--transition-base);
}

.study-row:hover,
.resource-row:hover {
  background: #f8fafc;
}

.study-title-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.study-title-cell strong,
.study-title-cell span {
  display: block;
}

.study-title-cell strong,
.resource-row strong {
  color: var(--color-text-strong);
  font-size: var(--text-base);
  line-height: 1.4;
}

.study-title-cell span,
.last-time,
.resource-row span {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.study-icon,
.quick-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 14px;
}

.study-icon {
  width: 38px;
  height: 38px;
  font-size: 1.16rem;
}

.tone-indigo,
.icon-indigo { background: var(--color-primary-soft); color: var(--color-primary); }
.tone-emerald,
.icon-emerald { background: rgba(16, 185, 129, 0.12); color: var(--color-success); }
.tone-amber,
.icon-amber { background: rgba(245, 158, 11, 0.14); color: var(--color-warning); }
.icon-blue { background: rgba(59, 130, 246, 0.11); color: #2563eb; }
.icon-purple { background: rgba(124, 58, 237, 0.1); color: #7c3aed; }

.progress-cell {
  display: grid;
  grid-template-columns: minmax(70px, 1fr) 42px;
  align-items: center;
  gap: 8px;
}

.progress-cell span {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
}

.row-action {
  border: none;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
  text-align: left;
  transition: opacity 150ms ease;
}

.side-stack {
  display: grid;
  gap: 18px;
}

.suggestion-list,
.quick-list {
  display: grid;
  gap: 8px;
}

.suggestion-item,
.quick-item {
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  display: grid;
  align-items: center;
  transition: background var(--transition-base), transform var(--transition-base);
}

.suggestion-item {
  grid-template-columns: 10px minmax(0, 1fr) 14px;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--color-border-light);
}

.suggestion-item:last-child { border-bottom: none; }

.suggestion-item:hover,
.quick-item:hover {
  background: #f8fafc;
}

.suggestion-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.suggestion-dot.blue { background: var(--color-primary); }
.suggestion-dot.amber { background: var(--color-warning); }
.suggestion-dot.green { background: var(--color-success); }

.suggestion-item strong,
.quick-item strong {
  display: block;
  color: var(--color-text-strong);
  font-size: var(--text-base);
  line-height: 1.35;
  margin-bottom: var(--space-1);
}

.suggestion-item p,
.quick-item p,
.challenge-card p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.chevron {
  color: var(--color-text-light);
  font-size: 1.25rem;
}

.challenge-card {
  border-left: 3px solid var(--color-warning) !important;
}

.challenge-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.challenge-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin: var(--space-3) 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}

.challenge-btn { width: 100%; justify-content: center; }

.resource-table-head,
.resource-row {
  display: grid;
  grid-template-columns: minmax(260px, 1.5fr) minmax(80px, 0.52fr) minmax(120px, 0.7fr) minmax(100px, 0.64fr) 52px;
  gap: 14px;
  align-items: center;
}

.quick-item {
  grid-template-columns: 42px minmax(0, 1fr) 16px;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 16px;
  background: #ffffff;
}

.quick-icon {
  width: 42px;
  height: 42px;
  font-size: 1.16rem;
}

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
  margin: 0 0 var(--space-2\.5) 0;
  color: var(--color-text-strong);
  font-size: var(--text-2xl);
  line-height: 1.25;
}

.state-copy p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  line-height: var(--leading-normal);
}

.state-btn {
  margin-top: 20px;
  border: none;
  background: var(--color-primary);
  color: #ffffff;
  border-radius: var(--radius-base);
  padding: 10px 20px;
  font-weight: 700;
  cursor: pointer;
  transition: background var(--transition-base);
}

.state-btn:hover { background: var(--color-primary-hover); }

.text-link:focus-visible,
.row-action:focus-visible,
.quick-item:focus-visible,
.suggestion-item:focus-visible,
.primary-task-btn:focus-visible,
.state-btn:focus-visible {
  outline: 3px solid rgba(79, 70, 229, 0.3);
  outline-offset: 2px;
}

@media (max-width: 1200px) {
  .span-4,
  .span-8 { grid-column: span 12; }
  .side-stack { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 900px) {
  .home-workspace { padding: var(--space-4) var(--space-4) var(--space-5); }
  .top-status,
  .overview-main,
  .primary-task,
  .card-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .system-status { justify-content: flex-start; }
  .date-panel { text-align: left; }
  .overview-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .study-table-head,
  .resource-table-head { display: none; }
  .study-row,
  .resource-row {
    grid-template-columns: 1fr;
    gap: var(--space-2\.5);
    align-items: flex-start;
    border: 1px solid var(--color-border-light);
  }
  .row-action { padding: 0; }
  .side-stack { grid-template-columns: 1fr; }
}

@media (max-width: 640px) {
  .home-workspace { padding: var(--space-3); }
  .workspace-grid { gap: var(--space-3); }
  .overview-stats { grid-template-columns: 1fr; }
  .primary-task-btn { width: 100%; }
  .overview-copy h1 { font-size: var(--text-xl); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
