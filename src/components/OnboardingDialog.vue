<template>
  <el-dialog
      v-model="visible"
      width="640px"
      :show-close="true"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="custom-onboarding-dialog"
      align-center
  >
    <div class="onboarding-wrapper">
      <header class="onboarding-header">
        <div class="header-text">
          <h2>欢迎来到学枢</h2>
          <p>请告诉我们你的专业方向和学习偏好，<br>以便为你定制个性化学习路径和多模态资源推荐。</p>
        </div>
        
        <div class="onboarding-step-indicator mt-4">
          <el-steps :active="currentStep" finish-status="success" simple style="background: transparent; padding: 0;">
            <el-step title="基础档案" />
            <el-step title="学习风格" />
          </el-steps>
        </div>
      </header>

      <main class="onboarding-main">
        <!-- 第 1 步：基础档案 -->
        <div v-show="currentStep === 1" class="step-content">
          <div class="section-card">
            <div class="section-title-row">
              <h3 class="section-title">1. 选择主修专业 <span class="required-star">*</span></h3>
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
              <h3 class="section-title">2. 选择当前课程（可多选） <span class="required-star">*</span></h3>
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
              </div>
              <div
                  v-for="customCourse in customAddedCourses"
                  :key="customCourse"
                  class="selectable-tag active"
                  @click="toggleMultiValue('courses', customCourse)"
              >
                {{ customCourse }}
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
              <h3 class="section-title">3. 学校与阶段</h3>
            </div>
            <div class="custom-input-wrap form-grid-2x2 mt-2">
              <div class="grid-item">
                <label class="sub-label">院校 <span class="required-star">*</span></label>
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
                <label class="sub-label">院校层次 <span class="required-star">*</span></label>
                <el-select v-model="onboardingForm.school_level" filterable allow-create default-first-option clearable placeholder="请选择或从院校带出" class="custom-inline-input w-full">
                  <el-option v-for="level in PRESET_SCHOOL_LEVELS" :key="level" :label="level" :value="level" />
                </el-select>
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
                <label class="sub-label">当前学习目标 <span class="required-star">*</span></label>
                <el-select v-model="onboardingForm.learning_goal" filterable allow-create default-first-option clearable placeholder="请选择或输入" class="custom-inline-input w-full">
                  <el-option v-for="goal in PRESET_GOALS" :key="goal" :label="goal" :value="goal" />
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
        </div>

        <!-- 第 2 步：学习风格 -->
        <div v-show="currentStep === 2" class="step-content">
          <div class="section-card">
            <div class="section-title-row">
              <h3 class="section-title">1. 认知风格（偏好的学习媒介） <span class="optional-text">（选填）</span></h3>
            </div>
            <div class="tag-group mt-2">
              <div
                  v-for="style in PRESET_COGNITIVE_STYLES"
                  :key="style.value"
                  class="selectable-tag"
                  :class="{ active: onboardingForm.cognitive_style === style.value }"
                  @click="onboardingForm.cognitive_style = style.value"
              >
                {{ style.label }}
              </div>
            </div>
          </div>

          <div class="section-card">
            <div class="section-title-row">
              <h3 class="section-title">2. 交互偏好（希望 AI 扮演的角色） <span class="optional-text">（选填）</span></h3>
            </div>
            <div class="tag-group mt-2">
              <div
                  v-for="pref in PRESET_INTERACTION_PREFS"
                  :key="pref.value"
                  class="selectable-tag"
                  :class="{ active: onboardingForm.interaction_preference === pref.value }"
                  @click="onboardingForm.interaction_preference = pref.value"
              >
                {{ pref.label }}
              </div>
            </div>
          </div>

          <div class="section-card">
            <div class="section-title-row">
              <h3 class="section-title">3. 实践能力自评 <span class="optional-text">（选填）</span></h3>
            </div>
            <div class="tag-group mt-2">
              <div
                  v-for="ability in PRESET_PRACTICE_ABILITIES"
                  :key="ability.value"
                  class="selectable-tag"
                  :class="{ active: onboardingForm.practice_ability === ability.value }"
                  @click="onboardingForm.practice_ability = ability.value"
              >
                {{ ability.label }}
              </div>
            </div>
          </div>

          <div class="section-card">
            <div class="section-title-row">
              <h3 class="section-title">4. 学习痛点与薄弱环节（可多选） <span class="optional-text">（选填）</span></h3>
            </div>
            <div class="tag-group mt-2">
              <div
                  v-for="weakness in PRESET_WEAKNESS_POINTS"
                  :key="weakness"
                  class="selectable-tag"
                  :class="{ active: onboardingForm.weakness_points?.includes(weakness) }"
                  @click="toggleWeakness(weakness)"
              >
                {{ weakness }}
              </div>
            </div>
          </div>
        </div>

      </main>

      <footer class="onboarding-footer">
        <div class="footer-left-actions">
          <el-button class="skip-btn-outline" @click="skipOnboarding">
            稍后完善
          </el-button>
          <el-button class="never-show-btn-outline" @click="disableOnboarding">
            不再弹出
          </el-button>
        </div>

        <div class="footer-right-actions">
          <el-button v-if="currentStep > 1" @click="currentStep--" class="prev-btn">
            上一步
          </el-button>
          <el-button
              v-if="currentStep === 1"
              type="primary"
              class="start-btn"
              @click="nextStep"
          >
            下一步 <el-icon class="ml-1"><Right /></el-icon>
          </el-button>
          <el-button
              v-if="currentStep === 2"
              type="primary"
              class="start-btn"
              :loading="submitting"
              @click="submitForm"
          >
            完成初始化 <el-icon class="ml-1"><Right /></el-icon>
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
import { Right, Search } from '@element-plus/icons-vue'

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

// 补充维度的选项
const PRESET_COGNITIVE_STYLES = [
  { label: '👁️ 视觉驱动 (偏好视频/动画)', value: '视觉驱动' },
  { label: '🗺️ 结构驱动 (偏好思维导图/图文)', value: '结构驱动' },
  { label: '🛠️ 实践驱动 (偏好代码实操)', value: '实践驱动' },
  { label: '📝 题海驱动 (偏好刷题演练)', value: '题海驱动' }
]
const PRESET_INTERACTION_PREFS = [
  { label: '💡 启发引导者 (引导我思考)', value: '启发引导者' },
  { label: '🎯 直白解答者 (直接给答案)', value: '直白解答者' },
  { label: '📝 严厉考官 (多出题抽查)', value: '严厉考官' }
]
const PRESET_PRACTICE_ABILITIES = [
  { label: '📚 偏重理论，缺乏实操', value: '偏重理论' },
  { label: '💻 完成过基础课设实验', value: '基础课设' },
  { label: '🚀 具备完整项目开发经验', value: '完整项目经验' }
]
const PRESET_WEAKNESS_POINTS = [
  '底层原理晦涩难懂', '知识点碎片化，难以串联', '缺乏动手实操能力', '考试刷题正确率低'
]

const onboardingForm = reactive<ProfileOnboardingUpdate>({
  education_level: '',
  grade: '',
  major: '',
  courses: [],
  learning_goal: '',
  school: '',
  school_level: '',
  preferred_language: '',
  cognitive_style: '',
  interaction_preference: '',
  practice_ability: '',
  weakness_points: []
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

const toggleWeakness = (weakness: string) => {
  if (!onboardingForm.weakness_points) {
    onboardingForm.weakness_points = []
  }
  const index = onboardingForm.weakness_points.indexOf(weakness)
  if (index > -1) {
    onboardingForm.weakness_points.splice(index, 1)
  } else {
    onboardingForm.weakness_points.push(weakness)
  }
}

const nextStep = () => {
  // 第 1 步必填校验
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
  if (!onboardingForm.school) {
    ElMessage.warning('请选择或填写就读院校')
    return
  }
  if (!onboardingForm.school_level) {
    ElMessage.warning('请选择院校层次')
    return
  }
  if (!onboardingForm.grade) {
    ElMessage.warning('请选择就读年级')
    return
  }
  if (!onboardingForm.learning_goal) {
    ElMessage.warning('请选择或输入当前学习目标')
    return
  }

  currentStep.value = 2
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
    
    if (profile.cognitive_style) onboardingForm.cognitive_style = profile.cognitive_style
    if (profile.interaction_preference) onboardingForm.interaction_preference = profile.interaction_preference
    if (profile.practice_ability) onboardingForm.practice_ability = profile.practice_ability
    if (profile.weakness_points) onboardingForm.weakness_points = profile.weakness_points
  } catch (e) {
    console.error('Failed to load status', e)
  }
}

const submitForm = async () => {
  submitting.value = true
  try {
    const payload = {
      ...onboardingForm,
      school: onboardingForm.school || null,
      school_level: onboardingForm.school_level || null,
      preferred_language: onboardingForm.preferred_language || null,
      cognitive_style: onboardingForm.cognitive_style || null,
      interaction_preference: onboardingForm.interaction_preference || null,
      practice_ability: onboardingForm.practice_ability || null,
      weakness_points: onboardingForm.weakness_points && onboardingForm.weakness_points.length > 0 ? onboardingForm.weakness_points : null
    }
    
    await updateProfileOnboarding(payload)
    visible.value = false
    ElMessage.success('档案初始化完成')
    emit('success')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

watch(visible, (newVal) => {
  if (newVal) {
    currentStep.value = 1
  }
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

/* 头部优化 */
.onboarding-header {
  padding: 32px 32px 16px;
  text-align: center;
}
.header-text h2 { font-size: 1.25rem; font-weight: 600; color: #111827; margin: 0 0 8px; }
.header-text p { font-size: 0.85rem; color: #6B7280; margin: 0; line-height: 1.5; }

.onboarding-step-indicator {
  max-width: 400px;
  margin: 0 auto;
}
.onboarding-step-indicator :deep(.el-step__title) {
  font-size: 0.85rem;
}

/* 主体优化 */
.onboarding-main { 
  display: flex; 
  flex-direction: column; 
  padding: 0 32px; 
  gap: 24px; 
  margin-bottom: 24px;
  min-height: 380px; /* 保证两步高度大致稳定，避免弹窗抖动 */
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-title-row { margin-bottom: 12px; }

.section-title { margin: 0; font-size: 0.95rem; font-weight: 600; color: #374151; }
.required-star { color: #EF4444; margin-left: 2px; }
.optional-text { font-size: 0.8rem; color: #9CA3AF; font-weight: normal; }

/* 标签样式 */
.tag-group { display: flex; flex-wrap: wrap; gap: 10px; }
.selectable-tag {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 6px 16px; background: #F9FAFB; border: 1px solid #E5E7EB;
  border-radius: 4px; color: #4B5563; font-size: 0.85rem;
  cursor: pointer; transition: all 0.2s; user-select: none;
}
.selectable-tag:hover {
  background: #F3F4F6;
}
.selectable-tag.active {
  background: #EFF6FF; border-color: #3B82F6; color: #1D4ED8; font-weight: 500;
}

/* 输入框定制与网格对齐 */
.custom-input-wrap { margin-top: 12px; }
.custom-inline-input :deep(.el-input__wrapper),
.custom-inline-input :deep(.el-select__wrapper) {
  box-shadow: none !important; border: 1px solid #E5E7EB !important;
  border-radius: 4px !important; min-height: 36px !important;
  background: #F9FAFB !important;
}
.custom-inline-input :deep(.el-input__wrapper.is-focus),
.custom-inline-input :deep(.el-select__wrapper.is-focus) {
  border-color: #3B82F6 !important;
  background: #FFFFFF !important;
}

.custom-inline-input :deep(.el-input__inner) { font-size: 0.85rem; color: #374151; }
.custom-inline-input :deep(.el-input-group__append) {
  background: #F3F4F6; border: 1px solid #E5E7EB; border-left: none;
  border-radius: 0 4px 4px 0; padding: 0 16px; color: #4B5563;
}

/* 2x2 网格布局 */
.form-grid-2x2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 20px;
}
.grid-item { display: flex; flex-direction: column; gap: 6px; }
.sub-label {
  font-size: 0.85rem; color: #374151; font-weight: 500; margin: 0;
}

.school-level-tag { margin-left: 8px; font-size: 0.7rem; color: #6B7280; background: #F3F4F6; padding: 2px 8px; border-radius: 4px; }
.w-full { width: 100%; }

/* 底部按钮 */
.onboarding-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 32px 32px;
  border-top: 1px solid #F3F4F6;
  margin-top: 16px;
}

.footer-left-actions { display: flex; align-items: center; gap: 16px; }
.footer-right-actions { display: flex; align-items: center; gap: 12px; }

.skip-btn-outline {
  border: none !important;
  background-color: transparent !important;
  color: #6B7280 !important;
  height: 36px;
  padding: 0;
  font-size: 0.85rem;
  font-weight: 400;
  transition: all 0.2s;
}
.skip-btn-outline:hover {
  color: #374151 !important;
  background-color: transparent !important;
}

.never-show-btn-outline {
  border: none !important;
  background-color: transparent !important;
  color: #9CA3AF !important;
  height: 36px;
  padding: 0;
  font-size: 0.85rem;
  font-weight: 400;
  cursor: pointer;
  transition: all 0.2s;
}
.never-show-btn-outline:hover {
  color: #6B7280 !important;
  background-color: transparent !important;
}

.prev-btn {
  background: #F3F4F6; border: none; color: #4B5563;
  height: 38px; padding: 0 16px; border-radius: 4px;
  font-size: 0.85rem;
  transition: all 0.2s;
}
.prev-btn:hover { background: #E5E7EB; color: #111827; }

.start-btn {
  background: #111827; border: none; color: #FFF;
  height: 38px; padding: 0 24px; border-radius: 4px;
  font-size: 0.85rem; font-weight: 500;
  transition: all 0.2s;
}
.start-btn:hover { background: #374151; }

.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }
.ml-1 { margin-left: 4px; }

@media (max-width: 480px) {
  .form-grid-2x2 { grid-template-columns: 1fr; gap: 12px; }
}
</style>
