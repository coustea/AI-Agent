<template>
  <div class="reading-resource" :class="{ compact }">
    <div v-if="readingData" class="reading-list">
      <div v-if="!compact && readingData.summary" class="reading-summary">
        {{ readingData.summary }}
      </div>
      
      <article v-for="(resource, index) in visibleResources" :key="resource.id || index" class="reading-item">
        <div class="reading-header">
          <span class="reading-type">{{ getResourceTypeText(resource.type) }}</span>
          <span class="reading-title">{{ resource.title || '推荐资源' }}</span>
        </div>
        <div class="reading-meta" v-if="!compact">
          <span v-if="resource.authors && resource.authors.length">
            <el-icon><User /></el-icon> {{ resource.authors.join(', ') }}
          </span>
          <span v-if="resource.difficulty" class="difficulty-badge" :class="resource.difficulty">
            难度: {{ getDifficultyText(resource.difficulty) }}
          </span>
        </div>
        <div class="reading-reason" v-if="resource.recommend_reason && !compact">
          <div class="reason-label">推荐理由</div>
          {{ resource.recommend_reason }}
        </div>
        <div class="reading-desc" v-if="resource.description && !compact">
          {{ resource.description }}
        </div>
      </article>

      <div v-if="compact && resources.length > visibleResources.length" class="reading-more">
        <el-button type="primary" link size="small">
          查看全部 {{ resources.length }} 份推荐阅读 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
    <div v-else class="reading-empty">
      <el-empty description="暂未收到可展示的拓展阅读内容" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { User, ArrowRight } from '@element-plus/icons-vue'
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
    practice_project: '实践项目'
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
}

.reading-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.reading-summary {
  padding: 20px 24px;
  background: #F8FAFC;
  border-radius: 16px;
  color: #334155;
  font-size: 1rem;
  line-height: 1.8;
  border-left: 4px solid #3B82F6;
  margin-bottom: 12px;
}

.reading-item {
  padding: 20px;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  background: #FFFFFF;
  transition: border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.reading-item:hover {
  border-color: #3B82F6;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  transform: translateY(-2px);
}

.reading-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.reading-type {
  padding: 3px 10px;
  border-radius: 8px;
  background: #F0F7FF;
  color: #3B82F6;
  font-size: 0.75rem;
  font-weight: 800;
  white-space: nowrap;
  letter-spacing: 0.05em;
  border: 1px solid #DBEAFE;
}

.reading-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: #0F172A;
  line-height: 1.4;
  letter-spacing: -0.01em;
}

.reading-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 0.9rem;
  color: #64748B;
  margin-bottom: 16px;
}

.reading-meta span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.difficulty-badge {
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: #F1F5F9;
}

.difficulty-badge.basic { color: #10B981; background: #F0FDF4; }
.difficulty-badge.medium { color: #F59E0B; background: #FFFBEB; }
.difficulty-badge.advanced { color: #EF4444; background: #FEF2F2; }

.reading-reason {
  font-size: 0.95rem;
  color: #1E293B;
  background: #F8FAFC;
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 16px;
  line-height: 1.7;
  border: 1px solid #F1F5F9;
}

.reason-label {
  font-size: 0.75rem;
  font-weight: 900;
  color: #64748B;
  text-transform: uppercase;
  margin-bottom: 6px;
  letter-spacing: 0.05em;
}

.reading-desc {
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.7;
}

.reading-more {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}

.reading-empty {
  padding: 40px;
}

.compact .reading-item {
  padding: 14px;
}

.compact .reading-header {
  margin-bottom: 0;
}

.compact .reading-title {
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
