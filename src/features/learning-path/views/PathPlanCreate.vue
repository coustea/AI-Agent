<template>
  <main class="page-container path-planner-page">
    <div class="planner-unified-container">

      <header class="workspace-brand-header">
        <div class="header-headline-group">
          <span class="agent-eyebrow">PATH PLANNER AI ENGINE</span>
          <h1>创建学习路径</h1>
          <p class="cognitive-subtext">
            自定义您专属的主题、目标与偏好。智能引擎将自动构建清晰的阶段性知识图谱与高维前置依赖节点。
          </p>
        </div>
        <div class="header-action-group">
          <button class="btn-outline btn-sm" type="button" :disabled="isPlanning" @click="goHistory">
            <span>历史路径记录</span>
            <ph-arrow-right class="arrow-symbol" :size="12" weight="bold" />
          </button>
        </div>
      </header>

      <div class="workspace-content-flow">

        <section class="horizontal-templates-gallery">
          <div class="gallery-title-strip">
            <h4>常用路径模板</h4>
            <span>一键载入行业标准参数配置</span>
          </div>
          <div class="templates-horizontal-grid">
            <button
                v-for="item in examples"
                :key="item.title"
                type="button"
                class="micro-template-gallery-card"
                :class="[item.tone, { active: isExampleActive(item) }]"
                @click="applyExample(item)"
            >
              <span class="category-glow-dot"></span>
              <div class="micro-card-meta">
                <strong>{{ item.title }}</strong>
                <span>{{ item.topic }}</span>
              </div>
            </button>
          </div>
        </section>

        <div class="panel structured-form-panel">

          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">01</span>
              <div class="row-headline-group">
                <h3 class="row-title-group">
                  <ph-tag :size="16" class="title-icon" />
                  <span>学习主题</span>
                </h3>
                <p>确定您要攻克或深入探究的核心科目或特定技术方向。</p>
              </div>
            </div>
            <div class="row-control-pane">
              <div class="input-container-box">
                <input
                    id="topic"
                    v-model.trim="form.topic"
                    maxlength="60"
                    type="text"
                    placeholder="例如：操作系统、数据结构、计算机网络、Vue3"
                />
              </div>
            </div>
          </div>

          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">02</span>
              <div class="row-headline-group">
                <h3 class="row-title-group">
                  <ph-target :size="16" class="title-icon" />
                  <span>学习目标</span>
                </h3>
                <p>说明您的学习动机、考察或应用重点以及期望达到的熟练度。</p>
              </div>
            </div>
            <div class="row-control-pane">
              <div class="textarea-container-box">
                <textarea
                    id="goal"
                    ref="goalRef"
                    v-model.trim="form.goal"
                    maxlength="500"
                    rows="3"
                    placeholder="例如：系统复习操作系统核心考点，重点掌握进程同步、死锁、内存管理和页面置换，用来准备期末考试。"
                    @input="autoResize"
                />
                <div class="textarea-info-bar">
                  <span>建议包含：学习目的、重点范围、预期掌握程度。</span>
                  <span class="char-counter">{{ form.goal.length }}/500</span>
                </div>
              </div>
            </div>
          </div>

          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">03</span>
              <div class="row-headline-group">
                <h3 class="row-title-group">
                  <ph-brain :size="16" class="title-icon" />
                  <span>当前基础</span>
                </h3>
                <p>添加已掌握的先修知识，使规划出的路线起点更平滑贴合。</p>
              </div>
            </div>
            <div class="row-control-pane">
              <div class="tag-input-bezel-box">
                <div class="tag-inner-flex">
                  <span
                      v-for="item in form.currentKnowledge"
                      :key="item"
                      class="custom-tag-node"
                  >
                    {{ item }}
                    <button type="button" class="tag-close-trigger" @click="removeKnowledge(item)">
                      <ph-x :size="10" />
                    </button>
                  </span>
                  <input
                      v-model.trim="knowledgeInput"
                      type="text"
                      placeholder="输入后按 Enter 或失去焦点添加"
                      @keydown.enter.prevent="addKnowledge"
                      @keydown.backspace="removeLastKnowledge"
                      @blur="addKnowledge"
                  />
                </div>
              </div>

              <div class="quick-tags-container">
                <button
                    v-for="item in quickKnowledge"
                    :key="item"
                    type="button"
                    class="btn-pill"
                    :class="{ active: form.currentKnowledge.includes(item) }"
                    @click="toggleKnowledge(item)"
                >
                  {{ item }}
                </button>
              </div>
            </div>
          </div>

          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">04</span>
              <div class="row-headline-group">
                <h3 class="row-title-group">
                  <ph-sliders :size="16" class="title-icon" />
                  <span>学习偏好</span>
                </h3>
                <p>个性化偏好参数将被注入生成算法以调校路径走向。</p>
              </div>
            </div>
            <div class="row-control-pane preferences-matrix">

              <div class="preference-flex-line">
                <label class="pref-field-label">学习场景</label>
                <div class="segmented-pill-group">
                  <button
                      v-for="item in sceneOptions"
                      :key="item.value"
                      type="button"
                      class="btn-pill"
                      :class="{ active: form.scene === item.value }"
                      @click="form.scene = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="preference-flex-line">
                <label class="pref-field-label">学习节奏</label>
                <div class="segmented-pill-group">
                  <button
                      v-for="item in paceOptions"
                      :key="item.value"
                      type="button"
                      class="btn-pill"
                      :class="{ active: form.pace === item.value }"
                      @click="form.pace = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="preference-flex-line">
                <label class="pref-field-label">路径粒度</label>
                <div class="segmented-pill-group">
                  <button
                      v-for="item in granularityOptions"
                      :key="item.value"
                      type="button"
                      class="btn-pill"
                      :class="{ active: form.granularity === item.value }"
                      @click="form.granularity = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="preference-flex-line">
                <label class="pref-field-label">规划重点</label>
                <div class="segmented-pill-group focus-accent-group">
                  <button
                      v-for="item in focusOptions"
                      :key="item.value"
                      type="button"
                      class="btn-pill"
                      :class="[item.value, { active: form.focus.includes(item.value) }]"
                      @click="toggleFocus(item.value)"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

            </div>
          </div>

          <footer class="form-action-footer">
            <div class="ai-readiness-inline-dashboard" :class="{ 'is-ready': canSubmit }">
              <div class="dashboard-visual-pulse">
                <div class="pulse-ring"></div>
                <div class="pulse-center-core"></div>
              </div>
              <div class="dashboard-inline-meta">
                <template v-if="canSubmit">
                  <strong>{{ submitStateTitle }}</strong>
                  <p>{{ submitStateDesc }}</p>
                </template>
                <template v-else>
                  <strong>规划参数未就绪</strong>
                  <p>请补全左侧<span :class="{ 'lack': !form.topic.trim() }">学习主题</span>与<span :class="{ 'lack': form.goal.trim().length < 8 }">目标诉求</span>以激活引擎。</p>
                </template>
              </div>
            </div>

            <div class="footer-buttons-cluster">
              <button class="btn-outline" type="button" @click="resetForm">
                <ph-arrow-clockwise :size="14" />
                <span>重置</span>
              </button>
              <button
                  class="btn-primary custom-premium-action"
                  type="button"
                  :disabled="!canSubmit || isSubmitting"
                  @click="handleSubmit"
              >
                <ph-sparkle v-if="!isSubmitting" :size="14" weight="fill" />
                <span v-if="!isSubmitting">生成学习路径</span>
                <span v-else>正在规划结构...</span>
              </button>
            </div>
          </footer>
        </div>

        <footer class="workspace-flow-footnote">
          <div class="agile-notice-banner-box">
            <span class="mini-badge">AGILE GENERATION SPECIFICATION</span>
            <p>当前步骤仅负责智能化解构学习路线骨架（包括学习阶段、核心节点顺序与前置依赖锁定）。各节点内部的精细化视频教程、前沿知识图谱、实操代码演练及自测题库均在后续进入具体节点页时按需弹性、瞬时全自动生成。</p>
          </div>
        </footer>
      </div>

      <transition name="modal-fade">
        <div v-if="isPlanning" class="student-planning-modal-backdrop">
          <div class="student-planning-modal-content">

            <div class="modal-loading-header">
              <div class="premium-sparkle-loader">
                <div class="spinner-double-ring"></div>
                <ph-sparkle :size="24" class="sparkle-center-icon animate-pulse" weight="fill" />
              </div>
              <h2>AI 正在为您量身定制学习路径</h2>
              <p>请稍候，我们正在梳理最佳的知识拓扑顺序...</p>
            </div>

            <div class="student-timeline-track">
              <div
                  v-for="(step, index) in planningSteps"
                  :key="step.key"
                  class="student-timeline-node"
                  :class="{
                  'is-active': currentPlanningIndex === index,
                  'is-done': currentPlanningIndex > index
                }"
              >
                <div class="node-circle-indicator">
                  <ph-check v-if="currentPlanningIndex > index" :size="12" weight="bold" />
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <span class="node-text-label">{{ step.title }}</span>
                <div v-if="index < planningSteps.length - 1" class="node-connecting-dash"></div>
              </div>
            </div>

            <div class="student-progress-dashboard">
              <div class="progress-bar-minimal">
                <div class="progress-bar-minimal-fill" :style="{ width: `${planningProgress}%` }"></div>
              </div>
              <div class="progress-percent-count">
                已编排 <span>{{ Math.round(planningProgress) }}%</span>
              </div>
            </div>

            <div class="student-friendly-log-box">
              <transition-group name="log-item-fade">
                <div v-for="(message, index) in planningLogs" :key="`${message}-${index}`" class="friendly-log-row">
                  <span class="friendly-log-dot"></span>
                  <span class="friendly-log-text">{{ message }}</span>
                </div>
              </transition-group>
            </div>

            <div v-if="planningError" class="student-error-box">
              <div class="error-meta-flex">
                <ph-warning-circle :size="18" weight="fill" />
                <div>
                  <strong>规划路径时遇到了一点小状况</strong>
                  <p>{{ planningError }}</p>
                </div>
              </div>
              <button type="button" class="btn-modal-back" @click="resetPlanningState">
                返回修改参数
              </button>
            </div>

          </div>
        </div>
      </transition>

    </div>
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
  threshold: number
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

// 面向学生精简的步骤名称
const planningSteps: PlanningStep[] = [
  { key: 'profile', title: '结合学术画像', threshold: 12 },
  { key: 'stage', title: '拆解学习阶段', threshold: 34 },
  { key: 'node', title: '编排知识节点', threshold: 58 },
  { key: 'validate', title: '校验图谱结构', threshold: 78 },
  { key: 'save', title: '生成完美路线', threshold: 92 },
]

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

const submitStateTitle = computed(() => {
  if (!form.topic.trim()) return '请先填写学习主题'
  if (form.goal.trim().length < 8) return '请补充学习目标'
  return '架构参数完整，可以开始生成'
})

const submitStateDesc = computed(() => {
  if (!form.topic.trim()) return '核心主题用作算法推演 and 确定路径大纲。'
  if (form.goal.trim().length < 8) return '请至少输入 8 个字以上的目标诉求描述。'
  return '点击提交后，智能引擎将调取您的学术画像数据并实时输出骨架方案。'
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

function autoResize() {
  if (!goalRef.value) return
  goalRef.value.style.height = 'auto'
  goalRef.value.style.height = `${Math.min(goalRef.value.scrollHeight, 150)}px`
}

function addKnowledge() {
  const value = knowledgeInput.value.trim()
  if (!value) return

  if (form.currentKnowledge.includes(value)) {
    toast.warning('请勿重复添加相同的先修知识')
    knowledgeInput.value = ''
    return
  }

  form.currentKnowledge.push(value)
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
  planningLogs.value = [...planningLogs.value, message].slice(-3)
}

function startProgressAnimation() {
  clearProgressTimer()
  planningProgress.value = 6
  planningLogs.value = ['✨ 智能路径任务已提交，开始构建路线啦']

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

    if (planningProgress.value >= 12) addPlanningLog('🎯 正在分析你的学习目标与已有基础偏好...')
    if (planningProgress.value >= 34) addPlanningLog('🌱 正在科学合理地为你切分学习的不同阶段...')
    if (planningProgress.value >= 58) addPlanningLog('🧩 正在精细安排路径内的知识核心节点...')
    if (planningProgress.value >= 78) addPlanningLog('🔮 正在智能校验路线的前后衔接与覆盖度...')
    if (planningProgress.value >= 92) addPlanningLog('🎈 完美！正在为您保存本次生成的专属路径...')
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
      throw new Error('路径规划因网络超时未能完成，请稍后前往历史路径查看。')
    }

    const detailRes = await getLearningPathById(pathId)
    const detail = detailRes.data.data

    if (detail.status === 'failed') {
      throw new Error('小主，系统规划路径失败了，请尝试换个表述或修改参数重试。')
    }

    const hasNodes = Array.isArray(detail.nodes) && detail.nodes.length > 0
    const isReady = ['active', 'completed'].includes(detail.status)

    if (isReady && hasNodes) {
      clearProgressTimer()
      planningProgress.value = 100
      addPlanningLog('🎉 路径大纲设计完毕，正在为你开启总览看板...')

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
      throw new Error('服务器开小差了，未成功分发路径标识。')
    }

    planningPathId.value = pathId
    planningRunId.value = runId

    await waitForPathReady(pathId, runId)
  } catch (error) {
    clearProgressTimer()
    const message = error instanceof Error ? error.message : '智能规划未能成功拉起'
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
/* ============================================================
   页面根布局与一体化流式容器重塑
   ============================================================ */
.path-planner-page {
  background-color: var(--color-bg);
  box-sizing: border-box;
}

.planner-unified-container {
  max-width: var(--content-max-width, 1120px);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6, 24px);
}

/* 一体化顶层头部 */
.workspace-brand-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: var(--space-4, 16px) var(--space-1, 4px) var(--space-2, 8px);
}
.header-headline-group {
  max-width: 75%;
}
.agent-eyebrow {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  font-weight: var(--weight-bold, 700);
  color: var(--color-primary, #46b8b4);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
.workspace-brand-header h1 {
  font-size: var(--text-2xl, 24px);
  font-weight: var(--weight-extrabold, 800);
  color: var(--color-text-strong, #1a1a1a);
  margin: var(--space-1, 4px) 0 var(--space-2, 8px);
}
.cognitive-subtext {
  margin: 0;
  font-size: var(--text-sm, 14px);
  color: var(--color-text-secondary, #666);
  line-height: var(--leading-normal, 1.5);
}
.arrow-symbol {
  font-weight: var(--weight-extrabold, 800);
  margin-left: var(--space-1, 4px);
  transition: transform 0.2s cubic-bezier(0.32, 0.72, 0, 1);
}
.header-action-group button:hover .arrow-symbol {
  transform: translateX(3px);
}

/* ============================================================
   常用模板横向快捷画廊
   ============================================================ */
.horizontal-templates-gallery {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
  padding: 0 var(--space-1, 4px);
  margin-bottom: 12px;
}
.gallery-title-strip {
  display: flex;
  align-items: baseline;
  gap: var(--space-2, 8px);
}
.gallery-title-strip h4 {
  font-size: var(--text-xs, 12px);
  font-weight: var(--weight-extrabold, 800);
  color: var(--color-text-strong, #1a1a1a);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}
.gallery-title-strip span {
  font-size: 11px;
  color: var(--color-text-faint, #999);
}
.templates-horizontal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4, 16px);
}
.micro-template-gallery-card {
  background: var(--color-surface, #fff);
  border: 1.5px solid var(--color-border-light, #eee);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  display: flex;
  align-items: center;
  gap: var(--space-3, 12px);
  text-align: left;
  cursor: pointer;
  box-sizing: border-box;
  transition: var(--transition-base, all 0.2s ease);
  height: 64px;
}
.micro-template-gallery-card:hover {
  border-color: var(--color-border-hover, #ccc);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05));
  transform: translateY(-2px);
}
.micro-template-gallery-card.active {
  border-color: currentColor;
  box-shadow: var(--shadow-md, 0 4px 6px rgba(0,0,0,0.05)), 0 0 12px var(--color-primary-soft, rgba(70,184,180,0.1));
  background: var(--color-surface, #fff);
  transform: translateY(-2px);
}
.category-glow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.micro-card-meta {
  min-width: 0;
  flex: 1;
}
.micro-card-meta strong {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-strong, #1a1a1a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.micro-card-meta span {
  display: block;
  font-size: 11px;
  color: var(--color-text-secondary, #666);
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.micro-template-gallery-card.teal { color: var(--color-primary, #46b8b4); }
.micro-template-gallery-card.blue { color: var(--cat-tutor, #1e40af); }
.micro-template-gallery-card.amber { color: var(--cat-path, #f59e0b); }
.micro-template-gallery-card.violet { color: var(--cat-eval, #7c3aed); }

/* ============================================================
   核心工作表单面板
   ============================================================ */
.structured-form-panel {
  display: flex;
  flex-direction: column;
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border-light, #eee);
  border-radius: var(--radius-lg, 12px);
  padding: var(--space-8, 32px);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05));
}

.form-grid-row {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: var(--space-6, 24px);
  padding: var(--space-6, 24px) 0;
  border-bottom: 1px solid var(--color-border-light, #eee);
}
.form-grid-row:first-child { padding-top: 0; }

.row-meta-pane {
  display: flex;
  gap: var(--space-3, 12px);
}
.row-badge-num {
  width: 28px;
  height: 28px;
  background: var(--color-primary-soft, rgba(70,184,180,0.1));
  border: 1.5px solid var(--color-primary-border, #46b8b4);
  color: var(--color-primary-text, #205f67);
  border-radius: var(--radius-sm, 4px);
  display: grid;
  place-items: center;
  font-family: var(--font-mono, monospace);
  font-size: var(--text-xs, 12px);
  font-weight: var(--weight-bold, 700);
  flex-shrink: 0;
}
.row-headline-group h3 {
  font-size: var(--text-base, 16px);
  font-weight: var(--weight-bold, 700);
  color: var(--color-text-strong, #1a1a1a);
  margin: 2px 0 0;
}
.row-title-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1_5, 6px);
}
.title-icon {
  color: var(--color-primary-text, #205f67);
  opacity: 0.85;
  flex-shrink: 0;
}
.row-headline-group p {
  margin: var(--space-2, 8px) 0 0;
  font-size: var(--text-xs, 12px);
  color: var(--color-text-muted, #888);
  line-height: var(--leading-normal, 1.5);
}

.input-container-box input,
.textarea-container-box textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1.5px solid var(--color-border, #ddd);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-bg, #fafafa);
  color: var(--color-text, #333);
  font-family: inherit;
  font-size: var(--text-sm, 14px);
  outline: none;
  transition: var(--transition-base, all 0.2s ease);
}
.input-container-box input {
  height: 42px;
  padding: 0 var(--space-4, 16px);
}
.textarea-container-box textarea {
  padding: var(--space-3, 12px) var(--space-4, 16px);
  resize: none;
  min-height: 96px;
  line-height: var(--leading-normal, 1.5);
}
.input-container-box input:focus,
.textarea-container-box textarea:focus {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-page-bg, #fff);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.15);
}
.textarea-info-bar {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-1_5, 6px);
  font-size: var(--text-xs, 12px);
  color: var(--color-text-faint, #999);
}

.tag-input-bezel-box {
  border: 1.5px solid var(--color-border, #ddd);
  border-radius: var(--radius-sm, 4px);
  background: var(--color-bg, #fafafa);
  padding: var(--space-1_5, 6px) var(--space-3, 12px);
  min-height: 42px;
  box-sizing: border-box;
  transition: var(--transition-base, all 0.2s ease);
}
.tag-input-bezel-box:focus-within {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-page-bg, #fff);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.15);
}
.tag-inner-flex {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1_5, 6px);
  align-items: center;
}
.tag-inner-flex input {
  border: none;
  background: transparent;
  outline: none;
  font-family: inherit;
  font-size: var(--text-sm, 14px);
  color: var(--color-text, #333);
  padding: 4px 0;
  flex-grow: 1;
}
.custom-tag-node {
  background: var(--color-primary-soft, rgba(70,184,180,0.1));
  border: 1px solid var(--color-primary-border, #46b8b4);
  color: var(--color-primary-text, #205f67);
  padding: var(--space-0_5, 2px) var(--space-2_5, 10px);
  border-radius: 6px;
  font-size: var(--text-xs, 12px);
  font-weight: var(--weight-semibold, 600);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: var(--transition-fast, all 0.1s ease);
}
.custom-tag-node:hover {
  background: var(--color-primary-soft, rgba(70,184,180,0.1));
  border-color: var(--color-primary, #46b8b4);
}
.tag-close-trigger {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  opacity: 0.6;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast, all 0.1s ease);
}
.tag-close-trigger:hover {
  opacity: 1;
  transform: scale(1.1);
}
.quick-tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
  margin-top: var(--space-3, 12px);
}
.quick-tags-container .btn-pill {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #ddd);
  color: var(--color-text-secondary, #666);
  font-size: var(--text-xs, 12px);
  border-radius: var(--radius-pill, 50px);
  height: 28px;
  padding: 0 var(--space-3, 12px);
  cursor: pointer;
  transition: var(--transition-base, all 0.2s ease);
}
.quick-tags-container .btn-pill:hover {
  border-color: var(--color-border-hover, #ccc);
  color: var(--color-text-strong, #1a1a1a);
  transform: translateY(-1px);
}
.quick-tags-container .btn-pill.active {
  background-color: var(--color-primary-soft, rgba(70,184,180,0.1)) !important;
  border-color: var(--color-primary, #46b8b4) !important;
  color: var(--color-primary-text, #205f67) !important;
  font-weight: var(--weight-bold, 700);
}

.preferences-matrix {
  display: flex;
  flex-direction: column;
  gap: var(--space-5, 20px);
}
.preference-flex-line {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  align-items: center;
  gap: var(--space-3, 12px);
}
.pref-field-label {
  font-size: var(--text-sm, 14px);
  font-weight: var(--weight-bold, 700);
  color: var(--color-text-strong, #1a1a1a);
}
.segmented-pill-group {
  display: inline-flex;
  background: var(--color-bg, #fafafa);
  border: 1px solid var(--color-border-light, #eee);
  border-radius: var(--radius-pill, 50px);
  padding: 4px;
  gap: 4px;
}
.segmented-pill-group .btn-pill {
  background: transparent;
  border: none;
  color: var(--color-text-secondary, #666);
  font-size: var(--text-xs, 12px);
  font-weight: var(--weight-medium, 500);
  padding: 6px 14px;
  border-radius: var(--radius-pill, 50px);
  height: 28px;
  transition: var(--transition-fast, all 0.1s ease);
  cursor: pointer;
}
.segmented-pill-group .btn-pill:hover {
  color: var(--color-text-strong, #1a1a1a);
}
.segmented-pill-group .btn-pill.active {
  background-color: var(--color-surface, #fff) !important;
  border: 1px solid var(--color-primary-border, #46b8b4) !important;
  color: var(--color-primary-text, #205f67) !important;
  font-weight: var(--weight-bold, 700);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05));
}

.focus-accent-group {
  display: flex;
  flex-wrap: wrap;
  background: transparent;
  border: none;
  padding: 0;
  gap: var(--space-2_5, 10px);
}
.focus-accent-group .btn-pill {
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #ddd);
  color: var(--color-text-secondary, #666);
  font-size: var(--text-xs, 12px);
  font-weight: var(--weight-semibold, 600);
  padding: var(--space-2, 8px) var(--space-4, 16px);
  border-radius: var(--radius-sm, 4px);
  height: auto;
  cursor: pointer;
  transition: var(--transition-base, all 0.2s ease);
}
.focus-accent-group .btn-pill:hover {
  border-color: var(--color-border-hover, #ccc);
  color: var(--color-text-strong, #1a1a1a);
  transform: translateY(-1px);
}
.focus-accent-group .btn-pill.foundation.active {
  background-color: var(--cat-tutor-soft, rgba(30,64,175,0.08)) !important;
  border-color: var(--cat-tutor, #1e40af) !important;
  color: var(--cat-tutor, #1e40af) !important;
  box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.08);
}
.focus-accent-group .btn-pill.key_points.active {
  background-color: var(--cat-path-soft, rgba(245,158,11,0.08)) !important;
  border-color: var(--cat-path, #f59e0b) !important;
  color: var(--cat-path, #f59e0b) !important;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.08);
}
.focus-accent-group .btn-pill.practice.active {
  background-color: var(--cat-resource-soft, rgba(16,185,129,0.08)) !important;
  border-color: var(--cat-resource, #10b981) !important;
  color: var(--cat-resource, #10b981) !important;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.08);
}
.focus-accent-group .btn-pill.weakness.active {
  background-color: var(--cat-rose-soft, rgba(244,63,94,0.08)) !important;
  border-color: var(--cat-rose, #f43f5e) !important;
  color: var(--cat-rose, #f43f5e) !important;
  box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.08);
}

.form-action-footer {
  border-top: 1px solid var(--color-border-light, #eee);
  margin-top: var(--space-4, 16px);
  padding-top: var(--space-6, 24px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-6, 24px);
}

.ai-readiness-inline-dashboard {
  display: flex;
  gap: var(--space-3, 12px);
  align-items: flex-start;
  background: rgba(242, 248, 247, 0.6);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-border-light, #eee);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-3_5, 14px) var(--space-4, 16px);
  flex-grow: 1;
  max-width: 60%;
  transition: var(--transition-base, all 0.2s ease);
}
.dashboard-visual-pulse {
  position: relative;
  width: 14px;
  height: 14px;
  margin-top: 3px;
  flex-shrink: 0;
}
.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  background: var(--color-text-faint, #999);
  border-radius: 50%;
  opacity: 0.2;
}
.pulse-center-core {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 8px;
  height: 8px;
  background: var(--color-text-faint, #999);
  border-radius: 50%;
}
.dashboard-inline-meta strong {
  display: block;
  font-size: var(--text-sm, 14px);
  color: var(--color-text-strong, #1a1a1a);
  margin-bottom: var(--space-1, 4px);
}
.dashboard-inline-meta p {
  margin: 0;
  font-size: 11.5px;
  color: var(--color-text-secondary, #666);
  line-height: var(--leading-tight, 1.25);
}
.dashboard-inline-meta .lack {
  color: var(--color-danger, #ef4444);
  font-weight: var(--weight-bold, 700);
  padding: 0 2px;
}

.ai-readiness-inline-dashboard.is-ready {
  background: rgba(216, 241, 240, 0.7);
  border-color: var(--color-primary-border, #46b8b4);
  box-shadow: 0 4px 16px rgba(70, 184, 180, 0.1);
}
.ai-readiness-inline-dashboard.is-ready .pulse-ring {
  background: var(--color-primary, #46b8b4);
  animation: pulseSpread 1.8s infinite ease-in-out;
  opacity: 0.4;
}
.ai-readiness-inline-dashboard.is-ready .pulse-center-core {
  background: var(--color-primary, #46b8b4);
}
.ai-readiness-inline-dashboard.is-ready .dashboard-inline-meta strong {
  color: var(--color-primary-text, #205f67);
}
.ai-readiness-inline-dashboard.is-ready .dashboard-inline-meta p {
  color: var(--color-primary-text, #205f67);
}

@keyframes pulseSpread {
  0% { transform: scale(1); opacity: 0.5; }
  100% { transform: scale(2.4); opacity: 0; }
}

.footer-buttons-cluster {
  display: flex;
  gap: var(--space-3, 12px);
  flex-shrink: 0;
}

.custom-premium-action {
  background: linear-gradient(135deg, var(--color-text-strong, #1a1a1a), var(--color-primary-text, #205f67)) !important;
  color: #FCFFFF !important;
  font-weight: var(--weight-bold, 700) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  box-shadow: 0 6px 16px rgba(32, 95, 103, 0.16) !important;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
  transition: var(--transition-base, all 0.2s ease) !important;
}
.custom-premium-action:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-primary-text, #205f67), var(--color-primary-hover, #3aa3a0)) !important;
  box-shadow: 0 8px 24px rgba(32, 95, 103, 0.24) !important;
  transform: translateY(-1.5px);
}
.custom-premium-action:active:not(:disabled) {
  transform: translateY(0.5px);
  box-shadow: 0 4px 10px rgba(32, 95, 103, 0.12) !important;
}

.workspace-flow-footnote {
  padding: 0 var(--space-1, 4px) var(--space-8, 32px);
}
.agile-notice-banner-box {
  background: rgba(70, 184, 180, 0.04);
  border: 1px dashed var(--color-border, #ddd);
  border-radius: var(--radius-md, 8px);
  padding: var(--space-4, 16px) var(--space-5, 20px);
}
.mini-badge {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  font-weight: var(--weight-bold, 700);
  color: var(--color-primary, #46b8b4);
  letter-spacing: 0.06em;
  display: block;
  margin-bottom: var(--space-1, 4px);
}
.agile-notice-banner-box p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-secondary, #666);
  line-height: var(--leading-relaxed, 1.6);
}

/* ============================================================
   学生友好型“就地弹窗”样式（全新重构 - 升级微调版）
   ============================================================ */
.student-planning-modal-backdrop {
  position: fixed;
  inset: 0;
  /* 调至更通透清爽的亮色毛玻璃质感底色 */
  background-color: rgba(244, 249, 249, 0.45);
  /* 降低模糊层级，隐约透出底层表单结构，消除盲盒感 */
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.student-planning-modal-content {
  background: #ffffff;
  border: 1px solid var(--color-primary-border, rgba(70, 184, 180, 0.25));
  border-radius: 20px;
  width: 100%;
  max-width: 620px;
  padding: 40px;
  /* 优化投影：使其具有如纸片浮于水面的通透悬浮感，去掉沉重暗色 */
  box-shadow: 0 12px 40px rgba(32, 95, 103, 0.08), 0 2px 10px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  gap: 32px;
  position: relative;
}

/* 头部微流光加载 */
.modal-loading-header {
  text-align: center;
}
.premium-sparkle-loader {
  position: relative;
  width: 56px;
  height: 56px;
  margin: 0 auto 20px;
  display: grid;
  place-items: center;
}
.spinner-double-ring {
  position: absolute;
  inset: 0;
  border: 3px solid rgba(70, 184, 180, 0.1);
  border-top-color: var(--color-primary, #46b8b4);
  border-bottom-color: var(--cat-tutor, #1e40af);
  border-radius: 50%;
  animation: modalSpin 1.2s infinite cubic-bezier(0.68, -0.55, 0.27, 1.55);
}
.sparkle-center-icon {
  color: var(--color-primary, #46b8b4);
}
.modal-loading-header h2 {
  font-size: 18px;
  color: var(--color-text-strong, #1a1a1a);
  margin: 0 0 6px 0;
  font-weight: 700;
}
.modal-loading-header p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary, #666);
}

/* 横向流式节点进度 */
.student-timeline-track {
  display: flex;
  justify-content: space-between;
  position: relative;
  padding: 0 10px;
}
.student-timeline-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
  flex: 1;
}
.node-circle-indicator {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--color-border, #ddd);
  display: grid;
  place-items: center;
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-faint, #999);
  z-index: 2;
  transition: all 0.3s ease;
}
.node-text-label {
  font-size: 11px;
  color: var(--color-text-faint, #999);
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;
}

/* 节点间连线 */
.node-connecting-dash {
  position: absolute;
  height: 2px;
  background: var(--color-border-light, #eee);
  top: 13px;
  left: 50%;
  width: 100%;
  z-index: 1;
  transition: all 0.3s ease;
}

/* 进度激活/完成联动 */
.student-timeline-node.is-active .node-circle-indicator {
  border-color: var(--color-primary, #46b8b4);
  color: var(--color-primary-text, #205f67);
  font-weight: 700;
  box-shadow: 0 0 0 4px var(--color-primary-soft, rgba(70,184,180,0.15));
}
.student-timeline-node.is-active .node-text-label {
  color: var(--color-text-strong, #1a1a1a);
  font-weight: 600;
}
.student-timeline-node.is-done .node-circle-indicator {
  background: var(--color-primary, #46b8b4);
  border-color: var(--color-primary, #46b8b4);
  color: #fff;
}
.student-timeline-node.is-done .node-text-label {
  color: var(--color-text-secondary, #666);
}
.student-timeline-node.is-done .node-connecting-dash {
  background: var(--color-primary, #46b8b4);
}

/* 简易仪表进度 */
.student-progress-dashboard {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fbfb;
  border: 1px solid rgba(70, 184, 180, 0.1);
  border-radius: 10px;
  padding: 12px 18px;
}
.progress-bar-minimal {
  flex: 1;
  height: 6px;
  background: var(--color-bg, #fafafa);
  border-radius: 3px;
  overflow: hidden;
  margin-right: 20px;
}
.progress-bar-minimal-fill {
  height: 100%;
  background: linear-gradient(90deg, #46b8b4, #1e40af);
  border-radius: 3px;
  transition: width 0.3s ease;
}
.progress-percent-count {
  font-size: 12px;
  color: var(--color-text-secondary, #666);
}
.progress-percent-count span {
  font-family: var(--font-mono, monospace);
  font-weight: 700;
  color: var(--color-primary-text, #205f67);
  font-size: 14px;
}

/* 暖心一句话流日志容器 */
.student-friendly-log-box {
  min-height: 24px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
.friendly-log-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.friendly-log-dot {
  width: 5px;
  height: 5px;
  background-color: var(--color-primary, #46b8b4);
  border-radius: 50%;
}
.friendly-log-text {
  font-size: 13px;
  color: var(--color-primary-text, #205f67);
  font-weight: 500;
}

/* 错误退出面板 */
.student-error-box {
  background: rgba(239, 68, 68, 0.03);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.error-meta-flex {
  display: flex;
  gap: 10px;
  color: #ef4444;
}
.error-meta-flex strong {
  font-size: 13px;
  display: block;
  margin-bottom: 2px;
}
.error-meta-flex p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-secondary, #666);
}
.btn-modal-back {
  align-self: flex-end;
  height: 30px;
  padding: 0 16px;
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-modal-back:hover {
  background: #ef4444;
  color: #fff;
}

/* 动画定义 */
@keyframes modalSpin {
  100% { transform: rotate(360deg); }
}
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.3s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}
.log-item-fade-enter-active {
  transition: all 0.2s ease;
}
.log-item-fade-enter-from {
  opacity: 0;
  transform: translateY(5px);
}

/* ============================================================
   移动端响应式降级
   ============================================================ */
@media (max-width: 1024px) {
  .templates-horizontal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .form-action-footer {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-4, 16px);
  }
  .ai-readiness-inline-dashboard {
    max-width: 100%;
  }
}
@media (max-width: 768px) {
  .form-grid-row {
    grid-template-columns: 1fr;
    gap: var(--space-3, 12px);
  }
  .templates-horizontal-grid {
    grid-template-columns: 1fr;
  }
  .footer-buttons-cluster {
    width: 100%;
  }
  .footer-buttons-cluster button {
    flex: 1;
  }
  .student-timeline-track {
    flex-direction: column;
    gap: 16px;
  }
  .node-connecting-dash {
    display: none;
  }
  .student-timeline-node {
    flex-direction: row;
    gap: 12px;
  }
}
</style>