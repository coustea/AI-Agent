<template>
  <main class="path-entry-page">
    <section class="entry-shell">
      <header class="entry-header">
        <div>
          <span class="eyebrow">PATH PLANNER</span>
          <h1>创建学习路径</h1>
          <p>
            填写学习主题、学习目标、当前基础和学习偏好。这里只生成路径结构，教程、测验、导图、代码实操等资源会在节点学习页按需生成。
          </p>
        </div>

        <button class="history-button" type="button" :disabled="isPlanning" @click="goHistory">
          历史路径
        </button>
      </header>

      <section class="entry-body">
        <aside class="example-rail">
          <div class="example-rail-header">
            <span class="side-kicker">EXAMPLES</span>
            <h2>常用路径模板</h2>
            <p>选择模板后，会自动填入主题、目标、基础和偏好。</p>
          </div>

          <div class="example-list">
            <button
                v-for="item in examples"
                :key="item.title"
                type="button"
                class="example-row"
                :class="[item.tone, { active: isExampleActive(item) }]"
                :disabled="isPlanning"
                @click="applyExample(item)"
            >
              <span class="example-dot"></span>
              <div>
                <strong>{{ item.title }}</strong>
                <em>{{ item.topic }}</em>
              </div>
            </button>
          </div>
        </aside>

        <section v-if="isPlanning" class="planning-panel">
          <div class="planning-head">
            <span class="planning-kicker">GENERATING PATH</span>
            <h2>正在规划学习路径</h2>
            <p>
              系统正在根据你的主题、目标、当前基础和学习偏好生成阶段结构、节点顺序与前置依赖。
            </p>
          </div>

          <div class="planning-visual">
            <div class="route-orbit">
              <div class="orbit-line"></div>

              <div
                  v-for="(step, index) in planningSteps"
                  :key="step.key"
                  class="orbit-step"
                  :class="[
                  step.tone,
                  {
                    active: currentPlanningIndex === index,
                    done: currentPlanningIndex > index,
                  },
                ]"
              >
                <span>{{ index + 1 }}</span>
                <strong>{{ step.title }}</strong>
              </div>
            </div>
          </div>

          <div class="planning-progress">
            <div class="progress-head">
              <span>{{ currentPlanningTitle }}</span>
              <strong>{{ Math.round(planningProgress) }}%</strong>
            </div>
            <div class="progress-track">
              <i :style="{ width: `${planningProgress}%` }"></i>
            </div>
          </div>

          <transition-group name="log" tag="div" class="planning-log">
            <div
                v-for="(message, index) in planningLogs"
                :key="`${message}-${index}`"
                class="log-item"
            >
              <i></i>
              <span>{{ message }}</span>
            </div>
          </transition-group>

          <div v-if="planningError" class="planning-error">
            <strong>路径规划失败</strong>
            <p>{{ planningError }}</p>
            <button type="button" @click="resetPlanningState">返回修改</button>
          </div>
        </section>

        <section v-else class="form-panel">
          <div class="form-section">
            <div class="section-title">
              <span>01</span>
              <div>
                <h2>学习主题</h2>
                <p>确定这条路径围绕哪门课、哪个知识点或哪个学习方向展开。</p>
              </div>
            </div>

            <div class="field-row">
              <label for="topic">主题名称</label>
              <div class="field-control">
                <input
                    id="topic"
                    v-model.trim="form.topic"
                    maxlength="60"
                    type="text"
                    placeholder="例如：操作系统、数据结构、计算机网络、Vue3"
                />
                <p>主题会作为路径标题和规划关键词使用。</p>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">
              <span>02</span>
              <div>
                <h2>学习目标</h2>
                <p>说明你为什么学、重点学什么、希望达到什么程度。</p>
              </div>
            </div>

            <div class="field-row align-start">
              <label for="goal">目标描述</label>
              <div class="field-control">
                <textarea
                    id="goal"
                    ref="goalRef"
                    v-model.trim="form.goal"
                    maxlength="500"
                    rows="4"
                    placeholder="例如：系统复习操作系统核心考点，重点掌握进程同步、死锁、内存管理和页面置换，用来准备期末考试。"
                    @input="autoResize"
                />
                <div class="field-footer">
                  <p>建议包含：学习目的、重点范围、预期掌握程度。</p>
                  <span>{{ form.goal.length }}/500</span>
                </div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">
              <span>03</span>
              <div>
                <h2>当前基础</h2>
                <p>添加你已经掌握的知识点，避免路径起点过低或过高。</p>
              </div>
            </div>

            <div class="field-row align-start">
              <label>已掌握知识</label>
              <div class="field-control">
                <div class="knowledge-input">
                  <span
                      v-for="item in form.currentKnowledge"
                      :key="item"
                      class="knowledge-tag"
                  >
                    {{ item }}
                    <button type="button" @click="removeKnowledge(item)">×</button>
                  </span>

                  <input
                      v-model.trim="knowledgeInput"
                      type="text"
                      placeholder="输入后按 Enter 添加，例如：Python、链表、进程基础"
                      @keydown.enter.prevent="addKnowledge"
                      @keydown.backspace="removeLastKnowledge"
                  />
                </div>

                <div class="quick-knowledge">
                  <button
                      v-for="item in quickKnowledge"
                      :key="item"
                      type="button"
                      :class="{ selected: form.currentKnowledge.includes(item) }"
                      @click="toggleKnowledge(item)"
                  >
                    {{ item }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">
              <span>04</span>
              <div>
                <h2>学习偏好</h2>
                <p>偏好会写入 preferences，用来辅助后端生成更适合的路径结构。</p>
              </div>
            </div>

            <div class="preference-grid">
              <div class="pref-group">
                <label>学习场景</label>
                <div class="choice-line wrap">
                  <button
                      v-for="item in sceneOptions"
                      :key="item.value"
                      type="button"
                      :class="{ selected: form.scene === item.value }"
                      @click="form.scene = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="pref-group">
                <label>学习节奏</label>
                <div class="choice-line">
                  <button
                      v-for="item in paceOptions"
                      :key="item.value"
                      type="button"
                      :class="{ selected: form.pace === item.value }"
                      @click="form.pace = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="pref-group">
                <label>路径粒度</label>
                <div class="choice-line">
                  <button
                      v-for="item in granularityOptions"
                      :key="item.value"
                      type="button"
                      :class="{ selected: form.granularity === item.value }"
                      @click="form.granularity = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="pref-group">
                <label>规划重点</label>
                <div class="choice-line wrap">
                  <button
                      v-for="item in focusOptions"
                      :key="item.value"
                      type="button"
                      :class="{ selected: form.focus.includes(item.value) }"
                      @click="toggleFocus(item.value)"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <footer class="submit-bar">
            <div class="submit-info">
              <strong>{{ submitStateTitle }}</strong>
              <span>{{ submitStateDesc }}</span>
            </div>

            <div class="submit-actions">
              <button class="secondary-button" type="button" @click="resetForm">
                重置
              </button>
              <button
                  class="primary-button"
                  type="button"
                  :disabled="!canSubmit || isSubmitting"
                  @click="handleSubmit"
              >
                <span v-if="!isSubmitting">生成学习路径</span>
                <span v-else>正在创建路径...</span>
              </button>
            </div>
          </footer>
        </section>

        <aside class="side-panel">
          <template v-if="isPlanning">
            <section class="side-section">
              <span class="side-kicker">PLANNING STATUS</span>
              <h2>{{ currentPlanningTitle }}</h2>
              <p>{{ currentPlanningDesc }}</p>
            </section>

            <section class="side-table">
              <div>
                <span>路径任务</span>
                <strong>{{ planningPathId ? `#${planningPathId}` : '创建中' }}</strong>
              </div>
              <div>
                <span>运行标识</span>
                <strong>{{ planningRunId || '等待返回' }}</strong>
              </div>
              <div>
                <span>当前阶段</span>
                <strong>{{ currentPlanningTitle }}</strong>
              </div>
              <div>
                <span>生成进度</span>
                <strong>{{ Math.round(planningProgress) }}%</strong>
              </div>
            </section>

            <section class="side-section path-only-section">
              <span class="side-kicker">NEXT STEP</span>
              <div class="logic-list">
                <div class="logic-item teal">
                  <strong>生成完成后自动进入路径页</strong>
                  <p>当前页面不会提前跳转，直到后端路径状态变为可查看。</p>
                </div>
                <div class="logic-item blue">
                  <strong>查看阶段和节点</strong>
                  <p>完成后会进入路径总览，展示阶段、节点和解锁状态。</p>
                </div>
              </div>
            </section>
          </template>

          <template v-else>
            <section class="side-section">
              <span class="side-kicker">REQUEST PREVIEW</span>
              <h2>{{ previewTitle }}</h2>
              <p>{{ previewGoal }}</p>
            </section>

            <section class="side-table">
              <div>
                <span>学习主题</span>
                <strong>{{ form.topic || '未填写' }}</strong>
              </div>
              <div>
                <span>学习场景</span>
                <strong>{{ sceneLabel }}</strong>
              </div>
              <div>
                <span>学习节奏</span>
                <strong>{{ paceLabel }}</strong>
              </div>
              <div>
                <span>路径粒度</span>
                <strong>{{ granularityLabel }}</strong>
              </div>
              <div>
                <span>当前基础</span>
                <strong>{{ knowledgeLabel }}</strong>
              </div>
            </section>

            <section class="side-section path-only-section">
              <span class="side-kicker">PATH ONLY</span>
              <div class="logic-list">
                <div class="logic-item teal">
                  <strong>先生成路线</strong>
                  <p>入口页只负责阶段、节点和学习顺序。</p>
                </div>
                <div class="logic-item blue">
                  <strong>节点内学习</strong>
                  <p>进入节点后再生成教程和测验。</p>
                </div>
                <div class="logic-item amber">
                  <strong>资源按需生成</strong>
                  <p>导图、代码、PPT 不在入口页选择。</p>
                </div>
              </div>
            </section>
          </template>
        </aside>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { createLearningPath, getLearningPathById } from '@/features/learning-path/api/path'
import type { PathRequest } from '@/features/learning-path/model/path'

type Scene = 'exam' | 'beginner' | 'project' | 'interview' | 'general'
type Pace = 'slow' | 'normal' | 'fast'
type Granularity = 'coarse' | 'standard' | 'fine'
type Focus = 'foundation' | 'key_points' | 'practice' | 'weakness'
type ExampleTone = 'teal' | 'blue' | 'amber' | 'violet'

interface ExampleItem {
  title: string
  topic: string
  goal: string
  currentKnowledge: string[]
  scene: Scene
  pace: Pace
  granularity: Granularity
  focus: Focus[]
  tone: ExampleTone
}

interface PlanningStep {
  key: string
  title: string
  desc: string
  threshold: number
  tone: ExampleTone
}

const router = useRouter()
const goalRef = ref<HTMLTextAreaElement | null>(null)
const knowledgeInput = ref('')
const isSubmitting = ref(false)
const isPlanning = ref(false)
const planningPathId = ref<number | null>(null)
const planningRunId = ref('')
const planningProgress = ref(0)
const planningLogs = ref<string[]>([])
const planningError = ref('')

let progressTimer: number | null = null
let pollingStopped = false

const form = reactive({
  topic: '',
  goal: '',
  currentKnowledge: [] as string[],
  scene: 'general' as Scene,
  pace: 'normal' as Pace,
  granularity: 'standard' as Granularity,
  focus: ['key_points'] as Focus[],
})

const sceneOptions = [
  { label: '通用学习', value: 'general' as Scene },
  { label: '考试复习', value: 'exam' as Scene },
  { label: '基础入门', value: 'beginner' as Scene },
  { label: '项目实战', value: 'project' as Scene },
  { label: '面试准备', value: 'interview' as Scene },
]

const paceOptions = [
  { label: '慢速细学', value: 'slow' as Pace },
  { label: '正常节奏', value: 'normal' as Pace },
  { label: '快速推进', value: 'fast' as Pace },
]

const granularityOptions = [
  { label: '粗略路径', value: 'coarse' as Granularity },
  { label: '标准路径', value: 'standard' as Granularity },
  { label: '细节点路径', value: 'fine' as Granularity },
]

const focusOptions = [
  { label: '补基础', value: 'foundation' as Focus },
  { label: '抓重点', value: 'key_points' as Focus },
  { label: '多练习', value: 'practice' as Focus },
  { label: '补薄弱点', value: 'weakness' as Focus },
]

const quickKnowledge = [
  'Python',
  'C++',
  'Java',
  '数据结构基础',
  '操作系统基础',
  '计算机网络基础',
  '数据库基础',
  'Linux',
]

const planningSteps: PlanningStep[] = [
  {
    key: 'profile',
    title: '读取画像与目标',
    desc: '正在结合学习画像、学习主题和本次目标确定路径起点。',
    threshold: 12,
    tone: 'teal',
  },
  {
    key: 'stage',
    title: '拆解学习阶段',
    desc: '正在将学习目标拆解为基础、核心、应用和巩固阶段。',
    threshold: 34,
    tone: 'blue',
  },
  {
    key: 'node',
    title: '生成学习节点',
    desc: '正在生成具体学习节点，并确定每个节点的前置关系。',
    threshold: 58,
    tone: 'amber',
  },
  {
    key: 'validate',
    title: '校验路径结构',
    desc: '正在检查节点依赖、阶段覆盖和学习顺序是否合理。',
    threshold: 78,
    tone: 'violet',
  },
  {
    key: 'save',
    title: '保存路径结果',
    desc: '正在保存路径数据，完成后会自动进入路径总览页。',
    threshold: 92,
    tone: 'teal',
  },
]

const fallbackPlanningStep: PlanningStep = {
  key: 'fallback',
  title: '正在规划路径',
  desc: '系统正在生成学习路径。',
  threshold: 0,
  tone: 'teal',
}

const examples: ExampleItem[] = [
  {
    title: '操作系统期末复习',
    topic: '操作系统',
    goal: '系统复习操作系统核心考点，重点掌握进程同步、死锁、内存管理和页面置换，用来准备期末考试。',
    currentKnowledge: ['进程基础', 'C语言'],
    scene: 'exam',
    pace: 'normal',
    granularity: 'fine',
    focus: ['key_points', 'weakness', 'practice'],
    tone: 'amber',
  },
  {
    title: '数据结构刷题路线',
    topic: '数据结构与算法',
    goal: '掌握栈、队列、树、图、排序和搜索等基础数据结构与算法，并能完成基础编程题。',
    currentKnowledge: ['Python', '数组', '链表'],
    scene: 'general',
    pace: 'normal',
    granularity: 'standard',
    focus: ['key_points', 'practice'],
    tone: 'teal',
  },
  {
    title: '计算机网络入门',
    topic: '计算机网络',
    goal: '从基础开始学习计算机网络，理解分层模型、TCP/IP、HTTP、DNS 和常见网络协议。',
    currentKnowledge: [],
    scene: 'beginner',
    pace: 'slow',
    granularity: 'fine',
    focus: ['foundation', 'key_points'],
    tone: 'blue',
  },
  {
    title: 'Vue 项目学习路线',
    topic: 'Vue3',
    goal: '通过项目实战学习 Vue3，掌握组件、路由、状态管理、接口请求和页面样式设计。',
    currentKnowledge: ['HTML', 'CSS', 'JavaScript'],
    scene: 'project',
    pace: 'normal',
    granularity: 'standard',
    focus: ['practice', 'key_points'],
    tone: 'violet',
  },
]

const canSubmit = computed(() => {
  return form.topic.trim().length > 0 && form.goal.trim().length >= 8
})

const sceneLabel = computed(() => {
  return sceneOptions.find(item => item.value === form.scene)?.label || '通用学习'
})

const paceLabel = computed(() => {
  return paceOptions.find(item => item.value === form.pace)?.label || '正常节奏'
})

const granularityLabel = computed(() => {
  return granularityOptions.find(item => item.value === form.granularity)?.label || '标准路径'
})

const knowledgeLabel = computed(() => {
  return form.currentKnowledge.length ? `${form.currentKnowledge.length} 个知识点` : '未填写'
})

const previewTitle = computed(() => {
  return form.topic || '等待填写学习主题'
})

const previewGoal = computed(() => {
  return form.goal || '填写学习目标后，这里会显示本次路径规划意图。'
})

const submitStateTitle = computed(() => {
  if (!form.topic.trim()) return '请先填写学习主题'
  if (form.goal.trim().length < 8) return '请补充学习目标'
  return '可以生成路径'
})

const submitStateDesc = computed(() => {
  if (!form.topic.trim()) return '主题用于确定路径标题和规划范围。'
  if (form.goal.trim().length < 8) return '目标至少需要说明想学什么或为什么学。'
  return '提交后会在当前页面展示生成动画，完成后再进入路径节点页面。'
})

const currentPlanningIndex = computed(() => {
  for (let i = planningSteps.length - 1; i >= 0; i -= 1) {
    const step = planningSteps[i]

    if (step && planningProgress.value >= step.threshold) {
      return i
    }
  }

  return 0
})

const currentPlanningStep = computed(() => {
  return planningSteps[currentPlanningIndex.value] ?? planningSteps[0] ?? fallbackPlanningStep
})

const currentPlanningTitle = computed(() => {
  return currentPlanningStep.value.title
})

const currentPlanningDesc = computed(() => {
  return currentPlanningStep.value.desc
})

function autoResize() {
  if (!goalRef.value) return
  goalRef.value.style.height = 'auto'
  goalRef.value.style.height = `${Math.min(goalRef.value.scrollHeight, 150)}px`
}

function addKnowledge() {
  const value = knowledgeInput.value.trim()
  if (!value) return

  if (!form.currentKnowledge.includes(value)) {
    form.currentKnowledge.push(value)
  }

  knowledgeInput.value = ''
}

function removeKnowledge(value: string) {
  form.currentKnowledge = form.currentKnowledge.filter(item => item !== value)
}

function removeLastKnowledge() {
  if (knowledgeInput.value || !form.currentKnowledge.length) return
  form.currentKnowledge.pop()
}

function toggleKnowledge(value: string) {
  if (form.currentKnowledge.includes(value)) {
    removeKnowledge(value)
    return
  }

  form.currentKnowledge.push(value)
}

function toggleFocus(value: Focus) {
  if (form.focus.includes(value)) {
    if (form.focus.length === 1) {
      toast.warning('至少保留一个规划重点')
      return
    }

    form.focus = form.focus.filter(item => item !== value)
    return
  }

  form.focus.push(value)
}

function isExampleActive(item: ExampleItem) {
  return form.topic === item.topic && form.goal === item.goal
}

function applyExample(item: ExampleItem) {
  form.topic = item.topic
  form.goal = item.goal
  form.currentKnowledge = [...item.currentKnowledge]
  form.scene = item.scene
  form.pace = item.pace
  form.granularity = item.granularity
  form.focus = [...item.focus]

  nextTick(autoResize)
}

function resetForm() {
  form.topic = ''
  form.goal = ''
  form.currentKnowledge = []
  form.scene = 'general'
  form.pace = 'normal'
  form.granularity = 'standard'
  form.focus = ['key_points']
  knowledgeInput.value = ''

  nextTick(autoResize)
}

function goHistory() {
  router.push('/path-planner/history')
}

function buildPayload(): PathRequest {
  return {
    goal: form.goal.trim(),
    topic: form.topic.trim(),
    current_knowledge: [...form.currentKnowledge],
    preferences: {
      use_profile: true,
      learning_scene: form.scene,
      pace: form.pace,
      granularity: form.granularity,
      focus: [...form.focus],
      resource_generation_mode: 'node_on_demand',
      entry_source: 'path_entry_structured_form',
    },
  }
}

function clearProgressTimer() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer)
    progressTimer = null
  }
}

function addPlanningLog(message: string) {
  if (planningLogs.value.includes(message)) return
  planningLogs.value = [...planningLogs.value, message].slice(-6)
}

function startProgressAnimation() {
  clearProgressTimer()

  planningProgress.value = 6
  planningLogs.value = ['路径任务已创建，正在启动规划流程']

  progressTimer = window.setInterval(() => {
    if (planningProgress.value < 28) {
      planningProgress.value += 3.2
    } else if (planningProgress.value < 58) {
      planningProgress.value += 2.1
    } else if (planningProgress.value < 82) {
      planningProgress.value += 1.2
    } else if (planningProgress.value < 94) {
      planningProgress.value += 0.45
    }

    if (planningProgress.value >= 12) addPlanningLog('正在读取学习画像与规划参数')
    if (planningProgress.value >= 34) addPlanningLog('正在拆解学习阶段')
    if (planningProgress.value >= 58) addPlanningLog('正在生成学习节点和依赖关系')
    if (planningProgress.value >= 78) addPlanningLog('正在校验路径结构')
    if (planningProgress.value >= 92) addPlanningLog('正在等待后端保存结果')
  }, 700)
}

function resetPlanningState() {
  clearProgressTimer()
  pollingStopped = true
  isPlanning.value = false
  isSubmitting.value = false
  planningPathId.value = null
  planningRunId.value = ''
  planningProgress.value = 0
  planningLogs.value = []
  planningError.value = ''
}

function delay(ms: number) {
  return new Promise<void>(resolve => {
    window.setTimeout(resolve, ms)
  })
}

async function waitForPathReady(pathId: number, runId: string) {
  const startedAt = Date.now()
  const timeoutMs = 180_000

  while (!pollingStopped) {
    await delay(1600)

    if (Date.now() - startedAt > timeoutMs) {
      throw new Error('路径生成等待超时，请稍后在历史路径中查看结果')
    }

    const detailRes = await getLearningPathById(pathId)
    const detail = detailRes.data.data

    if (detail.status === 'failed') {
      throw new Error('路径规划失败，请修改输入后重试')
    }

    const hasNodes = Array.isArray(detail.nodes) && detail.nodes.length > 0
    const isReady = ['active', 'completed'].includes(detail.status)

    if (isReady && hasNodes) {
      clearProgressTimer()
      planningProgress.value = 100
      addPlanningLog('学习路径生成完成，正在进入路径节点页面')

      await delay(650)

      router.push({
        path: `/path-planner/overview/${pathId}`,
        query: {
          run_id: runId,
          status: detail.status,
        },
      })

      return
    }
  }
}

async function handleSubmit() {
  if (isSubmitting.value || isPlanning.value) return

  if (!form.topic.trim()) {
    toast.warning('请输入学习主题')
    return
  }

  if (!form.goal.trim()) {
    toast.warning('请输入学习目标')
    return
  }

  if (form.goal.trim().length < 8) {
    toast.warning('学习目标太短，请补充学习内容或目标')
    return
  }

  isSubmitting.value = true
  isPlanning.value = true
  planningError.value = ''
  pollingStopped = false
  startProgressAnimation()

  try {
    const result = await createLearningPath(buildPayload())
    const data = result.data.data
    const pathId = data.id
    const runId = data.run_id || ''

    if (!pathId) {
      throw new Error('后端未返回路径 ID')
    }

    planningPathId.value = pathId
    planningRunId.value = runId

    addPlanningLog('后端已接收路径任务，正在后台生成路径')
    toast.success('路径任务已创建，正在规划')

    await waitForPathReady(pathId, runId)
  } catch (error) {
    clearProgressTimer()
    const message = error instanceof Error ? error.message : '学习路径创建失败'
    planningError.value = message
    planningProgress.value = Math.min(planningProgress.value, 96)
    toast.error(message)
  } finally {
    isSubmitting.value = false
  }
}

onBeforeUnmount(() => {
  pollingStopped = true
  clearProgressTimer()
})
</script>

<style scoped>
.path-entry-page {
  min-height: calc(100vh - var(--navbar-height, 72px));
  background:
      radial-gradient(circle at 12% 8%, rgba(216, 241, 240, 0.3), transparent 28%),
      radial-gradient(circle at 88% 12%, rgba(245, 243, 255, 0.26), transparent 26%),
      #fbfefe;
  color: var(--color-text, #173b42);
}

.entry-shell {
  width: min(1500px, calc(100vw - 48px));
  margin: 0 auto;
  padding: 26px 0 34px;
  background: rgba(255, 255, 255, 0.34);
}

.entry-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.eyebrow,
.side-kicker,
.planning-kicker {
  display: inline-flex;
  color: #5b6ee1;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.entry-header h1 {
  margin: 6px 0 0;
  color: var(--color-text-strong, #173b42);
  font-size: 32px;
  line-height: 1.15;
  letter-spacing: -0.045em;
}

.entry-header p {
  max-width: 820px;
  margin: 10px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 14px;
  line-height: 1.7;
}

.history-button {
  height: 38px;
  padding: 0 16px;
  border: 1px solid rgba(200, 228, 227, 0.72);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-text, #173b42);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.history-button:hover:not(:disabled) {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary-soft, #d8f1f0);
}

.history-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.entry-body {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 330px;
  gap: 28px;
  padding-top: 24px;
}

.example-rail {
  min-width: 0;
  padding-right: 22px;
  border-right: 1px solid rgba(200, 228, 227, 0.48);
}

.example-rail-header {
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.example-rail-header h2 {
  margin: 8px 0 0;
  color: var(--color-text-strong, #173b42);
  font-size: 20px;
  line-height: 1.25;
  letter-spacing: -0.025em;
}

.example-rail-header p {
  margin: 8px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  line-height: 1.6;
}

.example-list {
  padding-top: 10px;
}

.example-row {
  width: 100%;
  min-height: 64px;
  padding: 12px 0;
  border: 0;
  border-bottom: 1px solid rgba(200, 228, 227, 0.44);
  border-radius: 0;
  background: transparent;
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  text-align: left;
  cursor: pointer;
  transition: var(--transition-fast, 0.2s ease);
}

.example-row:hover:not(:disabled),
.example-row.active {
  padding-left: 8px;
  background: linear-gradient(90deg, rgba(216, 241, 240, 0.34), transparent);
}

.example-row:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}

.example-dot {
  width: 7px;
  height: 7px;
  margin-top: 6px;
  border-radius: 999px;
  background: currentColor;
}

.example-row.teal {
  color: #46b8b4;
}

.example-row.blue {
  color: #5b6ee1;
}

.example-row.amber {
  color: #f59e0b;
}

.example-row.violet {
  color: #8b5cf6;
}

.example-row strong {
  display: block;
  color: var(--color-text-strong, #173b42);
  font-size: 14px;
  line-height: 1.35;
}

.example-row em {
  display: block;
  margin-top: 4px;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-style: normal;
}

.form-panel,
.planning-panel {
  min-width: 0;
  border-top: 1px solid rgba(200, 228, 227, 0.48);
}

.form-section {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 28px;
  padding: 24px 0;
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.section-title {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  align-items: flex-start;
}

.section-title > span {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(200, 228, 227, 0.72);
  color: var(--color-primary-text, #205f67);
  font-size: 12px;
  font-weight: 800;
}

.section-title h2 {
  margin: 0;
  color: var(--color-text-strong, #173b42);
  font-size: 18px;
  line-height: 1.3;
  letter-spacing: -0.02em;
}

.section-title p {
  margin: 7px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  line-height: 1.65;
}

.field-row {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}

.field-row.align-start {
  align-items: flex-start;
}

.field-row label,
.pref-group label {
  color: var(--color-text-strong, #173b42);
  font-size: 13px;
  font-weight: 700;
}

.field-control {
  min-width: 0;
}

.field-control input,
.field-control textarea {
  width: 100%;
  border: 1px solid rgba(200, 228, 227, 0.78);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--color-text, #173b42);
  outline: none;
  font: inherit;
  transition: var(--transition-fast, 0.2s ease);
  box-sizing: border-box;
}

.field-control input {
  height: 44px;
  padding: 0 14px;
}

.field-control textarea {
  min-height: 104px;
  max-height: 150px;
  resize: none;
  padding: 13px 14px;
  line-height: 1.75;
}

.field-control input:focus,
.field-control textarea:focus {
  border-color: var(--color-primary, #46b8b4);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.12);
  background: rgba(255, 255, 255, 0.96);
}

.field-control p,
.field-footer p {
  margin: 7px 0 0;
  color: var(--color-text-faint, #8da4a8);
  font-size: 12px;
  line-height: 1.55;
}

.field-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.field-footer span {
  margin-top: 7px;
  color: var(--color-text-faint, #8da4a8);
  font-size: 12px;
}

.knowledge-input {
  min-height: 44px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid rgba(200, 228, 227, 0.78);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  box-sizing: border-box;
}

.knowledge-input:focus-within {
  border-color: var(--color-primary, #46b8b4);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.12);
  background: rgba(255, 255, 255, 0.96);
}

.knowledge-input input {
  flex: 1;
  min-width: 210px;
  height: 28px;
  border: 0;
  padding: 0;
  box-shadow: none;
  background: transparent;
}

.knowledge-input input:focus {
  box-shadow: none;
}

.knowledge-tag {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 8px 0 10px;
  border-radius: 999px;
  background: var(--color-primary-soft, #d8f1f0);
  color: var(--color-primary-text, #205f67);
  font-size: 12px;
  font-weight: 700;
}

.knowledge-tag button {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 15px;
}

.quick-knowledge {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.quick-knowledge button,
.choice-line button {
  height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(200, 228, 227, 0.72);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: var(--transition-fast, 0.2s ease);
}

.quick-knowledge button:hover,
.choice-line button:hover {
  border-color: var(--color-primary, #46b8b4);
  color: var(--color-primary-text, #205f67);
  background: rgba(255, 255, 255, 0.92);
}

.quick-knowledge button.selected,
.choice-line button.selected {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary-soft, #d8f1f0);
  color: var(--color-primary-text, #205f67);
}

.preference-grid {
  display: grid;
  gap: 18px;
}

.pref-group {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}

.choice-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.submit-bar {
  min-height: 78px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
  padding: 18px 0 0;
}

.submit-info strong {
  display: block;
  color: var(--color-text-strong, #173b42);
  font-size: 15px;
}

.submit-info span {
  display: block;
  margin-top: 4px;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
}

.submit-actions {
  display: flex;
  gap: 10px;
}

.secondary-button,
.primary-button {
  height: 40px;
  border-radius: 14px;
  padding: 0 18px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.secondary-button {
  border: 1px solid rgba(200, 228, 227, 0.72);
  background: rgba(255, 255, 255, 0.66);
  color: var(--color-text, #173b42);
}

.secondary-button:hover {
  border-color: var(--color-primary, #46b8b4);
  background: rgba(255, 255, 255, 0.92);
}

.primary-button {
  border: 1px solid rgba(32, 95, 103, 0.16);
  background: linear-gradient(135deg, #46b8b4, #5b6ee1);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(70, 184, 180, 0.14);
}

.primary-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.primary-button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
  box-shadow: none;
}

.planning-panel {
  padding-top: 24px;
}

.planning-head {
  padding-bottom: 22px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.planning-head h2 {
  margin: 8px 0 0;
  color: var(--color-text-strong, #173b42);
  font-size: 28px;
  line-height: 1.18;
  letter-spacing: -0.04em;
}

.planning-head p {
  max-width: 720px;
  margin: 10px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 14px;
  line-height: 1.7;
}

.planning-visual {
  padding: 34px 0 26px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.route-orbit {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.orbit-line {
  position: absolute;
  left: 5%;
  right: 5%;
  top: 25px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, #46b8b4, #5b6ee1, #f59e0b, #8b5cf6, #46b8b4);
  opacity: 0.34;
}

.orbit-step {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 10px;
  text-align: center;
  color: var(--color-text-faint, #8da4a8);
}

.orbit-step span {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  border: 2px solid currentColor;
  background: #ffffff;
  color: currentColor;
  font-size: 13px;
  font-weight: 800;
  transition: var(--transition-base, 0.4s ease);
}

.orbit-step strong {
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  line-height: 1.35;
}

.orbit-step.done.teal,
.orbit-step.active.teal {
  color: #46b8b4;
}

.orbit-step.done.blue,
.orbit-step.active.blue {
  color: #5b6ee1;
}

.orbit-step.done.amber,
.orbit-step.active.amber {
  color: #f59e0b;
}

.orbit-step.done.violet,
.orbit-step.active.violet {
  color: #8b5cf6;
}

.orbit-step.done span,
.orbit-step.active span {
  box-shadow: 0 12px 26px rgba(32, 95, 103, 0.12);
}

.orbit-step.active span {
  animation: pulseStep 1.4s ease-in-out infinite;
}

@keyframes pulseStep {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(70, 184, 180, 0.18);
  }
  50% {
    transform: scale(1.06);
    box-shadow: 0 0 0 8px rgba(70, 184, 180, 0.08);
  }
}

.planning-progress {
  padding: 24px 0 0;
}

.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.progress-head span {
  color: var(--color-text-strong, #173b42);
  font-size: 14px;
  font-weight: 800;
}

.progress-head strong {
  color: var(--color-primary-text, #205f67);
  font-size: 14px;
}

.progress-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(200, 228, 227, 0.46);
}

.progress-track i {
  height: 100%;
  display: block;
  border-radius: inherit;
  background: linear-gradient(90deg, #46b8b4, #5b6ee1);
  transition: width 0.45s ease;
}

.planning-log {
  margin-top: 20px;
  display: grid;
  gap: 10px;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
}

.log-item i {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--color-primary, #46b8b4);
}

.log-enter-active,
.log-leave-active {
  transition: all 0.2s ease;
}

.log-enter-from,
.log-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.planning-error {
  margin-top: 22px;
  padding: 16px 18px;
  border: 1px solid rgba(196, 61, 91, 0.2);
  border-radius: 16px;
  background: var(--color-danger-soft, #fff1f4);
}

.planning-error strong {
  display: block;
  color: var(--color-danger, #c43d5b);
  font-size: 14px;
}

.planning-error p {
  margin: 6px 0 12px;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
}

.planning-error button {
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(196, 61, 91, 0.24);
  border-radius: 12px;
  background: #ffffff;
  color: var(--color-danger, #c43d5b);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.side-panel {
  min-width: 0;
  padding-left: 24px;
  border-left: 1px solid rgba(200, 228, 227, 0.48);
  background: transparent;
}

.side-section {
  padding-bottom: 22px;
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.side-section h2 {
  margin: 10px 0 0;
  color: var(--color-text-strong, #173b42);
  font-size: 25px;
  line-height: 1.18;
  letter-spacing: -0.035em;
  word-break: break-word;
}

.side-section p {
  margin: 10px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 13px;
  line-height: 1.7;
}

.side-table {
  border-bottom: 1px solid rgba(200, 228, 227, 0.48);
}

.side-table div {
  min-height: 54px;
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  align-items: center;
  border-bottom: 1px solid rgba(200, 228, 227, 0.42);
}

.side-table div:last-child {
  border-bottom: 0;
}

.side-table span {
  color: var(--color-text-faint, #8da4a8);
  font-size: 12px;
  font-weight: 700;
}

.side-table strong {
  color: var(--color-text-strong, #173b42);
  font-size: 14px;
  text-align: right;
  word-break: break-word;
}

.path-only-section {
  padding-top: 22px;
}

.logic-list {
  margin-top: 16px;
}

.logic-item {
  padding: 12px 0 12px 14px;
  border-left: 3px solid currentColor;
  border-bottom: 1px solid rgba(200, 228, 227, 0.42);
}

.logic-item.teal {
  color: #46b8b4;
}

.logic-item.blue {
  color: #5b6ee1;
}

.logic-item.amber {
  color: #f59e0b;
}

.logic-item strong {
  display: block;
  color: var(--color-text-strong, #173b42);
  font-size: 14px;
}

.logic-item p {
  margin: 4px 0 0;
  color: var(--color-text-secondary, #58747a);
  font-size: 12px;
  line-height: 1.55;
}

@media (max-width: 1280px) {
  .entry-body {
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .side-panel {
    grid-column: 1 / -1;
    border-left: 0;
    border-top: 1px solid rgba(200, 228, 227, 0.48);
    padding-left: 0;
    padding-top: 24px;
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr) 280px;
    gap: 24px;
  }

  .side-section,
  .side-table {
    border-bottom: 0;
  }

  .path-only-section {
    padding-top: 0;
  }
}

@media (max-width: 920px) {
  .entry-shell {
    width: min(100vw - 28px, 760px);
  }

  .entry-header {
    display: block;
  }

  .history-button {
    margin-top: 16px;
  }

  .entry-body {
    grid-template-columns: 1fr;
  }

  .example-rail {
    padding-right: 0;
    border-right: 0;
    border-bottom: 1px solid rgba(200, 228, 227, 0.48);
    padding-bottom: 18px;
  }

  .example-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0 18px;
  }

  .form-section {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .field-row,
  .pref-group {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .submit-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .submit-actions {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr;
  }

  .secondary-button,
  .primary-button {
    width: 100%;
  }

  .side-panel {
    grid-template-columns: 1fr;
  }

  .route-orbit {
    grid-template-columns: 1fr;
  }

  .orbit-line {
    display: none;
  }

  .orbit-step {
    display: grid;
    grid-template-columns: 52px minmax(0, 1fr);
    justify-items: start;
    text-align: left;
  }
}

@media (max-width: 620px) {
  .example-list {
    grid-template-columns: 1fr;
  }

  .field-footer {
    display: block;
  }

  .entry-header h1 {
    font-size: 28px;
  }
}
</style>