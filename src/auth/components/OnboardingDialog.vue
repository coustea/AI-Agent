<template>
  <component :is="standalone ? 'div' : 'Fragment'" :class="standalone ? 'onboarding-standalone' : undefined">
    <el-dialog
      v-model="visible"
      width="980px"
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
            <p class="subcopy">像聊天一样逐步回答，系统会在每轮给出可点击的建议回复，最后整理成画像草稿。</p>
          </div>
          <el-button text class="skip-btn" @click="handleSkip">稍后完善</el-button>
        </header>

        <div class="onboarding-layout">
          <!-- 左侧：对话聊天区域 -->
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

                    <!-- 交互式步骤选择器 (Step Controls) -->
                    <div v-if="msg.role === 'assistant' && msg.id === lastAssistantMessageId && currentStep <= 10" class="step-controls-wrapper animate-slide-in">
                      <p class="assistant-option-label">{{ currentOptionHint }}</p>
                      <!-- Step 1: School & Major inputs -->
                      <div v-if="currentStep === 1" class="step-form school-major-step">
                        <div class="form-item">
                          <label>选择学校</label>
                          <el-autocomplete
                            v-model="form.school"
                            :fetch-suggestions="querySearchSchool"
                            placeholder="请输入并选择学校"
                            clearable
                            @select="handleSchoolSelect"
                            style="width: 100%;"
                          />
                        </div>
                        <div class="form-item">
                          <label>选择专业</label>
                          <el-select
                            v-model="form.major"
                            filterable
                            allow-create
                            default-first-option
                            placeholder="请输入或选择专业"
                            style="width: 100%;"
                          >
                            <el-option v-for="item in PRESET_MAJORS" :key="item" :label="item" :value="item" />
                          </el-select>
                        </div>
                        <el-button type="primary" size="small" :disabled="!form.school || !form.major" @click="submitStep1">
                          发送学校和专业
                        </el-button>
                      </div>

                      <!-- Step 2: Grade tag buttons -->
                      <div v-else-if="currentStep === 2" class="quick-options">
                        <el-button
                          v-for="option in PRESET_GRADES"
                          :key="option"
                          size="small"
                          round
                          class="option-btn"
                          @click="submitStep2(option)"
                        >
                          {{ option }}
                        </el-button>
                      </div>

                      <!-- Step 3: Daily Study Time choices -->
                      <div v-else-if="currentStep === 3" class="quick-options">
                        <el-button
                          v-for="option in PRESET_DAILY_STUDY_TIME"
                          :key="option"
                          size="small"
                          round
                          class="option-btn"
                          @click="submitStep3(option)"
                        >
                          {{ option }}
                        </el-button>
                      </div>

                      <!-- Step 4: Learning Goal tags -->
                      <div v-else-if="currentStep === 4" class="quick-options">
                        <el-button
                          v-for="option in PRESET_GOALS"
                          :key="option"
                          size="small"
                          round
                          class="option-btn"
                          @click="submitStep4(option)"
                        >
                          {{ option }}
                        </el-button>
                      </div>

                      <!-- Step 5: Core Courses multi-select checkable tags -->
                      <div v-else-if="currentStep === 5" class="step-form courses-step">
                        <div class="checkable-tags-group">
                          <div
                            v-for="option in PRESET_COURSES"
                            :key="option"
                            :class="['course-tag-btn', selectedCourses.includes(option) ? 'active' : '']"
                            @click="toggleCourseSelection(option)"
                          >
                            {{ option }}
                          </div>
                        </div>
                        <el-button type="primary" size="small" :disabled="selectedCourses.length === 0" @click="submitStep5" style="margin-top: 12px;">
                          发送选择的课程
                        </el-button>
                      </div>

                      <!-- Step 6: Course Levels selection tags -->
                      <div v-else-if="currentStep === 6" class="quick-options">
                        <el-button
                          v-for="option in PRESET_FOUNDATION_LEVELS"
                          :key="option"
                          size="small"
                          round
                          class="option-btn"
                          @click="submitStep6(option)"
                        >
                          {{ option }}
                        </el-button>
                      </div>

                      <!-- Step 7: Weak points per course -->
                      <div v-else-if="currentStep === 7" class="step-form">
                        <div class="checkable-tags-group">
                          <div
                            v-for="option in PRESET_WEAK_POINTS"
                            :key="option"
                            :class="['course-tag-btn', currentCourseWeakPoints.includes(option) ? 'active' : '']"
                            @click="toggleCurrentCourseWeakPoint(option)"
                          >
                            {{ option }}
                          </div>
                        </div>
                        <div class="step-action-row">
                          <el-button size="small" @click="submitStep7(true)">暂时没有</el-button>
                          <el-button type="primary" size="small" @click="submitStep7(false)">确认薄弱点</el-button>
                        </div>
                      </div>

                      <!-- Step 8: Resource preference tags -->
                      <div v-else-if="currentStep === 8" class="step-form">
                        <div class="checkable-tags-group">
                          <div
                            v-for="option in PRESET_RESOURCE_PREFERENCES"
                            :key="option"
                            :class="['course-tag-btn', form.resource_preference.includes(option) ? 'active' : '']"
                            @click="toggleArraySelection(form.resource_preference, option)"
                          >
                            {{ option }}
                          </div>
                        </div>
                        <el-button type="primary" size="small" :disabled="form.resource_preference.length === 0" @click="submitStep8">
                          发送资源偏好
                        </el-button>
                      </div>

                      <!-- Step 9: Learning style tags -->
                      <div v-else-if="currentStep === 9" class="step-form">
                        <div class="checkable-tags-group">
                          <div
                            v-for="option in PRESET_LEARNING_STYLE_TAGS"
                            :key="option"
                            :class="['course-tag-btn', form.learning_style_tags.includes(option) ? 'active' : '']"
                            @click="toggleArraySelection(form.learning_style_tags, option)"
                          >
                            {{ option }}
                          </div>
                        </div>
                        <el-button type="primary" size="small" :disabled="form.learning_style_tags.length === 0" @click="submitStep9">
                          发送学习方式
                        </el-button>
                      </div>

                      <!-- Step 10: Programming language tags -->
                      <div v-else-if="currentStep === 10" class="step-form">
                        <div class="checkable-tags-group">
                          <div
                            v-for="option in PRESET_PROGRAMMING_LANGUAGES"
                            :key="option"
                            :class="['course-tag-btn', form.programming_languages.includes(option) ? 'active' : '']"
                            @click="toggleArraySelection(form.programming_languages, option)"
                          >
                            {{ option }}
                          </div>
                        </div>
                        <div class="step-action-row">
                          <el-button size="small" @click="submitStep10">暂不选择</el-button>
                          <el-button type="primary" size="small" @click="submitStep10">确认语言偏好</el-button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：画像实时核对面板 -->
          <div class="preview-column">
              <div class="panel-header">
                <el-icon><Checked /></el-icon>
              <span>边聊边整理的画像草稿</span>
            </div>

            <div class="preview-scroll-content">
              <div class="grid two">
                <div class="form-group">
                  <label>学校 <span class="required">*</span></label>
                  <el-autocomplete
                    v-model="form.school"
                    :fetch-suggestions="querySearchSchool"
                    placeholder="搜索学校"
                    clearable
                    @select="handleSchoolSelect"
                  />
                </div>

                <div class="form-group">
                  <label>专业 <span class="required">*</span></label>
                  <el-select v-model="form.major" filterable allow-create default-first-option placeholder="请选择或输入专业">
                    <el-option v-for="item in PRESET_MAJORS" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>

                <div class="form-group">
                  <label>年级 <span class="required">*</span></label>
                  <el-select v-model="form.grade" placeholder="请选择年级">
                    <el-option v-for="item in PRESET_GRADES" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>

                <div class="form-group">
                  <label>每日学习时长 <span class="required">*</span></label>
                  <el-select v-model="form.daily_study_time" placeholder="请选择时长">
                    <el-option v-for="item in PRESET_DAILY_STUDY_TIME" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>

                <div class="form-group span-2">
                  <label>全局学习目标 <span class="required">*</span></label>
                  <el-select v-model="form.global_learning_goal" filterable allow-create default-first-option placeholder="请选择学习目标">
                    <el-option v-for="item in PRESET_GOALS" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
              </div>

              <div v-if="currentStep >= 5 || form.courses.length > 0" class="courses-section">
                <div class="section-title">
                  <span>正在学习的课程 (最多3门) <span class="required">*</span></span>
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
                      <el-select
                        v-if="currentStep >= 7 || (c.weak_points && c.weak_points.length > 0)"
                        v-model="c.weak_points"
                        multiple
                        filterable
                        allow-create
                        default-first-option
                        placeholder="薄弱点"
                        class="weak-point-select"
                      >
                        <el-option v-for="item in PRESET_WEAK_POINTS" :key="item" :label="item" :value="item" />
                      </el-select>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="currentStep >= 8 || form.resource_preference.length > 0 || form.learning_style_tags.length > 0 || form.programming_languages.length > 0" class="tag-review-section">
                <div v-if="currentStep >= 8 || form.resource_preference.length > 0" class="form-group">
                  <label>资源偏好</label>
                  <el-select v-model="form.resource_preference" multiple placeholder="请选择资源类型">
                    <el-option v-for="item in PRESET_RESOURCE_PREFERENCES" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
                <div v-if="currentStep >= 9 || form.learning_style_tags.length > 0" class="form-group">
                  <label>学习方式</label>
                  <el-select v-model="form.learning_style_tags" multiple placeholder="请选择学习方式">
                    <el-option v-for="item in PRESET_LEARNING_STYLE_TAGS" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
                <div v-if="currentStep >= 10 || form.programming_languages.length > 0" class="form-group">
                  <label>编程语言偏好</label>
                  <el-select v-model="form.programming_languages" multiple filterable allow-create default-first-option placeholder="可选">
                    <el-option v-for="item in PRESET_PROGRAMMING_LANGUAGES" :key="item" :label="item" :value="item" />
                  </el-select>
                </div>
              </div>
            </div>

            <div class="panel-actions">
              <el-button @click="resetToChat">清空重来</el-button>
              <el-button type="primary" :loading="submitting" @click="submitForm">确认并生成画像</el-button>
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
  Delete
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
const selectedCourses = ref<string[]>([])
const currentCourseIndex = ref(0)

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
      id: 1,
      role: 'assistant',
      content: '你好！我是你的学习画像引导助手。为了能为你量身定制更合适的学习路径与多模态学习资源，我们先完成冷启动画像初始化。<br/><br/>首先，能告诉我你目前所在的<b>学校</b>与<b>专业</b>吗？'
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
  selectedCourses.value = []
  currentCourseIndex.value = 0
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

const lastAssistantMessageId = computed(() => {
  const assistantMsgs = messages.value.filter(m => m.role === 'assistant')
  if (assistantMsgs.length === 0) return null
  return assistantMsgs[assistantMsgs.length - 1]?.id || null
})

const currentCourseWeakPoints = computed(() => {
  const currentCourse = form.courses[currentCourseIndex.value]
  return currentCourse?.weak_points || []
})

const currentOptionHint = computed(() => {
  if (currentStep.value === 1) return '请补充'
  if (currentStep.value === 5) return '助手建议的课程'
  if (currentStep.value === 7) return '助手建议的薄弱点'
  if (currentStep.value === 8) return '助手建议的资源方向'
  if (currentStep.value === 9) return '助手建议的学习方式'
  if (currentStep.value === 10) return '助手建议的语言偏好'
  return '助手建议的可选回答'
})

const toggleArraySelection = (items: string[], value: string) => {
  const idx = items.indexOf(value)
  if (idx > -1) {
    items.splice(idx, 1)
  } else {
    items.push(value)
  }
}

// Step Submission Logic
const submitStep1 = () => {
  if (!form.school || !form.school.trim() || !form.major || !form.major.trim()) return

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: `学校：${form.school}，专业：${form.major}`
  })

  currentStep.value = 2

  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: `太棒了！我已经记录了您的学校是 <b>${form.school}</b>，专业是 <b>${form.major}</b>。<br/><br/>接下来，请问你目前所在的<b>年级</b>是？`
  })
  scrollToBottom()
}

const submitStep2 = (grade: string) => {
  form.grade = grade
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: grade
  })

  currentStep.value = 3
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: `好的，<b>${grade}</b>。为了评估你的学习节奏，你每天大约能抽出多少<b>学习时间</b>呢？`
  })
  scrollToBottom()
}

const submitStep3 = (time: string) => {
  form.daily_study_time = time
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: time
  })

  currentStep.value = 4
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: `没问题，每天 <b>${time}</b>。那你的<b>全局学习目标</b>是什么呢？`
  })
  scrollToBottom()
}

const submitStep4 = (goal: string) => {
  form.global_learning_goal = goal
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: goal
  })

  currentStep.value = 5
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: `收到！那么这学期你主要修读了哪些<b>核心课程</b>呢？我先列出一些常见课程，你可以直接选择，也可以在右侧补充。`
  })
  scrollToBottom()
}

const toggleCourseSelection = (courseName: string) => {
  const idx = selectedCourses.value.indexOf(courseName)
  if (idx > -1) {
    selectedCourses.value.splice(idx, 1)
  } else {
    if (selectedCourses.value.length >= 3) {
      ElMessage.warning('最多选择 3 门正在学习的课程')
      return
    }
    selectedCourses.value.push(courseName)
  }
}

const submitStep5 = () => {
  if (selectedCourses.value.length === 0) return

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: `修读课程：${selectedCourses.value.join('、')}`
  })

  form.courses = selectedCourses.value.map(c => ({
    course: c,
    foundation_level: '一般',
    current_topic: null,
    course_learning_goal: null,
    weak_points: []
  }))

  currentStep.value = 6
  currentCourseIndex.value = 0

  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: `好的，你这学期修了 <b>${selectedCourses.value.join('、')}</b>。<br/><br/>那对于其中第一门课<b>“${selectedCourses.value[0]}”</b>，你的基础水平大概是？`
  })
  scrollToBottom()
}

const submitStep6 = (level: string) => {
  const currentCourse = form.courses[currentCourseIndex.value]
  if (!currentCourse) return
  currentCourse.foundation_level = level

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: `“${currentCourse.course}”基础水平：${level}`
  })

  currentCourseIndex.value++

  if (currentCourseIndex.value < form.courses.length) {
    const nextCourse = form.courses[currentCourseIndex.value]?.course || ''
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: `收到！继续看下一门课：<b>“${nextCourse}”</b>。你的基础水平大概是？`
    })
  } else {
    currentStep.value = 7
    currentCourseIndex.value = 0
    const firstCourse = form.courses[0]?.course || ''
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: `基础情况记录好了。接下来我会帮你把每门课的薄弱点也整理进画像。先看<b>“${firstCourse}”</b>，你目前更卡在哪些地方？`
    })
  }
  scrollToBottom()
}

const toggleCurrentCourseWeakPoint = (point: string) => {
  const currentCourse = form.courses[currentCourseIndex.value]
  if (!currentCourse) return
  if (!Array.isArray(currentCourse.weak_points)) {
    currentCourse.weak_points = []
  }
  toggleArraySelection(currentCourse.weak_points, point)
}

const submitStep7 = (skip: boolean) => {
  const currentCourse = form.courses[currentCourseIndex.value]
  if (!currentCourse) return
  if (skip) {
    currentCourse.weak_points = []
  }
  const points = currentCourse.weak_points || []

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: points.length > 0
      ? `“${currentCourse.course}”薄弱点：${points.join('、')}`
      : `“${currentCourse.course}”暂时没有明显薄弱点`
  })

  currentCourseIndex.value++
  if (currentCourseIndex.value < form.courses.length) {
    const nextCourse = form.courses[currentCourseIndex.value]?.course || ''
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: `那<b>“${nextCourse}”</b>呢？有没有类似的薄弱点需要我记下来？`
    })
  } else {
    currentStep.value = 8
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: '课程情况已经整理好了。接下来我想知道你更希望系统优先生成哪些<b>学习资源</b>，我会把它作为后续推荐的依据。'
    })
  }
  scrollToBottom()
}

const submitStep8 = () => {
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: `资源偏好：${form.resource_preference.join('、')}`
  })

  currentStep.value = 9
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: '收到。为了让后续讲解更贴合你，我再补充一个学习方式偏好：你平时更习惯哪种<b>学习方式</b>？'
  })
  scrollToBottom()
}

const submitStep9 = () => {
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: `学习方式：${form.learning_style_tags.join('、')}`
  })

  currentStep.value = 10
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: '最后，如果你的课程涉及编程，我可以顺手记下常用的<b>编程语言</b>，之后示例会更贴近你的技术栈。'
  })
  scrollToBottom()
}

const submitStep10 = () => {
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: form.programming_languages.length > 0
      ? `编程语言偏好：${form.programming_languages.join('、')}`
      : '暂不选择编程语言偏好'
  })

  currentStep.value = 11
  messages.value.push({
    id: Date.now() + 1,
    role: 'assistant',
    content: '太好啦！基本画像已经整理完成。你可以在右侧核对和微调，确认无误后点击右下角的<b>确认并生成画像</b>。'
  })
  scrollToBottom()
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
    if (form.school && form.major && form.grade && form.daily_study_time && form.global_learning_goal && form.courses.length > 0) {
      currentStep.value = 11
      messages.value = [
        {
          id: 1,
          role: 'assistant',
          content: '欢迎回来！已为你加载保存过的画像数据。你可以在右侧核对和微调，确认无误后点击右下角的<b>确认并生成画像</b>。'
        }
      ]
    }
  } catch (error) {
    console.error('Failed to load onboarding data', error)
  }
}

const validateForm = () => {
  if (!form.school || !form.school.trim()) {
    ElMessage.warning('请输入学校名称')
    return false
  }
  if (!form.major || !form.major.trim()) {
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
  const validCourses = form.courses.filter((c) => c.course && c.course.trim())
  if (validCourses.length === 0) {
    ElMessage.warning('请至少添加一门正在学习的课程')
    return false
  }
  if (validCourses.some((c) => !c.foundation_level)) {
    ElMessage.warning('请选择课程基础水平')
    return false
  }
  if (form.resource_preference.length === 0) {
    ElMessage.warning('请至少选择一个资源偏好')
    return false
  }
  if (form.learning_style_tags.length === 0) {
    ElMessage.warning('请至少选择一个学习方式')
    return false
  }
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

/* 侧边布局 */
.onboarding-layout {
  display: flex;
  flex: 1;
  gap: 24px;
  overflow: hidden;
  min-height: 0;
}

/* 聊天栏 (左侧) */
.chat-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
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
  padding: 8px 4px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-bubble-wrapper {
  display: flex;
  gap: 12px;
  max-width: 90%;
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

.message-bubble-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: calc(100% - 48px);
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

/* 交互式步骤控制器样式 */
.step-controls-wrapper {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.assistant-option-label {
  margin: 0;
  padding: 3px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.4;
}

.step-form {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  max-width: 340px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-item label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

/* 快速选择选项 */
.quick-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
  max-width: 360px;
}

.option-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  transition: all 0.2s ease;
  font-size: 12px;
}

.option-btn:hover {
  border-color: #4f46e5;
  color: #4f46e5;
  background: #eef2ff;
}

/* 助手建议选项 */
.checkable-tags-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.course-tag-btn {
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 12px;
  transition: all 0.2s ease;
  user-select: none;
}

.course-tag-btn:hover {
  border-color: #4f46e5;
  color: #4f46e5;
}

.course-tag-btn.active {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #ffffff;
  font-weight: 600;
}

.step-action-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 预览核对栏 (右侧) */
.preview-column {
  width: 420px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #4f46e5;
  margin-bottom: 16px;
  flex-shrink: 0;
  border-bottom: 1px solid #cbd5e1;
  padding-bottom: 12px;
}

.panel-header .el-icon {
  font-size: 18px;
}

.preview-scroll-content {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}

.form-group.span-2 {
  grid-column: span 2;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.required {
  color: #ef4444;
  margin-left: 2px;
}

.form-group :deep(.el-select),
.form-group :deep(.el-autocomplete) {
  width: 100%;
}

/* 选修课程 */
.courses-section {
  margin-top: 16px;
  border-top: 1px dashed #cbd5e1;
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
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.course-row-grid {
  display: grid;
  grid-template-columns: 1fr 100px 32px;
  gap: 8px;
  align-items: center;
}

.weak-point-select {
  grid-column: 1 / -1;
}

.tag-review-section {
  margin-top: 16px;
  border-top: 1px dashed #cbd5e1;
  padding-top: 16px;
}

.course-input :deep(.el-input__inner),
.level-select :deep(.el-input__inner),
.weak-point-select :deep(.el-input__inner) {
  border-radius: 6px;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  border-top: 1px solid #cbd5e1;
  padding-top: 16px;
  flex-shrink: 0;
}

/* 动效 */
.animate-slide-in {
  animation: slide-in 0.2s ease-out forwards;
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 960px) {
  .onboarding-layout {
    flex-direction: column;
    overflow-y: auto;
  }

  .preview-column {
    width: 100%;
    height: auto;
    overflow: visible;
  }

  .chat-column {
    height: 400px;
    border-right: none;
    padding-right: 0;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 20px;
  }
}
</style>
