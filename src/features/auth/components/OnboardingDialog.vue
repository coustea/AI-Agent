<template>
  <component :is="standalone ? 'div' : 'Fragment'" :class="standalone ? 'onboarding-standalone' : undefined">
    <el-dialog
      v-model="visible"
      width="700px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="onboarding-dialog"
      align-center
    >
      <div class="dialog-shell">
        <header class="dialog-header">
          <div class="header-titles">
            <p class="eyebrow">FIRST LOGIN</p>
            <h2>智能构建专属学习画像</h2>
          </div>
          <div class="header-actions">
            <el-button text class="skip-btn" @click="handleSkip">稍后</el-button>
            <el-button text class="skip-btn" @click="handleNeverShow">跳过</el-button>
          </div>
        </header>

        <div class="onboarding-layout">
          <!-- 纯净的沉浸式聊天区 -->
          <div class="chat-column">
            <div class="message-list" ref="messageListRef">
              <div
                v-for="msg in messages"
                :key="msg.id"
                :class="['message-bubble-wrapper', msg.role]"
              >
                <div class="avatar-icon" v-if="msg.role === 'assistant'">
                  <el-icon><Service /></el-icon>
                </div>
                <div class="message-bubble-container">
                  <div class="message-bubble">
                    <div class="bubble-content" v-html="formatMessageContent(msg.content)"></div>
                  </div>
                </div>
              </div>
              <div v-if="isTyping" class="message-bubble-wrapper assistant">
                 <div class="avatar-icon"><el-icon><Service /></el-icon></div>
                 <div class="message-bubble typing-bubble">
                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                 </div>
              </div>
            </div>

            <div class="chat-input-area" v-if="currentStep <= 7">
              <transition name="fade-up">
                <div class="quick-replies-wrapper" v-if="currentQuickReplies.length > 0">
                  <p class="quick-replies-hint">{{ isMultiSelectStep ? '建议标签 (可多选，选好后回车或点击发送)' : '建议标签 (点击直接发送)' }}</p>
                  <div class="quick-replies-scroll">
                    <button
                      v-for="reply in currentQuickReplies"
                      :key="reply"
                      class="quick-reply-btn"
                      :class="{ 'is-selected': isReplySelected(reply) }"
                      @click="handleQuickReply(reply)"
                    >
                      {{ reply }}
                    </button>
                  </div>
                </div>
              </transition>
              <div class="school-suggestions-wrapper" v-if="currentStep === 1 && schoolSuggestions.length > 0">
                <div class="school-suggestions-list">
                  <button
                    v-for="school in schoolSuggestions"
                    :key="school.name"
                    class="school-suggestion-btn"
                    @click="selectSchool(school)"
                  >
                    <span class="school-name">{{ school.name }}</span>
                    <span v-if="school.level" class="school-level-tag">{{ school.level }}</span>
                  </button>
                </div>
              </div>
              <div class="input-box-wrapper">
                <input
                  v-model="userInput"
                  class="stealth-input"
                  :placeholder="currentStep === 1 ? '输入学校名称搜索...' : '在这里自由输入回复...'"
                  @keyup.enter="handleSend"
                  @input="handleInputChange"
                />
                <button class="stealth-send-btn" @click="handleSend" :disabled="!userInput.trim()">
                  <el-icon><Position /></el-icon>
                </button>
              </div>
            </div>

            <div class="profile-footer" v-if="currentStep > 7 || isComplete">
              <el-button class="finish-btn glow-btn" type="primary" :loading="submitting" @click="submitForm">
                完成构建，进入学习空间 <el-icon class="el-icon--right"><Right /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </component>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Service,
  Position,
  Right
} from '@element-plus/icons-vue'

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

const messages = ref<Array<{ id: number; role: 'assistant' | 'user'; content: string }>>([])
const submitting = ref(false)
const messageListRef = ref<HTMLDivElement | null>(null)

const currentStep = ref(1)
const userInput = ref('')
const isTyping = ref(false)
const schoolSuggestions = ref<SchoolItem[]>([])
let schoolSearchTimer: ReturnType<typeof setTimeout> | null = null

const isComplete = computed(() => {
  return currentStep.value > 7 || (form.school && form.major && form.grade && form.daily_study_time && form.global_learning_goal)
})

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

const initMessages = () => {
  messages.value = [
    {
      id: Date.now(),
      role: 'assistant',
      content: '你好！我是你的专属学习智能体。<br/>为了能为你量身定制个性化的学习路径，我们需要进行一次短暂的交流，构建你的专属“数字学习档案”。<br/><br/>首先，能告诉我你目前所在的<b>学校</b>吗？'
    }
  ]
}

watch(visible, async (open) => {
  if (!open) return
  resetState()
  await loadStatus()
})

onMounted(async () => {
  if (visible.value) {
    resetState()
    await loadStatus()
  }
})

const resetState = () => {
  currentStep.value = 1
  userInput.value = ''
  isTyping.value = false
  form.school = ''
  form.major = ''
  form.grade = ''
  form.daily_study_time = ''
  form.global_learning_goal = ''
  form.programming_languages = []
  form.courses = []
  initMessages()
  submitting.value = false
}

const formatMessageContent = (text: string) => {
  return text.replace(/\n/g, '<br/>')
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

const handleInputChange = () => {
  if (currentStep.value !== 1) return
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

const selectSchool = (school: SchoolItem) => {
  userInput.value = school.name
  schoolSuggestions.value = []
  handleSend()
}

// ----------------- Chat Interactive Logic -----------------

const currentQuickReplies = computed(() => {
  switch(currentStep.value) {
    case 2: return PRESET_MAJORS
    case 3: return PRESET_GRADES
    case 4: return PRESET_DAILY_STUDY_TIME
    case 5: return PRESET_GOALS
    case 6: return ['暂不选择', ...PRESET_PROGRAMMING_LANGUAGES]
    case 7: return PRESET_COURSES
    default: return []
  }
})

const isMultiSelectStep = computed(() => [6, 7].includes(currentStep.value))

const isReplySelected = (reply: string) => {
  if (!userInput.value) return false
  const parts = userInput.value.split(/[,，、\s]+/).filter(Boolean)
  return parts.includes(reply)
}

const handleQuickReply = (q: string) => {
  if (q === '暂时没有' || q === '暂不选择') {
    userInput.value = q
    handleSend()
    return
  }

  if (isMultiSelectStep.value) {
    const parts = userInput.value.split(/[,，、\s]+/).filter(Boolean)
    if (parts.includes(q)) {
      userInput.value = parts.filter(p => p !== q).join('，')
    } else {
      parts.push(q)
      userInput.value = parts.join('，')
    }
  } else {
    userInput.value = q
    handleSend()
  }
}

const extractMultiple = (text: string, presets: string[]) => {
  const parts = text.split(/[,，、\s]+/).filter(Boolean)
  const result: string[] = []
  parts.forEach(part => {
    const matched = presets.find(p => p === part || part.includes(p) || p.includes(part))
    if (matched && !result.includes(matched)) {
      result.push(matched)
    } else if (!matched && !result.includes(part)) {
      result.push(part)
    }
  })
  return result
}

const advanceStep = (assistantMsg: string) => {
  isTyping.value = true
  scrollToBottom()
  setTimeout(() => {
    isTyping.value = false
    messages.value.push({ id: Date.now() + 1, role: 'assistant', content: assistantMsg })
    scrollToBottom()
  }, 600)
}

const handleSend = () => {
  const text = userInput.value.trim()
  if (!text) return

  messages.value.push({ id: Date.now(), role: 'user', content: text })
  userInput.value = ''
  schoolSuggestions.value = []
  scrollToBottom()

  if (currentStep.value === 1) {
    form.school = text
    currentStep.value = 2
    advanceStep(`好的，<b>${form.school}</b> 已记录。接下来，请问你的<b>专业</b>是？`)
  }
  else if (currentStep.value === 2) {
    const foundMajor = PRESET_MAJORS.find(m => text.includes(m))
    if (foundMajor) form.major = foundMajor; else form.major = text;
    currentStep.value = 3
    advanceStep(`太棒了！专业 <b>${form.major}</b> 已提取。接下来，请问你目前的<b>年级</b>是？`)
  }
  else if (currentStep.value === 3) {
    const found = PRESET_GRADES.find(g => text.includes(g))
    if (found) form.grade = found; else form.grade = text;
    currentStep.value = 4
    advanceStep(`好的，年级是 <b>${form.grade}</b>。为了评估你的学习节奏，你每天大约能抽出多少<b>学习时间</b>？`)
  }
  else if (currentStep.value === 4) {
    const found = PRESET_DAILY_STUDY_TIME.find(g => text.includes(g))
    if (found) form.daily_study_time = found; else form.daily_study_time = text;
    currentStep.value = 5
    advanceStep(`没问题，每天 <b>${form.daily_study_time}</b>。那你的<b>全局学习目标</b>是什么呢？（比如期末复习、考研等）`)
  }
  else if (currentStep.value === 5) {
    const found = PRESET_GOALS.find(g => text.includes(g))
    if (found) form.global_learning_goal = found; else form.global_learning_goal = text;
    currentStep.value = 6
    advanceStep(`收到！目标设定为 <b>${form.global_learning_goal}</b>。如果你的专业涉及编程，告诉我常用的<b>编程语言</b>，之后的代码示例会直接贴合你的技术栈。`)
  }
  else if (currentStep.value === 6) {
    if (text !== '暂不选择') {
      const found = extractMultiple(text, PRESET_PROGRAMMING_LANGUAGES)
      form.programming_languages = found.length > 0 ? found : [text]
    }
    currentStep.value = 7
    advanceStep(`好的，编程语言已提取。那么这学期你主要修读了哪些<b>核心课程</b>呢？你可以一次性选择多个，或打字告诉我。`)
  }
  else if (currentStep.value === 7) {
    const found = extractMultiple(text, PRESET_COURSES)
    if (found.length === 0 && text.length > 0) found.push(text)
    form.courses = found
    currentStep.value = 8
    advanceStep(`太好啦！全息数字档案已经构建完成！你可以点击下方的<b>完成构建</b>，直接开启个性化学习旅程。`)
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
    form.programming_languages = baseInfo.programming_languages || []
    form.courses = Array.isArray(baseInfo.courses) ? baseInfo.courses : []

    if (form.major && form.grade && form.daily_study_time && form.global_learning_goal) {
      currentStep.value = 8
      messages.value = [
        {
          id: 1,
          role: 'assistant',
          content: '欢迎回来！我已为你加载了过往收集的数字档案数据。点击下方的<b>进入学习空间</b>即可开始学习。'
        }
      ]
    }
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

    ElMessage.success('数字档案构建成功！')
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

const handleSkip = () => {
  visible.value = false
  emit('success')
  if (route.query.onboarding) {
    router.replace({ path: route.path, query: {} })
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
.onboarding-standalone {
  width: 100vw;
  height: 100vh;
  background-color: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.onboarding-dialog :deep(.el-dialog__header) {
  display: none;
}

.onboarding-dialog :deep(.el-dialog__body) {
  padding: 0;
  background: transparent;
}

.onboarding-dialog :deep(.el-dialog) {
  background: transparent;
  box-shadow: none;
}

.dialog-shell {
  padding: var(--space-8);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  height: 85vh;
  max-height: 800px;
  min-height: 600px;
  border-radius: var(--radius-2xl);
  overflow: hidden;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xl);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.eyebrow {
  margin: 0 0 var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-faint);
  letter-spacing: 0.1em;
}

.dialog-header h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
}

.header-actions {
  display: flex;
  gap: var(--space-2);
}

.skip-btn {
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  border-radius: var(--radius-lg);
}

/* 布局 */
.onboarding-layout {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* 沉浸式聊天区 */
.chat-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-list {
  flex-grow: 1;
  overflow-y: auto;
  padding: var(--space-3) 0 var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  scroll-behavior: smooth;
}

.message-list::-webkit-scrollbar { width: 4px; }
.message-list::-webkit-scrollbar-thumb { background: var(--color-border-hover); border-radius: 4px; }

.message-bubble-wrapper {
  display: flex;
  gap: var(--space-3);
  max-width: 90%;
  align-items: flex-start;
  animation: slide-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
  transform: translateY(10px);
}

@keyframes slide-up {
  to { opacity: 1; transform: translateY(0); }
}

.message-bubble-wrapper.assistant { align-self: flex-start; }
.message-bubble-wrapper.user { align-self: flex-end; flex-direction: row-reverse; }

.avatar-icon {
  width: 32px; height: 32px;
  border-radius: var(--radius-md);
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 4px;
}

.message-bubble {
  padding: var(--space-3) var(--space-4);
  line-height: var(--leading-relaxed);
  font-size: var(--text-base);
}

.message-bubble-wrapper.assistant .message-bubble {
  background: transparent;
  color: var(--color-text);
  padding: 4px 0; /* Ambient text feels native, not bounded */
}

.message-bubble-wrapper.user .message-bubble {
  background: var(--color-surface-hover);
  color: var(--color-text);
  border-radius: var(--radius-xl);
  border-bottom-right-radius: 4px;
}

.bubble-content :deep(b) {
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
}

.typing-bubble {
  display: flex; gap: 4px; padding: 12px 0 !important; align-items: center; height: 24px;
}
.dot {
  width: 6px; height: 6px; background: var(--color-text-faint); border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 100% { transform: translateY(0); opacity: 0.4; }
  50% { transform: translateY(-4px); opacity: 1; }
}

/* Chat Input */
.chat-input-area {
  padding: var(--space-4) 0 0;
  display: flex;
  flex-direction: column;
}

.quick-replies-wrapper { margin-bottom: var(--space-3); }
.quick-replies-hint { font-size: var(--text-xs); color: var(--color-text-muted); margin: 0 0 var(--space-2); font-weight: var(--weight-bold); }
.quick-replies-scroll { display: flex; flex-wrap: wrap; gap: var(--space-2); }

.quick-reply-btn {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-pill);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: all var(--transition-base);
}

.quick-reply-btn:hover {
  transform: translateY(-1px);
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
  color: var(--color-primary);
}

.quick-reply-btn.is-selected {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.input-box-wrapper {
  display: flex;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  padding: 6px 6px 6px var(--space-4);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}
.input-box-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.stealth-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: var(--text-base);
  color: var(--color-text-strong);
}
.stealth-input::placeholder { color: var(--color-text-placeholder); }

.stealth-send-btn {
  width: 36px; height: 36px;
  border-radius: 18px;
  border: none;
  background: var(--color-primary);
  color: white;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: all var(--transition-base);
}
.stealth-send-btn:disabled { background: var(--color-border-hover); cursor: not-allowed; opacity: 0.5; }
.stealth-send-btn:not(:disabled):hover { transform: scale(1.05); background: var(--color-primary-hover); }

/* School search suggestions */
.school-suggestions-wrapper { margin-bottom: var(--space-2); }
.school-suggestions-list {
  display: flex; flex-direction: column; gap: 4px;
  max-height: 200px; overflow-y: auto;
  background: var(--color-surface);
  border-radius: var(--radius-lg); border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  padding: var(--space-1);
}
.school-suggestion-btn {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: var(--space-2) var(--space-3); border: none; border-radius: var(--radius-sm);
  background: transparent; cursor: pointer; text-align: left;
  font-size: var(--text-sm); color: var(--color-text-strong);
  transition: background var(--transition-fast);
}
.school-suggestion-btn:hover { background: var(--color-surface-hover); }
.school-name { font-weight: var(--weight-medium); }
.school-level-tag {
  font-size: var(--text-xs); padding: 2px 8px; border-radius: 4px;
  background: var(--color-primary-soft); color: var(--color-primary); font-weight: var(--weight-bold);
}

.profile-footer {
  margin-top: var(--space-5);
  padding-top: var(--space-2);
}
.finish-btn {
  width: 100%; border-radius: var(--radius-lg); height: 52px; font-size: var(--text-md); font-weight: var(--weight-bold);
}

.fade-up-enter-active, .fade-up-leave-active { transition: all 0.3s ease; }
.fade-up-enter-from, .fade-up-leave-to { opacity: 0; transform: translateY(10px); }
</style>
