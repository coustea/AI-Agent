<template>
  <div class="search-tab">
    <div class="header-section">
      <h2>Question Bank</h2>
      <p class="subtitle">Search and explore the complete repository of questions.</p>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <div class="search-input-wrapper">
        <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input 
          v-model="filters.query" 
          type="text" 
          placeholder="Search questions..." 
          class="search-input"
          @keyup.enter="handleSearch"
        />
      </div>
      <select v-model="filters.subject" class="filter-select" @change="handleSearch">
        <option value="">All Subjects</option>
        <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
      </select>
      <select v-model="filters.difficulty" class="filter-select" @change="handleSearch">
        <option value="">All Difficulties</option>
        <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
      </select>
      <select v-model="filters.type" class="filter-select" @change="handleSearch">
        <option value="">All Types</option>
        <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
      </select>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <span>Loading questions...</span>
    </div>

    <!-- Question List -->
    <div v-else class="question-list">
      <article v-for="question in questions" :key="question.id" class="question-card">
        <div class="card-header">
          <div class="tags">
            <span class="tag">{{ question.subject }}</span>
            <span :class="['tag outline', difficultyClass(question.difficulty)]">{{ question.difficulty || 'Unrated' }}</span>
            <span class="tag type">{{ question.type }}</span>
          </div>
          <span class="question-id">#{{ question.id.split('-')[0] }}</span>
        </div>

        <div class="question-content" v-html="renderInline(question.content)"></div>

        <!-- Options / Input Area -->
        <div v-if="isOptionQuestion(question)" class="options-grid">
          <button
            v-for="(text, key) in getOptions(question)"
            :key="key"
            type="button"
            :class="[
              'option-btn', 
              { 
                'selected': isSelected(question, String(key)),
                'correct': submitted[question.id] && isCorrectOption(question, String(key)),
                'wrong': submitted[question.id] && isSelected(question, String(key)) && !isCorrectOption(question, String(key))
              }
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
          placeholder="Enter your answer... AI will review it."
        ></textarea>

        <!-- Actions & Result -->
        <div class="card-footer">
          <div v-if="submitted[question.id]" :class="['result-badge', correct[question.id] ? 'success' : 'danger']">
            <svg v-if="correct[question.id]" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            {{ correct[question.id] ? 'Correct' : 'Incorrect (Added to Wrong Book)' }}
            <span v-if="review[question.id]?.score" class="score-text">({{ review[question.id].score }} pts)</span>
          </div>
          <div v-else class="empty-badge"></div>

          <div class="action-buttons">
            <button 
              class="btn-text" 
              @click="$emit('toggle-analysis', question.id)"
            >
              {{ openedAnalysis.has(question.id) ? 'Hide Analysis' : 'Show Analysis' }}
            </button>
            <button
              class="btn-primary"
              :disabled="submitted[question.id] || !hasAnswer(question)"
              @click="submitAnswer(question)"
            >
              {{ reviewing[question.id] ? 'Reviewing...' : 'Submit' }}
            </button>
          </div>
        </div>

        <!-- Analysis Panel -->
        <div v-if="openedAnalysis.has(question.id)" class="analysis-panel">
          <div class="analysis-header">
            <strong>Reference: {{ formatAnswer(question.answer) }}</strong>
            <span v-if="review[question.id]?.feedback" class="feedback-text">{{ review[question.id].feedback }}</span>
          </div>
          <div class="analysis-content" v-html="renderInline(question.analysis || 'No analysis available.')"></div>
          <div v-if="question.knowledge_points?.length" class="knowledge-tags">
            <span v-for="point in question.knowledge_points" :key="point" class="tag small">{{ point }}</span>
          </div>
        </div>
      </article>

      <div v-if="questions.length === 0" class="empty-state">
        No questions match your criteria.
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > 0 && !loading" class="pagination">
      <button 
        class="page-btn" 
        :disabled="currentPage === 1"
        @click="changePage(currentPage - 1)"
      >
        Previous
      </button>
      <span class="page-info">Page {{ currentPage }} of {{ Math.ceil(total / pageSize) }}</span>
      <button 
        class="page-btn" 
        :disabled="currentPage >= Math.ceil(total / pageSize)"
        @click="changePage(currentPage + 1)"
      >
        Next
      </button>
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

// Helpers
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
    if (upper === 'A' || ['TRUE', 'T', '正确', '对'].some(i => upper.includes(i))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误', '错'].some(i => upper.includes(i))) ansText = 'B'
  }
  const correctKeys = ansText.split(/[、,，;；\s]+/).map(i => i.trim().toUpperCase()).filter(Boolean)
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
  gap: 24px;
}

.header-section h2 {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px 0;
}

.subtitle {
  color: #6B7280;
  font-size: 14px;
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  background: #FFFFFF;
  padding: 16px;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #9CA3AF;
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s ease;
  box-sizing: border-box;
}

.search-input:focus {
  border-color: #111827;
}

.filter-select {
  padding: 8px 32px 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 14px;
  background: #FFFFFF;
  outline: none;
  min-width: 140px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 0;
  color: #6B7280;
  gap: 16px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #E5E7EB;
  border-top-color: #111827;
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
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  background: #F3F4F6;
  color: #374151;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
}

.tag.outline {
  background: transparent;
  border: 1px solid #E5E7EB;
}

.tag.type {
  background: #FEF3C7;
  color: #92400E;
}

.success-text { color: #059669; border-color: #A7F3D0 !important; }
.warning-text { color: #D97706; border-color: #FDE68A !important; }
.danger-text { color: #DC2626; border-color: #FECACA !important; }

.question-id {
  font-family: monospace;
  color: #9CA3AF;
  font-size: 13px;
}

.question-content {
  font-size: 15px;
  color: #111827;
  line-height: 1.6;
  margin-bottom: 24px;
}

.options-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  margin-bottom: 24px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.option-btn:hover:not(:disabled) {
  border-color: #9CA3AF;
  background: #F9FAFB;
}

.option-btn.selected {
  border-color: #111827;
  background: #F3F4F6;
}

.option-btn.correct {
  border-color: #10B981;
  background: #ECFDF5;
}

.option-btn.wrong {
  border-color: #EF4444;
  background: #FEF2F2;
}

.option-btn:disabled {
  cursor: default;
}

.opt-key {
  font-weight: 600;
  color: #111827;
  min-width: 20px;
}

.opt-text {
  color: #374151;
  font-size: 14px;
  line-height: 1.5;
}

.text-area-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 24px;
  outline: none;
  box-sizing: border-box;
}

.text-area-input:focus {
  border-color: #111827;
}

.text-area-input:disabled {
  background: #F9FAFB;
  cursor: not-allowed;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #E5E7EB;
  padding-top: 16px;
}

.result-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 99px;
}

.result-badge.success {
  background: #ECFDF5;
  color: #059669;
}

.result-badge.danger {
  background: #FEF2F2;
  color: #DC2626;
}

.score-text {
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn-text {
  background: none;
  border: none;
  color: #6B7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.btn-text:hover {
  color: #111827;
}

.btn-primary {
  background: #111827;
  color: #FFFFFF;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #374151;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.analysis-panel {
  margin-top: 16px;
  padding: 16px;
  background: #F9FAFB;
  border-radius: 8px;
  border-left: 3px solid #111827;
}

.analysis-header {
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.feedback-text {
  color: #059669;
  font-size: 13px;
  font-weight: 500;
}

.analysis-content {
  font-size: 14px;
  color: #4B5563;
  line-height: 1.6;
}

.knowledge-tags {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag.small {
  font-size: 11px;
  padding: 2px 8px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
}

.page-btn {
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.page-btn:hover:not(:disabled) {
  background: #F9FAFB;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #4B5563;
}

.empty-state {
  text-align: center;
  padding: 64px 0;
  color: #6B7280;
  font-size: 14px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
}
</style>
