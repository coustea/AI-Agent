<template>
  <div v-if="mode === 'config'" class="exam-shell">
    <div class="workspace-grid">
      <section class="workspace-pane config-workspace">
        <div class="section-head compact">
          <div>
            <span class="section-kicker">模拟组卷</span>
            <h3>试卷参数配置</h3>
          </div>

          <div class="head-actions">
            <button class="text-btn" type="button" @click="$emit('reset-form')">重置</button>
            <button class="secondary-btn" type="button" :disabled="loading" @click="$emit('generate-preview')">
              {{ loading ? '生成中...' : '生成预览' }}
            </button>
            <button class="primary-btn" type="button" :disabled="!canStartExam" @click="$emit('start-exam')">
              开始考试
            </button>
          </div>
        </div>

        <form class="config-form" @submit.prevent>
          <div class="field-row compact-grid">
            <div class="field-group title-group">
              <label>标题</label>
              <input v-model="form.title" type="text" class="field" placeholder="例如：数据结构期末模拟" />
            </div>
            <div class="field-group">
              <label>学科</label>
              <select v-model="form.subject" class="field">
                <option value="">全部学科</option>
                <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="field-group">
              <label>难度</label>
              <select v-model="form.difficulty" class="field">
                <option value="混合">混合</option>
                <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="field-group duration-group">
              <label>时长</label>
              <input v-model="form.duration" type="number" min="5" max="180" class="field" />
            </div>
          </div>

          <div class="count-chip-row">
            <div v-for="item in typeCounts" :key="item.type" class="count-chip">
              <div class="count-chip-labels">
                <span class="chip-name">{{ item.label }}</span>
                <span class="chip-meta">{{ item.type }}</span>
              </div>
              <input v-model="item.count" type="number" min="0" max="30" class="count-input" />
            </div>
          </div>
        </form>
      </section>

      <section class="workspace-pane preview-workspace">
        <div class="section-head">
          <div>
            <span class="section-kicker">试卷预览</span>
            <h3>题目列表</h3>
          </div>
          <span class="preview-count">{{ preview.length }} / {{ expectedCount }} 题</span>
        </div>

        <div v-if="preview.length" class="preview-list">
          <article v-for="(question, index) in preview" :key="`${question.id}-${index}`" class="preview-item">
            <div class="preview-item-top">
              <span class="preview-no">第 {{ index + 1 }} 题</span>
              <div class="preview-tags">
                <span class="preview-tag type">{{ question.type }}</span>
                <span class="preview-tag subject">{{ question.subject }}</span>
                <span :class="['preview-tag difficulty', difficultyClass(question.difficulty)]">
                  {{ question.difficulty || '未评级' }}
                </span>
              </div>
            </div>
            <p class="preview-text">{{ summarize(question.content) }}</p>
          </article>
        </div>

        <div v-else class="preview-empty">
          <strong>暂无试卷预览</strong>
          <p>请先配置参数并生成预览。</p>
        </div>
      </section>
    </div>
  </div>

  <div v-else class="exam-workspace">
    <header class="exam-topbar">
      <div class="exam-topbar-left">
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
        <button class="btn-secondary" type="button" @click="$emit('exit-exam')">
          {{ examSubmitted ? '返回题库' : '退出考试' }}
        </button>
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
                  selected: isSelected(examAnswers[question.id], String(key)),
                  correct: examSubmitted && isCorrectOption(question, String(key)),
                  wrong: examSubmitted && isSelected(examAnswers[question.id], String(key)) && !isCorrectOption(question, String(key)),
                },
              ]"
              :disabled="examSubmitted"
              @click="$emit('select-exam-option', question, String(key))"
            >
              <span class="opt-key">{{ key }}</span>
              <span class="opt-text" v-html="renderInline(String(text))"></span>
            </button>
          </div>

          <textarea
            v-else-if="!examSubmitted"
            :value="examAnswers[question.id] as string"
            class="text-area-input"
            rows="4"
            placeholder="请输入你的答案..."
            @input="$emit('update-exam-answer', question.id, ($event.target as HTMLTextAreaElement).value)"
          ></textarea>

          <div v-if="examSubmitted" :class="['exam-answer-review', isExamCorrect(question) ? 'success' : 'danger']">
            <div class="answer-review-grid">
              <div class="answer-review-card">
                <span class="answer-review-label">你的答案</span>
                <div class="answer-review-value">{{ formatExamAnswer(question, examAnswers[question.id]) }}</div>
              </div>
              <div class="answer-review-card">
                <span class="answer-review-label">参考答案</span>
                <div class="answer-review-value">{{ formatExamReferenceAnswer(question) }}</div>
              </div>
            </div>

            <div class="answer-review-meta">
              <span :class="['result-badge', isExamCorrect(question) ? 'success' : 'danger']">
                {{ isExamCorrect(question) ? '正确' : '错误' }}
              </span>
              <span v-if="examReview[question.id]?.feedback" class="review-feedback">
                {{ examReview[question.id]?.feedback }}
              </span>
            </div>

            <div
              v-if="examReview[question.id]?.improvement_hints?.length"
              class="review-hints"
            >
              <strong>改进建议</strong>
              <ul>
                <li v-for="hint in examReview[question.id]?.improvement_hints || []" :key="hint">{{ hint }}</li>
              </ul>
            </div>

            <div class="analysis-text">
              <strong>题目解析</strong>
              <div v-html="renderInline(question.analysis || '暂无解析。')"></div>
            </div>
          </div>
        </article>
      </div>

      <aside class="exam-sidebar">
        <div class="panel">
          <h3>{{ examSubmitted ? '考试报告' : '答题卡' }}</h3>

          <div v-if="examSubmitted" class="score-display">
            <div class="score-value">{{ examScore }}%</div>
            <div class="score-label">{{ examResultLevel }}</div>
          </div>
          <div v-else class="progress-display">
            <div class="progress-value">{{ examAnsweredCount }} / {{ examPaper.length }}</div>
            <div class="progress-label">已作答</div>
          </div>

          <div v-if="!examSubmitted && examSubmitNoticeVisible && examUnansweredCount > 0" class="submit-inline-notice">
            <strong>还有 {{ examUnansweredCount }} 道题未作答</strong>
            <p>可以继续完成未答题目，或直接提交当前试卷。</p>
            <div class="submit-inline-actions">
              <button class="btn-secondary" type="button" @click="$emit('cancel-submit-exam')">继续作答</button>
              <button class="btn-primary" type="button" @click="$emit('request-submit-exam')">仍然交卷</button>
            </div>
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
              @click="$emit('scroll-to-question', index)"
            >
              {{ index + 1 }}
            </button>
          </div>

          <div v-if="examSubmitted" class="exam-report-grid">
            <div class="report-item">
              <span>正确</span>
              <strong>{{ examCorrectCount }}</strong>
            </div>
            <div class="report-item">
              <span>错误</span>
              <strong>{{ examWrongCount }}</strong>
            </div>
            <div class="report-item">
              <span>未答</span>
              <strong>{{ examUnansweredCount }}</strong>
            </div>
            <div class="report-item">
              <span>用时</span>
              <strong>{{ formattedExamTime }}</strong>
            </div>
          </div>

          <button v-if="!examSubmitted" class="btn-primary full-width sidebar-submit" type="button" @click="$emit('request-submit-exam')">
            交卷
          </button>
          <button v-else class="btn-secondary full-width sidebar-submit" type="button" @click="$emit('back-workspace')">
            完成查看
          </button>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">

type AnswerValue = string | string[] | undefined

interface ReviewResult {
  feedback?: string
  improvement_hints?: string[]
}

interface ExamQuestion {
  id: string
  subject: string
  type: string
  difficulty?: string | null
  content: string
  options?: Record<string, string> | null
  answer: string
  analysis: string
  knowledge_points: string[]
}

const props = defineProps<{
  mode: 'config' | 'exam'
  form: { title: string; subject: string; difficulty: string; duration: number }
  typeCounts: { type: string; label: string; count: number }[]
  preview: Array<{ id: string; subject: string; type: string; difficulty?: string | null; content: string }>
  loading: boolean
  subjects: string[]
  difficulties: string[]
  expectedCount: number
  canStartExam: boolean
  examTitle: string
  examPaper: ExamQuestion[]
  examAnswers: Record<string, AnswerValue>
  examReview: Record<string, ReviewResult | null>
  examSubmitted: boolean
  examSubmitNoticeVisible: boolean
  currentExamIndex: number
  formattedExamTime: string
  examAnsweredCount: number
  examUnansweredCount: number
  examCorrectCount: number
  examWrongCount: number
  examScore: number
  examResultLevel: string
}>()

defineEmits<{
  (e: 'reset-form'): void
  (e: 'generate-preview'): void
  (e: 'start-exam'): void
  (e: 'select-exam-option', question: ExamQuestion, key: string): void
  (e: 'update-exam-answer', id: string, value: string): void
  (e: 'request-submit-exam'): void
  (e: 'cancel-submit-exam'): void
  (e: 'scroll-to-question', index: number): void
  (e: 'exit-exam'): void
  (e: 'back-workspace'): void
}>()

function difficultyClass(diff: string | null | undefined) {
  if (diff === '简单') return 'text-success'
  if (diff === '中等') return 'text-warning'
  if (!diff) return 'text-neutral'
  return 'text-danger'
}

function summarize(text: string) {
  return String(text || '').replace(/\s+/g, ' ').trim().slice(0, 120)
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

function isOptionQuestion(question: ExamQuestion) {
  return ['选择题', '单选题', '多选题', '判断题'].includes(question.type)
}

function getOptions(question: ExamQuestion) {
  if (question.type === '判断题') return { A: '正确', B: '错误' }
  return question.options || {}
}

function isSelected(answer: AnswerValue, key: string) {
  if (!answer) return false
  return Array.isArray(answer) ? answer.includes(key) : answer === key
}

function correctKeys(question: ExamQuestion) {
  let ansText = String(question.answer || '').trim()

  if (question.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确'].some((item) => upper.includes(item))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误'].some((item) => upper.includes(item))) ansText = 'B'
  }

  return ansText
    .split(/[、,，\s]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean)
}

function isCorrectOption(question: ExamQuestion, key: string) {
  return correctKeys(question).includes(key)
}

function normalizeAnswer(answer: AnswerValue): string[] {
  if (Array.isArray(answer)) {
    return answer.map((item) => String(item).trim().toUpperCase()).filter(Boolean)
  }

  return String(answer || '')
    .split(/[、,，\s]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean)
}

function hasAnswerData(answer: AnswerValue) {
  return normalizeAnswer(answer).length > 0
}

function evaluateAnswer(question: ExamQuestion, answer: AnswerValue) {
  if (isOptionQuestion(question)) {
    const user = normalizeAnswer(answer).sort()
    const std = correctKeys(question).sort()
    return user.length > 0 && user.length === std.length && user.every((item, index) => item === std[index])
  }

  const userText = formatUserAnswer(answer).trim().toLowerCase()
  const stdText = String(question.answer || '').trim().toLowerCase()

  if (!userText) return false
  if (!stdText) return userText.length > 4

  if (question.type === '填空题') return userText === stdText

  return userText.includes(stdText) || stdText.includes(userText)
}

function isExamCorrect(question: ExamQuestion) {
  return evaluateAnswer(question, props.examAnswers?.[question.id])
}

function formatUserAnswer(answer: AnswerValue) {
  return Array.isArray(answer) ? answer.join(',') : String(answer || '')
}

function formatAnswer(answer: string) {
  return String(answer || '').replace(/,/g, '、')
}

function formatExamAnswer(question: ExamQuestion, answer: AnswerValue) {
  if (!hasAnswerData(answer)) return '未作答'

  if (isOptionQuestion(question)) {
    const optionMap = getOptions(question)
    return normalizeAnswer(answer)
      .map((key) => `${key}. ${optionMap[key] || key}`)
      .join('；')
  }

  return formatUserAnswer(answer).trim() || '未作答'
}

function formatExamReferenceAnswer(question: ExamQuestion) {
  if (isOptionQuestion(question)) {
    const optionMap = getOptions(question)
    return correctKeys(question)
      .map((key) => `${key}. ${optionMap[key] || key}`)
      .join('；')
  }

  return formatAnswer(question.answer)
}

</script>

<style scoped>
.exam-shell {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  align-items: start;
}

.workspace-pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.config-workspace {
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.section-head.compact {
  align-items: center;
}

.section-kicker {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.section-head h3 {
  margin: 2px 0 0;
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.text-btn,
.secondary-btn,
.primary-btn,
.btn-primary,
.btn-secondary {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.text-btn,
.btn-secondary,
.secondary-btn {
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: #fff;
  color: #475569;
}

.primary-btn,
.btn-primary {
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #fff;
}

.primary-btn:disabled,
.secondary-btn:disabled,
.text-btn:disabled,
.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-row.compact-grid {
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) repeat(3, minmax(120px, 0.7fr));
  gap: 10px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-group label {
  color: #475569;
  font-size: 11px;
  font-weight: 700;
}

.field,
.count-input {
  width: 100%;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  box-sizing: border-box;
  outline: none;
}

.field:focus,
.count-input:focus,
.text-area-input:focus {
  border-color: rgba(148, 163, 184, 0.96);
}

.count-chip-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.count-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 12px;
  background: #fff;
}

.count-chip-labels {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.chip-name {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.chip-meta {
  color: #94a3b8;
  font-size: 11px;
}

.count-input {
  width: 72px;
  min-width: 72px;
  text-align: center;
}

.preview-count {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 4px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 12px;
  background: #fff;
}

.preview-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.preview-no {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.preview-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preview-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.preview-tag.type {
  background: #eff6f2;
  color: #288a6e;
}

.preview-tag.subject {
  background: #eef6ff;
  color: #3d78b5;
}

.preview-tag.difficulty {
  background: #dff2ff;
  color: #3487c7;
}

.preview-text {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
}

.preview-empty {
  padding: 14px 0 4px;
  color: #64748b;
}

.preview-empty strong {
  display: block;
  color: #0f172a;
  font-size: 14px;
  font-weight: 700;
}

.preview-empty p {
  margin: 6px 0 0;
  font-size: 13px;
}

.exam-workspace {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.exam-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  position: sticky;
  top: 0;
  z-index: 8;
  padding: 12px 0 14px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 251, 255, 0.96);
  backdrop-filter: blur(12px);
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
  align-items: start;
}

.exam-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
}

.exam-question.active {
  border-color: rgba(66, 201, 154, 0.36);
  box-shadow: 0 0 0 4px rgba(66, 201, 154, 0.08);
}

.exam-sidebar .panel {
  position: sticky;
  top: 20px;
  padding: 18px;
  border-radius: 16px;
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

.tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.tag.outline {
  background: #fff;
  color: #5f6b7c;
  border: 1px solid rgba(203, 213, 225, 0.92);
}

.tag.type {
  background: #eff6f2;
  color: #288a6e;
}

.question-text {
  margin-bottom: 26px;
  color: #273142;
  font-size: 17px;
  line-height: 1.9;
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
  border-color: rgba(66, 201, 154, 0.6);
  background: rgba(209, 250, 229, 0.5);
  box-shadow: 0 0 0 4px rgba(66, 201, 154, 0.08);
}

.option-btn.correct {
  border-color: rgba(16, 185, 129, 0.55);
  background: rgba(236, 253, 245, 0.98);
}

.option-btn.wrong {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(254, 242, 242, 0.98);
}

.opt-key {
  display: inline-flex;
  align-items: flex-start;
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
  flex: 1;
  text-align: left;
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
  border-radius: 14px;
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

.exam-answer-review {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 24px;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: #f8fafc;
  font-size: 15px;
}

.exam-answer-review.success {
  border-color: rgba(16, 185, 129, 0.28);
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.72), rgba(248, 250, 252, 0.96));
}

.exam-answer-review.danger {
  border-color: rgba(239, 68, 68, 0.24);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.7), rgba(248, 250, 252, 0.96));
}

.answer-review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.answer-review-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.answer-review-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.answer-review-value {
  color: #172033;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.answer-review-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.review-feedback {
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

.review-hints {
  padding: 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.review-hints strong,
.analysis-text strong {
  display: block;
  margin-bottom: 8px;
  color: #172033;
  font-size: 13px;
  font-weight: 800;
}

.review-hints ul {
  margin: 0;
  padding-left: 18px;
  color: #475569;
}

.review-hints li + li {
  margin-top: 6px;
}

.analysis-text {
  padding: 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.92);
  color: #4f5b6d;
  line-height: 1.7;
}

.submit-inline-notice {
  margin-bottom: 18px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(245, 158, 11, 0.22);
  background: rgba(254, 249, 195, 0.62);
}

.submit-inline-notice strong {
  display: block;
  color: #92400e;
  font-size: 13px;
  font-weight: 800;
}

.submit-inline-notice p {
  margin: 6px 0 0;
  color: #a16207;
  font-size: 13px;
  line-height: 1.6;
}

.submit-inline-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.exam-report-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.report-item {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(248, 250, 252, 0.96);
}

.report-item span {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.report-item strong {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 800;
}

.text-success {
  color: #059669;
}

.text-warning {
  color: #d97706;
}

.text-neutral {
  color: #64748b;
}

.text-danger {
  color: #dc2626;
}

@media (max-width: 960px) {
  .section-head.compact {
    align-items: flex-start;
  }

  .head-actions {
    width: 100%;
  }

  .field-row.compact-grid,
  .count-chip-row,
  .exam-main,
  .answer-review-grid {
    grid-template-columns: 1fr 1fr;
  }

  .exam-main {
    grid-template-columns: 1fr;
  }

  .exam-sidebar .panel {
    position: static;
  }

  .answer-review-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .head-actions,
  .field-row.compact-grid,
  .count-chip-row {
    grid-template-columns: 1fr;
  }

  .secondary-btn,
  .primary-btn,
  .text-btn,
  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .count-input {
    width: 64px;
    min-width: 64px;
  }

  .submit-inline-actions {
    flex-direction: column;
  }
}
</style>
