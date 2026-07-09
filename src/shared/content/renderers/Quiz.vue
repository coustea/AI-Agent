<template>
  <div class="quiz-resource" :class="{ compact }">
    <div v-if="questions.length" class="quiz-list">
      <div v-for="(question, index) in visibleQuestions" :key="index" class="quiz-item">
        <div class="quiz-stem">
          <span class="quiz-index">Q{{ index + 1 }}</span>
          <div class="quiz-title">
            <div class="quiz-meta-row">
              <span class="quiz-meta">{{ getQuestionTypeText(question.type || question.question_type) }}</span>
              <span class="quiz-difficulty" :class="question.difficulty?.toLowerCase()">
                {{ getDifficultyText(question.difficulty) }}
              </span>
            </div>
            <MarkdownRenderer
              class="quiz-text quiz-rich-text"
              :content="String(question.stem || question.question || '题目内容')"
            />
          </div>
        </div>

        <div
          v-if="isChoiceType(question) && Array.isArray(question.options) && question.options.length"
          class="quiz-options"
        >
          <div
            v-for="(option, optionIndex) in question.options"
            :key="optionIndex"
            class="quiz-option-item"
            :class="{
              'is-selected': isSelected(index, option, question),
              'is-correct': showAnswers[index] && isCorrectOption(option, question),
              'is-wrong': showAnswers[index] && isSelected(index, option, question) && !isCorrectOption(option, question),
              'is-readonly': showAnswers[index] || compact
            }"
            @click="!showAnswers[index] && !compact && toggleOption(index, option, question)"
          >
            <div class="option-check">
              <div class="check-box"></div>
              <span v-if="option.label" class="option-label">{{ option.label }}</span>
            </div>
            <MarkdownRenderer
              class="option-content quiz-rich-text"
              :content="String(typeof option === 'string' ? option : option.content || '')"
            />

            <div v-if="showAnswers[index]" class="option-status-wrap">
              <CheckIcon v-if="isCorrectOption(option, question)" class='w-4 h-4 inline-block align-middle correct' />
              <CloseIcon v-else-if="isSelected(index, option, question)" class='w-4 h-4 inline-block align-middle wrong' />
            </div>
          </div>
        </div>

        <div v-else-if="!isChoiceType(question) && !compact" class="quiz-short-answer">
          <textarea
            v-model="userAnswers[index]"
            class="short-answer-input"
            :disabled="showAnswers[index]"
            placeholder="请输入您的答案 / ENTER_YOUR_ANSWER..."
            rows="4"
          ></textarea>
        </div>

        <div v-if="!compact && !showAnswers[index]" class="quiz-actions">
          <div class="action-footer">
            <div v-if="!hasSelected(index)" class="hint-text">
              <span class="mono-blink">_</span> 等待作答... / AWAITING_INPUT
            </div>
            <div v-else class="hint-text active">已作答 / READY_TO_SUBMIT</div>

            <button
              class="hud-btn-primary"
              :disabled="!hasSelected(index)"
              @click="showAnswers[index] = true"
            >
              提交答案
            </button>
          </div>
        </div>

        <template v-if="!compact && showAnswers[index]">
          <div
            v-if="question.answer !== undefined && question.answer !== null && question.answer !== ''"
            class="quiz-answer"
          >
            <div class="answer-header">
              <span class="header-tag">TARGET</span>
              <span class="header-text">正确答案</span>
            </div>
            <div class="answer-content">
              <MarkdownRenderer
                class="quiz-rich-text"
                :content="String(Array.isArray(question.answer) ? question.answer.join(', ') : question.answer)"
              />
            </div>
          </div>

          <div
            v-if="question.explanation || question.analysis || question.reference_answer"
            class="quiz-explanation"
          >
            <div class="explanation-header">
              <span class="header-tag analysis">ANALYSIS</span>
              <span class="header-text">解析报告</span>
            </div>
            <div class="explanation-content">
              <div v-if="question.reference_answer" class="ref-answer">
                <div class="ref-label">参考内容 / REFERENCE:</div>
                <MarkdownRenderer
                  class="quiz-rich-text reference-answer-render"
                  :content="String(question.reference_answer)"
                />
              </div>
              <MarkdownRenderer
                class="analysis-text quiz-rich-text"
                :content="String(question.explanation || question.analysis || '')"
              />
            </div>
          </div>
        </template>
      </div>

      <div v-if="compact && questions.length > visibleQuestions.length" class="quiz-more">
        <button class="btn-link text-blue hover:underline more-btn-hud">
          查看全部题目 / VIEW_ALL ({{ questions.length }}) <ArrowRightIcon class='w-4 h-4 inline-block align-middle' />
        </button>
      </div>
    </div>

    <div v-else class="quiz-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>暂无测验数据 / NO_QUIZ_DATA</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PhCheck as CheckIcon,
  PhArrowRight as ArrowRightIcon,
  PhX as CloseIcon
} from '@phosphor-icons/vue'
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'
import { normalizeQuizQuestions, type ResourceArtifactLike } from '../artifact'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const questions = computed<Record<string, any>[]>(() => normalizeQuizQuestions(props.resultData))
const visibleQuestions = computed(() => (props.compact ? questions.value.slice(0, 2) : questions.value))

const userAnswers = ref<Record<number, any>>({})
const showAnswers = ref<Record<number, boolean>>({})

const isChoiceType = (q: any) => {
  const type = (q.type || q.question_type)?.toLowerCase() || ''
  return ['choice', 'single_choice', 'true_false'].includes(type)
}

const toggleOption = (qIndex: number, option: any, _question: any) => {
  const val = option.label || (typeof option === 'string' ? option : option.content)
  userAnswers.value[qIndex] = val
}

const isSelected = (qIndex: number, option: any, _question: any) => {
  const val = option.label || (typeof option === 'string' ? option : option.content)
  return userAnswers.value[qIndex] === val
}

const hasSelected = (qIndex: number) => {
  const ans = userAnswers.value[qIndex]
  if (Array.isArray(ans)) return ans.length > 0
  return ans !== undefined && ans !== null && ans !== ''
}

const isCorrectOption = (option: any, question: any) => {
  if (question.answer === undefined || question.answer === null) return false
  const val = option.label || (typeof option === 'string' ? option : option.content)
  const type = (question.type || question.question_type)?.toLowerCase() || ''
  if (type === 'true_false' && typeof question.answer === 'boolean') {
    return val === (question.answer ? 'A' : 'B')
  }
  if (Array.isArray(question.answer)) {
    return question.answer.includes(val)
  }
  return String(question.answer).toLowerCase() === String(val).toLowerCase()
}

const getDifficultyText = (difficulty?: string) => {
  switch (difficulty?.toLowerCase()) {
    case 'easy':
    case 'basic':
      return '基础'
    case 'medium':
    case 'intermediate':
      return '进阶'
    case 'hard':
    case 'advanced':
    case 'challenge':
      return '挑战'
    default:
      return '练习'
  }
}

const getQuestionTypeText = (questionType?: string) => {
  switch (questionType?.toLowerCase()) {
    case 'single_choice':
    case 'choice':
      return '单选'
    case 'true_false':
      return '判断'
    case 'fill_blank':
    case 'blank':
      return '填空'
    default:
      return '题目'
  }
}
</script>

<style scoped>
.quiz-resource {
  width: 100%;
  --primary: var(--color-primary);
  --bg: var(--color-surface);
  --fg: var(--color-text);
  --border: var(--color-border);
  --accent: var(--color-primary);
  --success: var(--color-success);
  --error: var(--color-danger);
}

.quiz-list {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.quiz-item {
  padding: 24px;
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.quiz-stem {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.quiz-index {
  font-family: var(--font-sans);
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--color-primary-text);
  line-height: 1.1;
}

.quiz-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.quiz-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quiz-meta,
.quiz-difficulty {
  font-family: var(--font-sans);
  font-size: 0.65rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  letter-spacing: 0.5px;
}

.quiz-meta {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border: 1px solid var(--color-border);
}

.quiz-difficulty {
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}

.quiz-difficulty.hard,
.quiz-difficulty.challenge {
  border-color: var(--color-danger-border);
  color: var(--color-danger);
  background: var(--color-danger-soft);
}

.quiz-difficulty.medium,
.quiz-difficulty.intermediate {
  border-color: var(--color-warning-border);
  color: var(--color-warning-text, #D97706);
  background: var(--color-warning-soft, #FFFBEB);
}

.quiz-text {
  font-family: var(--font-sans);
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--color-text-strong);
  line-height: 1.6;
}

.quiz-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-left: 56px;
}

.quiz-option-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: #ffffff;
  border: 1px solid var(--color-border) !important;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.32, 0.72, 0, 1);
  box-shadow: var(--shadow-sm);
}

.quiz-option-item:not(.is-readonly):hover {
  border-color: var(--color-primary-border) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* Selected option: uses Tutor Blue as the minor auxiliary accent color */
.quiz-option-item.is-selected {
  border-color: var(--cat-tutor, #1E40AF) !important;
  background: var(--cat-tutor-soft, #EFF6FF) !important;
}

.option-check {
  display: flex;
  align-items: center;
  gap: 10px;
}

.check-box {
  width: 16px;
  height: 16px;
  border: 1.5px solid var(--color-border);
  border-radius: 4px;
  background: #ffffff;
  transition: all 0.15s ease;
}

.is-selected .check-box {
  background: var(--cat-tutor, #1E40AF);
  border-color: var(--cat-tutor, #1E40AF);
}

.option-label {
  font-family: var(--font-sans);
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.option-content {
  font-family: var(--font-sans);
  font-size: 0.95rem;
  color: var(--color-text);
  flex: 1;
  min-width: 0;
}

/* State highlights: Solid backgrounds with correct borders */
.quiz-option-item.is-correct {
  border-color: var(--color-success-border, #A7F3D0) !important;
  background: var(--color-success-soft, #ECFDF5) !important;
}

.is-correct .check-box {
  background: var(--color-success);
  border-color: var(--color-success);
}

.quiz-option-item.is-wrong {
  border-color: var(--color-danger-border, #FECACA) !important;
  background: var(--color-danger-soft, #FEF2F2) !important;
}

.is-wrong .check-box {
  background: var(--color-danger);
  border-color: var(--color-danger);
}

.option-status-wrap {
  display: flex;
  align-items: center;
  font-size: 1.2rem;
}

.correct {
  color: var(--color-success);
}

.wrong {
  color: var(--color-danger);
}

.quiz-actions {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border);
}

.action-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--color-text-muted);
  letter-spacing: 0.5px;
}

.hint-text.active {
  color: var(--color-primary-text);
  font-weight: 600;
}

.mono-blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

/* System standard rectangular primary button */
.hud-btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 0 var(--space-4);
  background: var(--color-primary);
  color: white;
  border: 1px solid var(--color-primary);
  font-family: var(--font-sans);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--btn-transition);
  letter-spacing: 0.5px;
}

.hud-btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  transform: translateY(-0.5px);
}

.hud-btn-primary:active:not(:disabled) {
  transform: translateY(0.5px);
}

.hud-btn-primary:disabled {
  background: var(--color-surface-hover);
  border-color: var(--color-border);
  color: var(--color-text-faint);
  cursor: not-allowed;
}

/* Solid white cards for answers and explanations */
.quiz-answer,
.quiz-explanation {
  margin-top: 20px;
  padding: 20px;
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.header-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  background: var(--color-primary);
  color: white;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  margin-right: 10px;
}

.header-tag.analysis {
  background: var(--color-primary-text);
}

.header-text {
  font-family: var(--font-sans);
  font-size: 0.9rem;
  color: var(--color-text-strong);
  font-weight: 700;
}

.answer-content {
  margin-top: 12px;
  margin-left: 20px;
  font-family: var(--font-mono);
  font-size: 1.1rem;
  color: var(--color-success);
  font-weight: 700;
}

.explanation-content {
  margin-top: 12px;
  color: var(--color-text-secondary);
}

.ref-label {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-primary-text);
  margin-bottom: 8px;
}

.analysis-text {
  font-family: var(--font-sans);
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--color-text);
}

.quiz-short-answer {
  margin-left: 56px;
  margin-top: 16px;
}

.short-answer-input {
  width: 100%;
  padding: 16px;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  color: var(--color-text-strong);
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  resize: vertical;
  transition: all 0.2s ease;
  line-height: 1.5;
}

.short-answer-input:focus {
  outline: none;
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-sm);
}

.short-answer-input:disabled {
  background: var(--color-surface-hover);
  color: var(--color-text-faint);
  cursor: not-allowed;
}

.more-btn-hud {
  width: 100%;
  margin-top: 16px;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 600;
}

.quiz-empty-hud {
  padding: 60px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px solid var(--color-border);
  background: #ffffff;
  padding: 40px 60px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  color: var(--color-primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: var(--font-sans);
  font-size: 0.8rem;
  color: var(--color-text-faint);
}

.quiz-rich-text {
  min-width: 0;
}

.quiz-rich-text :deep(p) {
  margin: 0;
}

.quiz-rich-text :deep(p + p) {
  margin-top: 0.6em;
}

.quiz-rich-text :deep(.katex-display) {
  margin: 0.8em 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.quiz-rich-text :deep(pre) {
  margin: 0.75em 0 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.quiz-rich-text :deep(code) {
  white-space: pre-wrap;
}

.quiz-rich-text :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.quiz-rich-text :deep(td),
.quiz-rich-text :deep(th) {
  padding: 4px 8px;
}

.reference-answer-render {
  margin-top: 8px;
}

.compact .quiz-item {
  padding: 16px;
  border: 1px solid var(--color-border);
  background: #ffffff;
  box-shadow: none;
}

.compact .quiz-stem {
  gap: 16px;
  margin-bottom: 16px;
}

.compact .quiz-index {
  font-size: 1.4rem;
}

.compact .quiz-options {
  margin-left: 36px;
  gap: 8px;
}

.compact .quiz-option-item {
  padding: 10px 16px;
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .quiz-options {
    margin-left: 0;
  }
  .quiz-short-answer {
    margin-left: 0;
  }
}
</style>
