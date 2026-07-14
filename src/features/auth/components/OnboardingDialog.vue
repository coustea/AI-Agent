<template>
  <section
    v-if="visible"
    :class="['onboarding-page', { 'onboarding-standalone': standalone }]"
  >
    <main class="onboarding-container">
      <header class="conversation-header">
        <div class="header-main">
          <div class="header-copy">
            <span class="header-eyebrow">学习画像初始化</span>
          </div>

          <button class="skip-btn" type="button" @click="handleCompleteLater">
            稍后完善
          </button>
        </div>

        <nav class="top-step-tabs" aria-label="填写步骤">
          <button
            v-for="step in stepTimeline"
            :key="step.key"
            :class="['top-step-tab', step.state]"
            type="button"
          >
            <span class="step-dot">{{ step.key }}</span>
            <span class="step-text">{{ step.short }}</span>
          </button>
        </nav>
      </header>

      <section class="onboarding-workspace">
        <section class="chat-area" aria-label="对话式填写基础资料">
          <div class="current-question">
            <span>当前确认</span>
            <strong>{{ currentQuestionTitle }}</strong>
            <p>{{ currentStepMeta.description }}</p>
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
                    <span>{{ msg.role === 'assistant' ? 'Mentorly' : '你' }}</span>
                    <span>{{ msg.time }}</span>
                  </div>

                  <div class="message-bubble">
                    <p class="message-text">
                      {{ msg.content }}<span v-if="msg.streaming" class="streaming-cursor"></span>
                    </p>

                    <div
                      v-if="msg.role === 'assistant' && isLatestAssistantMessage(msg.id) && showAssistantActions && currentQuickReplies.length > 0"
                      class="bubble-quick-replies"
                    >
                      <div class="quick-replies-grid">
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

                <div v-if="msg.role === 'user'" class="user-avatar">
                  你
                </div>
              </div>
            </transition-group>

            <div v-if="isThinking" class="message-row assistant thinking-row">
              <div class="avatar-icon">AI</div>

              <div class="message-main">
                <div class="message-meta">
                  <span>Mentorly</span>
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
              <transition name="fade-up">
                <div
                  v-if="currentStep === 4 && schoolSuggestions.length > 0"
                  class="school-autocomplete-popover"
                >
                  <button
                    v-for="school in schoolSuggestions"
                    :key="school.name"
                    class="autocomplete-suggestion-item"
                    type="button"
                    @click="selectSchool(school)"
                  >
                    <span class="school-name">{{ school.name }}</span>
                    <span v-if="school.level" class="school-level-tag">
                      {{ school.level }}
                    </span>
                  </button>
                </div>
              </transition>

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
                aria-label="发送"
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
            <div>
              <span>资料预览</span>
              <strong>{{ profileProgress }}%</strong>
            </div>
            <div class="progress-line" aria-hidden="true">
              <i :style="{ width: `${profileProgress}%` }"></i>
            </div>
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
            <strong>填写后可在个人中心继续修改</strong>
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

import { updateMe, getMe } from '@/features/auth/api/auth'
import { useCurrentUser } from '@/features/auth/model/currentUser'
import { updateProfileOnboarding } from '@/features/profile/api/profile'
import type { ProfileOnboardingUpdate } from '@/features/profile/api/profile'
import { searchSchools } from '@/features/profile/api/school'
import type { SchoolItem } from '@/features/profile/model/school'
import { hasAuthToken } from '@/shared/auth/token'

// 弹窗是否可见，支持 v-model（modelValue），standalone 表示独立落地页形态
const props = withDefaults(defineProps<{ modelValue?: boolean; standalone?: boolean }>(), {
  modelValue: true,
  standalone: false,
})

// 向父组件回传可见状态变化与提交成功事件
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const route = useRoute()
const router = useRouter()
const { currentUser } = useCurrentUser()

// 弹窗可见性的双向绑定封装
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

// 对话消息列表
const messages = ref<ChatMessage[]>([])
const submitting = ref(false)
const messageListRef = ref<HTMLDivElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

// 当前步骤（1-7 为采集步骤，>7 表示完成）、用户输入与各阶段状态
const currentStep = ref(1)
const userInput = ref('')
const isThinking = ref(false)
const isAssistantStreaming = ref(false)
const schoolSuggestions = ref<SchoolItem[]>([])
// 用户是否正在向上翻看历史消息（决定是否自动滚动到底部）
const isUserReadingHistory = ref(false)

// 判定“接近底部”的像素阈值
const MESSAGE_BOTTOM_THRESHOLD = 88

// 学校搜索防抖定时器、流式渲染运行号（用于中断旧流）、草稿水合标记、滚动锁存档
let schoolSearchTimer: ReturnType<typeof setTimeout> | null = null
let streamRunId = 0
let isDraftHydrating = false
let previousBodyOverflow = ''
let previousHtmlOverflow = ''

// 草稿本地存储 key，按用户隔离
const onboardingDraftKey = computed(() =>
  currentUser.value?.id
    ? `onboarding-dialog-draft:${currentUser.value.id}`
    : 'onboarding-dialog-draft',
)

// 收集到的学习画像表单数据
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

const PRESET_SCHOOLS = [
  '北京大学',
  '清华大学',
  '浙江大学',
  '北京邮电大学',
  '北京航空航天大学',
  '上海交通大学',
  '复旦大学',
  '南京大学',
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

// 7 步引导的元数据定义（专业→年级→目标→学校→时间→语言→课程）
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

const coursesValue = computed<string[]>(() => {
  return Array.isArray(form.courses) ? (form.courses as string[]).map(String) : []
})

// 是否已收集完所有必填项（或步骤超过 7）
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
  if (isAssistantStreaming.value) return 'Mentorly 正在输入...'
  if (currentStep.value === 1) return '输入专业名称，或点击推荐标签...'
  if (currentStep.value === 2) return '输入年级，或点击推荐标签...'
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
    case 4:
      return PRESET_SCHOOLS
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

// 页面滚动锁定：打开时禁掉 body/html 滚动
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

// 将当前进度持久化到 localStorage（水合中或 key 缺失时跳过）
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

// 从 localStorage 恢复草稿（含步骤、消息、表单）
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

// 切换可见时锁定/解锁页面滚动，并在打开时初始化对话
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

// 打开弹窗的初始化入口：重置状态→拉取已有资料→优先恢复草稿，否则发送开场白
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

  await streamAssistantMessage('你好，我是 Mentorly。我们会用聊天方式完成基础资料。先只确认一个问题：你的专业是什么？')
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

const isLatestAssistantMessage = (msgId: number) => {
  const assistantMsgs = messages.value.filter(m => m.role === 'assistant')
  if (assistantMsgs.length === 0) return false
  return assistantMsgs[assistantMsgs.length - 1]?.id === msgId
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

  const shouldScroll = options.force || isAssistantStreaming.value || !isUserReadingHistory.value || isMessageListNearBottom()

  if (!shouldScroll) return

  if (isAssistantStreaming.value && !options.force) {
    el.scrollTop = el.scrollHeight
  } else {
    el.scrollTo({
      top: el.scrollHeight,
      behavior: 'smooth',
    })
  }

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

// 以打字机效果逐段渲染助手消息（按 runId 支持中途中断）
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
  await nextTick()
  await scrollToBottom({ force: true })
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

// 发送消息：按当前步骤（1-7）解析用户输入写入表单并推进到下一步
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

// 从 /users/me 预填已保存的基础信息到表单
const loadStatus = async () => {
  if (!hasAuthToken()) return

  try {
    // 基础信息现在从 User 表读取（通过 /users/me 接口）
    const res = await getMe()
    const user = res.data?.data

    if (!user) return

    form.school = user.school || ''
    form.major = user.major || ''
    form.grade = user.grade || ''
    form.daily_study_time = user.daily_study_time || ''
    form.global_learning_goal = user.global_learning_goal || ''
    form.programming_languages = Array.isArray(user.programming_languages) ? user.programming_languages : []
    form.courses = Array.isArray(user.courses) ? user.courses : []
  } catch (error) {
    console.error('Failed to load onboarding data', error)
  }
}

// 提交引导结果：PATCH /profile/onboarding 保存并标记首次登录完成，随后关闭弹窗
const submitForm = async () => {
  submitting.value = true

  try {
    // 后端 PATCH /profile/onboarding 同步保存基本信息后立即返回，
    // 画像推理和评分由后台任务异步完成，前端无需等待。
    await updateProfileOnboarding({
      school: form.school ? form.school.trim() : '',
      major: form.major ? form.major.trim() : '',
      grade: form.grade ? form.grade.trim() : '',
      daily_study_time: form.daily_study_time || '',
      global_learning_goal: form.global_learning_goal || '',
      programming_languages: form.programming_languages,
      courses: form.courses as any,
    })

    // 标记首次登录完成（非关键，失败不影响流程）
    updateMe({ onboarding_completed: true }).catch(() => {})

    clearDraft()

    toast.success('基础资料已完成')
    // 立即关闭弹窗，让用户进入首页
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

// “稍后完善”：保留 onboarding 待完成状态并保存草稿，然后关闭弹窗
const handleCompleteLater = async () => {
  try {
    await updateMe({ onboarding_completed: false }).catch(() => {})
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
  padding: 24px 0;
  color: #0f172a;
  background: rgba(10, 15, 35, 0.55);
  backdrop-filter: blur(12px) saturate(120%);
  -webkit-backdrop-filter: blur(12px) saturate(120%);
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
    radial-gradient(circle at 12% 10%, rgba(20, 184, 166, 0.09), transparent 30%),
    radial-gradient(circle at 88% 8%, rgba(103, 232, 249, 0.1), transparent 28%),
    linear-gradient(180deg, #f8fcfb 0%, #eef8f8 100%);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.onboarding-container {
  position: relative;
  width: min(1240px, calc(100vw - 40px));
  height: min(760px, calc(100dvh - 64px));
  max-height: calc(100dvh - 64px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid rgba(190, 230, 229, 0.58);
  border-radius: 26px;
  background:
    radial-gradient(circle at 18% 10%, rgba(20, 184, 166, 0.07), transparent 28%),
    radial-gradient(circle at 86% 14%, rgba(59, 130, 246, 0.05), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(248, 253, 252, 0.98));
  box-shadow:
    0 38px 98px rgba(10, 15, 35, 0.22),
    0 1px 0 rgba(255, 255, 255, 0.96) inset;
}

.conversation-header {
  position: relative;
  z-index: 1;
  padding: 16px 34px 12px;
}

.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
}

.header-copy {
  min-width: 0;
}

.header-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-primary-text, #0f766e);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.header-eyebrow::before {
  content: '';
  width: 22px;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
}

.conversation-header h1 {
  margin: 8px 0 0;
  color: #0f172a;
  font-size: 30px;
  font-weight: 950;
  line-height: 1.12;
  letter-spacing: -0.03em;
}

.conversation-header p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.55;
}

.skip-btn {
  flex: 0 0 auto;
  height: 36px;
  padding: 0 16px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.54);
  color: #475569;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background 0.18s ease,
    color 0.18s ease;
}

.skip-btn:hover {
  color: var(--color-primary-text, #0f766e);
  border-color: rgba(20, 184, 166, 0.45);
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-1px);
}

.top-step-tabs {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 22px;
  overflow-x: auto;
  scrollbar-width: none;
}

.top-step-tabs::-webkit-scrollbar {
  display: none;
}

.top-step-tab {
  position: relative;
  flex: 1 0 0;
  min-width: 108px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 850;
  cursor: default;
}

.top-step-tab::after {
  content: '';
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: transparent;
}

.step-dot {
  width: 23px;
  height: 23px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(226, 232, 240, 0.75);
  color: #64748b;
  font-size: 12px;
  font-weight: 950;
}

.step-text {
  white-space: nowrap;
}

.top-step-tab.active {
  color: var(--color-primary-text, #0f766e);
  background: rgba(240, 253, 250, 0.72);
}

.top-step-tab.active::after {
  background: linear-gradient(90deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
}

.top-step-tab.active .step-dot,
.top-step-tab.done .step-dot {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
}

.top-step-tab.done {
  color: #0f766e;
}

.onboarding-workspace {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 34px;
  padding: 8px 34px 30px;
  overflow: hidden;
}

.chat-area {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
  background: transparent;
}

.current-question {
  max-width: 760px;
  padding: 0 0 18px;
}

.current-question span {
  display: block;
  margin-bottom: 6px;
  color: var(--color-primary-text, #0f766e);
  font-size: 12px;
  font-weight: 950;
  letter-spacing: 0.06em;
}

.current-question strong {
  display: block;
  color: #0f172a;
  font-size: 22px;
  font-weight: 950;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.current-question p {
  margin: 7px 0 0;
  color: #64748b;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.6;
}

.message-list {
  position: relative;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 10px 20px 0;
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
  gap: 18px;
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
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  border: none;
  font-size: 12px;
  font-weight: 950;
}

.avatar-icon {
  color: var(--color-primary-text, #0f766e);
  background: rgba(209, 250, 244, 0.82);
}

.user-avatar {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
}

.message-main {
  max-width: min(670px, 84%);
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
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
}

.message-bubble {
  position: relative;
  border: 1px solid rgba(226, 232, 240, 0.62);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.68);
  box-shadow: none;
}

.message-row.user .message-bubble {
  border-color: transparent;
  background: linear-gradient(145deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
  color: #ffffff;
}

.message-text {
  margin: 0;
  padding: 13px 16px;
  color: #1e293b;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.82;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-row.user .message-text {
  color: #ffffff;
  font-weight: 750;
}

.bubble-quick-replies {
  padding: 0 14px 14px;
}

.quick-replies-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-reply-btn {
  height: 32px;
  padding: 0 13px;
  border: 1px solid rgba(203, 213, 225, 0.86);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.84);
  color: #334155;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    border-color 0.15s ease,
    background 0.15s ease,
    color 0.15s ease;
}

.quick-reply-btn:hover {
  border-color: rgba(20, 184, 166, 0.58);
  background: rgba(240, 253, 250, 0.96);
  color: var(--color-primary-text, #0f766e);
  transform: translateY(-1px);
}

.quick-reply-btn.is-selected {
  color: #ffffff;
  border-color: transparent;
  background: linear-gradient(145deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
}

.quick-reply-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  transform: none;
}

.action-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.action-footer span {
  color: #68818a;
  font-size: 12px;
  font-weight: 850;
}

.confirm-selection-btn {
  height: 32px;
  padding: 0 13px;
  border: none;
  border-radius: 999px;
  color: #ffffff;
  background: #0f172a;
  font-size: 12px;
  font-weight: 900;
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
  background: var(--color-primary, #14b8a6);
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
  color: var(--color-primary-text, #0f766e);
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  backdrop-filter: blur(14px);
  box-shadow: 0 12px 28px rgba(70, 184, 180, 0.14);
}

.input-dock {
  padding: 12px 0 0;
  background: transparent;
}

.composer-wrapper {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 44px;
  gap: 10px;
  align-items: end;
  padding: 8px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: none;
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
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
  box-shadow: none;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    opacity 0.16s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.school-autocomplete-popover {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 200px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(20, 160, 157, 0.22);
  border-radius: 16px;
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.1);
  padding: 6px;
}

.autocomplete-suggestion-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: #1e293b;
  font-size: 13px;
  font-weight: 650;
  text-align: left;
  cursor: pointer;
  border-radius: 10px;
  transition: background 0.15s ease;
}

.autocomplete-suggestion-item:hover {
  background: rgba(20, 184, 166, 0.08);
}

.school-level-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(20, 184, 166, 0.12);
  color: var(--color-primary-text, #0f766e);
  border-radius: 999px;
  font-weight: 800;
}

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 14px;
  background: var(--color-primary, #14b8a6);
  margin-left: 4px;
  vertical-align: middle;
  animation: cursor-blink 1s step-end infinite;
}

.profile-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 15px 0;
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
  border-radius: 14px;
  font-weight: 900;
  background: linear-gradient(145deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
  box-shadow: none;
}

.profile-panel {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 4px 2px 8px 4px;
  background: transparent;
}

.profile-panel::-webkit-scrollbar {
  width: 6px;
}

.profile-panel::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(158, 218, 216, 0.82);
}

.profile-panel-head {
  display: grid;
  gap: 12px;
}

.profile-panel-head > div:first-child {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.profile-panel-head span {
  color: #123f48;
  font-size: 16px;
  font-weight: 950;
}

.profile-panel-head strong {
  color: var(--color-primary-text, #0f766e);
  font-size: 24px;
  font-weight: 950;
}

.progress-line {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(226, 232, 240, 0.9);
}

.progress-line i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--color-primary, #14b8a6), var(--color-action, #0ea5e9));
  transition: width 0.25s ease;
}

.info-block {
  min-height: 0;
}

.info-block h2 {
  margin: 0 0 12px;
  color: #123f48;
  font-size: 13px;
  font-weight: 950;
  letter-spacing: 0.08em;
}

.info-list {
  display: grid;
  gap: 9px;
}

.info-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 30px;
  font-size: 13px;
}

.info-row span {
  color: #64748b;
  font-weight: 850;
}

.info-row strong {
  overflow: hidden;
  color: #123f48;
  font-weight: 900;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-row.confirmed strong {
  color: var(--color-primary-text, #0f766e);
}

.info-row.pending strong {
  color: #94a3b8;
}

.empty-copy {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.6;
}

.profile-note {
  margin-top: 24px;
  flex-shrink: 0;
  color: #64748b;
}

.profile-note strong {
  display: block;
  color: var(--color-primary-text, #0f766e);
  font-size: 13px;
  font-weight: 950;
}

.profile-note p {
  margin: 6px 0 0;
  font-size: 12px;
  font-weight: 750;
  line-height: 1.65;
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

@keyframes cursor-blink {
  from,
  to {
    background-color: transparent;
  }

  50% {
    background-color: var(--color-primary, #14b8a6);
  }
}

@media (max-width: 960px) {
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
    padding: 22px 18px 14px;
  }

  .header-main {
    gap: 16px;
  }

  .conversation-header h1 {
    font-size: 25px;
  }

  .top-step-tabs {
    margin-top: 16px;
  }

  .top-step-tab {
    flex: 0 0 auto;
  }

  .onboarding-workspace {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, 1fr) auto;
    gap: 20px;
    padding: 4px 18px 18px;
    overflow-y: auto;
  }

  .chat-area {
    min-height: 560px;
  }

  .message-list {
    padding-right: 0;
  }

  .message-main {
    max-width: 82%;
  }

  .profile-panel {
    max-height: none;
    padding-bottom: 8px;
  }

  .profile-note {
    margin-top: 0;
  }
}

@media (max-width: 640px) {
  .header-main {
    align-items: stretch;
    flex-direction: column;
  }

  .skip-btn {
    align-self: flex-start;
  }

  .conversation-header h1 {
    font-size: 23px;
  }

  .current-question strong {
    font-size: 19px;
  }

  .message-row {
    gap: 8px;
  }

  .avatar-icon,
  .user-avatar {
    width: 30px;
    height: 30px;
    border-radius: 10px;
  }

  .message-main {
    max-width: 86%;
  }

  .composer-wrapper {
    grid-template-columns: minmax(0, 1fr) 42px;
    border-radius: 16px;
  }

  .send-btn {
    width: 42px;
    height: 42px;
  }

  .profile-footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>