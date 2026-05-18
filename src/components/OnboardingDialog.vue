<template>
  <el-dialog
      v-model="visible"
      width="680px"
      :show-close="false"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="custom-onboarding-dialog"
      align-center
  >
    <div class="onboarding-wrapper">
      <header class="onboarding-header">
        <h2 class="header-title">欢迎来到学枢</h2>

        <div class="custom-step-indicator">
          <div class="step-item" :class="{ 'is-active': currentStep >= 1 }">
            <div class="step-icon"><el-icon><Check /></el-icon></div>
            <div class="step-text">基础档案</div>
          </div>
          <div class="step-line" :class="{ 'is-active': currentStep === 2 }"></div>
          <div class="step-item" :class="{ 'is-active': currentStep === 2 }">
            <div class="step-icon">2</div>
            <div class="step-text">学校阶段</div>
          </div>
        </div>
      </header>

      <main class="onboarding-main">
        <div v-show="currentStep === 1" class="step-content">
          <div class="section-block">
            <h3 class="section-title">1. 选择主修专业 <span class="required">*</span></h3>
            <div class="tag-group">
              <div
                  v-for="major in PRESET_MAJORS"
                  :key="major"
                  class="selectable-tag"
                  :class="{ active: onboardingForm.major === major || (major === '其他专业' && isCustomMajor) }"
                  @click="handleMajorClick(major)"
              >
                {{ major }}
              </div>
            </div>
            <div v-if="isCustomMajor" class="custom-input-wrap mt-3">
              <el-input
                  v-model="customInputs.major"
                  placeholder="请输入您的专业名称"
                  class="custom-input"
                  @input="syncCustomMajor"
              />
            </div>
          </div>

          <div class="section-block mt-4">
            <h3 class="section-title">2. 选择当前课程 (可多选) <span class="required">*</span></h3>
            <div class="tag-group">
              <div
                  v-for="course in PRESET_COURSES"
                  :key="course"
                  class="selectable-tag"
                  :class="{ active: onboardingForm.courses.includes(course) }"
                  @click="toggleCourse(course)"
              >
                {{ course }}
              </div>
              <div
                  v-for="customCourse in customAddedCourses"
                  :key="customCourse"
                  class="selectable-tag active"
                  @click="toggleCourse(customCourse)"
              >
                {{ customCourse }}
              </div>
            </div>
            <div class="custom-input-wrap add-course-wrap mt-3">
              <el-input
                  v-model="customInputs.course"
                  placeholder="输入其他课程名称，按回车添加"
                  class="custom-input add-course-input"
                  @keyup.enter="addCustomCourse"
              >
                <template #append>
                  <el-button @click="addCustomCourse" class="add-btn">添加</el-button>
                </template>
              </el-input>
            </div>
          </div>
        </div>

        <div v-show="currentStep === 2" class="step-content">
          <div class="section-block">
            <h3 class="section-title">3. 学校与阶段</h3>
            <div class="form-grid-2x2 mt-3">
              <div class="grid-item">
                <label class="field-label">院校 <span class="required">*</span></label>
                <el-autocomplete
                    v-model="onboardingForm.school"
                    :fetch-suggestions="querySearchSchool"
                    placeholder="可以直接输入或搜索"
                    clearable
                    class="custom-input w-full"
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
                <label class="field-label">院校层次 <span class="required">*</span></label>
                <el-select v-model="onboardingForm.school_level" filterable allow-create default-first-option clearable placeholder="请选择或从院校带出" class="custom-input w-full">
                  <el-option v-for="level in PRESET_SCHOOL_LEVELS" :key="level" :label="level" :value="level" />
                </el-select>
              </div>

              <div class="grid-item">
                <label class="field-label">学历层次 <span class="required">*</span></label>
                <el-select v-model="onboardingForm.education_level" placeholder="请选择学历层次" class="custom-input w-full" filterable>
                  <el-option v-for="level in PRESET_EDUCATION_LEVELS" :key="level" :label="level" :value="level" />
                </el-select>
              </div>

              <div class="grid-item">
                <label class="field-label">年级 <span class="required">*</span></label>
                <el-select v-model="onboardingForm.grade" filterable allow-create default-first-option clearable placeholder="请选择年级" class="custom-input w-full">
                  <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
                </el-select>
              </div>

              <div class="grid-item">
                <label class="field-label">当前学习目标 <span class="required">*</span></label>
                <el-select v-model="onboardingForm.learning_goal" filterable allow-create default-first-option clearable placeholder="请选择或输入" class="custom-input w-full">
                  <el-option v-for="goal in PRESET_GOALS" :key="goal" :label="goal" :value="goal" />
                </el-select>
              </div>

              <div class="grid-item">
                <label class="field-label">常用编程语言 <span class="optional">（选填）</span></label>
                <el-select v-model="onboardingForm.preferred_language" filterable allow-create default-first-option clearable placeholder="请选择语言" class="custom-input w-full">
                  <el-option v-for="language in PRESET_LANGUAGES" :key="language" :label="language" :value="language" />
                </el-select>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer class="onboarding-footer">
        <div class="footer-left">
          <el-button v-if="currentStep === 2" class="nav-btn prev-btn" @click="currentStep = 1">
            <el-icon class="mr-1"><ArrowLeft /></el-icon> 上一步
          </el-button>

          <div v-else class="outline-links">
            <el-button class="outline-btn btn-skip" @click="skipOnboarding">稍后完善</el-button>
            <el-button class="outline-btn btn-never" @click="disableOnboarding">不再弹出</el-button>
          </div>

          <el-button v-if="currentStep === 2" class="outline-btn btn-skip ml-4" @click="skipOnboarding">
            稍后完善
          </el-button>
        </div>

        <div class="footer-right">
          <el-button
              v-if="currentStep === 1"
              class="action-btn next-btn"
              @click="nextStep"
          >
            下一步 <el-icon class="ml-1"><ArrowRight /></el-icon>
          </el-button>
          <el-button
              v-if="currentStep === 2"
              class="action-btn finish-btn"
              :loading="submitting"
              @click="submitForm"
          >
            完成
          </el-button>
        </div>
      </footer>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getProfileOnboarding, updateProfileOnboarding, searchSchools } from '@/api/ai'
import type { ProfileOnboardingUpdate, SchoolItem } from '@/api/ai'
import { Check, Search, ArrowRight, ArrowLeft } from '@element-plus/icons-vue'

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

const currentStep = ref(1)
const submitting = ref(false)
const isCustomMajor = ref(false)

const PRESET_MAJORS = ['计算机科学', '软件工程', '人工智能', '数据科学', '网络安全', '电子信息', '其他专业']
const PRESET_COURSES = ['数据结构', '操作系统', '计算机网络', '数据库原理', '算法分析', '机器学习']
const PRESET_GOALS = [
  '期末考试冲刺', '完成课设项目', '大厂求职面试', '考研初试复习', '考研复试准备',
  '系统学习进阶', '零基础快速入门', '竞赛夺奖(ACM/蓝桥)', '个人兴趣拓展', '行业证书考取'
]
const PRESET_EDUCATION_LEVELS = ['高职/专科', '本科', '研究生']
const PRESET_SCHOOL_LEVELS = ['985', '211', '双一流', '普通本科', '高职高专', '海外高校', '其他']
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
  education_level: '',
  grade: '',
  major: '',
  courses: [],
  learning_goal: '',
  school: '',
  school_level: '',
  preferred_language: ''
})

const customInputs = reactive({
  course: '',
  major: ''
})
const customAddedCourses = ref<string[]>([])
const profileSchoolOptions = ref<SchoolItem[]>([])

const querySearchSchool = async (queryString: string, cb: any) => {
  if (!queryString) {
    cb([]); return;
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

const handleMajorClick = (major: string) => {
  if (major === '其他专业') {
    if (isCustomMajor.value) {
      isCustomMajor.value = false;
      onboardingForm.major = '';
    } else {
      isCustomMajor.value = true;
      onboardingForm.major = customInputs.major;
    }
  } else {
    if (onboardingForm.major === major && !isCustomMajor.value) {
      onboardingForm.major = '';
    } else {
      isCustomMajor.value = false;
      onboardingForm.major = major;
    }
  }
}

const syncCustomMajor = () => {
  onboardingForm.major = customInputs.major;
}

const toggleCourse = (course: string) => {
  const index = onboardingForm.courses.indexOf(course);
  if (index > -1) {
    onboardingForm.courses.splice(index, 1);
    const customIdx = customAddedCourses.value.indexOf(course);
    if (customIdx > -1) customAddedCourses.value.splice(customIdx, 1);
  } else {
    onboardingForm.courses.push(course);
  }
}

const addCustomCourse = () => {
  const course = customInputs.course.trim();
  if (course && !onboardingForm.courses.includes(course)) {
    onboardingForm.courses.push(course);
    if (!PRESET_COURSES.includes(course)) {
      customAddedCourses.value.push(course);
    }
  }
  customInputs.course = '';
}

const nextStep = () => {
  if (!onboardingForm.major || (isCustomMajor.value && !customInputs.major.trim())) {
    ElMessage.warning('请选择或填写主修专业'); return;
  }
  if (onboardingForm.courses.length === 0) {
    ElMessage.warning('请至少选择一门课程'); return;
  }
  currentStep.value = 2;
}

const skipOnboarding = () => {
  visible.value = false;
  emit('success');
}

const disableOnboarding = () => {
  localStorage.setItem('hide_onboarding_dialog', 'true');
  visible.value = false;
  emit('success');
}

const loadStatus = async () => {
  try {
    const res = await getProfileOnboarding();
    const profile = res.data.data.student_profile;
    if (profile.major) {
      if (!PRESET_MAJORS.includes(profile.major)) {
        isCustomMajor.value = true;
        customInputs.major = profile.major;
      }
      onboardingForm.major = profile.major;
    }
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
  if (!onboardingForm.school || !onboardingForm.school_level) {
    ElMessage.warning('请输入并选择您的院校与层次'); return;
  }
  if (!onboardingForm.education_level) {
    ElMessage.warning('请选择学历层次'); return;
  }
  if (!onboardingForm.grade) {
    ElMessage.warning('请选择年级'); return;
  }
  if (!onboardingForm.learning_goal) {
    ElMessage.warning('请选择当前学习目标'); return;
  }

  submitting.value = true;
  try {
    const payload = {
      ...onboardingForm,
      school: onboardingForm.school || null,
      school_level: onboardingForm.school_level || null,
      preferred_language: onboardingForm.preferred_language || null,
    };

    await updateProfileOnboarding(payload as any);
    visible.value = false;
    ElMessage.success('配置已完成');
    emit('success');
  } catch (e) {
    ElMessage.error('保存失败，请重试');
  } finally {
    submitting.value = false;
  }
}

watch(visible, (newVal) => {
  if (newVal) { currentStep.value = 1; }
})

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

/* 头部样式 */
.onboarding-header {
  padding: 40px 40px 24px;
  text-align: center;
  position: relative;
}

.header-title {
  margin: 0 0 12px;
  font-size: 1.45rem;
  font-weight: 700;
  color: #1F2937;
}

.header-subtitle {
  margin: 0;
  font-size: 0.9rem;
  color: #6B7280;
  line-height: 1.6;
}

/* 自定义步骤指示器 */
.custom-step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9CA3AF;
}

.step-item.is-active {
  color: #10B981;
}

.step-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #9CA3AF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: bold;
  background-color: #FFFFFF;
}

.step-item.is-active .step-icon {
  border-color: #10B981;
  color: #10B981;
}

.step-text {
  font-size: 14px;
  font-weight: 500;
}

.step-line {
  width: 100px;
  height: 1px;
  background-color: #E5E7EB;
}

.step-line.is-active {
  background-color: #10B981;
}

/* 主体内容 */
.onboarding-main {
  display: flex;
  flex-direction: column;
  padding: 0 40px;
  min-height: 320px;
}

.step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-block { margin-bottom: 24px; }
.section-title {
  margin: 0 0 16px;
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
}
.required { color: #EF4444; margin-left: 4px; }
.optional { color: #9CA3AF; font-size: 0.85rem; font-weight: normal; margin-left: 4px; }

/* 标签样式 */
.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.selectable-tag {
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  color: #374151;
  padding: 8px 18px;
  border-radius: 6px;
  font-size: 13.5px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.selectable-tag:hover {
  background: #F9FAFB;
}

.selectable-tag.active {
  border-color: #10B981;
  color: #10B981;
  background: #ECFDF5;
}

/* 输入框定制 */
.custom-input-wrap { width: 100%; max-width: 400px; }
.add-course-wrap { max-width: 100%; }

.custom-input :deep(.el-input__wrapper),
.custom-input :deep(.el-select__wrapper) {
  box-shadow: none !important;
  border: 1px solid #E5E7EB !important;
  background: #FFFFFF !important;
  border-radius: 6px !important;
  min-height: 40px !important;
}

.custom-input :deep(.el-input__wrapper.is-focus),
.custom-input :deep(.el-select__wrapper.is-focus) {
  border-color: #10B981 !important;
}

.custom-input :deep(.el-input__inner) {
  font-size: 0.9rem;
  color: #374151;
}

/* 添加课程特殊拼接框样式还原 */
.add-course-input :deep(.el-input__wrapper) {
  border-right: none !important;
  border-top-right-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
}

.add-course-input :deep(.el-input-group__append) {
  background: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
  border-left: 1px solid #E5E7EB !important;
  border-radius: 0 6px 6px 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}

.add-btn {
  border: none !important;
  background: transparent !important;
  color: #4B5563 !important;
  font-weight: 500;
  height: 38px;
  padding: 0 36px;
  border-radius: 0;
  transition: all 0.2s ease;
}
.add-btn:hover {
  color: #10B981 !important;
  background-color: #F9FAFB !important;
}

/* 网格布局 */
.form-grid-2x2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px 24px;
}
.grid-item { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 0.9rem; color: #374151; font-weight: 500; margin: 0; }
.school-level-tag { margin-left: 8px; font-size: 0.75rem; color: #6B7280; background: #F3F4F6; padding: 2px 8px; border-radius: 4px; }
.w-full { width: 100%; }

/* 底部按钮区 */
.onboarding-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 40px 32px;
}

.footer-left { display: flex; align-items: center; }

/* 轮廓按钮组与样式 */
.outline-links {
  display: flex;
  gap: 12px;
}

.outline-btn {
  border-radius: 6px !important;
  padding: 0 20px !important;
  height: 42px !important;
  font-size: 0.9rem !important;
  font-weight: 600 !important;
  transition: all 0.2s !important;
}

/* 稍后完善 按钮 (蓝色主题) */
.btn-skip {
  background: #F0F5FF !important;
  border: 1px solid #BFDBFE !important;
  color: #3B82F6 !important;
}

.btn-skip:hover {
  background: #E0E7FF !important;
  border-color: #93C5FD !important;
  color: #2563EB !important;
}

/* 不再弹出 按钮 (灰白主题) */
.btn-never {
  background: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
  color: #4B5563 !important;
}

.btn-never:hover {
  background: #F9FAFB !important;
  border-color: #D1D5DB !important;
  color: #1F2937 !important;
}

/* 核心操作按钮颜色修改 */
.action-btn {
  background: #10B981 !important;
  color: #FFFFFF !important;
  border: none !important;
  border-radius: 6px !important;
  padding: 0 24px !important;
  font-size: 0.95rem !important;
  height: 42px !important;
  transition: background 0.2s !important;
}

.action-btn:hover {
  background: #059669 !important;
}

.nav-btn {
  background: #FFFFFF !important;
  border: 1px solid #E5E7EB !important;
  color: #374151 !important;
  border-radius: 6px !important;
  padding: 0 20px !important;
  height: 42px !important;
  transition: all 0.2s !important;
}

.nav-btn:hover {
  background: #F9FAFB !important;
  color: #111827 !important;
}

.mt-3 { margin-top: 12px; }
.mt-4 { margin-top: 24px; }
.ml-1 { margin-left: 4px; }
.mr-1 { margin-right: 4px; }
.ml-3 { margin-left: 12px; }
.ml-4 { margin-left: 20px; }

@media (max-width: 640px) {
  .form-grid-2x2 { grid-template-columns: 1fr; gap: 16px; }
  .onboarding-header { padding: 32px 24px 20px; }
  .onboarding-main { padding: 0 24px; }
  .onboarding-footer { padding: 20px 24px 24px; flex-direction: column; gap: 20px; align-items: stretch; }
  .footer-left { justify-content: center; }
  .footer-right { display: flex; }
  .footer-right .action-btn { width: 100%; justify-content: center; }
  .step-line { width: 60px; }
}
</style>