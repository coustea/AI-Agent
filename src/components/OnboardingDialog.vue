<template>
  <el-dialog
      v-model="visible"
      width="600px"
      :show-close="true"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="custom-onboarding-dialog"
      align-center
  >
    <div class="onboarding-wrapper">

      <header class="onboarding-header">
        <div class="header-icon-box">
          <el-icon><Avatar /></el-icon>
          <div class="icon-sparkle">✨</div>
        </div>
        <div class="header-text">
          <h2>欢迎来到学枢平台 👋</h2>
          <p>请告诉我们你的专业方向和当前学习课程（可多选），<br>以便为你定制个性化学习路径和资源推荐。</p>
        </div>
      </header>

      <main class="onboarding-main">

        <div class="section-card">
          <div class="section-title-row">
            <div class="step-badge">1</div>
            <h3 class="section-title">选择主修专业 <span class="required-star">*</span></h3>
          </div>
          <div class="tag-group">
            <div
                v-for="major in PRESET_MAJORS"
                :key="major"
                class="selectable-tag"
                :class="{ active: onboardingForm.major === major || (major === '其他专业' && isCustomMajor) }"
                @click="handleMajorClick(major)"
            >
              {{ major }}
              <div v-if="onboardingForm.major === major || (major === '其他专业' && isCustomMajor)" class="check-circle">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>

          <div v-if="isCustomMajor" class="custom-input-wrap mt-2">
            <el-input
                v-model="customInputs.major"
                placeholder="请输入您的专业名称"
                class="custom-inline-input"
                @input="syncCustomMajor"
            />
          </div>
        </div>

        <div class="section-card">
          <div class="section-title-row">
            <div class="step-badge">2</div>
            <h3 class="section-title">选择当前课程（可多选） <span class="required-star">*</span></h3>
          </div>
          <div class="tag-group">
            <div
                v-for="course in PRESET_COURSES"
                :key="course"
                class="selectable-tag"
                :class="{ active: onboardingForm.courses.includes(course) }"
                @click="toggleMultiValue('courses', course)"
            >
              {{ course }}
              <div v-if="onboardingForm.courses.includes(course)" class="check-circle">
                <el-icon><Check /></el-icon>
              </div>
            </div>
            <div
                v-for="customCourse in customAddedCourses"
                :key="customCourse"
                class="selectable-tag active"
                @click="toggleMultiValue('courses', customCourse)"
            >
              {{ customCourse }}
              <div class="check-circle">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>
          <div class="custom-input-wrap mt-2">
            <el-input
                v-model="customInputs.course"
                placeholder="输入其他课程名称，按回车添加"
                class="custom-inline-input"
                @keyup.enter="addCustomCourse"
            >
              <template #append>
                <el-button @click="addCustomCourse">添加</el-button>
              </template>
            </el-input>
          </div>
        </div>

      </main>

      <footer class="onboarding-footer">
        <el-button class="skip-btn-outline" @click="skipOnboarding">
          稍后完善
        </el-button>

        <el-button
            type="primary"
            class="start-btn"
            :loading="submitting"
            @click="submitForm"
        >
          开始学习之旅 <el-icon class="ml-1"><Right /></el-icon>
        </el-button>
      </footer>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getProfileOnboarding, updateProfileOnboarding } from '@/api/ai'
import type { ProfileOnboardingUpdate, StudentProfileData } from '@/api/ai'
import { Check, Avatar, Right } from '@element-plus/icons-vue'

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
const isCustomMajor = ref(false) // 标记是否处于“其他专业”编辑状态

const PRESET_MAJORS = ['计算机科学', '软件工程', '人工智能', '数据科学', '网络安全', '电子信息', '其他专业']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库原理', '算法分析', '机器学习']

const onboardingForm = reactive<ProfileOnboardingUpdate>({
  education_level: '本科',
  grade: '大二',
  major: '',
  courses: [],
  learning_goal: '日常系统学习进阶',
  school: '',
  school_level: '',
  preferred_language: '',
})

const customInputs = reactive({
  course: '',
  major: ''
})
const customAddedCourses = ref<string[]>([])

// 专业选择逻辑
const handleMajorClick = (major: string) => {
  if (major === '其他专业') {
    isCustomMajor.value = true
    onboardingForm.major = customInputs.major // 使用输入框的内容
  } else {
    isCustomMajor.value = false
    onboardingForm.major = major
  }
}

// 同步自定义专业输入
const syncCustomMajor = () => {
  onboardingForm.major = customInputs.major
}

// 课程多选逻辑
const toggleMultiValue = (field: 'courses', value: string) => {
  const index = onboardingForm[field].indexOf(value)
  if (index > -1) {
    onboardingForm[field].splice(index, 1)
    const customIdx = customAddedCourses.value.indexOf(value)
    if (customIdx > -1) customAddedCourses.value.splice(customIdx, 1)
  } else {
    onboardingForm[field].push(value)
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

const skipOnboarding = () => {
  visible.value = false
  emit('success')
}

const loadStatus = async () => {
  try {
    const res = await getProfileOnboarding()
    const profile = res.data.data.student_profile
    if (profile.major) {
      if (!PRESET_MAJORS.includes(profile.major)) {
        isCustomMajor.value = true
        customInputs.major = profile.major
      }
      onboardingForm.major = profile.major
    }
    if (profile.courses) onboardingForm.courses = profile.courses

    // 测试注释掉if这段：
    // if (res.data.data.profile_initialized) {
    //   visible.value = false
    // }
  } catch (e) {
    console.error('Failed to load status', e)
  }
}

const submitForm = async () => {
  if (!onboardingForm.major || (isCustomMajor.value && !customInputs.major.trim())) {
    ElMessage.warning('请填写或选择主修专业')
    return
  }
  if (onboardingForm.courses.length === 0) {
    ElMessage.warning('请至少选择一门课程')
    return
  }

  submitting.value = true
  try {
    await updateProfileOnboarding(onboardingForm)
    visible.value = false
    ElMessage.success('档案初始化完成')
    emit('success')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => { loadStatus() })
</script>

<style scoped>
/* 弹窗基础样式覆盖 */
.custom-onboarding-dialog :deep(.el-dialog__header) { display: none; }
.custom-onboarding-dialog :deep(.el-dialog__body) { padding: 0; }
.custom-onboarding-dialog :deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  background: #FFFFFF;
  box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.15);
}

.onboarding-wrapper { display: flex; flex-direction: column; }

/* 头部 */
.onboarding-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 32px 16px;
}
.header-icon-box {
  width: 52px; height: 52px;
  background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  position: relative; font-size: 1.6rem; color: #4F46E5;
}
.icon-sparkle { position: absolute; top: -4px; right: -4px; font-size: 0.9rem; }
.header-text h2 { font-size: 1.35rem; font-weight: 800; color: #0F172A; margin: 0 0 4px; }
.header-text p { font-size: 0.85rem; color: #64748B; margin: 0; line-height: 1.4; }

/* 主体 */
.onboarding-main { display: flex; flex-direction: column; padding: 0 32px; gap: 12px; }
.section-card {
  border: 1px solid #F1F5F9;
  border-radius: 12px;
  padding: 16px 20px;
}
.section-title-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.step-badge {
  width: 20px; height: 20px; background-color: #3B82F6; color: #FFF;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: bold;
}
.section-title { margin: 0; font-size: 0.95rem; font-weight: 700; color: #1E293B; }
.required-star { color: #EF4444; }

/* 标签样式 */
.tag-group { display: flex; flex-wrap: wrap; gap: 10px; margin-left: 30px; }
.selectable-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; background: #FFF; border: 1px solid #E2E8F0;
  border-radius: 6px; color: #475569; font-size: 0.85rem;
  cursor: pointer; transition: all 0.2s; user-select: none;
}
.selectable-tag.active {
  background: #F4F8FF; border-color: #3B82F6; color: #2563EB; font-weight: 600;
}
.check-circle {
  width: 14px; height: 14px; background: #3B82F6; color: #FFF;
  border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px;
}

/* 输入框定制 */
.custom-input-wrap { margin-left: 30px; }
.custom-inline-input :deep(.el-input__wrapper) {
  box-shadow: none !important; border: 1px solid #E2E8F0 !important;
  border-radius: 6px !important; min-height: 36px;
}
.custom-inline-input :deep(.el-input-group__append) {
  background: #F8FAFC; border: 1px solid #E2E8F0; border-left: none;
  border-radius: 0 6px 6px 0; padding: 0 16px;
}

/* 底部按钮 */
.onboarding-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 32px 24px;
}

/* 稍后完善按钮 - 轮廓样式 */
.skip-btn-outline {
  border: 1px solid #E2E8F0 !important;
  background-color: transparent !important;
  color: #64748B !important;
  height: 40px;
  padding: 0 20px;
  border-radius: 8px;
  font-weight: 500;
}
.skip-btn-outline:hover {
  border-color: #3B82F6 !important;
  color: #3B82F6 !important;
  background-color: #F8FAFC !important;
}

.start-btn {
  background: #3B82F6; border: none; color: #FFF;
  height: 40px; padding: 0 24px; border-radius: 8px;
  font-size: 0.9rem; font-weight: 600;
}
.start-btn:hover { background: #2563EB; transform: translateY(-1px); }

.mt-2 { margin-top: 10px; }
.ml-1 { margin-left: 6px; }
</style>