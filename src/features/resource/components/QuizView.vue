<template>
  <div class="quiz-resource" :class="{ compact }">
    <div v-if="questions.length" class="quiz-list">
      <ResourceCardWrapper v-for="(question, index) in visibleQuestions" :key="index" :compact="compact" class="quiz-item">
        <div class="quiz-stem">
          <span class="quiz-index">Q{{ index + 1 }}</span>
          <div class="quiz-title">
            <div class="quiz-meta-row">
              <span class="quiz-meta">{{ getQuestionTypeText(question.type || question.question_type) }}</span>
              <span class="quiz-difficulty" :class="question.difficulty?.toLowerCase()">
                {{ getDifficultyText(question.difficulty) }}
              </span>
            </div>
            <div
              class="quiz-text quiz-rich-text"
              v-html="renderQuizHtml(question.stem || question.question || '题目内容')"
            ></div>
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
            <div
              class="option-content quiz-rich-text"
              v-html="renderQuizHtml(typeof option === 'string' ? option : option.content)"
            ></div>

            <div v-if="showAnswers[index]" class="option-status-wrap">
              <Select class='w-4 h-4 inline-block align-middle' />
              <Close class='w-4 h-4 inline-block align-middle' />
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
          <div v-if="question.answer" class="quiz-answer">
            <div class="answer-header">
              <span class="header-tag">TARGET</span>
              <span class="header-text">正确答案</span>
            </div>
            <div class="answer-content">
              <div
                class="quiz-rich-text"
                v-html="renderQuizHtml(Array.isArray(question.answer) ? question.answer.join(', ') : question.answer)"
              ></div>
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
                <div
                  class="quiz-rich-text reference-answer-render"
                  v-html="renderQuizHtml(question.reference_answer)"
                ></div>
              </div>
              <div
                class="analysis-text quiz-rich-text"
                v-html="renderQuizHtml(question.explanation || question.analysis)"
              ></div>
            </div>
          </div>
        </template>
      </ResourceCardWrapper>

      <div v-if="compact && questions.length > visibleQuestions.length" class="quiz-more">
        <button class="btn-link text-blue hover:underline more-btn-hud">
          查看全部题目 / VIEW_ALL ({{ questions.length }}) <ArrowRight class='w-4 h-4 inline-block align-middle' />
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
  PhCheck as Select,
  PhArrowRight as ArrowRight,
  PhX as Close
} from '@phosphor-icons/vue'
import { renderStreamingMarkdownHtml } from '@/shared/utils/markdown'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import { normalizeQuizQuestions, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const questions = computed<Record<string, any>[]>(() => normalizeQuizQuestions(props.resultData))
const visibleQuestions = computed(() => (props.compact ? questions.value.slice(0, 2) : questions.value))

const userAnswers = ref<Record<number, any>>({})
const showAnswers = ref<Record<number, boolean>>({})

const renderQuizHtml = (content?: string) => {
  const text = String(content || '').trim()
  if (!text) return ''
  return renderStreamingMarkdownHtml(text)
}

const isChoiceType = (q: any) => {
  const type = (q.type || q.question_type)?.toLowerCase() || ''
  return ['choice', 'single_choice', 'multiple_choice', 'true_false'].includes(type)
}

const isMultipleChoice = (q: any) => {
  const type = (q.type || q.question_type)?.toLowerCase() || ''
  return type === 'multiple_choice'
}

const toggleOption = (qIndex: number, option: any, question: any) => {
  const val = option.label || (typeof option === 'string' ? option : option.content)
  if (isMultipleChoice(question)) {
    const current = userAnswers.value[qIndex] || []
    const idx = current.indexOf(val)
    userAnswers.value[qIndex] = idx > -1 ? current.filter((v: any) => v !== val) : [...current, val]
    return
  }
  userAnswers.value[qIndex] = val
}

const isSelected = (qIndex: number, option: any, question: any) => {
  const val = option.label || (typeof option === 'string' ? option : option.content)
  if (isMultipleChoice(question)) {
    return (userAnswers.value[qIndex] || []).includes(val)
  }
  return userAnswers.value[qIndex] === val
}

const hasSelected = (qIndex: number) => {
  const ans = userAnswers.value[qIndex]
  if (Array.isArray(ans)) return ans.length > 0
  return ans !== undefined && ans !== null && ans !== ''
}

const isCorrectOption = (option: any, question: any) => {
  if (!question.answer) return false
  const val = option.label || (typeof option === 'string' ? option : option.content)
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
    case 'multiple_choice':
      return '多选'
    case 'true_false':
      return '判断'
    case 'blank':
      return '填空'
    case 'short_answer':
      return '简答'
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

.quiz-stem {
  display: flex;
  gap: 24px;
  margin-bottom: 28px;
}

.quiz-index {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 400;
  color: var(--primary);
  line-height: 1;
  opacity: 0.8;
}

.quiz-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.quiz-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quiz-meta,
.quiz-difficulty {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 2px;
  letter-spacing: 1px;
}

.quiz-meta {
  background: var(--primary);
  color: white;
}

.quiz-difficulty {
  border: 1px solid var(--primary);
  color: var(--primary);
}

.quiz-difficulty.hard,
.quiz-difficulty.challenge {
  border-color: var(--error);
  color: var(--error);
}

.quiz-text {
  font-family: var(--font-mono);
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--fg);
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
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quiz-option-item:not(.is-readonly):hover {
  background: rgba(0, 0, 0, 0.03);
  transform: translateX(4px);
}

.quiz-option-item.is-selected {
  background: rgba(0, 0, 0, 0.04);
}

.option-check {
  display: flex;
  align-items: center;
  gap: 10px;
}

.check-box {
  width: 14px;
  height: 14px;
  border: 1px solid var(--border);
  border-radius: 2px;
  transition: all 0.2s;
}

.is-selected .check-box {
  background: var(--accent);
  border-color: var(--accent);
  box-shadow: none;
}

.option-label {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--primary);
}

.option-content {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--fg);
  flex: 1;
  min-width: 0;
}

.quiz-option-item.is-correct {
  background: rgba(16, 185, 129, 0.08);
}

.is-correct .check-box {
  background: var(--success);
  border-color: var(--success);
}

.quiz-option-item.is-wrong {
  background: rgba(239, 68, 68, 0.08);
}

.is-wrong .check-box {
  background: var(--error);
  border-color: var(--error);
}

.option-status-wrap {
  display: flex;
  align-items: center;
  font-size: 1.2rem;
}

.correct {
  color: var(--success);
}

.wrong {
  color: var(--error);
}

.quiz-actions {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px dashed var(--border);
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
  letter-spacing: 1px;
}

.hint-text.active {
  color: var(--accent);
}

.mono-blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.hud-btn-primary {
  background: var(--accent);
  color: white;
  border: none;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  padding: 10px 24px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.hud-btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.hud-btn-primary:disabled {
  background: var(--color-border-hover);
  cursor: not-allowed;
  color: var(--color-text-faint);
}

.quiz-answer,
.quiz-explanation {
  margin-top: 20px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.02);
  border: none;
  border-radius: 8px;
}

.header-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  background: var(--accent);
  color: white;
  padding: 2px 6px;
  margin-right: 10px;
}

.header-tag.analysis {
  background: var(--primary);
}

.header-text {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--fg);
  font-weight: 700;
}

.answer-content {
  margin-top: 12px;
  margin-left: 20px;
  font-family: var(--font-mono);
  font-size: 1.1rem;
  color: var(--success);
  font-weight: 700;
}

.explanation-content {
  margin-top: 12px;
  color: var(--color-text-secondary);
}

.ref-label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--primary);
  margin-bottom: 8px;
}

.analysis-text {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  line-height: 1.6;
}

.quiz-short-answer {
  margin-left: 56px;
  margin-top: 16px;
}

.short-answer-input {
  width: 100%;
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--fg);
  background: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  resize: vertical;
  transition: all 0.2s ease;
  line-height: 1.5;
}

.short-answer-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.05);
}

.short-answer-input:disabled {
  background: rgba(0, 0, 0, 0.03);
  color: var(--color-text-muted);
  cursor: not-allowed;
}

.more-btn-hud {
  width: 100%;
  margin-top: 16px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  letter-spacing: 1px;
}

.quiz-empty-hud {
  padding: 60px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: none;
  background: rgba(0, 0, 0, 0.02);
  padding: 40px 60px;
  border-radius: 8px;
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-text-faint);
  letter-spacing: 1px;
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
  padding: 0;
  border: none;
  background: transparent;
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
</style>
