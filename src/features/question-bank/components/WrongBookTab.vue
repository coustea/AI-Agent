<template>
  <div class="wrong-shell">
    <section class="drill-section">
      <div class="section-head">
        <div>
          <span class="section-kicker">随机错题再练</span>
          <h3>再练一题</h3>
        </div>
        <button class="text-btn" type="button" @click="$emit('pick-drill')">换一题</button>
      </div>

      <div v-if="drillQuestion" class="drill-card">
        <div class="drill-meta">
          <span>{{ drillQuestion.subject }}</span>
          <span>{{ drillQuestion.type }}</span>
        </div>

        <div class="drill-stem" v-html="renderInline(drillQuestion.content)"></div>

        <div v-if="isOptionQuestion(drillQuestion)" class="drill-options">
          <button
            v-for="(text, key) in getOptions(drillQuestion)"
            :key="key"
            type="button"
            :class="[
              'drill-option',
              {
                selected: isDrillSelected(String(key)),
                correct: drillSubmitted && isCorrectOption(drillQuestion, String(key)),
                wrong: drillSubmitted && isDrillSelected(String(key)) && !isCorrectOption(drillQuestion, String(key)),
              },
            ]"
            :disabled="drillSubmitted"
            @click="$emit('select-drill-option', String(key))"
          >
            <span class="drill-option-key">{{ key }}</span>
            <span class="drill-option-text" v-html="renderInline(text as string)"></span>
          </button>
        </div>

        <textarea
          v-else
          :value="drillAnswer"
          class="drill-answer"
          rows="4"
          placeholder="输入你的答案"
          :disabled="drillSubmitted"
          @input="$emit('update:drillAnswer', ($event.target as HTMLTextAreaElement).value)"
        ></textarea>

        <div class="drill-actions">
          <button
            v-if="!drillSubmitted"
            class="primary-btn"
            type="button"
            :disabled="!hasDrillAnswer || drillReviewing"
            @click="$emit('submit-drill')"
          >
            {{ drillReviewing ? '评阅中...' : '提交答案' }}
          </button>
          <button v-else class="secondary-btn" type="button" @click="$emit('pick-drill')">再练一题</button>
        </div>

        <div v-if="drillSubmitted" class="drill-result">
          <strong>{{ drillCorrect ? '已掌握' : '仍需复习' }}</strong>
          <p>参考答案：{{ formatAnswer(drillQuestion.answer) }}</p>
          <p v-if="drillReview?.feedback">{{ drillReview.feedback }}</p>
        </div>
      </div>

      <div v-else class="simple-empty">暂无可重练的错题。</div>
    </section>

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
            <span class="wrong-no">#{{ String(question.id).split('-')[0] }}</span>
          </div>

          <div class="wrong-summary">{{ summarizeText(question.content) }}</div>

          <div v-if="openedAnalysis.has(question.id)" class="wrong-analysis">
            <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
            <div v-html="renderInline(question.analysis || '暂无解析')"></div>
          </div>

          <AlgorithmVisualizer v-if="openedVisualizer.has(question.id)" :question="question" />

          <div class="wrong-actions">
            <div class="left-actions">
              <button class="action-link" type="button" @click="$emit('toggle-wrong-analysis', question.id)">
                {{ openedAnalysis.has(question.id) ? '收起解析' : '查看解析' }}
              </button>
              <button
                v-if="canVisualize(question)"
                class="action-link"
                type="button"
                @click="toggleVisualizer(question.id)"
              >
                {{ openedVisualizer.has(question.id) ? '收起可视化' : '算法可视化' }}
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
import { computed, ref } from 'vue'
import AlgorithmVisualizer from '@/features/question-bank/components/AlgorithmVisualizer.vue'
import { supportsAlgorithmVisualization } from '@/features/question-bank/utils/algorithmVisualization'

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

const openedVisualizer = ref<Set<string>>(new Set())

const hasDrillAnswer = computed(() => {
  const ans = props.drillAnswer
  if (Array.isArray(ans)) return ans.length > 0
  return !!ans && String(ans).trim().length > 0
})

function toggleVisualizer(id: string) {
  const next = new Set(openedVisualizer.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  openedVisualizer.value = next
}

function canVisualize(question: any) {
  return supportsAlgorithmVisualization(question)
}

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

function formatAnswer(ans: string) {
  return String(ans || '').replace(/,/g, '、')
}

function summarizeText(text: string) {
  const plain = String(text || '')
    .replace(/\s+/g, ' ')
    .replace(/[#*_`>-]/g, '')
    .trim()
  return plain.length > 120 ? `${plain.slice(0, 120)}...` : plain
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
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
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

.wrong-no,
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
