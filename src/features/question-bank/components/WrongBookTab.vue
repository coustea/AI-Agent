<template>
  <div class="wrong-shell">
    <section class="list-section">
      <div class="section-head">
        <div>
          <span class="section-kicker">错题列表</span>
          <h3>错题管理</h3>
        </div>
      </div>

      <div class="filter-row">
        <input
          v-model="filters.query"
          type="text"
          class="filter-field search"
          placeholder="搜索错题"
          @keyup.enter="$emit('search-wrong')"
        />
        <select v-model="filters.subject" class="filter-field" @change="$emit('search-wrong')">
          <option value="">全部学科</option>
          <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
        </select>
        <select v-model="filters.type" class="filter-field" @change="$emit('search-wrong')">
          <option value="">全部题型</option>
          <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
        </select>
      </div>

      <div v-if="loading" class="simple-empty">正在加载错题...</div>

      <div v-else class="wrong-list">
        <article v-for="question in questions" :key="question.id" class="wrong-item">
          <div class="wrong-head">
            <div class="wrong-tags">
              <span>{{ question.subject }}</span>
              <span>{{ question.type }}</span>
              <span>错 {{ question.wrong_count || 1 }} 次</span>
            </div>
          </div>

          <div class="wrong-summary" v-html="renderInline(question.content)"></div>

          <div v-if="openedAnalysis.has(question.id)" class="wrong-analysis">
            <p class="wrong-user-answer">
              <strong>你当时的答案：</strong>{{ formatUserAnswer(question) }}
            </p>
            <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
            <div v-html="renderInline(question.analysis || '暂无解析')"></div>
          </div>

          <div class="wrong-actions">
            <div class="left-actions">
              <button class="action-link" type="button" @click="$emit('toggle-wrong-analysis', question.id)">
                {{ openedAnalysis.has(question.id) ? '收起解析' : '查看解析' }}
              </button>
            </div>

            <div class="right-actions">
              <button class="action-link" type="button" @click="$emit('archive-wrong', question)">归档</button>
              <button class="action-link danger" type="button" @click="$emit('remove-wrong', question)">移除</button>
            </div>
          </div>
        </article>

        <div v-if="questions.length === 0" class="simple-empty">暂无错题。</div>
      </div>

      <div v-if="total > 0 && !loading" class="pagination-row">
        <button class="page-btn" :disabled="page === 1" @click="$emit('page-change', page - 1)">上一页</button>
        <span class="page-info">第 {{ page }} 页 / 共 {{ Math.ceil(total / pageSize) }} 页</span>
        <button class="page-btn" :disabled="page >= Math.ceil(total / pageSize)" @click="$emit('page-change', page + 1)">下一页</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { renderQuestionMarkdown } from '@/features/question-bank/model/questionText'

// 组件属性：错题列表与筛选过滤
defineProps<{
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
}>()

// 事件：搜索、翻页、归档、移除
defineEmits<{
  (e: 'search-wrong'): void
  (e: 'page-change', page: number): void
  (e: 'select-wrong-option', question: any, key: string): void
  (e: 'submit-wrong', question: any): void
  (e: 'toggle-wrong-analysis', id: string): void
  (e: 'archive-wrong', question: any): void
  (e: 'remove-wrong', question: any): void
}>()

function isOptionQuestion(question: any) {
  return ['选择题', '单选题', '判断题'].includes(question.type)
}

function getOptions(question: any) {
  if (question.type === '判断题') return { A: '正确', B: '错误' }
  return question.options || {}
}

function formatAnswer(ans: string) {
  return String(ans || '').replace(/,/g, '、')
}

function formatUserAnswer(question: any) {
  const raw = String(question.user_answer || '').trim()
  if (!raw) return '你未作答'

  if (isOptionQuestion(question)) {
    const optionMap = getOptions(question)
    return raw
      .split(/[、,，\s]+/)
      .map((key) => key.trim().toUpperCase())
      .filter(Boolean)
      .map((key) => `${key}. ${optionMap[key] || key}`)
      .join('；')
  }

  return raw
}

function renderInline(text: string) {
  return renderQuestionMarkdown(text)
}
</script>

<style scoped>
.wrong-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.drill-section,
.list-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.section-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 1.1rem;
  font-weight: 700;
}

.text-btn {
  border: none;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.drill-card {
  padding: 18px 20px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: #fff;
}

.drill-meta,
.wrong-tags,
.left-actions,
.right-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.drill-meta span,
.wrong-tags span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.92);
  color: #475569;
  font-size: 12px;
}

.drill-stem,
.wrong-summary,
.wrong-analysis {
  margin-top: 12px;
  color: #1e293b;
  line-height: 1.7;
}

.wrong-user-answer {
  margin: 0 0 8px;
  color: #475569;
  line-height: 1.7;
}

.wrong-user-answer strong {
  color: #0f172a;
}

.drill-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.drill-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.drill-option.selected {
  border-color: rgba(15, 23, 42, 0.35);
}

.drill-option.correct {
  border-color: rgba(16, 185, 129, 0.45);
}

.drill-option.wrong {
  border-color: rgba(239, 68, 68, 0.4);
}

.drill-option-key {
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.drill-option-text {
  flex: 1;
  text-align: left;
  line-height: 1.7;
}

.drill-answer,
.filter-field,
.page-btn {
  min-height: 40px;
  border-radius: 12px;
  font: inherit;
}

.drill-answer,
.filter-field {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  box-sizing: border-box;
  outline: none;
}

.drill-actions {
  margin-top: 14px;
}

.primary-btn,
.secondary-btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn {
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #fff;
}

.secondary-btn {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #334155;
}

.drill-result {
  margin-top: 14px;
  color: #475569;
  line-height: 1.7;
}

.drill-feedback {
  color: #6366f1;
  font-weight: 500;
}

.score-badge {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  margin-left: 8px;
  vertical-align: middle;
}

.score-badge.success {
  background: #dcfce7;
  color: #166534;
}

.score-badge.warning {
  background: #fef9c3;
  color: #854d0e;
}

.score-badge.danger {
  background: #fee2e2;
  color: #991b1b;
}

.improvement-hints {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #fffbeb;
  border: 1px solid rgba(250, 204, 21, 0.3);
}

.improvement-hints strong {
  display: block;
  margin-bottom: 6px;
  color: #92400e;
  font-size: 12px;
}

.improvement-hints ul {
  margin: 0;
  padding-left: 18px;
  color: #78350f;
  font-size: 13px;
  line-height: 1.8;
}

.improvement-hints li + li {
  margin-top: 4px;
}

.reviewing-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
  margin-right: 4px;
}

.reviewing-spinner-lg {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.reviewing-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.reviewing-text {
  color: #4338ca;
  font-size: 13px;
  font-weight: 500;
}

.filter-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) repeat(2, minmax(120px, 0.8fr));
  gap: 10px;
}

.wrong-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.wrong-item {
  padding: 16px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.wrong-head,
.wrong-actions,
.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.page-info {
  color: #64748b;
  font-size: 12px;
}

.wrong-actions {
  margin-top: 14px;
}

.action-link,
.page-btn {
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

.action-link.danger {
  color: #b91c1c;
}

.simple-empty {
  padding: 14px 0;
  color: #64748b;
}

@media (max-width: 900px) {
  .filter-row {
    grid-template-columns: 1fr;
  }

  .wrong-actions,
  .pagination-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
