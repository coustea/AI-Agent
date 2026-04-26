<template>
  <div class="quiz-resource" :class="{ compact }">
    <div v-if="questions.length" class="quiz-list">
      <article v-for="(question, index) in visibleQuestions" :key="index" class="quiz-item">
        <div class="quiz-stem">
          <span class="quiz-index">Q{{ index + 1 }}</span>
          <div class="quiz-title">
            <span class="quiz-meta">{{ getDifficultyText(question.difficulty) }} · {{ getQuestionTypeText(question.question_type) }}</span>
            <span>{{ question.stem || question.question || '题目内容' }}</span>
          </div>
        </div>
        <div v-if="Array.isArray(question.options) && question.options.length" class="quiz-options">
          <span v-for="(option, optionIndex) in question.options" :key="optionIndex">{{ option }}</span>
        </div>
        <div v-if="!compact && question.answer" class="quiz-answer">
          <strong>答案:</strong> {{ question.answer }}
        </div>
        <div v-if="!compact && (question.explanation || question.analysis)" class="quiz-explanation">
          <strong>解析:</strong> {{ question.explanation || question.analysis }}
        </div>
      </article>
      <div v-if="compact && questions.length > visibleQuestions.length" class="quiz-more">
        共 {{ questions.length }} 道专项练习，在线预览可查看答案与解析
      </div>
    </div>
    <pre v-else class="quiz-json"><code>{{ fallbackJson }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const questions = computed<Record<string, any>[]>(() => {
  if (!props.resultData || typeof props.resultData !== 'object') return []
  if (Array.isArray(props.resultData.questions)) return props.resultData.questions

  const parsedContent = parseJsonObject(props.resultData.content)
  if (Array.isArray(parsedContent?.questions)) return parsedContent.questions

  const parsedRawJson = parseJsonObject(props.resultData.raw_json)
  if (Array.isArray(parsedRawJson?.questions)) return parsedRawJson.questions

  return []
})

const visibleQuestions = computed(() => props.compact ? questions.value.slice(0, 2) : questions.value)
const fallbackJson = computed(() => JSON.stringify(props.resultData || {}, null, 2))

const getDifficultyText = (difficulty?: string) => {
  if (difficulty === 'basic') return '基础'
  if (difficulty === 'intermediate') return '进阶'
  if (difficulty === 'challenge') return '挑战'
  return '练习'
}

const getQuestionTypeText = (questionType?: string) => {
  if (questionType === 'choice') return '选择题'
  if (questionType === 'short_answer') return '简答题'
  return '题目'
}
</script>

<style scoped>
.quiz-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.quiz-item {
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.quiz-stem {
  display: flex;
  gap: 8px;
  color: #1f2d3d;
  font-size: 0.92rem;
  line-height: 1.55;
}

.quiz-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.quiz-meta {
  color: #64748b;
  font-size: 0.74rem;
  font-weight: 700;
}

.quiz-index {
  flex: 0 0 auto;
  color: #1d4ed8;
  font-weight: 800;
}

.quiz-options {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  color: #334155;
  font-size: 0.86rem;
}

.quiz-options span {
  padding: 7px 9px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
}

.quiz-answer,
.quiz-explanation {
  margin-top: 10px;
  color: #334155;
  font-size: 0.9rem;
  line-height: 1.6;
}

.compact .quiz-item {
  padding: 10px;
}

.compact .quiz-stem {
  overflow: hidden;
}

.compact .quiz-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}

.compact .quiz-meta {
  margin-right: 6px;
}

.quiz-more {
  color: #64748b;
  font-size: 0.84rem;
}

.quiz-json {
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background: #1e293b;
  color: #e2e8f0;
  overflow: auto;
}
</style>
