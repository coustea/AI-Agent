<template>
  <div class="history-tab-shell">
    <div class="history-toolbar">
      <div class="filter-group">
        <select v-model="localSubject" class="filter-select" @change="handleFilterChange">
          <option value="">全部科目</option>
          <option v-for="s in subjects" :key="s" :value="s">{{ s }}</option>
        </select>
        <select v-model="localCorrect" class="filter-select" @change="handleFilterChange">
          <option value="">全部结果</option>
          <option value="true">答对</option>
          <option value="false">答错</option>
        </select>
      </div>
      <div class="history-summary">
        <span>共 <strong>{{ total }}</strong> 道题</span>
        <span>答对 <strong class="correct-count">{{ correctCount }}</strong></span>
        <span>答错 <strong class="wrong-count">{{ wrongCount }}</strong></span>
      </div>
    </div>

    <div v-if="loading" class="state-block">正在加载答题历史...</div>

    <div v-else-if="items.length === 0" class="state-block empty">
      <span class="empty-icon">📋</span>
      <p>暂无答题记录</p>
      <small>去刷几道题吧</small>
    </div>

    <div v-else class="history-list">
      <div
        v-for="item in items"
        :key="item.question_id"
        :class="['history-item', { correct: item.is_correct, wrong: !item.is_correct }]"
      >
        <div class="history-item-head">
          <span :class="['result-dot', item.is_correct ? 'correct' : 'wrong']"></span>
          <span class="history-subject">{{ item.subject || '未知科目' }}</span>
          <span class="history-type">{{ toQuestionTypeLabel(item.question_type || '') }}</span>
          <span v-if="item.score != null" :class="['history-score', item.is_correct ? 'correct' : 'wrong']">
            {{ item.score }}分
          </span>
          <span v-if="item.attempts > 1" class="history-attempts">×{{ item.attempts }}</span>
        </div>
        <div class="history-item-foot">
          <span class="history-answer" v-if="item.last_answer">最后作答：{{ item.last_answer }}</span>
          <div class="history-item-actions">
            <span class="history-time">{{ formatTime(item.created_at) }}</span>
            <button class="history-open-btn" type="button" @click="emit('open-question', item.question_id)">
              查看题目
              <PhArrowRight :size="14" weight="bold" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button type="button" class="page-btn" :disabled="currentPage <= 1" @click="goPage(currentPage - 1)">上一页</button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button type="button" class="page-btn" :disabled="currentPage >= totalPages" @click="goPage(currentPage + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { PhArrowRight } from '@phosphor-icons/vue'
import { fetchQuizHistoryList, toQuestionTypeLabel, type QuizAnswerHistoryItem } from '@/features/question-bank/api/quizBank'

const emit = defineEmits<{
  (e: 'open-question', questionId: string): void
}>()

const PAGE_SIZE = 15

const items = ref<QuizAnswerHistoryItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const loading = ref(false)
const localSubject = ref('')
const localCorrect = ref('')
const subjects = ref<string[]>([])

const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))
const correctCount = computed(() => items.value.filter((i) => i.is_correct).length)
const wrongCount = computed(() => items.value.filter((i) => !i.is_correct).length)

async function loadHistory() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: PAGE_SIZE,
    }
    if (localSubject.value) params.subject = localSubject.value
    if (localCorrect.value) params.is_correct = localCorrect.value === 'true'

    const resp = await fetchQuizHistoryList(params)
    items.value = resp.items || []
    total.value = resp.total || 0
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  currentPage.value = 1
  void loadHistory()
}

function goPage(p: number) {
  currentPage.value = p
  void loadHistory()
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => {
  void loadHistory()
})
</script>

<style scoped>
.history-tab-shell {
  padding: 0;
}

.history-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  gap: 8px;
}

.filter-select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  color: #1e293b;
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: #6366f1;
}

.history-summary {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: #64748b;
}

.correct-count {
  color: #16a34a;
}

.wrong-count {
  color: #dc2626;
}

.state-block {
  padding: 48px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
}

.state-block.empty .empty-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}

.state-block.empty p {
  margin: 0 0 4px;
  font-size: 15px;
  color: #64748b;
}

.state-block.empty small {
  font-size: 13px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f8fafc;
  border-left: 3px solid transparent;
  transition: background 0.15s;
}

.history-item:hover {
  background: #f1f5f9;
}

.history-item.correct {
  border-left-color: #22c55e;
}

.history-item.wrong {
  border-left-color: #ef4444;
}

.history-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.result-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.result-dot.correct {
  background: #22c55e;
}

.result-dot.wrong {
  background: #ef4444;
}

.history-subject {
  font-weight: 600;
  color: #1e293b;
}

.history-type {
  color: #6366f1;
  font-size: 12px;
}

.history-score {
  font-size: 12px;
  font-weight: 700;
}

.history-score.correct {
  color: #15803d;
}

.history-score.wrong {
  color: #b91c1c;
}

.history-attempts {
  margin-left: auto;
  background: #fef3c7;
  color: #92400e;
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 600;
}

.history-item-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
}

.history-answer {
  color: #64748b;
}

.history-item-actions,
.history-open-btn {
  display: inline-flex;
  align-items: center;
}

.history-item-actions {
  gap: 12px;
  margin-left: auto;
}

.history-open-btn {
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.history-open-btn:hover {
  background: #f1f5f9;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.page-btn {
  padding: 5px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  color: #1e293b;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-btn:not(:disabled):hover {
  background: #f1f5f9;
}

.page-info {
  font-size: 13px;
  color: #64748b;
}

@media (max-width: 640px) {
  .history-item-foot {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .history-item-actions {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
  }
}
</style>
