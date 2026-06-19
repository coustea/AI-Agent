<template>
  <div class="search-tab">
    <header class="module-header">
      <div>
        <span class="section-label">Question Bank</span>
        <h2>全部题目</h2>
        <p class="subtitle">按学科、难度和题型检索题库，并直接在线作答。</p>
      </div>
    </header>

    <section class="filter-card">
      <div class="filter-bar">
        <div class="search-input-wrapper">
          <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input
            v-model="filters.query"
            type="text"
            placeholder="搜索题目..."
            class="search-input"
            @keyup.enter="handleSearch"
          />
        </div>
        <select v-model="filters.subject" class="filter-select" @change="handleSearch">
          <option value="">全部学科</option>
          <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.difficulty" class="filter-select" @change="handleSearch">
          <option value="">全部难度</option>
          <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.type" class="filter-select" @change="handleSearch">
          <option value="">全部题型</option>
          <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
    </section>

    <div v-if="loading" class="loading-card">
      <div class="spinner"></div>
      <span>加载题目中...</span>
    </div>

    <section v-else class="question-list">
      <article v-for="question in questions" :key="question.id" class="question-card">
        <div class="card-header">
          <div class="tags">
            <span class="tag">{{ question.subject }}</span>
            <span :class="['tag outline', difficultyClass(question.difficulty)]">{{ question.difficulty || '未评级' }}</span>
            <span class="tag type">{{ question.type }}</span>
          </div>
          <span class="question-id">#{{ question.id.split('-')[0] }}</span>
        </div>

        <div class="question-content" v-html="renderInline(question.content)"></div>

        <div v-if="isOptionQuestion(question)" class="options-grid">
          <button
            v-for="(text, key) in getOptions(question)"
            :key="key"
            type="button"
            :class="[
              'option-btn',
              {
                selected: isSelected(question, String(key)),
                correct: submitted[question.id] && isCorrectOption(question, String(key)),
                wrong: submitted[question.id] && isSelected(question, String(key)) && !isCorrectOption(question, String(key)),
              },
            ]"
            :disabled="submitted[question.id]"
            @click="selectOption(question, String(key))"
          >
            <span class="opt-key">{{ key }}</span>
            <span class="opt-text" v-html="renderInline(text as string)"></span>
          </button>
        </div>
        <textarea
          v-else
          v-model="answers[question.id]"
          :disabled="submitted[question.id]"
          class="text-area-input"
          rows="3"
          placeholder="请输入你的答案，系统会自动评阅。"
        ></textarea>

        <div class="card-footer">
          <div v-if="submitted[question.id]" :class="['result-badge', correct[question.id] ? 'success' : 'danger']">
            <svg v-if="correct[question.id]" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            {{ correct[question.id] ? '正确' : '错误（已加入错题本）' }}
            <span v-if="review[question.id]?.score" class="score-text">({{ review[question.id].score }} 分)</span>
          </div>
          <div v-else class="result-placeholder"></div>

          <div class="action-buttons">
            <button class="btn-link" @click="$emit('toggle-analysis', question.id)">
              {{ openedAnalysis.has(question.id) ? '收起解析' : '查看解析' }}
            </button>
            <button
              class="btn-primary"
              :disabled="submitted[question.id] || !hasAnswer(question)"
              @click="submitAnswer(question)"
            >
              {{ reviewing[question.id] ? '评阅中...' : '提交' }}
            </button>
          </div>
        </div>

        <div v-if="openedAnalysis.has(question.id)" class="analysis-panel">
          <div class="analysis-header">
            <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
            <span v-if="review[question.id]?.feedback" class="feedback-text">{{ review[question.id].feedback }}</span>
          </div>
          <div class="analysis-content" v-html="renderInline(question.analysis || '暂无解析。')"></div>
          <div v-if="question.knowledge_points?.length" class="knowledge-tags">
            <span v-for="point in question.knowledge_points" :key="point" class="tag small">{{ point }}</span>
          </div>
        </div>
      </article>

      <div v-if="questions.length === 0" class="empty-state">没有找到符合条件的题目。</div>
    </section>

    <div v-if="total > 0 && !loading" class="pagination-card">
      <button class="page-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">上一页</button>
      <span class="page-info">第 {{ currentPage }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
      <button class="page-btn" :disabled="currentPage >= Math.ceil(total / pageSize)" @click="changePage(currentPage + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
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
.search-tab {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.module-header,
.filter-card,
.question-card,
.pagination-card,
.loading-card,
.empty-state {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.module-header,
.filter-card,
.pagination-card,
.loading-card,
.empty-state {
  padding: 22px 24px;
}

.section-label {
  color: var(--cat-eval, #8b5cf6);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.module-header h2 {
  margin: 6px 0 0;
  color: #0f172a;
  font-size: 1.35rem;
  font-weight: 700;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  line-height: 1.65;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.search-input-wrapper {
  position: relative;
  flex: 1 1 320px;
}

.search-icon {
  position: absolute;
  top: 50%;
  left: 14px;
  transform: translateY(-50%);
  color: #94a3b8;
}

.search-input,
.filter-select,
.page-btn,
.btn-primary {
  min-height: 42px;
  border-radius: 14px;
  font-size: 14px;
}

.search-input,
.filter-select {
  width: 100%;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  font-family: inherit;
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.search-input {
  padding: 0 14px 0 42px;
}

.filter-select {
  flex: 0 0 148px;
  padding: 0 14px;
}

.search-input:focus,
.filter-select:focus,
.text-area-input:focus {
  border-color: rgba(79, 70, 229, 0.42);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
}

.loading-card,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 14px;
  color: #64748b;
  text-align: center;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(203, 213, 225, 0.96);
  border-top-color: var(--cat-eval, #8b5cf6);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-card {
  padding: 24px;
}

.card-header,
.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.card-header {
  align-items: center;
  margin-bottom: 16px;
}

.card-footer {
  align-items: center;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.tags,
.knowledge-tags,
.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(238, 242, 255, 0.92);
  color: #6d28d9;
  font-size: 12px;
  font-weight: 700;
}

.tag.outline {
  background: #fff;
  border: 1px solid rgba(203, 213, 225, 0.96);
  color: #475569;
}

.tag.type {
  border: 1px solid rgba(99, 102, 241, 0.16);
}

.tag.small {
  min-height: 24px;
  padding: 0 10px;
}

.success-text {
  color: #059669;
  border-color: rgba(16, 185, 129, 0.2) !important;
}

.warning-text {
  color: #d97706;
  border-color: rgba(245, 158, 11, 0.24) !important;
}

.danger-text {
  color: #dc2626;
  border-color: rgba(248, 113, 113, 0.24) !important;
}

.neutral-text {
  color: #64748b;
}

.question-id {
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
}

.question-content {
  margin-bottom: 20px;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.8;
}

.options-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: #fff;
  text-align: left;
  color: #0f172a;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
}

.option-btn:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.32);
  background: rgba(248, 250, 252, 0.95);
}

.option-btn.selected {
  border-color: rgba(79, 70, 229, 0.36);
  background: rgba(238, 242, 255, 0.94);
  box-shadow: 0 10px 24px rgba(79, 70, 229, 0.08);
}

.option-btn.correct {
  border-color: rgba(16, 185, 129, 0.28);
  background: rgba(236, 253, 245, 0.92);
}

.option-btn.wrong {
  border-color: rgba(239, 68, 68, 0.24);
  background: rgba(254, 242, 242, 0.94);
}

.opt-key {
  min-width: 20px;
  color: #6d28d9;
  font-weight: 800;
}

.opt-text {
  color: #334155;
  line-height: 1.6;
}

.text-area-input {
  width: 100%;
  margin-top: 4px;
  padding: 14px 16px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 18px;
  background: #fff;
  font-family: inherit;
  font-size: 14px;
  color: #0f172a;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.result-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.result-badge.success {
  background: rgba(236, 253, 245, 0.92);
  color: #059669;
}

.result-badge.danger {
  background: rgba(254, 242, 242, 0.94);
  color: #dc2626;
}

.score-text {
  font-weight: 700;
}

.result-placeholder {
  min-height: 32px;
}

.btn-link {
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.btn-link:hover {
  color: #6d28d9;
}

.page-btn:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}

.analysis-panel {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.analysis-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.feedback-text {
  color: #059669;
  font-size: 13px;
  font-weight: 700;
}

.analysis-content {
  color: #475569;
  line-height: 1.7;
}

.pagination-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.page-btn {
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #334155;
  cursor: pointer;
}

.page-btn:hover:not(:disabled) {
  background: #f8fafc;
}

.page-info {
  color: #475569;
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 720px) {
  .module-header,
  .filter-card,
  .question-card,
  .pagination-card,
  .loading-card,
  .empty-state {
    padding: 18px;
  }

  .filter-select {
    flex: 1 1 calc(50% - 12px);
  }

  .card-footer,
  .analysis-header,
  .pagination-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-buttons {
    width: 100%;
  }

  .btn-primary,
  .page-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
