<template>
  <el-card shadow="never" class="resource-card slide-up-anim">
    <div class="res-header">
      <div class="res-type">
        <span class="res-icon" aria-hidden="true">
          <el-icon><component :is="meta.icon" /></el-icon>
        </span>
        <span class="res-name">{{ meta.name }}</span>
      </div>
      <el-tag size="small" type="success" effect="plain" round>
        <el-icon><Check /></el-icon>
        <span>已就绪</span>
      </el-tag>
    </div>

    <div class="res-body">
      <div class="ai-badge">{{ badgeText }}</div>

      <MindmapResourceView
        v-if="agentId === 'mindmap'"
        :result-data="resultData"
        compact
      />
      <QuizResourceView
        v-else-if="agentId === 'quiz'"
        :result-data="resultData"
        compact
      />
      <MarkdownResourceView
        v-else-if="isMarkdownAgent"
        :result-data="resultData"
        compact
      />
      <pre v-else class="fallback-json"><code>{{ JSON.stringify(resultData || {}, null, 2) }}</code></pre>
    </div>

    <div class="res-footer">
      <el-button
        class="res-action"
        type="primary"
        plain
        @click="handlePreview"
      >
        <el-icon><View /></el-icon>
        在线预览
      </el-button>
      <el-button class="res-action" @click="handleDownload">
        <el-icon><Download /></el-icon>
        下载
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Download, View } from '@element-plus/icons-vue'
import { recordLearningEvent } from '@/api/ai'
import MindmapResourceView from '@/components/resource/MindmapResourceView.vue'
import MarkdownResourceView from '@/components/resource/MarkdownResourceView.vue'
import QuizResourceView from '@/components/resource/QuizResourceView.vue'
import {
  getFileCategory,
  getFileName,
  getFileUrl,
  getMarkdownContent,
} from '@/components/resource/resourceViewUtils'

const props = defineProps<{
  agentId: string
  meta: { name: string; icon: unknown }
  topic?: string
  gap?: string
  resultData?: any
}>()

const emit = defineEmits(['preview'])

const fileUrl = computed(() => getFileUrl(props.resultData))
const fileCategory = computed(() => getFileCategory(fileUrl.value))
const fileName = computed(() => getFileName(fileUrl.value))
const isMarkdownAgent = computed(() => ['content', 'reading', 'code'].includes(props.agentId))

const quizCount = computed(() => {
  return Array.isArray(props.resultData?.questions) ? props.resultData.questions.length : 0
})

const readingCount = computed(() => {
  return Array.isArray(props.resultData?.recommendations) ? props.resultData.recommendations.length : 0
})

const badgeText = computed(() => {
  if (props.agentId === 'mindmap') {
    return fileCategory.value === 'html' ? '动态 HTML 导图已就绪' : '知识拓扑提取完成'
  }
  if (props.agentId === 'quiz') {
    return `已生成 ${quizCount.value || '专属'} 道练习`
  }
  if (props.agentId === 'reading') {
    return `已匹配 ${readingCount.value || '多条'} 条拓展阅读`
  }
  if (props.agentId === 'code' && props.resultData?.detected_language) {
    return `实操代码 · ${props.resultData.detected_language}`
  }
  if (fileCategory.value === 'markdown') return `${fileName.value} · Markdown`
  return '学习资源已生成'
})

const handlePreview = () => {
  recordLearningEvent({
    event_type: 'resource_viewed',
    course: props.topic,
    topic: props.meta.name,
    metadata: { agent: props.agentId },
  }).catch((err) => {
    console.warn('[ResourceCard] record learning event failed:', err)
  })
  emit('preview', {
    agentId: props.agentId,
    title: props.meta.name,
    hasFile: !!fileUrl.value,
    fileUrl: fileUrl.value,
    fileCategory: fileCategory.value,
    resultData: props.resultData,
  })
}

const handleDownload = () => {
  const filename = `${props.meta.name}_${props.agentId}${props.agentId === 'quiz' ? '.json' : '.md'}`

  if (fileUrl.value) {
    const link = document.createElement('a')
    link.href = fileUrl.value
    link.download = getFileName(fileUrl.value) || filename
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    return
  }

  const isQuiz = props.agentId === 'quiz'
  const content = isQuiz
    ? JSON.stringify(props.resultData || {}, null, 2)
    : getMarkdownContent(props.resultData)
  const ext = isQuiz ? '.json' : '.md'
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${props.meta.name}_${props.agentId}${ext}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.resource-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}

.resource-card:hover {
  transform: translateY(-2px);
  border-color: #cbd5e1;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.06);
}

.res-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #eef2f7;
}

.res-type {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: #0f172a;
  font-weight: 700;
}

.res-icon {
  display: inline-flex;
  flex: 0 0 auto;
  color: #475569;
}

.res-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.res-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  min-height: 230px;
  padding: 16px;
  overflow: hidden;
}

.ai-badge {
  align-self: flex-start;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #334155;
  font-size: 0.75rem;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fallback-json {
  margin: 0;
  padding: 12px;
  border-radius: 8px;
  background: #1e293b;
  color: #e2e8f0;
  overflow: auto;
}

.res-footer {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
  padding: 12px 16px;
  border-top: 1px solid #eef2f7;
}

.res-action {
  flex: 1;
  min-height: 40px;
  margin-left: 0;
  border-radius: 6px;
}

.res-action:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.22);
  outline-offset: 2px;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.slide-up-anim {
  animation: slideUp 0.45s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
}

@media (prefers-reduced-motion: reduce) {
  .resource-card,
  .slide-up-anim {
    animation: none;
    transition: none;
  }

  .resource-card:hover {
    transform: none;
  }
}
</style>
