<template>
  <div class="wrong-book-tab">

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
  gap: 24px;
}

/* ================== Layout & Shells ================== */
.main-grid {
  display: grid;
  grid-template-columns: minmax(360px, 1fr) minmax(0, 1.6fr);
  gap: 24px;
}

@media (max-width: 1024px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}

.section-card,
.question-card,
.filter-card,
.loading-card,
.empty-state,
.pagination-card {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), border-color 0.3s ease;
}

.section-card,
.question-card {
  padding: 28px;
}

.question-card:hover {
  transform: translateY(-2px);
  border-color: rgba(139, 92, 246, 0.25);
  box-shadow: 0 14px 36px rgba(139, 92, 246, 0.06), 0 4px 12px rgba(0, 0, 0, 0.01);
}

.filter-card,
.pagination-card,
.loading-card,
.empty-state {
  padding: 18px 24px;
}

.list-column,
.wrong-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ================== Typography & Headers ================== */
.section-label {
  color: #8b5cf6;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.panel-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}

/* ================== Search / Filter ================== */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.search-input-wrapper {
  position: relative;
  flex: 1 1 240px;
}

.search-icon {
  position: absolute;
  top: 50%;
  left: 14px;
  transform: translateY(-50%);
  color: #94a3b8;
}

.search-input {
  width: 100%;
  height: 42px;
  padding: 0 14px 0 38px;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.6);
  font-family: inherit;
  font-size: 13.5px;
  color: #0f172a;
  outline: none;
  box-sizing: border-box;
  transition: all 0.2s ease;
}

.search-input:focus {
  border-color: rgba(139, 92, 246, 0.4);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.08);
}

.filter-select {
  height: 42px;
  flex: 0 0 130px;
  padding: 0 12px;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.6);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  color: #334155;
  outline: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-select:focus {
  border-color: rgba(139, 92, 246, 0.4);
  background: #fff;
}

/* ================== Tags & Badges ================== */
.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.tag.danger {
  background: rgba(239, 68, 68, 0.06);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.12);
}

.tag.outline {
  background: #fff;
  color: #475569;
}

.tag.type {
  background: rgba(99, 102, 241, 0.04);
  color: #4f46e5;
  border-color: rgba(99, 102, 241, 0.12);
}

.question-id {
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  font-weight: 500;
}

/* ================== Options & Buttons ================== */
.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 14px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.55);
  text-align: left;
  color: #1e293b;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  width: 100%;
}

.option-btn:hover:not(:disabled) {
  border-color: rgba(139, 92, 246, 0.35);
  background: rgba(255, 255, 255, 0.95);
  transform: translateX(4px);
}

.option-btn:disabled {
  cursor: not-allowed;
}

.opt-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(139, 92, 246, 0.08);
  border: 1px solid rgba(139, 92, 246, 0.16);
  color: #8b5cf6;
  font-weight: 800;
  font-size: 12px;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.opt-text {
  color: #334155;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.5;
}

.option-btn.selected {
  border-color: rgba(139, 92, 246, 0.5);
  background: rgba(139, 92, 246, 0.04);
}

.option-btn.selected .opt-key {
  background: #8b5cf6;
  border-color: #8b5cf6;
  color: #fff;
  box-shadow: 0 4px 8px rgba(139, 92, 246, 0.2);
}

.option-btn.correct {
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.04);
}

.option-btn.correct .opt-key {
  background: #10b981;
  border-color: #10b981;
  color: #fff;
  box-shadow: 0 4px 8px rgba(16, 185, 129, 0.2);
}

.option-btn.wrong {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.04);
}

.option-btn.wrong .opt-key {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.2);
}

.text-area-input {
  width: 100%;
  margin-bottom: 20px;
  padding: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.6);
  font-family: inherit;
  font-size: 14px;
  color: #0f172a;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
  transition: all 0.25s ease;
}

.text-area-input:focus {
  border-color: rgba(139, 92, 246, 0.4);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1);
}

/* ================== Actions & Custom Pill Buttons ================== */
.btn-icon {
  width: 38px;
  height: 38px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.8);
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-icon:hover {
  color: #8b5cf6;
  border-color: rgba(139, 92, 246, 0.3);
  transform: rotate(45deg);
}

.btn-primary,
.btn-secondary {
  height: 40px;
  border-radius: 12px;
  font-size: 13.5px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.btn-primary {
  background: #8b5cf6;
  color: #fff;
  box-shadow: 0 4px 10px rgba(139, 92, 246, 0.15);
}

.btn-primary:hover:not(:disabled) {
  background: #7c3aed;
  box-shadow: 0 6px 14px rgba(139, 92, 246, 0.25);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(226, 232, 240, 0.9);
  color: #475569;
}

.btn-secondary:hover {
  background: #f8fafc;
  color: #1e293b;
}

.full-width {
  width: 100%;
}

/* ================== Card Footers & Specific Action Links ================== */
.card-header,
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.card-header {
  margin-bottom: 16px;
}

.card-footer {
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px solid rgba(226, 232, 240, 0.8);
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-link {
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  padding: 0 8px;
  transition: all 0.2s ease;
}

.btn-link:hover {
  color: #4f46e5;
}

/* Custom premium pills for Archive and Remove buttons */
.danger-link,
.success-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid transparent;
}

.danger-link {
  border-color: rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.04);
  color: #ef4444;
}

.danger-link:hover {
  background: #ef4444;
  color: #fff;
  border-color: #ef4444;
  box-shadow: 0 4px 10px rgba(239, 68, 68, 0.2);
}

.success-link {
  border-color: rgba(16, 185, 129, 0.2);
  background: rgba(16, 185, 129, 0.04);
  color: #10b981;
}

.success-link:hover {
  background: #10b981;
  color: #fff;
  border-color: #10b981;
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.2);
}

/* ================== Panels & Results ================== */
.result-badge {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 800;
}

.result-badge.success {
  background: rgba(209, 250, 229, 0.6);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.result-badge.danger {
  background: rgba(254, 226, 226, 0.6);
  color: #b91c1c;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.result-placeholder {
  min-height: 32px;
}

.result-panel {
  padding: 20px;
  border-radius: 20px;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-panel.success {
  background: rgba(209, 250, 229, 0.45);
  border-color: rgba(16, 185, 129, 0.15);
  color: #065f46;
}

.result-panel.danger {
  background: rgba(254, 226, 226, 0.45);
  border-color: rgba(239, 68, 68, 0.15);
  color: #991b1b;
}

.result-panel strong {
  font-size: 15px;
  font-weight: 800;
}

.ref-ans {
  font-weight: 700;
  font-size: 13.5px;
}

.feedback-text {
  font-size: 13px;
  font-weight: 700;
  color: #047857;
}

.analysis-text,
.analysis-panel {
  font-size: 13.5px;
  line-height: 1.7;
}

.analysis-panel {
  margin-top: 20px;
  padding: 20px;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.85);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.analysis-panel strong {
  display: block;
  margin-bottom: 8px;
  color: #1e293b;
}

/* ================== Pagination & States ================== */
.loading-card,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  font-size: 14px;
  color: #64748b;
  font-weight: 600;
}

.pagination-card {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.page-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 700;
}

.page-btn:hover:not(:disabled) {
  border-color: rgba(139, 92, 246, 0.3);
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.02);
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-info {
  color: #475569;
  font-size: 13.5px;
  font-weight: 700;
}

/* ================== Responsive Adjustments ================== */
@media (max-width: 720px) {
  .section-card,
  .question-card {
    padding: 20px;
  }

  .card-footer,
  .pagination-card,
  .panel-head {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .action-buttons {
    justify-content: space-between;
  }

  .btn-primary,
  .btn-secondary,
  .page-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
