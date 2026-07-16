<template>
  <main class="home-page min-h-screen font-sans antialiased pb-16 bg-slate-50/30">
    <div class="home-shell max-w-7xl mx-auto px-6 py-8">
      <div v-if="dataLoaded" class="dashboard-content space-y-10">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          <div
              class="lg:col-span-2 relative rounded-3xl overflow-hidden bg-slate-900 group min-h-[380px] flex flex-col justify-end border border-slate-200/10"
          >
            <div class="absolute inset-0 select-none">
              <Transition name="slide-fade" mode="out-in">
                <div :key="activeSlide" class="absolute inset-0">
                  <img
                      :src="carouselSlides[activeSlide]?.image"
                      class="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105"
                      alt="Banner"
                  />
                  <div
                      class="absolute inset-0 bg-gradient-to-t from-slate-950/85 via-slate-900/35 to-transparent"
                  ></div>
                </div>
              </Transition>
            </div>

            <div class="relative z-10 p-8 sm:p-10 space-y-4 max-w-xl text-left">
              <h2
                  class="text-2xl sm:text-3xl font-black text-white tracking-tight leading-tight"
              >
                {{ carouselSlides[activeSlide]?.title }}
              </h2>

              <p
                  class="text-xs sm:text-sm text-slate-200/90 leading-relaxed font-medium"
              >
                {{ carouselSlides[activeSlide]?.description }}
              </p>

              <div class="pt-2">
                <Button
                    class="bg-teal-500 hover:bg-teal-400 text-white font-bold text-xs rounded-xl px-5 py-2.5 shadow-lg shadow-teal-500/25 border-none transition-all duration-300 cursor-pointer"
                    @click="goTo(carouselSlides[activeSlide]?.path || '')"
                >
                  {{ carouselSlides[activeSlide]?.actionText }}
                </Button>
              </div>
            </div>

            <button
                type="button"
                class="absolute left-4 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-black/25 text-white hover:bg-black/40 transition-all opacity-0 group-hover:opacity-100 cursor-pointer border border-white/10"
                aria-label="上一张"
                @click="prevSlide"
            >
              <ChevronLeft class="w-5 h-5" />
            </button>

            <button
                type="button"
                class="absolute right-4 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-black/25 text-white hover:bg-black/40 transition-all opacity-0 group-hover:opacity-100 cursor-pointer border border-white/10"
                aria-label="下一张"
                @click="nextSlide"
            >
              <ChevronRight class="w-5 h-5" />
            </button>

            <div class="absolute bottom-6 right-10 z-10 flex gap-2">
              <button
                  v-for="(_, index) in carouselSlides"
                  :key="index"
                  type="button"
                  class="w-2 h-2 rounded-full transition-all duration-300 cursor-pointer border-none"
                  :class="
                  activeSlide === index
                    ? 'bg-teal-400 w-6'
                    : 'bg-white/40 hover:bg-white/60'
                "
                  :aria-label="`切换到第 ${index + 1} 张`"
                  @click="setSlide(index)"
              ></button>
            </div>
          </div>

          <div
              class="lg:col-span-1 flex flex-col justify-between py-2 relative overflow-hidden"
          >
            <div
                class="flex items-center justify-between pb-3 border-b border-slate-200/60"
            >
              <h2
                  class="text-xs font-black text-slate-800 uppercase tracking-wider font-mono"
              >
                能力画像诊断
              </h2>

              <Button
                  variant="ghost"
                  class="text-xs font-bold text-teal-655 hover:text-teal-700 p-0 cursor-pointer h-7 hover:bg-transparent"
                  @click="isGlobalProfileVisible = true"
              >
                完整报告
              </Button>
            </div>

            <div class="flex items-center gap-4 my-4">
              <div
                  class="score-badge flex flex-col items-center justify-center text-center shrink-0 min-w-[90px] border-r border-slate-200/60 pr-6"
              >
                <span
                    class="text-[9px] text-teal-600 font-bold uppercase tracking-wider"
                >
                  画像评分
                </span>

                <strong
                    class="text-4xl font-black text-slate-800 mt-1 leading-none"
                >
                  {{ profileScore }}
                </strong>

                <span
                    class="text-[9px] font-mono text-teal-700 font-bold bg-teal-50 px-1.5 py-0.5 rounded border border-teal-100/40 mt-3"
                >
                  S-Tier
                </span>
              </div>

              <div class="flex-1 h-[150px] relative min-w-0">
                <div
                    v-if="!profileRadarData"
                    class="absolute inset-0 flex flex-col items-center justify-center text-slate-400 text-xs"
                >
                  <div
                      class="w-4 h-4 rounded-full border border-teal-500 border-t-transparent animate-spin"
                  ></div>
                </div>

                <v-chart
                    v-else
                    class="chart"
                    :option="radarOption"
                    autoresize
                />
              </div>
            </div>

            <div
                class="diagnostic-advice pt-4 border-t border-slate-200/60"
            >
              <div
                  class="text-[10px] font-bold text-teal-800 uppercase tracking-wider mb-1"
              >
                建议
              </div>

              <p class="text-xs text-slate-655 leading-relaxed text-left">
                {{
                  profileRadarData?.radar?.note ||
                  `综合画像分 ${profileScore}，薄弱方向：${weakAreaText}`
                }}
              </p>
            </div>
          </div>
        </div>

        <section
            class="quick-entry-section"
            aria-label="快捷入口"
        >
          <div class="quick-entry-grid">
            <button
                v-for="action in quickActions"
                :key="action.label"
                type="button"
                class="quick-entry-item"
                :style="getQuickActionStyle(action.icon)"
                @click="goTo(action.path)"
            >
              <span
                  class="quick-entry-icon"
                  aria-hidden="true"
              >
                <component
                    :is="getIconComponent(action.icon)"
                    class="w-[18px] h-[18px]"
                />
              </span>

              <span class="quick-entry-copy">
                <span class="quick-entry-title">
                  {{ action.label }}
                </span>

                <span class="quick-entry-description">
                  {{ action.description }}
                </span>
              </span>

              <ChevronRight
                  class="quick-entry-arrow"
                  aria-hidden="true"
              />
            </button>
          </div>
        </section>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-stretch">
          <section
              class="history-section flex flex-col justify-between py-2 min-h-[360px]"
          >
            <div class="space-y-4 flex-1">
              <div
                  class="flex items-center justify-between pb-3 border-b border-slate-200/60"
              >
                <div class="flex items-center gap-2">
                  <Files class="w-4.5 h-4.5 text-teal-600" />

                  <h3
                      class="text-sm font-black text-slate-800 font-mono tracking-wider uppercase"
                  >
                    多智能体资源生成历史
                  </h3>
                </div>

                <Button
                    variant="ghost"
                    class="text-xs font-bold text-teal-600 hover:text-teal-700 p-0 cursor-pointer h-7 hover:bg-transparent"
                    @click="goTo('/resource-generator')"
                >
                  生成新资源
                </Button>
              </div>

              <div
                  class="history-list-container h-[260px] flex flex-col justify-start"
              >
                <div
                    v-if="paginatedResources.length"
                    class="divide-y divide-slate-100/50"
                >
                  <div
                      v-for="resource in paginatedResources"
                      :key="resource.id"
                      class="history-item flex items-center justify-between py-3.5 hover:bg-slate-50 px-3 rounded-lg transition-all duration-200 cursor-pointer"
                      @click="goTo(resource.path)"
                  >
                    <div
                        class="space-y-1.5 text-left min-w-0 pr-4 flex-1"
                    >
                      <strong
                          class="block text-xs font-bold text-slate-800 truncate"
                      >
                        {{ resource.title }}
                      </strong>

                      <div
                          class="flex items-center gap-2 text-[10px] text-slate-400 font-mono"
                      >
                        <span
                            class="font-bold text-teal-700 bg-teal-50/70 px-1.5 py-0.5 rounded border border-teal-100/20"
                        >
                          {{ resource.agent }}
                        </span>

                        <span>•</span>
                        <span>{{ resource.timeStr }}</span>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                      <span
                          class="inline-flex items-center px-2.5 py-0.5 text-[9px] font-bold rounded bg-teal-50 text-teal-700 border border-teal-100/30"
                      >
                        {{ resource.type }}
                      </span>
                    </div>
                  </div>
                </div>

                <div
                    v-else
                    class="h-full border border-dashed border-slate-200/80 rounded-2xl flex flex-col items-center justify-center text-slate-400 text-xs space-y-3"
                >
                  <p>暂无资源生成记录</p>

                  <Button
                      size="sm"
                      class="rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white cursor-pointer border-none"
                      @click="goTo('/resource-generator')"
                  >
                    一键生成资源
                  </Button>
                </div>
              </div>
            </div>

            <div
                class="flex items-center justify-between border-t border-slate-200/60 pt-3 mt-4 text-[10px] font-mono text-slate-400"
            >
              <span>共 {{ recentResources.length }} 项</span>

              <div
                  v-if="totalResourcePages > 1"
                  class="flex items-center gap-3"
              >
                <span>
                  {{ resourcePage }} / {{ totalResourcePages }} 页
                </span>

                <div class="flex gap-1.5">
                  <button
                      type="button"
                      class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="resourcePage === 1"
                      aria-label="上一页"
                      @click="resourcePage--"
                  >
                    <ChevronLeft class="w-3 h-3 text-slate-655" />
                  </button>

                  <button
                      type="button"
                      class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="resourcePage === totalResourcePages"
                      aria-label="下一页"
                      @click="resourcePage++"
                  >
                    <ChevronRight class="w-3 h-3 text-slate-655" />
                  </button>
                </div>
              </div>
            </div>
          </section>

          <section
              class="history-section flex flex-col justify-between py-2 min-h-[360px]"
          >
            <div class="space-y-4 flex-1">
              <div
                  class="flex items-center justify-between pb-3 border-b border-slate-200/60"
              >
                <div class="flex items-center gap-2">
                  <Guide class="w-4.5 h-4.5 text-teal-600" />

                  <h3
                      class="text-sm font-black text-slate-800 font-mono tracking-wider uppercase"
                  >
                    路径规划历史
                  </h3>
                </div>

                <Button
                    variant="ghost"
                    class="text-xs font-bold text-teal-600 hover:text-teal-700 p-0 cursor-pointer h-7 hover:bg-transparent"
                    @click="goTo('/path-planner')"
                >
                  规划新路径
                </Button>
              </div>

              <div
                  class="history-list-container h-[260px] flex flex-col justify-start"
              >
                <div
                    v-if="paginatedPaths.length"
                    class="divide-y divide-slate-100/50"
                >
                  <div
                      v-for="path in paginatedPaths"
                      :key="path.id"
                      class="history-item flex flex-col py-3.5 hover:bg-slate-50 px-3 rounded-lg transition-all duration-200"
                  >
                    <div class="flex items-start justify-between gap-4">
                      <div class="space-y-1.5 text-left min-w-0 flex-1">
                        <strong
                            class="block text-xs font-black text-slate-800 truncate"
                        >
                          {{ path.title }}
                        </strong>

                        <div
                            class="text-[10px] text-slate-400 font-mono"
                        >
                          当前节点：
                          <span class="font-bold text-slate-650">
                            {{ path.currentNodeTitle }}
                          </span>
                        </div>
                      </div>

                      <Button
                          variant="outline"
                          size="sm"
                          class="text-[10px] h-6 px-2.5 bg-white text-slate-600 hover:text-teal-700 hover:bg-teal-50 border-slate-200 hover:border-teal-200 rounded-md shadow-sm transition-colors cursor-pointer"
                          @click="goTo(path.path)"
                      >
                        继续学习
                      </Button>
                    </div>

                    <div class="mt-2.5">
                      <div
                          class="flex items-center justify-between text-[9px] text-slate-450 font-mono mb-1"
                      >
                        <span>总体进度</span>
                        <span>{{ path.progress }}%</span>
                      </div>

                      <div
                          class="w-full h-[2px] bg-slate-200/70 rounded-full overflow-hidden"
                      >
                        <div
                            class="h-full bg-teal-500 rounded-full transition-all duration-500"
                            :style="{ width: `${path.progress}%` }"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                    v-else
                    class="h-full border border-dashed border-slate-200/80 rounded-2xl flex flex-col items-center justify-center text-slate-400 text-xs space-y-3"
                >
                  <p>暂无活跃路径记录</p>

                  <Button
                      size="sm"
                      class="rounded-xl text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-white cursor-pointer border-none"
                      @click="goTo('/path-planner')"
                  >
                    开始规划
                  </Button>
                </div>
              </div>
            </div>

            <div
                class="flex items-center justify-between border-t border-slate-200/60 pt-3 mt-4 text-[10px] font-mono text-slate-400"
            >
              <span>共 {{ activePaths.length }} 项</span>

              <div
                  v-if="totalPathPages > 1"
                  class="flex items-center gap-3"
              >
                <span>{{ pathPage }} / {{ totalPathPages }} 页</span>

                <div class="flex gap-1.5">
                  <button
                      type="button"
                      class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="pathPage === 1"
                      aria-label="上一页"
                      @click="pathPage--"
                  >
                    <ChevronLeft class="w-3 h-3 text-slate-655" />
                  </button>

                  <button
                      type="button"
                      class="p-1 border border-slate-200 hover:border-slate-350 rounded-lg hover:bg-slate-50 cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                      :disabled="pathPage === totalPathPages"
                      aria-label="下一页"
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

      <div v-if="loading" class="loading-state">
        <div class="loading-pulse-dots">
          <span class="pulse-dot"></span>
          <span class="pulse-dot"></span>
          <span class="pulse-dot"></span>
        </div>

        <p class="loading-label">正在同步学习控制台</p>
        <p class="loading-hint">读取画像、路径、资源与学习事件</p>
      </div>
      <GlobalProfileDialog />
    </div>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  onActivated,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue'
import { useRouter } from 'vue-router'
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

import {
  isGlobalProfileVisible,
} from '@/features/profile/model/useGlobalProfile'

import GlobalProfileDialog from '@/features/profile/components/GlobalProfileDialog.vue'

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
  ClipboardCheckIcon as Assessment,
} from '@lucide/vue'

defineOptions({
  name: 'Home',
})

use([
  CanvasRenderer,
  RadarChart,
  TooltipComponent,
])

const router = useRouter()

const recommendationData = ref<RecommendationData | null>(null)
const profileRadarData = ref<ProfileRadarData | null>(null)
const continueLearningData = ref<ContinueLearningData | null>(null)
const quickActionsData = ref<QuickActionsData | null>(null)
const recentResourcesData = ref<RecentResourceItem[]>([])

const loading = ref(true)
const dataLoaded = ref(false)

const activeSlide = ref(0)

const carouselSlides = [
  {
    title: 'AI 智能导师',
    description:
        '书案旁微微散发微光的智能书本，为您的自主探索提供全天候深度答疑与循循善诱的辅导。',
    image: '/ai-tutor.jpg',
    path: '/tutor',
    actionText: '进入智能辅导',
  },
  {
    title: '多智能体资源引擎',
    description:
        '知识图书馆中轻盈起舞的智慧卡片，针对您的薄弱能力指标，并行生成丰富完备的专研学习包。',
    image: '/resource-engine.jpg',
    path: '/resource-generator',
    actionText: '一键生成资源',
  },
  {
    title: '个性化路径规划',
    description:
        '指引探索方向的星座灯塔，为您理清通往终点的每一步台阶，点亮专属的知识成长阶梯。',
    image: '/path-planner.jpg',
    path: '/path-planner',
    actionText: '开启路径规划',
  },
]

let carouselInterval: ReturnType<typeof setInterval> | null = null

const nextSlide = () => {
  activeSlide.value =
      (activeSlide.value + 1) % carouselSlides.length
}

const prevSlide = () => {
  activeSlide.value =
      (activeSlide.value - 1 + carouselSlides.length) %
      carouselSlides.length
}

const setSlide = (index: number) => {
  activeSlide.value = index
  resetAutoplay()
}

const startAutoplay = () => {
  stopAutoplay()

  carouselInterval = setInterval(() => {
    nextSlide()
  }, 6000)
}

const stopAutoplay = () => {
  if (!carouselInterval) {
    return
  }

  clearInterval(carouselInterval)
  carouselInterval = null
}

const resetAutoplay = () => {
  stopAutoplay()
  startAutoplay()
}

const goTo = (path: string) => {
  if (!path) {
    return
  }

  router.push(path)
}

const getIconComponent = (iconName: string) => {
  switch (iconName) {
    case 'chat':
      return ChatDotRound
    case 'resource':
      return DocumentCopy
    case 'path':
      return Guide
    case 'practice':
      return EditPen
    case 'monitor':
      return Monitor
    case 'reading':
      return Reading
    case 'assessment':
      return Assessment
    default:
      return DocumentCopy
  }
}

const getQuickActionStyle = (iconName: string) => {
  const styles: Record<string, any> = {
    chat: { '--qe-color': '#2563EB', '--qe-bg': '#EFF6FF', '--qe-border': '#BFDBFE', '--qe-hover': '#1D4ED8' },
    resource: { '--qe-color': '#4F46E5', '--qe-bg': '#EEF2FF', '--qe-border': '#C7D2FE', '--qe-hover': '#4338CA' },
    path: { '--qe-color': '#059669', '--qe-bg': '#ECFDF5', '--qe-border': '#A7F3D0', '--qe-hover': '#047857' },
    practice: { '--qe-color': '#D97706', '--qe-bg': '#FFFBEB', '--qe-border': '#FDE68A', '--qe-hover': '#B45309' },
    monitor: { '--qe-color': '#E11D48', '--qe-bg': '#FFF1F2', '--qe-border': '#FECDD3', '--qe-hover': '#BE123C' },
    assessment: { '--qe-color': '#9333EA', '--qe-bg': '#FAF5FF', '--qe-border': '#E9D5FF', '--qe-hover': '#7E22CE' },
    reading: { '--qe-color': '#0284C7', '--qe-bg': '#F0F9FF', '--qe-border': '#BAE6FD', '--qe-hover': '#0369A1' },
    default: { '--qe-color': '#0D9488', '--qe-bg': '#F0FDFA', '--qe-border': '#99F6E4', '--qe-hover': '#0F766E' }
  }
  return styles[iconName] || styles.default
}

const clampPercent = (
    value: unknown,
    fallback = 0,
) => {
  const numberValue = Number(value)

  if (!Number.isFinite(numberValue)) {
    return fallback
  }

  const normalized =
      numberValue <= 1
          ? numberValue * 100
          : numberValue

  return Math.max(
      0,
      Math.min(100, Math.round(normalized)),
  )
}

const formatDate = (
    value?: string | null,
) => {
  if (!value) {
    return ''
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat('zh-CN', {
    month: 'numeric',
    day: 'numeric',
  }).format(date)
}

const formatDateTime = (
    value?: string | null,
) => {
  if (!value) {
    return '暂无记录'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '暂无记录'
  }

  const now = new Date()
  const yesterday = new Date(now)

  yesterday.setDate(now.getDate() - 1)

  const time = new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)

  const isSameDay = (
      first: Date,
      second: Date,
  ) => {
    return (
        first.getFullYear() === second.getFullYear() &&
        first.getMonth() === second.getMonth() &&
        first.getDate() === second.getDate()
    )
  }

  if (isSameDay(date, now)) {
    return `今天 ${time}`
  }

  if (isSameDay(date, yesterday)) {
    return `昨天 ${time}`
  }

  return `${formatDate(value)} ${time}`
}

const radarSource = computed<any>(() => {
  if (!profileRadarData.value) {
    return null
  }

  return getRadarChartData(
      profileRadarData.value,
  )
})

const radarValues = computed<number[]>(() => {
  const rawValues =
      radarSource.value?.series?.[0]?.data?.[0]?.value

  if (!Array.isArray(rawValues)) {
    return []
  }

  return rawValues.map((item: unknown) => {
    return clampPercent(item)
  })
})

const radarOption = computed(() => {
  const rawData = radarSource.value

  if (!rawData?.radar) {
    return {}
  }

  return {
    ...rawData,
    tooltip: {
      trigger: 'item',
      backgroundColor: '#FCFFFF',
      borderColor: '#C8E4E3',
      borderWidth: 1,
      textStyle: {
        color: '#173B42',
        fontSize: 11,
      },
    },
    radar: {
      ...rawData.radar,
      radius: '68%',
      center: ['50%', '50%'],
      splitNumber: 4,
      splitLine: {
        lineStyle: {
          color: '#B9DEDC',
          width: 1,
        },
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: [
            'rgba(252, 255, 255, 0.9)',
            'rgba(216, 241, 240, 0.35)',
          ],
        },
      },
      axisLine: {
        lineStyle: {
          color: '#B9DEDC',
        },
      },
      axisLabel: {
        show: false,
      },
      axisName: {
        color: '#58747A',
        fontSize: 9,
        fontWeight: 'bold',
        fontFamily: 'Geist, sans-serif',
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value:
                rawData.series?.[0]?.data?.[0]?.value ||
                [],
            name: '能力得分',
            areaStyle: {
              color: 'rgba(70, 184, 180, 0.2)',
            },
            lineStyle: {
              color: '#0d9488',
              width: 1.8,
            },
            itemStyle: {
              color: '#0d9488',
              borderColor: '#FCFFFF',
              borderWidth: 2,
            },
            symbolSize: 4,
          },
        ],
      },
    ],
  }
})

const profileScore = computed(() => {
  const raw = profileRadarData.value as any
  const candidate = raw?.score

  if (
      candidate !== undefined &&
      candidate !== null
  ) {
    return clampPercent(candidate)
  }

  const values = radarValues.value

  if (!values.length) {
    return 0
  }

  const total = values.reduce(
      (sum, value) => sum + value,
      0,
  )

  return clampPercent(total / values.length)
})

const profileDimensions = computed(() => {
  const indicators =
      radarSource.value?.radar?.indicator
  const values = radarValues.value

  if (
      !Array.isArray(indicators) ||
      !values.length
  ) {
    return []
  }

  return indicators.map(
      (item: any, index: number) => ({
        name:
            item?.name ||
            `维度 ${index + 1}`,
        score: values[index] ?? 0,
      }),
  )
})

const weakAreas = computed(() => {
  const backendWeakAreas =
      profileRadarData.value?.weak_areas

  if (
      Array.isArray(backendWeakAreas) &&
      backendWeakAreas.length
  ) {
    return backendWeakAreas
        .slice(0, 3)
        .map((item: unknown) => String(item))
  }

  const lowDimensions =
      profileDimensions.value
          .filter((item) => item.score < 75)
          .sort((first, second) => {
            return first.score - second.score
          })
          .map((item) => item.name)

  return lowDimensions.length
      ? lowDimensions.slice(0, 2)
      : []
})

const weakAreaText = computed(() => {
  return weakAreas.value.join(' / ')
})

const recentResources = computed(() => {
  const list = [
    ...(recentResourcesData.value || []),
  ]

  list.sort((first, second) => {
    const firstTime = first.created_at
        ? new Date(first.created_at).getTime()
        : 0

    const secondTime = second.created_at
        ? new Date(second.created_at).getTime()
        : 0

    return secondTime - firstTime
  })

  return list.map((item) => ({
    id: item.id,
    title: item.title || '未命名资源',
    type: item.type || '文档',
    agent:
        item.agent ||
        '资源生成智能体',
    timeStr: formatDateTime(item.created_at),
    path: item.id
        ? `/resource-detail/${item.id}`
        : '/resource-generator',
  }))
})

const activePaths = computed(() => {
  const paths = [
    ...(continueLearningData.value
        ?.active_paths || []),
  ]

  paths.sort((first, second) => {
    const firstTime = new Date(
        first.last_learned_at ||
        first.updated_at ||
        0,
    ).getTime()

    const secondTime = new Date(
        second.last_learned_at ||
        second.updated_at ||
        0,
    ).getTime()

    return secondTime - firstTime
  })

  return paths.map((path) => {
    const rawDate =
        path.last_learned_at ||
        path.updated_at

    return {
      id: path.id,
      title:
          path.title ||
          '继续当前学习路径',
      currentNodeTitle:
          path.current_node_title ||
          '未开始节点',
      currentNodeId: path.current_node_id,
      progress: clampPercent(
          path.overall_progress,
          0,
      ),
      timeStr: formatDateTime(rawDate),
      path: path.current_node_id
          ? `/path-planner/node/${path.current_node_id}`
          : `/path-planner/overview/${path.id}`,
    }
  })
})

const ITEMS_PER_PAGE = 4

const resourcePage = ref(1)
const pathPage = ref(1)

const totalResourcePages = computed(() => {
  return (
      Math.ceil(
          recentResources.value.length /
          ITEMS_PER_PAGE,
      ) || 1
  )
})

const totalPathPages = computed(() => {
  return (
      Math.ceil(
          activePaths.value.length /
          ITEMS_PER_PAGE,
      ) || 1
  )
})

const paginatedResources = computed(() => {
  const start =
      (resourcePage.value - 1) *
      ITEMS_PER_PAGE

  return recentResources.value.slice(
      start,
      start + ITEMS_PER_PAGE,
  )
})

const paginatedPaths = computed(() => {
  const start =
      (pathPage.value - 1) *
      ITEMS_PER_PAGE

  return activePaths.value.slice(
      start,
      start + ITEMS_PER_PAGE,
  )
})

watch(recentResources, () => {
  resourcePage.value = 1
})

watch(activePaths, () => {
  pathPage.value = 1
})

const quickActions = computed<
    HomeActionItem[]
>(() => {
  const actions =
      quickActionsData.value?.actions || []

  return actions.slice(0, 6)
})

const loadAllData = async () => {
  if (!dataLoaded.value) {
    loading.value = true
  }

  const results =
      await Promise.allSettled([
        getRecommendation(),
        getProfileRadar(),
        getContinueLearning(),
        getQuickActions(),
        getRecentResources(),
      ])

  const [
    recommendationResult,
    radarResult,
    continueResult,
    actionsResult,
    resourcesResult,
  ] = results

  if (
      recommendationResult.status ===
      'fulfilled'
  ) {
    recommendationData.value =
        recommendationResult.value.data.data
  }

  if (radarResult.status === 'fulfilled') {
    profileRadarData.value =
        radarResult.value.data.data
  }

  if (
      continueResult.status === 'fulfilled'
  ) {
    continueLearningData.value =
        continueResult.value.data.data
  }

  if (
      actionsResult.status === 'fulfilled'
  ) {
    quickActionsData.value =
        actionsResult.value.data.data
  }

  if (
      resourcesResult.status === 'fulfilled'
  ) {
    recentResourcesData.value =
        resourcesResult.value.data.data ?? []
  }

  const failedCount = results.filter(
      (result) => result.status === 'rejected',
  ).length

  if (failedCount > 0) {
    console.warn(
        `${failedCount} 个首页接口请求失败，部分数据不可用`,
    )
  }

  dataLoaded.value = true
  loading.value = false
}

onMounted(() => {
  loadAllData()
  startAutoplay()
})

onActivated(() => {
  loadAllData()
})

onUnmounted(() => {
  stopAutoplay()
})
</script>

<style scoped>
.home-page {
  color: var(--color-text);
  background:
      radial-gradient(
          circle at 84% 2%,
          rgba(13, 148, 136, 0.03),
          transparent 30rem
      ),
      #fafafa;
}

.home-shell {
  width: min(
      1360px,
      calc(100% - 48px)
  );
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

.quick-entry-section {
  padding: 12px 0;
  border-top: 1px solid
  rgba(203, 213, 225, 0.62);
  border-bottom: 1px solid
  rgba(203, 213, 225, 0.62);
}

.quick-entry-grid {
  display: grid;
  grid-template-columns:
    repeat(
      auto-fit,
      minmax(184px, 1fr)
    );
  width: 100%;
  align-items: stretch;
}

.quick-entry-item {
  position: relative;
  display: grid;
  grid-template-columns:
    38px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 68px;
  padding: 10px 14px;
  border: 0;
  border-right: 1px solid
  rgba(203, 213, 225, 0.58);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition:
      background-color 180ms ease,
      box-shadow 180ms ease;
}

.quick-entry-item:last-child {
  border-right: 0;
}

.quick-entry-item:hover,
.quick-entry-item:focus-visible {
  background: var(--qe-bg);
  box-shadow: inset 0 -2px 0 var(--qe-hover);
  outline: none;
}

.quick-entry-icon {
  display: inline-flex;
  width: 38px;
  height: 38px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--qe-border);
  border-radius: 9px;
  background: var(--qe-bg);
  color: var(--qe-color);
  transition: border-color 180ms ease, background-color 180ms ease, color 180ms ease;
}

.quick-entry-item:hover .quick-entry-icon,
.quick-entry-item:focus-visible .quick-entry-icon {
  border-color: var(--qe-hover);
  background: var(--qe-hover);
  color: #ffffff;
}

.quick-entry-copy {
  display: block;
  min-width: 0;
}

.quick-entry-title {
  display: block;
  overflow: hidden;
  color: #1e293b;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-entry-description {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 4px;
  color: #94a3b8;
  font-size: 10px;
  line-height: 1.45;
  white-space: normal;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.quick-entry-arrow {
  width: 15px;
  height: 15px;
  color: #cbd5e1;
  transition: color 180ms ease, transform 180ms ease;
}

.quick-entry-item:hover .quick-entry-arrow,
.quick-entry-item:focus-visible .quick-entry-arrow {
  color: var(--qe-hover);
  transform: translateX(2px);
}

.history-item {
  transition: all 0.2s ease;
}

.history-item:hover {
  background-color:
      rgba(241, 245, 249, 0.6);
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition:
      all 0.6s
      cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-fade-enter-from {
  opacity: 0;
  transform: scale(1.01);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: scale(0.99);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 52vh;
  gap: 0;
  animation:
      load-enter 0.4s
      cubic-bezier(0.32, 0.72, 0, 1)
      forwards;
}

.loading-pulse-dots {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 20px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-action);
  animation:
      dot-breathe 1.6s ease-in-out
      infinite;
}

.pulse-dot:nth-child(1) {
  animation-delay: 0s;
}

.pulse-dot:nth-child(2) {
  animation-delay: 0.18s;
}

.pulse-dot:nth-child(3) {
  animation-delay: 0.36s;
}

@keyframes dot-breathe {
  0%,
  80%,
  100% {
    opacity: 0.25;
    transform: scale(0.85);
  }

  40% {
    opacity: 1;
    transform: scale(1.15);
  }
}

@keyframes load-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.loading-label {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  letter-spacing: -0.01em;
}

.loading-hint {
  margin: 6px 0 0;
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--color-text-faint);
  letter-spacing: 0.01em;
}

@media (
prefers-reduced-motion: reduce
) {
  .pulse-dot {
    animation: none;
    opacity: 0.6;
    transform: scale(1);
  }

  .loading-state {
    animation: none;
  }

  .quick-entry-item,
  .quick-entry-icon,
  .quick-entry-arrow {
    transition: none;
  }
}

@media (max-width: 1024px) {
  .home-shell {
    width: calc(100% - 32px);
  }
}

@media (max-width: 900px) {
  .quick-entry-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .quick-entry-item:nth-child(2n) {
    border-right: 0;
  }

  .quick-entry-item:nth-child(n + 3) {
    border-top: 1px solid
    rgba(203, 213, 225, 0.58);
  }
}

@media (max-width: 560px) {
  .home-shell {
    width: calc(100% - 24px);
    padding-left: 0;
    padding-right: 0;
  }

  .quick-entry-grid {
    grid-template-columns: 1fr;
  }

  .quick-entry-item,
  .quick-entry-item:nth-child(2n) {
    border-right: 0;
  }

  .quick-entry-item:nth-child(n + 2) {
    border-top: 1px solid
    rgba(203, 213, 225, 0.58);
  }

  .quick-entry-title {
    white-space: normal;
  }
}
</style>