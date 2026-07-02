<template>
  <div class="question-bank-layout">
    <div v-if="viewMode === 'workspace'" class="question-bank-workspace">
      <section class="bank-shell">
        <!-- 左侧题单侧栏 -->
        <aside class="bank-left-rail">
          <div class="rail-brand">
            <div class="rail-brand-icon"></div>
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
              <span class="rail-menu-mark">{{ item.mark }}</span>
              <span>
                <strong>{{ item.label }}</strong>
                <small>{{ item.desc }}</small>
              </span>
            </button>
          </nav>

          <div class="rail-card">
            <div class="rail-card-title">
              <span>我的题单</span>
              <button type="button" @click="switchModule('wrong')">+</button>
            </div>

            <div v-if="visibleWrongSnippets.length" class="rail-question-list">
              <button
                  v-for="item in visibleWrongSnippets"
                  :key="item.id"
                  type="button"
                  class="rail-question"
                  @click="switchModule('wrong')"
              >
                <span>{{ item.subject || '综合' }}</span>
                <p>{{ item.content }}</p>
              </button>
            </div>

            <div v-else class="rail-empty">
              暂无错题，完成练习后会自动沉淀到这里。
            </div>
          </div>
        </aside>

        <!-- 中间主区域 -->
        <main class="bank-main">
          <transition name="fade-scale" mode="out-in">
            <!-- 首页控制台 -->
            <div v-if="activeModule === 'portal'" key="portal" class="portal-board">
<!--              <section class="portal-hero">-->
<!--                <div class="portal-hero-left">-->
<!--                  <span class="hero-kicker">Personalized Practice</span>-->
<!--                  <h1>个性化练习题库</h1>-->
<!--                  <p>基于你的课程、错题和练习记录，组织每日练习、智能刷题、模拟组卷与错题复习。</p>-->
<!--                </div>-->

<!--                <div class="portal-hero-metrics">-->
<!--                  <div class="accuracy-circle-container">-->
<!--                    <svg class="progress-ring" width="74" height="74" viewBox="0 0 100 100">-->
<!--                      <circle cx="50" cy="50" r="42" class="circle-bg" />-->
<!--                      <circle cx="50" cy="50" r="42" class="circle-progress" :style="circleProgressStyle" />-->
<!--                    </svg>-->
<!--                    <div class="circle-content">-->
<!--                      <span class="pct">{{ practiceAccuracy }}</span>-->
<!--                      <span class="lbl">正确率</span>-->
<!--                    </div>-->
<!--                  </div>-->

<!--                  <div class="hero-stat">-->
<!--                    <span>已练题数</span>-->
<!--                    <strong>{{ stats.totalAttempted }}</strong>-->
<!--                  </div>-->
<!--                  <div class="hero-stat">-->
<!--                    <span>待复习</span>-->
<!--                    <strong class="danger">{{ wrongTotal }}</strong>-->
<!--                  </div>-->
<!--                  <div class="hero-stat">-->
<!--                    <span>连续打卡</span>-->
<!--                    <strong>{{ localStreak }} 天</strong>-->
<!--                  </div>-->
<!--                </div>-->
<!--              </section>-->

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
                  <button type="button" class="soft-action" @click="pickDailyQuestion">换一题</button>
                  <button type="button" class="primary-action" @click="startSingleDailyQuestion">开始作答</button>
                </div>
              </section>

              <section class="recommend-question-card">
                <template v-if="dailyQuestion">
                  <div class="question-card-top">
                    <span class="question-index">1.</span>
                    <span class="tag">{{ dailyQuestion.subject }}</span>
                    <span class="tag soft">{{ dailyQuestion.type }}</span>
                    <span class="tag level">{{ dailyQuestion.difficulty || '中等' }}</span>
                  </div>

                  <div class="recommend-question-content" v-html="renderInline(dailyQuestion.content)"></div>

                  <div v-if="isOptionQuestion(dailyQuestion)" class="recommend-options">
                    <div v-for="(text, key) in getOptions(dailyQuestion)" :key="key" class="recommend-option">
                      <span>{{ key }}</span>
                      <p v-html="renderInline(text)"></p>
                    </div>
                  </div>

                  <div class="question-card-actions">
                    <button type="button" class="strong" @click="startSingleDailyQuestion">开始作答</button>
                    <button type="button" @click="switchModule('search')">进入全部题目</button>
                    <button type="button" @click="switchModule('wrong')">查看错题本</button>
                    <button type="button" @click="switchModule('daily')">进入练习</button>
                  </div>
                </template>

                <template v-else>
                  <div class="empty-state">
                    <strong>暂无可推荐题目</strong>
                    <p>题库接口返回为空时会显示此状态，请先导入题库数据或调整课程筛选。</p>
                    <button type="button" class="primary-action" @click="loadQuestionBank">重新加载题库</button>
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

                  <template v-else-if="activeModule === 'practice'">
                    <div class="module-stat">
                      <span>智能已练</span>
                      <strong>{{ stats.totalAttempted }} 题</strong>
                    </div>
                    <div class="module-stat">
                      <span>正确率</span>
                      <strong>{{ practiceAccuracy }}</strong>
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
                    :highlightQuestionId="highlightQuestionId"
                    :highlightVersion="highlightVersion"
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
              </section>
            </div>
          </transition>
        </main>

        <!-- 右侧信息面板 -->
        <aside class="bank-right-panel">
          <section class="right-card calendar-card">
            <div class="right-card-header">
              <strong>每日 1 题</strong>
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
              <button type="button" class="text-link-btn" @click="pickDailyChallengeQuestion">换一题</button>
            </div>

            <template v-if="dailyChallengeQuestion">
              <div class="daily-preview-tags">
                <span class="mini-tag">{{ dailyChallengeQuestion.subject }}</span>
                <span class="mini-tag">{{ dailyChallengeQuestion.type }}</span>
                <span class="mini-tag">{{ dailyChallengeQuestion.difficulty || '中等' }}</span>
              </div>
              <div class="daily-preview-content" v-html="renderInline(dailyChallengeQuestion.content)"></div>
              <button type="button" class="get-question-btn" @click="jumpToChallengeQuestion">作答</button>
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
    </div>

    <!-- 考试模式 -->
    <div v-else class="exam-workspace">
      <header class="exam-topbar">
        <div class="exam-topbar-left">
          <button class="btn-text" type="button" @click="quitExam">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m15 18-6-6 6-6" />
            </svg>
            退出考试
          </button>
          <h1 class="exam-title">{{ examTitle }}</h1>
        </div>

        <div class="exam-actions">
          <div class="timer-badge">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>{{ formattedExamTime }}</span>
          </div>
          <button v-if="!examSubmitted" class="btn-primary" type="button" @click="submitExam">交卷</button>
          <button v-else class="btn-secondary" type="button" @click="backWorkspace">返回题库</button>
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
                  type="button"
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

            <button v-if="!examSubmitted" class="btn-primary full-width sidebar-submit" type="button" @click="submitExam">
              交卷
            </button>
            <button v-else class="btn-secondary full-width sidebar-submit" type="button" @click="backWorkspace">
              完成查看
            </button>
          </div>
        </aside>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
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
import { getErrorMessage } from '@/shared/api/http'

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

interface CalendarCell {
  key: string
  label: number
  isCurrentMonth: boolean
  isToday: boolean
  isCompleted: boolean
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
const dailyChallengeQuestion = ref<Question | null>(null)

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
const highlightQuestionId = ref<string | null>(null)
const highlightVersion = ref(0)

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
const localStatsSeed = ref(0)
const dailyStateSeed = ref(0)

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

const weekLabels = ['日', '一', '二', '三', '四', '五', '六']

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

const moduleNavItems: Array<{ key: ModuleKey; label: string; desc: string; mark: string }> = [
  { key: 'portal', label: '控制台', desc: '刷题总览', mark: '01' },
  { key: 'daily', label: '每日练习', desc: '每日 1 题', mark: '02' },
  { key: 'practice', label: '智能练习', desc: '推荐训练', mark: '03' },
  { key: 'search', label: '全部题目', desc: '筛选检索', mark: '04' },
  { key: 'paper', label: '模拟组卷', desc: '考试模式', mark: '05' },
  { key: 'wrong', label: '错题本', desc: '薄弱复习', mark: '06' },
]

const portalCards = computed(() => [
  {
    key: 'daily' as ModuleKey,
    kicker: isDailyCompleted.value ? 'Completed' : 'Daily',
    title: '每日一题',
    subtitle: isDailyCompleted.value ? '今日训练已完成' : '完成今天的基础训练',
    accent: 'black',
  },
  {
    key: 'practice' as ModuleKey,
    kicker: 'Smart',
    title: `${recommendedSubject.value || '智能'}练习`,
    subtitle: '按薄弱点自动推荐练习',
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

const visibleWrongSnippets = computed(() => wrongQuestions.value.slice(0, 3))

const topSubjects = computed(() => {
  return learnerCourses.value
    .filter((course) => typeof course === 'string' && course.trim().length > 0)
    .slice(0, 5)
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

const animatedAccuracy = ref(0)
const radarAnimationScale = ref(0.1)

const calendarMonthLabel = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long' }).format(new Date())
})

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

const localStreak = computed(() => {
  localStatsSeed.value
  const streak = localStorage.getItem('question_hub_streak')
  if (!streak) {
    localStorage.setItem('question_hub_streak', '3')
    return 3
  }
  return Number(streak)
})

const isDailyCompleted = computed(() => {
  dailyStateSeed.value
  const todayKey = formatDateKey(new Date())
  const completionMap = readDailyCompletionMap()
  return completionMap[todayKey] === true
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

onMounted(() => {
  readLocalStats()

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
    const profileCourses = profile.data?.data?.student_profile?.courses
    learnerCourses.value = Array.isArray(profileCourses) ? profileCourses.map(String) : []
  } catch {
    learnerCourses.value = []
  }

  await loadPracticePool()
  await loadQuestionBank()
  await loadWrongBook()
  refreshDailySelections()
}

function switchModule(key: string) {
  activeModule.value = key as ModuleKey

  if (key === 'wrong') {
    void loadWrongBook()
    void pickWrongQuestion()
  } else if (key === 'search') {
    resetQuestionBankFilters()
    clearQuestionHighlight()
    void loadQuestionBank()
  } else if (key === 'daily') {
    pickDailyQuestion()
  }
}

function resetQuestionBankFilters() {
  bankFilters.query = ''
  bankFilters.subject = ''
  bankFilters.difficulty = ''
  bankFilters.type = ''
  bankPage.value = 1
}

function selectSubject(subject: string) {
  bankFilters.subject = bankFilters.subject === subject ? '' : subject
  activeModule.value = 'search'
  bankPage.value = 1
  void loadQuestionBank()
}

async function loadPracticePool() {
  try {
    const result = await fetchQuizBankQuestions({
      page: 1,
      page_size: 100,
    })

    practicePool.value = result.items || []
    totalQuestions.value = result.total || totalQuestions.value
    subjects.value = uniqueKeepOrder([...(result.subjects || []), ...subjects.value])
    difficulties.value = uniqueKeepOrder([...(result.difficulties || []), ...difficulties.value])
    types.value = uniqueKeepOrder([...(result.types || []), ...types.value])
  } catch (error) {
    practicePool.value = []
    toast.error(getErrorMessage(error, '加载练习池失败'))
  }
}

async function loadQuestionBank() {
  bankLoading.value = true
  try {
    const result = await fetchQuizBankQuestions({
      query: bankFilters.query || undefined,
      subject: bankFilters.subject || undefined,
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
  } catch (error) {
    toast.error(getErrorMessage(error, '加载题库失败'))
  } finally {
    bankLoading.value = false
  }
}

function searchBank() {
  bankPage.value = 1
  clearQuestionHighlight()
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
  const nextQuestion = pickQuestionExcluding(dailyChallengeQuestion.value ? [dailyChallengeQuestion.value.id] : [])
  dailyQuestion.value = nextQuestion
}

function pickDailyChallengeQuestion() {
  dailyChallengeQuestion.value = pickQuestionExcluding(dailyQuestion.value ? [dailyQuestion.value.id] : [])
}

function refreshDailySelections() {
  dailyQuestion.value = pickQuestionExcluding([])
  dailyChallengeQuestion.value = pickQuestionExcluding(dailyQuestion.value ? [dailyQuestion.value.id] : [])
}

function pickQuestionExcluding(excludedIds: string[]) {
  const source = practicePool.value.length ? practicePool.value : questions.value
  if (!source.length) return null

  const excluded = new Set(excludedIds)
  const available = source.filter((item) => !excluded.has(item.id))
  const pool = available.length ? available : source
  return pool[Math.floor(Math.random() * pool.length)] || null
}

function clearQuestionHighlight() {
  highlightQuestionId.value = null
}

async function jumpToChallengeQuestion() {
  if (!dailyChallengeQuestion.value) {
    toast.warning('暂无可跳转的每日挑战')
    return
  }

  const targetId = dailyChallengeQuestion.value.id
  const source = practicePool.value.length ? practicePool.value : questions.value
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
    toast.warning('暂无题目')
    return
  }

  startExam(selected, '推荐练习')
}

function startSingleDailyQuestion() {
  if (!dailyQuestion.value) {
    toast.warning('暂无每日一题')
    return
  }

  activeModule.value = 'daily'
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
      toast.warning('没有符合条件的题目')
      return
    }

    startExam(selected, '自定义练习')
  } catch {
    toast.error('生成练习失败')
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

async function generatePaperPreview() {
  const targetCount = paperTypeCounts.reduce((sum, item) => sum + Number(item.count || 0), 0)
  if (targetCount <= 0) return toast.warning('请至少选择 1 道题目')

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

    if (!selected.length) toast.warning('暂无题目')
    else toast.success(`已生成 ${selected.length} 道题目`)
  } catch {
    toast.error('生成失败')
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
  paper.forEach((q) => {
    examAnswers.value[q.id] = q.type === '多选题' ? [] : ''
  })
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
  if (window.confirm('当前进度将丢失，确定退出吗？')) {
    backWorkspace()
  }
}

async function submitExam() {
  if (examSubmitted.value) return

  const unAnswered = examPaper.value.length - examAnsweredCount.value
  if (unAnswered > 0) {
    if (!window.confirm(`还有 ${unAnswered} 道题未作答，确定交卷吗？`)) {
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
}

function backWorkspace() {
  stopExamTimer()
  viewMode.value = 'workspace'
  activeModule.value = 'daily'
  triggerChartAnimations()
  refreshDailySelections()
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

async function saveWrongQuestion(question: Question, answer: AnswerValue) {
  try {
    await submitObjectiveResults({
      results: [
        {
          question_id: question.id,
          user_answer: formatUserAnswer(answer),
          is_correct: false,
          subject: question.subject,
          question_type: question.type,
          content: question.content,
          options: question.options || {},
          answer: question.answer,
          analysis: question.analysis,
        },
      ],
    })

    wrongTotal.value += 1
  } catch {
    // 忽略重复错题
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

function isObjectiveQuestion(q: Question) {
  return ['选择题', '判断题', '填空题', '分析题'].includes(q.type)
}

function isOptionQuestion(q: Question) {
  return ['选择题', '判断题'].includes(q.type)
}

function getOptions(q: Question) {
  return q.type === '判断题' ? { A: '正确', B: '错误' } : q.options || {}
}

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
</script>

<style scoped>
.question-bank-layout {
  min-height: calc(100vh - var(--navbar-height, 64px));
  padding: 28px 28px 36px;
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

.question-bank-workspace,
.exam-workspace {
  width: min(1480px, 100%);
  margin: 0 auto;
}

.bank-shell {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr) 300px;
  gap: 22px;
  min-height: calc(100vh - var(--navbar-height, 64px) - 64px);
  border: 1px solid rgba(226, 232, 240, 0.84);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: none;
  backdrop-filter: blur(18px);
  overflow: visible;
}

.bank-left-rail {
  position: sticky;
  top: 16px;
  align-self: start;
  max-height: calc(100vh - var(--navbar-height, 64px) - 32px);
  overflow-y: auto;
  padding: 22px 14px;
  border-right: 1px solid rgba(226, 232, 240, 0.8);
  background: rgba(255, 255, 255, 0.54);
  scrollbar-width: thin;
}

.rail-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.rail-brand-icon {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background:
      linear-gradient(135deg, #67e8f9, #8bdbb6),
      #8bdbb6;
  box-shadow: none;
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
  color: #8a94a7;
  font-size: 11px;
  font-weight: 700;
}

.rail-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rail-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 50px;
  padding: 10px 8px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #5f6b7c;
  text-align: left;
  cursor: pointer;
  transition:
      background 160ms ease,
      border-color 160ms ease,
      transform 160ms ease,
      color 160ms ease;
}

.rail-menu-item:hover {
  background: rgba(248, 250, 252, 0.86);
  transform: none;
}

.rail-menu-item.active {
  border-color: rgba(82, 211, 173, 0.34);
  background: rgba(209, 250, 229, 0.48);
  color: #136f60;
}

.rail-menu-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(241, 245, 249, 0.8);
  color: #8a94a7;
  font-size: 11px;
  font-weight: 900;
  flex-shrink: 0;
}

.rail-menu-item.active .rail-menu-mark {
  background: #42c99a;
  color: #fff;
}

.rail-menu-item strong,
.rail-menu-item small {
  display: block;
}

.rail-menu-item strong {
  font-size: 13px;
  font-weight: 800;
}

.rail-menu-item small {
  margin-top: 2px;
  font-size: 11px;
  font-weight: 600;
  color: #9aa4b5;
}

.rail-menu-item.active small {
  color: rgba(19, 111, 96, 0.72);
}

.rail-card {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid rgba(226, 232, 240, 0.86);
}

.rail-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
}

.rail-card-title button {
  border: none;
  background: transparent;
  color: #5f6b7c;
  font-size: 17px;
  font-weight: 700;
  cursor: pointer;
}

.rail-question-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
}

.rail-question {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.rail-question span {
  display: block;
  margin-bottom: 4px;
  color: #8a94a7;
  font-size: 11px;
  font-weight: 700;
}

.rail-question p {
  display: -webkit-box;
  margin: 0;
  color: #3d4656;
  font-size: 13px;
  line-height: 1.45;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rail-empty {
  margin-top: 14px;
  color: #9aa4b5;
  font-size: 12px;
  line-height: 1.6;
}

.bank-main {
  min-width: 0;
  padding: 24px 0 28px;
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

.tag.soft {
  background: #eff6f2;
  color: #288a6e;
}

.tag.level {
  background: #dff2ff;
  color: #3487c7;
}

.recommend-question-content {
  color: #273142;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.82;
}

.recommend-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.recommend-option {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-width: 0 0 1px;
  border-radius: 0;
  background: transparent;
}

.recommend-option span {
  display: inline-flex;
  align-items: center;
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
}

.question-card-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 26px;
  margin-top: 24px;
  padding: 18px 0 8px;
  border-top: 1px solid rgba(226, 232, 240, 0.72);
}

.question-card-actions button {
  padding: 0;
  border: none;
  background: transparent;
  color: #3d4656;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.question-card-actions button.strong {
  color: #17856d;
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

.bank-right-panel {
  position: sticky;
  top: 16px;
  align-self: start;
  max-height: calc(100vh - var(--navbar-height, 64px) - 32px);
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
  height: 48px;
  margin-top: 18px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #ff9f9f, #ffd6b1);
  color: #fff;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(255, 159, 159, 0.2);
  transition:
      transform 160ms ease,
      box-shadow 160ms ease;
}

.get-question-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(255, 159, 159, 0.24);
}

.text-link-btn {
  border: none;
  background: transparent;
  color: #5f6b7c;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
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

.mini-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.92);
  color: #475569;
  font-size: 12px;
  font-weight: 700;
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

.exam-workspace {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.exam-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 0 18px;
  border: none;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
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
  gap: 14px;
}

.exam-title {
  margin: 0;
  color: #172033;
  font-size: 18px;
  font-weight: 900;
}

.timer-badge {
  gap: 8px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  background: #42c99a;
  color: #fff;
  font-weight: 900;
  box-shadow: 0 10px 20px rgba(66, 201, 154, 0.2);
}

.exam-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 20px;
}

.exam-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
}

.exam-question,
.exam-sidebar .panel {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 10px;
  background: #fff;
  box-shadow: none;
}

.exam-question {
  padding: 24px 26px;
}

.exam-question.active {
  border-color: rgba(66, 201, 154, 0.36);
}

.exam-sidebar .panel {
  position: sticky;
  top: 20px;
  padding: 18px;
}

.question-header {
  flex-wrap: wrap;
  margin-bottom: 22px;
}

.q-number {
  color: #172033;
  font-size: 20px;
  font-weight: 900;
}

.tags {
  gap: 8px;
  flex-wrap: wrap;
}

.tag.outline {
  background: #fff;
  color: #5f6b7c;
  border: 1px solid rgba(203, 213, 225, 0.92);
}

.question-text {
  margin-bottom: 26px;
  color: #273142;
  font-size: 18px;
  line-height: 1.85;
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
  border-radius: 10px;
  background: #fff;
  color: #172033;
  cursor: pointer;
  text-align: left;
  transition:
      border-color 150ms ease,
      background 150ms ease,
      box-shadow 150ms ease;
}

.option-btn:hover:not(:disabled) {
  border-color: rgba(66, 201, 154, 0.34);
  background: #fbfefd;
}

.option-btn.selected {
  border-color: rgba(66, 201, 154, 0.44);
  background: rgba(209, 250, 229, 0.38);
  box-shadow: none;
}

.option-btn.correct {
  border-color: rgba(16, 185, 129, 0.32);
  background: rgba(236, 253, 245, 0.92);
}

.option-btn.wrong {
  border-color: rgba(239, 68, 68, 0.28);
  background: rgba(254, 242, 242, 0.94);
}

.opt-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #e7f7f1;
  color: #17856d;
  font-size: 13px;
  font-weight: 900;
}

.opt-text {
  color: #273142;
  font-size: 15px;
  line-height: 1.65;
}

.text-area-input {
  width: 100%;
  min-height: 144px;
  padding: 16px 18px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #172033;
  font-family: inherit;
  font-size: 15px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition:
      border-color 150ms ease,
      box-shadow 150ms ease;
}

.text-area-input:focus {
  border-color: rgba(66, 201, 154, 0.48);
  box-shadow: 0 0 0 4px rgba(66, 201, 154, 0.1);
}

.panel h3 {
  margin: 0 0 18px;
  color: #172033;
  font-size: 14px;
  font-weight: 900;
}

.score-display,
.progress-display {
  margin-bottom: 22px;
  padding: 18px 16px;
  border-radius: 10px;
  background: rgba(209, 250, 229, 0.26);
  border: 1px solid rgba(66, 201, 154, 0.2);
  text-align: center;
}

.score-value,
.progress-value {
  margin-bottom: 8px;
  color: #17856d;
  font-size: 34px;
  font-weight: 900;
}

.score-label,
.progress-label {
  color: #7c8798;
  font-size: 12px;
  font-weight: 800;
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
  background: #fff;
  color: #5f6b7c;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
  transition: all 0.16s ease;
}

.sheet-btn:hover {
  border-color: rgba(66, 201, 154, 0.4);
  transform: scale(1.05);
}

.sheet-btn.answered {
  border-color: #42c99a;
  background: rgba(66, 201, 154, 0.12);
  color: #17856d;
}

.sheet-btn.active {
  background: #42c99a;
  border-color: #42c99a;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(66, 201, 154, 0.14);
}

.sheet-btn.correct {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.14);
  color: #059669;
}

.sheet-btn.wrong {
  border-color: #ef4444;
  background: rgba(239, 68, 68, 0.13);
  color: #dc2626;
}

.full-width {
  width: 100%;
}

.sidebar-submit {
  margin-top: 22px;
}

.result-badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
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
  border-radius: 10px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: #f8fafc;
  font-size: 15px;
}

.analysis-panel.success {
  border-color: rgba(16, 185, 129, 0.2);
}

.analysis-panel.danger {
  border-color: rgba(239, 68, 68, 0.2);
}

.analysis-text {
  margin-top: 10px;
  color: #4f5b6d;
  line-height: 1.7;
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
  .section-toolbar,
  .exam-topbar {
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

  .exam-main {
    grid-template-columns: 1fr;
  }

  .exam-sidebar .panel {
    position: static;
  }
}

@media (max-width: 640px) {
  .rail-menu {
    grid-template-columns: 1fr;
  }

  .recommend-question-card,
  .module-content-card,
  .exam-question,
  .exam-sidebar .panel {
    padding: 20px;
    border-radius: 10px;
  }

  .toolbar-actions,
  .question-card-actions,
  .exam-actions {
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
