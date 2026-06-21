<template>
  <div class="search-tab">
    <section class="filter-bar-capsule glass-panel">
      <!-- Search Input -->
      <div class="search-field">
        <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input
          v-model="filters.query"
          type="text"
          placeholder="搜索题目关键字..."
          class="search-input-raw"
          @keyup.enter="handleSearch"
        />
      </div>
      
      <div class="field-divider"></div>
      
      <!-- Select Subject -->
      <div class="select-field">
        <label>选择学科</label>
        <select v-model="filters.subject" class="select-raw" @change="handleSearch">
          <option value="">全部学科</option>
          <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
      
      <div class="field-divider"></div>
      
      <!-- Select Difficulty -->
      <div class="select-field">
        <label>设定难度</label>
        <select v-model="filters.difficulty" class="select-raw" @change="handleSearch">
          <option value="">全部难度</option>
          <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>
      
      <div class="field-divider"></div>
      
      <!-- Select Type -->
      <div class="select-field">
        <label>选择题型</label>
        <select v-model="filters.type" class="select-raw" @change="handleSearch">
          <option value="">全部题型</option>
          <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>

      <button class="btn-search-submit" @click="handleSearch">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <span>检索</span>
      </button>
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
  gap: 24px;
}

/* ================== Capsule Filter Bar ================== */
.filter-bar-capsule {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 12px 8px 24px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(140%);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 10px 30px 0 rgba(15, 23, 42, 0.04);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.filter-bar-capsule:focus-within {
  border-color: rgba(139, 92, 246, 0.35);
  box-shadow: 0 0 24px rgba(139, 92, 246, 0.12), 0 10px 30px 0 rgba(15, 23, 42, 0.04);
}

.search-field {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 2 1 240px;
  position: relative;
}

.search-icon {
  color: #94a3b8;
  flex-shrink: 0;
}

.search-input-raw {
  width: 100%;
  border: none;
  background: transparent;
  color: #0f172a;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  outline: none;
}

.search-input-raw::placeholder {
  color: #94a3b8;
}

.select-field {
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1 1 120px;
  min-width: 110px;
  padding: 0 4px;
}

.select-field label {
  font-size: 9px;
  font-weight: 800;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 2px;
}

.select-raw {
  width: 100%;
  border: none;
  background: transparent;
  color: #1e293b;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  outline: none;
  cursor: pointer;
  padding-right: 12px;
}

.field-divider {
  width: 1px;
  height: 28px;
  background: rgba(226, 232, 240, 0.9);
  flex-shrink: 0;
}

.btn-search-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  padding: 0 24px;
  border-radius: 99px;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: #fff;
  border: none;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(139, 92, 246, 0.25);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.btn-search-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.38);
}

.btn-search-submit:active {
  transform: translateY(0);
}

/* ================== Loading & Empty State ================== */
.loading-card,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 16px;
  padding: 48px 32px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  color: #64748b;
  text-align: center;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(226, 232, 240, 0.8);
  border-top-color: #8b5cf6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ================== Question List & Cards ================== */
.question-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.question-card {
  padding: 28px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.3s cubic-bezier(0.25, 0.8, 0.25, 1), border-color 0.3s ease;
}

.question-card:hover {
  transform: translateY(-2px);
  border-color: rgba(139, 92, 246, 0.25);
  box-shadow: 0 14px 36px rgba(139, 92, 246, 0.06), 0 4px 12px rgba(0, 0, 0, 0.01);
}

.card-header,
.card-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.card-header {
  align-items: center;
  margin-bottom: 20px;
}

.card-footer {
  align-items: center;
  margin-top: 12px;
  padding-top: 20px;
  border-top: 1px solid rgba(226, 232, 240, 0.8);
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
  border-radius: 99px;
  background: rgba(139, 92, 246, 0.06);
  color: #7c3aed;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(139, 92, 246, 0.12);
}

.tag.outline {
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.9);
  color: #475569;
}

.tag.type {
  border: 1px solid rgba(99, 102, 241, 0.16);
  background: rgba(99, 102, 241, 0.04);
  color: #4f46e5;
}

.tag.small {
  min-height: 24px;
  padding: 0 10px;
  font-size: 11px;
}

.success-text {
  color: #059669;
  border-color: rgba(16, 185, 129, 0.25) !important;
  background: rgba(16, 185, 129, 0.02) !important;
}

.warning-text {
  color: #d97706;
  border-color: rgba(245, 158, 11, 0.25) !important;
  background: rgba(245, 158, 11, 0.02) !important;
}

.danger-text {
  color: #dc2626;
  border-color: rgba(239, 68, 68, 0.25) !important;
  background: rgba(239, 68, 68, 0.02) !important;
}

.neutral-text {
  color: #64748b;
}

.question-id {
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  font-weight: 500;
}

.question-content {
  margin-bottom: 24px;
  color: #0f172a;
  font-size: 16px;
  line-height: 1.8;
}

/* ================== Options Styling (Circular Badge) ================== */
.options-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.55);
  text-align: left;
  color: #1e293b;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
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
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(139, 92, 246, 0.08);
  border: 1px solid rgba(139, 92, 246, 0.16);
  color: #8b5cf6;
  font-weight: 800;
  font-size: 13px;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.opt-text {
  color: #334155;
  font-size: 14.5px;
  font-weight: 500;
  line-height: 1.6;
}

.option-btn.selected {
  border-color: rgba(139, 92, 246, 0.5);
  background: rgba(139, 92, 246, 0.04);
}

.option-btn.selected .opt-key {
  background: #8b5cf6;
  border-color: #8b5cf6;
  color: #fff;
  box-shadow: 0 4px 10px rgba(139, 92, 246, 0.25);
}

.option-btn.correct {
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.04);
}

.option-btn.correct .opt-key {
  background: #10b981;
  border-color: #10b981;
  color: #fff;
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.25);
}

.option-btn.wrong {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.04);
}

.option-btn.wrong .opt-key {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
  box-shadow: 0 4px 10px rgba(239, 68, 68, 0.25);
}

.text-area-input {
  width: 100%;
  margin-top: 4px;
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  font-family: inherit;
  font-size: 14.5px;
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

/* ================== Result Badges & Footer Actions ================== */
.result-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 16px;
  border-radius: 99px;
  font-size: 13px;
  font-weight: 700;
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

.score-text {
  font-weight: 800;
  margin-left: 4px;
}

.result-placeholder {
  min-height: 36px;
}

.btn-link {
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: color 0.2s ease;
  padding: 0 8px;
}

.btn-link:hover {
  color: #4f46e5;
}

.btn-primary {
  min-height: 40px;
  padding: 0 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  background: #8b5cf6;
  color: #fff;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
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

/* ================== Analysis Panel ================== */
.analysis-panel {
  margin-top: 24px;
  padding: 24px;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.85);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.analysis-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(226, 232, 240, 0.9);
}

.analysis-header strong {
  color: #1e293b;
  font-size: 14px;
  font-weight: 800;
}

.feedback-text {
  color: #059669;
  font-size: 13px;
  font-weight: 700;
}

.analysis-content {
  color: #475569;
  font-size: 14px;
  line-height: 1.75;
}

/* ================== Pagination Card ================== */
.pagination-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.03);
}

.page-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: 12px;
  font-size: 13.5px;
  font-weight: 700;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
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

/* ================== Responsive Styles ================== */
@media (max-width: 900px) {
  .filter-bar-capsule {
    border-radius: 24px;
    flex-direction: column;
    align-items: stretch;
    padding: 20px;
    gap: 16px;
  }

  .field-divider {
    display: none;
  }

  .search-field {
    flex: 1 1 auto;
  }

  .select-field {
    flex: 1 1 auto;
  }

  .btn-search-submit {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .question-card {
    padding: 20px;
  }

  .card-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }

  .action-buttons {
    justify-content: space-between;
  }

  .btn-primary {
    flex-grow: 1;
    justify-content: center;
  }

  .pagination-card {
    flex-direction: column;
    gap: 12px;
  }

  .page-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
