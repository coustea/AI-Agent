<template>
  <main class="path-overview-page">
    <section v-if="loading" class="state-view">
      <div class="state-spinner"></div>
      <p>正在加载学习路径...</p>
    </section>

    <section v-else-if="!path && !isGenerating" class="state-view empty-state">
      <h2>还没有可用的学习路径</h2>
      <p>创建学习路径后，系统会在这里展示阶段、节点、解锁状态和学习进度。</p>
      <button class="primary-action" type="button" @click="router.push('/path-planner')">
        创建学习路径
      </button>
    </section>

    <section
        v-else-if="isGenerating"
        class="persistent-generation-stage"
    >
      <section
          class="generation-waiting-card"
          role="status"
          aria-live="polite"
          aria-atomic="true"
      >
        <template v-if="pathGenerationError">
          <div class="generation-result-state generation-error-state">
            <div
                class="generation-result-icon generation-error-icon"
                aria-hidden="true"
            >
              !
            </div>

            <div class="generation-result-copy">
              <h2>学习路径生成失败</h2>
              <p>
                路径任务信息已经保留，可以重新连接后台任务或返回创建页面。
              </p>
            </div>

            <div class="generation-error-detail">
              {{ pathGenerationError }}
            </div>

            <div class="generation-result-actions">
              <button
                  class="generation-secondary-action"
                  type="button"
                  @click="router.push('/path-planner')"
              >
                返回创建页面
              </button>

              <button
                  class="generation-primary-action"
                  type="button"
                  @click="retryPathStatus"
              >
                重新连接任务
              </button>
            </div>
          </div>
        </template>

        <template v-else-if="generatingProgressRounded >= 100">
          <div class="generation-result-state generation-success-state">
            <div
                class="generation-result-icon generation-success-icon"
                aria-hidden="true"
            >
              ✓
            </div>

            <div class="generation-result-copy">
              <h2>学习路径已生成</h2>
              <p>
                路径阶段、知识节点与前置依赖已经编排完成。
              </p>
            </div>

            <div class="generation-success-summary">
              <span></span>
              正在打开学习路径总览
            </div>

            <div class="generation-success-track">
              <i></i>
            </div>
          </div>
        </template>

        <template v-else>
          <header class="generation-loading-header">
            <div
                class="generation-loader"
                aria-hidden="true"
            >
              <div class="generation-loader-ring"></div>
              <span>✦</span>
            </div>

            <h2>AI 正在构建您的学习路径</h2>
            <p>
              正在结合学习目标、当前基础和学习偏好编排知识节点。
            </p>
          </header>

          <div class="generation-timeline">
            <div
                v-for="(step, index) in pathPlanningSteps"
                :key="step.key"
                class="generation-timeline-node"
                :class="{
                  'is-active': pathPlanningStepIndex === index,
                  'is-done': pathPlanningStepIndex > index,
                }"
                :style="generationStepStyle(step, index, pathPlanningSteps)"
            >
              <div class="generation-node-circle">
                <span v-if="pathPlanningStepIndex > index">✓</span>
                <span v-else>{{ index + 1 }}</span>
              </div>

              <span class="generation-node-label">
                {{ step.title }}
              </span>

              <div
                  v-if="index < pathPlanningSteps.length - 1"
                  class="generation-node-line"
              ></div>
            </div>
          </div>

          <div class="generation-progress-panel">
            <div class="generation-progress-head">
              <div>
                <span>当前阶段</span>
                <strong>{{ currentPathPlanningStep }}</strong>
              </div>

              <em>
                第 {{ currentPathPlanningStepNumber }}
                / {{ pathPlanningSteps.length }} 步
              </em>
            </div>

            <div
                class="generation-progress-track"
                role="progressbar"
                :aria-valuenow="generatingProgressRounded"
                aria-valuemin="0"
                aria-valuemax="100"
            >
              <i
                  :style="{
                    width: `${generatingProgressRounded}%`,
                  }"
              ></i>
            </div>
          </div>

          <div class="generation-log-box">
            <transition-group name="log">
              <div
                  v-for="(message, index) in visibleGeneratingMessages"
                  :key="`${message}-${index}`"
                  class="generation-log-row"
              >
                <span></span>
                <p>{{ message }}</p>
              </div>
            </transition-group>
          </div>

          <p class="generation-persistence-note">
            后台任务不会因切换页面或刷新而停止；再次进入本路径时会自动恢复进度并确认生成结果。
          </p>
        </template>
      </section>
    </section>

    <section v-else-if="path" class="overview-shell">
      <section class="overview-workspace">
        <section class="learning-map">
          <header class="map-toolbar">
            <div class="map-title">
              <span>LEARNING MAP</span>
              <h1>{{ path.title }}</h1>
              <p>{{ path.goal }}</p>
            </div>

            <div class="map-actions">
              <div class="compact-progress">
                <strong>{{ path.overall_progress }}%</strong>
                <span>总进度</span>
              </div>

              <div class="map-tags">
                <span>主题：{{ path.topic || path.title }}</span>
                <span>{{ path.stages.length }} 阶段</span>
                <span>{{ path.nodes.length }} 节点</span>
                <span>当前：{{ currentNode?.title || '暂无可学习节点' }}</span>
              </div>

              <div class="action-line">
                <button type="button" @click="router.push('/path-planner/history')">路径历史</button>
                <button class="primary-action" type="button" @click="router.push('/path-planner')">
                  重新规划
                </button>
              </div>
            </div>
          </header>

          <section class="summary-line">
            <div class="available">
              <span>可学习</span>
              <strong>{{ summary.available }}</strong>
            </div>
            <div class="learning">
              <span>学习中</span>
              <strong>{{ summary.learning }}</strong>
            </div>
            <div class="completed">
              <span>已完成</span>
              <strong>{{ summary.completed }}</strong>
            </div>
            <div class="locked">
              <span>未解锁</span>
              <strong>{{ summary.locked }}</strong>
            </div>
          </section>

          <div class="map-body">
            <article
                v-for="(stage, stageIndex) in stageSections"
                :key="stage.stageId"
                class="map-stage"
            >
              <header class="map-stage-head">
                <div class="stage-order">
                  <span>{{ String(stageIndex + 1).padStart(2, '0') }}</span>
                </div>

                <div class="stage-copy">
                  <span>阶段 {{ stageIndex + 1 }}</span>
                  <h3>{{ stage.title }}</h3>
                  <p>
                    {{ stage.nodes.length }} 个节点 ·
                    {{ stageCompletedCount(stage) }} 已完成 ·
                    {{ stageAvailableCount(stage) }} 可学习
                  </p>
                </div>

                <div class="stage-progress">
                  <strong>{{ stageProgress(stage) }}%</strong>
                  <span>阶段进度</span>
                  <div class="stage-progress-track">
                    <i :style="{ width: `${stageProgress(stage)}%` }"></i>
                  </div>
                </div>
              </header>

              <div class="map-node-list">
                <button
                    v-for="node in stage.nodes"
                    :key="node.id"
                    class="map-node"
                    :class="[
                    node.status,
                    {
                      selected: selectedNodeId === node.id,
                      current: currentNode?.id === node.id,
                      enterable: canEnterNode(node),
                      opening: openingNodeId === node.id,
                    },
                  ]"
                    type="button"
                    :disabled="Boolean(openingNodeId) || isGeneratingTutorial"
                    @mouseenter="previewNode(node)"
                    @focus="previewNode(node)"
                    @click="handleNodeClick(node)"
                >
                  <span class="checkpoint">
                    <i></i>
                  </span>

                  <div class="node-copy">
                    <strong>{{ node.title }}</strong>
                    <span>
                      {{ statusText(node.status) }} · {{ difficultyText(node.difficulty) }} · P{{ node.priority }}
                    </span>
                  </div>

                  <div class="node-extra">
                    <span v-if="openingNodeId === node.id">正在准备</span>
                    <span v-else-if="currentNode?.id === node.id">当前学习</span>
                    <span v-else-if="canEnterNode(node)">点击进入</span>
                    <span v-else>未解锁</span>
                    <em>{{ node.prerequisites?.length || 0 }} 个前置</em>
                  </div>
                </button>
              </div>
            </article>
          </div>
        </section>

        <aside class="mentor-panel">
          <section class="mentor-section mentor-hero">
            <span class="mentor-kicker">AI TUTOR</span>
            <h2>AI 导师判断</h2>
            <p>
              {{ displayedNode ? nodeLearningHint(displayedNode) : '选择一个学习节点后，这里会显示当前节点判断和学习建议。' }}
            </p>
          </section>

          <template v-if="displayedNode">
            <section class="mentor-section selected-node">
              <span class="mentor-kicker">CURRENT NODE</span>
              <h3>{{ displayedNode.title }}</h3>

              <div class="mentor-table">
                <div>
                  <span>所属阶段</span>
                  <strong>{{ displayedStageTitle }}</strong>
                </div>
                <div>
                  <span>节点状态</span>
                  <strong>{{ statusText(displayedNode.status) }}</strong>
                </div>
                <div>
                  <span>学习难度</span>
                  <strong>{{ difficultyText(displayedNode.difficulty) }}</strong>
                </div>
                <div>
                  <span>优先级</span>
                  <strong>P{{ displayedNode.priority }}</strong>
                </div>
                <div>
                  <span>测验次数</span>
                  <strong>{{ displayedNode.attempt_count || 0 }}</strong>
                </div>
              </div>
            </section>

            <section class="mentor-section">
              <span class="mentor-kicker">PREREQUISITES</span>

              <div v-if="displayedPrerequisites.length" class="prerequisite-list">
                <span v-for="item in displayedPrerequisites" :key="item">
                  {{ item }}
                </span>
              </div>

              <p v-else class="mentor-note">该节点没有前置依赖，点击左侧节点即可进入或生成教程。</p>
            </section>

            <section class="mentor-section">
              <span class="mentor-kicker">LEARNING FLOW</span>

              <div class="learn-flow">
                <div>
                  <span>01</span>
                  <p>点击左侧可学习节点</p>
                </div>
                <div>
                  <span>02</span>
                  <p>已有教程则直接进入学习页</p>
                </div>
                <div>
                  <span>03</span>
                  <p>没有教程则当前页等待生成完成</p>
                </div>
              </div>
            </section>
          </template>

          <section class="mentor-section evaluation-panel">
            <span class="mentor-kicker">EVALUATION</span>
            <h3>学习效果评估</h3>

            <div v-if="evaluation" class="cockpit-card">
              <div class="cockpit-header">
                <div class="header-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                </div>
                <h3>AI 导师学习诊断</h3>
              </div>

              <div class="metrics-grid">
                <div class="metric-item card-hover">
                  <div class="metric-icon clock">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <polyline points="12 6 12 12 16 14" />
                    </svg>
                  </div>
                  <div class="metric-info">
                    <label>学习时长</label>
                    <strong>{{ activeMinutes }} <small>分钟</small></strong>
                  </div>
                </div>

                <div class="metric-item card-hover">
                  <div class="metric-icon score">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                      <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5" />
                    </svg>
                  </div>
                  <div class="metric-info">
                    <label>测验均分</label>
                    <strong :class="{ good: averageScore >= 80, warning: averageScore > 0 && averageScore < 80 }">
                      {{ averageScore > 0 ? `${averageScore} 分` : '暂无' }}
                    </strong>
                  </div>
                </div>
              </div>

              <div class="diagnostic-section">
                <h4 class="section-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                  薄弱知识点
                </h4>

                <div v-if="weakTopics.length > 0" class="weak-tags">
                  <span v-for="topic in weakTopics" :key="topic" class="weak-tag">
                    {{ topic }}
                  </span>
                </div>

                <div v-else class="empty-weak">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  无明显薄弱知识点，继续保持！
                </div>
              </div>

              <div v-if="optimizationTips.length > 0" class="diagnostic-section advice-section">
                <h4 class="section-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 8V4H8" />
                    <rect width="16" height="12" x="4" y="8" rx="2" />
                    <path d="M2 14h2" />
                    <path d="M20 14h2" />
                    <path d="M15 13v2" />
                    <path d="M9 13v2" />
                  </svg>
                  优化处方与建议
                </h4>

                <ul class="advice-list">
                  <li v-for="(tip, idx) in optimizationTips" :key="idx" class="advice-item">
                    <span class="bullet">{{ idx + 1 }}</span>
                    <p>{{ tip }}</p>
                  </li>
                </ul>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </section>

    <Teleport to="body">
      <transition name="tutorial-overlay">
        <div
            v-if="isGeneratingTutorial"
            class="tutorial-generating-overlay"
        >
          <section
              class="generation-waiting-card tutorial-waiting-card"
              role="dialog"
              aria-modal="true"
              aria-live="polite"
              aria-atomic="true"
          >
            <template v-if="tutorialGenerationError">
              <div class="generation-result-state generation-error-state">
                <div
                    class="generation-result-icon generation-error-icon"
                    aria-hidden="true"
                >
                  !
                </div>

                <div class="generation-result-copy">
                  <h2>节点教程生成失败</h2>
                  <p>
                    教程任务状态已经保留，可以重新生成或关闭等待页面。
                  </p>
                </div>

                <div class="generation-error-detail">
                  {{ tutorialGenerationError }}
                </div>

                <div class="generation-result-actions">
                  <button
                      class="generation-secondary-action"
                      type="button"
                      @click="closeTutorialFailure"
                  >
                    关闭等待
                  </button>

                  <button
                      class="generation-primary-action"
                      type="button"
                      @click="retryTutorialGeneration"
                  >
                    重新生成教程
                  </button>
                </div>
              </div>
            </template>

            <template v-else-if="tutorialProgressRounded >= 100">
              <div class="generation-result-state generation-success-state">
                <div
                    class="generation-result-icon generation-success-icon"
                    aria-hidden="true"
                >
                  ✓
                </div>

                <div class="generation-result-copy">
                  <h2>节点教程已生成</h2>
                  <p>
                    教程正文、示例和易错点已经完成保存。
                  </p>
                </div>

                <div class="generation-success-summary">
                  <span></span>
                  正在进入节点学习页面
                </div>

                <div class="generation-success-track">
                  <i></i>
                </div>
              </div>
            </template>

            <template v-else>
              <header class="generation-loading-header">
                <div
                    class="generation-loader"
                    aria-hidden="true"
                >
                  <div class="generation-loader-ring"></div>
                  <span>✦</span>
                </div>

                <h2>AI 正在准备节点教程</h2>
                <p>
                  正在结合路径目标、节点知识与学习画像组织个性化教程。
                </p>
              </header>

              <div class="generation-timeline">
                <div
                    v-for="(step, index) in tutorialGenerationSteps"
                    :key="step.key"
                    class="generation-timeline-node"
                    :class="{
                      'is-active': tutorialStepIndex === index,
                      'is-done': tutorialStepIndex > index,
                    }"
                    :style="generationStepStyle(step, index, tutorialGenerationSteps)"
                >
                  <div class="generation-node-circle">
                    <span v-if="tutorialStepIndex > index">✓</span>
                    <span v-else>{{ index + 1 }}</span>
                  </div>

                  <span class="generation-node-label">
                    {{ step.title }}
                  </span>

                  <div
                      v-if="index < tutorialGenerationSteps.length - 1"
                      class="generation-node-line"
                  ></div>
                </div>
              </div>

              <div class="generation-progress-panel">
                <div class="generation-progress-head">
                  <div>
                    <span>当前阶段</span>
                    <strong>{{ currentTutorialStep }}</strong>
                  </div>

                  <em>
                    第 {{ currentTutorialStepNumber }}
                    / {{ tutorialGenerationSteps.length }} 步
                  </em>
                </div>

                <div
                    class="generation-progress-track"
                    role="progressbar"
                    :aria-valuenow="tutorialProgressRounded"
                    aria-valuemin="0"
                    aria-valuemax="100"
                >
                  <i
                      :style="{
                        width: `${tutorialProgressRounded}%`,
                      }"
                  ></i>
                </div>
              </div>

              <div class="generation-log-box">
                <transition-group name="log">
                  <div
                      v-for="(message, index) in visibleTutorialMessages"
                      :key="`${message}-${index}`"
                      class="generation-log-row"
                  >
                    <span></span>
                    <p>{{ message }}</p>
                  </div>
                </transition-group>
              </div>

              <p class="generation-persistence-note">
                教程任务由后端持续执行。切换页面或刷新后，再次进入该节点会自动恢复等待状态。
              </p>
            </template>
          </section>
        </div>
      </transition>
    </Teleport>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
  watch,
} from 'vue'
import type { CSSProperties } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import {
  createLearningPath,
  generateTutorial,
  getCurrentLearningPath,
  getLearningEvaluation,
  getLearningPathById,
  getLearningNodeWorkspace,
  startLearning,
} from '@/features/learning-path/api/path'
import type {
  LearningPathNode,
  LearningPathStage,
  PathLearningEvaluationResponse,
  PathOverview,
  PathPreferences,
} from '@/features/learning-path/model/path'
import type { PathEvent } from '@/features/learning-path/model/pathEvent'
import { usePathEvents } from '@/features/learning-path/composables/usePathEvents'
import { getErrorMessage } from '@/shared/api/http'

type StageSection = {
  stageId: string
  title: string
  nodes: LearningPathNode[]
}

type NodeWorkspaceLike = {
  current_tutorial?: unknown | null
}

type GenerationStatus =
    | 'running'
    | 'failed'
    | 'completed'

type GenerationStep = {
  key: string
  title: string
  threshold: number
  start: string
  end: string
  soft: string
  text: string
  glow: string
}

type CachedPlanningTask = {
  version: 3
  status: GenerationStatus
  pathId: number
  runId: string
  progress: number
  logs: string[]
  error: string
  startedAt: number
  updatedAt: number
  payload?: unknown
}

type CachedTutorialGeneration = {
  version: 3
  status: GenerationStatus
  nodeId: number
  pathId: number | null
  title: string
  progress: number
  logs: string[]
  error: string
  startedAt: number
  updatedAt: number
}

const PLANNING_CACHE_KEY =
    'mentorly:path-planning-task:v3'
const PLANNING_CACHE_TTL =
    60 * 60 * 1000
const PLANNING_CONFIRM_TIMEOUT =
    10 * 60 * 1000

const TUTORIAL_CACHE_PREFIX =
    'mentorly:tutorial-generation:v3:'
const TUTORIAL_CACHE_TTL =
    60 * 60 * 1000
const TUTORIAL_CONFIRM_TIMEOUT =
    10 * 60 * 1000

const router = useRouter()
const route = useRoute()
const pathEvents = usePathEvents()

const loading = ref(false)
const path = ref<PathOverview | null>(null)
const evaluation =
    ref<PathLearningEvaluationResponse | null>(null)
const activeDetailNode =
    ref<LearningPathNode | null>(null)

const isGenerating = ref(false)
const generatingProgress = ref(12)
const generatingMessages = ref<string[]>([])
const pathGenerationError = ref('')
const activeRunId = ref<string | null>(null)

const isGeneratingTutorial = ref(false)
const openingNodeId = ref<number | null>(null)
const tutorialNodeId = ref<number | null>(null)
const tutorialProgress = ref(0)
const tutorialMessages = ref<string[]>([])
const tutorialGenerationError = ref('')

let pageActive = true
let activationCount = 0
let pathMonitorToken = 0
let tutorialMonitorToken = 0
let pathFinishing = false
let tutorialFinishing = false

let pathProgressTimer: number | null = null
let tutorialProgressTimer: number | null = null

const sharedStepTones = [
  {
    start: '#4f8cf7',
    end: '#73a7ff',
    soft: '#eef5ff',
    text: '#3268bd',
    glow: 'rgba(79, 140, 247, 0.18)',
  },
  {
    start: '#8d78f2',
    end: '#aa96ff',
    soft: '#f4f1ff',
    text: '#6651c1',
    glow: 'rgba(141, 120, 242, 0.18)',
  },
  {
    start: '#ef9a58',
    end: '#f6b072',
    soft: '#fff5ed',
    text: '#bd6c2f',
    glow: 'rgba(239, 154, 88, 0.18)',
  },
  {
    start: '#df7fac',
    end: '#ed9bc2',
    soft: '#fff0f7',
    text: '#b25582',
    glow: 'rgba(223, 127, 172, 0.18)',
  },
  {
    start: '#28ad9e',
    end: '#58c7bb',
    soft: '#ebfaf8',
    text: '#197b72',
    glow: 'rgba(40, 173, 158, 0.18)',
  },
] as const

const pathPlanningSteps: GenerationStep[] = [
  {
    key: 'profile',
    title: '结合学习画像',
    threshold: 10,
    ...sharedStepTones[0],
  },
  {
    key: 'stage',
    title: '拆解学习阶段',
    threshold: 30,
    ...sharedStepTones[1],
  },
  {
    key: 'node',
    title: '编排知识节点',
    threshold: 52,
    ...sharedStepTones[2],
  },
  {
    key: 'validate',
    title: '校验路径依赖',
    threshold: 74,
    ...sharedStepTones[3],
  },
  {
    key: 'save',
    title: '保存路径结构',
    threshold: 90,
    ...sharedStepTones[4],
  },
]

const tutorialGenerationSteps: GenerationStep[] = [
  {
    key: 'context',
    title: '读取节点上下文',
    threshold: 8,
    ...sharedStepTones[0],
  },
  {
    key: 'scope',
    title: '提取核心知识',
    threshold: 27,
    ...sharedStepTones[1],
  },
  {
    key: 'outline',
    title: '搭建教程结构',
    threshold: 48,
    ...sharedStepTones[2],
  },
  {
    key: 'content',
    title: '补充示例与易错点',
    threshold: 70,
    ...sharedStepTones[3],
  },
  {
    key: 'save',
    title: '保存并校验教程',
    threshold: 90,
    ...sharedStepTones[4],
  },
]

const learningStatuses = new Set([
  'in_progress',
  'remediation',
  'reinforced',
])
const completedStatuses = new Set([
  'completed',
  'completed_with_gaps',
])
const enterableStatuses = new Set([
  'available',
  'in_progress',
  'remediation',
  'reinforced',
  'completed',
  'completed_with_gaps',
])

const generatingProgressRounded = computed(() => {
  return clampProgress(generatingProgress.value)
})

const tutorialProgressRounded = computed(() => {
  return clampProgress(tutorialProgress.value)
})

const pathPlanningStepIndex = computed(() => {
  return stepIndexForProgress(
      generatingProgressRounded.value,
      pathPlanningSteps,
  )
})

const tutorialStepIndex = computed(() => {
  return stepIndexForProgress(
      tutorialProgressRounded.value,
      tutorialGenerationSteps,
  )
})

const currentPathPlanningStep = computed(() => {
  if (generatingProgressRounded.value >= 100) {
    return '路径结构已生成'
  }

  return (
      pathPlanningSteps[
          pathPlanningStepIndex.value
          ]?.title ||
      '准备规划任务'
  )
})

const currentTutorialStep = computed(() => {
  if (tutorialProgressRounded.value >= 100) {
    return '节点教程已生成'
  }

  return (
      tutorialGenerationSteps[
          tutorialStepIndex.value
          ]?.title ||
      '准备教程任务'
  )
})

const currentPathPlanningStepNumber = computed(() => {
  if (generatingProgressRounded.value >= 100) {
    return pathPlanningSteps.length
  }

  return Math.min(
      pathPlanningStepIndex.value + 1,
      pathPlanningSteps.length,
  )
})

const currentTutorialStepNumber = computed(() => {
  if (tutorialProgressRounded.value >= 100) {
    return tutorialGenerationSteps.length
  }

  return Math.min(
      tutorialStepIndex.value + 1,
      tutorialGenerationSteps.length,
  )
})

const visibleGeneratingMessages = computed(() => {
  if (generatingProgressRounded.value >= 100) {
    return [
      '路径阶段、知识节点和前置依赖已保存，正在打开学习路径总览。',
    ]
  }

  return generatingMessages.value.slice(-3)
})

const visibleTutorialMessages = computed(() => {
  if (tutorialProgressRounded.value >= 100) {
    return [
      '节点教程已保存，正在进入学习页面。',
    ]
  }

  return tutorialMessages.value.slice(-3)
})

const averageScore = computed(() => {
  const score =
      evaluation.value?.signal_snapshot?.average_score

  if (
      score === null ||
      score === undefined
  ) {
    return 0
  }

  return Math.round(score)
})

const activeMinutes = computed(() => {
  return (
      evaluation.value
          ?.signal_snapshot
          ?.active_minutes ??
      0
  )
})

const weakTopics = computed(() => {
  return (
      evaluation.value
          ?.signal_snapshot
          ?.weak_topics ??
      []
  )
})

const optimizationTips = computed(() => {
  return (
      evaluation.value
          ?.optimization_tips ??
      []
  )
})

const currentNode = computed(() => {
  if (!path.value) return null

  return (
      path.value.nodes.find(
          node =>
              node.node_id ===
              path.value?.current_node_key,
      ) ??
      path.value.nodes.find(
          node =>
              [
                'available',
                'in_progress',
                'remediation',
                'reinforced',
              ].includes(node.status),
      ) ??
      null
  )
})

const displayedNode = computed(() => {
  return (
      activeDetailNode.value ||
      currentNode.value
  )
})

const selectedNodeId = computed(() => {
  return displayedNode.value?.id ?? null
})

const displayedStageTitle = computed(() => {
  if (!displayedNode.value) return ''

  return stageTitleById(
      displayedNode.value.stage_id,
  )
})

const displayedPrerequisites = computed(() => {
  return (
      displayedNode.value
          ?.prerequisites
          ?.map(prerequisiteLabel) ??
      []
  )
})

const summary = computed(() => {
  const nodes = path.value?.nodes ?? []

  return {
    available:
        nodes.filter(
            node =>
                node.status === 'available',
        ).length,
    learning:
        nodes.filter(
            node =>
                learningStatuses.has(node.status),
        ).length,
    completed:
        nodes.filter(
            node =>
                completedStatuses.has(node.status),
        ).length,
    locked:
        nodes.filter(
            node =>
                node.status === 'locked',
        ).length,
  }
})

const nodeTitleMap = computed(() => {
  const map = new Map<string, string>()

  for (const node of path.value?.nodes ?? []) {
    map.set(node.node_id, node.title)
  }

  return map
})

const stageSections = computed<StageSection[]>(() => {
  if (!path.value) return []

  const stages = path.value.stages ?? []
  const nodes = path.value.nodes ?? []

  const sections: StageSection[] =
      stages.map(stage => {
        const stageId = getStageId(stage)

        return {
          stageId,
          title: getStageTitle(stage),
          nodes:
              nodes
                  .filter(
                      node =>
                          node.stage_id === stageId,
                  )
                  .sort(
                      (first, second) =>
                          (first.priority || 0) -
                          (second.priority || 0),
                  ),
        }
      })

  const knownStageIds =
      new Set(
          sections.map(
              section => section.stageId,
          ),
      )

  const orphanNodes =
      nodes.filter(
          node =>
              !knownStageIds.has(node.stage_id),
      )

  if (orphanNodes.length) {
    sections.push({
      stageId: 'unknown-stage',
      title: '未归类节点',
      nodes:
          orphanNodes.sort(
              (first, second) =>
                  (first.priority || 0) -
                  (second.priority || 0),
          ),
    })
  }

  return sections.filter(
      section => section.nodes.length > 0,
  )
})

function clampProgress(value: number) {
  return Math.max(
      0,
      Math.min(
          100,
          Math.round(value),
      ),
  )
}

function stepIndexForProgress(
    progress: number,
    steps: GenerationStep[],
) {
  for (
      let index = steps.length - 1;
      index >= 0;
      index -= 1
  ) {
    const step = steps[index]

    if (
        step &&
        progress >= step.threshold
    ) {
      return index
    }
  }

  return 0
}

function generationStepStyle(
    step: GenerationStep,
    index: number,
    steps: GenerationStep[],
): CSSProperties {
  const next =
      steps[index + 1] ?? step

  return {
    '--generation-node-start': step.start,
    '--generation-node-end': step.end,
    '--generation-node-soft': step.soft,
    '--generation-node-text': step.text,
    '--generation-node-glow': step.glow,
    '--generation-next-start': next.start,
  } as CSSProperties
}

function getStageId(
    stage: LearningPathStage,
) {
  return stage.stage_id
}

function getStageTitle(
    stage: LearningPathStage,
) {
  return stage.title
}

function stageTitleById(
    stageId: string,
) {
  const stage =
      stageSections.value.find(
          item =>
              item.stageId === stageId,
      )

  return stage?.title || stageId
}

function stageCompletedCount(
    stage: StageSection,
) {
  return (
      stage.nodes.filter(
          node =>
              completedStatuses.has(node.status),
      ).length
  )
}

function stageAvailableCount(
    stage: StageSection,
) {
  return (
      stage.nodes.filter(
          node =>
              node.status === 'available',
      ).length
  )
}

function stageProgress(
    stage: StageSection,
) {
  if (!stage.nodes.length) return 0

  return Math.round(
      (
          stageCompletedCount(stage) /
          stage.nodes.length
      ) * 100,
  )
}

function difficultyText(
    difficulty?: string | null,
) {
  if (difficulty === 'beginner') {
    return '入门'
  }

  if (difficulty === 'intermediate') {
    return '进阶'
  }

  if (difficulty === 'advanced') {
    return '挑战'
  }

  return difficulty || '常规'
}

function statusText(status: string) {
  switch (status) {
    case 'available':
      return '可开始'
    case 'in_progress':
      return '学习中'
    case 'remediation':
      return '补弱中'
    case 'reinforced':
      return '强化中'
    case 'locked':
      return '未解锁'
    case 'completed':
      return '已完成'
    case 'completed_with_gaps':
      return '带缺口完成'
    default:
      return status
  }
}

function nodeLearningHint(
    node: LearningPathNode,
) {
  if (node.status === 'locked') {
    return '该节点暂未解锁。完成前置节点后，系统会自动开放学习入口。'
  }

  if (node.status === 'completed') {
    return '该节点已经完成。点击左侧节点可以直接进入学习页回顾教程、题目和辅助资源。'
  }

  if (
      node.status ===
      'completed_with_gaps'
  ) {
    return '该节点已完成但仍存在薄弱点。点击左侧节点可以进入学习页查看强化内容并复习错题。'
  }

  return '该节点可以开始学习。点击左侧节点后，若已有教程会直接进入学习页；若没有教程，会在当前页面生成完成后进入。'
}

function prerequisiteLabel(
    nodeKey: string,
) {
  return (
      nodeTitleMap.value.get(nodeKey) ||
      nodeKey
  )
}

function canEnterNode(
    node: LearningPathNode,
) {
  return enterableStatuses.has(node.status)
}

function unwrapResponseData<T>(
    response: unknown,
): T {
  const maybeResponse = response as {
    data?: {
      data?: T
    } | T
  }

  if (
      maybeResponse &&
      typeof maybeResponse === 'object' &&
      maybeResponse.data &&
      typeof maybeResponse.data === 'object' &&
      'data' in maybeResponse.data
  ) {
    return maybeResponse.data.data as T
  }

  if (
      maybeResponse &&
      'data' in maybeResponse
  ) {
    return maybeResponse.data as T
  }

  return response as T
}

function delay(ms: number) {
  return new Promise<void>(resolve => {
    window.setTimeout(resolve, ms)
  })
}

async function animateProgressTo(
    target: {
      value: number
    },
    finalValue: number,
    duration = 720,
) {
  const from = target.value
  const startedAt = performance.now()

  await new Promise<void>(resolve => {
    const tick = (now: number) => {
      const ratio = Math.min(
          1,
          (now - startedAt) / duration,
      )

      const eased =
          1 - Math.pow(1 - ratio, 3)

      target.value =
          from +
          (finalValue - from) * eased

      if (ratio >= 1) {
        target.value = finalValue
        resolve()
        return
      }

      window.requestAnimationFrame(tick)
    }

    window.requestAnimationFrame(tick)
  })
}

function canUseStorage() {
  return (
      typeof window !== 'undefined' &&
      Boolean(window.localStorage)
  )
}

function readPlanningCache():
    CachedPlanningTask | null {
  if (!canUseStorage()) return null

  try {
    const raw =
        window.localStorage.getItem(
            PLANNING_CACHE_KEY,
        )

    if (!raw) return null

    const task =
        JSON.parse(raw) as CachedPlanningTask

    const invalid =
        task.version !== 3 ||
        !task.pathId ||
        Date.now() - task.updatedAt >
        PLANNING_CACHE_TTL

    if (invalid) {
      window.localStorage.removeItem(
          PLANNING_CACHE_KEY,
      )
      return null
    }

    return task
  } catch {
    return null
  }
}

function writePlanningCache(
    task: CachedPlanningTask,
) {
  if (!canUseStorage()) return

  try {
    const raw =
        window.localStorage.getItem(
            PLANNING_CACHE_KEY,
        )

    const previous =
        raw
            ? JSON.parse(raw)
            : {}

    window.localStorage.setItem(
        PLANNING_CACHE_KEY,
        JSON.stringify({
          ...previous,
          ...task,
        }),
    )
  } catch {
    // 缓存失败不影响后端任务。
  }
}

function clearPlanningCache(
    targetPathId?: number,
) {
  if (!canUseStorage()) return

  if (targetPathId) {
    const current = readPlanningCache()

    if (
        current &&
        current.pathId !== targetPathId
    ) {
      return
    }
  }

  window.localStorage.removeItem(
      PLANNING_CACHE_KEY,
  )
}

function persistPlanningTask(
    patch: Partial<CachedPlanningTask> = {},
) {
  const previous = readPlanningCache()
  const routePathId =
      Number(route.params.id || 0)

  const resolvedPathId =
      patch.pathId ??
      previous?.pathId ??
      path.value?.id ??
      (
          Number.isFinite(routePathId)
              ? routePathId
              : 0
      )

  if (!resolvedPathId) return null

  const task: CachedPlanningTask = {
    version: 3,
    status:
        patch.status ??
        previous?.status ??
        'running',
    pathId: resolvedPathId,
    runId:
        patch.runId ??
        previous?.runId ??
        activeRunId.value ??
        '',
    progress:
        patch.progress ??
        generatingProgress.value,
    logs:
        patch.logs ??
        [...generatingMessages.value],
    error:
        patch.error ??
        pathGenerationError.value,
    startedAt:
        patch.startedAt ??
        previous?.startedAt ??
        Date.now(),
    updatedAt: Date.now(),
    payload:
        patch.payload ??
        previous?.payload,
  }

  writePlanningCache(task)
  return task
}

function tutorialCacheKey(
    targetNodeId: number,
) {
  return (
      `${TUTORIAL_CACHE_PREFIX}` +
      `${targetNodeId}`
  )
}

function readTutorialCache(
    targetNodeId: number,
): CachedTutorialGeneration | null {
  if (
      !canUseStorage() ||
      !targetNodeId
  ) {
    return null
  }

  try {
    const key =
        tutorialCacheKey(targetNodeId)

    const raw =
        window.localStorage.getItem(key)

    if (!raw) return null

    const task =
        JSON.parse(raw) as
            CachedTutorialGeneration

    const invalid =
        task.version !== 3 ||
        task.nodeId !== targetNodeId ||
        Date.now() - task.updatedAt >
        TUTORIAL_CACHE_TTL

    if (invalid) {
      window.localStorage.removeItem(key)
      return null
    }

    return task
  } catch {
    return null
  }
}

function writeTutorialCache(
    task: CachedTutorialGeneration,
) {
  if (!canUseStorage()) return

  try {
    window.localStorage.setItem(
        tutorialCacheKey(task.nodeId),
        JSON.stringify(task),
    )
  } catch {
    // 缓存失败不影响后端任务。
  }
}

function clearTutorialCache(
    targetNodeId: number,
) {
  if (
      !canUseStorage() ||
      !targetNodeId
  ) {
    return
  }

  window.localStorage.removeItem(
      tutorialCacheKey(targetNodeId),
  )
}

function persistTutorialTask(
    targetNodeId: number,
    patch:
        Partial<CachedTutorialGeneration> = {},
) {
  if (!targetNodeId) return null

  const previous =
      readTutorialCache(targetNodeId)

  const targetNode =
      path.value?.nodes.find(
          node =>
              node.id === targetNodeId,
      )

  const task: CachedTutorialGeneration = {
    version: 3,
    status:
        patch.status ??
        previous?.status ??
        'running',
    nodeId: targetNodeId,
    pathId:
        patch.pathId ??
        previous?.pathId ??
        path.value?.id ??
        null,
    title:
        patch.title ??
        previous?.title ??
        targetNode?.title ??
        '',
    progress:
        patch.progress ??
        tutorialProgress.value,
    logs:
        patch.logs ??
        [...tutorialMessages.value],
    error:
        patch.error ??
        tutorialGenerationError.value,
    startedAt:
        patch.startedAt ??
        previous?.startedAt ??
        Date.now(),
    updatedAt: Date.now(),
  }

  writeTutorialCache(task)
  return task
}

function findPendingTutorialForPath(
    pathId: number,
): CachedTutorialGeneration | null {
  if (
      !canUseStorage() ||
      !pathId
  ) {
    return null
  }

  let latest:
      CachedTutorialGeneration | null =
      null

  for (
      let index = 0;
      index < window.localStorage.length;
      index += 1
  ) {
    const key =
        window.localStorage.key(index)

    if (
        !key ||
        !key.startsWith(
            TUTORIAL_CACHE_PREFIX,
        )
    ) {
      continue
    }

    const nodeId =
        Number(
            key.slice(
                TUTORIAL_CACHE_PREFIX.length,
            ),
        )

    const task =
        readTutorialCache(nodeId)

    if (
        !task ||
        task.pathId !== pathId
    ) {
      continue
    }

    if (
        !latest ||
        task.updatedAt > latest.updatedAt
    ) {
      latest = task
    }
  }

  return latest
}

function estimatePlanningProgress(
    task: CachedPlanningTask,
) {
  const elapsedSeconds =
      Math.max(
          0,
          (
              Date.now() -
              task.startedAt
          ) / 1000,
      )

  if (elapsedSeconds < 10) {
    return Math.min(
        30,
        10 + elapsedSeconds * 2,
    )
  }

  if (elapsedSeconds < 35) {
    return Math.min(
        64,
        30 +
        (elapsedSeconds - 10) * 1.36,
    )
  }

  if (elapsedSeconds < 70) {
    return Math.min(
        86,
        64 +
        (elapsedSeconds - 35) * 0.63,
    )
  }

  return Math.min(
      94,
      86 +
      (elapsedSeconds - 70) * 0.12,
  )
}

function estimateTutorialProgress(
    task: CachedTutorialGeneration,
) {
  const elapsedSeconds =
      Math.max(
          0,
          (
              Date.now() -
              task.startedAt
          ) / 1000,
      )

  if (elapsedSeconds < 10) {
    return Math.min(
        28,
        7 + elapsedSeconds * 2.1,
    )
  }

  if (elapsedSeconds < 32) {
    return Math.min(
        61,
        28 +
        (elapsedSeconds - 10) * 1.5,
    )
  }

  if (elapsedSeconds < 65) {
    return Math.min(
        84,
        61 +
        (elapsedSeconds - 32) * 0.7,
    )
  }

  return Math.min(
      94,
      84 +
      (elapsedSeconds - 65) * 0.13,
  )
}

function addPlanningMessage(
    message: string,
) {
  if (
      !message ||
      generatingMessages.value.includes(
          message,
      )
  ) {
    return
  }

  generatingMessages.value = [
    ...generatingMessages.value,
    message,
  ].slice(-5)

  if (isGenerating.value) {
    persistPlanningTask({
      logs: [
        ...generatingMessages.value,
      ],
    })
  }
}

function addTutorialMessage(
    message: string,
) {
  if (
      !message ||
      tutorialMessages.value.includes(
          message,
      )
  ) {
    return
  }

  tutorialMessages.value = [
    ...tutorialMessages.value,
    message,
  ].slice(-5)

  if (
      isGeneratingTutorial.value &&
      tutorialNodeId.value
  ) {
    persistTutorialTask(
        tutorialNodeId.value,
        {
          logs: [
            ...tutorialMessages.value,
          ],
        },
    )
  }
}

function syncPlanningMessagesByProgress() {
  if (generatingProgress.value >= 10) {
    addPlanningMessage(
        '已读取学习目标、当前基础和学习偏好。',
    )
  }

  if (generatingProgress.value >= 30) {
    addPlanningMessage(
        '正在拆解学习阶段并确定阶段目标。',
    )
  }

  if (generatingProgress.value >= 52) {
    addPlanningMessage(
        '正在编排核心知识节点和学习顺序。',
    )
  }

  if (generatingProgress.value >= 74) {
    addPlanningMessage(
        '正在检查节点覆盖度和前置依赖。',
    )
  }

  if (generatingProgress.value >= 90) {
    addPlanningMessage(
        '路径结构已基本完成，正在保存结果。',
    )
  }
}

function syncTutorialMessagesByProgress() {
  if (tutorialProgress.value >= 8) {
    addTutorialMessage(
        '已读取学习目标、节点信息和当前学习基础。',
    )
  }

  if (tutorialProgress.value >= 27) {
    addTutorialMessage(
        '正在提取本节点需要讲清的核心知识与边界。',
    )
  }

  if (tutorialProgress.value >= 48) {
    addTutorialMessage(
        '正在组织章节顺序、概念关系和讲解层次。',
    )
  }

  if (tutorialProgress.value >= 70) {
    addTutorialMessage(
        '正在补充示例、易错点和学习提示。',
    )
  }

  if (tutorialProgress.value >= 90) {
    addTutorialMessage(
        '教程内容已基本完成，正在保存并校验。',
    )
  }
}

function stopPathProgressAnimation() {
  if (pathProgressTimer === null) {
    return
  }

  window.clearInterval(pathProgressTimer)
  pathProgressTimer = null
}

function startPathProgressAnimation(
    initialProgress =
        generatingProgress.value,
) {
  stopPathProgressAnimation()

  generatingProgress.value =
      Math.max(
          generatingProgress.value,
          initialProgress,
      )

  pathProgressTimer =
      window.setInterval(() => {
        if (
            !pageActive ||
            !isGenerating.value ||
            pathFinishing
        ) {
          return
        }

        if (generatingProgress.value < 28) {
          generatingProgress.value += 2.6
        } else if (
            generatingProgress.value < 56
        ) {
          generatingProgress.value += 1.7
        } else if (
            generatingProgress.value < 78
        ) {
          generatingProgress.value += 0.95
        } else if (
            generatingProgress.value < 94
        ) {
          generatingProgress.value += 0.32
        }

        generatingProgress.value =
            Math.min(
                generatingProgress.value,
                94,
            )

        syncPlanningMessagesByProgress()

        persistPlanningTask({
          status: 'running',
          progress:
              generatingProgress.value,
          logs: [
            ...generatingMessages.value,
          ],
        })
      }, 700)
}

function stopTutorialProgressAnimation() {
  if (
      tutorialProgressTimer === null
  ) {
    return
  }

  window.clearInterval(
      tutorialProgressTimer,
  )
  tutorialProgressTimer = null
}

function startTutorialProgressAnimation(
    initialProgress =
        tutorialProgress.value,
) {
  stopTutorialProgressAnimation()

  tutorialProgress.value =
      Math.max(
          tutorialProgress.value,
          initialProgress,
      )

  tutorialProgressTimer =
      window.setInterval(() => {
        if (
            !pageActive ||
            !isGeneratingTutorial.value ||
            tutorialFinishing
        ) {
          return
        }

        if (tutorialProgress.value < 27) {
          tutorialProgress.value += 2.3
        } else if (
            tutorialProgress.value < 53
        ) {
          tutorialProgress.value += 1.55
        } else if (
            tutorialProgress.value < 76
        ) {
          tutorialProgress.value += 0.9
        } else if (
            tutorialProgress.value < 94
        ) {
          tutorialProgress.value += 0.3
        }

        tutorialProgress.value =
            Math.min(
                tutorialProgress.value,
                94,
            )

        syncTutorialMessagesByProgress()

        if (tutorialNodeId.value) {
          persistTutorialTask(
              tutorialNodeId.value,
              {
                status: 'running',
                progress:
                    tutorialProgress.value,
                logs: [
                  ...tutorialMessages.value,
                ],
              },
          )
        }
      }, 700)
}

function previewNode(
    node: LearningPathNode,
) {
  activeDetailNode.value = node
}

async function handleNodeClick(
    node: LearningPathNode,
) {
  activeDetailNode.value = node

  if (!canEnterNode(node)) {
    toast.warning(
        '该节点尚未解锁，请先完成前置节点',
    )
    return
  }

  await openNodeLearning(node)
}

async function openNodeLearning(
    node: LearningPathNode,
) {
  if (
      openingNodeId.value ||
      isGeneratingTutorial.value
  ) {
    return
  }

  openingNodeId.value = node.id
  tutorialNodeId.value = node.id
  tutorialMessages.value = [
    '正在检查该节点是否已有教程。',
  ]

  try {
    const workspaceResponse =
        await getLearningNodeWorkspace(
            node.id,
        )

    const workspace =
        unwrapResponseData<NodeWorkspaceLike>(
            workspaceResponse,
        )

    if (workspace.current_tutorial) {
      await startLearning(node.id)

      await router.push(
          `/path-planner/node/${node.id}`,
      )
      return
    }

    await beginTutorialGeneration(node)
  } catch (error) {
    toast.error(
        getErrorMessage(
            error,
            '打开节点学习页失败',
        ),
    )

    openingNodeId.value = null
    tutorialNodeId.value = null
    tutorialMessages.value = []
  }
}

async function invokeTutorialGeneration(
    targetNodeId: number,
    token: number,
) {
  try {
    await startLearning(targetNodeId)

    const response =
        await generateTutorial(
            targetNodeId,
        )

    if (
        token !== tutorialMonitorToken ||
        !pageActive
    ) {
      return ''
    }

    const workspace =
        unwrapResponseData<NodeWorkspaceLike>(
            response,
        )

    if (workspace.current_tutorial) {
      await finishTutorialGeneration(
          targetNodeId,
          workspace,
      )
    }

    return ''
  } catch (error) {
    return getErrorMessage(
        error,
        '教程生成请求失败',
    )
  }
}

async function checkTutorialReady(
    targetNodeId: number,
) {
  const response =
      await getLearningNodeWorkspace(
          targetNodeId,
      )

  const workspace =
      unwrapResponseData<NodeWorkspaceLike>(
          response,
      )

  if (workspace.current_tutorial) {
    await finishTutorialGeneration(
        targetNodeId,
        workspace,
    )
    return true
  }

  return false
}

async function finishTutorialGeneration(
    targetNodeId: number,
    readyWorkspace?: NodeWorkspaceLike,
) {
  if (
      tutorialFinishing ||
      !pageActive
  ) {
    return
  }

  let workspace = readyWorkspace

  if (!workspace?.current_tutorial) {
    const response =
        await getLearningNodeWorkspace(
            targetNodeId,
        )

    workspace =
        unwrapResponseData<NodeWorkspaceLike>(
            response,
        )
  }

  if (!workspace.current_tutorial) {
    return
  }

  tutorialFinishing = true
  tutorialMonitorToken += 1
  stopTutorialProgressAnimation()

  addTutorialMessage(
      '教程内容已生成，正在准备进入学习页面。',
  )

  await animateProgressTo(
      tutorialProgress,
      100,
      760,
  )

  persistTutorialTask(
      targetNodeId,
      {
        status: 'completed',
        progress: 100,
        error: '',
        logs: [
          ...tutorialMessages.value,
        ],
      },
  )

  await delay(850)

  if (!pageActive) {
    tutorialFinishing = false
    return
  }

  clearTutorialCache(targetNodeId)

  isGeneratingTutorial.value = false
  openingNodeId.value = null
  tutorialNodeId.value = null
  tutorialGenerationError.value = ''
  tutorialFinishing = false

  await router.push(
      `/path-planner/node/${targetNodeId}`,
  )
}

function failTutorialGeneration(
    message: string,
) {
  stopTutorialProgressAnimation()

  tutorialGenerationError.value =
      message

  if (tutorialNodeId.value) {
    persistTutorialTask(
        tutorialNodeId.value,
        {
          status: 'failed',
          progress:
              tutorialProgress.value,
          error: message,
          logs: [
            ...tutorialMessages.value,
          ],
        },
    )
  }

  toast.error(message)
}

async function monitorTutorialGeneration(
    targetNodeId: number,
    invokeImmediately: boolean,
) {
  const token = ++tutorialMonitorToken
  const startedAt = Date.now()

  let generatorInvoked = false
  let generatorError = ''
  let checksAfterGeneratorError = 0

  const invoke = async () => {
    if (
        generatorInvoked ||
        token !== tutorialMonitorToken ||
        !pageActive
    ) {
      return
    }

    generatorInvoked = true

    generatorError =
        await invokeTutorialGeneration(
            targetNodeId,
            token,
        )

    if (generatorError) {
      addTutorialMessage(
          '生成连接暂时中断，正在继续确认后台结果。',
      )
    }
  }

  if (invokeImmediately) {
    void invoke()
  }

  while (
      token === tutorialMonitorToken &&
      pageActive &&
      isGeneratingTutorial.value &&
      !tutorialGenerationError.value &&
      !tutorialFinishing &&
      Date.now() - startedAt <
      TUTORIAL_CONFIRM_TIMEOUT
  ) {
    try {
      if (
          await checkTutorialReady(
              targetNodeId,
          )
      ) {
        return
      }

      if (
          !invokeImmediately &&
          !generatorInvoked &&
          Date.now() - startedAt >= 5000
      ) {
        void invoke()
      }

      if (
          generatorInvoked &&
          generatorError
      ) {
        checksAfterGeneratorError += 1

        if (
            checksAfterGeneratorError >= 8
        ) {
          failTutorialGeneration(
              generatorError,
          )
          return
        }
      }
    } catch {
      addTutorialMessage(
          '暂时无法读取教程状态，正在继续重试。',
      )
    }

    await delay(1500)
  }

  if (
      token === tutorialMonitorToken &&
      pageActive &&
      isGeneratingTutorial.value &&
      !tutorialGenerationError.value &&
      !tutorialFinishing
  ) {
    failTutorialGeneration(
        '教程生成确认超时，后台任务可能仍在继续。刷新页面后会继续确认生成结果。',
    )
  }
}

async function beginTutorialGeneration(
    node: LearningPathNode,
) {
  tutorialMonitorToken += 1
  tutorialFinishing = false

  isGeneratingTutorial.value = true
  openingNodeId.value = node.id
  tutorialNodeId.value = node.id
  tutorialGenerationError.value = ''
  tutorialProgress.value = 7
  tutorialMessages.value = [
    '教程任务已提交，正在准备节点上下文。',
  ]

  clearTutorialCache(node.id)

  persistTutorialTask(
      node.id,
      {
        status: 'running',
        pathId: path.value?.id ?? null,
        title: node.title,
        progress: 7,
        logs: [
          ...tutorialMessages.value,
        ],
        error: '',
        startedAt: Date.now(),
      },
  )

  startTutorialProgressAnimation(7)

  await monitorTutorialGeneration(
      node.id,
      true,
  )
}

async function resumeTutorialGeneration(
    cached: CachedTutorialGeneration,
) {
  const node =
      path.value?.nodes.find(
          item =>
              item.id === cached.nodeId,
      )

  if (!node) {
    clearTutorialCache(cached.nodeId)
    return
  }

  openingNodeId.value = cached.nodeId
  tutorialNodeId.value = cached.nodeId
  isGeneratingTutorial.value = true
  tutorialGenerationError.value =
      cached.error || ''
  tutorialProgress.value =
      Math.max(
          cached.progress,
          estimateTutorialProgress(cached),
      )
  tutorialMessages.value =
      cached.logs.length
          ? [...cached.logs]
          : [
            '已恢复教程生成任务，正在确认后台结果。',
          ]

  if (cached.status === 'failed') {
    stopTutorialProgressAnimation()
    return
  }

  try {
    if (
        await checkTutorialReady(
            cached.nodeId,
        )
    ) {
      return
    }
  } catch {
    addTutorialMessage(
        '正在重新连接后台教程任务。',
    )
  }

  startTutorialProgressAnimation(
      tutorialProgress.value,
  )

  await monitorTutorialGeneration(
      cached.nodeId,
      false,
  )
}

async function resumePendingTutorialForPath(
    pathId: number,
) {
  if (
      !pageActive ||
      isGeneratingTutorial.value
  ) {
    return
  }

  const cached =
      findPendingTutorialForPath(pathId)

  if (!cached) return

  await resumeTutorialGeneration(cached)
}

function closeTutorialFailure() {
  tutorialMonitorToken += 1
  stopTutorialProgressAnimation()

  if (tutorialNodeId.value) {
    clearTutorialCache(
        tutorialNodeId.value,
    )
  }

  isGeneratingTutorial.value = false
  openingNodeId.value = null
  tutorialNodeId.value = null
  tutorialProgress.value = 0
  tutorialMessages.value = []
  tutorialGenerationError.value = ''
}

async function retryTutorialGeneration() {
  const targetNodeId =
      tutorialNodeId.value

  if (!targetNodeId) {
    closeTutorialFailure()
    return
  }

  const node =
      path.value?.nodes.find(
          item =>
              item.id === targetNodeId,
      )

  if (!node) {
    closeTutorialFailure()
    toast.error(
        '未找到需要重新生成的学习节点',
    )
    return
  }

  tutorialMonitorToken += 1
  stopTutorialProgressAnimation()
  clearTutorialCache(targetNodeId)

  tutorialGenerationError.value = ''
  tutorialProgress.value = 0
  tutorialMessages.value = []

  await beginTutorialGeneration(node)
}

function stopSSE() {
  pathEvents.close()
}

function handlePathEvent(
    event: PathEvent,
) {
  if (
      typeof event.progress === 'number'
  ) {
    generatingProgress.value =
        Math.max(
            generatingProgress.value,
            Math.min(
                event.progress,
                96,
            ),
        )
  }

  if (event.message) {
    addPlanningMessage(event.message)
  }

  persistPlanningTask({
    status: 'running',
    progress:
        generatingProgress.value,
    logs: [
      ...generatingMessages.value,
    ],
  })
}

function startSSE(
    pathId: number,
    runId: string,
) {
  stopSSE()

  pathEvents.connect(
      pathId,
      runId,
      {
        onEvent: handlePathEvent,
        onCompleted: () => {
          generatingProgress.value =
              Math.max(
                  generatingProgress.value,
                  96,
              )

          addPlanningMessage(
              '后端规划已完成，正在确认路径结构写入。',
          )

          void confirmPathCompletion(
              pathId,
          )
        },
        onFailed: error => {
          addPlanningMessage(
              '实时进度连接暂时中断，正在通过路径状态继续确认。',
          )

          persistPlanningTask({
            status: 'running',
            error:
                error.message || '',
          })
        },
      },
  )
}

async function confirmPathCompletion(
    pathId: number,
) {
  for (
      let index = 0;
      index < 12;
      index += 1
  ) {
    if (!pageActive) return

    try {
      const response =
          await getLearningPathById(
              pathId,
          )

      const readyPath =
          unwrapResponseData<PathOverview>(
              response,
          )

      if (
          readyPath.status !==
          'generating'
      ) {
        await finishPathGeneration(
            readyPath,
        )
        return
      }
    } catch {
      // 交由轮询继续确认。
    }

    await delay(800)
  }
}

async function monitorPathGeneration(
    pathId: number,
) {
  const token = ++pathMonitorToken
  const startedAt = Date.now()

  while (
      token === pathMonitorToken &&
      pageActive &&
      isGenerating.value &&
      !pathFinishing &&
      !pathGenerationError.value &&
      Date.now() - startedAt <
      PLANNING_CONFIRM_TIMEOUT
  ) {
    try {
      const response =
          await getLearningPathById(
              pathId,
          )

      const current =
          unwrapResponseData<PathOverview>(
              response,
          )

      if (
          current.status !== 'generating'
      ) {
        if (
            current.status === 'failed'
        ) {
          failPathGeneration(
              '学习路径生成失败，请返回创建页面重新规划。',
          )
          return
        }

        await finishPathGeneration(
            current,
        )
        return
      }
    } catch {
      addPlanningMessage(
          '暂时无法读取路径状态，正在继续重试。',
      )
    }

    await delay(1800)
  }

  if (
      token === pathMonitorToken &&
      pageActive &&
      isGenerating.value &&
      !pathFinishing &&
      !pathGenerationError.value
  ) {
    failPathGeneration(
        '路径生成确认超时，后台任务可能仍在继续。刷新页面后会继续确认生成结果。',
    )
  }
}

async function finishPathGeneration(
    readyPath?: PathOverview,
) {
  if (
      pathFinishing ||
      !pageActive
  ) {
    return
  }

  pathFinishing = true
  pathMonitorToken += 1
  stopSSE()
  stopPathProgressAnimation()

  addPlanningMessage(
      '路径结构生成完成，正在打开学习路径总览。',
  )

  await animateProgressTo(
      generatingProgress,
      100,
      760,
  )

  persistPlanningTask({
    status: 'completed',
    progress: 100,
    error: '',
    logs: [
      ...generatingMessages.value,
    ],
  })

  await delay(850)

  if (!pageActive) {
    pathFinishing = false
    return
  }

  let latest = readyPath

  if (!latest) {
    const pathId =
        path.value?.id ??
        Number(route.params.id || 0)

    if (pathId) {
      const response =
          await getLearningPathById(
              pathId,
          )

      latest =
          unwrapResponseData<PathOverview>(
              response,
          )
    }
  }

  if (
      !latest ||
      latest.status === 'generating'
  ) {
    pathFinishing = false
    generatingProgress.value = 94
    startPathProgressAnimation(94)

    const pathId =
        path.value?.id ??
        Number(route.params.id || 0)

    if (pathId) {
      void monitorPathGeneration(pathId)
    }

    return
  }

  path.value = latest
  activeDetailNode.value = null
  isGenerating.value = false
  pathGenerationError.value = ''
  pathFinishing = false

  clearPlanningCache(latest.id)

  await loadEvaluation(latest.id)
  await resumePendingTutorialForPath(
      latest.id,
  )
}

function failPathGeneration(
    message: string,
) {
  stopSSE()
  stopPathProgressAnimation()

  pathGenerationError.value = message

  persistPlanningTask({
    status: 'failed',
    progress:
        generatingProgress.value,
    error: message,
    logs: [
      ...generatingMessages.value,
    ],
  })

  toast.error(message)
}

async function retryPathStatus() {
  const pathId =
      path.value?.id ??
      Number(route.params.id || 0)

  if (!pathId) {
    await router.push('/path-planner')
    return
  }

  pathGenerationError.value = ''
  isGenerating.value = true

  addPlanningMessage(
      '正在重新连接路径规划任务。',
  )

  startPathProgressAnimation(
      generatingProgress.value,
  )

  if (activeRunId.value) {
    startSSE(
        pathId,
        activeRunId.value,
    )
  }

  void monitorPathGeneration(pathId)
}

async function loadEvaluation(
    pathId: number,
) {
  try {
    const response =
        await getLearningEvaluation(
            pathId,
        )

    evaluation.value =
        unwrapResponseData<
            PathLearningEvaluationResponse
        >(response)
  } catch (error) {
    console.error(
        'Failed to load evaluation',
        error,
    )

    evaluation.value = null
  }
}

async function loadNewPathRequest() {
  isGenerating.value = true
  loading.value = false
  path.value = null
  evaluation.value = null
  activeDetailNode.value = null
  pathGenerationError.value = ''
  generatingProgress.value = 8
  generatingMessages.value = [
    '正在创建路径任务。',
    '正在读取学习目标与用户画像。',
  ]

  const newGoal =
      String(route.query.goal || '')

  const newTopic =
      String(
          route.query.topic ||
          newGoal,
      )

  if (!newGoal) {
    await router.replace(
        '/path-planner',
    )
    return
  }

  try {
    let parsedKnowledge: string[] = []

    if (route.query.current_knowledge) {
      try {
        parsedKnowledge =
            JSON.parse(
                String(
                    route.query
                        .current_knowledge,
                ),
            )
      } catch (error) {
        console.warn(
            '解析已掌握知识点失败:',
            error,
        )
      }
    }

    const preferences:
        PathPreferences = {
          use_profile:
              route.query.use_profile !==
              'false',
          scene: 'general',
          pace: 'normal',
          granularity: 'standard',
          focus: ['key_points'],
        }

    const response =
        await createLearningPath({
          goal: newGoal,
          topic: newTopic,
          current_knowledge:
              parsedKnowledge,
          preferences,
        })

    const newPath =
        unwrapResponseData<
            PathOverview & {
              run_id?: string
            }
        >(response)

    activeRunId.value =
        newPath.run_id || null

    persistPlanningTask({
      status: 'running',
      pathId: newPath.id,
      runId: newPath.run_id || '',
      progress:
          generatingProgress.value,
      logs: [
        ...generatingMessages.value,
      ],
      error: '',
      startedAt: Date.now(),
    })

    await router.replace({
      path:
          `/path-planner/overview/` +
          `${newPath.id}`,
      query:
          newPath.run_id
              ? {
                run_id:
                    newPath.run_id,
              }
              : {},
    })
  } catch (error) {
    const message =
        getErrorMessage(
            error,
            '路径规划任务创建失败',
        )

    failPathGeneration(message)
  }
}

async function loadPath() {
  pageActive = true

  const rawId =
      String(route.params.id || '')

  if (rawId === 'new') {
    await loadNewPathRequest()
    return
  }

  loading.value = true

  try {
    const paramId =
        Number(rawId || 0)

    const shouldLoadSpecificPath =
        Boolean(
            rawId &&
            rawId !== 'latest' &&
            Number.isFinite(paramId) &&
            paramId > 0,
        )

    let currentPathId = 0
    let loadedPath:
        PathOverview | null = null

    if (shouldLoadSpecificPath) {
      const response =
          await getLearningPathById(
              paramId,
          )

      loadedPath =
          unwrapResponseData<PathOverview>(
              response,
          )

      currentPathId = loadedPath.id
    } else {
      const response =
          await getCurrentLearningPath()

      loadedPath =
          unwrapResponseData<
              PathOverview | null
          >(response)

      if (!loadedPath) {
        path.value = null
        evaluation.value = null
        return
      }

      currentPathId = loadedPath.id

      if (rawId === 'latest') {
        await router.replace(
            `/path-planner/overview/` +
            `${loadedPath.id}`,
        )
      }
    }

    path.value = loadedPath
    activeDetailNode.value = null

    if (
        loadedPath.status ===
        'generating'
    ) {
      isGenerating.value = true
      pathGenerationError.value = ''

      const cached =
          readPlanningCache()

      if (
          cached &&
          cached.pathId === currentPathId
      ) {
        activeRunId.value =
            String(
                route.query.run_id ||
                cached.runId ||
                '',
            ) || null

        generatingProgress.value =
            Math.max(
                12,
                cached.progress,
                estimatePlanningProgress(
                    cached,
                ),
            )

        generatingMessages.value =
            cached.logs.length
                ? [...cached.logs]
                : [
                  '已恢复正在生成的路径任务。',
                ]

        if (
            cached.status === 'failed'
        ) {
          pathGenerationError.value =
              cached.error ||
              '路径生成失败'
          stopPathProgressAnimation()
          return
        }
      } else {
        activeRunId.value =
            String(
                route.query.run_id ||
                activeRunId.value ||
                '',
            ) || null

        generatingProgress.value =
            Math.max(
                generatingProgress.value,
                18,
            )

        if (
            generatingMessages.value
                .length === 0
        ) {
          generatingMessages.value = [
            '已找到正在生成的路径任务。',
            '正在恢复后端进度连接。',
          ]
        }

        persistPlanningTask({
          status: 'running',
          pathId: currentPathId,
          runId:
              activeRunId.value || '',
          progress:
              generatingProgress.value,
          logs: [
            ...generatingMessages.value,
          ],
          error: '',
          startedAt: Date.now(),
        })
      }

      startPathProgressAnimation(
          generatingProgress.value,
      )

      if (activeRunId.value) {
        startSSE(
            currentPathId,
            activeRunId.value,
        )
      }

      void monitorPathGeneration(
          currentPathId,
      )
      return
    }

    const cached =
        readPlanningCache()

    if (
        cached &&
        cached.pathId === currentPathId &&
        cached.status !== 'failed'
    ) {
      isGenerating.value = true
      generatingProgress.value =
          Math.max(
              cached.progress,
              94,
          )
      generatingMessages.value =
          cached.logs.length
              ? [...cached.logs]
              : [
                '路径结构已生成，正在打开学习路径总览。',
              ]

      await finishPathGeneration(
          loadedPath,
      )
      return
    }

    isGenerating.value = false
    generatingProgress.value = 100
    pathGenerationError.value = ''
    stopSSE()
    stopPathProgressAnimation()
    clearPlanningCache(
        currentPathId,
    )

    await loadEvaluation(
        currentPathId,
    )

    await resumePendingTutorialForPath(
        currentPathId,
    )
  } catch (error) {
    toast.error(
        getErrorMessage(
            error,
            '加载学习路径失败',
        ),
    )
  } finally {
    loading.value = false
  }
}

function deactivatePage() {
  pageActive = false
  pathMonitorToken += 1
  tutorialMonitorToken += 1

  stopSSE()
  stopPathProgressAnimation()
  stopTutorialProgressAnimation()
}

watch(
    () => route.params.id,
    (newId, oldId) => {
      if (newId === oldId) return

      deactivatePage()
      pageActive = true

      activeDetailNode.value = null
      pathGenerationError.value = ''
      pathFinishing = false
      tutorialFinishing = false

      if (
          oldId !== 'new'
      ) {
        generatingMessages.value = []
        generatingProgress.value = 12
        isGenerating.value = false
      }

      void loadPath()
    },
)

onMounted(() => {
  pageActive = true
  void loadPath()
})

onActivated(() => {
  activationCount += 1

  if (activationCount <= 1) {
    return
  }

  pageActive = true
  pathFinishing = false
  tutorialFinishing = false

  void loadPath()
})

onDeactivated(() => {
  deactivatePage()
})

onBeforeUnmount(() => {
  deactivatePage()
})

</script>

<style scoped>
.path-overview-page {
  --color-state-locked: #94a3b8;
  --color-state-locked-border: #e2e8f0;

  --color-state-available: var(--color-primary-text, #205f67);
  --color-state-available-border: var(--color-primary-border, #b9dedc);

  --color-state-active: #4f46e5;
  --color-state-active-border: #6366f1;
  --color-state-active-glow: rgba(99, 102, 241, 0.15);

  --color-state-alert: #d97706;
  --color-state-alert-border: #fbbf24;

  --color-state-completed: var(--color-success, #329a82);
  --color-state-completed-bg: var(--color-success-soft, #e8f7f2);
  --color-state-completed-border: #86efac;

  min-height: calc(100vh - var(--navbar-height, 72px));
  background: #fafbfc;
  color: var(--color-text, #173b42);
}

.state-view {
  width: min(760px, calc(100vw - 48px));
  min-height: calc(100vh - var(--navbar-height, 72px));
  margin: 0 auto;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 14px;
  text-align: center;
}

.state-view h2 {
  margin: 0;
  color: var(--color-text-strong, #173b42);
  font-size: 24px;
}

.state-view p {
  margin: 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 14px;
}

.state-spinner {
  width: 34px;
  height: 34px;
  border: 3px solid rgba(200, 228, 227, 0.72);
  border-top-color: var(--color-primary, #46b8b4);
  border-radius: 999px;
  animation: spin 0.85s linear infinite;
}

.primary-action {
  border: 1px solid rgba(32, 95, 103, 0.16);
  border-radius: 14px;
  background: linear-gradient(135deg, #46b8b4, #5b6ee1);
  color: #ffffff;
  font-weight: 850;
  cursor: pointer;
}

.generating-view {
  width: min(820px, calc(100vw - 48px));
  min-height: calc(100vh - var(--navbar-height, 72px));
  margin: 0 auto;
  display: grid;
  align-content: center;
  gap: 24px;
}

.generate-copy {
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.52);
}

.generate-copy span {
  display: inline-flex;
  color: #5b6ee1;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.generate-copy h1 {
  margin: 10px 0 8px;
  color: var(--color-text-strong, #173b42);
  font-size: 32px;
  line-height: 1.12;
  letter-spacing: -0.04em;
}

.generate-copy p {
  margin: 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 14px;
  line-height: 1.7;
}

.generate-progress-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  font-weight: 800;
}

.generate-progress-head strong {
  color: var(--color-primary-text, #205f67);
}

.generate-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(200, 228, 227, 0.46);
}

.generate-track i {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: linear-gradient(90deg, #46b8b4, #5b6ee1);
  transition: width 0.35s ease;
}

.generate-log {
  display: grid;
  gap: 10px;
}

.log-item {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.42);
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
}

.log-item i {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--color-primary, #46b8b4);
}

.tutorial-generating-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.32);
  backdrop-filter: blur(6px);
  padding: 24px;
}

.tutorial-generating-modal {
  width: min(560px, 100%);
  padding: 36px 32px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.12);
  backdrop-filter: blur(20px);
}

.tutorial-generating-modal .generate-copy {
  text-align: center;
}

.tutorial-generating-modal .generate-log {
  margin-top: 20px;
}

.tutorial-overlay-enter-active,
.tutorial-overlay-leave-active {
  transition: opacity 0.2s ease;
}

.tutorial-overlay-enter-active .tutorial-generating-modal,
.tutorial-overlay-leave-active .tutorial-generating-modal {
  transition: transform 0.2s ease;
}

.tutorial-overlay-enter-from,
.tutorial-overlay-leave-to {
  opacity: 0;
}

.tutorial-overlay-enter-from .tutorial-generating-modal,
.tutorial-overlay-leave-to .tutorial-generating-modal {
  transform: scale(0.97) translateY(8px);
}

.overview-shell {
  width: min(1720px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 14px 0 30px;
}

.overview-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 450px;
  gap: 34px;
  align-items: start;
}

.learning-map {
  min-width: 0;
}

.map-toolbar {
  min-height: 86px;
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(520px, 0.92fr);
  gap: 24px;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.52);
}

.map-title {
  min-width: 0;
}

.map-title span,
.mentor-kicker {
  display: inline-flex;
  color: #5b6ee1;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.map-title h1 {
  margin: 7px 0 5px;
  color: var(--color-text-strong, #173b42);
  font-size: 22px;
  line-height: 1.25;
  letter-spacing: -0.035em;
}

.map-title p {
  margin: 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  line-height: 1.55;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.map-actions {
  min-width: 0;
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
}

.compact-progress {
  height: 58px;
  display: grid;
  align-content: center;
  border-right: 1px solid rgba(200, 228, 227, 0.66);
}

.compact-progress strong {
  color: var(--color-primary-text, #205f67);
  font-size: 25px;
  line-height: 1;
}

.compact-progress span {
  margin-top: 5px;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-weight: 800;
}

.map-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.map-tags span {
  min-height: 27px;
  max-width: 250px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border: 1px solid rgba(200, 228, 227, 0.72);
  border-radius: 999px;
  color: var(--color-text-secondary, #58747a);
  background: rgba(255, 255, 255, 0.58);
  font-size: 12px;
  font-weight: 780;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-line {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 9px;
}

.action-line button,
.primary-action {
  height: 38px;
  padding: 0 14px;
  font-size: 13px;
}

.action-line button:not(.primary-action) {
  border: 1px solid rgba(200, 228, 227, 0.72);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.66);
  color: var(--color-text, #173b42);
  font-weight: 800;
  cursor: pointer;
}

.action-line button:hover {
  border-color: var(--color-primary, #46b8b4);
}

.summary-line {
  min-height: 56px;
  display: grid;
  grid-template-columns: repeat(4, minmax(86px, 1fr));
  gap: 14px;
  align-items: center;
  padding: 10px 0 14px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.52);
}

.summary-line div {
  min-height: 42px;
  padding-left: 12px;
  display: grid;
  align-content: center;
  border-left: 3px solid currentColor;
}

.summary-line .available {
  color: var(--color-primary, #46b8b4);
}

.summary-line .learning {
  color: #5b6ee1;
}

.summary-line .completed {
  color: #329a82;
}

.summary-line .locked {
  color: #9aaeb1;
}

.summary-line span {
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-weight: 800;
}

.summary-line strong {
  margin-top: 3px;
  color: var(--color-text-strong, #173b42);
  font-size: 19px;
  line-height: 1;
}

.map-body {
  display: grid;
}

.map-stage {
  padding: 26px 0 30px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.52);
}

.map-stage-head {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) 128px;
  gap: 16px;
  align-items: center;
  margin-bottom: 20px;
}

.stage-order {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  border: 1px solid rgba(200, 228, 227, 0.82);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-primary-text, #205f67);
}

.stage-order span {
  font-size: 12px;
  font-weight: 900;
}

.stage-copy span {
  color: #5b6ee1;
  font-size: 12px;
  font-weight: 900;
}

.stage-copy h3 {
  margin: 5px 0 5px;
  color: var(--color-text-strong, #173b42);
  font-size: 20px;
  line-height: 1.35;
  letter-spacing: -0.025em;
}

.stage-copy p {
  margin: 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  line-height: 1.45;
}

.stage-progress {
  min-width: 0;
}

.stage-progress strong {
  display: block;
  color: var(--color-text-strong, #173b42);
  font-size: 22px;
  line-height: 1;
}

.stage-progress span {
  display: block;
  margin-top: 5px;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-weight: 800;
}

.stage-progress-track {
  height: 6px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(200, 228, 227, 0.52);
}

.stage-progress-track i {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: linear-gradient(90deg, #46b8b4, #5b6ee1);
}

.map-node-list {
  position: relative;
  display: grid;
  gap: 12px;
  padding-left: 12px;
}

.map-node-list::before {
  content: "";
  position: absolute;
  left: 34px;
  top: 18px;
  bottom: 18px;
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(
      180deg,
      rgba(70, 184, 180, 0.68),
      rgba(91, 110, 225, 0.5),
      rgba(139, 92, 246, 0.32)
  );
}

.map-node {
  position: relative;
  z-index: 1;
  width: min(860px, 100%);
  min-height: 78px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) 118px;
  gap: 14px;
  align-items: center;
  padding: 12px 14px 12px 0;
  border: 0;
  border-bottom: 1px solid rgba(200, 228, 227, 0.56);
  border-radius: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: var(--transition-fast, 0.2s ease);
}

.map-node::after {
  content: "";
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 0;
  border-radius: 999px;
  background: transparent;
  transition: var(--transition-fast, 0.2s ease);
}

.map-node:disabled {
  cursor: wait;
}

.map-node:hover:not(:disabled),
.map-node.selected {
  padding-left: 10px;
  background: linear-gradient(
      90deg,
      rgba(216, 241, 240, 0.5),
      rgba(255, 255, 255, 0)
  );
}

.map-node.current {
  padding-left: 12px;
  background: linear-gradient(
      90deg,
      rgba(70, 184, 180, 0.2) 0%,
      rgba(216, 241, 240, 0.52) 42%,
      rgba(255, 255, 255, 0) 100%
  );
  border-bottom-color: rgba(70, 184, 180, 0.36);
}

.map-node.current::after {
  width: 4px;
  background: linear-gradient(180deg, #46b8b4, #5b6ee1);
}

.map-node.opening {
  padding-left: 12px;
  background: linear-gradient(
      90deg,
      rgba(91, 110, 225, 0.16) 0%,
      rgba(238, 242, 255, 0.7) 44%,
      rgba(255, 255, 255, 0) 100%
  );
}

.map-node.opening::after {
  width: 4px;
  background: #5b6ee1;
}

.map-node.locked {
  opacity: 0.82;
}

.map-node.locked:hover:not(:disabled) {
  background: linear-gradient(
      90deg,
      rgba(237, 243, 243, 0.72),
      rgba(255, 255, 255, 0)
  );
}

.checkpoint {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
}

.checkpoint i {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  border: 4px solid #ffffff;
  background: var(--color-primary, #46b8b4);
  box-shadow:
      0 0 0 2px rgba(70, 184, 180, 0.38),
      0 8px 18px rgba(70, 184, 180, 0.2);
}

.map-node.current .checkpoint i {
  width: 22px;
  height: 22px;
  background: #2fb9b4;
  box-shadow:
      0 0 0 3px rgba(70, 184, 180, 0.34),
      0 10px 24px rgba(70, 184, 180, 0.22);
  animation: checkpointPulse 1.45s ease-in-out infinite;
}

.map-node.in_progress .checkpoint i {
  background: #5b6ee1;
  box-shadow:
      0 0 0 2px rgba(91, 110, 225, 0.34),
      0 8px 18px rgba(91, 110, 225, 0.16);
}

.map-node.completed .checkpoint i,
.map-node.completed_with_gaps .checkpoint i {
  background: #329a82;
  box-shadow:
      0 0 0 2px rgba(50, 154, 130, 0.32),
      0 8px 18px rgba(50, 154, 130, 0.14);
}

.map-node.locked .checkpoint i {
  width: 17px;
  height: 17px;
  background: #9aaeb1;
  box-shadow: 0 0 0 2px rgba(154, 174, 177, 0.22);
}

.map-node.opening .checkpoint i {
  animation: checkpointPulse 1.45s ease-in-out infinite;
}

.node-copy {
  min-width: 0;
}

.node-copy strong {
  display: block;
  color: var(--color-text-strong, #173b42);
  font-size: 16px;
  line-height: 1.38;
  font-weight: 850;
}

.map-node.current .node-copy strong {
  color: var(--color-primary-text, #205f67);
  font-weight: 900;
}

.node-copy span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 5px;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-weight: 700;
}

.map-node.current .node-copy span {
  color: #2d7078;
  font-weight: 800;
}

.node-extra {
  justify-self: end;
  display: grid;
  gap: 6px;
  text-align: right;
  white-space: nowrap;
}

.node-extra span,
.node-extra em {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-weight: 800;
  font-style: normal;
}

.node-extra span {
  color: var(--color-primary-text, #205f67);
}

.map-node.current .node-extra span {
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(70, 184, 180, 0.16);
  color: var(--color-primary-text, #205f67);
}

.map-node.locked .node-copy strong {
  color: #496267;
}

.map-node.locked .node-copy span,
.map-node.locked .node-extra span,
.map-node.locked .node-extra em {
  color: #8aa0a4;
}

.mentor-panel {
  min-width: 0;
  padding-left: 28px;
  border-left: 1px solid rgba(200, 228, 227, 0.54);
}

.mentor-section {
  padding-bottom: 20px;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.52);
}

.mentor-section h2 {
  margin: 8px 0 8px;
  color: var(--color-text-strong, #173b42);
  font-size: 21px;
  line-height: 1.25;
  letter-spacing: -0.035em;
}

.mentor-section h3 {
  margin: 8px 0 0;
  color: var(--color-text-strong, #173b42);
  font-size: 17px;
  line-height: 1.35;
  letter-spacing: -0.025em;
}

.mentor-section p,
.mentor-note {
  margin: 8px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  line-height: 1.7;
}

.mentor-table {
  margin-top: 14px;
}

.mentor-table div {
  min-height: 44px;
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  align-items: center;
  border-bottom: 1px solid rgba(200, 228, 227, 0.38);
}

.mentor-table div:last-child {
  border-bottom: 0;
}

.mentor-table span {
  color: var(--color-text-faint, #8da4a8);
  font-size: 12px;
  font-weight: 800;
}

.mentor-table strong {
  color: var(--color-text-strong, #173b42);
  font-size: 13px;
  text-align: right;
  word-break: break-word;
}

.prerequisite-list {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.prerequisite-list span {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(200, 228, 227, 0.72);
  color: var(--color-text-secondary, #58747a);
  background: rgba(255, 255, 255, 0.58);
  font-size: 12px;
  font-weight: 750;
}

.learn-flow {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}

.learn-flow div {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
}

.learn-flow span {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  border: 1px solid rgba(200, 228, 227, 0.82);
  color: var(--color-primary-text, #205f67);
  font-size: 12px;
  font-weight: 900;
}

.learn-flow p {
  margin: 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  font-weight: 700;
}

.evaluation-panel :deep(.evaluation-banner),
.evaluation-panel :deep(.dashboard-banner) {
  margin: 12px 0 0;
  box-shadow: none;
}

.log-enter-active,
.log-leave-active {
  transition: all 0.24s ease;
}

.log-enter-from,
.log-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.cockpit-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: var(--shadow-sm);
  border-top: 3px solid var(--color-primary);
  transition: all 0.3s ease;
}

.cockpit-card:hover {
  box-shadow: var(--shadow-md);
}

.cockpit-header {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--color-border-light);
  padding-bottom: 14px;
}

.header-icon {
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse-glow 2s infinite alternate;
}

.cockpit-header h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-text-strong);
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.metric-item {
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.metric-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon.clock {
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
}

.metric-icon.score {
  background: rgba(16, 185, 129, 0.08);
  color: var(--color-success);
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-info label {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
}

.metric-info strong {
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--color-text);
}

.metric-info strong.good {
  color: var(--color-success);
}

.metric-info strong.warning {
  color: var(--color-warning);
}

.metric-info strong small {
  font-size: 0.75rem;
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
}

.diagnostic-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.section-title svg {
  color: var(--color-text-muted);
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.weak-tag {
  font-size: 0.75rem;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border: 1px solid rgba(239, 68, 68, 0.15);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-weight: 600;
}

.empty-weak {
  font-size: 0.75rem;
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid rgba(16, 185, 129, 0.15);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.advice-section {
  border-top: 1px dashed var(--color-border);
  padding-top: 16px;
}

.advice-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.advice-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.bullet {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.6875rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.advice-item p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes checkpointPulse {
  0%,
  100% {
    box-shadow:
        0 0 0 3px rgba(70, 184, 180, 0.34),
        0 0 0 0 rgba(70, 184, 180, 0.18);
  }

  50% {
    box-shadow:
        0 0 0 3px rgba(70, 184, 180, 0.34),
        0 0 0 9px rgba(70, 184, 180, 0.1);
  }
}

@keyframes pulse-glow {
  0% {
    transform: scale(0.95);
    opacity: 0.8;
  }

  100% {
    transform: scale(1.05);
    opacity: 1;
  }
}

@media (max-width: 1380px) {
  .overview-workspace {
    grid-template-columns: minmax(0, 1fr) 410px;
    gap: 28px;
  }

  .map-toolbar {
    grid-template-columns: 1fr;
  }

  .map-actions {
    grid-template-columns: 78px minmax(0, 1fr);
  }

  .action-line {
    justify-content: flex-start;
  }
}

@media (max-width: 1180px) {
  .overview-workspace {
    grid-template-columns: 1fr;
  }

  .mentor-panel {
    padding-left: 0;
    padding-top: 22px;
    border-left: 0;
    border-top: 1px solid rgba(200, 228, 227, 0.54);
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 22px;
  }

  .mentor-section {
    margin-bottom: 0;
  }

  .evaluation-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .overview-shell {
    width: min(100vw - 24px, 760px);
  }

  .map-actions {
    grid-template-columns: 1fr;
  }

  .compact-progress {
    height: auto;
    padding-bottom: 12px;
    border-right: 0;
    border-bottom: 1px solid rgba(200, 228, 227, 0.52);
  }

  .action-line {
    display: grid;
    grid-template-columns: 1fr;
  }

  .summary-line {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .map-stage-head {
    grid-template-columns: 40px minmax(0, 1fr);
  }

  .stage-progress {
    grid-column: 1 / -1;
  }

  .map-node {
    width: 100%;
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .node-extra {
    grid-column: 2;
    justify-self: start;
    display: flex;
    gap: 12px;
    text-align: left;
  }

  .mentor-panel {
    grid-template-columns: 1fr;
  }
}

/* =========================================================
   持久化生成等待界面
   与路径创建页保持一致：多色阶段节点，青绿色固定进度条
   ========================================================= */

.persistent-generation-stage {
  min-height: calc(100vh - var(--navbar-height, 72px));
  display: grid;
  place-items: center;
  padding: 28px 20px;
  background:
      radial-gradient(
          circle at 50% 35%,
          rgba(21, 154, 148, 0.055),
          transparent 30rem
      ),
      #fafcfc;
}

.generation-waiting-card {
  width: min(680px, 100%);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  padding: 31px 32px;
  border: 1px solid #cfe4e2;
  border-radius: 14px;
  background: #ffffff;
  box-shadow:
      0 20px 55px rgba(31, 76, 80, 0.1),
      0 3px 10px rgba(31, 76, 80, 0.035);
  color: #26383c;
}

.generation-loading-header {
  text-align: center;
}

.generation-loader {
  position: relative;
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  margin: 0 auto 16px;
}

.generation-loader-ring {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(21, 154, 148, 0.11);
  border-top-color: #159a94;
  border-right-color: #6bc3be;
  border-radius: 50%;
  animation: generationSpin 1.15s linear infinite;
}

.generation-loader > span {
  position: relative;
  z-index: 1;
  color: #159a94;
  font-size: 19px;
  line-height: 1;
  animation: generationBreathe 1.6s ease-in-out infinite;
}

.generation-loading-header h2,
.generation-result-copy h2 {
  margin: 0;
  color: #172d31;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.4;
  letter-spacing: -0.015em;
}

.generation-loading-header p,
.generation-result-copy p {
  margin: 7px 0 0;
  color: #607277;
  font-size: 13px;
  line-height: 1.65;
}

.generation-timeline {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
  padding: 0 7px;
}

.generation-timeline-node {
  --generation-node-start: #7f9b98;
  --generation-node-end: #a7bfbc;
  --generation-node-soft: #f2f7f6;
  --generation-node-text: #58726f;
  --generation-node-glow: rgba(73, 111, 107, 0.14);
  --generation-next-start: #a7bfbc;

  position: relative;
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.generation-node-circle {
  position: relative;
  z-index: 2;
  isolation: isolate;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 2px solid transparent;
  border-radius: 50%;
  background:
      linear-gradient(#ffffff, #ffffff) padding-box,
      linear-gradient(
          135deg,
          var(--generation-node-start),
          var(--generation-node-end)
      ) border-box;
  color: var(--generation-node-text);
  box-shadow: 0 2px 8px rgba(39, 72, 75, 0.055);
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  font-weight: 750;
  line-height: 1;
  transition:
      color 260ms ease,
      box-shadow 260ms ease,
      transform 260ms ease,
      filter 260ms ease;
}

.generation-node-circle::after {
  content: "";
  position: absolute;
  z-index: -1;
  inset: -6px;
  border-radius: inherit;
  background:
      radial-gradient(
          circle,
          var(--generation-node-glow) 0%,
          transparent 70%
      );
  opacity: 0;
  transform: scale(0.76);
  transition:
      opacity 260ms ease,
      transform 260ms ease;
}

.generation-node-label {
  max-width: 98px;
  color: #9ca9ac;
  font-size: 12px;
  font-weight: 550;
  line-height: 1.45;
  text-align: center;
  transition:
      color 240ms ease,
      font-weight 240ms ease,
      transform 240ms ease;
}

.generation-node-line {
  position: absolute;
  z-index: 1;
  top: 14px;
  left: 50%;
  width: 100%;
  height: 2px;
  overflow: hidden;
  background: #e9efee;
  transition:
      background 320ms ease,
      box-shadow 320ms ease;
}

.generation-timeline-node.is-active .generation-node-circle {
  background:
      linear-gradient(
          135deg,
          var(--generation-node-soft),
          #ffffff
      ) padding-box,
      linear-gradient(
          135deg,
          var(--generation-node-start),
          var(--generation-node-end)
      ) border-box;
  color: var(--generation-node-text);
  box-shadow:
      0 0 0 5px var(--generation-node-glow),
      0 8px 18px var(--generation-node-glow);
  transform: translateY(-1px) scale(1.04);
}

.generation-timeline-node.is-active .generation-node-circle::after {
  opacity: 1;
  transform: scale(1);
  animation: generationNodeBreathe 1.9s ease-in-out infinite;
}

.generation-timeline-node.is-active .generation-node-label {
  color: var(--generation-node-text);
  font-weight: 750;
  transform: translateY(1px);
}

.generation-timeline-node.is-done .generation-node-circle {
  border-color: transparent;
  background:
      linear-gradient(
          135deg,
          var(--generation-node-start),
          var(--generation-node-end)
      ) padding-box;
  color: #ffffff;
  box-shadow:
      0 5px 13px var(--generation-node-glow);
}

.generation-timeline-node.is-done .generation-node-label {
  color: #607277;
  font-weight: 650;
}

.generation-timeline-node.is-done .generation-node-line {
  background:
      linear-gradient(
          90deg,
          var(--generation-node-start),
          var(--generation-node-end) 54%,
          var(--generation-next-start)
      );
  box-shadow: 0 0 7px var(--generation-node-glow);
}

.generation-progress-panel {
  margin-top: 25px;
  padding: 13px 15px;
  border: 1px solid #dfecea;
  border-radius: 8px;
  background: #f8fbfb;
}

.generation-progress-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.generation-progress-head > div {
  min-width: 0;
}

.generation-progress-head span {
  display: block;
  margin-bottom: 2px;
  color: #9ca9ac;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.45;
}

.generation-progress-head strong {
  display: block;
  overflow: hidden;
  color: #176b67;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-progress-head em {
  flex-shrink: 0;
  color: #839397;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  font-style: normal;
  line-height: 1.45;
}

.generation-progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #e4eeed;
}

.generation-progress-track > i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background:
      linear-gradient(
          90deg,
          #159a94,
          #5abdb8
      );
  transition: width 320ms ease;
}

.generation-log-box {
  min-height: 82px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
  margin-top: 17px;
  padding: 12px 15px;
  border-left: 2px solid #82cbc7;
  background: #fbfdfd;
}

.generation-log-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.generation-log-row > span {
  width: 5px;
  height: 5px;
  flex-shrink: 0;
  margin-top: 7px;
  border-radius: 50%;
  background: #159a94;
}

.generation-log-row p {
  margin: 0;
  color: #607277;
  font-size: 13px;
  line-height: 1.65;
}

.generation-persistence-note {
  margin: 12px 0 0;
  color: #8a9a9e;
  font-size: 11px;
  line-height: 1.6;
  text-align: center;
}

.generation-result-state {
  min-height: 310px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.generation-result-icon {
  width: 62px;
  height: 62px;
  display: grid;
  place-items: center;
  margin-bottom: 19px;
  border-radius: 50%;
  font-size: 29px;
  font-weight: 850;
  line-height: 1;
}

.generation-success-icon {
  border: 1px solid #82cbc7;
  background: #eaf7f6;
  color: #159a94;
  animation:
      generationSuccessEnter 420ms
      cubic-bezier(0.16, 1, 0.3, 1);
}

.generation-error-icon {
  border: 1px solid rgba(211, 94, 94, 0.22);
  background: rgba(211, 94, 94, 0.07);
  color: #cc5b5b;
}

.generation-result-copy {
  max-width: 470px;
}

.generation-error-detail {
  width: 100%;
  margin-top: 24px;
  padding: 13px 15px;
  border: 1px solid rgba(211, 94, 94, 0.2);
  border-radius: 8px;
  background: rgba(211, 94, 94, 0.045);
  color: #775d5d;
  font-size: 12px;
  line-height: 1.65;
  text-align: left;
  overflow-wrap: anywhere;
}

.generation-result-actions {
  display: flex;
  justify-content: center;
  gap: 9px;
  margin-top: 23px;
}

.generation-secondary-action,
.generation-primary-action {
  min-width: 116px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 15px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.45;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      background-color 180ms ease,
      color 180ms ease,
      transform 180ms ease;
}

.generation-secondary-action {
  border: 1px solid #dce7e6;
  background: #ffffff;
  color: #607277;
}

.generation-secondary-action:hover {
  border-color: #bccdca;
  background: #f7fafa;
  color: #172d31;
}

.generation-primary-action {
  border: 1px solid #159a94;
  background: #159a94;
  color: #ffffff;
}

.generation-primary-action:hover {
  border-color: #10847f;
  background: #10847f;
  transform: translateY(-1px);
}

.generation-success-summary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
  color: #176b67;
  font-size: 13px;
  font-weight: 650;
  line-height: 1.45;
}

.generation-success-summary > span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #159a94;
  animation: generationSuccessDot 1.1s ease-in-out infinite;
}

.generation-success-track {
  width: min(330px, 100%);
  height: 5px;
  overflow: hidden;
  margin-top: 16px;
  border-radius: 999px;
  background: #e3efee;
}

.generation-success-track > i {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background:
      linear-gradient(
          90deg,
          #159a94,
          #65c4bf
      );
  transform-origin: left center;
  animation: generationSuccessProgress 800ms ease-out;
}

.tutorial-generating-overlay {
  position: fixed;
  z-index: 9000;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(247, 250, 250, 0.84);
  backdrop-filter: blur(5px);
}

.tutorial-waiting-card {
  max-height: calc(100vh - 40px);
}

.tutorial-overlay-enter-active,
.tutorial-overlay-leave-active {
  transition: opacity 220ms ease;
}

.tutorial-overlay-enter-active .tutorial-waiting-card,
.tutorial-overlay-leave-active .tutorial-waiting-card {
  transition:
      opacity 220ms ease,
      transform 220ms ease;
}

.tutorial-overlay-enter-from,
.tutorial-overlay-leave-to {
  opacity: 0;
}

.tutorial-overlay-enter-from .tutorial-waiting-card,
.tutorial-overlay-leave-to .tutorial-waiting-card {
  opacity: 0;
  transform: translateY(8px) scale(0.985);
}

.overview-shell {
  animation:
      overviewReveal 320ms
      cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes generationSpin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes generationBreathe {
  0%,
  100% {
    opacity: 0.62;
    transform: scale(0.92);
  }

  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

@keyframes generationNodeBreathe {
  0%,
  100% {
    opacity: 0.5;
    transform: scale(0.86);
  }

  50% {
    opacity: 1;
    transform: scale(1.08);
  }
}

@keyframes generationSuccessEnter {
  from {
    opacity: 0;
    transform: scale(0.72);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes generationSuccessDot {
  0%,
  100% {
    opacity: 0.45;
  }

  50% {
    opacity: 1;
  }
}

@keyframes generationSuccessProgress {
  from {
    transform: scaleX(0);
  }

  to {
    transform: scaleX(1);
  }
}

@keyframes overviewReveal {
  from {
    opacity: 0;
    transform: translateY(7px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 760px) {
  .persistent-generation-stage {
    padding: 14px 12px;
  }

  .generation-waiting-card {
    max-height: calc(100vh - 24px);
    padding: 26px 18px;
  }

  .generation-timeline {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
    margin-top: 25px;
    padding: 0;
  }

  .generation-timeline-node {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr);
    align-items: center;
    justify-items: start;
    gap: 10px;
  }

  .generation-node-circle {
    grid-column: 1;
  }

  .generation-node-label {
    grid-column: 2;
    max-width: none;
    text-align: left;
  }

  .generation-node-line {
    top: 29px;
    left: 14px;
    width: 2px;
    height: 22px;
  }

  .generation-progress-head {
    align-items: flex-start;
  }

  .generation-result-actions {
    width: 100%;
    flex-direction: column;
  }

  .generation-secondary-action,
  .generation-primary-action {
    width: 100%;
  }

  .tutorial-generating-overlay {
    padding: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .generation-loader-ring,
  .generation-loader > span,
  .generation-timeline-node.is-active .generation-node-circle::after,
  .generation-success-icon,
  .generation-success-summary > span,
  .generation-success-track > i,
  .overview-shell {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}

</style>