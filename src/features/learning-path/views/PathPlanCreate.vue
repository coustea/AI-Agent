<template>
  <main class="page-container path-planner-page">
    <div class="planner-unified-container">

      <!-- 全局高维顶层头部 -->
      <header class="workspace-brand-header">
        <div class="header-headline-group">
          <span class="agent-eyebrow">PATH PLANNER AI ENGINE</span>
          <h1>创建学习路径</h1>
          <p class="cognitive-subtext">
            自定义您专属的主题、目标与偏好。智能引擎将自动构建清晰的阶段性知识图谱与高维前置依赖节点。
          </p>
        </div>
        <!-- 历史路径从右侧隔离盒优雅上移归位 -->
        <div class="header-action-group">
          <button class="btn-outline btn-sm" type="button" :disabled="isPlanning" @click="goHistory">
            <span>历史路径记录</span>
            <ph-arrow-right class="arrow-symbol" :size="12" weight="bold" />
          </button>
        </div>
      </header>

      <!-- 状态一：正在生成路径的动态全屏卡片 -->
      <div v-if="isPlanning" class="bezel-card-outer planning-card-wrapper">
        <div class="bezel-card-inner">
          <div class="planning-engine-head">
            <span class="status-badge pulse-animation">ENGINE GENERATING</span>
            <h2>AI 路径结构规划中</h2>
            <p>系统正根据您的动态基础画像、场景及偏好，校准最优学习路由...</p>
          </div>

          <!-- 横向精密流程时轴线 -->
          <div class="orbit-timeline-container">
            <div class="orbit-line-track"></div>
            <div
                v-for="(step, index) in planningSteps"
                :key="step.key"
                class="orbit-node-item"
                :class="[
                step.tone,
                {
                  active: currentPlanningIndex === index,
                  done: currentPlanningIndex > index,
                },
              ]"
            >
              <div class="node-geometric-dot">
                <ph-check v-if="currentPlanningIndex > index" :size="14" weight="bold" />
                <span v-else>{{ index + 1 }}</span>
              </div>
              <strong class="node-label">{{ step.title }}</strong>
            </div>
          </div>

          <!-- 进度条系统 -->
          <div class="progress-bar-block">
            <div class="progress-bar-header">
              <span class="task-title">{{ currentPlanningTitle }}</span>
              <strong class="percent-value">{{ Math.round(planningProgress) }}%</strong>
            </div>
            <div class="progress-bar-track">
              <div class="progress-bar-fill animate-pulse" :style="{ width: `${planningProgress}%` }"></div>
            </div>
          </div>

          <!-- 实时规划流日志 -->
          <transition-group name="log-slide" tag="div" class="planning-logs-area">
            <div
                v-for="(message, index) in planningLogs"
                :key="`${message}-${index}`"
                class="log-row-item"
            >
              <i class="log-dot-indicator"></i>
              <span class="log-message-text">{{ message }}</span>
            </div>
          </transition-group>

          <div v-if="planningError" class="error-handling-panel">
            <div class="error-message-content">
              <strong>高维规划引擎中断</strong>
              <p>{{ planningError }}</p>
            </div>
            <button type="button" class="btn-sm btn-outline danger-border" @click="resetPlanningState">
              返回修改参数
            </button>
          </div>
        </div>
      </div>

      <!-- 状态二：流式智能配置工作台 -->
      <div v-else class="workspace-content-flow">

        <!-- 常用模板横向快捷画廊：大幅提升视线流畅度与操作效率 -->
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

        <!-- 主表单卡片容器 -->
        <div class="panel structured-form-panel">

          <!-- 01 学习主题 -->
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

          <!-- 02 学习目标 -->
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

          <!-- 03 当前基础 -->
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
                      placeholder="输入后按 Enter 添加，如：Python、链表"
                      @keydown.enter.prevent="addKnowledge"
                      @keydown.backspace="removeLastKnowledge"
                  />
                </div>
              </div>

              <!-- 快捷基础池 -->
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

          <!-- 04 学习偏好 -->
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

          <!-- 高度集成的就绪仪表控制底栏：彻底抹去右边死板复读的预览表格 -->
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

        <!-- 敏捷说明页脚区 -->
        <footer class="workspace-flow-footnote">
          <div class="agile-notice-banner-box">
            <span class="mini-badge">AGILE GENERATION SPECIFICATION</span>
            <p>当前步骤仅负责智能化解构学习路线骨架（包括学习阶段、核心节点顺序与前置依赖锁定）。各节点内部的精细化视频教程、前沿知识图谱、实操代码演练及自测题库均在后续进入具体节点页时按需弹性、瞬时全自动生成。</p>
          </div>
        </footer>
      </div>

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
  desc: string
  threshold: number
  tone: ExampleTone
}

const router = useRouter()
// 表单 DOM 引用与输入状态
const goalRef = ref<HTMLTextAreaElement | null>(null)
const knowledgeInput = ref('')
// 提交/规划流程状态
const isSubmitting = ref(false)
const isPlanning = ref(false)
const planningPathId = ref<number | null>(null)
const planningRunId = ref('')
const planningProgress = ref(0)
const planningLogs = ref<string[]>([])
const planningError = ref('')

// 轮播进度定时器与轮询停止标识
let progressTimer: number | null = null
let pollingStopped = false

// 表单响应式数据：主题、目标、已有知识、偏好参数
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

// 表单是否可提交：主题非空且目标至少 8 个字
const canSubmit = computed(() => {
  return form.topic.trim().length > 0 && form.goal.trim().length >= 8
})

// 提交按钮状态的标题和描述文案
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

// 根据进度百分比计算当前处于规划流程的第几步
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

// 自动调整 textarea 高度
function autoResize() {
  if (!goalRef.value) return
  goalRef.value.style.height = 'auto'
  goalRef.value.style.height = `${Math.min(goalRef.value.scrollHeight, 150)}px`
}

// 添加已有知识标签
function addKnowledge() {
  const value = knowledgeInput.value.trim()
  if (!value) return

  if (!form.currentKnowledge.includes(value)) {
    form.currentKnowledge.push(value)
  }

  knowledgeInput.value = ''
}

// 删除指定知识标签
function removeKnowledge(value: string) {
  form.currentKnowledge = form.currentKnowledge.filter(item => item !== value)
}

// 按退格键删除最后一个标签
function removeLastKnowledge() {
  if (knowledgeInput.value || !form.currentKnowledge.length) return
  form.currentKnowledge.pop()
}

// 切换知识标签（选中/取消）
function toggleKnowledge(value: string) {
  if (form.currentKnowledge.includes(value)) {
    removeKnowledge(value)
    return
  }

  form.currentKnowledge.push(value)
}

// 切换规划重点（至少保留一个）
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

// 重置表单到初始状态
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

// 跳转到历史路径页
function goHistory() {
  router.push('/path-planner/history')
}

// 构建提交给后端的请求 payload
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

// 清除进度轮播定时器
function clearProgressTimer() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer)
    progressTimer = null
  }
}

// 添加 SSE 规划日志（去重并限制最多 6 条）
function addPlanningLog(message: string) {
  if (planningLogs.value.includes(message)) return
  planningLogs.value = [...planningLogs.value, message].slice(-6)
}

// 启动前端模拟进度动画，逐步展示各阶段的提示文案
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

// 重置规划状态以便用户重新提交
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

// 轮询等待后端路径生成完成（超时 3 分钟），完成后跳转至总览页
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

// 提交路径创建：校验表单、调用 API、启动进度轮播并等待生成完成
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

// 组件卸载时停止轮询与定时器

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
  max-width: var(--content-max-width); /* 1120px 黄金内宽垂直对齐 */
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* 一体化顶层头部 */
.workspace-brand-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: var(--space-4) var(--space-1) var(--space-2);
}
.header-headline-group {
  max-width: 75%;
}
.agent-eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: var(--weight-bold);
  color: var(--color-primary);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
.workspace-brand-header h1 {
  font-size: var(--text-2xl);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  margin: var(--space-1) 0 var(--space-2);
}
.cognitive-subtext {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}
.arrow-symbol {
  font-weight: var(--weight-extrabold);
  margin-left: var(--space-1);
  transition: transform 0.2s cubic-bezier(0.32, 0.72, 0, 1);
}
.header-action-group button:hover .arrow-symbol {
  transform: translateX(3px);
}

/* ============================================================
   常用模板：重塑为表单上方的横向全宽快速配置画廊
   ============================================================ */
.horizontal-templates-gallery {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: 0 var(--space-1);
}
.gallery-title-strip {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}
.gallery-title-strip h4 {
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.gallery-title-strip span {
  font-size: 11px;
  color: var(--color-text-faint);
}
.templates-horizontal-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}
.micro-template-gallery-card {
  background: var(--color-surface);
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-align: left;
  cursor: pointer;
  box-sizing: border-box;
  transition: var(--transition-base);
  height: 64px;
}
.micro-template-gallery-card:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
}
.micro-template-gallery-card.active {
  border-color: currentColor;
  box-shadow: var(--shadow-md), 0 0 12px var(--color-primary-soft);
  background: var(--color-surface);
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
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.micro-card-meta span {
  display: block;
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.micro-template-gallery-card.teal { color: var(--color-primary); }
.micro-template-gallery-card.blue { color: var(--cat-tutor); }
.micro-template-gallery-card.amber { color: var(--cat-path); }
.micro-template-gallery-card.violet { color: var(--cat-eval); }

/* ============================================================
   核心工作表单面板
   ============================================================ */
.structured-form-panel {
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  box-shadow: var(--shadow-sm);
}

.form-grid-row {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: var(--space-6);
  padding: var(--space-6) 0;
  border-bottom: 1px solid var(--color-border-light);
}
.form-grid-row:first-child { padding-top: 0; }

.row-meta-pane {
  display: flex;
  gap: var(--space-3);
}
.row-badge-num {
  width: 28px;
  height: 28px;
  background: var(--color-primary-soft);
  border: 1.5px solid var(--color-primary-border);
  color: var(--color-primary-text);
  border-radius: var(--radius-sm);
  display: grid;
  place-items: center;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
}
.row-headline-group h3 {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  margin: 2px 0 0;
}
.row-title-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1_5);
}
.title-icon {
  color: var(--color-primary-text);
  opacity: 0.85;
  flex-shrink: 0;
}
.row-headline-group p {
  margin: var(--space-2) 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-normal);
}

/* 控制台输入域 */
.input-container-box input,
.textarea-container-box textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: var(--text-sm);
  outline: none;
  transition: var(--transition-base);
}
.input-container-box input {
  height: 42px;
  padding: 0 var(--space-4);
}
.textarea-container-box textarea {
  padding: var(--space-3) var(--space-4);
  resize: none;
  min-height: 96px;
  line-height: var(--leading-normal);
}
.input-container-box input:focus,
.textarea-container-box textarea:focus {
  border-color: var(--color-primary);
  background: var(--color-page-bg);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.15);
}
.textarea-info-bar {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-1_5);
  font-size: var(--text-xs);
  color: var(--color-text-faint);
}

/* 先修基础标签盒 */
.tag-input-bezel-box {
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  padding: var(--space-1_5) var(--space-3);
  min-height: 42px;
  box-sizing: border-box;
  transition: var(--transition-base);
}
.tag-input-bezel-box:focus-within {
  border-color: var(--color-primary);
  background: var(--color-page-bg);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.15);
}
.tag-inner-flex {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1_5);
  align-items: center;
}
.tag-inner-flex input {
  border: none;
  background: transparent;
  outline: none;
  font-family: inherit;
  font-size: var(--text-sm);
  color: var(--color-text);
  padding: 4px 0;
  flex-grow: 1;
}
.custom-tag-node {
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary-text);
  padding: var(--space-0_5) var(--space-2_5);
  border-radius: 6px;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: var(--transition-fast);
}
.custom-tag-node:hover {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
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
  transition: var(--transition-fast);
}
.tag-close-trigger:hover {
  opacity: 1;
  transform: scale(1.1);
}
.quick-tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}
.quick-tags-container .btn-pill {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  border-radius: var(--radius-pill);
  height: 28px;
  padding: 0 var(--space-3);
  cursor: pointer;
  transition: var(--transition-base);
}
.quick-tags-container .btn-pill:hover {
  border-color: var(--color-border-hover);
  color: var(--color-text-strong);
  transform: translateY(-1px);
}
.quick-tags-container .btn-pill.active {
  background-color: var(--color-primary-soft) !important;
  border-color: var(--color-primary) !important;
  color: var(--color-primary-text) !important;
  font-weight: var(--weight-bold);
}

/* 偏好微调控制轴 */
.preferences-matrix {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.preference-flex-line {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr);
  align-items: center;
  gap: var(--space-3);
}
.pref-field-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
}
.segmented-pill-group {
  display: inline-flex;
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-pill);
  padding: 4px;
  gap: 4px;
}
.segmented-pill-group .btn-pill {
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  height: 28px;
  transition: var(--transition-fast);
  cursor: pointer;
}
.segmented-pill-group .btn-pill:hover {
  color: var(--color-text-strong);
}
.segmented-pill-group .btn-pill.active {
  background-color: var(--color-surface) !important;
  border: 1px solid var(--color-primary-border) !important;
  color: var(--color-primary-text) !important;
  font-weight: var(--weight-bold);
  box-shadow: var(--shadow-sm);
}

/* 多选重点专属高亮 */
.focus-accent-group {
  display: flex;
  flex-wrap: wrap;
  background: transparent;
  border: none;
  padding: 0;
  gap: var(--space-2_5);
}
.focus-accent-group .btn-pill {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  height: auto;
  cursor: pointer;
  transition: var(--transition-base);
}
.focus-accent-group .btn-pill:hover {
  border-color: var(--color-border-hover);
  color: var(--color-text-strong);
  transform: translateY(-1px);
}
.focus-accent-group .btn-pill.foundation.active {
  background-color: var(--cat-tutor-soft) !important;
  border-color: var(--cat-tutor) !important;
  color: var(--cat-tutor) !important;
  box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.08);
}
.focus-accent-group .btn-pill.key_points.active {
  background-color: var(--cat-path-soft) !important;
  border-color: var(--cat-path) !important;
  color: var(--cat-path) !important;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.08);
}
.focus-accent-group .btn-pill.practice.active {
  background-color: var(--cat-resource-soft) !important;
  border-color: var(--cat-resource) !important;
  color: var(--cat-resource) !important;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.08);
}
.focus-accent-group .btn-pill.weakness.active {
  background-color: var(--cat-rose-soft) !important;
  border-color: var(--cat-rose) !important;
  color: var(--cat-rose) !important;
  box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.08);
}

/* ============================================================
   高度集成的底栏控制台（融合 AI 校验就绪状态与提交控制）
   ============================================================ */
.form-action-footer {
  border-top: 1px solid var(--color-border-light);
  margin-top: var(--space-4);
  padding-top: var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-6);
}

/* 内联 AI 参数校验视窗 */
.ai-readiness-inline-dashboard {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  background: rgba(242, 248, 247, 0.6);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--space-3_5) var(--space-4);
  flex-grow: 1;
  max-width: 60%;
  transition: var(--transition-base);
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
  background: var(--color-text-faint);
  border-radius: 50%;
  opacity: 0.2;
}
.pulse-center-core {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 8px;
  height: 8px;
  background: var(--color-text-faint);
  border-radius: 50%;
}
.dashboard-inline-meta strong {
  display: block;
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  margin-bottom: var(--space-1);
}
.dashboard-inline-meta p {
  margin: 0;
  font-size: 11.5px;
  color: var(--color-text-secondary);
  line-height: var(--leading-tight);
}
.dashboard-inline-meta .lack {
  color: var(--color-danger);
  font-weight: var(--weight-bold);
  padding: 0 2px;
}

/* 引擎就绪动态高亮（清透冰川工作室质感） */
.ai-readiness-inline-dashboard.is-ready {
  background: rgba(216, 241, 240, 0.7);
  backdrop-filter: blur(8px);
  border-color: var(--color-primary-border);
  box-shadow: 0 4px 16px rgba(70, 184, 180, 0.1);
}
.ai-readiness-inline-dashboard.is-ready .pulse-ring {
  background: var(--color-primary);
  animation: pulseSpread 1.8s infinite ease-in-out;
  opacity: 0.4;
}
.ai-readiness-inline-dashboard.is-ready .pulse-center-core {
  background: var(--color-primary);
}
.ai-readiness-inline-dashboard.is-ready .dashboard-inline-meta strong {
  color: var(--color-primary-text);
}
.ai-readiness-inline-dashboard.is-ready .dashboard-inline-meta p {
  color: var(--color-primary-text);
}

@keyframes pulseSpread {
  0% { transform: scale(1); opacity: 0.5; }
  100% { transform: scale(2.4); opacity: 0; }
}

.footer-buttons-cluster {
  display: flex;
  gap: var(--space-3);
  flex-shrink: 0;
}

/* 生成路径主行动按钮 */
.custom-premium-action {
  background: linear-gradient(135deg, var(--color-text-strong), var(--color-primary-text)) !important;
  color: #FCFFFF !important;
  font-weight: var(--weight-bold) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  box-shadow: 0 6px 16px rgba(32, 95, 103, 0.16) !important;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
  transition: var(--transition-base) !important;
}
.custom-premium-action:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-primary-text), var(--color-primary-hover)) !important;
  box-shadow: 0 8px 24px rgba(32, 95, 103, 0.24) !important;
  transform: translateY(-1.5px);
}
.custom-premium-action:active:not(:disabled) {
  transform: translateY(0.5px);
  box-shadow: 0 4px 10px rgba(32, 95, 103, 0.12) !important;
}

/* ============================================================
   统一流式页脚提示区
   ============================================================ */
.workspace-flow-footnote {
  padding: 0 var(--space-1) var(--space-8);
}
.agile-notice-banner-box {
  background: rgba(70, 184, 180, 0.04);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-5);
}
.mini-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: var(--weight-bold);
  color: var(--color-primary);
  letter-spacing: 0.06em;
  display: block;
  margin-bottom: var(--space-1);
}
.agile-notice-banner-box p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

/* ============================================================
   智能引擎构建动画状态卡片
   ============================================================ */
.planning-card-wrapper {
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  box-shadow: var(--shadow-md);
  max-width: 860px;
  margin: var(--space-4) auto;
}
.planning-engine-head {
  text-align: center;
  margin-bottom: var(--space-8);
}
.status-badge {
  display: inline-block;
  padding: 4px var(--space-3);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: var(--weight-bold);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-primary-border);
}
.status-badge.pulse-animation {
  animation: pulseOpacity 2s infinite ease-in-out;
}
@keyframes pulseOpacity {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.planning-engine-head h2 {
  font-size: var(--text-xl);
  color: var(--color-text-strong);
  margin: var(--space-3) 0 var(--space-1);
}
.planning-engine-head p {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.orbit-timeline-container {
  position: relative;
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-8);
  padding: 0 var(--space-6);
}
.orbit-line-track {
  position: absolute;
  top: 18px;
  left: var(--space-10);
  right: var(--space-10);
  height: 2px;
  background: var(--color-border-light);
  z-index: 1;
}
.orbit-node-item {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2_5);
  flex: 1;
}
.node-geometric-dot {
  width: 36px;
  height: 36px;
  background: var(--color-surface);
  border: 2px solid var(--color-border);
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  color: var(--color-text-faint);
  transition: var(--transition-base);
}
.node-label {
  font-size: var(--text-xs);
  color: var(--color-text-faint);
  transition: var(--transition-base);
}
.orbit-node-item.active .node-geometric-dot {
  border-color: currentColor;
  box-shadow: 0 0 0 4px var(--color-primary-soft);
  transform: scale(1.05);
}
.orbit-node-item.done .node-geometric-dot,
.orbit-node-item.active .node-geometric-dot {
  background: currentColor;
  color: #FFFFFF;
}
.orbit-node-item.done .node-label,
.orbit-node-item.active .node-label {
  color: var(--color-text-strong);
  font-weight: var(--weight-bold);
}
.orbit-node-item.teal { color: var(--color-primary); }
.orbit-node-item.blue { color: var(--cat-tutor); }
.orbit-node-item.amber { color: var(--cat-path); }
.orbit-node-item.violet { color: var(--cat-eval); }

.progress-bar-block {
  margin-bottom: var(--space-6);
}
.progress-bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  font-size: var(--text-sm);
}
.task-title { font-weight: var(--weight-bold); color: var(--color-text-strong); }
.percent-value { color: var(--color-primary-text); }
.progress-bar-track {
  height: 6px;
  background: var(--color-border-light);
  border-radius: var(--radius-pill);
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--cat-tutor));
  border-radius: var(--radius-pill);
  transition: width 0.4s ease;
}

.planning-logs-area {
  background: #0f2427;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2_5);
}
.log-row-item {
  display: flex;
  align-items: center;
  gap: var(--space-2_5);
}
.log-dot-indicator {
  width: 5px;
  height: 5px;
  background: var(--color-primary);
  border-radius: 50%;
}
.log-message-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: #a4cbd1;
}
.log-slide-enter-active, .log-slide-leave-active { transition: all 0.25s ease; }
.log-slide-enter-from { opacity: 0; transform: translateY(5px); }

.error-handling-panel {
  margin-top: var(--space-4);
  padding: var(--space-4);
  background: var(--color-danger-soft);
  border: 1px solid rgba(196, 61, 91, 0.15);
  border-radius: var(--radius-md);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}
.error-message-content strong { display: block; font-size: var(--text-sm); color: var(--color-danger); }
.error-message-content p { margin: 2px 0 0; font-size: var(--text-xs); color: var(--color-text-secondary); }
.danger-border { border-color: rgba(196, 61, 91, 0.3) !important; color: var(--color-danger) !important; }

/* ============================================================
   移动端与小屏幕平滑降级自适应
   ============================================================ */
@media (max-width: 1024px) {
  .templates-horizontal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .form-action-footer {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-4);
  }
  .ai-readiness-inline-dashboard {
    max-width: 100%;
  }
}

@media (max-width: 768px) {
  .form-grid-row {
    grid-template-columns: 1fr;
    gap: var(--space-3);
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
  .orbit-timeline-container {
    flex-direction: column;
    gap: var(--space-4);
    padding-left: var(--space-2);
  }
  .orbit-line-track {
    top: 0;
    bottom: 0;
    left: 21px;
    width: 2px;
    height: auto;
  }
  .orbit-node-item {
    flex-direction: row;
    align-items: center;
    gap: var(--space-4);
  }
}
</style>