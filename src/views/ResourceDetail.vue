<template>
  <div class="resource-detail-page">
    <div class="page-header">
      <el-button link @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回个人中心
      </el-button>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="error" class="error-container">
      <el-empty description="加载失败">
        <el-button type="primary" @click="loadResource">重试</el-button>
      </el-empty>
    </div>

    <template v-else-if="resource">
      <header class="detail-hero-premium">
        <div class="hero-bg-pattern"></div>
        <div class="hero-content">
          <div class="hero-status-tag" :class="getStatusTypeClass(resource.status)">
            <el-icon><CircleCheckFilled v-if="resource.status === 'completed'" /><Loading v-else-if="resource.status === 'processing'" /><WarningFilled v-else /></el-icon>
            <span>{{ getStatusText(resource.status).toUpperCase() }}</span>
          </div>
          <h1 class="hero-title gradient-text">{{ resource.title || resource.learning_need || '学习资源包' }}</h1>
          
          <div class="hero-context-pills">
            <div class="context-pill glass-pill">
              <span class="pill-label">创建时间</span>
              <span class="pill-value"><el-icon><Clock /></el-icon> {{ formatTime(resource.created_at) }}</span>
            </div>
            <div class="context-pill context-pill-wide glass-pill">
              <span class="pill-label">学习需求</span>
              <span class="pill-value">{{ resource.learning_need || '暂无描述' }}</span>
            </div>
          </div>
        </div>
      </header>

      <main class="detail-body-bento">
        <div class="resource-section">
          <div class="section-header">
            <h3>生成资源 ({{ resource.resources?.length || 0 }})</h3>
          </div>
          
          <div v-if="!resource.resources?.length" class="empty-resources">
            <el-empty description="暂无生成资源" />
          </div>
          <div v-else class="premium-resource-grid">
            <article
              v-for="(item, index) in resource.resources"
              :key="item.id"
              class="premium-res-card"
              :class="[getAgentMeta(item.type).color, { 'is-clickable': hasPreviewContent(item) }]"
              :style="{ animationDelay: `${index * 0.08}s` }"
              @click="openResourcePreview(item)"
              @keydown.enter.prevent="openResourcePreview(item)"
              @keydown.space.prevent="openResourcePreview(item)"
              :role="hasPreviewContent(item) ? 'button' : undefined"
              :tabindex="hasPreviewContent(item) ? 0 : undefined"
            >
              <div class="card-bg-glow"></div>
              <div class="card-header">
                <div class="type-icon-box">
                  <el-icon><component :is="getAgentMeta(item.type).icon" /></el-icon>
                </div>
                <div class="type-info">
                  <span class="type-label">{{ getAgentTypeName(item.type) }}</span>
                  <el-tag :type="getStatusType(item.status)" size="small" effect="light" class="status-badge">
                    {{ getStatusText(item.status) }}
                  </el-tag>
                </div>
              </div>

              <div class="card-body">
                <h4 class="card-title">{{ item.title || `${getAgentTypeName(item.type)}资源` }}</h4>
                <p v-if="item.summary" class="card-summary">{{ item.summary }}</p>
                
                <div v-if="item.error_message" class="item-error">
                  <el-icon><WarningFilled /></el-icon>
                  {{ item.error_message }}
                </div>
              </div>

              <div class="card-footer">
                <button class="modern-text-btn" :class="{ disabled: !hasPreviewContent(item) }">
                  {{ hasPreviewContent(item) ? '查看详情' : '暂无可预览内容' }} <span>&rarr;</span>
                </button>
              </div>
            </article>
          </div>
        </div>
      </main>
    </template>

    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="78%"
      top="6vh"
      destroy-on-close
      class="resource-preview-dialog"
    >
      <div v-if="previewItem" class="preview-dialog-body">
        <MindmapView v-if="previewItem.type === 'mindmap'" :result-data="previewItem" />
        <QuizView v-else-if="previewItem.type === 'quiz'" :result-data="previewItem" />
        <KnowledgeGraphView v-else-if="previewItem.type === 'knowledge_graph'" :result-data="previewItem" />
        <CodeView v-else-if="previewItem.type === 'code'" :result-data="previewItem" />
        <ReadingView v-else-if="previewItem.type === 'reading'" :result-data="previewItem" />
        <MarkdownView v-else :result-data="previewItem" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock, Document, WarningFilled, CircleCheckFilled, Loading, Cpu, Edit, Collection, VideoPlay, Share } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getGeneratedResourceDetail } from '@/api/ai'
import type { GeneratedResourceBundle, ResourceItemDetail } from '@/api/ai'
import MindmapView from '@/components/resource/MindmapView.vue'
import MarkdownView from '@/components/resource/MarkdownView.vue'
import QuizView from '@/components/resource/QuizView.vue'
import KnowledgeGraphView from '@/components/resource/KnowledgeGraphView.vue'
import CodeView from '@/components/resource/CodeView.vue'
import ReadingView from '@/components/resource/ReadingView.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const resource = ref<GeneratedResourceBundle | null>(null)
const previewVisible = ref(false)
const previewItem = ref<ResourceItemDetail | null>(null)

const previewTitle = computed(() => {
  if (!previewItem.value) return '资源预览'
  return previewItem.value.title || `${getAgentTypeName(previewItem.value.type)}资源`
})

const loadResource = async () => {
  const resourceId = Number(route.params.id)
  if (!resourceId) {
    error.value = true
    return
  }

  loading.value = true
  error.value = false

  try {
    const res = await getGeneratedResourceDetail(resourceId)
    resource.value = res.data.data
  } catch (e) {
    console.error('Failed to load resource detail', e)
    error.value = true
    ElMessage.error('加载资源详情失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push({ name: 'Profile' })
}

const getStatusType = (status: string) => {
  if (status === 'completed') return 'success'
  if (status === 'pending' || status === 'processing') return 'primary'
  if (status === 'failed') return 'danger'
  return 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    completed: '已完成',
    pending: '生成中',
    processing: '生成中',
    failed: '失败',
  }
  return map[status] || status
}

const getStatusTypeClass = (status: string) => {
  if (status === 'completed') return 'success-glow'
  if (status === 'pending' || status === 'processing') return 'processing-glow'
  if (status === 'failed') return 'danger-glow'
  return 'info-glow'
}

const getAgentMeta = (type: string) => {
  const map: Record<string, { icon: any, color: string }> = {
    content: { icon: Document, color: 'tone-blue' },
    mindmap: { icon: Share, color: 'tone-purple' },
    knowledge_graph: { icon: Share, color: 'tone-amber' },
    quiz: { icon: Edit, color: 'tone-emerald' },
    code: { icon: Cpu, color: 'tone-rose' },
    reading: { icon: Collection, color: 'tone-indigo' },
    video: { icon: VideoPlay, color: 'tone-slate' }
  }
  return map[type] || { icon: Document, color: 'tone-slate' }
}

const getAgentTypeName = (type: string) => {
  const map: Record<string, string> = {
    content: '学习内容',
    mindmap: '思维导图',
    quiz: '测验题',
    code: '代码示例',
    reading: '阅读材料',
    knowledge_graph: '知识图谱',
    video: '视频',
    ppt: 'PPT',
  }
  return map[type] || type
}

const hasPreviewContent = (item: ResourceItemDetail) => {
  if (item.content != null && String(item.content).trim()) return true
  if (item.summary_data && Object.keys(item.summary_data).length) return true
  if (item.metadata && Object.keys(item.metadata).length) return true
  return false
}

const openResourcePreview = (item: ResourceItemDetail) => {
  if (!hasPreviewContent(item)) return
  previewItem.value = item
  previewVisible.value = true
}

const formatTime = (time: string | null) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60))
      return minutes <= 1 ? '刚刚' : `${minutes}分钟前`
    }
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else if (days === 1) {
    return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else if (days < 7) {
    return `${days}天前`
  }
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

onMounted(() => {
  loadResource()
})
</script>

<style scoped>
.resource-detail-page {
  background: var(--color-bg);
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}
.resource-detail-page::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 500px;
  background: linear-gradient(180deg, rgba(224, 231, 255, 0.6) 0%, rgba(244, 247, 251, 0) 100%);
  pointer-events: none;
  z-index: 0;
}

.page-header {
  position: relative;
  padding: var(--space-6) 60px 0;
  z-index: 2;
}
.back-btn {
  font-weight: var(--weight-bold);
  font-size: 1rem;
  color: var(--color-text-secondary);
}
.back-btn:hover { color: var(--color-info); }

.loading-container,
.error-container {
  background: var(--color-surface);
  border-radius: 24px;
  padding: 60px;
  margin: var(--space-10) 60px;
  position: relative;
  z-index: 1;
  box-shadow: var(--shadow-md);
}

.detail-hero-premium {
  position: relative;
  margin: var(--space-6) 60px var(--space-10);
  padding: var(--space-12) 54px;
  background: var(--color-surface);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 32px;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  z-index: 1;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}
.hero-bg-pattern {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  background-image: radial-gradient(rgba(15, 23, 42, 0.03) 1px, transparent 1px);
  background-size: var(--space-6) var(--space-6);
  pointer-events: none;
}
.hero-content {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  z-index: 1;
}

.hero-status-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  font-weight: var(--weight-extrabold);
  width: max-content;
}
.hero-status-tag.success-glow {
  background: rgba(16, 185, 129, 0.1); color: var(--tone-emerald); border: 1px solid rgba(16, 185, 129, 0.2);
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.15); animation: pulse-success 2s infinite alternate;
}
.hero-status-tag.processing-glow {
  background: rgba(59, 130, 246, 0.1); color: var(--color-info); border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.15); animation: pulse-primary 2s infinite alternate;
}
.hero-status-tag.danger-glow {
  background: rgba(225, 29, 72, 0.1); color: #E11D48; border: 1px solid rgba(225, 29, 72, 0.2);
}
.hero-status-tag.info-glow {
  background: rgba(100, 116, 139, 0.1); color: var(--color-text-secondary); border: 1px solid rgba(100, 116, 139, 0.2);
}

@keyframes pulse-success { 0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.1); } 100% { box-shadow: 0 0 25px rgba(16, 185, 129, 0.3); } }
@keyframes pulse-primary { 0% { box-shadow: 0 0 10px rgba(59, 130, 246, 0.1); } 100% { box-shadow: 0 0 25px rgba(59, 130, 246, 0.3); } }

.hero-title.gradient-text {
  margin: 0;
  font-size: 2.2rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, var(--color-text) 0%, #334155 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.3;
}

.hero-context-pills { display: flex; gap: var(--space-4); flex-wrap: wrap; margin-top: var(--space-2); }
.glass-pill {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-lg);
  padding: 10px 18px;
  font-size: 0.95rem;
  box-shadow: var(--shadow-sm);
}
.pill-label { color: var(--color-text-muted); font-weight: var(--weight-extrabold); margin-right: var(--space-3); text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.8rem; }
.pill-value { color: var(--color-text); font-weight: var(--weight-semibold); display: flex; align-items: center; gap: var(--space-2); }

.detail-body-bento {
  padding: 0 60px 60px;
  position: relative;
  z-index: 1;
}

.section-header { margin-bottom: var(--space-6); }
.section-header h3 { margin: 0; font-size: 1.4rem; font-weight: var(--weight-extrabold); color: var(--color-text); letter-spacing: -0.01em; }

.premium-resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 28px;
  align-items: stretch;
}

.premium-res-card {
  background: var(--color-surface);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 24px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: var(--shadow-md);
  animation: fadeSlideUp 0.6s ease-out backwards;
  outline: none;
}
@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }

.premium-res-card.is-clickable { cursor: pointer; }
.premium-res-card.is-clickable:hover,
.premium-res-card.is-clickable:focus-visible {
  transform: translateY(-8px);
  box-shadow: var(--shadow-xl);
  border-color: transparent;
}

.card-bg-glow {
  position: absolute; top: 0; left: 0; right: 0; height: 100%;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 100%);
  opacity: 0; transition: opacity 0.4s ease; z-index: 0; pointer-events: none;
}
.premium-res-card.tone-blue:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-purple:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-amber:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(245, 158, 11, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-rose:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(225, 29, 72, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-emerald:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-indigo:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-slate:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(100, 116, 139, 0.08) 0%, transparent 70%); opacity: 1; }

.premium-res-card.is-clickable.tone-blue:hover, .premium-res-card.is-clickable.tone-blue:focus-visible { border-color: rgba(59, 130, 246, 0.3); }
.premium-res-card.is-clickable.tone-purple:hover, .premium-res-card.is-clickable.tone-purple:focus-visible { border-color: rgba(139, 92, 246, 0.3); }
.premium-res-card.is-clickable.tone-amber:hover, .premium-res-card.is-clickable.tone-amber:focus-visible { border-color: rgba(245, 158, 11, 0.3); }
.premium-res-card.is-clickable.tone-rose:hover, .premium-res-card.is-clickable.tone-rose:focus-visible { border-color: rgba(225, 29, 72, 0.3); }
.premium-res-card.is-clickable.tone-emerald:hover, .premium-res-card.is-clickable.tone-emerald:focus-visible { border-color: rgba(16, 185, 129, 0.3); }
.premium-res-card.is-clickable.tone-indigo:hover, .premium-res-card.is-clickable.tone-indigo:focus-visible { border-color: rgba(99, 102, 241, 0.3); }
.premium-res-card.is-clickable.tone-slate:hover, .premium-res-card.is-clickable.tone-slate:focus-visible { border-color: rgba(100, 116, 139, 0.3); }

.card-header, .card-body, .card-footer { position: relative; z-index: 1; }

.card-header { display: flex; align-items: center; gap: var(--space-3); }
.type-icon-box {
  width: var(--space-12); height: var(--space-12); border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04);
}
.premium-res-card.tone-blue .type-icon-box { color: var(--color-info); }
.premium-res-card.tone-purple .type-icon-box { color: #7C3AED; }
.premium-res-card.tone-amber .type-icon-box { color: var(--tone-amber); }
.premium-res-card.tone-rose .type-icon-box { color: #E11D48; }
.premium-res-card.tone-emerald .type-icon-box { color: var(--tone-emerald); }
.premium-res-card.tone-indigo .type-icon-box { color: var(--tone-indigo); }
.premium-res-card.tone-slate .type-icon-box { color: var(--color-text-secondary); }

.type-info { display: flex; flex-direction: column; gap: var(--space-1); }
.type-label { font-size: 0.95rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.status-badge { font-weight: var(--weight-bold); border: none; }

.card-body { display: flex; flex-direction: column; gap: var(--space-3); flex: 1; }
.card-title { margin: 0; font-size: 1.15rem; font-weight: var(--weight-extrabold); color: var(--color-text); line-height: 1.45; }
.card-summary { margin: 0; font-size: 0.95rem; color: var(--color-text-secondary); line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.item-error {
  display: flex; align-items: center; gap: var(--space-2);
  background: var(--color-danger-soft); color: #E11D48; padding: 10px 14px; border-radius: 10px; font-size: 0.85rem; font-weight: var(--weight-semibold);
  margin-top: auto;
}

.card-footer {
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  padding-top: var(--space-5); margin-top: var(--space-1); display: flex; justify-content: space-between; align-items: center;
}
.modern-text-btn {
  background: transparent; border: none; color: var(--color-text); font-weight: var(--weight-extrabold); font-size: 0.95rem; padding: 0;
  display: flex; align-items: center; gap: var(--space-2); transition: color var(--transition-base); cursor: pointer;
}
.modern-text-btn.disabled { color: var(--color-text-faint); cursor: not-allowed; }
.modern-text-btn span { transition: transform var(--transition-slow); }
.premium-res-card.is-clickable:hover .modern-text-btn:not(.disabled),
.premium-res-card.is-clickable:focus-visible .modern-text-btn:not(.disabled) { color: var(--color-info); }
.premium-res-card.is-clickable:hover .modern-text-btn:not(.disabled) span,
.premium-res-card.is-clickable:focus-visible .modern-text-btn:not(.disabled) span { transform: translateX(var(--space-1)); }

.resource-preview-dialog :deep(.el-dialog) { border-radius: 24px; overflow: hidden; box-shadow: var(--shadow-xl); }
.resource-preview-dialog :deep(.el-dialog__header) { padding: var(--space-6) var(--space-8) var(--space-5); margin-right: 0; border-bottom: 1px solid var(--color-surface-hover); }
.resource-preview-dialog :deep(.el-dialog__title) { font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.resource-preview-dialog :deep(.el-dialog__body) { background: var(--color-bg); padding: var(--space-6) var(--space-8) var(--space-8); }

.preview-dialog-body {
  max-height: 70vh; overflow-y: auto; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-xl); padding: var(--space-6);
  box-shadow: var(--shadow-sm);
}
</style>
