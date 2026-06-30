<template>
  <div class="daily-tab-shell">
    <section v-if="dailyQuestion" class="daily-question-block">
      <div class="question-meta">
        <div class="meta-left">
          <span class="meta-title">今日一题</span>
          <div class="meta-tags">
            <span class="meta-tag">{{ dailyQuestion.subject }}</span>
            <span class="meta-tag muted">{{ dailyQuestion.type }}</span>
          </div>
        </div>

        <div class="action-row">
          <button class="action-btn secondary" type="button" @click="$emit('refresh-daily')">换一题</button>
          <button class="action-btn primary" type="button" @click="$emit('start-daily')">开始作答</button>
        </div>
      </div>

      <div class="question-content" v-html="renderInline(dailyQuestion.content)"></div>
    </section>

    <section v-else class="daily-empty">
      <div class="empty-copy">
        <strong>今日一题暂未生成</strong>
        <p>当前没有可用题目，可重新获取一题。</p>
      </div>
      <button class="action-btn secondary" type="button" @click="$emit('refresh-daily')">换一题</button>
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
.daily-tab-shell {
  display: flex;
  flex-direction: column;
}

.daily-question-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 4px;
}

.question-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.meta-title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.meta-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.92);
  color: #334155;
  font-size: 12px;
  font-weight: 600;
}

.meta-tag.muted {
  background: #fff;
}

.question-content {
  max-height: 160px;
  overflow-y: auto;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.65;
  padding-right: 4px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.action-btn.secondary {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 9px;
  font-size: 12px;
}

.action-btn.primary {
  border-color: #0f172a;
  background: #0f172a;
  color: #fff;
}

.daily-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 88px;
  padding-top: 4px;
}

.empty-copy {
  min-width: 0;
}

.daily-empty strong {
  color: #0f172a;
  font-size: 15px;
  line-height: 1.3;
}

.daily-empty p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 640px) {
  .question-meta,
  .daily-empty {
    flex-direction: column;
    align-items: stretch;
  }

  .action-row {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
