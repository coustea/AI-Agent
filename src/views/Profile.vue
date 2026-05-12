<template>
  <div class="profile-dashboard">
    <div class="bento-container">
      <!-- 1. User Profile & Stats (Span 2x1) -->
      <div class="bento-card bento-span-2 user-card">
        <div class="user-header">
          <el-upload
              class="avatar-uploader"
              :show-file-list="false"
              :before-upload="beforeAvatarUpload"
              :http-request="handleAvatarUpload"
          >
            <div class="avatar-box" :class="{ 'has-avatar': userAvatar }">
              <img v-if="userAvatar" :src="userAvatar" class="avatar-image" alt="用户头像" />
              <el-icon v-else class="avatar-icon"><UserFilled /></el-icon>
              <div class="avatar-upload-overlay">
                <el-icon><Edit /></el-icon>
              </div>
            </div>
          </el-upload>
          <div class="user-info">
            <div class="name-row">
              <h3>{{ userName }}</h3>
              <el-icon class="verify-icon"><CircleCheckFilled /></el-icon>
            </div>
            <p class="email-text" v-if="userEmail">{{ userEmail }}</p>
            <p class="major">{{ profileHeadline }}</p>
            <div class="tags">
              <span class="tag">{{ studentProfile.grade || '年级待完善' }}</span>
              <span class="tag outline">{{ studentProfile.learning_goal || '学习目标待完善' }}</span>
            </div>
          </div>
          <el-button plain class="edit-btn" size="small" @click="openProfileEditor">
            <el-icon><Edit /></el-icon> 编辑资料
          </el-button>
        </div>
        <div class="user-stats">
          <div class="stat-item">
            <el-icon class="text-blue"><Clock /></el-icon>
            <div class="stat-val">128<small>h</small></div>
            <div class="stat-label">累计学习时长</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-indigo"><Reading /></el-icon>
            <div class="stat-val">18</div>
            <div class="stat-label">已完成课程</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-green"><DocumentCopy /></el-icon>
            <div class="stat-val">46</div>
            <div class="stat-label">生成资源数</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-orange"><StarFilled /></el-icon>
            <div class="stat-val">89<small>分</small></div>
            <div class="stat-label">综合评分</div>
          </div>
        </div>
      </div>

      <!-- 2. Recent Performance (Span 1x1) -->
      <div class="bento-card performance-card">
        <div class="card-header-flex">
          <h4>近期表现</h4>
          <el-select v-model="timeRange" size="small" style="width: 90px" aria-label="时间范围">
            <el-option label="近 7 天" value="7" />
            <el-option label="近 30 天" value="30" />
          </el-select>
        </div>
        <div class="perf-grid">
          <div class="perf-box">
            <div class="perf-icon bg-blue-light"><el-icon class="text-blue"><Timer /></el-icon></div>
            <div class="perf-data">
              <span class="label">学习时长</span>
              <span class="value">12.8<small>h</small></span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-green-light"><el-icon class="text-green"><Checked /></el-icon></div>
            <div class="perf-data">
              <span class="label">完成任务</span>
              <span class="value">16 <small>个</small></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Recent Record (Span 1x1) -->
      <div class="bento-card recent-card">
        <div class="card-header-flex">
          <h4 class="card-title">最近学习记录</h4>
          <a href="#" @click.prevent class="link-text">全部 ></a>
        </div>
        <div class="recent-record">
          <div class="record-icon"><el-icon><VideoPlay /></el-icon></div>
          <div class="record-info">
            <h5>CNN 3D 卷积核可视化</h5>
            <div class="record-meta">
              <span class="meta-tag">多模态视频 · MP4</span>
            </div>
          </div>
        </div>
        <div class="record-progress">
          <el-progress :percentage="60" :show-text="false" />
          <div class="prog-text"><span>进度 60%</span><span>今天 19:32</span></div>
        </div>
      </div>

      <!-- 4. Profile Details (Span 1x1) -->
      <div class="bento-card profile-info-card">
        <div class="card-header-flex">
          <h4 class="card-title">学习画像资料</h4>
        </div>
        <div class="profile-info-list">
          <div class="profile-info-row"><span><el-icon><Reading /></el-icon> 学历层次</span><strong>{{ studentProfile.education_level || '未填写' }}</strong></div>
          <div class="profile-info-row"><span><el-icon><UserFilled /></el-icon> 专业</span><strong>{{ studentProfile.major || '未填写' }}</strong></div>
          <div class="profile-info-row"><span><el-icon><VideoPlay /></el-icon> 正在学习</span><strong>{{ courseSummary }}</strong></div>
          <div class="profile-info-row"><span><el-icon><Cpu /></el-icon> 常用语言</span><strong>{{ studentProfile.preferred_language || '未填写' }}</strong></div>
        </div>
      </div>

      <!-- 5. Growth Trend (Span 2x1) -->
      <div class="bento-card bento-span-2 trend-section">
        <div class="card-header-flex">
          <h4 class="card-title">学习成长趋势</h4>
        </div>
        <div class="trend-chart-container">
          <v-chart class="chart" :option="lineOption" autoresize />
        </div>
      </div>

      <!-- 6. Radar Chart (Span 1x1) -->
      <div class="bento-card radar-card">
        <div class="card-header-flex">
          <h4>学习画像 <el-icon class="info-icon"><InfoFilled /></el-icon></h4>
        </div>
        <div class="radar-container">
          <v-chart class="chart" :option="radarOption" autoresize />
        </div>
      </div>

      <!-- 7. History Table (Span 4x1) -->
      <div class="bento-card bento-span-4 history-card">
        <div class="card-header-flex">
          <h4 class="card-title"><el-icon class="text-blue"><Cpu /></el-icon> 资源生成历史</h4>
          <el-radio-group v-model="historyFilter" size="small" aria-label="资源过滤">
            <el-radio-button label="全部" />
            <el-radio-button label="已完成" />
          </el-radio-group>
        </div>

        <el-table :data="tableData" style="width: 100%" :header-cell-style="{background:'#F8FAFC', color:'#64748B'}">
          <el-table-column label="任务名称 / 学习主题" min-width="200">
            <template #default="scope">
              <div class="task-title-cell">
                <span>{{ scope.row.title }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small" class="custom-tag">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="120" />
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="viewResourceDetail(scope.row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog
        v-model="profileEditorVisible"
        title="编辑学习画像资料"
        width="720px"
        :close-on-click-modal="false"
        class="profile-editor-dialog"
    >
      <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-position="top"
      >
        <div class="profile-form-section">
          <div class="profile-form-section-head">
            <span>必填 01</span>
            <h5>专业与课程</h5>
            <p>先确定专业背景和正在学习的课程。</p>
          </div>
          <el-form-item label="专业" prop="major">
            <el-select
                v-model="profileForm.major"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="请选择专业，列表没有可直接输入"
            >
              <el-option v-for="major in PRESET_MAJORS" :key="major" :label="major" :value="major" />
            </el-select>
          </el-form-item>

          <el-form-item label="正在学习的课程" prop="courses">
            <el-select
                v-model="profileForm.courses"
                multiple
                filterable
                allow-create
                default-first-option
                placeholder="输入课程名称后回车，可添加多门课程"
                class="w-full"
                aria-label="正在学习的课程"
            >
              <el-option v-for="course in PRESET_COURSES" :key="course" :label="course" :value="course" />
            </el-select>
          </el-form-item>
        </div>

        <div class="profile-form-section">
          <div class="profile-form-section-head">
            <span>必填 02</span>
            <h5>学习目标</h5>
            <p>目标决定资源和路径生成方向。</p>
          </div>
          <el-form-item label="当前学习目标" prop="learning_goal">
            <el-select
                v-model="profileForm.learning_goal"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="请选择目标，列表没有可直接输入"
            >
              <el-option v-for="goal in PRESET_GOALS" :key="goal" :label="goal" :value="goal" />
            </el-select>
          </el-form-item>
        </div>

        <div class="profile-form-section optional">
          <div class="profile-form-section-head">
            <span>背景 03</span>
            <h5>学校与阶段</h5>
            <p>学校信息可选；学历层次和年级用于判断内容难度。</p>
          </div>
          <div class="profile-form-grid">
            <el-form-item label="院校（选填）" prop="school">
              <el-select
                  v-model="profileForm.school"
                  filterable
                  remote
                  allow-create
                  default-first-option
                  clearable
                  placeholder="搜索并选择院校，列表没有可直接输入"
                  :remote-method="searchProfileSchoolsDebounced"
                  :loading="profileSchoolSearchLoading"
                  @focus="handleProfileSchoolFocus"
                  @change="handleProfileSchoolChange"
              >
                <el-option
                    v-for="school in profileSchoolOptions"
                    :key="school.id"
                    :label="school.name"
                    :value="school.name"
                >
                  <span>{{ school.name }}</span>
                  <span v-if="school.level" class="school-level-tag">{{ school.level }}</span>
                </el-option>
              </el-select>
              <div v-if="profileSchoolLevelLabel" class="school-level-note">
                已识别院校层次：<span>{{ profileSchoolLevelLabel }}</span>
              </div>
            </el-form-item>
            <el-form-item label="学历层次" prop="education_level">
              <el-select v-model="profileForm.education_level" placeholder="请选择学历层次" filterable aria-label="学历层次">
                <el-option v-for="level in PRESET_EDUCATION_LEVELS" :key="level" :label="level" :value="level" />
              </el-select>
            </el-form-item>
            <el-form-item label="年级" prop="grade">
              <el-select
                  v-model="profileForm.grade"
                  filterable
                  allow-create
                  default-first-option
                  clearable
                  placeholder="请选择年级，列表没有可直接输入"
              >
                <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
              </el-select>
            </el-form-item>
            <el-form-item label="常用编程语言（选填）" prop="preferred_language">
              <el-select
                  v-model="profileForm.preferred_language"
                  filterable
                  allow-create
                  default-first-option
                  clearable
                  placeholder="请选择常用语言，列表没有可直接输入"
              >
                <el-option v-for="language in PRESET_LANGUAGES" :key="language" :label="language" :value="language" />
              </el-select>
            </el-form-item>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="profileEditorVisible = false">取消</el-button>
        <el-button type="primary" :loading="profileSubmitting" @click="submitProfile(profileFormRef)">
          保存资料
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  UserFilled, CircleCheckFilled, Edit, Clock, Reading, DocumentCopy, StarFilled,
  InfoFilled, Timer, Checked, VideoPlay, Cpu
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { getMe, uploadAvatar } from '@/api/auth'
import { getProfileOnboarding, updateProfileOnboarding, getGeneratedResources, searchSchools } from '@/api/ai'
import type { ProfileOnboardingUpdate, StudentProfileData, GeneratedResourceItem, SchoolItem } from '@/api/ai'

use([CanvasRenderer, RadarChart, LineChart, GridComponent, TooltipComponent])

const router = useRouter()

const timeRange = ref('7')
const historyFilter = ref('全部')
const userName = ref('学习者')
const userEmail = ref<string | null>(null)
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const profileSubmitting = ref(false)
const profileFormRef = ref<FormInstance>()
const profileSchoolSearchLoading = ref(false)
const profileSchoolOptions = ref<SchoolItem[]>([])

const PRESET_MAJORS = [
  '计算机科学与技术', '软件工程', '人工智能', '数据科学', '网络安全',
  '信息安全', '物联网工程', '通信工程', '电子信息工程', '数字媒体技术'
]
const PRESET_COURSES = [
  '数据结构', '算法分析', '操作系统', '计算机网络', '数据库系统',
  '计算机组成原理', '编译原理', '离散数学', '线性代数', '概率统计',
  '软件工程', 'Web开发', '机器学习', '深度学习', '计算机视觉', 'NLP',
  '分布式系统', '云计算', '嵌入式开发', '移动端开发'
]
const PRESET_GOALS = [
  '期末考试冲刺', '完成课设项目', '大厂求职面试', '考研初试复习', '考研复试准备',
  '系统学习进阶', '零基础快速入门', '竞赛夺奖(ACM/蓝桥)', '个人兴趣拓展', '行业证书考取'
]
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

const studentProfile = ref<StudentProfileData>({
  education_level: null,
  grade: null,
  major: null,
  courses: [],
  learning_goal: null,
  school: null,
  school_level: null,
  preferred_language: null,
})

const profileForm = reactive<ProfileOnboardingUpdate>({
  education_level: '',
  grade: '',
  major: '',
  courses: [],
  learning_goal: '',
  school: '',
  school_level: '',
  preferred_language: '',
})

const profileRules: FormRules<ProfileOnboardingUpdate> = {
  education_level: [{ required: true, message: '请选择学历层次', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  major: [{ required: true, message: '请选择或输入专业', trigger: 'change' }],
  courses: [{ required: true, type: 'array', min: 1, message: '请至少填写一门课程', trigger: 'change' }],
  learning_goal: [{ required: true, message: '请选择或输入当前学习目标', trigger: 'change' }],
}

const profileHeadline = computed(() => {
  const parts = [studentProfile.value.major, studentProfile.value.education_level, studentProfile.value.school]
    .filter((item): item is string => Boolean(item))
  return parts.length ? parts.join(' · ') : '学习资料待完善'
})

const courseSummary = computed(() => {
  return studentProfile.value.courses.length ? studentProfile.value.courses.join('、') : '未填写'
})

const profileSchoolLevelLabel = computed(() => profileForm.school_level || '')

const fillProfileForm = (payload: StudentProfileData) => {
  profileForm.education_level = payload.education_level || ''
  profileForm.grade = payload.grade || ''
  profileForm.major = payload.major || ''
  profileForm.courses = Array.isArray(payload.courses) ? [...payload.courses] : []
  profileForm.learning_goal = payload.learning_goal || ''
  profileForm.school = payload.school || ''
  profileForm.school_level = payload.school_level || ''
  profileForm.preferred_language = payload.preferred_language || ''
}

const applyProfileSchoolLevelFromSelection = (schoolName: string | null | undefined, clearWhenMissing = true) => {
  if (!schoolName) {
    profileForm.school_level = ''
    return
  }
  const selectedSchool = profileSchoolOptions.value.find((school) => school.name === schoolName)
  if (selectedSchool) {
    profileForm.school_level = selectedSchool.level || ''
  } else if (clearWhenMissing) {
    profileForm.school_level = ''
  }
}

let profileSchoolSearchTimeout: ReturnType<typeof setTimeout> | null = null
const handleProfileSchoolSearch = async (keyword: string) => {
  profileSchoolSearchLoading.value = true
  try {
    const res = await searchSchools(keyword, 20)
    profileSchoolOptions.value = res.data.data
    applyProfileSchoolLevelFromSelection(profileForm.school, false)
  } catch (e) {
    console.error('Failed to search schools', e)
  } finally {
    profileSchoolSearchLoading.value = false
  }
}

const searchProfileSchoolsDebounced = (keyword: string) => {
  if (profileSchoolSearchTimeout) {
    clearTimeout(profileSchoolSearchTimeout)
  }
  profileSchoolSearchTimeout = setTimeout(() => {
    handleProfileSchoolSearch(keyword)
  }, 300)
}

const handleProfileSchoolFocus = () => {
  if (profileSchoolOptions.value.length === 0) {
    handleProfileSchoolSearch('')
  }
}

const handleProfileSchoolChange = (schoolName: string) => {
  applyProfileSchoolLevelFromSelection(schoolName)
}

const loadProfileInfo = async () => {
  const [userRes, onboardingRes] = await Promise.all([
    getMe(),
    getProfileOnboarding(),
  ])
  console.log('[Profile] getMe response:', userRes.data)
  console.log('[Profile] avatar value:', userRes.data.data.avatar)
  userName.value = userRes.data.data.username
  userAvatar.value = userRes.data.data.avatar
  userEmail.value = userRes.data.data.email
  studentProfile.value = onboardingRes.data.data.student_profile
  fillProfileForm(studentProfile.value)
}

const beforeAvatarUpload = (file: File) => {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 jpg, png, gif, webp 格式的图片')
    return false
  }
  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('图片大小不能超过 2MB')
    return false
  }
  return true
}

const handleAvatarUpload = async (options: { file: File }) => {
  avatarUploading.value = true
  try {
    const res = await uploadAvatar(options.file)
    userAvatar.value = res.data.data.avatar
    ElMessage.success('头像上传成功')
  } catch (e) {
    console.error('Failed to upload avatar', e)
    ElMessage.error('头像上传失败，请稍后重试')
  } finally {
    avatarUploading.value = false
  }
}

const openProfileEditor = () => {
  fillProfileForm(studentProfile.value)
  profileEditorVisible.value = true
}

const submitProfile = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  const valid = await formEl.validate().catch(() => false)
  if (!valid) return
  profileSubmitting.value = true
  try {
    const res = await updateProfileOnboarding({
      ...profileForm,
      courses: profileForm.courses.map((course) => course.trim()).filter(Boolean),
      school: profileForm.school || null,
      school_level: profileForm.school_level || null,
      preferred_language: profileForm.preferred_language || null,
    })
    studentProfile.value = res.data.data.onboarding.student_profile
    profileEditorVisible.value = false
    ElMessage.success('学习画像资料已更新')
  } catch (e) {
    console.error('Failed to update profile onboarding', e)
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    profileSubmitting.value = false
  }
}

onMounted(() => {
  loadProfileInfo().catch((error) => {
    console.error('Failed to load profile center data', error)
  })
  loadResourceHistory().catch((error) => {
    console.error('Failed to load resource history', error)
  })
})

// 雷达图配置
const radarOption = computed(() => ({
  radar: {
    indicator: [
      { name: '知识基础', max: 100 },
      { name: '学习节奏', max: 100 },
      { name: '认知风格', max: 100 },
      { name: '兴趣偏好', max: 100 },
      { name: '薄弱环节', max: 100 },
      { name: '学习历史', max: 100 }
    ],
    shape: 'polygon',
    radius: '70%',
    axisName: { color: '#64748B', fontSize: 10 },
    splitArea: { show: false },
    splitLine: { lineStyle: { color: '#E2E8F0' } }
  },
  series: [{
    type: 'radar',
    data: [{
      value: [82, 78, 88, 85, 72, 79],
      areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
      lineStyle: { color: '#4F46E5', width: 2 },
      itemStyle: { color: '#4F46E5' },
      symbol: 'none'
    }]
  }]
}))

// 折线图配置
const lineOption = computed(() => ({
  grid: { top: 20, right: 10, bottom: 20, left: 30 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: ['1', '5', '10', '15', '20', '25', '30'],
    axisLine: { lineStyle: { color: '#E2E8F0' } },
    axisLabel: { color: '#94A3B8', fontSize: 10 }
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
    axisLabel: { color: '#94A3B8', fontSize: 10 }
  },
  series: [{
    data: [20, 32, 45, 40, 60, 85, 110],
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: { color: '#4F46E5', width: 3 },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: 'rgba(79, 70, 229, 0.1)' }, { offset: 1, color: 'rgba(79, 70, 229, 0)' }]
      }
    }
  }]
}))

// 资源历史数据
const resourceHistory = ref<GeneratedResourceItem[]>([])
const resourceHistoryLoading = ref(false)

const tableData = computed(() => {
  return resourceHistory.value.map(item => ({
    id: item.id,
    title: item.learning_need || '学习资源',
    status: translateStatus(item.status),
    time: formatTime(item.created_at),
    rawStatus: item.status,
  }))
})

const translateStatus = (status: string) => {
  const map: Record<string, string> = {
    completed: '已完成',
    pending: '生成中',
    processing: '生成中',
    failed: '失败',
  }
  return map[status] || status
}

const formatTime = (time: string | null) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  const timeFormatter = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const monthDayFormatter = new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric' })
  const rtf = new Intl.RelativeTimeFormat('zh-CN', { numeric: 'auto' })

  if (days === 0) {
    return `今天 ${timeFormatter.format(date)}`
  } else if (days === 1) {
    return `昨天 ${timeFormatter.format(date)}`
  } else if (days < 7) {
    return rtf.format(-days, 'day')
  }
  return monthDayFormatter.format(date)
}

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true
  try {
    const res = await getGeneratedResources(20)
    resourceHistory.value = res.data.data
  } catch (e) {
    console.error('Failed to load resource history', e)
  } finally {
    resourceHistoryLoading.value = false
  }
}

const viewResourceDetail = (row: { id: number }) => {
  router.push({ name: 'ResourceDetail', params: { id: row.id } })
}

const getStatusType = (status: string) => {
  if (status === '已完成') return 'success'
  if (status === '生成中') return 'primary'
  if (status === '失败') return 'danger'
  return 'info'
}
</script>

<style scoped>
.profile-dashboard {
  padding: 30px;
  background-color: #F8FAFC;
  min-height: 100%;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}

.bento-container {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.bento-card {
  background: #FFFFFF;
  border-radius: 24px;
  padding: 24px;
  border: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
}

.bento-span-2 {
  grid-column: span 2;
}

.bento-span-4 {
  grid-column: span 4;
}

@media (max-width: 1200px) {
  .bento-container {
    grid-template-columns: repeat(2, 1fr);
  }
  .bento-span-4 {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .bento-container {
    grid-template-columns: 1fr;
  }
  .bento-span-2, .bento-span-4 {
    grid-column: span 1;
  }
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-title, .card-header-flex h4 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1E293B;
  display: flex;
  align-items: center;
  gap: 8px;
}

.link-text {
  font-size: 0.8rem;
  color: #3B82F6;
  cursor: pointer;
}

/* User Card */
.user-header { display: flex; align-items: center; gap: 20px; margin-bottom: 24px; position: relative; }
.avatar-uploader { cursor: pointer; }
.avatar-box {
  width: 72px; height: 72px; background: #EEF2FF; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 2.2rem; color: #4F46E5;
  position: relative; overflow: hidden; transition: background-color 0.3s;
}
.avatar-box:hover { background: #E0E7FF; }
.avatar-box.has-avatar { background: transparent; }
.avatar-image { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
.avatar-upload-overlay {
  position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center; opacity: 0;
  transition: opacity 0.3s; border-radius: 50%;
}
.avatar-box:hover .avatar-upload-overlay { opacity: 1; }
.avatar-upload-overlay .el-icon { color: white; font-size: 1.5rem; }
.user-info h3 { margin: 0; font-size: 1.3rem; font-weight: 800; }
.user-info .email-text { margin: 2px 0 0; font-size: 0.8rem; color: #94A3B8; }
.user-info .major { margin: 4px 0 8px; font-size: 0.9rem; color: #64748B; }
.tags { display: flex; gap: 8px; }
.tag { font-size: 0.75rem; padding: 3px 10px; background: #F1F5F9; color: #475569; border-radius: 6px; }
.edit-btn { position: absolute; right: 0; top: 0; }
.w-full { width: 100%; }

.user-stats { display: flex; justify-content: space-between; padding-top: 20px; border-top: 1px solid #F1F5F9; margin-top: auto;}
.stat-item { text-align: center; }
.stat-val { font-size: 1.4rem; font-weight: 800; color: #0F172A; }
.stat-label { font-size: 0.75rem; color: #94A3B8; margin-top: 2px; }

/* Radar & Trend */
.radar-container {
  height: 220px;
  width: 100%;
  flex: 1;
}

.trend-chart-container {
  height: 220px;
  width: 100%;
  flex: 1;
}

/* Performance */
.perf-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  justify-content: center;
}

.perf-box {
  display: flex;
  align-items: center;
  gap: 15px;
  background: #F8FAFC;
  padding: 16px;
  border-radius: 16px;
}

.perf-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
}

.bg-blue-light {
  background: #EFF6FF;
}

.bg-green-light {
  background: #ECFDF5;
}

.text-blue {
  color: #3B82F6;
}

.text-green {
  color: #10B981;
}

/* Profile Info */
.profile-info-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  flex: 1;
  justify-content: center;
}

.profile-info-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #F1F5F9;
}

.profile-info-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.profile-info-row span {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748B;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.profile-info-row strong {
  color: #0F172A;
  font-size: 0.88rem;
  line-height: 1.5;
  text-align: right;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.profile-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

:deep(.profile-form-grid .el-select) {
  width: 100%;
}

.school-level-tag {
  margin-left: 8px;
  font-size: 0.75rem;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 6px;
  border-radius: 4px;
}

.school-level-note {
  margin-top: 8px;
  font-size: 0.82rem;
  color: #64748B;
}

.school-level-note span {
  color: #2563EB;
  font-weight: 700;
}

.profile-editor-dialog :deep(.el-dialog) {
  border-radius: 20px;
  overflow: hidden;
}

.profile-editor-dialog :deep(.el-dialog__body) {
  background: #F8FAFC;
  padding: 22px 24px;
}

.profile-form-section {
  padding: 18px;
  margin-bottom: 16px;
  border-radius: 18px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
}

.profile-form-section:last-child {
  margin-bottom: 0;
}

.profile-form-section.optional {
  background: #FCFCFD;
}

.profile-form-section-head {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F1F5F9;
}

.profile-form-section-head span {
  color: #4F46E5;
  font-size: 0.72rem;
  font-weight: 900;
  letter-spacing: 0;
}

.profile-form-section-head h5 {
  margin: 6px 0 4px;
  color: #0F172A;
  font-size: 1rem;
  line-height: 1.35;
}

.profile-form-section-head p {
  margin: 0;
  color: #64748B;
  font-size: 0.82rem;
  line-height: 1.55;
}

.profile-editor-dialog :deep(.el-input__wrapper),
.profile-editor-dialog :deep(.el-select__wrapper),
.profile-editor-dialog :deep(.el-textarea__inner) {
  min-height: 42px;
  border-radius: 12px;
}

@media (max-width: 720px) {
  .profile-form-grid {
    grid-template-columns: 1fr;
  }
}

/* Recent Record */
.recent-card {
  justify-content: center;
}
.recent-record {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-top: 10px;
}

.record-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: #FEF2F2;
  color: #EF4444;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
}

.record-info h5 {
  margin: 0 0 5px 0;
  font-size: 1rem;
  font-weight: 600;
}

.meta-tag {
  font-size: 0.75rem;
  color: #64748B;
  background: #F1F5F9;
  padding: 4px 10px;
  border-radius: 6px;
}

.record-progress {
  margin-top: 24px;
}

.prog-text {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #94A3B8;
  margin-top: 8px;
  font-weight: 500;
}

.task-title-cell {
  font-weight: 600;
  color: #1E293B;
}

.custom-tag {
  border-radius: 6px;
}
</style>
