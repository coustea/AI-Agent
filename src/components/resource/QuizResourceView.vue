<template>
  <div class="quiz-resource" :class="{ compact }">
    <div v-if="questions.length" class="quiz-list">
      <article v-for="(question, index) in visibleQuestions" :key="index" class="technical-frame quiz-item">

        <div class="frame-header">
          <div class="status-indicator"></div>
          <span class="technical-label">TECHNICAL_QUIZ // MODULE_{{ (index + 1).toString().padStart(2, '0') }}</span>
        </div>

        <div class="quiz-stem">
          <span class="quiz-index">Q{{ index + 1 }}</span>
          <div class="quiz-title">
            <div class="quiz-meta-row">
              <span class="quiz-meta">{{ getQuestionTypeText(question.type || question.question_type) }}</span>
              <span class="quiz-difficulty" :class="question.difficulty?.toLowerCase()">{{ getDifficultyText(question.difficulty) }}</span>
            </div>
            <span class="quiz-text">{{ question.stem || question.question || '题目内容' }}</span>
          </div>
        </div>
        
        <div v-if="Array.isArray(question.options) && question.options.length" class="quiz-options">
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
              <span class="option-label" v-if="option.label">{{ option.label }}</span>
            </div>
            <span class="option-content">{{ typeof option === 'string' ? option : option.content }}</span>
            
            <div class="option-status-wrap" v-if="showAnswers[index]">
              <el-icon v-if="isCorrectOption(option, question)" class="status-icon correct"><Select /></el-icon>
              <el-icon v-if="isSelected(index, option, question) && !isCorrectOption(option, question)" class="status-icon wrong"><Close /></el-icon>
            </div>
          </div>
        </div>

        <!-- 作答区与查看答案按钮 -->
        <div v-if="!compact && !showAnswers[index]" class="quiz-actions">
          <div class="action-footer">
            <div class="hint-text" v-if="isChoiceType(question) && !hasSelected(index)">
              <span class="mono-blink">_</span> AWAITING_SELECTION...
            </div>
            <div class="hint-text active" v-else-if="isChoiceType(question) && hasSelected(index)">
              SYSTEM_READY: SUBMIT_AUTHORIZED
            </div>
            
            <button 
              class="hud-btn-primary" 
              @click="showAnswers[index] = true" 
              :disabled="isChoiceType(question) && !hasSelected(index)"
            >
              {{ isChoiceType(question) ? 'EXECUTE: SUBMIT' : 'EXECUTE: REVEAL_ANALYSIS' }}
            </button>
          </div>
        </div>

        <template v-if="!compact && showAnswers[index]">
          <div v-if="question.answer" class="quiz-answer">
            <div class="answer-header">
              <span class="header-tag">TARGET_VALUE</span>
              <span class="header-text">正确答案</span>
            </div>
            <div class="answer-content">
              {{ Array.isArray(question.answer) ? question.answer.join(', ') : question.answer }}
            </div>
          </div>

          <div v-if="question.explanation || question.analysis || question.reference_answer" class="quiz-explanation">
            <div class="explanation-header">
              <span class="header-tag analysis">SYSTEM_LOG</span>
              <span class="header-text">解析报告</span>
            </div>
            <div class="explanation-content">
              <div v-if="question.reference_answer" class="ref-answer">
                <div class="ref-label">REFERENCE_ARTIFACT:</div>
                <pre><code>{{ question.reference_answer }}</code></pre>
              </div>
              <div class="analysis-text">{{ question.explanation || question.analysis }}</div>
            </div>
          </div>
        </template>
      </article>
      
      <div v-if="compact && questions.length > visibleQuestions.length" class="quiz-more">
        <el-button type="primary" link class="more-btn-hud">
          ACCESS_ALL_MODULES ({{ questions.length }}) <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div v-else class="quiz-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>NO_QUIZ_DATA_FOUND</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Select, ArrowRight, Close } from '@element-plus/icons-vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const questions = computed<Record<string, any>[]>(() => {
  if (!props.resultData || typeof props.resultData !== 'object') return []

  // 1. 直层级 resource.content.questions
  if (props.resultData.resource?.content?.questions && Array.isArray(props.resultData.resource.content.questions)) {
    return props.resultData.resource.content.questions
  }
  
  // 2. 直层级 questions
  if (Array.isArray(props.resultData.questions)) {
    return props.resultData.questions
  }

  // 3. content 是嵌套 JSON 字符串的情况
  const parsedContent = parseJsonObject(props.resultData.content)
  if (parsedContent?.questions && Array.isArray(parsedContent.questions)) {
    return parsedContent.questions
  }

  // 4. raw_json 字段
  const parsedRawJson = parseJsonObject(props.resultData.raw_json)
  if (parsedRawJson?.questions && Array.isArray(parsedRawJson.questions)) {
    return parsedRawJson.questions
  }

  return []
})

const visibleQuestions = computed(() => props.compact ? questions.value.slice(0, 2) : questions.value)

// --- 交互与作答状态 ---
const userAnswers = ref<Record<number, any>>({})
const showAnswers = ref<Record<number, boolean>>({})

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
    if (idx > -1) {
      userAnswers.value[qIndex] = current.filter((v: any) => v !== val)
    } else {
      userAnswers.value[qIndex] = [...current, val]
    }
  } else {
    userAnswers.value[qIndex] = val
  }
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
    case 'basic': return '基础'
    case 'medium':
    case 'intermediate': return '进阶'
    case 'hard':
    case 'advanced':
    case 'challenge': return '挑战'
    default: return '练习'
  }
}

const getQuestionTypeText = (questionType?: string) => {
  switch (questionType?.toLowerCase()) {
    case 'single_choice':
    case 'choice': return '单选'
    case 'multiple_choice': return '多选'
    case 'true_false': return '判断'
    case 'blank': return '填空'
    case 'short_answer': return '简答'
    default: return '题目'
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.quiz-resource {
  width: 100%;
  --primary: #000000;
  --bg: #FFFFFF;
  --fg: #000000;
  --border: #E5E7EB;
  --accent: #000000;
}

.quiz-list {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* 技术框架样式 */
.technical-frame {
  position: relative;
  background: var(--bg);
  border: none;
  border-radius: 4px;
  padding: 40px 32px 32px;
  box-shadow: none;
  transition: all 0.3s ease;
}

.frame-corners {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--primary);
  pointer-events: none;
}

.top-left { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.top-right { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bottom-left { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.bottom-right { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

.frame-header {
  position: absolute;
  top: 12px;
  left: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: none;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.technical-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: var(--primary);
  letter-spacing: 1px;
}

/* 题目干样式 */
.quiz-stem {
  display: flex;
  gap: 24px;
  margin-bottom: 28px;
}

.quiz-index {
  font-family: 'Share Tech Mono', monospace;
  font-size: 1.8rem;
  font-weight: normal;
  color: var(--primary);
  line-height: 1;
  opacity: 0.8;
}

.quiz-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quiz-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quiz-meta, .quiz-difficulty {
  font-family: 'Share Tech Mono', monospace;
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

.quiz-difficulty.hard, .quiz-difficulty.challenge {
  border-color: #000000;
  color: #000000;
}

.quiz-text {
  font-family: 'Fira Code', monospace;
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--fg);
  line-height: 1.6;
}

/* 选项样式 */
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
  background: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.quiz-option-item:not(.is-readonly):hover {
  background: rgba(0, 0, 0, 0.03);
  border-color: var(--primary);
  transform: translateX(4px);
}

.quiz-option-item.is-selected {
  background: rgba(0, 0, 0, 0.05);
  border-color: var(--primary);
  box-shadow: none;
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
  background: var(--primary);
  border-color: var(--primary);
  box-shadow: none;
}

.option-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.9rem;
  font-weight: bold;
  color: var(--primary);
}

.option-content {
  font-family: 'Fira Code', monospace;
  font-size: 0.95rem;
  color: var(--fg);
  flex: 1;
}

/* 状态样式 */
.quiz-option-item.is-correct {
  border-color: var(--accent);
  background: rgba(0, 0, 0, 0.05);
}
.is-correct .check-box { background: var(--accent); border-color: var(--accent); box-shadow: none; }

.quiz-option-item.is-wrong {
  border-color: #000000;
  background: rgba(0, 0, 0, 0.05);
}
.is-wrong .check-box { background: #000000; border-color: #000000; box-shadow: none; }

.option-status-wrap {
  display: flex;
  align-items: center;
  font-size: 1.2rem;
}
.correct { color: var(--accent); }
.wrong { color: #000000; }

/* 动作区 */
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
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  color: #64748B;
  letter-spacing: 1px;
}

.hint-text.active {
  color: var(--accent);
}

.mono-blink {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.hud-btn-primary {
  background: var(--primary);
  color: white;
  border: none;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.85rem;
  padding: 10px 24px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.hud-btn-primary:hover:not(:disabled) {
  opacity: 0.9;
  box-shadow: none;
}

.hud-btn-primary:disabled {
  background: #000000;
  cursor: not-allowed;
  color: #94A3B8;
}

/* 答案与解析 */
.quiz-answer {
  margin-top: 28px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}

.header-tag {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  background: var(--accent);
  color: white;
  padding: 2px 6px;
  margin-right: 10px;
}

.header-text {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.9rem;
  color: var(--fg);
  font-weight: bold;
}

.answer-content {
  margin-top: 12px;
  margin-left: 20px;
  font-family: 'Fira Code', monospace;
  font-size: 1.1rem;
  color: var(--accent);
  font-weight: bold;
}

.quiz-explanation {
  margin-top: 16px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}

.header-tag.analysis {
  background: var(--primary);
}

.explanation-content {
  margin-top: 12px;
  color: #475569;
}

.ref-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  color: var(--primary);
  margin-bottom: 8px;
}

.ref-answer pre {
  margin: 0 0 16px 0;
  padding: 16px;
  background: #FFFFFF;
  border: 1px solid #334155;
  border-radius: 6px;
  overflow: auto;
}

.ref-answer code {
  font-family: 'Fira Code', monospace;
  color: #000000;
  font-size: 0.85rem;
}

.analysis-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.95rem;
  line-height: 1.6;
}

/* 更多按钮 */
.more-btn-hud {
  width: 100%;
  margin-top: 16px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.85rem;
  letter-spacing: 1px;
}

/* 空状态 */
.quiz-empty-hud {
  padding: 60px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px dashed var(--border);
  padding: 40px 60px;
  border-radius: 4px;
}

.empty-icon {
  font-family: 'Share Tech Mono', monospace;
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  color: #94A3B8;
  letter-spacing: 1px;
}

/* 紧凑模式 */
.compact .technical-frame {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}
.compact .frame-header {
  display: none;
}
.compact .quiz-stem { gap: 16px; margin-bottom: 16px; }
.compact .quiz-index { font-size: 1.4rem; }
.compact .quiz-options { margin-left: 36px; gap: 8px; }
.compact .quiz-option-item { padding: 10px 16px; font-size: 0.85rem; }
</style>
