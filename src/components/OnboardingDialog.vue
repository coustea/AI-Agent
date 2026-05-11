<template>
  <el-dialog
    v-model="visible"
    width="680px"
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    class="pure-form-onboarding-dialog"
    align-center
  >
    <div class="onboarding-wrapper">
      
      <main class="onboarding-main">
        <div class="step-meta-box">
          <h2>{{ currentStepMeta.title }}</h2>
          <p>{{ currentStepMeta.helper }}</p>
        </div>

        <el-form
          ref="onboardingFormRef"
          :model="onboardingForm"
          :rules="onboardingRules"
          label-position="top"
          class="tag-form"
          hide-required-asterisk
          @submit.prevent
        >
          <transition name="fade-slide-up" mode="out-in">
            
            <div v-if="currentStep === 0" key="step0" class="step-pane">
              <el-form-item prop="major">
                <template #label>
                  <div class="custom-label">
                    <span>主修专业</span><span class="required-star">*</span>
                  </div>
                </template>
                <div class="tag-group">
                  <div 
                    v-for="major in PRESET_MAJORS" 
                    :key="major"
                    class="selectable-tag"
                    :class="{ active: onboardingForm.major === major }"
                    @click="setSingleValue('major', major)"
                  >
                    {{ major }}
                  </div>
                </div>
                <el-input 
                  v-model="customInputs.major" 
                  placeholder="上方没有？请输入您的专业" 
                  class="custom-inline-input mt-3"
                  @input="setSingleValue('major', customInputs.major)"
                />
              </el-form-item>

              <el-form-item prop="courses">
                <template #label>
                  <div class="custom-label">
                    <span>当前正在学习的课程 (可多选)</span><span class="required-star">*</span>
                  </div>
                </template>
                <div class="tag-group">
                  <div 
                    v-for="course in PRESET_COURSES" 
                    :key="course"
                    class="selectable-tag"
                    :class="{ active: onboardingForm.courses.includes(course) }"
                    @click="toggleMultiValue('courses', course)"
                  >
                    {{ course }}
                  </div>
                  <div 
                    v-for="customCourse in customAddedCourses" 
                    :key="customCourse"
                    class="selectable-tag active custom-added-tag"
                    @click="toggleMultiValue('courses', customCourse)"
                  >
                    {{ customCourse }} <el-icon class="ml-1"><Close /></el-icon>
                  </div>
                </div>
                <el-input 
                  v-model="customInputs.course" 
                  placeholder="输入课程名称，按回车添加" 
                  class="custom-inline-input mt-3"
                  @keyup.enter="addCustomCourse"
                >
                  <template #append>
                    <el-button @click="addCustomCourse">添加</el-button>
                  </template>
                </el-input>
              </el-form-item>
            </div>

            <div v-else-if="currentStep === 1" key="step1" class="step-pane">
              <el-form-item prop="learning_goal">
                <template #label>
                  <div class="custom-label">
                    <span>近期的核心学习诉求</span><span class="required-star">*</span>
                  </div>
                </template>
                <div class="goal-cards-grid">
                  <div 
                    v-for="goal in PRESET_GOALS" 
                    :key="goal"
                    class="goal-card"
                    :class="{ active: onboardingForm.learning_goal === goal }"
                    @click="setSingleValue('learning_goal', goal)"
                  >
                    <div class="goal-radio">
                      <div class="radio-inner"></div>
                    </div>
                    <span>{{ goal }}</span>
                  </div>
                </div>
                <el-input 
                  v-model="customInputs.learning_goal" 
                  placeholder="其它诉求？请用一句话描述" 
                  class="custom-inline-input mt-4"
                  @input="setSingleValue('learning_goal', customInputs.learning_goal)"
                />
              </el-form-item>
            </div>

            <div v-else-if="currentStep === 2" key="step2" class="step-pane">
              
              <div class="form-row-grid">
                <el-form-item prop="education_level">
                  <template #label>
                    <div class="custom-label">
                      <span>学历阶段</span><span class="required-star">*</span>
                    </div>
                  </template>
                  <div class="tag-group">
                    <div 
                      v-for="level in PRESET_EDUCATION_LEVELS" 
                      :key="level"
                      class="selectable-tag"
                      :class="{ active: onboardingForm.education_level === level }"
                      @click="setSingleValue('education_level', level)"
                    >
                      {{ level }}
                    </div>
                  </div>
                </el-form-item>

                <el-form-item prop="school_level">
                  <template #label>
                    <div class="custom-label">
                      <span>院校类别 (选填)</span>
                    </div>
                  </template>
                  <div class="tag-group">
                    <div 
                      v-for="level in PRESET_SCHOOL_LEVELS" 
                      :key="level"
                      class="selectable-tag"
                      :class="{ active: onboardingForm.school_level === level }"
                      @click="setSingleValue('school_level', level)"
                    >
                      {{ level }}
                    </div>
                  </div>
                </el-form-item>
              </div>

              <el-form-item prop="grade">
                <template #label>
                  <div class="custom-label">
                    <span>当前年级</span><span class="required-star">*</span>
                  </div>
                </template>
                <div class="tag-group">
                  <div 
                    v-for="grade in PRESET_GRADES" 
                    :key="grade"
                    class="selectable-tag"
                    :class="{ active: onboardingForm.grade === grade }"
                    @click="setSingleValue('grade', grade)"
                  >
                    {{ grade }}
                  </div>
                </div>
              </el-form-item>

              <el-form-item label="就读院校名称 (选填)" prop="school">
                <el-input 
                  v-model="onboardingForm.school" 
                  placeholder="例如：北京大学、清华大学" 
                  class="custom-inline-input"
                />
              </el-form-item>

              <el-form-item label="常用编程语言 (选填)" prop="preferred_language">
                <div class="tag-group">
                  <div 
                    v-for="language in PRESET_LANGUAGES" 
                    :key="language"
                    class="selectable-tag"
                    :class="{ active: onboardingForm.preferred_language === language }"
                    @click="setSingleValue('preferred_language', language)"
                  >
                    {{ language }}
                  </div>
                </div>
              </el-form-item>

            </div>

          </transition>
        </el-form>
      </main>

      <footer class="onboarding-footer">
        <div class="footer-left">
          <el-button v-if="currentStep > 0" class="nav-btn prev-btn" @click="currentStep--">
            返回
          </el-button>
          <el-button v-else link class="skip-btn" @click="skipOnboarding">
            暂不完善，跳过
          </el-button>
        </div>
        
        <div class="footer-right">
          <el-button 
            v-if="currentStep < 2" 
            type="primary" 
            class="nav-btn next-btn" 
            @click="nextStep"
          >
            下一步
          </el-button>
          <el-button
            v-else
            type="primary"
            class="nav-btn finish-btn"
            :loading="submitting"
            @click="submitForm(onboardingFormRef)"
          >
            完成创建 <el-icon class="ml-1"><MagicStick /></el-icon>
          </el-button>
        </div>
      </footer>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getProfileOnboarding, updateProfileOnboarding } from '@/api/ai'
import type { ProfileOnboardingUpdate, StudentProfileData } from '@/api/ai'
import { Close, MagicStick } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'success'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const submitting = ref(false)
const currentStep = ref(0)
const onboardingFormRef = ref<FormInstance>()

const STEP_META = [
  {
    title: '确立专业与课程',
    helper: '点击标签快速选择，或在输入框中补充',
  },
  {
    title: '设定核心学习目标',
    helper: '告诉我们近期的诉求，系统将为你调整资源策略',
  },
  {
    title: '补充学术背景',
    helper: '了解你的基础，提供难度更匹配的讲解',
  },
]

const currentStepMeta = computed(() => STEP_META[currentStep.value] ?? STEP_META[0]!)

// 预设数据 (可平铺展示的长度)
const PRESET_MAJORS = ['计算机科学', '软件工程', '人工智能', '数据科学', '网络安全', '电子信息', '自动化']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库原理', '算法分析', '机器学习']
const PRESET_GOALS = ['期末考试冲刺', '完成课设/毕设', '大厂求职/面试', '考研初复试准备', '零基础快速入门', '日常系统学习进阶']
const PRESET_EDUCATION_LEVELS = ['专科', '本科', '硕士', '博士']
const PRESET_GRADES = ['大一', '大二', '大三', '大四', '研一', '研二']
const PRESET_SCHOOL_LEVELS = ['985', '211', '双一流', '普通本科', '高职高专']
const PRESET_LANGUAGES = ['Python', 'Java', 'C++', 'Go', 'JavaScript']

const onboardingForm = reactive<ProfileOnboardingUpdate>({
  education_level: '',
  grade: '',
  major: '',
  courses: [],
  learning_goal: '',
  school: '',
  school_level: '',
  preferred_language: '',
})

// 用于绑定自定义输入的内容
const customInputs = reactive({
  major: '',
  learning_goal: '',
  course: ''
})
const customAddedCourses = ref<string[]>([])

const onboardingRules: FormRules<ProfileOnboardingUpdate> = {
  education_level: [{ required: true, message: '请选择学历阶段', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  major: [{ required: true, message: '请选择或输入专业', trigger: 'change' }],
  courses: [{ required: true, type: 'array', min: 1, message: '请至少选择一门课程', trigger: 'change' }],
  learning_goal: [{ required: true, message: '请选择或输入当前学习目标', trigger: 'change' }],
}

// 标签单选逻辑
const setSingleValue = (field: keyof ProfileOnboardingUpdate, value: string) => {
  if (onboardingForm[field] === value) {
    ;(onboardingForm[field] as string) = ''
  } else {
    ;(onboardingForm[field] as string) = value
  }
  // 同步清除对应的自定义输入框内容（如果是预设标签）
  if (field === 'major' && PRESET_MAJORS.includes(value)) customInputs.major = ''
  if (field === 'learning_goal' && PRESET_GOALS.includes(value)) customInputs.learning_goal = ''
  
  onboardingFormRef.value?.validateField(field).catch(() => {})
}

// 标签多选逻辑
const toggleMultiValue = (field: 'courses', value: string) => {
  const index = onboardingForm[field].indexOf(value)
  if (index > -1) {
    onboardingForm[field].splice(index, 1)
    const customIdx = customAddedCourses.value.indexOf(value)
    if (customIdx > -1) customAddedCourses.value.splice(customIdx, 1)
  } else {
    onboardingForm[field].push(value)
  }
  onboardingFormRef.value?.validateField(field).catch(() => {})
}

// 添加自定义课程
const addCustomCourse = () => {
  const course = customInputs.course.trim()
  if (course && !onboardingForm.courses.includes(course)) {
    onboardingForm.courses.push(course)
    if (!PRESET_COURSES.includes(course) && !customAddedCourses.value.includes(course)) {
      customAddedCourses.value.push(course)
    }
  }
  customInputs.course = ''
  onboardingFormRef.value?.validateField('courses').catch(() => {})
}

const skipOnboarding = () => {
  visible.value = false
  emit('success')
}

const nextStep = async () => {
  if (!onboardingFormRef.value) return
  const fieldsByStep = [
    ['major', 'courses'],
    ['learning_goal'],
    ['education_level', 'grade']
  ]
  try {
    await onboardingFormRef.value.validateField(fieldsByStep[currentStep.value])
    currentStep.value++
  } catch {
    // 拦截验证错误，让 Element Plus 自己渲染红字
  }
}

const fillForm = (payload: Partial<ProfileOnboardingUpdate> | StudentProfileData) => {
  onboardingForm.education_level = payload.education_level || ''
  onboardingForm.grade = payload.grade || ''
  onboardingForm.major = payload.major || ''
  onboardingForm.courses = Array.isArray(payload.courses) ? payload.courses : []
  onboardingForm.learning_goal = payload.learning_goal || ''
  onboardingForm.school = payload.school || ''
  onboardingForm.school_level = payload.school_level || ''
  onboardingForm.preferred_language = payload.preferred_language || ''
}

const loadStatus = async () => {
  try {
    const res = await getProfileOnboarding()
    fillForm(res.data.data.student_profile)
    if (res.data.data.profile_initialized) {
      visible.value = false
    }
  } catch (e) {
    console.error('Failed to load onboarding status', e)
  }
}

const submitForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  const valid = await formEl.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await updateProfileOnboarding({
      ...onboardingForm,
      courses: onboardingForm.courses.map((course) => course.trim()).filter(Boolean),
      school: onboardingForm.school || null,
      school_level: onboardingForm.school_level || null,
      preferred_language: onboardingForm.preferred_language || null,
    })
    visible.value = false
    ElMessage.success('档案初始化完成，开始体验吧！')
    emit('success')
  } catch (e) {
    console.error('Failed to submit onboarding', e)
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadStatus()
})
</script>

<style scoped>
/* =========== Element Dialog 覆盖样式 =========== */
.pure-form-onboarding-dialog :deep(.el-dialog__header) {
  display: none;
}
.pure-form-onboarding-dialog :deep(.el-dialog__body) {
  padding: 0;
}
.pure-form-onboarding-dialog :deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  background: transparent;
  box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.2);
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  margin: auto;
}

/* =========== 整体容器 =========== */
.onboarding-wrapper {
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  min-height: 440px; /* 去掉头部后，减少最小高度限制 */
}

/* =========== 主体内容与表单 =========== */
.onboarding-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 40px 48px 16px; /* 增加顶部 Padding */
  min-width: 0;
}

.step-meta-box {
  margin-bottom: 28px;
}

.step-meta-box h2 {
  font-size: 1.4rem;
  font-weight: 800;
  color: #0F172A;
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}

.step-meta-box p {
  font-size: 0.9rem;
  color: #64748B;
  margin: 0;
  line-height: 1.5;
}

.tag-form {
  flex: 1;
  min-height: 0;
}

.tag-form .custom-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  color: #334155;
  font-size: 0.88rem;
}

.tag-form .required-star {
  color: #EF4444;
}

.tag-form .el-form-item {
  margin-bottom: 24px;
}

.form-row-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 20px;
}

/* =========== 标签系统样式 =========== */
.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}

.selectable-tag {
  padding: 8px 16px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  color: #475569;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  display: inline-flex;
  align-items: center;
}

.selectable-tag:hover {
  background: #F1F5F9;
  color: #1E293B;
  border-color: #CBD5E1;
}

.selectable-tag.active {
  background: #EFF6FF;
  border-color: #3B82F6;
  color: #2563EB;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}

.custom-added-tag {
  padding-right: 12px;
}

/* 目标卡片样式 */
.goal-cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 4px;
}

.goal-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.goal-card:hover {
  border-color: #CBD5E1;
  background: #F8FAFC;
}

.goal-card.active {
  border-color: #3B82F6;
  background: #EFF6FF;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.goal-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #CBD5E1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.goal-card.active .goal-radio {
  border-color: #3B82F6;
}

.radio-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #3B82F6;
  opacity: 0;
  transform: scale(0.5);
  transition: all 0.2s;
}

.goal-card.active .radio-inner {
  opacity: 1;
  transform: scale(1);
}

.goal-card span {
  font-size: 0.9rem;
  color: #334155;
  font-weight: 500;
}
.goal-card.active span {
  color: #1E293B;
  font-weight: 600;
}

/* 输入框定制 */
.custom-inline-input :deep(.el-input__wrapper) {
  box-shadow: none !important;
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  border-radius: 8px !important;
  min-height: 42px;
  padding: 0 16px !important;
}

.custom-inline-input :deep(.el-input__inner) {
  font-size: 0.9rem;
}

.custom-inline-input :deep(.el-input__wrapper.is-focus) {
  border-color: #3B82F6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 16px; }
.ml-1 { margin-left: 4px; }

/* =========== 底部操作区 =========== */
.onboarding-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 48px 32px;
  background: #FFFFFF;
}

.nav-btn {
  height: 42px;
  padding: 0 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.prev-btn {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  color: #475569;
}

.prev-btn:hover {
  background: #F8FAFC;
  color: #0F172A;
  border-color: #CBD5E1;
}

.next-btn, .finish-btn {
  background: #0F172A;
  border: none;
  color: #FFFFFF;
}

.next-btn:hover, .finish-btn:hover {
  background: #3B82F6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
}

.skip-btn {
  color: #94A3B8;
  font-weight: 500;
  font-size: 0.9rem;
}

.skip-btn:hover {
  color: #64748B;
}

/* 过渡动画 */
.fade-slide-up-enter-active,
.fade-slide-up-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.fade-slide-up-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.fade-slide-up-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 响应式调整 */
@media (max-width: 640px) {
  .onboarding-main { padding: 32px 24px 16px; }
  .onboarding-footer { padding: 16px 24px 24px; }
  .form-row-grid, .goal-cards-grid { grid-template-columns: 1fr; gap: 0; }
  .pure-form-onboarding-dialog :deep(.el-dialog) { width: 92% !important; }
}
</style>