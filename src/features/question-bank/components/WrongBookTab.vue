<template>
  <div class="wrong-book-tab">
    <header class="module-header">
      <div>
        <span class="section-label">Wrong Book</span>
        <h2>错题本</h2>
        <p class="subtitle">集中复习错题、查看解析，并持续巩固薄弱点。</p>
      </div>
    </header>

    <div class="main-grid">
      <section class="drill-column">
        <div class="section-card">
          <div class="panel-head">
            <div>
              <span class="section-label">Quick Drill</span>
              <h3>快速再练</h3>
            </div>
            <button class="btn-icon" @click="$emit('pick-drill')" title="换一题">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            </button>
          </div>

          <div v-if="drillQuestion" class="drill-content">
            <div class="tags">
              <span class="tag danger">错题重练</span>
              <span class="tag outline">{{ drillQuestion.subject }}</span>
              <span class="tag outline">{{ drillQuestion.type }}</span>
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
                    selected: isDrillSelected(String(key)),
                    correct: drillSubmitted && isCorrectOption(drillQuestion, String(key)),
                    wrong: drillSubmitted && isDrillSelected(String(key)) && !isCorrectOption(drillQuestion, String(key)),
                  },
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
              class="text-area-input"
              rows="4"
              placeholder="请重新作答..."
              :disabled="drillSubmitted"
              @input="$emit('update:drillAnswer', ($event.target as HTMLTextAreaElement).value)"
            ></textarea>

            <button
              v-if="!drillSubmitted"
              class="btn-primary full-width"
              :disabled="!hasDrillAnswer || drillReviewing"
              @click="$emit('submit-drill')"
            >
              {{ drillReviewing ? '评阅中...' : '提交答案' }}
            </button>
            <button
              v-else
              class="btn-secondary full-width"
              @click="$emit('pick-drill')"
            >
              再练一题
            </button>

            <div v-if="drillSubmitted" :class="['result-panel', drillCorrect ? 'success' : 'danger']">
              <strong>{{ drillCorrect ? '已掌握' : '还需练习' }}</strong>
              <div class="ref-ans">参考答案：{{ formatAnswer(drillQuestion.answer) }}</div>
              <p v-if="drillReview?.feedback" class="feedback-text">{{ drillReview.feedback }}</p>
              <div class="analysis-text" v-html="renderInline(drillQuestion.analysis || '暂无解析。')"></div>
            </div>
          </div>

          <div v-else class="empty-state">暂无可再练的错题。</div>
        </div>
      </section>

      <section class="list-column">
        <div class="filter-card">
          <div class="filter-bar">
            <div class="search-input-wrapper">
              <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              <input
                v-model="filters.query"
                type="text"
                placeholder="搜索错题..."
                class="search-input"
                @keyup.enter="$emit('search-wrong')"
              />
            </div>
            <select v-model="filters.subject" class="filter-select" @change="$emit('search-wrong')">
              <option value="">全部学科</option>
              <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
            </select>
            <select v-model="filters.type" class="filter-select" @change="$emit('search-wrong')">
              <option value="">全部题型</option>
              <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="loading-card">加载错题中...</div>

        <div v-else class="wrong-list">
          <article v-for="question in questions" :key="question.id" class="question-card">
            <div class="card-header">
              <div class="tags">
                <span class="tag danger">错 {{ question.wrong_count || 1 }} 次</span>
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
                    selected: isSelected(question, String(key)),
                    correct: submitted[question.id] && isCorrectOption(question, String(key)),
                    wrong: submitted[question.id] && isSelected(question, String(key)) && !isCorrectOption(question, String(key)),
                  },
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
              class="text-area-input"
              rows="3"
              placeholder="请重新作答..."
              :disabled="submitted[question.id]"
            ></textarea>

            <div class="card-footer">
              <div v-if="submitted[question.id]" :class="['result-badge', correct[question.id] ? 'success' : 'danger']">
                {{ correct[question.id] ? '已掌握' : '仍需练习' }}
              </div>
              <div v-else class="result-placeholder"></div>

              <div class="action-buttons">
                <button class="btn-link" @click="$emit('toggle-wrong-analysis', question.id)">
                  {{ openedAnalysis.has(question.id) ? '收起解析' : '查看解析' }}
                </button>
                <button class="btn-link danger-link" @click="$emit('remove-wrong', question)">移出</button>
                <button class="btn-link success-link" @click="$emit('archive-wrong', question)">归档</button>
                <button
                  class="btn-primary"
                  :disabled="submitted[question.id] || !hasAnswer(question)"
                  @click="$emit('submit-wrong', question)"
                >
                  {{ reviewing[question.id] ? '评阅中...' : '提交' }}
                </button>
              </div>
            </div>

            <div v-if="openedAnalysis.has(question.id)" class="analysis-panel">
              <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
              <div class="analysis-text" v-html="renderInline(question.analysis || '暂无解析。')"></div>
            </div>
          </article>

          <div v-if="questions.length === 0" class="empty-state">暂无错题。</div>
        </div>

        <div v-if="total > 0 && !loading" class="pagination-card">
          <button class="page-btn" :disabled="page === 1" @click="$emit('page-change', page - 1)">上一页</button>
          <span class="page-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
          <button class="page-btn" :disabled="page >= Math.ceil(total / pageSize)" @click="$emit('page-change', page + 1)">下一页</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

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
  gap: 20px;
}

.module-header,
.section-card,
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
.empty-state,
.section-card,
.question-card {
  padding: 22px 24px;
}

.section-label {
  color: #4f46e5;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.module-header h2,
.panel-head h3 {
  margin: 6px 0 0;
  color: #0f172a;
}

.module-header h2 {
  font-size: 1.35rem;
  font-weight: 700;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  line-height: 1.65;
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(320px, 0.95fr) minmax(0, 1.45fr);
  gap: 20px;
}

.list-column,
.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-head,
.card-header,
.card-footer,
.pagination-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.panel-head,
.card-header,
.card-footer {
  align-items: center;
}

.tags,
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
  font-size: 12px;
  font-weight: 700;
}

.tag.danger {
  background: rgba(254, 242, 242, 0.94);
  color: #dc2626;
}

.tag.outline {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #475569;
}

.tag.type {
  background: rgba(238, 242, 255, 0.92);
  color: #4338ca;
}

.drill-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-stem,
.question-content,
.analysis-text {
  color: #334155;
  line-height: 1.7;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-btn {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: #fff;
  color: #0f172a;
  text-align: left;
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
  color: #4338ca;
  font-weight: 800;
}

.opt-text {
  line-height: 1.6;
}

.text-area-input,
.search-input,
.filter-select,
.btn-primary,
.btn-secondary,
.page-btn {
  min-height: 42px;
  border-radius: 14px;
  font-size: 14px;
  font-family: inherit;
}

.text-area-input,
.search-input,
.filter-select {
  width: 100%;
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.text-area-input {
  min-height: 120px;
  padding-top: 14px;
  padding-bottom: 14px;
  resize: vertical;
}

.text-area-input:focus,
.search-input:focus,
.filter-select:focus {
  border-color: rgba(79, 70, 229, 0.42);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
}

.btn-primary,
.btn-secondary,
.page-btn {
  padding: 0 18px;
  font-weight: 700;
}

.btn-primary {
  border: 1px solid #4f46e5;
  background: #4f46e5;
  color: #fff;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: #4338ca;
  border-color: #4338ca;
}

.btn-secondary {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #334155;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled),
.page-btn:hover:not(:disabled) {
  background: #f8fafc;
}

.btn-primary:disabled,
.btn-secondary:disabled,
.page-btn:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}

.btn-icon {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  border-radius: 14px;
  background: #fff;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.btn-icon:hover {
  color: #4338ca;
  background: rgba(238, 242, 255, 0.88);
}

.full-width {
  width: 100%;
}

.result-panel {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid transparent;
}

.result-panel.success {
  background: rgba(236, 253, 245, 0.75);
  border-color: rgba(16, 185, 129, 0.18);
}

.result-panel.danger {
  background: rgba(254, 242, 242, 0.85);
  border-color: rgba(239, 68, 68, 0.18);
}

.ref-ans,
.feedback-text {
  margin-top: 8px;
}

.feedback-text {
  color: #059669;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.search-input-wrapper {
  position: relative;
  flex: 1 1 280px;
}

.search-icon {
  position: absolute;
  top: 50%;
  left: 14px;
  transform: translateY(-50%);
  color: #94a3b8;
}

.search-input {
  padding-left: 38px;
}

.filter-select {
  flex: 0 0 148px;
}

.question-id {
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
}

.card-header {
  margin-bottom: 16px;
}

.question-content {
  margin-bottom: 20px;
}

.card-footer {
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.result-badge {
  display: inline-flex;
  align-items: center;
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
  color: #4338ca;
}

.danger-link:hover {
  color: #dc2626;
}

.success-link:hover {
  color: #059669;
}

.analysis-panel {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.loading-card,
.empty-state {
  color: #64748b;
  text-align: center;
}

.pagination-card {
  align-items: center;
  justify-content: center;
}

.page-info {
  color: #475569;
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 980px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .module-header,
  .section-card,
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
  .pagination-card,
  .panel-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-buttons {
    width: 100%;
  }

  .btn-primary,
  .btn-secondary,
  .page-btn {
    width: 100%;
  }
}
</style>
