<template>
  <div class="question-bank-layout">
    <div v-if="viewMode === 'workspace'" class="question-bank-workspace">
      <transition name="fade-scale" mode="out-in">
        <!-- 1. Portal Home Page -->
        <div v-if="activeModule === 'portal'" key="portal" class="portal-workspace-view">
          <section class="question-bank-hero glass-panel">
            <div class="hero-left">
              <span class="hero-kicker">Question Bank Portal</span>
              <h1>刷题控制台</h1>
              <p class="quote">“{{ randomQuote }}”</p>
              
              <div class="hero-stats-row">
                <!-- SVG Progress Circle -->
                <div class="accuracy-circle-container">
                  <svg class="progress-ring" width="76" height="76" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="42" class="circle-bg" />
                    <circle cx="50" cy="50" r="42" class="circle-progress" :style="circleProgressStyle" />
                  </svg>
                  <div class="circle-content">
                    <span class="pct">{{ practiceAccuracy }}</span>
                    <span class="lbl">正确率</span>
                  </div>
                </div>
                
                <div class="stats-text-block">
                  <div class="stat-item">
                    <span class="lbl">已练题数</span>
                    <strong class="val">{{ stats.totalAttempted }}</strong>
                  </div>
                  <div class="stat-item">
                    <span class="lbl">待复习错题</span>
                    <strong class="val danger-color">{{ wrongTotal }}</strong>
                  </div>
                  <div class="stat-item">
                    <span class="lbl">持续打卡</span>
                    <strong class="val warning-color">{{ localStreak }} 天</strong>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="hero-right">
              <div class="radar-chart-wrapper">
                <svg width="170" height="170" viewBox="0 0 200 200">
                  <defs>
                    <radialGradient id="radarGrad" cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stop-color="rgba(139, 92, 246, 0.1)" />
                      <stop offset="100%" stop-color="rgba(139, 92, 246, 0.45)" />
                    </radialGradient>
                  </defs>
                  <!-- Grid Background Polygons -->
                  <polygon v-for="(points, idx) in gridPolygons" :key="idx" :points="points" class="radar-grid-poly" />
                  
                  <!-- Axis Lines -->
                  <line v-for="(line, idx) in axisLines" :key="idx" :x1="center" :y1="center" :x2="line.x2" :y2="line.y2" class="radar-axis-line" />
                  
                  <!-- Data Area Polygon -->
                  <polygon :points="polygonPointsString" class="radar-data-poly" fill="url(#radarGrad)" />
                  
                  <!-- Data Points Dots -->
                  <circle v-for="(p, idx) in radarPoints" :key="idx" :cx="p.x" :cy="p.y" r="4.5" class="radar-data-dot" />
                  
                  <!-- Labels -->
                  <text v-for="(lbl, idx) in labelPositions" :key="idx" :x="lbl.x" :y="lbl.y" :text-anchor="lbl.anchor" class="radar-label">{{ lbl.text }}</text>
                </svg>
              </div>
            </div>
          </section>

          <section class="portal-grid">
            <!-- Card 1: 每日练习 -->
            <div class="portal-card glow-border" @click="switchModule('daily')">
              <div class="card-glow-bg"></div>
              <div class="card-header-icon">
                <div class="icon-box violet">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                </div>
                <span :class="['card-badge', isDailyCompleted ? 'success' : 'pulsing-warning']">
                  {{ isDailyCompleted ? '已达标' : '今日待做' }}
                </span>
              </div>
              <h3>每日练习</h3>
              <p>先完成今天这一题，保持稳定的每日训练频率。</p>
            </div>
            
            <!-- Card 2: 智能练习 -->
            <div class="portal-card glow-border" @click="switchModule('practice')">
              <div class="card-glow-bg"></div>
              <div class="card-header-icon">
                <div class="icon-box blue">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v2"/><path d="M12 20v2"/><path d="M4.93 4.93l1.41 1.41"/><path d="M17.66 17.66l1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="M6.34 17.66l-1.41 1.41"/><path d="M19.07 4.93l-1.41 1.41"/><path d="M10 8.5a2.5 2.5 0 1 1 5 0c0 1.5-2.5 2.5-2.5 2.5h-.5"/><path d="M12 16h.01"/></svg>
                </div>
                <span class="card-badge info">智能推荐</span>
              </div>
              <h3>智能练习</h3>
              <p>个性化推荐练习，自动设定题型和学科，巩固巩固薄弱点。</p>
            </div>
            
            <!-- Card 3: 全部题目 -->
            <div class="portal-card glow-border" @click="switchModule('search')">
              <div class="card-glow-bg"></div>
              <div class="card-header-icon">
                <div class="icon-box green">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                </div>
                <span class="card-badge secondary">{{ totalQuestions }} 题可用</span>
              </div>
              <h3>全部题目</h3>
              <p>按学科、难度和题型快速检索并作答，支持即时AI评阅。</p>
            </div>
            
            <!-- Card 4: 模拟组卷 -->
            <div class="portal-card glow-border" @click="switchModule('paper')">
              <div class="card-glow-bg"></div>
              <div class="card-header-icon">
                <div class="icon-box orange">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                </div>
                <span class="card-badge secondary">全真模拟</span>
              </div>
              <h3>模拟组卷</h3>
              <p>配置题量、学科、题型与考试时长，在模拟环境下进行测试。</p>
            </div>
            
            <!-- Card 5: 错题本 -->
            <div class="portal-card glow-border" @click="switchModule('wrong')">
              <div class="card-glow-bg"></div>
              <div class="card-header-icon">
                <div class="icon-box red">
                  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
                <span v-if="wrongTotal > 0" class="card-badge danger pulsing">{{ wrongTotal }} 道待巩固</span>
                <span v-else class="card-badge success">无待复习错题</span>
              </div>
              <h3>错题本</h3>
              <p>重点攻克练习中做错的难题，提供快速再练与归档管理。</p>
            </div>
          </section>
        </div>

        <!-- 2. Focused Workspace Page -->
        <div v-else :key="activeModule" class="focused-workspace-view" :class="'theme-' + activeModule">
          <header class="workspace-nav-header glass-panel">
            <button class="btn-back" @click="backToPortal">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
              返回控制台
            </button>
            <div class="breadcrumb">
              <span class="crumb-parent">刷题中心</span>
              <span class="crumb-divider">/</span>
              <span class="crumb-active">{{ moduleTitles[activeModule] }}</span>
            </div>
          </header>

          <section class="workspace-panel-shell">
            <div class="workspace-panel-header">
              <div class="header-left-side">
                <div class="theme-accent-strip"></div>
                <div class="header-info">
                  <span class="workspace-panel-label">Current Module</span>
                  <h2>{{ moduleTitles[activeModule] }}</h2>
                  <p class="workspace-panel-desc">{{ moduleDescriptions[activeModule] }}</p>
                </div>
              </div>

              <div class="header-right-stats">
                <!-- Daily Practice Stats -->
                <template v-if="activeModule === 'daily'">
                  <div class="stat-badge">
                    <span class="badge-label">今日完成</span>
                    <span :class="['badge-value', isDailyCompleted ? 'text-success' : 'text-warning']">
                      {{ isDailyCompleted ? '已达标' : '未达标' }}
                    </span>
                  </div>
                  <div class="stat-badge">
                    <span class="badge-label">连续打卡</span>
                    <span class="badge-value theme-text">{{ localStreak }} 天</span>
                  </div>
                </template>

                <!-- Smart Practice Stats -->
                <template v-else-if="activeModule === 'practice'">
                  <div class="stat-badge">
                    <span class="badge-label">智能已练</span>
                    <span class="badge-value theme-text">{{ stats.totalAttempted }} 题</span>
                  </div>
                  <div class="stat-badge">
                    <span class="badge-label">正确率</span>
                    <span class="badge-value theme-text">{{ practiceAccuracy }}</span>
                  </div>
                </template>

                <!-- All Search Stats -->
                <template v-else-if="activeModule === 'search'">
                  <div class="stat-badge">
                    <span class="badge-label">题库总量</span>
                    <span class="badge-value theme-text">{{ totalQuestions }} 题</span>
                  </div>
                </template>

                <!-- Mock Paper Stats -->
                <template v-else-if="activeModule === 'paper'">
                  <div class="stat-badge">
                    <span class="badge-label">已完模考</span>
                    <span class="badge-value theme-text">{{ mockExamsCount }} 次</span>
                  </div>
                </template>

                <!-- Wrong Book Stats -->
                <template v-else-if="activeModule === 'wrong'">
                  <div class="stat-badge">
                    <span class="badge-label">待巩固错题</span>
                    <span class="badge-value text-danger">{{ wrongTotal }} 题</span>
                  </div>
                  <div class="stat-badge">
                    <span class="badge-label">已归档错题</span>
                    <span class="badge-value text-success">{{ archivedWrongTotal }} 题</span>
                  </div>
                </template>
              </div>
            </div>

            <main class="workspace-panel-content">
              <DailyPracticeTab
                v-if="activeModule === 'daily'"
                :dailyQuestion="dailyQuestion"
                @start-daily="startSingleDailyQuestion"
                @refresh-daily="pickDailyQuestion"
              />

              <PracticeTab
                v-else-if="activeModule === 'practice'"
                :stats="stats"
                :wrongTotal="wrongTotal"
                :recommendedSubject="recommendedSubject"
                :recommendedCount="recommendedCount"
                :practiceLoading="practiceLoading"
                :subjects="subjects"
                :difficulties="difficulties"
                :types="types"
                @switch-tab="switchModule"
                @start-recommended="startRecommendedPractice"
                @start-custom="startSpecialPracticeProxy"
              />

              <SearchTab
                v-else-if="activeModule === 'search'"
                :questions="questions"
                :total="totalQuestions"
                :loading="bankLoading"
                :currentPage="bankPage"
                :pageSize="bankPageSize"
                :filters="bankFilters"
                :subjects="subjects"
                :difficulties="difficulties"
                :types="types"
                :answers="bankAnswers"
                :submitted="bankSubmitted"
                :correct="bankCorrect"
                :reviewing="bankReviewing"
                :review="bankReview"
                :openedAnalysis="openedAnalysis"
                @search="searchBank"
                @page-change="handleBankPageChange"
                @select-option="selectBankOption"
                @submit="submitBankAnswer"
                @toggle-analysis="toggleBankAnalysis"
              />

              <ExamTab
                v-else-if="activeModule === 'paper'"
                :form="paperForm"
                :typeCounts="paperTypeCounts"
                :preview="paperPreview"
                :loading="paperLoading"
                :subjects="subjects"
                :difficulties="difficulties"
                @reset-form="resetPaperForm"
                @generate-preview="generatePaperPreview"
                @start-exam="startPreviewExam"
              />

              <WrongBookTab
                v-else-if="activeModule === 'wrong'"
                :questions="filteredWrongQuestions"
                :total="wrongTotal"
                :loading="wrongLoading"
                :page="wrongPage"
                :pageSize="wrongPageSize"
                :filters="wrongFilters"
                :subjects="subjects"
                :types="types"
                :answers="wrongAnswers"
                :submitted="wrongSubmitted"
                :correct="wrongCorrect"
                :reviewing="wrongReviewing"
                :review="wrongReview"
                :openedAnalysis="openedWrongAnalysis"
                :drillQuestion="wrongDrillQuestion"
                :drillAnswer="wrongDrillAnswer"
                :drillSubmitted="wrongDrillSubmitted"
                :drillCorrect="wrongDrillCorrect"
                :drillReviewing="wrongDrillReviewing"
                :drillReview="wrongDrillReview"
                @search-wrong="searchWrong"
                @page-change="handleWrongPageChange"
                @pick-drill="pickWrongQuestion"
                @select-drill-option="selectWrongDrillOption"
                @update:drillAnswer="wrongDrillAnswer = $event"
                @submit-drill="submitWrongDrill"
                @select-wrong-option="selectWrongOption"
                @submit-wrong="submitWrongAnswer"
                @toggle-wrong-analysis="toggleWrongAnalysis"
                @archive-wrong="archiveWrong"
                @remove-wrong="removeWrong"
              />
            </main>
          </section>
        </div>
      </transition>
    </div>

    <div v-else class="exam-workspace">
      <header class="exam-topbar">
        <div class="exam-topbar-left">
          <button class="btn-text" @click="quitExam">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            退出考试
          </button>
          <h1 class="exam-title">{{ examTitle }}</h1>
        </div>
        <div class="exam-actions">
          <div class="timer-badge">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>{{ formattedExamTime }}</span>
          </div>
          <button v-if="!examSubmitted" class="btn-primary" @click="submitExam">交卷</button>
          <button v-else class="btn-secondary" @click="backWorkspace">返回首页</button>
        </div>
      </header>

      <main class="exam-main">
        <div class="exam-content">
          <article
            v-for="(question, index) in examPaper"
            :key="question.id"
            :id="'exam-q-' + index"
            :class="['exam-question', { active: currentExamIndex === index }]"
          >
            <div class="question-header">
              <span class="q-number">第 {{ index + 1 }} 题 / 共 {{ examPaper.length }} 题</span>
              <div class="tags">
                <span class="tag outline">{{ question.subject }}</span>
                <span class="tag type">{{ question.type }}</span>
              </div>
              <div v-if="examSubmitted" :class="['result-badge', isExamCorrect(question) ? 'success' : 'danger']">
                {{ isExamCorrect(question) ? '正确' : '错误' }}
              </div>
            </div>

            <div class="question-text" v-html="renderInline(question.content)"></div>

            <div v-if="isOptionQuestion(question)" class="options-list">
              <button
                v-for="(text, key) in getOptions(question)"
                :key="key"
                type="button"
                :class="[
                  'option-btn',
                  {
                    selected: isSelected(examAnswers[question.id], key),
                    correct: examSubmitted && isCorrectOption(question, key),
                    wrong: examSubmitted && isSelected(examAnswers[question.id], key) && !isCorrectOption(question, key),
                  },
                ]"
                :disabled="examSubmitted"
                @click="selectExamOption(question, key)"
              >
                <span class="opt-key">{{ key }}</span>
                <span class="opt-text" v-html="renderInline(text)"></span>
              </button>
            </div>
            <textarea
              v-else
              v-model="examAnswers[question.id]"
              class="text-area-input"
              rows="4"
              :disabled="examSubmitted"
              placeholder="请输入你的答案..."
            ></textarea>

            <div v-if="examSubmitted" :class="['analysis-panel', isExamCorrect(question) ? 'success' : 'danger']">
              <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
              <div class="analysis-text" v-html="renderInline(question.analysis || '暂无解析。')"></div>
            </div>
          </article>
        </div>

        <aside class="exam-sidebar">
          <div class="panel">
            <h3>{{ examSubmitted ? '考试报告' : '答题卡' }}</h3>

            <div v-if="examSubmitted" class="score-display">
              <div class="score-value">{{ examScore }}%</div>
              <div class="score-label">最终得分</div>
            </div>
            <div v-else class="progress-display">
              <div class="progress-value">{{ examAnsweredCount }} / {{ examPaper.length }}</div>
              <div class="progress-label">已作答</div>
            </div>

            <div class="grid-sheet">
              <button
                v-for="(question, index) in examPaper"
                :key="question.id"
                :class="[
                  'sheet-btn',
                  {
                    active: currentExamIndex === index,
                    answered: !examSubmitted && hasAnswerData(examAnswers[question.id]),
                    correct: examSubmitted && isExamCorrect(question),
                    wrong: examSubmitted && !isExamCorrect(question),
                  },
                ]"
                @click="scrollToQuestion(index)"
              >
                {{ index + 1 }}
              </button>
            </div>

            <button v-if="!examSubmitted" class="btn-primary full-width sidebar-submit" @click="submitExam">交卷</button>
            <button v-else class="btn-secondary full-width sidebar-submit" @click="backWorkspace">完成查看</button>
          </div>
        </aside>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getProfileOnboarding } from '@/features/profile/api/profile'
import { fetchQuizBankQuestions, fetchQuizReview, submitObjectiveResults, type QuizReviewResult } from '@/features/question-bank/api/quizBank'
import {
  archiveWrongQuestion,
  fetchRandomWrongQuestion,
  fetchWrongQuestions,
  removeWrongQuestion,
} from '@/features/question-bank/api/wrongQuestions'

import DailyPracticeTab from '@/features/question-bank/components/DailyPracticeTab.vue'
import PracticeTab from '@/features/question-bank/components/PracticeTab.vue'
import SearchTab from '@/features/question-bank/components/SearchTab.vue'
import ExamTab from '@/features/question-bank/components/ExamTab.vue'
import WrongBookTab from '@/features/question-bank/components/WrongBookTab.vue'


type ViewMode = 'workspace' | 'exam'
type ModuleKey = 'portal' | 'daily' | 'practice' | 'search' | 'paper' | 'wrong'
type AnswerValue = string | string[] | undefined

interface Question {
  id: string
  subject: string
  subject_en?: string | null
  type: string
  difficulty?: string | null
  content: string
  options?: Record<string, string> | null
  answer: string
  analysis: string
  knowledge_points: string[]
  tags?: string[]
  language?: string | null
  split?: string | null
  wrong_id?: number
  wrong_count?: number
  is_archived?: boolean
}

interface WrongQuestionDTO {
  id: number
  question_id: string
  subject: string
  question_type: string
  content: string
  options?: Record<string, string> | null
  standard_answer?: string | null
  analysis?: string | null
  wrong_count?: number
  is_archived?: boolean
}

const viewMode = ref<ViewMode>('workspace')
const activeModule = ref<ModuleKey>('portal')
const route = useRoute()

const subjects = ref<string[]>([])
const difficulties = ref<string[]>([])
const types = ref<string[]>([])
const learnerCourses = ref<string[]>([])
const practicePool = shallowRef<Question[]>([])

const practiceLoading = ref(false)
const practiceForm = reactive({ subject: '', difficulty: '', type: '', count: 10 })
const dailyQuestion = ref<Question | null>(null)

const questions = shallowRef<Question[]>([])
const totalQuestions = ref(0)
const bankLoading = ref(false)
const bankPage = ref(1)
const bankPageSize = ref(8)
const bankFilters = reactive({ query: '', subject: '', difficulty: '', type: '' })

const wrongQuestions = shallowRef<Question[]>([])
const wrongTotal = ref(0)
const wrongLoading = ref(false)
const wrongPage = ref(1)
const wrongPageSize = ref(8)
const wrongFilters = reactive({ query: '', subject: '', type: '' })

const bankAnswers = ref<Record<string, AnswerValue>>({})
const bankSubmitted = ref<Record<string, boolean>>({})
const bankCorrect = ref<Record<string, boolean>>({})
const bankReviewing = ref<Record<string, boolean>>({})
const bankReview = ref<Record<string, QuizReviewResult | null>>({})
const openedAnalysis = ref<Set<string>>(new Set())

const wrongAnswers = ref<Record<string, AnswerValue>>({})
const wrongSubmitted = ref<Record<string, boolean>>({})
const wrongCorrect = ref<Record<string, boolean>>({})
const wrongReviewing = ref<Record<string, boolean>>({})
const wrongReview = ref<Record<string, QuizReviewResult | null>>({})
const openedWrongAnalysis = ref<Set<string>>(new Set())

const wrongDrillQuestion = ref<Question | null>(null)
const wrongDrillAnswer = ref<AnswerValue>('')
const wrongDrillSubmitted = ref(false)
const wrongDrillCorrect = ref(false)
const wrongDrillReviewing = ref(false)
const wrongDrillReview = ref<QuizReviewResult | null>(null)

const stats = reactive({ totalAttempted: 0, totalCorrect: 0 })

const mockExamsCount = ref(Number(localStorage.getItem('question_hub_mock_exams_count') || '0'))
const archivedWrongTotal = ref(0)

const paperForm = reactive({
  title: '模拟试卷',
  subject: '',
  difficulty: '混合',
  duration: 45,
})

const paperTypeCounts = reactive([
  { type: '选择题', label: '选择题', count: 5 },
  { type: '判断题', label: '判断题', count: 3 },
  { type: '填空题', label: '填空题', count: 2 },
  { type: '分析题', label: '分析题', count: 1 },
])
const paperPreview = shallowRef<Question[]>([])
const paperLoading = ref(false)

const examTitle = ref('')
const examPaper = shallowRef<Question[]>([])
const examAnswers = ref<Record<string, AnswerValue>>({})
const examSubmitted = ref(false)
const currentExamIndex = ref(0)
const examTime = ref(0)
const examCorrectCount = ref(0)
let examTimer: number | null = null

const recommendedSubject = computed(() => wrongQuestions.value[0]?.subject || learnerCourses.value[0] || subjects.value[0] || 'General')
const recommendedCount = computed(() => {
  const available = practicePool.value.length || questions.value.length
  return available ? Math.min(10, Math.max(5, available)) : 10
})

const filteredWrongQuestions = computed(() => {
  const keyword = wrongFilters.query.trim().toLowerCase()
  if (!keyword) return wrongQuestions.value
  return wrongQuestions.value.filter((item) => {
    return [item.content, item.analysis, item.answer, ...(item.knowledge_points || [])]
      .join(' ')
      .toLowerCase()
      .includes(keyword)
  })
})

const formattedExamTime = computed(() => formatDuration(examTime.value))

const examAnsweredCount = computed(() => examPaper.value.filter((item) => hasAnswerData(examAnswers.value[item.id])).length)
const examScore = computed(() => {
  if (!examPaper.value.length) return 0
  return Math.round((examCorrectCount.value / examPaper.value.length) * 100)
})
const practiceAccuracy = computed(() => {
  if (!stats.totalAttempted) return '0%'
  return `${Math.round((stats.totalCorrect / stats.totalAttempted) * 100)}%`
})

// === SVG 环形进度与雷达图计算 ===
const animatedAccuracy = ref(0)
const radarAnimationScale = ref(0.1)

const circleProgressStyle = computed(() => {
  const perimeter = 2 * Math.PI * 42 // radius = 42 -> ~263.89
  const offset = perimeter - (perimeter * animatedAccuracy.value) / 100
  return {
    strokeDasharray: `${perimeter}`,
    strokeDashoffset: `${offset}`,
    transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)'
  }
})

const radarMetrics = computed(() => {
  const attempted = stats.totalAttempted
  const correct = stats.totalCorrect
  const activeWrong = wrongTotal.value
  
  // 1. 练习量 (Volume): 50道题及以上为100%
  const volume = Math.min(100, Math.max(30, attempted > 0 ? (attempted / 50) * 100 : 30))
  
  // 2. 准确度 (Accuracy)
  const accuracyVal = attempted > 0 ? Math.round((correct / attempted) * 100) : 0
  const accuracy = Math.min(100, Math.max(30, accuracyVal))
  
  // 3. 错题消灭率 (Consolidation)
  const consolidation = Math.min(100, Math.max(30, 100 - (activeWrong * 10)))
  
  // 4. 每日坚持度 (Consistency)
  const streak = Number(localStorage.getItem('question_hub_streak') || '3')
  const consistency = Math.min(100, Math.max(30, 30 + streak * 10))
  
  // 5. 模考应试力 (Mock Score)
  const lastMock = Number(localStorage.getItem('question_hub_last_mock') || '75')
  const mockScore = Math.min(100, Math.max(30, lastMock))
  
  return { volume, accuracy, consolidation, consistency, mockScore }
})

const center = 100
const radius = 64
const angles = [
  -Math.PI / 2,                     // 0: Volume (Top)
  -Math.PI / 2 + (2 * Math.PI) / 5, // 1: Accuracy (Right Top)
  -Math.PI / 2 + (4 * Math.PI) / 5, // 2: Consolidation (Right Bottom)
  -Math.PI / 2 + (6 * Math.PI) / 5, // 3: Consistency (Left Bottom)
  -Math.PI / 2 + (8 * Math.PI) / 5  // 4: Mock Score (Left Top)
]

const radarPoints = computed(() => {
  const metrics = radarMetrics.value
  const vals = [
    metrics.volume,
    metrics.accuracy,
    metrics.consolidation,
    metrics.consistency,
    metrics.mockScore
  ]
  return vals.map((val, i) => {
    const angle = angles[i]!
    const r = radius * (val / 100) * radarAnimationScale.value
    const x = center + r * Math.cos(angle)
    const y = center + r * Math.sin(angle)
    return { x, y }
  })
})

const polygonPointsString = computed(() => {
  return radarPoints.value.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
})

const gridPolygons = computed(() => {
  const levels = [0.33, 0.66, 1.0]
  return levels.map(level => {
    return angles.map(angle => {
      const x = center + radius * level * Math.cos(angle)
      const y = center + radius * level * Math.sin(angle)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
  })
})

const axisLines = computed(() => {
  return angles.map(angle => {
    const x = center + radius * Math.cos(angle)
    const y = center + radius * Math.sin(angle)
    return { x2: x, y2: y }
  })
})

const labelPositions = computed(() => {
  const labelNames = ['练习量', '准确度', '错题消灭', '每日坚持', '模考能力']
  const offset = 16
  return angles.map((angle, i) => {
    const x = center + (radius + offset) * Math.cos(angle)
    const y = center + (radius + offset) * Math.sin(angle)
    let anchor = 'middle'
    if (Math.cos(angle) > 0.3) anchor = 'start'
    else if (Math.cos(angle) < -0.3) anchor = 'end'
    return { text: labelNames[i], x, y: y + 4, anchor }
  })
})

const quotes = [
  '勤学如春起之苗，不见其增，日有所长。',
  '学如逆水行舟，不进则退。',
  '不积跬步，无以至千里；不积小流，无以成江海。',
  '温故而知新，可以为师矣。',
  '博学之，审问之，慎思之，明辨之，笃行之。',
  '独学而无友，则孤陋而寡闻。'
]

const randomQuote = computed(() => {
  const index = (stats.totalAttempted + new Date().getDay()) % quotes.length
  return quotes[index]
})

const localStreak = computed(() => {
  const streak = localStorage.getItem('question_hub_streak')
  if (!streak) {
    localStorage.setItem('question_hub_streak', '3')
    return 3
  }
  return Number(streak)
})

const isDailyCompleted = computed(() => {
  return localStorage.getItem('daily_completed_' + new Date().toDateString()) === 'true'
})

function triggerChartAnimations() {
  radarAnimationScale.value = 0.1
  animatedAccuracy.value = 0
  setTimeout(() => {
    radarAnimationScale.value = 1.0
    const total = stats.totalAttempted
    const corr = stats.totalCorrect
    animatedAccuracy.value = total > 0 ? Math.round((corr / total) * 100) : 0
  }, 100)
}

function backToPortal() {
  activeModule.value = 'portal'
  triggerChartAnimations()
}

// === 原模块定义扩展 ===
const moduleTitles: Record<ModuleKey, string> = {
  portal: '刷题控制台',
  daily: '每日练习',
  practice: '智能练习',
  search: '全部题目',
  paper: '模拟组卷',
  wrong: '错题本',
}
const moduleDescriptions: Record<ModuleKey, string> = {
  portal: '个人刷题进度仪表盘与能力画像。',
  daily: '先完成今天这一题，再进入更完整的练习节奏。',
  practice: '按推荐练习、错题复习、模拟组卷和自定义练习组织你的训练。',
  search: '按学科、难度和题型检索题库并直接作答。',
  paper: '配置你的模拟试卷，并在预览后进入考试模式。',
  wrong: '集中复习错题、管理薄弱点并进行再练。',
}

onMounted(() => {
  readLocalStats()

  // 支持 URL query 参数切换 Tab (e.g., ?tab=wrong)
  const tabParam = route.query.tab as string
  if (tabParam && ['daily', 'practice', 'search', 'paper', 'wrong', 'portal'].includes(tabParam)) {
    activeModule.value = tabParam as ModuleKey
  }
  triggerChartAnimations()

  void bootstrap()
})

watch(viewMode, (newVal) => {
  if (newVal === 'exam') {
    document.body.classList.add('zen-mode-exam')
  } else {
    document.body.classList.remove('zen-mode-exam')
  }
})

onUnmounted(() => {
  stopExamTimer()
  document.body.classList.remove('zen-mode-exam')
})

function scrollToQuestion(index: number) {
  currentExamIndex.value = index
  const el = document.getElementById(`exam-q-${index}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

async function bootstrap() {
  try {
    const profile = await getProfileOnboarding()
    learnerCourses.value = profile.data?.data?.student_profile?.courses || []
  } catch {
    learnerCourses.value = []
  }
  await loadPracticePool()
  await loadQuestionBank()
  await loadWrongBook()
  pickDailyQuestion()
}

function switchModule(key: string) {
  activeModule.value = key as ModuleKey
  if (key === 'wrong') {
    void loadWrongBook()
    void pickWrongQuestion()
  } else if (key === 'search') {
    void loadQuestionBank()
  }
}

async function loadPracticePool() {
  try {
    const result = await fetchQuizBankQuestions({
      subjects: learnerCourses.value.length ? learnerCourses.value : undefined,
      page: 1,
      page_size: 100,
    })
    practicePool.value = result.items || []
    totalQuestions.value = result.total || totalQuestions.value
    subjects.value = uniqueKeepOrder([...(result.subjects || []), ...subjects.value])
    difficulties.value = uniqueKeepOrder([...(result.difficulties || []), ...difficulties.value])
    types.value = uniqueKeepOrder([...(result.types || []), ...types.value])
  } catch {
    practicePool.value = []
  }
}

async function loadQuestionBank() {
  bankLoading.value = true
  try {
    const result = await fetchQuizBankQuestions({
      query: bankFilters.query || undefined,
      subject: bankFilters.subject || undefined,
      subjects: !bankFilters.subject && learnerCourses.value.length ? learnerCourses.value : undefined,
      difficulty: bankFilters.difficulty || undefined,
      type: bankFilters.type || undefined,
      page: bankPage.value,
      page_size: bankPageSize.value,
    })
    questions.value = result.items || []
    totalQuestions.value = result.total || 0
    subjects.value = uniqueKeepOrder([...(result.subjects || []), ...subjects.value])
    difficulties.value = uniqueKeepOrder([...(result.difficulties || []), ...difficulties.value])
    types.value = uniqueKeepOrder([...(result.types || []), ...types.value])
  } catch {
    ElMessage.error('鍔犺浇棰樺簱澶辫触')
  } finally {
    bankLoading.value = false
  }
}

function searchBank() {
  bankPage.value = 1
  openedAnalysis.value = new Set()
  void loadQuestionBank()
}

function handleBankPageChange(page: number) {
  bankPage.value = page
  void loadQuestionBank()
}

async function loadWrongBook() {
  wrongLoading.value = true
  try {
    const result = await fetchWrongQuestions({
      subject: wrongFilters.subject || undefined,
      question_type: wrongFilters.type || undefined,
      is_archived: false,
      page: wrongPage.value,
      page_size: wrongPageSize.value,
    })
    wrongQuestions.value = (result.items || []).map(normalizeWrongQuestion)
    wrongTotal.value = result.total || 0

    // Fetch archived wrong questions count
    const archivedResult = await fetchWrongQuestions({
      subject: wrongFilters.subject || undefined,
      question_type: wrongFilters.type || undefined,
      is_archived: true,
      page: 1,
      page_size: 1,
    })
    archivedWrongTotal.value = archivedResult.total || 0
  } catch {
    ElMessage.error('加载错题本失败')
  } finally {
    wrongLoading.value = false
  }
}

function searchWrong() {
  wrongPage.value = 1
  openedWrongAnalysis.value = new Set()
  void loadWrongBook()
}

function handleWrongPageChange(page: number) {
  wrongPage.value = page
  void loadWrongBook()
}

function normalizeWrongQuestion(item: WrongQuestionDTO): Question {
  return {
    id: item.question_id,
    wrong_id: item.id,
    subject: item.subject,
    type: item.question_type,
    content: item.content,
    options: item.options,
    answer: item.standard_answer || '',
    analysis: item.analysis || '',
    knowledge_points: [],
    wrong_count: item.wrong_count,
    is_archived: item.is_archived,
  }
}

function pickDailyQuestion() {
  const source = practicePool.value.length ? practicePool.value : questions.value
  if (!source.length) {
    dailyQuestion.value = null
    return
  }
  dailyQuestion.value = source[Math.floor(Math.random() * source.length)] || null
}

async function pickWrongQuestion() {
  try {
    const result = await fetchRandomWrongQuestion()
    wrongDrillQuestion.value = result ? normalizeWrongQuestion(result) : null
  } catch {
    wrongDrillQuestion.value = wrongQuestions.value[0] || null
  }
  wrongDrillAnswer.value = ''
  wrongDrillSubmitted.value = false
  wrongDrillCorrect.value = false
  wrongDrillReviewing.value = false
  wrongDrillReview.value = null
}

function startRecommendedPractice() {
  const pool = practicePool.value.filter((item) => !recommendedSubject.value || item.subject === recommendedSubject.value)
  const selected = shuffle(pool.length ? pool : practicePool.value).slice(0, recommendedCount.value)
  if (!selected.length) {
    ElMessage.warning('暂无题目')
    return
  }
  startExam(selected, '推荐练习')
}

function startSingleDailyQuestion() {
  if (!dailyQuestion.value) {
    ElMessage.warning('暂无每日一题')
    return
  }
  startExam([dailyQuestion.value], '每日一题')
}

function startSpecialPracticeProxy(config: typeof practiceForm) {
  void startCustomPractice(config)
}

async function startCustomPractice(config: typeof practiceForm) {
  practiceLoading.value = true
  try {
    const result = await fetchQuizBankQuestions({
      subject: config.subject || undefined,
      difficulty: config.difficulty || undefined,
      type: config.type || undefined,
      page: 1,
      page_size: Math.min(30, Math.max(1, Number(config.count || 10))),
    })
    const selected = result.items || []
    if (!selected.length) {
      ElMessage.warning('没有符合条件的题目')
      return
    }
    startExam(selected, '自定义练习')
  } catch {
    ElMessage.error('鐢熸垚缁冧範澶辫触')
  } finally {
    practiceLoading.value = false
  }
}

function selectBankOption(question: Question, key: string) {
  if (bankSubmitted.value[question.id]) return
  bankAnswers.value[question.id] = updateOptionAnswer(question, bankAnswers.value[question.id], key)
}

async function submitBankAnswer(question: Question) {
  if (bankSubmitted.value[question.id]) return
  bankReviewing.value[question.id] = true
  const result = await gradeQuestion(question, bankAnswers.value[question.id])
  bankSubmitted.value[question.id] = true
  bankCorrect.value[question.id] = result.correct
  bankReview.value[question.id] = result.review
  openedAnalysis.value = new Set(openedAnalysis.value).add(question.id)
  saveAttempt(1, result.correct ? 1 : 0)
  if (!result.correct) await saveWrongQuestion(question, bankAnswers.value[question.id])
  bankReviewing.value[question.id] = false
}

function selectWrongOption(question: Question, key: string) {
  if (wrongSubmitted.value[question.id]) return
  wrongAnswers.value[question.id] = updateOptionAnswer(question, wrongAnswers.value[question.id], key)
}

async function submitWrongAnswer(question: Question) {
  if (wrongSubmitted.value[question.id]) return
  wrongReviewing.value[question.id] = true
  const result = await gradeQuestion(question, wrongAnswers.value[question.id])
  wrongSubmitted.value[question.id] = true
  wrongCorrect.value[question.id] = result.correct
  wrongReview.value[question.id] = result.review
  openedWrongAnalysis.value = new Set(openedWrongAnalysis.value).add(question.id)
  saveAttempt(1, result.correct ? 1 : 0)
  wrongReviewing.value[question.id] = false
}

async function submitWrongDrill() {
  if (!wrongDrillQuestion.value || wrongDrillSubmitted.value) return
  wrongDrillReviewing.value = true
  const result = await gradeQuestion(wrongDrillQuestion.value, wrongDrillAnswer.value)
  wrongDrillSubmitted.value = true
  wrongDrillCorrect.value = result.correct
  wrongDrillReview.value = result.review
  saveAttempt(1, result.correct ? 1 : 0)
  wrongDrillReviewing.value = false
}

function selectWrongDrillOption(key: string) {
  if (!wrongDrillQuestion.value || wrongDrillSubmitted.value) return
  wrongDrillAnswer.value = updateOptionAnswer(wrongDrillQuestion.value, wrongDrillAnswer.value, key)
}

function toggleBankAnalysis(id: string) {
  const next = new Set(openedAnalysis.value)
  next.has(id) ? next.delete(id) : next.add(id)
  openedAnalysis.value = next
}

function toggleWrongAnalysis(id: string) {
  const next = new Set(openedWrongAnalysis.value)
  next.has(id) ? next.delete(id) : next.add(id)
  openedWrongAnalysis.value = next
}

function resetPaperForm() {
  paperForm.title = '妯℃嫙璇曞嵎'
  paperForm.subject = subjects.value[0] || ''
  paperForm.difficulty = '混合'
  paperForm.duration = 45
  if (paperTypeCounts[0]) paperTypeCounts[0].count = 5
  if (paperTypeCounts[1]) paperTypeCounts[1].count = 3
  if (paperTypeCounts[2]) paperTypeCounts[2].count = 2
  if (paperTypeCounts[3]) paperTypeCounts[3].count = 1
  paperPreview.value = []
}

async function generatePaperPreview() {
  const targetCount = paperTypeCounts.reduce((sum, item) => sum + Number(item.count || 0), 0)
  if (targetCount <= 0) return ElMessage.warning('请至少选择 1 道题目')
  paperLoading.value = true
  try {
    const result = await fetchQuizBankQuestions({
      subject: paperForm.subject || undefined,
      difficulty: paperForm.difficulty === '混合' ? undefined : paperForm.difficulty,
      page: 1,
      page_size: 100,
    })
    const pool = result.items || []
    const selected: Question[] = []
    paperTypeCounts.forEach((config) => {
      const sameType = pool.filter((item) => item.type === config.type)
      selected.push(...shuffle(sameType).slice(0, config.count))
    })
    paperPreview.value = selected
    if (!selected.length) ElMessage.warning('暂无题目')
    else ElMessage.success(`已生成 ${selected.length} 道题目`)
  } catch {
    ElMessage.error('生成失败')
  } finally {
    paperLoading.value = false
  }
}

function startPreviewExam() {
  if (!paperPreview.value.length) return
  startExam(paperPreview.value, paperForm.title)
}

function startExam(paper: Question[], title: string) {
  examTitle.value = title
  examPaper.value = paper
  examAnswers.value = {}
    paper.forEach((q) => (examAnswers.value[q.id] = q.type === '多选题' ? [] : ''))
  examSubmitted.value = false
  examCorrectCount.value = 0
  currentExamIndex.value = 0
  examTime.value = 0
  viewMode.value = 'exam'
  startExamTimer()
}

function startExamTimer() {
  stopExamTimer()
  examTimer = window.setInterval(() => {
    if (!examSubmitted.value) examTime.value += 1
  }, 1000)
}

function stopExamTimer() {
  if (examTimer) {
    window.clearInterval(examTimer)
    examTimer = null
  }
}

function quitExam() {
  ElMessageBox.confirm('当前进度将丢失，确定退出吗？', '退出考试', { type: 'warning' })
    .then(() => backWorkspace())
    .catch(() => undefined)
}

async function submitExam() {
  if (examSubmitted.value) return
  const unAnswered = examPaper.value.length - examAnsweredCount.value
  if (unAnswered > 0) {
    try {
      await ElMessageBox.confirm(`还有 ${unAnswered} 道题未作答，确定交卷吗？`, '确认交卷', { type: 'warning' })
    } catch {
      return
    }
  }
  stopExamTimer()
  let correctCount = 0

  const batchResults: Array<Record<string, unknown>> = []

  examPaper.value.forEach((q) => {
    if (isObjectiveQuestion(q)) {
      const isCorrect = evaluateAnswer(q, examAnswers.value[q.id])
      if (isCorrect) correctCount += 1
      batchResults.push({
        question_id: q.id,
        user_answer: formatUserAnswer(examAnswers.value[q.id]),
        is_correct: isCorrect,
        subject: q.subject,
        question_type: q.type,
        content: q.content,
        options: q.options || {},
        answer: q.answer,
        analysis: q.analysis,
      })
    }
  })

  const subjectiveTasks = examPaper.value
    .filter((q) => !isObjectiveQuestion(q))
    .map(async (q) => {
      const { correct } = await gradeQuestion(q, examAnswers.value[q.id])
      if (correct) correctCount += 1
      batchResults.push({
        question_id: q.id,
        user_answer: formatUserAnswer(examAnswers.value[q.id]),
        is_correct: correct,
        subject: q.subject,
        question_type: q.type,
        content: q.content,
        options: q.options || {},
        answer: q.answer,
        analysis: q.analysis,
      })
    })

  await Promise.all(subjectiveTasks)

  if (batchResults.length > 0) {
    await submitObjectiveResults({ results: batchResults as any[] })
  }

  examCorrectCount.value = correctCount
  examSubmitted.value = true
  saveAttempt(examPaper.value.length, correctCount)

  // Save metrics for radar display
  if (examTitle.value === '每日一题') {
    localStorage.setItem('daily_completed_' + new Date().toDateString(), 'true')
    const lastStreak = Number(localStorage.getItem('question_hub_streak') || '3')
    localStorage.setItem('question_hub_streak', String(lastStreak + 1))
  } else if (examPaper.value.length > 0) {
    const pct = Math.round((correctCount / examPaper.value.length) * 100)
    localStorage.setItem('question_hub_last_mock', String(pct))

    // Increment mock exams count
    if (activeModule.value === 'paper') {
      const prevCount = Number(localStorage.getItem('question_hub_mock_exams_count') || '0')
      const newCount = prevCount + 1
      localStorage.setItem('question_hub_mock_exams_count', String(newCount))
      mockExamsCount.value = newCount
    }
  }
}

function backWorkspace() {
  stopExamTimer()
  viewMode.value = 'workspace'
  activeModule.value = 'portal'
  triggerChartAnimations()
  void loadQuestionBank()
  void loadWrongBook()
}

function selectExamOption(q: Question, key: string) {
  if (examSubmitted.value) return
  examAnswers.value[q.id] = updateOptionAnswer(q, examAnswers.value[q.id], key)
}

function isExamCorrect(q: Question) {
  return evaluateAnswer(q, examAnswers.value[q.id])
}

async function gradeQuestion(question: Question, answer: AnswerValue) {
  if (isObjectiveQuestion(question)) return { correct: evaluateAnswer(question, answer), review: null }
  try {
    const review = await fetchQuizReview({
      question_id: question.id,
      question_type: question.type,
      question_content: question.content,
      standard_answer: question.answer,
      user_answer: formatUserAnswer(answer),
      knowledge_points: question.knowledge_points || [],
    })
    return { correct: review.is_correct, review }
  } catch {
    const correct = evaluateAnswer(question, answer)
    return { correct, review: { score: correct ? 100 : 0, is_correct: correct, feedback: correct ? 'Correct' : 'Review needed', improvement_hints: [] } }
  }
}

async function saveWrongQuestion(question: Question, answer: AnswerValue) {
  try {
    await submitObjectiveResults({
      results: [{
        question_id: question.id,
        user_answer: formatUserAnswer(answer),
        is_correct: false,
        subject: question.subject,
        question_type: question.type,
        content: question.content,
        options: question.options || {},
        answer: question.answer,
        analysis: question.analysis,
      }],
    })
    wrongTotal.value += 1
  } catch {
    // ignore duplicates
  }
}

async function archiveWrong(q: Question) {
  if (!q.wrong_id) return
  await archiveWrongQuestion(q.wrong_id)
  await loadWrongBook()
}

async function removeWrong(q: Question) {
  if (!q.wrong_id) return
  await removeWrongQuestion(q.wrong_id)
  await loadWrongBook()
}

function evaluateAnswer(question: Question, answer: AnswerValue) {
  if (isOptionQuestion(question)) {
    const user = normalizeAnswer(answer).sort()
    const std = correctKeys(question).sort()
    return user.length > 0 && user.length === std.length && user.every((item, i) => item === std[i])
  }
  const userText = formatUserAnswer(answer).trim().toLowerCase()
  const stdText = String(question.answer || '').trim().toLowerCase()
  if (!userText) return false
  if (!stdText) return userText.length > 4

  if (question.type === '填空题') {
    return userText === stdText
  }
  return userText.includes(stdText) || stdText.includes(userText)
}

function isObjectiveQuestion(q: Question) { return ['选择题', '判断题', '填空题', '分析题'].includes(q.type) }
function isOptionQuestion(q: Question) { return ['选择题', '判断题'].includes(q.type) }
function getOptions(q: Question) { return q.type === '判断题' ? { A: '正确', B: '错误' } : (q.options || {}) }
function isSelected(ans: AnswerValue, key: string) {
  if (!ans) return false
  return Array.isArray(ans) ? ans.includes(key) : ans === key
}
function updateOptionAnswer(q: Question, ans: AnswerValue, key: string) {
  if (q.type !== '多选题') return key
  const selected = normalizeAnswer(ans)
  return selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]
}
function correctKeys(q: Question) {
  let ansText = String(q.answer || '').trim()
  if (q.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确'].some((item) => upper.includes(item))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误'].some((item) => upper.includes(item))) ansText = 'B'
  }
  return ansText.split(/[、,，\s]+/).map((item) => item.trim().toUpperCase()).filter(Boolean)
}
function isCorrectOption(q: Question, key: string) { return correctKeys(q).includes(key) }
function normalizeAnswer(ans: AnswerValue): string[] {
  if (Array.isArray(ans)) return ans.map((item) => String(item).trim().toUpperCase()).filter(Boolean)
  return String(ans || '').split(/[、,，\s]+/).map((item) => item.trim().toUpperCase()).filter(Boolean)
}
function hasAnswerData(ans: AnswerValue) { return normalizeAnswer(ans).length > 0 }
function formatAnswer(ans: string) { return String(ans || '').replace(/,/g, '、') }
function formatUserAnswer(ans: AnswerValue) { return Array.isArray(ans) ? ans.join(',') : String(ans || '') }

function shuffle<T>(array: T[]): T[] {
  const result = [...array]
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    const temp = result[i] as T
    result[i] = result[j] as T
    result[j] = temp
  }
  return result
}
function uniqueKeepOrder(items: string[]) { return Array.from(new Set(items.filter(Boolean))) }

function readLocalStats() {
  try {
    const saved = JSON.parse(localStorage.getItem('question_hub_stats') || '{}')
    stats.totalAttempted = Number(saved.totalAttempted || 0)
    stats.totalCorrect = Number(saved.totalCorrect || 0)
  } catch {
    stats.totalAttempted = 0
    stats.totalCorrect = 0
  }
}
function saveAttempt(attempted: number, correct: number) {
  stats.totalAttempted += attempted
  stats.totalCorrect += correct
  localStorage.setItem('question_hub_stats', JSON.stringify({ totalAttempted: stats.totalAttempted, totalCorrect: stats.totalCorrect }))
}
function formatDuration(sec: number) {
  return `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`
}
function renderInline(text: string) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.question-bank-layout {
  min-height: calc(100vh - var(--navbar-height, 64px));
  padding: 16px 24px;
  background: var(--color-bg, #f8fafc);
  color: var(--color-text, #0f172a);
  font-family: 'Inter', 'Segoe UI', sans-serif;
  box-sizing: border-box;
}

.question-bank-workspace,
.exam-workspace {
  max-width: 1400px;
  margin: 0 auto;
}

.question-bank-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ================== 新增：玻璃材质材质与全局效果 ================== */
.glass-panel {
  background: rgba(255, 255, 255, 0.72) !important;
  backdrop-filter: blur(16px) saturate(120%) !important;
  border: 1px solid rgba(255, 255, 255, 0.5) !important;
  box-shadow: 0 10px 30px 0 rgba(15, 23, 42, 0.05) !important;
}

.glow-border {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glow-border:hover {
  border-color: rgba(139, 92, 246, 0.4) !important;
  box-shadow: 0 0 24px rgba(139, 92, 246, 0.16) !important;
}

/* ================== 题库控制台主页 & 仪表盘 ================== */
.portal-workspace-view,
.focused-workspace-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.question-bank-hero,
.exam-question,
.exam-sidebar .panel {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.question-bank-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 32px;
}

@media (max-width: 900px) {
  .question-bank-hero {
    flex-direction: column;
    align-items: stretch;
    gap: 24px;
    padding: 24px 28px;
  }
}

.hero-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.hero-kicker,
.workspace-panel-label {
  color: var(--cat-eval, #8b5cf6);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-left h1,
.workspace-panel-header h2,
.exam-title {
  margin: 0;
  color: #0f172a;
  line-height: 1.15;
}

.hero-left h1 {
  font-size: 1.85rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.hero-left .quote {
  margin: 4px 0 10px 0;
  color: var(--color-text-muted, #64748b);
  font-style: italic;
  font-size: 0.9rem;
}

.hero-stats-row {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

/* 环形进度条 */
.accuracy-circle-container {
  position: relative;
  width: 76px;
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.progress-ring {
  transform: rotate(-90deg);
}

.circle-bg {
  fill: none;
  stroke: rgba(226, 232, 240, 0.8);
  stroke-width: 8px;
}

.circle-progress {
  fill: none;
  stroke: var(--cat-eval, #8b5cf6);
  stroke-width: 8px;
  stroke-linecap: round;
}

.circle-content {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.circle-content .pct {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-text-strong, #0f172a);
  line-height: 1;
}

.circle-content .lbl {
  font-size: 9px;
  font-weight: 700;
  color: var(--color-text-muted, #64748b);
  margin-top: 1px;
}

/* 右侧文本指标 */
.stats-text-block {
  display: flex;
  align-items: center;
  gap: 28px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item .lbl {
  color: var(--color-text-muted, #64748b);
  font-size: 12px;
  font-weight: 700;
}

.stat-item .val {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--color-text-strong, #0f172a);
}

.stat-item .danger-color {
  color: var(--color-danger, #ef4444);
}

.stat-item .warning-color {
  color: var(--color-warning, #f59e0b);
}

/* 雷达图 */
.hero-right {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.radar-chart-wrapper {
  background: rgba(255, 255, 255, 0.4);
  border-radius: 20px;
  padding: 8px;
  border: 1px solid rgba(226, 232, 240, 0.5);
}

.radar-grid-poly {
  fill: none;
  stroke: rgba(226, 232, 240, 0.9);
  stroke-width: 1px;
}

.radar-axis-line {
  stroke: rgba(226, 232, 240, 0.9);
  stroke-width: 1px;
  stroke-dasharray: 2 2;
}

.radar-data-poly {
  stroke: var(--cat-eval, #8b5cf6);
  stroke-width: 2px;
  stroke-linejoin: round;
  transition: points 1s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.radar-data-dot {
  fill: #fff;
  stroke: var(--cat-eval, #8b5cf6);
  stroke-width: 2px;
  transition: cx 1s cubic-bezier(0.34, 1.56, 0.64, 1), cy 1s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.radar-label {
  fill: var(--color-text-muted, #64748b);
  font-size: 11px;
  font-weight: 700;
  font-family: inherit;
}

/* ================== 功能入口卡片网格 ================== */
.portal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 1024px) {
  .portal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .portal-grid {
    grid-template-columns: 1fr;
  }
}

.portal-card {
  position: relative;
  padding: 16px 20px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.portal-card:hover {
  transform: translateY(-4px);
  border-color: rgba(139, 92, 246, 0.4) !important;
  box-shadow: 0 10px 24px rgba(139, 92, 246, 0.12) !important;
}

.card-glow-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 10% 10%, rgba(139, 92, 246, 0.03) 0%, transparent 70%);
  pointer-events: none;
}

.card-header-icon {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.icon-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-box.violet { background: rgba(139, 92, 246, 0.08); color: #8b5cf6; }
.icon-box.blue { background: rgba(59, 130, 246, 0.08); color: #3b82f6; }
.icon-box.green { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.icon-box.orange { background: rgba(245, 158, 11, 0.08); color: #f59e0b; }
.icon-box.red { background: rgba(239, 68, 68, 0.08); color: #ef4444; }

.card-badge {
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 99px;
  text-transform: uppercase;
}

.card-badge.success { background: rgba(236, 253, 245, 0.9); color: #059669; }
.card-badge.info { background: rgba(239, 246, 255, 0.9); color: #2563eb; }
.card-badge.secondary { background: rgba(241, 245, 249, 0.9); color: #475569; }
.card-badge.danger { background: rgba(254, 242, 242, 0.9); color: #dc2626; }

/* 呼吸灯动画 */
@keyframes pulseGlow {
  0%, 100% { transform: scale(1); opacity: 0.9; box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
  50% { transform: scale(1.03); opacity: 1; box-shadow: 0 0 10px 4px rgba(245, 158, 11, 0.15); }
}

@keyframes pulseRed {
  0%, 100% { transform: scale(1); opacity: 0.9; box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50% { transform: scale(1.04); opacity: 1; box-shadow: 0 0 10px 4px rgba(239, 68, 68, 0.2); }
}

.pulsing-warning {
  background: rgba(254, 243, 199, 0.9) !important;
  color: #d97706 !important;
  animation: pulseGlow 2s infinite ease-in-out;
}

.pulsing {
  animation: pulseRed 2.5s infinite ease-in-out;
}

.portal-card h3 {
  margin: 0 0 4px 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}

.portal-card p {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
  color: #64748b;
}

/* ================== Themes and Accents ================== */
.focused-workspace-view.theme-daily {
  --theme-color: #8b5cf6;
  --theme-color-glow: rgba(139, 92, 246, 0.25);
  --theme-color-soft: rgba(139, 92, 246, 0.08);
}
.focused-workspace-view.theme-practice {
  --theme-color: #3b82f6;
  --theme-color-glow: rgba(59, 130, 246, 0.25);
  --theme-color-soft: rgba(59, 130, 246, 0.08);
}
.focused-workspace-view.theme-search {
  --theme-color: #10b981;
  --theme-color-glow: rgba(16, 185, 129, 0.25);
  --theme-color-soft: rgba(16, 185, 129, 0.08);
}
.focused-workspace-view.theme-paper {
  --theme-color: #f59e0b;
  --theme-color-glow: rgba(245, 158, 11, 0.25);
  --theme-color-soft: rgba(245, 158, 11, 0.08);
}
.focused-workspace-view.theme-wrong {
  --theme-color: #ef4444;
  --theme-color-glow: rgba(239, 68, 68, 0.25);
  --theme-color-soft: rgba(239, 68, 68, 0.08);
}

/* Accent strip pulsing glow animation */
@keyframes pulseThemeGlow {
  0%, 100% {
    opacity: 0.6;
    box-shadow: 0 0 6px var(--theme-color);
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 14px var(--theme-color);
  }
}

.header-left-side {
  display: flex;
  align-items: stretch;
  gap: 14px;
  max-width: 65%;
}

.theme-accent-strip {
  width: 4px;
  border-radius: 4px;
  background: var(--theme-color);
  box-shadow: 0 0 10px var(--theme-color);
  animation: pulseThemeGlow 2.5s infinite ease-in-out;
  flex-shrink: 0;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.workspace-panel-desc {
  margin: 4px 0 0 0;
  font-size: 0.88rem;
  color: var(--color-text-muted, #64748b);
  line-height: 1.45;
}

/* Header Statistics Badges */
.header-right-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.stat-badge {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(226, 232, 240, 0.8);
  padding: 6px 12px;
  border-radius: 12px;
  min-width: 80px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.02);
}

.badge-label {
  font-size: 10px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.badge-value {
  font-size: 14px;
  font-weight: 800;
  margin-top: 2px;
}

.badge-value.theme-text {
  color: var(--theme-color);
}

.badge-value.text-success {
  color: #10b981;
}

.badge-value.text-warning {
  color: #f59e0b;
}

.badge-value.text-danger {
  color: #ef4444;
}

/* Deep component styling overrides based on active theme */
.focused-workspace-view .crumb-active {
  color: var(--theme-color);
}

.focused-workspace-view .btn-back:hover {
  border-color: var(--theme-color-glow);
  color: var(--theme-color);
}

.focused-workspace-view :deep(.btn-primary) {
  background: var(--theme-color) !important;
  border-color: var(--theme-color) !important;
}

.focused-workspace-view :deep(.btn-primary:hover:not(:disabled)) {
  background: var(--theme-color) !important;
  filter: brightness(0.95);
  box-shadow: 0 0 12px var(--theme-color-glow) !important;
}

.focused-workspace-view :deep(.btn-secondary:hover:not(:disabled)) {
  border-color: var(--theme-color) !important;
  color: var(--theme-color) !important;
  background: var(--theme-color-soft) !important;
}

.focused-workspace-view :deep(.btn-link) {
  color: var(--theme-color) !important;
}

.focused-workspace-view :deep(.btn-link:hover) {
  color: var(--theme-color) !important;
  opacity: 0.8;
}

.focused-workspace-view :deep(.btn-ghost:hover) {
  color: var(--theme-color) !important;
}

.focused-workspace-view :deep(.option-btn.selected) {
  border-color: var(--theme-color) !important;
  background: var(--theme-color-soft) !important;
}

.focused-workspace-view :deep(.option-btn.selected .opt-key) {
  background: var(--theme-color) !important;
  border-color: var(--theme-color) !important;
  box-shadow: 0 4px 10px var(--theme-color-glow) !important;
}

.focused-workspace-view :deep(.opt-key) {
  color: var(--theme-color) !important;
}

.focused-workspace-view :deep(.text-area-input:focus) {
  border-color: var(--theme-color) !important;
  box-shadow: 0 0 0 4px var(--theme-color-soft) !important;
}

.focused-workspace-view :deep(.page-btn:hover:not(:disabled)) {
  border-color: var(--theme-color) !important;
  color: var(--theme-color) !important;
}

.focused-workspace-view :deep(.page-btn.active) {
  background: var(--theme-color) !important;
  border-color: var(--theme-color) !important;
  color: #fff !important;
}

.focused-workspace-view :deep(.tag.type) {
  border-color: var(--theme-color-soft) !important;
  background: var(--theme-color-soft) !important;
  color: var(--theme-color) !important;
}

/* ================== 子工作区玻璃粘性返回栏 ================== */
.workspace-nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-radius: 18px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 10px;
  padding: 8px 14px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-back svg {
  transition: transform 0.2s ease;
}

.btn-back:hover {
  background: rgba(248, 250, 252, 0.95);
  border-color: rgba(139, 92, 246, 0.3);
  color: var(--cat-eval, #8b5cf6);
}

.btn-back:hover svg {
  transform: translateX(-3px);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
}

.crumb-parent {
  color: #64748b;
}

.crumb-divider {
  color: rgba(203, 213, 225, 0.8);
}

.crumb-active {
  color: var(--cat-eval, #8b5cf6);
}

/* ================== 过渡动画 fade-scale ================== */
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.fade-scale-enter-from {
  opacity: 0;
  transform: scale(0.97) translateY(8px);
}

.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(-8px);
}

.workspace-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
  width: fit-content;
}

.workspace-tab {
  min-height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease, transform 150ms ease;
}

.workspace-tab:hover {
  background: rgba(238, 242, 255, 0.9);
  color: #6d28d9;
}

.workspace-tab.active {
  background: var(--cat-eval, #8b5cf6);
  color: #fff;
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.24);
}

.workspace-panel-shell {
  padding: 24px;
}

.workspace-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 18px;
  margin-bottom: 22px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.workspace-panel-header h2 {
  margin-top: 6px;
  font-size: 1.35rem;
  font-weight: 700;
}

.workspace-panel-content {
  min-width: 0;
}

.exam-workspace {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.exam-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 24px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 24px;
  background: linear-gradient(135deg, #ffffff 0%, var(--cat-eval-soft, #f5f3ff) 100%);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.exam-topbar-left,
.exam-actions,
.timer-badge,
.tags,
.question-header {
  display: flex;
  align-items: center;
}

.exam-topbar-left,
.exam-actions,
.question-header {
  gap: 16px;
}

.exam-title {
  font-size: 1.15rem;
  font-weight: 700;
}

.timer-badge {
  gap: 8px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 14px;
  background: var(--cat-eval, #8b5cf6);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 10px 20px rgba(79, 70, 229, 0.18);
}

.exam-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
}

.exam-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.exam-question {
  padding: 28px;
}

.exam-sidebar .panel {
  padding: 24px;
}

.question-header {
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.q-number {
  font-size: 1.55rem;
  font-weight: 800;
  color: #0f172a;
}

.tags {
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  background: #fff;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.tag.type {
  border-color: rgba(99, 102, 241, 0.18);
  background: rgba(238, 242, 255, 0.9);
  color: #6d28d9;
}

.question-text {
  margin-bottom: 28px;
  color: #0f172a;
  font-size: 1.05rem;
  line-height: 1.8;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: #fff;
  color: #0f172a;
  cursor: pointer;
  text-align: left;
  transition: border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
}

.option-btn:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.32);
  background: rgba(248, 250, 252, 0.95);
}

.option-btn.selected {
  border-color: rgba(79, 70, 229, 0.36);
  background: rgba(238, 242, 255, 0.95);
  box-shadow: 0 10px 24px rgba(79, 70, 229, 0.08);
}

.option-btn.correct {
  border-color: rgba(16, 185, 129, 0.28);
  background: rgba(236, 253, 245, 0.92);
}

.option-btn.wrong {
  border-color: rgba(239, 68, 68, 0.25);
  background: rgba(254, 242, 242, 0.94);
}

.opt-key {
  min-width: 24px;
  color: #6d28d9;
  font-size: 15px;
  font-weight: 800;
}

.opt-text {
  font-size: 15px;
  line-height: 1.6;
}

.text-area-input {
  width: 100%;
  min-height: 144px;
  padding: 16px 18px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 18px;
  background: #fff;
  font-family: inherit;
  font-size: 15px;
  color: #0f172a;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.text-area-input:focus {
  border-color: rgba(79, 70, 229, 0.45);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
}

.nav-controls {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.panel h3 {
  margin: 0 0 18px;
  color: #334155;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.score-display,
.progress-display {
  margin-bottom: 24px;
  padding: 24px;
  border-radius: 20px;
  background: linear-gradient(135deg, var(--cat-eval-soft, #f5f3ff) 0%, #ffffff 100%);
  border: 1px solid rgba(165, 180, 252, 0.28);
  text-align: center;
}

.score-value,
.progress-value {
  margin-bottom: 8px;
  color: #6d28d9;
  font-size: 2.25rem;
  font-weight: 800;
}

.score-label,
.progress-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.grid-sheet {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.sheet-btn {
  aspect-ratio: 1;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  color: #475569;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sheet-btn:hover {
  border-color: rgba(139, 92, 246, 0.4);
  background: #fff;
  transform: scale(1.05);
}

.sheet-btn.answered {
  border-color: #8b5cf6;
  background: rgba(139, 92, 246, 0.1);
  color: #7c3aed;
}

.sheet-btn.active {
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.35), inset 0 0 0 2px #fff;
  background: var(--cat-eval, #8b5cf6);
  border-color: var(--cat-eval, #8b5cf6);
  color: #fff;
}

.sheet-btn.correct {
  background: rgba(16, 185, 129, 0.15);
  border-color: #10b981;
  color: #10b981;
}

.sheet-btn.correct.active {
  background: #10b981;
  border-color: #10b981;
  color: #fff;
}

.sheet-btn.wrong {
  background: rgba(239, 68, 68, 0.15);
  border-color: #ef4444;
  color: #ef4444;
}

.sheet-btn.wrong.active {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}

.full-width {
  width: 100%;
}

.sidebar-submit {
  margin-top: 24px;
}

.result-badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.result-badge.success {
  background: rgba(236, 253, 245, 0.92);
  color: #059669;
}

.result-badge.danger {
  background: rgba(254, 242, 242, 0.94);
  color: #dc2626;
}

.analysis-panel {
  margin-top: 24px;
  padding: 18px;
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: #f8fafc;
  font-size: 15px;
}

.analysis-panel.success {
  border-color: rgba(16, 185, 129, 0.16);
}

.analysis-panel.danger {
  border-color: rgba(239, 68, 68, 0.16);
}

.analysis-text {
  margin-top: 10px;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 1100px) {
  .exam-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .question-bank-layout {
    padding: 16px;
  }

  .question-bank-hero,
  .workspace-panel-header,
  .exam-topbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-stats {
    grid-template-columns: 1fr;
    width: 100%;
    min-width: 0;
  }
}

@media (max-width: 640px) {
  .question-bank-layout {
    padding: 12px;
  }

  .question-bank-hero,
  .workspace-panel-shell,
  .exam-question,
  .exam-sidebar .panel {
    border-radius: 20px;
    padding: 18px;
  }

  .workspace-tabs {
    width: 100%;
    border-radius: 24px;
  }

  .workspace-tab {
    flex: 1 1 calc(50% - 8px);
  }

  .nav-controls,
  .exam-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
    justify-content: center;
  }
}

/* ================== Zen Mode (Exam Mode) Global Overrides ================== */
:global(body.zen-mode-exam) .top-navbar {
  display: none !important;
}

:global(body.zen-mode-exam) .page-content {
  padding-top: 0 !important;
  height: 100vh !important;
}

:global(body.zen-mode-exam) .app-layout {
  height: 100vh !important;
}
</style>

