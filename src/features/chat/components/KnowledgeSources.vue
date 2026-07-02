<template>
  <section v-if="sources && sources.length > 0" class="knowledge-sources">
    <header class="sources-header">
      <svg class="sources-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
      <span class="sources-title">参考来源</span>
      <span class="sources-count">{{ sources.length }}</span>
    </header>

    <ul class="sources-list">
      <li v-for="(source, index) in visibleSources" :key="index" class="source-item">
        <div class="source-main">
          <strong class="source-title">{{ source.title || '未知来源' }}</strong>
          <span v-if="source.heading" class="source-heading">{{ source.heading }}</span>
        </div>
        <p class="source-summary">{{ truncateSummary(source.summary) }}</p>
      </li>
    </ul>

    <button
      v-if="sources.length > maxVisible"
      class="sources-toggle"
      type="button"
      @click="expanded = !expanded"
    >
      {{ expanded ? '收起' : `展开全部 ${sources.length} 个来源` }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { KnowledgeSource } from '@/features/chat/views/tutorUtils'

const props = defineProps<{
  sources: KnowledgeSource[]
}>()

const maxVisible = 3
const expanded = ref(false)

const visibleSources = computed(() => {
  if (expanded.value) return props.sources
  return props.sources.slice(0, maxVisible)
})

function truncateSummary(summary: string, maxLength = 120): string {
  if (!summary) return ''
  const text = summary.replace(/\s+/g, ' ').trim()
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength).trim() + '...'
}
</script>

<style scoped>
.knowledge-sources {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.6);
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sources-icon {
  width: 18px;
  height: 18px;
  color: #64748b;
}

.sources-title {
  color: #334155;
  font-size: 13px;
  font-weight: 600;
}

.sources-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.sources-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.source-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.source-item .source-title {
  color: #1e293b;
  font-size: 13px;
  font-weight: 600;
}

.source-heading {
  color: #64748b;
  font-size: 12px;
}

.source-summary {
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.sources-toggle {
  margin-top: 10px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
}

.sources-toggle:hover {
  color: #334155;
}
</style>