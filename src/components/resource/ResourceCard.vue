<template>
  <div class="technical-frame resource-card slide-up-anim">
    <div class="frame-corners top-left"></div>
    <div class="frame-corners top-right"></div>
    <div class="frame-corners bottom-left"></div>
    <div class="frame-corners bottom-right"></div>

    <div class="res-header">
      <div class="res-type">
        <div class="res-step-badge" v-if="stepNumber">STAGE_{{ stepNumber.toString().padStart(2, '0') }}</div>
        <span class="res-icon" aria-hidden="true">
          <el-icon><component :is="meta.icon" /></el-icon>
        </span>
        <span class="res-name">{{ meta.name.toUpperCase() }}</span>
      </div>
      <div class="status-tag">
        <div class="status-dot"></div>
        <span>LIVE_SYNC</span>
      </div>
    </div>

    <div class="res-body">
      <div class="ai-badge-hud">{{ badgeText.toUpperCase() }}</div>

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
          SYSTEM_SLIDES: {{ pptSlideCount }} TOTAL
        </div>
        <div class="ppt-titles" v-if="pptSlideTitles.length > 0">
          <div v-for="(title, idx) in pptSlideTitles.slice(0, 5)" :key="idx" class="ppt-title-item">
            <span class="ppt-title-num">{{ (Number(idx) + 1).toString().padStart(2, '0') }}</span>
            <span class="ppt-title-text">{{ title }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="agentId === 'image'" class="image-card-body">
        <div class="image-preview-container-hud">
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
            <span>RENDER_PENDING</span>
          </div>
        </div>
      </div>
      <div v-else-if="agentId === 'video'" class="video-card-body">
        <div class="video-preview-placeholder-hud">
          <div class="video-overlay">
            <el-icon class="play-icon"><VideoPlay /></el-icon>
          </div>
          <el-icon class="video-bg-icon"><VideoCamera /></el-icon>
          <div class="video-badge-hud">SEQUENCE_SYNC_READY</div>
        </div>
      </div>
      <pre v-else class="fallback-json-hud"><code>{{ JSON.stringify(resultData || {}, null, 2) }}</code></pre>
    </div>

    <div class="res-footer">
      <button class="hud-btn-primary" @click="handlePreview">
        EXECUTE_PREVIEW
      </button>
      <button class="hud-btn-secondary" @click="handleDownload">
        DOWNLOAD_DATA
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Download, View, DataBoard, Picture, VideoCamera, VideoPlay, Loading } from '@element-plus/icons-vue'
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
    return pptSlideCount.value > 0 ? `SLIDES_${pptSlideCount.value}_SYNC` : 'SLIDES_SYNC'
  }
  if (props.agentId === 'mindmap') {
    return fileCategory.value === 'html' ? 'TOPOLOGY_HTML_READY' : 'TOPOLOGY_COMPLETE'
  }
  if (props.agentId === 'quiz') {
    return `QUIZ_BLOCKS_${quizCount.value || 'AUTO'}`
  }
  if (props.agentId === 'reading') {
    return `KNOWLEDGE_NODES_${readingCount.value || 'MULTI'}`
  }
  if (props.agentId === 'code' && props.resultData?.detected_language) {
    return `RUNTIME_${props.resultData.detected_language.toUpperCase()}`
  }
  if (fileCategory.value === 'markdown') return `MD_${fileName.value.toUpperCase()}`
  return 'RESOURCE_SYNC_OK'
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
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.resource-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #FFFFFF;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
  --primary: #6366F1;
  --accent: #059669;
  --border: #E0E7FF;
}

/* 技术框架扩展 */
.technical-frame {
  position: relative;
  border: 1px solid var(--border);
  border-radius: 4px;
}

.frame-corners {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--primary);
  pointer-events: none;
  z-index: 10;
}

.top-left { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.top-right { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bottom-left { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.bottom-right { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

.resource-card:hover {
  transform: translateY(-8px);
  border-color: var(--primary);
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.1);
}

.res-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px dashed var(--border);
}

.res-type {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.res-step-badge {
  font-family: 'Share Tech Mono', monospace;
  background: rgba(99, 102, 241, 0.1);
  color: var(--primary);
  font-size: 0.65rem;
  padding: 2px 8px;
  border-radius: 2px;
  letter-spacing: 1px;
}

.res-icon {
  display: inline-flex;
  color: var(--primary);
  font-size: 1.25rem;
  opacity: 0.8;
}

.res-name {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.9rem;
  color: #1E1B4B;
  letter-spacing: 1px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.6rem;
  color: var(--accent);
}

.status-dot {
  width: 5px;
  height: 5px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--accent);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}

.res-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  overflow: hidden;
}

.ai-badge-hud {
  align-self: flex-start;
  padding: 4px 10px;
  border-radius: 2px;
  background: rgba(99, 102, 241, 0.03);
  color: #64748B;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 1px;
  border: 1px solid rgba(99, 102, 241, 0.05);
}

.fallback-json-hud {
  margin: 0;
  padding: 16px;
  background: #0F172A;
  color: #E2E8F0;
  border: 1px solid #334155;
  font-size: 0.75rem;
  font-family: 'Fira Code', monospace;
  overflow: auto;
  border-radius: 4px;
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
  font-size: 2rem;
  color: #EE4444;
  opacity: 0.8;
}

.ppt-file-name {
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  color: #1E1B4B;
  word-break: break-all;
}

.ppt-meta {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  color: #64748B;
}

.ppt-title-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.ppt-title-num {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: var(--primary);
  background: rgba(99, 102, 241, 0.05);
  padding: 1px 4px;
}

.ppt-title-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.8rem;
  color: #475569;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-preview-container-hud {
  flex: 1;
  border-radius: 4px;
  background: #F8FAFC;
  border: 1px solid var(--border);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
  background-image: linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px);
  background-size: 20px 20px;
}

.res-image-preview {
  width: 100%;
  height: 100%;
  cursor: pointer;
  transition: transform 0.5s ease;
}

.video-preview-placeholder-hud {
  flex: 1;
  position: relative;
  border-radius: 4px;
  background: #0F172A;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.video-badge-hud {
  position: absolute;
  bottom: 12px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  color: rgba(255,255,255,0.6);
  letter-spacing: 1px;
}

.res-footer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px 24px 24px;
  background: rgba(255, 255, 255, 0.5);
}

.hud-btn-primary, .hud-btn-secondary {
  width: 100%;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  padding: 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.hud-btn-primary {
  background: var(--primary);
  color: white;
  border: none;
}
.hud-btn-primary:hover {
  background: #4F46E5;
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
}

.hud-btn-secondary {
  background: transparent;
  border: 1px solid var(--border);
  color: #64748B;
}
.hud-btn-secondary:hover {
  border-color: var(--primary);
  color: var(--primary);
}

@keyframes flyInBento {
  0% { opacity: 0; transform: translateY(40px); }
  100% { opacity: 1; transform: translateY(0); }
}

.slide-up-anim {
  animation: flyInBento 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
}

@media (prefers-reduced-motion: reduce) {
  .resource-card, .slide-up-anim {
    animation: none;
    transition: none;
  }
}
</style>
