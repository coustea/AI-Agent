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

                <el-button
                    v-if="hasPreviewContent(item)"
                    class="export-btn"
                    type="primary"
                    link
                    title="导出到本地"
                    @click.stop="exportToLocal(item)"
                >
                  <el-icon :size="18"><Download /></el-icon>
                </el-button>
              </div>
            </article>
          </div>
        </div>
      </main>
    </template>

<script setup lang="ts">
import { ArrowLeft, Clock, Document, WarningFilled, CircleCheckFilled, Loading, Cpu, Edit, Collection, VideoPlay, Monitor, Share, Download } from '@element-plus/icons-vue'

import { computed, ref, onMounted } from 'vue'

import { ElMessage } from 'element-plus'

import { useRoute, useRouter } from 'vue-router'

import CodeView from '@/components/resource/CodeView.vue'

import MarkdownView from '@/components/resource/MarkdownView.vue'

import MindmapView from '@/components/resource/MindmapView.vue'

import PptView from '@/components/resource/PptView.vue'

import QuizView from '@/components/resource/QuizView.vue'

import ReadingView from '@/components/resource/ReadingView.vue'

import { getGeneratedResourceDetail } from '@/api/ai'

import type { GeneratedResourceBundle, ResourceItemDetail } from '@/api/ai'

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

onMounted(() => {
  loadResource()
})

declare function withDefaults<T, D>(props: T, defaults: D): T;

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
    diagram: { icon: Monitor, color: 'tone-amber' },
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
    diagram: '图解',
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

const exportToLocal = async (item: ResourceItemDetail) => {
  if (!hasPreviewContent(item)) {
    ElMessage.warning('暂无可导出的内容')
    return
  }

  let contentStr = ''
  let ext = '.md'
  let mimeType = 'text/markdown'

  // 1. 尝试从不同字段获取可导出的内容，并自动判断格式
  if (item.content != null && String(item.content).trim()) {
    contentStr = String(item.content)
    // 简单试探内容是否为原生 JSON
    if (contentStr.trim().startsWith('{') || contentStr.trim().startsWith('[')) {
      try {
        JSON.parse(contentStr)
        ext = '.json'
        mimeType = 'application/json'
      } catch (e) {
        // 如果解析失败，则按正常的 markdown/普通文本处理
      }
    }
  } else if (item.summary_data && Object.keys(item.summary_data).length > 0) {
    contentStr = JSON.stringify(item.summary_data, null, 2)
    ext = '.json'
    mimeType = 'application/json'
  } else if (item.metadata && Object.keys(item.metadata).length > 0) {
    contentStr = JSON.stringify(item.metadata, null, 2)
    ext = '.json'
    mimeType = 'application/json'
  }

  // 2. 构造默认文件名
  const fileName = `${item.title || getAgentTypeName(item.type) || '导出资源'}${ext}`

  try {
    // 3. 尝试使用现代 File System Access API（允许用户在弹窗中选择具体保存路径）
    if ('showSaveFilePicker' in window) {
      // @ts-ignore (规避 TypeScript 可能找不到 DOM 文件系统 API 声明的问题)
      const handle = await window.showSaveFilePicker({
        suggestedName: fileName,
        types: [
          {
            description: `${getAgentTypeName(item.type)}文件`,
            accept: {
              [mimeType]: [ext]
            }
          }
        ]
      })
      const writable = await handle.createWritable()
      await writable.write(contentStr)
      await writable.close()
      ElMessage.success('已成功导出到本地')
    } else {
      // 4. 降级方案：使用传统 <a> 标签下载（路径由浏览器控制，通常在浏览器设置里可以开启“下载前询问每个文件的保存位置”）
      const blob = new Blob([contentStr], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      ElMessage.success('已开始下载')
    }
  } catch (error: any) {
    // 捕获异常，如果是用户在选择路径面板点击了“取消”(AbortError)，则静默处理
    if (error.name !== 'AbortError') {
      console.error('导出失败:', error)
      ElMessage.error('导出失败，可能缺少权限或不支持此操作')
    }
  }
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
</script>

<style scoped>
.resource-detail-page {
  background: #F4F7FB;
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
  padding: 24px 60px 0;
  z-index: 2;
}
.back-btn {
  font-weight: 700;
  font-size: 1rem;
  color: #475569;
}
.back-btn:hover { color: #2563EB; }

.loading-container,
.error-container {
  background: #FFFFFF;
  border-radius: 24px;
  padding: 60px;
  margin: 40px 60px;
  position: relative;
  z-index: 1;
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.05);
}

.detail-hero-premium {
  position: relative;
  margin: 24px 60px 40px;
  padding: 48px 54px;
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  z-index: 1;
  box-shadow: 0 20px 40px -10px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}
.hero-bg-pattern {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  background-image: radial-gradient(rgba(15, 23, 42, 0.03) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}
.hero-content {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 1;
}

.hero-status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 800;
  width: max-content;
}
.hero-status-tag.success-glow {
  background: rgba(16, 185, 129, 0.1); color: #059669; border: 1px solid rgba(16, 185, 129, 0.2);
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.15); animation: pulse-success 2s infinite alternate;
}
.hero-status-tag.processing-glow {
  background: rgba(59, 130, 246, 0.1); color: #2563EB; border: 1px solid rgba(59, 130, 246, 0.2);
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.15); animation: pulse-primary 2s infinite alternate;
}
.hero-status-tag.danger-glow {
  background: rgba(225, 29, 72, 0.1); color: #E11D48; border: 1px solid rgba(225, 29, 72, 0.2);
}
.hero-status-tag.info-glow {
  background: rgba(100, 116, 139, 0.1); color: #475569; border: 1px solid rgba(100, 116, 139, 0.2);
}

@keyframes pulse-success { 0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.1); } 100% { box-shadow: 0 0 25px rgba(16, 185, 129, 0.3); } }
@keyframes pulse-primary { 0% { box-shadow: 0 0 10px rgba(59, 130, 246, 0.1); } 100% { box-shadow: 0 0 25px rgba(59, 130, 246, 0.3); } }

.hero-title.gradient-text {
  margin: 0;
  font-size: 2.2rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #0F172A 0%, #334155 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.3;
}

.hero-context-pills { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 8px; }
.glass-pill {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 10px 18px;
  font-size: 0.95rem;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
}
.pill-label { color: #64748B; font-weight: 800; margin-right: 12px; text-transform: uppercase; letter-spacing: 0.05em; font-size: 0.8rem; }
.pill-value { color: #0F172A; font-weight: 600; display: flex; align-items: center; gap: 6px; }

.detail-body-bento {
  padding: 0 60px 60px;
  position: relative;
  z-index: 1;
}

.section-header { margin-bottom: 24px; }
.section-header h3 { margin: 0; font-size: 1.4rem; font-weight: 800; color: #0F172A; letter-spacing: -0.01em; }

.premium-resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 28px;
  align-items: stretch;
}

.premium-res-card {
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 24px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.03);
  animation: fadeSlideUp 0.6s ease-out backwards;
  outline: none;
}
@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }

.premium-res-card.is-clickable { cursor: pointer; }
.premium-res-card.is-clickable:hover,
.premium-res-card.is-clickable:focus-visible {
  transform: translateY(-8px);
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.1);
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

.card-header { display: flex; align-items: center; gap: 12px; }
.type-icon-box {
  width: 48px; height: 48px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04);
}
.premium-res-card.tone-blue .type-icon-box { color: #2563EB; }
.premium-res-card.tone-purple .type-icon-box { color: #7C3AED; }
.premium-res-card.tone-amber .type-icon-box { color: #D97706; }
.premium-res-card.tone-rose .type-icon-box { color: #E11D48; }
.premium-res-card.tone-emerald .type-icon-box { color: #059669; }
.premium-res-card.tone-indigo .type-icon-box { color: #6366F1; }
.premium-res-card.tone-slate .type-icon-box { color: #475569; }

.type-info { display: flex; flex-direction: column; gap: 4px; }
.type-label { font-size: 0.95rem; font-weight: 800; color: #0F172A; }
.status-badge { font-weight: 700; border: none; }

.card-body { display: flex; flex-direction: column; gap: 12px; flex: 1; }
.card-title { margin: 0; font-size: 1.15rem; font-weight: 800; color: #0F172A; line-height: 1.45; }
.card-summary { margin: 0; font-size: 0.95rem; color: #475569; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

.item-error {
  display: flex; align-items: center; gap: 8px;
  background: #FEF2F2; color: #E11D48; padding: 10px 14px; border-radius: 10px; font-size: 0.85rem; font-weight: 600;
  margin-top: auto;
}

.card-footer {
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  padding-top: 20px; margin-top: 4px; display: flex; justify-content: space-between; align-items: center;
}
.modern-text-btn {
  background: transparent; border: none; color: #0F172A; font-weight: 800; font-size: 0.95rem; padding: 0;
  display: flex; align-items: center; gap: 8px; transition: color 0.2s ease; cursor: pointer;
}
.modern-text-btn.disabled { color: #94A3B8; cursor: not-allowed; }
.modern-text-btn span { transition: transform 0.3s ease; }
.premium-res-card.is-clickable:hover .modern-text-btn:not(.disabled),
.premium-res-card.is-clickable:focus-visible .modern-text-btn:not(.disabled) { color: #2563EB; }
.premium-res-card.is-clickable:hover .modern-text-btn:not(.disabled) span,
.premium-res-card.is-clickable:focus-visible .modern-text-btn:not(.disabled) span { transform: translateX(4px); }

/* 导出按钮动画样式 */
.export-btn {
  color: #64748B !important;
  transition: color 0.2s ease, transform 0.2s ease !important;
}
.premium-res-card.is-clickable:hover .export-btn,
.premium-res-card.is-clickable:focus-visible .export-btn {
  color: #2563EB !important;
}
.export-btn:hover {
  transform: translateY(-2px) scale(1.1);
  color: #1D4ED8 !important;
}

.resource-preview-dialog :deep(.el-dialog) { border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25); }
.resource-preview-dialog :deep(.el-dialog__header) { padding: 24px 32px 20px; margin-right: 0; border-bottom: 1px solid #F1F5F9; }
.resource-preview-dialog :deep(.el-dialog__title) { font-size: 1.25rem; font-weight: 800; color: #0F172A; }
.resource-preview-dialog :deep(.el-dialog__body) { background: #F8FAFC; padding: 24px 32px 32px; }

.preview-dialog-body {
  max-height: 70vh; overflow-y: auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; padding: 24px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}
</style>
