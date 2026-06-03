<template>
  <div class="profile-page">
    <section class="hero-card" v-if="profile">
      <div class="hero-copy">
        <h1>学习画像中心</h1>
        <p>首次填写的信息只是冷启动底座。后续学习行为、练习结果和智能辅导信号，才是画像持续更新的主来源。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="editorVisible = true">编辑基础信息</el-button>
        <el-button @click="refreshAll">刷新</el-button>
      </div>
    </section>

    <section v-if="profile" class="grid">
      <article class="panel">
        <div class="panel-head">
          <h2>基础信息</h2>
        </div>
        <div class="kv-grid">
          <div><span>学校</span><strong>{{ profile.base_info.school || '未填写' }}</strong></div>
          <div><span>院校层次</span><strong>{{ profile.base_info.school_level || '未识别' }}</strong></div>
          <div><span>专业</span><strong>{{ profile.base_info.major || '未填写' }}</strong></div>
          <div><span>年级</span><strong>{{ profile.base_info.grade || '未填写' }}</strong></div>
          <div><span>每日学习时长</span><strong>{{ profile.base_info.daily_study_time || '未填写' }}</strong></div>
          <div><span>全局学习目标</span><strong>{{ profile.base_info.global_learning_goal || '未填写' }}</strong></div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>全局画像</h2>
        </div>
        <div class="kv-grid">
          <div v-for="item in globalItems" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>课程子画像</h2>
        </div>
        <div v-if="courseProfiles.length" class="stack">
          <div v-for="course in courseProfiles" :key="course.name" class="course-card">
            <div class="course-head">
              <h3>{{ course.name }}</h3>
              <span>{{ course.level }}</span>
            </div>
            <p>{{ course.goal }}</p>
            <div v-if="course.weakPoints.length" class="tag-list">
              <span v-for="point in course.weakPoints" :key="point">{{ point }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">当前还没有课程子画像。</div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>知识掌握度</h2>
        </div>
        <div v-if="masteryItems.length" class="stack">
          <div v-for="item in masteryItems" :key="`${item.course}-${item.knowledge_point}`" class="mastery-card">
            <div class="mastery-top">
              <div>
                <strong>{{ item.knowledge_point }}</strong>
                <span>{{ item.course }} / {{ item.status }}</span>
              </div>
              <em>{{ item.mastery_score }}%</em>
            </div>
            <el-progress :percentage="item.mastery_score" :status="item.mastery_score < 40 ? 'exception' : undefined" />
          </div>
        </div>
        <div v-else class="empty-state">掌握度会在练习、学习路径和辅导过程中持续形成。</div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>当前策略</h2>
        </div>
        <ul v-if="strategyItems.length" class="strategy-list">
          <li v-for="item in strategyItems" :key="item">{{ item }}</li>
        </ul>
        <div v-else class="empty-state">当前没有可展示的策略摘要。</div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>画像历史</h2>
        </div>
        <div v-if="history.length" class="stack">
          <div v-for="item in history" :key="item.version" class="history-card">
            <strong>V{{ item.version }}</strong>
            <span>{{ item.change_reason || 'system_update' }}</span>
            <em>{{ formatTime(item.created_at) }}</em>
          </div>
        </div>
        <div v-else class="empty-state">当前没有历史版本。</div>
      </article>
    </section>

    <el-dialog v-model="editorVisible" width="760px" title="编辑基础信息">
      <div class="editor-grid">
        <el-autocomplete
          v-model="form.school"
          :fetch-suggestions="querySearchSchool"
          placeholder="学校"
          clearable
          @select="handleSchoolSelect"
        />
        <el-input v-model="form.major" placeholder="专业" />
        <el-select v-model="form.grade" placeholder="年级">
          <el-option v-for="item in PRESET_GRADES" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="form.daily_study_time" placeholder="每日学习时长">
          <el-option v-for="item in PRESET_DAILY_STUDY_TIME" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="form.global_learning_goal" placeholder="学习目标">
          <el-option v-for="item in PRESET_GOALS" :key="item" :label="item" :value="item" />
        </el-select>
      </div>

      <div class="editor-course-block">
        <h3>课程与基础水平</h3>
        <div v-for="(course, index) in form.courses" :key="index" class="editor-course-row">
          <el-input v-model="course.course" placeholder="课程名称" />
          <el-select v-model="course.foundation_level" placeholder="基础水平">
            <el-option v-for="item in PRESET_FOUNDATION_LEVELS" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
      </div>

      <template #footer>
        <el-button @click="editorVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBaseInfo">保存并更新画像</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import {
  getProfile,
  getProfileHistory,
  updateProfileOnboarding,
  type ProfileData,
  type ProfileHistoryItem,
  type ProfileOnboardingUpdate,
} from '@/profile/api/profile'
import { searchSchools } from '@/resource/api/school'

const profile = ref<ProfileData | null>(null)
const history = ref<ProfileHistoryItem[]>([])
const editorVisible = ref(false)
const saving = ref(false)

const PRESET_GRADES = ['大一', '大二', '大三', '大四', '研一', '研二', '研三']
const PRESET_DAILY_STUDY_TIME = ['30min以下', '30-60min', '1-2h', '2-3h', '3h以上']
const PRESET_GOALS = ['期末复习', '考研学习', '进阶学习', '补基础', '项目实战']
const PRESET_FOUNDATION_LEVELS = ['薄弱', '一般', '较好', '熟练']

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

const globalItems = computed(() => {
  const globalProfile = (profile.value?.learning_profile as any)?.global_profile || {}
  return [
    { label: '专业背景', value: globalProfile.major_background?.value || '暂无' },
    { label: '学习阶段', value: globalProfile.student_stage?.value || '暂无' },
    { label: '学习节奏', value: globalProfile.learning_pace?.value || '暂无' },
    { label: '认知风格', value: globalProfile.cognitive_style?.value || '暂无' },
    { label: '实践画像', value: formatValue(globalProfile.practice_profile?.value) },
    { label: '资源偏好', value: formatValue(globalProfile.resource_preference_weight?.value) },
  ]
})

const courseProfiles = computed(() => {
  const courses = ((profile.value?.learning_profile as any)?.course_profiles || []) as any[]
  return courses.map((course) => ({
    name: course.course_context?.value?.course || '未命名课程',
    level: course.knowledge_level?.value || '暂无',
    goal: ((course.learning_goal_type?.value || []) as string[]).join(' / ') || '暂无目标',
    weakPoints: (course.weak_knowledge_points?.value || []).map((item: any) => item.name || item),
  }))
})

const masteryItems = computed(() => (profile.value?.knowledge_mastery || []) as Array<any>)

const strategyItems = computed(() => {
  const strategy = profile.value?.initial_strategy || {}
  return [
    strategy.strategy_summary,
    strategy.path_planning_strategy,
    strategy.tutor_strategy,
  ].filter(Boolean) as string[]
})

watch(editorVisible, (open) => {
  if (open && profile.value) {
    fillForm(profile.value.base_info)
  }
})

const formatValue = (value: unknown) => {
  if (!value) return '暂无'
  if (Array.isArray(value)) return value.join(' / ') || '暂无'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const formatTime = (value: string | null) => {
  if (!value) return '未知时间'
  return new Date(value).toLocaleString()
}

const fillForm = (baseInfo: ProfileData['base_info']) => {
  form.school = baseInfo.school || ''
  form.school_level = baseInfo.school_level || ''
  form.major = baseInfo.major || ''
  form.grade = baseInfo.grade || ''
  form.daily_study_time = baseInfo.daily_study_time || ''
  form.global_learning_goal = baseInfo.global_learning_goal || ''
  form.resource_preference = [...(baseInfo.resource_preference || [])]
  form.programming_languages = [...(baseInfo.programming_languages || [])]
  form.self_description = baseInfo.self_description || ''
  form.courses = (baseInfo.courses || []).map((course) => ({
    course: course.course,
    foundation_level: course.foundation_level,
    current_topic: course.current_topic || null,
    course_learning_goal: course.course_learning_goal || null,
    weak_points: [...(course.weak_points || [])],
  }))
}

const loadProfile = async () => {
  const [profileRes, historyRes] = await Promise.all([getProfile(), getProfileHistory(20)])
  profile.value = profileRes.data.data
  history.value = historyRes.data.data
}

const refreshAll = async () => {
  try {
    await loadProfile()
  } catch (error) {
    console.error('Failed to refresh profile page', error)
  }
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

const saveBaseInfo = async () => {
  saving.value = true
  try {
    await updateProfileOnboarding({
      ...form,
      courses: form.courses.filter((course) => course.course && course.foundation_level).slice(0, 3),
    })
    editorVisible.value = false
    await loadProfile()
    ElMessage.success('基础信息已更新，画像已重新生成')
  } catch (error) {
    console.error('Failed to save profile base info', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadProfile)
</script>

<style scoped>
.profile-page {
  min-height: calc(100vh - 64px);
  padding: 24px;
  background: #f8fafc;
}

.hero-card,
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 24px;
  margin-bottom: 24px;
}

.hero-copy h1 {
  margin: 0 0 8px;
  font-size: 2rem;
}

.hero-copy p {
  margin: 0;
  color: #64748b;
  line-height: 1.75;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.panel {
  padding: 24px;
}

.panel-head {
  margin-bottom: 16px;
}

.panel-head h2 {
  margin: 0;
  font-size: 1.08rem;
}

.kv-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.kv-grid div,
.course-card,
.mastery-card,
.history-card {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.kv-grid span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #64748b;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-head,
.mastery-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.course-head h3 {
  margin: 0;
  font-size: 1rem;
}

.course-card p,
.mastery-top span,
.mastery-top em,
.history-card span,
.history-card em {
  color: #64748b;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.tag-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 12px;
}

.mastery-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mastery-top strong {
  display: block;
  margin-bottom: 4px;
}

.strategy-list {
  margin: 0;
  padding-left: 18px;
  color: #475569;
}

.strategy-list li {
  line-height: 1.8;
}

.history-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.editor-grid,
.editor-course-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.editor-course-block {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-course-block h3 {
  margin: 0;
  font-size: 1rem;
}

.empty-state {
  color: #94a3b8;
}

@media (max-width: 960px) {
  .profile-page {
    padding: 18px;
  }

  .hero-card,
  .grid,
  .kv-grid,
  .editor-grid,
  .editor-course-row {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
