<template>
  <article class="resource-card slide-up-anim" :class="toneClass">
    <header class="res-header">
      <div class="res-type">
        <span class="res-icon" aria-hidden="true">
          <el-icon><component :is="meta.icon" /></el-icon>
        </span>
        <div class="res-title-group">
          <span class="res-name">{{ meta.name }}</span>
          <span class="res-subtitle">{{ resourceTypeLabel }} · {{ resourceFormatLabel }}</span>
        </div>
      </div>
      <div class="status-tag">
        <span class="status-dot"></span>
        <span>已生成</span>
      </div>
    </header>

    <section class="res-insight-panel">
      <div class="res-step-badge" v-if="stepNumber">第 {{ stepNumber }} 阶段</div>
      <h3>{{ previewTitle }}</h3>
      <p>{{ resourceSummary }}</p>
    </section>

    <div class="res-body">
      <div class="resource-preview-shell">
        <MindmapView v-if="agentId === 'mindmap'" :result-data="resultData" compact />
        <KnowledgeGraphView v-else-if="agentId === 'knowledge_graph'" :result-data="resultData" compact />
        <QuizView v-else-if="agentId === 'quiz'" :result-data="resultData" compact />
        <CodeView v-else-if="agentId === 'code'" :result-data="resultData" compact />
        <ReadingView v-else-if="agentId === 'reading'" :result-data="resultData" compact />
        <MarkdownView v-else-if="isMarkdownAgent" :result-data="resultData" compact />
        <PptView v-else-if="agentId === 'ppt'" :result-data="resultData" compact />
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
              <span>图像资源待渲染</span>
            </div>
          </div>
        </div>
        <div v-else-if="agentId === 'video'" class="video-card-body">
          <div class="video-preview-placeholder">
            <div class="video-overlay">
              <el-icon class="play-icon"><VideoPlay /></el-icon>
            </div>
            <el-icon class="video-bg-icon"><VideoCamera /></el-icon>
            <div class="video-badge">视频脚本已就绪</div>
          </div>
        </div>
        <pre v-else class="fallback-json"><code>{{ JSON.stringify(resultData || {}, null, 2) }}</code></pre>
      </div>
    </div>

    <section class="res-usage-row">
      <div>
        <b>使用建议</b>
        <span>{{ usageHint }}</span>
      </div>
    </section>

    <footer class="res-footer">
      <button class="card-btn-primary" @click="handlePreview">查看详情</button>
      <button class="card-btn-secondary" @click="handleDownload">下载资源</button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Picture, VideoCamera, VideoPlay, Loading } from '@element-plus/icons-vue'
import { recordLearningEvent } from '@/api/ai'
import MindmapView from '@/components/resource/MindmapView.vue'
import MarkdownView from '@/components/resource/MarkdownView.vue'
import QuizView from '@/components/resource/QuizView.vue'
import KnowledgeGraphView from '@/components/resource/KnowledgeGraphView.vue'
import CodeView from '@/components/resource/CodeView.vue'
import ReadingView from '@/components/resource/ReadingView.vue'
import PptView from '@/components/resource/PptView.vue'
import {
  getFileCategory,
  getFileName,
  getFileUrl,
  getMarkdownContent,
  normalizeReadingArtifact,
} from '@/components/resource/resourceViewUtils'

const props = defineProps<{
  agentId: string
  meta: { name: string; icon: unknown }
  topic?: string
  gap?: string
  resultData?: any
}>()

const stepOrder = ['content', 'mindmap', 'knowledge_graph', 'code', 'quiz', 'reading']
const stepNumber = computed(() => {
  const idx = stepOrder.indexOf(props.agentId)
  return idx !== -1 ? idx + 1 : null
})

const emit = defineEmits(['preview'])

const fileUrl = computed(() => getFileUrl(props.resultData))
const fileCategory = computed(() => getFileCategory(fileUrl.value))
const isMarkdownAgent = computed(() => ['content', 'reading', 'code'].includes(props.agentId))

const imageUrl = computed(() => {
  if (props.agentId !== 'image' || !props.resultData) return ''
  return props.resultData.image_url || props.resultData.url || ''
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
  return normalizeReadingArtifact(props.resultData)?.resources?.length || 0
})

const resourceTypeLabel = computed(() => {
  const labelMap: Record<string, string> = {
    content: '专业讲解',
    mindmap: '知识导图',
    knowledge_graph: '知识图谱',
    code: '代码案例',
    quiz: '自测题',
    reading: '拓展阅读',
    ppt: '教学演示',
    image: '图像资源',
    video: '视频脚本',
  }
  return labelMap[props.agentId] || props.meta.name
})

const resourceFormatLabel = computed(() => {
  const formatMap: Record<string, string> = {
    content: 'Markdown',
    mindmap: 'Tree',
    knowledge_graph: 'Graph',
    code: 'Code',
    quiz: 'Quiz',
    reading: 'Reading List',
    ppt: 'PPTX',
    image: 'Image',
    video: 'Script',
  }
  return formatMap[props.agentId] || fileCategory.value || 'Resource'
})

const previewTitle = computed(() => {
  return props.resultData?.title || props.resultData?.name || props.meta.name || resourceTypeLabel.value
})

const resourceSummary = computed(() => {
  const summary = props.resultData?.summary || props.resultData?.description || props.resultData?.metadata?.summary
  if (summary) return String(summary)
  if (props.agentId === 'quiz') return `已生成 ${quizCount.value || '多'} 道自测题，用于检测当前知识掌握情况。`
  if (props.agentId === 'reading') return `已推荐 ${readingCount.value || '多'} 条拓展阅读资源，用于课后延伸学习。`
  if (props.agentId === 'code') return '已生成可实践的代码案例，适合结合讲解内容运行和修改。'
  if (props.agentId === 'mindmap') return '已生成结构化知识导图，用于快速梳理概念层级。'
  if (props.agentId === 'knowledge_graph') return '已生成知识图谱，用于探索知识点之间的前置、包含和扩展关系。'
  return '资源已生成，可点击查看详情进入完整内容。'
})

const usageHint = computed(() => {
  const hintMap: Record<string, string> = {
    content: '先阅读讲解，建立核心概念。',
    mindmap: '用于复习前快速回顾知识结构。',
    knowledge_graph: '用于理解抽象关系和知识依赖。',
    code: '建议边运行边修改，形成实践记忆。',
    quiz: '完成后对照解析，定位薄弱点。',
    reading: '完成基础学习后再阅读拓展内容。',
    ppt: '适合课堂汇报或复习讲解使用。',
    video: '可作为动画讲解或视频录制脚本。',
  }
  return hintMap[props.agentId] || '建议结合学习目标使用该资源。'
})

const toneClass = computed(() => {
  const toneMap: Record<string, string> = {
    content: 'tone-blue',
    mindmap: 'tone-purple',
    knowledge_graph: 'tone-amber',
    code: 'tone-rose',
    quiz: 'tone-emerald',
    reading: 'tone-indigo',
    ppt: 'tone-slate',
    image: 'tone-slate',
    video: 'tone-slate',
  }
  return toneMap[props.agentId] || 'tone-blue'
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
  height: 520px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #E2E8F0;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.055);
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}
.resource-card:hover {
  transform: translateY(-3px);
  border-color: #CBD5E1;
  box-shadow: 0 22px 46px rgba(15, 23, 42, 0.08);
}
.res-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid #EEF2F7;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
  flex-shrink: 0;
}
.res-type { display: flex; align-items: center; gap: 12px; min-width: 0; }
.res-icon {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.18rem;
  flex-shrink: 0;
}
.res-title-group { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.res-name { color: #0F172A; font-size: 1rem; font-weight: 900; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.res-subtitle { color: #64748B; font-size: 0.78rem; font-weight: 750; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  color: #047857;
  font-size: 0.75rem;
  font-weight: 850;
  flex-shrink: 0;
}
.status-dot { width: 7px; height: 7px; background: #10B981; border-radius: 999px; }
.res-insight-panel { padding: 16px 20px 0; }
.res-step-badge {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 9px;
  padding: 4px 9px;
  border-radius: 999px;
  background: #F1F5F9;
  color: #64748B;
  font-size: 0.74rem;
  font-weight: 850;
}
.res-insight-panel h3 { margin: 0; color: #0F172A; font-size: 1.08rem; line-height: 1.35; overflow-wrap: anywhere; }
.res-insight-panel p { margin: 8px 0 0; color: #64748B; line-height: 1.58; font-size: 0.92rem; overflow-wrap: anywhere; }
.res-body { flex: 1; min-height: 0; padding: 16px 20px; overflow: hidden; }
.resource-preview-shell {
  height: 100%;
  overflow-y: auto;
  border: 1px solid #E2E8F0;
  border-radius: 18px;
  background: #F8FAFC;
  padding: 14px;
}
.resource-preview-shell::-webkit-scrollbar { width: 5px; }
.resource-preview-shell::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 999px; }
.fallback-json {
  margin: 0;
  padding: 14px;
  background: #FFFFFF;
  color: #334155;
  border: 1px solid #E2E8F0;
  font-size: 0.78rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  overflow: auto;
  border-radius: 14px;
}
.ppt-card-body, .video-card-body { display: flex; flex-direction: column; gap: 14px; }
.ppt-info-row { display: flex; align-items: center; gap: 12px; }
.ppt-file-icon { font-size: 2rem; color: #475569; }
.ppt-file-name { font-size: 0.92rem; color: #0F172A; font-weight: 800; word-break: break-all; }
.ppt-meta { font-size: 0.82rem; color: #64748B; font-weight: 750; }
.ppt-title-item { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
.ppt-title-num { width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; background: #F1F5F9; color: #64748B; font-size: 0.72rem; font-weight: 900; }
.ppt-title-text { font-size: 0.86rem; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.image-preview-container, .video-preview-placeholder {
  border-radius: 16px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 190px;
  position: relative;
}
.res-image-preview { width: 100%; height: 100%; object-fit: cover; }
.image-placeholder.empty { display: flex; flex-direction: column; align-items: center; gap: 8px; color: #94A3B8; }
.video-badge { position: absolute; bottom: 12px; color: #64748B; font-size: 0.8rem; font-weight: 800; }
.res-usage-row { padding: 0 20px 14px; }
.res-usage-row > div {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.res-usage-row b { color: #334155; font-size: 0.8rem; }
.res-usage-row span { color: #64748B; line-height: 1.45; font-size: 0.86rem; }
.res-footer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 14px 20px 18px;
  border-top: 1px solid #EEF2F7;
  background: #FFFFFF;
  flex-shrink: 0;
}
.card-btn-primary, .card-btn-secondary {
  border-radius: 999px;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
  text-align: center;
  font-size: 0.88rem;
  font-weight: 850;
  padding: 10px 12px;
}
.card-btn-primary { background: #0F172A; color: #FFFFFF; border: 1px solid #0F172A; }
.card-btn-primary:hover { background: #1E293B; transform: translateY(-1px); }
.card-btn-secondary { background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; }
.card-btn-secondary:hover { background: #F8FAFC; color: #0F172A; border-color: #94A3B8; transform: translateY(-1px); }
.tone-blue .res-icon { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
.tone-purple .res-icon { background: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE; }
.tone-amber .res-icon { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
.tone-rose .res-icon { background: #FFF1F2; color: #BE123C; border: 1px solid #FFE4E6; }
.tone-emerald .res-icon { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
.tone-indigo .res-icon { background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE; }
.tone-slate .res-icon { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
@keyframes flyInBento {
  0% { opacity: 0; transform: translateY(16px); }
  100% { opacity: 1; transform: translateY(0); }
}
.slide-up-anim { animation: flyInBento 0.35s ease-out forwards; }
@media (max-width: 640px) {
  .resource-card { height: auto; min-height: 520px; }
  .res-header { flex-direction: column; }
  .res-footer { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .resource-card, .slide-up-anim, .card-btn-primary, .card-btn-secondary { animation: none; transition: none; }
}
</style>
