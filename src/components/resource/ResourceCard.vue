<template>
  <el-card shadow="never" class="resource-card slide-up-anim">
    <div class="res-header">
      <div class="res-type">
        <div class="res-step-badge" v-if="stepNumber">STEP {{ stepNumber }}</div>
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
      <DiagramResourceView
        v-else-if="agentId === 'diagram' || agentId === 'image'"
        :result-data="resultData"
        compact
      />
      <QuizResourceView
        v-else-if="agentId === 'quiz'"
        :result-data="resultData"
        compact
      />
      <CodeResourceView
        v-else-if="agentId === 'code'"
        :result-data="resultData"
        compact
      />
      <ReadingResourceView
        v-else-if="agentId === 'reading'"
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
            <span class="ppt-title-num">{{ Number(idx) + 1 }}</span>
            <span class="ppt-title-text">{{ title }}</span>
          </div>
          <div v-if="pptSlideTitles.length > 5" class="ppt-title-more">
            …还有 {{ pptSlideTitles.length - 5 }} 页
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
import DiagramResourceView from '@/components/resource/DiagramResourceView.vue'
import CodeResourceView from '@/components/resource/CodeResourceView.vue'
import ReadingResourceView from '@/components/resource/ReadingResourceView.vue'
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

const stepOrder = ['content', 'diagram', 'mindmap', 'code', 'quiz', 'reading']
const stepNumber = computed(() => {
  const idx = stepOrder.indexOf(props.agentId)
  return idx !== -1 ? idx + 1 : null
})

const emit = defineEmits(['preview'])

const fileUrl = computed(() => getFileUrl(props.resultData))
const fileCategory = computed(() => getFileCategory(fileUrl.value))
const fileName = computed(() => getFileName(fileUrl.value))
const isMarkdownAgent = computed(() => ['content', 'reading', 'code'].includes(props.agentId))

const imageUrl = computed(() => {
  if (props.agentId !== 'image' || !props.resultData) return ''
  return props.resultData.image_url || props.resultData.url || ''
})

const pptSlideCount = computed<number>(() => {
  if (props.agentId !== 'ppt' || !props.resultData) return 0
  const count = props.resultData.slide_count
  return typeof count === 'number' ? count : parseInt(String(count)) || 0
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
  border: 1px solid #E2E8F0;
  border-radius: 24px;
  background: #FFFFFF;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.4s, box-shadow 0.4s;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.resource-card:hover {
  transform: translateY(-8px);
  border-color: #3B82F6;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.res-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #F1F5F9;
}

.res-type {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  color: #0F172A;
  font-weight: 800;
  font-size: 1.15rem;
  letter-spacing: -0.025em;
}

.res-step-badge {
  background: #EFF6FF;
  color: #3B82F6;
  font-size: 0.7rem;
  font-weight: 900;
  padding: 4px 10px;
  border-radius: 8px;
  letter-spacing: 0.05em;
  border: 1px solid #DBEAFE;
}

.res-icon {
  display: inline-flex;
  flex: 0 0 auto;
  color: #3B82F6;
  font-size: 1.5rem;
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
  gap: 20px;
  padding: 24px;
  overflow: hidden;
  color: #475569;
}

.ai-badge {
  align-self: flex-start;
  max-width: 100%;
  padding: 6px 14px;
  border-radius: 10px;
  background: #F8FAFC;
  color: #64748B;
  font-size: 0.85rem;
  font-weight: 700;
  border: 1px solid #F1F5F9;
}

/* Bento 适配调整 */
.bento-main .res-body { min-height: 420px; }
.bento-side .res-body { min-height: 200px; }
.bento-small .res-body { min-height: 140px; }

.fallback-json {
  margin: 0;
  padding: 20px;
  border-radius: 16px;
  background: #F8FAFC;
  color: #64748B;
  border: 1px solid #E2E8F0;
  font-size: 0.85rem;
  font-family: 'JetBrains Mono', monospace;
  overflow: auto;
}

.ppt-card-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ppt-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ppt-file-icon {
  font-size: 2.2rem;
  color: #EE4444;
  flex-shrink: 0;
}

.ppt-file-name {
  font-size: 1rem;
  font-weight: 700;
  color: #0F172A;
  word-break: break-all;
}

.ppt-meta {
  font-size: 0.9rem;
  color: #64748B;
  font-weight: 600;
}

.ppt-titles {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ppt-title-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ppt-title-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: #F1F5F9;
  color: #64748B;
  font-size: 0.8rem;
  font-weight: 800;
  flex-shrink: 0;
}

.ppt-title-text {
  font-size: 0.9rem;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.image-preview-container {
  flex: 1;
  width: 100%;
  border-radius: 16px;
  background: #F8FAFC;
  border: 1px solid #F1F5F9;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.res-image-preview {
  width: 100%;
  height: 100%;
  cursor: pointer;
  transition: transform 0.5s ease;
}

.res-image-preview:hover {
  transform: scale(1.02);
}

.video-preview-placeholder {
  flex: 1;
  position: relative;
  width: 100%;
  border-radius: 16px;
  background: #0F172A;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.res-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: auto;
  padding: 24px;
  border-top: 1px solid #F1F5F9;
  background: #FAFAFA;
}

.res-action {
  flex: 1;
  min-height: 48px;
  margin-left: 0;
  border-radius: 14px;
  font-weight: 700;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s, box-shadow 0.2s;
}

.res-action:first-child {
  background: #3B82F6;
  border: none;
  color: white;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
}
.res-action:first-child:hover { background: #2563EB; box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3); }

.res-action:last-child {
  background: #FFFFFF;
  border: 2px solid #F1F5F9;
  color: #64748B;
}
.res-action:last-child:hover { border-color: #E2E8F0; color: #0F172A; background: #F8FAFC; }

@keyframes flyInBento {
  0% { opacity: 0; transform: translateY(40px); }
  100% { opacity: 1; transform: translateY(0); }
}

.slide-up-anim {
  animation: flyInBento 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
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

@keyframes flyInBento {
  0% { opacity: 0; transform: translateY(40px); }
  100% { opacity: 1; transform: translateY(0); }
}

.slide-up-anim {
  animation: flyInBento 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
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
