<template>
  <div class="practice-tab">
    <header class="dashboard-header">
      <div class="header-content">
        <h1>AI Practice Center</h1>
        <p class="subtitle">Focus on your daily goals, recommended tasks, and comprehensive review.</p>
      </div>
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">Total Attempted</span>
          <strong class="metric-value">{{ stats.totalAttempted }}</strong>
        </div>
        <div class="metric-card">
          <span class="metric-label">Accuracy</span>
          <strong class="metric-value">{{ accuracyText }}</strong>
        </div>
        <div class="metric-card warning">
          <span class="metric-label">To Review</span>
          <strong class="metric-value">{{ wrongTotal }}</strong>
        </div>
      </div>
    </header>

    <div class="main-grid">
      <!-- Left Column: Tasks -->
      <div class="tasks-column">
        <h2 class="section-title">Today's Tasks</h2>
        
        <div class="task-card primary-task">
          <div class="task-info">
            <h3>Recommended Practice</h3>
            <p>A curated set of {{ recommendedCount }} questions based on your current courses and weak points.</p>
            <div class="tags">
              <span class="tag">{{ recommendedSubject }}</span>
              <span class="tag">{{ recommendedCount }} questions</span>
            </div>
          </div>
          <button class="btn-primary" :disabled="practiceLoading" @click="$emit('start-recommended')">
            {{ practiceLoading ? 'Loading...' : 'Start Practice' }}
          </button>
        </div>

        <div class="task-card danger-task">
          <div class="task-info">
            <h3>Wrong Questions Review</h3>
            <p>You have {{ wrongTotal }} questions that need your attention. Prioritize these to improve your accuracy.</p>
          </div>
          <button class="btn-danger" @click="$emit('switch-tab', 'wrong')">
            Review Now
          </button>
        </div>

        <div class="task-card">
          <div class="task-info">
            <h3>Mock Exam Builder</h3>
            <p>Ready for a test? Configure a custom paper based on subjects, difficulty, and question types.</p>
          </div>
          <button class="btn-secondary" @click="$emit('switch-tab', 'paper')">
            Build Exam
          </button>
        </div>
      </div>

      <!-- Right Column: Custom Practice & Daily Pick -->
      <div class="sidebar-column">
        <!-- Daily Pick -->
        <div class="panel">
          <div class="panel-header">
            <h3>Daily Pick</h3>
            <button class="btn-icon" @click="$emit('refresh-daily')" title="Refresh Daily Question">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            </button>
          </div>
          <div v-if="dailyQuestion" class="daily-question">
            <div class="tags small-tags">
              <span class="tag outline">{{ dailyQuestion.subject }}</span>
              <span class="tag outline">{{ dailyQuestion.type }}</span>
            </div>
            <div class="question-content" v-html="renderInline(dailyQuestion.content)"></div>
            <button class="btn-primary full-width" @click="$emit('start-daily')">Solve</button>
          </div>
          <div v-else class="empty-state">
            No daily question available.
          </div>
        </div>

        <!-- Custom Practice Form -->
        <div class="panel">
          <h3>Custom Practice</h3>
          <form @submit.prevent="handleCustomStart" class="custom-form">
            <div class="form-group">
              <label>Subject</label>
              <select v-model="form.subject" class="select-input">
                <option value="">All Subjects</option>
                <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Difficulty</label>
              <select v-model="form.difficulty" class="select-input">
                <option value="">Any Difficulty</option>
                <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Type</label>
              <select v-model="form.type" class="select-input">
                <option value="">All Types</option>
                <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Count</label>
              <input type="number" v-model="form.count" min="1" max="30" class="text-input" />
            </div>
            <button type="submit" class="btn-primary full-width" :disabled="practiceLoading">
              {{ practiceLoading ? 'Loading...' : 'Generate Practice' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue'

const props = defineProps<{
  stats: { totalAttempted: number; totalCorrect: number }
  wrongTotal: number
  recommendedSubject: string
  recommendedCount: number
  practiceLoading: boolean
  dailyQuestion: any | null
  subjects: string[]
  difficulties: string[]
  types: string[]
}>()

const emit = defineEmits<{
  (e: 'switch-tab', tab: string): void
  (e: 'start-recommended'): void
  (e: 'start-daily'): void
  (e: 'start-custom', config: any): void
  (e: 'refresh-daily'): void
}>()

const form = reactive({
  subject: '',
  difficulty: '',
  type: '',
  count: 10
})

const accuracyText = computed(() => {
  if (!props.stats.totalAttempted) return '0%'
  return `${Math.round((props.stats.totalCorrect / props.stats.totalAttempted) * 100)}%`
})

function handleCustomStart() {
  emit('start-custom', { ...form })
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
.practice-tab {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 1px solid #E5E7EB;
  padding-bottom: 24px;
}

.header-content h1 {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #6B7280;
  margin: 0;
  font-size: 14px;
}

.metrics-grid {
  display: flex;
  gap: 16px;
}

.metric-card {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  min-width: 120px;
}

.metric-card.warning {
  background: #FEF2F2;
  border-color: #FCA5A5;
}

.metric-card.warning .metric-value {
  color: #DC2626;
}

.metric-label {
  font-size: 12px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

.main-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 32px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #111827;
}

.tasks-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  transition: border-color 0.15s ease;
}

.task-card:hover {
  border-color: #D1D5DB;
}

.primary-task {
  border: 1px solid #111827;
  background: #F9FAFB;
}

.danger-task {
  border: 1px solid #FECACA;
}

.task-info h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.task-info p {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #4B5563;
  line-height: 1.5;
}

.tags {
  display: flex;
  gap: 8px;
}

.tag {
  background: #E5E7EB;
  color: #374151;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
}

.tag.outline {
  background: transparent;
  border: 1px solid #D1D5DB;
}

.sidebar-column {
  display: flex;
  flex-direction: column;
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

.panel h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  color: #6B7280;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 4px;
}

.btn-icon:hover {
  background: #F3F4F6;
  color: #111827;
}

.daily-question {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.question-content {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
  max-height: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 5;
  -webkit-box-orient: vertical;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.select-input, .text-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 14px;
  color: #111827;
  background: #FFFFFF;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s ease;
  box-sizing: border-box;
}

.select-input:focus, .text-input:focus {
  border-color: #111827;
}

/* Buttons */
.btn-primary {
  background: #111827;
  color: #FFFFFF;
  border: none;
  padding: 8px 16px;
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
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  background: #FFFFFF;
  color: #111827;
  border: 1px solid #D1D5DB;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary:hover {
  background: #F9FAFB;
  border-color: #9CA3AF;
}

.btn-danger {
  background: #FEF2F2;
  color: #DC2626;
  border: 1px solid #FECACA;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-danger:hover {
  background: #FEE2E2;
}

.full-width {
  width: 100%;
}

.empty-state {
  text-align: center;
  padding: 32px 0;
  color: #6B7280;
  font-size: 14px;
}
</style>
