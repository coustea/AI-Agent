<template>
  <div class="question-bank-layout">
    <!-- Workspace Layout -->
    <div v-if="viewMode === 'workspace'" class="workspace-layout">
      <!-- Top Navigation -->
      <header class="top-nav">
        <div class="nav-container">
          <div class="brand">
            <svg class="logo-icon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
            <h2>刷题中心</h2>
          </div>
          <nav class="nav-links">
            <button :class="['nav-item', { active: activeModule === 'practice' }]" @click="switchModule('practice')">智能练习</button>
            <button :class="['nav-item', { active: activeModule === 'search' }]" @click="switchModule('search')">全部题目</button>
            <button :class="['nav-item', { active: activeModule === 'paper' }]" @click="switchModule('paper')">模拟组卷</button>
            <button :class="['nav-item', { active: activeModule === 'wrong' }]" @click="switchModule('wrong')">错题本</button>
          </nav>
        </div>
      </header>

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

            <button v-if="!examSubmitted" class="btn-primary full-width" style="margin-top: 24px;" @click="submitExam">交卷</button>
            <button v-else class="btn-secondary full-width" style="margin-top: 24px;" @click="backWorkspace">完成查看</button>
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
import { fetchQuizBankQuestions, fetchQuizReview, submitObjectiveResults, type QuizReviewResult } from '@/features/learning/api/quizBank'
import {
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
    ElMessage.error('加载题库失败')
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
  const pool = practicePool.value.length ? practicePool.value : questions.value
  dailyQuestion.value = pool.length ? (shuffle(pool)[0] as Question) : null
}

function startSingleDailyQuestion() {
  if (!dailyQuestion.value) return ElMessage.warning('暂无题目')
  startExam([dailyQuestion.value], '每日一题')
}

async function startRecommendedPractice() {
  const subject = wrongQuestions.value[0]?.subject || practiceForm.subject || learnerCourses.value[0] || ''
  await startPracticeByCondition({
    title: subject ? `${subject} · 推荐练习` : '推荐练习',
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
    title: practiceForm.subject ? `${practiceForm.subject} · 自定义练习` : '自定义练习',
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
      page_size: 100,
    })
    const pool = result.items || []
    const selected = shuffle(pool).slice(0, config.count)
    if (!selected.length) return ElMessage.warning('没有符合条件的题目')
    startExam(selected, config.title)
  } catch {
    ElMessage.error('生成练习失败')
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
  paperForm.title = '模拟试卷'
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
    .then(() => backWorkspace()).catch(() => undefined)
}

async function submitExam() {
  if (examSubmitted.value) return
  const unAnswered = examPaper.value.length - examAnsweredCount.value
  if (unAnswered > 0) {
    try {
      await ElMessageBox.confirm(`还有 ${unAnswered} 道题目未作答，确定交卷吗？`, '确认交卷', { type: 'warning' })
    } catch {
      return
    }
  }
  stopExamTimer()
  let correctCount = 0
  
  const batchResults: any[] = []
  
  // Grade objective locally and prepare batch
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
  
  // Grade subjective concurrently via AI review and add to batch
  const subjectiveTasks = examPaper.value.filter(q => !isObjectiveQuestion(q)).map(async (q) => {
    const { correct } = await gradeQuestion(q, examAnswers.value[q.id])
    if (correct) correctCount += 1
    // Optional: save review to some state to show to user
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

  // Submit all objective results to save wrongs
  if (batchResults.length > 0) {
    await submitObjectiveResults({ results: batchResults })
  }

  examCorrectCount.value = correctCount
  examSubmitted.value = true
  saveAttempt(examPaper.value.length, correctCount)
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
      }]
    })
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
/* Minimalist Professional Flat Design Tokens */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.question-bank-layout {
  min-height: calc(100vh - 60px);
  background: #FFFFFF;
  color: #171717;
  font-family: 'Inter', -apple-system, sans-serif;
  box-sizing: border-box;
}

/* Top Navigation */
.workspace-layout {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 60px);
}

.top-nav {
  background: #171717;
  color: #FFFFFF;
  border-bottom: 2px solid #D4AF37;
  position: sticky;
  top: 0;
  z-index: 50;
}

.nav-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 40px;
  height: 64px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand h2 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.logo-icon {
  color: #D4AF37;
}

.nav-links {
  display: flex;
  gap: 16px;
}

.nav-item {
  background: transparent;
  border: none;
  color: #A3A3A3;
  font-size: 14px;
  font-weight: 500;
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.nav-item:hover {
  color: #FFFFFF;
}

.nav-item.active {
  color: #D4AF37;
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -22px;
  left: 0;
  right: 0;
  height: 2px;
  background: #D4AF37;
}

.main-content {
  flex: 1;
  padding: 40px;
  max-width: 1000px;
  margin: 0 auto;
  width: 100%;
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
  padding: 16px 40px;
  background: #171717;
  color: #FFFFFF;
  border-bottom: 2px solid #D4AF37;
}

.exam-topbar-left {
  display: flex;
  align-items: center;
  gap: 24px;
}

.exam-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  letter-spacing: 0.05em;
  text-transform: uppercase;
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
  background: #262626;
  border-radius: 4px;
  font-weight: 600;
  font-size: 14px;
  color: #FFFFFF;
  border: 1px solid #404040;
}

.exam-main {
  display: grid;
  grid-template-columns: 1fr 340px;
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.exam-content {
  padding: 48px 40px;
}

.exam-sidebar {
  border-left: 1px solid #E5E7EB;
  background: #FAFAFA;
  padding: 32px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.q-number {
  font-size: 24px;
  font-weight: 700;
  color: #171717;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  background: #FFFFFF;
  color: #404040;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  border: 1px solid #D4D4D4;
}

.tag.type { background: #171717; color: #FFFFFF; border: none; }

.question-text {
  font-size: 18px;
  line-height: 1.6;
  margin-bottom: 40px;
  color: #171717;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  background: #FFFFFF;
  border: 2px solid #E5E7EB;
  border-radius: 0;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.option-btn:hover:not(:disabled) { border-color: #171717; }
.option-btn.selected { border-color: #171717; background: #171717; color: #FFFFFF; }
.option-btn.correct { border-color: #059669; background: #059669; color: #FFFFFF; }
.option-btn.wrong { border-color: #DC2626; background: #DC2626; color: #FFFFFF; }

.opt-key { font-weight: 700; min-width: 24px; font-size: 16px; }
.opt-text { font-size: 16px; line-height: 1.5; }

.text-area-input {
  width: 100%;
  padding: 16px;
  border: 2px solid #E5E7EB;
  border-radius: 0;
  font-size: 16px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  background: #FFFFFF;
  transition: border-color 0.15s;
}
.text-area-input:focus { border-color: #171717; }

.nav-controls {
  display: flex;
  justify-content: space-between;
  margin-top: 48px;
  padding-top: 32px;
  border-top: 1px solid #E5E7EB;
}

.panel h3 { font-size: 14px; margin: 0 0 24px 0; text-transform: uppercase; letter-spacing: 0.05em; color: #404040; }

.score-display, .progress-display {
  text-align: center;
  padding: 32px 24px;
  background: #171717;
  color: #FFFFFF;
  border-radius: 0;
  margin-bottom: 32px;
}

.score-value, .progress-value {
  font-size: 40px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #D4AF37;
}

.score-label, .progress-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #A3A3A3;
}

.grid-sheet {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.sheet-btn {
  aspect-ratio: 1;
  background: #FFFFFF;
  border: 2px solid #E5E7EB;
  border-radius: 0;
  font-size: 14px;
  font-weight: 600;
  color: #404040;
  cursor: pointer;
  transition: all 0.15s;
}

.sheet-btn:hover { border-color: #171717; }
.sheet-btn.answered { background: #171717; color: #FFFFFF; border-color: #171717; }
.sheet-btn.active { border-color: #D4AF37; color: #D4AF37; }
.sheet-btn.correct { background: #059669; color: #FFFFFF; border-color: #059669; }
.sheet-btn.wrong { background: #DC2626; color: #FFFFFF; border-color: #DC2626; }

/* Global Buttons */
.btn-primary { background: #171717; color: #FFFFFF; border: 2px solid #171717; padding: 12px 24px; border-radius: 0; font-weight: 600; cursor: pointer; transition: 0.15s; text-transform: uppercase; letter-spacing: 0.05em; font-size: 13px; }
.btn-primary:hover:not(:disabled) { background: #D4AF37; border-color: #D4AF37; color: #171717; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary { background: #FFFFFF; color: #171717; border: 2px solid #171717; padding: 12px 24px; border-radius: 0; font-weight: 600; cursor: pointer; transition: 0.15s; text-transform: uppercase; letter-spacing: 0.05em; font-size: 13px; }
.btn-secondary:hover:not(:disabled) { background: #171717; color: #FFFFFF; }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-text { background: none; border: none; color: #A3A3A3; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; text-transform: uppercase; letter-spacing: 0.05em; font-size: 13px; }
.btn-text:hover { color: #FFFFFF; }

.full-width { width: 100%; }

.result-badge { padding: 6px 12px; border-radius: 0; font-size: 13px; font-weight: 700; text-transform: uppercase; border: 2px solid transparent; }
.result-badge.success { background: #ECFDF5; color: #059669; border-color: #059669; }
.result-badge.danger { background: #FEF2F2; color: #DC2626; border-color: #DC2626; }

.analysis-panel { margin-top: 32px; padding: 24px; border-radius: 0; font-size: 15px; }
.analysis-panel.success { background: #F8FAFC; border-left: 4px solid #10B981; }
.analysis-panel.danger { background: #FAFAFA; border-left: 4px solid #EF4444; }
.analysis-text { margin-top: 12px; color: #404040; line-height: 1.6; }
</style>
