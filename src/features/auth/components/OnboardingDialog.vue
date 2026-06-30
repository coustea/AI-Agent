<template>
  <section
      v-if="visible"
      :class="['onboarding-page', { 'onboarding-standalone': standalone }]"
  >
    <main class="onboarding-container">
      <header class="conversation-header">
        <div class="progress-badge" aria-label="基础资料进度">
          <strong>{{ profileProgress }}%</strong>
          <span>资料进度</span>
        </div>

        <button class="skip-btn" type="button" @click="handleCompleteLater">
          稍后完善
        </button>

        <div class="header-center">
          <div class="title-mark">
            <span></span>
            <span></span>
          </div>

          <h1>对话式构建基础资料</h1>
          <p>每次只确认一个主题，填写完成后可在个人中心继续修改。</p>
        </div>
      </header>

      <section class="onboarding-workspace">
        <aside class="step-rail" aria-label="填写步骤">
          <div class="step-rail-title">
            <span>{{ currentStepLabel }}</span>
            <strong>{{ currentStepMeta.short }}</strong>
          </div>

          <ol class="step-list">
            <li
                v-for="step in stepTimeline"
                :key="step.key"
                :class="['step-item', step.state]"
            >
              <span class="step-index">{{ step.key }}</span>
              <div>
                <strong>{{ step.short }}</strong>
                <small>{{ step.title }}</small>
              </div>
            </li>
          </ol>
        </aside>

        <section class="chat-card">
          <div class="current-question">
            <div class="question-copy">
              <span>当前问题</span>
              <strong>{{ currentQuestionTitle }}</strong>
              <p>{{ currentStepMeta.description }}</p>
            </div>
          </div>

          <div
              ref="messageListRef"
              class="message-list"
              @scroll="handleMessageListScroll"
          >
            <transition-group name="message-pop" tag="div" class="message-inner">
              <div
                  v-for="msg in messages"
                  :key="msg.id"
                  :class="['message-row', msg.role, { 'is-streaming': msg.streaming }]"
              >
                <div v-if="msg.role === 'assistant'" class="avatar-icon">
                  AI
                </div>

                <div class="message-main">
                  <div class="message-meta">
                    <span>{{ msg.role === 'assistant' ? '学枢智导' : '你' }}</span>
                    <span>{{ msg.time }}</span>
                  </div>

                  <div class="message-bubble">
                    <p class="message-text">{{ msg.content }}</p>
                  </div>
                </div>

                <div v-if="msg.role === 'user'" class="user-avatar">
                  你
                </div>
              </div>
            </transition-group>

            <transition name="fade-up">
              <div
                  v-if="showAssistantActions"
                  class="message-row assistant action-row"
              >
                <div class="avatar-icon">AI</div>

                <div class="message-main">
                  <div class="message-meta">
                    <span>学枢智导</span>
                    <span>{{ currentTimeLabel }}</span>
                  </div>

                  <div class="message-bubble action-bubble">
                    <div class="action-copy">
                      <strong>{{ activeActionTitle }}</strong>
                      <p>{{ activeActionHint }}</p>
                    </div>

                    <div
                        v-if="currentQuickReplies.length > 0"
                        :class="['quick-replies-grid', { 'is-card-mode': shouldShowReplyHint, 'is-grade-mode': isGradeStep }]"
                    >
                      <button
                          v-for="reply in currentQuickReplies"
                          :key="reply"
                          class="quick-reply-btn"
                          :class="{ 'is-selected': isReplySelected(reply) }"
                          type="button"
                          :disabled="isAssistantStreaming"
                          @click="handleQuickReply(reply)"
                      >
                        <span>{{ reply }}</span>
                        <small v-if="getReplyHint(reply)">{{ getReplyHint(reply) }}</small>
                      </button>
                    </div>

                    <div
                        v-if="currentStep === 4 && schoolSuggestions.length > 0"
                        class="school-suggestions-grid"
                    >
                      <button
                          v-for="school in schoolSuggestions"
                          :key="school.name"
                          class="school-suggestion-btn"
                          type="button"
                          @click="selectSchool(school)"
                      >
                        <span class="school-name">{{ school.name }}</span>
                        <span v-if="school.level" class="school-level-tag">
                          {{ school.level }}
                        </span>
                      </button>
                    </div>

                    <div v-if="isMultiSelectStep" class="action-footer">
                      <span>{{ selectionSummaryText }}</span>
                      <button
                          class="confirm-selection-btn"
                          type="button"
                          :disabled="!canSend"
                          @click="handleSend"
                      >
                        确认选择
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </transition>

            <div v-if="isThinking" class="message-row assistant thinking-row">
              <div class="avatar-icon">AI</div>

              <div class="message-main">
                <div class="message-meta">
                  <span>学枢智导</span>
                  <span>{{ currentTimeLabel }}</span>
                </div>

                <div class="message-bubble thinking-bubble" aria-label="正在输入">
                  <span class="typing-dot"></span>
                  <span class="typing-dot"></span>
                  <span class="typing-dot"></span>
                </div>
              </div>
            </div>

            <button
                v-if="isUserReadingHistory"
                class="back-bottom-btn"
                type="button"
                @click="scrollToBottom({ force: true })"
            >
              回到底部
            </button>
          </div>

          <div class="input-dock">
            <div v-if="currentStep <= 7" class="composer-wrapper">
              <textarea
                  id="onboarding-chat-input"
                  ref="inputRef"
                  v-model="userInput"
                  class="chat-composer"
                  name="onboarding_reply"
                  rows="1"
                  :placeholder="composerPlaceholder"
                  :disabled="isAssistantStreaming || submitting"
                  @keydown="handleComposerKeydown"
                  @input="handleInputChange"
              ></textarea>

              <button
                  class="send-btn"
                  type="button"
                  :disabled="!canSend"
                  @click="handleSend"
              >
                <Position class="btn-icon" />
              </button>
            </div>

            <div v-else class="profile-footer">
              <div>
                <strong>基础资料已经完成</strong>
                <p>这些内容会同步到个人中心，后续可继续修改。</p>
              </div>

              <button
                  class="btn btn-primary finish-btn"
                  :disabled="submitting"
                  @click="submitForm"
              >
                <span>确认进入</span>
                <Right class="btn-icon-right ml-2" />
              </button>
            </div>
          </div>
        </section>

        <aside class="profile-panel" aria-label="基础资料确认">
          <div class="profile-panel-head">
            <span>正在生成基础资料</span>
            <strong>{{ profileProgress }}%</strong>
          </div>

          <div class="progress-ring" :style="{ '--progress': profileProgress }">
            <span>{{ profileProgress }}%</span>
          </div>

          <div class="info-block">
            <h2>已确认</h2>
            <div v-if="confirmedFields.length > 0" class="info-list">
              <div
                  v-for="item in confirmedFields"
                  :key="item.key"
                  class="info-row confirmed"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
            <p v-else class="empty-copy">先从当前问题开始填写。</p>
          </div>

          <div class="info-block">
            <h2>待确认</h2>
            <div class="info-list">
              <div
                  v-for="item in pendingFields"
                  :key="item.key"
                  class="info-row pending"
              >
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>

          <div class="profile-note">
            <strong>填写后可在个人中心修改</strong>
            <p>点击稍后完善不会标记完成，下次进入系统仍会继续引导。</p>
          </div>
        </aside>
      </section>
    </main>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { PhPaperPlaneRight as Position, PhArrowRight as Right } from '@phosphor-icons/vue'

import { updateMe } from '@/features/auth/api/auth'
import { useCurrentUser } from '@/features/auth/model/currentUser'
import { getProfileOnboarding, updateProfileOnboarding } from '@/features/profile/api/profile'
import type { ProfileOnboardingUpdate } from '@/features/profile/api/profile'
import { searchSchools } from '@/features/resource/api/school'
import type { SchoolItem } from '@/features/resource/api/school'
import { hasAuthToken } from '@/shared/auth/token'

const props = withDefaults(defineProps<{ modelValue?: boolean; standalone?: boolean }>(), {
  modelValue: true,
  standalone: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const route = useRoute()
const router = useRouter()
const { currentUser } = useCurrentUser()

const visible = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value),
})

type ChatMessage = {
  id: number
  role: 'assistant' | 'user'
  content: string
  time: string
  streaming?: boolean
}

type StepMeta = {
  key: number
  short: string
  title: string
  description: string
  quickTitle: string
}

type StepTimelineItem = StepMeta & {
  state: 'done' | 'active' | 'pending'
}

type InfoField = {
  key: string
  label: string
  value: string
}

type ProfileOnboardingDraftState = {
  version: 1
  currentStep: number
  userInput: string
  messages: ChatMessage[]
  form: ProfileOnboardingUpdate
}

const messages = ref<ChatMessage[]>([])
const submitting = ref(false)
const messageListRef = ref<HTMLDivElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

const currentStep = ref(1)
const userInput = ref('')
const isThinking = ref(false)
const isAssistantStreaming = ref(false)
const schoolSuggestions = ref<SchoolItem[]>([])
const isUserReadingHistory = ref(false)

const MESSAGE_BOTTOM_THRESHOLD = 88

let schoolSearchTimer: ReturnType<typeof setTimeout> | null = null
let streamRunId = 0
let isDraftHydrating = false
let previousBodyOverflow = ''
let previousHtmlOverflow = ''

const onboardingDraftKey = computed(() =>
    currentUser.value?.id
        ? `onboarding-dialog-draft:${currentUser.value.id}`
        : 'onboarding-dialog-draft',
)

const form = reactive<ProfileOnboardingUpdate>({
  school: '',
  major: '',
  grade: '',
  daily_study_time: '',
  global_learning_goal: '',
  programming_languages: [],
  courses: [],
})

const PRESET_MAJORS = [
  '软件工程',
  '计算机科学与技术',
  '人工智能',
  '数据科学与大数据技术',
  '网络空间安全',
  '电子信息工程',
]

const PRESET_COURSES = [
  '数据结构',
  '操作系统',
  '计算机网络',
  '数据库系统',
  '编译原理',
  '机器学习',
]

const PRESET_GOALS = ['期末复习', '考研学习', '进阶学习', '补基础', '项目实战']
const PRESET_GRADES = ['大一', '大二', '大三', '大四', '研一', '研二', '研三']
const PRESET_DAILY_STUDY_TIME = ['30min以下', '30-60min', '1-2h', '2-3h', '3h以上']
const PRESET_PROGRAMMING_LANGUAGES = ['Python', 'Java', 'C++', 'JavaScript', 'Go', 'Rust']

const ONBOARDING_STEPS: StepMeta[] = [
  {
    key: 1,
    short: '专业',
    title: '先确认你的专业方向',
    description: '专业会影响课程体系、案例选择和讲解方式。',
    quickTitle: '常见专业',
  },
  {
    key: 2,
    short: '年级',
    title: '确认当前学习阶段',
    description: '不同年级的学习重点不同，系统会据此调整难度。',
    quickTitle: '年级阶段',
  },
  {
    key: 3,
    short: '目标',
    title: '明确你的学习目标',
    description: '目标会决定系统更偏向复习、补基础、进阶还是项目实践。',
    quickTitle: '学习目标',
  },
  {
    key: 4,
    short: '学校',
    title: '填写学校名称',
    description: '输入学校名称后会出现搜索结果，可以直接选择。',
    quickTitle: '学校名称',
  },
  {
    key: 5,
    short: '时间',
    title: '设置每天学习时长',
    description: '学习时长会影响节奏安排、任务强度和复习频率。',
    quickTitle: '每日时长',
  },
  {
    key: 6,
    short: '语言',
    title: '选择常用编程语言',
    description: '编程语言会影响代码示例、实践任务和项目练习。',
    quickTitle: '技术栈',
  },
  {
    key: 7,
    short: '课程',
    title: '选择本学期核心课程',
    description: '课程会直接影响学习路径、题库练习和资源生成范围。',
    quickTitle: '核心课程',
  },
]

const currentTimeLabel = computed(() => {
  void currentStep.value
  void messages.value.length
  return formatTime()
})

const currentStepLabel = computed(() => {
  const safeStep = Math.min(currentStep.value, 7)
  return `${safeStep}/7`
})

const coursesValue = computed<string[]>(() => {
  return Array.isArray(form.courses) ? (form.courses as string[]).map(String) : []
})

const isComplete = computed(() => {
  return currentStep.value > 7 || Boolean(
      form.school &&
      form.major &&
      form.grade &&
      form.daily_study_time &&
      form.global_learning_goal &&
      coursesValue.value.length > 0,
  )
})

const completedRequiredCount = computed(() => {
  return [
    Boolean(form.major),
    Boolean(form.grade),
    Boolean(form.global_learning_goal),
    Boolean(form.school),
    Boolean(form.daily_study_time),
    coursesValue.value.length > 0,
  ].filter(Boolean).length
})

const profileProgress = computed(() => {
  if (currentStep.value > 7 || isComplete.value) return 100
  return Math.round((completedRequiredCount.value / 6) * 100)
})

const canSend = computed(() => {
  return userInput.value.trim().length > 0 && !isAssistantStreaming.value && !submitting.value
})

const isMultiSelectStep = computed(() => [6, 7].includes(currentStep.value))
const shouldShowReplyHint = computed(() => [7].includes(currentStep.value))
const isGradeStep = computed(() => currentStep.value === 2)

const currentStepMeta = computed<StepMeta>(() => {
  return ONBOARDING_STEPS.find(step => step.key === Math.min(currentStep.value, 7)) ?? ONBOARDING_STEPS[0]!
})

const currentQuestionTitle = computed(() => {
  switch (currentStep.value) {
    case 1:
      return '你的专业是什么？'
    case 2:
      return '你目前处于哪个年级？'
    case 3:
      return '你的主要学习目标是什么？'
    case 4:
      return '你的学校是哪一所？'
    case 5:
      return '每天大约能学习多久？'
    case 6:
      return '常用哪些编程语言？'
    case 7:
      return '本学期重点课程有哪些？'
    default:
      return '基础资料已确认'
  }
})

const stepTimeline = computed<StepTimelineItem[]>(() => {
  return ONBOARDING_STEPS.map(step => {
    let state: StepTimelineItem['state'] = 'pending'

    if (step.key < currentStep.value) state = 'done'
    if (step.key === Math.min(currentStep.value, 7)) state = 'active'

    return {
      ...step,
      state,
    }
  })
})

const composerPlaceholder = computed(() => {
  if (isAssistantStreaming.value) return '学枢智导正在输入...'
  if (currentStep.value === 1) return '输入专业名称，或点击 AI 推荐标签...'
  if (currentStep.value === 2) return '输入年级，或点击 AI 推荐标签...'
  if (currentStep.value === 4) return '输入学校名称，支持搜索选择...'
  if (currentStep.value === 7) return '输入多门课程，用逗号、空格或顿号分隔...'
  if (isMultiSelectStep.value) return '输入多个内容，用逗号、空格或顿号分隔...'
  return '输入回复，Enter 发送，Shift + Enter 换行...'
})

const selectionItems = computed(() => {
  return userInput.value.split(/[,，、\s]+/).filter(Boolean)
})

const selectionSummaryText = computed(() => {
  return selectionItems.value.length > 0 ? `已选择 ${selectionItems.value.length} 项` : '可多选后发送'
})

const currentQuickReplies = computed(() => {
  switch (currentStep.value) {
    case 1:
      return PRESET_MAJORS
    case 2:
      return PRESET_GRADES
    case 3:
      return PRESET_GOALS
    case 5:
      return PRESET_DAILY_STUDY_TIME
    case 6:
      return ['暂不选择', ...PRESET_PROGRAMMING_LANGUAGES]
    case 7:
      return PRESET_COURSES
    default:
      return []
  }
})

const confirmedFields = computed<InfoField[]>(() => {
  const fields: InfoField[] = [
    { key: 'major', label: '专业', value: form.major || '' },
    { key: 'grade', label: '年级', value: form.grade || '' },
    { key: 'goal', label: '学习目标', value: form.global_learning_goal || '' },
    { key: 'school', label: '学校', value: form.school || '' },
    { key: 'time', label: '每日时长', value: form.daily_study_time || '' },
    {
      key: 'languages',
      label: '常用语言',
      value: Array.isArray(form.programming_languages) ? form.programming_languages.join('，') : '',
    },
    {
      key: 'courses',
      label: '核心课程',
      value: coursesValue.value.join('，'),
    },
  ]

  return fields.filter(item => item.value)
})

const pendingFields = computed<InfoField[]>(() => {
  const fields: InfoField[] = [
    { key: 'major', label: '专业', value: '待填写' },
    { key: 'grade', label: '年级', value: '待填写' },
    { key: 'goal', label: '学习目标', value: '待填写' },
    { key: 'school', label: '学校', value: '待填写' },
    { key: 'time', label: '每日时长', value: '待填写' },
    { key: 'languages', label: '常用语言', value: '可选' },
    { key: 'courses', label: '核心课程', value: '待填写' },
  ]

  const confirmedKeys = new Set(confirmedFields.value.map(item => item.key))
  return fields.filter(item => !confirmedKeys.has(item.key))
})

const showAssistantActions = computed(() => {
  if (currentStep.value > 7 || isAssistantStreaming.value || isThinking.value) return false

  if (currentQuickReplies.value.length > 0) return true
  return currentStep.value === 4 && schoolSuggestions.value.length > 0
})

const activeActionTitle = computed(() => {
  if (currentStep.value === 4 && schoolSuggestions.value.length > 0) {
    return '我找到了这些学校'
  }

  return currentStepMeta.value.quickTitle
})

const activeActionHint = computed(() => {
  if (currentStep.value === 4) {
    return schoolSuggestions.value.length > 0
        ? '选择一个学校后，我会把它作为你的回答继续记录。'
        : '输入学校名称后，我会从学校库里返回匹配项。'
  }

  if (isMultiSelectStep.value) {
    return '这些标签会写入当前回答，可多选后再确认。'
  }

  return '点击任一标签，我会把它作为你的当前回答。'
})

const lockPageScroll = () => {
  previousBodyOverflow = document.body.style.overflow
  previousHtmlOverflow = document.documentElement.style.overflow
  document.body.style.overflow = 'hidden'
  document.documentElement.style.overflow = 'hidden'
}

const unlockPageScroll = () => {
  document.body.style.overflow = previousBodyOverflow
  document.documentElement.style.overflow = previousHtmlOverflow
}

const cloneFormState = (): ProfileOnboardingUpdate => ({
  school: form.school || '',
  major: form.major || '',
  grade: form.grade || '',
  daily_study_time: form.daily_study_time || '',
  global_learning_goal: form.global_learning_goal || '',
  programming_languages: Array.isArray(form.programming_languages) ? [...form.programming_languages] : [],
  courses: Array.isArray(form.courses) ? [...form.courses] : [],
})

const persistDraft = () => {
  if (isDraftHydrating || !onboardingDraftKey.value) return

  const state: ProfileOnboardingDraftState = {
    version: 1,
    currentStep: currentStep.value,
    userInput: userInput.value,
    messages: messages.value.map(message => ({ ...message })),
    form: cloneFormState(),
  }

  localStorage.setItem(onboardingDraftKey.value, JSON.stringify(state))
}

const clearDraft = () => {
  if (!onboardingDraftKey.value) return
  localStorage.removeItem(onboardingDraftKey.value)
}

const loadDraft = () => {
  if (!onboardingDraftKey.value) return false

  const raw = localStorage.getItem(onboardingDraftKey.value)
  if (!raw) return false

  try {
    const state = JSON.parse(raw) as Partial<ProfileOnboardingDraftState>
    isDraftHydrating = true

    currentStep.value = typeof state.currentStep === 'number' ? state.currentStep : 1
    userInput.value = typeof state.userInput === 'string' ? state.userInput : ''
    messages.value = Array.isArray(state.messages)
        ? state.messages.map(message => ({ ...message }))
        : []

    form.school = typeof state.form?.school === 'string' ? state.form.school : ''
    form.major = typeof state.form?.major === 'string' ? state.form.major : ''
    form.grade = typeof state.form?.grade === 'string' ? state.form.grade : ''
    form.daily_study_time = typeof state.form?.daily_study_time === 'string' ? state.form.daily_study_time : ''
    form.global_learning_goal = typeof state.form?.global_learning_goal === 'string' ? state.form.global_learning_goal : ''
    form.programming_languages = Array.isArray(state.form?.programming_languages) ? [...state.form.programming_languages] : []
    form.courses = Array.isArray(state.form?.courses) ? [...state.form.courses] : []

    isDraftHydrating = false

    return messages.value.length > 0 || currentStep.value > 1 || Boolean(userInput.value.trim())
  } catch {
    isDraftHydrating = false
    clearDraft()
    return false
  }
}

watch(visible, async open => {
  if (!open) {
    streamRunId += 1
    unlockPageScroll()
    return
  }

  lockPageScroll()
  await initializeDialog()
})

onMounted(async () => {
  if (visible.value) {
    lockPageScroll()
    await initializeDialog()
  }
})

onUnmounted(() => {
  unlockPageScroll()
})

watch([currentStep, userInput], () => {
  persistDraft()
})

watch(messages, () => {
  persistDraft()
}, { deep: true })

watch(form, () => {
  persistDraft()
}, { deep: true })

const initializeDialog = async () => {
  resetState()
  await loadStatus()

  if (loadDraft()) {
    await nextTick()
    autoResizeComposer()
    await scrollToBottom({ force: true })
    await focusComposer()
    return
  }

  await streamAssistantMessage('你好，我是学枢智导。我们会用聊天方式完成基础资料。先只确认一个问题：你的专业是什么？')
}

const resetState = () => {
  streamRunId += 1
  currentStep.value = 1
  userInput.value = ''
  isThinking.value = false
  isAssistantStreaming.value = false
  isUserReadingHistory.value = false
  schoolSuggestions.value = []
  form.school = ''
  form.major = ''
  form.grade = ''
  form.daily_study_time = ''
  form.global_learning_goal = ''
  form.programming_languages = []
  form.courses = []
  messages.value = []
  submitting.value = false
  isDraftHydrating = false
}

const formatTime = () => {
  const now = new Date()
  const hour = String(now.getHours()).padStart(2, '0')
  const minute = String(now.getMinutes()).padStart(2, '0')
  return `${hour}:${minute}`
}

const sleep = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms))

const isMessageListNearBottom = () => {
  const el = messageListRef.value
  if (!el) return true

  const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  return distanceToBottom <= MESSAGE_BOTTOM_THRESHOLD
}

const handleMessageListScroll = () => {
  if (!messageListRef.value) return
  isUserReadingHistory.value = !isMessageListNearBottom()
}

const scrollToBottom = async (options: { force?: boolean } = {}) => {
  await nextTick()

  const el = messageListRef.value
  if (!el) return

  const shouldScroll = options.force || !isUserReadingHistory.value || isMessageListNearBottom()

  if (!shouldScroll) return

  el.scrollTop = el.scrollHeight
  isUserReadingHistory.value = false
}

const focusComposer = async () => {
  await nextTick()
  inputRef.value?.focus()
}

const splitToTypewriterChunks = (text: string) => {
  const chunks: string[] = []
  let buffer = ''

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    if (char == null) continue

    const isAscii = /[A-Za-z0-9_+#./-]/.test(char)

    if (isAscii) {
      buffer += char
      if (buffer.length >= 4) {
        chunks.push(buffer)
        buffer = ''
      }
      continue
    }

    if (buffer) {
      chunks.push(buffer)
      buffer = ''
    }

    chunks.push(char)
  }

  if (buffer) chunks.push(buffer)
  return chunks
}

const getChunkDelay = (chunk: string) => {
  if (/\n/.test(chunk)) return 80
  if (/[。！？?]/.test(chunk)) return 110
  if (/[，、；;]/.test(chunk)) return 60
  if (/[A-Za-z0-9_+#./-]{2,}/.test(chunk)) return 24
  return 18
}

const streamAssistantMessage = async (content: string) => {
  const runId = streamRunId
  isAssistantStreaming.value = true
  isThinking.value = true

  await scrollToBottom()
  await sleep(160)

  if (runId !== streamRunId) return

  isThinking.value = false

  const messageId = Date.now() + Math.floor(Math.random() * 1000)

  messages.value.push({
    id: messageId,
    role: 'assistant',
    content: '',
    time: formatTime(),
    streaming: true,
  })

  await scrollToBottom()

  const chunks = splitToTypewriterChunks(content)

  for (const chunk of chunks) {
    if (runId !== streamRunId) return

    const msgIndex = messages.value.findIndex(item => item.id === messageId)
    if (msgIndex === -1) return

    const currentMessage = messages.value[msgIndex]
    if (!currentMessage) return

    messages.value[msgIndex] = {
      ...currentMessage,
      content: currentMessage.content + chunk,
    }

    await scrollToBottom()
    await sleep(getChunkDelay(chunk))
  }

  const msgIndex = messages.value.findIndex(item => item.id === messageId)
  if (msgIndex !== -1) {
    const currentMessage = messages.value[msgIndex]
    if (!currentMessage) return

    messages.value[msgIndex] = {
      ...currentMessage,
      streaming: false,
    }
  }

  isAssistantStreaming.value = false
  await focusComposer()
}

const addUserMessage = (content: string) => {
  messages.value.push({
    id: Date.now() + Math.floor(Math.random() * 1000),
    role: 'user',
    content,
    time: formatTime(),
  })
}

const handleComposerKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Enter') return
  if (event.shiftKey) return

  event.preventDefault()
  handleSend()
}

const handleInputChange = () => {
  autoResizeComposer()

  if (currentStep.value !== 4) return

  if (schoolSearchTimer) clearTimeout(schoolSearchTimer)

  const query = userInput.value.trim()

  if (!query) {
    schoolSuggestions.value = []
    return
  }

  schoolSearchTimer = setTimeout(async () => {
    try {
      const res = await searchSchools(query, 8)
      schoolSuggestions.value = res.data?.data ?? []
    } catch {
      schoolSuggestions.value = []
    }
  }, 300)
}

const autoResizeComposer = () => {
  const textarea = inputRef.value
  if (!textarea) return

  textarea.style.height = '42px'
  textarea.style.height = `${Math.min(textarea.scrollHeight, 82)}px`
}

const selectSchool = (school: SchoolItem) => {
  if (isAssistantStreaming.value) return

  userInput.value = school.name
  schoolSuggestions.value = []
  handleSend()
}

const isReplySelected = (reply: string) => {
  if (!userInput.value) return false

  const parts = userInput.value.split(/[,，、\s]+/).filter(Boolean)
  return parts.includes(reply)
}

const handleQuickReply = (reply: string) => {
  if (isAssistantStreaming.value) return

  if (reply === '暂不选择') {
    userInput.value = reply
    handleSend()
    return
  }

  if (isMultiSelectStep.value) {
    const parts = userInput.value.split(/[,，、\s]+/).filter(Boolean)

    if (parts.includes(reply)) {
      userInput.value = parts.filter(item => item !== reply).join('，')
    } else {
      parts.push(reply)
      userInput.value = parts.join('，')
    }

    nextTick(autoResizeComposer)
    return
  }

  userInput.value = reply
  handleSend()
}

const extractMultiple = (text: string, presets: string[]) => {
  const parts = text.split(/[,，、\s]+/).filter(Boolean)
  const result: string[] = []

  parts.forEach(part => {
    const matched = presets.find(item => item === part || part.includes(item) || item.includes(part))

    if (matched && !result.includes(matched)) {
      result.push(matched)
      return
    }

    if (!matched && !result.includes(part)) {
      result.push(part)
    }
  })

  return result
}

/*
const getGradeHint = (grade: string) => {
  if (grade.includes('大一')) return '偏基础导入'
  if (grade.includes('大二')) return '核心专业课'
  if (grade.includes('大三')) return '项目与复习'
  if (grade.includes('大四')) return '毕设与实习'
  if (grade.includes('研')) return '专题深入'
  return '调整难度'
}
*/

const getReplyHint = (reply: string) => {
  if (currentStep.value === 7) {
    const courseHints: Record<string, string> = {
      数据结构: '算法、树图',
      操作系统: '进程、内存',
      计算机网络: '协议、分层',
      数据库系统: 'SQL、事务',
      编译原理: '词法、语法',
      机器学习: '模型、评估',
    }

    return courseHints[reply] || ''
  }

  return ''
}

const handleSend = async () => {
  if (!canSend.value) return

  const text = userInput.value.trim()
  if (!text) return

  isUserReadingHistory.value = false

  addUserMessage(text)
  userInput.value = ''
  schoolSuggestions.value = []

  await nextTick(autoResizeComposer)
  await scrollToBottom({ force: true })

  if (currentStep.value === 1) {
    const foundMajor = PRESET_MAJORS.find(major => text.includes(major))
    form.major = foundMajor || text
    currentStep.value = 2
    await streamAssistantMessage(`已记录专业：${form.major}。接下来只确认年级，我会据此调整讲解深度。`)
    return
  }

  if (currentStep.value === 2) {
    const foundGrade = PRESET_GRADES.find(grade => text.includes(grade))
    form.grade = foundGrade || text
    currentStep.value = 3
    await streamAssistantMessage(`已记录年级：${form.grade}。现在只聊学习目标。`)
    return
  }

  if (currentStep.value === 3) {
    const foundGoal = PRESET_GOALS.find(goal => text.includes(goal))
    form.global_learning_goal = foundGoal || text
    currentStep.value = 4
    await streamAssistantMessage(`目标已记录：${form.global_learning_goal}。接下来确认学校，输入学校名称后我会给出搜索建议。`)
    return
  }

  if (currentStep.value === 4) {
    form.school = text
    currentStep.value = 5
    await streamAssistantMessage(`学校已记录：${form.school}。现在只确认每天大约能学习多久。`)
    return
  }

  if (currentStep.value === 5) {
    const foundStudyTime = PRESET_DAILY_STUDY_TIME.find(time => text.includes(time))
    form.daily_study_time = foundStudyTime || text
    currentStep.value = 6
    await streamAssistantMessage(`学习时间已记录：${form.daily_study_time}。现在选择常用编程语言，也可以暂不选择。`)
    return
  }

  if (currentStep.value === 6) {
    if (text !== '暂不选择') {
      const languages = extractMultiple(text, PRESET_PROGRAMMING_LANGUAGES)
      form.programming_languages = languages.length > 0 ? languages : [text]
    }

    currentStep.value = 7
    await streamAssistantMessage('技术栈信息已记录。最后只确认本学期核心课程，可以多选。')
    return
  }

  if (currentStep.value === 7) {
    const courses = extractMultiple(text, PRESET_COURSES)
    form.courses = courses.length > 0 ? courses : [text]
    currentStep.value = 8
    persistDraft()
    await streamAssistantMessage('基础资料已经完成。这些信息会展示到个人中心，也会用于初始化学习路径、资源推荐和题库偏好。')
  }
}

const loadStatus = async () => {
  if (!hasAuthToken()) return

  try {
    const res = await getProfileOnboarding()
    const baseInfo = res.data?.data?.base_info

    if (!baseInfo) return

    form.school = baseInfo.school || ''
    form.major = baseInfo.major || ''
    form.grade = baseInfo.grade || ''
    form.daily_study_time = baseInfo.daily_study_time || ''
    form.global_learning_goal = baseInfo.global_learning_goal || ''
    form.programming_languages = Array.isArray(baseInfo.programming_languages) ? baseInfo.programming_languages : []
    form.courses = Array.isArray(baseInfo.courses) ? baseInfo.courses : []
  } catch (error) {
    console.error('Failed to load onboarding data', error)
  }
}

const submitForm = async () => {
  submitting.value = true

  try {
    await updateProfileOnboarding({
      school: form.school ? form.school.trim() : '',
      major: form.major ? form.major.trim() : '',
      grade: form.grade ? form.grade.trim() : '',
      daily_study_time: form.daily_study_time || '',
      global_learning_goal: form.global_learning_goal || '',
      programming_languages: form.programming_languages,
      courses: form.courses as any,
    })

    await updateMe({ is_first_login: true }).catch(() => {})
    clearDraft()

    toast.success('基础资料已完成')
    visible.value = false
    emit('success')

    if (route.query.onboarding) {
      router.replace({ path: route.path, query: {} })
    }
  } catch (error) {
    console.error('Failed to submit onboarding', error)
    toast.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

const handleCompleteLater = async () => {
  try {
    await updateMe({ is_first_login: false }).catch(() => {})
  } catch (error) {
    console.error('Failed to keep onboarding pending', error)
  }

  persistDraft()
  visible.value = false

  if (route.query.onboarding) {
    router.replace({ path: route.path, query: {} })
  }
}
</script>

<style scoped>
.onboarding-page {
  position: fixed;
  inset: 0;
  z-index: 2000;
  width: 100%;
  height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 0;
  color: #0f172a;
  /* 深色半透明遮罩 + 背景模糊，让底层页面模糊可见 */
  background: rgba(10, 15, 35, 0.55);
  backdrop-filter: blur(12px) saturate(120%);
  -webkit-backdrop-filter: blur(12px) saturate(120%);
  /* 阻止点击穿透到下层所有元素 */
  pointer-events: all;
}

.onboarding-page,
.onboarding-page * {
  box-sizing: border-box;
}

.onboarding-standalone {
  height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  background:
      radial-gradient(circle at 14% 12%, rgba(20, 184, 166, 0.13), transparent 30%),
      radial-gradient(circle at 86% 10%, rgba(103, 232, 249, 0.15), transparent 28%),
      linear-gradient(180deg, #f8fcfb 0%, #eef8f8 100%);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.onboarding-container {
  position: relative;
  width: min(1240px, calc(100vw - 40px));
  height: min(760px, calc(100dvh - 72px));
  max-height: calc(100dvh - 72px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid rgba(159, 220, 218, 0.58);
  border-radius: 26px;
  background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(247, 253, 252, 0.98)),
      #ffffff;
  box-shadow:
      0 40px 100px rgba(10, 15, 35, 0.26),
      0 8px 32px rgba(20, 184, 166, 0.12),
      0 1px 0 rgba(255, 255, 255, 0.95) inset;
}

.onboarding-container::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
      radial-gradient(circle at 18% 8%, rgba(70, 184, 180, 0.12), transparent 30%),
      radial-gradient(circle at 86% 16%, rgba(98, 201, 197, 0.12), transparent 34%);
}

.conversation-header {
  position: relative;
  z-index: 1;
  min-height: 112px;
  padding: 18px 132px 14px;
  text-align: center;
  border-bottom: 1px solid rgba(190, 230, 229, 0.74);
}

.header-center {
  position: relative;
  top: 0;
  width: min(560px, 100%);
  margin: 0 auto;
}

.progress-badge {
  position: absolute;
  top: 32px;
  left: 24px;
  z-index: 4;
  min-width: 96px;
  height: 48px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 7px 12px;
  border: 1px solid rgba(158, 218, 216, 0.78);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  box-shadow:
      0 12px 28px rgba(15, 23, 42, 0.06),
      0 1px 0 rgba(255, 255, 255, 0.9) inset;
}

.progress-badge strong {
  color: var(--color-primary-text);
  font-size: 17px;
  font-weight: 950;
  line-height: 1;
}

.progress-badge span {
  margin-top: 4px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 850;
  line-height: 1;
}

.skip-btn {
  position: absolute;
  top: 40px;
  right: 24px;
  z-index: 5;
  height: 32px;
  padding: 0 15px;
  border: 1px solid rgba(158, 218, 216, 0.76);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: #41676d;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
  backdrop-filter: blur(14px);
  transition:
      transform 0.18s ease,
      border-color 0.18s ease,
      background 0.18s ease,
      color 0.18s ease,
      box-shadow 0.18s ease;
}

.skip-btn:hover {
  color: var(--color-primary-text);
  border-color: rgba(20, 160, 157, 0.86);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.title-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 10px;
  margin-bottom: 6px;
}

.title-mark span:first-child {
  width: 32px;
  height: 5px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--color-primary), var(--color-action));
  box-shadow: 0 8px 20px rgba(70, 184, 180, 0.2);
}

.title-mark span:last-child {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #93c5fd;
}

.conversation-header h1 {
  margin: 0;
  color: #0f172a;
  font-size: 28px;
  font-weight: 950;
  line-height: 1.15;
  letter-spacing: 0;
}

.conversation-header p {
  margin: 8px auto 0;
  max-width: 520px;
  color: #5f7780;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.55;
}

.onboarding-workspace {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 214px minmax(0, 1fr) 300px;
  gap: 16px;
  margin: 0 20px 20px;
}

.step-rail,
.profile-panel {
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(183, 226, 224, 0.9);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
      0 16px 42px rgba(15, 23, 42, 0.06),
      0 1px 0 rgba(255, 255, 255, 0.94) inset;
  backdrop-filter: blur(18px);
}

.step-rail {
  padding: 16px;
}

.step-rail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(225, 250, 248, 0.96), rgba(255, 255, 255, 0.96));
  color: var(--color-primary-text);
}

.step-rail-title span {
  font-size: 20px;
  font-weight: 950;
}

.step-rail-title strong {
  font-size: 13px;
  font-weight: 950;
}

.step-list {
  display: grid;
  gap: 9px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.step-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 54px;
  padding: 9px;
  border: 1px solid transparent;
  border-radius: 16px;
  color: #6b7f87;
}

.step-item.active {
  border-color: rgba(20, 160, 157, 0.34);
  background: rgba(231, 250, 248, 0.8);
  color: var(--color-primary-text);
}

.step-item.done {
  color: #315f66;
  background: rgba(248, 253, 252, 0.88);
}

.step-index {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #78919a;
  background: rgba(236, 248, 247, 0.9);
  font-size: 13px;
  font-weight: 950;
}

.step-item.active .step-index,
.step-item.done .step-index {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
}

.step-item strong {
  display: block;
  font-size: 13px;
  font-weight: 950;
}

.step-item small {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: #8aa0a8;
  font-size: 11px;
  font-weight: 750;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-card {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  margin: 0;
  overflow: hidden;
  border: 1px solid rgba(183, 226, 224, 0.96);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
      0 18px 48px rgba(15, 23, 42, 0.08),
      0 1px 0 rgba(255, 255, 255, 0.95) inset;
  backdrop-filter: blur(18px);
}

.current-question {
  display: block;
  padding: 16px 22px;
  border-bottom: 1px solid rgba(203, 235, 233, 0.82);
  background:
      linear-gradient(120deg, rgba(232, 250, 248, 0.92), rgba(255, 255, 255, 0.94) 54%, rgba(240, 253, 250, 0.88)),
      #ffffff;
}

.question-copy span {
  display: block;
  margin-bottom: 5px;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 950;
}

.question-copy strong {
  display: block;
  color: #0f172a;
  font-size: 19px;
  font-weight: 950;
  line-height: 1.3;
}

.question-copy p {
  margin: 7px 0 0;
  color: #64748b;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.5;
}

.message-list {
  position: relative;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 20px 22px;
  scroll-behavior: smooth;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.message-list::-webkit-scrollbar {
  width: 8px;
}

.message-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(203, 213, 225, 0.72);
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: min-content;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.message-row.user {
  justify-content: flex-end;
}

.avatar-icon,
.user-avatar {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 950;
}

.avatar-icon {
  color: var(--color-primary-text);
  background:
      linear-gradient(145deg, rgba(235, 251, 249, 0.95), rgba(213, 246, 243, 0.95));
  border: 1px solid rgba(158, 218, 216, 0.88);
  box-shadow: 0 12px 24px rgba(70, 184, 180, 0.12);
}

.user-avatar {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.22);
}

.message-main {
  max-width: min(640px, 84%);
}

.message-row.user .message-main {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 7px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 850;
}

.message-bubble {
  position: relative;
  border: 1px solid rgba(203, 235, 233, 0.98);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 12px 28px rgba(15, 23, 42, 0.06),
      0 1px 0 rgba(255, 255, 255, 0.96) inset;
}

.message-row.assistant .message-bubble {
  border-top-left-radius: 8px;
}

.message-row.user .message-bubble {
  border-color: transparent;
  border-top-right-radius: 8px;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 14px 28px rgba(20, 160, 157, 0.2);
}

.message-text {
  margin: 0;
  padding: 13px 16px;
  color: #1e293b;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.85;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-row.user .message-text {
  color: #ffffff;
  font-weight: 750;
}

.action-row {
  margin-top: 2px;
}

.action-bubble {
  width: min(100%, 620px);
  padding: 14px;
  background:
      linear-gradient(145deg, rgba(246, 254, 253, 0.98), rgba(255, 255, 255, 0.98));
}

.action-copy {
  margin-bottom: 12px;
}

.action-copy strong {
  display: block;
  color: #123f48;
  font-size: 14px;
  font-weight: 950;
}

.action-copy p {
  margin: 5px 0 0;
  color: #68818a;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.55;
}

.action-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(203, 235, 233, 0.86);
}

.action-footer span {
  color: #68818a;
  font-size: 12px;
  font-weight: 850;
}

.confirm-selection-btn {
  height: 34px;
  padding: 0 13px;
  border: none;
  border-radius: 12px;
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  font-size: 12px;
  font-weight: 950;
  cursor: pointer;
}

.confirm-selection-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.thinking-bubble {
  display: inline-flex;
  gap: 6px;
  padding: 14px 18px;
}

.typing-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--color-primary);
  animation: typing-bounce 1s infinite ease-in-out;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.14s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.28s;
}

.back-bottom-btn {
  position: sticky;
  left: 50%;
  bottom: 10px;
  z-index: 8;
  transform: translateX(-50%);
  display: block;
  width: fit-content;
  height: 32px;
  margin: 10px auto 0;
  padding: 0 14px;
  border: 1px solid rgba(158, 218, 216, 0.9);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  backdrop-filter: blur(14px);
  box-shadow: 0 12px 28px rgba(70, 184, 180, 0.14);
  transition:
      box-shadow 0.18s ease,
      background 0.18s ease;
}

.back-bottom-btn:hover {
  background: #ffffff;
  box-shadow: 0 16px 34px rgba(70, 184, 180, 0.18);
}

.input-dock {
  border-top: 1px solid rgba(203, 235, 233, 0.9);
  background:
      linear-gradient(180deg, rgba(248, 250, 252, 0.86), rgba(255, 255, 255, 0.98));
  padding: 14px 16px 16px;
}

.quick-replies-grid,
.school-suggestions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  max-height: 132px;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding-right: 2px;
}

.quick-replies-grid::-webkit-scrollbar,
.school-suggestions-grid::-webkit-scrollbar {
  width: 6px;
}

.quick-replies-grid::-webkit-scrollbar-thumb,
.school-suggestions-grid::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(203, 213, 225, 0.65);
}

.quick-replies-grid::-webkit-scrollbar-track,
.school-suggestions-grid::-webkit-scrollbar-track {
  background: transparent;
}

.quick-replies-grid.is-card-mode {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.quick-reply-btn,
.school-suggestion-btn {
  position: relative;
  min-height: 36px;
  border: 1px solid rgba(183, 226, 224, 0.96);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #24545b;
  font-size: 13px;
  font-weight: 850;
  cursor: pointer;
  overflow: hidden;
  transition:
      border-color 0.16s ease,
      background 0.16s ease,
      color 0.16s ease,
      box-shadow 0.16s ease;
}

.quick-reply-btn {
  padding: 0 15px;
}

.quick-replies-grid.is-card-mode .quick-reply-btn {
  min-height: 54px;
  padding: 9px 13px;
  border-radius: 16px;
  text-align: left;
}

/* 年级专属：紧凑胶囊 pill，稍宽以容纳副标题 */
.quick-replies-grid.is-grade-mode {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: none;
  overflow: visible;
}

.quick-replies-grid.is-grade-mode .quick-reply-btn {
  min-height: 44px;
  padding: 6px 16px;
  border-radius: 999px;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  text-align: center;
  min-width: 68px;
}

.quick-replies-grid.is-grade-mode .quick-reply-btn small {
  margin-top: 2px;
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  white-space: nowrap;
}

.quick-replies-grid.is-grade-mode .quick-reply-btn.is-selected small {
  color: rgba(255, 255, 255, 0.8);
}

.quick-reply-btn span {
  display: block;
}

.quick-reply-btn small {
  display: block;
  margin-top: 4px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 750;
}

.quick-reply-btn:hover,
.school-suggestion-btn:hover {
  transform: none;
  z-index: auto;
  border-color: rgba(20, 160, 157, 0.82);
  color: var(--color-primary-text);
  background: linear-gradient(180deg, #ffffff 0%, #f4fcfb 100%);
  box-shadow: inset 0 0 0 1px rgba(20, 160, 157, 0.12);
}

.quick-reply-btn.is-selected {
  color: #ffffff;
  border-color: transparent;
  background: linear-gradient(135deg, var(--color-primary), var(--color-action));
  box-shadow: none;
}

.quick-reply-btn.is-selected:hover {
  color: #ffffff;
  border-color: transparent;
  background: linear-gradient(135deg, var(--color-primary), var(--color-action));
  box-shadow: none;
}

.quick-reply-btn.is-selected small {
  color: rgba(255, 255, 255, 0.82);
}

.quick-reply-btn:disabled,
.school-suggestion-btn:disabled {
  cursor: not-allowed;
  opacity: 0.58;
  transform: none;
  box-shadow: none;
}

.school-suggestion-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
}

.school-level-tag {
  padding: 2px 7px;
  border-radius: 999px;
  background: #e6f8f6;
  color: var(--color-primary-text);
  font-size: 11px;
  font-weight: 900;
}

.composer-wrapper {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 46px;
  gap: 10px;
  align-items: end;
  padding: 8px;
  border: 1px solid rgba(20, 160, 157, 0.5);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 0 0 5px rgba(20, 184, 166, 0.08),
      0 16px 34px rgba(15, 23, 42, 0.08);
}

.chat-composer {
  width: 100%;
  height: 42px;
  max-height: 82px;
  resize: none;
  border: none;
  outline: none;
  padding: 11px 10px 9px 12px;
  background: transparent;
  color: #0f172a;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.55;
  font-family: inherit;
}

.chat-composer::placeholder {
  color: #94a3b8;
}

.send-btn {
  width: 46px;
  height: 46px;
  border: none;
  border-radius: 17px;
  display: grid;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 14px 28px rgba(70, 184, 180, 0.24);
  cursor: pointer;
  transition:
      transform 0.16s ease,
      opacity 0.16s ease,
      box-shadow 0.16s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(70, 184, 180, 0.28);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  box-shadow: none;
}

.profile-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 15px;
  border: 1px solid rgba(199, 210, 254, 0.76);
  border-radius: 22px;
  background:
      linear-gradient(135deg, rgba(238, 242, 255, 0.86), rgba(255, 255, 255, 0.98));
}

.profile-footer strong {
  display: block;
  color: #0f172a;
  font-size: 16px;
  font-weight: 950;
}

.profile-footer p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 650;
}

.finish-btn {
  height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 15px;
  font-weight: 900;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 16px 32px rgba(70, 184, 180, 0.22);
}

.profile-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  overflow-y: auto;
}

.profile-panel::-webkit-scrollbar {
  width: 6px;
}

.profile-panel::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(158, 218, 216, 0.82);
}

.profile-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.profile-panel-head span {
  color: #315f66;
  font-size: 14px;
  font-weight: 950;
}

.profile-panel-head strong {
  color: var(--color-primary-text);
  font-size: 22px;
  font-weight: 950;
}

.progress-ring {
  --progress: 0;
  width: 96px;
  height: 96px;
  display: grid;
  place-items: center;
  justify-self: center;
  border-radius: 999px;
  background:
      radial-gradient(circle closest-side, #ffffff 72%, transparent 73%),
      conic-gradient(var(--color-primary) calc(var(--progress) * 1%), rgba(219, 239, 238, 0.95) 0);
  box-shadow:
      0 16px 36px rgba(20, 160, 157, 0.14),
      inset 0 0 0 1px rgba(255, 255, 255, 0.92);
}

.progress-ring span {
  color: var(--color-primary-text);
  font-size: 22px;
  font-weight: 950;
}

.info-block {
  min-height: 0;
}

.info-block h2 {
  margin: 0 0 9px;
  color: #123f48;
  font-size: 14px;
  font-weight: 950;
}

.info-list {
  display: grid;
  gap: 6px;
}

.info-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 32px;
  padding: 6px 10px;
  border-radius: 14px;
  font-size: 12px;
}

.info-row span {
  color: #6f8790;
  font-weight: 850;
}

.info-row strong {
  overflow: hidden;
  color: #123f48;
  font-weight: 950;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-row.confirmed {
  border: 1px solid rgba(183, 226, 224, 0.88);
  background: rgba(246, 254, 253, 0.9);
}

.info-row.pending {
  border: 1px dashed rgba(183, 226, 224, 0.9);
  background: rgba(255, 255, 255, 0.58);
}

.info-row.pending strong {
  color: #8aa0a8;
}

.empty-copy {
  margin: 0;
  padding: 13px;
  border-radius: 14px;
  background: rgba(246, 254, 253, 0.86);
  color: #6f8790;
  font-size: 12px;
  font-weight: 800;
}

.profile-note {
  margin-top: auto;
  align-self: stretch;
  padding: 13px;
  border: 1px solid rgba(20, 160, 157, 0.18);
  border-radius: 16px;
  background: linear-gradient(145deg, #e9fbf9, #ffffff);
  box-shadow: 0 -8px 24px rgba(255, 255, 255, 0.82);
}

.profile-note strong {
  display: block;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 950;
}

.profile-note p {
  margin: 6px 0 0;
  color: #68818a;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.6;
}

.message-pop-enter-active,
.message-pop-leave-active,
.fade-up-enter-active,
.fade-up-leave-active {
  transition:
      opacity 0.18s ease,
      transform 0.18s ease;
}

.message-pop-enter-from,
.message-pop-leave-to,
.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@keyframes typing-bounce {
  0%,
  80%,
  100% {
    transform: translateY(0);
    opacity: 0.45;
  }

  40% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

@media (max-width: 860px) {
  .onboarding-page {
    align-items: stretch;
    justify-content: stretch;
    padding: 0;
  }

  .onboarding-container {
    width: 100%;
    height: 100dvh;
    max-height: 100dvh;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .conversation-header {
    min-height: 134px;
    padding: 70px 20px 14px;
    text-align: left;
  }

  .header-center {
    top: 0;
    width: 100%;
    margin: 0;
  }

  .progress-badge {
    top: 34px;
    left: 16px;
  }

  .skip-btn {
    top: 42px;
    right: 16px;
  }

  .conversation-header h1 {
    font-size: 25px;
  }

  .conversation-header p {
    margin-left: 0;
    font-size: 13px;
  }

  .title-mark {
    justify-content: flex-start;
  }

  .onboarding-workspace {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr) auto;
    gap: 10px;
    margin: 0 12px 12px;
    overflow-y: auto;
  }

  .step-rail {
    padding: 10px;
  }

  .step-rail-title {
    margin-bottom: 10px;
  }

  .step-list {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .step-item {
    width: 138px;
    flex: 0 0 auto;
  }

  .chat-card {
    border-radius: 22px;
    min-height: 560px;
  }

  .current-question {
    padding: 16px;
  }

  .message-list {
    padding: 18px 14px;
  }

  .message-main {
    max-width: 82%;
  }

  .action-bubble {
    width: 100%;
  }

  .quick-replies-grid.is-card-mode {
    grid-template-columns: 1fr;
  }

  .quick-replies-grid,
  .school-suggestions-grid {
    max-height: 112px;
  }

  .profile-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .profile-panel {
    max-height: none;
  }

  .progress-ring {
    width: 96px;
    height: 96px;
  }
}
</style>
