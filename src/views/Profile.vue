<template>
  <div class="profile-dashboard">
    <div class="bento-container">
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
            <div class="stat-val">
              {{ formatDurationValue(studentProfile.learning_duration_total) }}<small>{{ formatDurationUnit(studentProfile.learning_duration_total) }}</small>
            </div>
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
              <span class="value">
                {{ formatDurationValue(studentProfile.learning_duration_total) }}<small>{{ formatDurationUnit(studentProfile.learning_duration_total) }}</small>
              </span>
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

      <div class="bento-card profile-info-card">
        <div class="card-header-flex">
          <h4 class="card-title">学习画像资料</h4>
        </div>
        <div class="profile-info-list">
          <div class="profile-info-row">
            <span><el-icon><Reading /></el-icon> 学历层次</span>
            <strong>{{ studentProfile.education_level || '未填写' }}</strong>
          </div>
          <div class="profile-info-row">
            <span><el-icon><UserFilled /></el-icon> 专业</span>
            <strong>{{ studentProfile.major || '未填写' }}</strong>
          </div>

          <div class="profile-info-row course-display-row">
            <span><el-icon><VideoPlay /></el-icon> 正在学习</span>
            <div v-if="studentProfile.courses && studentProfile.courses.length > 0" class="course-tags-display">
              <span v-for="c in studentProfile.courses" :key="c" class="c-tag">{{ c }}</span>
            </div>
            <strong v-else>未填写</strong>
          </div>

          <div class="profile-info-row">
            <span><el-icon><Cpu /></el-icon> 常用语言</span>
            <strong>{{ studentProfile.preferred_language || '未填写' }}</strong>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-2 trend-section">
        <div class="card-header-flex">
          <h4 class="card-title">学习成长趋势</h4>
        </div>
        <div class="trend-chart-container">
          <v-chart class="chart" :option="lineOption" autoresize />
        </div>
      </div>

      <div class="bento-card radar-card">
        <div class="card-header-flex">
          <h4>学习画像 <el-icon class="info-icon"><InfoFilled /></el-icon></h4>
        </div>
        <div class="radar-container">
          <v-chart class="chart" :option="radarOption" autoresize />
        </div>
      </div>

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
        width="660px"
        :close-on-click-modal="false"
        class="profile-editor-dialog compact-dialog"
        :show-close="true"
        align-center
    >
      <template #header>
        <div class="dialog-custom-header">
          <h2 class="dialog-title">编辑学习画像资料</h2>
          <p class="dialog-subtitle">完善你的基础信息，帮助系统生成更贴合你的学习资源与学习路径</p>

          <div class="editor-step-indicator">
            <div class="step-item" :class="{ 'is-active': currentEditorStep >= 1 }">
              <div class="step-icon">
                <el-icon v-if="currentEditorStep === 2"><Check /></el-icon>
                <span v-else>1</span>
              </div>
              <div class="step-text">专业与目标</div>
            </div>
            <div class="step-line" :class="{ 'is-active': currentEditorStep === 2 }"></div>
            <div class="step-item" :class="{ 'is-active': currentEditorStep === 2 }">
              <div class="step-icon">2</div>
              <div class="step-text">学校与阶段</div>
            </div>
          </div>
        </div>
      </template>

      <el-form
          ref="profileFormRef"
          :model="profileForm"
          :rules="profileRules"
          label-position="top"
          class="custom-profile-form"
          hide-required-asterisk
      >
        <div v-show="currentEditorStep === 1" class="editor-step-content">
          <div class="profile-form-section">
            <div class="profile-form-section-head">
              <div class="section-badge required-badge">必填 01</div>
              <h5 class="section-title">专业与课程</h5>
<!--              <span class="section-desc-inline">先确定专业背景和正在学习的课程。</span>-->
            </div>

            <div class="profile-form-grid">
              <el-form-item prop="major">
                <template #label><span class="custom-label"><span class="req-star">*</span> 专业</span></template>
                <el-autocomplete
                    v-model="profileForm.major"
                    :fetch-suggestions="querySearchMajor"
                    placeholder="可以直接输入或选择"
                    clearable
                    class="w-full"
                >
                  <template #default="{ item }">
                    <span>{{ item.value }}</span>
                  </template>
                </el-autocomplete>
              </el-form-item>

              <el-form-item prop="courses">
                <template #label><span class="custom-label"><span class="req-star">*</span> 正在学习的课程</span></template>
                <el-select
                    v-model="profileForm.courses"
                    multiple
                    filterable
                    allow-create
                    default-first-option
                    placeholder="输入课程名后【按回车】即可添加"
                    class="w-full"
                >
                  <el-option v-for="course in PRESET_COURSES" :key="course" :label="course" :value="course" />
                </el-select>
              </el-form-item>
            </div>
          </div>

          <div class="profile-form-section mt-3">
            <div class="profile-form-section-head">
              <div class="section-badge required-badge">必填 02</div>
              <h5 class="section-title">学习目标</h5>
<!--              <span class="section-desc-inline">目标决定资源和路径生成方向。</span>-->
            </div>

            <el-form-item prop="learning_goal">
              <template #label><span class="custom-label"><span class="req-star">*</span> 当前学习目标</span></template>
              <el-select v-model="profileForm.learning_goal" filterable allow-create default-first-option clearable placeholder="请选择目标，列表没有可直接输入后【按回车】">
                <el-option v-for="goal in PRESET_GOALS" :key="goal" :label="goal" :value="goal" />
              </el-select>
            </el-form-item>
          </div>
        </div>

        <div v-show="currentEditorStep === 2" class="editor-step-content">
          <div class="profile-form-section">
            <div class="profile-form-section-head">
              <div class="section-badge bg-badge">背景 03</div>
              <h5 class="section-title">学校与阶段</h5>
<!--              <span class="section-desc-inline">学校可选；学历和年级用于判断内容难度。</span>-->
            </div>

            <div class="profile-form-grid">
              <el-form-item prop="school">
                <template #label><span class="custom-label"><span class="req-star">*</span> 院校</span></template>
                <el-autocomplete
                    v-model="profileForm.school"
                    :fetch-suggestions="querySearchSchool"
                    placeholder="可以直接输入或搜索"
                    clearable
                    class="w-full"
                    @select="handleSchoolSelect"
                >
                  <template #prefix><el-icon><Search /></el-icon></template>
                  <template #default="{ item }">
                    <span>{{ item.value }}</span>
                    <span v-if="item.level" class="school-level-tag">{{ item.level }}</span>
                  </template>
                </el-autocomplete>
              </el-form-item>

              <el-form-item prop="school_level">
                <template #label><span class="custom-label"><span class="req-star">*</span> 院校层次</span></template>
                <el-select v-model="profileForm.school_level" placeholder="请选择或从院校自动带出" filterable allow-create default-first-option>
                  <el-option v-for="level in PRESET_SCHOOL_LEVELS" :key="level" :label="level" :value="level" />
                </el-select>
              </el-form-item>

              <el-form-item prop="education_level">
                <template #label><span class="custom-label"><span class="req-star">*</span> 学历层次</span></template>
                <el-select v-model="profileForm.education_level" placeholder="请选择学历层次" filterable>
                  <el-option v-for="level in PRESET_EDUCATION_LEVELS" :key="level" :label="level" :value="level" />
                </el-select>
              </el-form-item>

              <el-form-item prop="grade">
                <template #label><span class="custom-label"><span class="req-star">*</span> 年级</span></template>
                <el-select v-model="profileForm.grade" filterable allow-create default-first-option clearable placeholder="请选择年级">
                  <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
                </el-select>
              </el-form-item>

              <el-form-item prop="preferred_language">
                <template #label><span class="custom-label">常用编程语言（选填）</span></template>
                <el-select v-model="profileForm.preferred_language" filterable allow-create default-first-option clearable placeholder="请选择常用语言">
                  <el-option v-for="language in PRESET_LANGUAGES" :key="language" :label="language" :value="language" />
                </el-select>
              </el-form-item>
            </div>
          </div>
        </div>
      </el-form>

      <template #footer>
        <div class="dialog-custom-footer">
          <div class="footer-hint">
            <el-icon><InfoFilled /></el-icon>
            <span>带 <span class="req-star">*</span> 为必填项，完善信息后可获得精准推荐</span>
          </div>
          <div class="footer-actions">
            <template v-if="currentEditorStep === 1">
              <el-button class="step-btn" @click="nextEditorStep(profileFormRef)">
                下一步 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
              <el-button type="primary" class="save-btn" @click="profileEditorVisible = false">取消</el-button>
            </template>
            <template v-else>
              <el-button class="step-btn" @click="currentEditorStep = 1">
                <el-icon class="el-icon--left"><ArrowLeft /></el-icon> 上一步
              </el-button>
              <el-button type="primary" class="save-btn" :loading="profileSubmitting" @click="submitProfile(profileFormRef)">
                保存资料
              </el-button>
            </template>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UserFilled, CircleCheckFilled, Edit, Clock, Reading, DocumentCopy, StarFilled,
  InfoFilled, Timer, Checked, VideoPlay, Cpu, Search, Check, ArrowRight, ArrowLeft
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { getMe, uploadAvatar } from '@/api/auth'
import { getProfileOnboarding, updateProfileOnboarding, getGeneratedResources, searchSchools, getProfileScore } from '@/api/ai'
import type { ProfileOnboardingUpdate, StudentProfileData, GeneratedResourceItem, SchoolItem, ProfileScoreData } from '@/api/ai'

use([CanvasRenderer, RadarChart, LineChart, GridComponent, TooltipComponent])

const router = useRouter()
const route = useRoute()

const timeRange = ref('7')
const historyFilter = ref('全部')
const userName = ref('学习者')
const userEmail = ref<string | null>(null)
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const currentEditorStep = ref(1) // 弹窗阶段控制
const profileSubmitting = ref(false)
const profileFormRef = ref<FormInstance>()
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
const PRESET_SCHOOL_LEVELS = ['985', '211', '双一流', '普通本科', '高职高专', '海外高校', '其他']
const PRESET_GRADES = [
  '大一', '大二', '大三', '大四',
  '研一', '研二', '研三',
  '博一', '博二', '博三',
  '高职一年级', '高职二年级', '高职三年级'
]
const PRESET_LANGUAGES = [
  'Python', 'Java', 'C/C++', 'Go', 'Rust', 'JavaScript', 'TypeScript',
  'SQL', 'Shell', 'Kotlin', 'Swift', 'PHP', 'HTML/CSS'
]

const studentProfile = ref<StudentProfileData & { learning_duration_total?: number }>({
  education_level: null,
  grade: null,
  major: null,
  courses: [],
  learning_goal: null,
  school: null,
  school_level: null,
  preferred_language: null,
  learning_duration_total: 0
})

const profileScoreData = ref<ProfileScoreData | null>(null)

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
  school: [{ required: true, message: '请选择或填写院校', trigger: 'change' }],
  school_level: [{ required: true, message: '请选择院校层次', trigger: 'change' }],
  education_level: [{ required: true, message: '请选择学历层次', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  major: [{ required: true, message: '请填写或选择专业', trigger: 'change' }],
  courses: [{ required: true, type: 'array', min: 1, message: '请至少填写一门课程', trigger: 'change' }],
  learning_goal: [{ required: true, message: '请选择或输入当前学习目标', trigger: 'change' }],
}

const profileHeadline = computed(() => {
  const parts = [studentProfile.value.major, studentProfile.value.education_level, studentProfile.value.school]
      .filter((item): item is string => Boolean(item))
  return parts.length ? parts.join(' · ') : '学习资料待完善'
})

const formatDurationValue = (seconds?: number | null) => {
  if (!seconds) return '0';
  if (seconds < 3600) return Math.floor(seconds / 60).toString();
  return (seconds / 3600).toFixed(1);
}

const formatDurationUnit = (seconds?: number | null) => {
  if (!seconds) return 'm';
  if (seconds < 3600) return 'm';
  return 'h';
}

const querySearchMajor = (queryString: string, cb: any) => {
  const results = queryString
      ? PRESET_MAJORS.filter(m => m.toLowerCase().includes(queryString.toLowerCase()))
      : PRESET_MAJORS;
  cb(results.map(m => ({ value: m })));
}

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
  profileForm.school_level = item.level || '';
}

watch(() => profileForm.school, (newVal) => {
  if (!newVal) {
    profileForm.school_level = '';
    return;
  }
  const matched = profileSchoolOptions.value.find((s: any) => s.name === newVal);
  profileForm.school_level = matched ? (matched.level || '') : '';
})

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

const loadProfileInfo = async () => {
  const [userRes, onboardingRes, scoreRes] = await Promise.all([
    getMe(),
    getProfileOnboarding(),
    getProfileScore(),
  ])
  userName.value = userRes.data.data.username
  userAvatar.value = userRes.data.data.avatar
  userEmail.value = userRes.data.data.email
  studentProfile.value = onboardingRes.data.data.student_profile
  fillProfileForm(studentProfile.value)
  profileScoreData.value = scoreRes.data.data
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
  currentEditorStep.value = 1
  profileEditorVisible.value = true
}

const openProfileEditorFromRoute = () => {
  if (route.query.action === 'edit-profile') {
    openProfileEditor()
  }
}

const nextEditorStep = (formEl: FormInstance | undefined) => {
  if (!formEl) return
  formEl.validateField(['major', 'courses', 'learning_goal'], (valid) => {
    if (valid) {
      currentEditorStep.value = 2
    } else {
      ElMessage.warning('请先完善当前页面的必填项')
    }
  })
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
    } as any)
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

onMounted(async () => {
  await loadProfileInfo().catch(console.error)
  openProfileEditorFromRoute()
  loadResourceHistory().catch(console.error)
})

watch(() => route.query.action, () => {
  openProfileEditorFromRoute()
})

const radarOption = computed(() => {
  // 后端维度名称映射到前端雷达图维度
  const dimensionMap: Record<string, { name: string; index: number }> = {
    knowledge_foundation: { name: '知识基础', index: 0 },
    learning_goal: { name: '学习目标', index: 1 },
    cognitive_style: { name: '认知风格', index: 2 },
    weakness_points: { name: '薄弱环节', index: 3 },
    practice_ability: { name: '实践能力', index: 4 },
    interaction_preference: { name: '交互偏好', index: 5 },
  }

  // 从 API 数据获取评分，如果没有则使用默认值
  const scores = profileScoreData.value?.metrics?.dimension_scores || {}
  const radarValues = [50, 50, 50, 50, 50, 50] // 默认值

  for (const [key, mapping] of Object.entries(dimensionMap)) {
    const score = scores[key]
    if (score !== null && score !== undefined) {
      radarValues[mapping.index] = score
    }
  }

  return {
    radar: {
      indicator: [
        { name: '知识基础', max: 100 },
        { name: '学习目标', max: 100 },
        { name: '认知风格', max: 100 },
        { name: '薄弱环节', max: 100 },
        { name: '实践能力', max: 100 },
        { name: '交互偏好', max: 100 },
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
        value: radarValues,
        areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
        lineStyle: { color: '#4F46E5', width: 2 },
        itemStyle: { color: '#4F46E5' },
        symbol: 'none'
      }]
    }]
  }
})

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

  if (days === 0) return `今天 ${timeFormatter.format(date)}`
  else if (days === 1) return `昨天 ${timeFormatter.format(date)}`
  else if (days < 7) return rtf.format(-days, 'day')
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
  padding: 30px; background-color: #F8FAFC; min-height: 100%; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
}
.bento-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.bento-card { background: #FFFFFF; border-radius: 24px; padding: 24px; border: 1px solid #E2E8F0; display: flex; flex-direction: column; }
.bento-span-2 { grid-column: span 2; }
.bento-span-4 { grid-column: span 4; }

@media (max-width: 1200px) {
  .bento-container { grid-template-columns: repeat(2, 1fr); }
  .bento-span-4 { grid-column: span 2; }
}
@media (max-width: 768px) {
  .bento-container { grid-template-columns: 1fr; }
  .bento-span-2, .bento-span-4 { grid-column: span 1; }
}

.card-header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.card-title, .card-header-flex h4 { margin: 0; font-size: 1.05rem; font-weight: 700; color: #1E293B; display: flex; align-items: center; gap: 8px; }
.link-text { font-size: 0.8rem; color: #3B82F6; cursor: pointer; }

/* User Card */
.user-header { display: flex; align-items: center; gap: 20px; margin-bottom: 24px; position: relative; }
.avatar-uploader { cursor: pointer; }
.avatar-box { width: 72px; height: 72px; background: #EEF2FF; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.2rem; color: #4F46E5; position: relative; overflow: hidden; transition: background-color 0.3s; }
.avatar-box:hover { background: #E0E7FF; }
.avatar-box.has-avatar { background: transparent; }
.avatar-image { width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }
.avatar-upload-overlay { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.3s; border-radius: 50%; }
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
.radar-container { height: 220px; width: 100%; flex: 1; }
.trend-chart-container { height: 220px; width: 100%; flex: 1; }

/* Performance */
.perf-grid { display: flex; flex-direction: column; gap: 16px; flex: 1; justify-content: center; }
.perf-box { display: flex; align-items: center; gap: 15px; background: #F8FAFC; padding: 16px; border-radius: 16px; }
.perf-icon { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; }
.bg-blue-light { background: #EFF6FF; }
.bg-green-light { background: #ECFDF5; }
.text-blue { color: #3B82F6; }
.text-green { color: #10B981; }
.perf-data .label { font-size: 0.8rem; color: #64748B; display: block; margin-bottom: 2px; }
.perf-data .value { font-size: 1.1rem; font-weight: 700; color: #1E293B; }

/* ================= 优化后的 Profile Info ================= */
.profile-info-list { display: flex; flex-direction: column; gap: 18px; flex: 1; justify-content: center; }
.profile-info-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding-bottom: 14px; border-bottom: 1px solid #F1F5F9; }
.profile-info-row:last-child { border-bottom: none; padding-bottom: 0; }
.profile-info-row span { display: flex; align-items: center; gap: 8px; color: #64748B; font-size: 0.85rem; flex-shrink: 0; }
.profile-info-row strong { color: #0F172A; font-size: 0.88rem; line-height: 1.5; text-align: right; font-weight: 700; overflow-wrap: anywhere; }

/* 课程 Tag 显示样式 */
.course-display-row { align-items: flex-start !important; }
.course-tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
  max-width: 65%;
}
.c-tag {
  background-color: #EEF2FF;
  color: #4F46E5;
  font-size: 0.75rem !important;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 700;
  white-space: nowrap;
}

/* Recent Record */
.recent-card { justify-content: center; }
.recent-record { display: flex; gap: 15px; align-items: center; margin-top: 10px; }
.record-icon { width: 48px; height: 48px; border-radius: 16px; background: #FEF2F2; color: #EF4444; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
.record-info h5 { margin: 0 0 5px 0; font-size: 1rem; font-weight: 600; }
.meta-tag { font-size: 0.75rem; color: #64748B; background: #F1F5F9; padding: 4px 10px; border-radius: 6px; }
.record-progress { margin-top: 24px; }
.prog-text { display: flex; justify-content: space-between; font-size: 0.8rem; color: #94A3B8; margin-top: 8px; font-weight: 500; }
.task-title-cell { font-weight: 600; color: #1E293B; }
.custom-tag { border-radius: 6px; }

/* ================= 极致紧凑防滚动弹窗样式 ================= */
.profile-editor-dialog :deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px -10px rgba(0, 0, 0, 0.15);
  margin-top: 5vh !important;
}

.profile-editor-dialog :deep(.el-dialog__header) {
  padding: 0; margin: 0; border-bottom: none;
}

.profile-editor-dialog :deep(.el-dialog__headerbtn) {
  top: 18px; right: 20px; font-size: 1.2rem; color: #64748B; z-index: 10;
}

.dialog-custom-header {
  padding: 24px 32px 12px;
  text-align: center;
}
.dialog-title {
  margin: 0 0 4px; font-size: 1.25rem; font-weight: 800; color: #0F172A;
}
.dialog-subtitle {
  margin: 0; font-size: 0.85rem; color: #64748B; line-height: 1.4;
}

/* 步骤指示器 */
.editor-step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}
.editor-step-indicator .step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9CA3AF;
}
.editor-step-indicator .step-item.is-active {
  color: #4F46E5;
}
.editor-step-indicator .step-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid #9CA3AF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  background-color: #FFFFFF;
}
.editor-step-indicator .step-item.is-active .step-icon {
  border-color: #4F46E5;
  color: #4F46E5;
}
.editor-step-indicator .step-text {
  font-size: 13px;
  font-weight: 600;
}
.editor-step-indicator .step-line {
  width: 80px;
  height: 1px;
  background-color: #E5E7EB;
}
.editor-step-indicator .step-line.is-active {
  background-color: #4F46E5;
}

.editor-step-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.profile-editor-dialog :deep(.el-dialog__body) {
  background: #FFFFFF; padding: 0 32px 8px;
}

.custom-profile-form { display: flex; flex-direction: column; gap: 12px; }
.profile-form-section {
  padding: 14px 16px;
  border-radius: 12px;
  background: #FFFFFF; border: 1px solid #E2E8F0;
}
.profile-form-section-head {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
}
.section-desc-inline {
  color: #64748B; font-size: 0.8rem; margin-left: auto;
}

.section-badge {
  font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.required-badge { color: #4F46E5; background: #EEF2FF; }
.bg-badge { color: #4F46E5; background: #EEF2FF; }
.section-title { margin: 0; color: #0F172A; font-size: 0.95rem; font-weight: 800; }

.profile-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }

.custom-label { font-size: 0.8rem; font-weight: 600; color: #334155; display: flex; align-items: center; }
.req-star { color: #EF4444; margin-right: 4px; }
.profile-editor-dialog :deep(.el-form-item) { margin-bottom: 12px; }

.profile-editor-dialog :deep(.el-input__wrapper),
.profile-editor-dialog :deep(.el-select__wrapper) {
  min-height: 36px !important;
  border-radius: 8px; box-shadow: none !important; border: 1px solid #E2E8F0; background: #FFFFFF;
}
.profile-editor-dialog :deep(.el-input__inner) { font-size: 0.85rem; }

.school-level-tag { margin-left: 8px; font-size: 0.7rem; color: #64748B; background: #F1F5F9; padding: 2px 6px; border-radius: 4px; }

.profile-editor-dialog :deep(.el-dialog__footer) {
  padding: 10px 32px 24px; border-top: none;
}
.dialog-custom-footer {
  display: flex; justify-content: space-between; align-items: center;
}
.footer-hint { display: flex; align-items: center; gap: 6px; color: #64748B; font-size: 0.8rem; }
.footer-hint .el-icon { color: #4F46E5; font-size: 0.9rem; }
.footer-actions { display: flex; gap: 10px; }

.step-btn, .save-btn {
  border-radius: 8px; height: 38px; padding: 0 20px; font-weight: 600; font-size: 0.85rem;
}
.step-btn { background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; }
.step-btn:hover { background: #F8FAFC; color: #0F172A; border-color: #94A3B8; }
.save-btn { background: #4F46E5; border: none; color: white;}
.save-btn:hover { background: #4338CA; transform: translateY(-1px); }

.mt-3 { margin-top: 12px; }

@media (max-width: 720px) {
  .profile-form-grid { grid-template-columns: 1fr; gap: 0; }
  .dialog-custom-footer { flex-direction: column; gap: 12px; align-items: flex-start; }
  .section-desc-inline { display: none; }
  .editor-step-indicator .step-line { width: 40px; }
}
</style>
