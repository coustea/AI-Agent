<template>
  <div class="question-bank-layout">
    <div v-if="viewMode === 'workspace'" class="question-bank-workspace">
      <section class="question-bank-hero">
        <div class="hero-copy">
          <span class="hero-kicker">Question Bank Workspace</span>
          <h1>刷题中心</h1>
          <p>在统一的学习工作台中完成练习、检索、组卷和错题巩固。</p>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <span>已练题数</span>
            <strong>{{ stats.totalAttempted }}</strong>
          </div>
          <div class="hero-stat">
            <span>正确率</span>
            <strong>{{ practiceAccuracy }}</strong>
          </div>
          <div class="hero-stat warning">
            <span>待复习</span>
            <strong>{{ wrongTotal }}</strong>
          </div>
        </div>
      </section>

      <section class="workspace-tabs" role="tablist" aria-label="棰樺簱妯″潡">
        <button :class="['workspace-tab', { active: activeModule === 'daily' }]" @click="switchModule('daily')">每日练习</button>
        <button :class="['workspace-tab', { active: activeModule === 'practice' }]" @click="switchModule('practice')">智能练习</button>
        <button :class="['workspace-tab', { active: activeModule === 'search' }]" @click="switchModule('search')">全部题目</button>
        <button :class="['workspace-tab', { active: activeModule === 'paper' }]" @click="switchModule('paper')">模拟组卷</button>
        <button :class="['workspace-tab', { active: activeModule === 'wrong' }]" @click="switchModule('wrong')">错题本</button>
      </section>

      <section class="workspace-panel-shell">
        <div class="workspace-panel-header">
          <div>
            <span class="workspace-panel-label">Current Module</span>
            <h2>{{ moduleTitles[activeModule] }}</h2>
          </div>
          <p>{{ moduleDescriptions[activeModule] }}</p>
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

    <div v-else class="exam-workspace">
      <header class="exam-topbar">
        <div class="exam-topbar-left">
          <button class="btn-text" @click="quitExam">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            閫€鍑鸿€冭瘯
          </button>
          <h1 class="exam-title">{{ examTitle }}</h1>
        </div>
        <div class="exam-actions">
          <div class="timer-badge">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>{{ formattedExamTime }}</span>
          </div>
          <button v-if="!examSubmitted" class="btn-primary" @click="submitExam">浜ゅ嵎</button>
          <button v-else class="btn-secondary" @click="backWorkspace">杩斿洖棣栭〉</button>
        </div>
      </header>

      <main class="exam-main">
        <div class="exam-content">
          <article v-if="currentExamQuestion" class="exam-question">
            <div class="question-header">
              <span class="q-number">第 {{ currentExamIndex + 1 }} 题 / 共 {{ examPaper.length }} 题</span>
              <div class="tags">
                <span class="tag outline">{{ currentExamQuestion.subject }}</span>
                <span class="tag type">{{ currentExamQuestion.type }}</span>
              </div>
              <div v-if="examSubmitted" :class="['result-badge', isExamCorrect(currentExamQuestion) ? 'success' : 'danger']">
                {{ isExamCorrect(currentExamQuestion) ? '正确' : '错误' }}
              </div>
            </div>

            <div class="question-text" v-html="renderInline(currentExamQuestion.content)"></div>

            <div v-if="isOptionQuestion(currentExamQuestion)" class="options-list">
              <button
                v-for="(text, key) in getOptions(currentExamQuestion)"
                :key="key"
                type="button"
                :class="[
                  'option-btn',
                  {
                    selected: isSelected(examAnswers[currentExamQuestion.id], key),
                    correct: examSubmitted && isCorrectOption(currentExamQuestion, key),
                    wrong: examSubmitted && isSelected(examAnswers[currentExamQuestion.id], key) && !isCorrectOption(currentExamQuestion, key),
                  },
                ]"
                :disabled="examSubmitted"
                @click="selectExamOption(currentExamQuestion, key)"
              >
                <span class="opt-key">{{ key }}</span>
                <span class="opt-text" v-html="renderInline(text)"></span>
              </button>
            </div>
            <textarea
              v-else
              v-model="examAnswers[currentExamQuestion.id]"
              class="text-area-input"
              rows="6"
              :disabled="examSubmitted"
              placeholder="请输入你的答案..."
            ></textarea>

            <div v-if="examSubmitted" :class="['analysis-panel', isExamCorrect(currentExamQuestion) ? 'success' : 'danger']">
              <strong>参考答案：{{ formatAnswer(currentExamQuestion.answer) }}</strong>
              <div class="analysis-text" v-html="renderInline(currentExamQuestion.analysis || '暂无解析。')"></div>
            </div>

            <div class="nav-controls">
              <button class="btn-secondary" :disabled="currentExamIndex === 0" @click="currentExamIndex -= 1">上一题</button>
              <button class="btn-primary" :disabled="currentExamIndex >= examPaper.length - 1" @click="currentExamIndex += 1">下一题</button>
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
                @click="currentExamIndex = index"
              >
                {{ index + 1 }}
              </button>
            </div>

            <button v-if="!examSubmitted" class="btn-primary full-width sidebar-submit" @click="submitExam">浜ゅ嵎</button>
            <button v-else class="btn-secondary full-width sidebar-submit" @click="backWorkspace">瀹屾垚鏌ョ湅</button>
          </div>
        </aside>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, shallowRef } from 'vue'
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
type ModuleKey = 'daily' | 'practice' | 'search' | 'paper' | 'wrong'
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
const activeModule = ref<ModuleKey>('daily')

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
const currentExamQuestion = computed(() => examPaper.value[currentExamIndex.value] || null)
const examAnsweredCount = computed(() => examPaper.value.filter((item) => hasAnswerData(examAnswers.value[item.id])).length)
const examScore = computed(() => {
  if (!examPaper.value.length) return 0
  return Math.round((examCorrectCount.value / examPaper.value.length) * 100)
})
const practiceAccuracy = computed(() => {
  if (!stats.totalAttempted) return '0%'
  return `${Math.round((stats.totalCorrect / stats.totalAttempted) * 100)}%`
})
const moduleTitles: Record<ModuleKey, string> = {
  daily: '每日练习',
  practice: '智能练习',
  search: '全部题目',
  paper: '模拟组卷',
  wrong: '错题本',
}
const moduleDescriptions: Record<ModuleKey, string> = {
  daily: '先完成今天这一题，再进入更完整的练习节奏。',
  practice: '按推荐练习、错题复习、模拟组卷和自定义练习组织你的训练。',
  search: '按学科、难度和题型检索题库并直接作答。',
  paper: '配置你的模拟试卷，并在预览后进入考试模式。',
  wrong: '集中复习错题、管理薄弱点并进行再练。',
}

onMounted(() => {
  readLocalStats()
  void bootstrap()
})

onUnmounted(() => stopExamTimer())

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
}

function backWorkspace() {
  stopExamTimer()
  viewMode.value = 'workspace'
  activeModule.value = 'daily'
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
  padding: 24px;
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
  gap: 20px;
}

.question-bank-hero,
.workspace-panel-shell,
.exam-question,
.exam-sidebar .panel {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.question-bank-hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 20px;
  padding: 28px;
  background: linear-gradient(135deg, #ffffff 0%, var(--cat-eval-soft, #f5f3ff) 100%);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 680px;
}

.hero-kicker,
.workspace-panel-label {
  color: var(--cat-eval, #8b5cf6);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy h1,
.workspace-panel-header h2,
.exam-title {
  margin: 0;
  color: #0f172a;
  line-height: 1.15;
}

.hero-copy h1 {
  font-size: clamp(2rem, 3vw, 2.8rem);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.hero-copy p,
.workspace-panel-header p {
  margin: 0;
  color: #475569;
  line-height: 1.65;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(140px, 1fr));
  gap: 12px;
  min-width: min(100%, 460px);
}

.hero-stat {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  padding: 18px 20px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.86);
}

.hero-stat span {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.hero-stat strong {
  color: #0f172a;
  font-size: 1.75rem;
  font-weight: 800;
}

.hero-stat.warning strong {
  color: #dc2626;
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
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 14px;
  background: #fff;
  color: #475569;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, color 150ms ease;
}

.sheet-btn:hover {
  border-color: rgba(79, 70, 229, 0.28);
}

.sheet-btn.answered {
  border-color: rgba(79, 70, 229, 0.2);
  background: rgba(238, 242, 255, 0.88);
  color: #6d28d9;
}

.sheet-btn.active {
  background: var(--cat-eval, #8b5cf6);
  border-color: var(--cat-eval, #8b5cf6);
  color: #fff;
}

.sheet-btn.correct {
  background: rgba(16, 185, 129, 0.92);
  border-color: rgba(16, 185, 129, 0.92);
  color: #fff;
}

.sheet-btn.wrong {
  background: rgba(239, 68, 68, 0.92);
  border-color: rgba(239, 68, 68, 0.92);
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
</style>

