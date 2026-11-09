<template>
  <main class="home-page min-h-screen font-sans antialiased pb-16">
    <div class="home-shell max-w-7xl mx-auto px-6 py-8">
      <!-- 顶部工作台环境状态栏 -->
      <header class="workbench-header mb-8">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-6 border-b border-[var(--color-border-light)]">
          <div>
            <div class="flex items-center gap-2.5">
              <h1 class="text-xl font-bold text-[var(--color-text-strong)] tracking-tight">
                研学控制台
              </h1>
              <span class="inline-flex items-center px-2 py-0.5 text-[11px] font-mono font-medium rounded bg-[var(--color-primary-soft)] text-[var(--color-primary-text)] border border-[var(--color-primary-border)]">
                学术工作台
              </span>
            </div>
            <p class="text-xs text-[var(--color-text-secondary)] mt-1">
              基于 8 维画像认知建模与多智能体协同的高效自适应研学空间
            </p>
          </div>

          <div class="flex items-center gap-4 text-xs text-[var(--color-text-secondary)] font-mono">
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--color-surface)] border border-[var(--color-border-light)]">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span class="text-[11px] text-[var(--color-text-secondary)]">智能体集群就绪</span>
            </div>
            <span class="hidden md:inline text-[11px] text-[var(--color-text-faint)]">{{ currentDateFormatted }}</span>
          </div>
        </div>
      </header>

      <div v-if="dataLoaded" class="dashboard-content space-y-8">
        <!-- 核心第一屏：学习断点聚焦 / 研学起航舱 + 能力画像诊断 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
          <!-- 左侧 2 栏：当前学习断点直达 (Active) / 学科起航舱 (Cold Start) -->
          <div class="lg:col-span-2 workbench-card p-6 flex flex-col justify-between">
            <!-- 状态 A: 存在活跃学习路径 -->
            <div v-if="primaryActivePath" class="space-y-5">
              <div class="flex items-center justify-between">
                <div class="inline-flex items-center gap-2">
                  <span class="flex h-2 w-2 rounded-full bg-[var(--color-primary)]"></span>
                  <span class="text-xs font-bold text-[var(--color-primary-text)] tracking-wider uppercase font-mono">
                    当前学习断点
                  </span>
                </div>
                <div class="text-[11px] text-[var(--color-text-secondary)] font-mono flex items-center gap-1.5">
                  <Clock class="w-3.5 h-3.5 text-[var(--color-text-faint)]" />
                  <span>上次学习：{{ primaryActivePath.timeStr }}</span>
                </div>
              </div>

              <div class="space-y-3">
                <h2 class="text-xl sm:text-2xl font-bold text-[var(--color-text-strong)] tracking-tight leading-snug">
                  {{ primaryActivePath.title }}
                </h2>

                <div class="inline-flex items-center gap-2.5 px-3 py-2 rounded-md bg-[var(--color-bg)] border border-[var(--color-border-light)] text-xs text-[var(--color-text)]">
                  <Target class="w-4 h-4 text-[var(--color-primary)] shrink-0" />
                  <span class="text-[var(--color-text-secondary)]">当前攻坚节点：</span>
                  <strong class="font-semibold text-[var(--color-text-strong)]">{{ primaryActivePath.currentNodeTitle }}</strong>
                </div>
              </div>

              <!-- 学习进度条（采用 scaleX 硬件加速，防止宽度重排抖动） -->
              <div class="space-y-1.5 pt-1">
                <div class="flex items-center justify-between text-xs font-mono">
                  <span class="text-[var(--color-text-secondary)]">总体掌握进度</span>
                  <span class="font-bold text-[var(--color-primary-text)]">{{ primaryActivePath.progress }}%</span>
                </div>
                <div class="w-full h-2 rounded-full bg-[var(--color-bg)] overflow-hidden border border-[var(--color-border-light)]">
                  <div
                    class="h-full bg-[var(--color-primary)] origin-left transition-transform duration-500 ease-out"
                    :style="{ transform: `scaleX(${primaryActivePath.progress / 100})` }"
                  ></div>
                </div>
              </div>

              <div class="pt-2 flex flex-wrap items-center gap-3">
                <Button
                  class="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold text-xs rounded-md px-5 py-2.5 shadow-sm transition-all cursor-pointer flex items-center gap-2"
                  @click="goTo(primaryActivePath.path)"
                >
                  <Play class="w-3.5 h-3.5 fill-current" />
                  <span>继续攻坚节点</span>
                </Button>

                <Button
                  variant="outline"
                  class="text-xs font-medium text-[var(--color-text)] hover:text-[var(--color-primary-text)] hover:bg-[var(--color-primary-soft)] border-[var(--color-border)] rounded-md px-4 py-2.5 transition-colors cursor-pointer"
                  @click="goTo(`/path-planner/overview/${primaryActivePath.id}`)"
                >
                  <span>查看完整图谱</span>
                </Button>

                <Button
                  variant="ghost"
                  class="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-primary-text)] hover:bg-transparent px-3 py-2.5 transition-colors cursor-pointer ml-auto"
                  @click="goTo('/tutor')"
                >
                  <span>呼叫 AI 导师答疑 →</span>
                </Button>
              </div>
            </div>

            <!-- 状态 B: 冷启动 / 暂无活跃路径时的“408 核心学科研学起航舱” -->
            <div v-else class="space-y-5 flex-1 flex flex-col justify-between">
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <div class="inline-flex items-center gap-2">
                    <Sparkles class="w-4 h-4 text-[var(--color-primary)]" />
                    <span class="text-xs font-bold text-[var(--color-primary-text)] tracking-wider uppercase font-mono">
                      学科研学起航舱
                    </span>
                  </div>
                  <span class="text-[11px] font-mono text-[var(--color-text-faint)]">
                    多智能体协作已就绪
                  </span>
                </div>

                <div>
                  <h2 class="text-xl font-bold text-[var(--color-text-strong)] tracking-tight">
                    {{ recommendationData?.recommendation?.title || '规划系统化学科学习路径' }}
                  </h2>
                  <p class="text-xs text-[var(--color-text-secondary)] mt-1 leading-relaxed">
                    {{ recommendationData?.recommendation?.text || '多智能体将根据学科考纲与认知水位，自主解构知识图谱、规划进阶阶段并生成随堂自测。' }}
                  </p>
                </div>
              </div>

              <!-- 408 核心学科快捷起航卡片（彻底消除空白，提供即时学术探索价值） -->
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-2">
                <div
                  v-for="sub in coreSubjectPresets"
                  :key="sub.name"
                  class="subject-preset-card p-3 rounded-md border border-[var(--color-border-light)] bg-[var(--color-bg)] hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-soft)] transition-all cursor-pointer group"
                  @click="goTo(`/path-planner?topic=${encodeURIComponent(sub.name)}`)"
                >
                  <div class="flex items-center justify-between mb-1.5">
                    <span class="text-base">{{ sub.icon }}</span>
                    <span class="text-[10px] font-mono text-[var(--color-text-faint)] group-hover:text-[var(--color-primary-text)]">
                      规划 →
                    </span>
                  </div>
                  <strong class="block text-xs font-bold text-[var(--color-text-strong)] group-hover:text-[var(--color-primary-text)]">
                    {{ sub.name }}
                  </strong>
                  <span class="block text-[10px] text-[var(--color-text-secondary)] truncate mt-0.5">
                    {{ sub.focus }}
                  </span>
                </div>
              </div>

              <!-- 底部操作入口 -->
              <div class="pt-2 flex flex-wrap items-center gap-3">
                <Button
                  class="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold text-xs rounded-md px-5 py-2.5 shadow-sm transition-all cursor-pointer"
                  @click="goTo(recommendationData?.recommendation?.path || '/path-planner')"
                >
                  {{ recommendationData?.recommendation?.action || '开启个性化路径规划' }}
                </Button>

                <Button
                  variant="outline"
                  class="text-xs font-medium text-[var(--color-text)] hover:text-[var(--color-primary-text)] hover:bg-[var(--color-primary-soft)] border-[var(--color-border)] rounded-md px-4 py-2.5 transition-colors cursor-pointer"
                  @click="goTo('/resource-generator')"
                >
                  生成多模态教学资源
                </Button>

                <Button
                  variant="ghost"
                  class="text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-primary-text)] hover:bg-transparent px-3 py-2.5 transition-colors cursor-pointer ml-auto"
                  @click="goTo('/tutor')"
                >
                  向 AI 导师提问 →
                </Button>
              </div>
            </div>
          </div>

          <!-- 右侧 1 栏：能力画像诊断 (Proficiency & Guidance Overview) -->
          <div class="lg:col-span-1 workbench-card p-6 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between pb-3 border-b border-[var(--color-border-light)]">
                <h2 class="text-xs font-bold text-[var(--color-text-strong)] uppercase tracking-wider font-mono">
                  能力画像诊断
                </h2>
                <Button
                  variant="ghost"
                  class="text-xs font-medium text-[var(--color-primary-text)] hover:text-[var(--color-primary)] p-0 cursor-pointer h-7 hover:bg-transparent"
                  @click="isGlobalProfileVisible = true"
                >
                  完整报告 →
                </Button>
              </div>

              <div class="flex items-center gap-4 my-4">
                <div class="score-badge flex flex-col items-center justify-center text-center shrink-0 min-w-[84px] border-r border-[var(--color-border-light)] pr-4">
                  <span class="text-[10px] text-[var(--color-primary-text)] font-semibold uppercase tracking-wider">
                    画像评分
                  </span>
                  <strong class="text-3xl font-extrabold text-[var(--color-text-strong)] mt-1 leading-none font-mono">
                    {{ profileScore }}
                  </strong>
                  <span class="text-[10px] font-mono text-[var(--color-primary-text)] font-bold bg-[var(--color-primary-soft)] px-1.5 py-0.5 rounded border border-[var(--color-primary-border)] mt-2.5">
                    {{ tierBadgeText }}
                  </span>
                </div>

                <div class="flex-1 h-[145px] relative min-w-0">
                  <div
                    v-if="!profileRadarData"
                    class="absolute inset-0 flex flex-col items-center justify-center text-[var(--color-text-faint)] text-xs"
                  >
                    <div class="w-4 h-4 rounded-full border-2 border-[var(--color-primary)] border-t-transparent animate-spin"></div>
                  </div>
                  <v-chart
                    v-else
                    class="chart"
                    :option="radarOption"
                    autoresize
                  />
                </div>
              </div>
            </div>

            <div class="diagnostic-advice pt-3 border-t border-[var(--color-border-light)]">
              <div class="text-[10px] font-bold text-[var(--color-primary-text)] uppercase tracking-wider mb-1">
                导学自适应建议
              </div>
              <p class="text-xs text-[var(--color-text-secondary)] leading-relaxed text-left">
                {{ formattedDiagnosticNote }}
              </p>
            </div>
          </div>
        </div>

        <!-- 核心学术工具矩阵 (Quick Actions Grid) -->
        <section class="quick-entry-section" aria-label="核心学术工具">
          <div class="quick-entry-grid">
            <button
              v-for="action in curatedQuickActions"
              :key="action.label"
              type="button"
              class="quick-entry-item"
              @click="goTo(action.path)"
            >
              <span class="quick-entry-icon" aria-hidden="true">
                <component
                  :is="getIconComponent(action.icon)"
                  class="w-4 h-4"
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

        <!-- 双流执行区：路径规划进度 vs 资源生成历史 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
          <!-- 左侧：路径规划历史 -->
          <section class="workbench-card p-5 flex flex-col justify-between min-h-[380px]">
            <div class="space-y-4 flex-1">
              <div class="flex items-center justify-between pb-3 border-b border-[var(--color-border-light)]">
                <div class="flex items-center gap-2">
                  <Compass class="w-4 h-4 text-[var(--color-primary)]" />
                  <h3 class="text-xs font-bold text-[var(--color-text-strong)] font-mono tracking-wider uppercase">
                    活跃学习路径 ({{ activePaths.length }})
                  </h3>
                </div>

                <Button
                  variant="ghost"
                  class="text-xs font-medium text-[var(--color-primary-text)] hover:text-[var(--color-primary)] p-0 cursor-pointer h-6 hover:bg-transparent"
                  @click="goTo('/path-planner')"
                >
                  规划新路径 →
                </Button>
              </div>

              <div class="history-list-container flex flex-col justify-start">
                <div v-if="paginatedPaths.length" class="divide-y divide-[var(--color-border-light)]">
                  <div
                    v-for="path in paginatedPaths"
                    :key="path.id"
                    class="path-item py-3 px-2 rounded-md transition-colors"
                  >
                    <div class="flex items-start justify-between gap-3">
                      <div class="space-y-1 text-left min-w-0 flex-1">
                        <strong class="block text-xs font-semibold text-[var(--color-text-strong)] truncate">
                          {{ path.title }}
                        </strong>
                        <div class="text-[11px] text-[var(--color-text-secondary)] font-mono">
                          当前节点：
                          <span class="text-[var(--color-text)] font-medium">
                            {{ path.currentNodeTitle }}
                          </span>
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        class="text-[11px] h-7 px-3 bg-[var(--color-surface)] text-[var(--color-primary-text)] hover:bg-[var(--color-primary-soft)] hover:text-[var(--color-primary-text)] border-[var(--color-border)] rounded shadow-none transition-colors cursor-pointer shrink-0"
                        @click="goTo(path.path)"
                      >
                        继续学习
                      </Button>
                    </div>

                    <div class="mt-2.5 space-y-1">
                      <div class="flex items-center justify-between text-[10px] text-[var(--color-text-secondary)] font-mono">
                        <span>进度</span>
                        <span class="font-bold text-[var(--color-primary-text)]">{{ path.progress }}%</span>
                      </div>
                      <div class="w-full h-1.5 bg-[var(--color-bg)] rounded-full overflow-hidden border border-[var(--color-border-light)]">
                        <div
                          class="h-full bg-[var(--color-primary)] rounded-full origin-left transition-transform duration-500 ease-out"
                          :style="{ transform: `scaleX(${path.progress / 100})` }"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  v-else
                  class="h-48 border border-dashed border-[var(--color-border)] rounded-md flex flex-col items-center justify-center text-[var(--color-text-secondary)] text-xs space-y-3"
                >
                  <p>暂无活跃路径 · 规划后在此实时跟踪攻坚进度</p>
                  <Button
                    size="sm"
                    class="rounded-md text-xs font-medium bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white cursor-pointer border-none"
                    @click="goTo('/path-planner')"
                  >
                    开始规划第一条路径
                  </Button>
                </div>
              </div>
            </div>

            <!-- 路径分页 -->
            <div class="flex items-center justify-between border-t border-[var(--color-border-light)] pt-3 mt-4 text-[11px] font-mono text-[var(--color-text-secondary)]">
              <span>共 {{ activePaths.length }} 项</span>

              <div v-if="totalPathPages > 1" class="flex items-center gap-3">
                <span>{{ pathPage }} / {{ totalPathPages }} 页</span>
                <div class="flex gap-1.5">
                  <button
                    type="button"
                    class="p-1 border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded hover:bg-[var(--color-bg)] cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="pathPage === 1"
                    aria-label="上一页"
                    @click="pathPage--"
                  >
                    <ChevronLeft class="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
                  </button>
                  <button
                    type="button"
                    class="p-1 border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded hover:bg-[var(--color-bg)] cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="pathPage === totalPathPages"
                    aria-label="下一页"
                    @click="pathPage++"
                  >
                    <ChevronRight class="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- 右侧：资源生成历史 -->
          <section class="workbench-card p-5 flex flex-col justify-between min-h-[380px]">
            <div class="space-y-4 flex-1">
              <div class="flex items-center justify-between pb-3 border-b border-[var(--color-border-light)]">
                <div class="flex items-center gap-2">
                  <Files class="w-4 h-4 text-[var(--color-primary)]" />
                  <h3 class="text-xs font-bold text-[var(--color-text-strong)] font-mono tracking-wider uppercase">
                    资源生成记录 ({{ recentResources.length }})
                  </h3>
                </div>

                <Button
                  variant="ghost"
                  class="text-xs font-medium text-[var(--color-primary-text)] hover:text-[var(--color-primary)] p-0 cursor-pointer h-6 hover:bg-transparent"
                  @click="goTo('/resource-generator')"
                >
                  生成新资源 →
                </Button>
              </div>

              <div class="history-list-container flex flex-col justify-start">
                <div v-if="paginatedResources.length" class="divide-y divide-[var(--color-border-light)]">
                  <div
                    v-for="resource in paginatedResources"
                    :key="resource.id"
                    class="resource-item flex items-center justify-between py-3 px-2 rounded-md hover:bg-[var(--color-bg)] transition-colors cursor-pointer"
                    @click="goTo(resource.path)"
                  >
                    <div class="space-y-1 text-left min-w-0 pr-3 flex-1">
                      <strong class="block text-xs font-semibold text-[var(--color-text-strong)] truncate">
                        {{ resource.title }}
                      </strong>
                      <div class="flex items-center gap-2 text-[10px] text-[var(--color-text-secondary)] font-mono">
                        <span class="font-medium text-[var(--color-primary-text)] bg-[var(--color-primary-soft)] px-1.5 py-0.5 rounded border border-[var(--color-primary-border)]">
                          {{ resource.agent }}
                        </span>
                        <span>•</span>
                        <span>{{ resource.timeStr }}</span>
                      </div>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                      <span class="inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-[var(--color-border-light)]">
                        {{ resource.type }}
                      </span>
                    </div>
                  </div>
                </div>

                <div
                  v-else
                  class="h-48 border border-dashed border-[var(--color-border)] rounded-md flex flex-col items-center justify-center text-[var(--color-text-secondary)] text-xs space-y-3"
                >
                  <p>暂无独立资源生成记录 · 多智能体生成产物将在此汇聚</p>
                  <Button
                    size="sm"
                    class="rounded-md text-xs font-medium bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white cursor-pointer border-none"
                    @click="goTo('/resource-generator')"
                  >
                    一键生成多模态资源
                  </Button>
                </div>
              </div>
            </div>

            <!-- 资源分页 -->
            <div class="flex items-center justify-between border-t border-[var(--color-border-light)] pt-3 mt-4 text-[11px] font-mono text-[var(--color-text-secondary)]">
              <span>共 {{ recentResources.length }} 项</span>

              <div v-if="totalResourcePages > 1" class="flex items-center gap-3">
                <span>{{ resourcePage }} / {{ totalResourcePages }} 页</span>
                <div class="flex gap-1.5">
                  <button
                    type="button"
                    class="p-1 border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded hover:bg-[var(--color-bg)] cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="resourcePage === 1"
                    aria-label="上一页"
                    @click="resourcePage--"
                  >
                    <ChevronLeft class="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
                  </button>
                  <button
                    type="button"
                    class="p-1 border border-[var(--color-border)] hover:border-[var(--color-border-hover)] rounded hover:bg-[var(--color-bg)] cursor-pointer disabled:opacity-30 disabled:hover:bg-transparent"
                    :disabled="resourcePage === totalResourcePages"
                    aria-label="下一页"
                    @click="resourcePage++"
                  >
                    <ChevronRight class="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-pulse-dots">
          <span class="pulse-dot"></span>
          <span class="pulse-dot"></span>
          <span class="pulse-dot"></span>
        </div>
        <p class="loading-label">正在同步学术控制台</p>
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
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
  CompassIcon as Compass,
  MonitorIcon as Monitor,
  BookOpenIcon as Reading,
  ChevronLeftIcon as ChevronLeft,
  ChevronRightIcon as ChevronRight,
  FilesIcon as Files,
  ClipboardCheckIcon as Assessment,
  PlayIcon as Play,
  TargetIcon as Target,
  SparklesIcon as Sparkles,
  ClockIcon as Clock,
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
const route = useRoute()

const recommendationData = ref<RecommendationData | null>(null)
const profileRadarData = ref<ProfileRadarData | null>(null)
const continueLearningData = ref<ContinueLearningData | null>(null)
const quickActionsData = ref<QuickActionsData | null>(null)
const recentResourcesData = ref<RecentResourceItem[]>([])

const loading = ref(true)
const dataLoaded = ref(false)

// 408 核心学科快捷起航卡片（消除冷启动空白，提供即时学术探索）
const coreSubjectPresets = [
  { name: '计算机网络', icon: '🌐', focus: 'TCP/IP 协议栈 · 拥塞控制' },
  { name: '操作系统', icon: '⚡', focus: '进程同步 · 虚拟分页寻址' },
  { name: '数据结构', icon: '🌲', focus: '平衡树 · 图论最短路径' },
  { name: '组成原理', icon: '💻', focus: '指令流水线 · Cache 一致性' },
]

const currentDateFormatted = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date())
})

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
      return Compass
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

// 经过专业设计的清晰学术工具列表（杜绝后端返回负向未完成提示和文字溢出截断）
const curatedQuickActions = computed(() => {
  return [
    {
      label: '智能辅导',
      description: '苏格拉底式启发答疑与深层推导',
      path: '/tutor',
      icon: 'chat',
    },
    {
      label: '资源引擎',
      description: '课件、代码、导图与随堂练习生成',
      path: '/resource-generator',
      icon: 'resource',
    },
    {
      label: '路径规划',
      description: '知识图谱解构与攻坚阶梯路线',
      path: '/path-planner',
      icon: 'path',
    },
    {
      label: '学习题库',
      description: '408 经典真题自测与错题智能收录',
      path: '/quiz-bank',
      icon: 'practice',
    },
    {
      label: '学情评估',
      description: '8 维能力评估与自适应学习建议',
      path: '/learning-assessment',
      icon: 'assessment',
    },
  ]
})

const clampPercent = (value: unknown, fallback = 0) => {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) {
    return fallback
  }
  const normalized = numberValue <= 1 ? numberValue * 100 : numberValue
  return Math.max(0, Math.min(100, Math.round(normalized)))
}

const formatDate = (value?: string | null) => {
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

const formatDateTime = (value?: string | null) => {
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

  const isSameDay = (first: Date, second: Date) => {
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
  return getRadarChartData(profileRadarData.value)
})

const radarValues = computed<number[]>(() => {
  const rawValues = radarSource.value?.series?.[0]?.data?.[0]?.value
  if (!Array.isArray(rawValues)) {
    return []
  }
  return rawValues.map((item: unknown) => clampPercent(item))
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
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: rawData.series?.[0]?.data?.[0]?.value || [],
            name: '能力得分',
            areaStyle: {
              color: 'rgba(70, 184, 180, 0.22)',
            },
            lineStyle: {
              color: '#46B8B4',
              width: 2,
            },
            itemStyle: {
              color: '#46B8B4',
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
  if (candidate !== undefined && candidate !== null) {
    return clampPercent(candidate)
  }
  const values = radarValues.value
  if (!values.length) {
    return 0
  }
  const total = values.reduce((sum, value) => sum + value, 0)
  return clampPercent(total / values.length)
})

const tierBadgeText = computed(() => {
  const score = profileScore.value
  if (score >= 85) return 'S-Tier'
  if (score >= 70) return 'A-Tier'
  if (score >= 55) return 'B-Tier'
  return 'C-Tier'
})

const profileDimensions = computed(() => {
  const indicators = radarSource.value?.radar?.indicator
  const values = radarValues.value
  if (!Array.isArray(indicators) || !values.length) {
    return []
  }
  return indicators.map((item: any, index: number) => ({
    name: item?.name || `维度 ${index + 1}`,
    score: values[index] ?? 0,
  }))
})

const weakAreas = computed(() => {
  const backendWeakAreas = profileRadarData.value?.weak_areas
  if (Array.isArray(backendWeakAreas) && backendWeakAreas.length) {
    return backendWeakAreas.slice(0, 3).map((item: unknown) => String(item))
  }
  const lowDimensions = profileDimensions.value
    .filter((item) => item.score < 75)
    .sort((first, second) => first.score - second.score)
    .map((item) => item.name)

  return lowDimensions.length ? lowDimensions.slice(0, 2) : []
})

const weakAreaText = computed(() => {
  return weakAreas.value.join(' / ')
})

const formattedDiagnosticNote = computed(() => {
  if (weakAreaText.value) {
    return `综合指数 ${profileScore.value} 分。薄弱攻坚方向：${weakAreaText.value}。建议针对薄弱知识点规划专项路径或生成针对性练习。`
  }
  if (profileScore.value >= 70) {
    return `综合指数 ${profileScore.value} 分，学情掌握良好。建议在当前学科基础上开启深度探究或进行全真模拟自测。`
  }
  return '尚未沉淀足够作答信号。建议先开启首条路径或做一组 408 随堂练习，以提升认知模型置信度。'
})

const recentResources = computed(() => {
  const list = [...(recentResourcesData.value || [])]
  list.sort((first, second) => {
    const firstTime = first.created_at ? new Date(first.created_at).getTime() : 0
    const secondTime = second.created_at ? new Date(second.created_at).getTime() : 0
    return secondTime - firstTime
  })

  return list.map((item) => ({
    id: item.id,
    title: item.title || '未命名资源',
    type: item.type || '文档',
    agent: item.agent || '资源生成智能体',
    timeStr: formatDateTime(item.created_at),
    path: item.id ? `/resource-detail/${item.id}` : '/resource-generator',
  }))
})

const activePaths = computed(() => {
  const paths = [...(continueLearningData.value?.active_paths || [])]
  paths.sort((first, second) => {
    const firstTime = new Date(first.last_learned_at || first.updated_at || 0).getTime()
    const secondTime = new Date(second.last_learned_at || second.updated_at || 0).getTime()
    return secondTime - firstTime
  })

  return paths.map((path) => {
    const rawDate = path.last_learned_at || path.updated_at
    return {
      id: path.id,
      title: path.title || '未命名学习路径',
      currentNodeTitle: path.current_node_title || '未开始节点',
      currentNodeId: path.current_node_id,
      progress: clampPercent(path.overall_progress, 0),
      timeStr: formatDateTime(rawDate),
      path: path.current_node_id
        ? `/path-planner/node/${path.current_node_id}`
        : `/path-planner/overview/${path.id}`,
    }
  })
})

const primaryActivePath = computed(() => {
  return activePaths.value[0] || null
})

const ITEMS_PER_PAGE = 4
const resourcePage = ref(1)
const pathPage = ref(1)

const totalResourcePages = computed(() => {
  return Math.ceil(recentResources.value.length / ITEMS_PER_PAGE) || 1
})

const totalPathPages = computed(() => {
  return Math.ceil(activePaths.value.length / ITEMS_PER_PAGE) || 1
})

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

const loadAllData = async () => {
  if (!dataLoaded.value) {
    loading.value = true
  }

  const results = await Promise.allSettled([
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

  if (recommendationResult.status === 'fulfilled') {
    recommendationData.value = recommendationResult.value.data.data
  }
  if (radarResult.status === 'fulfilled') {
    profileRadarData.value = radarResult.value.data.data
  }
  if (continueResult.status === 'fulfilled') {
    continueLearningData.value = continueResult.value.data.data
  }
  if (actionsResult.status === 'fulfilled') {
    quickActionsData.value = actionsResult.value.data.data
  }
  if (resourcesResult.status === 'fulfilled') {
    recentResourcesData.value = resourcesResult.value.data.data ?? []
  }

  const failedCount = results.filter((result) => result.status === 'rejected').length
  if (failedCount > 0) {
    console.warn(`${failedCount} 个首页接口请求失败，部分数据不可用`)
  }

  dataLoaded.value = true
  loading.value = false
}

watch(
  () => route.query.onboarding,
  (current, previous) => {
    if (previous === 'true' && current !== 'true') {
      void loadAllData()
    }
  },
)

onMounted(() => {
  loadAllData()
})

onActivated(() => {
  loadAllData()
})
</script>

<style scoped>
.home-page {
  color: var(--color-text);
  background: var(--color-page-bg);
}

.home-shell {
  width: min(1360px, calc(100% - 48px));
  margin: 0 auto;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
}

/* 学术工作台统一定义卡片容器 */
.workbench-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--duration-fast) var(--ease-out);
}

.workbench-card:hover {
  border-color: var(--color-border);
}

.chart {
  width: 100%;
  height: 100%;
}

/* 核心学科快捷起航卡片 */
.subject-preset-card {
  transition: all var(--duration-fast) var(--ease-out);
}

.subject-preset-card:hover {
  transform: translateY(-1px);
}

/* 核心学术工具矩阵 */
.quick-entry-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.quick-entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  width: 100%;
  align-items: stretch;
}

.quick-entry-item {
  position: relative;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 14px;
  align-items: center;
  gap: 12px;
  min-width: 0;
  min-height: 64px;
  padding: 12px 16px;
  border: 0;
  border-right: 1px solid var(--color-border-light);
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-out);
}

.quick-entry-item:last-child {
  border-right: 0;
}

.quick-entry-item:hover,
.quick-entry-item:focus-visible {
  background: var(--color-bg);
  outline: none;
}

.quick-entry-icon {
  display: inline-flex;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-primary-text);
  transition: border-color var(--duration-fast) var(--ease-out), background-color var(--duration-fast) var(--ease-out), color var(--duration-fast) var(--ease-out);
}

.quick-entry-item:hover .quick-entry-icon,
.quick-entry-item:focus-visible .quick-entry-icon {
  border-color: var(--color-primary-border);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.quick-entry-copy {
  display: block;
  min-width: 0;
}

.quick-entry-title {
  display: block;
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-entry-description {
  display: block;
  overflow: hidden;
  margin-top: 2px;
  color: var(--color-text-secondary);
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.quick-entry-arrow {
  width: 14px;
  height: 14px;
  color: var(--color-text-faint);
  transition: color var(--duration-fast) var(--ease-out), transform var(--duration-fast) var(--ease-out);
}

.quick-entry-item:hover .quick-entry-arrow,
.quick-entry-item:focus-visible .quick-entry-arrow {
  color: var(--color-primary-text);
  transform: translateX(2px);
}

.path-item:hover {
  background-color: var(--color-bg);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 52vh;
  animation: load-enter var(--duration-normal) var(--ease-out) forwards;
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
  background: var(--color-primary);
  animation: dot-breathe 1.6s ease-in-out infinite;
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
  0%, 80%, 100% {
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
  color: var(--color-text-secondary);
  letter-spacing: 0.01em;
}

@media (prefers-reduced-motion: reduce) {
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
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .quick-entry-item:nth-child(2n) {
    border-right: 0;
  }
  .quick-entry-item:nth-child(n + 3) {
    border-top: 1px solid var(--color-border-light);
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
    border-top: 1px solid var(--color-border-light);
  }
  .quick-entry-title {
    white-space: normal;
  }
}
</style>
