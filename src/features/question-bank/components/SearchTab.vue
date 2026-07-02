<template>
  <div class="search-shell">
    <div class="toolbar">
      <div class="toolbar-search-row">
        <input
          v-model="filters.query"
          type="text"
          class="toolbar-field search"
          placeholder="搜索题目关键词"
          @keyup.enter="handleSearch"
        />
      </div>

      <div class="toolbar-filter-row">
        <select v-model="filters.subject" class="toolbar-field" @change="handleSearch">
          <option value="">全部学科</option>
          <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.difficulty" class="toolbar-field" @change="handleSearch">
          <option value="">全部难度</option>
          <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.type" class="toolbar-field" @change="handleSearch">
          <option value="">全部题型</option>
          <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
        </select>
        <button class="toolbar-btn" type="button" @click="handleSearch">查询</button>
      </div>
    </div>

    <div v-if="loading" class="state-block">正在加载题目...</div>

    <div v-else class="question-list">
      <article
        v-for="(question, index) in questions"
        :id="`bank-question-${question.id}`"
        :key="question.id"
        :class="['question-item', { highlighted: question.id === highlightQuestionId, expanded: activeQuestionId === question.id }]"
      >
        <div class="question-head">
          <div class="head-main">
            <div class="head-line">
              <span class="question-number">第 {{ computeQuestionNumber(index) }} 题</span>
              <div class="head-tags">
                <span class="head-tag subject-tag">{{ question.subject || '未分类' }}</span>
                <span class="head-tag type-tag">{{ question.type || '未分类' }}</span>
                <span class="head-tag difficulty-tag">{{ question.difficulty || '未评级' }}</span>
                <span :class="['status-pill', statusClass(question)]">
                  {{ statusText(question) }}
                </span>
              </div>
            </div>

            <div class="question-summary">
              {{ summarizeText(question.content) }}
            </div>

            <div v-if="question.knowledge_points?.length" class="knowledge-points">
              <span v-for="point in visibleKnowledgePoints(question)" :key="point">{{ point }}</span>
              <span v-if="hiddenKnowledgePointCount(question) > 0">+{{ hiddenKnowledgePointCount(question) }}</span>
            </div>
          </div>
        </div>

        <div class="question-foot">
          <div class="foot-actions">
            <button class="action-link" type="button" @click="toggleQuestion(question.id)">
              {{ activeQuestionId === question.id ? '收起' : '开始作答' }}
            </button>
            <button
              v-if="canVisualize(question)"
              class="action-link"
              type="button"
              @click="$emit('open-visualizer', question)"
            >
              算法可视化
            </button>
          </div>
        </div>

        <div v-if="activeQuestionId === question.id" class="expanded-panel">
          <div class="expanded-header">
            <span class="expanded-kicker">快速作答</span>
            <span class="expanded-status">{{ submitted[question.id] ? '已提交' : '作答中' }}</span>
          </div>
          <p class="expanded-tip">可直接提交答案，也可先查看答案用于快速复习。</p>

          <div v-if="isOptionQuestion(question)" class="option-list">
            <button
              v-for="(text, key) in getOptions(question)"
              :key="key"
              type="button"
              :class="[
                'option-item',
                {
                  selected: isSelected(question, String(key)),
                  correct: submitted[question.id] && isCorrectOption(question, String(key)),
                  wrong: submitted[question.id] && isSelected(question, String(key)) && !isCorrectOption(question, String(key)),
                },
              ]"
              :disabled="submitted[question.id]"
              @click="selectOption(question, String(key))"
            >
              <span class="option-key">{{ key }}</span>
              <span class="option-text" v-html="renderInline(text as string)"></span>
            </button>
          </div>

          <textarea
            v-else-if="!submitted[question.id]"
            v-model="answers[question.id]"
            class="answer-box"
            rows="5"
            placeholder="请输入你的答案"
          ></textarea>

          <div class="expanded-actions">
            <button
              class="action-link submit"
              type="button"
              :disabled="reviewing[question.id] || submitted[question.id] || !hasAnswer(question)"
              @click="submitAnswer(question)"
            >
              {{ reviewing[question.id] ? '评阅中...' : '提交答案' }}
            </button>

            <button
              class="action-link answer"
              type="button"
              @click="$emit('toggle-analysis', question.id)"
            >
              {{ openedAnalysis.has(question.id) ? '收起答案' : '查看答案' }}
            </button>
          </div>

          <div v-if="submitted[question.id]" class="result-banner">
            <span :class="['status-pill', correct[question.id] ? 'success' : 'danger']">
              {{ correct[question.id] ? '回答正确' : '回答错误，已加入错题本' }}
            </span>
          </div>

          <div v-if="openedAnalysis.has(question.id)" class="analysis-box">
            <div class="answer-review-grid">
              <div class="answer-review-card">
                <span class="answer-review-label">你的答案</span>
                <div class="answer-review-value">{{ formatUserAnswer(question) }}</div>
              </div>
              <div class="answer-review-card">
                <span class="answer-review-label">参考答案</span>
                <div class="answer-review-value">{{ formatReferenceAnswer(question) }}</div>
              </div>
            </div>

            <div v-if="review[question.id]?.feedback" class="analysis-feedback">
              {{ review[question.id].feedback }}
            </div>

            <div class="analysis-body" v-html="renderInline(question.analysis || '暂无解析')"></div>
          </div>
        </div>
      </article>

      <div v-if="questions.length === 0" class="state-block">没有找到符合条件的题目。</div>
    </div>

    <div v-if="total > 0 && !loading" class="pagination-row">
      <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">上一页</button>
      <span class="page-info">第 {{ currentPage }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
      <button class="page-btn" :disabled="currentPage >= Math.ceil(total / pageSize)" @click="changePage(currentPage + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { supportsAlgorithmVisualization } from '@/features/question-bank/utils/algorithmVisualization'

const props = defineProps<{
  questions: any[]
  total: number
  loading: boolean
  currentPage: number
  pageSize: number
  filters: { query: string; subject: string; difficulty: string; type: string }
  subjects: string[]
  difficulties: string[]
  types: string[]
  answers: Record<string, any>
  submitted: Record<string, boolean>
  correct: Record<string, boolean>
  reviewing: Record<string, boolean>
  review: Record<string, any>
  openedAnalysis: Set<string>
  highlightQuestionId?: string | null
  highlightVersion?: number
}>()

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'page-change', page: number): void
  (e: 'select-option', question: any, key: string): void
  (e: 'submit', question: any): void
  (e: 'toggle-analysis', id: string): void
  (e: 'open-visualizer', question: any): void
}>()

const activeQuestionId = ref<string | null>(null)

watch(
  () => [props.highlightQuestionId, props.highlightVersion, props.questions.length],
  async () => {
    if (!props.highlightQuestionId) return
    const matched = props.questions.some((question) => question.id === props.highlightQuestionId)
    if (!matched) return

    activeQuestionId.value = props.highlightQuestionId
    await nextTick()
    const target = document.getElementById(`bank-question-${props.highlightQuestionId}`)
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  },
  { immediate: true },
)

watch(
  () => props.questions.map((question) => question.id).join(','),
  () => {
    if (!activeQuestionId.value) return
    const exists = props.questions.some((question) => question.id === activeQuestionId.value)
    if (!exists) activeQuestionId.value = null
  },
)

function handleSearch() {
  activeQuestionId.value = null
  emit('search')
}

function changePage(page: number) {
  activeQuestionId.value = null
  emit('page-change', page)
}

function toggleQuestion(id: string) {
  activeQuestionId.value = activeQuestionId.value === id ? null : id
}

function computeQuestionNumber(index: number) {
  return (props.currentPage - 1) * props.pageSize + index + 1
}

function selectOption(question: any, key: string) {
  emit('select-option', question, key)
}

function submitAnswer(question: any) {
  emit('submit', question)
}

function canVisualize(question: any) {
  return supportsAlgorithmVisualization(question)
}

function isOptionQuestion(question: any) {
  return ['选择题', '单选题', '多选题', '判断题'].includes(question.type)
}

function getOptions(question: any) {
  if (question.type === '判断题') return { A: '正确', B: '错误' }
  return question.options || {}
}

function isSelected(question: any, key: string) {
  const ans = props.answers[question.id]
  if (!ans) return false
  if (Array.isArray(ans)) return ans.includes(key)
  return ans === key
}

function isCorrectOption(question: any, key: string) {
  return correctKeys(question).includes(key)
}

function hasAnswer(question: any) {
  const ans = props.answers[question.id]
  if (Array.isArray(ans)) return ans.length > 0
  return !!ans && String(ans).trim().length > 0
}

function correctKeys(question: any) {
  let ansText = String(question.answer || '').trim()
  if (question.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确', '对'].some((item) => upper.includes(item))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误', '错'].some((item) => upper.includes(item))) ansText = 'B'
  }
  return ansText.split(/[、,，\s]+/).map((item) => item.trim().toUpperCase()).filter(Boolean)
}

function formatAnswer(ans: string) {
  return String(ans || '').replace(/,/g, '、')
}

function formatUserAnswer(question: any) {
  const answer = props.answers[question.id]
  if (!hasAnswer(question)) return '你未作答'

  if (isOptionQuestion(question)) {
    const optionMap = getOptions(question)
    const values = Array.isArray(answer) ? answer : String(answer || '').split(/[、,，\s]+/)
    return values
      .map((key) => String(key).trim().toUpperCase())
      .filter(Boolean)
      .map((key) => `${key}. ${optionMap[key] || key}`)
      .join('；')
  }

  return String(answer || '').trim() || '你未作答'
}

function formatReferenceAnswer(question: any) {
  if (isOptionQuestion(question)) {
    const optionMap = getOptions(question)
    return correctKeys(question)
      .map((key) => `${key}. ${optionMap[key] || key}`)
      .join('；')
  }
  return formatAnswer(question.answer)
}

function summarizeText(text: string) {
  return String(text || '')
    .replace(/\s+/g, ' ')
    .replace(/[#*_`>-]/g, '')
    .trim()
}

function visibleKnowledgePoints(question: any) {
  return (question.knowledge_points || []).slice(0, 3)
}

function hiddenKnowledgePointCount(question: any) {
  return Math.max((question.knowledge_points || []).length - 3, 0)
}

function statusText(question: any) {
  if (props.submitted[question.id]) return '今日提交过'
  return activeQuestionId.value === question.id ? '作答中' : '未作答'
}

function statusClass(question: any) {
  if (props.submitted[question.id]) return props.correct[question.id] ? 'success' : 'danger'
  return activeQuestionId.value === question.id ? 'active' : 'neutral'
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
.search-shell {
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar-search-row,
.toolbar-filter-row {
  display: grid;
  gap: 10px;
}

.toolbar-search-row {
  grid-template-columns: 1fr;
}

.toolbar-filter-row {
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
}

.toolbar-field,
.toolbar-btn,
.answer-box,
.page-btn {
  min-height: 42px;
  border-radius: 12px;
  font: inherit;
}

.toolbar-field,
.answer-box {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  outline: none;
}

.toolbar-field {
  padding: 0 12px;
}

.toolbar-btn {
  padding: 0 16px;
  border: 1px solid #1e293b;
  background: #1e293b;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.state-block {
  padding: 28px 0;
  color: #64748b;
  text-align: center;
}

.question-list {
  display: flex;
  flex-direction: column;
  margin-top: 18px;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.question-item {
  width: 100%;
  padding: 22px 24px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  background: #fff;
  scroll-margin-top: 120px;
  box-sizing: border-box;
  transition: background-color 160ms ease;
}

.question-item.highlighted {
  background: rgba(248, 250, 252, 0.96);
}

.question-item.expanded {
  background: linear-gradient(180deg, #ffffff, #fbfcfd);
}

.question-head,
.question-foot {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.head-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
  width: 100%;
}

.head-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}

.question-number {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
}

.head-tags,
.knowledge-points,
.foot-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.head-tag,
.knowledge-points span,
.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.head-tag,
.knowledge-points span {
  background: #f8fafc;
  color: #475569;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.subject-tag {
  background: #eef6ff;
  color: #3d78b5;
  border-color: transparent;
}

.type-tag {
  background: #eff6f2;
  color: #288a6e;
  border-color: transparent;
}

.difficulty-tag {
  background: #dff2ff;
  color: #3487c7;
  border-color: transparent;
}

.status-pill.success {
  background: #f1f5f9;
  color: #0f172a;
}

.status-pill.danger {
  background: #f8fafc;
  color: #475569;
}

.status-pill.active {
  background: #f1f5f9;
  color: #0f172a;
}

.status-pill.neutral {
  background: #f8fafc;
  color: #64748b;
}

.question-summary {
  display: -webkit-box;
  overflow: hidden;
  color: #334155;
  font-size: 14px;
  line-height: 1.8;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.question-foot {
  margin-top: 14px;
}

.foot-actions {
  width: 100%;
  justify-content: flex-end;
}

.action-link {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.action-link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-link.submit {
  border-color: #0f172a;
  background: #0f172a;
  color: #fff;
}

.action-link.answer {
  border-color: rgba(203, 213, 225, 0.96);
  background: #f8fafc;
  color: #0f172a;
}

.expanded-panel {
  margin-top: 18px;
  padding: 18px 18px 0;
  border-top: 1px dashed rgba(226, 232, 240, 0.92);
  background: #fcfcfd;
  border-radius: 14px;
}

.expanded-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.expanded-kicker,
.expanded-status {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.expanded-tip {
  margin: 0 0 14px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  background: #fff;
  color: #1e293b;
  text-align: left;
  cursor: pointer;
}

.option-item.selected {
  border-color: rgba(148, 163, 184, 0.96);
  background: #f8fafc;
}

.option-item.correct {
  border-color: rgba(203, 213, 225, 0.96);
  background: #f8fafc;
}

.option-item.wrong {
  border-color: rgba(203, 213, 225, 0.96);
  background: #f8fafc;
}

.option-key {
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.option-text {
  flex: 1;
  color: #1e293b;
  line-height: 1.7;
  text-align: left;
}

.answer-box {
  width: 100%;
  margin-top: 16px;
  padding: 12px 14px;
  resize: vertical;
  box-sizing: border-box;
}

.expanded-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.result-banner {
  margin-top: 14px;
}

.analysis-box {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
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
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 12px;
  background: #f8fafc;
}

.answer-review-label {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.answer-review-value {
  color: #0f172a;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.analysis-feedback {
  margin-top: 12px;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}

.analysis-body {
  margin-top: 12px;
  color: #475569;
  line-height: 1.8;
}

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 28px;
  padding-top: 6px;
}

.page-btn {
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #334155;
  cursor: pointer;
}

.page-info {
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 980px) {
  .toolbar-filter-row {
    grid-template-columns: 1fr 1fr;
  }

  .toolbar-btn {
    grid-column: span 2;
  }
}

@media (max-width: 640px) {
  .question-item {
    padding: 20px 16px;
  }

  .toolbar-filter-row,
  .answer-review-grid {
    grid-template-columns: 1fr;
  }

  .toolbar-btn {
    grid-column: auto;
  }

  .head-line,
  .question-foot,
  .pagination-row,
  .expanded-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .foot-actions,
  .expanded-actions {
    justify-content: flex-start;
  }

  .expanded-panel {
    padding: 16px 0 0;
    background: transparent;
    border-radius: 0;
  }
}
</style>
