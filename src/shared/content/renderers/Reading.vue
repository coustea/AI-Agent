<template>
  <div class="reading-resource" :class="{ compact }">
    <Frame v-if="readingData && resources.length" :compact="compact" class="reading-container">

      <div v-if="!compact && readingData.summary" class="reading-summary">
        <div class="summary-icon"><Reading class='w-4 h-4 inline-block align-middle' /></div>
        <div class="summary-text">{{ readingData.summary }}</div>
      </div>
      
      <div class="reading-list">
        <article v-for="(resource, index) in visibleResources" :key="resource.id || index" class="reading-item" :class="resource.type">
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
          
          <!-- Explicitly styled URL tag link -->
          <div v-if="resource.url" class="reading-url-wrap">
            <LinkIcon class="w-3.5 h-3.5 text-slate-400 inline-block align-middle mr-1.5" />
            <a :href="resource.url" target="_blank" rel="noopener noreferrer" class="reading-url-link">
              {{ getDisplayDomain(resource.url) }} ↗
            </a>
          </div>

          <a
            v-if="resource.url"
            class="reading-action-btn"
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
          查看全部资源 ({{ resources.length }}) <ArrowRightIcon class='w-4 h-4 inline-block align-middle' />
        </button>
      </div>

      <div class="frame-footer">
        <span class="mono-tag">知识同步完成</span>
        <div class="footer-line"></div>
      </div>
    </Frame>
    
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
  PhArrowRight as ArrowRightIcon,
  PhBookOpen as Reading,
  PhLink as LinkIcon
} from '@phosphor-icons/vue'
import Frame from '../Frame.vue'
import { normalizeReadingArtifact, type ResourceArtifactLike } from '../artifact'

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

const getDisplayDomain = (urlStr?: string) => {
  if (!urlStr) return ''
  try {
    const url = new URL(urlStr)
    return url.hostname
  } catch (e) {
    return urlStr
  }
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

.frame-footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mono-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--color-border), transparent);
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
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 24px;
}

.reading-item {
  padding: 24px;
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-primary);
  border-radius: var(--radius-md);
  background: #ffffff;
  transition: all 0.2s cubic-bezier(0.32, 0.72, 0, 1);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reading-item:hover {
  background: #ffffff;
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-md);
  transform: translateY(-1.5px);
}

.reading-item.book {
  border-left-color: var(--cat-path, #F59E0B);
}
.reading-item.paper {
  border-left-color: var(--color-primary);
}
.reading-item.article {
  border-left-color: var(--cat-tutor, #1E40AF);
}
.reading-item.documentation {
  border-left-color: var(--cat-rose, #F43F5E);
}

.reading-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.reading-type {
  font-family: var(--font-sans);
  font-size: 0.7rem;
  padding: 2px 8px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-weight: 700;
}

.reading-title {
  font-family: var(--font-sans);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text-strong);
  line-height: 1.4;
}

.reading-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  font-family: var(--font-sans);
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.reading-meta span {
  display: flex;
  align-items: center;
  gap: 6px;
}

.difficulty-tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-weight: 600;
}

.difficulty-tag.basic { color: var(--color-primary-text); background: var(--color-primary-soft); }
.difficulty-tag.medium { color: var(--color-warning-text, #D97706); border-color: var(--color-warning-border); background: var(--color-warning-soft); }
.difficulty-tag.advanced { color: var(--color-danger); border-color: var(--color-danger-border); background: var(--color-danger-soft); }

.reading-reason {
  font-family: var(--font-sans);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  background: var(--color-primary-soft);
  padding: 16px;
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-sm);
  line-height: 1.6;
}

.reason-label {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-primary-text);
  margin-bottom: 6px;
  text-transform: uppercase;
}

.reading-desc {
  font-family: var(--font-sans);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.reading-url-wrap {
  display: flex;
  align-items: center;
  margin-top: 4px;
}

.reading-url-link {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-primary-text);
  text-decoration: none;
  font-weight: 500;
}

.reading-url-link:hover {
  text-decoration: underline;
}

.reading-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  margin-top: var(--space-2);
  height: 36px;
  padding: 0 var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  color: var(--color-primary-text);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: 600;
  text-decoration: none;
  transition: var(--btn-transition);
}

.reading-action-btn:hover {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #ffffff;
  transform: translateY(-0.5px);
  box-shadow: var(--shadow-sm);
}

.reading-action-btn:active {
  transform: translateY(0.5px);
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
.compact .frame-footer {
  display: none;
}
.compact .reading-list { gap: 12px; }
.compact .reading-item { padding: 12px; }
.compact .reading-header { margin-bottom: 0; }
.compact .reading-title { font-size: 0.9rem; }
</style>
