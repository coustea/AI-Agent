<template>
  <component :is="standalone ? 'div' : 'Fragment'" :class="standalone ? 'onboarding-standalone' : undefined">
    <el-dialog
      v-model="visible"
      width="1000px"
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
            <h2>对话式冷启动画像</h2>
            <p class="subcopy">在右侧像聊天一样打字或点击标签，左侧画像会自动实时更新。您也可以随时在左侧手动修改。</p>
          </div>
          <div class="header-actions">
            <el-button text class="skip-btn" @click="handleSkip">稍后完善</el-button>
            <el-button text type="info" class="skip-btn" @click="handleNeverShow">不再弹出</el-button>
          </div>
        </header>

        <div class="onboarding-layout">
          <!-- 左侧：画像实时核对面板 (现在移到了左侧) -->
          <div class="form-column">
            <div class="panel-header">
              <el-icon><Checked /></el-icon>
              <span>边聊边整理的画像草稿</span>
            </div>

            <div class="form-scroll-content">
              <div class="grid two compact-grid">
                <div class="form-group" :class="{ 'is-filled': !!form.school }">
                  <label>
                    <span>学校 <span class="required">*</span></span>
                    <span class="filled-badge" v-if="form.school"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-autocomplete
                    v-model="form.school"
                    :fetch-suggestions="querySearchSchool"
                    placeholder="搜索学校"
                    clearable
                    size="small"
                    @select="handleSchoolSelect"
                  />
                </div>

                <div class="form-group" :class="{ 'is-filled': !!form.major }">
                  <label>
                    <span>专业 <span class="required">*</span></span>
                    <span class="filled-badge" v-if="form.major"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.major" filterable allow-create default-first-option placeholder="输入专业" size="small">
                    <el-option v-for="item in PRESET_MAJORS" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>

                <div class="form-group" :class="{ 'is-filled': !!form.grade }">
                  <label>
                    <span>年级 <span class="required">*</span></span>
                    <span class="filled-badge" v-if="form.grade"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.grade" placeholder="选择年级" size="small">
                    <el-option v-for="item in PRESET_GRADES" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>

                <div class="form-group" :class="{ 'is-filled': !!form.daily_study_time }">
                  <label>
                    <span>每日学习时长 <span class="required">*</span></span>
                    <span class="filled-badge" v-if="form.daily_study_time"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.daily_study_time" placeholder="选择时长" size="small">
                    <el-option v-for="item in PRESET_DAILY_STUDY_TIME" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>

                <div class="form-group span-2" :class="{ 'is-filled': !!form.global_learning_goal }">
                  <label>
                    <span>全局学习目标 <span class="required">*</span></span>
                    <span class="filled-badge" v-if="form.global_learning_goal"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.global_learning_goal" filterable allow-create default-first-option placeholder="选择学习目标" size="small">
                    <el-option v-for="item in PRESET_GOALS" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
              </div>

              <div class="courses-section">
                <div class="section-title">
                  <span>正在学习的课程 <span class="required">*</span></span>
                  <el-button v-if="form.courses.length < 3" link type="primary" @click="addCourseRow" size="small">
                    <el-icon><Plus /></el-icon>添加
                  </el-button>
                </div>
                <div class="course-list">
                  <div v-for="(c, idx) in form.courses" :key="idx" class="course-row-card" :class="{ 'is-filled': !!c.course }">
                    <div class="course-row-grid">
                      <el-autocomplete
                        v-model="c.course"
                        :fetch-suggestions="querySearchCourse"
                        placeholder="课程名称"
                        class="course-input"
                        size="small"
                      />
                      <el-select v-model="c.foundation_level" placeholder="基础" class="level-select" size="small">
                        <el-option v-for="level in PRESET_FOUNDATION_LEVELS" :key="level" :label="level" :value="level" />
                      </el-select>
                      <el-button link type="danger" @click="removeCourseRow(idx)" size="small" class="del-btn">
                        <el-icon><Delete /></el-icon>
                      </el-button>
                      <el-select
                        v-model="c.weak_points"
                        multiple
                        filterable
                        allow-create
                        default-first-option
                        placeholder="薄弱点 (多选)"
                        class="weak-point-select"
                        size="small"
                      >
                        <el-option v-for="item in PRESET_WEAK_POINTS" :key="item" :label="item" :value="item" />
                      </el-select>
                    </div>
                  </div>
                  <div v-if="form.courses.length === 0" class="empty-hint">暂未添加课程</div>
                </div>
              </div>

              <div class="tag-review-section">
                <div class="form-group" :class="{ 'is-filled': form.resource_preference.length > 0 }">
                  <label>
                    <span>资源偏好</span>
                    <span class="filled-badge" v-if="form.resource_preference.length > 0"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.resource_preference" multiple placeholder="请选择资源类型" size="small">
                    <el-option v-for="item in PRESET_RESOURCE_PREFERENCES" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
                <div class="form-group" :class="{ 'is-filled': form.learning_style_tags.length > 0 }">
                  <label>
                    <span>学习方式</span>
                    <span class="filled-badge" v-if="form.learning_style_tags.length > 0"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.learning_style_tags" multiple placeholder="请选择学习方式" size="small">
                    <el-option v-for="item in PRESET_LEARNING_STYLE_TAGS" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
                <div class="form-group" :class="{ 'is-filled': form.programming_languages.length > 0 }">
                  <label>
                    <span>编程语言偏好</span>
                    <span class="filled-badge" v-if="form.programming_languages.length > 0"><el-icon><Select /></el-icon>已记录</span>
                  </label>
                  <el-select v-model="form.programming_languages" multiple filterable allow-create default-first-option placeholder="可选" size="small">
                    <el-option v-for="item in PRESET_PROGRAMMING_LANGUAGES" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
              </div>
            </div>

            <div class="panel-actions">
              <el-button @click="resetToChat">清空重置</el-button>
              <el-button type="primary" :loading="submitting" @click="submitForm">确认并生成画像</el-button>
            </div>
          </div>

          <!-- 右侧：对话聊天区域 -->
          <div class="chat-column">
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
                  <div class="message-bubble-container">
                    <div class="message-bubble">
                      <div class="bubble-content" v-html="formatMessageContent(msg.content)"></div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 统一的底部聊天输入框区域 -->
              <div class="chat-input-area" v-if="currentStep <= 10">
                <!-- 快捷选项区域 -->
                <div class="quick-replies-wrapper" v-if="currentQuickReplies.length > 0">
                  <p class="quick-replies-hint">{{ isMultiSelectStep ? '建议标签 (可点击多个后发送)' : '建议标签 (点击直接发送)' }}</p>
                  <div class="quick-replies-scroll">
                    <el-button
                      v-for="reply in currentQuickReplies"
                      :key="reply"
                      size="small"
                      round
                      class="quick-reply-btn"
                      :class="{ 'is-selected': isReplySelected(reply) }"
                      @click="handleQuickReply(reply)"
                    >
                      {{ reply }}
                    </el-button>
                  </div>
                </div>
                <!-- 真实输入框 -->
                <div class="input-box-wrapper">
                  <el-input
                    v-model="userInput"
                    placeholder="在这里自由输入回复..."
                    @keyup.enter="handleSend"
                    clearable
                  >
                    <template #append>
                      <el-button type="primary" @click="handleSend" class="send-btn">
                        发送
                      </el-button>
                    </template>
                  </el-input>
                </div>
              </div>
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
  Checked,
  Plus,
  Delete,
  Select
} from '@element-plus/icons-vue'

import { updateMe } from '@/auth/api/auth'
import { getProfileOnboarding, updateProfileOnboarding } from '@/profile/api/profile'
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
const submitting = ref(false)
const messageListRef = ref<HTMLDivElement | null>(null)

const currentStep = ref(1)
const currentCourseIndex = ref(0)
const userInput = ref('')

const form = reactive<ProfileOnboardingUpdate>({
  school: '',
  school_level: '',
  major: '',
  grade: '',
  daily_study_time: '',
  global_learning_goal: '',
  resource_preference: [],
  programming_languages: [],
  learning_style_tags: [],
  self_description: '',
  courses: [],
})

const PRESET_MAJORS = ['软件工程', '计算机科学与技术', '人工智能', '数据科学与大数据技术', '网络空间安全', '电子信息工程']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库系统', '编译原理', '机器学习']
const PRESET_GOALS = ['期末复习', '考研学习', '进阶学习', '补基础', '项目实战']
const PRESET_GRADES = ['大一', '大二', '大三', '大四', '研一', '研二', '研三']
const PRESET_DAILY_STUDY_TIME = ['30min以下', '30-60min', '1-2h', '2-3h', '3h以上']
const PRESET_FOUNDATION_LEVELS = ['薄弱', '一般', '较好', '熟练']
const PRESET_RESOURCE_PREFERENCES = ['文档', '图解', '练习题', '代码案例', '思维导图', 'PPT', '视频动画']
const PRESET_LEARNING_STYLE_TAGS = ['先看例子', '图解理解', '拆步骤慢慢学', '先做题巩固', '阅读文档', '项目实践']
const PRESET_PROGRAMMING_LANGUAGES = ['Python', 'Java', 'C++', 'JavaScript', 'Go', 'Rust']
const PRESET_WEAK_POINTS = ['概念理解', '公式推导', '代码实现', '题目分析', '实验操作', '知识串联']

const initMessages = () => {
  messages.value = [
    {
      id: Date.now(),
      role: 'assistant',
      content: '你好！我是你的学习画像引导助手。为了能为你量身定制更合适的学习路径与资源，我们需要先完成画像初始化。<br/><br/>首先，能告诉我你目前所在的<b>专业</b>吗？如果在读也可以告诉我学校~'
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
  currentCourseIndex.value = 0
  userInput.value = ''
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

// ----------------- Chat Interactive Logic -----------------

const currentQuickReplies = computed(() => {
  switch(currentStep.value) {
    case 1: return PRESET_MAJORS
    case 2: return PRESET_GRADES
    case 3: return PRESET_DAILY_STUDY_TIME
    case 4: return PRESET_GOALS
    case 5: return PRESET_COURSES
    case 6: return PRESET_FOUNDATION_LEVELS
    case 7: return ['暂时没有', ...PRESET_WEAK_POINTS]
    case 8: return PRESET_RESOURCE_PREFERENCES
    case 9: return PRESET_LEARNING_STYLE_TAGS
    case 10: return ['暂不选择', ...PRESET_PROGRAMMING_LANGUAGES]
    default: return []
  }
})

const isMultiSelectStep = computed(() => [5, 7, 8, 9, 10].includes(currentStep.value))

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
    // Single choice, send directly
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
  messages.value.push({ id: Date.now() + 1, role: 'assistant', content: assistantMsg })
  scrollToBottom()
}

const handleSend = () => {
  const text = userInput.value.trim()
  if (!text) return

  messages.value.push({ id: Date.now(), role: 'user', content: text })
  userInput.value = ''
  scrollToBottom()

  // Client-side parser for onboarding chat
  if (currentStep.value === 1) {
    const foundMajor = PRESET_MAJORS.find(m => text.includes(m))
    if (foundMajor) form.major = foundMajor; else form.major = text;
    currentStep.value = 2
    advanceStep(`太棒了！我已经记录了专业是 <b>${form.major}</b>。<br/><br/>接下来，请问你目前所在的<b>年级</b>是？`)
  }
  else if (currentStep.value === 2) {
    const found = PRESET_GRADES.find(g => text.includes(g))
    if (found) form.grade = found; else form.grade = text;
    currentStep.value = 3
    advanceStep(`好的，<b>${form.grade}</b>。为了评估你的学习节奏，你每天大约能抽出多少<b>学习时间</b>呢？`)
  }
  else if (currentStep.value === 3) {
    const found = PRESET_DAILY_STUDY_TIME.find(g => text.includes(g))
    if (found) form.daily_study_time = found; else form.daily_study_time = text;
    currentStep.value = 4
    advanceStep(`没问题，每天 <b>${form.daily_study_time}</b>。那你的<b>全局学习目标</b>是什么呢？`)
  }
  else if (currentStep.value === 4) {
    const found = PRESET_GOALS.find(g => text.includes(g))
    if (found) form.global_learning_goal = found; else form.global_learning_goal = text;
    currentStep.value = 5
    advanceStep(`收到！那么这学期你主要修读了哪些<b>核心课程</b>呢？你可以一次性选择多个，或打字告诉我。`)
  }
  else if (currentStep.value === 5) {
    const found = extractMultiple(text, PRESET_COURSES)
    if (found.length === 0 && text.length > 0) found.push(text)
    
    // Auto populate courses form
    form.courses = found.slice(0,3).map(c => ({
      course: c, foundation_level: '一般', current_topic: null, course_learning_goal: null, weak_points: []
    }))
    
    currentCourseIndex.value = 0
    currentStep.value = 6
    if (form.courses && form.courses.length > 0) {
      advanceStep(`好的，你这学期修了 <b>${form.courses.map(c=>c.course).join('、')}</b>。<br/><br/>那对于其中第一门课<b>“${form.courses[0]?.course}”</b>，你的基础水平大概是？`)
    } else {
      currentStep.value = 8
      advanceStep(`好的，暂时没有课程也没关系。接下来我想知道你更希望系统优先生成哪些<b>学习资源</b>？`)
    }
  }
  else if (currentStep.value === 6) {
    const found = PRESET_FOUNDATION_LEVELS.find(g => text.includes(g))
    const course = form.courses?.[currentCourseIndex.value]
    if (course) {
       course.foundation_level = found || text || '一般'
    }
    currentCourseIndex.value++
    if (form.courses && currentCourseIndex.value < form.courses.length) {
       advanceStep(`收到！继续看下一门课：<b>“${form.courses[currentCourseIndex.value]?.course}”</b>。你的基础水平大概是？`)
    } else {
       currentStep.value = 7
       currentCourseIndex.value = 0
       advanceStep(`基础情况记录好了。接下来我会帮你把每门课的薄弱点也整理进画像。先看<b>“${form.courses?.[0]?.course || ''}”</b>，你目前更卡在哪些地方？`)
    }
  }
  else if (currentStep.value === 7) {
    if (text !== '暂时没有') {
       const found = extractMultiple(text, PRESET_WEAK_POINTS)
       const course = form.courses?.[currentCourseIndex.value]
       if (course) {
          course.weak_points = found.length > 0 ? found : [text]
       }
    }
    currentCourseIndex.value++
    if (form.courses && currentCourseIndex.value < form.courses.length) {
       advanceStep(`那<b>“${form.courses[currentCourseIndex.value]?.course}”</b>呢？有没有类似的薄弱点需要我记下来？`)
    } else {
       currentStep.value = 8
       advanceStep(`课程情况已经整理好了。接下来我想知道你更希望系统优先生成哪些<b>学习资源</b>？`)
    }
  }
  else if (currentStep.value === 8) {
    const found = extractMultiple(text, PRESET_RESOURCE_PREFERENCES)
    form.resource_preference = found.length > 0 ? found : [text]
    currentStep.value = 9
    advanceStep(`收到。为了让后续讲解更贴合你，我再补充一个学习方式偏好：你平时更习惯哪种<b>学习方式</b>？`)
  }
  else if (currentStep.value === 9) {
    const found = extractMultiple(text, PRESET_LEARNING_STYLE_TAGS)
    form.learning_style_tags = found.length > 0 ? found : [text]
    currentStep.value = 10
    advanceStep(`最后，如果你的专业涉及编程，我可以顺手记下常用的<b>编程语言</b>，之后示例会更贴近你的技术栈。`)
  }
  else if (currentStep.value === 10) {
    if (text !== '暂不选择') {
       const found = extractMultiple(text, PRESET_PROGRAMMING_LANGUAGES)
       form.programming_languages = found.length > 0 ? found : [text]
    }
    currentStep.value = 11
    advanceStep(`太好啦！基本画像已经整理完成。你可以在左侧核对和微调，确认无误后点击左下角的<b>确认并生成画像</b>。`)
  }
}

// ----------------- Form Logic -----------------

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
}

const resetToChat = () => {
  resetState()
  form.school = ''
  form.school_level = ''
  form.major = ''
  form.grade = ''
  form.daily_study_time = ''
  form.global_learning_goal = ''
  form.resource_preference = []
  form.programming_languages = []
  form.learning_style_tags = []
  form.self_description = ''
  form.courses = []
}

const querySearchSchool = async (
  queryString: string,
  cb: (items: Array<{ value: string; level?: string | null }>) => void
) => {
  if (!queryString) { cb([]); return }
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
  if (!localStorage.getItem('token')) return
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
    form.learning_style_tags = baseInfo.learning_style_tags || []
    form.self_description = baseInfo.self_description || ''
    form.courses = Array.isArray(baseInfo.courses) ? baseInfo.courses.map((item) => ({
      course: item.course || '',
      foundation_level: item.foundation_level || '一般',
      current_topic: item.current_topic || null,
      course_learning_goal: item.course_learning_goal || null,
      weak_points: item.weak_points || []
    })) : []

    // 默认加载全部画像时，如果信息完整直接置为最终核对状态
    if (form.major && form.grade && form.daily_study_time && form.global_learning_goal) {
      currentStep.value = 11
      messages.value = [
        {
          id: 1,
          role: 'assistant',
          content: '欢迎回来！已为你加载保存过的画像数据。你可以在左侧核对和微调，确认无误后点击<b>确认并生成画像</b>。'
        }
      ]
    }
  } catch (error) {
    console.error('Failed to load onboarding data', error)
  }
}

const validateForm = () => {
  if (!form.major || !form.major.trim()) { ElMessage.warning('请输入或选择专业'); return false }
  if (!form.grade) { ElMessage.warning('请选择年级'); return false }
  if (!form.daily_study_time) { ElMessage.warning('请选择每日学习时间'); return false }
  if (!form.global_learning_goal) { ElMessage.warning('请选择全局学习目标'); return false }
  return true
}

const submitForm = async () => {
  if (!validateForm()) return
  submitting.value = true
  try {
    const validCourses = form.courses.filter((c) => c.course && c.course.trim())
    await updateProfileOnboarding({
      ...form,
      school: form.school ? form.school.trim() : '',
      major: form.major ? form.major.trim() : '',
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
    
    // 画像全部填满/生成后，不再弹出
    await updateMe({ is_first_login: false }).catch(() => {})

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

const handleSkip = () => {
  // 仅关闭本次弹窗，不修改状态，下次登录仍会弹出
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
}

.dialog-shell {
  padding: 24px;
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  height: 85vh;
  max-height: 800px;
  min-height: 500px;
  border-radius: 16px;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 16px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 700;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.dialog-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.subcopy {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.skip-btn {
  font-weight: 500;
  color: var(--color-text-muted);
}

/* 侧边布局 */
.onboarding-layout {
  display: flex;
  flex: 1;
  gap: 24px;
  overflow: hidden;
  min-height: 0;
}

/* 左侧：画像表单 (原右侧) */
.form-column {
  width: 440px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.02);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 12px;
}

.form-scroll-content {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.form-scroll-content::-webkit-scrollbar {
  width: 4px;
}
.form-scroll-content::-webkit-scrollbar-thumb {
  background: var(--color-border-hover);
  border-radius: 4px;
}

.compact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 0.3s ease;
}

.form-group.is-filled :deep(.el-input__wrapper) {
  border-color: var(--color-success);
  background-color: #f0fdf4;
  box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.2);
}

.form-group.is-filled :deep(.el-input__inner) {
  color: #065f46;
  font-weight: 600;
}

.form-group.span-2 {
  grid-column: span 2;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filled-badge {
  color: var(--color-success);
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 2px;
  animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes pop-in {
  0% { opacity: 0; transform: scale(0.8); }
  100% { opacity: 1; transform: scale(1); }
}

.required {
  color: var(--color-danger);
  margin-left: 2px;
}

.form-group :deep(.el-select),
.form-group :deep(.el-autocomplete) {
  width: 100%;
}

.courses-section {
  margin-top: 14px;
  border-top: 1px dashed var(--color-border-hover);
  padding-top: 14px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-hint {
  font-size: 12px;
  color: var(--color-text-faint);
  text-align: center;
  padding: 8px 0;
  background: var(--color-surface-hover);
  border-radius: 6px;
}

.course-row-card {
  padding: 8px;
  background: var(--color-surface);
  border-radius: 8px;
  border: 1px solid var(--color-border);
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  transition: all 0.3s ease;
}

.course-row-card.is-filled {
  border-color: var(--color-success);
  background-color: #f0fdf4;
}

.course-row-card.is-filled :deep(.el-input__wrapper) {
  border-color: var(--color-success);
  background-color: var(--color-surface);
}

.course-row-card.is-filled :deep(.el-input__inner) {
  color: #065f46;
  font-weight: 600;
}

.course-row-grid {
  display: grid;
  grid-template-columns: 1fr 90px 24px;
  gap: 6px;
  align-items: center;
}

.weak-point-select {
  grid-column: 1 / -1;
  margin-top: 2px;
}

.tag-review-section {
  margin-top: 14px;
  border-top: 1px dashed var(--color-border-hover);
  padding-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
  border-top: 1px solid var(--color-border-hover);
  padding-top: 16px;
  flex-shrink: 0;
}

/* 右侧：聊天区域 (原左侧) */
.chat-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-surface);
  border-radius: 12px;
  border: 1px solid var(--color-border);
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.message-list {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-list::-webkit-scrollbar {
  width: 4px;
}
.message-list::-webkit-scrollbar-thumb {
  background: var(--color-border-hover);
  border-radius: 4px;
}

.message-bubble-wrapper {
  display: flex;
  gap: 10px;
  max-width: 90%;
  align-items: flex-start;
  animation: fade-in-up 0.3s ease forwards;
}

.message-bubble-wrapper.assistant {
  align-self: flex-start;
}

.message-bubble-wrapper.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-bubble-wrapper.user .avatar-icon {
  background: var(--color-primary);
  color: var(--color-surface);
}

.message-bubble-container {
  display: flex;
  flex-direction: column;
}

.message-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  font-size: 13px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message-bubble-wrapper.assistant .message-bubble {
  background: var(--color-surface-hover);
  color: var(--color-text);
  border-top-left-radius: 2px;
}

.message-bubble-wrapper.user .message-bubble {
  background: var(--color-primary);
  color: var(--color-surface);
  border-top-right-radius: 2px;
}

.bubble-content :deep(b) {
  font-weight: 600;
  color: #1e1b4b;
}

.message-bubble-wrapper.user .bubble-content :deep(b) {
  color: var(--color-surface);
}

/* 统一底部聊天输入框区域 */
.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-replies-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quick-replies-hint {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 600;
}

.quick-replies-scroll {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-reply-btn {
  background: var(--color-surface);
  border: 1px solid var(--color-border-hover);
  color: var(--color-text-secondary);
  transition: all 0.2s ease;
}

.quick-reply-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.quick-reply-btn.is-selected {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-surface);
  font-weight: 600;
}

.input-box-wrapper :deep(.el-input-group__append) {
  background-color: transparent;
  border: none;
  padding: 0 8px;
}

.send-btn {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

/* 动效 */
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 960px) {
  .onboarding-layout {
    flex-direction: column-reverse;
    overflow-y: auto;
  }
  .form-column, .chat-column {
    width: 100%;
    height: 400px;
  }
}
</style>
