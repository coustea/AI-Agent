<template>
  <div class="reading-resource" :class="{ compact }">
    <div v-if="readingData" class="technical-frame reading-container">
      <div class="frame-corners top-left"></div>
      <div class="frame-corners top-right"></div>
      <div class="frame-corners bottom-left"></div>
      <div class="frame-corners bottom-right"></div>

      <div class="frame-header">
        <div class="status-indicator"></div>
        <span class="technical-label">READING_ARTIFACT // EXTENDED_LEARNING // MODULE_ALPHA</span>
      </div>

      <div v-if="!compact && readingData.summary" class="reading-summary">
        <div class="summary-icon"><el-icon><Reading /></el-icon></div>
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
              <el-icon><User /></el-icon> {{ resource.authors.join(', ') }}
            </span>
            <span v-if="resource.difficulty" class="difficulty-tag" :class="resource.difficulty">
              {{ getDifficultyText(resource.difficulty) }}
            </span>
          </div>
          <div class="reading-reason" v-if="resource.recommend_reason && !compact">
            <div class="reason-label">RECOMMEND_REASON //</div>
            {{ resource.recommend_reason }}
          </div>
          <div class="reading-desc" v-if="resource.description && !compact">
            {{ resource.description }}
          </div>
        </article>
      </div>

      <div v-if="compact && resources.length > visibleResources.length" class="reading-more">
        <el-button type="primary" link class="more-btn-hud">
          ACCESS_ALL_MODULES ({{ resources.length }}) <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>

      <div class="frame-footer">
        <span class="mono-tag">KNOWLEDGE_SYNC_COMPLETE</span>
        <div class="footer-line"></div>
      </div>
    </div>
    
    <div v-else class="reading-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>NO_READING_CONTENT_DETECTED</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, ArrowRight, Reading } from '@element-plus/icons-vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const readingData = computed<Record<string, any> | null>(() => {
  if (!props.resultData) return null
  
  let data = props.resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  // 1. 直层级有 resources
  if (Array.isArray(data.resources)) {
    return data
  }
  
  // 2. content 为对象且内部有 resources
  if (typeof data.content === 'object' && data.content !== null) {
    if (Array.isArray(data.content.resources)) return data.content
    if (Array.isArray(data.content.recommendations)) return { ...data.content, resources: data.content.recommendations }
  }

  // 3. content 为字符串 but 包含 resources or recommendations
  const parsedContent = parseJsonObject(data.content)
  if (parsedContent) {
    if (Array.isArray(parsedContent.resources)) return parsedContent
    if (Array.isArray(parsedContent.recommendations)) return { ...parsedContent, resources: parsedContent.recommendations }
  }

  // 4. recommendations (兼容旧版拼写)
  if (Array.isArray(data.recommendations)) {
    return { ...data, resources: data.recommendations }
  }

  return null
})

const resources = computed<any[]>(() => {
  return readingData.value?.resources || []
})

const visibleResources = computed(() => {
  return props.compact ? resources.value.slice(0, 3) : resources.value
})

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
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.reading-resource {
  width: 100%;
  --primary: #6366F1;
  --bg: #F5F3FF;
  --fg: #1E1B4B;
  --border: #E0E7FF;
  --accent: #059669;
}

/* 技术框架样式 */
.technical-frame {
  position: relative;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 44px 32px 32px;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.05);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.frame-corners {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--primary);
  pointer-events: none;
}

.top-left { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.top-right { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bottom-left { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.bottom-right { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

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
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.technical-label {
  font-family: 'Share Tech Mono', monospace;
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
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  color: var(--primary);
  background: rgba(99, 102, 241, 0.1);
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
  background: white;
  border-radius: 8px;
  border: 1px solid var(--border);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.02);
}

.summary-icon {
  font-size: 1.5rem;
  color: var(--primary);
  opacity: 0.8;
}

.summary-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.95rem;
  color: var(--fg);
  line-height: 1.6;
}

.reading-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reading-item {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: white;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.reading-item:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.05);
  transform: translateX(4px);
}

.reading-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.reading-type {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  padding: 2px 8px;
  background: var(--primary);
  color: white;
  border-radius: 2px;
  letter-spacing: 1px;
}

.reading-title {
  font-family: 'Fira Code', monospace;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--fg);
  line-height: 1.4;
}

.reading-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  color: #64748B;
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
  border: 1px solid #CBD5E1;
  border-radius: 2px;
  color: #64748B;
}

.difficulty-tag.basic { color: var(--accent); border-color: var(--accent); }
.difficulty-tag.medium { color: #F59E0B; border-color: #F59E0B; }
.difficulty-tag.advanced { color: #DC2626; border-color: #DC2626; }

.reading-reason {
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  color: var(--fg);
  background: rgba(99, 102, 241, 0.03);
  padding: 16px;
  border-radius: 4px;
  margin-bottom: 16px;
  line-height: 1.6;
  border: 1px solid var(--border);
}

.reason-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  font-weight: bold;
  color: var(--primary);
  margin-bottom: 8px;
}

.reading-desc {
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.6;
}

.reading-more {
  display: flex;
  justify-content: center;
}

.more-btn-hud {
  font-family: 'Share Tech Mono', monospace;
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
  font-family: 'Share Tech Mono', monospace;
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  color: #94A3B8;
  letter-spacing: 1px;
}

/* 紧凑模式 */
.compact .technical-frame {
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
