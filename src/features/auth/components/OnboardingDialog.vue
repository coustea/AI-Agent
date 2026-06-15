<template>
  <div :class="['onboarding-root', { 'onboarding-standalone': standalone }]">
    <el-dialog
      v-model="visible"
      width="980px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="onboarding-dialog"
      align-center
    >
      <section class="dialog-shell">
        <button class="skip-only-btn" type="button" @click="handleNeverShow">跳过</button>

        <main class="chat-stage">
          <div ref="messageListRef" class="message-list">
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
              <div v-if="profileChips.length > 0" class="extracted-strip">
                <span class="strip-title">已从对话提取</span>
                <div class="chip-list">
                  <span v-for="item in profileChips" :key="item.label" class="profile-chip">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </span>
                </div>
              </div>
            </transition>

            <transition name="fade-up">
              <div v-if="currentStep <= 7 && currentQuickReplies.length > 0" class="quick-replies-wrapper">
                <div class="quick-replies-scroll">
                  <button
                    v-for="reply in currentQuickReplies"
                    :key="reply"
                    class="quick-reply-btn"
                    :class="{ 'is-selected': isReplySelected(reply) }"
                    type="button"
                    :disabled="isAssistantStreaming"
                    @click="handleQuickReply(reply)"
                  >
                    {{ reply }}
                  </button>
                </div>
              </div>
            </transition>

            <transition name="fade-up">
              <div v-if="currentStep === 4 && schoolSuggestions.length > 0" class="school-suggestions-wrapper">
                <div class="school-suggestions-list">
                  <button
                    v-for="school in schoolSuggestions"
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
              <el-button
                class="finish-btn"
                type="primary"
                :loading="submitting"
                @click="submitForm"
              >
                完成构建，进入学习空间
                <el-icon class="el-icon--right"><Right /></el-icon>
              </el-button>
            </div>
          </div>
        </main>
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

const currentTimeLabel = computed(() => formatTime())

const isComplete = computed(() => {
  return currentStep.value > 7 || Boolean(
    form.school &&
    form.major &&
    form.grade &&
    form.daily_study_time &&
    form.global_learning_goal,
  )
})

const canSend = computed(() => {
  return userInput.value.trim().length > 0 && !isAssistantStreaming.value && !submitting.value
})

const composerPlaceholder = computed(() => {
  if (isAssistantStreaming.value) return '智能体正在输入...'
  if (currentStep.value === 4) return '输入学校名称，支持搜索选择...'
  if (isMultiSelectStep.value) return '可以输入多个内容，用逗号、空格或顿号分隔...'
  return '在这里输入你的回复，Enter 发送，Shift + Enter 换行...'
})

const profileChips = computed(() => {
  const chips: Array<{ label: string; value: string }> = []
  if (form.major) chips.push({ label: '专业', value: String(form.major) })
  if (form.grade) chips.push({ label: '年级', value: String(form.grade) })
  if (form.global_learning_goal) chips.push({ label: '目标', value: String(form.global_learning_goal) })
  if (form.school) chips.push({ label: '学校', value: String(form.school) })
  if (form.daily_study_time) chips.push({ label: '时间', value: String(form.daily_study_time) })
  if (Array.isArray(form.programming_languages) && form.programming_languages.length > 0) {
    chips.push({ label: '语言', value: form.programming_languages.join('、') })
  }
  if (Array.isArray(form.courses) && form.courses.length > 0) {
    chips.push({ label: '课程', value: form.courses.join('、') })
  }
  return chips
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

const isMultiSelectStep = computed(() => [6, 7].includes(currentStep.value))

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
    await streamAssistantMessage(
      '你好！我是你的专属学习智能体。\n\n接下来我们像聊天一样完成一次学习画像构建。我会根据你的回答提取专业、年级、学校、学习目标、学习时间、技术栈和课程信息。\n\n先从最基础的开始：你目前的专业是什么？',
    )
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
    const char = text[index]
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
  if (/\n/.test(chunk)) return 120
  if (/[。！？!?]/.test(chunk)) return 180
  if (/[，、；;：:]/.test(chunk)) return 90
  if (/[A-Za-z0-9_+#./-]{2,}/.test(chunk)) return 34
  return 24
}

const streamAssistantMessage = async (content: string) => {
  const runId = streamRunId
  isAssistantStreaming.value = true
  isThinking.value = true
  await scrollToBottom()
  await sleep(220)

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

    messages.value[msgIndex] = {
      ...messages.value[msgIndex],
      content: messages.value[msgIndex].content + chunk,
    }

    await scrollToBottom()
    await sleep(getChunkDelay(chunk))
  }

  const msgIndex = messages.value.findIndex(item => item.id === messageId)
  if (msgIndex !== -1) {
    messages.value[msgIndex] = {
      ...messages.value[msgIndex],
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
  textarea.style.height = '44px'
  textarea.style.height = `${Math.min(textarea.scrollHeight, 88)}px`
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
    await streamAssistantMessage(`已提取你的专业：${form.major}。\n\n接下来确认一下年级，你目前是大几或研几？`)
    return
  }

  if (currentStep.value === 2) {
    const foundGrade = PRESET_GRADES.find(grade => text.includes(grade))
    form.grade = foundGrade || text
    currentStep.value = 3
    await streamAssistantMessage(`好的，年级是：${form.grade}。\n\n你现在最主要的学习目标是什么？比如期末复习、考研学习、补基础、项目实战。`)
    return
  }

  if (currentStep.value === 3) {
    const foundGoal = PRESET_GOALS.find(goal => text.includes(goal))
    form.global_learning_goal = foundGoal || text
    currentStep.value = 4
    await streamAssistantMessage(`目标已记录：${form.global_learning_goal}。\n\n接下来告诉我你的学校名称。输入学校名称时，我会自动帮你搜索匹配。`)
    return
  }

  if (currentStep.value === 4) {
    form.school = text
    currentStep.value = 5
    await streamAssistantMessage(`学校已记录：${form.school}。\n\n为了给你安排合适的学习节奏，你每天大约能抽出多少学习时间？`)
    return
  }

  if (currentStep.value === 5) {
    const foundStudyTime = PRESET_DAILY_STUDY_TIME.find(time => text.includes(time))
    form.daily_study_time = foundStudyTime || text
    currentStep.value = 6
    await streamAssistantMessage(`学习时间已记录：${form.daily_study_time}。\n\n如果你的专业涉及编程，可以告诉我常用的编程语言。之后生成代码示例、练习和项目任务时，会优先贴合你的技术栈。`)
    return
  }

  if (currentStep.value === 6) {
    if (text !== '暂不选择') {
      const languages = extractMultiple(text, PRESET_PROGRAMMING_LANGUAGES)
      form.programming_languages = languages.length > 0 ? languages : [text]
    }
    currentStep.value = 7
    await streamAssistantMessage('好的，技术栈信息已记录。\n\n最后一步：这学期你主要学习了哪些核心课程？可以一次输入多个，例如：数据结构、操作系统、数据库系统。')
    return
  }

  if (currentStep.value === 7) {
    const courses = extractMultiple(text, PRESET_COURSES)
    form.courses = courses.length > 0 ? courses : [text]
    currentStep.value = 8
    await streamAssistantMessage('学习画像已经构建完成。\n\n我会基于这些信息初始化你的个性化学习路径、资源推荐策略和题库练习偏好。点击下方按钮即可进入学习空间。')
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

    if (form.major && form.grade && form.daily_study_time && form.global_learning_goal) {
      currentStep.value = 8
      messages.value = [
        {
          id: Date.now(),
          role: 'assistant',
          content: '欢迎回来。我已经加载了你之前填写的学习画像信息。点击下方按钮即可进入学习空间。',
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

    await updateMe({ is_first_login: false }).catch(() => {})

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
    await updateMe({ is_first_login: false })
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
.onboarding-root {
  width: 100%;
}

.onboarding-standalone {
  width: 100vw;
  height: 100vh;
  min-height: 720px;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 18% 12%, rgba(99, 102, 241, 0.12), transparent 34%),
    radial-gradient(circle at 82% 16%, rgba(14, 165, 233, 0.12), transparent 30%),
    linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.onboarding-dialog :deep(.el-dialog__header) {
  display: none;
}

.onboarding-dialog :deep(.el-dialog__body) {
  padding: 0;
  background: transparent;
}

.onboarding-dialog :deep(.el-dialog) {
  overflow: hidden;
  background: transparent;
  border-radius: 28px;
  box-shadow: none;
}

.dialog-shell {
  position: relative;
  height: 88vh;
  min-height: 640px;
  max-height: 860px;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow:
    0 28px 70px rgba(15, 23, 42, 0.16),
    0 1px 0 rgba(255, 255, 255, 0.8) inset;
}

.skip-only-btn {
  position: absolute;
  top: 18px;
  right: 20px;
  z-index: 8;
  height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
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

.chat-stage {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 60px 54px 26px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  scroll-behavior: smooth;
}

.message-list::-webkit-scrollbar {
  width: 6px;
}

.message-list::-webkit-scrollbar-track {
  background: transparent;
}

.message-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.36);
}

.message-row {
  width: 100%;
  display: flex;
  gap: 12px;
  align-items: flex-start;
  animation: message-in 0.28s ease both;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

@keyframes message-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.avatar-icon {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%);
  color: #4f46e5;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 0.02em;
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.12);
}

.message-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.message-row.assistant .message-main {
  max-width: min(56ch, calc(100% - 70px));
}

.message-row.user .message-main {
  max-width: min(44ch, 72%);
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 2px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.message-row.user .message-meta {
  justify-content: flex-end;
}

.message-bubble {
  position: relative;
  max-width: 100%;
  border-radius: 20px;
  line-height: 1.75;
  font-size: 15px;
  word-break: break-word;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.message-row.assistant .message-bubble {
  padding: 14px 18px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-top-left-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.message-row.user .message-bubble {
  padding: 12px 16px;
  border-bottom-right-radius: 8px;
  background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
  color: #ffffff;
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.22);
}

.message-row.is-streaming .message-bubble {
  border-color: rgba(129, 140, 248, 0.5);
  box-shadow:
    0 14px 34px rgba(79, 70, 229, 0.1),
    0 0 0 3px rgba(99, 102, 241, 0.06);
}

.message-text {
  max-width: 100%;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.thinking-row .message-bubble {
  width: 74px;
  min-height: 42px;
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
  padding: 14px 32px 26px;
  border-top: 1px solid rgba(226, 232, 240, 0.78);
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.82) 0%, rgba(255, 255, 255, 0.96) 100%);
  backdrop-filter: blur(16px);
}

.extracted-strip {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.strip-title {
  flex: 0 0 auto;
  padding-top: 3px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.chip-list {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.profile-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 260px;
  padding: 5px 9px;
  border: 1px solid rgba(199, 210, 254, 0.88);
  border-radius: 999px;
  background: rgba(238, 242, 255, 0.72);
  color: #475569;
  font-size: 12px;
  line-height: 1;
}

.profile-chip strong {
  min-width: 0;
  overflow: hidden;
  color: #3730a3;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-replies-wrapper {
  margin-bottom: 10px;
}

.quick-replies-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.quick-replies-scroll::-webkit-scrollbar {
  display: none;
}

.quick-reply-btn {
  flex: 0 0 auto;
  height: 32px;
  padding: 0 13px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.quick-reply-btn:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.45);
  background: #eef2ff;
  color: #4f46e5;
  transform: translateY(-1px);
}

.quick-reply-btn.is-selected {
  border-color: #4f46e5;
  background: #4f46e5;
  color: #ffffff;
}

.quick-reply-btn:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.school-suggestions-wrapper {
  margin-bottom: 10px;
}

.school-suggestions-list {
  max-height: 184px;
  overflow-y: auto;
  padding: 6px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
}

.school-suggestion-btn {
  width: 100%;
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #334155;
  cursor: pointer;
  text-align: left;
  transition: background 0.16s ease;
}

.school-suggestion-btn:hover {
  background: #f1f5f9;
}

.school-name {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 750;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.school-level-tag {
  flex: 0 0 auto;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 12px;
  font-weight: 800;
}

.composer-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 8px;
  border: 1px solid rgba(203, 213, 225, 0.95);
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
  transition: all 0.18s ease;
}

.composer-wrapper:focus-within {
  border-color: rgba(99, 102, 241, 0.72);
  box-shadow:
    0 16px 40px rgba(79, 70, 229, 0.12),
    0 0 0 4px rgba(99, 102, 241, 0.1);
}

.chat-composer {
  flex: 1;
  width: 100%;
  height: 44px;
  max-height: 88px;
  resize: none;
  overflow-y: auto;
  padding: 10px 10px 8px 12px;
  border: none;
  outline: none;
  background: transparent;
  color: #0f172a;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.55;
}

.chat-composer::placeholder {
  color: #94a3b8;
}

.chat-composer:disabled {
  cursor: not-allowed;
  color: #94a3b8;
}

.chat-composer::-webkit-scrollbar {
  width: 4px;
}

.chat-composer::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.38);
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
  filter: grayscale(0.4);
}

.profile-footer {
  display: flex;
  align-items: center;
  justify-content: center;
}

.finish-btn {
  width: 100%;
  height: 50px;
  border: none;
  border-radius: 18px;
  font-size: 15px;
  font-weight: 800;
  background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%);
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.22);
}

.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.22s ease;
}

.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 1024px) {
  .onboarding-dialog :deep(.el-dialog) {
    width: calc(100vw - 28px) !important;
  }

  .dialog-shell {
    height: 90vh;
    min-height: 620px;
  }

  .message-list {
    padding: 58px 28px 24px;
  }

  .input-dock {
    padding: 12px 20px 22px;
  }
}

@media (max-width: 640px) {
  .dialog-shell {
    height: 92vh;
    min-height: 600px;
    border-radius: 22px;
  }

  .skip-only-btn {
    top: 14px;
    right: 14px;
  }

  .message-list {
    padding: 54px 18px 20px;
    gap: 18px;
  }

  .avatar-icon {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
    border-radius: 12px;
    font-size: 12px;
  }

  .message-row.assistant .message-main {
    max-width: min(52ch, calc(100% - 48px));
  }

  .message-row.user .message-main {
    max-width: 82%;
  }

  .message-bubble {
    font-size: 14px;
  }

  .input-dock {
    padding: 10px 12px 16px;
  }

  .extracted-strip {
    flex-direction: column;
    gap: 8px;
  }

  .composer-wrapper {
    border-radius: 18px;
  }

  .send-btn {
    width: 40px;
    height: 40px;
    flex-basis: 40px;
  }
}
</style>
