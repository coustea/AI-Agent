<template>
  <div class="daily-practice-tab">
    <header class="daily-header">
      <div class="header-copy">
        <span class="section-label">Daily Practice</span>
        <h2>每日练习</h2>
        <p class="subtitle">把题库入口聚焦成一件事：先完成今天这一题，再进入更完整的训练节奏。</p>
      </div>
      <div class="header-badge">
        <span>Default Entry</span>
        <strong>1 题</strong>
      </div>
    </header>

    <section class="daily-card">
      <div class="card-copy">
        <span class="eyebrow">Today's Question</span>
        <h3>每日一题</h3>
        <p class="card-description">系统会从当前题库中抽取一道适合今日完成的练习题，保持稳定的每日训练频率。</p>
      </div>

      <div v-if="dailyQuestion" class="question-panel">
        <div class="tags">
          <span class="tag">{{ dailyQuestion.subject }}</span>
          <span class="tag outline">{{ dailyQuestion.type }}</span>
        </div>
        <div class="question-content" v-html="renderInline(dailyQuestion.content)"></div>
        <div class="actions">
          <button class="btn-primary" @click="$emit('start-daily')">开始今日练习</button>
          <button class="btn-secondary" @click="$emit('refresh-daily')">重新推荐</button>
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

.daily-header,
.daily-card {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.daily-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 26px;
}

.header-copy h2,
.card-copy h3,
.empty-copy h4 {
  margin: 6px 0 0;
  color: #0f172a;
}

.header-copy h2 {
  font-size: 1.5rem;
  font-weight: 700;
}

.section-label,
.eyebrow {
  color: var(--cat-eval, #8b5cf6);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.subtitle,
.card-description,
.empty-copy p {
  margin: 10px 0 0;
  color: #64748b;
  line-height: 1.7;
}

.header-badge {
  min-width: 132px;
  padding: 16px 18px;
  border: 1px solid rgba(165, 180, 252, 0.22);
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(238, 242, 255, 0.98) 0%, rgba(255, 255, 255, 0.92) 100%);
}

.header-badge span {
  display: block;
  color: #6366f1;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.header-badge strong {
  display: block;
  margin-top: 10px;
  color: #1e1b4b;
  font-size: 2rem;
  font-weight: 800;
}

.daily-card {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 30px;
  background: linear-gradient(135deg, #ffffff 0%, var(--cat-eval-soft, #f5f3ff) 100%);
}

.card-copy {
  max-width: 760px;
}

.card-copy h3 {
  font-size: 1.7rem;
  font-weight: 800;
}

.question-panel,
.empty-state {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(79, 70, 229, 0.1);
  color: #6d28d9;
  font-size: 12px;
  font-weight: 700;
}

.tag.outline {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #475569;
}

.question-content {
  color: #334155;
  font-size: 1rem;
  line-height: 1.85;
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
}

.actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.empty-state {
  align-items: flex-start;
}

.empty-copy h4 {
  font-size: 1.1rem;
  font-weight: 700;
}

@media (max-width: 760px) {
  .daily-header {
    flex-direction: column;
  }

  .header-badge {
    min-width: 0;
    width: 100%;
  }
}

@media (max-width: 640px) {
  .daily-header,
  .daily-card,
  .question-panel,
  .empty-state {
    padding: 18px;
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
