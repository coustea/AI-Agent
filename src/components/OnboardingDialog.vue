<template>
  <el-dialog
      v-model="visible"
      width="580px"
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

        <div class="section-card">
          <div class="section-title-row">
            <div class="step-badge">3</div>
            <h3 class="section-title">学校与阶段</h3>
          </div>
          <div class="custom-input-wrap form-grid-2x2 mt-2">

            <div class="grid-item">
              <label class="sub-label">院校 <span class="optional-text">（选填）</span></label>
              <el-autocomplete
                  v-model="onboardingForm.school"
                  :fetch-suggestions="querySearchSchool"
                  placeholder="可以直接输入或搜索"
                  clearable
                  class="custom-inline-input w-full"
                  @select="handleSchoolSelect"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
                <template #default="{ item }">
                  <span>{{ item.value }}</span>
                  <span v-if="item.level" class="school-level-tag">{{ item.level }}</span>
                </template>
              </el-autocomplete>
            </div>

            <div class="grid-item">
              <label class="sub-label">学历层次 <span class="required-star">*</span></label>
              <el-select v-model="onboardingForm.education_level" placeholder="请选择学历层次" class="custom-inline-input w-full" filterable>
                <el-option v-for="level in PRESET_EDUCATION_LEVELS" :key="level" :label="level" :value="level" />
              </el-select>
            </div>

            <div class="grid-item">
              <label class="sub-label">年级 <span class="required-star">*</span></label>
              <el-select v-model="onboardingForm.grade" filterable allow-create default-first-option clearable placeholder="请选择年级" class="custom-inline-input w-full">
                <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
              </el-select>
            </div>

            <div class="grid-item">
              <label class="sub-label">常用编程语言 <span class="optional-text">（选填）</span></label>
              <el-select v-model="onboardingForm.preferred_language" filterable allow-create default-first-option clearable placeholder="请选择语言" class="custom-inline-input w-full">
                <el-option v-for="language in PRESET_LANGUAGES" :key="language" :label="language" :value="language" />
              </el-select>
            </div>

          </div>
        </div>

      </main>

      <footer class="onboarding-footer">
        <div class="footer-left-actions">
          <el-button class="skip-btn-outline" @click="skipOnboarding">
            <el-icon style="margin-right: 4px; font-size: 1rem;"><Clock /></el-icon>稍后完善
          </el-button>
          <el-button class="never-show-btn-outline" @click="disableOnboarding">
            <el-icon style="margin-right: 4px; font-size: 1rem;"><CircleClose /></el-icon>不再弹出
          </el-button>
        </div>

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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getProfileOnboarding, updateProfileOnboarding, searchSchools } from '@/api/ai'
import type { ProfileOnboardingUpdate, SchoolItem } from '@/api/ai'
// 更改点：导入了 CircleClose 图标
import { Check, Avatar, Right, Search, Clock, CircleClose } from '@element-plus/icons-vue'

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
const isCustomMajor = ref(false)

const PRESET_MAJORS = ['计算机科学', '软件工程', '人工智能', '数据科学', '网络安全', '电子信息', '其他专业']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库原理', '算法分析', '机器学习']
const PRESET_EDUCATION_LEVELS = ['高职/专科', '本科', '研究生']
const PRESET_GRADES = [
  '大一', '大二', '大三', '大四', '大五',
  '研一', '研二', '研三',
  '博一', '博二', '博三',
  '高职一年级', '高职二年级', '高职三年级'
]
const PRESET_LANGUAGES = [
  'Python', 'Java', 'C/C++', 'Go', 'Rust', 'JavaScript', 'TypeScript',
  'SQL', 'Shell', 'Kotlin', 'Swift', 'PHP', 'HTML/CSS'
]

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

const profileSchoolOptions = ref<SchoolItem[]>([])

const querySearchSchool = async (queryString: string, cb: any) => {
  if (!queryString) {
    cb([]);
    return;
  }
  try {
    const res = await searchSchools(queryString, 20);
    profileSchoolOptions.value = res.data.data;
    const options = res.data.data.map((school: any) => ({
      value: school.name,
      level: school.level
    }));
    cb(options);
  } catch (e) {
    cb([]);
  }
}

const handleSchoolSelect = (item: any) => {
  onboardingForm.school_level = item.level || '';
}

watch(() => onboardingForm.school, (newVal) => {
  if (!newVal) {
    onboardingForm.school_level = '';
    return;
  }
  const matched = profileSchoolOptions.value.find((s: any) => s.name === newVal);
  onboardingForm.school_level = matched ? (matched.level || '') : '';
})

// 专业选择逻辑
const handleMajorClick = (major: string) => {
  if (major === '其他专业') {
    if (isCustomMajor.value) {
      isCustomMajor.value = false
      onboardingForm.major = ''
    } else {
      isCustomMajor.value = true
      onboardingForm.major = customInputs.major
    }
  } else {
    if (onboardingForm.major === major && !isCustomMajor.value) {
      onboardingForm.major = ''
    } else {
      isCustomMajor.value = false
      onboardingForm.major = major
    }
  }
}

const syncCustomMajor = () => {
  onboardingForm.major = customInputs.major
}

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

// 写入 localStorage，并关闭弹窗
const disableOnboarding = () => {
  localStorage.setItem('hide_onboarding_dialog', 'true')
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

    if (profile.education_level) onboardingForm.education_level = profile.education_level
    if (profile.grade) onboardingForm.grade = profile.grade
    if (profile.preferred_language) onboardingForm.preferred_language = profile.preferred_language
    if (profile.school) {
      onboardingForm.school = profile.school
      onboardingForm.school_level = profile.school_level || ''
    }
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
  if (!onboardingForm.education_level) {
    ElMessage.warning('请选择学历层次')
    return
  }
  if (!onboardingForm.grade) {
    ElMessage.warning('请选择就读年级')
    return
  }

  submitting.value = true
  try {
    await updateProfileOnboarding({
      ...onboardingForm,
      school: onboardingForm.school || null,
      school_level: onboardingForm.school_level || null,
      preferred_language: onboardingForm.preferred_language || null,
    })
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
.custom-onboarding-dialog :deep(.el-dialog__header) { display: none; }
.custom-onboarding-dialog :deep(.el-dialog__body) { padding: 0; }
.custom-onboarding-dialog :deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
  background: #FFFFFF;
  box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.15);
}

.onboarding-wrapper { display: flex; flex-direction: column; }

/* 头部优化 */
.onboarding-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px 12px;
}
.header-icon-box {
  width: 44px; height: 44px;
  background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  position: relative; font-size: 1.4rem; color: #4F46E5;
}
.icon-sparkle { position: absolute; top: -4px; right: -4px; font-size: 0.8rem; }
.header-text h2 { font-size: 1.15rem; font-weight: 800; color: #0F172A; margin: 0 0 2px; }
.header-text p { font-size: 0.75rem; color: #64748B; margin: 0; line-height: 1.4; }

/* 主体优化 */
.onboarding-main { display: flex; flex-direction: column; padding: 0 24px; gap: 8px; }
.section-card {
  border: 1px solid #F1F5F9;
  border-radius: 10px;
  padding: 12px 16px;
}
.section-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }

/* ======== 统一的步骤徽章 ======== */
.step-badge {
  width: 18px; height: 18px; background-color: #3B82F6; color: #FFF;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: bold;
}
.section-title { margin: 0; font-size: 0.88rem; font-weight: 700; color: #1E293B; }
.required-star { color: #EF4444; margin-left: 2px; }
.optional-text { font-size: 0.75rem; color: #94A3B8; font-weight: normal; }

/* 标签样式 */
.tag-group { display: flex; flex-wrap: wrap; gap: 8px; margin-left: 26px; }
.selectable-tag {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 12px; background: #FFF; border: 1px solid #E2E8F0;
  border-radius: 6px; color: #475569; font-size: 0.8rem;
  cursor: pointer; transition: all 0.2s; user-select: none;
}
.selectable-tag.active {
  background: #F4F8FF; border-color: #3B82F6; color: #2563EB; font-weight: 600;
}
.check-circle {
  width: 12px; height: 12px; background: #3B82F6; color: #FFF;
  border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 8px;
}

/* 输入框定制与网格对齐 */
.custom-input-wrap { margin-left: 26px; }
.custom-inline-input :deep(.el-input__wrapper),
.custom-inline-input :deep(.el-select__wrapper) {
  box-shadow: none !important; border: 1px solid #E2E8F0 !important;
  border-radius: 6px !important; min-height: 32px !important;
}
.custom-inline-input :deep(.el-input__inner) { font-size: 0.8rem; }
.custom-inline-input :deep(.el-input-group__append) {
  background: #F8FAFC; border: 1px solid #E2E8F0; border-left: none;
  border-radius: 0 6px 6px 0; padding: 0 12px;
}

/* 2x2 网格布局 */
.form-grid-2x2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
}
.grid-item { display: flex; flex-direction: column; }
.sub-label {
  font-size: 0.75rem; color: #475569; margin-bottom: 4px; font-weight: 600;
}

.school-level-tag { margin-left: 6px; font-size: 0.65rem; color: #64748B; background: #F1F5F9; padding: 2px 6px; border-radius: 4px; }
.w-full { width: 100%; }

/* 底部按钮 */
.onboarding-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 24px 20px;
}

.footer-left-actions { display: flex; align-items: center; gap: 12px; }

/* ======== 修改点：变为蓝色轮廓和文字 ======== */
.skip-btn-outline {
  border: 1px solid #3B82F6 !important;
  background-color: transparent !important;
  color: #3B82F6 !important;
  height: 36px;
  padding: 0 16px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  transition: all 0.2s;
}
.skip-btn-outline:hover {
  background-color: #EFF6FF !important;
}

/* 轮廓按钮样式 (不再弹出 保持原有低调样式) */
.never-show-btn-outline {
  border: 1px solid #E2E8F0 !important;
  background-color: transparent !important;
  color: #94A3B8 !important;
  height: 36px;
  padding: 0 16px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.2s;
}
.never-show-btn-outline:hover {
  border-color: #CBD5E1 !important;
  color: #64748B !important;
  background-color: #F8FAFC !important;
}

.start-btn {
  background: #3B82F6; border: none; color: #FFF;
  height: 36px; padding: 0 20px; border-radius: 6px;
  font-size: 0.85rem; font-weight: 600;
}
.start-btn:hover { background: #2563EB; transform: translateY(-1px); }

.mt-2 { margin-top: 8px; }
.ml-1 { margin-left: 4px; }

@media (max-width: 480px) {
  .form-grid-2x2 { grid-template-columns: 1fr; gap: 8px; }
}
</style>