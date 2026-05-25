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
            <div class="stat-val">{{ dynamicStats.completedCourses }}</div>
            <div class="stat-label">已完成课程</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-green"><DocumentCopy /></el-icon>
            <div class="stat-val">{{ dynamicStats.generatedResources }}</div>
            <div class="stat-label">生成资源数</div>
          </div>
          <div class="stat-item">
            <el-icon class="text-orange"><StarFilled /></el-icon>
            <div class="stat-val">{{ dynamicStats.compositeScore }}<small>分</small></div>
            <div class="stat-label">综合评分</div>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-2 history-card">
        <div class="card-header-flex">
          <h4 class="card-title"><el-icon class="text-blue"><Cpu /></el-icon> 资源生成历史</h4>
          <el-radio-group v-model="historyFilter" size="small" aria-label="资源过滤">
            <el-radio-button label="全部" />
            <el-radio-button label="已完成" />
          </el-radio-group>
        </div>

        <el-table
            :data="filteredTableData"
            v-loading="resourceHistoryLoading"
            height="260"
            style="width: 100%"
            :header-cell-style="{background:'#F8FAFC', color:'#64748B'}"
        >
          <el-table-column label="任务名称 / 学习主题" min-width="150" show-overflow-tooltip>
            <template #default="scope">
              <div class="task-title-cell">
                <span>{{ scope.row.title }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small" class="custom-tag">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="100" />
          <el-table-column label="操作" width="60" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="viewResourceDetail(scope.row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
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
            <div v-if="studentProfile.courses && studentProfile.courses.length > 0" class="course-display-wrapper">
              <strong class="course-single-title" :title="studentProfile.courses[0]">{{ studentProfile.courses[0] }}</strong>
              <el-popover
                v-if="studentProfile.courses.length > 1"
                placement="top"
                :width="220"
                trigger="hover"
                popper-class="course-popover"
              >
                <template #reference>
                  <el-button link type="primary" class="view-all-courses-btn">
                    (共{{ studentProfile.courses.length }}门)
                  </el-button>
                </template>
                <div class="all-courses-popover-content">
                  <div class="popover-title">
                    <el-icon><VideoPlay /></el-icon> 正在学习的全部课程
                  </div>
                  <div class="popover-course-list">
                    <div v-for="(c, idx) in studentProfile.courses" :key="c" class="popover-course-item">
                      <span class="course-number">{{ idx + 1 }}.</span>
                      <span class="course-name">{{ c }}</span>
                    </div>
                  </div>
                </div>
              </el-popover>
            </div>
            <strong v-else>未填写</strong>
          </div>

          <div class="profile-info-row">
            <span><el-icon><Cpu /></el-icon> 常用语言</span>
            <strong>{{ studentProfile.preferred_language || '未填写' }}</strong>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-2 radar-card">
        <div class="card-header-flex">
          <h4>学习画像分析 <el-icon class="info-icon"><InfoFilled /></el-icon></h4>
        </div>
        <div style="display: flex; gap: 16px; width: 100%; height: 220px;">
          <div class="radar-container" style="flex: 1; min-height: 0;">
            <v-chart class="chart" :option="radarOption" autoresize />
          </div>
          <div class="pie-container" style="flex: 1; min-height: 0; width: 100%;">
            <v-chart class="chart" :option="pieOption" autoresize />
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
              <span class="label">区间学习时长</span>
              <span class="value">
                {{ formatDurationValue(learningStats?.total_seconds || 45600) }}<small>{{ formatDurationUnit(learningStats?.total_seconds || 45600) }}</small>
              </span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-green-light"><el-icon class="text-green"><Checked /></el-icon></div>
            <div class="perf-data">
              <span class="label">完成任务</span>
              <span class="value">{{ dynamicStats.completedTasks }} <small>个</small></span>
            </div>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-4 trend-section">
        <div class="card-header-flex">
          <h4 class="card-title">学习成长趋势（按课程）</h4>

          <div class="trend-course-selector">
            <template v-if="studentProfile.courses && studentProfile.courses.length > 1">
              <el-select v-model="selectedTrendCourse" size="small" style="width: 150px" placeholder="选择课程">
                <el-option v-for="c in studentProfile.courses" :key="c" :label="c" :value="c" />
              </el-select>
            </template>
            <template v-else-if="studentProfile.courses && studentProfile.courses.length === 1">
              <el-tag type="primary" effect="light" size="small" class="single-course-tag">
                <el-icon><VideoPlay /></el-icon> {{ studentProfile.courses[0] }}
              </el-tag>
            </template>
            <template v-else>
              <span class="no-course-text">暂无在学课程</span>
            </template>
          </div>
        </div>
        <div class="trend-chart-container">
          <v-chart class="chart" :option="lineOption" autoresize />
        </div>
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
            </template>
            <template v-else-if="currentEditorStep === 2">
              <el-button class="step-btn" @click="currentEditorStep = 1">
                <el-icon class="el-icon--left"><ArrowLeft /></el-icon> 上一步
              </el-button>
              <el-button type="primary" class="save-btn" :loading="profileSubmitting" @click="submitProfile(profileFormRef)">
                保存 <el-icon class="el-icon--right"><Check /></el-icon>
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
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import {
  InfoFilled, Timer, Checked, VideoPlay, Search, Check, ArrowRight, ArrowLeft
} from '@element-plus/icons-vue'
import { getMe, uploadAvatar } from '@/api/auth'
import {
  getProfileOnboarding, updateProfileOnboarding, getGeneratedResources,
  searchSchools, getProfileScore, getLearningTimeStats
} from '@/api/ai'
import type {
  ProfileOnboardingUpdate, StudentProfileData, GeneratedResourceItem,
  SchoolItem, ProfileScoreData, LearningTimeStats
} from '@/api/ai'

use([CanvasRenderer, RadarChart, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const route = useRoute()

const timeRange = ref('7')
const historyFilter = ref('全部')
const userName = ref('AI 学习者')
const userEmail = ref<string | null>('user@example.com')
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const currentEditorStep = ref(1)
const profileSubmitting = ref(false)
const profileFormRef = ref<FormInstance>()
const profileSchoolOptions = ref<SchoolItem[]>([])
const learningStats = ref<LearningTimeStats | null>(null)
const selectedTrendCourse = ref<string>('')
const resourceHistoryLoading = ref(false)

const studentProfile = ref<StudentProfileData & { learning_duration_total?: number }>({
  education_level: '本科',
  grade: '大三',
  major: '人工智能',
  courses: ['深度学习', '计算机视觉', 'Python高级编程'],
  learning_goal: '大厂求职面试',
  school: '测试大学',
  school_level: '双一流',
  preferred_language: 'Python',
  learning_duration_total: 45600
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

const resourceHistory = ref<GeneratedResourceItem[]>([
  { id: 1, learning_need: '深度学习核心概念', status: 'completed', resource_types: [], created_at: new Date().toISOString(), updated_at: null },
  { id: 2, learning_need: 'Python 高级编程指南', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000).toISOString(), updated_at: null },
  { id: 3, learning_need: '计算机视觉中的CNN', status: 'pending', resource_types: [], created_at: new Date(Date.now() - 86400000 * 2).toISOString(), updated_at: null },
  { id: 4, learning_need: '数据结构：二叉树遍历', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 3).toISOString(), updated_at: null },
  { id: 5, learning_need: '考研复试英语口语准备', status: 'failed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 4).toISOString(), updated_at: null },
  { id: 6, learning_need: 'Transformer 模型解析', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 5).toISOString(), updated_at: null },
  { id: 7, learning_need: '操作系统：进程与线程', status: 'completed', resource_types: [], created_at: new Date(Date.now() - 86400000 * 6).toISOString(), updated_at: null },
])

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
  '大一', '大二', '大三', '大四',
  '研一', '研二', '研三',
  '博一', '博二', '博三',
  '高职一年级', '高职二年级', '高职三年级'
]
const PRESET_LANGUAGES = [
  'Python', 'Java', 'C/C++', 'Go', 'Rust', 'JavaScript', 'TypeScript',
  'SQL', 'Shell', 'Kotlin', 'Swift', 'PHP', 'HTML/CSS'
]

const profileRules: FormRules<ProfileOnboardingUpdate> = {
  school: [{ required: true, message: '请选择或填写院校', trigger: 'change' }],
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

const radarValuesList = computed(() => {
  const dimensionMap: Record<string, number> = {
    knowledge_foundation: 0,
    learning_goal: 1,
    cognitive_style: 2,
    weakness_points: 3,
    practice_ability: 4,
    interaction_preference: 5,
  }

  const scores = profileScoreData.value?.metrics?.dimension_scores || {}
  const vals = [75, 85, 68, 60, 82, 90]

  for (const [key, index] of Object.entries(dimensionMap)) {
    const score = scores[key]
    if (score !== null && score !== undefined) {
      vals[index] = score
    }
  }
  return vals
})

const dynamicStats = computed(() => {
  const avgScore = Math.round(radarValuesList.value.reduce((a, b) => a + b, 0) / 6)
  const completedResourcesCount = resourceHistory.value.filter(r => r.status === 'completed').length
  const totalCourses = studentProfile.value.courses?.length || 0

  return {
    compositeScore: avgScore,
    generatedResources: resourceHistory.value.length > 0 ? resourceHistory.value.length : 12,
    completedCourses: totalCourses > 0 ? totalCourses : 3,
    completedTasks: completedResourcesCount > 0 ? completedResourcesCount : 8
  }
})

const radarOption = computed(() => {
  return {
    radar: {
      indicator: [
        { name: `知识基础 ${radarValuesList.value[0]}`, max: 100 },
        { name: `学习目标 ${radarValuesList.value[1]}`, max: 100 },
        { name: `认知风格 ${radarValuesList.value[2]}`, max: 100 },
        { name: `薄弱点 ${radarValuesList.value[3]}`, max: 100 },
        { name: `实践能力 ${radarValuesList.value[4]}`, max: 100 },
        { name: `交互偏好 ${radarValuesList.value[5]}`, max: 100 },
      ],
      shape: 'polygon',
      radius: '65%',
      axisName: { color: '#64748B', fontSize: 11 },
      splitArea: { show: false },
      splitLine: { lineStyle: { color: '#E2E8F0' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: radarValuesList.value,
        areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
        lineStyle: { color: '#4F46E5', width: 2 },
        itemStyle: { color: '#4F46E5' },
        symbol: 'none'
      }]
    }]
  }
})

const pieOption = computed(() => {
  return {
    tooltip: { trigger: 'item' },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'middle',
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: '#64748B', fontSize: 11 }
    },
    series: [
      {
        name: '能力占比',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: '13', fontWeight: 'bold' }
        },
        labelLine: { show: false },
        data: [
          { value: radarValuesList.value[0], name: '知识基础', itemStyle: { color: '#4F46E5' } },
          { value: radarValuesList.value[1], name: '学习目标', itemStyle: { color: '#10B981' } },
          { value: radarValuesList.value[2], name: '认知风格', itemStyle: { color: '#3B82F6' } },
          { value: radarValuesList.value[3], name: '薄弱点', itemStyle: { color: '#F59E0B' } },
          { value: radarValuesList.value[4], name: '实践能力', itemStyle: { color: '#8B5CF6' } },
          { value: radarValuesList.value[5], name: '交互偏好', itemStyle: { color: '#EC4899' } }
        ]
      }
    ]
  }
})

const lineOption = computed(() => {
  const dates = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    dates.push(`${d.getMonth() + 1}-${d.getDate()}`)
  }

  let mockValues = [0, 0, 0, 0, 0, 0, 0]
  if (selectedTrendCourse.value) {
    const modifier = selectedTrendCourse.value.length % 5
    mockValues = [
      12 + modifier,
      25 + modifier * 2,
      40 + modifier,
      58 + modifier * 3,
      80 + modifier * 2,
      105 + modifier,
      130 + modifier * 4
    ]
  }

  return {
    grid: { top: 30, right: 20, bottom: 25, left: 45 },
    tooltip: {
      trigger: 'axis',
      formatter: `{b} <br/>课程: ${selectedTrendCourse.value || '无'} <br/>掌握度: {c} 分`
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisLabel: { color: '#94A3B8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '掌握度(预测)',
      nameTextStyle: { color: '#94A3B8', fontSize: 10, padding: [0, 0, 0, 10] },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLabel: { color: '#94A3B8', fontSize: 10 }
    },
    series: [{
      name: selectedTrendCourse.value,
      data: mockValues,
      type: 'line',
      smooth: true,
      showSymbol: true,
      symbolSize: 6,
      lineStyle: { color: '#4F46E5', width: 3 },
      itemStyle: { color: '#4F46E5' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: 'rgba(79, 70, 229, 0.15)' }, { offset: 1, color: 'rgba(79, 70, 229, 0)' }]
        }
      }
    }]
  }
})

const tableData = computed(() => {
  return resourceHistory.value.map(item => ({
    id: item.id,
    title: item.learning_need || '学习资源',
    status: translateStatus(item.status),
    time: formatTime(item.created_at),
    rawStatus: item.status,
  }))
})

const filteredTableData = computed(() => {
  if (historyFilter.value === '已完成') {
    return tableData.value.filter(item => item.rawStatus === 'completed')
  }
  return tableData.value
})

watch(() => studentProfile.value.courses, (newCourses) => {
  if (newCourses && newCourses.length > 0) {
    if (!newCourses.includes(selectedTrendCourse.value)) {
      selectedTrendCourse.value = newCourses[0] || ''
    }
  } else {
    selectedTrendCourse.value = ''
  }
}, { immediate: true })

watch(() => profileForm.school, (newVal) => {
  if (!newVal) {
    profileForm.school_level = ''
    return
  }
  const matched = profileSchoolOptions.value.find((s: any) => s.name === newVal)
  profileForm.school_level = matched ? (matched.level || '') : ''
})

watch(() => route.query.action, () => {
  openProfileEditorFromRoute()
})

watch(timeRange, () => {
  loadLearningStats()
})

onMounted(async () => {
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadLearningStats()
  ]).catch(console.error)
  openProfileEditorFromRoute()
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
  
  if (now.getFullYear() > date.getFullYear()) {
    return '去年'
  }
  
  const isToday = date.toDateString() === now.toDateString()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  const isYesterday = date.toDateString() === yesterday.toDateString()

  const timeFormatter = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' })
  const monthDayFormatter = new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' })

  if (isToday) return timeFormatter.format(date)
  if (isYesterday) return '昨天'
  return monthDayFormatter.format(date)
}

const formatDurationValue = (seconds?: number | null) => {
  if (!seconds) return '0'
  if (seconds < 3600) return Math.floor(seconds / 60).toString()
  return (seconds / 3600).toFixed(1)
}

const formatDurationUnit = (seconds?: number | null) => {
  if (!seconds) return 'm'
  if (seconds < 3600) return 'm'
  return 'h'
}

const querySearchMajor = (queryString: string, cb: any) => {
  const results = queryString
      ? PRESET_MAJORS.filter(m => m.toLowerCase().includes(queryString.toLowerCase()))
      : PRESET_MAJORS
  cb(results.map(m => ({ value: m })))
}

const querySearchSchool = async (queryString: string, cb: any) => {
  if (!queryString) {
    cb([])
    return
  }
  try {
    const res = await searchSchools(queryString, 20)
    profileSchoolOptions.value = res.data.data
    const options = res.data.data.map((school: any) => ({
      value: school.name,
      level: school.level
    }))
    cb(options)
  } catch (e) {
    cb([])
  }
}

const handleSchoolSelect = (item: any) => {
  profileForm.school_level = item.level || ''
}

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
  try {
    const [userRes, onboardingRes, scoreRes] = await Promise.all([
      getMe(),
      getProfileOnboarding(),
      getProfileScore(),
    ])
    userName.value = userRes.data.data.username
    userAvatar.value = userRes.data.data.avatar
    userEmail.value = userRes.data.data.email
    studentProfile.value = onboardingRes.data.data.student_profile
    profileScoreData.value = scoreRes.data.data
  } catch (e) {
    console.warn('后端 API 未连接，个人资料已使用前端 Mock 数据。')
  } finally {
    fillProfileForm(studentProfile.value)
  }
}

const loadLearningStats = async () => {
  try {
    const days = parseInt(timeRange.value) || 7
    const res = await getLearningTimeStats(days)
    learningStats.value = res.data.data
  } catch (e) {
    console.warn('后端 API 未连接，学习时长统计已使用前端 Mock 数据。')
  }
}

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true
  try {
    const res = await getGeneratedResources(20)
    if (res.data.data && res.data.data.length > 0) {
      resourceHistory.value = res.data.data
    }
  } catch (e) {
    console.warn('后端 API 未连接，资源历史已使用前端 Mock 数据。')
  } finally {
    resourceHistoryLoading.value = false
  }
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
    await loadProfileInfo()
  } catch (e) {
    console.error('Failed to update profile onboarding', e)
    ElMessage.error('保存失败，当前为无后端演示模式')
    Object.assign(studentProfile.value, profileForm)
    profileEditorVisible.value = false
  } finally {
    profileSubmitting.value = false
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
  padding: var(--space-8); background-color: var(--color-bg); min-height: 100%; font-family: var(--font-sans);
}
.bento-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-6); }
.bento-card { background: var(--color-surface); border-radius: 8px; padding: var(--space-6); border: 1px solid var(--color-border); display: flex; flex-direction: column; }
.bento-span-2 { grid-column: span 2; }
.bento-span-4 { grid-column: span 4; }

/* Grid 响应式收缩 */
@media (max-width: 1200px) {
  .bento-container { grid-template-columns: repeat(2, 1fr); }
  .bento-span-4 { grid-column: span 2; }
}
@media (max-width: 768px) {
  .bento-container { grid-template-columns: 1fr; }
  .bento-span-2, .bento-span-4 { grid-column: span 1; }
}

.card-header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); }
.card-title, .card-header-flex h4 { margin: 0; font-size: var(--text-md); font-weight: var(--weight-bold); color: var(--color-text-strong); display: flex; align-items: center; gap: var(--space-2); }
.link-text { font-size: var(--text-xs); color: var(--color-info); cursor: pointer; }

/* Course selector styles */
.trend-course-selector { display: flex; align-items: center; gap: 10px; }
.single-course-tag { display: flex; align-items: center; gap: 4px; font-weight: var(--weight-semibold); border-radius: var(--radius-sm); }
.no-course-text { font-size: 12px; color: var(--color-text-muted); }

/* User Card */
.user-header { display: flex; align-items: center; gap: var(--space-5); margin-bottom: var(--space-6); position: relative; }
.avatar-uploader { cursor: pointer; }
.avatar-box { width: 72px; height: 72px; background: var(--color-primary-soft); border-radius: var(--radius-pill); display: flex; align-items: center; justify-content: center; font-size: 2.2rem; color: var(--color-primary); position: relative; overflow: hidden; transition: background-color var(--transition-slow); }
.avatar-box:hover { background: var(--color-primary-soft); }
.avatar-box.has-avatar { background: transparent; }
.avatar-image { width: 100%; height: 100%; object-fit: cover; border-radius: var(--radius-pill); }
.avatar-upload-overlay { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity var(--transition-slow); border-radius: var(--radius-pill); }
.avatar-box:hover .avatar-upload-overlay { opacity: 1; }
.avatar-upload-overlay .el-icon { color: white; font-size: 1.5rem; }
.user-info h3 { margin: 0; font-size: 1.3rem; font-weight: var(--weight-extrabold); }
.user-info .email-text { margin: 2px 0 0; font-size: var(--text-xs); color: var(--color-text-faint); }
.user-info .major { margin: var(--space-1) 0 var(--space-2); font-size: 0.9rem; color: var(--color-text-muted); }
.tags { display: flex; gap: var(--space-2); }
.tag { font-size: 0.75rem; padding: 3px var(--space-3); background: var(--color-surface-hover); color: var(--color-text-secondary); border-radius: var(--radius-sm); }
.edit-btn { position: absolute; right: 0; top: 0; }
.w-full { width: 100%; }

.user-stats { display: flex; justify-content: space-between; padding-top: var(--space-5); border-top: 1px solid var(--color-surface-hover); margin-top: auto;}
.stat-item { text-align: center; }
.stat-val { font-size: 1.4rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.stat-label { font-size: 0.75rem; color: var(--color-text-faint); margin-top: 2px; }

/* Radar & Trend */
.radar-container { height: 220px; width: 100%; flex: 1; }
.trend-chart-container { height: 220px; width: 100%; flex: 1; }

/* Performance */
.perf-grid { display: flex; flex-direction: column; gap: var(--space-4); flex: 1; justify-content: center; }
.perf-box { display: flex; align-items: center; gap: 15px; background: var(--color-bg); padding: var(--space-4); border-radius: var(--radius-xl); }
.perf-icon { width: 44px; height: 44px; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; }
.bg-blue-light { background: var(--color-info-soft); }
.bg-green-light { background: var(--color-success-soft); }
.text-blue { color: var(--color-info); }
.text-green { color: var(--color-success); }
.perf-data .label { font-size: var(--text-xs); color: var(--color-text-muted); display: block; margin-bottom: 2px; }
.perf-data .value { font-size: 1.1rem; font-weight: var(--weight-bold); color: var(--color-text-strong); }

/* Profile Info List */
.profile-info-list { display: flex; flex-direction: column; gap: 18px; flex: 1; justify-content: center; }
.profile-info-row { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); padding-bottom: 14px; border-bottom: 1px solid var(--color-surface-hover); }
.profile-info-row:last-child { border-bottom: none; padding-bottom: 0; }
.profile-info-row span { display: flex; align-items: center; gap: var(--space-2); color: var(--color-text-muted); font-size: 0.85rem; flex-shrink: 0; }
.profile-info-row strong { color: var(--color-text); font-size: 0.88rem; line-height: 1.5; text-align: right; font-weight: var(--weight-bold); overflow-wrap: anywhere; }

/* Course Tag display styles */
.course-display-row { align-items: center !important; }
.course-display-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  justify-content: flex-end;
  max-width: 65%;
}
.course-single-title {
  color: var(--color-text);
  font-size: 0.88rem;
  font-weight: var(--weight-bold);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.view-all-courses-btn {
  font-size: 0.75rem !important;
  color: var(--color-primary) !important;
  padding: 0 !important;
  margin-left: 2px !important;
  height: auto !important;
  font-weight: var(--weight-semibold);
}
.view-all-courses-btn:hover {
  opacity: 0.8;
  text-decoration: underline;
}

.task-title-cell { font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.custom-tag { border-radius: var(--radius-sm); }

/* 滚动条优化 */
.history-card :deep(.el-scrollbar__bar.is-vertical) { width: 6px !important; }
.history-card :deep(.el-scrollbar__thumb) { background-color: #CBD5E1 !important; border-radius: 4px; }
.history-card :deep(.el-scrollbar__thumb:hover) { background-color: #94A3B8 !important; }

/* Compact dialog styles */
.profile-editor-dialog :deep(.el-dialog) {
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-xl);
  margin-top: 5vh !important;
}

.profile-editor-dialog :deep(.el-dialog__header) {
  padding: 0; margin: 0; border-bottom: none;
}

.profile-editor-dialog :deep(.el-dialog__headerbtn) {
  top: 18px; right: var(--space-5); font-size: 1.2rem; color: var(--color-text-muted); z-index: 10;
}

.dialog-custom-header {
  padding: var(--space-6) var(--space-8) var(--space-3);
  text-align: center;
}
.dialog-title {
  margin: 0 0 var(--space-1); font-size: var(--text-lg); font-weight: var(--weight-extrabold); color: var(--color-text);
}
.dialog-subtitle {
  margin: 0; font-size: 0.85rem; color: var(--color-text-muted); line-height: 1.4;
}

/* Step indicator */
.editor-step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-5);
}
.editor-step-indicator .step-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-faint);
}
.editor-step-indicator .step-item.is-active {
  color: var(--color-primary);
}
.editor-step-indicator .step-icon {
  width: var(--space-6);
  height: var(--space-6);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-text-faint);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  background-color: var(--color-surface);
}
.editor-step-indicator .step-item.is-active .step-icon {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.editor-step-indicator .step-text {
  font-size: 13px;
  font-weight: var(--weight-semibold);
}
.editor-step-indicator .step-line {
  width: 80px;
  height: 1px;
  background-color: var(--color-border);
}
.editor-step-indicator .step-line.is-active {
  background-color: var(--color-primary);
}

.editor-step-content {
  animation: fadeIn var(--transition-slow);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

.profile-editor-dialog :deep(.el-dialog__body) {
  background: var(--color-surface); padding: 0 var(--space-8) var(--space-2);
}

.custom-profile-form { display: flex; flex-direction: column; gap: var(--space-3); }
.profile-form-section {
  padding: 14px var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--color-surface); border: 1px solid var(--color-border);
}
.profile-form-section-head {
  display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3);
}

.section-badge {
  font-size: 0.75rem; font-weight: var(--weight-bold); padding: 2px var(--space-2); border-radius: var(--space-1);
}
.required-badge { color: var(--color-primary); background: var(--color-primary-soft); }
.bg-badge { color: var(--color-primary); background: var(--color-primary-soft); }
.section-title { margin: 0; color: var(--color-text); font-size: 0.95rem; font-weight: var(--weight-extrabold); }

.profile-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--space-4); }

.custom-label { font-size: var(--text-xs); font-weight: var(--weight-semibold); color: var(--color-text-secondary); display: flex; align-items: center; }
.req-star { color: var(--color-danger); margin-right: var(--space-1); }
.profile-editor-dialog :deep(.el-form-item) { margin-bottom: var(--space-3); }

.profile-editor-dialog :deep(.el-input__wrapper),
.profile-editor-dialog :deep(.el-select__wrapper) {
  min-height: 36px !important;
  border-radius: var(--radius-md); box-shadow: none !important; border: 1px solid var(--color-border); background: var(--color-surface);
}
.profile-editor-dialog :deep(.el-input__inner) { font-size: 0.85rem; }

.school-level-tag { margin-left: var(--space-2); font-size: 0.7rem; color: var(--color-text-muted); background: var(--color-surface-hover); padding: 2px var(--space-2); border-radius: var(--space-1); }

.profile-editor-dialog :deep(.el-dialog__footer) {
  padding: 10px var(--space-8) var(--space-6); border-top: none;
}
.dialog-custom-footer {
  display: flex; justify-content: space-between; align-items: center;
}
.footer-hint { display: flex; align-items: center; gap: var(--space-2); color: var(--color-text-muted); font-size: var(--text-xs); }
.footer-hint .el-icon { color: var(--color-primary); font-size: 0.9rem; }
.footer-actions { display: flex; gap: 10px; }

.step-btn, .save-btn {
  border-radius: var(--radius-md); height: 38px; padding: 0 var(--space-5); font-weight: var(--weight-semibold); font-size: 0.85rem;
}
.step-btn { background: var(--color-surface); color: var(--color-text-secondary); border: 1px solid var(--color-border-hover); }
.step-btn:hover { background: var(--color-bg); color: var(--color-text); border-color: var(--color-text-faint); }
.save-btn { background: var(--color-primary); border: none; color: white;}
.save-btn:hover { background: var(--color-primary-hover); transform: translateY(-1px); }

.mt-3 { margin-top: var(--space-3); }

/* 让 ECharts 画布填满外部容器 */
.chart {
  width: 100%;
  height: 100%;
  min-height: 220px;
}

.trend-chart-container {
  height: 220px;
  min-height: 220px;
  width: 100%;
  flex: 1;
}

.radar-container {
  height: 220px;
  min-height: 220px;
  width: 100%;
  flex: 1;
}
@media (max-width: 720px) {
  .profile-form-grid { grid-template-columns: 1fr; gap: 0; }
  .dialog-custom-footer { flex-direction: column; gap: var(--space-3); align-items: flex-start; }
  .editor-step-indicator .step-line { width: 40px; }
}
</style>

<style>
/* Global styles for teleported popover */
.course-popover {
  padding: 12px !important;
  border-radius: 8px !important;
  box-shadow: var(--shadow-lg) !important;
  border: 1px solid var(--color-border) !important;
  background: var(--color-surface) !important;
}
.all-courses-popover-content .popover-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-strong);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 6px;
}
.all-courses-popover-content .popover-course-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.all-courses-popover-content .popover-course-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  padding: 6px 8px;
  border-radius: 4px;
  background-color: var(--color-surface-hover);
  transition: all var(--transition-fast);
}
.all-courses-popover-content .popover-course-item:hover {
  background-color: var(--color-primary-soft);
  color: var(--color-primary);
}
.all-courses-popover-content .course-number {
  font-weight: 700;
  color: var(--color-text-muted);
  font-size: 0.75rem;
}
.all-courses-popover-content .course-name {
  font-weight: 600;
}
</style>