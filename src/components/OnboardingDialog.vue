<template>
  <el-dialog
      v-model="visible"
      width="640px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="ai-native-dialog-light"
      align-center
  >
    <div class="chat-wrapper">
      <header class="chat-header">
        <div class="header-content">
          <div class="header-left">
            <div class="bot-avatar-container">
              <div class="bot-avatar-header">
                <el-icon><Service /></el-icon>
              </div>
            </div>
            <div class="header-info">
              <h3 class="header-title">学枢 AI 学习规划师</h3>
              <div class="status-wrap">
                <span class="status-dot"></span>
                <span class="header-status">在线并准备就绪</span>
              </div>
            </div>
          </div>
          <div class="header-right">
            <el-dropdown trigger="click" @command="handleHeaderCommand">
              <el-button link class="more-btn">
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="premium-dropdown">
                  <el-dropdown-item command="skip">
                    <el-icon><Clock /></el-icon> 稍后完善
                  </el-dropdown-item>
                  <el-dropdown-item command="never" divided>
                    <el-icon><Close /></el-icon> 不再弹出
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'

import { User, Service, Position, Search, MoreFilled, Clock, Close, Check, Plus } from '@element-plus/icons-vue'

import { useRoute, useRouter } from 'vue-router'

import { getProfileOnboarding, updateProfileOnboarding, searchSchools } from '@/api/ai'

import type { ProfileOnboardingUpdate, SchoolItem } from '@/api/ai'

interface Message {
  id: number;
  role: 'bot' | 'user';
  content: string;
}

const props = defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const route = useRoute()

const router = useRouter()

const messages = ref<Message[]>([])

const isTyping = ref(false)

const isStreaming = ref(false)

const currentQuestion = ref('major')

const messagesRef = ref<HTMLElement | null>(null)

const submitting = ref(false)

const onboardingForm = reactive<ProfileOnboardingUpdate>({
  education_level: '', grade: '', major: '', courses: [],
  learning_goal: '', school: '', school_level: '', preferred_language: ''
})

const customInputs = reactive({ course: '', major: '' })

const customAddedCourses = ref<string[]>([])

const profileSchoolOptions = ref<SchoolItem[]>([])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const PRESET_MAJORS = ['计算机科学', '软件工程', '人工智能', '数据科学', '网络安全', '电子信息', '其他']

const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库原理', '算法', '机器学习']

const PRESET_GOALS = [
  '期末考试冲刺', '完成课设项目', '大厂求职面试', '考研初试复习', '考研复试准备',
  '系统学习进阶', '零基础快速入门', '竞赛夺奖', '兴趣拓展', '行业证书考取'
]

const PRESET_EDUCATION_LEVELS = ['高职/专科', '本科', '研究生']

const PRESET_SCHOOL_LEVELS = ['985', '211', '双一流', '普通本科', '高职高专', '海外高校', '其他']

const PRESET_GRADES = [
  '大一', '大二', '大三', '大四', '大五',
  '研一', '研二', '研三',
  '博一', '博二', '博三',
  '高职一年级', '二年级', '三年级'
]

const PRESET_LANGUAGES = [
  'Python', 'Java', 'C/C++', 'Go', 'Rust', 'JavaScript', 'TypeScript', 'SQL', 'Swift'
]

watch(() => onboardingForm.school, (newVal) => {
  if (!newVal) { onboardingForm.school_level = ''; return; }
  const matched = profileSchoolOptions.value.find((s: any) => s.name === newVal);
  if (matched) onboardingForm.school_level = matched.level || '';
})

watch(visible, (newVal) => {
  if (newVal) {
    onboardingForm.courses = [];
    customInputs.major = '';
    customInputs.course = '';
    loadStatus().then(() => {
      startChat();
    });
  }
})

onMounted(() => { if (visible.value) { loadStatus().then(() => startChat()) } })

declare function withDefaults<T, D>(props: T, defaults: D): T;

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTo({
      top: messagesRef.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

const streamMessageContent = (msgObj: Message, fullText: string, speed = 25): Promise<void> => {
  return new Promise((resolve) => {
    isStreaming.value = true
    let index = 0
    const timer = setInterval(() => {
      if (index >= fullText.length) {
        clearInterval(timer)
        isStreaming.value = false
        resolve()
        return
      }

      let char = fullText[index]
      if (char === '<') {
        let tag = ''
        while (index < fullText.length && fullText[index] !== '>') {
          tag += fullText[index]
          index++
        }
        tag += '>'
        msgObj.content += tag
        index++ // 核心修复：跳过 '>' 字符本身，防止进入下次循环当成文本输出
      } else {
        msgObj.content += char
        index++
      }

      scrollToBottom()
    }, speed)
  })
}

const addBotMessage = async (content: string, delay = 600) => {
  isTyping.value = true
  scrollToBottom()
  await new Promise(resolve => setTimeout(resolve, delay))
  isTyping.value = false

  const msgObj: Message = reactive({ id: Date.now(), role: 'bot', content: '' })
  messages.value.push(msgObj)
  scrollToBottom()

  await streamMessageContent(msgObj, content)
}

const addUserMessage = (content: string) => {
  messages.value.push({ id: Date.now(), role: 'user', content })
  scrollToBottom()
}

const startChat = async () => {
  messages.value = []
  currentQuestion.value = ''
  await addBotMessage('👋 欢迎来到学枢！我是你的专属 AI 学习规划师。', 500)
  await addBotMessage('为了给你生成最精准的个性化学习资源，我们需要构建一下你的专属画像。首先，能告诉我你目前<b>主修什么专业</b>吗？', 800)
  currentQuestion.value = 'major'
}

const submitMajor = async (majorVal: string) => {
  const val = majorVal.trim()
  if (!val) { ElMessage.warning('请输入专业名称'); return }
  onboardingForm.major = val
  addUserMessage(val)
  currentQuestion.value = ''

  await addBotMessage(`太棒了！针对 <b>${val}</b> 专业，你目前主要在学<b>哪些核心课程</b>呢？（可多选）`, 600)
  currentQuestion.value = 'courses'
}

const toggleCourse = (course: string) => {
  const idx = onboardingForm.courses.indexOf(course)
  if (idx > -1) {
    onboardingForm.courses.splice(idx, 1)
  } else {
    onboardingForm.courses.push(course)
  }
}

const addCustomCourse = () => {
  const course = customInputs.course.trim()
  if (course && !onboardingForm.courses.includes(course)) {
    onboardingForm.courses.push(course)
    if (!PRESET_COURSES.includes(course)) {
      customAddedCourses.value.push(course)
    }
  }
  customInputs.course = ''
}

const submitCourses = async () => {
  if (onboardingForm.courses.length === 0) {
    ElMessage.warning('请至少选择或添加一门课程'); return
  }
  addUserMessage(onboardingForm.courses.join('、'))
  currentQuestion.value = ''

  await addBotMessage('了解了！为了匹配合适的学习难度，请问你是<b>哪个院校</b>的同学呢？', 600)
  currentQuestion.value = 'school'
}

const submitSchool = async () => {
  if (!onboardingForm.school || !onboardingForm.school_level) {
    ElMessage.warning('请输入并选择您的院校与层次'); return
  }
  let text = onboardingForm.school
  if (onboardingForm.school_level) text += ` <span style="opacity:0.6;font-size:0.9em">(${onboardingForm.school_level})</span>`
  addUserMessage(text)
  currentQuestion.value = ''

  await addBotMessage('收到！你的<b>学历层次</b>和<b>当前年级</b>是？', 600)
  currentQuestion.value = 'grade'
}

const submitGrade = async () => {
  if (!onboardingForm.education_level) { ElMessage.warning('请选择学历层次'); return }
  if (!onboardingForm.grade) { ElMessage.warning('请选择年级'); return }

  addUserMessage(`${onboardingForm.education_level} - ${onboardingForm.grade}`)
  currentQuestion.value = ''

  await addBotMessage('最后两个小问题！你当前的<b>主要学习目标</b>是什么？有比较常用的编程语言吗？', 600)
  currentQuestion.value = 'goal'
}

const submitGoal = async () => {
  if (!onboardingForm.learning_goal) { ElMessage.warning('请选择当前学习目标'); return }

  let text = onboardingForm.learning_goal
  if (onboardingForm.preferred_language) text += ` <span style="opacity:0.6;font-size:0.9em">(语言: ${onboardingForm.preferred_language})</span>`
  addUserMessage(text)
  currentQuestion.value = ''

  await addBotMessage('🎉 感谢配合！正在为你进行 AI 运算并生成专属学习画像...', 600)
  submitForm()
}

const querySearchSchool = async (queryString: string, cb: any) => {
  if (!queryString) { cb([]); return; }
  try {
    const res = await searchSchools(queryString, 20);
    profileSchoolOptions.value = res.data.data;
    const options = res.data.data.map((school: any) => ({
      value: school.name,
      level: school.level
    }));
    cb(options);
  } catch (e) { cb([]); }
}

const handleSchoolSelect = (item: any) => {
  onboardingForm.school_level = item.level || '';
}

const loadStatus = async () => {
  try {
    const res = await getProfileOnboarding();
    const profile = res.data?.data?.student_profile ?? {};
    if (profile.major) { onboardingForm.major = profile.major; }
    if (profile.courses) onboardingForm.courses = profile.courses;
    if (profile.education_level) onboardingForm.education_level = profile.education_level;
    if (profile.grade) onboardingForm.grade = profile.grade;
    if (profile.learning_goal) onboardingForm.learning_goal = profile.learning_goal;
    if (profile.preferred_language) onboardingForm.preferred_language = profile.preferred_language;
    if (profile.school) {
      onboardingForm.school = profile.school;
      onboardingForm.school_level = profile.school_level || '';
    }
  } catch (e) {
    console.error('Failed to load status', e);
  }
}

const submitForm = async () => {
  submitting.value = true;
  try {
    const payload = {
      ...onboardingForm,
      school: onboardingForm.school || null,
      school_level: onboardingForm.school_level || null,
      preferred_language: onboardingForm.preferred_language || null,
    };
    await updateProfileOnboarding(payload as any);
    ElMessage.success({
      message: '画像构建完成！',
      customClass: 'premium-toast'
    });
    setTimeout(() => {
      visible.value = false;
      emit('success');
      if (route.query.onboarding) {
        router.replace({ path: route.path, query: {} })
      }
    }, 1000);
  } catch (e) {
    ElMessage.error('保存失败，请重试');
    submitting.value = false;
  }
}

const handleHeaderCommand = (cmd: string) => {
  if (cmd === 'skip' || cmd === 'never') {
    visible.value = false;
    emit('success');
  }
  if (route.query.onboarding) {
    router.replace({ path: route.path, query: {} })
  }
}
</script>

<style scoped>
/* Dialog Base Overrides */
.ai-native-dialog-light :deep(.el-dialog__header) { display: none; }
.ai-native-dialog-light :deep(.el-dialog__body) { padding: 0; }
.ai-native-dialog-light :deep(.el-dialog) {
  border-radius: var(--radius-2xl);
  overflow: hidden;
  background: var(--color-surface);
  box-shadow: var(--shadow-xl), 0 0 0 1px rgba(0,0,0,0.02) inset;
  margin-top: 8vh !important;
  font-family: var(--font-sans);
}

.chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 680px;
  background: var(--color-surface);
  position: relative;
  overflow: hidden;
  color: #1d1d1f;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  position: relative;
  z-index: 10;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid #e5e5ea;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.bot-avatar-container {
  position: relative;
  width: 38px;
  height: 38px;
}

.bot-avatar-header {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  border-radius: var(--radius-pill);
  background: #000000;
  color: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  z-index: 2;
  box-shadow: var(--shadow-sm);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.header-title {
  margin: 0;
  font-size: 16px;
  font-weight: var(--weight-semibold);
  color: #1d1d1f;
  letter-spacing: -0.3px;
}

.status-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.status-dot {
  width: 6px;
  height: 6px;
  background-color: #34c759;
  border-radius: var(--radius-pill);
}

.header-status {
  font-size: var(--text-xs);
  color: #86868b;
  font-weight: var(--weight-medium);
}

.more-btn {
  font-size: 18px;
  color: #86868b;
  transition: color var(--transition-slow);
}
.more-btn:hover { color: #1d1d1f; }

/* Messages Area */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 30px var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  background: var(--color-surface);
}

.msg-list-enter-active,
.msg-list-leave-active {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.msg-list-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
.msg-list-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.message-row {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
  width: 100%;
}

.message-row.bot { justify-content: flex-start; }
.message-row.user { justify-content: flex-end; }

.avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-pill);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.bot .avatar {
  background: #f5f5f7;
  color: #1d1d1f;
  border: 1px solid #e5e5ea;
}

.user .avatar {
  background: #000000;
  color: var(--color-surface);
}

.bubble {
  max-width: 75%;
  padding: var(--space-3) var(--space-4);
  font-size: 15px;
  line-height: 1.5;
  word-break: break-word;
  position: relative;
}

.bot .bubble {
  background: #f5f5f7;
  color: #1d1d1f;
  border-radius: 18px 18px 18px 4px;
  border: 1px solid rgba(0,0,0,0.02);
}

.bot .bubble :deep(b) {
  color: #1d1d1f;
  font-weight: var(--weight-semibold);
}

.user .bubble {
  background: #000000;
  color: var(--color-surface);
  border-radius: 18px 18px 4px 18px;
  font-weight: var(--weight-medium);
}
.user .bubble :deep(span) {
  color: rgba(255, 255, 255, 0.7) !important;
}

/* Typing Indicator */
.typing-bubble {
  padding: 14px var(--space-4) !important;
}
.typing-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.typing-indicator span {
  display: block;
  width: 5px;
  height: 5px;
  border-radius: var(--radius-pill);
  background-color: #86868b;
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-4px); background-color: #1d1d1f; }
}

/* Footer / Action Area */
.chat-footer {
  background: var(--color-surface);
  border-top: 1px solid #e5e5ea;
  padding: var(--space-5) var(--space-6) 28px;
  min-height: 150px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.action-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.panel-tip {
  font-size: 13px;
  color: #86868b;
  font-weight: var(--weight-medium);
}

.selected-count {
  font-size: var(--text-xs);
  color: #1d1d1f;
  background: #f5f5f7;
  padding: 2px var(--space-2);
  border-radius: var(--radius-lg);
  font-weight: var(--weight-medium);
}

.chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.ai-chip {
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-2xl);
  font-size: 14px;
  font-weight: var(--weight-normal);
  background: var(--color-surface);
  color: #1d1d1f;
  cursor: pointer;
  border: 1px solid #e5e5ea;
  transition: all var(--transition-base);
  user-select: none;
}

.ai-chip:hover {
  background: #f5f5f7;
  border-color: #d1d1d6;
}

/* 这里是修复缺失样式的关键：直接硬编码黑底白字 */
.ai-chip.active {
  background: #000000 !important;
  color: var(--color-surface) !important;
  border-color: #000000 !important;
  font-weight: var(--weight-medium);
}

.stagger-animation .ai-chip {
  animation: slideUpFade 0.4s ease forwards;
  opacity: 0;
  transform: translateY(10px);
}

.pop-in {
  animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
}

/* Inputs */
.ai-input-wrap { width: 100%; }

.pill-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-2xl) !important;
  padding: var(--space-1) var(--space-1) var(--space-1) var(--space-4) !important;
  background: #f5f5f7 !important;
  box-shadow: none !important;
  border: 1px solid transparent !important;
  transition: all var(--transition-base);
}

.pill-input :deep(.el-input__wrapper.is-focus) {
  background: var(--color-surface) !important;
  border-color: #000000 !important;
  box-shadow: 0 0 0 1px #000000 !important;
}

/* Buttons */
.inside-action-btn {
  background: #000000 !important;
  color: var(--color-surface) !important;
  border: none !important;
  width: 30px !important;
  height: 30px !important;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 !important;
  transition: all var(--transition-base) !important;
}

.inside-action-btn:hover {
  transform: scale(1.05);
  background: #333333 !important;
}

.ghost-circle {
  background: #f5f5f7 !important;
  color: #1d1d1f !important;
}
.ghost-circle:hover {
  background: #e5e5ea !important;
}

/* 彻底修复主按钮不可见的样式 */
.primary-send-btn {
  background: #000000 !important;
  color: var(--color-surface) !important;
  border: none !important;
  border-radius: var(--radius-lg) !important;
  font-weight: var(--weight-medium) !important;
  padding: var(--space-3) 28px !important;
  height: 44px !important;
  transition: all var(--transition-base) !important;
}
.primary-send-btn:hover {
  background: #333333 !important;
}

/* Forms */
.form-panel { max-width: 100%; }

.glass-select :deep(.el-input__wrapper),
.glass-select :deep(.el-select__wrapper) {
  border-radius: var(--radius-lg);
  padding: var(--space-2) var(--space-4);
  background: #f5f5f7 !important;
  box-shadow: none !important;
  border: 1px solid transparent !important;
}

.glass-select :deep(.el-input__wrapper.is-focus),
.glass-select :deep(.el-select__wrapper.is-focused) {
  background: var(--color-surface) !important;
  box-shadow: 0 0 0 1px #000000 !important;
}

.school-tag {
  margin-left: var(--space-2); font-size: var(--text-xs); color: #1d1d1f; background: #e5e5ea;
  padding: 2px var(--space-2); border-radius: var(--radius-sm); font-weight: var(--weight-medium);
}
.autocomplete-item { display: flex; align-items: center; justify-content: space-between; }

/* Transitions & Animations */
.panel-slide-enter-active, .panel-slide-leave-active { transition: all var(--transition-slow) cubic-bezier(0.4, 0, 0.2, 1); }
.panel-slide-enter-from { opacity: 0; transform: translateY(15px) scale(0.98); }
.panel-slide-leave-to { opacity: 0; transform: translateY(-15px) scale(0.98); }

.slide-up-anim {
  animation: slideUpFade 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0; transform: translateY(15px);
}

@keyframes slideUpFade {
  0% { opacity: 0; transform: translateY(15px); }
  100% { opacity: 1; transform: translateY(0); }
}

@keyframes popIn {
  0% { transform: scale(0.9); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

/* Empty status pulse */
.empty-panel { align-items: center; justify-content: center; height: 60px; }
.status-pulse { display: flex; align-items: center; gap: var(--space-2); color: #86868b; font-size: 13px; font-weight: var(--weight-medium); }
.pulse-ring {
  width: 12px; height: 12px; border-radius: var(--radius-pill);
  background: #86868b;
  animation: pulseShadow 2s infinite;
}
@keyframes pulseShadow {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

/* Utilities */
.w-full { width: 100%; }
.mt-3 { margin-top: var(--space-3); }
.mt-4 { margin-top: var(--space-4); }
.ml-1 { margin-left: var(--space-1); }
.flex-1 { flex: 1; }

@media (max-width: 640px) {
  .chat-wrapper { height: 100vh; border-radius: 0; }
  .ai-native-dialog-light :deep(.el-dialog) { margin-top: 0 !important; border-radius: 0; }
  .bubble { max-width: 85%; }
}
</style>
