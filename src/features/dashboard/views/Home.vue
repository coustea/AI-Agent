<template>
  <main class="home-page min-h-screen font-sans antialiased">
    <div class="home-shell">
      
      <div class="dashboard-grid" v-if="recommendationData && profileRadarData">
        
        <!-- ================= LEFT COLUMN (col-span-8) ================= -->
        <div class="primary-column">
          
          <!-- Block 1: Welcome & Today Header (Cardless) -->
          <section class="recommendation-panel">
            <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
              <div class="space-y-1">
                <span class="inline-flex items-center gap-1.5 text-[9px] font-mono font-bold bg-blue/10 text-blue px-2 py-0.5 rounded-sm">
                  <span class="w-1.5 h-1.5 rounded-sm bg-blue animate-pulse"></span>
                  {{ recommendationData.recommendation.label || '智能推荐' }}
                </span>
                <h1 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight leading-tight">今天，从哪里继续？</h1>
                <p class="text-xs text-slate-500 leading-relaxed max-w-[600px]">
                  根据你的画像分数、学习路径进度和最近练习表现，系统已整理好下一步学习建议。
                </p>
              </div>

              <!-- Today Date Display -->
              <div class="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-sm shrink-0 font-mono text-xs">
                <Calendar class="w-3.5 h-3.5 text-slate-400" />
                <span class="text-slate-500">{{ todayText }}</span>
                <span class="text-slate-300">|</span>
                <span class="font-bold text-slate-800">{{ todayWeekday }}</span>
              </div>
            </div>

            <!-- Recommended Action (Editorial Banner, Cardless) -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-6 py-6 px-1 border-t border-b border-slate-100">
              <div class="space-y-1 min-w-0">
                <span class="text-[9px] font-mono text-blue font-black uppercase tracking-wider block">推荐学习项目</span>
                <h2 class="text-sm font-bold text-slate-900 truncate">{{ recommendationData.recommendation.title }}</h2>
                <p class="text-xs text-slate-500 leading-relaxed truncate">{{ recommendationData.recommendation.text }}</p>
              </div>
              <Button class="shrink-0 h-9 px-4 rounded-sm text-xs font-semibold cursor-pointer border border-blue text-blue hover:bg-blue/5 bg-transparent shadow-none" @click="goTo(recommendationData.recommendation.path)">
                <component :is="getIconComponent(recommendationData.recommendation.icon)" class="w-3.5 h-3.5 mr-2" />
                <span>{{ recommendationData.recommendation.action }}</span>
              </Button>
            </div>

            <!-- Stats Quantitative Indicators (Cardless Grid) -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-6 pt-2">
              <div class="space-y-1" v-for="item in overviewStats" :key="item.label">
                <span class="text-[9px] text-slate-400 font-mono uppercase tracking-wider block">{{ item.label }}</span>
                <strong class="text-xl font-extrabold text-slate-950 font-mono tracking-tight block mt-0.5">{{ item.value }}</strong>
              </div>
            </div>
          </section>

          <!-- Block 2: Continue Learning Section (Cardless List) -->
          <section class="learning-panel">
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest block">PROGRESS TRACKING</span>
                <h2 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">继续学习进度</h2>
              </div>
              <Button variant="ghost" class="text-xs font-bold text-blue hover:text-blue/80 p-0 cursor-pointer h-7" @click="goTo('/path-planner')" v-if="continueItems.length">
                查看全部
              </Button>
            </div>

            <!-- Learning Items List -->
            <div v-if="continueItems.length" class="divide-y divide-slate-100">
              <div 
                v-for="item in continueItems" 
                :key="item.title" 
                class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4 first:pt-0 last:pb-0 hover:bg-slate-50/40 rounded-sm px-2 transition-colors"
              >
                <!-- Title & info -->
                <div class="flex items-center gap-3 min-w-0">
                  <div class="w-8 h-8 rounded-sm flex items-center justify-center shrink-0" :class="item.tone === 'tone-emerald' ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue'">
                    <component :is="getIconComponent(item.icon)" class="w-4 h-4" />
                  </div>
                  <div class="min-w-0">
                    <strong class="text-xs font-bold text-slate-800 block truncate">{{ item.title }}</strong>
                    <span class="text-[10px] text-slate-400 block mt-0.5">{{ item.category }}</span>
                  </div>
                </div>

                <!-- Progress & action -->
                <div class="flex items-center gap-6 justify-between sm:justify-end">
                  <div class="flex items-center gap-2">
                    <div class="w-24 h-1 bg-slate-100 rounded-sm overflow-hidden shrink-0">
                      <div class="h-full bg-emerald-500 rounded-sm" :style="{ width: item.progress + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono font-bold text-slate-700 min-w-[28px] text-right">{{ item.progress }}%</span>
                  </div>
                  <span class="text-[10px] text-slate-400 font-mono hidden md:inline">{{ item.lastTime }}</span>
                  <Button variant="outline" size="sm" class="text-[10px] h-7 px-3 border-slate-200 hover:bg-slate-50 rounded-sm shrink-0 cursor-pointer bg-white" @click="goTo(item.path)">
                    继续
                  </Button>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="py-10 border border-dashed border-slate-200/60 rounded-sm flex flex-col items-center justify-center text-slate-400 text-xs space-y-3">
              <p>还没有学习路径，开始规划你的学习计划吧</p>
              <Button size="sm" class="rounded-sm text-xs font-semibold cursor-pointer" @click="goTo('/path-planner')">
                开始规划
              </Button>
            </div>
          </section>

          <!-- Block 3: Recently Generated Resources (Cardless List) -->
          <section class="resource-panel">
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest block">GENERATED ARTIFACTS</span>
                <h2 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">最近生成资源</h2>
              </div>
              <Button variant="ghost" class="text-xs font-bold text-blue hover:text-blue/80 p-0 cursor-pointer h-7" @click="goTo('/resource-generator')" v-if="recentGeneratedItems.length">
                进入资源工坊
              </Button>
            </div>

            <!-- Generated resources list -->
            <div v-if="recentGeneratedItems.length" class="divide-y divide-slate-100">
              <div 
                v-for="item in recentGeneratedItems" 
                :key="item.title" 
                class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4 first:pt-0 last:pb-0 hover:bg-slate-50/40 rounded-sm px-2 transition-colors"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <div class="w-8 h-8 rounded-sm bg-slate-50 flex items-center justify-center shrink-0">
                    <FileText class="w-4 h-4 text-slate-400" />
                  </div>
                  <div class="min-w-0">
                    <strong class="text-xs font-bold text-slate-800 block truncate">{{ item.title }}</strong>
                    <div class="flex items-center gap-2 mt-0.5">
                      <span class="text-[9px] font-mono text-slate-400 uppercase">{{ item.type }}</span>
                      <span class="text-slate-200 text-[10px]">|</span>
                      <span class="text-[9px] text-slate-400 truncate">{{ item.agent }}</span>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-4 justify-between sm:justify-end shrink-0">
                  <span class="text-[9px] text-slate-400 font-mono">{{ item.time }}</span>
                  <Button variant="outline" size="sm" class="text-[10px] h-7 px-3 border-slate-200 hover:bg-slate-50 rounded-sm cursor-pointer bg-white" @click="goTo(item.path)">
                    打开
                  </Button>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="py-10 border border-dashed border-slate-200/60 rounded-sm flex flex-col items-center justify-center text-slate-400 text-xs space-y-3">
              <p>还没有生成过资源，开始创建你的第一个学习资源吧</p>
              <Button size="sm" class="rounded-sm text-xs font-semibold cursor-pointer" @click="goTo('/resource-generator')">
                生成资源
              </Button>
            </div>
          </section>

        </div>

        <!-- ================= RIGHT COLUMN (col-span-4) ================= -->
        <aside class="insight-column">
          
          <!-- Block 1: Radar Chart (Cardless) -->
          <section class="radar-panel">
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest block">CAPABILITY PROFILE</span>
                <h2 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">画像雷达能力图</h2>
              </div>
              <Button variant="ghost" class="text-xs font-bold text-blue hover:text-blue/80 p-0 cursor-pointer h-7" @click="goTo(profilePath)">
                完整画像
              </Button>
            </div>

            <!-- Radar chart ECharts container -->
            <div class="radar-canvas h-[248px] relative overflow-hidden">
              <div v-if="loading" class="absolute inset-0 flex flex-col items-center justify-center text-slate-400 text-xs space-y-2">
                <div class="w-5 h-5 rounded-sm border border-blue border-t-transparent animate-spin"></div>
                <span>读取能力维度...</span>
              </div>
              <v-chart v-else class="chart" :option="radarOption" autoresize />
            </div>

            <!-- Headline Score note -->
            <div class="p-3 bg-slate-50 border border-slate-100/80 rounded-sm text-xs text-slate-500 leading-relaxed font-medium">
              {{ profileRadarData.radar?.note || `综合画像分 ${profileScore}，薄弱方向：${weakAreaText}` }}
            </div>
          </section>

          <!-- Block 2: Today Suggestions (Cardless) -->
          <section class="suggestion-panel">
            <div class="space-y-0.5">
              <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest block">PERSONALIZED RECOMMENDATION</span>
              <h2 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">今日能力画像建议</h2>
            </div>

            <!-- Suggestion items list -->
            <div v-if="todaySuggestions.length" class="space-y-2">
              <div 
                v-for="item in todaySuggestions" 
                :key="item.title" 
                class="flex items-start gap-3 p-3 hover:bg-slate-50/40 rounded-sm transition-all cursor-pointer border-b border-slate-50"
                @click="goTo(item.path)"
              >
                <span class="w-2.5 h-2.5 rounded-sm mt-1 shrink-0" :class="{
                  'bg-blue': item.tone === 'blue',
                  'bg-amber-500': item.tone === 'amber',
                  'bg-emerald-500': item.tone === 'green'
                }"></span>
                <div class="space-y-0.5 min-w-0">
                  <strong class="text-xs font-bold text-slate-800 block truncate">{{ item.title }}</strong>
                  <p class="text-[11px] text-slate-500 leading-relaxed line-clamp-2">{{ item.reason }}</p>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="py-6 border border-dashed border-slate-200/60 rounded-sm flex flex-col items-center justify-center text-slate-400 text-xs">
              完善学习画像后可获得个性化建议
            </div>
          </section>

          <!-- Block 3: Daily Challenge (Cardless) -->
          <section class="challenge-panel" v-if="dailyChallenge">
            <div class="flex items-center justify-between">
              <div class="space-y-0.5">
                <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest block">DAILY CHALLENGE</span>
                <h2 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">每日专项挑战</h2>
              </div>
              <Badge variant="secondary" class="text-[9px] font-bold px-2 py-0.5 rounded-sm">
                {{ dailyChallenge.difficulty }}
              </Badge>
            </div>

            <div class="space-y-3.5">
              <div class="space-y-1">
                <h3 class="text-xs font-bold text-slate-800">{{ dailyChallenge.title }}</h3>
                <p class="text-[11px] text-slate-500 leading-relaxed">{{ dailyChallenge.reason }}</p>
              </div>

              <!-- Meta estimates -->
              <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono border-t border-b border-slate-100 py-2">
                <span>EST. TIME: {{ dailyChallenge.minutes }} MINS</span>
                <span>{{ dailyChallenge.source }}</span>
              </div>

              <Button class="w-full h-9 rounded-sm text-xs font-semibold cursor-pointer" @click="goTo('/question-bank')">
                开始挑战
              </Button>
            </div>
          </section>

          <!-- Block 4: Quick Start Links (Cardless) -->
          <section class="quick-panel" v-if="quickActions.length">
            <div class="space-y-0.5">
              <span class="text-[9px] font-mono text-slate-400 uppercase tracking-widest block">QUICK ACCESS LINKS</span>
              <h2 class="text-xs font-black text-slate-900 uppercase tracking-wider font-mono">导航快速开始</h2>
            </div>

            <!-- Grid links -->
            <div class="grid grid-cols-1 gap-2">
              <div 
                v-for="action in quickActions" 
                :key="action.label" 
                class="flex items-center justify-between py-2 border-b border-slate-50 hover:border-slate-200 hover:bg-slate-50/40 px-2 rounded-sm transition-all cursor-pointer group"
                @click="goTo(action.path)"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <div class="w-7 h-7 rounded-sm flex items-center justify-center shrink-0" :class="{
                    'bg-blue/5 text-blue': action.icon === 'chat',
                    'bg-indigo-500/5 text-indigo-500': action.icon === 'resource',
                    'bg-emerald-500/5 text-emerald-500': action.icon === 'path',
                    'bg-amber-500/5 text-amber-500': action.icon === 'practice',
                    'bg-purple-500/5 text-purple-500': action.icon === 'monitor'
                  }">
                    <component :is="getIconComponent(action.icon)" class="w-4 h-4" />
                  </div>
                  <div class="min-w-0">
                    <strong class="text-xs font-bold text-slate-800 block truncate group-hover:text-blue transition-colors">{{ action.label }}</strong>
                    <p class="text-[10px] text-slate-400 truncate">{{ action.description }}</p>
                  </div>
                </div>
                <ChevronRight class="w-3.5 h-3.5 text-slate-300 group-hover:text-blue group-hover:translate-x-0.5 transition-all shrink-0" />
              </div>
            </div>
          </section>

        </aside>

      </div>

      <ErrorStatePanel
        v-else
        :is-loading="loading"
        :loading-title="'正在同步学习控制台'"
        :loading-message="'正在读取画像、路径、资源和学习事件...'"
        :error-title="'首页数据加载失败'"
        :error-message="loadError || '暂时无法获取数据'"
        @retry="loadAllData"
      />
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ErrorStatePanel from '@/shared/ui/ErrorStatePanel.vue'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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
  CalendarIcon as Calendar,
  MessageSquareIcon as ChatDotRound,
  FilesIcon as DocumentCopy,
  PencilIcon as EditPen,
  CompassIcon as Guide,
  MonitorIcon as Monitor,
  BookOpenIcon as Reading,
  ChevronRightIcon as ChevronRight,
  FileTextIcon as FileText,
} from '@lucide/vue'

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
      backgroundColor: '#FCFFFF',
      borderColor: '#C8E4E3',
      borderWidth: 1,
      textStyle: { color: '#173B42', fontSize: 11 }
    },
    radar: {
      ...rawData.radar,
      radius: '68%',
      center: ['50%', '50%'],
      splitNumber: 4,
      splitLine: { lineStyle: { color: '#C8E4E3', width: 1 } },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(252, 255, 255, 0.9)', 'rgba(216, 241, 240, 0.35)']
        }
      },
      axisLine: { lineStyle: { color: '#B9DEDC' } },
      axisLabel: { show: false },
      axisName: { color: '#58747A', fontSize: 10, fontWeight: 'bold', fontFamily: 'Geist, sans-serif' }
    },
    series: [{
      type: 'radar',
      data: [{
        value: rawData.series?.[0]?.data?.[0]?.value || [],
        name: '能力得分',
        areaStyle: { color: 'rgba(70, 184, 180, 0.2)' },
        lineStyle: { color: '#205F67', width: 1.8 },
        itemStyle: { color: '#46B8B4', borderColor: '#FCFFFF', borderWidth: 2 },
        symbolSize: 4
      }]
    }]
  }
})

const profileScore = computed(() => {
  const raw = profileRadarData.value as any
  const candidate = raw?.overall_score ?? raw?.total_score ?? raw?.score ?? raw?.profile_score ?? raw?.composite_score
  if (candidate !== undefined && candidate !== null) return clampPercent(candidate)

  const values = radarValues.value
  if (!values.length) return 0
  return clampPercent(values.reduce((sum, value) => sum + value, 0) / values.length)
})

const profileDimensions = computed(() => {
  const indicators = radarSource.value?.radar?.indicator
  const values = radarValues.value

  if (!Array.isArray(indicators) || !values.length) {
    return []
  }

  return indicators.map((item: any, index: number) => ({
    name: item?.name || `维度 ${index + 1}`,
    score: values[index] ?? 0
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

  return lowDimensions.length ? lowDimensions.slice(0, 2) : []
})

const weakAreaText = computed(() => weakAreas.value.join(' / '))

const overviewStats = computed(() => {
  const stats = studyStatsData.value
  return [
    { label: '本周学习', value: `${stats?.weekly_days ?? 0} 天` },
    { label: '累计学习', value: `${stats?.total_hours ?? 0} 小时` },
    { label: '待完成节点', value: `${stats?.pending_nodes ?? 0} 个` },
    { label: '今日建议', value: `${stats?.today_suggestions ?? 0} 条` }
  ]
})

const continueItems = computed<ContinueItem[]>(() => {
  const data = continueLearningData.value
  const activePaths = data?.active_paths || []

  if (!activePaths.length) {
    return []
  }

  return activePaths.map(path => ({
    title: path.current_node_title || path.title || '继续当前学习路径',
    category: path.title || '学习路径',
    progress: clampPercent(path.overall_progress, 0),
    lastTime: formatDateTime(path.last_learned_at || path.updated_at),
    path: path.current_node_id ? `/path-planner/node/${path.current_node_id}` : `/path-planner/overview/${path.id}`,
    icon: 'path',
    tone: 'tone-emerald'
  }))
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
  return []
})

const dailyChallenge = computed(() => {
  const challenge = dailyChallengeData.value
  if (challenge) {
    return {
      title: challenge.subject || '今日挑战',
      difficulty: challenge.difficulty || '中等',
      minutes: challenge.estimated_minutes || 12,
      source: challenge.source || '题库推荐',
      reason: challenge.reason || `推荐你从「${challenge.subject}」切入，保持每日练习节奏。`
    }
  }
  return null
})

const quickActions = computed<HomeActionItem[]>(() => {
  const actions = quickActionsData.value?.actions || []
  return actions.slice(0, 6)
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
  return []
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
.home-page {
  padding: clamp(24px, 3vw, 46px) 0 56px;
  color: var(--color-text);
  background:
    radial-gradient(circle at 84% 2%, rgba(98, 201, 197, 0.14), transparent 30rem),
    var(--color-bg);
}

.home-shell {
  width: min(1420px, calc(100% - 48px));
  margin: 0 auto;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 8fr) minmax(340px, 4fr);
  gap: 22px;
  align-items: start;
}

.primary-column,
.insight-column {
  display: flex;
  flex-direction: column;
  gap: 22px;
  min-width: 0;
}

.recommendation-panel,
.radar-panel,
.learning-panel,
.resource-panel,
.suggestion-panel,
.challenge-panel,
.quick-panel {
  position: relative;
  background: rgba(252, 255, 255, 0.92);
  border: 1px solid var(--color-border);
  border-radius: 16px;
}

.recommendation-panel {
  min-height: 356px;
  padding: clamp(24px, 3vw, 38px);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.recommendation-panel::after {
  content: '';
  position: absolute;
  width: 260px;
  height: 260px;
  right: -120px;
  top: -130px;
  border: 40px solid rgba(98, 201, 197, 0.14);
  border-radius: 50%;
  pointer-events: none;
}

.radar-panel {
  min-height: 356px;
  padding: 22px;
  background:
    linear-gradient(150deg, rgba(216, 241, 240, 0.58), rgba(252, 255, 255, 0.95) 48%);
  box-shadow: var(--shadow-sm);
}

.radar-canvas {
  background: rgba(252, 255, 255, 0.64);
  border: 1px solid rgba(200, 228, 227, 0.86);
  border-radius: 13px;
}

.learning-panel,
.resource-panel,
.suggestion-panel,
.challenge-panel,
.quick-panel {
  padding: 22px;
}

.recommendation-panel :deep(.text-blue),
.recommendation-panel :deep(.text-slate-900),
.primary-column :deep(.hover\:text-blue:hover),
.insight-column :deep(.text-blue),
.insight-column :deep(.hover\:text-blue:hover) {
  color: var(--color-primary-text) !important;
}

.recommendation-panel :deep(.bg-blue),
.suggestion-panel :deep(.bg-blue) {
  background-color: var(--color-primary) !important;
}

.recommendation-panel :deep(.border-blue) {
  border-color: var(--color-primary) !important;
}

.recommendation-panel :deep(h1) {
  margin-top: 10px;
  font-size: clamp(28px, 3vw, 42px);
  letter-spacing: -0.045em;
}

.recommendation-panel :deep(.font-mono),
.primary-column :deep(.font-mono),
.insight-column :deep(.font-mono) {
  font-family: var(--font-sans);
  letter-spacing: 0.02em;
}

.recommendation-panel :deep(button),
.challenge-panel :deep(button) {
  border-radius: 10px;
}

.learning-panel :deep(.divide-y > *),
.resource-panel :deep(.divide-y > *) {
  border-color: var(--color-border-light);
}

.learning-panel :deep(.bg-emerald-500) {
  background: var(--color-primary);
}

.learning-panel :deep(.bg-emerald-50) {
  background: var(--color-primary-soft);
}

.learning-panel :deep(.text-emerald-600) {
  color: var(--color-primary-text);
}

.learning-panel :deep(.hover\:bg-slate-50\/40:hover),
.resource-panel :deep(.hover\:bg-slate-50\/40:hover),
.suggestion-panel :deep(.hover\:bg-slate-50\/40:hover),
.quick-panel :deep(.hover\:bg-slate-50\/40:hover) {
  background: rgba(216, 241, 240, 0.34);
}

.resource-panel :deep(.bg-slate-50) {
  background: var(--color-primary-soft);
}

.resource-panel :deep(.text-slate-400) {
  color: var(--color-text-muted);
}

.suggestion-panel,
.challenge-panel,
.quick-panel {
  box-shadow: none;
}

.challenge-panel {
  background: linear-gradient(145deg, #FFFDF6, #FCFFFF);
  border-color: #E9DDBB;
}

.quick-panel :deep(.grid) {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 14px;
}

.quick-panel :deep(.border-b) {
  border-bottom-color: var(--color-border-light);
}

.chart {
  width: 100%;
  height: 100%;
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: minmax(0, 7fr) minmax(310px, 5fr);
  }

  .home-shell {
    width: min(100% - 32px, 1120px);
  }
}

@media (max-width: 767px) {
  .home-page {
    padding-top: 18px;
  }

  .home-shell {
    width: min(100% - 24px, 680px);
  }

  .dashboard-grid {
    display: contents;
  }

  .home-shell {
    display: flex;
    flex-direction: column;
  }

  .primary-column,
  .insight-column {
    display: contents;
  }

  .recommendation-panel { order: 1; }
  .radar-panel { order: 2; margin-top: 16px; }
  .learning-panel { order: 3; margin-top: 16px; }
  .resource-panel { order: 4; margin-top: 16px; }
  .suggestion-panel { order: 5; margin-top: 16px; }
  .challenge-panel { order: 6; margin-top: 16px; }
  .quick-panel { order: 7; margin-top: 16px; }

  .recommendation-panel,
  .radar-panel {
    min-height: auto;
  }

  .recommendation-panel,
  .radar-panel,
  .learning-panel,
  .resource-panel,
  .suggestion-panel,
  .challenge-panel,
  .quick-panel {
    border-radius: 14px;
  }

  .quick-panel :deep(.grid) {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-page *,
  .home-page *::before,
  .home-page *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
