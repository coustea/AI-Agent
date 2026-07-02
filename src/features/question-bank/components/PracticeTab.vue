<template>
  <div class="practice-shell">
    <section class="practice-section recommendation-section">
      <div class="section-head">
        <div>
          <span class="section-kicker">智能推荐</span>
          <h3>推荐练习</h3>
        </div>
        <button class="primary-btn" type="button" :disabled="practiceLoading" @click="$emit('start-recommended')">
          {{ practiceLoading ? '生成中...' : '开始推荐练习' }}
        </button>
      </div>

      <div class="summary-grid">
        <div class="summary-item">
          <span>推荐学科</span>
          <strong>{{ recommendedSubject || '未指定' }}</strong>
        </div>
        <div class="summary-item">
          <span>推荐数量</span>
          <strong>{{ recommendedCount }} 题</strong>
        </div>
        <div class="summary-item">
          <span>正确率</span>
          <strong>{{ accuracyText }}</strong>
        </div>
        <div class="summary-item">
          <span>错题数量</span>
          <strong>{{ wrongTotal }} 题</strong>
        </div>
      </div>
    </section>

    <section class="practice-section custom-section">
      <div class="section-head compact-head">
        <div class="compact-title">
          <span class="section-kicker">自定义练习</span>
          <p>按学科、难度和题型快速开始一组练习</p>
        </div>
      </div>

      <form class="custom-form" @submit.prevent="handleCustomStart">
        <div class="field-group">
          <label>学科</label>
          <select v-model="form.subject" class="field">
            <option value="">全部学科</option>
            <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>

        <div class="field-group">
          <label>难度</label>
          <select v-model="form.difficulty" class="field">
            <option value="">不限难度</option>
            <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>

        <div class="field-group">
          <label>题型</label>
          <select v-model="form.type" class="field">
            <option value="">全部题型</option>
            <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
          </select>
        </div>

        <div class="field-group">
          <label>题量</label>
          <input v-model="form.count" type="number" min="1" max="30" class="field count-field" />
        </div>

        <div class="field-group action-cell">
          <button class="primary-btn" type="submit" :disabled="practiceLoading">
            {{ practiceLoading ? '生成中...' : '开始自定义练习' }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'

const props = defineProps<{
  stats: { totalAttempted: number; totalCorrect: number }
  wrongTotal: number
  recommendedSubject: string
  recommendedCount: number
  practiceLoading: boolean
  subjects: string[]
  difficulties: string[]
  types: string[]
}>()

const emit = defineEmits<{
  (e: 'switch-tab', tab: string): void
  (e: 'start-recommended'): void
  (e: 'start-custom', config: { subject: string; difficulty: string; type: string; count: number }): void
}>()

const form = reactive({
  subject: '',
  difficulty: '',
  type: '',
  count: 10,
})

const accuracyText = computed(() => {
  if (!props.stats.totalAttempted) return '0%'
  return `${Math.round((props.stats.totalCorrect / props.stats.totalAttempted) * 100)}%`
})

function handleCustomStart() {
  emit('start-custom', { ...form })
}
</script>

<style scoped>
.practice-shell {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.practice-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-section {
  padding-bottom: 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.compact-head {
  align-items: center;
  justify-content: flex-start;
}

.section-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.compact-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.compact-title p {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.section-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 1.1rem;
  font-weight: 700;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.92);
}

.summary-item span {
  color: #64748b;
  font-size: 12px;
}

.summary-item strong {
  color: #0f172a;
  font-size: 15px;
}

.custom-section {
  gap: 10px;
}

.custom-form {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) repeat(2, minmax(0, 1fr)) 104px auto;
  align-items: end;
  gap: 10px 12px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-group.action-cell {
  justify-content: flex-end;
}

.field-group label {
  color: #475569;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.field {
  width: 100%;
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  outline: none;
  box-sizing: border-box;
}

.count-field {
  text-align: center;
}

.primary-btn {
  min-height: 38px;
  padding: 0 16px;
  border: 1px solid #0f172a;
  border-radius: 12px;
  background: #0f172a;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .custom-form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field-group.action-cell {
    grid-column: span 2;
  }
}

@media (max-width: 640px) {
  .section-head {
    flex-direction: column;
    align-items: stretch;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .compact-title {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
  }

  .custom-form {
    grid-template-columns: 1fr;
  }

  .field-group.action-cell {
    grid-column: auto;
  }
}
</style>
