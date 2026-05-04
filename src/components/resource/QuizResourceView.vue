<template>
  <div class="quiz-resource" :class="{ compact }">
    <div v-if="questions.length" class="quiz-list">
      <article v-for="(question, index) in visibleQuestions" :key="index" class="quiz-item">
        <div class="quiz-stem">
          <span class="quiz-index">Q{{ index + 1 }}</span>
          <div class="quiz-title">
            <span class="quiz-meta">
              {{ getDifficultyText(question.difficulty) }} · {{ getQuestionTypeText(question.type || question.question_type) }}
            </span>
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
            <span class="option-label" v-if="option.label">{{ option.label }}.</span>
            <span class="option-content">{{ typeof option === 'string' ? option : option.content }}</span>
            <el-icon v-if="showAnswers[index] && isCorrectOption(option, question)" class="status-icon correct-icon"><Select /></el-icon>
            <el-icon v-if="showAnswers[index] && isSelected(index, option, question) && !isCorrectOption(option, question)" class="status-icon wrong-icon"><Close /></el-icon>
          </div>
        </div>

        <!-- 作答区与查看答案按钮 -->
        <div v-if="!compact && !showAnswers[index]" class="quiz-actions">
          <div class="hint-text" v-if="isChoiceType(question) && !hasSelected(index)">请选择您认为正确的选项</div>
          <div class="hint-text" v-else-if="!isChoiceType(question)">请独立思考后再查看参考答案</div>
          <el-button type="primary" round @click="showAnswers[index] = true" :disabled="isChoiceType(question) && !hasSelected(index)">
            <el-icon><Check /></el-icon> {{ isChoiceType(question) ? '提交并查看答案' : '查看答案解析' }}
          </el-button>
        </div>

        <template v-if="!compact && showAnswers[index]">
          <div v-if="question.answer" class="quiz-answer">
            <div class="answer-header">
              <el-icon><Select /></el-icon> 正确答案
            </div>
            <div class="answer-content">
              {{ Array.isArray(question.answer) ? question.answer.join(', ') : question.answer }}
            </div>
          </div>

          <div v-if="question.explanation || question.analysis || question.reference_answer" class="quiz-explanation">
            <div class="explanation-header">
              <el-icon><Reading /></el-icon> 答案解析
            </div>
            <div class="explanation-content">
              <div v-if="question.reference_answer" class="ref-answer">
                <div class="ref-label">参考代码 / 要点</div>
                <pre>{{ question.reference_answer }}</pre>
              </div>
              <div class="analysis-text">{{ question.explanation || question.analysis }}</div>
            </div>
          </div>
        </template>
      </article>
      
      <div v-if="compact && questions.length > visibleQuestions.length" class="quiz-more">
        <el-button type="primary" link size="small" class="more-btn">
          查看全部 {{ questions.length }} 道专项练习题 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
    <div v-else-if="!questions.length && fallbackJson !== '{}'" class="quiz-json">
      <pre><code>{{ fallbackJson }}</code></pre>
    </div>
    <div v-else class="quiz-empty">
      <el-empty description="暂未生成练习题数据" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Select, Reading, ArrowRight, Check, Close } from '@element-plus/icons-vue'
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
const fallbackJson = computed(() => JSON.stringify(props.resultData || {}, null, 2))

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
// --- 状态结束 ---

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
    case 'choice': return '单选题'
    case 'multiple_choice': return '多选题'
    case 'true_false': return '判断题'
    case 'blank': return '填空题'
    case 'short_answer': return '简答题'
    default: return '题目'
  }
}
</script>

<style scoped>
.quiz-resource {
  width: 100%;
}

.quiz-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.quiz-item {
  padding: 28px;
  border: 1px solid #E2E8F0;
  border-radius: 20px;
  background: #FFFFFF;
  transition: border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.quiz-item:hover {
  border-color: #3B82F6;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  transform: translateX(4px);
}

.quiz-stem {
  display: flex;
  gap: 20px;
  color: #0F172A;
  font-size: 1.15rem;
  line-height: 1.6;
  margin-bottom: 24px;
}

.quiz-title {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.quiz-meta {
  align-self: flex-start;
  padding: 4px 12px;
  background: #F0F7FF;
  border-radius: 8px;
  color: #3B82F6;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  border: 1px solid #DBEAFE;
}

.quiz-text {
  font-weight: 700;
}

.quiz-index {
  flex: 0 0 auto;
  color: #3B82F6;
  font-size: 1.5rem;
  font-weight: 900;
  font-family: 'JetBrains Mono', monospace;
}

.quiz-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-left: 52px;
}

.quiz-option-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border: 2px solid #F1F5F9;
  border-radius: 14px;
  background: #FAFAFA;
  color: #475569;
  font-size: 1.05rem;
  line-height: 1.5;
  transition: background-color 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1), color 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.quiz-option-item:not(.is-readonly):hover {
  background: #F0F7FF;
  border-color: #3B82F6;
  color: #0F172A;
}

.quiz-option-item.is-selected {
  background: #EFF6FF;
  border-color: #3B82F6;
  color: #0F172A;
  font-weight: 700;
}

.quiz-option-item.is-correct {
  background: #F0FDF4;
  border-color: #10B981;
  color: #065F46;
  font-weight: 700;
}

.quiz-option-item.is-wrong {
  background: #FEF2F2;
  border-color: #EF4444;
  color: #991B1B;
  font-weight: 700;
}

.quiz-answer {
  margin-top: 28px;
  padding-top: 28px;
  border-top: 2px dashed #F1F5F9;
}

.answer-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #10B981;
  font-size: 1rem;
  font-weight: 900;
  margin-bottom: 16px;
}

.answer-content {
  color: #065F46;
  font-size: 1.1rem;
  font-weight: 800;
  margin-left: 36px;
  background: #DCFCE7;
  display: inline-block;
  padding: 8px 20px;
  border-radius: 10px;
}

.quiz-explanation {
  margin-top: 24px;
  padding: 24px;
  background: #F8FAFC;
  border-radius: 16px;
  border: 1px solid #E2E8F0;
}

.explanation-header {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #3B82F6;
  font-size: 1rem;
  font-weight: 900;
  margin-bottom: 16px;
}

.explanation-content {
  color: #475569;
  font-size: 1.05rem;
  line-height: 1.7;
}

.ref-answer pre {
  margin: 0 0 16px 0;
  padding: 20px;
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  border-radius: 14px;
  font-size: 0.95rem;
  color: #1E293B;
  font-family: 'JetBrains Mono', monospace;
}

.quiz-json {
  margin: 0;
  padding: 24px;
  border-radius: 16px;
  background: #F8FAFC;
  color: #64748B;
  border: 1px solid #E2E8F0;
}

.quiz-empty {
  padding: 40px;
}

.compact .quiz-item {
  padding: 20px;
}

.compact .quiz-stem {
  margin-bottom: 16px;
  font-size: 1rem;
}

.compact .quiz-index {
  font-size: 1.2rem;
}

.compact .quiz-options {
  margin-left: 36px;
  gap: 8px;
}

.compact .quiz-option-item {
  padding: 10px 16px;
  font-size: 0.9rem;
}
</style>
