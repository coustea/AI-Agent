<template>
  <main class="path-dashboard">
    <BaseCard v-if="loading" class="state-card">
      <div class="state-spinner"></div>
      <p>正在加载学习路径...</p>
    </BaseCard>

    <BaseCard v-else-if="!path && !isGenerating" class="state-card empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 6.5h6l2 2h8v9.5a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.5a2 2 0 0 1 2-2Z" />
        </svg>
      </div>
      <h2>还没有可用的学习路径</h2>
      <p>输入学习目标后，系统会根据你的画像生成阶段化学习路径。</p>
      <BaseButton variant="primary" @click="router.push('/path-planner')">创建学习路径</BaseButton>
    </BaseCard>

    <section v-else-if="isGenerating" class="generating-view">
      <div class="generate-panel">
        <div class="generate-loader">
          <span></span>
          <span></span>
          <span></span>
        </div>

        <div class="generate-copy">
          <p>AI Path Planning</p>
          <h1>正在生成学习路径</h1>
          <span>后端正在拆解阶段、节点顺序和前置依赖。</span>
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
          <div v-for="(message, index) in generatingMessages" :key="`${message}-${index}`" class="log-item">
            <i></i>
            <span>{{ message }}</span>
          </div>
        </transition-group>
      </div>
    </section>

    <div v-else-if="path" class="overview-layout">
      <header class="compact-header">
        <div class="title-area">
          <div class="route-label">
            <span></span>
            个性化学习路径
          </div>
          <h1>{{ path.title }}</h1>
          <p>{{ path.goal }}</p>
        </div>

        <div class="header-right">
          <div class="progress-mini">
            <strong>{{ path.overall_progress }}%</strong>
            <span>总进度</span>
          </div>

          <div class="header-meta">
            <span>主题：{{ path.topic || path.title }}</span>
            <span>{{ path.stages.length }} 个阶段</span>
            <span>{{ path.nodes.length }} 个节点</span>
            <span>当前：{{ currentNode?.title || '暂无可学习节点' }}</span>
          </div>

          <div class="header-actions">
            <BaseButton variant="secondary" @click="router.push('/path-planner/history')">路径历史</BaseButton>
            <BaseButton variant="secondary" @click="router.push('/path-resource-history')">资源记录</BaseButton>
            <BaseButton variant="primary" @click="router.push('/path-planner')">重新规划</BaseButton>
          </div>
        </div>
      </header>

      <section class="main-grid">
        <section class="roadmap-panel">
          <div class="roadmap-head">
            <div class="roadmap-title">
              <span class="section-kicker">Learning Roadmap</span>
              <h2>学习路径规划图</h2>
              <p>点击可学习节点直接进入学习空间；悬浮或点击锁定节点可在右侧查看节点详情。</p>
            </div>

            <div class="mini-stats">
              <article>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3 20 7.5v9L12 21l-8-4.5v-9L12 3Zm0 2.2L6 8.6v6.8l6 3.4 6-3.4V8.6l-6-3.4Z" />
                </svg>
                <span>可学习</span>
                <strong>{{ summary.available }}</strong>
              </article>

              <article>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-2.35-5.65L15 9h7V2l-2.9 2.9A9.96 9.96 0 0 0 12 2Z" />
                </svg>
                <span>学习中</span>
                <strong>{{ summary.learning }}</strong>
              </article>

              <article>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m9.2 16.6-4.1-4.1-1.4 1.4 5.5 5.5L21 7.6l-1.4-1.4L9.2 16.6Z" />
                </svg>
                <span>已完成</span>
                <strong>{{ summary.completed }}</strong>
              </article>

              <article>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M17 9V7A5 5 0 0 0 7 7v2H5v12h14V9h-2ZM9 7a3 3 0 0 1 6 0v2H9V7Zm8 12H7v-8h10v8Z" />
                </svg>
                <span>未解锁</span>
                <strong>{{ summary.locked }}</strong>
              </article>
            </div>
          </div>

          <div class="roadmap-canvas">
            <article
              v-for="(stage, stageIndex) in stageSections"
              :key="stage.stageId"
              class="stage-track"
            >
              <div class="stage-marker">
                <div class="stage-number">{{ stageIndex + 1 }}</div>
                <div class="stage-line"></div>
              </div>

              <div class="stage-main">
                <header class="stage-title-row">
                  <div>
                    <span>阶段 {{ stageIndex + 1 }}</span>
                    <h3>{{ stage.title }}</h3>
                  </div>
                  <strong>{{ stage.nodes.length }} 个节点</strong>
                </header>

                <div class="path-node-row">
                  <button
                    v-for="(node, nodeIndex) in stage.nodes"
                    :key="node.id"
                    class="path-node"
                    :class="[
                      node.status,
                      {
                        selected: selectedNodeId === node.id,
                        current: currentNode?.id === node.id,
                        enterable: canEnterNode(node),
                      },
                    ]"
                    type="button"
                    @mouseenter="previewNode(node)"
                    @focus="previewNode(node)"
                    @click="handleNodeClick(node)"
                  >
                    <span v-if="nodeIndex !== 0" class="node-connector"></span>

                    <div class="node-icon-wrap">
                      <svg v-if="node.status === 'locked'" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M17 9V7A5 5 0 0 0 7 7v2H5v12h14V9h-2ZM9 7a3 3 0 0 1 6 0v2H9V7Zm8 12H7v-8h10v8Z" />
                      </svg>
                      <svg v-else-if="completedStatuses.has(node.status)" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="m9.2 16.6-4.1-4.1-1.4 1.4 5.5 5.5L21 7.6l-1.4-1.4L9.2 16.6Z" />
                      </svg>
                      <svg v-else-if="learningStatuses.has(node.status)" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 2a10 10 0 1 0 10 10h-2a8 8 0 1 1-2.35-5.65L15 9h7V2l-2.9 2.9A9.96 9.96 0 0 0 12 2Z" />
                      </svg>
                      <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M12 3 20 7.5v9L12 21l-8-4.5v-9L12 3Zm0 2.2L6 8.6v6.8l6 3.4 6-3.4V8.6l-6-3.4Z" />
                      </svg>
                    </div>

                    <div class="path-node-content">
                      <div class="node-badges">
                        <span class="status-badge" :class="node.status">{{ statusText(node.status) }}</span>
                        <span class="difficulty-badge" :class="node.difficulty || 'normal'">
                          {{ difficultyText(node.difficulty) }}
                        </span>
                      </div>

                      <h4>{{ node.title }}</h4>

                      <div class="node-data">
                        <span>P{{ node.priority }}</span>
                        <span>{{ node.attempt_count || 0 }} 次测验</span>
                        <span>{{ node.prerequisites?.length || 0 }} 个前置</span>
                      </div>

                      <div v-if="node.prerequisites?.length" class="node-prerequisites">
                        <label>前置</label>
                        <em v-for="item in node.prerequisites.slice(0, 2)" :key="item">
                          {{ prerequisiteLabel(item) }}
                        </em>
                        <em v-if="node.prerequisites.length > 2">+{{ node.prerequisites.length - 2 }}</em>
                      </div>

                      <p>{{ canEnterNode(node) ? '点击进入节点学习空间' : nodeActionText(node.status) }}</p>
                    </div>
                  </button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <aside class="learning-panel">
          <section v-if="displayedNode" class="current-card">
            <div class="current-card-head">
              <span>{{ activeDetailNode ? '选中节点' : '当前推荐节点' }}</span>
              <strong class="status-badge" :class="displayedNode.status">
                {{ statusText(displayedNode.status) }}
              </strong>
            </div>

            <h2>{{ displayedNode.title }}</h2>
            <p>{{ nodeLearningHint(displayedNode) }}</p>

            <div class="current-grid">
              <div>
                <label>所属阶段</label>
                <strong>{{ stageTitleById(displayedNode.stage_id) }}</strong>
              </div>
              <div>
                <label>难度</label>
                <strong>{{ difficultyText(displayedNode.difficulty) }}</strong>
              </div>
              <div>
                <label>优先级</label>
                <strong>P{{ displayedNode.priority }}</strong>
              </div>
              <div>
                <label>测验轮次</label>
                <strong>{{ displayedNode.attempt_count || 0 }}</strong>
              </div>
            </div>

            <div class="dependency-box">
              <div class="box-title">前置依赖</div>

              <div v-if="displayedNode.prerequisites?.length" class="dependency-list">
                <span v-for="item in displayedNode.prerequisites" :key="item">
                  {{ prerequisiteLabel(item) }}
                </span>
              </div>

              <p v-else>该节点没有前置依赖，可以直接开始学习。</p>
            </div>

            <div class="learn-flow">
              <div>
                <span>1</span>
                <p>进入节点学习空间</p>
              </div>
              <div>
                <span>2</span>
                <p>懒加载主教程</p>
              </div>
              <div>
                <span>3</span>
                <p>生成节点测验</p>
              </div>
              <div>
                <span>4</span>
                <p>按需生成导图、代码、PPT、阅读资源</p>
              </div>
            </div>

            <div class="side-tip">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M11 17h2v-6h-2v6Zm0-8h2V7h-2v2Zm1 13a10 10 0 1 1 0-20 10 10 0 0 1 0 20Zm0-2a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z" />
              </svg>
              <span>{{ canEnterNode(displayedNode) ? '点击左侧路径节点即可进入学习。' : '该节点需要完成前置依赖后才能进入学习。' }}</span>
            </div>
          </section>

          <section v-else class="current-card empty-current">
            <h2>请选择一个路径节点</h2>
            <p>点击左侧任意节点后，这里会展示节点状态、前置依赖和学习说明。</p>
          </section>

          <section class="evaluation-card">
            <div class="evaluation-head">
              <span>Learning Evaluation</span>
              <h2>学习效果评估</h2>
            </div>
            <EvaluationBanner :evaluation="evaluation" />
          </section>
        </aside>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import BaseCard from '@/shared/ui/BaseCard.vue'
import BaseButton from '@/shared/ui/BaseButton.vue'
import EvaluationBanner from '@/features/learning-path/components/EvaluationBanner.vue'

import {
  createLearningPath,
  getCurrentLearningPath,
  getLearningEvaluation,
  getLearningPathById,
} from '@/features/learning-path/api/path'
import type {
  LearningPathNode,
  LearningPathOverview,
  PathLearningEvaluationResponse,
} from '@/features/learning-path/model/path'
import { getErrorMessage } from '@/shared/api/http'
import type { AgentEvent } from '@/shared/agent-events/model'
import { useAgentRun } from '@/shared/agent-events/useAgentRun'

type StageLike = {
  stage_id?: string
  id?: string
  title?: string
  name?: string
}

type StageSection = {
  stageId: string
  title: string
  nodes: LearningPathNode[]
}

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const path = ref<LearningPathOverview | null>(null)
const evaluation = ref<PathLearningEvaluationResponse | null>(null)
const activeDetailNode = ref<LearningPathNode | null>(null)

const isGenerating = ref(false)
const generatingProgress = ref(12)
const generatingMessages = ref<string[]>([])
const agentRun = useAgentRun()
const activeRunId = ref<string | null>(null)

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

const currentNode = computed(() => {
  if (!path.value) return null

  return path.value.nodes.find((node) => node.node_id === path.value?.current_node_key)
    ?? path.value.nodes.find((node) => ['available', 'in_progress', 'remediation', 'reinforced'].includes(node.status))
    ?? null
})

const displayedNode = computed(() => activeDetailNode.value || currentNode.value)

const selectedNodeId = computed(() => displayedNode.value?.id ?? null)

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

  const stages = (path.value.stages ?? []) as StageLike[]
  const nodes = path.value.nodes ?? []

  const sections: StageSection[] = stages.map((stage, index) => {
    const stageId = getStageId(stage, index)

    return {
      stageId,
      title: getStageTitle(stage, index),
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

const getStageId = (stage: StageLike, index: number) => {
  return String(stage.stage_id || stage.id || `stage-${index + 1}`)
}

const getStageTitle = (stage: StageLike, index: number) => {
  return String(stage.title || stage.name || `阶段 ${index + 1}`)
}

const stageTitleById = (stageId: string) => {
  const stage = stageSections.value.find((item) => item.stageId === stageId)
  return stage?.title || stageId
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

const nodeActionText = (status: string) => {
  switch (status) {
    case 'available':
      return '可以开始学习'
    case 'in_progress':
      return '继续学习当前节点'
    case 'remediation':
      return '需要专项补救'
    case 'reinforced':
      return '进入强化学习'
    case 'completed':
      return '可回顾复习'
    case 'completed_with_gaps':
      return '建议查漏补缺'
    case 'locked':
      return '前置节点未完成'
    default:
      return '查看节点'
  }
}

const nodeLearningHint = (node: LearningPathNode) => {
  if (node.status === 'locked') {
    return '该节点暂未解锁。完成前置节点后，系统会自动开放学习入口。'
  }

  if (node.status === 'completed') {
    return '该节点已经完成，可以重新进入学习空间回顾教程、题目和辅助资源。'
  }

  if (node.status === 'completed_with_gaps') {
    return '该节点已完成但仍存在薄弱点，建议进入学习空间查看强化内容并复习错题。'
  }

  if (node.status === 'remediation') {
    return '该节点测验暴露出薄弱点，进入学习空间后会围绕错题知识点进行补救学习。'
  }

  if (node.status === 'reinforced') {
    return '该节点正在进行强化学习。系统会围绕薄弱点补充更有针对性的学习资源。'
  }

  return '进入学习空间后，后端会按需生成主教程、节点测验和辅助学习资源。'
}

const prerequisiteLabel = (nodeKey: string) => {
  return nodeTitleMap.value.get(nodeKey) || nodeKey
}

const canEnterNode = (node: LearningPathNode) => {
  return enterableStatuses.has(node.status)
}

const previewNode = (node: LearningPathNode) => {
  activeDetailNode.value = node
}

const handleNodeClick = (node: LearningPathNode) => {
  activeDetailNode.value = node

  if (!canEnterNode(node)) {
    ElMessage.info('该节点尚未解锁，请先完成前置节点')
    return
  }

  router.push(`/path-planner/node/${node.id}`)
}

const stopSSE = () => {
  agentRun.close()
}

const handlePathEvent = (event: AgentEvent) => {
    if (typeof event.progress === 'number') {
      generatingProgress.value = Math.max(generatingProgress.value, Math.min(event.progress, 100))
    }

    const message = event.summary || event.title
    if (message && !generatingMessages.value.includes(message)) {
      generatingMessages.value.push(message)

      if (generatingMessages.value.length > 6) {
        generatingMessages.value.shift()
      }
    }

}

const startSSE = (runId: string) => {
  stopSSE()
  agentRun.connect(runId, {
    onEvent: handlePathEvent,
    onCompleted: () => {
      generatingProgress.value = 100
      setTimeout(() => {
        loadPath()
      }, 700)
    },
    onFailed: (error) => {
      ElMessage.error(error.message || '路径规划失败')
      isGenerating.value = false
      loadPath()
    },
    onConnectionError: () => {
      if (isGenerating.value && !generatingMessages.value.includes('正在等待后端继续推送路径生成状态...')) {
        generatingMessages.value.push('正在等待后端继续推送路径生成状态...')
      }
    },
  })
}

const loadEvaluation = async (pathId: number) => {
  try {
    const res = await getLearningEvaluation(pathId)
    evaluation.value = res.data.data
  } catch (error) {
    console.error('Failed to load evaluation', error)
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
      const res = await createLearningPath({ goal: newGoal, topic: newGoal })
      const newPath = res.data.data
      activeRunId.value = newPath.run_id
      router.replace({
        path: `/path-planner/overview/${newPath.id}`,
        query: { run_id: newPath.run_id },
      })
    } catch (error) {
      ElMessage.error(getErrorMessage(error, '路径规划任务创建失败'))
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
      const res = await getLearningPathById(paramId)
      path.value = res.data.data
      currentPathId = path.value.id
    } else {
      const res = await getCurrentLearningPath()
      const current = res.data.data

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

    if (path.value.status === 'generating') {
      isGenerating.value = true
      generatingProgress.value = Math.max(generatingProgress.value, 18)

      if (generatingMessages.value.length === 0) {
        generatingMessages.value = [
          '已找到正在生成的路径任务...',
          '正在连接后端 SSE 进度流...',
        ]
      }

      activeRunId.value = String(route.query.run_id || activeRunId.value || '') || null
      if (activeRunId.value) startSSE(activeRunId.value)
    } else {
      isGenerating.value = false
      generatingProgress.value = 100
      stopSSE()

      if (currentPathId > 0) {
        await loadEvaluation(currentPathId)
      }
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载学习路径失败'))
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
  if (isGenerating.value && activeRunId.value) {
    startSSE(activeRunId.value)
  }
})

onBeforeUnmount(() => {
  stopSSE()
})

onMounted(loadPath)
</script>

<style scoped>
.path-dashboard {
  --lp-primary: #4f46e5;
  --lp-primary-dark: #3730a3;
  --lp-primary-soft: #eef2ff;
  --lp-blue: #0ea5e9;
  --lp-cyan: #06b6d4;
  --lp-green: #10b981;
  --lp-slate: #64748b;
  --lp-muted: #94a3b8;
  --lp-border: #e2e8f0;
  --lp-border-strong: #c7d2fe;
  --lp-card: #ffffff;
  --lp-text: #0f172a;
  --lp-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);

  min-height: calc(100vh - 64px);
  padding: 16px;
  background:
    radial-gradient(circle at 8% 0%, rgba(79, 70, 229, 0.08), transparent 30%),
    radial-gradient(circle at 92% 2%, rgba(14, 165, 233, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  color: var(--lp-text);
}

.path-dashboard svg {
  width: 1em;
  height: 1em;
  fill: currentColor;
}

.state-card {
  max-width: 720px;
  margin: 80px auto 0;
  padding: 42px;
  text-align: center;
  border-radius: 24px;
}

.state-spinner {
  width: 34px;
  height: 34px;
  margin: 0 auto 14px;
  border: 4px solid #e0e7ff;
  border-top-color: var(--lp-primary);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.state-card p {
  margin: 0;
  color: var(--lp-slate);
}

.empty-state h2 {
  margin: 16px 0 8px;
  font-size: 1.35rem;
}

.empty-state :deep(.base-button) {
  margin-top: 22px;
}

.empty-icon {
  width: 82px;
  height: 82px;
  margin: 0 auto;
  display: grid;
  place-items: center;
  border-radius: 24px;
  color: var(--lp-primary-dark);
  font-size: 34px;
  background: linear-gradient(135deg, #eef2ff, #dbeafe);
  border: 1px solid var(--lp-border-strong);
}

.generating-view {
  min-height: calc(100vh - 110px);
  display: grid;
  place-items: center;
}

.generate-panel {
  width: min(620px, 100%);
  padding: 34px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--lp-border-strong);
  box-shadow: var(--lp-shadow);
  backdrop-filter: blur(16px);
  text-align: center;
}

.generate-loader {
  width: 84px;
  height: 84px;
  margin: 0 auto 22px;
  position: relative;
  display: grid;
  place-items: center;
}

.generate-loader::before {
  content: "";
  width: 42px;
  height: 42px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--lp-primary), var(--lp-blue));
  box-shadow: 0 20px 40px rgba(79, 70, 229, 0.25);
  animation: floatBlock 2.2s ease-in-out infinite;
}

.generate-loader span {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(79, 70, 229, 0.22);
  border-radius: 50%;
  animation: pulseRing 2.6s ease-out infinite;
}

.generate-loader span:nth-child(2) {
  inset: 14px;
  animation-delay: 0.35s;
}

.generate-loader span:nth-child(3) {
  inset: 28px;
  animation-delay: 0.7s;
}

.generate-copy p {
  margin: 0;
  color: var(--lp-primary);
  font-size: 0.75rem;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.generate-copy h1 {
  margin: 10px 0 8px;
  font-size: 2rem;
  letter-spacing: -0.04em;
}

.generate-copy span {
  color: var(--lp-slate);
  font-size: 0.95rem;
}

.generate-progress {
  margin-top: 24px;
  padding: 16px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid var(--lp-border);
}

.generate-progress-head {
  display: flex;
  justify-content: space-between;
  color: var(--lp-slate);
  font-size: 0.86rem;
  margin-bottom: 10px;
}

.generate-progress-head strong {
  color: var(--lp-primary-dark);
}

.generate-track {
  height: 9px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.generate-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--lp-primary), var(--lp-blue));
  transition: width 0.35s ease;
}

.generate-log {
  margin-top: 18px;
  display: grid;
  gap: 10px;
  text-align: left;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 9px 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid var(--lp-border);
  color: #334155;
  font-size: 0.88rem;
}

.log-item i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--lp-primary);
  box-shadow: 0 0 0 5px rgba(79, 70, 229, 0.1);
  flex: 0 0 auto;
}

.overview-layout {
  width: min(1720px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 14px;
}

.compact-header {
  min-height: 96px;
  padding: 16px 18px;
  display: grid;
  grid-template-columns: minmax(340px, 1fr) minmax(520px, 1.5fr);
  gap: 18px;
  align-items: center;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(199, 210, 254, 0.75);
  border-radius: 22px;
  box-shadow: var(--lp-shadow);
  backdrop-filter: blur(16px);
}

.title-area {
  min-width: 0;
}

.route-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--lp-primary);
  font-size: 0.76rem;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.route-label span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--lp-green);
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.12);
}

.title-area h1 {
  margin: 8px 0 6px;
  font-size: clamp(1.35rem, 2.2vw, 2.1rem);
  line-height: 1.14;
  letter-spacing: -0.04em;
  color: var(--lp-text);
}

.title-area p {
  margin: 0;
  color: var(--lp-slate);
  line-height: 1.45;
  font-size: 0.9rem;
}

.header-right {
  min-width: 0;
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.progress-mini {
  width: 78px;
  height: 78px;
  border-radius: 22px;
  display: grid;
  place-items: center;
  align-content: center;
  background: linear-gradient(135deg, #eef2ff, #dbeafe);
  border: 1px solid var(--lp-border-strong);
}

.progress-mini strong {
  color: var(--lp-primary-dark);
  font-size: 1.45rem;
  line-height: 1;
}

.progress-mini span {
  margin-top: 5px;
  color: var(--lp-slate);
  font-size: 0.7rem;
  font-weight: 800;
}

.header-meta {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.header-meta span {
  max-width: 250px;
  height: 29px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid var(--lp-border);
  color: #475569;
  font-size: 0.78rem;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 390px;
  gap: 14px;
  align-items: start;
}

.roadmap-panel,
.current-card,
.evaluation-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--lp-border);
  border-radius: 24px;
  box-shadow: var(--lp-shadow);
  backdrop-filter: blur(16px);
}

.roadmap-panel {
  padding: 18px;
  min-height: 720px;
}

.roadmap-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--lp-border);
}

.roadmap-title {
  min-width: 0;
}

.section-kicker,
.evaluation-head span,
.current-card-head > span {
  color: var(--lp-primary);
  font-size: 0.74rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.roadmap-head h2,
.evaluation-head h2 {
  margin: 5px 0 4px;
  font-size: 1.25rem;
  letter-spacing: -0.03em;
}

.roadmap-head p {
  margin: 0;
  color: var(--lp-slate);
  font-size: 0.88rem;
}

.mini-stats {
  display: grid;
  grid-template-columns: repeat(4, 112px);
  gap: 8px;
}

.mini-stats article {
  height: 64px;
  padding: 10px;
  display: grid;
  grid-template-columns: 28px 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 2px 8px;
  align-items: center;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid var(--lp-border);
}

.mini-stats svg {
  grid-row: 1 / 3;
  font-size: 22px;
  color: var(--lp-primary);
}

.mini-stats span {
  color: var(--lp-slate);
  font-size: 0.72rem;
  font-weight: 900;
}

.mini-stats strong {
  color: var(--lp-text);
  font-size: 1.05rem;
  line-height: 1;
}

.roadmap-canvas {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.stage-track {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 14px;
}

.stage-marker {
  position: relative;
  display: flex;
  justify-content: center;
}

.stage-number {
  width: 40px;
  height: 40px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-weight: 900;
  background: linear-gradient(135deg, var(--lp-primary), var(--lp-blue));
  box-shadow: 0 12px 28px rgba(79, 70, 229, 0.2);
  z-index: 1;
}

.stage-line {
  position: absolute;
  top: 46px;
  bottom: -10px;
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(79, 70, 229, 0.36), rgba(79, 70, 229, 0.04));
}

.stage-track:last-child .stage-line {
  display: none;
}

.stage-main {
  padding-bottom: 24px;
}

.stage-title-row {
  min-height: 40px;
  margin-bottom: 12px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.stage-title-row span {
  color: var(--lp-primary);
  font-size: 0.75rem;
  font-weight: 900;
}

.stage-title-row h3 {
  margin: 3px 0 0;
  font-size: 1.06rem;
  color: var(--lp-text);
}

.stage-title-row strong {
  color: var(--lp-slate);
  font-size: 0.78rem;
  white-space: nowrap;
}

.path-node-row {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(285px, 1fr));
  gap: 16px;
}

.path-node {
  position: relative;
  appearance: none;
  width: 100%;
  min-height: 176px;
  padding: 14px;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  gap: 12px;
  border: 1px solid var(--lp-border);
  border-radius: 22px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.path-node:hover {
  transform: translateY(-3px);
  border-color: rgba(79, 70, 229, 0.42);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
}

.path-node.selected {
  border-color: rgba(79, 70, 229, 0.78);
  box-shadow: 0 16px 38px rgba(79, 70, 229, 0.15);
}

.path-node.current {
  background:
    linear-gradient(#ffffff, #ffffff) padding-box,
    linear-gradient(135deg, rgba(79, 70, 229, 0.95), rgba(14, 165, 233, 0.82)) border-box;
  border-color: transparent;
}

.path-node.locked {
  background: #f8fafc;
}

.path-node.enterable p {
  color: var(--lp-primary);
}

.node-connector {
  position: absolute;
  left: -17px;
  top: 50%;
  width: 16px;
  height: 2px;
  transform: translateY(-50%);
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.22), rgba(79, 70, 229, 0.52));
}

.node-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-size: 24px;
  background: linear-gradient(135deg, var(--lp-primary), #818cf8);
  box-shadow: 0 12px 24px rgba(79, 70, 229, 0.18);
}

.path-node.in_progress .node-icon-wrap,
.path-node.remediation .node-icon-wrap,
.path-node.reinforced .node-icon-wrap {
  background: linear-gradient(135deg, var(--lp-blue), var(--lp-cyan));
}

.path-node.completed .node-icon-wrap,
.path-node.completed_with_gaps .node-icon-wrap {
  background: linear-gradient(135deg, var(--lp-green), #34d399);
}

.path-node.locked .node-icon-wrap {
  color: #64748b;
  background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
  box-shadow: none;
}

.path-node-content {
  min-width: 0;
}

.node-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 9px;
}

.status-badge,
.difficulty-badge {
  min-height: 23px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 900;
  white-space: nowrap;
}

.status-badge.available {
  color: var(--lp-primary-dark);
  background: var(--lp-primary-soft);
}

.status-badge.in_progress,
.status-badge.remediation,
.status-badge.reinforced {
  color: #075985;
  background: #e0f2fe;
}

.status-badge.completed,
.status-badge.completed_with_gaps {
  color: #047857;
  background: #d1fae5;
}

.status-badge.locked {
  color: #475569;
  background: #e2e8f0;
}

.difficulty-badge.beginner {
  color: #047857;
  background: #ecfdf5;
}

.difficulty-badge.intermediate {
  color: #075985;
  background: #e0f2fe;
}

.difficulty-badge.advanced {
  color: #6d28d9;
  background: #f3e8ff;
}

.difficulty-badge.normal {
  color: #475569;
  background: #f1f5f9;
}

.path-node h4 {
  min-height: 45px;
  margin: 0;
  color: var(--lp-text);
  font-size: 1rem;
  line-height: 1.42;
}

.node-data {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.node-data span {
  min-height: 23px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid var(--lp-border);
  color: var(--lp-slate);
  font-size: 0.72rem;
  font-weight: 800;
}

.node-prerequisites {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.node-prerequisites label {
  color: var(--lp-muted);
  font-size: 0.72rem;
  font-weight: 900;
}

.node-prerequisites em {
  max-width: 130px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.72rem;
  font-style: normal;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.path-node p {
  margin: 12px 0 0;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
  color: var(--lp-slate);
  font-size: 0.78rem;
  font-weight: 900;
}

.learning-panel {
  display: grid;
  gap: 14px;
  position: sticky;
  top: 16px;
  align-self: start;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(79, 70, 229, 0.28) transparent;
}

.learning-panel::-webkit-scrollbar {
  width: 6px;
}

.learning-panel::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(79, 70, 229, 0.28);
}

.learning-panel::-webkit-scrollbar-track {
  background: transparent;
}

.current-card,
.evaluation-card {
  padding: 18px;
}

.current-card-head {
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.current-card h2 {
  margin: 0 0 8px;
  color: var(--lp-text);
  font-size: 1.2rem;
  line-height: 1.35;
  letter-spacing: -0.03em;
}

.current-card > p {
  margin: 0;
  color: var(--lp-slate);
  font-size: 0.88rem;
  line-height: 1.65;
}

.current-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.current-grid div {
  padding: 11px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--lp-border);
}

.current-grid label {
  display: block;
  margin-bottom: 4px;
  color: var(--lp-muted);
  font-size: 0.7rem;
  font-weight: 900;
}

.current-grid strong {
  color: var(--lp-text);
  font-size: 0.82rem;
}

.dependency-box {
  margin-top: 16px;
  padding: 13px;
  border-radius: 16px;
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border: 1px solid rgba(199, 210, 254, 0.75);
}

.box-title {
  margin-bottom: 9px;
  color: #334155;
  font-size: 0.8rem;
  font-weight: 900;
}

.dependency-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.dependency-list span {
  padding: 5px 8px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid var(--lp-border);
  color: #475569;
  font-size: 0.76rem;
  font-weight: 800;
}

.dependency-box p {
  margin: 0;
  color: var(--lp-slate);
  font-size: 0.82rem;
  line-height: 1.55;
}

.learn-flow {
  margin-top: 16px;
  display: grid;
  gap: 8px;
}

.learn-flow div {
  padding: 9px;
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid var(--lp-border);
}

.learn-flow span {
  width: 26px;
  height: 26px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 900;
  background: linear-gradient(135deg, var(--lp-primary), var(--lp-blue));
}

.learn-flow p {
  margin: 0;
  color: #475569;
  font-size: 0.8rem;
  font-weight: 800;
}

.side-tip {
  margin-top: 16px;
  padding: 12px;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  border-radius: 14px;
  color: #3730a3;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
}

.side-tip svg {
  font-size: 20px;
}

.side-tip span {
  font-size: 0.82rem;
  font-weight: 800;
  line-height: 1.5;
}

.empty-current {
  min-height: 240px;
  display: grid;
  align-content: center;
}

.evaluation-head {
  margin-bottom: 12px;
}

.evaluation-card :deep(.evaluation-banner),
.evaluation-card :deep(.dashboard-banner) {
  margin: 0;
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

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulseRing {
  0% {
    opacity: 0.85;
    transform: scale(0.72);
  }

  100% {
    opacity: 0;
    transform: scale(1.18);
  }
}

@keyframes floatBlock {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }

  50% {
    transform: translateY(-7px) rotate(6deg);
  }
}

@media (max-width: 1320px) {
  .compact-header,
  .main-grid {
    grid-template-columns: 1fr;
  }

  .header-right {
    grid-template-columns: 82px minmax(0, 1fr);
  }

  .header-actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }

  .learning-panel {
    position: static;
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }

  .mini-stats {
    grid-template-columns: repeat(4, minmax(100px, 1fr));
  }
}

@media (max-width: 920px) {
  .path-dashboard {
    padding: 12px;
  }

  .roadmap-head {
    grid-template-columns: 1fr;
  }

  .mini-stats {
    grid-template-columns: 1fr 1fr;
  }

  .stage-track {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .stage-number {
    width: 30px;
    height: 30px;
    border-radius: 12px;
    font-size: 0.82rem;
  }

  .stage-line {
    top: 36px;
  }

  .path-node-row {
    grid-template-columns: 1fr;
  }

  .node-connector {
    display: none;
  }
}

@media (max-width: 640px) {
  .header-right,
  .current-grid,
  .mini-stats {
    grid-template-columns: 1fr;
  }

  .progress-mini {
    width: 100%;
    height: 64px;
    border-radius: 18px;
  }

  .header-actions {
    display: grid;
  }

  .path-node {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .node-icon-wrap {
    width: 42px;
    height: 42px;
    border-radius: 16px;
    font-size: 21px;
  }
}
</style>
