<template>
  <main class="profile-page min-h-screen font-sans antialiased text-left">
    <div class="profile-shell">
      <div class="profile-title-row profile-motion-item">
        <div class="title-mark">
          <UserRound class="h-7 w-7" />
        </div>
        <h1>个人中心</h1>
      </div>

      <section class="profile-identity-strip profile-motion-item">
        <div class="identity-panel">
          <div class="identity-inner">
            <Button
              variant="ghost"
              class="avatar-button"
              :disabled="avatarUploading"
              aria-label="更换头像"
              @click="triggerAvatarUpload"
            >
              <input ref="avatarInput" type="file" class="hidden" accept="image/*" @change="onAvatarFileChange" />
              <Avatar class="profile-avatar">
                <AvatarImage v-if="userAvatar" :src="userAvatar" alt="用户头像" />
                <AvatarFallback>{{ userName?.slice(0, 1) || 'U' }}</AvatarFallback>
              </Avatar>
              <span class="avatar-edit-mask">
                <Edit class="h-4 w-4" />
              </span>
            </Button>

            <div class="identity-copy">
              <div class="name-line">
                <h2>{{ userName }}</h2>
                <CircleCheckFilled class="h-5 w-5" />
              </div>
              <p class="email-line">
                <Mail class="h-3.5 w-3.5" />
                <span>{{ userEmail || '邮箱待同步' }}</span>
              </p>
              <p class="headline-line">
                <GraduationCap class="h-3.5 w-3.5" />
                <span>{{ profileHeadline }}</span>
              </p>
            </div>
          </div>

          <Button variant="outline" class="edit-profile-button" @click="openProfileEditor">
            <Edit class="h-4 w-4" />
            编辑资料
          </Button>
        </div>

        <div class="identity-facts">
          <div v-for="fact in identityFacts" :key="fact.label" class="identity-fact">
            <span>{{ fact.label }}</span>
            <strong>{{ fact.value }}</strong>
          </div>
        </div>
      </section>

      <section class="profile-panel learning-dashboard profile-motion-item">
        <div class="dashboard-header">
          <div class="panel-heading">
            <ChartColumn class="h-5 w-5" />
            <h3>学习数据面板</h3>
          </div>
          <div class="dashboard-controls">
            <Select v-if="studentProfile.courses && studentProfile.courses.length > 1" v-model="selectedTrendCourse">
              <SelectTrigger class="course-trigger">
                <SelectValue placeholder="切换课程" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem v-for="course in studentProfile.courses" :key="course" :value="course" class="text-xs cursor-pointer">
                    {{ course }}
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>

            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              class="range-toggle"
              :model-value="timeRange"
              @update:model-value="setTimeRange"
            >
              <ToggleGroupItem value="7">7天</ToggleGroupItem>
              <ToggleGroupItem value="30">30天</ToggleGroupItem>
            </ToggleGroup>
          </div>
        </div>

        <div class="summary-card-grid">
          <div v-for="card in learningSummaryCards" :key="card.label" class="summary-card">
            <div class="summary-icon">
              <component :is="card.icon" class="h-7 w-7" />
            </div>
            <div>
              <span>{{ card.label }}</span>
              <strong>{{ card.value }}</strong>
              <small>{{ card.hint }}</small>
            </div>
          </div>
        </div>

        <div class="dashboard-mosaic">
          <div class="chart-panel focus-chart-panel">
            <div class="chart-heading">
              <h4>学习专注走势</h4>
              <span>(h)</span>
            </div>
            <div class="chart-box">
              <v-chart class="chart" :option="lineOption" autoresize />
              <div v-if="!hasLineChartData" class="chart-empty">暂无学习时长数据</div>
            </div>
          </div>

          <div class="chart-panel scenario-chart-panel">
            <div class="chart-heading">
              <h4>功能使用占比</h4>
            </div>
            <div class="scenario-body">
              <div class="donut-box">
                <v-chart class="chart" :option="pieOption" autoresize />
                <div v-if="!hasScenarioData" class="chart-empty">暂无场景数据</div>
              </div>
              <div class="scenario-list">
                <div v-for="item in scenarioBreakdown" :key="item.name" class="scenario-row">
                  <span class="scenario-name">
                    <i :style="{ backgroundColor: item.color }"></i>
                    {{ item.name }}
                  </span>
                  <strong>{{ item.percent }}%</strong>
                </div>
              </div>
            </div>
          </div>

          <div class="insight-panel resource-panel">
            <div class="chart-heading">
              <h4>学习产出分布</h4>
              <span>{{ resourceHistoryLoading ? '同步中' : `${resourceHistory.length}份` }}</span>
            </div>
            <div class="resource-mix-list">
              <div v-for="item in resourceMixRows" :key="item.label" class="resource-mix-row">
                <div>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.count }}份</strong>
                </div>
                <div class="mix-track">
                  <i :style="{ width: `${item.percent}%` }"></i>
                </div>
              </div>
            </div>
          </div>

          <div class="insight-panel signal-panel">
            <div class="chart-heading">
              <h4>学习效果信号</h4>
              <span>{{ evaluationLoading ? '同步中' : `${evaluationSummary?.event_count || 0}条` }}</span>
            </div>
            <div class="signal-list">
              <div v-for="signal in learningSignalRows" :key="signal.label" class="signal-row">
                <span>{{ signal.label }}</span>
                <strong>{{ signal.value }}</strong>
                <small>{{ signal.hint }}</small>
              </div>
            </div>
          </div>

          <div class="insight-panel status-panel">
            <div class="chart-heading">
              <h4>学习状态速览</h4>
            </div>
            <div class="status-grid">
              <div v-for="item in learningStatusCards" :key="item.label" class="status-card">
                <div class="status-card-head">
                  <component :is="item.icon" class="h-4 w-4" />
                  <span>{{ item.label }}</span>
                </div>
                <strong>{{ item.value }}</strong>
                <small>{{ item.hint }}</small>
              </div>
            </div>
          </div>

          <div class="insight-panel advice-panel">
            <div class="chart-heading">
              <h4>薄弱点与建议</h4>
            </div>
            <div class="tag-cloud">
              <span v-for="topic in displayedWeakTopics" :key="topic" class="weak-tag">{{ topic }}</span>
              <span v-if="displayedWeakTopics.length === 0" class="empty-chip">暂无薄弱点</span>
            </div>
            <div class="tag-cloud preference-cloud">
              <span v-for="resource in displayedPreferredResources" :key="resource" class="data-chip">{{ resource }}</span>
              <span v-if="displayedPreferredResources.length === 0" class="empty-chip">继续积累反馈</span>
            </div>
            <div class="next-action-box">
              <span>下一步建议</span>
              <p>{{ primaryLearningAdvice }}</p>
            </div>
          </div>

          <div class="insight-panel activity-panel">
            <div class="chart-heading">
              <h4>近期学习动态</h4>
              <span>{{ recentActivityRows.length }}条</span>
            </div>
            <div class="activity-list">
              <div v-for="item in recentActivityRows" :key="item.id" class="activity-row">
                <span>{{ item.type }}</span>
                <strong>{{ item.title }}</strong>
                <small>{{ item.time }}</small>
              </div>
              <div v-if="recentActivityRows.length === 0" class="activity-empty">暂无近期动态</div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- Modals -->
    <!-- Profile Editor Dialog -->
    <Dialog v-model:open="profileEditorVisible">
      <DialogContent class="profile-editor-dialog sm:max-w-[580px] w-full gap-0 overflow-hidden rounded-xl border border-teal-100 bg-white p-0 shadow-[0_28px_80px_rgba(32,95,103,0.16)]">
        <DialogHeader class="sr-only">
          <DialogTitle>编辑学业资料</DialogTitle>
          <DialogDescription>
            完善就读学校、专业和课程信息，系统将据此为您智能推荐学习内容。
          </DialogDescription>
        </DialogHeader>

        <!-- Form Scroll Area -->
        <div class="px-6 py-6">
          <form @submit.prevent class="space-y-4">
            <!-- School -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-slate-700">就读学校 <span class="text-rose-500">*</span></label>
              <div class="relative">
                <Input
                  v-model="profileForm.school"
                  type="text"
                  placeholder="请输入学校名称"
                  class="editor-input"
                  @focus="schoolFocus = true"
                  @blur="schoolFocus = false"
                />
                <div v-if="profileErrors.school" class="editor-error text-rose-500 text-[11px] mt-0.5">{{ profileErrors.school }}</div>
                
                <ul v-if="schoolFocus && schoolSuggestions.length > 0" class="editor-suggestion-list">
                  <li
                    v-for="item in schoolSuggestions"
                    :key="item.value"
                    @mousedown="selectSchool(item.value)"
                  >
                    <span class="font-bold text-slate-700">{{ item.value }}</span>
                    <small v-if="item.level" class="text-slate-400 text-[10px] ml-2">{{ item.level }}</small>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Grade & Major (Grid) -->
            <div class="grid grid-cols-2 gap-4">
              <!-- Grade -->
              <div class="space-y-1.5">
                <label class="text-xs font-bold text-slate-700">年级阶段 <span class="text-rose-500">*</span></label>
                <Select v-model="profileForm.grade">
                  <SelectTrigger class="editor-select-trigger">
                    <SelectValue placeholder="选择年级" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem v-for="grade in PRESET_GRADES" :key="grade" :value="grade" class="text-xs cursor-pointer">
                        {{ grade }}
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <div v-if="profileErrors.grade" class="editor-error text-rose-500 text-[11px] mt-0.5">{{ profileErrors.grade }}</div>
              </div>

              <!-- Major -->
              <div class="space-y-1.5">
                <label class="text-xs font-bold text-slate-700">专业 <span class="text-rose-500">*</span></label>
                <div class="relative">
                  <Input
                    v-model="profileForm.major"
                    type="text"
                    placeholder="输入或选择专业"
                    class="editor-input"
                    @focus="majorFocus = true"
                    @blur="majorFocus = false"
                  />
                  <div v-if="profileErrors.major" class="editor-error text-rose-500 text-[11px] mt-0.5">{{ profileErrors.major }}</div>

                  <ul v-if="majorFocus && majorSuggestions.length > 0" class="editor-suggestion-list">
                    <li
                      v-for="item in majorSuggestions"
                      :key="item.value"
                      @mousedown="selectMajor(item.value)"
                    >
                      {{ item.value }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- Goal & Daily Time (Grid) -->
            <div class="grid grid-cols-2 gap-4">
              <!-- Goal -->
              <div class="space-y-1.5">
                <label class="text-xs font-bold text-slate-700">当前学习目标 <span class="text-rose-500">*</span></label>
                <Select v-model="profileForm.global_learning_goal">
                  <SelectTrigger class="editor-select-trigger">
                    <SelectValue placeholder="选择当前目标" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem v-for="goal in PRESET_GOALS" :key="goal" :value="goal" class="text-xs cursor-pointer">
                        {{ goal }}
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <div v-if="profileErrors.global_learning_goal" class="editor-error text-rose-500 text-[11px] mt-0.5">{{ profileErrors.global_learning_goal }}</div>
              </div>

              <!-- Daily study time -->
              <div class="space-y-1.5">
                <label class="text-xs font-bold text-slate-700">每日计划学习时间</label>
                <Select v-model="profileForm.daily_study_time">
                  <SelectTrigger class="editor-select-trigger">
                    <SelectValue placeholder="请选择计划时间" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem v-for="time in PRESET_DAILY_STUDY_TIME" :key="time" :value="time" class="text-xs cursor-pointer">
                        {{ time }}
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <!-- Courses -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-slate-700">正在学习的课程 <span class="text-rose-500">*</span></label>
              <div class="editor-chip-input">
                <span
                  v-for="(course, index) in profileForm.courses"
                  :key="course"
                  class="editor-course-chip"
                >
                  {{ course }}
                  <Button type="button" variant="ghost" class="editor-chip-remove" aria-label="移除课程" @click="removeCourse(index)">
                    <Close class="h-3 w-3" />
                  </Button>
                </span>
                <input
                  v-model="newCourseInput"
                  type="text"
                  placeholder="按回车添加课程"
                  @keydown.enter.prevent="addCourse"
                />
              </div>
              <div v-if="profileErrors.courses" class="editor-error text-rose-500 text-[11px] mt-0.5">{{ profileErrors.courses }}</div>

              <div class="editor-preset-block mt-2">
                <span class="text-[10px] font-bold text-slate-400">快捷推荐课程：</span>
                <div class="editor-preset-list">
                  <Button
                    v-for="course in PRESET_COURSES.slice(0, 8)"
                    :key="course"
                    type="button"
                    variant="outline"
                    class="editor-preset-button text-xs"
                    @click="() => { if(!profileForm.courses.includes(course)) profileForm.courses.push(course) }"
                  >
                    + {{ course }}
                  </Button>
                </div>
              </div>
            </div>

            <!-- Programming Languages -->
            <div class="space-y-1.5">
              <label class="text-xs font-bold text-slate-700">常用编程语言偏好（多选）</label>
              <div class="language-grid">
                <label v-for="language in PRESET_LANGUAGES" :key="language" class="flex items-center gap-2 cursor-pointer text-xs">
                  <input
                    type="checkbox"
                    :value="language"
                    v-model="profileForm.programming_languages"
                    class="accent-teal-600 rounded"
                  />
                  <span>{{ language }}</span>
                </label>
              </div>
            </div>

            <!-- Footer Actions -->
            <div class="flex justify-end gap-3 pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                class="px-4 py-2 border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold rounded-lg h-9"
                @click="profileEditorVisible = false"
              >
                取消
              </Button>
              <Button
                type="submit"
                class="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-sm h-9"
                :disabled="profileSubmitting"
                @click="submitProfile"
              >
                <span v-if="profileSubmitting">正在保存...</span>
                <span v-else class="flex items-center gap-1.5">保存修改 <Check class="h-4 w-4" /></span>
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  </main>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { gsap } from 'gsap'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  BadgeCheckIcon as BadgeCheck,
  BookOpenCheckIcon as BookOpenCheck,
  CalendarDaysIcon as CalendarDays,
  CheckIcon as Check,
  ChartColumnIcon as ChartColumn,
  CircleCheckIcon as CircleCheckFilled,
  Clock3Icon as Clock3,
  FileCheckIcon as FileCheck,
  GaugeIcon as Gauge,
  GraduationCapIcon as GraduationCap,
  LayersIcon as Layers,
  MailIcon as Mail,
  PencilIcon as Edit,
  UserRoundIcon as UserRound,
  XIcon as Close,
} from '@lucide/vue'
import { uploadAvatar } from '@/features/auth/api/auth'
import { ensureCurrentUser, setCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import {
  getProfileOnboarding, updateProfileOnboarding,
} from '@/features/profile/api/profile'
import { getRecentResources, getStudyStats } from '@/features/dashboard/api/home'
import type { RecentResourceItem, StudyStatsData } from '@/features/dashboard/api/home'
import { getGeneratedResources } from '@/features/resource/api/history'
import type { GeneratedResourceItem } from '@/features/resource/api/history'
import { getEvaluationSummary, getLearningTimeStats } from '@/features/evaluation/api/evaluation'
import type { EvaluationSummary, LearningTimeStats } from '@/features/evaluation/api/evaluation'
import { fetchWrongQuestions } from '@/features/question-bank/api/wrongQuestions'
import { searchSchools } from '@/features/profile/api/school'
import type { SchoolItem } from '@/features/profile/model/school'
import type { ProfileOnboardingUpdate, StudentProfileData } from '@/features/profile/api/profile'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const route = useRoute()
const { currentUser, userName } = useCurrentUser()

const timeRange = ref('7')
const userEmail = ref<string | null>(null)
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const profileSubmitting = ref(false)
const learningStats = ref<LearningTimeStats | null>(null)
const evaluationSummary = ref<EvaluationSummary | null>(null)
const studyStats = ref<StudyStatsData | null>(null)
const selectedTrendCourse = ref<string>('')
const resourceHistoryLoading = ref(false)
const dashboardStatsLoading = ref(false)
const evaluationLoading = ref(false)
const wrongLoading = ref(false)
const wrongTotal = ref(0)

const studentProfile = ref<StudentProfileData & { learning_duration_total?: number }>({
  school: null,
  school_level: null,
  grade: null,
  major: null,
  courses: [],
  learning_goal: null,
  preferred_language: null,
  learning_duration_total: 0
})

const profileMeta = reactive({
  dailyStudyTime: '',
  globalLearningGoal: '',
  programmingLanguages: [] as string[],
})

interface ProfileFormData {
  grade: string
  major: string
  courses: string[]
  global_learning_goal: string
  school: string
  daily_study_time: string
  programming_languages: string[]
}

const profileForm = reactive<ProfileFormData>({
  grade: '',
  major: '',
  courses: [],
  global_learning_goal: '',
  school: '',
  daily_study_time: '',
  programming_languages: [],
})

const resourceHistory = ref<GeneratedResourceItem[]>([])
const recentDashboardResources = ref<RecentResourceItem[]>([])

const PRESET_MAJORS = [
  '计算机科学与技术', '软件工程', '人工智能', '数据科学', '网络安全',
  '信息安全', '物联网工程', '通信工程', '电子信息工程', '数字媒体技术'
]
const PRESET_COURSES = [
  '数据结构', '算法分析', '操作系统', '计算机网络', '数据库系统',
  '计算机组成原理', '编译原理', '离散数学', '线性代数', '概率统计',
  '软件工程', 'Web 开发', '机器学习', '深度学习', '计算机视觉', 'NLP',
  '分布式系统', '云计算', '嵌入式开发', '移动端开发'
]
const PRESET_GOALS = [
  '期末考试冲刺', '完成课程设计项目', '大厂求职面试', '考研初试复习', '考研复试准备',
  '系统学习进阶', '零基础快速入门', '竞赛获奖', '个人兴趣拓展', '行业证书考取'
]
const PRESET_DAILY_STUDY_TIME = ['30min 以下', '30-60min', '1-2h', '2-3h', '3h 以上']
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

const profileHeadline = computed(() => {
  const parts = [studentProfile.value.major, studentProfile.value.grade, studentProfile.value.learning_goal]
    .filter((item): item is string => Boolean(item))
  return parts.length ? parts.join(' · ') : '学习资料待完善'
})

const preferredLanguages = computed(() => {
  if (profileMeta.programmingLanguages.length > 0) {
    return profileMeta.programmingLanguages.filter(Boolean)
  }
  return (studentProfile.value.preferred_language || '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
})

const formatStudyDuration = (seconds?: number | null) => {
  if (!seconds || seconds <= 0) return '0m'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  const hours = seconds / 3600
  return `${Number.isInteger(hours) ? hours.toFixed(0) : hours.toFixed(1)}h`
}

const displayLanguages = computed(() => preferredLanguages.value.slice(0, 5))
const displayCourses = computed(() => (studentProfile.value.courses || []).filter(Boolean).slice(0, 5))

const boundedPercent = (value: number) => Math.min(100, Math.max(0, Math.round(value)))

const profileCompletionPercent = computed(() => {
  const checks = [
    studentProfile.value.school,
    studentProfile.value.major,
    studentProfile.value.grade,
    studentProfile.value.learning_goal || profileMeta.globalLearningGoal,
    (studentProfile.value.courses || []).length > 0,
    preferredLanguages.value.length > 0,
    profileMeta.dailyStudyTime,
  ]
  const completed = checks.filter(Boolean).length
  return boundedPercent((completed / checks.length) * 100)
})

const resourceTypeSet = computed(() => {
  const types = new Set<string>()
  resourceHistory.value.forEach((item) => {
    ;(item.resource_types || []).forEach((type) => {
      if (type) types.add(type)
    })
  })
  return types
})

const resourceTypeCoverage = computed(() => resourceTypeSet.value.size)
const completedResourceCount = computed(() => evaluationSummary.value?.completed_resources || resourceHistory.value.length || 0)
const averageScoreLabel = computed(() => {
  const score = evaluationSummary.value?.average_score
  return typeof score === 'number' ? score.toFixed(1) : '暂无'
})

const secondsForContexts = (...keys: string[]) => {
  const context = learningStats.value?.context_breakdown || {}
  return keys.reduce((sum, key) => sum + (context[key] || 0), 0)
}

const questionBankSeconds = computed(() => secondsForContexts('QuestionBank', 'question-bank'))
const tutorSeconds = computed(() => secondsForContexts('Tutor', 'tutor'))
const pathPlanningSeconds = computed(() => secondsForContexts(
  'LearningPathEntry',
  'LearningPathOverview',
  'LearningPathHistory',
  'LearningPathNode',
  'path-planner',
  'path-planner-overview',
  'path-planner-history',
  'path-planner-node',
))
const recommendationSeconds = computed(() => secondsForContexts(
  'ResourceGenerator',
  'ResourceGenerator.vue',
  'ResourceDetail',
  'ResourceHistory',
  'PathResourceDetail',
  'PathResourceHistory',
  'resource-generator',
  'resource-detail',
  'ai/resources/history',
  'path-resource-detail',
  'path-resource-history',
))

const identityFacts = computed(() => [
  { label: '学校', value: studentProfile.value.school || '未完善' },
  { label: '专业', value: studentProfile.value.major || '未完善' },
  { label: '课程', value: displayCourses.value.length ? displayCourses.value.join(' / ') : '未设置' },
  { label: '语言', value: displayLanguages.value.length ? displayLanguages.value.join(' / ') : '未设置' },
])

const learningSummaryCards = computed(() => [
  {
    label: '本周活跃',
    value: `${studyStats.value?.weekly_days ?? learningStats.value?.streak_days ?? 0}天`,
    hint: `今日 ${formatStudyDuration(learningStats.value?.today_seconds || 0)}`,
    icon: CalendarDays,
  },
  {
    label: '学习产出',
    value: `${completedResourceCount.value}`,
    hint: evaluationSummary.value?.viewed_resources ? `已浏览 ${evaluationSummary.value.viewed_resources} 份` : `${resourceHistory.value.length}份生成记录`,
    icon: FileCheck,
  },
  {
    label: '测验均分',
    value: averageScoreLabel.value,
    hint: typeof evaluationSummary.value?.average_score === 'number' ? '近期练习表现' : '等待测验样本',
    icon: Gauge,
  },
  {
    label: '待巩固错题',
    value: `${wrongTotal.value}题`,
    hint: wrongTotal.value > 0 ? '建议优先复盘' : '暂无积压',
    icon: BookOpenCheck,
  },
])

const learningStatusCards = computed(() => [
  {
    label: '资料完整度',
    value: `${profileCompletionPercent.value}%`,
    hint: profileCompletionPercent.value >= 80 ? '推荐更精准' : '继续完善资料',
    percent: profileCompletionPercent.value,
    icon: BadgeCheck,
  },
  {
    label: '资源类型覆盖',
    value: `${Math.min(resourceTypeCoverage.value, 5)}/5`,
    hint: resourceHistoryLoading.value ? '同步中' : '文档/题库/案例等',
    percent: boundedPercent((resourceTypeCoverage.value / 5) * 100),
    icon: Layers,
  },
  {
    label: '评估样本',
    value: `${evaluationSummary.value?.event_count || 0}条`,
    hint: evaluationLoading.value ? '同步中' : '行为与测验信号',
    percent: boundedPercent(((evaluationSummary.value?.event_count || 0) / 12) * 100),
    icon: ChartColumn,
  },
  {
    label: '连续学习',
    value: `${learningStats.value?.streak_days || 0}天`,
    hint: dashboardStatsLoading.value ? '同步中' : `${timeRange.value}天窗口`,
    percent: boundedPercent(((learningStats.value?.streak_days || 0) / 7) * 100),
    icon: Clock3,
  },
])

const displayedWeakTopics = computed(() => (evaluationSummary.value?.weak_topics || []).slice(0, 4))
const displayedPreferredResources = computed(() => (evaluationSummary.value?.preferred_resources || []).slice(0, 4))
const primaryLearningAdvice = computed(() => {
  return evaluationSummary.value?.recommendations?.[0] || '继续完成资源学习与阶段测验，系统会逐步积累学习效果信号。'
})

const learningSignalRows = computed(() => [
  {
    label: '资源完成',
    value: `${completedResourceCount.value}份`,
    hint: evaluationSummary.value?.viewed_resources ? `浏览 ${evaluationSummary.value.viewed_resources} 份` : '来自资源记录',
  },
  {
    label: '测验表现',
    value: averageScoreLabel.value,
    hint: averageScoreLabel.value === '暂无' ? '暂无分数样本' : '平均分',
  },
  {
    label: '错题压力',
    value: `${wrongTotal.value}题`,
    hint: wrongTotal.value > 0 ? '需要巩固' : '状态轻',
  },
])

const resourceTypeLabels: Record<string, string> = {
  content: '知识文档',
  mindmap: '思维导图',
  quiz: '题库练习',
  code: '代码案例',
  reading: '阅读资料',
  ppt: '演示课件',
  video: '视频脚本',
}

const resourceMixRows = computed(() => {
  const counts = new Map<string, number>()
  resourceHistory.value.forEach((item) => {
    const types = item.resource_types?.length ? item.resource_types : ['content']
    types.forEach((type) => counts.set(type, (counts.get(type) || 0) + 1))
  })
  const rows = [...counts.entries()]
    .map(([type, count]) => ({
      label: resourceTypeLabels[type] || type,
      count,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)
  const max = Math.max(...rows.map(item => item.count), 1)
  return rows.length
    ? rows.map(item => ({ ...item, percent: boundedPercent((item.count / max) * 100) }))
    : [
        { label: '知识文档', count: 0, percent: 0 },
        { label: '题库练习', count: 0, percent: 0 },
        { label: '思维导图', count: 0, percent: 0 },
      ]
})

const eventTypeLabels: Record<string, string> = {
  resource_viewed: '浏览资源',
  resource_completed: '完成资源',
  quiz_submitted: '提交测验',
  path_feedback: '路径反馈',
  tutor_helpful: 'AI辅导',
  resource_feedback: '资源反馈',
}

const formatDateLabel = (value?: string | null) => {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}-${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const recentActivityRows = computed(() => {
  const eventRows = (evaluationSummary.value?.recent_events || []).slice(0, 3).map(event => ({
    id: `event-${event.id}`,
    type: eventTypeLabels[event.event_type] || '学习事件',
    title: event.topic || event.course || event.feedback || '学习行为已记录',
    time: formatDateLabel(event.created_at),
  }))
  const resourceRows = recentDashboardResources.value.slice(0, 3).map(resource => ({
    id: `resource-${resource.id}`,
    type: resource.agent || '学习资源',
    title: resource.title,
    time: formatDateLabel(resource.created_at),
  }))
  return [...eventRows, ...resourceRows].slice(0, 5)
})

const scenarioBreakdown = computed(() => {
  const items = [
    { name: '题库练习', seconds: questionBankSeconds.value, color: '#159F9B' },
    { name: 'AI辅导', seconds: tutorSeconds.value, color: '#62C9C5' },
    { name: '路径规划', seconds: pathPlanningSeconds.value, color: '#F0BE84' },
    { name: '智能推荐', seconds: recommendationSeconds.value, color: '#CFC5EE' },
  ]
  const total = items.reduce((sum, item) => sum + item.seconds, 0)
  return items.map(item => ({
    ...item,
    percent: total > 0 ? Math.round((item.seconds / total) * 100) : 0,
  }))
})

const hasLineChartData = computed(() => (learningStats.value?.daily_breakdown || []).some(item => item.seconds > 0))
const hasScenarioData = computed(() => scenarioBreakdown.value.some(item => item.seconds > 0))

const lineOption = computed(() => {
  const dailyBreakdown = learningStats.value?.daily_breakdown || []
  const dates = dailyBreakdown.map((item) => {
    const date = new Date(item.date)
    if (Number.isNaN(date.getTime())) return item.date
    return `${date.getMonth() + 1}-${date.getDate()}`
  })
  const values = dailyBreakdown.map((item) => Number((item.seconds / 3600).toFixed(1)))

  return {
    grid: { top: 24, right: 12, bottom: 28, left: 36 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#FCFFFF',
      borderColor: '#C8E4E3',
      borderWidth: 1,
      textStyle: { color: '#173B42', fontSize: 11 },
      formatter: `{b}<br/>课程：${selectedTrendCourse.value || '全部课程'}<br/>专注时长：{c}h`
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#DDEDEC' } },
      axisLabel: { color: '#6B858A', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#DDEDEC', type: 'dashed' } },
      axisLabel: { color: '#6B858A', fontSize: 10 }
    },
    series: [{
      name: selectedTrendCourse.value,
      data: values,
      type: 'line',
      smooth: true,
      showSymbol: true,
      symbolSize: 6,
      lineStyle: { color: '#159F9B', width: 3 },
      itemStyle: { color: '#FCFFFF', borderColor: '#159F9B', borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(70, 184, 180, 0.22)' },
            { offset: 1, color: 'rgba(70, 184, 180, 0)' },
          ]
        }
      }
    }]
  }
})

const pieOption = computed(() => {
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {d}%',
      backgroundColor: '#FCFFFF',
      borderColor: '#C8E4E3',
      borderWidth: 1,
      textStyle: { color: '#173B42', fontSize: 11 }
    },
    series: [
      {
        name: '学习场景占比',
        type: 'pie',
        radius: ['58%', '78%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#FCFFFF',
          borderWidth: 2
        },
        label: { show: false },
        labelLine: { show: false },
        data: hasScenarioData.value
          ? scenarioBreakdown.value.map(item => ({
              value: item.seconds,
              name: item.name,
              itemStyle: { color: item.color },
            }))
          : [{ value: 1, name: '暂无数据', itemStyle: { color: '#DDEDEC' } }]
      }
    ]
  }
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

watch(() => route.query.action, () => {
  openProfileEditorFromRoute()
})

watch(timeRange, () => {
  loadLearningStats()
})

watch(() => route.path, (newPath) => {
  if (newPath === '/profile') {
    Promise.all([
      loadProfileInfo(),
      loadResourceHistory(),
      loadDashboardStats(),
      loadLearningStats(),
      loadEvaluationSummary(),
      loadWrongOverview(),
    ]).catch(console.error)
  }
})

let profileMotionContext: ReturnType<typeof gsap.context> | null = null
onMounted(async () => {
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadDashboardStats(),
    loadLearningStats(),
    loadEvaluationSummary(),
    loadWrongOverview(),
  ]).catch(console.error)
  openProfileEditorFromRoute()

  requestAnimationFrame(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    profileMotionContext = gsap.context(() => {
      gsap.from('.profile-motion-item', {
        opacity: 0,
        y: 10,
        duration: 0.45,
        stagger: 0.08,
        ease: 'power2.out'
      })
    })
  })
})

onBeforeUnmount(() => {
  profileMotionContext?.revert()
})

const avatarInput = ref<HTMLInputElement>()
const triggerAvatarUpload = () => {
  avatarInput.value?.click()
}

const onAvatarFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    toast.error('仅支持 JPG、PNG、GIF、WebP 格式图片')
    return
  }
  const maxSize = 2 * 1024 * 1024
  if (file.size > maxSize) {
    toast.error('图片大小不能超过 2MB')
    return
  }

  avatarUploading.value = true
  try {
    const res = await uploadAvatar(file)
    userAvatar.value = res.data.data.avatar
    if (currentUser.value) {
      setCurrentUser({
        ...currentUser.value,
        avatar: res.data.data.avatar
      })
    }
    toast.success('头像更新成功')
  } catch (err) {
    console.error('Failed to upload avatar', err)
    toast.error('头像更新失败，请重试')
  } finally {
    avatarUploading.value = false
    target.value = ''
  }
}

const newCourseInput = ref('')
const addCourse = () => {
  const course = newCourseInput.value.trim()
  if (course && !profileForm.courses.includes(course)) {
    profileForm.courses.push(course)
  }
  newCourseInput.value = ''
}
const removeCourse = (index: number) => {
  profileForm.courses.splice(index, 1)
}

const majorFocus = ref(false)
const schoolFocus = ref(false)

const majorSuggestions = computed(() => {
  const query = profileForm.major.trim().toLowerCase()
  if (!query) return PRESET_MAJORS.map(m => ({ value: m }))
  return PRESET_MAJORS.filter(m => m.toLowerCase().includes(query)).map(m => ({ value: m }))
})

const schoolSuggestions = ref<{ value: string; level?: string | null }[]>([])
const querySearchSchool = async (query: string) => {
  if (!query.trim()) {
    schoolSuggestions.value = []
    return
  }
  try {
    const res = await searchSchools(query, 20)
    schoolSuggestions.value = (res.data.data || []).map((school: SchoolItem) => ({
      value: school.name,
      level: school.level
    }))
  } catch (e) {
    schoolSuggestions.value = []
  }
}

watch(() => profileForm.school, (newVal) => {
  querySearchSchool(newVal)
})

const selectMajor = (val: string) => {
  profileForm.major = val
  majorFocus.value = false
}

const selectSchool = (val: string) => {
  profileForm.school = val
  schoolFocus.value = false
}

const profileErrors = reactive({
  major: '',
  courses: '',
  global_learning_goal: '',
  school: '',
  grade: '',
})




const validateProfile = () => {
  let valid = true
  profileErrors.major = ''
  profileErrors.courses = ''
  profileErrors.global_learning_goal = ''
  profileErrors.school = ''
  profileErrors.grade = ''

  if (!profileForm.school.trim()) {
    profileErrors.school = '请输入或搜索你的就读学校'
    valid = false
  }
  if (!profileForm.grade) {
    profileErrors.grade = '请选择你当前的年级阶段'
    valid = false
  }
  if (!profileForm.major.trim()) {
    profileErrors.major = '请选择或输入你的专业'
    valid = false
  }
  if (!profileForm.global_learning_goal) {
    profileErrors.global_learning_goal = '请选择你当前的学习目标'
    valid = false
  }
  if (profileForm.courses.length === 0) {
    profileErrors.courses = '请至少添加一门课程'
    valid = false
  }
  return valid
}

const fillProfileForm = (payload: StudentProfileData) => {
  profileForm.grade = payload.grade || ''
  profileForm.major = payload.major || ''
  profileForm.courses = Array.isArray(payload.courses) ? [...payload.courses] : []
  profileForm.global_learning_goal = profileMeta.globalLearningGoal || payload.learning_goal || ''
  profileForm.school = payload.school || ''
  profileForm.daily_study_time = profileMeta.dailyStudyTime
  profileForm.programming_languages = profileMeta.programmingLanguages.length > 0
    ? [...profileMeta.programmingLanguages]
    : (payload.preferred_language ? payload.preferred_language.split(',').map(s => s.trim()).filter(Boolean) : [])
}

const loadProfileInfo = async () => {
  try {
    const [userRes, onboardingRes] = await Promise.allSettled([
      ensureCurrentUser(true),
      getProfileOnboarding(),
    ])

    if (userRes.status === 'fulfilled' && userRes.value) {
      setCurrentUser(userRes.value)
      userAvatar.value = userRes.value.avatar
      userEmail.value = userRes.value.email
    } else if (currentUser.value) {
      userAvatar.value = currentUser.value.avatar
      userEmail.value = currentUser.value.email
    }

    if (onboardingRes.status === 'fulfilled') {
      const onboardingData = onboardingRes.value.data?.data
      const baseInfo = onboardingData?.base_info
      // 统一从 base_info 中获取所有基本信息，确保数据正确展示
      if (baseInfo) {
        studentProfile.value = {
          school: baseInfo.school || null,
          school_level: baseInfo.school_level || null,
          major: baseInfo.major || null,
          grade: baseInfo.grade || null,
          courses: baseInfo.courses || [],
          learning_goal: baseInfo.global_learning_goal || null,
          preferred_language: (baseInfo.programming_languages || []).join(', '),
        }
        profileMeta.dailyStudyTime = baseInfo.daily_study_time || ''
        profileMeta.globalLearningGoal = baseInfo.global_learning_goal || ''
        profileMeta.programmingLanguages = Array.isArray(baseInfo.programming_languages)
          ? [...baseInfo.programming_languages]
          : []
      }
    }
  } catch (e) {
    console.warn('加载个人中心数据失败', e)
  } finally {
    fillProfileForm(studentProfile.value)
  }
}

const loadLearningStats = async () => {
  try {
    const days = parseInt(timeRange.value) || 7
    const res = await getLearningTimeStats(days)
    learningStats.value = res.data.data
    studentProfile.value.learning_duration_total = res.data.data.total_seconds
  } catch (e) {
    console.warn('加载学习时长统计失败', e)
    learningStats.value = null
    studentProfile.value.learning_duration_total = 0
  }
}

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true
  try {
    const res = await getGeneratedResources(1, 40)
    resourceHistory.value = res.data.data?.items || []
  } catch (e) {
    console.warn('加载资源生成历史失败', e)
    resourceHistory.value = []
  } finally {
    resourceHistoryLoading.value = false
  }
}

const loadDashboardStats = async () => {
  dashboardStatsLoading.value = true
  try {
    const [statsRes, resourcesRes] = await Promise.allSettled([
      getStudyStats(),
      getRecentResources(),
    ])
    studyStats.value = statsRes.status === 'fulfilled' ? statsRes.value.data.data : null
    recentDashboardResources.value = resourcesRes.status === 'fulfilled' ? resourcesRes.value.data.data || [] : []
  } catch (e) {
    console.warn('加载学习数据概览失败', e)
    studyStats.value = null
    recentDashboardResources.value = []
  } finally {
    dashboardStatsLoading.value = false
  }
}

const loadEvaluationSummary = async () => {
  evaluationLoading.value = true
  try {
    const res = await getEvaluationSummary(100)
    evaluationSummary.value = res.data.data
  } catch (e) {
    console.warn('加载学习评估摘要失败', e)
    evaluationSummary.value = null
  } finally {
    evaluationLoading.value = false
  }
}

const loadWrongOverview = async () => {
  wrongLoading.value = true
  try {
    const res = await fetchWrongQuestions({ is_archived: false, page: 1, page_size: 1 })
    wrongTotal.value = res.total || 0
  } catch (e) {
    console.warn('加载错题概览失败', e)
    wrongTotal.value = 0
  } finally {
    wrongLoading.value = false
  }
}

const openProfileEditor = () => {
  fillProfileForm(studentProfile.value)
  profileErrors.major = ''
  profileErrors.courses = ''
  profileErrors.global_learning_goal = ''
  profileErrors.school = ''
  profileErrors.grade = ''
  profileEditorVisible.value = true
}

const openProfileEditorFromRoute = () => {
  if (route.query.action === 'edit-profile') {
    openProfileEditor()
  }
}

const setTimeRange = (val: any) => {
  if (typeof val === 'string' && val) timeRange.value = val
}

const submitProfile = async () => {
  if (!validateProfile()) {
    toast.warning('请先完善所有必填项')
    return
  }

  profileSubmitting.value = true
  try {
    const payload: ProfileOnboardingUpdate = {
      school: profileForm.school,
      major: profileForm.major,
      grade: profileForm.grade,
      global_learning_goal: profileForm.global_learning_goal,
      daily_study_time: profileForm.daily_study_time,
      courses: profileForm.courses.filter(Boolean).map((c) => c.trim()),
      programming_languages: profileForm.programming_languages,
    }
    await updateProfileOnboarding(payload)
    studentProfile.value = {
      ...studentProfile.value,
      school: payload.school,
      major: payload.major,
      grade: payload.grade,
      courses: payload.courses,
      learning_goal: payload.global_learning_goal,
      preferred_language: payload.programming_languages.join(', '),
    }
    profileMeta.dailyStudyTime = payload.daily_study_time
    profileMeta.globalLearningGoal = payload.global_learning_goal
    profileMeta.programmingLanguages = [...payload.programming_languages]
    profileEditorVisible.value = false
    toast.success('学习资料更新成功')
    await loadProfileInfo()
  } catch (e: any) {
    console.error('Failed to update profile onboarding', e)
    toast.error(e.response?.data?.message || '保存失败，请稍后重试')
  } finally {
    profileSubmitting.value = false
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100%;
  background: #ffffff;
  color: var(--color-text);
}

.profile-page :is(h1, h2, h3, h4, p, span, strong, small, button) {
  letter-spacing: 0;
}

.profile-shell {
  width: min(100%, 1680px);
  margin: 0 auto;
  padding: 26px 28px 32px;
}

.profile-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  color: var(--color-primary-text);
}

.profile-title-row h1 {
  font-size: 28px;
  font-weight: 800;
  color: var(--color-primary-text);
}

.title-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  color: #079894;
}

.profile-identity-strip,
.profile-panel {
  border: 1px solid rgba(157, 210, 208, .82);
  border-radius: 12px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, .92), rgba(252, 255, 255, .72)),
    var(--color-surface);
  box-shadow: 0 18px 44px rgba(32, 95, 103, .08);
}

.profile-identity-strip {
  display: grid;
  grid-template-columns: minmax(420px, .95fr) minmax(0, 1.45fr);
  gap: 18px;
  align-items: stretch;
  margin-bottom: 18px;
  padding: 16px;
}

.identity-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: 16px;
  padding-right: 14px;
  border-right: 1px solid rgba(200, 228, 227, .72);
}

.identity-inner {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-button {
  position: relative;
  width: 76px;
  height: 76px;
  flex: 0 0 76px;
  padding: 0;
  border-radius: 999px;
  background: transparent;
}

.avatar-button:hover {
  background: transparent;
}

.profile-avatar {
  width: 70px;
  height: 70px;
  border: 1px solid rgba(157, 210, 208, .95);
  box-shadow: inset 0 0 0 4px rgba(255, 255, 255, .84), 0 10px 24px rgba(32, 95, 103, .11);
}

.profile-avatar :deep(span) {
  font-size: 24px;
  font-weight: 800;
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
}

.avatar-edit-mask {
  position: absolute;
  inset: 5px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: #fff;
  background: rgba(23, 59, 66, .54);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.avatar-button:hover .avatar-edit-mask {
  opacity: 1;
}

.identity-copy {
  min-width: 0;
}

.name-line {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #079894;
}

.name-line h2 {
  max-width: 260px;
  overflow: hidden;
  color: var(--color-primary-text);
  font-size: 24px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-line,
.headline-line {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 9px;
  margin-top: 8px;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 600;
}

.email-line span,
.headline-line span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edit-profile-button {
  height: 36px;
  flex: 0 0 auto;
  gap: 8px;
  border-color: rgba(32, 95, 103, .55);
  border-radius: 8px;
  background: rgba(252, 255, 255, .72);
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 700;
}

.identity-facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
}

.identity-fact {
  display: grid;
  gap: 4px;
  min-width: 0;
  min-height: 74px;
  padding: 13px 14px;
  border: 1px solid rgba(200, 228, 227, .78);
  border-radius: 9px;
  background: rgba(252, 255, 255, .7);
}

.identity-fact span {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.identity-fact strong {
  min-width: 0;
  overflow: hidden;
  color: var(--color-primary-text);
  font-size: 14px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-panel {
  padding: 26px;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 20px;
  color: #079894;
}

.panel-heading h3 {
  color: var(--color-primary-text);
  font-size: 20px;
  font-weight: 800;
}

.profile-row-list {
  display: grid;
  gap: 0;
}

.profile-info-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  min-height: 48px;
  border-bottom: 1px solid rgba(200, 228, 227, .7);
  font-size: 15px;
}

.profile-info-row span,
.chip-row-label {
  color: var(--color-primary-text);
  font-weight: 600;
}

.profile-info-row strong {
  overflow: hidden;
  color: var(--color-primary-text);
  font-weight: 700;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-section {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  padding-top: 16px;
  font-size: 15px;
}

.chip-list {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.chip-list.compact-chip-list {
  justify-content: flex-start;
  gap: 7px;
}

.data-chip,
.empty-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 3px 13px;
  border: 1px solid rgba(70, 184, 180, .42);
  border-radius: 8px;
  background: rgba(216, 241, 240, .52);
  color: #159f9b;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}

.empty-chip {
  color: var(--color-text-muted);
  background: rgba(234, 245, 244, .62);
}

.next-action-box {
  margin-top: 16px;
  padding: 15px 16px;
  border: 1px solid rgba(200, 228, 227, .78);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(216, 241, 240, .58), rgba(252, 255, 255, .72));
}

.next-action-box span {
  display: block;
  color: #079894;
  font-size: 12px;
  font-weight: 800;
}

.next-action-box p {
  margin: 7px 0 0;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.6;
}

.learning-dashboard {
  min-width: 0;
  padding: 22px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.dashboard-header .panel-heading {
  margin-bottom: 0;
}

.dashboard-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.course-trigger {
  width: 132px;
  height: 32px;
  border-color: rgba(200, 228, 227, .95);
  border-radius: 8px;
  background: rgba(252, 255, 255, .9);
  color: var(--color-primary-text);
  font-size: 12px;
}

.range-toggle {
  overflow: hidden;
  border: 1px solid rgba(200, 228, 227, .95);
  border-radius: 8px;
  background: rgba(252, 255, 255, .88);
}

.range-toggle :deep(button) {
  height: 30px;
  min-width: 48px;
  border: 0;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 700;
}

.range-toggle :deep(button[data-state="on"]) {
  background: var(--color-primary-soft);
  color: #079894;
}

.summary-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 88px;
  padding: 16px 18px;
  border: 1px solid rgba(200, 228, 227, .95);
  border-radius: 10px;
  background: rgba(252, 255, 255, .84);
}

.summary-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  color: #079894;
}

.summary-card span,
.summary-card small {
  display: block;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 700;
}

.summary-card strong {
  display: block;
  margin-top: 2px;
  color: var(--color-primary-text);
  font-size: 28px;
  font-weight: 800;
  line-height: 1.05;
}

.summary-card small {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.dashboard-mosaic {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-auto-flow: dense;
  gap: 14px;
}

.chart-panel,
.insight-panel {
  min-width: 0;
  padding: 16px 18px 14px;
  border: 1px solid rgba(200, 228, 227, .9);
  border-radius: 10px;
  background: rgba(252, 255, 255, .82);
}

.focus-chart-panel {
  grid-column: span 8;
}

.scenario-chart-panel {
  grid-column: span 4;
}

.signal-panel,
.status-panel,
.resource-panel,
.activity-panel {
  grid-column: span 4;
}

.advice-panel {
  grid-column: span 8;
}

.chart-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.chart-heading h4 {
  color: var(--color-primary-text);
  font-size: 16px;
  font-weight: 800;
}

.chart-heading span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.chart-box {
  position: relative;
  height: 232px;
}

.scenario-body {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  align-items: center;
}

.donut-box {
  position: relative;
  height: 168px;
}

.scenario-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.scenario-row,
.scenario-name {
  display: flex;
  align-items: center;
  gap: 10px;
}

.scenario-row {
  justify-content: space-between;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 700;
}

.scenario-name i {
  width: 11px;
  height: 11px;
  flex: 0 0 11px;
  border-radius: 3px;
}

.scenario-row strong {
  color: var(--color-primary-text);
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 700;
  pointer-events: none;
}

.chart {
  width: 100%;
  height: 100%;
}

.signal-list {
  display: grid;
  gap: 10px;
}

.resource-mix-list {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.resource-mix-row {
  display: grid;
  gap: 8px;
}

.resource-mix-row > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 800;
}

.resource-mix-row strong {
  color: #079894;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 800;
}

.mix-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(221, 237, 236, .9);
}

.mix-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #159f9b, #62c9c5);
}

.signal-row {
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid rgba(221, 237, 236, .9);
  border-radius: 9px;
  background: rgba(255, 255, 255, .72);
}

.signal-row span,
.signal-row small {
  display: block;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.signal-row strong {
  display: block;
  margin: 6px 0 5px;
  overflow: hidden;
  color: var(--color-primary-text);
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-panel {
  overflow: hidden;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(221, 237, 236, .9);
  border-radius: 9px;
  background: rgba(255, 255, 255, .72);
}

.status-card-head {
  display: flex;
  align-items: center;
  gap: 7px;
  color: #079894;
}

.status-card-head span {
  min-width: 0;
  overflow: hidden;
  color: var(--color-primary-text);
  font-size: 11px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-card strong {
  display: block;
  margin-top: 8px;
  color: var(--color-primary-text);
  font-size: 22px;
  font-weight: 800;
  line-height: 1;
}

.status-card small {
  display: block;
  min-height: 16px;
  margin-top: 6px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.preference-cloud {
  margin-top: 12px;
}

.weak-tag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 12px;
  border: 1px solid rgba(240, 190, 132, .5);
  border-radius: 8px;
  background: rgba(255, 241, 222, .64);
  color: #96621c;
  font-size: 12px;
  font-weight: 800;
}

.advice-panel .next-action-box {
  margin-top: 14px;
}

.activity-list {
  display: grid;
  gap: 9px;
}

.activity-row {
  display: grid;
  min-width: 0;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid rgba(221, 237, 236, .9);
  border-radius: 9px;
  background: rgba(255, 255, 255, .72);
}

.activity-row span,
.activity-row small {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.activity-row strong {
  overflow: hidden;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-empty {
  display: grid;
  min-height: 180px;
  place-items: center;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 700;
}

:global(.profile-editor-dialog) {
  width: min(580px, calc(100vw - 48px)) !important;
  max-width: min(580px, calc(100vw - 48px)) !important;
  max-height: min(720px, calc(100dvh - 48px));
  color: var(--color-primary-text);
}

.profile-editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 24px 68px 22px 28px;
  border-bottom: 1px solid rgba(200, 228, 227, .82);
  background:
    radial-gradient(circle at 92% 0%, rgba(70, 184, 180, .16), transparent 30%),
    linear-gradient(135deg, rgba(252, 255, 255, .98), rgba(239, 250, 250, .74));
}

.profile-editor-title {
  color: var(--color-primary-text);
  font-size: 20px;
  font-weight: 800;
}

.profile-editor-desc {
  margin-top: 7px;
  max-width: 520px;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.6;
}

.profile-editor-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 2px;
}

.profile-editor-meta span {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border: 1px solid rgba(70, 184, 180, .42);
  border-radius: 999px;
  background: rgba(216, 241, 240, .62);
  color: #079894;
  font-size: 12px;
  font-weight: 800;
}

.profile-editor-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 520px;
  max-height: calc(100dvh - 146px);
  overflow: hidden;
}

.profile-editor-aside {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  padding: 22px 18px;
  border-right: 1px solid rgba(200, 228, 227, .82);
  background: linear-gradient(180deg, rgba(247, 253, 253, .95), rgba(255, 255, 255, .92));
}

.editor-step-card {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(200, 228, 227, .76);
  border-radius: 10px;
  background: rgba(255, 255, 255, .72);
  color: var(--color-primary-text);
  text-align: left;
  transition: border-color var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
}

.editor-step-card:hover {
  border-color: rgba(70, 184, 180, .62);
  background: #fff;
}

.editor-step-card:active {
  transform: translateY(1px);
}

.editor-step-card.active,
.editor-step-card.done {
  border-color: rgba(21, 159, 155, .55);
  background: linear-gradient(135deg, rgba(216, 241, 240, .76), rgba(255, 255, 255, .92));
}

.editor-step-index {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(234, 245, 244, .92);
  color: #079894;
  font-size: 13px;
  font-weight: 800;
}

.editor-step-card.active .editor-step-index,
.editor-step-card.done .editor-step-index {
  background: #079894;
  color: #fff;
}

.editor-step-card strong,
.editor-step-card small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-step-card strong {
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 800;
}

.editor-step-card small {
  margin-top: 4px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.editor-aside-note {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 9px;
  margin-top: auto;
  padding: 13px 12px;
  border: 1px solid rgba(200, 228, 227, .82);
  border-radius: 10px;
  background: rgba(252, 255, 255, .8);
  color: #079894;
}

.editor-aside-note p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
  line-height: 1.6;
}

.profile-editor-main {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.profile-editor-form {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding: 24px 26px;
}

.editor-step-pane {
  display: grid;
  gap: 16px;
}

.editor-form-section {
  min-width: 0;
  padding: 18px;
  border: 1px solid rgba(200, 228, 227, .82);
  border-radius: 10px;
  background: rgba(252, 255, 255, .82);
}

.compact-section {
  max-width: 520px;
}

.editor-section-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.editor-section-heading h5 {
  color: var(--color-primary-text);
  font-size: 14px;
  font-weight: 800;
}

.editor-badge {
  height: 22px;
  border-radius: 7px;
  background: var(--color-primary-soft);
  color: #079894;
  font-size: 11px;
  font-weight: 800;
}

.editor-badge.outline {
  border-color: rgba(70, 184, 180, .42);
  color: #079894;
}

.editor-field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.editor-field,
.editor-field label {
  min-width: 0;
}

.editor-field {
  display: grid;
  gap: 8px;
}

.editor-field-wide {
  grid-column: 1 / -1;
}

.editor-field > label {
  display: block;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 800;
}

.editor-field > label span {
  margin-right: 3px;
  color: #e05268;
}

.editor-input,
.editor-select-trigger {
  height: 42px;
  border: 1px solid rgba(200, 228, 227, .96) !important;
  border-radius: 8px;
  background: #fff !important;
  color: var(--color-primary-text);
  font-size: 13px;
}

.editor-select-trigger {
  width: 100% !important;
  padding: 0 14px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
}

.editor-error {
  margin-top: 2px;
  color: #e05268;
  font-size: 11px;
  font-weight: 700;
}

.editor-suggestion-list {
  position: absolute;
  right: 0;
  left: 0;
  z-index: 2100;
  max-height: 180px;
  margin-top: 6px;
  overflow-y: auto;
  border: 1px solid rgba(200, 228, 227, .9);
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(32, 95, 103, .14);
}

.editor-suggestion-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.editor-suggestion-list li:hover {
  background: rgba(216, 241, 240, .48);
}

.editor-suggestion-list small {
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(234, 245, 244, .82);
  color: var(--color-text-muted);
  font-size: 10px;
  font-weight: 800;
}

.editor-chip-input {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 48px;
  padding: 8px;
  border: 1px solid rgba(200, 228, 227, .96);
  border-radius: 9px;
  background: #fff;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.editor-chip-input:focus-within {
  border-color: rgba(21, 159, 155, .72);
  box-shadow: 0 0 0 3px rgba(21, 159, 155, .1);
}

.editor-chip-input input {
  min-width: 180px;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-primary-text);
  font-size: 13px;
  font-weight: 600;
}

.editor-course-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 3px 6px 3px 11px;
  border: 1px solid rgba(70, 184, 180, .38);
  border-radius: 8px;
  background: rgba(216, 241, 240, .5);
  color: #0b7774;
  font-size: 12px;
  font-weight: 800;
}

.editor-chip-remove {
  width: 20px;
  height: 20px;
  padding: 0;
  border-radius: 999px;
  color: var(--color-text-muted);
}

.editor-chip-remove:hover {
  background: rgba(21, 159, 155, .12);
  color: #079894;
}

.editor-preset-block {
  margin-top: 12px;
}

.editor-preset-block > span {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 800;
}

.editor-preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.editor-preset-button {
  height: 30px;
  border-color: rgba(200, 228, 227, .96);
  border-radius: 8px;
  background: #fff;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 700;
}

.language-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  max-height: 178px;
  overflow-y: auto;
  padding: 12px;
  border: 1px solid rgba(200, 228, 227, .96);
  border-radius: 9px;
  background: #fff;
}

.language-grid label {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  user-select: none;
}

.language-grid input {
  width: 14px;
  height: 14px;
  flex: 0 0 14px;
  accent-color: #079894;
  cursor: pointer;
}

.language-grid span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 26px;
  border-top: 1px solid rgba(200, 228, 227, .72);
  background: rgba(252, 255, 255, .92);
}

.editor-footer-note,
.editor-footer-actions,
.editor-primary-button,
.editor-secondary-button {
  display: flex;
  align-items: center;
}

.editor-footer-note {
  gap: 6px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.editor-footer-actions {
  gap: 10px;
}

.editor-primary-button,
.editor-secondary-button {
  height: 38px;
  gap: 7px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 800;
}

.editor-primary-button {
  border: 0;
  background: #079894;
  color: #fff;
}

.editor-primary-button:hover {
  background: #0aa7a3;
}

.editor-secondary-button {
  border-color: rgba(200, 228, 227, .96);
  color: var(--color-primary-text);
}

@media (max-width: 1280px) {
  .profile-identity-strip {
    grid-template-columns: 1fr;
  }

  :global(.profile-editor-dialog) {
    width: min(580px, calc(100vw - 40px)) !important;
    max-width: min(580px, calc(100vw - 40px)) !important;
  }

  .profile-editor-layout {
    grid-template-columns: 232px minmax(0, 1fr);
  }

  .language-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .identity-panel {
    padding-right: 0;
    padding-bottom: 14px;
    border-right: 0;
    border-bottom: 1px solid rgba(200, 228, 227, .72);
  }

  .summary-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-mosaic {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .focus-chart-panel,
  .scenario-chart-panel {
    grid-column: 1 / -1;
  }

  .signal-panel,
  .status-panel,
  .resource-panel,
  .activity-panel {
    grid-column: auto;
  }

  .advice-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .profile-shell {
    padding: 20px 16px 28px;
  }

  :global(.profile-editor-dialog) {
    width: calc(100vw - 24px) !important;
    max-width: calc(100vw - 24px) !important;
    max-height: calc(100dvh - 24px);
  }

  .profile-editor-header {
    flex-direction: column;
    gap: 12px;
    padding: 20px 52px 18px 18px;
  }

  .profile-editor-meta {
    justify-content: flex-start;
  }

  .profile-editor-layout {
    grid-template-columns: 1fr;
    min-height: auto;
    max-height: calc(100dvh - 126px);
  }

  .profile-editor-aside {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    padding: 14px;
    border-right: 0;
    border-bottom: 1px solid rgba(200, 228, 227, .82);
  }

  .editor-step-card {
    grid-template-columns: 30px minmax(0, 1fr);
    padding: 10px;
  }

  .editor-step-index {
    width: 30px;
    height: 30px;
    border-radius: 8px;
  }

  .editor-aside-note {
    display: none;
  }

  .profile-editor-form {
    padding: 16px;
  }

  .editor-form-section {
    padding: 14px;
  }

  .compact-section {
    max-width: none;
  }

  .editor-field-grid,
  .language-grid {
    grid-template-columns: 1fr;
  }

  .editor-field-wide {
    grid-column: auto;
  }

  .profile-editor-footer {
    align-items: stretch;
    flex-direction: column;
    padding: 14px 16px;
  }

  .editor-footer-actions {
    justify-content: flex-end;
  }

  .profile-title-row h1 {
    font-size: 24px;
  }

  .profile-identity-strip {
    padding: 14px;
  }

  .identity-panel {
    align-items: flex-start;
    flex-direction: column;
    padding-bottom: 14px;
  }

  .identity-inner {
    width: 100%;
    align-items: center;
    gap: 14px;
  }

  .avatar-button {
    width: 70px;
    height: 70px;
    flex-basis: 70px;
  }

  .profile-avatar {
    width: 64px;
    height: 64px;
  }

  .name-line h2 {
    max-width: min(58vw, 320px);
    font-size: 22px;
  }

  .edit-profile-button {
    width: 100%;
  }

  .identity-facts {
    grid-template-columns: 1fr;
  }

  .profile-panel {
    padding: 20px;
  }

  .summary-card-grid,
  .scenario-body,
  .signal-list,
  .status-grid,
  .scenario-list,
  .dashboard-mosaic {
    grid-template-columns: 1fr;
  }

  .focus-chart-panel,
  .scenario-chart-panel,
  .signal-panel,
  .status-panel,
  .resource-panel,
  .activity-panel,
  .advice-panel {
    grid-column: 1 / -1;
  }

  .dashboard-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .dashboard-controls {
    width: 100%;
    flex-wrap: wrap;
  }

  .course-trigger {
    width: 100%;
  }

  .range-toggle {
    width: 100%;
  }

  .range-toggle :deep(button) {
    flex: 1;
  }

  .profile-info-row,
  .chip-section {
    grid-template-columns: 82px minmax(0, 1fr);
  }

  .compact-row-list .profile-info-row {
    grid-template-columns: 1fr;
  }

  .chart-box,
  .donut-box {
    height: 220px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .avatar-edit-mask,
  .ring-value {
    transition: none;
  }
}

/* Micro-interaction transition for companion card */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1), transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
