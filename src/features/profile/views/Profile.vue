<template>
  <div class="profile-dashboard">
    <div class="bento-container">

      <div class="bento-span-5 top-row-wrapper">

        <div class="bento-card user-card">
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
            <button class="btn-outline custom-edit-btn" @click="openProfileEditor">
              <el-icon><Edit /></el-icon> 编辑资料
            </button>
          </div>
          <div class="user-divider"></div>
          <div class="profile-info-grid">
            <div class="info-mini-card">
              <div class="info-icon-box"><el-icon><Search /></el-icon></div>
              <div class="info-content-box">
                <span class="info-label">学校</span>
                <div class="info-value school-info-strong">
                  <span class="school-name-text" :title="studentProfile.school || undefined">{{ studentProfile.school || '未填写' }}</span>
                  <span v-if="studentProfile.school_level" class="school-level-badge">{{ studentProfile.school_level }}</span>
                </div>
              </div>
            </div>
            <div class="info-mini-card">
              <div class="info-icon-box"><el-icon><Checked /></el-icon></div>
              <div class="info-content-box">
                <span class="info-label">年级</span>
                <span class="info-value">{{ studentProfile.grade || '未填写' }}</span>
              </div>
            </div>
            <div class="info-mini-card">
              <div class="info-icon-box"><el-icon><UserFilled /></el-icon></div>
              <div class="info-content-box">
                <span class="info-label">专业</span>
                <span class="info-value" :title="studentProfile.major || undefined">{{ studentProfile.major || '未填写' }}</span>
              </div>
            </div>
            <div class="info-mini-card">
              <div class="info-icon-box"><el-icon><Cpu /></el-icon></div>
              <div class="info-content-box">
                <span class="info-label">编程语言</span>
                <div class="info-value">
                  <div v-if="preferredLanguages.length > 0" class="course-display-wrapper user-card-course-wrapper">
                    <strong class="course-single-title user-card-course-title" :title="preferredLanguages[0]">{{ preferredLanguages[0] }}</strong>
                    <el-popover
                        v-if="preferredLanguages.length > 1"
                        placement="top"
                        :width="220"
                        trigger="hover"
                        popper-class="course-popover"
                    >
                      <template #reference>
                        <el-button link type="primary" class="view-all-courses-btn user-card-view-btn">
                          共 {{ preferredLanguages.length }} 项
                        </el-button>
                      </template>
                      <div class="all-courses-popover-content">
                        <div class="popover-title">
                          <el-icon><Cpu /></el-icon> 已填写的全部编程语言
                        </div>
                        <div class="popover-course-list">
                          <div v-for="(language, idx) in preferredLanguages" :key="language" class="popover-course-item">
                            <span class="course-number">{{ idx + 1 }}.</span>
                            <span class="course-name">{{ language }}</span>
                          </div>
                        </div>
                      </div>
                    </el-popover>
                  </div>
                  <span v-else>未填写</span>
                </div>
              </div>
            </div>
            <div class="info-mini-card">
              <div class="info-icon-box"><el-icon><VideoPlay /></el-icon></div>
              <div class="info-content-box">
                <span class="info-label">正在学习</span>
                <div class="info-value">
                  <div v-if="studentProfile.courses && studentProfile.courses.length > 0" class="course-display-wrapper user-card-course-wrapper">
                    <strong class="course-single-title user-card-course-title" :title="studentProfile.courses[0]">{{ studentProfile.courses[0] }}</strong>
                    <el-popover
                        v-if="studentProfile.courses.length > 1"
                        placement="top"
                        :width="220"
                        trigger="hover"
                        popper-class="course-popover"
                    >
                      <template #reference>
                        <el-button link type="primary" class="view-all-courses-btn user-card-view-btn">
                          共 {{ studentProfile.courses.length }} 门
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
                  <span v-else>未填写</span>
                </div>
              </div>
            </div>
            <div class="info-mini-card">
              <div class="info-icon-box"><el-icon><Aim /></el-icon></div>
              <div class="info-content-box">
                <span class="info-label">学习目标</span>
                <span class="info-value" :title="studentProfile.learning_goal || undefined">{{ studentProfile.learning_goal || '未填写' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="combined-profile-wrapper">
          <div class="bento-card combined-profile-card">
            <div class="card-header-flex main-card-header">
              <h4 class="card-title"><el-icon class="text-blue"><Cpu /></el-icon> 资源生成历史</h4>
              <div class="custom-pill-group">
                <button type="button" :class="['pill-btn', { active: historyFilter === 'all' }]" @click="historyFilter = 'all'">全部</button>
                <button type="button" :class="['pill-btn', { active: historyFilter === 'completed' }]" @click="historyFilter = 'completed'">已完成</button>
              </div>
            </div>

            <div class="profile-tabs-content">
              <div style="flex: 1; min-height: 0; display: flex; flex-direction: column; overflow-y: auto; padding-right: 4px;" v-loading="resourceHistoryLoading">
                <div v-if="filteredTableData.length === 0" class="empty-history">
                  <el-empty description="暂无历史生成记录" :image-size="60" />
                </div>
                <div v-else class="history-list-flow">
                  <div
                      v-for="item in filteredTableData"
                      :key="item.id"
                      class="history-row-card"
                      :class="getStatusClass(item.rawStatus)"
                      @click="viewResourceDetail(item)"
                  >
                    <div class="status-bar"></div>
                    <div class="item-icon-wrapper">
                      <el-icon><component :is="getHistoryIcon(item.rawStatus)" /></el-icon>
                    </div>

                    <div class="item-main-info">
                      <span class="item-title" :title="item.title">{{ item.title }}</span>
                      <div class="item-sub-meta">
                        <span class="item-time"><el-icon><Clock /></el-icon>{{ item.time }}</span>
                        <span class="status-badge-pill" :class="item.rawStatus">
                          <span class="badge-dot"></span>
                          {{ item.status }}
                        </span>
                      </div>
                    </div>

                    <div class="item-action-btn">
                      <span>查看</span>
                      <el-icon class="action-arrow"><ArrowRight /></el-icon>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="bento-card bento-span-3 profile-notes-card">
        <div class="card-header-flex profile-notes-header">
          <div class="profile-notes-title-block">
            <h4 class="card-title"><el-icon><DocumentCopy /></el-icon> 我的笔记</h4>
            <p class="profile-notes-subtitle">同步展示全局笔记草稿和最近保存内容</p>
          </div>
          <div class="profile-notes-summary">
            <span class="notes-card-count">{{ profileSavedNotes.length }} 条已保存</span>
            <span v-if="profileDraft" class="notes-draft-pill">草稿未保存</span>
          </div>
        </div>
        <div class="profile-notes-body">
          <div v-if="profileDraft || profileSavedNotes.length > 0" class="profile-notes-stack">
            <article v-if="profileDraft" class="profile-note-item draft-note-item" @click="openNotePreview({ id: 'draft', content: profileDraft, savedAt: '' }, true)">
              <div class="note-item-head">
                <span class="note-state-badge">未保存草稿</span>
                <span class="note-time-text">关闭弹窗后仍会保留</span>
              </div>
              <p class="note-item-title">{{ getNoteSummary(profileDraft) }}</p>
            </article>

            <article
              v-for="note in profileSavedNotes"
              :key="note.id"
              class="profile-note-item"
              @click="openNotePreview(note)"
            >
              <div class="note-item-head">
                <span class="note-state-badge subtle">已保存</span>
                <span class="note-time-text">{{ formatNoteTime(note.savedAt) }}</span>
              </div>
              <p class="note-item-title">{{ getNoteSummary(note.content) }}</p>
            </article>
          </div>

          <div v-else class="profile-notes-empty">
            <div class="profile-notes-empty-inner">
              <span>还没有笔记</span>
              <p>点击右下角全局笔记按钮后记录的内容，会在这里同步展示。</p>
            </div>
          </div>
        </div>
      </div>

      <el-dialog
        v-model="notePreviewVisible"
        width="min(760px, 92vw)"
        class="note-preview-dialog"
        destroy-on-close
      >
        <template #header>
          <div class="note-preview-header">
            <div>
              <h3>{{ notePreviewDraft ? '未保存草稿' : '笔记详情' }}</h3>
              <p>{{ notePreviewDraft ? '关闭全局笔记前会继续保留' : (notePreviewSavedAt ? formatNoteTime(notePreviewSavedAt) : '刚刚记录') }}</p>
            </div>
          </div>
        </template>

        <div class="note-preview-body">
          <p class="note-preview-content">{{ notePreviewContent }}</p>
        </div>
      </el-dialog>

      <div class="bento-card bento-span-2 performance-card">
        <div class="card-header-flex">
          <h4>近期任务</h4>
          <div class="custom-pill-group mini">
            <button type="button" :class="['pill-btn', { active: timeRange === '7' }]" @click="timeRange = '7'">近 7 天</button>
            <button type="button" :class="['pill-btn', { active: timeRange === '30' }]" @click="timeRange = '30'">近 30 天</button>
          </div>
        </div>
        <div class="perf-grid">
          <div class="perf-box">
            <div class="perf-icon bg-blue-light"><el-icon class="text-blue"><Timer /></el-icon></div>
            <div class="perf-data">
              <span class="label">累计学习时长</span>
              <span class="value">
                {{ formatDurationValue(learningStats?.total_seconds) }}<small>{{ formatDurationUnit(learningStats?.total_seconds) }}</small>
              </span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-indigo-light"><el-icon class="text-indigo"><Reading /></el-icon></div>
            <div class="perf-data">
              <span class="label">已完成课程</span>
              <span class="value">{{ dynamicStats.completedCourses }} <small>门</small></span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-green-light"><el-icon class="text-green"><DocumentCopy /></el-icon></div>
            <div class="perf-data">
              <span class="label">生成资源数</span>
              <span class="value">{{ dynamicStats.generatedResources }} <small>个</small></span>
            </div>
          </div>
          <div class="perf-box">
            <div class="perf-icon bg-purple-light"><el-icon class="text-purple"><ChatDotRound /></el-icon></div>
            <div class="perf-data">
              <span class="label">AI 互动次数</span>
              <span class="value">{{ dynamicStats.interactions }} <small>次</small></span>
            </div>
          </div>
        </div>
      </div>

      <div class="bento-card bento-span-5 trend-section">
        <div class="card-header-flex">
          <h4 class="card-title">学习成长趋势（按课程）</h4>

          <div class="trend-course-selector">
            <template v-if="studentProfile.courses && studentProfile.courses.length > 1">
              <div class="custom-dropdown" :class="{ 'is-open': courseDropdownOpen }" @click="courseDropdownOpen = !courseDropdownOpen" @blur="courseDropdownOpen = false" tabindex="0">
                <div class="dropdown-selected">
                  <span class="selected-text" :title="selectedTrendCourse">{{ selectedTrendCourse || '选择课程' }}</span>
                  <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
                </div>
                <ul class="dropdown-options" v-show="courseDropdownOpen">
                  <li v-for="c in studentProfile.courses" :key="c"
                      :class="['dropdown-option', { active: selectedTrendCourse === c }]"
                      @click.stop="selectCourse(c)">
                    {{ c }}
                  </li>
                </ul>
              </div>
            </template>
            <template v-else-if="studentProfile.courses && studentProfile.courses.length === 1">
              <div class="custom-single-course">
                <el-icon><VideoPlay /></el-icon>
                <span>{{ studentProfile.courses[0] }}</span>
              </div>
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
                    placeholder="输入课程名后，按回车即可添加"
                    class="w-full"
                >
                  <template #tag>
                    <div v-if="profileForm.courses.length > 0" class="editor-course-selection">
                      <strong class="course-single-title" :title="profileForm.courses[0]">{{ profileForm.courses[0] }}</strong>
                      <el-popover
                          v-if="profileForm.courses.length > 1"
                          placement="top"
                          :width="220"
                          trigger="hover"
                          popper-class="course-popover"
                      >
                        <template #reference>
                          <el-button link type="primary" class="view-all-courses-btn" @click.stop>
                            共 {{ profileForm.courses.length }} 门
                          </el-button>
                        </template>
                        <div class="all-courses-popover-content">
                          <div class="popover-title">
                            <el-icon><VideoPlay /></el-icon> 正在学习的全部课程
                          </div>
                          <div class="popover-course-list">
                            <div v-for="(course, idx) in profileForm.courses" :key="course" class="popover-course-item">
                              <span class="course-number">{{ idx + 1 }}.</span>
                              <span class="course-name">{{ course }}</span>
                            </div>
                          </div>
                        </div>
                      </el-popover>
                    </div>
                  </template>
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

            <el-form-item prop="global_learning_goal">
              <template #label><span class="custom-label"><span class="req-star">*</span> 当前学习目标</span></template>
              <el-select v-model="profileForm.global_learning_goal" filterable allow-create default-first-option clearable placeholder="请选择学习目标，没有合适选项可直接输入">
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
                <template #label><span class="custom-label"><span class="req-star">*</span> 学校</span></template>
                <el-autocomplete
                    v-model="profileForm.school"
                    :fetch-suggestions="querySearchSchool"
                    placeholder="可以直接输入或搜索"
                    clearable
                    class="w-full"
                >
                  <template #prefix><el-icon><Search /></el-icon></template>
                  <template #default="{ item }">
                    <span>{{ item.value }}</span>
                    <span v-if="item.level" class="school-level-tag">{{ item.level }}</span>
                  </template>
                </el-autocomplete>
              </el-form-item>

              <el-form-item prop="grade">
                <template #label><span class="custom-label"><span class="req-star">*</span> 年级</span></template>
                <el-select v-model="profileForm.grade" filterable allow-create default-first-option clearable placeholder="请选择年级">
                  <el-option v-for="grade in PRESET_GRADES" :key="grade" :label="grade" :value="grade" />
                </el-select>
              </el-form-item>

              <el-form-item>
                <template #label><span class="custom-label">每天学习时间</span></template>
                <el-select v-model="profileForm.daily_study_time" clearable placeholder="请选择每天学习时间">
                  <el-option v-for="t in PRESET_DAILY_STUDY_TIME" :key="t" :label="t" :value="t" />
                </el-select>
              </el-form-item>

              <el-form-item>
                <template #label><span class="custom-label">编程语言（选填）</span></template>
                <el-select v-model="profileForm.programming_languages" multiple filterable allow-create default-first-option clearable placeholder="请选择编程语言">
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
            <span>带 <span class="req-star">*</span> 为必填项，完善信息后可获得更精准推荐</span>
          </div>
          <div class="footer-actions">
            <template v-if="currentEditorStep === 1">
              <el-button class="step-btn" @click="nextEditorStep(profileFormRef)">
                下一步<el-icon class="el-icon--right"><ArrowRight /></el-icon>
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
import { reactive, ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import {
  Aim,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ChatDotRound,
  Check,
  Checked,
  CircleCheckFilled,
  Clock,
  Cpu,
  DocumentCopy,
  Edit,
  InfoFilled,
  Reading,
  Search,
  Timer,
  UserFilled,
  VideoPlay,
} from '@element-plus/icons-vue'
import { uploadAvatar } from '@/features/auth/api/auth'
import { ensureCurrentUser, setCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import {
  getProfileOnboarding, updateProfileOnboarding,
} from '@/features/profile/api/profile'
import { getGeneratedResources } from '@/features/resource/api/resource-history'
import type { GeneratedResourceItem } from '@/features/resource/api/resource-history'
import { getLearningTimeStats } from '@/features/evaluation/api/evaluation'
import type { LearningTimeStats } from '@/features/evaluation/api/evaluation'
import { searchSchools } from '@/features/resource/api/school'
import type { SchoolItem } from '@/features/resource/api/school'
import type { ProfileOnboardingUpdate, StudentProfileData } from '@/features/profile/api/profile'
import { useGlobalNotesSnapshot } from '@/shared/model/globalNotes'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const router = useRouter()
const route = useRoute()
const { currentUser, userName } = useCurrentUser()
const notesSnapshot = useGlobalNotesSnapshot(computed(() => currentUser.value?.id))

const timeRange = ref('7')
const historyFilter = ref<'all' | 'completed'>('all')
const userEmail = ref<string | null>(null)
const userAvatar = ref<string | null>(null)
const avatarUploading = ref(false)
const profileEditorVisible = ref(false)
const currentEditorStep = ref(1)
const profileSubmitting = ref(false)
const profileFormRef = ref<FormInstance>()
const learningStats = ref<LearningTimeStats | null>(null)
const selectedTrendCourse = ref<string>('')
const resourceHistoryLoading = ref(false)
const courseDropdownOpen = ref(false)
const notePreviewVisible = ref(false)
const notePreviewContent = ref('')
const notePreviewSavedAt = ref('')
const notePreviewDraft = ref(false)

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

const profileRules = {
  school: [{ required: true, message: '请选择或填写学校', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  major: [{ required: true, message: '请填写或选择专业', trigger: 'change' }],
  courses: [{ required: true, type: 'array', min: 1, message: '请至少填写一门课程', trigger: 'change' }],
  global_learning_goal: [{ required: true, message: '请选择或填写当前学习目标', trigger: 'change' }],
}

const profileHeadline = computed(() => {
  const parts = [studentProfile.value.major, studentProfile.value.school]
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

const selectCourse = (c: string) => {
  selectedTrendCourse.value = c
  courseDropdownOpen.value = false
}

const dynamicStats = computed(() => {
  const totalCourses = studentProfile.value.courses?.length || 0

  return {
    generatedResources: resourceHistory.value.length,
    completedCourses: totalCourses,
    interactions: 0
  }
})

const lineOption = computed(() => {
  const dailyBreakdown = learningStats.value?.daily_breakdown || []
  const dates = dailyBreakdown.map((item) => {
    const date = new Date(item.date)
    if (Number.isNaN(date.getTime())) return item.date
    return `${date.getMonth() + 1}-${date.getDate()}`
  })
  const values = dailyBreakdown.map((item) => Math.round(item.seconds / 60))

  return {
    grid: { top: 30, right: 20, bottom: 25, left: 45 },
    tooltip: {
      trigger: 'axis',
      formatter: `{b} <br/>课程: ${selectedTrendCourse.value || '全部课程'} <br/>学习时长: {c} 分钟`
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#E2E8F0' } },
      axisLabel: { color: '#94A3B8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '学习时长',
      nameTextStyle: { color: '#94A3B8', fontSize: 10, padding: [0, 0, 0, 10] },
      splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
      axisLabel: { color: '#94A3B8', fontSize: 10 }
    },
    series: [{
      name: selectedTrendCourse.value,
      data: values,
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
  if (historyFilter.value === 'completed') {
    return tableData.value.filter(item => item.rawStatus === 'completed')
  }
  return tableData.value
})

const profileDraft = computed(() => notesSnapshot.draft.value.trim())
const profileSavedNotes = computed(() => notesSnapshot.savedNotes.value)

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
    notesSnapshot.sync()
    Promise.all([
      loadProfileInfo(),
      loadResourceHistory(),
      loadLearningStats()
    ]).catch(console.error)
  }
})

onMounted(async () => {
  notesSnapshot.sync()
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadLearningStats()
  ]).catch(console.error)
  openProfileEditorFromRoute()
})

onBeforeUnmount(() => {
  notesSnapshot.dispose()
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

const querySearchSchool = async (
  queryString: string,
  cb: (results: Array<{ value: string; level?: string | null }>) => void
) => {
  if (!queryString) {
    cb([])
    return
  }
  try {
    const res = await searchSchools(queryString, 20)
    const options = (res.data.data || []).map((school: SchoolItem) => ({
      value: school.name,
      level: school.level
    }))
    cb(options)
  } catch (e) {
    cb([])
  }
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
      studentProfile.value = onboardingData?.student_profile ?? studentProfile.value
      profileMeta.dailyStudyTime = baseInfo?.daily_study_time || ''
      profileMeta.globalLearningGoal = baseInfo?.global_learning_goal || onboardingData?.student_profile?.learning_goal || ''
      profileMeta.programmingLanguages = Array.isArray(baseInfo?.programming_languages)
        ? [...baseInfo.programming_languages]
        : []
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
    const res = await getGeneratedResources(1, 20)
    resourceHistory.value = res.data.data?.items || []
  } catch (e) {
    console.warn('加载资源生成历史失败', e)
    resourceHistory.value = []
  } finally {
    resourceHistoryLoading.value = false
  }
}

const beforeAvatarUpload = (file: File) => {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('仅支持 jpg、png、gif、webp 格式图片')
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
    if (currentUser.value) {
      setCurrentUser({
        ...currentUser.value,
        avatar: res.data.data.avatar
      })
    }
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

const nextEditorStep = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  try {
    await formEl.validateField(['major', 'courses', 'global_learning_goal'])
    currentEditorStep.value = 2
  } catch {
    ElMessage.warning('请先完善当前页面的必填项')
  }
}

const submitProfile = async (formEl: FormInstance | undefined) => {
  if (!formEl) return
  const valid = await formEl.validate().catch(() => false)
  if (!valid) return
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
    ElMessage.success('学习资料已更新')
    await loadProfileInfo()
  } catch (e: any) {
    console.error('Failed to update profile onboarding', e)
    ElMessage.error(e.response?.data?.message || '保存失败，请稍后重试')
  } finally {
    profileSubmitting.value = false
  }
}

const viewResourceDetail = (row: { id: number }) => {
  router.push({ name: 'ResourceDetail', params: { id: row.id } })
}

const getHistoryIcon = (status: string) => {
  if (status === 'failed') return InfoFilled
  if (status === 'pending' || status === 'processing') return Cpu
  return Check
}

const getStatusClass = (status: string) => {
  return `status-${status}`
}

const formatNoteTime = (savedAt: string) => {
  const date = new Date(savedAt)
  if (Number.isNaN(date.getTime())) return '刚刚保存'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
const getNoteSummary = (content: string) => {
  const normalized = content.replace(/\s+/g, ' ').trim()
  return normalized || '绌虹櫧绗旇'
}

const openNotePreview = (note: { id?: string; content: string; savedAt?: string }, isDraft = false) => {
  notePreviewContent.value = note.content
  notePreviewSavedAt.value = note.savedAt || ''
  notePreviewDraft.value = isDraft
  notePreviewVisible.value = true
}
</script>

<style scoped>
.course-link { color: var(--color-primary); text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 4px; }
.course-link:hover { text-decoration: underline; }

.profile-dashboard {
  padding: var(--space-8); background-color: var(--color-bg); min-height: 100%; font-family: var(--font-sans);
}
.bento-container { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-6); }
.bento-card { background: var(--color-surface); border-radius: 8px; padding: var(--space-6); border: 1px solid var(--color-border); display: flex; flex-direction: column; }
.profile-notes-card {
  height: 224px;
}
.performance-card {
  height: 224px;
}
.bento-span-2 { grid-column: span 2; }
.bento-span-3 { grid-column: span 3; }
.bento-span-4 { grid-column: span 4; }
.bento-span-5 { grid-column: span 5; }

/* ======== 銆愭牳蹇冩牱寮忎慨鏀瑰尯銆戦《閮ㄥ寘瑁瑰眰甯冨眬 ======== */
.top-row-wrapper {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
  gap: var(--space-6);
  align-items: stretch;
  width: 100%;
}

.user-card {
  min-width: 0;
  position: relative;
  background: linear-gradient(135deg, var(--color-surface) 0%, rgba(79, 70, 229, 0.02) 100%);
  transition: all var(--transition-slow);
}

.user-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-border);
}

.combined-profile-wrapper {
  min-width: 0;
  position: relative;
  height: 100%;
}

.combined-profile-card {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  box-sizing: border-box !important;
  margin: 0 !important;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.profile-tabs-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  margin-top: var(--space-4);
}

.profile-notes-header {
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.profile-notes-title-block {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.profile-notes-subtitle {
  display: none;
}

.profile-notes-summary {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
}

.notes-draft-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: var(--weight-semibold);
}

.profile-notes-body {
  flex: 1;
  min-height: 0;
  display: flex;
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.92), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(226, 232, 240, 0.9);
  padding: 12px;
  overflow: hidden;
}

.profile-notes-stack {
  width: 100%;
  min-height: 0;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding-right: 4px;
}

.profile-note-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(248, 250, 252, 0.96));
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04);
  cursor: pointer;
  transition: border-color var(--transition-base), box-shadow var(--transition-base), transform var(--transition-base);
}

.profile-note-item:hover {
  border-color: var(--color-primary-border);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
}

.draft-note-item {
  border-color: var(--color-primary-border);
  background: linear-gradient(180deg, rgba(238, 242, 255, 0.9), rgba(248, 250, 252, 0.96));
}

.note-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.note-state-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.72rem;
  font-weight: var(--weight-bold);
}

.note-state-badge.subtle {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}

.note-time-text,
.notes-card-count {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.note-item-title {
  margin: 0;
  color: var(--color-text);
  font-size: 0.88rem;
  line-height: 1.5;
  font-weight: var(--weight-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.profile-notes-empty {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-notes-empty-inner {
  width: 100%;
  min-height: 100%;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.03) 0%, rgba(79, 70, 229, 0.08) 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: var(--space-6);
  text-align: center;
  color: var(--color-text-muted);
}

.profile-notes-empty-inner span {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.profile-notes-empty-inner p {
  margin: 0;
  line-height: 1.6;
}

/* 鍝嶅簲寮忚皟鏁达紙灏忓睆骞曚笅鎭㈠涓婁笅鍫嗗彔锛?*/
@media (max-width: 1200px) {
  .top-row-wrapper {
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }
  .user-card, .combined-profile-wrapper {
    flex: none;
    width: 100%;
  }
  .combined-profile-wrapper {
    height: 500px;
  }
  .combined-profile-card {
    position: relative;
    height: 100%;
  }
  .bento-container { grid-template-columns: repeat(2, 1fr); }
  .bento-span-3 { grid-column: span 2; }
  .bento-span-4 { grid-column: span 2; }
  .bento-span-5 { grid-column: span 2; }
}

@media (max-width: 768px) {
  .bento-container { grid-template-columns: 1fr; }
  .bento-span-2, .bento-span-3, .bento-span-4, .bento-span-5 { grid-column: span 1; }
  .profile-notes-card { height: 360px; }
  .performance-card { height: auto; min-height: 260px; }
  .combined-profile-wrapper {
    height: 450px;
  }
  .profile-notes-header {
    flex-direction: column;
    align-items: stretch;
  }
  .profile-notes-summary {
    align-items: flex-start;
  }
}

.note-preview-header h3 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 1.05rem;
}

.note-preview-header p {
  margin: 6px 0 0;
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.note-preview-body {
  max-height: min(62vh, 520px);
  overflow-y: auto;
  padding-right: 4px;
}

.note-preview-content {
  margin: 0;
  color: var(--color-text);
  font-size: 0.92rem;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.user-divider {
  width: 100%;
  height: 1px;
  border-top: 1px dashed var(--color-border);
  margin: var(--space-4) 0;
}
.profile-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
  width: 100%;
  margin-top: var(--space-2);
}
.info-mini-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--color-bg);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  transition: all var(--transition-fast);
}
.info-mini-card:hover {
  border-color: var(--color-primary-border);
  background: var(--color-primary-soft);
}
.info-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(79, 70, 229, 0.06);
  color: var(--color-primary);
  font-size: 1rem;
  flex-shrink: 0;
}
.info-content-box {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
  flex: 1;
}
.info-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: 2px;
  font-weight: 500;
}
.info-value {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-strong);
  width: 100%;
  text-align: left;
  min-width: 0;
}
.school-info-strong {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  min-width: 0;
  width: 100%;
}
.school-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 0 1 auto;
  min-width: 0;
}

.user-card .user-card-course-wrapper {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-start;
  width: 100%;
  margin-left: 0 !important;
  min-width: 0;
  flex-wrap: wrap;
}

.user-card .user-card-course-title {
  color: var(--color-text-strong);
  font-size: 0.85rem;
  font-weight: 700;
  max-width: none;
  flex: 0 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin: 0;
}

.user-card .user-card-view-btn {
  font-size: 0.72rem !important;
  color: var(--color-primary) !important;
  padding: 0 !important;
  margin-left: 2px !important;
  height: auto !important;
  flex-shrink: 0;
}

.user-header {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  margin-bottom: 0;
  position: relative;
  text-align: left;
  width: 100%;
}

/* ================= 銆愯嚜瀹氫箟 UI 缁勪欢鍖恒€?================= */

/* 1. 鑷畾涔夎兌鍥婏細缂栬緫璧勬枡鎸夐挳 */
/* 1. 自定义胶囊：编辑资料按钮 */
.custom-edit-btn {
  position: absolute; right: 0; top: 0;
  font-size: 0.8rem;
  padding: 6px 14px !important;
  border-radius: var(--radius-pill) !important;
  min-height: auto !important;
}

/* 2. 自定义丝滑分段控制器 (近期任务 / 资源历史) */
.custom-pill-group {
  display: inline-flex;
  background: var(--color-surface-hover, var(--color-surface-hover));
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}
.custom-pill-group.mini {
  border-radius: 6px;
  padding: 2px;
}
.custom-pill-group .pill-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 4px 14px !important;
  border-radius: 6px !important;
  min-height: auto !important;
  cursor: pointer;
  box-shadow: none !important;
  transform: none !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.custom-pill-group.mini .pill-btn {
  padding: 3px 10px !important;
  font-size: 0.75rem;
  border-radius: 4px !important;
}
.custom-pill-group .pill-btn:hover {
  color: var(--color-text-strong);
  transform: none !important;
  box-shadow: none !important;
}
.custom-pill-group .pill-btn:active {
  transform: none !important;
}
.custom-pill-group .pill-btn.active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08) !important;
  font-weight: 700;
}

/* 3. 鑷畾涔夊師鐢熼鏍间笅鎷夎彍鍗?(璇剧▼鍒囨崲) */
.custom-dropdown {
  position: relative; display: inline-flex; align-items: center;
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 8px; font-size: 0.82rem; font-weight: 600;
  color: var(--color-text-strong); cursor: pointer; user-select: none;
  min-width: 140px; transition: all 0.2s ease; outline: none;
}
.custom-dropdown:hover { border-color: var(--color-border-hover); }
.custom-dropdown.is-open { border-color: var(--color-primary); box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1); }
.dropdown-selected {
  display: flex; justify-content: space-between; align-items: center;
  width: 100%; padding: 6px 12px; gap: 8px;
}
.selected-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; text-align: left; }
.dropdown-arrow { font-size: 0.8rem; color: var(--color-text-muted); transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1); }
.custom-dropdown.is-open .dropdown-arrow { transform: rotate(180deg); }
.dropdown-options {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0;
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 8px; padding: 4px; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.1);
  z-index: 100; max-height: 200px; overflow-y: auto; list-style: none; margin: 0;
}
.dropdown-option {
  padding: 8px 10px; border-radius: 4px; color: var(--color-text-secondary);
  transition: all 0.15s; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dropdown-option:hover { background: var(--color-surface-hover); color: var(--color-text-strong); }
.dropdown-option.active { background: var(--color-primary-soft); color: var(--color-primary); font-weight: 700; }
.custom-single-course {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
  background: var(--color-primary-soft); color: var(--color-primary);
  border-radius: 8px; font-size: 0.82rem; font-weight: 700;
}

/* ==================================================== */

.avatar-uploader { cursor: pointer; }
.avatar-box { width: 72px; height: 72px; background: var(--color-primary-soft); border-radius: var(--radius-pill); display: flex; align-items: center; justify-content: center; font-size: 2.2rem; color: var(--color-primary); position: relative; overflow: hidden; transition: background-color var(--transition-slow), transform var(--transition-slow); box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1); }
.avatar-box:hover { background: var(--color-primary-soft); transform: scale(1.05); }
.avatar-box.has-avatar { background: transparent; }
.avatar-image { width: 100%; height: 100%; object-fit: cover; border-radius: var(--radius-pill); }
.avatar-upload-overlay { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity var(--transition-slow); border-radius: var(--radius-pill); }
.avatar-box:hover .avatar-upload-overlay { opacity: 1; }
.avatar-upload-overlay .el-icon { color: white; font-size: 1.5rem; }
.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}
.name-row { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.name-row h3 { margin: 0; font-size: 1.4rem; color: var(--color-text); font-weight: 800; letter-spacing: -0.02em; }
.verify-icon { color: var(--color-primary); font-size: 1.15rem; }
.email-text { color: var(--color-text-muted); font-size: 0.82rem; margin: 0 0 var(--space-1) 0; }
.major { font-size: 0.88rem; color: var(--color-text-secondary); margin: 0 0 var(--space-2) 0; font-weight: 500; }
.tags { display: flex; gap: var(--space-2); }
.tag { padding: 2px 8px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; background: var(--color-primary-soft); color: var(--color-primary); border: 1px solid transparent; }
.tag.outline { background: transparent; border: 1px solid var(--color-primary-border); color: var(--color-primary-text); }
.w-full { width: 100%; }

/* Radar & Trend */
.radar-container { height: 220px; width: 100%; flex: 1; }
.trend-chart-container { height: 220px; width: 100%; flex: 1; }

/* Performance */
.perf-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; flex: 1; align-content: stretch; }
.perf-box { display: flex; align-items: center; gap: 12px; background: var(--color-bg); padding: 12px 14px; border-radius: var(--radius-xl); }
.perf-icon { width: 44px; height: 44px; border-radius: var(--radius-full); display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
.bg-blue-light { background: var(--color-info-soft); }
.bg-indigo-light { background: var(--color-primary-soft); }
.bg-green-light { background: var(--color-success-soft); }
.bg-orange-light { background: #fff2e8; }
.bg-purple-light { background: #f3e8ff; }
.text-blue { color: var(--color-info); }
.text-indigo { color: var(--color-primary); }
.text-green { color: var(--color-success); }
.text-orange { color: #fa8c16; }
.text-purple { color: #9333ea; }
.perf-data .label { font-size: var(--text-xs); color: var(--color-text-muted); display: block; margin-bottom: 2px; }
.perf-data .value { font-size: 1.1rem; font-weight: var(--weight-bold); color: var(--color-text-strong); }

/* Profile Info List */
.profile-info-list { display: flex; flex-direction: column; gap: 18px; flex: 1; justify-content: center; }
.profile-info-row { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); padding-bottom: 14px; border-bottom: 1px solid var(--color-surface-hover); }
.profile-info-row:last-child { border-bottom: none; padding-bottom: 0; }
.profile-info-row span { display: flex; align-items: center; gap: var(--space-2); color: var(--color-text-muted); font-size: 0.85rem; flex-shrink: 0; }
.profile-info-row strong { color: var(--color-text); font-size: 0.88rem; line-height: 1.5; text-align: right; font-weight: var(--weight-bold); overflow-wrap: anywhere; }
.school-info-strong {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}
.school-info-strong .school-level-tag {
  margin-left: 0;
  margin-right: var(--space-2);
}

.card-header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); }
.card-title, .card-header-flex h4 { margin: 0; font-size: var(--text-md); font-weight: var(--weight-bold); color: var(--color-text-strong); display: flex; align-items: center; gap: var(--space-2); }
.link-text { font-size: var(--text-xs); color: var(--color-info); cursor: pointer; }
.trend-course-selector { display: flex; align-items: center; gap: 10px; }
.single-course-tag { display: flex; align-items: center; gap: 4px; font-weight: var(--weight-semibold); border-radius: var(--radius-sm); }
.no-course-text { font-size: 12px; color: var(--color-text-muted); }
.main-card-header { padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border); margin-bottom: var(--space-4) !important; }

.task-title-cell { font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.custom-tag { border-radius: var(--radius-sm); }

/* 婊氬姩鏉′紭鍖?*/
.history-card :deep(.el-scrollbar__bar.is-vertical) { width: 6px !important; }
.history-card :deep(.el-scrollbar__thumb) { background-color: var(--color-border-hover) !important; border-radius: 4px; }
.history-card :deep(.el-scrollbar__thumb:hover) { background-color: var(--color-text-faint) !important; }

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

/* 璁?ECharts 鐢诲竷濉弧澶栭儴瀹瑰櫒 */
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

.profile-meta-tags {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* ======== 鍙充笂瑙掔嫭绔嬭兌鍥婃寜閽粍 ======== */
/* 瀹瑰櫒锛氬交搴曞幓闄よ儗鏅鍜岀粺涓€杈规锛屼娇鐢?gap 鎷夊紑闂磋窛 */
.custom-tab-switcher {
  display: flex;
  gap: 12px;
  align-items: center;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

/* 鐙珛鎸夐挳锛氬崟鐙祴浜堝舰鐘躲€佽竟妗嗗拰闃村奖 */
.switcher-btn {
  background: var(--color-surface);
  border: 1px solid var(--color-border, var(--color-border));
  padding: 6px 18px;
  border-radius: 100px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text-secondary, var(--color-text-muted));
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

.switcher-btn:hover {
  color: var(--color-text-strong, var(--color-text));
  border-color: var(--color-border-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(15, 23, 42, 0.05);
}

.switcher-btn.active {
  background: var(--color-primary, var(--color-primary));
  color: var(--color-surface);
  border-color: var(--color-primary, var(--color-primary));
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
  transform: translateY(-1px);
}
/* ================================================= */

/* 婊氬姩鏉℃牱寮忕編鍖?*/
.profile-tabs-content::-webkit-scrollbar {
  width: 6px;
}
.profile-tabs-content::-webkit-scrollbar-thumb {
  background: var(--color-border, var(--color-border));
  border-radius: 4px;
}
.profile-tabs-content::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}

.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dimension-item {
  padding: 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  cursor: pointer;
  transition: all 0.25s ease;
  margin-bottom: 4px;
}
.dimension-item:hover {
  border-color: var(--color-primary-hover, var(--color-primary));
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.05);
  background: var(--color-surface-hover, #FAF9FF);
}
.dimension-item.is-active {
  border-color: var(--color-primary, var(--color-primary));
  background: var(--color-primary-soft, var(--color-primary-soft));
}
.dim-main-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 0.9rem;
}
.dim-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary, var(--color-primary));
  font-size: 0.95rem;
}
.dim-name {
  color: var(--color-text-strong);
  flex: 1;
}
.dim-score {
  color: var(--color-text);
  font-weight: 800;
}
.dim-trend {
  display: inline-flex;
  align-items: center;
}
.dim-trend.up { color: var(--color-success, var(--color-success)); }
.dim-trend.down { color: var(--color-danger, var(--color-danger)); }
.dim-trend.stable { color: var(--color-text-faint, var(--color-text-faint)); }

.dim-progress-track {
  width: 100%;
  height: 6px;
  background: var(--color-border, var(--color-border));
  border-radius: 3px;
  margin-top: 10px;
  overflow: hidden;
}
.dim-progress-bar {
  height: 100%;
  border-radius: 3px;
  background-color: var(--color-primary, var(--color-primary));
  transition: width 0.4s ease;
}
.dim-progress-bar.weakness_points {
  background-color: var(--color-warning, var(--color-warning));
}

.dim-summary-short {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dim-summary-expanded {
  font-size: 0.85rem;
  color: var(--color-text);
  line-height: 1.55;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-border);
}
.dim-desc-p {
  margin: 0 0 10px 0;
}
.dim-evidence-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(255, 255, 255, 0.6);
  padding: 8px 10px;
  border-radius: 6px;
  margin-top: 8px;
}
.evidence-lbl {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-secondary);
}
.evidence-list-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.evidence-item-tag {
  font-size: 0.72rem;
  padding: 2px 6px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-text-muted);
}

/* Weakness details styles */
.weakness-details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 4px;
}
.section-title-bar {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}
.weak-detail-card {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-surface);
  margin-bottom: 8px;
}
.weak-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.weak-card-header strong {
  font-size: 0.95rem;
  color: var(--color-text-strong);
}
.weak-rec-text {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin: 0 0 12px 0;
}
.weak-action-btn {
  border-radius: 6px !important;
  font-weight: 700 !important;
}

/* Profile timeline styles */
.profile-history-timeline {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px 4px 10px 10px;
}
.history-log-card {
  cursor: pointer;
  border: 1px solid var(--color-border) !important;
  transition: all 0.2s ease;
}
.history-log-card:hover {
  border-color: var(--color-primary-hover) !important;
  background: var(--color-surface-hover);
}
.history-log-card.is-selected {
  border-color: var(--color-primary) !important;
  background: var(--color-primary-soft);
}
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.log-header strong {
  font-size: 0.9rem;
  color: var(--color-text-strong);
}
.log-reason {
  font-size: 0.8rem;
  color: var(--color-text);
  margin: 0 0 8px 0;
  line-height: 1.45;
}
.log-meta {
  display: flex;
  gap: 12px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* Comparison styles */
.history-compare-panel {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid var(--color-primary-border, var(--color-primary-border));
  border-radius: 8px;
  background: #F9FAFF;
  animation: fadeIn var(--transition-slow);
}
.compare-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 12px;
  border-bottom: 1px solid var(--color-primary-border);
  padding-bottom: 6px;
}
.compare-scores-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.compare-score-row {
  display: flex;
  align-items: center;
  gap: 14px;
}
.c-dim-name {
  width: 70px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-text-strong);
  text-align: right;
}
.c-dim-bars {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.c-bar-current, .c-bar-historical {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.72rem;
}
.bar-lbl {
  width: 60px;
  color: var(--color-text-muted);
  text-align: right;
}
.c-bar-current :deep(.el-progress),
.c-bar-historical :deep(.el-progress) {
  flex: 1;
}
.c-bar-current :deep(.el-progress__text),
.c-bar-historical :deep(.el-progress__text) {
  font-size: 0.72rem !important;
  font-weight: 700;
  min-width: 28px;
}

/* Footer info */
.profile-card-footer {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  margin-top: auto;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
.meta-footer-item strong {
  color: var(--color-text);
  font-weight: 600;
}
.school-level-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  padding: 2px 6px;
  border-radius: 999px;
  margin-left: 0;
  line-height: 1.2;
}

@media (max-width: 720px) {
  .profile-form-grid { grid-template-columns: 1fr; gap: 0; }
  .dialog-custom-footer { flex-direction: column; gap: var(--space-3); align-items: flex-start; }
  .editor-step-indicator .step-line { width: 40px; }
}

</style>

<style>
/* 淇浣犵殑鍏ㄥ眬寮圭獥鏍峰紡瑕嗙洊寮曞彂鑳屾櫙閫忔槑鐨勯棶棰?*/
.course-popover {
  padding: 12px !important;
  border-radius: 8px !important;
  box-shadow: var(--shadow-lg), 0 4px 20px rgba(0,0,0,0.1) !important; /* 澧炲姞闃村奖锛屽寮哄眰绾ф劅 */
  border: 1px solid var(--color-border) !important;
  background: var(--color-surface, var(--color-surface)) !important; /* 寮哄埗鐧借壊鑳屾櫙锛岄槻姝㈠唴瀹圭┛閫忛噸鍙?*/
  z-index: 9999 !important; /* 鎻愬崌灞傜骇 */
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

/* ============================================================
   璧勬簮鐢熸垚鍘嗗彶 鈥斺€斺€?鏃犵晫琛屽崱鐗囨祦鏍峰紡
   ============================================================ */
.history-list-flow {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: 4px;
}

.history-row-card {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 12px 18px 12px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);
}

.history-row-card:hover {
  transform: translateX(4px);
  border-color: var(--color-primary-border);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.06);
}

/* 宸︿晶鐘舵€佹寚绀哄僵鑹叉潯 */
.history-row-card .status-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--color-text-faint);
  transition: width 0.2s ease;
}

.history-row-card:hover .status-bar {
  width: 6px;
}

.history-row-card.status-completed .status-bar {
  background: var(--color-success);
}

.history-row-card.status-pending .status-bar,
.history-row-card.status-processing .status-bar {
  background: var(--color-primary);
}

.history-row-card.status-failed .status-bar {
  background: var(--color-danger);
}

/* 鍥炬爣鍖呰９鍣?*/
.item-icon-wrapper {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.05rem;
  flex-shrink: 0;
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  transition: transform 0.2s ease;
}

.history-row-card:hover .item-icon-wrapper {
  transform: scale(1.05);
}

.history-row-card.status-completed .item-icon-wrapper {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.history-row-card.status-pending .item-icon-wrapper,
.history-row-card.status-processing .item-icon-wrapper {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.history-row-card.status-failed .item-icon-wrapper {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

/* 涓讳綋淇℃伅鍖?*/
.item-main-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.item-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-sub-meta {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.item-time {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

/* 鐘舵€佽嵂涓歌兌鍥?*/
.status-badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  font-weight: var(--weight-bold);
  font-size: 0.7rem;
}

.status-badge-pill.completed {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.status-badge-pill.pending,
.status-badge-pill.processing {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.status-badge-pill.failed {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

/* 鐢熸垚涓懠鍚哥伅鍔ㄧ敾 */
.status-badge-pill.pending .badge-dot,
.status-badge-pill.processing .badge-dot {
  animation: badge-pulse 1.6s infinite alternate;
}

@keyframes badge-pulse {
  0% { transform: scale(0.9); opacity: 0.4; }
  100% { transform: scale(1.3); opacity: 1; }
}

/* 鍙充晶鍔ㄤ綔鏌ョ湅鎸夐挳 */
.item-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-primary);
  opacity: 0.6;
  transition: all var(--transition-fast);
  padding: 4px var(--space-2);
  border-radius: var(--radius-sm);
}

.history-row-card:hover .item-action-btn {
  opacity: 1;
  background: var(--color-primary-soft);
}

.action-arrow {
  transition: transform 0.2s ease;
}

.history-row-card:hover .action-arrow {
  transform: translateX(3px);
}

.empty-history {
  padding: var(--space-6) 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
