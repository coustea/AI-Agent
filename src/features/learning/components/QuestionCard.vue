<template>
  <div class="qcard">
    <div v-if="mode === 'challenge'" class="qcard-meta">
      <el-tag size="small" type="info" effect="plain">{{ question.subject }}</el-tag>
      <el-tag size="small" :type="difficultyType" effect="light">{{ question.difficulty || '未标注' }}</el-tag>
      <el-tag size="small" type="warning" effect="light">{{ question.type }}</el-tag>
      <el-tag v-if="question.type === '多选题'" size="small" type="primary" effect="plain">可多选</el-tag>
    </div>

    <div v-else class="qcard-tags">
      <el-tag size="small" type="info" effect="plain">{{ question.subject }}</el-tag>
      <el-tag size="small" :type="difficultyType" effect="light">{{ question.difficulty || '未标注' }}</el-tag>
      <el-tag size="small" type="warning" effect="light">{{ question.type }}</el-tag>
      <el-tag v-if="question.type === '多选题'" size="small" type="primary" effect="plain">可多选</el-tag>
      <el-tag v-if="submitted && !isCorrect" size="small" type="danger" effect="dark">错题</el-tag>
    </div>

    <div class="qcard-text markdown-body" v-html="renderContent()"></div>

    <!-- Options -->
    <div v-if="isOptionType" :class="['qcard-options', { 'binary': question.type === '判断题', 'challenge-grid': mode === 'challenge' }]">
      <div
        v-for="(val, key) in displayOptions"
        :key="key"
        :class="['qcard-opt', {
          selected: isSelected(key),
          correct: submitted && isCorrectOption(key),
          wrong: submitted && isSelected(key) && !isCorrectOption(key),
        }]"
        @click="handleOptionClick(key)"
      >
        <span class="opt-indicator">{{ key }}</span>
        <span class="opt-content markdown-body" v-html="renderInline(val)"></span>
        <el-tag v-if="submitted && isCorrectOption(key)" size="small" type="success" class="opt-result-tag">正确答案</el-tag>
        <el-tag v-if="submitted && isSelected(key) && !isCorrectOption(key)" size="small" type="danger" class="opt-result-tag">您的选项</el-tag>
      </div>
    </div>

    <!-- Text input -->
    <div v-else class="qcard-textarea">
      <el-input
        :model-value="userAnswer"
        @update:model-value="$emit('update:answer', $event)"
        :disabled="submitted"
        type="textarea"
        :rows="mode === 'challenge' ? 2 : 3"
        :placeholder="question.type === '填空题' ? '请输入填空答案...' : '请在此简要作答...'"
      />
    </div>

    <!-- Action Footer -->
    <div class="qcard-footer">
      <div v-if="submitted && !reviewLoading" class="qcard-result" :class="isCorrect ? 'ok' : 'fail'">
        <el-icon v-if="isCorrect"><CircleCheck /></el-icon>
        <el-icon v-else><CircleClose /></el-icon>
        <span>{{ isCorrect ? '回答正确！' : '回答错误' }}</span>
        <span v-if="reviewResult && !isOptionType" class="score-pill">{{ reviewResult.score }}分</span>
      </div>
      <div v-if="reviewLoading" class="qcard-loading">
        <span class="loading-text">AI 审查中...</span>
      </div>
      <template v-if="!submitted">
        <el-button type="primary" :disabled="!hasAnyAnswer" class="submit-btn" @click="$emit('submit')">提交答案</el-button>
      </template>
      <template v-else>
        <el-button v-if="mode === 'challenge'" type="primary" class="submit-btn" @click="$emit('next')">下一题</el-button>
        <el-button v-else link type="primary" size="small" class="toggle-btn" @click="$emit('toggle-analysis')">
          {{ showAnalysis ? '收起答案解析' : '查看答案解析' }}
        </el-button>
      </template>
    </div>

    <!-- AI Review Result (for text questions) -->
    <transition name="collapse">
      <div v-if="submitted && showAnalysis && reviewResult && !isOptionType" class="qcard-ai-review">
        <div class="ai-header">
          <span class="ai-label">AI 评分</span>
          <span :class="['ai-score', reviewResult.is_correct ? 'ok' : 'fail']">{{ reviewResult.score }}分</span>
        </div>
        <div class="ai-feedback">{{ reviewResult.feedback }}</div>
        <div v-if="reviewResult.improvement_hints?.length" class="ai-hints">
          <div class="hints-title">改进建议</div>
          <ul><li v-for="h in reviewResult.improvement_hints" :key="h">{{ h }}</li></ul>
        </div>
      </div>
    </transition>

    <!-- Analysis Panel -->
    <transition name="collapse">
      <div v-if="submitted && showAnalysis" class="qcard-analysis">
        <div class="analysis-ans">参考答案: <span class="ans-badge">{{ formatAnswer(question.answer) }}</span></div>
        <div class="analysis-body markdown-body" v-html="renderAnalysis()"></div>
        <div v-if="question.knowledge_points?.length" class="analysis-kps">
          <span>知识点：</span>
          <el-tag v-for="kp in question.knowledge_points" :key="kp" size="small" type="info">{{ kp }}</el-tag>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { marked } from 'marked'

interface Question {
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

interface ReviewResult {
  score: number
  is_correct: boolean
  feedback: string
  improvement_hints: string[]
}

const props = defineProps<{
  question: Question
  submitted: boolean
  userAnswer: any
  isCorrect: boolean
  reviewResult?: ReviewResult | null
  reviewLoading?: boolean
  showAnalysis: boolean
  mode: 'challenge' | 'browse'
}>()

const emit = defineEmits<{
  'update:answer': [value: any]
  submit: []
  next: []
  'toggle-analysis': []
}>()

const renderContent = () => {
  const text = props.question.content || ''
  return marked.parse(text, { async: false }) as string
}

const renderInline = (text: string) => {
  return marked.parseInline(text || '', { async: false }) as string
}

const renderAnalysis = () => {
  return marked.parse(props.question.analysis || '', { async: false }) as string
}

const difficultyType = computed(() => {
  const d = props.question.difficulty
  if (d === '简单') return 'success'
  if (d === '中等') return 'warning'
  return 'danger'
})

const isOptionType = computed(() => {
  return props.question.type === '选择题' || props.question.type === '多选题' || props.question.type === '判断题'
})

const displayOptions = computed(() => {
  if (props.question.type === '判断题') return { A: '正确', B: '错误' }
  return props.question.options || {}
})

const normalizeAnswers = (answer: any): string[] => {
  const values = Array.isArray(answer) ? answer : String(answer || '').split(',')
  return values.map(v => String(v).trim().toUpperCase()).filter(Boolean).sort()
}

const getOptionValue = (key: string) => {
  if (props.question.type === '判断题') return key === 'A' ? '正确' : '错误'
  return key
}

const isSelected = (key: string) => {
  const selected = normalizeAnswers(props.userAnswer)
  const value = String(getOptionValue(key)).toUpperCase()
  return selected.includes(value) || selected.includes(key)
}

const isCorrectOption = (key: string) => {
  const standard = normalizeAnswers(props.question.answer)
  const value = String(getOptionValue(key)).toUpperCase()
  return standard.includes(value)
}

const handleOptionClick = (key: string) => {
  if (props.submitted) return
  const value = getOptionValue(key)
  if (props.question.type === '多选题') {
    const selected = normalizeAnswers(props.userAnswer)
    const norm = String(value).toUpperCase()
    const newAnswer = selected.includes(norm)
      ? selected.filter(v => v !== norm)
      : [...selected, norm]
    emit('update:answer', newAnswer)
  } else {
    emit('update:answer', value)
  }
}

const hasAnyAnswer = computed(() => {
  const answer = props.userAnswer
  if (Array.isArray(answer)) return answer.length > 0
  return String(answer || '').trim().length > 0
})

const formatAnswer = (a: string) => a.split(',').join('、')
</script>

<style scoped>
.qcard { display: flex; flex-direction: column; gap: 14px; }
.qcard-meta, .qcard-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.qcard-text { font-weight: 600; line-height: 1.6; color: var(--color-text); }
.qcard-text:deep(p) { margin: 0.3rem 0; }

.qcard-options {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
  background: var(--color-bg); padding: 12px; border-radius: 10px; border: 1px solid var(--color-border);
}
.qcard-options.binary { grid-template-columns: repeat(2, 1fr); }
.qcard-options.challenge-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); margin-bottom: 16px; }
.qcard-options.challenge-grid.binary { grid-template-columns: repeat(2, 1fr); }

.qcard-opt {
  display: flex; align-items: flex-start; gap: 8px; padding: 10px 12px;
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 8px; cursor: pointer; transition: all 0.2s ease; font-size: 0.88rem;
}
.qcard-opt:hover { border-color: var(--color-primary); background: rgba(79, 70, 229, 0.04); }
.qcard-opt.selected { border-color: var(--color-primary); background: rgba(79, 70, 229, 0.08); font-weight: 600; }
.qcard-opt.correct { border-color: var(--color-success); background: rgba(16, 185, 129, 0.08); color: #047857; }
.qcard-opt.wrong { border-color: var(--color-danger); background: rgba(239, 68, 68, 0.08); color: #B91C1C; }

.opt-indicator {
  width: 24px; height: 24px; border-radius: 50%; background: rgba(15, 23, 42, 0.05);
  display: flex; align-items: center; justify-content: center; font-weight: bold;
  font-size: 0.82rem; flex-shrink: 0; color: var(--color-text-secondary);
}
.qcard-opt.selected .opt-indicator { background: var(--color-primary); color: #fff; }
.qcard-opt.correct .opt-indicator { background: var(--color-success); color: #fff; }
.qcard-opt.wrong .opt-indicator { background: var(--color-danger); color: #fff; }

.opt-content { flex: 1; min-width: 0; overflow-wrap: anywhere; word-break: break-word; }
.opt-content:deep(p) { margin: 0; }
.opt-result-tag { margin-left: auto; font-weight: 700; flex-shrink: 0; }

.qcard-textarea { margin-top: 4px; }

.qcard-footer { display: flex; align-items: center; gap: 10px; justify-content: flex-end; }
.qcard-result { display: flex; align-items: center; gap: 6px; font-weight: 700; margin-right: auto; }
.qcard-result.ok { color: var(--color-success); }
.qcard-result.fail { color: var(--color-danger); }
.qcard-loading { margin-right: auto; }
.loading-text { font-size: 0.88rem; color: var(--color-text-muted); animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.score-pill {
  display: inline-block; margin-left: 6px; font-size: 0.78rem; font-weight: 700;
  padding: 1px 6px; border-radius: 4px; background: rgba(79, 70, 229, 0.12); color: var(--color-primary);
}

.submit-btn { border-radius: 10px !important; font-weight: 600 !important; }
.toggle-btn { font-size: 0.82rem !important; font-weight: 600 !important; color: var(--color-primary) !important; }

.qcard-ai-review {
  padding: 14px; background: rgba(79, 70, 229, 0.05); border: 1px solid rgba(79, 70, 229, 0.12);
  border-radius: 10px;
}
.ai-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.ai-label { font-size: 0.85rem; font-weight: 600; color: var(--color-primary); }
.ai-score { font-size: 1.1rem; font-weight: 800; padding: 2px 10px; border-radius: 6px; }
.ai-score.ok { background: rgba(16, 185, 129, 0.12); color: var(--color-success); }
.ai-score.fail { background: rgba(239, 68, 68, 0.12); color: var(--color-danger); }
.ai-feedback { font-size: 0.88rem; color: var(--color-text); line-height: 1.5; margin-bottom: 6px; }
.ai-hints .hints-title { font-size: 0.82rem; font-weight: 600; color: var(--color-text-muted); margin-bottom: 4px; }
.ai-hints ul { margin: 0; padding-left: 16px; font-size: 0.84rem; color: var(--color-text-secondary); }
.ai-hints li { margin: 2px 0; }

.qcard-analysis {
  padding: 14px; border-top: 1px dashed #FCD34D; border-left: 4px solid var(--color-warning);
  background: #FFFDF5; border-radius: 8px;
}
.analysis-ans { font-weight: bold; margin-bottom: 8px; color: #B45309; font-size: 0.9rem; }
.ans-badge { background: #FEF3C7; padding: 2px 8px; border-radius: 4px; border: 1px solid #FCD34D; }
.analysis-body { font-size: 0.88rem; color: #78350F; line-height: 1.6; margin-bottom: 8px; }
.analysis-kps { display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: #92400E; flex-wrap: wrap; }

.collapse-enter-active, .collapse-leave-active { transition: all 0.25s ease; overflow: hidden; }
.collapse-enter-from, .collapse-leave-to { opacity: 0; max-height: 0; }
.collapse-enter-to, .collapse-leave-from { max-height: 600px; }
</style>
