<template>
  <main class="profile-page min-h-screen font-sans antialiased text-left">
    <div class="profile-shell">
      <div class="profile-title-row profile-motion-item">
        <div class="title-mark">
          <UserRound class="h-7 w-7" />
        </div>
        <h1>个人中心</h1>
      </div>

      <div class="profile-layout-grid">
        <!-- Left Sidebar (Academic Profile Card) -->
        <aside class="academic-profile-sidebar profile-motion-item">
          <!-- Profile Card Header -->
          <div class="sidebar-user-info">
            <Button
              variant="ghost"
              class="avatar-button"
              :disabled="avatarUploading"
              aria-label="更换头像"
              @click="triggerAvatarUpload"
            >
              <input
                ref="avatarInput"
                type="file"
                class="hidden"
                accept="image/*"
                @change="onAvatarFileChange"
              />
              <Avatar class="profile-avatar">
                <AvatarImage
                  v-if="userAvatar"
                  :src="userAvatar"
                  alt="用户头像"
                />
                <AvatarFallback>{{
                  userName?.slice(0, 1) || "U"
                }}</AvatarFallback>
              </Avatar>
              <span class="avatar-edit-mask">
                <Edit class="h-4 w-4" />
              </span>
            </Button>

            <h2 class="user-name">{{ userName }}</h2>
            <span class="academic-role-badge">智能系统学习者</span>
            <p class="user-email">{{ userEmail || "邮箱待同步" }}</p>
            <p class="user-headline">{{ profileHeadline || "暂无个性签名" }}</p>
          </div>

          <!-- Academic Info Grid -->
          <div class="sidebar-details-section">
            <div class="detail-group">
              <span class="detail-label">就读学校</span>
              <strong class="detail-value">{{
                studentProfile.school || "点击下方编辑资料完善学校"
              }}</strong>
            </div>

            <div class="detail-group">
              <span class="detail-label">专业领域</span>
              <strong class="detail-value">{{
                studentProfile.major || "未填写"
              }}</strong>
            </div>

            <div class="detail-group">
              <span class="detail-label">年级阶段</span>
              <strong class="detail-value">{{
                studentProfile.grade || "未填写"
              }}</strong>
            </div>

            <div class="detail-group">
              <span class="detail-label">当前学习目标</span>
              <strong class="detail-value">{{
                profileMeta.globalLearningGoal ||
                studentProfile.learning_goal ||
                "未设置"
              }}</strong>
            </div>

            <div class="detail-group">
              <span class="detail-label">每日计划学习时间</span>
              <strong class="detail-value">{{
                profileMeta.dailyStudyTime || "未设置"
              }}</strong>
            </div>

            <div class="detail-group">
              <span class="detail-label">正在学习课程</span>
              <div class="detail-badges vertical-badges">
                <span
                  v-for="course in displayCourses"
                  :key="course"
                  class="detail-badge-pill"
                  >{{ course }}</span
                >
                <span v-if="!displayCourses.length" class="empty-badge-pill"
                  >未选课</span
                >
              </div>
            </div>

            <div class="detail-group">
              <span class="detail-label">常用编程语言</span>
              <div class="detail-badges vertical-badges">
                <span
                  v-for="lang in displayLanguages"
                  :key="lang"
                  class="detail-badge-pill lang-pill"
                  >{{ lang }}</span
                >
                <span v-if="!displayLanguages.length" class="empty-badge-pill"
                  >未设置</span
                >
              </div>
            </div>
          </div>

          <!-- Actions at bottom -->
          <div class="sidebar-actions">
            <Button
              variant="outline"
              class="edit-profile-button w-full"
              @click="openProfileEditor"
            >
              <Edit class="h-4 w-4" />
              编辑学业资料
            </Button>
          </div>
        </aside>

        <!-- Right Main Panel (Learning Dashboard) -->
        <section class="analytics-dashboard-main profile-motion-item">
          <!-- Controls & Header -->
          <div class="dashboard-header">
            <div class="panel-heading">
              <ChartColumn class="h-5 w-5 text-indigo-500" />
              <h3>学业数据看板</h3>
            </div>
            <div class="dashboard-controls">
              <Select
                v-if="
                  studentProfile.courses && studentProfile.courses.length > 1
                "
                v-model="selectedTrendCourse"
              >
                <SelectTrigger class="course-trigger">
                  <SelectValue placeholder="切换课程" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem
                      v-for="course in studentProfile.courses"
                      :key="course"
                      :value="course"
                      class="text-xs cursor-pointer"
                    >
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

          <!-- Summary Metric Cards -->
          <div class="summary-card-grid">
            <div
              v-for="card in learningSummaryCards"
              :key="card.label"
              :class="['summary-card', card.themeClass]"
            >
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

          <!-- Dashboard Charts & Insights Bento Grid -->
          <div class="dashboard-grid">
            <!-- Left Column (Visualizations) -->
            <div class="visual-column">
              <div class="chart-panel focus-chart-panel">
                <div class="chart-heading">
                  <h4>学习专注走势</h4>
                  <span>(h)</span>
                </div>
                <div class="chart-box">
                  <v-chart class="chart" :option="lineOption" autoresize />
                  <div v-if="!hasLineChartData" class="chart-empty">
                    暂无学习时长数据
                  </div>
                </div>
              </div>

              <div class="visual-sub-grid">
                <div class="insight-panel resource-panel">
                  <div class="chart-heading">
                    <h4>学习产出分布</h4>
                    <span>{{
                      resourceHistoryLoading
                        ? "同步中"
                        : `${resourceHistory.length}份`
                    }}</span>
                  </div>
                  <div class="resource-mix-list">
                    <div
                      v-for="item in resourceMixRows"
                      :key="item.label"
                      class="resource-mix-row"
                    >
                      <div>
                        <span>{{ item.label }}</span>
                        <strong>{{ item.count }}份</strong>
                      </div>
                      <div class="mix-track">
                        <i
                          :style="{
                            width: `${item.percent}%`,
                            background: item.gradient,
                          }"
                        ></i>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="chart-panel scenario-chart-panel">
                  <div class="chart-heading">
                    <h4>功能使用占比</h4>
                  </div>
                  <div class="scenario-body">
                    <div class="donut-box">
                      <v-chart class="chart" :option="pieOption" autoresize />
                      <div v-if="!hasScenarioData" class="chart-empty">
                        暂无场景数据
                      </div>
                    </div>
                    <div class="scenario-list">
                      <div
                        v-for="item in scenarioBreakdown"
                        :key="item.name"
                        class="scenario-row"
                      >
                        <span class="scenario-name">
                          <i :style="{ backgroundColor: item.color }"></i>
                          {{ item.name }}
                        </span>
                        <strong>{{ item.percent }}%</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Right Column (Insights & Status) -->
            <div class="insights-column">
              <div class="insight-panel advice-panel">
                <div class="chart-heading">
                  <h4>薄弱点与建议</h4>
                </div>
                <div class="tag-cloud">
                  <span
                    v-for="topic in displayedWeakTopics"
                    :key="topic"
                    class="weak-tag"
                    >{{ topic }}</span
                  >
                  <span
                    v-if="displayedWeakTopics.length === 0"
                    class="empty-chip"
                    >暂无薄弱点</span
                  >
                </div>
                <div class="tag-cloud preference-cloud">
                  <span
                    v-for="resource in displayedPreferredResources"
                    :key="resource"
                    class="data-chip"
                    >{{ resource }}</span
                  >
                  <span
                    v-if="displayedPreferredResources.length === 0"
                    class="empty-chip"
                    >继续积累反馈</span
                  >
                </div>
                <div class="next-action-box">
                  <span>下一步建议</span>
                  <p>{{ primaryLearningAdvice }}</p>
                </div>
              </div>

              <div class="insight-panel status-panel">
                <div class="chart-heading">
                  <h4>学习状态速览</h4>
                </div>
                <div class="status-grid">
                  <div
                    v-for="item in learningStatusCards"
                    :key="item.label"
                    :class="['status-card', item.themeClass]"
                  >
                    <div class="status-card-head">
                      <component :is="item.icon" class="h-4 w-4 status-icon" />
                      <span>{{ item.label }}</span>
                    </div>
                    <strong>{{ item.value }}</strong>
                    <div class="status-progress-bar">
                      <div
                        class="status-progress-fill"
                        :style="{ width: `${item.percent}%` }"
                      ></div>
                    </div>
                    <small>{{ item.hint }}</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Modals -->
    <!-- Profile Editor Dialog -->
    <!-- Profile Editor Dialog -->
    <Dialog v-model:open="profileEditorVisible">
      <DialogContent
        class="profile-editor-dialog sm:max-w-[620px] w-full gap-0 overflow-hidden rounded-xl border border-slate-100 bg-white p-0 shadow-[0_28px_80px_rgba(15,118,110,0.16)]"
      >
        <DialogHeader class="sr-only">
          <DialogTitle>编辑学业资料</DialogTitle>
          <DialogDescription>
            完善就读学校、专业和课程信息，系统将据此为您智能推荐学习内容。
          </DialogDescription>
        </DialogHeader>

        <!-- Custom Gorgeous Header Banner -->
        <div class="dialog-header-banner">
          <div class="header-banner-content">
            <span class="header-badge">
              <Sparkles class="h-3 w-3 mr-1" /> MAS 画像同步
            </span>
            <h3>编辑个人学业画像</h3>
            <p>完善您的就读学校、当前年级与正在学习的课程信息，AI 将为您定制专属学习路径。</p>
          </div>
        </div>

        <!-- Form Scroll Area -->
        <div class="dialog-scroll-container">
          <form @submit.prevent class="dialog-form-layout">
            
            <!-- Section 1: 基础就读信息 -->
            <div class="form-section">
              <div class="section-title-wrapper">
                <span class="section-num">01</span>
                <span class="section-title">基础就读信息</span>
              </div>
              
              <!-- School -->
              <div class="form-field-group">
                <label class="form-field-label">
                  就读学校 <span class="text-rose-500">*</span>
                </label>
                <div class="relative">
                  <Input
                    v-model="profileForm.school"
                    type="text"
                    placeholder="请输入学校名称"
                    class="editor-input"
                    @focus="schoolFocus = true"
                    @blur="schoolFocus = false"
                  />
                  <div
                    v-if="profileErrors.school"
                    class="editor-error text-rose-500 text-[11px] mt-0.5"
                  >
                    {{ profileErrors.school }}
                  </div>

                  <ul
                    v-if="schoolFocus && schoolSuggestions.length > 0"
                    class="editor-suggestion-list"
                  >
                    <li
                      v-for="item in schoolSuggestions"
                      :key="item.value"
                      @mousedown="selectSchool(item.value)"
                    >
                      <span class="font-bold text-slate-700">{{
                        item.value
                      }}</span>
                      <small
                        v-if="item.level"
                        class="text-slate-400 text-[10px] ml-2"
                        >{{ item.level }}</small
                      >
                    </li>
                  </ul>
                </div>
              </div>

              <!-- Grade & Major (Grid) -->
              <div class="grid grid-cols-2 gap-4 mt-4">
                <!-- Grade -->
                <div class="form-field-group">
                  <label class="form-field-label">
                    年级阶段 <span class="text-rose-500">*</span>
                  </label>
                  <Select v-model="profileForm.grade">
                    <SelectTrigger class="editor-select-trigger">
                      <SelectValue placeholder="选择年级" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem
                          v-for="grade in PRESET_GRADES"
                          :key="grade"
                          :value="grade"
                          class="text-xs cursor-pointer"
                        >
                          {{ grade }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  <div
                    v-if="profileErrors.grade"
                    class="editor-error text-rose-500 text-[11px] mt-0.5"
                  >
                    {{ profileErrors.grade }}
                  </div>
                </div>

                <!-- Major -->
                <div class="form-field-group">
                  <label class="form-field-label">
                    专业 <span class="text-rose-500">*</span>
                  </label>
                  <div class="relative">
                    <Input
                      v-model="profileForm.major"
                      type="text"
                      placeholder="输入或选择专业"
                      class="editor-input"
                      @focus="majorFocus = true"
                      @blur="majorFocus = false"
                    />
                    <div
                      v-if="profileErrors.major"
                      class="editor-error text-rose-500 text-[11px] mt-0.5"
                    >
                      {{ profileErrors.major }}
                    </div>

                    <ul
                      v-if="majorFocus && majorSuggestions.length > 0"
                      class="editor-suggestion-list"
                    >
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
            </div>

            <!-- Section 2: 学习目标与时长 -->
            <div class="form-section mt-6">
              <div class="section-title-wrapper">
                <span class="section-num">02</span>
                <span class="section-title">学习目标与时长</span>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <!-- Goal -->
                <div class="form-field-group">
                  <label class="form-field-label">
                    当前学习目标 <span class="text-rose-500">*</span>
                  </label>
                  <Select v-model="profileForm.global_learning_goal">
                    <SelectTrigger class="editor-select-trigger">
                      <SelectValue placeholder="选择当前目标" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem
                          v-for="goal in PRESET_GOALS"
                          :key="goal"
                          :value="goal"
                          class="text-xs cursor-pointer"
                        >
                          {{ goal }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                  <div
                    v-if="profileErrors.global_learning_goal"
                    class="editor-error text-rose-500 text-[11px] mt-0.5"
                  >
                    {{ profileErrors.global_learning_goal }}
                  </div>
                </div>

                <!-- Daily study time -->
                <div class="form-field-group">
                  <label class="form-field-label">每日计划学习时间</label>
                  <Select v-model="profileForm.daily_study_time">
                    <SelectTrigger class="editor-select-trigger">
                      <SelectValue placeholder="请选择计划时间" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectGroup>
                        <SelectItem
                          v-for="time in PRESET_DAILY_STUDY_TIME"
                          :key="time"
                          :value="time"
                          class="text-xs cursor-pointer"
                        >
                          {{ time }}
                        </SelectItem>
                      </SelectGroup>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <!-- Section 3: 学习路径配置 -->
            <div class="form-section mt-6">
              <div class="section-title-wrapper">
                <span class="section-num">03</span>
                <span class="section-title">学习路径与偏好</span>
              </div>
              
              <!-- Courses -->
              <div class="form-field-group">
                <label class="form-field-label">
                  正在学习的课程 <span class="text-rose-500">*</span>
                </label>
                <div class="editor-chip-input-container">
                  <div class="editor-chip-input">
                    <span
                      v-for="(course, index) in profileForm.courses"
                      :key="course"
                      class="editor-course-chip"
                    >
                      {{ course }}
                      <Button
                        type="button"
                        variant="ghost"
                        class="editor-chip-remove"
                        aria-label="移除课程"
                        @click="removeCourse(index)"
                      >
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
                  <div
                    v-if="profileErrors.courses"
                    class="editor-error text-rose-500 text-[11px] mt-0.5"
                  >
                    {{ profileErrors.courses }}
                  </div>
                </div>

                <div class="editor-preset-block mt-2.5">
                  <span class="preset-label">快捷推荐课程：</span>
                  <div class="editor-preset-list">
                    <Button
                      v-for="course in PRESET_COURSES.slice(0, 8)"
                      :key="course"
                      type="button"
                      variant="outline"
                      class="editor-preset-button text-xs"
                      @click="
                        () => {
                          if (!profileForm.courses.includes(course))
                            profileForm.courses.push(course);
                        }
                      "
                    >
                      + {{ course }}
                    </Button>
                  </div>
                </div>
              </div>

              <!-- Programming Languages -->
              <div class="form-field-group mt-4">
                <label class="form-field-label">常用编程语言偏好（多选）</label>
                <div class="language-chips-grid">
                  <button
                    v-for="language in PRESET_LANGUAGES"
                    :key="language"
                    type="button"
                    :class="['lang-chip', { active: profileForm.programming_languages.includes(language) }]"
                    @click="toggleLanguage(language)"
                  >
                    <Check v-if="profileForm.programming_languages.includes(language)" class="h-3 w-3 mr-1 flex-shrink-0" />
                    <span class="truncate">{{ language }}</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Footer Actions -->
            <div class="flex justify-end gap-3 pt-5 mt-6 border-t border-slate-100">
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
                <span v-else class="flex items-center gap-1.5"
                  >保存修改 <Check class="h-4 w-4"
                /></span>
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  </main>
</template>

<script setup lang="ts">
import {
  reactive,
  ref,
  computed,
  onMounted,
  onBeforeUnmount,
  watch,
} from "vue";
import { useRoute } from "vue-router";
import { toast } from "vue-sonner";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { gsap } from "gsap";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  BadgeCheckIcon as BadgeCheck,
  BookOpenCheckIcon as BookOpenCheck,
  CalendarDaysIcon as CalendarDays,
  CheckIcon as Check,
  ChartColumnIcon as ChartColumn,
  Clock3Icon as Clock3,
  FileCheckIcon as FileCheck,
  GaugeIcon as Gauge,
  LayersIcon as Layers,
  PencilIcon as Edit,
  SparklesIcon as Sparkles,
  UserRoundIcon as UserRound,
  XIcon as Close,
} from "@lucide/vue";
import { uploadAvatar } from "@/features/auth/api/auth";
import {
  ensureCurrentUser,
  setCurrentUser,
  useCurrentUser,
} from "@/features/auth/model/currentUser";
import {
  getProfile,
  updateProfileOnboarding,
} from "@/features/profile/api/profile";
import {
  getRecentResources,
  getStudyStats,
} from "@/features/dashboard/api/home";
import type {
  RecentResourceItem,
  StudyStatsData,
} from "@/features/dashboard/api/home";
import { getGeneratedResources } from "@/features/resource/api/history";
import type { GeneratedResourceItem } from "@/features/resource/api/history";
import {
  getEvaluationSummary,
  getLearningTimeStats,
} from "@/features/evaluation/api/evaluation";
import type {
  EvaluationSummary,
  LearningTimeStats,
} from "@/features/evaluation/api/evaluation";
import { fetchWrongQuestions } from "@/features/question-bank/api/wrongQuestions";
import { searchSchools } from "@/features/profile/api/school";
import type { SchoolItem } from "@/features/profile/model/school";
import type {
  ProfileOnboardingUpdate,
  StudentProfileData,
} from "@/features/profile/api/profile";

use([
  CanvasRenderer,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
]);

const route = useRoute();
const { currentUser, userName } = useCurrentUser();

const timeRange = ref("7");
const userEmail = ref<string | null>(null);
const userAvatar = ref<string | null>(null);
const avatarUploading = ref(false);
const profileEditorVisible = ref(false);
const profileSubmitting = ref(false);
const learningStats = ref<LearningTimeStats | null>(null);
const evaluationSummary = ref<EvaluationSummary | null>(null);
const studyStats = ref<StudyStatsData | null>(null);
const selectedTrendCourse = ref<string>("");
const resourceHistoryLoading = ref(false);
const dashboardStatsLoading = ref(false);
const evaluationLoading = ref(false);
const wrongLoading = ref(false);
const wrongTotal = ref(0);

const studentProfile = ref<
  StudentProfileData & { learning_duration_total?: number }
>({
  school: null,
  school_level: null,
  grade: null,
  major: null,
  courses: [],
  learning_goal: null,
  preferred_language: null,
  learning_duration_total: 0,
});

const profileMeta = reactive({
  dailyStudyTime: "",
  globalLearningGoal: "",
  programmingLanguages: [] as string[],
});

interface ProfileFormData {
  grade: string;
  major: string;
  courses: string[];
  global_learning_goal: string;
  school: string;
  daily_study_time: string;
  programming_languages: string[];
}

const profileForm = reactive<ProfileFormData>({
  grade: "",
  major: "",
  courses: [],
  global_learning_goal: "",
  school: "",
  daily_study_time: "",
  programming_languages: [],
});

const resourceHistory = ref<GeneratedResourceItem[]>([]);
const recentDashboardResources = ref<RecentResourceItem[]>([]);

const PRESET_MAJORS = [
  "计算机科学与技术",
  "软件工程",
  "人工智能",
  "数据科学",
  "网络安全",
  "信息安全",
  "物联网工程",
  "通信工程",
  "电子信息工程",
  "数字媒体技术",
];
const PRESET_COURSES = [
  "数据结构",
  "算法分析",
  "操作系统",
  "计算机网络",
  "数据库系统",
  "计算机组成原理",
  "编译原理",
  "离散数学",
  "线性代数",
  "概率统计",
  "软件工程",
  "Web 开发",
  "机器学习",
  "深度学习",
  "计算机视觉",
  "NLP",
  "分布式系统",
  "云计算",
  "嵌入式开发",
  "移动端开发",
];
const PRESET_GOALS = [
  "期末考试冲刺",
  "完成课程设计项目",
  "大厂求职面试",
  "考研初试复习",
  "考研复试准备",
  "系统学习进阶",
  "零基础快速入门",
  "竞赛获奖",
  "个人兴趣拓展",
  "行业证书考取",
];
const PRESET_DAILY_STUDY_TIME = [
  "30min 以下",
  "30-60min",
  "1-2h",
  "2-3h",
  "3h 以上",
];
const PRESET_GRADES = [
  "大一",
  "大二",
  "大三",
  "大四",
  "研一",
  "研二",
  "研三",
  "博一",
  "博二",
  "博三",
  "高职一年级",
  "高职二年级",
  "高职三年级",
];
const PRESET_LANGUAGES = [
  "Python",
  "Java",
  "C/C++",
  "Go",
  "Rust",
  "JavaScript",
  "TypeScript",
  "SQL",
  "Shell",
  "Kotlin",
  "Swift",
  "PHP",
  "HTML/CSS",
];

const profileHeadline = computed(() => {
  const parts = [
    studentProfile.value.major,
    studentProfile.value.grade,
    studentProfile.value.learning_goal,
  ].filter((item): item is string => Boolean(item));
  return parts.length ? parts.join(" · ") : "学习资料待完善";
});

const preferredLanguages = computed(() => {
  if (profileMeta.programmingLanguages.length > 0) {
    return profileMeta.programmingLanguages.filter(Boolean);
  }
  return (studentProfile.value.preferred_language || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
});

const formatStudyDuration = (seconds?: number | null) => {
  if (!seconds || seconds <= 0) return "0m";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const hours = seconds / 3600;
  return `${Number.isInteger(hours) ? hours.toFixed(0) : hours.toFixed(1)}h`;
};

const displayLanguages = computed(() => preferredLanguages.value.slice(0, 5));
const displayCourses = computed(() =>
  (studentProfile.value.courses || []).filter(Boolean).slice(0, 5),
);

const boundedPercent = (value: number) =>
  Math.min(100, Math.max(0, Math.round(value)));

const profileCompletionPercent = computed(() => {
  const checks = [
    studentProfile.value.school,
    studentProfile.value.major,
    studentProfile.value.grade,
    studentProfile.value.learning_goal || profileMeta.globalLearningGoal,
    (studentProfile.value.courses || []).length > 0,
    preferredLanguages.value.length > 0,
    profileMeta.dailyStudyTime,
  ];
  const completed = checks.filter(Boolean).length;
  return boundedPercent((completed / checks.length) * 100);
});

const resourceTypeSet = computed(() => {
  const types = new Set<string>();
  resourceHistory.value.forEach((item) => {
    (item.resource_types || []).forEach((type) => {
      if (type) types.add(type);
    });
  });
  return types;
});

const resourceTypeCoverage = computed(() => resourceTypeSet.value.size);
const completedResourceCount = computed(
  () =>
    evaluationSummary.value?.completed_resources ||
    resourceHistory.value.length ||
    0,
);

const secondsForContexts = (...keys: string[]) => {
  const context = learningStats.value?.context_breakdown || {};
  return keys.reduce((sum, key) => sum + (context[key] || 0), 0);
};

const questionBankSeconds = computed(() =>
  secondsForContexts("QuestionBank", "question-bank"),
);
const tutorSeconds = computed(() => secondsForContexts("Tutor", "tutor"));
const pathPlanningSeconds = computed(() =>
  secondsForContexts(
    "LearningPathEntry",
    "LearningPathOverview",
    "LearningPathHistory",
    "LearningPathNode",
    "path-planner",
    "path-planner-overview",
    "path-planner-history",
    "path-planner-node",
  ),
);
const recommendationSeconds = computed(() =>
  secondsForContexts(
    "ResourceGenerator",
    "ResourceGenerator.vue",
    "ResourceDetail",
    "ResourceHistory",
    "PathResourceDetail",
    "PathResourceHistory",
    "resource-generator",
    "resource-detail",
    "ai/resources/history",
    "path-resource-detail",
    "path-resource-history",
  ),
);

const learningSummaryCards = computed(() => [
  {
    label: "本周活跃",
    value: `${studyStats.value?.weekly_days ?? learningStats.value?.streak_days ?? 0}天`,
    hint: `今日 ${formatStudyDuration(learningStats.value?.today_seconds || 0)}`,
    icon: CalendarDays,
    themeClass: "card-active",
  },
  {
    label: "学习产出",
    value: `${completedResourceCount.value}`,
    hint: evaluationSummary.value?.viewed_resources
      ? `已浏览 ${evaluationSummary.value.viewed_resources} 份`
      : `${resourceHistory.value.length}份生成记录`,
    icon: FileCheck,
    themeClass: "card-output",
  },
  {
    label: "学习时间",
    value: formatStudyDuration(learningStats.value?.total_seconds || 0),
    hint: `今日已学 ${formatStudyDuration(learningStats.value?.today_seconds || 0)}`,
    icon: Clock3,
    themeClass: "card-score",
  },
  {
    label: "待巩固错题",
    value: `${wrongTotal.value}题`,
    hint: wrongTotal.value > 0 ? "建议优先复盘" : "暂无积压",
    icon: BookOpenCheck,
    themeClass: "card-wrong",
  },
]);

const learningStatusCards = computed(() => [
  {
    label: "资料完整度",
    value: `${profileCompletionPercent.value}%`,
    hint: profileCompletionPercent.value >= 80 ? "推荐更精准" : "继续完善资料",
    percent: profileCompletionPercent.value,
    icon: BadgeCheck,
    themeClass: "theme-teal",
  },
  {
    label: "资源类型覆盖",
    value: `${Math.min(resourceTypeCoverage.value, 5)}/5`,
    hint: resourceHistoryLoading.value ? "同步中" : "文档/题库/案例等",
    percent: boundedPercent((resourceTypeCoverage.value / 5) * 100),
    icon: Layers,
    themeClass: "theme-purple",
  },
  {
    label: "评估样本",
    value: `${evaluationSummary.value?.event_count || 0}条`,
    hint: evaluationLoading.value ? "同步中" : "行为与测验信号",
    percent: boundedPercent(
      ((evaluationSummary.value?.event_count || 0) / 12) * 100,
    ),
    icon: ChartColumn,
    themeClass: "theme-indigo",
  },
  {
    label: "连续学习",
    value: `${learningStats.value?.streak_days || 0}天`,
    hint: dashboardStatsLoading.value ? "同步中" : `${timeRange.value}天窗口`,
    percent: boundedPercent(
      ((learningStats.value?.streak_days || 0) / 7) * 100,
    ),
    icon: Gauge,
    themeClass: "theme-amber",
  },
]);

const displayedWeakTopics = computed(() =>
  (evaluationSummary.value?.weak_topics || []).slice(0, 4),
);
const displayedPreferredResources = computed(() =>
  (evaluationSummary.value?.preferred_resources || []).slice(0, 4),
);
const primaryLearningAdvice = computed(() => {
  return (
    evaluationSummary.value?.recommendations?.[0] ||
    "继续完成资源学习与阶段测验，系统会逐步积累学习效果信号。"
  );
});

const resourceTypeLabels: Record<string, string> = {
  content: "知识文档",
  mindmap: "思维导图",
  quiz: "题库练习",
  code: "代码案例",
  reading: "阅读资料",
  ppt: "演示课件",
  video: "视频脚本",
};

const resourceGradients: Record<string, string> = {
  content: "linear-gradient(90deg, #0D9488, #2DD4BF)",
  mindmap: "linear-gradient(90deg, #EA580C, #FBBF24)",
  quiz: "linear-gradient(90deg, #6D28D9, #A78BFA)",
  code: "linear-gradient(90deg, #BE123C, #F43F5E)",
  reading: "linear-gradient(90deg, #047857, #34D399)",
  ppt: "linear-gradient(90deg, #0369A1, #38BDF8)",
  video: "linear-gradient(90deg, #DB2777, #F472B6)",
};

const resourceMixRows = computed(() => {
  const counts = new Map<string, number>();
  resourceHistory.value.forEach((item) => {
    const types = item.resource_types?.length
      ? item.resource_types
      : ["content"];
    types.forEach((type) => counts.set(type, (counts.get(type) || 0) + 1));
  });
  const rows = [...counts.entries()]
    .map(([type, count]) => ({
      label: resourceTypeLabels[type] || type,
      count,
      type,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);
  const max = Math.max(...rows.map((item) => item.count), 1);
  return rows.length
    ? rows.map((item) => ({
        ...item,
        percent: boundedPercent((item.count / max) * 100),
        gradient:
          resourceGradients[item.type] ||
          "linear-gradient(90deg, #079894, #62c9c5)",
      }))
    : [
        {
          label: "知识文档",
          count: 0,
          percent: 0,
          gradient: "linear-gradient(90deg, #0D9488, #2DD4BF)",
        },
        {
          label: "题库练习",
          count: 0,
          percent: 0,
          gradient: "linear-gradient(90deg, #6D28D9, #A78BFA)",
        },
        {
          label: "思维导图",
          count: 0,
          percent: 0,
          gradient: "linear-gradient(90deg, #EA580C, #FBBF24)",
        },
      ];
});

const scenarioBreakdown = computed(() => {
  const items = [
    { name: "题库练习", seconds: questionBankSeconds.value, color: "#818CF8" },
    { name: "AI辅导", seconds: tutorSeconds.value, color: "#2DD4BF" },
    { name: "路径规划", seconds: pathPlanningSeconds.value, color: "#FBBF24" },
    {
      name: "智能推荐",
      seconds: recommendationSeconds.value,
      color: "#34D399",
    },
  ];
  const total = items.reduce((sum, item) => sum + item.seconds, 0);
  return items.map((item) => ({
    ...item,
    percent: total > 0 ? Math.round((item.seconds / total) * 100) : 0,
  }));
});

const hasLineChartData = computed(() =>
  (learningStats.value?.daily_breakdown || []).some((item) => item.seconds > 0),
);
const hasScenarioData = computed(() =>
  scenarioBreakdown.value.some((item) => item.seconds > 0),
);

const lineOption = computed(() => {
  const dailyBreakdown = learningStats.value?.daily_breakdown || [];
  const dates = dailyBreakdown.map((item) => {
    const date = new Date(item.date);
    if (Number.isNaN(date.getTime())) return item.date;
    return `${date.getMonth() + 1}-${date.getDate()}`;
  });
  const values = dailyBreakdown.map((item) =>
    Number((item.seconds / 3600).toFixed(1)),
  );

  return {
    grid: { top: 24, right: 12, bottom: 28, left: 36 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#FCFFFF",
      borderColor: "#C8E4E3",
      borderWidth: 1,
      textStyle: { color: "#173B42", fontSize: 11 },
      formatter: `{b}<br/>课程：${selectedTrendCourse.value || "全部课程"}<br/>专注时长：{c}h`,
    },
    xAxis: {
      type: "category",
      data: dates,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "#DDEDEC" } },
      axisLabel: { color: "#6B858A", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "#DDEDEC", type: "dashed" } },
      axisLabel: { color: "#6B858A", fontSize: 10 },
    },
    series: [
      {
        name: selectedTrendCourse.value,
        data: values,
        type: "line",
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        lineStyle: { color: "#6366F1", width: 3 },
        itemStyle: { color: "#FCFFFF", borderColor: "#6366F1", borderWidth: 2 },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(99, 102, 241, 0.22)" },
              { offset: 1, color: "rgba(99, 102, 241, 0)" },
            ],
          },
        },
      },
    ],
  };
});

const pieOption = computed(() => {
  return {
    tooltip: {
      trigger: "item",
      formatter: "{b}: {d}%",
      backgroundColor: "#FCFFFF",
      borderColor: "#C8E4E3",
      borderWidth: 1,
      textStyle: { color: "#173B42", fontSize: 11 },
    },
    series: [
      {
        name: "学习场景占比",
        type: "pie",
        radius: ["58%", "78%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: "#FCFFFF",
          borderWidth: 2,
        },
        label: { show: false },
        labelLine: { show: false },
        data: hasScenarioData.value
          ? scenarioBreakdown.value.map((item) => ({
              value: item.seconds,
              name: item.name,
              itemStyle: { color: item.color },
            }))
          : [{ value: 1, name: "暂无数据", itemStyle: { color: "#DDEDEC" } }],
      },
    ],
  };
});

watch(
  () => studentProfile.value.courses,
  (newCourses) => {
    if (newCourses && newCourses.length > 0) {
      if (!newCourses.includes(selectedTrendCourse.value)) {
        selectedTrendCourse.value = newCourses[0] || "";
      }
    } else {
      selectedTrendCourse.value = "";
    }
  },
  { immediate: true },
);

watch(
  () => route.query.action,
  () => {
    openProfileEditorFromRoute();
  },
);

watch(timeRange, () => {
  loadLearningStats();
});

watch(
  () => route.path,
  (newPath) => {
    if (newPath === "/profile") {
      Promise.all([
        loadProfileInfo(),
        loadResourceHistory(),
        loadDashboardStats(),
        loadLearningStats(),
        loadEvaluationSummary(),
        loadWrongOverview(),
      ]).catch(console.error);
    }
  },
);

let profileMotionContext: ReturnType<typeof gsap.context> | null = null;
onMounted(async () => {
  await Promise.all([
    loadProfileInfo(),
    loadResourceHistory(),
    loadDashboardStats(),
    loadLearningStats(),
    loadEvaluationSummary(),
    loadWrongOverview(),
  ]).catch(console.error);
  openProfileEditorFromRoute();

  requestAnimationFrame(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    profileMotionContext = gsap.context(() => {
      gsap.from(".profile-motion-item", {
        opacity: 0,
        y: 10,
        duration: 0.45,
        stagger: 0.08,
        ease: "power2.out",
      });
    });
  });
});

onBeforeUnmount(() => {
  profileMotionContext?.revert();
});

const avatarInput = ref<HTMLInputElement>();
const triggerAvatarUpload = () => {
  avatarInput.value?.click();
};

const onAvatarFileChange = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
  if (!allowedTypes.includes(file.type)) {
    toast.error("仅支持 JPG、PNG、GIF、WebP 格式图片");
    return;
  }
  const maxSize = 2 * 1024 * 1024;
  if (file.size > maxSize) {
    toast.error("图片大小不能超过 2MB");
    return;
  }

  avatarUploading.value = true;
  try {
    const res = await uploadAvatar(file);
    userAvatar.value = res.data.data.avatar;
    if (currentUser.value) {
      setCurrentUser({
        ...currentUser.value,
        avatar: res.data.data.avatar,
      });
    }
    toast.success("头像更新成功");
  } catch (err) {
    console.error("Failed to upload avatar", err);
    toast.error("头像更新失败，请重试");
  } finally {
    avatarUploading.value = false;
    target.value = "";
  }
};

const newCourseInput = ref("");
const addCourse = () => {
  const course = newCourseInput.value.trim();
  if (course && !profileForm.courses.includes(course)) {
    profileForm.courses.push(course);
  }
  newCourseInput.value = "";
};
const removeCourse = (index: number) => {
  profileForm.courses.splice(index, 1);
};

const toggleLanguage = (lang: string) => {
  const index = profileForm.programming_languages.indexOf(lang);
  if (index > -1) {
    profileForm.programming_languages.splice(index, 1);
  } else {
    profileForm.programming_languages.push(lang);
  }
};

const majorFocus = ref(false);
const schoolFocus = ref(false);

const majorSuggestions = computed(() => {
  const query = profileForm.major.trim().toLowerCase();
  if (!query) return PRESET_MAJORS.map((m) => ({ value: m }));
  return PRESET_MAJORS.filter((m) => m.toLowerCase().includes(query)).map(
    (m) => ({ value: m }),
  );
});

const schoolSuggestions = ref<{ value: string; level?: string | null }[]>([]);
const querySearchSchool = async (query: string) => {
  if (!query.trim()) {
    schoolSuggestions.value = [];
    return;
  }
  try {
    const res = await searchSchools(query, 20);
    schoolSuggestions.value = (res.data.data || []).map(
      (school: SchoolItem) => ({
        value: school.name,
        level: school.level,
      }),
    );
  } catch (e) {
    schoolSuggestions.value = [];
  }
};

watch(
  () => profileForm.school,
  (newVal) => {
    querySearchSchool(newVal);
  },
);

const selectMajor = (val: string) => {
  profileForm.major = val;
  majorFocus.value = false;
};

const selectSchool = (val: string) => {
  profileForm.school = val;
  schoolFocus.value = false;
};

const profileErrors = reactive({
  major: "",
  courses: "",
  global_learning_goal: "",
  school: "",
  grade: "",
});

const validateProfile = () => {
  let valid = true;
  profileErrors.major = "";
  profileErrors.courses = "";
  profileErrors.global_learning_goal = "";
  profileErrors.school = "";
  profileErrors.grade = "";

  if (!profileForm.school.trim()) {
    profileErrors.school = "请输入或搜索你的就读学校";
    valid = false;
  }
  if (!profileForm.grade) {
    profileErrors.grade = "请选择你当前的年级阶段";
    valid = false;
  }
  if (!profileForm.major.trim()) {
    profileErrors.major = "请选择或输入你的专业";
    valid = false;
  }
  if (!profileForm.global_learning_goal) {
    profileErrors.global_learning_goal = "请选择你当前的学习目标";
    valid = false;
  }
  if (profileForm.courses.length === 0) {
    profileErrors.courses = "请至少添加一门课程";
    valid = false;
  }
  return valid;
};

const fillProfileForm = (payload: StudentProfileData) => {
  profileForm.grade = payload.grade || "";
  profileForm.major = payload.major || "";
  profileForm.courses = Array.isArray(payload.courses)
    ? [...payload.courses]
    : [];
  profileForm.global_learning_goal =
    profileMeta.globalLearningGoal || payload.learning_goal || "";
  profileForm.school = payload.school || "";
  profileForm.daily_study_time = profileMeta.dailyStudyTime;
  profileForm.programming_languages =
    profileMeta.programmingLanguages.length > 0
      ? [...profileMeta.programmingLanguages]
      : payload.preferred_language
        ? payload.preferred_language
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : [];
};

const fullProfileData = ref<any>(null);

const loadProfileInfo = async () => {
  try {
    const [userRes, profileRes] = await Promise.allSettled([
      ensureCurrentUser(true),
      getProfile(),
    ]);

    if (userRes.status === "fulfilled" && userRes.value) {
      setCurrentUser(userRes.value);
      userAvatar.value = userRes.value.avatar;
      userEmail.value = userRes.value.email;
    } else if (currentUser.value) {
      userAvatar.value = currentUser.value.avatar;
      userEmail.value = currentUser.value.email;
    }

    if (profileRes.status === "fulfilled") {
      const profileData = profileRes.value.data?.data;
      fullProfileData.value = profileData;
      const baseInfo = profileData?.base_info;
      // 统一从 base_info 中获取所有基本信息，确保数据正确展示
      if (baseInfo) {
        studentProfile.value = {
          school: baseInfo.school || null,
          school_level: baseInfo.school_level || null,
          major: baseInfo.major || null,
          grade: baseInfo.grade || null,
          courses: baseInfo.courses || [],
          learning_goal: baseInfo.global_learning_goal || null,
          preferred_language: (baseInfo.programming_languages || []).join(", "),
        };
        profileMeta.dailyStudyTime = baseInfo.daily_study_time || "";
        profileMeta.globalLearningGoal = baseInfo.global_learning_goal || "";
        profileMeta.programmingLanguages = Array.isArray(
          baseInfo.programming_languages,
        )
          ? [...baseInfo.programming_languages]
          : [];
      }
    }
  } catch (e) {
    console.warn("加载个人中心数据失败", e);
  } finally {
    fillProfileForm(studentProfile.value);
  }
};

const loadLearningStats = async () => {
  try {
    const days = parseInt(timeRange.value) || 7;
    const res = await getLearningTimeStats(days);
    learningStats.value = res.data.data;
    studentProfile.value.learning_duration_total = res.data.data.total_seconds;
  } catch (e) {
    console.warn("加载学习时长统计失败", e);
    learningStats.value = null;
    studentProfile.value.learning_duration_total = 0;
  }
};

const loadResourceHistory = async () => {
  resourceHistoryLoading.value = true;
  try {
    const res = await getGeneratedResources(1, 40);
    resourceHistory.value = res.data.data?.items || [];
  } catch (e) {
    console.warn("加载资源生成历史失败", e);
    resourceHistory.value = [];
  } finally {
    resourceHistoryLoading.value = false;
  }
};

const loadDashboardStats = async () => {
  dashboardStatsLoading.value = true;
  try {
    const [statsRes, resourcesRes] = await Promise.allSettled([
      getStudyStats(),
      getRecentResources(),
    ]);
    studyStats.value =
      statsRes.status === "fulfilled" ? statsRes.value.data.data : null;
    recentDashboardResources.value =
      resourcesRes.status === "fulfilled"
        ? resourcesRes.value.data.data || []
        : [];
  } catch (e) {
    console.warn("加载学习数据概览失败", e);
    studyStats.value = null;
    recentDashboardResources.value = [];
  } finally {
    dashboardStatsLoading.value = false;
  }
};

const loadEvaluationSummary = async () => {
  evaluationLoading.value = true;
  try {
    const res = await getEvaluationSummary(100);
    evaluationSummary.value = res.data.data;
  } catch (e) {
    console.warn("加载学习评估摘要失败", e);
    evaluationSummary.value = null;
  } finally {
    evaluationLoading.value = false;
  }
};

const loadWrongOverview = async () => {
  wrongLoading.value = true;
  try {
    const res = await fetchWrongQuestions({
      is_archived: false,
      page: 1,
      page_size: 1,
    });
    wrongTotal.value = res.total || 0;
  } catch (e) {
    console.warn("加载错题概览失败", e);
    wrongTotal.value = 0;
  } finally {
    wrongLoading.value = false;
  }
};

const openProfileEditor = () => {
  fillProfileForm(studentProfile.value);
  profileErrors.major = "";
  profileErrors.courses = "";
  profileErrors.global_learning_goal = "";
  profileErrors.school = "";
  profileErrors.grade = "";
  profileEditorVisible.value = true;
};

const openProfileEditorFromRoute = () => {
  if (route.query.action === "edit-profile") {
    openProfileEditor();
  }
};

const setTimeRange = (val: any) => {
  if (typeof val === "string" && val) timeRange.value = val;
};

const submitProfile = async () => {
  if (!validateProfile()) {
    toast.warning("请先完善所有必填项");
    return;
  }

  profileSubmitting.value = true;
  try {
    const payload: ProfileOnboardingUpdate = {
      school: profileForm.school,
      major: profileForm.major,
      grade: profileForm.grade,
      global_learning_goal: profileForm.global_learning_goal,
      daily_study_time: profileForm.daily_study_time,
      courses: profileForm.courses.filter(Boolean).map((c) => c.trim()),
      programming_languages: profileForm.programming_languages,
    };
    await updateProfileOnboarding(payload);
    studentProfile.value = {
      ...studentProfile.value,
      school: payload.school,
      major: payload.major,
      grade: payload.grade,
      courses: payload.courses,
      learning_goal: payload.global_learning_goal,
      preferred_language: payload.programming_languages.join(", "),
    };
    profileMeta.dailyStudyTime = payload.daily_study_time;
    profileMeta.globalLearningGoal = payload.global_learning_goal;
    profileMeta.programmingLanguages = [...payload.programming_languages];
    profileEditorVisible.value = false;
    toast.success("学习资料更新成功");
    await loadProfileInfo();
  } catch (e: any) {
    console.error("Failed to update profile onboarding", e);
    toast.error(e.response?.data?.message || "保存失败，请稍后重试");
  } finally {
    profileSubmitting.value = false;
  }
};
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

/* Layout Grid */
.profile-layout-grid {
  display: grid;
  grid-template-columns: 350px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

/* Left Sidebar Styles */
.academic-profile-sidebar {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.02);
  text-align: left;
}

.sidebar-user-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
}

.avatar-button {
  position: relative;
  width: 90px;
  height: 90px;
  padding: 0;
  border-radius: 999px;
  background: transparent;
  margin-bottom: 16px;
}

.avatar-button:hover {
  background: transparent;
}

.profile-avatar {
  width: 90px;
  height: 90px;
  border: 2px solid rgba(157, 210, 208, 0.7);
  box-shadow:
    inset 0 0 0 4px #fff,
    0 8px 20px rgba(15, 23, 42, 0.05);
}

.profile-avatar :deep(span) {
  font-size: 32px;
  font-weight: 800;
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
}

.avatar-edit-mask {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: #fff;
  background: rgba(15, 23, 42, 0.6);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.avatar-button:hover .avatar-edit-mask {
  opacity: 1;
}

.user-name {
  color: #0f172a;
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 6px;
}

.academic-role-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 12px;
}

.user-email {
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.user-headline {
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  max-width: 280px;
}

.sidebar-details-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-label {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-value {
  color: #1e293b;
  font-size: 14px;
  font-weight: 700;
}

.detail-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-badge-pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 6px;
  background: rgba(245, 243, 255, 0.8);
  color: #4f46e5;
  font-size: 11px;
  font-weight: 700;
}

.detail-badge-pill.lang-pill {
  border-color: rgba(13, 148, 136, 0.15);
  background: rgba(240, 253, 250, 0.8);
  color: #0d9488;
}

.empty-badge-pill {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 600;
}

.sidebar-actions {
  margin-top: 8px;
}

.edit-profile-button {
  height: 40px;
  gap: 8px;
  border-color: rgba(203, 213, 225, 0.8);
  border-radius: 8px;
  background: #ffffff;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

.edit-profile-button:hover {
  background: #f8fafc;
  color: #0f172a;
  border-color: rgba(148, 163, 184, 0.8);
}

/* Right Main Dashboard Panel */
.analytics-dashboard-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #4f46e5;
}

.panel-heading h3 {
  color: #0f172a;
  font-size: 20px;
  font-weight: 800;
}

.dashboard-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.course-trigger {
  width: 140px;
  height: 32px;
  border-color: rgba(226, 232, 240, 0.8);
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  font-size: 12px;
}

.range-toggle {
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 8px;
  background: #ffffff;
}

.range-toggle :deep(button) {
  height: 30px;
  min-width: 48px;
  border: 0;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.range-toggle :deep(button[data-state="on"]) {
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
}

/* Core Summary Grid */
.summary-card-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 84px;
  padding: 16px 20px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.01);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
  text-align: left;
}

.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.03);
}

.summary-card.card-active {
  border-color: rgba(217, 119, 6, 0.2);
  background: rgba(255, 251, 235, 0.45);
}
.summary-card.card-active .summary-icon {
  color: #d97706;
}
.summary-card.card-active span {
  color: #b45309;
}
.summary-card.card-active strong {
  color: #78350f;
}

.summary-card.card-output {
  border-color: rgba(16, 185, 129, 0.2);
  background: rgba(240, 253, 250, 0.45);
}
.summary-card.card-output .summary-icon {
  color: #10b981;
}
.summary-card.card-output span {
  color: #047857;
}
.summary-card.card-output strong {
  color: #064e3b;
}

.summary-card.card-score {
  border-color: rgba(99, 102, 241, 0.2);
  background: rgba(245, 243, 255, 0.45);
}
.summary-card.card-score .summary-icon {
  color: #6366f1;
}
.summary-card.card-score span {
  color: #4338ca;
}
.summary-card.card-score strong {
  color: #312e81;
}

.summary-card.card-wrong {
  border-color: rgba(244, 63, 94, 0.2);
  background: rgba(255, 241, 242, 0.45);
}
.summary-card.card-wrong .summary-icon {
  color: #f43f5e;
}
.summary-card.card-wrong span {
  color: #b91c1c;
}
.summary-card.card-wrong strong {
  color: #7f1d1d;
}

.summary-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
}

.summary-card span,
.summary-card small {
  display: block;
  font-size: 13px;
  font-weight: 700;
}

.summary-card strong {
  display: block;
  margin-top: 1px;
  font-size: 26px;
  font-weight: 800;
  line-height: 1.1;
}

.summary-card small {
  margin-top: 3px;
  color: #64748b;
  font-size: 11px;
}

/* Double Column Grid Layout */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 20px;
}

.visual-column {
  grid-column: span 7;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.insights-column {
  grid-column: span 5;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-panel,
.insight-panel {
  min-width: 0;
  padding: 20px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.01);
  text-align: left;
  display: flex;
  flex-direction: column;
}

.visual-sub-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  flex: 1;
}

.status-panel {
  flex: 1;
}

.chart-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.chart-heading h4 {
  color: #0f172a;
  font-size: 16px;
  font-weight: 800;
}

.chart-heading span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.chart-box {
  position: relative;
  height: 220px;
}

.chart {
  width: 100%;
  height: 100%;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 600;
  pointer-events: none;
}

/* Scenario breakdown & Resource Progress */
.scenario-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  justify-content: space-between;
}

.donut-box {
  position: relative;
  min-height: 110px;
  flex: 1;
}

.scenario-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}

.scenario-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.scenario-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scenario-name i {
  width: 10px;
  height: 10px;
  flex: 0 0 10px;
  border-radius: 2px;
}

.scenario-row strong {
  color: #0f172a;
  font-family: monospace;
}

.resource-mix-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  justify-content: space-between;
}

.resource-mix-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.resource-mix-row > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.resource-mix-row strong {
  color: #0f172a;
  font-weight: 800;
}

.mix-track {
  height: 6px;
  border-radius: 999px;
  background: #f1f5f9;
  overflow: hidden;
}

.mix-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #159f9b, #62c9c5);
}

/* Advice Panel & Next Action */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preference-cloud {
  margin-top: 10px;
}

.weak-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid rgba(99, 102, 241, 0.15);
  background: rgba(245, 243, 255, 0.7);
  color: #4f46e5;
  transition: transform 0.2s ease;
}

.weak-tag:hover {
  transform: scale(1.03);
}

.weak-tag:nth-child(2n) {
  border-color: rgba(13, 148, 136, 0.15);
  background: rgba(240, 253, 250, 0.7);
  color: #0d9488;
}

.weak-tag:nth-child(3n) {
  border-color: rgba(217, 119, 6, 0.15);
  background: rgba(255, 251, 235, 0.7);
  color: #d97706;
}

.weak-tag:nth-child(4n) {
  border-color: rgba(244, 63, 94, 0.15);
  background: rgba(255, 241, 242, 0.7);
  color: #f43f5e;
}

.data-chip,
.empty-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 24px;
  padding: 0 10px;
  border: 1px solid rgba(13, 148, 136, 0.15);
  border-radius: 6px;
  background: rgba(240, 253, 250, 0.5);
  color: #0d9488;
  font-size: 11px;
  font-weight: 700;
}

.empty-chip {
  color: #94a3b8;
  border-color: rgba(226, 232, 240, 0.8);
  background: #f8fafc;
}

.next-action-box {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 8px;
  background: linear-gradient(
    135deg,
    rgba(245, 243, 255, 0.5),
    rgba(240, 253, 250, 0.5)
  );
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.next-action-box span {
  display: block;
  color: #4f46e5;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.next-action-box p {
  margin: 4px 0 0;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.6;
}

/* Status Cards & Progress */
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  flex: 1;
}

.status-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 8px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.status-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-card-head span {
  color: #475569;
  font-size: 11px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-card strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
}

.status-progress-bar {
  height: 4px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
  margin: 8px 0 4px;
}

.status-progress-fill {
  height: 100%;
  border-radius: inherit;
  transition: width 0.4s ease;
}

.status-card.theme-teal {
  border-color: rgba(13, 148, 136, 0.15);
  background: rgba(240, 253, 250, 0.45);
}
.status-card.theme-teal .status-icon {
  color: #0d9488;
}
.status-card.theme-teal .status-progress-fill {
  background: #0d9488;
}

.status-card.theme-purple {
  border-color: rgba(139, 92, 246, 0.15);
  background: rgba(245, 243, 255, 0.45);
}
.status-card.theme-purple .status-icon {
  color: #8b5cf6;
}
.status-card.theme-purple .status-progress-fill {
  background: #8b5cf6;
}

.status-card.theme-indigo {
  border-color: rgba(79, 70, 229, 0.15);
  background: rgba(238, 242, 255, 0.45);
}
.status-card.theme-indigo .status-icon {
  color: #4f46e5;
}
.status-card.theme-indigo .status-progress-fill {
  background: #4f46e5;
}

.status-card.theme-amber {
  border-color: rgba(217, 119, 6, 0.15);
  background: rgba(255, 251, 235, 0.45);
}
.status-card.theme-amber .status-icon {
  color: #d97706;
}
.status-card.theme-amber .status-progress-fill {
  background: #d97706;
}

.status-card small {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
}

/* Responsive Overrides */
@media (max-width: 1024px) {
  .profile-layout-grid {
    grid-template-columns: 1fr;
  }
  .visual-column,
  .insights-column {
    grid-column: span 12;
  }
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
  border-bottom: 1px solid rgba(200, 228, 227, 0.82);
  background:
    radial-gradient(
      circle at 92% 0%,
      rgba(70, 184, 180, 0.16),
      transparent 30%
    ),
    linear-gradient(
      135deg,
      rgba(252, 255, 255, 0.98),
      rgba(239, 250, 250, 0.74)
    );
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
  border: 1px solid rgba(70, 184, 180, 0.42);
  border-radius: 999px;
  background: rgba(216, 241, 240, 0.62);
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
  border-right: 1px solid rgba(200, 228, 227, 0.82);
  background: linear-gradient(
    180deg,
    rgba(247, 253, 253, 0.95),
    rgba(255, 255, 255, 0.92)
  );
}

.editor-step-card {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(200, 228, 227, 0.76);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-primary-text);
  text-align: left;
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast),
    transform var(--transition-fast);
}

.editor-step-card:hover {
  border-color: rgba(70, 184, 180, 0.62);
  background: #fff;
}

.editor-step-card:active {
  transform: translateY(1px);
}

.editor-step-card.active,
.editor-step-card.done {
  border-color: rgba(21, 159, 155, 0.55);
  background: linear-gradient(
    135deg,
    rgba(216, 241, 240, 0.76),
    rgba(255, 255, 255, 0.92)
  );
}

.editor-step-index {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(234, 245, 244, 0.92);
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
  border: 1px solid rgba(200, 228, 227, 0.82);
  border-radius: 10px;
  background: rgba(252, 255, 255, 0.8);
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
  border: 1px solid rgba(200, 228, 227, 0.82);
  border-radius: 10px;
  background: rgba(252, 255, 255, 0.82);
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
  border-color: rgba(70, 184, 180, 0.42);
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
  border: 1px solid rgba(200, 228, 227, 0.96) !important;
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
  border: 1px solid rgba(200, 228, 227, 0.9);
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 18px 40px rgba(32, 95, 103, 0.14);
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
  background: rgba(216, 241, 240, 0.48);
}

.editor-suggestion-list small {
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(234, 245, 244, 0.82);
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
  border: 1px solid rgba(200, 228, 227, 0.96);
  border-radius: 9px;
  background: #fff;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.editor-chip-input:focus-within {
  border-color: rgba(21, 159, 155, 0.72);
  box-shadow: 0 0 0 3px rgba(21, 159, 155, 0.1);
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
  border: 1px solid rgba(70, 184, 180, 0.38);
  border-radius: 8px;
  background: rgba(216, 241, 240, 0.5);
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
  background: rgba(21, 159, 155, 0.12);
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
  border-color: rgba(200, 228, 227, 0.96);
  border-radius: 8px;
  background: #fff;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 700;
}

.language-chips-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px;
  border: 1px solid rgba(200, 228, 227, 0.8);
  border-radius: 9px;
  background: #f8fafc;
}

.lang-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 32px;
  user-select: none;
}

.lang-chip:hover {
  border-color: #0d9488;
  color: #0d9488;
  background: rgba(13, 148, 136, 0.02);
}

.lang-chip.active {
  border-color: #0d9488;
  background: #0f766e;
  color: #ffffff;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(15, 118, 110, 0.15);
}

.dialog-header-banner {
  background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
  padding: 24px 28px;
  text-align: left;
  position: relative;
}

.header-banner-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: #ffffff;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.dialog-header-banner h3 {
  margin: 6px 0 2px;
  font-size: 18px;
  font-weight: 800;
  color: #ffffff;
  line-height: 1.2;
}

.dialog-header-banner p {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.4;
}

.dialog-scroll-container {
  max-height: calc(85vh - 120px);
  overflow-y: auto;
  padding: 24px 28px;
}

.dialog-form-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-section {
  display: flex;
  flex-direction: column;
  text-align: left;
}

.section-title-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 6px;
}

.section-num {
  font-size: 11px;
  font-weight: 800;
  color: #0d9488;
  background: rgba(13, 148, 136, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

.section-title {
  font-size: 12px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: 0.05em;
}

.form-field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.form-field-label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 2px;
}

.editor-chip-input-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preset-label {
  font-size: 11px;
  font-weight: 800;
  color: #94a3b8;
}

.profile-editor-dialog button.absolute {
  color: rgba(255, 255, 255, 0.8) !important;
  transition: all 0.2s ease;
  top: 20px !important;
  right: 20px !important;
}

.profile-editor-dialog button.absolute:hover {
  color: #ffffff !important;
  background: rgba(255, 255, 255, 0.15) !important;
}

.profile-editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 26px;
  border-top: 1px solid rgba(200, 228, 227, 0.72);
  background: rgba(252, 255, 255, 0.92);
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
  border-color: rgba(200, 228, 227, 0.96);
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
    border-bottom: 1px solid rgba(200, 228, 227, 0.72);
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
    border-bottom: 1px solid rgba(200, 228, 227, 0.82);
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
  transition:
    opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
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
