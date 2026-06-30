<template>
  <section
      v-if="visible"
      :class="['onboarding-page', { 'onboarding-standalone': standalone }]"
  >
    <main class="onboarding-container">
      <header class="conversation-header">
        <div class="progress-badge" aria-label="画像完成度">
          <strong>{{ profileProgress }}%</strong>
          <span>画像完成度</span>
        </div>

        <button class="skip-btn" type="button" @click="handleNeverShow">
          跳过
        </button>

        <div class="header-center">
          <div class="title-mark">
            <span></span>
            <span></span>
          </div>

          <h1>学枢智导</h1>
          <p>通过对话完成基础信息收集，为你初始化更合适的学习路径。</p>
        </div>
      </header>

      <section class="chat-card">
        <div class="current-question">
          <div class="question-copy">
            <span>当前问题 · {{ currentStepMeta.short }}</span>
            <strong>{{ currentStepMeta.title }}</strong>
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
          <transition name="fade-up">
            <div
                v-if="currentStep <= 7 && currentQuickReplies.length > 0"
                class="quick-replies-wrapper"
            >
              <div class="quick-head">
                <span>{{ currentStepMeta.quickTitle }}</span>
                <em v-if="isCourseFormStep">可多选，选完后点击发送</em>
                <em v-else-if="isMultiSelectStep">可多选，选完后点击发送</em>
                <em v-else>点击后自动进入下一步</em>
              </div>

              <div :class="['quick-replies-grid', { 'is-grade-mode': isCompactReplyStep }]">
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
                  <small v-if="shouldShowReplyHint && getReplyHint(reply)">{{ getReplyHint(reply) }}</small>
                </button>
              </div>
            </div>
          </transition>

          <transition name="fade-up">
            <div
                v-if="currentStep === 4 && schoolSuggestions.length > 0"
                class="school-suggestions-wrapper"
            >
              <div class="quick-head">
                <span>学校搜索结果</span>
                <em>选择一个匹配的学校</em>
              </div>

              <div class="school-suggestions-grid">
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
            </div>
          </transition>

          <transition name="fade-up">
            <div v-if="isMultiSelectStep && selectionItems.length > 0" class="selection-preview">
              <span>当前选择</span>
              <div>
                <strong v-for="item in selectionItems" :key="item">
                  {{ item }}
                </strong>
              </div>
            </div>
          </transition>

          <div v-if="currentStep <= 7" class="composer-wrapper">
            <textarea
                ref="inputRef"
                v-model="userInput"
                class="chat-composer"
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
              <strong>学习画像已经完成</strong>
              <p>进入学习空间后，系统会根据这些信息生成路径、资源和题库。</p>
            </div>

            <button
                class="btn btn-primary finish-btn"
                :disabled="submitting"
                @click="submitForm"
            >
              <span>进入学习空间</span>
              <Right class="btn-icon-right ml-2" />
            </button>
          </div>
        </div>
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

const currentTimeLabel = computed(() => formatTime())

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

const isMultiSelectStep = computed(() => currentStep.value === 6)
const isCourseFormStep = computed(() => currentStep.value === 7)
const shouldShowReplyHint = computed(() => false)
const isCompactReplyStep = computed(() => [2, 7].includes(currentStep.value))

const currentStepMeta = computed<StepMeta>(() => {
  return ONBOARDING_STEPS.find(step => step.key === Math.min(currentStep.value, 7)) ?? ONBOARDING_STEPS[0]!
})

const composerPlaceholder = computed(() => {
  if (isAssistantStreaming.value) return '学枢智导正在输入...'
  if (currentStep.value === 2) return '选择年级或输入你的学习阶段...'
  if (currentStep.value === 4) return '输入学校名称，支持搜索选择...'
  if (currentStep.value === 7) return '选择课程或输入多门课程，用逗号、空格或顿号分隔...'
  if (isMultiSelectStep.value) return '可以输入多个内容，用逗号、空格或顿号分隔...'
  return '输入回复，Enter 发送，Shift + Enter 换行...'
})

const selectionItems = computed(() => {
  return userInput.value.split(/[,，、\s]+/).filter(Boolean)
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

  await streamAssistantMessage('你好，我是学枢智导。我们会用聊天方式完成画像初始化。先告诉我：你目前是什么专业？')
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
  if (currentStep.value === 7) {
    return coursesValue.value.includes(reply)
  }

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

  if (currentStep.value === 7) {
    if (coursesValue.value.includes(reply)) {
      form.courses = coursesValue.value.filter(item => item !== reply)
    } else {
      form.courses = [...coursesValue.value, reply]
    }

    userInput.value = form.courses.join('，')
    persistDraft()
    nextTick(autoResizeComposer)
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

const completeCourseStep = async (courses: string[]) => {
  form.courses = courses
  currentStep.value = 8
  userInput.value = ''
  persistDraft()
  await nextTick(autoResizeComposer)
  await streamAssistantMessage('学习画像已经完成。这些信息会用于初始化学习路径、资源推荐和题库偏好。')
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
    await streamAssistantMessage(`已记录专业：${form.major}。接下来确认年级，我会据此调整讲解深度。`)
    return
  }

  if (currentStep.value === 2) {
    const foundGrade = PRESET_GRADES.find(grade => text.includes(grade))
    form.grade = foundGrade || text
    currentStep.value = 3
    await streamAssistantMessage(`已记录年级：${form.grade}。现在告诉我你的主要学习目标。`)
    return
  }

  if (currentStep.value === 3) {
    const foundGoal = PRESET_GOALS.find(goal => text.includes(goal))
    form.global_learning_goal = foundGoal || text
    currentStep.value = 4
    await streamAssistantMessage(`目标已记录：${form.global_learning_goal}。接下来输入学校名称，我会给出搜索建议。`)
    return
  }

  if (currentStep.value === 4) {
    form.school = text
    currentStep.value = 5
    await streamAssistantMessage(`学校已记录：${form.school}。现在设置每天大约能学习多久。`)
    return
  }

  if (currentStep.value === 5) {
    const foundStudyTime = PRESET_DAILY_STUDY_TIME.find(time => text.includes(time))
    form.daily_study_time = foundStudyTime || text
    currentStep.value = 6
    await streamAssistantMessage(`学习时间已记录：${form.daily_study_time}。可以选择常用编程语言，也可以暂不选择。`)
    return
  }

  if (currentStep.value === 6) {
    if (text !== '暂不选择') {
      const languages = extractMultiple(text, PRESET_PROGRAMMING_LANGUAGES)
      form.programming_languages = languages.length > 0 ? languages : [text]
    }

    currentStep.value = 7
    await streamAssistantMessage('技术栈信息已记录。最后选择本学期核心课程，可以多选。')
    return
  }

  if (currentStep.value === 7) {
    const courses = extractMultiple(text, PRESET_COURSES)
    await completeCourseStep(courses.length > 0 ? courses : [text])
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

    await updateMe({ is_first_login: false }).catch(() => {})
    clearDraft()

    toast.success('学习画像构建成功')
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

const handleNeverShow = async () => {
  try {
    await updateMe({ is_first_login: false })
  } catch (error) {
    console.error('Failed to update first login state', error)
  }

  clearDraft()
  visible.value = false
  emit('success')

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
      radial-gradient(circle at 14% 12%, rgba(99, 102, 241, 0.12), transparent 30%),
      radial-gradient(circle at 86% 10%, rgba(59, 130, 246, 0.12), transparent 28%),
      linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.onboarding-container {
  position: relative;
  width: min(1120px, calc(100vw - 40px));
  height: min(720px, calc(100dvh - 72px));
  max-height: calc(100dvh - 72px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid rgba(219, 228, 242, 0.6);
  border-radius: 30px;
  background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(248, 250, 255, 0.98)),
      #ffffff;
  box-shadow:
      0 40px 100px rgba(10, 15, 35, 0.35),
      0 8px 32px rgba(99, 102, 241, 0.12),
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
  min-height: 138px;
  padding: 16px 132px 12px;
  text-align: center;
  border-bottom: 1px solid rgba(226, 232, 240, 0.78);
}

.header-center {
  position: relative;
  top: 0;
  width: min(560px, 100%);
  margin: 0 auto;
}

.progress-badge {
  position: absolute;
  top: 42px;
  left: 24px;
  z-index: 4;
  min-width: 96px;
  height: 48px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 7px 12px;
  border: 1px solid rgba(203, 213, 225, 0.76);
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
  top: 50px;
  right: 24px;
  z-index: 5;
  height: 32px;
  padding: 0 15px;
  border: 1px solid rgba(203, 213, 225, 0.72);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.66);
  color: #64748b;
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
  color: #334155;
  border-color: rgba(148, 163, 184, 0.96);
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
  font-size: 30px;
  font-weight: 950;
  line-height: 1.1;
  letter-spacing: -0.05em;
}

.conversation-header p {
  margin: 8px auto 0;
  max-width: 520px;
  color: #64748b;
  font-size: 14px;
  font-weight: 650;
  line-height: 1.55;
}

.chat-card {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  margin: 0 24px 24px;
  overflow: hidden;
  border: 1px solid rgba(219, 228, 242, 0.92);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
      0 18px 48px rgba(15, 23, 42, 0.08),
      0 1px 0 rgba(255, 255, 255, 0.95) inset;
  backdrop-filter: blur(18px);
}

.current-question {
  display: block;
  padding: 18px 26px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background:
      linear-gradient(120deg, rgba(238, 242, 255, 0.92), rgba(255, 255, 255, 0.92) 52%, rgba(239, 246, 255, 0.86)),
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
  font-size: 20px;
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
  padding: 22px 26px;
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
      linear-gradient(145deg, rgba(238, 242, 255, 0.95), rgba(219, 234, 254, 0.95));
  border: 1px solid rgba(199, 210, 254, 0.88);
  box-shadow: 0 12px 24px rgba(70, 184, 180, 0.12);
}

.user-avatar {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.22);
}

.message-main {
  max-width: min(660px, 74%);
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
  border: 1px solid rgba(226, 232, 240, 0.98);
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
  border-color: rgba(191, 219, 254, 0.92);
  border-top-right-radius: 8px;
  background: linear-gradient(145deg, #eef4ff, #e0e7ff);
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
  color: #1e3a8a;
  font-weight: 750;
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
  background: #818cf8;
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
  border: 1px solid rgba(199, 210, 254, 0.9);
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
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  background:
      linear-gradient(180deg, rgba(248, 250, 252, 0.86), rgba(255, 255, 255, 0.98));
  padding: 14px 20px 16px;
}

.quick-replies-wrapper,
.school-suggestions-wrapper,
.selection-preview {
  margin-bottom: 12px;
}

.quick-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 9px;
  color: #64748b;
  font-size: 12px;
}

.quick-head span {
  color: #334155;
  font-size: 13px;
  font-weight: 950;
}

.quick-head em {
  color: #94a3b8;
  font-style: normal;
  font-weight: 800;
}

.quick-replies-grid,
.school-suggestions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  max-height: 128px;
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

.quick-reply-btn,
.school-suggestion-btn {
  position: relative;
  min-height: 36px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
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


/* 年级专属：紧凑胶囊 pill，稍宽以容纳副标题 */
.quick-replies-grid.is-grade-mode {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: none;
  overflow: visible;
}

.quick-replies-grid.is-grade-mode .quick-reply-btn {
  min-height: 40px;
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
  border-color: rgba(129, 140, 248, 0.9);
  color: #4338ca;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(129, 140, 248, 0.12);
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
  background: #eef2ff;
  color: var(--color-primary-text);
  font-size: 11px;
  font-weight: 900;
}

.selection-preview {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid rgba(199, 210, 254, 0.78);
  border-radius: 18px;
  background: rgba(238, 242, 255, 0.62);
}

.selection-preview > span {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 900;
  line-height: 25px;
}

.selection-preview div {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.selection-preview strong {
  padding: 5px 9px;
  border-radius: 999px;
  background: #ffffff;
  color: #4338ca;
  font-size: 12px;
  font-weight: 900;
  box-shadow: 0 6px 16px rgba(70, 184, 180, 0.08);
}

.composer-wrapper {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 46px;
  gap: 10px;
  align-items: end;
  padding: 8px;
  border: 1px solid rgba(129, 140, 248, 0.82);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 0 0 5px rgba(99, 102, 241, 0.08),
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
    min-height: 150px;
    padding: 76px 20px 14px;
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

  .chat-card {
    margin: 0 12px 12px;
    border-radius: 22px;
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

  .quick-replies-grid,
  .school-suggestions-grid {
    max-height: 112px;
  }

  .profile-footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
