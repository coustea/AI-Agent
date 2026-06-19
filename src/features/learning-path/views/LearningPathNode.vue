<template>
  <main class="node-study-page">
    <section v-if="loading && !isGeneratingTutorial" class="state-card">
      <div class="state-spinner"></div>
      <p>正在准备节点学习空间...</p>
    </section>

    <section v-else-if="!workspace && !isGeneratingTutorial" class="state-card">
      <h2>节点不存在或已经失效</h2>
      <p>请返回路径总览重新选择学习节点。</p>
      <BaseButton variant="primary" @click="router.push('/path-planner')">返回路径总览</BaseButton>
    </section>

    <section v-else-if="isGeneratingTutorial" class="generating-view">
      <div class="generate-panel">
        <div class="generate-loader">
          <span></span>
          <span></span>
          <span></span>
        </div>

        <div class="generate-copy">
          <p>AI Tutorial Agent</p>
          <h1>正在生成节点主教程</h1>
          <span>后端正在调用学习推进智能体，结合画像、路径目标和当前节点生成定制讲义。</span>
        </div>

        <transition-group name="log" tag="div" class="generate-log">
          <div v-for="(msg, index) in generatingLogs" :key="`${msg}-${index}`" class="log-item">
            <i></i>
            <span>{{ msg }}</span>
          </div>
        </transition-group>
      </div>
    </section>

    <template v-else-if="workspace">
      <nav class="node-toolbar">
        <div class="toolbar-left">
          <button class="back-button" type="button" @click="router.push(`/path-planner/overview/${workspace.path.id}`)">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z" />
            </svg>
            返回路径总览
          </button>

          <div class="toolbar-title">
            <span>知识节点学习</span>
            <h1>{{ workspace.node.title }}</h1>
          </div>
        </div>

        <div class="toolbar-right">
          <span class="status-pill" :class="workspace.node.status">
            <i></i>
            {{ statusText(workspace.node.status) }}
          </span>
        </div>
      </nav>

      <section class="study-workspace">
        <aside class="toc-panel">
          <div class="toc-card">
            <div class="side-head">
              <span>Contents</span>
              <strong>教程目录</strong>
            </div>

            <div v-if="tutorialToc.length" class="toc-list">
              <button
                v-for="item in tutorialToc"
                :key="item.id"
                type="button"
                :class="['toc-item', `level-${item.level}`, { active: activeHeadingId === item.id }]"
                @click="scrollToHeading(item.id)"
              >
                {{ item.title }}
              </button>
            </div>

            <div v-else class="toc-empty">
              <p>当前教程暂未识别到标题目录。</p>
              <span>AI 教程会自动展示在中间阅读区。</span>
            </div>
          </div>
        </aside>

        <article class="tutorial-main">
          <header class="tutorial-head">
            <div>
              <span class="section-kicker">AI Tutorial</span>
              <h2>{{ displayedTutorial?.title || workspace.node.title }}</h2>
              <p>
                这里是当前节点的主教程阅读区。先完成教程理解，再通过右侧资源推送生成导图、代码实操、PPT、拓展阅读和节点测验。
              </p>
            </div>

            <div v-if="workspace.tutorials.length > 1" class="tutorial-tabs">
              <button
                v-for="tutorial in workspace.tutorials"
                :key="tutorial.id"
                type="button"
                :class="{ active: tutorial.id === displayedTutorial?.id, current: tutorial.id === workspace.current_tutorial?.id }"
                @click="selectedTutorialId = tutorial.id"
              >
                {{ tutorialTypeText(tutorial.tutorial_type) }}
                <em>v{{ tutorial.version_no }}</em>
              </button>
            </div>
          </header>

          <section class="tutorial-reader">
            <div v-if="displayedTutorial" class="markdown-shell" ref="tutorialContentRef">
              <MarkdownView :result-data="{ content: displayedTutorial.content_markdown }" />
            </div>

            <div v-else class="tutorial-empty">
              <h3>当前节点还没有教程</h3>
              <p>进入节点后系统会自动调用后端学习推进智能体生成主教程。</p>
            </div>
          </section>
        </article>

        <aside class="resource-panel">
          <section class="resource-workbench-card">
            <div class="side-head workbench-head">
              <div>
                <span>Multi-Agent Push</span>
                <strong>资源推送与诊断测验</strong>
              </div>
            </div>

            <p class="push-desc">
              围绕当前教程，调用不同资源智能体生成配套学习材料。完成教程后，可以继续生成节点测验，系统会根据测验结果判断是否通过、补救或强化。
            </p>

            <div class="workbench-section">
              <div class="workbench-title">
                <span></span>
                <strong>多智能体资源推送</strong>
              </div>

              <div class="resource-list">
                <article
                  v-for="item in resourcePushItems"
                  :key="item.type"
                  :class="['resource-item', { generated: Boolean(item.resource), active: resourceLoading === item.type }]"
                >
                  <div class="resource-icon" :class="item.type">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path :d="item.icon" />
                    </svg>
                  </div>

                  <div class="resource-copy">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.desc }}</span>
                    <em v-if="item.resource">{{ item.resource.status === 'failed' ? '生成失败' : '已生成' }}</em>
                    <em v-else>按需生成</em>
                  </div>

                  <button
                    type="button"
                    :disabled="resourceLoading === item.type"
                    @click="item.resource ? openResourceDetail(item.resource.id) : createResource(item.type)"
                  >
                    {{ resourceLoading === item.type ? '生成中' : item.resource ? '查看' : '生成' }}
                  </button>
                </article>
              </div>
            </div>

            <div class="workbench-section quiz-section">
              <div class="workbench-title">
                <span></span>
                <strong>节点诊断测验</strong>
              </div>

              <p class="quiz-desc">
                生成 5 道节点测验题，检测当前教程掌握情况，并根据结果触发补救或强化学习。
              </p>

              <button
                v-if="!quizRound"
                class="primary-wide-btn"
                type="button"
                :disabled="quizLoading"
                @click="loadQuiz"
              >
                {{ quizLoading ? '正在生成题目...' : '生成节点测验' }}
              </button>

              <div v-else class="quiz-area">
                <div class="quiz-head">
                  <strong>第 {{ quizRound.round_no }} 轮测验</strong>
                  <span>{{ quizRound.questions.length }} 道题</span>
                </div>

                <div class="question-list">
                  <article v-for="(question, index) in quizRound.questions" :key="question.id" class="question-card">
                    <h4>{{ index + 1 }}. {{ question.question }}</h4>

                    <label
                      v-for="choice in choiceEntries(question.choice)"
                      :key="choice[0]"
                      :class="{ selected: answers[question.id] === choice[0] }"
                      class="choice-item"
                    >
                      <input
                        v-model="answers[question.id]"
                        type="radio"
                        :name="`q-${question.id}`"
                        :value="choice[0]"
                        :disabled="isQuizSubmitted"
                      />
                      <span>{{ choice[0] }}</span>
                      <p>{{ choice[1] }}</p>
                    </label>

                    <div v-if="isQuizSubmitted" class="answer-analysis">
                      <strong>正确答案：{{ question.answer }}</strong>
                      <p v-if="question.analysis">{{ question.analysis }}</p>
                    </div>
                  </article>
                </div>

                <button
                  v-if="!isQuizSubmitted"
                  class="primary-wide-btn"
                  type="button"
                  :disabled="submitLoading"
                  @click="submitQuiz"
                >
                  {{ submitLoading ? '正在提交...' : '提交测验' }}
                </button>

                <div v-if="quizResult" class="quiz-result-card">
                  <div>
                    <span>测验结果</span>
                    <strong>{{ quizResult.score }} / 5</strong>
                  </div>
                  <p>{{ resultText(quizResult.outcome) }}</p>

                  <div v-if="quizResult.weak_knowledge_points?.length" class="weak-points">
                    <label>薄弱知识点</label>
                    <span v-for="point in quizResult.weak_knowledge_points" :key="point">{{ point }}</span>
                  </div>

                  <button
                    v-if="quizResult.next_node_id"
                    class="secondary-wide-btn"
                    type="button"
                    @click="goToNextNode(quizResult.next_node_id)"
                  >
                    进入下一个节点
                  </button>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import BaseButton from '@/shared/ui/BaseButton.vue'
import MarkdownView from '@/features/resource/components/MarkdownView.vue'

import {
  generateAuxiliaryResource,
  generateNodeQuestions,
  getLearningNodeWorkspace,
  startNodeLearning,
  submitNodeQuiz,
} from '@/features/learning-path/api/path'
import { recordPathLearningEvent } from '@/features/evaluation/api/evaluation'
import type {
  AuxiliaryResourceRequest,
  LearningPathTutorial,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitResponse,
} from '@/features/learning-path/model/path'
import { getErrorMessage } from '@/shared/api/http'
import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'

type TocItem = {
  id: string
  title: string
  level: number
}

type ResourceKind = AuxiliaryResourceRequest['resource_type']

type ResourcePushItem = {
  type: ResourceKind
  title: string
  desc: string
  icon: string
  resource: LearningPathWorkspace['resources'][number] | null
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const quizLoading = ref(false)
const submitLoading = ref(false)
const resourceLoading = ref<ResourceKind | ''>('')

const workspace = ref<LearningPathWorkspace | null>(null)
const quizRound = ref<PathQuizRound | null>(null)
const quizResult = ref<PathQuizSubmitResponse | null>(null)
const answers = ref<Record<number, string>>({})
const hasStartedTracking = ref(false)

const selectedTutorialId = ref<number | null>(null)
const isGeneratingTutorial = ref(false)
const generatingLogs = ref<string[]>([])
const tutorialContentRef = ref<HTMLElement | null>(null)
const activeHeadingId = ref('')
const isQuizSubmitted = ref(false)

const nodeId = computed(() => Number(route.params.nodeId || 0))

const displayedTutorial = computed<LearningPathTutorial | null>(() => {
  if (!workspace.value) return null

  if (selectedTutorialId.value) {
    return workspace.value.tutorials.find((item) => item.id === selectedTutorialId.value)
      || workspace.value.current_tutorial
  }

  return workspace.value.current_tutorial
})

const tutorialMarkdown = computed(() => displayedTutorial.value?.content_markdown || '')

const tutorialToc = computed<TocItem[]>(() => {
  const markdown = tutorialMarkdown.value
  if (!markdown) return []

  const result: TocItem[] = []
  const used = new Map<string, number>()
  const headingRegex = /^(#{2,3})\s+(.+)$/gm

  let match: RegExpExecArray | null

  while ((match = headingRegex.exec(markdown)) !== null) {
    const level = match[1].length
    const title = match[2]
      .replace(/[#*_`>]/g, '')
      .trim()

    if (!title) continue

    const base = slugify(title)
    const count = used.get(base) || 0
    used.set(base, count + 1)

    result.push({
      id: count ? `${base}-${count + 1}` : base,
      title,
      level,
    })
  }

  return result.slice(0, 18)
})

const resourcePushItems = computed<ResourcePushItem[]>(() => [
  {
    type: 'mindmap',
    title: '思维导图',
    desc: '抽取教程中的核心概念和层级关系。',
    icon: 'M11 3h2v4h-2V3Zm-7 8h6v2H4v-2Zm10 0h6v2h-6v-2ZM5 17h5v2H5v-2Zm9 0h5v2h-5v-2ZM11 8h2v3h-2V8Zm0 5h2v3h-2v-3Z',
    resource: latestResourceByType('mindmap'),
  },
  {
    type: 'code',
    title: '代码实操',
    desc: '把抽象知识点转换成代码案例或模拟实验。',
    icon: 'm8.7 16.3-4.3-4.3 4.3-4.3L7.3 6.3 1.6 12l5.7 5.7 1.4-1.4Zm6.6 0 4.3-4.3-4.3-4.3 1.4-1.4 5.7 5.7-5.7 5.7-1.4-1.4ZM10.8 20 13.4 4h2l-2.6 16h-2Z',
    resource: latestResourceByType('code'),
  },
  {
    type: 'ppt',
    title: 'PPT 课件',
    desc: '生成适合复习展示的课程讲解课件。',
    icon: 'M4 3h16v18H4V3Zm2 2v14h12V5H6Zm2 3h8v2H8V8Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z',
    resource: latestResourceByType('ppt'),
  },
  {
    type: 'reading',
    title: '拓展阅读',
    desc: '围绕当前节点推送补充材料和延伸阅读。',
    icon: 'M12 6.5A5.5 5.5 0 0 0 6.5 1H3v18h4.5A4.5 4.5 0 0 1 12 23a4.5 4.5 0 0 1 4.5-4H21V1h-3.5A5.5 5.5 0 0 0 12 6.5ZM5 3h1.5A3.5 3.5 0 0 1 10 6.5v11.2A6.5 6.5 0 0 0 7.5 17H5V3Zm14 14h-2.5a6.5 6.5 0 0 0-2.5.7V6.5A3.5 3.5 0 0 1 17.5 3H19v14Z',
    resource: latestResourceByType('reading'),
  },
])

function latestResourceByType(type: string) {
  if (!workspace.value) return null

  const matched = workspace.value.resources
    .filter((item) => item.resource_type === type)
    .sort((a, b) => b.version_no - a.version_no)

  return matched[0] || null
}

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
    .replace(/^-+|-+$/g, '')
    || `heading-${Math.random().toString(36).slice(2, 8)}`
}

async function syncHeadingAnchors() {
  await nextTick()

  window.setTimeout(() => {
    const root = tutorialContentRef.value
    if (!root) return

    const headings = Array.from(root.querySelectorAll('h2, h3')) as HTMLElement[]
    const toc = tutorialToc.value

    headings.forEach((heading, index) => {
      const item = toc[index]
      if (!item) return
      heading.id = item.id
      heading.classList.add('tutorial-anchor-heading')
    })
  }, 80)
}

function scrollToHeading(id: string) {
  activeHeadingId.value = id

  const root = tutorialContentRef.value
  const target = root?.querySelector(`#${CSS.escape(id)}`) as HTMLElement | null

  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

async function loadWorkspace() {
  if (!nodeId.value) return

  loading.value = true

  try {
    const res = await getLearningNodeWorkspace(nodeId.value)
    workspace.value = res.data.data

    if (workspace.value && !workspace.value.current_tutorial) {
      await generatePrimaryTutorial()
    } else if (workspace.value?.current_tutorial) {
      selectedTutorialId.value = workspace.value.current_tutorial.id
    }

    await startLearningTracking()
    await syncHeadingAnchors()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载节点学习空间失败'))
  } finally {
    loading.value = false
    isGeneratingTutorial.value = false
  }
}

async function generatePrimaryTutorial() {
  isGeneratingTutorial.value = true
  loading.value = false

  generatingLogs.value = ['正在呼叫后端多智能体系统...']

  const logs = [
    '正在连接 LangGraph 学习推进智能体...',
    '正在读取当前路径目标与节点前置依赖...',
    '正在结合学习画像裁剪讲解深度...',
    '正在组织教程目录、例子和易错点...',
    '正在写入主教程并刷新学习空间...',
  ]

  let index = 0
  const interval = window.setInterval(() => {
    if (index < logs.length) {
      generatingLogs.value.push(logs[index])
      if (generatingLogs.value.length > 5) generatingLogs.value.shift()
      index += 1
    } else {
      window.clearInterval(interval)
    }
  }, 1600)

  try {
    const startRes = await startNodeLearning(nodeId.value)
    workspace.value = startRes.data.data

    if (workspace.value?.current_tutorial) {
      selectedTutorialId.value = workspace.value.current_tutorial.id
    }
  } finally {
    window.clearInterval(interval)
    isGeneratingTutorial.value = false
  }
}

async function startLearningTracking() {
  if (!workspace.value || hasStartedTracking.value) return

  hasStartedTracking.value = true

  startTracking({
    sourcePage: 'path_node',
    pathId: workspace.value.path.id,
    pathNodeId: workspace.value.node.id,
    nodeId: workspace.value.node.node_id,
    course: workspace.value.path.title,
    topic: workspace.value.node.title,
  })

  await recordPathLearningEvent(workspace.value.path.id, {
    event_type: 'resource_viewed',
    path_id: workspace.value.path.id,
    path_node_id: workspace.value.node.id,
    node_id: workspace.value.node.node_id,
    course: workspace.value.path.title,
    topic: workspace.value.node.title,
  })
}

async function loadQuiz() {
  if (!workspace.value) return

  quizLoading.value = true
  quizResult.value = null
  isQuizSubmitted.value = false

  try {
    const res = await generateNodeQuestions(workspace.value.node.id)
    quizRound.value = res.data.data
    answers.value = {}
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成节点测验失败'))
  } finally {
    quizLoading.value = false
  }
}

async function submitQuiz() {
  if (!workspace.value || !quizRound.value) return

  const payload = {
    answers: quizRound.value.questions.map((question) => ({
      question_id: question.id,
      response: answers.value[question.id] || '',
    })),
  }

  if (payload.answers.some((item) => !item.response)) {
    ElMessage.warning('请先完成全部 5 道题')
    return
  }

  submitLoading.value = true

  try {
    const res = await submitNodeQuiz(workspace.value.node.id, payload)
    quizResult.value = res.data.data
    isQuizSubmitted.value = true

    await recordPathLearningEvent(workspace.value.path.id, {
      event_type: 'quiz_submitted',
      path_id: workspace.value.path.id,
      path_node_id: workspace.value.node.id,
      node_id: workspace.value.node.node_id,
      course: workspace.value.path.title,
      topic: workspace.value.node.title,
      score: Number(((quizResult.value.score / 5) * 100).toFixed(0)),
      metadata: {
        outcome: quizResult.value.outcome,
        weak_knowledge_points: quizResult.value.weak_knowledge_points,
      },
    })

    const resWorkspace = await getLearningNodeWorkspace(nodeId.value)
    workspace.value = resWorkspace.data.data

    if (workspace.value?.current_tutorial) {
      selectedTutorialId.value = workspace.value.current_tutorial.id
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '提交节点测验失败'))
  } finally {
    submitLoading.value = false
  }
}

async function createResource(type: ResourceKind) {
  if (!workspace.value) return

  resourceLoading.value = type

  try {
    const res = await generateAuxiliaryResource(workspace.value.node.id, { resource_type: type })
    openResourceDetail(res.data.data.id)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成辅助资源失败'))
  } finally {
    resourceLoading.value = ''

    if (workspace.value) {
      const resWorkspace = await getLearningNodeWorkspace(nodeId.value)
      workspace.value = resWorkspace.data.data
    }
  }
}

function openResourceDetail(resourceId: number) {
  if (!workspace.value) return

  router.push({
    name: 'PathResourceDetail',
    params: { id: resourceId },
    query: {
      pathId: workspace.value.path.id,
      pathNodeId: workspace.value.node.id,
      nodeId: workspace.value.node.node_id,
    },
  })
}

function goToNextNode(nextNodeId: number) {
  router.push(`/path-planner/node/${nextNodeId}`)
}

function choiceEntries(choice: Record<string, string> | undefined | null) {
  return Object.entries(choice || {})
}

function tutorialTypeText(value?: string | null) {
  if (value === 'remediation') return '专项巩固'
  if (value === 'reinforced') return '强化教程'
  return '主教程'
}

function statusText(status: string) {
  switch (status) {
    case 'available':
      return '可开始'
    case 'in_progress':
      return '学习中'
    case 'remediation':
      return '专项巩固中'
    case 'reinforced':
      return '强化学习中'
    case 'completed':
      return '已通过'
    case 'completed_with_gaps':
      return '带缺口完成'
    default:
      return status
  }
}

function resultText(outcome: string) {
  switch (outcome) {
    case 'completed':
    case 'passed':
      return '本节点通过，下一节点已解锁。'
    case 'remediation':
      return '首轮未通过，系统会围绕薄弱点生成专项巩固教程。'
    case 'reinforced':
      return '系统已进入强化学习模式，会继续补足薄弱点。'
    case 'completed_with_gaps':
      return '当前节点已判定为带缺口完成，可以继续推进，但建议回看薄弱点。'
    default:
      return outcome
  }
}

watch(
  () => route.params.nodeId,
  (newId) => {
    if (!newId) return

    workspace.value = null
    quizRound.value = null
    quizResult.value = null
    answers.value = {}
    selectedTutorialId.value = null
    isQuizSubmitted.value = false
    hasStartedTracking.value = false
    loadWorkspace()
  },
)

watch(tutorialMarkdown, () => {
  syncHeadingAnchors()
})

onMounted(loadWorkspace)

onBeforeUnmount(() => {
  stopTracking()
})
</script>

<style scoped>
.node-study-page {
  --np-primary: #4f46e5;
  --np-primary-dark: #3730a3;
  --np-primary-soft: #eef2ff;
  --np-blue: #0ea5e9;
  --np-cyan: #06b6d4;
  --np-green: #10b981;
  --np-orange: #f59e0b;
  --np-red: #ef4444;
  --np-slate: #64748b;
  --np-muted: #94a3b8;
  --np-text: #0f172a;
  --np-border: #e2e8f0;
  --np-border-strong: #c7d2fe;
  --np-card: #ffffff;
  --np-shadow: 0 14px 38px rgba(15, 23, 42, 0.06);

  min-height: calc(100vh - 64px);
  padding: 14px;
  background:
    radial-gradient(circle at 8% 0%, rgba(79, 70, 229, 0.07), transparent 30%),
    radial-gradient(circle at 92% 0%, rgba(14, 165, 233, 0.07), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  color: var(--np-text);
}

.node-study-page svg {
  width: 1em;
  height: 1em;
  fill: currentColor;
}

.state-card {
  width: min(720px, calc(100% - 24px));
  min-height: 260px;
  margin: 84px auto 0;
  padding: 40px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  text-align: center;
  border-radius: 24px;
  background: var(--np-card);
  border: 1px solid var(--np-border);
  box-shadow: var(--np-shadow);
}

.state-card h2 {
  margin: 0;
  font-size: 1.35rem;
}

.state-card p {
  margin: 0;
  color: var(--np-slate);
}

.state-spinner {
  width: 34px;
  height: 34px;
  border: 4px solid #e0e7ff;
  border-top-color: var(--np-primary);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.generating-view {
  min-height: calc(100vh - 110px);
  display: grid;
  place-items: center;
}

.generate-panel {
  width: min(640px, 100%);
  padding: 34px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid var(--np-border-strong);
  box-shadow: var(--np-shadow);
  backdrop-filter: blur(16px);
  text-align: center;
}

.generate-loader {
  width: 86px;
  height: 86px;
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
  background: linear-gradient(135deg, var(--np-primary), var(--np-blue));
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
  color: var(--np-primary);
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
  color: var(--np-slate);
  font-size: 0.95rem;
}

.generate-log {
  margin-top: 20px;
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
  border: 1px solid var(--np-border);
  color: #334155;
  font-size: 0.88rem;
}

.log-item i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--np-primary);
  box-shadow: 0 0 0 5px rgba(79, 70, 229, 0.1);
  flex: 0 0 auto;
}

.node-toolbar {
  width: min(1760px, 100%);
  min-height: 64px;
  margin: 0 auto 14px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(199, 210, 254, 0.75);
  box-shadow: var(--np-shadow);
  backdrop-filter: blur(16px);
}

.toolbar-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.back-button {
  min-height: 36px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--np-primary);
  font: inherit;
  font-size: 0.86rem;
  font-weight: 900;
  cursor: pointer;
  white-space: nowrap;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.18s ease;
}

.back-button:hover {
  background: var(--np-primary-soft);
  border-color: var(--np-border-strong);
  transform: translateY(-1px);
}

.toolbar-title {
  min-width: 0;
}

.toolbar-title span {
  display: block;
  color: var(--np-muted);
  font-size: 0.72rem;
  font-weight: 900;
  margin-bottom: 2px;
}

.toolbar-title h1 {
  margin: 0;
  color: var(--np-text);
  font-size: clamp(1rem, 1.6vw, 1.35rem);
  line-height: 1.25;
  letter-spacing: -0.03em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toolbar-right {
  flex: 0 0 auto;
}

.status-pill {
  min-height: 34px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 12px;
  color: #d97706;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  font-size: 0.86rem;
  font-weight: 900;
  white-space: nowrap;
}

.status-pill i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-pill.completed,
.status-pill.completed_with_gaps {
  color: #047857;
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.status-pill.remediation,
.status-pill.reinforced {
  color: #075985;
  background: #e0f2fe;
  border-color: #bae6fd;
}

.status-pill.available {
  color: var(--np-primary-dark);
  background: var(--np-primary-soft);
  border-color: var(--np-border-strong);
}

.study-workspace {
  width: min(1760px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 330px;
  gap: 14px;
  align-items: start;
}

.toc-panel,
.resource-panel {
  display: grid;
  gap: 14px;
  position: sticky;
  top: 14px;
  max-height: calc(100vh - 28px);
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(79, 70, 229, 0.28) transparent;
}

.toc-panel::-webkit-scrollbar,
.resource-panel::-webkit-scrollbar {
  width: 6px;
}

.toc-panel::-webkit-scrollbar-thumb,
.resource-panel::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(79, 70, 229, 0.28);
}

.toc-panel::-webkit-scrollbar-track,
.resource-panel::-webkit-scrollbar-track {
  background: transparent;
}

.toc-card,
.tutorial-main,
.resource-workbench-card {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--np-border);
  box-shadow: var(--np-shadow);
  backdrop-filter: blur(16px);
}

.toc-card,
.resource-workbench-card {
  padding: 16px;
}

.resource-workbench-card {
  display: grid;
  gap: 16px;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.workbench-head {
  margin-bottom: 0;
}

.workbench-head div {
  min-width: 0;
}

.side-head span,
.section-kicker {
  color: var(--np-primary);
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.side-head strong {
  color: var(--np-text);
  font-size: 0.9rem;
}

.workbench-head strong {
  display: block;
  margin-top: 4px;
  color: var(--np-text);
  font-size: 1rem;
}

.workbench-section {
  padding-top: 14px;
  border-top: 1px solid var(--np-border);
}

.workbench-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.workbench-title span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--np-primary);
  box-shadow: 0 0 0 5px rgba(79, 70, 229, 0.1);
}

.workbench-title strong {
  color: var(--np-text);
  font-size: 0.9rem;
}

.quiz-section {
  margin-top: 2px;
}

.quiz-desc {
  margin: 0 0 12px;
  color: var(--np-slate);
  font-size: 0.82rem;
  line-height: 1.6;
}

.toc-list {
  display: grid;
  gap: 5px;
}

.toc-item {
  width: 100%;
  min-height: 34px;
  padding: 7px 9px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #475569;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 800;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.toc-item.level-3 {
  padding-left: 20px;
  font-size: 0.78rem;
  color: var(--np-slate);
}

.toc-item:hover,
.toc-item.active {
  color: var(--np-primary-dark);
  background: var(--np-primary-soft);
}

.toc-empty {
  padding: 12px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--np-border);
}

.toc-empty p,
.toc-empty span {
  margin: 0;
  color: var(--np-slate);
  font-size: 0.82rem;
  line-height: 1.55;
}

.toc-empty span {
  display: block;
  margin-top: 6px;
  color: var(--np-muted);
}

.tutorial-main {
  min-width: 0;
  overflow: hidden;
}

.tutorial-head {
  padding: 20px 22px;
  display: grid;
  gap: 14px;
  border-bottom: 1px solid var(--np-border);
  background:
    radial-gradient(circle at 92% 0%, rgba(79, 70, 229, 0.08), transparent 32%),
    linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.tutorial-head h2 {
  margin: 6px 0 8px;
  font-size: clamp(1.35rem, 2vw, 2rem);
  letter-spacing: -0.04em;
  color: var(--np-text);
}

.tutorial-head p {
  max-width: 920px;
  margin: 0;
  color: var(--np-slate);
  line-height: 1.65;
  font-size: 0.92rem;
}

.tutorial-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tutorial-tabs button {
  min-height: 34px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 12px;
  border: 1px solid var(--np-border);
  background: #ffffff;
  color: #475569;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 900;
  cursor: pointer;
}

.tutorial-tabs button.active {
  color: var(--np-primary-dark);
  background: var(--np-primary-soft);
  border-color: var(--np-border-strong);
}

.tutorial-tabs button.current em {
  color: var(--np-green);
}

.tutorial-tabs em {
  font-style: normal;
  color: var(--np-muted);
}

.tutorial-reader {
  padding: 18px;
}

.markdown-shell {
  min-height: 680px;
  padding: 16px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid var(--np-border);
  scroll-margin-top: 90px;
}

.markdown-shell :deep(.markdown-view) {
  max-width: none;
}

.markdown-shell :deep(.tutorial-anchor-heading) {
  scroll-margin-top: 90px;
}

.tutorial-empty {
  min-height: 360px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 8px;
  text-align: center;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid var(--np-border);
}

.tutorial-empty h3,
.tutorial-empty p {
  margin: 0;
}

.tutorial-empty p {
  color: var(--np-slate);
}

.push-desc {
  margin: 0;
  color: var(--np-slate);
  font-size: 0.84rem;
  line-height: 1.65;
}

.resource-list {
  display: grid;
  gap: 9px;
}

.resource-item {
  min-height: 76px;
  padding: 10px;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) 58px;
  gap: 10px;
  align-items: center;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid var(--np-border);
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}

.resource-item:hover {
  transform: translateY(-1px);
  border-color: var(--np-border-strong);
}

.resource-item.generated {
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border-color: var(--np-border-strong);
}

.resource-icon {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: #ffffff;
  font-size: 20px;
  background: linear-gradient(135deg, var(--np-primary), var(--np-blue));
}

.resource-icon.mindmap {
  background: linear-gradient(135deg, #7c3aed, #6366f1);
}

.resource-icon.code {
  background: linear-gradient(135deg, #0f766e, #14b8a6);
}

.resource-icon.ppt {
  background: linear-gradient(135deg, #ea580c, #f59e0b);
}

.resource-icon.reading {
  background: linear-gradient(135deg, #059669, #10b981);
}

.resource-copy {
  min-width: 0;
}

.resource-copy strong {
  display: block;
  margin-bottom: 3px;
  color: var(--np-text);
  font-size: 0.84rem;
}

.resource-copy span {
  display: block;
  color: var(--np-slate);
  font-size: 0.74rem;
  line-height: 1.35;
}

.resource-copy em {
  display: inline-flex;
  margin-top: 5px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 900;
}

.resource-item.generated .resource-copy em {
  background: var(--np-primary);
  color: #ffffff;
}

.resource-item button,
.primary-wide-btn,
.secondary-wide-btn {
  min-height: 34px;
  border: 0;
  border-radius: 12px;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 900;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    opacity 0.18s ease,
    box-shadow 0.18s ease;
}

.resource-item button {
  background: var(--np-primary-soft);
  color: var(--np-primary-dark);
}

.resource-item button:hover,
.primary-wide-btn:hover,
.secondary-wide-btn:hover {
  transform: translateY(-1px);
}

.resource-item button:disabled,
.primary-wide-btn:disabled,
.secondary-wide-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
  transform: none;
}

.primary-wide-btn {
  width: 100%;
  margin-top: 4px;
  color: #ffffff;
  background: linear-gradient(135deg, var(--np-primary), var(--np-blue));
  box-shadow: 0 12px 26px rgba(79, 70, 229, 0.18);
}

.secondary-wide-btn {
  width: 100%;
  color: var(--np-primary-dark);
  background: var(--np-primary-soft);
}

.quiz-area {
  display: grid;
  gap: 12px;
}

.quiz-head {
  min-height: 40px;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--np-border);
}

.quiz-head strong {
  color: var(--np-text);
  font-size: 0.86rem;
}

.quiz-head span {
  color: var(--np-slate);
  font-size: 0.78rem;
  font-weight: 800;
}

.question-list {
  display: grid;
  gap: 10px;
}

.question-card {
  padding: 12px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid var(--np-border);
}

.question-card h4 {
  margin: 0 0 10px;
  color: var(--np-text);
  font-size: 0.88rem;
  line-height: 1.55;
}

.choice-item {
  display: grid;
  grid-template-columns: 16px 26px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  padding: 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.18s ease;
}

.choice-item:hover,
.choice-item.selected {
  background: #f8fafc;
}

.choice-item input {
  margin-top: 3px;
}

.choice-item span {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--np-primary-dark);
  background: var(--np-primary-soft);
  font-size: 0.74rem;
  font-weight: 900;
}

.choice-item p {
  margin: 2px 0 0;
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.45;
}

.answer-analysis {
  margin-top: 10px;
  padding: 10px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid var(--np-border);
}

.answer-analysis strong {
  display: block;
  margin-bottom: 5px;
  color: var(--np-primary-dark);
  font-size: 0.8rem;
}

.answer-analysis p {
  margin: 0;
  color: var(--np-slate);
  font-size: 0.78rem;
  line-height: 1.5;
}

.quiz-result-card {
  padding: 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
  border: 1px solid var(--np-border-strong);
}

.quiz-result-card > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.quiz-result-card span {
  color: var(--np-primary);
  font-size: 0.78rem;
  font-weight: 900;
}

.quiz-result-card strong {
  color: var(--np-primary-dark);
  font-size: 1.2rem;
}

.quiz-result-card p {
  margin: 8px 0 0;
  color: #475569;
  font-size: 0.82rem;
  line-height: 1.55;
}

.weak-points {
  margin: 10px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.weak-points label {
  width: 100%;
  color: var(--np-muted);
  font-size: 0.7rem;
  font-weight: 900;
}

.weak-points span {
  padding: 4px 8px;
  border-radius: 999px;
  color: #075985;
  background: #e0f2fe;
  font-size: 0.72rem;
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

@media (max-width: 1380px) {
  .study-workspace {
    grid-template-columns: 260px minmax(0, 1fr) 320px;
  }
}

@media (max-width: 1180px) {
  .study-workspace {
    grid-template-columns: 1fr;
  }

  .toc-panel,
  .resource-panel {
    position: static;
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }

  .toc-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .node-study-page {
    padding: 10px;
  }

  .node-toolbar,
  .toolbar-left {
    align-items: stretch;
  }

  .node-toolbar {
    display: grid;
  }

  .toolbar-left {
    display: grid;
  }

  .toolbar-title h1 {
    white-space: normal;
  }

  .toolbar-right {
    justify-self: start;
  }

  .tutorial-head,
  .tutorial-reader,
  .resource-workbench-card,
  .toc-card {
    padding: 14px;
  }

  .resource-item {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .resource-item button {
    grid-column: 1 / -1;
  }
}
</style>