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
      <div v-else-if="agentId === 'ppt'" class="ppt-card-body">
        <div class="ppt-info-row">
          <el-icon class="ppt-file-icon"><DataBoard /></el-icon>
          <span class="ppt-file-name">{{ pptFileName }}</span>
        </div>
        <div class="ppt-meta" v-if="pptSlideCount > 0">
          共 {{ pptSlideCount }} 页幻灯片
        </div>
        <div class="ppt-titles" v-if="pptSlideTitles.length > 0">
          <div v-for="(title, idx) in pptSlideTitles.slice(0, 5)" :key="idx" class="ppt-title-item">
            <span class="ppt-title-num">{{ idx + 1 }}</span>
            <span class="ppt-title-text">{{ title }}</span>
          </div>
          <div v-if="pptSlideTitles.length > 5" class="ppt-title-more">
            ...还有 {{ pptSlideTitles.length - 5 }} 页
          </div>
        </div>
      </div>
      <div v-else-if="agentId === 'image'" class="image-card-body">
        <div class="image-preview-container">
          <el-image 
            v-if="imageUrl" 
            :src="imageUrl" 
            fit="cover" 
            class="res-image-preview"
            :preview-src-list="[imageUrl]"
            preview-teleported
          >
            <template #placeholder>
              <div class="image-placeholder"><el-icon class="is-loading"><Loading /></el-icon></div>
            </template>
          </el-image>
          <div v-else class="image-placeholder empty">
            <el-icon><Picture /></el-icon>
            <span>图片渲染中</span>
          </div>
        </div>
      </div>
      <div v-else-if="agentId === 'video'" class="video-card-body">
        <div class="video-preview-placeholder">
          <div class="video-overlay">
            <el-icon class="play-icon"><VideoPlay /></el-icon>
          </div>
          <el-icon class="video-bg-icon"><VideoCamera /></el-icon>
          <div class="video-badge">视频脚本与素材已就绪</div>
        </div>
      </div>
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
import { Check, Download, View, DataBoard, Picture, VideoCamera, VideoPlay, Loading } from '@element-plus/icons-vue'
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

const imageUrl = computed(() => {
  if (props.agentId !== 'image' || !props.resultData) return ''
  return props.resultData.image_url || props.resultData.url || ''
})

const pptSlideCount = computed(() => {
  if (props.agentId !== 'ppt' || !props.resultData) return 0
  return props.resultData.slide_count || 0
})

const pptSlideTitles = computed(() => {
  if (props.agentId !== 'ppt' || !props.resultData) return []
  return Array.isArray(props.resultData.slide_titles) ? props.resultData.slide_titles : []
})

const pptFileName = computed(() => {
  if (fileUrl.value) return getFileName(fileUrl.value)
  return props.resultData?.file_path
    ? (props.resultData.file_path.split(/[\\/]/).pop() || 'presentation.pptx')
    : 'presentation.pptx'
})

const quizCount = computed(() => {
  return Array.isArray(props.resultData?.questions) ? props.resultData.questions.length : 0
})

const readingCount = computed(() => {
  return Array.isArray(props.resultData?.recommendations) ? props.resultData.recommendations.length : 0
})

const badgeText = computed(() => {
  if (props.agentId === 'ppt') {
    return pptSlideCount.value > 0 ? `已生成 ${pptSlideCount.value} 页演示文稿` : '演示文稿已生成'
  }
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
  if (props.agentId === 'ppt' && fileUrl.value) {
    const link = document.createElement('a')
    link.href = fileUrl.value
    link.download = pptFileName.value
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    return
  }

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

.ppt-card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ppt-info-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ppt-file-icon {
  font-size: 2rem;
  color: #6366f1;
  flex-shrink: 0;
}

.ppt-file-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
  word-break: break-all;
}

.ppt-meta {
  font-size: 0.85rem;
  color: #64748b;
  font-weight: 600;
}

.ppt-titles {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ppt-title-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ppt-title-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #eef2ff;
  color: #6366f1;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.ppt-title-text {
  font-size: 0.85rem;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ppt-title-more {
  font-size: 0.8rem;
  color: #94a3b8;
  padding-left: 30px;
}

.image-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.image-preview-container {
  flex: 1;
  width: 100%;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.res-image-preview {
  width: 100%;
  height: 100%;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.res-image-preview:hover {
  transform: scale(1.02);
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 0.85rem;
}

.image-placeholder .el-icon {
  font-size: 1.5rem;
}

.video-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-preview-placeholder {
  flex: 1;
  position: relative;
  width: 100%;
  border-radius: 8px;
  background: #0f172a;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.video-bg-icon {
  font-size: 3.5rem;
  color: #334155;
  opacity: 0.4;
}

.video-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.play-icon {
  font-size: 3rem;
  color: #ffffff;
  opacity: 0.8;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.video-preview-placeholder:hover .play-icon {
  transform: scale(1.15);
  opacity: 1;
}

.video-badge {
  position: absolute;
  bottom: 12px;
  left: 12px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  backdrop-filter: blur(4px);
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
