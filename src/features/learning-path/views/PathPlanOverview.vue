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

    <section v-else-if="isGenerating" class="generating-view">
      <div class="generate-copy">
        <span>AI PATH PLANNING</span>
        <h1>正在生成学习路径</h1>
        <p>后端正在拆解阶段、节点顺序和前置依赖。</p>
      </div>

      <div class="generate-progress">
        <div class="generate-progress-head">
          <span>生成进度</span>
          <strong>{{ generatingProgress }}%</strong>
        </div>
        <div class="generate-track">
          <i :style="{ width: `${generatingProgress}%` }"></i>
        </div>
      </div>

      <transition-group name="log" tag="div" class="generate-log">
        <div
            v-for="(message, index) in generatingMessages"
            :key="`${message}-${index}`"
            class="log-item"
        >
          <i></i>
          <span>{{ message }}</span>
        </div>
      </transition-group>
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
        <div v-if="isGeneratingTutorial" class="tutorial-generating-overlay">
          <section class="tutorial-generating-modal">
            <div class="generate-copy">
              <span>NODE TUTORIAL</span>
              <h1>正在准备节点教程</h1>
              <p>
                如果该节点已有教程，系统会直接进入学习页；如果没有教程，系统会在当前页面生成完成后再进入。
              </p>
            </div>

            <transition-group name="log" tag="div" class="generate-log">
              <div
                  v-for="(msg, index) in tutorialMessages"
                  :key="`${msg}-${index}`"
                  class="log-item"
              >
                <i></i>
                <span>{{ msg }}</span>
              </div>
            </transition-group>
          </section>
        </div>
      </transition>
    </Teleport>
  </main>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const path = ref<PathOverview | null>(null)
const evaluation = ref<PathLearningEvaluationResponse | null>(null)
const activeDetailNode = ref<LearningPathNode | null>(null)

const isGenerating = ref(false)
const generatingProgress = ref(12)
const generatingMessages = ref<string[]>([])
const pathEvents = usePathEvents()
const activeRunId = ref<string | null>(null)

const isGeneratingTutorial = ref(false)
const openingNodeId = ref<number | null>(null)
const tutorialNodeId = ref<number | null>(null)
const tutorialMessages = ref<string[]>([])

const learningStatuses = new Set(['in_progress', 'remediation', 'reinforced'])
const completedStatuses = new Set(['completed', 'completed_with_gaps'])
const enterableStatuses = new Set([
  'available',
  'in_progress',
  'remediation',
  'reinforced',
  'completed',
  'completed_with_gaps',
])

const averageScore = computed(() => {
  const score = evaluation.value?.signal_snapshot?.average_score
  if (score === null || score === undefined) return 0
  return Math.round(score)
})

const activeMinutes = computed(() => {
  return evaluation.value?.signal_snapshot?.active_minutes ?? 0
})

const weakTopics = computed(() => {
  return evaluation.value?.signal_snapshot?.weak_topics ?? []
})

const optimizationTips = computed(() => {
  return evaluation.value?.optimization_tips ?? []
})

const currentNode = computed(() => {
  if (!path.value) return null

  return (
      path.value.nodes.find((node) => node.node_id === path.value?.current_node_key)
      ?? path.value.nodes.find((node) => ['available', 'in_progress', 'remediation', 'reinforced'].includes(node.status))
      ?? null
  )
})

const displayedNode = computed(() => activeDetailNode.value || currentNode.value)

const selectedNodeId = computed(() => displayedNode.value?.id ?? null)

const displayedStageTitle = computed(() => {
  if (!displayedNode.value) return ''
  return stageTitleById(displayedNode.value.stage_id)
})

const displayedPrerequisites = computed(() => {
  return displayedNode.value?.prerequisites?.map(prerequisiteLabel) ?? []
})

const summary = computed(() => {
  const nodes = path.value?.nodes ?? []

  return {
    available: nodes.filter((node) => node.status === 'available').length,
    learning: nodes.filter((node) => learningStatuses.has(node.status)).length,
    completed: nodes.filter((node) => completedStatuses.has(node.status)).length,
    locked: nodes.filter((node) => node.status === 'locked').length,
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

  const sections: StageSection[] = stages.map((stage) => {
    const stageId = getStageId(stage)

    return {
      stageId,
      title: getStageTitle(stage),
      nodes: nodes
          .filter((node) => node.stage_id === stageId)
          .sort((a, b) => (a.priority || 0) - (b.priority || 0)),
    }
  })

  const knownStageIds = new Set(sections.map((section) => section.stageId))
  const orphanNodes = nodes.filter((node) => !knownStageIds.has(node.stage_id))

  if (orphanNodes.length) {
    sections.push({
      stageId: 'unknown-stage',
      title: '未归类节点',
      nodes: orphanNodes.sort((a, b) => (a.priority || 0) - (b.priority || 0)),
    })
  }

  return sections.filter((section) => section.nodes.length > 0)
})

const getStageId = (stage: LearningPathStage) => {
  return stage.stage_id
}

const getStageTitle = (stage: LearningPathStage) => {
  return stage.title
}

const stageTitleById = (stageId: string) => {
  const stage = stageSections.value.find((item) => item.stageId === stageId)
  return stage?.title || stageId
}

const stageCompletedCount = (stage: StageSection) => {
  return stage.nodes.filter((node) => completedStatuses.has(node.status)).length
}

const stageAvailableCount = (stage: StageSection) => {
  return stage.nodes.filter((node) => node.status === 'available').length
}

const stageProgress = (stage: StageSection) => {
  if (!stage.nodes.length) return 0
  return Math.round((stageCompletedCount(stage) / stage.nodes.length) * 100)
}

const difficultyText = (diff?: string | null) => {
  if (diff === 'beginner') return '入门'
  if (diff === 'intermediate') return '进阶'
  if (diff === 'advanced') return '挑战'
  return diff || '常规'
}

const statusText = (status: string) => {
  switch (status) {
    case 'available':
      return '可开始'
    case 'in_progress':
      return '学习中'
    case 'remediation':
      return '补救中'
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

const nodeLearningHint = (node: LearningPathNode) => {
  if (node.status === 'locked') {
    return '该节点暂未解锁。完成前置节点后，系统会自动开放学习入口。'
  }

  if (node.status === 'completed') {
    return '该节点已经完成。点击左侧节点可以直接进入学习页回顾教程、题目和辅助资源。'
  }

  if (node.status === 'completed_with_gaps') {
    return '该节点已完成但仍存在薄弱点。点击左侧节点可以进入学习页查看强化内容并复习错题。'
  }

  if (node.status === 'remediation') {
    return '该节点测验暴露出薄弱点。点击左侧节点后会进入补救学习流程。'
  }

  if (node.status === 'reinforced') {
    return '该节点正在进行强化学习。点击左侧节点后，系统会围绕薄弱点补充更有针对性的学习资源。'
  }

  return '该节点可以开始学习。点击左侧节点后，若已有教程会直接进入学习页；若没有教程，会在当前页面生成完成后进入。'
}

const prerequisiteLabel = (nodeKey: string) => {
  return nodeTitleMap.value.get(nodeKey) || nodeKey
}

const canEnterNode = (node: LearningPathNode) => {
  return enterableStatuses.has(node.status)
}

function unwrapResponseData<T>(response: unknown): T {
  const maybeResponse = response as {
    data?: {
      data?: T
    } | T
  }

  if (
      maybeResponse
      && typeof maybeResponse === 'object'
      && maybeResponse.data
      && typeof maybeResponse.data === 'object'
      && 'data' in maybeResponse.data
  ) {
    return maybeResponse.data.data as T
  }

  if (maybeResponse && 'data' in maybeResponse) {
    return maybeResponse.data as T
  }

  return response as T
}

const previewNode = (node: LearningPathNode) => {
  activeDetailNode.value = node
}

const handleNodeClick = async (node: LearningPathNode) => {
  activeDetailNode.value = node

  if (!canEnterNode(node)) {
    toast.warning('该节点尚未解锁，请先完成前置节点')
    return
  }

  await openNodeLearning(node)
}

const openNodeLearning = async (node: LearningPathNode) => {
  if (openingNodeId.value || isGeneratingTutorial.value) return

  openingNodeId.value = node.id
  tutorialNodeId.value = node.id
  tutorialMessages.value = ['正在检查该节点是否已有教程...']

  try {
    const workspaceResponse = await getLearningNodeWorkspace(node.id)
    const workspace = unwrapResponseData<NodeWorkspaceLike>(workspaceResponse)

    if (workspace.current_tutorial) {
      await startLearning(node.id)
      router.push(`/path-planner/node/${node.id}`)
      return
    }

    await generateNodeTutorialAndEnter(node)
  } catch (error) {
    toast.error(getErrorMessage(error, '打开节点学习页失败'))
  } finally {
    if (!isGeneratingTutorial.value) {
      openingNodeId.value = null
      tutorialNodeId.value = null
      tutorialMessages.value = []
    }
  }
}

const generateNodeTutorialAndEnter = async (node: LearningPathNode) => {
  isGeneratingTutorial.value = true
  tutorialNodeId.value = node.id
  tutorialMessages.value = [
    '当前节点还没有教程，正在启动教程生成流程...',
    '正在读取路径目标、节点信息和学习画像...',
  ]

  const logs = [
    '正在生成节点主教程结构...',
    '正在补充核心概念、例子和易错点...',
    '正在整理教程正文与知识点...',
    '正在保存教程并准备进入学习页...',
  ]

  let logIndex = 0
  const interval = window.setInterval(() => {
    if (logIndex < logs.length) {
      tutorialMessages.value.push(logs[logIndex]!)

      if (tutorialMessages.value.length > 5) {
        tutorialMessages.value.shift()
      }

      logIndex += 1
    }
  }, 1800)

  try {
    await startLearning(node.id)
    await generateTutorial(node.id)
    router.push(`/path-planner/node/${node.id}`)
  } catch (error) {
    toast.error(getErrorMessage(error, '教程生成失败'))
  } finally {
    window.clearInterval(interval)
    isGeneratingTutorial.value = false
    openingNodeId.value = null
    tutorialNodeId.value = null
    tutorialMessages.value = []
  }
}

const stopSSE = () => {
  pathEvents.close()
}

const handlePathEvent = (event: PathEvent) => {
  if (typeof event.progress === 'number') {
    generatingProgress.value = Math.max(generatingProgress.value, Math.min(event.progress, 100))
  }

  const message = event.message
  if (message && !generatingMessages.value.includes(message)) {
    generatingMessages.value.push(message)

    if (generatingMessages.value.length > 6) {
      generatingMessages.value.shift()
    }
  }
}

const startSSE = (pathId: number, runId: string) => {
  stopSSE()
  pathEvents.connect(pathId, runId, {
    onEvent: handlePathEvent,
    onCompleted: () => {
      generatingProgress.value = 100
      window.setTimeout(() => {
        loadPath()
      }, 700)
    },
    onFailed: (error) => {
      toast.error(error.message || '路径规划失败')
      isGenerating.value = false
      loadPath()
    },
  })
}

const loadEvaluation = async (pathId: number) => {
  try {
    const response = await getLearningEvaluation(pathId)
    evaluation.value = unwrapResponseData<PathLearningEvaluationResponse>(response)
  } catch (error) {
    console.error('Failed to load evaluation', error)
    evaluation.value = null
  }
}

const loadPath = async () => {
  const rawId = String(route.params.id || '')

  if (rawId === 'new') {
    isGenerating.value = true
    loading.value = false
    path.value = null
    evaluation.value = null
    activeDetailNode.value = null
    generatingProgress.value = 12

    const newGoal = route.query.goal as string
    const newTopic = (route.query.topic as string) || newGoal

    if (!newGoal) {
      router.replace('/path-planner')
      return
    }

    if (generatingMessages.value.length === 0) {
      generatingMessages.value = [
        '正在创建路径任务...',
        '正在读取学习目标与用户画像...',
      ]
    }

    try {
      let parsedKnowledge: string[] = []

      if (route.query.current_knowledge) {
        try {
          parsedKnowledge = JSON.parse(route.query.current_knowledge as string)
        } catch (error) {
          console.warn('解析已掌握知识点失败:', error)
        }
      }

      const preferences = {
        difficulty: (route.query.difficulty as string) || 'intermediate',
        use_profile: route.query.use_profile !== 'false',
      }

      const response = await createLearningPath({
        goal: newGoal,
        topic: newTopic,
        current_knowledge: parsedKnowledge,
        preferences,
      })

      const newPath = unwrapResponseData<PathOverview & { run_id?: string }>(response)
      activeRunId.value = newPath.run_id || null

      router.replace({
        path: `/path-planner/overview/${newPath.id}`,
        query: newPath.run_id ? { run_id: newPath.run_id } : {},
      })
    } catch (error) {
      toast.error(getErrorMessage(error, '路径规划任务创建失败'))
      isGenerating.value = false
      router.replace('/path-planner')
    }

    return
  }

  loading.value = true

  try {
    const paramId = Number(rawId || 0)
    const shouldLoadSpecificPath = Boolean(rawId && rawId !== 'latest' && Number.isFinite(paramId) && paramId > 0)

    let currentPathId = 0

    if (shouldLoadSpecificPath) {
      const response = await getLearningPathById(paramId)
      const loadedPath = unwrapResponseData<PathOverview>(response)
      path.value = loadedPath
      currentPathId = loadedPath.id
    } else {
      const response = await getCurrentLearningPath()
      const current = unwrapResponseData<PathOverview | null>(response)

      if (!current) {
        path.value = null
        evaluation.value = null
        return
      }

      path.value = current
      currentPathId = current.id

      if (rawId === 'latest') {
        router.replace(`/path-planner/overview/${current.id}`)
      }
    }

    activeDetailNode.value = null

    const loaded = path.value
    if (!loaded) return

    if (loaded.status === 'generating') {
      isGenerating.value = true
      generatingProgress.value = Math.max(generatingProgress.value, 18)

      if (generatingMessages.value.length === 0) {
        generatingMessages.value = [
          '已找到正在生成的路径任务...',
          '正在连接后端 SSE 进度流...',
        ]
      }

      activeRunId.value = String(route.query.run_id || activeRunId.value || '') || null

      if (activeRunId.value && currentPathId) {
        startSSE(currentPathId, activeRunId.value)
      }
    } else {
      isGenerating.value = false
      generatingProgress.value = 100
      stopSSE()

      if (currentPathId > 0) {
        await loadEvaluation(currentPathId)
      }
    }
  } catch (error) {
    toast.error(getErrorMessage(error, '加载学习路径失败'))
  } finally {
    loading.value = false
  }
}

watch(
    () => route.params.id,
    (newId, oldId) => {
      stopSSE()

      if (oldId === 'new' && newId && newId !== 'new') {
        isGenerating.value = true
      } else {
        generatingMessages.value = []
        generatingProgress.value = 12
        isGenerating.value = false
      }

      activeDetailNode.value = null
      loadPath()
    },
)

onActivated(() => {
  if (isGenerating.value && activeRunId.value && path.value?.id) {
    startSSE(path.value.id, activeRunId.value)
  }
})

onBeforeUnmount(() => {
  stopSSE()
})

onMounted(loadPath)
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

.map-node.in_progress .checkpoint i,
.map-node.remediation .checkpoint i,
.map-node.reinforced .checkpoint i {
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
</style>