<template>
  <div class="wrong-book-tab">
    <div class="header-section">
      <h2>Wrong Questions Book</h2>
      <p class="subtitle">Review and drill your mistakes to solidify your understanding.</p>
    </div>

    <div class="main-grid">
      <!-- Left: Quick Drill -->
      <div class="drill-column">
        <div class="panel">
          <div class="panel-header">
            <h3>Quick Drill</h3>
            <button class="btn-text" @click="$emit('pick-drill')" title="Next Question">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            </button>
          </div>

          <div v-if="drillQuestion" class="drill-content">
            <div class="tags">
              <span class="tag danger">Mistake Retry</span>
              <span class="tag outline">{{ drillQuestion.subject }}</span>
            </div>
            
            <div class="question-stem" v-html="renderInline(drillQuestion.content)"></div>

            <div v-if="isOptionQuestion(drillQuestion)" class="options-list">
              <button
                v-for="(text, key) in getOptions(drillQuestion)"
                :key="key"
                type="button"
                :class="[
                  'option-btn', 
                  { 
                    'selected': isDrillSelected(String(key)),
                    'correct': drillSubmitted && isCorrectOption(drillQuestion, String(key)),
                    'wrong': drillSubmitted && isDrillSelected(String(key)) && !isCorrectOption(drillQuestion, String(key))
                  }
                ]"
                :disabled="drillSubmitted"
                @click="$emit('select-drill-option', String(key))"
              >
                <span class="opt-key">{{ key }}</span>
                <span class="opt-text" v-html="renderInline(text as string)"></span>
              </button>
            </div>
            <textarea
              v-else
              :value="drillAnswer"
              @input="$emit('update:drillAnswer', ($event.target as HTMLTextAreaElement).value)"
              :disabled="drillSubmitted"
              class="text-area-input"
              rows="3"
            ></textarea>

            <button
              v-if="!drillSubmitted"
              class="btn-primary full-width"
              :disabled="!hasDrillAnswer || drillReviewing"
              @click="$emit('submit-drill')"
            >
              {{ drillReviewing ? 'Reviewing...' : 'Submit Drill' }}
            </button>
            <button
              v-else
              class="btn-secondary full-width"
              @click="$emit('pick-drill')"
            >
              Next Question
            </button>

            <!-- Drill Result -->
            <div v-if="drillSubmitted" :class="['result-panel', drillCorrect ? 'success' : 'danger']">
              <strong>{{ drillCorrect ? 'Mastered!' : 'Needs more work' }}</strong>
              <div class="ref-ans">Reference: {{ formatAnswer(drillQuestion.answer) }}</div>
              <p v-if="drillReview?.feedback" class="feedback-text">{{ drillReview.feedback }}</p>
              <div class="analysis-text" v-html="renderInline(drillQuestion.analysis)"></div>
            </div>
          </div>
          <div v-else class="empty-state small">
            No wrong questions to drill. Good job!
          </div>
        </div>
      </div>

      <!-- Right: List & Filters -->
      <div class="list-column">
        <div class="filter-bar">
          <div class="search-input-wrapper">
            <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <input 
              v-model="filters.query" 
              type="text" 
              placeholder="Search in wrong book..." 
              class="search-input"
              @keyup.enter="$emit('search-wrong')"
            />
          </div>
          <select v-model="filters.subject" class="filter-select" @change="$emit('search-wrong')">
            <option value="">All Subjects</option>
            <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="filters.type" class="filter-select" @change="$emit('search-wrong')">
            <option value="">All Types</option>
            <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>

        <div v-if="loading" class="loading-state">
          Loading wrong questions...
        </div>

        <div v-else class="wrong-list">
          <article v-for="question in questions" :key="question.id" class="question-card">
            <div class="card-header">
              <div class="tags">
                <span class="tag danger-outline">Mistakes: {{ question.wrong_count || 1 }}</span>
                <span class="tag outline">{{ question.subject }}</span>
                <span class="tag type">{{ question.type }}</span>
              </div>
              <span class="question-id">#{{ question.id.split('-')[0] }}</span>
            </div>

            <div class="question-content" v-html="renderInline(question.content)"></div>

            <div v-if="isOptionQuestion(question)" class="options-list">
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
                @click="$emit('select-wrong-option', question, String(key))"
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
              placeholder="Try answering again..."
            ></textarea>

            <div class="card-footer">
              <div v-if="submitted[question.id]" :class="['result-badge', correct[question.id] ? 'success' : 'danger']">
                {{ correct[question.id] ? 'Mastered!' : 'Still needs work' }}
              </div>
              <div v-else class="empty-badge"></div>

              <div class="action-buttons">
                <button class="btn-text" @click="$emit('toggle-wrong-analysis', question.id)">
                  {{ openedAnalysis.has(question.id) ? 'Hide Analysis' : 'Show Analysis' }}
                </button>
                <button class="btn-text text-danger" @click="$emit('remove-wrong', question)">Remove</button>
                <button class="btn-text text-success" @click="$emit('archive-wrong', question)">Archive</button>
                <button
                  class="btn-primary"
                  :disabled="submitted[question.id] || !hasAnswer(question)"
                  @click="$emit('submit-wrong', question)"
                >
                  {{ reviewing[question.id] ? 'Reviewing...' : 'Submit' }}
                </button>
              </div>
            </div>

            <div v-if="openedAnalysis.has(question.id)" class="analysis-panel">
              <strong>Reference: {{ formatAnswer(question.answer) }}</strong>
              <div class="analysis-text" v-html="renderInline(question.analysis || 'No analysis available.')"></div>
            </div>
          </article>

          <div v-if="questions.length === 0" class="empty-state">
            No wrong questions found.
          </div>
        </div>

        <div v-if="total > 0 && !loading" class="pagination">
          <button class="page-btn" :disabled="page === 1" @click="$emit('page-change', page - 1)">Previous</button>
          <span class="page-info">Page {{ page }} of {{ Math.ceil(total / pageSize) }}</span>
          <button class="page-btn" :disabled="page >= Math.ceil(total / pageSize)" @click="$emit('page-change', page + 1)">Next</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  questions: any[]
  total: number
  loading: boolean
  page: number
  pageSize: number
  filters: { query: string; subject: string; type: string }
  subjects: string[]
  types: string[]
  
  answers: Record<string, any>
  submitted: Record<string, boolean>
  correct: Record<string, boolean>
  reviewing: Record<string, boolean>
  review: Record<string, any>
  openedAnalysis: Set<string>

  drillQuestion: any | null
  drillAnswer: any
  drillSubmitted: boolean
  drillCorrect: boolean
  drillReviewing: boolean
  drillReview: any | null
}>()

defineEmits<{
  (e: 'search-wrong'): void
  (e: 'page-change', page: number): void
  (e: 'pick-drill'): void
  (e: 'select-drill-option', key: string): void
  (e: 'update:drillAnswer', value: string): void
  (e: 'submit-drill'): void
  (e: 'select-wrong-option', question: any, key: string): void
  (e: 'submit-wrong', question: any): void
  (e: 'toggle-wrong-analysis', id: string): void
  (e: 'archive-wrong', question: any): void
  (e: 'remove-wrong', question: any): void
}>()

import { computed } from 'vue'

const hasDrillAnswer = computed(() => {
  const ans = props.drillAnswer
  if (Array.isArray(ans)) return ans.length > 0
  return !!ans && String(ans).trim().length > 0
})

function isDrillSelected(key: string) {
  const ans = props.drillAnswer
  if (!ans) return false
  if (Array.isArray(ans)) return ans.includes(key)
  return ans === key
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
.wrong-book-tab {
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

.main-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 24px;
}

.panel {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.tags {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tag {
  background: #F3F4F6;
  color: #374151;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
}

.tag.danger { background: #FEF2F2; color: #DC2626; }
.tag.danger-outline { border: 1px solid #FECACA; color: #DC2626; background: transparent; }
.tag.outline { background: transparent; border: 1px solid #E5E7EB; }
.tag.type { background: #FEF3C7; color: #92400E; }

.question-stem {
  font-size: 15px;
  color: #111827;
  line-height: 1.6;
  margin-bottom: 20px;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 14px;
  background: #FFFFFF;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.option-btn:hover:not(:disabled) { border-color: #9CA3AF; background: #F9FAFB; }
.option-btn.selected { border-color: #111827; background: #F3F4F6; }
.option-btn.correct { border-color: #10B981; background: #ECFDF5; }
.option-btn.wrong { border-color: #EF4444; background: #FEF2F2; }

.opt-key { font-weight: 600; color: #111827; min-width: 20px; }
.opt-text { color: #374151; font-size: 14px; line-height: 1.5; }

.text-area-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #D1D5DB;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 16px;
  outline: none;
  box-sizing: border-box;
}

.text-area-input:focus { border-color: #111827; }

.btn-primary { background: #111827; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 500; cursor: pointer; transition: 0.15s; }
.btn-primary:hover:not(:disabled) { background: #374151; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary { background: #FFFFFF; color: #111827; border: 1px solid #D1D5DB; padding: 8px 16px; border-radius: 6px; font-weight: 500; cursor: pointer; transition: 0.15s; }
.btn-secondary:hover { background: #F9FAFB; }

.btn-text { background: none; border: none; color: #6B7280; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-text:hover { color: #111827; }
.text-danger:hover { color: #DC2626; }
.text-success:hover { color: #059669; }

.full-width { width: 100%; }

.result-panel {
  margin-top: 16px;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
}
.result-panel.success { background: #ECFDF5; border-left: 3px solid #10B981; }
.result-panel.danger { background: #FEF2F2; border-left: 3px solid #EF4444; }

.ref-ans { margin-top: 8px; font-weight: 500; }
.feedback-text { color: #059669; margin-top: 8px; }
.analysis-text { margin-top: 8px; color: #4B5563; line-height: 1.5; }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input-wrapper { position: relative; flex: 1; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: #9CA3AF; }
.search-input { width: 100%; padding: 6px 12px 6px 32px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 13px; outline: none; box-sizing: border-box;}
.filter-select { padding: 6px 12px; border: 1px solid #D1D5DB; border-radius: 6px; font-size: 13px; outline: none; }

.wrong-list { display: flex; flex-direction: column; gap: 16px; }

.question-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 20px;
}

.card-header { display: flex; justify-content: space-between; margin-bottom: 12px; }
.question-id { font-family: monospace; color: #9CA3AF; font-size: 12px; }

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #E5E7EB;
  padding-top: 16px;
}

.result-badge { padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; }
.result-badge.success { background: #ECFDF5; color: #059669; }
.result-badge.danger { background: #FEF2F2; color: #DC2626; }

.action-buttons { display: flex; gap: 12px; }

.analysis-panel {
  margin-top: 16px;
  padding: 12px 16px;
  background: #F9FAFB;
  border-radius: 8px;
  border-left: 3px solid #111827;
  font-size: 13px;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 48px 0;
  color: #6B7280;
  font-size: 14px;
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
  font-size: 13px;
  cursor: pointer;
}

.page-btn:hover:not(:disabled) { background: #F9FAFB; }
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
