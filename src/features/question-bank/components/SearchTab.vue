<template>
  <div class="search-shell">
    <div class="toolbar">
      <input
        v-model="filters.query"
        type="text"
        class="toolbar-field search"
        placeholder="搜索题目关键词"
        @keyup.enter="handleSearch"
      />
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

    <div v-if="loading" class="state-block">正在加载题目...</div>

    <div v-else class="question-list">
      <article v-for="question in questions" :key="question.id" class="question-item">
        <div class="question-head">
          <span class="question-no">#{{ question.id.split('-')[0] }}</span>
          <div class="head-tags">
            <span class="head-tag">{{ question.subject }}</span>
            <span class="head-tag">{{ question.type }}</span>
            <span :class="['head-tag', difficultyClass(question.difficulty)]">
              {{ question.difficulty || '未评级' }}
            </span>
          </div>
        </div>

        <div class="question-stem" v-html="renderInline(question.content)"></div>

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
          v-else
          v-model="answers[question.id]"
          :disabled="submitted[question.id]"
          class="answer-box"
          rows="3"
          placeholder="输入你的答案"
        ></textarea>

        <div class="question-foot">
          <div class="foot-status">
            <span v-if="submitted[question.id]" :class="['status-pill', correct[question.id] ? 'success' : 'danger']">
              {{ correct[question.id] ? '回答正确' : '回答错误，已加入错题本' }}
            </span>
            <span v-else class="auto-wrong-note">答错后自动加入错题本</span>
          </div>

          <div class="foot-actions">
            <button
              class="action-link submit"
              type="button"
              :disabled="submitted[question.id] || !hasAnswer(question)"
              @click="submitAnswer(question)"
            >
              {{ reviewing[question.id] ? '评阅中...' : '提交答案' }}
            </button>
            <button class="action-link" type="button" @click="$emit('toggle-analysis', question.id)">
              {{ openedAnalysis.has(question.id) ? '收起解析' : '查看解析' }}
            </button>
            <button class="action-link muted" type="button" disabled>加入错题</button>
            <button
              v-if="canVisualize(question)"
              class="action-link"
              type="button"
              @click="toggleVisualizer(question.id)"
            >
              {{ openedVisualizer.has(question.id) ? '收起可视化' : '算法可视化' }}
            </button>
          </div>
        </div>

        <div v-if="openedAnalysis.has(question.id)" class="analysis-box">
          <div class="analysis-head">
            <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
            <span v-if="review[question.id]?.feedback">{{ review[question.id].feedback }}</span>
          </div>
          <div class="analysis-body" v-html="renderInline(question.analysis || '暂无解析')"></div>
          <div v-if="question.knowledge_points?.length" class="knowledge-points">
            <span v-for="point in question.knowledge_points" :key="point">{{ point }}</span>
          </div>
        </div>

        <AlgorithmVisualizer v-if="openedVisualizer.has(question.id)" :question="question" />
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
import { ref } from 'vue'
import AlgorithmVisualizer from '@/features/question-bank/components/AlgorithmVisualizer.vue'
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
}>()

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'page-change', page: number): void
  (e: 'select-option', question: any, key: string): void
  (e: 'submit', question: any): void
  (e: 'toggle-analysis', id: string): void
}>()

const openedVisualizer = ref<Set<string>>(new Set())

function handleSearch() {
  emit('search')
}

function changePage(page: number) {
  emit('page-change', page)
}

function selectOption(question: any, key: string) {
  emit('select-option', question, key)
}

function submitAnswer(question: any) {
  emit('submit', question)
}

function toggleVisualizer(id: string) {
  const next = new Set(openedVisualizer.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  openedVisualizer.value = next
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
  let ansText = String(question.answer || '').trim()
  if (question.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确', '对'].some((item) => upper.includes(item))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误', '错'].some((item) => upper.includes(item))) ansText = 'B'
  }
  const correctKeys = ansText.split(/[、,，\s]+/).map((item) => item.trim().toUpperCase()).filter(Boolean)
  return correctKeys.includes(key)
}

function hasAnswer(question: any) {
  const ans = props.answers[question.id]
  if (Array.isArray(ans)) return ans.length > 0
  return !!ans && String(ans).trim().length > 0
}

function formatAnswer(ans: string) {
  return String(ans || '').replace(/,/g, '、')
}

function difficultyClass(diff: string) {
  if (diff === '简单') return 'success-text'
  if (diff === '中等') return 'warning-text'
  if (!diff) return 'neutral-text'
  return 'danger-text'
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
  gap: 16px;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1.6fr) repeat(3, minmax(120px, 0.8fr)) auto;
  gap: 10px;
}

.toolbar-field,
.toolbar-btn,
.answer-box,
.page-btn {
  min-height: 40px;
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
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.state-block {
  padding: 18px 0;
  color: #64748b;
  text-align: center;
}

.question-list {
  display: flex;
  flex-direction: column;
}

.question-item {
  width: 100%;
  padding: 18px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.question-item:first-child {
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.question-head,
.question-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.question-no {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.head-tags,
.foot-actions,
.knowledge-points {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.head-tag,
.knowledge-points span,
.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}

.head-tag {
  border: 1px solid rgba(226, 232, 240, 0.95);
  background: rgba(248, 250, 252, 0.92);
  color: #334155;
}

.success-text {
  color: #047857;
}

.warning-text {
  color: #b45309;
}

.danger-text {
  color: #b91c1c;
}

.neutral-text {
  color: #475569;
}

.question-stem {
  margin: 14px 0 16px;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.7;
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
  border-color: rgba(15, 23, 42, 0.35);
}

.option-item.correct {
  border-color: rgba(16, 185, 129, 0.45);
  background: rgba(236, 253, 245, 0.7);
}

.option-item.wrong {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(254, 242, 242, 0.7);
}

.option-key {
  display: inline-flex;
  align-items: center;
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
  line-height: 1.7;
}

.answer-box {
  width: 100%;
  padding: 12px 14px;
  resize: vertical;
  box-sizing: border-box;
}

.foot-status {
  min-height: 28px;
  display: flex;
  align-items: center;
}

.status-pill.success {
  background: rgba(220, 252, 231, 0.8);
  color: #047857;
}

.status-pill.danger {
  background: rgba(254, 226, 226, 0.8);
  color: #b91c1c;
}

.auto-wrong-note {
  color: #94a3b8;
  font-size: 12px;
}

.foot-actions {
  justify-content: flex-end;
}

.action-link {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.action-link.submit {
  border-color: #0f172a;
  background: #0f172a;
  color: #fff;
}

.action-link.muted:disabled {
  color: #94a3b8;
  cursor: not-allowed;
}

.analysis-box {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(226, 232, 240, 0.92);
}

.analysis-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: #475569;
  font-size: 13px;
}

.analysis-body {
  margin-top: 10px;
  color: #475569;
  line-height: 1.7;
}

.knowledge-points {
  margin-top: 10px;
}

.knowledge-points span {
  background: rgba(248, 250, 252, 0.92);
  color: #475569;
}

.pagination-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding-top: 8px;
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
  .toolbar {
    grid-template-columns: 1fr 1fr;
  }

  .toolbar .search,
  .toolbar-btn {
    grid-column: span 2;
  }
}

@media (max-width: 640px) {
  .question-foot,
  .pagination-row {
    align-items: stretch;
    flex-direction: column;
  }

  .foot-actions {
    justify-content: flex-start;
  }
}
</style>
