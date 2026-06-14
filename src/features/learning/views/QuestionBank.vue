<template>
  <div class="question-bank-layout">
    <!-- Workspace Layout -->
    <div v-if="viewMode === 'workspace'" class="workspace-layout">
      <!-- Sidebar Navigation -->
      <aside class="sidebar">
        <div class="sidebar-header">
          <svg class="logo-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
          <h2>Practice Center</h2>
        </div>
        <nav class="sidebar-nav">
          <button :class="['nav-item', { active: activeModule === 'practice' }]" @click="switchModule('practice')">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            Dashboard
          </button>
          <button :class="['nav-item', { active: activeModule === 'search' }]" @click="switchModule('search')">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            Question Bank
          </button>
          <button :class="['nav-item', { active: activeModule === 'paper' }]" @click="switchModule('paper')">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            Mock Exams
          </button>
          <button :class="['nav-item', { active: activeModule === 'wrong' }]" @click="switchModule('wrong')">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.5 9.5-9.1 9.1a2 2 0 0 1-2.8 0l-5.7-5.7a2 2 0 0 1 0-2.8l9.1-9.1a2 2 0 0 1 2.8 0l5.7 5.7a2 2 0 0 1 0 2.8Z"/><path d="M5.5 15.5 12 22"/></svg>
            Wrong Book
          </button>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="main-content">
        <PracticeTab
          v-if="activeModule === 'practice'"
          :stats="stats"
          :wrongTotal="wrongTotal"
          :recommendedSubject="recommendedSubject"
          :recommendedCount="recommendedCount"
          :practiceLoading="practiceLoading"
          :dailyQuestion="dailyQuestion"
          :subjects="subjects"
          :difficulties="difficulties"
          :types="types"
          @switch-tab="switchModule"
          @start-recommended="startRecommendedPractice"
          @start-daily="startSingleDailyQuestion"
          @start-custom="startSpecialPracticeProxy"
          @refresh-daily="pickDailyQuestion"
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
    </div>

    <!-- Fullscreen Exam View -->
    <div v-else class="exam-workspace">
      <header class="exam-topbar">
        <div class="exam-topbar-left">
          <button class="btn-text" @click="quitExam">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            Exit Exam
          </button>
          <h1 class="exam-title">{{ examTitle }}</h1>
        </div>
        <div class="exam-actions">
          <div class="timer-badge">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            <span>{{ formattedExamTime }}</span>
          </div>
          <button v-if="!examSubmitted" class="btn-primary" @click="submitExam">Submit Exam</button>
          <button v-else class="btn-secondary" @click="backWorkspace">Back to Dashboard</button>
        </div>
      </header>

      <main class="exam-main">
        <div class="exam-content">
          <article v-if="currentExamQuestion" class="exam-question">
            <div class="question-header">
              <span class="q-number">Question {{ currentExamIndex + 1 }} of {{ examPaper.length }}</span>
              <div class="tags">
                <span class="tag outline">{{ currentExamQuestion.subject }}</span>
                <span class="tag type">{{ currentExamQuestion.type }}</span>
              </div>
              <div v-if="examSubmitted" :class="['result-badge', isExamCorrect(currentExamQuestion) ? 'success' : 'danger']">
                {{ isExamCorrect(currentExamQuestion) ? 'Correct' : 'Incorrect' }}
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
                    'selected': isSelected(examAnswers[currentExamQuestion.id], key),
                    'correct': examSubmitted && isCorrectOption(currentExamQuestion, key),
                    'wrong': examSubmitted && isSelected(examAnswers[currentExamQuestion.id], key) && !isCorrectOption(currentExamQuestion, key)
                  }
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
              placeholder="Enter your answer here..."
            ></textarea>

            <div v-if="examSubmitted" :class="['analysis-panel', isExamCorrect(currentExamQuestion) ? 'success' : 'danger']">
              <strong>Reference: {{ formatAnswer(currentExamQuestion.answer) }}</strong>
              <div class="analysis-text" v-html="renderInline(currentExamQuestion.analysis || 'No analysis available.')"></div>
            </div>

            <div class="nav-controls">
              <button class="btn-secondary" :disabled="currentExamIndex === 0" @click="currentExamIndex -= 1">Previous</button>
              <button class="btn-primary" :disabled="currentExamIndex >= examPaper.length - 1" @click="currentExamIndex += 1">Next</button>
            </div>
          </article>
        </div>

        <aside class="exam-sidebar">
          <div class="panel">
            <h3>{{ examSubmitted ? 'Exam Report' : 'Answer Sheet' }}</h3>

            <div v-if="examSubmitted" class="score-display">
              <div class="score-value">{{ examScore }}%</div>
              <div class="score-label">Final Score</div>
            </div>
            <div v-else class="progress-display">
              <div class="progress-value">{{ examAnsweredCount }} / {{ examPaper.length }}</div>
              <div class="progress-label">Answered</div>
            </div>

            <div class="grid-sheet">
              <button
                v-for="(question, index) in examPaper"
                :key="question.id"
                :class="[
                  'sheet-btn',
                  {
                    'active': currentExamIndex === index,
                    'answered': !examSubmitted && hasAnswerData(examAnswers[question.id]),
                    'correct': examSubmitted && isExamCorrect(question),
                    'wrong': examSubmitted && !isExamCorrect(question)
                  }
                ]"
                @click="currentExamIndex = index"
              >
                {{ index + 1 }}
              </button>
            </div>

            <button v-if="!examSubmitted" class="btn-primary full-width" style="margin-top: 24px;" @click="submitExam">Submit Exam</button>
            <button v-else class="btn-secondary full-width" style="margin-top: 24px;" @click="backWorkspace">Complete Review</button>
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
import { fetchQuizBankQuestions, fetchQuizReview, type QuizReviewResult } from '@/features/learning/api/quizBank'
import {
  addWrongQuestion,
  archiveWrongQuestion,
  fetchRandomWrongQuestion,
  fetchWrongQuestions,
  removeWrongQuestion,
} from '@/features/learning/api/wrongQuestions'

// Subcomponents
import PracticeTab from '@/features/learning/components/question-bank/PracticeTab.vue'
import SearchTab from '@/features/learning/components/question-bank/SearchTab.vue'
import ExamTab from '@/features/learning/components/question-bank/ExamTab.vue'
import WrongBookTab from '@/features/learning/components/question-bank/WrongBookTab.vue'

type ViewMode = 'workspace' | 'exam'
type ModuleKey = 'practice' | 'search' | 'paper' | 'wrong'
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

// Global State
const viewMode = ref<ViewMode>('workspace')
const activeModule = ref<ModuleKey>('practice')

const subjects = ref<string[]>([])
const difficulties = ref<string[]>([])
const types = ref<string[]>([])
const learnerCourses = ref<string[]>([])
const practicePool = shallowRef<Question[]>([])

// Practice State
const practiceLoading = ref(false)
const practiceForm = reactive({ subject: '', difficulty: '', type: '', count: 10 })
const dailyQuestion = ref<Question | null>(null)

// Bank State
const questions = shallowRef<Question[]>([])
const totalQuestions = ref(0)
const bankLoading = ref(false)
const bankPage = ref(1)
const bankPageSize = ref(8)
const bankFilters = reactive({ query: '', subject: '', difficulty: '', type: '' })

// Wrong State
const wrongQuestions = shallowRef<Question[]>([])
const wrongTotal = ref(0)
const wrongLoading = ref(false)
const wrongPage = ref(1)
const wrongPageSize = ref(8)
const wrongFilters = reactive({ query: '', subject: '', type: '' })

// Interaction States
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

// Drill State
const wrongDrillQuestion = ref<Question | null>(null)
const wrongDrillAnswer = ref<AnswerValue>('')
const wrongDrillSubmitted = ref(false)
const wrongDrillCorrect = ref(false)
const wrongDrillReviewing = ref(false)
const wrongDrillReview = ref<QuizReviewResult | null>(null)

const stats = reactive({ totalAttempted: 0, totalCorrect: 0 })

// Paper State
const paperForm = reactive({
  title: 'Mock Exam',
  subject: '',
  difficulty: '混合',
  duration: 45,
})

const paperTypeCounts = reactive([
  { type: '选择题', label: 'Single Choice', count: 5 },
  { type: '多选题', label: 'Multiple Choice', count: 2 },
  { type: '判断题', label: 'True/False', count: 3 },
  { type: '填空题', label: 'Fill Blanks', count: 2 },
  { type: '简答题', label: 'Short Answer', count: 1 },
])
const paperPreview = shallowRef<Question[]>([])
const paperLoading = ref(false)

// Active Exam State
const examTitle = ref('')
const examPaper = shallowRef<Question[]>([])
const examAnswers = ref<Record<string, AnswerValue>>({})
const examSubmitted = ref(false)
const currentExamIndex = ref(0)
const examTime = ref(0)
const examCorrectCount = ref(0)
let examTimer: number | null = null

// Computed
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

// Lifecycle
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

// Navigation & Actions
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
      page_size: 160,
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
    ElMessage.error('Failed to load question bank')
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
    ElMessage.error('Failed to load wrong book')
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
  const pool = practicePool.value.length ? practicePool.value : questions.value
  dailyQuestion.value = pool.length ? (shuffle(pool)[0] as Question) : null
}

function startSingleDailyQuestion() {
  if (!dailyQuestion.value) return ElMessage.warning('No questions available')
  startExam([dailyQuestion.value], 'Daily Challenge')
}

async function startRecommendedPractice() {
  const subject = wrongQuestions.value[0]?.subject || practiceForm.subject || learnerCourses.value[0] || ''
  await startPracticeByCondition({
    title: subject ? `${subject} · Recommended Practice` : 'Recommended Practice',
    subject,
    count: recommendedCount.value,
  })
}

function startSpecialPracticeProxy(formObj: any) {
  practiceForm.subject = formObj.subject
  practiceForm.difficulty = formObj.difficulty
  practiceForm.type = formObj.type
  practiceForm.count = formObj.count
  void startSpecialPractice()
}

async function startSpecialPractice() {
  await startPracticeByCondition({
    title: practiceForm.subject ? `${practiceForm.subject} · Custom Practice` : 'Custom Practice',
    subject: practiceForm.subject,
    difficulty: practiceForm.difficulty,
    type: practiceForm.type,
    count: practiceForm.count,
  })
}

async function startPracticeByCondition(config: { title: string; subject?: string; difficulty?: string; type?: string; count: number }) {
  practiceLoading.value = true
  try {
    const result = await fetchQuizBankQuestions({
      subject: config.subject || undefined,
      difficulty: config.difficulty || undefined,
      type: config.type || undefined,
      subjects: !config.subject && learnerCourses.value.length ? learnerCourses.value : undefined,
      page: 1,
      page_size: 300,
    })
    const pool = result.items || []
    const selected = shuffle(pool).slice(0, config.count)
    if (!selected.length) return ElMessage.warning('No questions match the criteria')
    startExam(selected, config.title)
  } catch {
    ElMessage.error('Failed to generate practice')
  } finally {
    practiceLoading.value = false
  }
}

// Review/Answering Logic (Bank + Wrong)
async function pickWrongQuestion() {
  wrongDrillAnswer.value = ''
  wrongDrillSubmitted.value = false
  wrongDrillCorrect.value = false
  wrongDrillReviewing.value = false
  wrongDrillReview.value = null
  try {
    const item = await fetchRandomWrongQuestion()
    wrongDrillQuestion.value = item ? normalizeWrongQuestion(item) : null
  } catch {
    wrongDrillQuestion.value = null
  }
}

function selectWrongDrillOption(key: string) {
  if (!wrongDrillQuestion.value || wrongDrillSubmitted.value) return
  wrongDrillAnswer.value = updateOptionAnswer(wrongDrillQuestion.value, wrongDrillAnswer.value, key)
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

// Mock Exam Builder
function resetPaperForm() {
  paperForm.title = 'Mock Exam'
  paperForm.subject = subjects.value[0] || ''
  paperForm.difficulty = '混合'
  paperForm.duration = 45
  if (paperTypeCounts[0]) paperTypeCounts[0].count = 5
  if (paperTypeCounts[1]) paperTypeCounts[1].count = 2
  if (paperTypeCounts[2]) paperTypeCounts[2].count = 3
  if (paperTypeCounts[3]) paperTypeCounts[3].count = 2
  if (paperTypeCounts[4]) paperTypeCounts[4].count = 1
  paperPreview.value = []
}

async function generatePaperPreview() {
  const targetCount = paperTypeCounts.reduce((sum, item) => sum + Number(item.count || 0), 0)
  if (targetCount <= 0) return ElMessage.warning('Select at least 1 question')
  paperLoading.value = true
  try {
    const result = await fetchQuizBankQuestions({
      subject: paperForm.subject || undefined,
      difficulty: paperForm.difficulty === '混合' ? undefined : paperForm.difficulty,
      page: 1,
      page_size: 400,
    })
    const pool = result.items || []
    const selected: Question[] = []
    paperTypeCounts.forEach((config) => {
      const sameType = pool.filter((item) => item.type === config.type)
      selected.push(...shuffle(sameType).slice(0, config.count))
    })
    paperPreview.value = selected
    if (!selected.length) ElMessage.warning('No questions available')
    else ElMessage.success(`Generated ${selected.length} questions`)
  } catch {
    ElMessage.error('Generation failed')
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
  ElMessageBox.confirm('Progress will be lost.', 'Quit Exam', { type: 'warning' })
    .then(() => backWorkspace()).catch(() => undefined)
}

async function submitExam() {
  if (examSubmitted.value) return
  const unAnswered = examPaper.value.length - examAnsweredCount.value
  if (unAnswered > 0) {
    try {
      await ElMessageBox.confirm(`You have ${unAnswered} unanswered questions. Submit anyway?`, 'Confirm Submit', { type: 'warning' })
    } catch {
      return
    }
  }
  stopExamTimer()
  let correctCount = 0
  const wrongTasks: Promise<void>[] = []
  examPaper.value.forEach((q) => {
    if (evaluateAnswer(q, examAnswers.value[q.id])) correctCount += 1
    else wrongTasks.push(saveWrongQuestion(q, examAnswers.value[q.id]))
  })
  examCorrectCount.value = correctCount
  examSubmitted.value = true
  saveAttempt(examPaper.value.length, correctCount)
  await Promise.allSettled(wrongTasks)
}

function backWorkspace() {
  stopExamTimer()
  viewMode.value = 'workspace'
  activeModule.value = 'practice'
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

// Helpers
async function gradeQuestion(question: Question, answer: AnswerValue) {
  if (isOptionQuestion(question)) return { correct: evaluateAnswer(question, answer), review: null }
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
    await addWrongQuestion({ question_id: question.id, user_answer: formatUserAnswer(answer) })
    wrongTotal.value += 1
  } catch { /* ignore duplicates */ }
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
  return userText.includes(stdText) || stdText.includes(userText)
}

function isOptionQuestion(q: Question) { return ['选择题', '单选题', '多选题', '判断题'].includes(q.type) }
function getOptions(q: Question) { return q.type === '判断题' ? { A: '正确', B: '错误' } : (q.options || {}) }
function isSelected(ans: AnswerValue, key: string) {
  if (!ans) return false
  return Array.isArray(ans) ? ans.includes(key) : ans === key
}
function updateOptionAnswer(q: Question, ans: AnswerValue, key: string) {
  if (q.type !== '多选题') return key
  const selected = normalizeAnswer(ans)
  return selected.includes(key) ? selected.filter(k => k !== key) : [...selected, key]
}
function correctKeys(q: Question) {
  let ansText = String(q.answer || '').trim()
  if (q.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确', '对'].some(i => upper.includes(i))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误', '错'].some(i => upper.includes(i))) ansText = 'B'
  }
  return ansText.split(/[、,，;；\s]+/).map(i => i.trim().toUpperCase()).filter(Boolean)
}
function isCorrectOption(q: Question, key: string) { return correctKeys(q).includes(key) }
function normalizeAnswer(ans: AnswerValue): string[] {
  if (Array.isArray(ans)) return ans.map(i => String(i).trim().toUpperCase()).filter(Boolean)
  return String(ans || '').split(/[、,，;；\s]+/).map(i => i.trim().toUpperCase()).filter(Boolean)
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
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
}
</script>

<style scoped>
/* Base Professional SaaS Minimalist Styles */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.question-bank-layout {
  min-height: calc(100vh - 60px);
  background: #F9FAFB;
  color: #111827;
  font-family: 'Inter', -apple-system, sans-serif;
  box-sizing: border-box;
}

/* Sidebar Layout */
.workspace-layout {
  display: flex;
  min-height: calc(100vh - 60px);
}

.sidebar {
  width: 260px;
  background: #FFFFFF;
  border-right: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #F3F4F6;
}

.sidebar-header h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  letter-spacing: -0.01em;
}

.logo-icon {
  color: #111827;
}

.sidebar-nav {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #4B5563;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: #F3F4F6;
  color: #111827;
}

.nav-item.active {
  background: #111827;
  color: #FFFFFF;
}

.main-content {
  flex: 1;
  padding: 32px 40px;
  max-width: 1200px;
  margin: 0 auto;
  overflow-y: auto;
}

/* Fullscreen Exam Workspace */
.exam-workspace {
  background: #FFFFFF;
  min-height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
}

.exam-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  border-bottom: 1px solid #E5E7EB;
}

.exam-topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.exam-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.exam-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.timer-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #F3F4F6;
  border-radius: 6px;
  font-weight: 600;
  font-size: 14px;
}

.exam-main {
  display: grid;
  grid-template-columns: 1fr 320px;
  flex: 1;
}

.exam-content {
  padding: 40px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

.exam-sidebar {
  border-left: 1px solid #E5E7EB;
  background: #F9FAFB;
  padding: 24px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.q-number {
  font-size: 18px;
  font-weight: 600;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  background: #F3F4F6;
  color: #374151;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
}

.tag.outline { background: transparent; border: 1px solid #E5E7EB; }
.tag.type { background: #FEF3C7; color: #92400E; }

.question-text {
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 32px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.option-btn:hover:not(:disabled) { border-color: #9CA3AF; }
.option-btn.selected { border-color: #111827; background: #F3F4F6; }
.option-btn.correct { border-color: #10B981; background: #ECFDF5; }
.option-btn.wrong { border-color: #EF4444; background: #FEF2F2; }

.opt-key { font-weight: 600; min-width: 24px; }
.opt-text { font-size: 15px; line-height: 1.5; }

.text-area-input {
  width: 100%;
  padding: 16px;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  font-size: 15px;
  font-family: inherit;
  resize: vertical;
  outline: none;
}
.text-area-input:focus { border-color: #111827; }

.nav-controls {
  display: flex;
  justify-content: space-between;
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid #E5E7EB;
}

.panel h3 { font-size: 16px; margin: 0 0 24px 0; }

.score-display, .progress-display {
  text-align: center;
  padding: 24px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  margin-bottom: 24px;
}

.score-value, .progress-value {
  font-size: 32px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 8px;
}

.score-label, .progress-label {
  font-size: 12px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.grid-sheet {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.sheet-btn {
  aspect-ratio: 1;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #4B5563;
  cursor: pointer;
}

.sheet-btn.answered { background: #111827; color: white; border-color: #111827; }
.sheet-btn.active { border: 2px solid #111827; }
.sheet-btn.correct { background: #10B981; color: white; border-color: #10B981; }
.sheet-btn.wrong { background: #EF4444; color: white; border-color: #EF4444; }

/* Global Buttons */
.btn-primary { background: #111827; color: #FFFFFF; border: none; padding: 8px 24px; border-radius: 6px; font-weight: 500; cursor: pointer; transition: 0.15s; }
.btn-primary:hover:not(:disabled) { background: #374151; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary { background: #FFFFFF; color: #111827; border: 1px solid #D1D5DB; padding: 8px 24px; border-radius: 6px; font-weight: 500; cursor: pointer; transition: 0.15s; }
.btn-secondary:hover:not(:disabled) { background: #F9FAFB; border-color: #9CA3AF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-text { background: none; border: none; color: #6B7280; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px;}
.btn-text:hover { color: #111827; }

.full-width { width: 100%; }

.result-badge { padding: 4px 12px; border-radius: 99px; font-size: 13px; font-weight: 500; }
.result-badge.success { background: #ECFDF5; color: #059669; }
.result-badge.danger { background: #FEF2F2; color: #DC2626; }

.analysis-panel { margin-top: 24px; padding: 16px; border-radius: 8px; font-size: 14px; }
.analysis-panel.success { background: #ECFDF5; border-left: 3px solid #10B981; }
.analysis-panel.danger { background: #FEF2F2; border-left: 3px solid #EF4444; }
</style>