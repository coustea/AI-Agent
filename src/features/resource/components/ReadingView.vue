<template>
  <div class="reading-resource" :class="{ compact }">
    <ResourceCardWrapper v-if="readingData && resources.length" :compact="compact" class="reading-container">


      <div v-if="!compact && readingData.summary" class="reading-summary">
        <div class="summary-icon"><Reading class='w-4 h-4 inline-block align-middle' /></div>
        <div class="summary-text">{{ readingData.summary }}</div>
      </div>
      
      <div class="reading-list">
        <article v-for="(resource, index) in visibleResources" :key="resource.id || index" class="reading-item">
          <div class="reading-header">
            <span class="reading-type">{{ getResourceTypeText(resource.type) }}</span>
            <span class="reading-title">{{ resource.title || '推荐资源' }}</span>
          </div>
          <div class="reading-meta" v-if="!compact">
            <span v-if="resource.authors && resource.authors.length">
              <User class='w-4 h-4 inline-block align-middle' /> {{ resource.authors.join(', ') }}
            </span>
            <span v-if="resource.source">
              来源 {{ resource.source }}
            </span>
            <span v-if="resource.difficulty" class="difficulty-tag" :class="resource.difficulty">
              {{ getDifficultyText(resource.difficulty) }}
            </span>
          </div>
          <div class="reading-reason" v-if="getRecommendReason(resource) && !compact">
            <div class="reason-label">推荐理由</div>
            {{ getRecommendReason(resource) }}
          </div>
          <div class="reading-desc" v-if="getDescription(resource) && !compact">
            {{ getDescription(resource) }}
          </div>
          <a
            v-if="resource.url"
            class="reading-link"
            :href="resource.url"
            target="_blank"
            rel="noopener noreferrer"
          >
            打开资源
          </a>
        </article>
      </div>

      <div v-if="compact && resources.length > visibleResources.length" class="reading-more">
        <button class="btn-link text-blue hover:underline more-btn-hud">
          查看全部资源 ({{ resources.length }}) <ArrowRight class='w-4 h-4 inline-block align-middle' />
        </button>
      </div>

      <div class="frame-footer">
        <span class="mono-tag">知识同步完成</span>
        <div class="footer-line"></div>
      </div>
    </ResourceCardWrapper>
    
    <div v-else class="reading-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>未检测到阅读内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  PhUser as User,
  PhArrowRight as ArrowRight,
  PhBookOpen as Reading
} from '@phosphor-icons/vue'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import { normalizeReadingArtifact, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const readingData = computed<Record<string, any> | null>(() => {
  return normalizeReadingArtifact(props.resultData)
})

const resources = computed<any[]>(() => {
  return readingData.value?.resources || []
})

const visibleResources = computed(() => {
  return props.compact ? resources.value.slice(0, 3) : resources.value
})

const getRecommendReason = (resource: Record<string, any>) => {
  return resource.recommend_reason || resource.reason || resource.relevance || ''
}

const getDescription = (resource: Record<string, any>) => {
  return resource.description || resource.content || resource.abstract || resource.summary || ''
}

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
  --primary: var(--color-primary); /* Slate 600 */
  --bg: var(--color-surface);
  --fg: var(--color-text); /* Slate 700 */
  --border: var(--color-border);
  --accent: var(--color-primary); /* Indigo 500 */
}

.reading-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 头部 HUD */
.frame-header {
  position: absolute;
  top: 12px;
  left: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: none;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.technical-label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--primary);
  letter-spacing: 1px;
}

/* 底部 HUD */
.frame-footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mono-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--primary);
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

.reading-summary {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  border: none;
  box-shadow: none;
}

.summary-icon {
  font-size: 1.5rem;
  color: var(--primary);
  opacity: 0.8;
}

.summary-text {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--fg);
  line-height: 1.6;
}

.reading-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
}

.reading-item {
  padding: 24px;
  border: none;
  border-left: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: transparent;
  transition: all 0.3s ease;
  box-shadow: none;
  display: flex;
  flex-direction: column;
}

.reading-item:hover {
  background: rgba(0, 0, 0, 0.03);
  border-left-color: var(--primary);
  box-shadow: none;
  transform: translateX(4px);
}

.reading-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.reading-type {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 2px 8px;
  background: var(--primary);
  color: white;
  border-radius: 2px;
  letter-spacing: 1px;
}

.reading-title {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--fg);
  line-height: 1.4;
}

.reading-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: 16px;
}

.reading-meta span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.difficulty-tag {
  font-size: 0.7rem;
  padding: 1px 8px;
  border: 1px solid var(--color-border-hover);
  border-radius: 2px;
  color: var(--color-text-muted);
}

.difficulty-tag.basic { color: var(--accent); border-color: var(--accent); }
.difficulty-tag.medium { color: var(--color-warning); border-color: var(--color-warning); } /* Amber 500 */
.difficulty-tag.advanced { color: var(--color-danger); border-color: var(--color-danger); } /* Red 500 */

.reading-reason {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--fg);
  background: rgba(0, 0, 0, 0.02);
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  line-height: 1.6;
  border: none;
}

.reason-label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: bold;
  color: var(--primary);
  margin-bottom: 8px;
}

.reading-desc {
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.reading-link {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  margin-top: 14px;
  padding: 7px 12px;
  border: 1px solid var(--primary);
  border-radius: 4px;
  color: var(--primary);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.6px;
  text-decoration: none;
  transition: background 0.2s ease, color 0.2s ease;
}

.reading-link:hover {
  background: var(--primary);
  color: #fff;
}

.reading-more {
  display: flex;
  justify-content: center;
}

.more-btn-hud {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  letter-spacing: 1px;
}

.reading-empty-hud {
  padding: 60px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px dashed var(--border);
  padding: 40px 60px;
  border-radius: 4px;
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-text-faint);
  letter-spacing: 1px;
}

/* 紧凑模式 */
.compact .reading-container {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}
.compact .frame-corners,
.compact .frame-header,
.compact .frame-footer {
  display: none;
}
.compact .reading-list { gap: 12px; }
.compact .reading-item { padding: 12px; }
.compact .reading-header { margin-bottom: 0; }
.compact .reading-title { font-size: 0.9rem; }
</style>
