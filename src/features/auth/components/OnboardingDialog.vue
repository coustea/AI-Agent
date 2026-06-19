<template>
  <div :class="['onboarding-root', { 'onboarding-standalone': standalone }]">
    <el-dialog
        v-model="visible"
        width="1160px"
        :show-close="false"
        :close-on-click-modal="false"
        :close-on-press-escape="false"
        class="onboarding-dialog"
        align-center
    >
      <section class="dialog-shell">
        <button class="skip-only-btn" type="button" @click="handleNeverShow">跳过</button>

        <main class="conversation-panel">
          <header class="conversation-header">
            <div class="header-left">
              <span class="agent-state">
                <i></i>
                学习画像智能体
              </span>
              <h1>用对话完成学习画像构建</h1>
              <p>每回答一步，右侧只展示已填写的信息，不展示空字段和策略说明。</p>
            </div>

            <div class="header-progress" aria-label="当前进度">
              <strong>{{ profileProgress }}%</strong>
              <span>画像完整度</span>
            </div>
          </header>

          <div class="step-strip" aria-label="画像构建步骤">
            <button
                v-for="step in ONBOARDING_STEPS"
                :key="step.key"
                type="button"
                :class="['step-dot', getStepState(step.key)]"
            >
              <strong>{{ step.key }}</strong>
              <span>{{ step.short }}</span>
            </button>
          </div>

          <section class="chat-card">
            <div class="current-question">
              <div>
                <span>当前步骤 · {{ currentStepMeta.short }}</span>
                <strong>{{ currentStepMeta.title }}</strong>
                <p>{{ currentStepMeta.description }}</p>
              </div>
              <em>{{ currentStepMeta.example }}</em>
            </div>

            <div ref="messageListRef" class="message-list">
              <transition-group name="message-pop" tag="div" class="message-inner">
                <div
                    v-for="msg in messages"
                    :key="msg.id"
                    :class="['message-row', msg.role, { 'is-streaming': msg.streaming }]"
                >
                  <div v-if="msg.role === 'assistant'" class="avatar-icon">AI</div>

                  <div class="message-main">
                    <div class="message-meta">
                      <span>{{ msg.role === 'assistant' ? '学习智能体' : '我' }}</span>
                      <span>{{ msg.time }}</span>
                    </div>

                    <div class="message-bubble">
                      <p class="message-text">{{ msg.content }}</p>
                    </div>
                  </div>
                </div>
              </transition-group>

              <div v-if="isThinking" class="message-row assistant thinking-row">
                <div class="avatar-icon">AI</div>
                <div class="message-main">
                  <div class="message-meta">
                    <span>学习智能体</span>
                    <span>{{ currentTimeLabel }}</span>
                  </div>
                  <div class="message-bubble thinking-bubble" aria-label="正在输入">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                  </div>
                </div>
              </div>
            </div>

            <div class="input-dock">
              <transition name="fade-up">
                <div v-if="currentStep <= 7 && currentQuickReplies.length > 0" class="quick-replies-wrapper">
                  <div class="quick-head">
                    <span>{{ currentStepMeta.quickTitle }}</span>
                    <em v-if="isMultiSelectStep">可多选，选完后点击发送</em>
                    <em v-else>点击后自动进入下一步</em>
                  </div>

                  <div :class="['quick-replies-grid', { 'is-card-mode': shouldShowReplyHint }]">
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
                </div>
              </transition>

              <transition name="fade-up">
                <div v-if="currentStep === 4 && limitedSchoolSuggestions.length > 0" class="school-suggestions-wrapper">
                  <div class="quick-head">
                    <span>学校搜索结果</span>
                    <em>最多展示 4 个结果，避免出现滚轮</em>
                  </div>
                  <div class="school-suggestions-grid">
                    <button
                        v-for="school in limitedSchoolSuggestions"
                        :key="school.name"
                        class="school-suggestion-btn"
                        type="button"
                        @click="selectSchool(school)"
                    >
                      <span class="school-name">{{ school.name }}</span>
                      <span v-if="school.level" class="school-level-tag">{{ school.level }}</span>
                    </button>
                  </div>
                </div>
              </transition>

              <transition name="fade-up">
                <div v-if="isMultiSelectStep && selectionItems.length > 0" class="selection-preview">
                  <span>当前选择</span>
                  <div>
                    <strong v-for="item in selectionItems" :key="item">{{ item }}</strong>
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
                  <el-icon><Position /></el-icon>
                </button>
              </div>

              <div v-else class="profile-footer">
                <div>
                  <strong>学习画像已经完成</strong>
                  <p>进入学习空间后，系统会根据这些信息生成路径、资源和题库。</p>
                </div>
                <el-button
                    class="finish-btn"
                    type="primary"
                    :loading="submitting"
                    @click="submitForm"
                >
                  进入学习空间
                  <el-icon class="el-icon--right"><Right /></el-icon>
                </el-button>
              </div>
            </div>
          </section>
        </main>

        <aside class="profile-panel">
          <div class="profile-top">
            <span>实时画像</span>
            <strong>{{ filledProfileCards.length }} 项信息</strong>
          </div>

          <section class="info-panel">
            <div class="panel-title">
              <span>已填写信息</span>
              <em>填一项，展示一项</em>
            </div>

            <div v-if="filledProfileCards.length === 0" class="empty-info-card">
              <span>等待第一条信息</span>
              <p>回答专业后，这里会立即出现第一张画像卡片。</p>
            </div>

            <transition-group v-else name="info-pop" tag="div" class="info-grid">
              <article
                  v-for="card in filledProfileCards"
                  :key="card.key"
                  class="info-card"
              >
                <div class="info-card-top">
                  <span class="info-icon">{{ card.icon }}</span>
                  <span class="info-label">{{ card.label }}</span>
                </div>
                <strong class="info-value">{{ card.value }}</strong>
              </article>
            </transition-group>
          </section>
        </aside>
      </section>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Position, Right } from '@element-plus/icons-vue'

import { updateMe } from '@/features/auth/api/auth'
import { getProfileOnboarding, updateProfileOnboarding } from '@/features/profile/api/profile'
import type { ProfileOnboardingUpdate } from '@/features/profile/api/profile'
import { isProfileOnboardingComplete } from '@/features/profile/model/profile'
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

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
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
  example: string
  quickTitle: string
}

type ProfileCard = {
  key: string
  icon: string
  label: string
  value: string
  filled: boolean
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
let schoolSearchTimer: ReturnType<typeof setTimeout> | null = null
let streamRunId = 0

const form = reactive<ProfileOnboardingUpdate>({
  school: '',
  major: '',
  grade: '',
  daily_study_time: '',
  global_learning_goal: '',
  programming_languages: [],
  courses: [],
})

const PRESET_MAJORS = ['软件工程', '计算机科学与技术', '人工智能', '数据科学与大数据技术', '网络空间安全', '电子信息工程']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库系统', '编译原理', '机器学习']
const PRESET_GOALS = ['期末复习', '考研学习', '进阶学习', '补基础', '项目实战']
const PRESET_GRADES = ['大一', '大二', '大三', '大四', '研一', '研二', '研三']
const PRESET_DAILY_STUDY_TIME = ['30min以下', '30-60min', '1-2h', '2-3h', '3h以上']
const PRESET_PROGRAMMING_LANGUAGES = ['Python', 'Java', 'C++', 'JavaScript', 'Go', 'Rust']
const ONBOARDING_STEPS: StepMeta[] = [
  {
    key: 1,
    short: '专业',
    title: '先确认专业方向',
    description: '专业会影响后续课程体系、案例选择和讲解方式。',
    example: '例如：软件工程、计算机科学与技术',
    quickTitle: '常见专业',
  },
  {
    key: 2,
    short: '年级',
    title: '确认学习阶段',
    description: '不同年级的学习重点不同，系统会据此调整难度。',
    example: '例如：大二、研一',
    quickTitle: '年级阶段',
  },
  {
    key: 3,
    short: '目标',
    title: '明确学习目标',
    description: '目标决定系统偏向期末复习、补基础、进阶学习还是项目实战。',
    example: '例如：期末复习、项目实战',
    quickTitle: '学习目标',
  },
  {
    key: 4,
    short: '学校',
    title: '填写学校名称',
    description: '输入学校名称后会出现搜索结果，可以直接选择。',
    example: '例如：重庆邮电大学',
    quickTitle: '学校名称',
  },
  {
    key: 5,
    short: '时间',
    title: '设置每日学习时间',
    description: '学习时间会影响节点大小、任务强度和复习节奏。',
    example: '例如：30-60min、1-2h',
    quickTitle: '每日时间',
  },
  {
    key: 6,
    short: '语言',
    title: '选择常用编程语言',
    description: '编程语言会影响代码示例、实操任务和项目练习。',
    example: '例如：Python、Java、C++',
    quickTitle: '技术栈',
  },
  {
    key: 7,
    short: '课程',
    title: '选择本学期核心课程',
    description: '课程会直接影响学习路径、题库练习和资源生成范围。',
    example: '建议选择 1-4 门重点课程',
    quickTitle: '核心课程',
  },
]

const currentTimeLabel = computed(() => formatTime())

const programmingLanguagesValue = computed<string[]>(() => {
  return Array.isArray(form.programming_languages) ? form.programming_languages.map(String) : []
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

const canSend = computed(() => {
  return userInput.value.trim().length > 0 && !isAssistantStreaming.value && !submitting.value
})

const isMultiSelectStep = computed(() => [6, 7].includes(currentStep.value))

const shouldShowReplyHint = computed(() => [2, 7].includes(currentStep.value))

const currentStepMeta = computed<StepMeta>(() => {
  const step = ONBOARDING_STEPS.find(item => item.key === Math.min(currentStep.value, 7))
  return step || ONBOARDING_STEPS[0]!
})

const composerPlaceholder = computed(() => {
  if (isAssistantStreaming.value) return '智能体正在输入...'
  if (currentStep.value === 2) return '选择年级或输入你的学习阶段...'
  if (currentStep.value === 4) return '输入学校名称，支持搜索选择...'
  if (currentStep.value === 7) return '选择课程或输入多个课程，用逗号、空格、顿号分隔...'
  if (isMultiSelectStep.value) return '可以输入多个内容，用逗号、空格或顿号分隔...'
  return '输入回复，Enter 发送，Shift + Enter 换行...'
})

const selectionItems = computed(() => {
  return userInput.value.split(/[,，、\s]+/).filter(Boolean)
})

const limitedSchoolSuggestions = computed(() => schoolSuggestions.value.slice(0, 4))

const profileCards = computed<ProfileCard[]>(() => {
  return [
    {
      key: 'major',
      icon: '🎓',
      label: '专业方向',
      value: form.major || '',
      filled: Boolean(form.major),
    },
    {
      key: 'grade',
      icon: '📍',
      label: '当前年级',
      value: form.grade || '',
      filled: Boolean(form.grade),
    },
    {
      key: 'goal',
      icon: '🎯',
      label: '学习目标',
      value: form.global_learning_goal || '',
      filled: Boolean(form.global_learning_goal),
    },
    {
      key: 'school',
      icon: '🏫',
      label: '学校',
      value: form.school || '',
      filled: Boolean(form.school),
    },
    {
      key: 'time',
      icon: '⏱',
      label: '每日时间',
      value: form.daily_study_time || '',
      filled: Boolean(form.daily_study_time),
    },
    {
      key: 'language',
      icon: '💻',
      label: '编程语言',
      value: programmingLanguagesValue.value.join('、'),
      filled: programmingLanguagesValue.value.length > 0,
    },
    {
      key: 'courses',
      icon: '📚',
      label: '核心课程',
      value: coursesValue.value.join('、'),
      filled: coursesValue.value.length > 0,
    },
  ]
})

const filledProfileCards = computed(() => profileCards.value.filter(item => item.filled))

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

watch(visible, async (open) => {
  if (!open) {
    streamRunId += 1
    return
  }
  await initializeDialog()
})

onMounted(async () => {
  if (visible.value) {
    await initializeDialog()
  }
})

const initializeDialog = async () => {
  resetState()
  const loadedComplete = await loadStatus()
  if (!loadedComplete) {
    await streamAssistantMessage('你好，我是你的学习画像智能体。我们用聊天方式完成画像构建，右侧会按填写顺序逐项展示信息。先告诉我：你目前是什么专业？')
  }
}

const resetState = () => {
  streamRunId += 1
  currentStep.value = 1
  userInput.value = ''
  isThinking.value = false
  isAssistantStreaming.value = false
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
}

const formatTime = () => {
  const now = new Date()
  const hour = String(now.getHours()).padStart(2, '0')
  const minute = String(now.getMinutes()).padStart(2, '0')
  return `${hour}:${minute}`
}

const sleep = (ms: number) => new Promise(resolve => window.setTimeout(resolve, ms))

const scrollToBottom = async () => {
  await nextTick()
  if (!messageListRef.value) return
  messageListRef.value.scrollTop = messageListRef.value.scrollHeight
}

const focusComposer = async () => {
  await nextTick()
  inputRef.value?.focus()
}

const splitToTypewriterChunks = (text: string) => {
  const chunks: string[] = []
  let buffer = ''

  for (let index = 0; index < text.length; index += 1) {
    const char = text.charAt(index)
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
  if (/[。！？!?]/.test(chunk)) return 110
  if (/[，、；;：:]/.test(chunk)) return 60
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
    const currentMsg = messages.value[msgIndex]
    if (!currentMsg) return
    messages.value[msgIndex] = {
      ...currentMsg,
      content: currentMsg.content + chunk,
    }

    await scrollToBottom()
    await sleep(getChunkDelay(chunk))
  }

  const msgIndex = messages.value.findIndex(item => item.id === messageId)
  if (msgIndex !== -1) {
    const currentMsg = messages.value[msgIndex]
    if (currentMsg) {
      messages.value[msgIndex] = {
        ...currentMsg,
        streaming: false,
      }
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
  textarea.style.height = '44px'
  textarea.style.height = `${Math.min(textarea.scrollHeight, 76)}px`
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

const getStepState = (key: number) => {
  if (currentStep.value > key) return 'is-done'
  if (currentStep.value === key) return 'is-active'
  return 'is-pending'
}

const getGradeHint = (grade: string) => {
  if (grade.includes('大一')) return '基础导入，降低抽象程度'
  if (grade.includes('大二')) return '核心专业课，重点建立体系'
  if (grade.includes('大三')) return '项目实践与综合复习'
  if (grade.includes('大四')) return '毕设、实习和冲刺复习'
  if (grade.includes('研')) return '专题研究和深度学习'
  return '用于调整学习难度'
}

const getReplyHint = (reply: string) => {
  if (currentStep.value === 2) {
    return getGradeHint(reply)
  }

  if (currentStep.value === 7) {
    const courseHints: Record<string, string> = {
      数据结构: '算法、线性表、树图基础',
      操作系统: '进程、内存、文件系统',
      计算机网络: '协议、分层、网络应用',
      数据库系统: 'SQL、事务、索引优化',
      编译原理: '词法、语法、中间代码',
      机器学习: '模型、训练、评估方法',
    }
    return courseHints[reply] || ''
  }

  return ''
}

const handleSend = async () => {
  if (!canSend.value) return

  const text = userInput.value.trim()
  if (!text) return

  addUserMessage(text)
  userInput.value = ''
  schoolSuggestions.value = []
  await nextTick(autoResizeComposer)
  await scrollToBottom()

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
    form.courses = courses.length > 0 ? courses : [text]
    currentStep.value = 8
    await streamAssistantMessage('学习画像已经完成。右侧信息会用于初始化学习路径、资源推荐和题库偏好。')
  }
}

const loadStatus = async () => {
  if (!hasAuthToken()) return false

  try {
    const res = await getProfileOnboarding()
    const baseInfo = res.data?.data?.base_info
    if (!baseInfo) return false

    form.school = baseInfo.school || ''
    form.major = baseInfo.major || ''
    form.grade = baseInfo.grade || ''
    form.daily_study_time = baseInfo.daily_study_time || ''
    form.global_learning_goal = baseInfo.global_learning_goal || ''
    form.programming_languages = Array.isArray(baseInfo.programming_languages) ? baseInfo.programming_languages : []
    form.courses = Array.isArray(baseInfo.courses) ? baseInfo.courses : []

    if (isProfileOnboardingComplete(baseInfo)) {
      currentStep.value = 8
      messages.value = [
        {
          id: Date.now(),
          role: 'assistant',
          content: '欢迎回来。我已经加载了之前填写的画像信息，可以直接进入学习空间。',
          time: formatTime(),
          streaming: false,
        },
      ]
      await scrollToBottom()
      return true
    }

    return false
  } catch (error) {
    console.error('Failed to load onboarding data', error)
    return false
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

    ElMessage.success('学习画像构建成功')
    visible.value = false
    emit('success')
    if (route.query.onboarding) {
      router.replace({ path: route.path, query: {} })
    }
  } catch (error) {
    console.error('Failed to submit onboarding', error)
    ElMessage.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

const handleNeverShow = async () => {
  try {
    await updateMe({ is_first_login: true })
  } catch (error) {
    console.error('Failed to update first login state', error)
  }
  visible.value = false
  emit('success')
  if (route.query.onboarding) {
    router.replace({ path: route.path, query: {} })
  }
}
</script>

<style scoped>
:global(html),
:global(body) {
  overflow: hidden;
}

.onboarding-root {
  width: 100%;
}

.onboarding-standalone {
  width: 100vw;
  height: 100vh;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
      radial-gradient(circle at 18% 12%, rgba(79, 70, 229, 0.14), transparent 30%),
      radial-gradient(circle at 88% 18%, rgba(14, 165, 233, 0.12), transparent 28%),
      linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.onboarding-dialog :deep(.el-dialog__header) {
  display: none;
}

.onboarding-dialog :deep(.el-dialog__body) {
  padding: 0;
  overflow: hidden;
  background: transparent;
}

.onboarding-dialog :deep(.el-overlay-dialog) {
  overflow: hidden !important;
}

.onboarding-dialog :deep(.el-dialog) {
  overflow: hidden;
  background: transparent;
  border-radius: 30px;
  box-shadow: none;
}

.dialog-shell {
  position: relative;
  width: 100%;
  height: min(86vh, 760px);
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 28px 80px rgba(15, 23, 42, 0.16),
      0 1px 0 rgba(255, 255, 255, 0.9) inset;
}

.dialog-shell * {
  box-sizing: border-box;
}

.onboarding-root,
.onboarding-root *,
.onboarding-dialog :deep(.el-overlay-dialog),
.onboarding-dialog :deep(.el-dialog),
.onboarding-dialog :deep(.el-dialog__body) {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.onboarding-root::-webkit-scrollbar,
.onboarding-root *::-webkit-scrollbar,
.onboarding-dialog :deep(.el-overlay-dialog)::-webkit-scrollbar,
.onboarding-dialog :deep(.el-dialog)::-webkit-scrollbar,
.onboarding-dialog :deep(.el-dialog__body)::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.skip-only-btn {
  position: absolute;
  top: 18px;
  right: 18px;
  z-index: 12;
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: all 0.18s ease;
}

.skip-only-btn:hover {
  color: #334155;
  border-color: rgba(148, 163, 184, 0.95);
  background: #ffffff;
  transform: translateY(-1px);
}

.conversation-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  background:
      linear-gradient(180deg, rgba(248, 250, 252, 0.94) 0%, rgba(255, 255, 255, 0.98) 52%, #ffffff 100%);
}

.conversation-header {
  min-height: 116px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 30px 34px 14px;
}

.header-left {
  min-width: 0;
}

.agent-state {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid rgba(199, 210, 254, 0.86);
  border-radius: 999px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 12px;
  font-weight: 900;
}

.agent-state i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.14);
}

.conversation-header h1 {
  margin: 13px 0 6px;
  color: #0f172a;
  font-size: 25px;
  line-height: 1.2;
  font-weight: 950;
  letter-spacing: -0.03em;
}

.conversation-header p {
  max-width: 560px;
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
}

.header-progress {
  width: 108px;
  height: 78px;
  flex: 0 0 108px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(199, 210, 254, 0.8);
  border-radius: 20px;
  background: linear-gradient(135deg, #ffffff 0%, #eef2ff 100%);
  box-shadow: 0 14px 30px rgba(79, 70, 229, 0.08);
}

.header-progress strong {
  color: #3730a3;
  font-size: 23px;
  font-weight: 950;
  line-height: 1;
}

.header-progress span {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  font-weight: 850;
}

.step-strip {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  padding: 0 34px 14px;
  overflow: hidden;
}

.step-dot {
  min-width: 0;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 15px;
  background: rgba(255, 255, 255, 0.82);
  color: #94a3b8;
  cursor: default;
  transition: all 0.18s ease;
}

.step-dot strong {
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #f1f5f9;
  color: inherit;
  font-size: 12px;
  font-weight: 950;
}

.step-dot span {
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-dot.is-active {
  border-color: rgba(99, 102, 241, 0.58);
  background: #eef2ff;
  color: #4f46e5;
  box-shadow: 0 10px 24px rgba(79, 70, 229, 0.1);
}

.step-dot.is-active strong,
.step-dot.is-done strong {
  background: #4f46e5;
  color: #ffffff;
}

.step-dot.is-done {
  border-color: rgba(199, 210, 254, 0.92);
  color: #4f46e5;
}

.chat-card {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  overflow: hidden;
  margin: 0 34px 30px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.current-question {
  min-height: 92px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 17px 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.86);
  background:
      radial-gradient(circle at 8% 0%, rgba(99, 102, 241, 0.12), transparent 38%),
      linear-gradient(135deg, rgba(248, 250, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.current-question div {
  min-width: 0;
}

.current-question span {
  display: block;
  color: #6366f1;
  font-size: 12px;
  font-weight: 950;
}

.current-question strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 17px;
  font-weight: 950;
}

.current-question p {
  margin: 5px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.current-question em {
  max-width: 230px;
  flex: 0 0 230px;
  padding: 10px 12px;
  border: 1px solid rgba(199, 210, 254, 0.8);
  border-radius: 15px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 12px;
  line-height: 1.55;
  font-style: normal;
  font-weight: 850;
}

.message-list {
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 18px 20px;
  scroll-behavior: smooth;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.45) transparent;
}

.message-inner {
  min-height: min-content;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 12px;
  overflow: visible;
}

.onboarding-root .message-list::-webkit-scrollbar {
  width: 6px;
  height: 6px;
  display: block;
}

.onboarding-root .message-list::-webkit-scrollbar-track {
  background: transparent;
}

.onboarding-root .message-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.42);
}

.onboarding-root .message-list::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.55);
}

.message-row {
  width: 100%;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.avatar-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%);
  color: #4f46e5;
  font-size: 12px;
  font-weight: 950;
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.12);
}

.message-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.message-row.assistant .message-main {
  max-width: min(54ch, calc(100% - 58px));
}

.message-row.user .message-main {
  max-width: min(40ch, 72%);
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 850;
  line-height: 1;
}

.message-row.user .message-meta {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 100%;
  padding: 11px 14px;
  border-radius: 18px;
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
  overflow: hidden;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.message-row.assistant .message-bubble {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-top-left-radius: 7px;
  background: #ffffff;
  color: #334155;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
}

.message-row.user .message-bubble {
  border-bottom-right-radius: 7px;
  background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.2);
}

.message-text {
  max-width: 100%;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.thinking-row .message-bubble {
  width: 72px;
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thinking-bubble {
  gap: 5px;
}

.typing-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #94a3b8;
  animation: dot-bounce 1.15s infinite ease-in-out;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.16s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.32s;
}

@keyframes dot-bounce {
  0%, 80%, 100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-4px);
  }
}

.input-dock {
  flex-shrink: 0;
  padding: 14px 18px 18px;
  border-top: 1px solid rgba(226, 232, 240, 0.78);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.84) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.quick-replies-wrapper,
.school-suggestions-wrapper,
.selection-preview {
  position: relative;
  z-index: 3;
  margin-bottom: 10px;
  overflow: visible;
}

.quick-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.quick-head span {
  color: #334155;
  font-size: 12px;
  font-weight: 950;
}

.quick-head em {
  color: #94a3b8;
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.quick-replies-grid {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  overflow: visible;
  isolation: isolate;
}

.quick-replies-grid.is-card-mode {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  overflow: visible;
}

.quick-reply-btn {
  position: relative;
  z-index: 1;
  min-width: 0;
  min-height: 34px;
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 3px;
  padding: 7px 12px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  cursor: pointer;
  transition: all 0.18s ease;
}

.quick-reply-btn span {
  max-width: 100%;
  overflow: hidden;
  font-size: 13px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-reply-btn small {
  max-width: 100%;
  overflow: hidden;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 750;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-reply-btn:hover:not(:disabled) {
  z-index: 8;
  border-color: rgba(99, 102, 241, 0.72);
  background: #eef2ff;
  color: #4f46e5;
  transform: translateY(-1px);
  box-shadow:
      0 12px 26px rgba(79, 70, 229, 0.16),
      0 0 0 3px rgba(99, 102, 241, 0.08);
}

.quick-reply-btn:hover:not(:disabled) small {
  color: #64748b;
}

.quick-reply-btn.is-selected {
  z-index: 6;
  border-color: #4f46e5;
  background: #eef2ff;
  color: #4f46e5;
  box-shadow:
      0 12px 26px rgba(79, 70, 229, 0.16),
      0 0 0 3px rgba(99, 102, 241, 0.08);
}

.quick-reply-btn.is-selected small {
  color: #64748b;
}

.quick-reply-btn.is-selected:hover:not(:disabled) {
  z-index: 12;
  border-color: rgba(99, 102, 241, 0.8);
  background: #eef2ff;
  color: #4f46e5;
  transform: translateY(-1px);
  box-shadow:
      0 14px 30px rgba(79, 70, 229, 0.18),
      0 0 0 3px rgba(99, 102, 241, 0.1);
}

.quick-reply-btn.is-selected:hover:not(:disabled) small {
  color: #64748b;
}

.quick-reply-btn:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.school-suggestions-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  overflow: hidden;
}

.school-suggestion-btn {
  min-width: 0;
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 13px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  text-align: left;
  transition: all 0.16s ease;
}

.school-suggestion-btn:hover {
  border-color: rgba(99, 102, 241, 0.45);
  background: #f8fafc;
}

.school-name {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.school-level-tag {
  flex: 0 0 auto;
  padding: 3px 7px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 11px;
  font-weight: 900;
}

.selection-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px dashed rgba(99, 102, 241, 0.5);
  border-radius: 14px;
  background: rgba(238, 242, 255, 0.62);
  overflow: hidden;
}

.selection-preview span {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 950;
}

.selection-preview div {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  overflow: hidden;
}

.selection-preview strong {
  max-width: 120px;
  overflow: hidden;
  padding: 4px 8px;
  border-radius: 999px;
  background: #ffffff;
  color: #3730a3;
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 7px;
  border: 1px solid rgba(203, 213, 225, 0.95);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.07);
  transition: all 0.18s ease;
}

.composer-wrapper:focus-within {
  border-color: rgba(99, 102, 241, 0.72);
  box-shadow:
      0 14px 34px rgba(79, 70, 229, 0.11),
      0 0 0 4px rgba(99, 102, 241, 0.1);
}

.chat-composer {
  flex: 1;
  width: 100%;
  height: 44px;
  max-height: 76px;
  resize: none;
  overflow: hidden;
  padding: 10px 10px 8px 12px;
  border: none;
  outline: none;
  background: transparent;
  color: #0f172a;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.55;
}

.chat-composer::placeholder {
  color: #94a3b8;
}

.chat-composer:disabled {
  cursor: not-allowed;
  color: #94a3b8;
}

.send-btn {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 15px;
  background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.25);
  transition: all 0.18s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.3);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.42;
  box-shadow: none;
}

.profile-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 190px;
  gap: 12px;
  align-items: stretch;
}

.profile-footer > div {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid rgba(199, 210, 254, 0.8);
  border-radius: 16px;
  background: #eef2ff;
}

.profile-footer strong {
  display: block;
  color: #3730a3;
  font-size: 14px;
  font-weight: 950;
}

.profile-footer p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.finish-btn {
  width: 100%;
  height: auto;
  border: none;
  border-radius: 16px;
  font-size: 14px;
  font-weight: 900;
  background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.2);
}

.profile-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  overflow: hidden;
  padding: 30px 22px 22px;
  border-left: 1px solid rgba(226, 232, 240, 0.9);
  background:
      radial-gradient(circle at 88% 6%, rgba(99, 102, 241, 0.16), transparent 26%),
      linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.profile-top {
  padding-right: 58px;
}

.profile-top span {
  display: block;
  color: #6366f1;
  font-size: 12px;
  font-weight: 950;
}

.profile-top strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 22px;
  font-weight: 950;
  letter-spacing: -0.03em;
}

.info-panel {
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.05);
}

.info-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  padding: 14px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-title span {
  color: #1e293b;
  font-size: 13px;
  font-weight: 950;
}

.panel-title em {
  color: #94a3b8;
  font-size: 11px;
  font-style: normal;
  font-weight: 850;
}

.empty-info-card {
  height: 100%;
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px;
  border: 1px dashed rgba(148, 163, 184, 0.55);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.78);
  text-align: center;
}

.empty-info-card span {
  color: #475569;
  font-size: 14px;
  font-weight: 950;
}

.empty-info-card p {
  margin: 8px 0 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.55;
}

.info-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 9px;
  overflow: hidden;
}

.info-card {
  min-width: 0;
  min-height: 72px;
  padding: 9px;
  border: 1px solid rgba(199, 210, 254, 0.74);
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #eef2ff 100%);
  overflow: hidden;
}

.info-card-top {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 11px;
  font-weight: 900;
}

.info-icon {
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.82);
  font-size: 13px;
}

.info-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-value {
  display: block;
  margin-top: 6px;
  overflow: hidden;
  color: #1e293b;
  font-size: 13px;
  font-weight: 950;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fade-up-enter-active,
.fade-up-leave-active,
.info-pop-enter-active,
.info-pop-leave-active,
.message-pop-enter-active,
.message-pop-leave-active {
  transition: all 0.22s ease;
}

.fade-up-enter-from,
.fade-up-leave-to,
.info-pop-enter-from,
.info-pop-leave-to,
.message-pop-enter-from,
.message-pop-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 1160px) {
  .onboarding-dialog :deep(.el-dialog) {
    width: calc(100vw - 28px) !important;
  }

  .dialog-shell {
    grid-template-columns: minmax(0, 1fr) 330px;
  }

  .conversation-header,
  .step-strip {
    padding-left: 24px;
    padding-right: 24px;
  }

  .chat-card {
    margin-left: 24px;
    margin-right: 24px;
  }
}

@media (max-width: 900px) {
  .dialog-shell {
    height: min(92vh, 720px);
    min-height: 0;
    grid-template-columns: 1fr;
  }

  .profile-panel {
    display: none;
  }

  .conversation-header {
    min-height: 106px;
    padding: 24px 20px 12px;
  }

  .conversation-header h1 {
    font-size: 21px;
  }

  .conversation-header p {
    font-size: 12px;
  }

  .step-strip {
    padding: 0 20px 12px;
    gap: 6px;
  }

  .step-dot {
    height: 42px;
    flex-direction: column;
    gap: 2px;
  }

  .step-dot strong {
    width: 20px;
    height: 20px;
  }

  .chat-card {
    margin: 0 20px 22px;
  }

  .current-question {
    min-height: 84px;
    padding: 14px 16px;
  }

  .current-question em {
    display: none;
  }
}

@media (max-width: 640px) {
  .dialog-shell {
    height: min(94vh, 680px);
    min-height: 0;
    border-radius: 22px;
  }

  .skip-only-btn {
    top: 14px;
    right: 14px;
  }

  .header-progress {
    display: none;
  }

  .conversation-header {
    padding: 22px 16px 10px;
  }

  .step-strip {
    padding: 0 16px 10px;
  }

  .step-dot span {
    display: none;
  }

  .chat-card {
    margin: 0 16px 18px;
    border-radius: 22px;
  }

  .current-question strong {
    font-size: 15px;
  }

  .current-question p {
    font-size: 12px;
  }

  .message-list {
    padding: 14px;
  }

  .message-inner {
    gap: 10px;
  }

  .avatar-icon {
    width: 31px;
    height: 31px;
    flex-basis: 31px;
    border-radius: 12px;
  }

  .message-row.assistant .message-main {
    max-width: min(48ch, calc(100% - 42px));
  }

  .message-row.user .message-main {
    max-width: 84%;
  }

  .message-bubble {
    font-size: 13px;
  }

  .input-dock {
    padding: 12px 12px 14px;
  }

  .quick-replies-grid.is-card-mode,
  .school-suggestions-grid,
  .profile-footer {
    grid-template-columns: 1fr;
  }

  .finish-btn {
    min-height: 48px;
  }
}
</style>
