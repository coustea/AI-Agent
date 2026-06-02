<template>
  <el-dialog
      v-model="visible"
      width="800px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="ai-native-dialog-light"
      align-center
  >
    <div class="ai-chat-wrapper">
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
            <el-dropdown trigger="click" @command="handleHeaderCommand" class="more-dropdown">
              <el-button class="header-action-btn" circle>
                <el-icon><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="never" class="never-prompt-item">不再弹出</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button class="header-action-btn close-btn" circle @click="handleHeaderCommand('skip')" title="稍后完善">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
      </header>

      <main class="chat-messages" ref="messagesRef">
        <transition-group name="msg-list">
          <div v-for="(msg, index) in botMessages" :key="msg.id" class="message-row" :class="msg.role">
            <div class="message-content" style="display: flex; flex-direction: column; align-items: flex-start; max-width: 100%; width: 100%;">
              <div class="bubble" v-html="msg.content"></div>
              
              <!-- INLINE WIDGETS -->
              <div v-if="index === botMessages.length - 1 && !isTyping && !isStreaming && currentQuestion && (currentQuestion === 'major' || currentQuestion === 'courses')" class="inline-action-panel mt-3 w-full">
                <transition name="panel-slide" mode="out-in">
                  
                  <!-- Major Options -->
                  <div v-if="currentQuestion === 'major'" class="action-card" key="major">
                    <div class="chips-container stagger-animation">
                      <div v-for="(major, idx) in PRESET_MAJORS" :key="major" class="ai-chip" :style="{ animationDelay: `${idx * 0.03}s` }" @click="submitMajor(major)">
                        {{ major }}
                      </div>
                    </div>
                  </div>

                  <!-- Courses Options -->
                  <div v-else-if="currentQuestion === 'courses'" class="action-card" key="courses">
                    <div class="chips-container stagger-animation">
                      <div v-for="(course, idx) in PRESET_COURSES" :key="course" class="ai-chip" :class="{ active: onboardingForm.courses.includes(course) }" :style="{ animationDelay: `${idx * 0.03}s` }" @click="toggleCourse(course)">
                        {{ course }}
                      </div>
                      <div v-for="customCourse in customAddedCourses" :key="customCourse" class="ai-chip active pop-in" @click="toggleCourse(customCourse)">
                        {{ customCourse }}
                      </div>
                    </div>
                    <div class="button-row mt-3">
                       <el-button type="primary" class="primary-send-btn" @click="submitCourses">
                         确认并继续 <el-icon class="ml-1"><Position/></el-icon>
                       </el-button>
                    </div>
                  </div>
                </transition>
              </div>
            </div>
          </div>

          <div v-if="isTyping" key="typing" class="message-row bot typing-row">
            <div class="bubble typing-bubble">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </transition-group>
      </main>

      <footer class="chat-footer" :class="{ 'is-collapsed-panel': isFinishedState || !currentQuestion }">
        <transition name="panel-slide" mode="out-in">
          <!-- Universal Input for Major and Courses -->
          <div v-if="currentQuestion === 'major' || currentQuestion === 'courses'" class="ai-input-wrap slide-up-anim" key="chat-input">
            <el-input
                v-model="universalInput"
                placeholder="直接回复，或输入补充细节..."
                @keyup.enter="handleUniversalSubmit"
                class="glass-command-bar"
            >
              <template #suffix>
                <el-button @click="handleUniversalSubmit" class="inside-action-btn" circle :disabled="!universalInput.trim()">
                  <el-icon><Position/></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>

          <!-- School Form -->
          <div v-else-if="currentQuestion === 'school'" class="action-panel form-panel" key="school">
            <div class="form-row slide-up-anim" style="animation-delay: 0.1s">
              <el-autocomplete v-model="onboardingForm.school" :fetch-suggestions="querySearchSchool" placeholder="搜索并选择院校名称" clearable class="glass-select w-full" @select="handleSchoolSelect" placement="top-start" popper-class="school-autocomplete-popper">
                <template #prefix><el-icon><Search /></el-icon></template>
                <template #default="{ item }">
                  <div class="autocomplete-item">
                    <span class="school-name">
                      <el-icon class="mr-1"><School /></el-icon>
                      {{ item.value }}
                    </span>
                    <span v-if="item.level" class="school-tag" :class="getSchoolLevelClass(item.level)">
                      {{ item.level }}
                    </span>
                  </div>
                </template>
              </el-autocomplete>
            </div>
            <div class="button-row mt-3 slide-up-anim" style="animation-delay: 0.2s">
               <el-button type="primary" class="primary-send-btn" @click="submitSchool">
                 确认发送 <el-icon class="ml-1"><Position/></el-icon>
               </el-button>
            </div>
          </div>

          <!-- Grade Form -->
          <div v-else-if="currentQuestion === 'grade'" class="action-panel form-panel" key="grade">
            <div class="form-row slide-up-anim" style="animation-delay: 0.1s">
              <el-select v-model="onboardingForm.education_level" placeholder="请选择学历层次" class="glass-select w-full" filterable placement="top-start">
                <el-option v-for="level in PRESET_EDUCATION_LEVELS" :key="level" :label="level" :value="level" />
              </el-select>
            </div>
            <div class="form-row mt-3 slide-up-anim" style="animation-delay: 0.18s">
              <el-select v-model="onboardingForm.grade" filterable allow-create default-first-option placeholder="请选择当前年级" class="glass-select w-full" placement="top-start">
                <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
              </el-select>
            </div>
            <div class="button-row mt-3 slide-up-anim" style="animation-delay: 0.25s">
               <el-button type="primary" class="primary-send-btn" @click="submitGrade">
                 确认发送 <el-icon class="ml-1"><Position/></el-icon>
               </el-button>
            </div>
          </div>

          <!-- Goal Form -->
          <div v-else-if="currentQuestion === 'goal'" class="action-panel form-panel" key="goal">
            <div class="form-row slide-up-anim" style="animation-delay: 0.1s">
              <el-select v-model="onboardingForm.learning_goal" filterable allow-create default-first-option placeholder="请选择核心学习目标" class="glass-select w-full" placement="top-start">
                <el-option v-for="goal in PRESET_GOALS" :key="goal" :label="goal" :value="goal" />
              </el-select>
            </div>
            <div class="form-row mt-3 slide-up-anim" style="animation-delay: 0.18s">
              <el-select v-model="onboardingForm.preferred_language" filterable allow-create default-first-option clearable placeholder="常用编程语言 (选填)" class="glass-select w-full" placement="top-start">
                <el-option v-for="language in PRESET_LANGUAGES" :key="language" :label="language" :value="language" />
              </el-select>
            </div>
            <div class="button-row mt-3 slide-up-anim" style="animation-delay: 0.25s">
               <el-button type="primary" class="primary-send-btn finish-btn" :loading="submitting" @click="submitGoal">
                 <span class="finish-text">生成画像</span> <el-icon class="ml-1"><Check /></el-icon>
               </el-button>
            </div>
          </div>
        </transition>
      </footer>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Service, Position, Search, Close, Check, MoreFilled, School } from '@element-plus/icons-vue'

import { getProfileOnboarding, updateProfileOnboarding, searchSchools } from '@/api/ai'
import type { ProfileOnboardingUpdate, SchoolItem } from '@/api/ai'
import { updateMe } from '@/api/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const route = useRoute()
const router = useRouter()

interface Message {
  id: number;
  role: 'bot' | 'user';
  content: string;
}
const messages = ref<Message[]>([])
const isTyping = ref(false)
const isStreaming = ref(false)
const currentQuestion = ref('major')
const isFinishedState = ref(false)
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

const botMessages = computed(() => messages.value.filter(m => m.role === 'bot'))

// 优化：删除了原本列表末尾的 '其他' 选项
const PRESET_MAJORS = ['计算机科学与技术', '软件工程', '人工智能', '数据科学与大数据技术', '网络空间安全', '电子信息工程']
const PRESET_COURSES = ['数据结构与算法', '操作系统', '计算机网络', '数据库系统概论', '编译原理', '机器学习']
const PRESET_GOALS = [
  '考研深造与学术冲刺（真题攻坚与专业课精讲）',
  '求职就业与面试突击（大厂真题与项目实战经验）',
  '竞赛夺奖与科研攻坚（高水平赛事与论文指导）',
  '名校保研与出国留学（背景提升与直通申请）',
  '期末满绩与绩点跃升（核心专业课重难点突破）'
]
const PRESET_EDUCATION_LEVELS = ['高职/专科', '本科', '研究生']
const PRESET_GRADES = [
  '大一', '大二', '大三', '大四', '大五',
  '研一', '研二', '研三',
  '博一', '博二', '博三',
  '高职一年级', '二年级', '三年级'
]
const PRESET_LANGUAGES = ['Python', 'Java', 'C++', 'JavaScript', 'Go', 'Rust']

const universalInput = ref('')

const handleUniversalSubmit = () => {
  const val = universalInput.value.trim()
  if (!val) return
  
  if (currentQuestion.value === 'major') {
    submitMajor(val)
  } else if (currentQuestion.value === 'courses') {
    customInputs.course = val
    addCustomCourse()
  } else {
    ElMessage.info('请在上方卡片中完成选择')
  }
  universalInput.value = ''
}

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
    isFinishedState.value = false;
    loadStatus().then(() => {
      startChat();
    });
  }
})

onMounted(() => { if (visible.value) { loadStatus().then(() => startChat()) } })

const scrollOnNewMessage = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTo({
      top: messagesRef.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

const streamMessageContent = (msgObj: Message, fullText: string, speed = 20): Promise<void> => {
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
        index++
      } else {
        msgObj.content += char
        index++
      }
    }, speed)
  })
}

const addBotMessage = async (content: string, delay = 500) => {
  isTyping.value = true
  await new Promise(resolve => setTimeout(resolve, delay))
  isTyping.value = false

  const msgObj: Message = reactive({ id: Date.now(), role: 'bot', content: '' })
  messages.value.push(msgObj)

  await scrollOnNewMessage()
  await streamMessageContent(msgObj, content)
}

const addUserMessage = async (content: string) => {
  messages.value.push({ id: Date.now(), role: 'user', content })
  await scrollOnNewMessage()
}

const startChat = async () => {
  messages.value = []
  currentQuestion.value = ''
  isFinishedState.value = false
  await addBotMessage('👋 欢迎来到学枢！我是你的专属 AI 学习规划师。', 400)
  await addBotMessage('为了给你生成最精准的个性化学习资源，我们需要构建一下你的专属画像。首先，能告诉我你目前<b>主修什么专业</b>吗？', 600)
  currentQuestion.value = 'major'
}

const submitMajor = async (majorVal: string) => {
  const val = majorVal.trim()
  if (!val) { ElMessage.warning('请输入专业名称'); return }
  onboardingForm.major = val
  await addUserMessage(val)
  currentQuestion.value = ''

  await addBotMessage(`太棒了！针对 <b>${val}</b> 专业，你目前主要在学<b>哪些核心课程</b>呢？（可多选）`, 500)
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
  await addUserMessage(onboardingForm.courses.join('、'))
  currentQuestion.value = ''

  await addBotMessage('了解了！为了匹配合适的学习难度，请问你是<b>哪个院校</b>的同学呢？', 500)
  currentQuestion.value = 'school'
}

const submitSchool = async () => {
  if (!onboardingForm.school) {
    ElMessage.warning('请输入并选择您的院校名称'); return
  }
  let text = onboardingForm.school
  if (onboardingForm.school_level) text += ` <span style="opacity:0.6;font-size:0.9em">(${onboardingForm.school_level})</span>`
  await addUserMessage(text)
  currentQuestion.value = ''

  await addBotMessage('收到！你的<b>学历层次</b>和<b>当前年级</b>是？', 500)
  currentQuestion.value = 'grade'
}

const submitGrade = async () => {
  if (!onboardingForm.education_level) { ElMessage.warning('请选择学历层次'); return }
  if (!onboardingForm.grade) { ElMessage.warning('请选择年级'); return }

  await addUserMessage(`${onboardingForm.education_level} - ${onboardingForm.grade}`)
  currentQuestion.value = ''

  await addBotMessage('最后两个小问题！你当前的<b>主要学习目标</b>是什么？有比较常用的编程语言吗？', 500)
  currentQuestion.value = 'goal'
}

const submitGoal = async () => {
  if (!onboardingForm.learning_goal) { ElMessage.warning('请选择当前学习目标'); return }

  let text = onboardingForm.learning_goal
  if (onboardingForm.preferred_language) text += ` <span style="opacity:0.6;font-size:0.9em">(语言: ${onboardingForm.preferred_language})</span>`

  await addUserMessage(text)
  currentQuestion.value = ''
  isFinishedState.value = true

  await addBotMessage('🎉 感谢配合！正在为你进行 AI 运算并生成专属学习画像...', 400)
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

const getSchoolLevelClass = (level: string) => {
  if (!level) return '';
  if (level.includes('985') || level.includes('211') || level.includes('双一流')) {
    return 'level-elite';
  }
  if (level.includes('本科')) {
    return 'level-undergrad';
  }
  return 'level-associate';
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
    }, 1200);
  } catch (e) {
    ElMessage.error('保存失败，请重试');
    submitting.value = false;
    isFinishedState.value = false;
  }
}

const handleHeaderCommand = async (cmd: string) => {
  if (cmd === 'never') {
    try {
      await updateMe({ is_first_login: false })
      ElMessage.success('画像引导已关闭，不再弹出。')
    } catch (e) {
      console.error('Failed to update onboarding status', e)
    }
  }
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

.ai-chat-wrapper {
  display: flex;
  flex-direction: column;
  height: 640px;
  background: var(--color-surface);
  position: relative;
  overflow: hidden;
  color: #1d1d1f;
}

.chat-footer {
  background: var(--color-surface);
  border-top: 1px solid #e5e5ea;
  padding: var(--space-4) var(--space-6) 24px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  transition: all var(--transition-slow) cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 10;
}

.chat-footer.is-collapsed-panel {
  height: 0;
  min-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  border-top-color: transparent;
  overflow: hidden;
  pointer-events: none;
}

.quick-reply-area {
  width: 100%;
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
  background: var(--color-primary, #4F46E5);
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

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.header-action-btn {
  border: none !important;
  background: transparent !important;
  color: #86868b !important;
  width: 32px !important;
  height: 32px !important;
  font-size: 16px !important;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-base) !important;
  padding: 0 !important;
}

.header-action-btn:hover {
  background: #f5f5f7 !important;
  color: #1d1d1f !important;
}

.header-action-btn.close-btn:hover {
  background: #fef2f2 !important;
  color: #ef4444 !important;
}

:deep(.never-prompt-item) {
  color: #ef4444 !important;
  font-weight: 500;
}

/* Messages Area */
.chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 30px var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  background: var(--color-surface);
  transition: all var(--transition-slow) cubic-bezier(0.4, 0, 0.2, 1);
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
  flex-direction: column;
  width: 100%;
}

.bubble {
  box-sizing: border-box;
  width: 100%;
  padding: var(--space-4);
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
  position: relative;
}

.bot .bubble {
  background: #f8fafc;
  color: #1e293b;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
}

.bot .bubble :deep(b) {
  color: var(--color-primary, #4F46E5);
  font-weight: var(--weight-semibold);
}

.inline-action-panel {
  background: transparent;
  width: 100%;
}

.glass-command-bar {
  --el-input-border-radius: 24px;
  --el-input-bg-color: #ffffff;
  --el-input-border-color: rgba(0,0,0,0.1);
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border-radius: 24px;
}
.glass-command-bar :deep(.el-input__wrapper) {
  padding: 8px 16px;
  box-shadow: none !important;
  border: 1px solid rgba(0,0,0,0.1);
}
.glass-command-bar :deep(.el-input__inner) {
  font-size: 15px;
}
.user .bubble :deep(span) {
  color: rgba(255, 255, 255, 0.85) !important;
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
  background-color: var(--color-primary, #4F46E5);
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-4px); background-color: var(--color-primary-hover, #4338CA); }
}

/* Footer / Action Area */
/* (Action Area is now .right-action-pane, keeping some inner layout classes intact) */

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
  color: var(--color-primary, #4F46E5);
  background: var(--color-primary-soft, #EEF2FF);
  padding: 2px var(--space-2);
  border-radius: var(--radius-lg);
  font-weight: var(--weight-medium);
}

.chips-container {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.ai-chip {
  padding: 10px 18px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 500;
  background: #ffffff;
  color: #1e293b;
  cursor: pointer;
  border: 1px solid #f1f5f9;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  transition: all 0.2s ease;
  user-select: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-grow: 0;
  text-align: center;
  max-width: 100%;
  box-sizing: border-box;
  white-space: normal;
  word-break: break-all;
}

.ai-chip:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  border-color: var(--color-primary-border, #C7D2FE);
  color: var(--color-primary, #4F46E5);
}

.ai-chip.active {
  background: var(--color-primary, #4F46E5) !important;
  color: var(--color-surface) !important;
  border-color: var(--color-primary, #4F46E5) !important;
  font-weight: var(--weight-medium);
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.2);
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
  border-color: var(--color-primary, #4F46E5) !important;
  box-shadow: 0 0 0 1px var(--color-primary, #4F46E5) !important;
}

/* Buttons & Action Bar */
.footer-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.action-bar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.action-bar-right {
  display: flex;
  justify-content: flex-end;
  flex: 1;
}

.outline-action-btn {
  font-size: 13px !important;
  height: 32px !important;
  padding: 0 14px !important;
  border-color: #d1d1d6 !important;
  color: #515154 !important;
  background: var(--color-surface) !important;
  font-weight: var(--weight-medium) !important;
  transition: all var(--transition-base) !important;
}

.outline-action-btn:hover, .outline-action-btn:focus {
  border-color: var(--color-primary-border, #C7D2FE) !important;
  background: var(--color-primary-soft, #EEF2FF) !important;
  color: var(--color-primary, #4F46E5) !important;
}

.outline-action-btn.danger-outline:hover {
  border-color: #fca5a5 !important;
  background: #fef2f2 !important;
  color: #ef4444 !important;
}

.outline-action-btn .el-icon {
  margin-right: 3px;
  font-size: 14px;
}

.inside-action-btn {
  background: var(--color-primary, #4F46E5) !important;
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
  background: var(--color-primary-hover, #4338CA) !important;
}

.ghost-circle {
  background: #f5f5f7 !important;
  color: #1d1d1f !important;
}
.ghost-circle:hover {
  background: var(--color-primary-soft, #EEF2FF) !important;
  color: var(--color-primary, #4F46E5) !important;
}

.button-row {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

.primary-send-btn {
  background: var(--color-primary, #4F46E5) !important;
  color: var(--color-surface) !important;
  border: none !important;
  border-radius: var(--radius-lg) !important;
  font-weight: var(--weight-medium) !important;
  padding: 0 var(--space-5) !important;
  height: 36px !important;
  font-size: 13.5px !important;
  transition: all var(--transition-base) !important;
  box-shadow: 0 4px 10px rgba(79, 70, 229, 0.12) !important;
}
.primary-send-btn:hover {
  background: var(--color-primary-hover, #4338CA) !important;
  box-shadow: 0 6px 14px rgba(79, 70, 229, 0.22) !important;
}

.finish-btn {
  padding: 0 var(--space-6) !important;
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
  box-shadow: 0 0 0 1px var(--color-primary, #4F46E5) !important;
}

/* School Autocomplete Popper styles */
:global(.school-autocomplete-popper) {
  border-radius: 12px !important;
  box-shadow: 0 10px 25px rgba(0,0,0,0.08) !important;
  border: 1px solid #e2e8f0 !important;
  background: var(--color-surface) !important;
  overflow: hidden;
}

:global(.school-autocomplete-popper .el-autocomplete-suggestion__wrap) {
  padding: 4px 0 !important;
}

:global(.school-autocomplete-popper .el-autocomplete-suggestion__list li) {
  padding: 10px 16px !important;
  transition: all 0.2s ease;
}

:global(.school-autocomplete-popper .el-autocomplete-suggestion__list li:hover),
:global(.school-autocomplete-popper .el-autocomplete-suggestion__list li.highlighted) {
  background-color: var(--color-primary-soft, #EEF2FF) !important;
}

:global(.school-autocomplete-popper .el-autocomplete-suggestion__list li:hover .school-name),
:global(.school-autocomplete-popper .el-autocomplete-suggestion__list li.highlighted .school-name) {
  color: var(--color-primary, #4F46E5) !important;
}

.autocomplete-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.school-name {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: #1d1d1f;
  font-weight: 500;
  transition: color 0.2s ease;
}

.school-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 20px;
  font-weight: 500;
  white-space: nowrap;
}

.school-tag.level-elite {
  color: #b45309;
  background: #fef3c7;
  border: 1px solid #fcd34d;
}

.school-tag.level-undergrad {
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.school-tag.level-associate {
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}

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
.status-pulse { display: flex; align-items: center; gap: var(--space-2); color: var(--color-primary, #4F46E5); font-size: 13px; font-weight: var(--weight-medium); }
.pulse-ring {
  width: 12px; height: 12px; border-radius: var(--radius-pill);
  background: var(--color-primary, #4F46E5);
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
  .ai-chat-wrapper { height: 100vh; border-radius: 0; }
  .ai-native-dialog-light :deep(.el-dialog) { margin-top: 0 !important; border-radius: 0; width: 100% !important; }
  .bubble { max-width: 85%; }
}
</style>
