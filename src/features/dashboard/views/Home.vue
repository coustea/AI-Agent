<template>
  <main class="home-page min-h-screen font-sans antialiased pb-16 bg-slate-50/30">
    <div class="home-shell max-w-7xl mx-auto px-6 py-8">
      
      <div class="dashboard-content space-y-10" v-if="recommendationData && profileRadarData">
        
        <!-- Top Visual Row: Carousel + Radar (Cardless) -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          
          <!-- Carousel Banner (Left 2 columns on desktop) -->
          <div class="lg:col-span-2 relative rounded-3xl overflow-hidden bg-slate-900 group min-h-[380px] flex flex-col justify-end border border-slate-200/10">
            <!-- Slides -->
            <div class="absolute inset-0 select-none">
              <Transition name="slide-fade" mode="out-in">
                <div :key="activeSlide" class="absolute inset-0">
                  <img :src="carouselSlides[activeSlide]?.image" class="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105" alt="Banner" />
                  <!-- Gradient overlay for text readability -->
                  <div class="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-slate-900/35 to-transparent"></div>
                </div>
              </Transition>
            </div>

            <!-- Slide Content Overlay -->
            <div class="relative z-10 p-8 sm:p-10 space-y-4 max-w-xl text-left">
              <h2 class="text-2xl sm:text-3xl font-black text-white tracking-tight leading-tight">
                {{ carouselSlides[activeSlide]?.title }}
              </h2>
              <p class="text-xs sm:text-sm text-slate-200/90 leading-relaxed font-medium">
                {{ carouselSlides[activeSlide]?.description }}
              </p>
              <div class="pt-2">
                <Button 
                  @click="goTo(carouselSlides[activeSlide]?.path || '')" 
                  class="bg-teal-500 hover:bg-teal-400 text-white font-bold text-xs rounded-xl px-5 py-2.5 shadow-lg shadow-teal-500/25 border-none transition-all duration-300 cursor-pointer"
                >
                  {{ carouselSlides[activeSlide]?.actionText }}
                </Button>
              </div>
            </div>

            <!-- Carousel Controls -->
            <!-- Previous Button -->
            <button 
              @click="prevSlide" 
              class="absolute left-4 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-black/25 text-white hover:bg-black/40 transition-all opacity-0 group-hover:opacity-100 cursor-pointer border border-white/10"
            >
              <ChevronLeft class="w-5 h-5" />
            </button>
            <!-- Next Button -->
            <button 
              @click="nextSlide" 
              class="absolute right-4 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-black/25 text-white hover:bg-black/40 transition-all opacity-0 group-hover:opacity-100 cursor-pointer border border-white/10"
            >
              <ChevronRight class="w-5 h-5" />
            </button>

            <!-- Indicators -->
            <div class="absolute bottom-6 right-10 z-10 flex gap-2">
              <button 
                v-for="(_, index) in carouselSlides" 
                :key="index"
                @click="setSlide(index)"
                class="w-2 h-2 rounded-full transition-all duration-300 cursor-pointer border-none"
                :class="activeSlide === index ? 'bg-teal-400 w-6' : 'bg-white/40 hover:bg-white/60'"
              ></button>
            </div>
          </div>

          <!-- Radar Chart Snapshot (Right column on desktop, Cardless) -->
          <div class="lg:col-span-1 flex flex-col justify-between py-2 relative overflow-hidden">
            <div class="flex items-center justify-between pb-3 border-b border-slate-200/60">
              <h2 class="text-xs font-black text-slate-800 uppercase tracking-wider font-mono">能力画像诊断</h2>
              <Button variant="ghost" class="text-xs font-bold text-teal-655 hover:text-teal-700 p-0 cursor-pointer h-7 hover:bg-transparent" @click="goTo(profilePath)">
                完整报告
              </Button>
            </div>

            <!-- Score KPI & Radar Content -->
            <div class="flex items-center gap-4 my-4">
              <!-- KPI (Cardless) -->
              <div class="score-badge flex flex-col items-center justify-center text-center shrink-0 min-w-[90px] border-r border-slate-200/60 pr-6">
                <span class="text-[9px] text-teal-600 font-bold uppercase tracking-wider">画像评分</span>
                <strong class="text-4xl font-black text-slate-800 mt-1 leading-none">{{ profileScore }}</strong>
                <span class="text-[9px] font-mono text-teal-700 font-bold bg-teal-50 px-1.5 py-0.5 rounded border border-teal-100/40 mt-3">S-Tier</span>
              </div>
              <!-- Radar Chart -->
              <div class="flex-1 h-[150px] relative min-w-0">
                <div v-if="loading" class="absolute inset-0 flex flex-col items-center justify-center text-slate-400 text-xs">
                  <div class="w-4 h-4 rounded-full border border-teal-500 border-t-transparent animate-spin"></div>
                </div>
                <v-chart v-else class="chart" :option="radarOption" autoresize />
              </div>
            </div>

            <!-- Diagnostics (Cardless) -->
            <div class="diagnostic-advice pt-4 border-t border-slate-200/60">
              <div class="text-[10px] font-bold text-teal-800 uppercase tracking-wider mb-1">建议</div>
              <p class="text-xs text-slate-655 leading-relaxed text-left">
                {{ profileRadarData.radar?.note || `综合画像分 ${profileScore}，薄弱方向：${weakAreaText}` }}
              </p>
            </div>
          </div>
          
        </div>

        <!-- Middle Row: Quick Action Dock (Cardless) -->
        <section class="dock-section py-6 border-y border-slate-200/60">
          <div class="flex flex-wrap items-center justify-center gap-6 sm:gap-12">
            <button 
              v-for="action in quickActions" 
              :key="action.label" 
              class="dock-button flex items-center gap-4 hover:bg-slate-100/45 px-4 py-2.5 rounded-2xl transition-all duration-300 cursor-pointer text-left"
              @click="goTo(action.path)"
            >
              <div class="dock-icon-circle w-11 h-11 rounded-2xl flex items-center justify-center bg-teal-50/70 text-teal-655 hover:bg-teal-500 hover:text-white transition-colors duration-300 shrink-0">
                <component :is="getIconComponent(action.icon)" class="w-5 h-5" />
              </div>
              <div class="min-w-0">
                <span class="block text-sm font-black text-slate-800 leading-tight">{{ action.label }}</span>
                <span class="block text-[10px] text-slate-400 mt-1 max-w-[140px] truncate">{{ action.description }}</span>
              </div>
            </button>
          </div>
        </section>

        <!-- Bottom Row: Dual History Board (Cardless & Equal Height) -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-stretch">
          
          <!-- Left Column: Resource History (Cardless) -->
          <section class="history-section flex flex-col justify-between py-2 min-h-[360px]">
            <div class="space-y-4 flex-1">
              <div class="flex items-center justify-between pb-3 border-b border-slate-200/60">
                <div class="flex items-center gap-2">
                  <Files class="w-4.5 h-4.5 text-teal-600" />
                  <h3 class="text-sm font-black text-slate-800 font-mono tracking-wider uppercase">多智能体资源生成历史</h3>
                </div>
                <Button variant="ghost" class="text-xs font-bold text-teal-600 hover:text-teal-700 p-0 cursor-pointer h-7 hover:bg-transparent" @click="goTo('/resource-generator')">
                  生成新资源
                </Button>
              </div>

              <!-- Fixed Height List Container to guarantee alignment -->
              <div class="history-list-container h-[260px] flex flex-col justify-start">
                <div v-if="paginatedResources.length" class="divide-y divide-slate-100/50">
                  <div 
                    v-for="resource in paginatedResources" 
                    :key="resource.id"
                    class="history-item flex items-center justify-between py-3 hover:bg-slate-55/65 px-2 rounded-xl transition-all duration-200 cursor-pointer"
                    @click="goTo(resource.path)"
                  >
                    <div class="space-y-1.5 text-left min-w-0 pr-4 flex-1">
                      <strong class="block text-xs font-bold text-slate-800 truncate">{{ resource.title }}</strong>
                      <div class="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                        <span class="font-bold text-teal-700 bg-teal-50/70 px-1.5 py-0.5 rounded border border-teal-100/20">{{ resource.agent }}</span>
                        <span>•</span>
                        <span>{{ resource.timeStr }}</span>
                      </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <span class="inline-flex items-center px-2.5 py-0.5 text-[9px] font-bold rounded bg-teal-50 text-teal-700 border border-teal-100/30">
                        {{ resource.type }}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div v-else class="h-full border border-dashed border-slate-200/80 rounded-2xl flex flex-col items-center justify-center text-slate-400 text-xs space-y-3">
                  <p>暂无资源生成记录</p>
                  <Button size="sm" class="rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white cursor-pointer border-none" @click="goTo('/resource-generator')">
                    一键生成资源
                  </Button>
                </div>
              </div>
            </div>

            <!-- Pagination footer -->
            <div class="flex items-center justify-between border-t border-slate-200/60 pt-3 mt-4 text-[10px] font-mono text-slate-400">
              <span>共 {{ recentResources.length }} 项</span>
              <div class="flex items-center gap-3" v-if="totalResourcePages > 1">
                <span>{{ resourcePage }} / {{ totalResourcePages }} 页</span>
                <div class="flex gap-1.5">
                  <button 
                    class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="resourcePage === 1"
                    @click="resourcePage--"
                  >
                    <ChevronLeft class="w-3 h-3 text-slate-655" />
                  </button>
                  <button 
                    class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="resourcePage === totalResourcePages"
                    @click="resourcePage++"
                  >
                    <ChevronRight class="w-3 h-3 text-slate-655" />
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- Right Column: Path History (Cardless) -->
          <section class="history-section flex flex-col justify-between py-2 min-h-[360px]">
            <div class="space-y-4 flex-1">
              <div class="flex items-center justify-between pb-3 border-b border-slate-200/60">
                <div class="flex items-center gap-2">
                  <Guide class="w-4.5 h-4.5 text-teal-600" />
                  <h3 class="text-sm font-black text-slate-800 font-mono tracking-wider uppercase">路径规划历史</h3>
                </div>
                <Button variant="ghost" class="text-xs font-bold text-teal-600 hover:text-teal-700 p-0 cursor-pointer h-7 hover:bg-transparent" @click="goTo('/path-planner')">
                  规划新路径
                </Button>
              </div>

              <!-- Fixed Height List Container to guarantee alignment -->
              <div class="history-list-container h-[260px] flex flex-col justify-start">
                <div v-if="paginatedPaths.length" class="divide-y divide-slate-100/50">
                  <div 
                    v-for="path in paginatedPaths" 
                    :key="path.id"
                    class="history-item flex flex-col py-3 hover:bg-slate-55/65 px-2 rounded-xl transition-all duration-200"
                  >
                    <div class="flex items-start justify-between gap-4">
                      <div class="space-y-1.5 text-left min-w-0 flex-1">
                        <strong class="block text-xs font-black text-slate-800 truncate">{{ path.title }}</strong>
                        <div class="text-[10px] text-slate-400 font-mono">
                          当前节点：<span class="font-bold text-slate-650">{{ path.currentNodeTitle }}</span>
                        </div>
                      </div>
                      <Button 
                        size="sm" 
                        class="text-[10px] h-7 px-3 bg-teal-600 hover:bg-teal-500 text-white font-bold rounded-xl border-none cursor-pointer" 
                        @click="goTo(path.path)"
                      >
                        继续学习
                      </Button>
                    </div>
                    
                    <!-- Progress bar -->
                    <div class="mt-2.5">
                      <div class="flex items-center justify-between text-[9px] text-slate-450 font-mono mb-1">
                        <span>总体进度</span>
                        <span>{{ path.progress }}%</span>
                      </div>
                      <div class="w-full h-1 bg-slate-200/70 rounded-full overflow-hidden">
                        <div class="h-full bg-teal-500 rounded-full transition-all duration-500" :style="{ width: path.progress + '%' }"></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div v-else class="h-full border border-dashed border-slate-200/80 rounded-2xl flex flex-col items-center justify-center text-slate-400 text-xs space-y-3">
                  <p>暂无活跃路径记录</p>
                  <Button size="sm" class="rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white cursor-pointer border-none" @click="goTo('/path-planner')">
                    开始规划
                  </Button>
                </div>
              </div>
            </div>

            <!-- Pagination footer -->
            <div class="flex items-center justify-between border-t border-slate-200/60 pt-3 mt-4 text-[10px] font-mono text-slate-400">
              <span>共 {{ activePaths.length }} 项</span>
              <div class="flex items-center gap-3" v-if="totalPathPages > 1">
                <span>{{ pathPage }} / {{ totalPathPages }} 页</span>
                <div class="flex gap-1.5">
                  <button 
                    class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="pathPage === 1"
                    @click="pathPage--"
                  >
                    <ChevronLeft class="w-3 h-3 text-slate-655" />
                  </button>
                  <button 
                    class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="pathPage === totalPathPages"
                    @click="pathPage++"
                  >
                    <ChevronRight class="w-3 h-3 text-slate-655" />
                  </button>
                </div>
              </div>
            </div>
          </section>

        </div>

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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import ErrorStatePanel from '@/shared/ui/ErrorStatePanel.vue'
import { Button } from '@/components/ui/button'

import {
  getRecommendation,
  getProfileRadar,
  getContinueLearning,
  getQuickActions,
  getRecentResources,
  type RecommendationData,
  type ProfileRadarData,
  type ContinueLearningData,
  type QuickActionsData,
  type HomeActionItem,
  type RecentResourceItem,
} from '@/features/dashboard/api/home'
import { getRadarChartData } from '@/features/profile/model/profileViewModel'

import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

import {
  MessageSquareIcon as ChatDotRound,
  FilesIcon as DocumentCopy,
  PencilIcon as EditPen,
  CompassIcon as Guide,
  MonitorIcon as Monitor,
  BookOpenIcon as Reading,
  ChevronLeftIcon as ChevronLeft,
  ChevronRightIcon as ChevronRight,
  FilesIcon as Files,
} from '@lucide/vue'

use([CanvasRenderer, RadarChart, TooltipComponent])

const router = useRouter()
const route = useRoute()

const recommendationData = ref<RecommendationData | null>(null)
const profileRadarData = ref<ProfileRadarData | null>(null)
const continueLearningData = ref<ContinueLearningData | null>(null)
const quickActionsData = ref<QuickActionsData | null>(null)
const recentResourcesData = ref<RecentResourceItem[]>([])
const loading = ref(false)
const loadError = ref('')

// Carousel slides definition
const activeSlide = ref(0)
const carouselSlides = [
  {
    title: 'AI 智能导师',
    description: '书案旁微微散发微光的智能书本，为您的自主探索提供全天候深度答疑与循循善诱的辅导。',
    image: '/ai-tutor.jpg',
    path: '/tutor',
    actionText: '进入智能辅导'
  },
  {
    title: '多智能体资源引擎',
    description: '知识图书馆中轻盈起舞的智慧卡片，针对您的薄弱能力指标，并行生成丰富完备的专研学习包。',
    image: '/resource-engine.jpg',
    path: '/resource-generator',
    actionText: '一键生成资源'
  },
  {
    title: '个性化路径规划',
    description: '指引探索方向的星座灯塔，为您理清通往终点的每一步台阶，点亮专属的知识成长阶梯。',
    image: '/path-planner.jpg',
    path: '/path-planner',
    actionText: '开启路径规划'
  }
]

let carouselInterval: ReturnType<typeof setInterval> | null = null

const nextSlide = () => {
  activeSlide.value = (activeSlide.value + 1) % carouselSlides.length
}

const prevSlide = () => {
  activeSlide.value = (activeSlide.value - 1 + carouselSlides.length) % carouselSlides.length
}

const setSlide = (index: number) => {
  activeSlide.value = index
  resetAutoplay()
}

const startAutoplay = () => {
  carouselInterval = setInterval(nextSlide, 6000)
}

const stopAutoplay = () => {
  if (carouselInterval) {
    clearInterval(carouselInterval)
    carouselInterval = null
  }
}

const resetAutoplay = () => {
  stopAutoplay()
  startAutoplay()
}

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
      splitLine: { lineStyle: { color: '#B9DEDC', width: 1 } },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(252, 255, 255, 0.9)', 'rgba(216, 241, 240, 0.35)']
        }
      },
      axisLine: { lineStyle: { color: '#B9DEDC' } },
      axisLabel: { show: false },
      axisName: { color: '#58747A', fontSize: 9, fontWeight: 'bold', fontFamily: 'Geist, sans-serif' }
    },
    series: [{
      type: 'radar',
      data: [{
        value: rawData.series?.[0]?.data?.[0]?.value || [],
        name: '能力得分',
        areaStyle: { color: 'rgba(70, 184, 180, 0.2)' },
        lineStyle: { color: '#0d9488', width: 1.8 }, // Teal-600 equivalent
        itemStyle: { color: '#0d9488', borderColor: '#FCFFFF', borderWidth: 2 },
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

const recentResources = computed(() => {
  const list = [...(recentResourcesData.value || [])]
  // Sort by created_at descending (time sort)
  list.sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
    return timeB - timeA
  })
  return list.map(item => {
    return {
      id: item.id,
      title: item.title || '未命名资源',
      type: item.type || '文档',
      agent: item.agent || '资源生成智能体',
      timeStr: formatDateTime(item.created_at),
      path: item.id ? `/resource-detail/${item.id}` : '/resource-generator'
    }
  })
})

const activePaths = computed(() => {
  const paths = [...(continueLearningData.value?.active_paths || [])]
  // Sort by last_learned_at or updated_at descending (time sort)
  paths.sort((a, b) => {
    const timeA = new Date(a.last_learned_at || a.updated_at || 0).getTime()
    const timeB = new Date(b.last_learned_at || b.updated_at || 0).getTime()
    return timeB - timeA
  })
  return paths.map(path => {
    const rawDate = path.last_learned_at || path.updated_at
    return {
      id: path.id,
      title: path.title || '继续当前学习路径',
      currentNodeTitle: path.current_node_title || '未开始节点',
      currentNodeId: path.current_node_id,
      progress: clampPercent(path.overall_progress, 0),
      timeStr: formatDateTime(rawDate),
      path: path.current_node_id ? `/path-planner/node/${path.current_node_id}` : `/path-planner/overview/${path.id}`
    }
  })
})

// Pagination logic
const ITEMS_PER_PAGE = 4
const resourcePage = ref(1)
const pathPage = ref(1)

const totalResourcePages = computed(() => Math.ceil(recentResources.value.length / ITEMS_PER_PAGE) || 1)
const totalPathPages = computed(() => Math.ceil(activePaths.value.length / ITEMS_PER_PAGE) || 1)

const paginatedResources = computed(() => {
  const start = (resourcePage.value - 1) * ITEMS_PER_PAGE
  return recentResources.value.slice(start, start + ITEMS_PER_PAGE)
})

const paginatedPaths = computed(() => {
  const start = (pathPage.value - 1) * ITEMS_PER_PAGE
  return activePaths.value.slice(start, start + ITEMS_PER_PAGE)
})

watch(recentResources, () => {
  resourcePage.value = 1
})
watch(activePaths, () => {
  pathPage.value = 1
})

const quickActions = computed<HomeActionItem[]>(() => {
  const actions = quickActionsData.value?.actions || []
  return actions.slice(0, 6)
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
    ] = await Promise.all([
      getRecommendation(),
      getProfileRadar(),
      getContinueLearning(),
      getQuickActions(),
      getRecentResources(),
    ])

    recommendationData.value = recRes.data.data
    profileRadarData.value = radarRes.data.data
    continueLearningData.value = continueRes.data.data
    quickActionsData.value = actionsRes.data.data
    recentResourcesData.value = resourcesRes.data.data ?? []
  } catch (error) {
    console.error('Failed to load dashboard data', error)
    recommendationData.value = null
    profileRadarData.value = null
    loadError.value = '后端接口暂时不可用，请稍后重试。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAllData()
  startAutoplay()
})

onUnmounted(() => {
  stopAutoplay()
})

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
  color: var(--color-text);
  background:
    radial-gradient(circle at 84% 2%, rgba(13, 148, 136, 0.03), transparent 30rem),
    #fafafa; /* Flat soft off-white background */
}

.home-shell {
  width: min(1360px, calc(100% - 48px));
  margin: 0 auto;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
}

.chart {
  width: 100%;
  height: 100%;
}

/* Custom dock button effects without white card borders */
.dock-button {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.dock-button:hover {
  transform: translateY(-1px);
}

.dock-button:hover .dock-icon-circle {
  background: #0d9488;
  color: #ffffff;
}

/* History lists custom minimal styles */
.history-item {
  transition: all 0.2s ease;
}

.history-item:hover {
  background-color: rgba(241, 245, 249, 0.6);
}

/* Carousel slide transitions */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: scale(1.01);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: scale(0.99);
}

@media (max-width: 1024px) {
  .home-shell {
    width: calc(100% - 32px);
  }
}
</style>
