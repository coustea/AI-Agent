<template>
  <component :is="standalone ? 'div' : 'Fragment'" :class="standalone ? 'onboarding-standalone' : undefined">
    <el-dialog
      v-model="visible"
      width="760px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="onboarding-dialog"
      align-center
    >
      <div class="dialog-shell">
        <header class="dialog-header">
          <div>
            <p class="eyebrow">首次登录</p>
            <h2>智能对话冷启动画像</h2>
            <p class="subcopy">只需用自然语言简要描述你的学习背景，AI 即可自动为你抽取画像维度。</p>
          </div>
          <el-button text class="skip-btn" @click="handleSkip">稍后完善</el-button>
        </header>

        <!-- 对话式聊天区域 -->
        <div class="chat-container">
          <div class="message-list" ref="messageListRef">
            <div
              v-for="msg in messages"
              :key="msg.id"
              :class="['message-bubble-wrapper', msg.role]"
            >
              <div class="avatar-icon">
                <el-icon v-if="msg.role === 'assistant'"><Avatar /></el-icon>
                <el-icon v-else><User /></el-icon>
              </div>
              <div class="message-bubble">
                <div class="bubble-content" v-html="formatMessageContent(msg.content)"></div>
              </div>
            </div>

            <!-- AI 抽取状态提示 -->
            <div v-if="parsing" class="message-bubble-wrapper assistant">
              <div class="avatar-icon">
                <el-icon class="is-loading"><Loading /></el-icon>
              </div>
              <div class="message-bubble loading-bubble">
                <div class="bubble-content">
                  <span class="loading-text">正在抽取画像特征</span>
                  <span class="dot-flashing"></span>
                </div>
              </div>
            </div>

            <!-- 画像抽取校验卡片 -->
            <div v-if="showReviewCard && form" class="review-card-wrapper animate-slide-in">
              <div class="review-card">
                <div class="card-title">
                  <el-icon><Checked /></el-icon>
                  <span>画像抽取结果核对</span>
                </div>
                <div class="card-subtitle">AI 已经为您提取了以下学习特征，请核对无误后点击生成：</div>

                <div class="grid two">
                  <div class="form-group">
                    <label>学校</label>
                    <el-autocomplete
                      v-model="form.school"
                      :fetch-suggestions="querySearchSchool"
                      placeholder="搜索学校"
                      clearable
                      @select="handleSchoolSelect"
                    />
                  </div>

                  <div class="form-group">
                    <label>专业</label>
                    <el-select v-model="form.major" filterable allow-create default-first-option placeholder="请选择或输入专业">
                      <el-option v-for="item in PRESET_MAJORS" :key="item" :label="item" :value="item" />
                    </el-select>
                  </div>

                  <div class="form-group">
                    <label>年级</label>
                    <el-select v-model="form.grade" placeholder="请选择年级">
                      <el-option v-for="item in PRESET_GRADES" :key="item" :label="item" :value="item" />
                    </el-select>
                  </div>

                  <div class="form-group">
                    <label>每日学习时长</label>
                    <el-select v-model="form.daily_study_time" placeholder="请选择时长">
                      <el-option v-for="item in PRESET_DAILY_STUDY_TIME" :key="item" :label="item" :value="item" />
                    </el-select>
                  </div>

                  <div class="form-group span-2">
                    <label>全局学习目标</label>
                    <el-select v-model="form.global_learning_goal" filterable allow-create default-first-option placeholder="请选择学习目标">
                      <el-option v-for="item in PRESET_GOALS" :key="item" :label="item" :value="item" />
                    </el-select>
                  </div>
                </div>

                <div class="courses-section">
                  <div class="section-title">
                    <span>所选课程基础水平 (最多3门)</span>
                    <el-button v-if="form.courses.length < 3" link type="primary" @click="addCourseRow">
                      <el-icon><Plus /></el-icon>添加课程
                    </el-button>
                  </div>
                  <div class="course-list">
                    <div v-for="(c, idx) in form.courses" :key="idx" class="course-row-card">
                      <div class="course-row-grid">
                        <el-autocomplete
                          v-model="c.course"
                          :fetch-suggestions="querySearchCourse"
                          placeholder="课程名称"
                          class="course-input"
                        />
                        <el-select v-model="c.foundation_level" placeholder="基础水平" class="level-select">
                          <el-option v-for="level in PRESET_FOUNDATION_LEVELS" :key="level" :label="level" :value="level" />
                        </el-select>
                        <el-button link type="danger" @click="removeCourseRow(idx)">
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="card-actions">
                  <el-button @click="resetToChat">重新对话</el-button>
                  <el-button type="primary" :loading="submitting" @click="submitForm">确认并生成画像</el-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 输入区 -->
          <div v-if="!showReviewCard" class="input-panel">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="3"
              placeholder="请输入您的自我介绍，如：我是北京大学大二学生，专业是软件工程，全局学习目标是考研学习，每日学习时长1-2h。本学期正在学数据结构（熟练）和计算机网络（一般）。"
              :disabled="parsing"
              @keydown.enter.prevent="handleSend"
            />
            <div class="input-actions">
              <span class="char-count">{{ inputText.length }} 字</span>
              <el-button
                type="primary"
                :disabled="!inputText.trim() || parsing"
                @click="handleSend"
              >
                发送并智能提取
                <el-icon class="el-icon--right"><Promotion /></el-icon>
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
  Avatar,
  User,
  Loading,
  Checked,
  Plus,
  Delete,
  Promotion
} from '@element-plus/icons-vue'

import { updateMe } from '@/auth/api/auth'
import { getProfileOnboarding, updateProfileOnboarding, parseOnboardingDialogue } from '@/profile/api/profile'
import type { ProfileOnboardingUpdate } from '@/profile/api/profile'
import { searchSchools } from '@/resource/api/school'

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
const inputText = ref('')
const parsing = ref(false)
const showReviewCard = ref(false)
const submitting = ref(false)
const messageListRef = ref<HTMLDivElement | null>(null)

const form = reactive<ProfileOnboardingUpdate>({
  school: '',
  school_level: '',
  major: '',
  grade: '',
  daily_study_time: '',
  global_learning_goal: '',
  resource_preference: [],
  programming_languages: [],
  self_description: '',
  courses: [],
})

const PRESET_MAJORS = ['软件工程', '计算机科学与技术', '人工智能', '数据科学与大数据技术', '网络空间安全', '电子信息工程']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库系统', '编译原理', '机器学习']
const PRESET_GOALS = ['期末复习', '考研学习', '进阶学习', '补基础', '项目实战']
const PRESET_GRADES = ['大一', '大二', '大三', '大四', '研一', '研二', '研三']
const PRESET_DAILY_STUDY_TIME = ['30min以下', '30-60min', '1-2h', '2-3h', '3h以上']
const PRESET_FOUNDATION_LEVELS = ['薄弱', '一般', '较好', '熟练']

const initMessages = () => {
  messages.value = [
    {
      id: 1,
      role: 'assistant',
      content: '你好！我是你的 AI 学习画像助手。为了能为你量身定制最适合的学习路径与多模态学习资源，我们需要为你进行冷启动画像初始化。<br/><br/>请自然地告诉我：<b>你的学校、专业、年级是？你的全局学习目标是什么？每天大约能花多少时间学习？以及这学期你正在学哪些课程，你觉得目前各课程的基础水平如何？</b><br/><br/><i>（例如：我是华中科技大学软件工程大三学生，每天学习 1-2 小时，目标是期末复习。目前主要在学“数据结构”和“计算机网络”，数据结构基础还可以，但计算机网络比较薄弱。）</i>'
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
  initMessages()
  inputText.value = ''
  parsing.value = false
  showReviewCard.value = false
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

const handleSend = async () => {
  const text = inputText.value.trim()
  if (!text || parsing.value) return

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: text
  })
  inputText.value = ''
  parsing.value = true
  await scrollToBottom()

  try {
    const res = await parseOnboardingDialogue({ text })
    const data = res.data?.data
    if (data) {
      form.school = data.school || ''
      form.school_level = data.school_level || ''
      form.major = data.major || ''
      form.grade = data.grade || ''
      form.daily_study_time = data.daily_study_time || ''
      form.global_learning_goal = data.global_learning_goal || ''
      form.resource_preference = data.resource_preference || []
      form.programming_languages = data.programming_languages || []
      form.self_description = text
      form.courses = Array.isArray(data.courses) ? data.courses.map((item) => ({
        course: item.course || '',
        foundation_level: item.foundation_level || '一般',
        current_topic: item.current_topic || null,
        course_learning_goal: item.course_learning_goal || null,
        weak_points: item.weak_points || []
      })) : []

      // 保障至少有一行课程数据
      if (form.courses.length === 0) {
        form.courses.push({
          course: '',
          foundation_level: '一般',
          current_topic: null,
          course_learning_goal: null,
          weak_points: []
        })
      }

      messages.value.push({
        id: Date.now() + 1,
        role: 'assistant',
        content: '我已经提取了您的画像信息，请在下方的面板中核对并完善。确认无误后点击“确认并生成画像”即可。'
      })
      showReviewCard.value = true
    } else {
      throw new Error('No data returned')
    }
  } catch (error) {
    console.error('Failed to parse onboarding dialog', error)
    messages.value.push({
      id: Date.now() + 2,
      role: 'assistant',
      content: '抽取画像特征失败了，您可以尝试换个说法描述您的信息，或者点击“稍后完善”跳过。'
    })
  } finally {
    parsing.value = false
    await scrollToBottom()
  }
}

const addCourseRow = () => {
  if (form.courses.length >= 3) return
  form.courses.push({
    course: '',
    foundation_level: '一般',
    current_topic: null,
    course_learning_goal: null,
    weak_points: []
  })
}

const removeCourseRow = (idx: number) => {
  form.courses.splice(idx, 1)
  if (form.courses.length === 0) {
    addCourseRow()
  }
}

const resetToChat = () => {
  showReviewCard.value = false
  initMessages()
}

const querySearchSchool = async (
  queryString: string,
  cb: (items: Array<{ value: string; level?: string | null }>) => void
) => {
  if (!queryString) {
    cb([])
    return
  }
  try {
    const res = await searchSchools(queryString, 20)
    cb(res.data.data.map((item) => ({ value: item.name, level: item.level })))
  } catch {
    cb([])
  }
}

const handleSchoolSelect = (item: { value: string; level?: string | null }) => {
  form.school = item.value
  form.school_level = item.level || ''
}

const querySearchCourse = (queryString: string, cb: (items: Array<{ value: string }>) => void) => {
  const filtered = PRESET_COURSES.filter(c => c.toLowerCase().includes(queryString.toLowerCase()))
  cb(filtered.map(c => ({ value: c })))
}

const loadStatus = async () => {
  try {
    const res = await getProfileOnboarding()
    const baseInfo = res.data?.data?.base_info
    if (!baseInfo) return
    form.school = baseInfo.school || ''
    form.school_level = baseInfo.school_level || ''
    form.major = baseInfo.major || ''
    form.grade = baseInfo.grade || ''
    form.daily_study_time = baseInfo.daily_study_time || ''
    form.global_learning_goal = baseInfo.global_learning_goal || ''
    form.resource_preference = baseInfo.resource_preference || []
    form.programming_languages = baseInfo.programming_languages || []
    form.self_description = baseInfo.self_description || ''
    form.courses = Array.isArray(baseInfo.courses) ? baseInfo.courses.map((item) => ({
      course: item.course || '',
      foundation_level: item.foundation_level || '一般',
      current_topic: item.current_topic || null,
      course_learning_goal: item.course_learning_goal || null,
      weak_points: item.weak_points || []
    })) : []
  } catch (error) {
    console.error('Failed to load onboarding data', error)
  }
}

const validateForm = () => {
  if (!(form.school ?? '').trim()) {
    ElMessage.warning('请输入学校名称')
    return false
  }
  if (!form.major.trim()) {
    ElMessage.warning('请输入或选择专业')
    return false
  }
  if (!form.grade) {
    ElMessage.warning('请选择年级')
    return false
  }
  if (!form.daily_study_time) {
    ElMessage.warning('请选择每日学习时间')
    return false
  }
  if (!form.global_learning_goal) {
    ElMessage.warning('请选择全局学习目标')
    return false
  }
  const validCourses = form.courses.filter((c) => c.course.trim())
  if (validCourses.length === 0) {
    ElMessage.warning('请至少添加一门正在学习的课程')
    return false
  }
  if (validCourses.some((c) => !c.foundation_level)) {
    ElMessage.warning('请选择课程基础水平')
    return false
  }
  return true
}

const submitForm = async () => {
  if (!validateForm()) return
  submitting.value = true
  try {
    const validCourses = form.courses.filter((c) => c.course.trim())
    await updateProfileOnboarding({
      ...form,
      school: (form.school ?? '').trim(),
      major: form.major.trim(),
      school_level: form.school_level || null,
      self_description: form.self_description || null,
      courses: validCourses.map((item) => ({
        course: item.course.trim(),
        foundation_level: item.foundation_level,
        current_topic: item.current_topic || null,
        course_learning_goal: item.course_learning_goal || null,
        weak_points: item.weak_points || [],
      })),
    })
    ElMessage.success('冷启动画像已生成')
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

const handleSkip = async () => {
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
  background-color: var(--color-bg, #f8fafc);
  display: flex;
  align-items: center;
  justify-content: center;
}

.onboarding-dialog :deep(.el-dialog__header) {
  display: none;
}

.onboarding-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.dialog-shell {
  padding: 24px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  height: 720px;
  border-radius: 16px;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 16px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 700;
  color: #4f46e5;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.dialog-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.subcopy {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.skip-btn {
  font-weight: 500;
  color: #64748b;
}

/* 聊天容器样式 */
.chat-container {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  overflow: hidden;
  position: relative;
}

.message-list {
  flex-grow: 1;
  overflow-y: auto;
  padding: 8px 4px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 消息气泡样式 */
.message-bubble-wrapper {
  display: flex;
  gap: 12px;
  max-width: 85%;
  align-items: flex-start;
}

.message-bubble-wrapper.assistant {
  align-self: flex-start;
}

.message-bubble-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #eef2ff;
  color: #4f46e5;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(79, 70, 229, 0.05);
}

.message-bubble-wrapper.user .avatar-icon {
  background: #4f46e5;
  color: #ffffff;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.message-bubble-wrapper.assistant .message-bubble {
  background: #f1f5f9;
  color: #0f172a;
  border-top-left-radius: 2px;
}

.message-bubble-wrapper.user .message-bubble {
  background: #4f46e5;
  color: #ffffff;
  border-top-right-radius: 2px;
}

.bubble-content :deep(b) {
  font-weight: 600;
  color: #1e1b4b;
}

.message-bubble-wrapper.user .bubble-content :deep(b) {
  color: #ffffff;
}

/* 加载动画气泡 */
.loading-bubble {
  display: flex;
  align-items: center;
}

.loading-text {
  font-size: 13px;
  color: #64748b;
  margin-right: 8px;
}

.dot-flashing {
  position: relative;
  width: 6px;
  height: 6px;
  border-radius: 5px;
  background-color: #4f46e5;
  color: #4f46e5;
  animation: dot-flashing 1s infinite linear;
}

@keyframes dot-flashing {
  0% { background-color: #4f46e5; }
  50%, 100% { background-color: rgba(79, 70, 229, 0.2); }
}

/* 输入面板样式 */
.input-panel {
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
  margin-top: 8px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.input-panel :deep(.el-textarea__inner) {
  border-radius: 12px;
  border: 1px solid #cbd5e1;
  padding: 12px;
  font-size: 14px;
  resize: none;
  transition: all 0.2s ease;
}

.input-panel :deep(.el-textarea__inner:focus) {
  border-color: #4f46e5;
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-count {
  font-size: 12px;
  color: #94a3b8;
}

/* 画像校验卡片样式 (Glassmorphism Detail) */
.review-card-wrapper {
  margin: 10px 0;
  width: 100%;
}

.review-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #10b981;
  margin-bottom: 8px;
}

.card-title .el-icon {
  font-size: 18px;
}

.card-subtitle {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 18px;
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.form-group.span-2 {
  grid-column: span 2;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.form-group :deep(.el-select),
.form-group :deep(.el-autocomplete) {
  width: 100%;
}

.courses-section {
  margin-top: 16px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 16px;
}

.courses-section .section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 12px;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-row-card {
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #f1f5f9;
}

.course-row-grid {
  display: grid;
  grid-template-columns: 1fr 120px 32px;
  gap: 8px;
  align-items: center;
}

.course-input :deep(.el-input__inner),
.level-select :deep(.el-input__inner) {
  border-radius: 6px;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
  border-top: 1px solid #f1f5f9;
  padding-top: 16px;
}

/* 动效 */
.animate-slide-in {
  animation: slide-in 0.3s ease-out forwards;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(15px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 760px) {
  .dialog-shell {
    padding: 16px;
    height: 100%;
  }

  .dialog-header {
    flex-direction: column;
    gap: 8px;
  }

  .grid.two {
    grid-template-columns: 1fr;
  }

  .form-group.span-2 {
    grid-column: span 1;
  }

  .course-row-grid {
    grid-template-columns: 1fr 100px 32px;
  }
}
</style>
