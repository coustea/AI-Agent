<template>
  <div class="daily-practice-tab">
    <section class="daily-card glass-panel">
      <div class="card-copy">
        <span class="eyebrow">Today's Challenge</span>
        <h3>每日一题</h3>
        <p class="card-description">系统会从当前题库中为你精选量身定制的练习，温故而知新，今日挑战，即刻开始！</p>
      </div>

      <div v-if="dailyQuestion" class="question-panel">
        <div class="tags">
          <span class="tag subject">{{ dailyQuestion.subject }}</span>
          <span class="tag type">{{ dailyQuestion.type }}</span>
        </div>
        <div class="question-content-box">
          <div class="question-content" v-html="renderInline(dailyQuestion.content)"></div>
        </div>
        <div class="actions">
          <button class="btn-primary glow-button" @click="$emit('start-daily')">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><polygon points="6 3 20 12 6 21 6 3"/></svg>
            开始今日练习
          </button>
          <button class="btn-secondary" @click="$emit('refresh-daily')">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M16 3h5v5"/></svg>
            重新换一题
          </button>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-copy">
          <h4>暂无可用题目</h4>
          <p>当前还没有可用的每日一题，你可以重新推荐一次。</p>
        </div>
        <button class="btn-secondary" @click="$emit('refresh-daily')">重新推荐</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
interface DailyQuestion {
  subject: string
  type: string
  content: string
}

defineProps<{
  dailyQuestion: DailyQuestion | null
}>()

defineEmits<{
  (e: 'start-daily'): void
  (e: 'refresh-daily'): void
}>()

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
.daily-practice-tab {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.daily-card {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 36px;
  border-radius: 24px;
}

.card-copy {
  max-width: 760px;
}

.card-copy h3,
.empty-copy h4 {
  margin: 6px 0 0;
  color: #0f172a;
}

.card-copy h3 {
  font-size: 1.8rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.eyebrow {
  color: var(--cat-eval, #8b5cf6);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.card-description,
.empty-copy p {
  margin: 10px 0 0;
  color: #64748b;
  line-height: 1.7;
}

.question-panel,
.empty-state {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 28px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.02);
}

.tags {
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
  font-size: 12px;
  font-weight: 700;
}

.tag.subject {
  background: rgba(139, 92, 246, 0.08);
  color: #8b5cf6;
  border: 1px solid rgba(139, 92, 246, 0.16);
}

.tag.type {
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
  color: #475569;
}

.question-content-box {
  background: #f8fafc;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid rgba(226, 232, 240, 0.6);
}

.question-content {
  color: #1e293b;
  font-size: 1.05rem;
  line-height: 1.85;
}

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-primary,
.btn-secondary {
  min-height: 44px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  min-width: 150px;
}

.btn-secondary {
  min-width: 130px;
}

.empty-state {
  align-items: flex-start;
}

.empty-copy h4 {
  font-size: 1.15rem;
  font-weight: 700;
}

@media (max-width: 640px) {
  .daily-card,
  .question-panel,
  .empty-state {
    padding: 20px;
  }

  .actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
