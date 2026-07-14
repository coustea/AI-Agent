<template>
  <div class="reading-resource" :class="{ compact }">
    <div v-if="readingData && resources.length" class="reading-container">

      <div v-if="!compact && readingData.summary" class="reading-summary">
        <div class="summary-icon"><Reading class='w-4 h-4 inline-block align-middle' /></div>
        <div class="summary-text">{{ readingData.summary }}</div>
      </div>
      
      <div class="reading-list">
        <article v-for="(resource, index) in visibleResources" :key="resource.id || index" class="reading-item">
          <div class="reading-main">
            <div class="reading-header">
              <span class="reading-title">{{ resource.title || '推荐资源' }}</span>
            </div>
            
            <div class="reading-meta" v-if="!compact">
              <span>
                {{ getResourceTypeText(resource.type) }}
                <template v-if="resource.difficulty"> · {{ getDifficultyText(resource.difficulty) }}</template>
                <template v-if="resource.source"> · 来自 {{ resource.source }}</template>
                <template v-if="resource.authors && resource.authors.length"> · {{ resource.authors.join(', ') }}</template>
              </span>
            </div>
            
            <div class="reading-reason" v-if="getRecommendReason(resource) && !compact">
              {{ getRecommendReason(resource) }}
            </div>
            
            <div class="reading-url" v-if="resource.url && !compact">
              <LinkIcon class="w-3.5 h-3.5 inline-block mr-1 opacity-50" />
              <span class="url-text" :title="resource.url">{{ resource.url }}</span>
            </div>
          </div>
          
          <div class="reading-action" v-if="resource.url">
            <a :href="resource.url" target="_blank" rel="noopener noreferrer" class="visit-btn" title="前往阅读">
              <span>前往阅读</span>
              <ArrowRightIcon class="w-4 h-4" />
            </a>
          </div>
        </article>
      </div>

      <div v-if="compact && resources.length > visibleResources.length" class="reading-more">
        <button class="btn-link text-blue hover:underline more-btn-hud">
          查看全部资源 ({{ resources.length }}) <ArrowRightIcon class='w-4 h-4 inline-block align-middle' />
        </button>
      </div>
    </div>

    <div v-else class="reading-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>未检测到阅读内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 拓展阅读渲染器：展示推荐资源列表（书籍/论文/文章），含摘要、难度、链接

import { computed } from 'vue'
import {
  PhArrowRight as ArrowRightIcon,
  PhBookOpen as Reading,
  PhLink as LinkIcon
} from '@phosphor-icons/vue'
import { normalizeReadingArtifact, type ResourceArtifactLike } from '../artifact'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

// 规范化后的阅读推荐数据
const readingData = computed<Record<string, any> | null>(() => {
  return normalizeReadingArtifact(props.resultData)
})

const resources = computed<any[]>(() => {
  return readingData.value?.resources || []
})

// 紧凑模式只显示前 3 条
const visibleResources = computed(() => {
  return props.compact ? resources.value.slice(0, 3) : resources.value
})

const getRecommendReason = (resource: Record<string, any>) => {
  return resource.recommend_reason || resource.reason || resource.relevance || ''
}

// 资源类型的中文映射
const getResourceTypeText = (type?: string) => {
  const map: Record<string, string> = {
    book: '书籍',
    paper: '论文',
    article: '文章',
    documentation: '文档',
    practice_project: '项目'
  }
  return map[type || ''] || '资源'
}

const getDifficultyText = (difficulty?: string) => {
  const map: Record<string, string> = {
    basic: '入门',
    medium: '中等',
    advanced: '进阶'
  }
  return map[difficulty || ''] || '适中'
}
</script>

<style scoped>
.reading-resource {
  width: 100%;
  --primary: var(--color-primary);
  --bg: var(--color-surface);
  --fg: var(--color-text);
  --border: var(--color-border);
  --accent: var(--color-primary);
}

.reading-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.reading-summary {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.summary-icon {
  font-size: 1.5rem;
  color: var(--color-primary-text);
  opacity: 0.8;
}

.summary-text {
  font-family: var(--font-sans);
  font-size: 0.95rem;
  color: var(--color-text);
  line-height: 1.6;
}

.reading-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reading-item {
  padding: 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.reading-item:hover {
  border-color: #bbd2fb;
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.reading-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.reading-header {
  display: flex;
  align-items: center;
  margin-bottom: 2px;
}

.reading-title {
  font-family: var(--font-sans);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text-strong);
  line-height: 1.4;
}

.reading-meta {
  display: flex;
  align-items: center;
  font-family: var(--font-sans);
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.reading-meta span {
  display: inline-block;
}

.reading-reason {
  font-family: var(--font-sans);
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.reading-url {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-text-faint);
  display: flex;
  align-items: center;
  margin-top: 6px;
  overflow: hidden;
}

.url-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reading-action {
  flex-shrink: 0;
}

.visit-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #eff6ff;
  color: #2563eb;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
}

.visit-btn:hover {
  background: #2563eb;
  color: white;
}

.reading-more {
  display: flex;
  justify-content: center;
}

.more-btn-hud {
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 600;
}

.reading-empty-hud {
  padding: 60px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px solid var(--color-border);
  background: #ffffff;
  padding: 40px 60px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  color: var(--color-primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: var(--font-sans);
  font-size: 0.8rem;
  color: var(--color-text-faint);
}

.compact .reading-container {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}
.compact .reading-list { gap: 12px; }
.compact .reading-item { padding: 16px; gap: 16px; }
.compact .reading-header { margin-bottom: 0; }
.compact .reading-title { font-size: 0.95rem; }
.compact .visit-btn { padding: 6px 12px; font-size: 0.85rem; }
</style>
