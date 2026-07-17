<template>
  <div class="question-bank-layout">
    <div class="question-bank-workspace">
      <section v-if="viewMode === 'workspace'" class="bank-shell">
        <!-- 左侧题单侧栏 -->
        <aside class="bank-left-rail">
          <div class="rail-brand">
            <div class="rail-brand-icon" aria-hidden="true">
              <PhBooks :size="22" weight="fill" />
            </div>
            <div>
              <strong>题库</strong>
              <span>Question Bank</span>
            </div>
          </div>

          <nav class="rail-menu">
            <button
                v-for="item in moduleNavItems"
                :key="item.key"
                type="button"
                :class="['rail-menu-item', { active: activeModule === item.key }]"
                @click="switchModule(item.key)"
            >
              <span class="rail-menu-icon" aria-hidden="true">
                <component
                  :is="item.icon"
                  :size="20"
                  :weight="activeModule === item.key ? 'fill' : 'regular'"
                />
              </span>
              <span class="rail-menu-copy">
                <strong>{{ item.label }}</strong>
                <small>{{ item.desc }}</small>
              </span>
            </button>
          </nav>

        </aside>

        <!-- 中间主区域 -->
        <main class="bank-main">
          <transition name="fade-scale" mode="out-in">
            <!-- 首页控制台 -->
            <div v-if="activeModule === 'portal'" key="portal" class="portal-board">

              <section class="feature-card-row">
                <button
                    v-for="card in portalCards"
                    :key="card.key"
                    type="button"
                    :class="['feature-card', card.accent]"
                    @click="switchModule(card.key)"
                >
                  <span class="feature-card-kicker">{{ card.kicker }}</span>
                  <strong>{{ card.title }}</strong>
                  <small>{{ card.subtitle }}</small>
                  <i></i>
                </button>
              </section>

              <section v-if="topSubjects.length" class="subject-strip">
                <strong>学科</strong>
                <button
                    v-for="subject in topSubjects"
                    :key="subject"
                    type="button"
                    :class="['subject-chip', { active: bankFilters.subject === subject }]"
                    @click="selectSubject(subject)"
                >
                  {{ subject }}
                </button>
                <button type="button" class="subject-chip muted" @click="switchModule('search')">更多</button>
              </section>

              <section class="section-toolbar">
                <div>
                  <h2>今日推荐题目</h2>
                  <p>先完成一题，系统会根据答题结果更新统计与错题沉淀。</p>
                </div>

                <div class="toolbar-actions">
                  <button type="button" class="soft-action" @click="pickPortalQuestion">换一题</button>
                  <button type="button" class="primary-action" @click="switchModule('search')">全部题库</button>
                </div>
              </section>

              <section class="recommend-question-card">
                <template v-if="portalQuestion">
                  <div class="question-card-top">
                    <span class="tag subject-tag">{{ portalQuestion.subject }}</span>
                    <span class="tag type-tag">{{ portalQuestion.type }}</span>
                    <span class="tag difficulty-tag">{{ portalQuestion.difficulty || '中等' }}</span>
                    <span v-if="isQuestionDone(portalQuestion.id)" class="tag done-tag">做过</span>
                  </div>

                  <div class="recommend-question-content" v-html="renderInline(portalQuestion.content)"></div>

                  <div v-if="isOptionQuestion(portalQuestion)" class="recommend-options">
                    <button
                      v-for="(text, key) in getOptions(portalQuestion)"
                      :key="key"
                      type="button"
                      :class="[
                        'recommend-option',
                        {
                          selected: isSelected(portalAnswers[portalQuestion.id], String(key)),
                          correct: portalSubmitted[portalQuestion.id] && isCorrectOption(portalQuestion, String(key)),
                          wrong:
                            portalSubmitted[portalQuestion.id] &&
                            isSelected(portalAnswers[portalQuestion.id], String(key)) &&
                            !isCorrectOption(portalQuestion, String(key)),
                        },
                      ]"
                      :disabled="portalSubmitted[portalQuestion.id]"
                      @click="selectPortalOption(portalQuestion, String(key))"
                    >
                      <span>{{ key }}</span>
                      <p v-html="renderInline(text)"></p>
                    </button>
                  </div>
                  <textarea
                    v-else
                    v-model="portalAnswers[portalQuestion.id]"
                    :disabled="portalSubmitted[portalQuestion.id]"
                    class="portal-answer-box"
                    rows="4"
                    placeholder="请输入你的答案"
                  ></textarea>

                  <div class="portal-question-foot">
                    <div class="foot-status">
                      <span
                        v-if="portalSubmitted[portalQuestion.id]"
                        :class="['status-pill', subjectiveScoreClass(portalQuestion.id, portalReview, portalCorrect)]"
                      >
                        {{ subjectiveScoreText(portalQuestion.id, portalReview, portalCorrect) }}
                      </span>
                    </div>

                    <div class="question-card-actions">
                      <button
                        type="button"
                        class="primary-action inline"
                        :disabled="portalSubmitted[portalQuestion.id] || !hasAnswerData(portalAnswers[portalQuestion.id])"
                        @click="submitPortalAnswer(portalQuestion)"
                      >
                        {{ portalReviewing[portalQuestion.id] ? `${pendingAnswerLabel(portalQuestion.type)}...` : '提交答案' }}
                      </button>
                      <button type="button" class="soft-action inline" @click="pickPortalQuestion">换一题</button>
                      <button type="button" class="soft-action inline" @click="switchModule('search')">全部题库</button>
                    </div>
                  </div>

                  <div
                    v-if="portalSubmitted[portalQuestion.id] && openedPortalAnalysis.has(portalQuestion.id)"
                    class="portal-analysis-box"
                  >
                    <div class="analysis-head">
                      <strong>参考答案：{{ formatAnswer(portalQuestion.answer) }}</strong>
                      <span v-if="portalReview[portalQuestion.id]?.feedback">
                        {{ portalReview[portalQuestion.id]?.feedback }}
                      </span>
                    </div>
                    <div class="analysis-body" v-html="renderInline(portalQuestion.analysis || '暂无解析')"></div>
                  </div>
                </template>

                <template v-else-if="recommendationLoading">
                  <div class="empty-state">
                    <strong>正在加载推荐题目</strong>
                    <p>正在同步题库数据，请稍候。</p>
                  </div>
                </template>

                <template v-else>
                  <div class="empty-state">
                    <strong>暂无可推荐题目</strong>
                    <p>题库接口返回为空时会显示此状态，请先导入题库数据或调整课程筛选。</p>
                    <button type="button" class="primary-action" @click="reloadQuestionBank">重新加载题库</button>
                  </div>
                </template>
              </section>
            </div>

            <!-- 子模块工作区 -->
            <div v-else :key="activeModule" :class="['module-board', 'theme-' + activeModule]">
              <header class="module-header">
                <div class="module-header-left">
                  <div>
                    <span class="module-kicker">Current Module</span>
                    <h2>{{ moduleTitles[activeModule] }}</h2>
                    <p>{{ moduleDescriptions[activeModule] }}</p>
                  </div>
                </div>

                <div class="module-stats">
                  <template v-if="activeModule === 'daily'">
                    <div class="module-stat">
                      <span>今日完成</span>
                      <strong :class="isDailyCompleted ? 'success' : 'warning'">
                        {{ isDailyCompleted ? '已达标' : '未达标' }}
                      </strong>
                    </div>
                    <div class="module-stat">
                      <span>连续打卡</span>
                      <strong>{{ localStreak }} 天</strong>
                    </div>
                  </template>

                  <template v-else-if="activeModule === 'search'">
                    <div class="module-stat">
                      <span>题库总量</span>
                      <strong>{{ totalQuestions }} 题</strong>
                    </div>
                  </template>

                  <template v-else-if="activeModule === 'paper'">
                    <div class="module-stat">
                      <span>已完模考</span>
                      <strong>{{ mockExamsCount }} 次</strong>
                    </div>
                  </template>

                  <template v-else-if="activeModule === 'wrong'">
                    <div class="module-stat">
                      <span>待巩固</span>
                      <strong class="danger">{{ wrongTotal }} 题</strong>
                    </div>
                    <div class="module-stat">
                      <span>已归档</span>
                      <strong class="success">{{ archivedWrongTotal }} 题</strong>
                    </div>
                  </template>
                </div>
              </header>

              <section class="module-content-card">
                <DailyPracticeTab
                    v-if="activeModule === 'daily'"
                    :questions="dailyQuestions"
                    :answers="dailyAnswers"
                    :submitted="dailySubmitted"
                    :correct="dailyCorrect"
                    :reviewing="dailyReviewing"
                    :review="dailyReview"
                    :openedAnalysis="openedDailyAnalysis"
                    :submittedCount="dailySubmittedCount"
                    :correctCount="dailyCorrectCount"
                    :answerHistoryMap="answerHistoryMap"
                    @refresh-daily="refreshDailyQuestions"
                    @select-daily-option="selectDailyOption"
                    @submit-daily="submitDailyAnswer"
                    @toggle-daily-analysis="toggleDailyAnalysis"
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
                    :highlightQuestionId="highlightQuestionId"
                    :highlightVersion="highlightVersion"
                    :answerHistoryMap="answerHistoryMap"
                    @search="searchBank"
                    @page-change="handleBankPageChange"
                    @select-option="selectBankOption"
                    @submit="submitBankAnswer"
                    @toggle-analysis="toggleBankAnalysis"
                />

                <ExamTab
                    v-else-if="activeModule === 'paper'"
                    mode="config"
                    :form="paperForm"
                    :typeCounts="paperTypeCounts"
                    :preview="paperPreview"
                    :loading="paperLoading"
                    :subjects="subjects"
                    :difficulties="difficulties"
                    :expectedCount="paperExpectedCount"
                    :canStartExam="canStartPaperExam"
                    :examTitle="examTitle"
                    :examPaper="examPaper"
                    :examAnswers="examAnswers"
                    :examReview="examReview"
                    :examSubmitted="examSubmitted"
                    :examReviewing="examReviewing"
                    :examSubmitNoticeVisible="examSubmitNoticeVisible"
                    :currentExamIndex="currentExamIndex"
                    :formattedExamTime="formattedExamTime"
                    :examAnsweredCount="examAnsweredCount"
                    :examUnansweredCount="examUnansweredCount"
                    :examCorrectCount="examCorrectCount"
                    :examWrongCount="examWrongCount"
                    :examScore="examScore"
                    :examResultLevel="examResultLevel"
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
                    @search-wrong="searchWrong"
                    @page-change="handleWrongPageChange"
                    @select-wrong-option="selectWrongOption"
                    @submit-wrong="submitWrongAnswer"
                    @toggle-wrong-analysis="toggleWrongAnalysis"
                    @archive-wrong="archiveWrong"
                    @remove-wrong="removeWrong"
                />

                <HistoryTab
                    v-else-if="activeModule === 'history'"
                    @open-question="openHistoryQuestion"
                />
              </section>
            </div>
          </transition>
        </main>

        <!-- 右侧信息面板 -->
        <aside class="bank-right-panel">
          <section class="right-card calendar-card">
            <div class="right-card-header">
              <strong>每日 10 题</strong>
              <span>{{ calendarMonthLabel }}</span>
            </div>

            <div class="calendar-week">
              <span v-for="day in weekLabels" :key="day">{{ day }}</span>
            </div>

            <div class="calendar-grid">
              <span
                  v-for="day in calendarDays"
                  :key="day.key"
                  :class="[
                  'calendar-day',
                  {
                    muted: !day.isCurrentMonth,
                    today: day.isToday,
                    completed: day.isCompleted,
                  },
                ]"
              >
                {{ day.label }}
              </span>
            </div>
          </section>

          <section class="right-card daily-preview-card">
            <div class="right-card-header">
              <strong>每日挑战</strong>
              <button type="button" class="soft-action" @click="pickDailyChallengeQuestion">换一题</button>
            </div>

            <template v-if="dailyChallengeQuestion">
              <div class="daily-preview-tags">
                <span class="tag subject-tag">{{ dailyChallengeQuestion.subject }}</span>
                <span class="tag type-tag">{{ dailyChallengeQuestion.type }}</span>
                <span class="tag difficulty-tag">{{ dailyChallengeQuestion.difficulty || '中等' }}</span>
              </div>
              <div class="daily-preview-content" v-html="renderInline(dailyChallengeQuestion.content)"></div>
              <button type="button" class="get-question-btn" @click="jumpToChallengeQuestion">
                <span>立即作答</span>
                <i></i>
              </button>
            </template>

            <template v-else>
              <p class="daily-preview-empty">当前暂无可用的每日挑战。</p>
            </template>
          </section>

          <section class="right-card summary-card">
            <div>
              <span>当前题库</span>
              <strong>{{ totalQuestions }}</strong>
            </div>
            <div>
              <span>错题待复习</span>
              <strong>{{ wrongTotal }}</strong>
            </div>
          </section>
        </aside>
      </section>
      <ExamTab
        v-else-if="viewMode === 'exam'"
        mode="exam"
        :form="paperForm"
        :typeCounts="paperTypeCounts"
        :preview="paperPreview"
        :loading="paperLoading"
        :subjects="subjects"
        :difficulties="difficulties"
        :expectedCount="paperExpectedCount"
        :canStartExam="canStartPaperExam"
        :examTitle="examTitle"
        :examPaper="examPaper"
        :examAnswers="examAnswers"
        :examReview="examReview"
        :examSubmitted="examSubmitted"
        :examReviewing="examReviewing"
        :examSubmitNoticeVisible="examSubmitNoticeVisible"
        :currentExamIndex="currentExamIndex"
        :formattedExamTime="formattedExamTime"
        :examAnsweredCount="examAnsweredCount"
        :examUnansweredCount="examUnansweredCount"
        :examCorrectCount="examCorrectCount"
        :examWrongCount="examWrongCount"
        :examScore="examScore"
        :examResultLevel="examResultLevel"
        @select-exam-option="selectExamOption"
        @update-exam-answer="updateExamAnswer"
        @request-submit-exam="requestSubmitExam"
        @cancel-submit-exam="cancelSubmitExam"
        @scroll-to-question="scrollToQuestion"
        @exit-exam="handleExamExit"
        @back-workspace="backWorkspace"
        @open-analysis-review="openAnalysisReview"
      />

      <AnalysisReviewPage
        v-else-if="viewMode === 'analysis-review' && activeAnalysisQuestion"
        :key="activeAnalysisQuestion.id"
        :question="activeAnalysisQuestion"
        :answer="activeAnalysisAnswer"
        :review="activeAnalysisReview"
        :score-value="activeAnalysisScore"
        :result-text="activeAnalysisResultText"
        :question-number="activeAnalysisQuestionNumber"
        :analysis-index="activeAnalysisQuestionIndex"
        :analysis-total="analysisQuestions.length"
        :previous-disabled="activeAnalysisQuestionIndex <= 0"
        :next-disabled="activeAnalysisQuestionIndex >= analysisQuestions.length - 1"
        @close="closeAnalysisReview"
        @previous="showPreviousAnalysisReview"
        @next="showNextAnalysisReview"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
// 导入 Vue 组合式 API 及路由/通知/接口模块
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  PhBookmarkSimple,
  PhBooks,
  PhCalendarCheck,
  PhClockCounterClockwise,
  PhExam,
  PhGauge,
  PhListMagnifyingGlass,
} from '@phosphor-icons/vue'
import { getProfileOnboarding } from '@/features/profile/api/profile'
import { fetchQuizBankQuestions, fetchQuizReview, fetchQuizAnswerHistory, submitObjectiveResults, toQuestionTypeLabel, type QuizReviewResult, type QuizAnswerHistoryItem } from '@/features/question-bank/api/quizBank'
import {
  archiveWrongQuestion,
  fetchWrongQuestions,
  removeWrongQuestion,
} from '@/features/question-bank/api/wrongQuestions'

import DailyPracticeTab from '@/features/question-bank/components/DailyPracticeTab.vue'
import SearchTab from '@/features/question-bank/components/SearchTab.vue'
import ExamTab from '@/features/question-bank/components/ExamTab.vue'
import AnalysisReviewPage from '@/features/question-bank/components/AnalysisReviewPage.vue'
import WrongBookTab from '@/features/question-bank/components/WrongBookTab.vue'
import HistoryTab from '@/features/question-bank/components/HistoryTab.vue'
import { getErrorMessage } from '@/shared/api/http'
import { pendingAnswerLabel, requiresAiReview } from '@/features/question-bank/model/grading'

type ViewMode = 'workspace' | 'exam' | 'analysis-review'
type ModuleKey = 'portal' | 'daily' | 'search' | 'paper' | 'wrong' | 'history'
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
  user_answer?: string | null
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
  user_answer?: string | null
  wrong_count?: number
  is_archived?: boolean
}

interface CalendarCell {
  key: string
  label: number
  isCurrentMonth: boolean
  isToday: boolean
  isCompleted: boolean
}

// 每日练习题量
const DAILY_QUESTION_COUNT = 10

// 视图模式（工作台/考试/分析评阅）
const viewMode = ref<ViewMode>('workspace')
const activeModule = ref<ModuleKey>('portal')
const route = useRoute()

// 筛选条件可选值
const subjects = ref<string[]>([])
const difficulties = ref<string[]>([])
const types = ref<string[]>([])
// 用户课程列表
const learnerCourses = ref<string[]>([])
// 全部/推荐题目池
const practicePool = shallowRef<Question[]>([])
const allQuestionPool = shallowRef<Question[]>([])

// 首页推荐题目 & 每日练习列表 & 右侧每日挑战
const portalQuestion = ref<Question | null>(null)
const dailyQuestions = shallowRef<Question[]>([])
const dailyChallengeQuestion = ref<Question | null>(null)
const recommendationLoading = ref(true)

// 题库搜索状态
const questions = shallowRef<Question[]>([])
const totalQuestions = ref(0)
const bankLoading = ref(false)
const bankPage = ref(1)
const bankPageSize = ref(8)
const bankFilters = reactive({ query: '', subject: '', difficulty: '', type: '' })

// 错题本状态
const wrongQuestions = shallowRef<Question[]>([])
const wrongTotal = ref(0)
const wrongLoading = ref(false)
const wrongPage = ref(1)
const wrongPageSize = ref(8)
const wrongFilters = reactive({ query: '', subject: '', type: '' })

// 答题历史（做过的题）— key: question_id, value: 最新作答记录
const answerHistoryMap = ref<Map<string, QuizAnswerHistoryItem>>(new Map())

// 题库答题状态
const bankAnswers = ref<Record<string, AnswerValue>>({})
const bankSubmitted = ref<Record<string, boolean>>({})
const bankCorrect = ref<Record<string, boolean>>({})
const bankReviewing = ref<Record<string, boolean>>({})
const bankReview = ref<Record<string, QuizReviewResult | null>>({})
const openedAnalysis = ref<Set<string>>(new Set())
const highlightQuestionId = ref<string | null>(null)
const highlightVersion = ref(0)

// 错题答题状态
const wrongAnswers = ref<Record<string, AnswerValue>>({})
const wrongSubmitted = ref<Record<string, boolean>>({})
const wrongCorrect = ref<Record<string, boolean>>({})
const wrongReviewing = ref<Record<string, boolean>>({})
const wrongReview = ref<Record<string, QuizReviewResult | null>>({})
const openedWrongAnalysis = ref<Set<string>>(new Set())

// 首页推荐答题状态
const portalAnswers = ref<Record<string, AnswerValue>>({})
const portalSubmitted = ref<Record<string, boolean>>({})
const portalCorrect = ref<Record<string, boolean>>({})
const portalReviewing = ref<Record<string, boolean>>({})
const portalReview = ref<Record<string, QuizReviewResult | null>>({})
const openedPortalAnalysis = ref<Set<string>>(new Set())

// 每日练习答题状态
const dailyAnswers = ref<Record<string, AnswerValue>>({})
const dailySubmitted = ref<Record<string, boolean>>({})
const dailyCorrect = ref<Record<string, boolean>>({})
const dailyReviewing = ref<Record<string, boolean>>({})
const dailyReview = ref<Record<string, QuizReviewResult | null>>({})
const openedDailyAnalysis = ref<Set<string>>(new Set())

// 答题统计（本地持久化）
const stats = reactive({ totalAttempted: 0, totalCorrect: 0 })
const localStatsSeed = ref(0)
const dailyStateSeed = ref(0)

// 模考次数 & 已归档错题数
const mockExamsCount = ref(Number(localStorage.getItem('question_hub_mock_exams_count') || '0'))
const archivedWrongTotal = ref(0)

// 试卷表单配置
const paperForm = reactive({
  title: '模拟试卷',
  subject: '',
  difficulty: '混合',
  duration: 45,
})

// 各题型数量配置
const paperTypeCounts = reactive([
  { type: '单选题', label: '单选题', count: 5 },
  { type: '判断题', label: '判断题', count: 3 },
  { type: '填空题', label: '填空题', count: 2 },
  { type: '分析题', label: '分析题', count: 1 },
])
const paperPreview = shallowRef<Question[]>([])
const paperLoading = ref(false)

// 考试状态
const examTitle = ref('')
const examPaper = shallowRef<Question[]>([])
const examAnswers = ref<Record<string, AnswerValue>>({})
const examReview = ref<Record<string, QuizReviewResult | null>>({})
const examSubmitted = ref(false)
const examReviewing = ref(false)
const examSubmitNoticeVisible = ref(false)
const currentExamIndex = ref(-1)
const examTime = ref(0)
const examCorrectCount = ref(0)
const activeAnalysisQuestionId = ref<string | null>(null)
const analysisReturnQuestionIndex = ref(0)
let examTimer: number | null = null

// 分析题列表（用于评阅翻页）
const analysisQuestions = computed(() => examPaper.value.filter((question) => question.type === '分析题'))

// 当前评阅的分析题对象
const activeAnalysisQuestion = computed(() => {
  if (!activeAnalysisQuestionId.value) return null
  return examPaper.value.find((question) => question.id === activeAnalysisQuestionId.value) || null
})

// 当前评阅的分析题在列表中的索引
const activeAnalysisQuestionIndex = computed(() => {
  if (!activeAnalysisQuestion.value) return -1
  return analysisQuestions.value.findIndex((question) => question.id === activeAnalysisQuestion.value?.id)
})

// 当前评阅的分析题在试卷中的题号
const activeAnalysisQuestionNumber = computed(() => {
  if (!activeAnalysisQuestion.value) return 0
  return examPaper.value.findIndex((question) => question.id === activeAnalysisQuestion.value?.id) + 1
})

// 当前评阅的用户答案
const activeAnalysisAnswer = computed<AnswerValue>(() => {
  if (!activeAnalysisQuestion.value) return undefined
  return examAnswers.value[activeAnalysisQuestion.value.id]
})

// 当前评阅的 AI 评阅结果
const activeAnalysisReview = computed<QuizReviewResult | null>(() => {
  if (!activeAnalysisQuestion.value) return null
  return examReview.value[activeAnalysisQuestion.value.id] || null
})

// 当前评阅的得分
const activeAnalysisScore = computed(() => {
  const question = activeAnalysisQuestion.value
  if (!question) return 0
  const score = examReview.value[question.id]?.score
  if (score != null) return Math.min(100, Math.max(0, Math.round(Number(score) || 0)))
  return evaluateAnswer(question, examAnswers.value[question.id]) ? 100 : 0
})

// 当前评阅结果文本
const activeAnalysisResultText = computed(() => {
  const score = activeAnalysisScore.value
  if (score >= 80) return '优秀'
  if (score >= 60) return '部分正确'
  return '需要改进'
})

const weekLabels = ['日', '一', '二', '三', '四', '五', '六']

const moduleTitles: Record<ModuleKey, string> = {
  portal: '刷题控制台',
  daily: '每日练习',
  search: '全部题目',
  paper: '模拟组卷',
  wrong: '错题本',
  history: '答题记录',
}

const moduleDescriptions: Record<ModuleKey, string> = {
  portal: '个人刷题进度仪表盘与能力画像。',
  daily: '先完成今天这一题，再进入更完整的练习节奏。',
  search: '按学科、难度和题型检索题库并直接作答。',
  paper: '配置你的模拟试卷，并在预览后进入考试模式。',
  wrong: '集中复习错题、管理薄弱点并进行再练。',
  history: '查看所有做过的题目，按科目和对错筛选。',
}

const moduleNavItems = [
  { key: 'portal' as ModuleKey, label: '控制台', desc: '刷题总览', icon: PhGauge },
  { key: 'daily' as ModuleKey, label: '每日练习', desc: '每日 10 题', icon: PhCalendarCheck },
  { key: 'search' as ModuleKey, label: '全部题目', desc: '筛选检索', icon: PhListMagnifyingGlass },
  { key: 'paper' as ModuleKey, label: '模拟组卷', desc: '考试模式', icon: PhExam },
  { key: 'wrong' as ModuleKey, label: '错题本', desc: '薄弱复习', icon: PhBookmarkSimple },
  { key: 'history' as ModuleKey, label: '答题记录', desc: '做过汇总', icon: PhClockCounterClockwise },
]

// 首页功能卡片配置（动态显示每日/错题/模考状态）
const portalCards = computed(() => [
  {
    key: 'daily' as ModuleKey,
    kicker: isDailyCompleted.value ? 'Completed' : 'Daily',
    title: '每日 10 题',
    subtitle: isDailyCompleted.value ? '今日训练已完成' : '完成今天的基础训练',
    accent: 'black',
  },
  {
    key: 'wrong' as ModuleKey,
    kicker: 'Review',
    title: `错题本 ${wrongTotal.value || wrongQuestions.value.length}`,
    subtitle: wrongTotal.value ? '集中复盘薄弱错题' : '暂无错题，保持正确率',
    accent: 'green',
  },
  {
    key: 'paper' as ModuleKey,
    kicker: 'Exam',
    title: '模拟组卷',
    subtitle: '配置题量并进入考试模式',
    accent: 'blue',
  },
])

// 试卷期望题目总数
const paperExpectedCount = computed(() => {
  return paperTypeCounts.reduce((sum, item) => sum + Number(item.count || 0), 0)
})

// 是否可以开始考试
const canStartPaperExam = computed(() => {
  return paperExpectedCount.value > 0 && paperPreview.value.length === paperExpectedCount.value
})

// 每日练习已提交数和正确数
const dailySubmittedCount = computed(() => {
  return dailyQuestions.value.filter((question) => dailySubmitted.value[question.id]).length
})

const dailyCorrectCount = computed(() => {
  return dailyQuestions.value.filter((question) => dailyCorrect.value[question.id]).length
})

// 错题列表（客户端关键词过滤）
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

const topSubjects = computed(() => {
  return learnerCourses.value
    .filter((course) => typeof course === 'string' && course.trim().length > 0)
    .slice(0, 5)
})

// 格式化考试倒计时
const formattedExamTime = computed(() => formatDuration(examTime.value))

// 考试已答/未答/错误数
const examAnsweredCount = computed(() => examPaper.value.filter((item) => hasAnswerData(examAnswers.value[item.id])).length)

const examUnansweredCount = computed(() => examPaper.value.length - examAnsweredCount.value)

const examWrongCount = computed(() => Math.max(examPaper.value.length - examCorrectCount.value - examUnansweredCount.value, 0))

// 考试成绩百分比
const examScore = computed(() => {
  if (!examPaper.value.length) return 0
  return Math.round((examCorrectCount.value / examPaper.value.length) * 100)
})

// 考试等级评定
const examResultLevel = computed(() => {
  if (examScore.value >= 90) return '优秀'
  if (examScore.value >= 75) return '良好'
  if (examScore.value >= 60) return '合格'
  return '待加强'
})

const animatedAccuracy = ref(0)
const radarAnimationScale = ref(0.1)

// 日历标题（当前年月）
const calendarMonthLabel = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long' }).format(new Date())
})

// 生成日历网格（42 格，含完成标记）
const calendarDays = computed<CalendarCell[]>(() => {
  dailyStateSeed.value
  const completionMap = readDailyCompletionMap()

  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth()
  const firstDay = new Date(year, month, 1)
  const start = new Date(year, month, 1 - firstDay.getDay())
  const result: CalendarCell[] = []

  for (let i = 0; i < 42; i += 1) {
    const date = new Date(start)
    date.setDate(start.getDate() + i)

    const isToday =
        date.getFullYear() === today.getFullYear() &&
        date.getMonth() === today.getMonth() &&
        date.getDate() === today.getDate()

    result.push({
      key: formatDateKey(date),
      label: date.getDate(),
      isCurrentMonth: date.getMonth() === month,
      isToday,
      isCompleted: completionMap[formatDateKey(date)] === true,
    })
  }

  return result
})

// 连续打卡天数（本地存储）
const localStreak = computed(() => {
  localStatsSeed.value
  const streak = localStorage.getItem('question_hub_streak')
  if (!streak) {
    localStorage.setItem('question_hub_streak', '3')
    return 3
  }
  return Number(streak)
})

// 今日是否已完成每日练习
const isDailyCompleted = computed(() => {
  dailyStateSeed.value
  const todayKey = formatDateKey(new Date())
  const completionMap = readDailyCompletionMap()
  return completionMap[todayKey] === true
})

// 触发首页图表动画（延迟更新数值实现入场效果）
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

// 页面挂载：读取本地统计、解析路由参数、加载数据
onMounted(() => {
  readLocalStats()

  const tabParam = route.query.tab as string
  if (tabParam && ['daily', 'search', 'paper', 'wrong', 'portal'].includes(tabParam)) {
    activeModule.value = tabParam as ModuleKey
  }

  triggerChartAnimations()
  void bootstrap()
})

// 试卷表单变化时清除旧预览
watch(
  () => [
    paperForm.subject,
    paperForm.difficulty,
    paperForm.duration,
    paperForm.title,
    ...paperTypeCounts.map((item) => Number(item.count || 0)),
  ],
  () => {
    paperPreview.value = []
  },
)

// 组件卸载时停止考试计时器
onUnmounted(() => {
  stopExamTimer()
})

// 滚动到指定考试题号
function scrollToQuestion(index: number) {
  currentExamIndex.value = index
  const el = document.getElementById(`exam-q-${index}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

// 初始化加载所有数据
async function bootstrap() {
  try {
    const profile = await getProfileOnboarding()
    const profileCourses = profile.data?.data?.student_profile?.courses
    learnerCourses.value = Array.isArray(profileCourses) ? profileCourses.map(String) : []
  } catch {
    learnerCourses.value = []
  }

  syncBankSubmissionStateForToday()
  recommendationLoading.value = true
  const practicePoolPromise = loadPracticePool()
  await Promise.all([
    practicePoolPromise,
    loadQuestionBank(),
    loadWrongBook(),
    loadAnswerHistory(),
  ])
  refreshDailySelections()
  recommendationLoading.value = false
}

async function reloadQuestionBank() {
  recommendationLoading.value = true
  await Promise.all([
    loadPracticePool(),
    loadQuestionBank(),
  ])
  refreshDailySelections()
  recommendationLoading.value = false
}

// 切换左侧导航模块
function switchModule(key: string) {
  activeModule.value = key as ModuleKey

  if (key === 'wrong') {
    void loadWrongBook()
  } else if (key === 'search') {
    resetQuestionBankFilters()
    clearQuestionHighlight()
    void loadQuestionBank()
  } else if (key === 'daily') {
    refreshDailyQuestions()
  }
}

// 重置题库搜索筛选条件
function resetQuestionBankFilters() {
  bankFilters.query = ''
  bankFilters.subject = ''
  bankFilters.difficulty = ''
  bankFilters.type = ''
  bankPage.value = 1
}

// 点击学科标签跳转到搜索
function selectSubject(subject: string) {
  bankFilters.subject = bankFilters.subject === subject ? '' : subject
  activeModule.value = 'search'
  bankPage.value = 1
  void loadQuestionBank()
}

// 加载全部题目到内存池（用于随机推荐）
async function loadPracticePool() {
  try {
    const pageSize = 100
    const allItems: Question[] = []
    const seen = new Set<string>()
    let page = 1
    let total = 0

    while (true) {
      const result = await fetchQuizBankQuestions({
        page,
        page_size: pageSize,
      })

      const items = result.items || []
      total = result.total || total

      items.forEach((item) => {
        if (item?.id && !seen.has(item.id)) {
          seen.add(item.id)
          allItems.push(item)
        }
      })

      subjects.value = uniqueKeepOrder([...(result.subjects || []), ...subjects.value])
      difficulties.value = uniqueKeepOrder([...(result.difficulties || []), ...difficulties.value])
      types.value = uniqueKeepOrder([...(result.types || []), ...types.value])

      if (!items.length || items.length < pageSize || (total > 0 && allItems.length >= total)) break
      page += 1
    }

    allQuestionPool.value = allItems
    practicePool.value = allItems
    totalQuestions.value = total || allItems.length || totalQuestions.value
  } catch (error) {
    allQuestionPool.value = []
    practicePool.value = []
    toast.error(getErrorMessage(error, '加载练习池失败'))
  }
}

// 加载答题历史（做过的题）
async function loadAnswerHistory() {
  try {
    answerHistoryMap.value = await fetchQuizAnswerHistory()
  } catch {
    answerHistoryMap.value = new Map()
  }
}

// 检查题目是否做过
function isQuestionDone(questionId: string): boolean {
  return answerHistoryMap.value.has(questionId)
}

// 根据筛选条件加载题库分页
async function loadQuestionBank() {
  bankLoading.value = true
  try {
    const response = await fetchQuizBankQuestions({
      query: bankFilters.query || undefined,
      subject: bankFilters.subject || undefined,
      difficulty: bankFilters.difficulty || undefined,
      type: bankFilters.type || undefined,
      page: bankPage.value,
      page_size: bankPageSize.value,
    })

    questions.value = response.items || []
    totalQuestions.value = response.total || 0

    if (response.subjects?.length) subjects.value = uniqueKeepOrder(response.subjects)
    if (response.difficulties?.length) difficulties.value = uniqueKeepOrder(response.difficulties)
    if (response.types?.length) types.value = uniqueKeepOrder(response.types)
  } catch (error) {
    toast.error(getErrorMessage(error, '加载题库失败'))
  } finally {
    bankLoading.value = false
  }
}

// 触发题库搜索（重置到第一页）
function searchBank() {
  bankPage.value = 1
  clearQuestionHighlight()
  openedAnalysis.value = new Set()
  void loadQuestionBank()
}

// 题库翻页
function handleBankPageChange(page: number) {
  bankPage.value = page
  void loadQuestionBank()
}

// 加载错题本列表
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

    const archivedResult = await fetchWrongQuestions({
      subject: wrongFilters.subject || undefined,
      question_type: wrongFilters.type || undefined,
      is_archived: true,
      page: 1,
      page_size: 1,
    })
    archivedWrongTotal.value = archivedResult.total || 0
  } catch {
    toast.error('加载错题本失败')
  } finally {
    wrongLoading.value = false
  }
}

// 搜索错题（重置到第一页）
function searchWrong() {
  wrongPage.value = 1
  openedWrongAnalysis.value = new Set()
  void loadWrongBook()
}

// 错题本翻页
function handleWrongPageChange(page: number) {
  wrongPage.value = page
  void loadWrongBook()
}

// 将后端错题格式转为通用 Question 格式
function normalizeWrongQuestion(item: WrongQuestionDTO): Question {
  return {
    id: item.question_id,
    wrong_id: item.id,
    subject: item.subject,
    type: toQuestionTypeLabel(item.question_type),
    content: item.content,
    options: item.options,
    answer: item.standard_answer || '',
    analysis: item.analysis || '',
    user_answer: item.user_answer || '',
    knowledge_points: [],
    wrong_count: item.wrong_count,
    is_archived: item.is_archived,
  }
}

// 从题库随机选一道首页推荐题（排除已在其他模块的题目）
function pickPortalQuestion() {
  const excluded = [
    ...dailyQuestions.value.map((item) => item.id),
    ...(dailyChallengeQuestion.value ? [dailyChallengeQuestion.value.id] : []),
  ]
  const nextQuestion = pickQuestionExcluding(excluded)
  portalQuestion.value = nextQuestion
  resetPortalState(nextQuestion)
}

// 随机选一道每日挑战题
function pickDailyChallengeQuestion() {
  const excluded = [
    ...(portalQuestion.value ? [portalQuestion.value.id] : []),
    ...dailyQuestions.value.map((item) => item.id),
  ]
  dailyChallengeQuestion.value = pickQuestionExcluding(excluded)
}

// 刷新每日练习 10 题（打乱抽取）
function refreshDailyQuestions() {
  const excluded = new Set<string>([
    ...(portalQuestion.value ? [portalQuestion.value.id] : []),
    ...(dailyChallengeQuestion.value ? [dailyChallengeQuestion.value.id] : []),
  ])
  const source = allQuestionPool.value.length ? allQuestionPool.value : questions.value
  const pool = source.filter((item) => !excluded.has(item.id))
  const selected = shuffle(pool.length ? pool : source).slice(0, Math.min(DAILY_QUESTION_COUNT, source.length))

  dailyQuestions.value = selected
  resetDailyState(selected)
}

// 重新选取首页推荐、每日练习、每日挑战
function refreshDailySelections() {
  portalQuestion.value = null
  dailyQuestions.value = []
  dailyChallengeQuestion.value = null
  pickPortalQuestion()
  refreshDailyQuestions()
  pickDailyChallengeQuestion()
}

// 从题目池中排除指定 ID 后随机选取
function pickQuestionExcluding(excludedIds: string[]) {
  const source = allQuestionPool.value.length ? allQuestionPool.value : practicePool.value.length ? practicePool.value : questions.value
  if (!source.length) return null

  const excluded = new Set(excludedIds)
  const available = source.filter((item) => !excluded.has(item.id))
  const pool = available.length ? available : source
  return pool[Math.floor(Math.random() * pool.length)] || null
}

function clearQuestionHighlight() {
  highlightQuestionId.value = null
}

// 重置首页推荐题的答题状态
function resetPortalState(question: Question | null) {
  portalAnswers.value = {}
  portalSubmitted.value = {}
  portalCorrect.value = {}
  portalReviewing.value = {}
  portalReview.value = {}
  openedPortalAnalysis.value = new Set()

  if (!question) return
  portalAnswers.value[question.id] = ''
}

// 重置每日练习的答题状态
function resetDailyState(selected: Question[]) {
  const nextAnswers: Record<string, AnswerValue> = {}
  const nextSubmitted: Record<string, boolean> = {}
  const nextCorrect: Record<string, boolean> = {}
  const nextReviewing: Record<string, boolean> = {}
  const nextReview: Record<string, QuizReviewResult | null> = {}

  selected.forEach((question) => {
    nextAnswers[question.id] = ''
    nextSubmitted[question.id] = false
    nextCorrect[question.id] = false
    nextReviewing[question.id] = false
    nextReview[question.id] = null
  })

  dailyAnswers.value = nextAnswers
  dailySubmitted.value = nextSubmitted
  dailyCorrect.value = nextCorrect
  dailyReviewing.value = nextReviewing
  dailyReview.value = nextReview
  openedDailyAnalysis.value = new Set()
}

// 从每日挑战跳转到搜索模块并高亮对应题目
async function jumpToChallengeQuestion() {
  if (!dailyChallengeQuestion.value) {
    toast.warning('暂无可跳转的每日挑战')
    return
  }

  const targetId = dailyChallengeQuestion.value.id
  const source = allQuestionPool.value.length ? allQuestionPool.value : practicePool.value.length ? practicePool.value : questions.value
  const sourceIndex = source.findIndex((item) => item.id === targetId)

  activeModule.value = 'search'
  resetQuestionBankFilters()
  bankPage.value = sourceIndex >= 0 ? Math.floor(sourceIndex / bankPageSize.value) + 1 : 1
  highlightQuestionId.value = targetId
  highlightVersion.value += 1
  openedAnalysis.value = new Set()

  await loadQuestionBank()

  if (!questions.value.some((item) => item.id === targetId)) {
    highlightQuestionId.value = null
    toast.warning('未在当前题库分页中定位到该题目')
  }
}

// 题库选项选择
function selectBankOption(question: Question, key: string) {
  if (bankSubmitted.value[question.id]) return
  bankAnswers.value[question.id] = updateOptionAnswer(question, bankAnswers.value[question.id], key)
}

// 首页推荐题选项选择
function selectPortalOption(question: Question, key: string) {
  if (portalSubmitted.value[question.id]) return
  portalAnswers.value[question.id] = updateOptionAnswer(question, portalAnswers.value[question.id], key)
}

// 提交首页推荐题（调用 AI 评阅 or 自动判题）
async function submitPortalAnswer(question: Question) {
  if (portalSubmitted.value[question.id]) return

  portalReviewing.value[question.id] = true
  const result = await gradeQuestion(question, portalAnswers.value[question.id])
  portalSubmitted.value[question.id] = true
  portalCorrect.value[question.id] = result.correct
  portalReview.value[question.id] = result.review
  openedPortalAnalysis.value = new Set(openedPortalAnalysis.value).add(question.id)
  saveAttempt(1, result.correct ? 1 : 0)

  await submitQuestionAttempt(question, portalAnswers.value[question.id], result.correct, result.review?.score)

  portalReviewing.value[question.id] = false
}

// 从答题记录定位到题库原题，并自动展开作答面板。
async function openHistoryQuestion(questionId: string) {
  const source = allQuestionPool.value.length
    ? allQuestionPool.value
    : practicePool.value.length
      ? practicePool.value
      : questions.value
  const sourceIndex = source.findIndex((item) => item.id === questionId)

  activeModule.value = 'search'
  resetQuestionBankFilters()
  bankPage.value = sourceIndex >= 0 ? Math.floor(sourceIndex / bankPageSize.value) + 1 : 1
  highlightQuestionId.value = questionId
  highlightVersion.value += 1
  openedAnalysis.value = new Set()

  await loadQuestionBank()

  if (!questions.value.some((item) => item.id === questionId)) {
    highlightQuestionId.value = null
    toast.warning('未能在题库中定位到这道题目')
  }
}

// 提交题库搜索中的题目答案
async function submitBankAnswer(question: Question) {
  if (bankSubmitted.value[question.id]) return

  bankReviewing.value[question.id] = true
  const result = await gradeQuestion(question, bankAnswers.value[question.id])
  bankSubmitted.value[question.id] = true
  bankCorrect.value[question.id] = result.correct
  bankReview.value[question.id] = result.review
  openedAnalysis.value = new Set(openedAnalysis.value).add(question.id)
  markBankQuestionSubmittedToday(question.id, result.correct)
  saveAttempt(1, result.correct ? 1 : 0)

  await submitQuestionAttempt(question, bankAnswers.value[question.id], result.correct, result.review?.score)

  bankReviewing.value[question.id] = false
}

// 每日练习选项选择
function selectDailyOption(question: Question, key: string) {
  if (dailySubmitted.value[question.id]) return
  dailyAnswers.value[question.id] = updateOptionAnswer(question, dailyAnswers.value[question.id], key)
}

// 提交每日练习答案
async function submitDailyAnswer(question: Question) {
  if (dailySubmitted.value[question.id]) return

  dailyReviewing.value[question.id] = true
  const result = await gradeQuestion(question, dailyAnswers.value[question.id])
  dailySubmitted.value[question.id] = true
  dailyCorrect.value[question.id] = result.correct
  dailyReview.value[question.id] = result.review
  openedDailyAnalysis.value = new Set(openedDailyAnalysis.value).add(question.id)
  saveAttempt(1, result.correct ? 1 : 0)

  await submitQuestionAttempt(question, dailyAnswers.value[question.id], result.correct, result.review?.score)

  dailyReviewing.value[question.id] = false

  // 全部完成后标记今日达标并更新连续打卡
  if (dailySubmittedCount.value === dailyQuestions.value.length && dailyQuestions.value.length > 0 && !isDailyCompleted.value) {
    markDailyCompleted(new Date())

    const lastStreak = Number(localStorage.getItem('question_hub_streak') || '3')
    localStorage.setItem('question_hub_streak', String(lastStreak + 1))

    dailyStateSeed.value += 1
    localStatsSeed.value += 1
  }
}

// 错题本选项选择
function selectWrongOption(question: Question, key: string) {
  if (wrongSubmitted.value[question.id]) return
  wrongAnswers.value[question.id] = updateOptionAnswer(question, wrongAnswers.value[question.id], key)
}

// 提交错题本中的题目
async function submitWrongAnswer(question: Question) {
  if (wrongSubmitted.value[question.id]) return

  wrongReviewing.value[question.id] = true
  const result = await gradeQuestion(question, wrongAnswers.value[question.id])
  wrongSubmitted.value[question.id] = true
  wrongCorrect.value[question.id] = result.correct
  wrongReview.value[question.id] = result.review
  openedWrongAnalysis.value = new Set(openedWrongAnalysis.value).add(question.id)
  saveAttempt(1, result.correct ? 1 : 0)
  await submitQuestionAttempt(question, wrongAnswers.value[question.id], result.correct, result.review?.score)
  wrongReviewing.value[question.id] = false
}

// 切换题库题目的解析展开/收起
function toggleBankAnalysis(id: string) {
  const next = new Set(openedAnalysis.value)
  next.has(id) ? next.delete(id) : next.add(id)
  openedAnalysis.value = next
}

// 切换每日练习的解析展开/收起
function toggleDailyAnalysis(id: string) {
  const next = new Set(openedDailyAnalysis.value)
  next.has(id) ? next.delete(id) : next.add(id)
  openedDailyAnalysis.value = next
}

// 切换错题本解析展开/收起
function toggleWrongAnalysis(id: string) {
  const next = new Set(openedWrongAnalysis.value)
  next.has(id) ? next.delete(id) : next.add(id)
  openedWrongAnalysis.value = next
}

// 重置试卷配置表单
function resetPaperForm() {
  paperForm.title = '模拟试卷'
  paperForm.subject = subjects.value[0] || ''
  paperForm.difficulty = '混合'
  paperForm.duration = 45

  if (paperTypeCounts[0]) paperTypeCounts[0].count = 5
  if (paperTypeCounts[1]) paperTypeCounts[1].count = 3
  if (paperTypeCounts[2]) paperTypeCounts[2].count = 2
  if (paperTypeCounts[3]) paperTypeCounts[3].count = 1

  paperPreview.value = []
}

// 分页加载试卷题目池
async function fetchPaperQuestionPool() {
  const pageSize = 100
  const allItems: Question[] = []
  const seen = new Set<string>()
  let page = 1
  let total = 0

  while (true) {
    const result = await fetchQuizBankQuestions({
      subject: paperForm.subject || undefined,
      difficulty: paperForm.difficulty === '混合' ? undefined : paperForm.difficulty,
      page,
      page_size: pageSize,
    })

    const items = result.items || []
    total = result.total || total

    items.forEach((item) => {
      if (item?.id && !seen.has(item.id)) {
        seen.add(item.id)
        allItems.push(item)
      }
    })

    if (!items.length || items.length < pageSize || (total > 0 && allItems.length >= total)) break
    page += 1
  }

  return allItems
}

// 根据配置生成试卷预览（按题型随机抽题）
async function generatePaperPreview() {
  const targetCount = paperExpectedCount.value
  if (targetCount <= 0) return toast.warning('请至少选择 1 道题目')

  paperLoading.value = true
  try {
    const pool = await fetchPaperQuestionPool()
    const selected: Question[] = []
    const shortages: string[] = []

    paperTypeCounts.forEach((config) => {
      const needed = Number(config.count || 0)
      if (needed <= 0) return

      const sameType = pool.filter((item) => item.type === config.type)
      const picked = shuffle(sameType).slice(0, needed)
      selected.push(...picked)

      if (picked.length < needed) {
        shortages.push(`${config.label}缺少 ${needed - picked.length} 道`)
      }
    })

    paperPreview.value = selected

    if (!selected.length) {
      toast.warning('暂无题目')
      return
    }

    if (shortages.length > 0 || selected.length !== targetCount) {
      toast.warning(`题量不足：${shortages.join('，') || '请重新调整题型数量'}`)
      return
    }

    toast.success(`已生成 ${selected.length} 道题目`)
  } catch {
    toast.error('生成失败')
  } finally {
    paperLoading.value = false
  }
}

// 从预览进入考试模式
function startPreviewExam() {
  if (!canStartPaperExam.value) {
    toast.warning('试卷题量与配置不一致，请重新生成或调整题型数量')
    return
  }
  startExam(paperPreview.value, paperForm.title)
}

// 启动考试模式（初始化答题状态、开始计时）
function startExam(paper: Question[], title: string) {
  examTitle.value = title
  examPaper.value = paper
  examAnswers.value = {}
  examReview.value = {}
  paper.forEach((q) => {
    examAnswers.value[q.id] = ''
    examReview.value[q.id] = null
  })
  examSubmitted.value = false
  examReviewing.value = false
  examSubmitNoticeVisible.value = false
  examCorrectCount.value = 0
  currentExamIndex.value = -1
  activeAnalysisQuestionId.value = null
  analysisReturnQuestionIndex.value = 0
  examTime.value = 0
  viewMode.value = 'exam'
  startExamTimer()
  void nextTick(() => {
    scrollQuestionBankViewportToTop()
  })
}

// 启动考试计时器（每秒 +1）
function startExamTimer() {
  stopExamTimer()
  examTimer = window.setInterval(() => {
    if (!examSubmitted.value) examTime.value += 1
  }, 1000)
}

// 停止考试计时器
function stopExamTimer() {
  if (examTimer) {
    window.clearInterval(examTimer)
    examTimer = null
  }
}

// 处理退出考试（已提交直接返回，未提交弹出确认）
function handleExamExit() {
  if (examReviewing.value) return

  if (examSubmitted.value) {
    backWorkspace()
    return
  }

  if (window.confirm('当前试卷尚未提交，退出考试会丢失本次作答进度，确定退出吗？')) {
    backWorkspace()
  }
}

// 请求交卷（先显示未答提示，确认后提交）
function requestSubmitExam() {
  if (examSubmitted.value || examReviewing.value) return

  if (examUnansweredCount.value > 0 && !examSubmitNoticeVisible.value) {
    examSubmitNoticeVisible.value = true
    return
  }

  void submitExam()
}

function cancelSubmitExam() {
  examSubmitNoticeVisible.value = false
}

// 执行交卷：判客观题 + AI 评阅主观题 + 提交记录
async function submitExam() {
  if (examSubmitted.value || examReviewing.value) return

  examSubmitNoticeVisible.value = false
  examReviewing.value = true
  stopExamTimer()

  try {
    let correctCount = 0
    const batchResults: Array<Record<string, unknown>> = []

    examPaper.value.forEach((q) => {
      if (!requiresAiReview(q.type)) {
        const isCorrect = evaluateAnswer(q, examAnswers.value[q.id])
        if (isCorrect) correctCount += 1

        batchResults.push({
          question_id: q.id,
          user_answer: formatUserAnswer(examAnswers.value[q.id]),
          is_correct: isCorrect,
          score: isCorrect ? 100 : 0,
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
      .filter((q) => requiresAiReview(q.type))
      .map(async (q) => {
        const result = await gradeQuestion(q, examAnswers.value[q.id])
        examReview.value[q.id] = result.review
        const correct = result.correct
        if (correct) correctCount += 1

        batchResults.push({
          question_id: q.id,
          user_answer: formatUserAnswer(examAnswers.value[q.id]),
          is_correct: correct,
          score: result.review?.score,
          subject: q.subject,
          question_type: q.type,
          content: q.content,
          options: q.options || {},
          answer: q.answer,
          analysis: q.analysis,
        })
      })

    await Promise.all(subjectiveTasks)

    if (batchResults.length > 0) await submitObjectiveResults({ results: batchResults as any[] })

    // 提交接口成功即视为交卷完成；历史和错题本刷新失败不应回滚考试页面状态。
    examCorrectCount.value = correctCount
    examSubmitted.value = true
    saveAttempt(examPaper.value.length, correctCount)

    if (examTitle.value === '每日一题') {
      markDailyCompleted(new Date())

      const lastStreak = Number(localStorage.getItem('question_hub_streak') || '3')
      localStorage.setItem('question_hub_streak', String(lastStreak + 1))

      dailyStateSeed.value += 1
      localStatsSeed.value += 1
    } else if (examPaper.value.length > 0) {
      const pct = Math.round((correctCount / examPaper.value.length) * 100)
      localStorage.setItem('question_hub_last_mock', String(pct))

      if (activeModule.value === 'paper') {
        const prevCount = Number(localStorage.getItem('question_hub_mock_exams_count') || '0')
        const newCount = prevCount + 1
        localStorage.setItem('question_hub_mock_exams_count', String(newCount))
        mockExamsCount.value = newCount
      }
    }

    // 后置刷新与交卷结果解耦，避免网络抖动造成“后端已保存、前端仍显示提交失败”。
    void Promise.allSettled([loadAnswerHistory(), loadWrongBook()]).then((refreshResults) => {
      if (refreshResults.some((result) => result.status === 'rejected')) {
        toast.warning('试卷已提交，答题记录将在下次进入时刷新')
      }
    })
  } catch (error) {
    toast.error(getErrorMessage(error) || '交卷失败，请稍后重试')
    startExamTimer()
  } finally {
    examReviewing.value = false
  }
}

// 打开分析题评阅详情页面
function openAnalysisReview(questionId: string) {
  if (!examSubmitted.value) return

  const questionIndex = examPaper.value.findIndex((question) => question.id === questionId)
  const question = examPaper.value[questionIndex]
  if (!question || question.type !== '分析题') return

  analysisReturnQuestionIndex.value = questionIndex
  activeAnalysisQuestionId.value = questionId
  viewMode.value = 'analysis-review'
  void nextTick(() => scrollQuestionBankViewportToTop())
}

// 关闭分析题评阅，返回答题位置
function closeAnalysisReview() {
  const returnIndex = analysisReturnQuestionIndex.value
  viewMode.value = 'exam'
  activeAnalysisQuestionId.value = null

  void nextTick(() => {
    scrollToQuestion(returnIndex)
  })
}

// 切换到上一道分析题评阅
function showPreviousAnalysisReview() {
  const previous = analysisQuestions.value[activeAnalysisQuestionIndex.value - 1]
  if (!previous) return

  activeAnalysisQuestionId.value = previous.id
  analysisReturnQuestionIndex.value = examPaper.value.findIndex((question) => question.id === previous.id)
  void nextTick(() => scrollQuestionBankViewportToTop())
}

// 切换到下一道分析题评阅
function showNextAnalysisReview() {
  const next = analysisQuestions.value[activeAnalysisQuestionIndex.value + 1]
  if (!next) return

  activeAnalysisQuestionId.value = next.id
  analysisReturnQuestionIndex.value = examPaper.value.findIndex((question) => question.id === next.id)
  void nextTick(() => scrollQuestionBankViewportToTop())
}

// 返回工作台首页
function backWorkspace() {
  stopExamTimer()
  examReviewing.value = false
  activeAnalysisQuestionId.value = null
  viewMode.value = 'workspace'
  activeModule.value = 'daily'
  triggerChartAnimations()
  refreshDailySelections()
  void loadQuestionBank()
  void loadWrongBook()
  void nextTick(() => {
    scrollQuestionBankViewportToTop()
  })
}

// 选择考试选项
function selectExamOption(q: Question, key: string) {
  if (examSubmitted.value) return
  examAnswers.value[q.id] = updateOptionAnswer(q, examAnswers.value[q.id], key)
}

// 更新考试文本答案
function updateExamAnswer(id: string, value: string) {
  if (examSubmitted.value) return
  examAnswers.value[id] = value
}

// 仅填空题和分析题调用 AI，其余题型在前端精确判定。
async function gradeQuestion(question: Question, answer: AnswerValue) {
  if (!requiresAiReview(question.type)) return { correct: evaluateAnswer(question, answer), review: null }

  // 未作答的主观题直接记 0 分，避免空答案仍发起耗时的 AI 评阅请求。
  if (!hasAnswerData(answer)) {
    return {
      correct: false,
      review: {
        score: 0,
        is_correct: false,
        feedback: '本题未作答',
        improvement_hints: ['请完成作答后再提交'],
      },
    }
  }

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
    return {
      correct,
      review: {
        score: correct ? 100 : 0,
        is_correct: correct,
        feedback: correct ? 'Correct' : 'Review needed',
        improvement_hints: [],
      },
    }
  }
}

// 提交单题作答；后端统一保存历史，并仅在答错时维护错题本。
async function submitQuestionAttempt(question: Question, answer: AnswerValue, isCorrect: boolean, score?: number) {
  try {
    const response = await submitObjectiveResults({
      results: [
        {
          question_id: question.id,
          user_answer: formatUserAnswer(answer),
          is_correct: isCorrect,
          score,
          subject: question.subject,
          question_type: question.type,
          content: question.content,
          options: question.options || {},
          answer: question.answer,
          analysis: question.analysis,
        },
      ],
    })

    await loadAnswerHistory()
    if (!isCorrect && response.wrong_saved_count > 0) await loadWrongBook()
    return true
  } catch (error) {
    toast.error(getErrorMessage(error, '答题结果未同步，请稍后重试'))
    return false
  }
}

// 归档错题（标记已掌握）
async function archiveWrong(q: Question) {
  if (!q.wrong_id) return
  await archiveWrongQuestion(q.wrong_id)
  await loadWrongBook()
}

// 删除错题记录
async function removeWrong(q: Question) {
  if (!q.wrong_id) return
  await removeWrongQuestion(q.wrong_id)
  await loadWrongBook()
}

function subjectiveScoreClass(id: string, reviewMap: Record<string, QuizReviewResult | null>, correctMap: Record<string, boolean>) {
  const score = reviewMap[id]?.score
  if (score == null) return correctMap[id] ? 'success' : 'danger'
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

function subjectiveScoreText(id: string, reviewMap: Record<string, QuizReviewResult | null>, correctMap: Record<string, boolean>) {
  const score = reviewMap[id]?.score
  if (score == null) return correctMap[id] ? '回答正确' : '回答错误，已加入错题本'
  if (score >= 80) return '回答优秀'
  if (score >= 60) return '基本正确，部分不足'
  return '回答错误，已加入错题本'
}

// 评估答案是否正确（客观题精确匹配，主观题包容匹配）
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

function isOptionQuestion(q: Question) {
  return ['选择题', '单选题', '判断题'].includes(q.type)
}

function getOptions(q: Question) {
  return q.type === '判断题' ? { A: '正确', B: '错误' } : q.options || {}
}

function isSelected(ans: AnswerValue, key: string) {
  if (!ans) return false
  return Array.isArray(ans) ? ans.includes(key) : ans === key
}

function updateOptionAnswer(_q: Question, _ans: AnswerValue, key: string) {
  return key
}

function correctKeys(q: Question) {
  let ansText = String(q.answer || '').trim()

  if (q.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确'].some((item) => upper.includes(item))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误'].some((item) => upper.includes(item))) ansText = 'B'
  }

  return ansText
      .split(/[、,，\s]+/)
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean)
}

function isCorrectOption(q: Question, key: string) {
  return correctKeys(q).includes(key)
}

function normalizeAnswer(ans: AnswerValue): string[] {
  if (Array.isArray(ans)) {
    return ans.map((item) => String(item).trim().toUpperCase()).filter(Boolean)
  }

  return String(ans || '')
      .split(/[、,，\s]+/)
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean)
}

function hasAnswerData(ans: AnswerValue) {
  return normalizeAnswer(ans).length > 0
}

function formatAnswer(ans: string) {
  return String(ans || '').replace(/,/g, '、')
}

function formatUserAnswer(ans: AnswerValue) {
  return Array.isArray(ans) ? ans.join(',') : String(ans || '')
}

// Fisher-Yates 洗牌算法
function shuffle<T>(array: T[]): T[] {
  const result = [...array]

  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const temp = result[i] as T
    result[i] = result[j] as T
    result[j] = temp
  }

  return result
}

function uniqueKeepOrder(items: string[]) {
  return Array.from(new Set(items.filter(Boolean)))
}

// 从 localStorage 读取答题统计数据
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

// 保存答题记录到 localStorage 并触发图表动画
function saveAttempt(attempted: number, correct: number) {
  stats.totalAttempted += attempted
  stats.totalCorrect += correct
  localStorage.setItem(
      'question_hub_stats',
      JSON.stringify({
        totalAttempted: stats.totalAttempted,
        totalCorrect: stats.totalCorrect,
      }),
  )
  localStatsSeed.value += 1
  triggerChartAnimations()
}

function readDailyCompletionMap(): Record<string, boolean> {
  const next: Record<string, boolean> = {}

  try {
    const raw = localStorage.getItem('question_hub_daily_completion_map')
    if (raw) {
      const parsed = JSON.parse(raw) as Record<string, unknown>
      Object.entries(parsed).forEach(([key, value]) => {
        if (value === true) next[key] = true
      })
    }
  } catch {
    // ignore invalid local cache
  }

  const legacyKey = 'daily_completed_' + new Date().toDateString()
  if (localStorage.getItem(legacyKey) === 'true') {
    next[formatDateKey(new Date())] = true
  }

  return next
}

function writeDailyCompletionMap(map: Record<string, boolean>) {
  localStorage.setItem('question_hub_daily_completion_map', JSON.stringify(map))
}

function markDailyCompleted(date: Date) {
  const key = formatDateKey(date)
  const map = readDailyCompletionMap()
  map[key] = true
  writeDailyCompletionMap(map)
  localStorage.setItem('daily_completed_' + date.toDateString(), 'true')
}

function readBankSubmissionMap(): Record<string, { correct: boolean }> {
  try {
    return JSON.parse(localStorage.getItem(`question_hub_bank_submitted_${formatDateKey(new Date())}`) || '{}')
  } catch {
    return {}
  }
}

function writeBankSubmissionMap(map: Record<string, { correct: boolean }>) {
  localStorage.setItem(`question_hub_bank_submitted_${formatDateKey(new Date())}`, JSON.stringify(map))
}

function syncBankSubmissionStateForToday() {
  const saved = readBankSubmissionMap()
  const nextSubmitted: Record<string, boolean> = {}
  const nextCorrect: Record<string, boolean> = {}

  Object.entries(saved).forEach(([id, value]) => {
    nextSubmitted[id] = true
    nextCorrect[id] = value.correct === true
  })

  bankSubmitted.value = nextSubmitted
  bankCorrect.value = nextCorrect
}

function markBankQuestionSubmittedToday(id: string, correct: boolean) {
  const saved = readBankSubmissionMap()
  saved[id] = { correct }
  writeBankSubmissionMap(saved)
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

function formatDateKey(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function scrollQuestionBankViewportToTop() {
  window.scrollTo({ top: 0, behavior: 'auto' })

  const pageContent = document.querySelector('.page-content')
  if (pageContent instanceof HTMLElement) {
    pageContent.scrollTo({ top: 0, behavior: 'auto' })
  }
}
</script>

<style scoped>
.question-bank-layout {
  min-height: calc(100vh - var(--navbar-height, 72px));
  padding: 0;
  box-sizing: border-box;
  color: #172033;
  background:
      radial-gradient(circle at 28% 8%, rgba(94, 234, 212, 0.16), transparent 28%),
      radial-gradient(circle at 70% 18%, rgba(147, 197, 253, 0.18), transparent 30%),
      linear-gradient(180deg, #f8fbff 0%, #f7f8fc 52%, #fbfcff 100%);
  font-family:
      Inter,
      ui-sans-serif,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      "Microsoft YaHei",
      sans-serif;
}

.question-bank-workspace {
  width: 100%;
  margin: 0;
}

.exam-workspace {
  width: min(1480px, calc(100% - 56px));
  margin: 28px auto 36px;
}

.bank-shell {
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr) 300px;
  gap: 0;
  min-height: calc(100vh - var(--navbar-height, 72px));
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
  overflow: visible;
}

.bank-left-rail {
  position: sticky;
  top: 0;
  align-self: start;
  min-height: calc(100vh - var(--navbar-height, 72px));
  max-height: calc(100vh - var(--navbar-height, 72px));
  overflow-y: auto;
  padding: 24px 12px 28px 20px;
  border-right: 1px solid rgba(226, 232, 240, 0.82);
  background: rgba(255, 255, 255, 0.7);
  scrollbar-width: thin;
}

.rail-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding: 0 4px;
}

.rail-brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background:
      linear-gradient(135deg, #67e8f9, #8bdbb6),
      #8bdbb6;
  color: #075f57;
  box-shadow: none;
  flex-shrink: 0;
}

.rail-brand strong {
  display: block;
  color: #172033;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.2;
}

.rail-brand span {
  display: block;
  margin-top: 2px;
  color: #a5adbb;
  font-size: 10px;
  font-weight: 600;
}

.rail-menu {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rail-menu-item {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  width: 100%;
  min-height: 58px;
  padding: 8px 10px 8px 4px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #516071;
  text-align: left;
  cursor: pointer;
  transition:
      background 160ms ease,
      border-color 160ms ease,
      transform 160ms ease,
      color 160ms ease;
}

.rail-menu-item:hover {
  background: rgba(235, 242, 244, 0.72);
  transform: none;
}

.rail-menu-item.active {
  border-color: transparent;
  background: rgba(209, 250, 229, 0.42);
  color: #0f6b55;
}

.rail-menu-item.active::before {
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 0;
  width: 3px;
  border-radius: 3px;
  background: #2fc68f;
  content: '';
}

.rail-menu-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: transparent;
  color: #6f7d90;
  flex-shrink: 0;
}

.rail-menu-item.active .rail-menu-icon {
  background: rgba(47, 198, 143, 0.14);
  color: #168165;
}

.rail-menu-copy {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.rail-menu-item strong,
.rail-menu-item small {
  display: block;
}

.rail-menu-item strong {
  color: #334155;
  font-size: 14px;
  font-weight: 800;
}

.rail-menu-item.active strong {
  color: #0f6b55;
}

.rail-menu-item small {
  margin-top: 2px;
  font-size: 11px;
  font-weight: 600;
  color: #94a0b2;
}

.rail-menu-item.active small {
  color: rgba(19, 111, 96, 0.72);
}

.rail-empty {
  margin-top: 14px;
  color: #9aa4b5;
  font-size: 12px;
  line-height: 1.6;
}

.bank-main {
  min-width: 0;
  padding: 28px 32px 36px;
}

.portal-board,
.module-board {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.portal-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
  min-height: 126px;
  padding: 26px 30px;
  border: 1px solid rgba(226, 232, 240, 0.82);
  border-radius: 26px;
  background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(241, 253, 249, 0.88)),
      #fff;
  box-shadow: 0 18px 45px rgba(27, 42, 78, 0.07);
}

.hero-kicker,
.module-kicker {
  display: block;
  margin-bottom: 8px;
  color: #42b892;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.portal-hero h1 {
  margin: 0;
  color: #172033;
  font-size: 32px;
  font-weight: 900;
  letter-spacing: -0.04em;
  line-height: 1.14;
}

.portal-hero p {
  width: min(680px, 100%);
  margin: 10px 0 0;
  color: #6d7687;
  font-size: 14px;
  line-height: 1.7;
}

.portal-hero-metrics {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}

.accuracy-circle-container {
  position: relative;
  width: 74px;
  height: 74px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-ring {
  transform: rotate(-90deg);
}

.circle-bg {
  fill: none;
  stroke: #e8edf3;
  stroke-width: 8px;
}

.circle-progress {
  fill: none;
  stroke: #42c99a;
  stroke-width: 8px;
  stroke-linecap: round;
}

.circle-content {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.circle-content .pct {
  color: #172033;
  font-size: 16px;
  font-weight: 900;
  line-height: 1;
}

.circle-content .lbl {
  margin-top: 2px;
  color: #8a94a7;
  font-size: 10px;
  font-weight: 800;
}

.hero-stat {
  min-width: 72px;
}

.hero-stat span {
  display: block;
  margin-bottom: 4px;
  color: #8a94a7;
  font-size: 12px;
  font-weight: 700;
}

.hero-stat strong {
  color: #172033;
  font-size: 24px;
  font-weight: 900;
}

.hero-stat strong.danger {
  color: #e05252;
}

.feature-card-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  border-top: none;
}

.feature-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  min-height: 132px;
  padding: 18px 18px 20px;
  border: none;
  border-radius: 16px;
  background: #fff;
  color: #172033;
  text-align: left;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(27, 42, 78, 0.06);
  transition:
      transform 180ms ease,
      box-shadow 180ms ease,
      color 180ms ease;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 34px rgba(27, 42, 78, 0.08);
}

.feature-card.black {
  background: radial-gradient(circle at 88% 15%, rgba(255, 255, 255, 0.16), transparent 22%), #111;
  color: #fff;
}

.feature-card.green {
  background: linear-gradient(135deg, #dcff9f 0%, #91ebc6 100%);
  color: #153b2d;
}

.feature-card.blue {
  background: linear-gradient(135deg, #9ef1c9 0%, #96d6f8 100%);
  color: #14364a;
}

.feature-card-kicker {
  display: block;
  color: currentColor;
  opacity: 0.78;
  font-size: 12px;
  font-weight: 800;
}

.feature-card strong {
  display: block;
  margin-top: 10px;
  font-size: 18px;
  font-weight: 900;
}

.feature-card small {
  display: block;
  margin-top: 5px;
  font-size: 13px;
  font-weight: 700;
  opacity: 0.7;
  color: currentColor;
}

.feature-card i {
  position: absolute;
  right: 18px;
  bottom: 18px;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.24);
}

.feature-card i::before {
  content: "";
  position: absolute;
  inset: 15px 13px 13px 16px;
  border-top: 2px solid currentColor;
  border-right: 2px solid currentColor;
  transform: rotate(45deg);
  opacity: 0.75;
}

.subject-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.78);
  overflow-x: auto;
}

.subject-strip strong {
  flex-shrink: 0;
  margin-right: 4px;
  color: #172033;
  font-size: 16px;
  font-weight: 900;
}

.subject-chip {
  flex-shrink: 0;
  min-height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: 999px;
  background: #f1f3f5;
  color: #5f6b7c;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition:
      background 160ms ease,
      color 160ms ease,
      transform 160ms ease;
}

.subject-chip:hover {
  transform: translateY(-1px);
  background: #e7f7f1;
  color: #17856d;
}

.subject-chip.active {
  background: #42c99a;
  color: #fff;
}

.subject-chip.muted {
  background: transparent;
}

.section-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 4px 0 2px;
}

.section-toolbar h2 {
  margin: 0;
  color: #172033;
  font-size: 24px;
  font-weight: 900;
  letter-spacing: -0.03em;
}

.section-toolbar p {
  margin: 6px 0 0;
  color: #7c8798;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.primary-action,
.soft-action,
.btn-primary,
.btn-secondary,
.btn-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  transition:
      transform 150ms ease,
      box-shadow 150ms ease,
      border-color 150ms ease,
      background 150ms ease,
      color 150ms ease;
}

.primary-action,
.btn-primary {
  border: 1px solid #42c99a;
  background: #42c99a;
  color: #fff;
  box-shadow: 0 10px 20px rgba(66, 201, 154, 0.2);
}

.primary-action:hover,
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 24px rgba(66, 201, 154, 0.26);
}

.soft-action,
.btn-secondary,
.btn-text {
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: #fff;
  color: #4f5b6d;
}

.soft-action:hover,
.btn-secondary:hover,
.btn-text:hover {
  border-color: rgba(66, 201, 154, 0.36);
  color: #17856d;
}

.recommend-question-card {
  padding: 8px 0 0;
  border-top: 1px solid rgba(226, 232, 240, 0.86);
  border-bottom: 1px solid rgba(226, 232, 240, 0.86);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.question-card-top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
  padding: 0 0 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.72);
}

.question-index {
  margin-right: 6px;
  color: #172033;
  font-size: 18px;
  font-weight: 900;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.warning {
  background: #fef9c3;
  color: #854d0e;
}

.status-pill.danger {
  background: #fee2e2;
  color: #991b1b;
}

.tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: #eef6ff;
  color: #3d78b5;
  font-size: 12px;
  font-weight: 800;
}

.subject-tag {
  background: #eef6ff;
  color: #3d78b5;
}

.type-tag {
  background: #eff6f2;
  color: #288a6e;
}

.difficulty-tag {
  background: #dff2ff;
  color: #3487c7;
}

.done-tag {
  background: #e8f5e9;
  color: #2e7d32;
}

.recommend-question-content {
  color: #273142;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.82;
}

.recommend-options {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-top: 18px;
}

.recommend-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 14px 0;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-width: 0 0 1px;
  border-radius: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.recommend-option span {
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: #e7f7f1;
  color: #17856d;
  font-size: 12px;
  font-weight: 900;
  flex-shrink: 0;
}

.recommend-option p {
  margin: 0;
  color: #4f5b6d;
  font-size: 14px;
  line-height: 1.55;
  flex: 1;
  text-align: left;
}

.recommend-option.selected {
  border-color: rgba(15, 23, 42, 0.35);
}

.recommend-option.correct {
  border-color: rgba(16, 185, 129, 0.45);
  background: rgba(236, 253, 245, 0.7);
}

.recommend-option.wrong {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(254, 242, 242, 0.7);
}

.portal-answer-box {
  width: 100%;
  margin-top: 18px;
  padding: 12px 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  resize: vertical;
  box-sizing: border-box;
}

.portal-question-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 18px;
}

.question-card-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 0;
  padding: 0;
  border-top: none;
}

.question-card-actions .inline {
  min-height: 40px;
  padding: 0 16px;
}

.portal-analysis-box {
  margin-top: 18px;
  padding: 16px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 20px;
  border: 1px dashed rgba(148, 163, 184, 0.46);
  border-radius: 18px;
  background: #f8fafc;
}

.empty-state strong {
  color: #172033;
  font-size: 16px;
}

.empty-state p {
  margin: 0 0 10px;
  color: #6d7687;
  font-size: 13px;
}

.module-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 0 0 18px;
  border: none;
  border-bottom: 1px solid rgba(226, 232, 240, 0.86);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.module-header-left {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  min-width: 0;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 13px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 999px;
  background: #fff;
  color: #5f6b7c;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
  flex-shrink: 0;
}

.module-header h2 {
  margin: 0;
  color: #172033;
  font-size: 25px;
  font-weight: 900;
  letter-spacing: -0.03em;
}

.module-header p {
  margin: 7px 0 0;
  color: #7c8798;
  font-size: 13px;
  line-height: 1.55;
}

.module-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.module-stat {
  min-width: 92px;
  padding: 0 0 0 14px;
  border: none;
  border-left: 1px solid rgba(226, 232, 240, 0.86);
  border-radius: 0;
  background: transparent;
  text-align: right;
}

.module-stat span {
  display: block;
  color: #8a94a7;
  font-size: 11px;
  font-weight: 800;
}

.module-stat strong {
  display: block;
  margin-top: 3px;
  color: #172033;
  font-size: 15px;
  font-weight: 900;
}

.module-stat strong.success {
  color: #18a77c;
}

.module-stat strong.warning {
  color: #e09b2d;
}

.module-stat strong.danger {
  color: #e05252;
}

.module-content-card {
  min-width: 0;
  padding: 6px 0 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.module-board.theme-daily {
  --module-color: #42c99a;
  --module-soft: rgba(66, 201, 154, 0.1);
}

.module-board.theme-practice {
  --module-color: #4b8ef7;
  --module-soft: rgba(75, 142, 247, 0.1);
}

.module-board.theme-search {
  --module-color: #42c99a;
  --module-soft: rgba(66, 201, 154, 0.1);
}

.module-board.theme-paper {
  --module-color: #efae45;
  --module-soft: rgba(239, 174, 69, 0.12);
}

.module-board.theme-wrong {
  --module-color: #e05252;
  --module-soft: rgba(224, 82, 82, 0.1);
}

.module-board .btn-back:hover {
  border-color: color-mix(in srgb, var(--module-color), transparent 60%);
  color: var(--module-color);
}

.module-board :deep(.btn-primary) {
  border-color: var(--module-color) !important;
  background: var(--module-color) !important;
  color: #fff !important;
}

.module-board :deep(.btn-secondary:hover),
.module-board :deep(.btn-ghost:hover),
.module-board :deep(.btn-link) {
  color: var(--module-color) !important;
  border-color: color-mix(in srgb, var(--module-color), transparent 62%) !important;
}

.module-board :deep(input),
.module-board :deep(select),
.module-board :deep(textarea) {
  border-radius: 10px !important;
}

.module-board :deep(input:focus),
.module-board :deep(select:focus),
.module-board :deep(textarea:focus) {
  border-color: var(--module-color) !important;
  box-shadow: 0 0 0 4px var(--module-soft) !important;
}

.module-board :deep(.option-btn.selected) {
  border-color: var(--module-color) !important;
  background: var(--module-soft) !important;
}

.module-board :deep(.tag.type),
.module-board :deep(.page-btn.active) {
  border-color: var(--module-color) !important;
  background: var(--module-color) !important;
  color: #fff !important;
}

.module-content-card :deep(.section-card),
.module-content-card :deep(.question-card),
.module-content-card :deep(.tab-card),
.module-content-card :deep(.practice-card),
.module-content-card :deep(.filter-panel),
.module-content-card :deep(.preview-card),
.module-content-card :deep(.wrong-card),
.module-content-card :deep(.daily-question-block),
.module-content-card :deep(.daily-empty),
.module-content-card :deep(.practice-section),
.module-content-card :deep(.question-item),
.module-content-card :deep(.workspace-pane),
.module-content-card :deep(.preview-item),
.module-content-card :deep(.drill-card),
.module-content-card :deep(.wrong-item) {
  border: none !important;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.module-content-card :deep(.question-text),
.module-content-card :deep(.question-content) {
  color: #273142 !important;
  font-size: 16px !important;
  line-height: 1.75 !important;
}

.module-content-card :deep(.daily-tab-shell),
.module-content-card :deep(.practice-shell),
.module-content-card :deep(.search-shell),
.module-content-card :deep(.exam-shell),
.module-content-card :deep(.wrong-shell) {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.module-content-card :deep(.question-item),
.module-content-card :deep(.preview-item),
.module-content-card :deep(.wrong-item),
.module-content-card :deep(.daily-question-block),
.module-content-card :deep(.drill-card) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.module-content-card :deep(.search-shell .question-item) {
  padding-left: 24px !important;
  padding-right: 24px !important;
}

.module-content-card :deep(.practice-section),
.module-content-card :deep(.workspace-pane),
.module-content-card :deep(.list-section),
.module-content-card :deep(.drill-section) {
  padding: 0 0 20px !important;
}

.module-content-card :deep(.practice-section + .practice-section),
.module-content-card :deep(.workspace-pane + .workspace-pane),
.module-content-card :deep(.drill-section + .list-section) {
  margin-top: 22px !important;
}

.module-content-card :deep(.toolbar),
.module-content-card :deep(.filter-row),
.module-content-card :deep(.custom-form),
.module-content-card :deep(.config-form),
.module-content-card :deep(.counts-section) {
  border-radius: 0 !important;
  box-shadow: none !important;
}

.module-content-card :deep(.summary-item),
.module-content-card :deep(.count-row),
.module-content-card :deep(.wrong-analysis),
.module-content-card :deep(.analysis-box),
.module-content-card :deep(.drill-result),
.module-content-card :deep(.preview-empty),
.module-content-card :deep(.simple-empty),
.module-content-card :deep(.state-block) {
  border-radius: 10px !important;
  box-shadow: none !important;
}

.module-content-card :deep(.question-list),
.module-content-card :deep(.wrong-list),
.module-content-card :deep(.preview-list) {
  display: flex;
  flex-direction: column;
  gap: 0 !important;
}

.module-content-card :deep(.question-item + .question-item),
.module-content-card :deep(.wrong-item + .wrong-item),
.module-content-card :deep(.preview-item + .preview-item) {
  margin-top: 0 !important;
}

.module-content-card :deep(.daily-question-block .action-row),
.module-content-card :deep(.question-foot),
.module-content-card :deep(.wrong-actions),
.module-content-card :deep(.action-row) {
  border-top: 1px solid rgba(226, 232, 240, 0.72);
  padding-top: 16px;
}

.module-content-card :deep(.search-shell) {
  gap: 16px !important;
}

.module-content-card :deep(.search-shell .question-foot) {
  border-top: none !important;
  padding-top: 0 !important;
}

.module-content-card :deep(.search-shell .toolbar) {
  gap: 12px !important;
}

.module-content-card :deep(.search-shell .pagination-row) {
  margin-top: 28px !important;
}

.bank-right-panel {
  position: sticky;
  top: 16px;
  align-self: start;
  max-height: calc(100vh - var(--navbar-height, 72px) - 32px);
  overflow-y: auto;
  padding: 24px 18px 28px;
  border-left: 1px solid rgba(226, 232, 240, 0.82);
  background: rgba(255, 255, 255, 0.7);
  scrollbar-width: thin;
}

.right-card {
  padding: 18px;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 12px 28px rgba(27, 42, 78, 0.06),
      inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.right-card + .right-card {
  margin-top: 18px;
}

.right-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.right-card-header strong {
  color: #172033;
  font-size: 14px;
  font-weight: 900;
}

.right-card-header span {
  color: #5f6b7c;
  font-size: 12px;
  font-weight: 800;
}

.calendar-week,
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.calendar-grid {
  row-gap: 4px;
}

.calendar-week span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  color: #8a94a7;
  font-size: 11px;
  font-weight: 800;
}

.calendar-day {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  border-radius: 999px;
  color: #4f5b6d;
  font-size: 12px;
  font-weight: 800;
  background: rgba(248, 250, 252, 0.9);
}

.calendar-day.muted {
  color: #c7cdd8;
  background: transparent;
}

.calendar-day.today {
  background: #42c99a;
  color: #fff;
  box-shadow: 0 8px 18px rgba(66, 201, 154, 0.22);
}

.calendar-day.completed::after {
  content: "";
  width: 5px;
  height: 5px;
  margin-left: 3px;
  border-radius: 50%;
  background: #fff;
}

.right-label {
  display: block;
  margin-bottom: 10px;
  color: #172033;
  font-size: 13px;
  font-weight: 900;
}

.right-input {
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  border-radius: 12px;
  background: #fff;
  color: #172033;
  font: inherit;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition:
      border-color 150ms ease,
      box-shadow 150ms ease;
}

.right-input:focus {
  border-color: rgba(66, 201, 154, 0.56);
  box-shadow: 0 0 0 4px rgba(66, 201, 154, 0.1);
}

.difficulty-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.difficulty-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 12px;
  background: #fff;
  color: #3d4656;
  text-align: left;
  cursor: pointer;
  transition:
      border-color 150ms ease,
      background 150ms ease,
      color 150ms ease;
}

.difficulty-row span {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  background: #d7eef1;
  box-shadow: inset 0 0 0 4px #eefafa;
}

.difficulty-row:nth-child(2) span {
  background: #8ed0ff;
}

.difficulty-row:nth-child(3) span {
  background: #ffc36a;
}

.difficulty-row strong {
  font-size: 13px;
  font-weight: 900;
}

.difficulty-row.active {
  border-color: rgba(66, 201, 154, 0.42);
  background: linear-gradient(135deg, rgba(209, 250, 229, 0.72), rgba(239, 246, 255, 0.78));
  color: #136f60;
}

.summary-card {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.summary-card div {
  padding: 12px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.96);
}

.summary-card span {
  display: block;
  color: #8a94a7;
  font-size: 11px;
  font-weight: 800;
}

.summary-card strong {
  display: block;
  margin-top: 4px;
  color: #172033;
  font-size: 22px;
  font-weight: 900;
}

.get-question-btn {
  width: 100%;
  height: 54px;
  margin-top: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1px solid #0f172a;
  border-radius: 12px;
  background: #0f172a;
  color: #fff;
  font-size: 15px;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.18);
  transition:
      transform 160ms ease,
      box-shadow 160ms ease,
      background 160ms ease,
      border-color 160ms ease;
}

.get-question-btn span {
  line-height: 1;
}

.get-question-btn i {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  position: relative;
  flex-shrink: 0;
}

.get-question-btn i::before {
  content: "";
  position: absolute;
  left: 5px;
  top: 4px;
  width: 6px;
  height: 6px;
  border-top: 2px solid #ffffff;
  border-right: 2px solid #ffffff;
  transform: rotate(45deg);
}

.get-question-btn:hover {
  transform: translateY(-2px);
  background: #1e293b;
  border-color: #1e293b;
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.24);
}

.get-question-btn:active {
  transform: translateY(0);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18);
}

.daily-preview-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.daily-preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.daily-preview-content {
  color: #172033;
  font-size: 14px;
  line-height: 1.7;
  padding: 2px 0 4px;
}

.daily-preview-empty {
  margin: 0;
  color: #7c8798;
  font-size: 13px;
  line-height: 1.7;
}

.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.22s ease;
}

.fade-scale-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-scale-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

:deep(code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #0f766e;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.92em;
}

@media (max-width: 1240px) {
  .bank-shell {
    grid-template-columns: 190px minmax(0, 1fr);
  }

  .bank-right-panel {
    display: none;
  }
}

@media (max-width: 960px) {
  .question-bank-layout {
    padding: 16px;
  }

  .bank-shell {
    grid-template-columns: 1fr;
  }

  .bank-left-rail {
    position: static;
    top: auto;
    align-self: stretch;
    min-height: 0;
    max-height: none;
    overflow: visible;
    border-right: none;
    border-bottom: 1px solid rgba(226, 232, 240, 0.82);
  }

  .bank-right-panel {
    position: static;
    top: auto;
    align-self: stretch;
    max-height: none;
    overflow: visible;
  }

  .rail-menu {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .bank-main {
    padding: 0 18px 22px;
  }

  .module-header,
  .section-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .portal-hero-metrics {
    width: 100%;
    flex-wrap: wrap;
  }

  .feature-card-row {
    grid-template-columns: 1fr;
  }

  .feature-card {
    min-height: 120px;
  }

  .recommend-options {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .rail-menu {
    grid-template-columns: 1fr;
  }

  .recommend-question-card,
  .module-content-card {
    padding: 20px;
    border-radius: 10px;
  }

  .toolbar-actions,
  .question-card-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .primary-action,
  .soft-action,
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .module-stat {
    min-width: 0;
    width: 100%;
    padding-left: 0;
    border-left: none;
    border-top: 1px solid rgba(226, 232, 240, 0.86);
    padding-top: 10px;
    text-align: left;
  }
}

</style>
