<template>
  <el-dialog
    v-model="visible"
    width="720px"
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
          <h2>先完成冷启动画像</h2>
          <p class="subcopy">只收集必要基础信息，后续画像会在学习和辅导过程中持续更新。</p>
        </div>
        <el-button text @click="handleSkip">稍后完善</el-button>
      </header>

      <div class="stepper">
        <div
          v-for="item in steps"
          :key="item.key"
          :class="['step-chip', { active: item.key === currentStep, done: stepOrder.indexOf(item.key) < stepOrder.indexOf(currentStep) }]"
        >
          {{ item.label }}
        </div>
      </div>

      <section class="panel" v-if="currentStep === 'base'">
        <div class="grid two">
          <el-form-item label="专业" required>
            <el-select v-model="form.major" filterable allow-create default-first-option placeholder="请选择或输入专业">
              <el-option v-for="item in PRESET_MAJORS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>

          <el-form-item label="学校" required>
            <el-autocomplete
              v-model="form.school"
              :fetch-suggestions="querySearchSchool"
              placeholder="搜索学校"
              clearable
              @select="handleSchoolSelect"
            />
          </el-form-item>

          <el-form-item label="年级" required>
            <el-select v-model="form.grade" placeholder="请选择年级">
              <el-option v-for="item in PRESET_GRADES" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>

          <el-form-item label="每日学习时长" required>
            <el-select v-model="form.daily_study_time" placeholder="请选择时长">
              <el-option v-for="item in PRESET_DAILY_STUDY_TIME" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </div>
      </section>

      <section class="panel" v-else-if="currentStep === 'goal'">
        <div class="grid two">
          <el-form-item label="全局学习目标" required>
            <el-select v-model="form.global_learning_goal" filterable allow-create default-first-option placeholder="请选择学习目标">
              <el-option v-for="item in PRESET_GOALS" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>

          <el-form-item label="当前课程" required>
            <el-select
              v-model="selectedCourseNames"
              multiple
              filterable
              allow-create
              default-first-option
              collapse-tags
              collapse-tags-tooltip
              placeholder="最多选择 3 门课程"
            >
              <el-option v-for="item in PRESET_COURSES" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
        </div>
        <p class="hint">课程画像会按课程分别维护，后续可在个人中心继续修改。</p>
      </section>

      <section class="panel" v-else>
        <div class="course-grid">
          <div v-for="(course, index) in form.courses" :key="course.course || index" class="course-card">
            <div class="course-card-head">
              <strong>{{ course.course }}</strong>
            </div>
            <el-form-item label="基础水平" required>
              <el-select v-model="course.foundation_level" placeholder="请选择基础水平">
                <el-option v-for="item in PRESET_FOUNDATION_LEVELS" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </section>

      <footer class="dialog-footer">
        <el-button v-if="currentStep !== 'base'" @click="goPrev">上一步</el-button>
        <el-button v-if="currentStep !== 'foundation'" type="primary" @click="goNext">下一步</el-button>
        <el-button v-else type="primary" :loading="submitting" @click="submitForm">生成冷启动画像</el-button>
      </footer>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { updateMe } from '@/api/auth'
import { getProfileOnboarding, updateProfileOnboarding } from '@/profile/api/profile'
import type { CourseBaseInfo, ProfileOnboardingUpdate } from '@/profile/api/profile'
import { searchSchools } from '@/resource/api/school'

type StepKey = 'base' | 'goal' | 'foundation'

const props = defineProps<{ modelValue: boolean }>()
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

const steps = [
  { key: 'base', label: '基础信息' },
  { key: 'goal', label: '目标与课程' },
  { key: 'foundation', label: '课程基础' },
] as const

const stepOrder: StepKey[] = ['base', 'goal', 'foundation']
const currentStep = ref<StepKey>('base')
const selectedCourseNames = ref<string[]>([])
const submitting = ref(false)

const form = reactive<ProfileOnboardingUpdate & { courses: CourseBaseInfo[] }>({
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

watch(visible, async (open) => {
  if (!open) return
  resetState()
  await loadStatus()
})

onMounted(async () => {
  if (visible.value) {
    await loadStatus()
  }
})

const resetState = () => {
  currentStep.value = 'base'
  submitting.value = false
}

const validateBase = () => {
  if (!form.major || !form.school || !form.grade || !form.daily_study_time) {
    ElMessage.warning('请先完整填写基础信息')
    return false
  }
  return true
}

const validateGoal = () => {
  if (!form.global_learning_goal) {
    ElMessage.warning('请选择学习目标')
    return false
  }
  const names = selectedCourseNames.value.map((item) => item.trim()).filter(Boolean).slice(0, 3)
  if (names.length === 0) {
    ElMessage.warning('至少选择一门课程')
    return false
  }
  form.courses = names.map((course): CourseBaseInfo => ({
    course,
    foundation_level: '',
    current_topic: null,
    course_learning_goal: null,
    weak_points: [],
  }))
  return true
}

const validateFoundation = () => {
  if (form.courses.some((item) => !item.foundation_level)) {
    ElMessage.warning('请为每门课程选择基础水平')
    return false
  }
  return true
}

const goNext = () => {
  if (currentStep.value === 'base' && !validateBase()) return
  if (currentStep.value === 'goal' && !validateGoal()) return
  currentStep.value = stepOrder[Math.min(stepOrder.indexOf(currentStep.value) + 1, stepOrder.length - 1)]!
}

const goPrev = () => {
  currentStep.value = stepOrder[Math.max(stepOrder.indexOf(currentStep.value) - 1, 0)]!
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
    form.courses = Array.isArray(baseInfo.courses) ? [...baseInfo.courses] : []
    selectedCourseNames.value = form.courses.map((item) => item.course).filter(Boolean)
  } catch (error) {
    console.error('Failed to load onboarding data', error)
  }
}

const submitForm = async () => {
  if (!validateFoundation()) return
  submitting.value = true
  try {
    await updateProfileOnboarding({
      ...form,
      school_level: form.school_level || null,
      self_description: form.self_description || null,
      courses: form.courses.map((item) => ({
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
.onboarding-dialog :deep(.el-dialog__header) {
  display: none;
}

.onboarding-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.dialog-shell {
  padding: 28px;
  background: #fff;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: #4f46e5;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.dialog-header h2 {
  margin: 0;
  font-size: 26px;
  color: #0f172a;
}

.subcopy {
  margin: 10px 0 0;
  color: #64748b;
  line-height: 1.6;
}

.stepper {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.step-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: #eef2ff;
  color: #6366f1;
  font-size: 13px;
  font-weight: 600;
}

.step-chip.done {
  background: #dcfce7;
  color: #15803d;
}

.step-chip.active {
  background: #4f46e5;
  color: #fff;
}

.panel {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 20px;
  background: #f8fafc;
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.course-grid {
  display: grid;
  gap: 14px;
}

.course-card {
  padding: 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e2e8f0;
}

.course-card-head {
  margin-bottom: 10px;
  color: #0f172a;
}

.hint {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 13px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

@media (max-width: 760px) {
  .dialog-shell {
    padding: 20px;
  }

  .dialog-header,
  .grid.two {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
