<template>
  <div class="resource-detail-page">
    <div v-if="loading" class="detail-state-shell" aria-label="正在加载资源包">
      <div class="custom-skeleton-loader">
        <div class="skeleton-line" v-for="i in 8" :key="i"></div>
      </div>
    </div>

    <div v-else-if="error" class="detail-state-shell detail-error-state">
      <div class="custom-error-empty">
        <p class="error-desc">资源包加载失败</p>
        <div class="error-actions">
          <button class="btn btn-outline" @click="goBack">返回个人中心</button>
          <button class="btn btn-primary" @click="loadResource">重新加载</button>
        </div>
      </div>
    </div>

    <Bundle
      v-else-if="resource"
      :bundle="resource"
      :warning="resourceWarning"
      action-label="返回个人中心"
      action-kind="back"
      context-label="创建时间"
      :context-value="createdAtLabel"
      @action="goBack"
      @preview="openResourcePreview"
    />

    <!-- 统一资源预览弹窗 -->
    <PreviewDialog
      v-model:activeAgent="activePreviewAgent"
      :data="previewData"
      :resource="previewResource"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import Bundle from '@/features/resource/components/result/Bundle.vue'
import PreviewDialog from '@/shared/content/PreviewDialog.vue'
import { getGeneratedResourceDetail } from '@/features/resource/api/history'
import type { GeneratedResourceBundle } from '@/features/resource/api/history'

type PreviewPayload = {
  agentId: string
  resultData: any
  title: string
  resource?: any
}



const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const resource = shallowRef<GeneratedResourceBundle | null>(null)
const activePreviewAgent = ref<string | null>(null)
const previewData = ref<any>(null)
const previewResource = ref<any>(null)

const resourceId = computed(() => Number(route.params.id) || null)

const resourceWarning = computed(() => {
  if (resource.value?.status !== 'partial_completed') return ''
  return '部分资源未能完成，以下已生成内容仍可正常查看。'
})

const createdAtLabel = computed(() => formatTime(resource.value?.created_at || null))

onMounted(loadResource)

async function loadResource() {
  if (!resourceId.value) {
    loading.value = false
    error.value = true
    return
  }

  loading.value = true
  error.value = false

  try {
    const response = await getGeneratedResourceDetail(resourceId.value)
    resource.value = response.data?.data || null
    error.value = !resource.value
  } catch (requestError) {
    console.error('Failed to load resource detail:', requestError)
    resource.value = null
    error.value = true
    toast.error('加载资源详情失败')
  } finally {
    loading.value = false
  }
}

function openResourcePreview(payload: PreviewPayload) {
  activePreviewAgent.value = payload.agentId || null
  previewData.value = payload.resultData || null
  previewResource.value = payload.resource || null
}

function goBack() {
  router.push({ name: 'Profile' })
}

function formatTime(time: string | null) {
  if (!time) return ''

  const date = new Date(time)
  if (Number.isNaN(date.getTime())) return ''

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<style scoped>
.resource-detail-page {
  width: 100%;
  min-height: 100%;
  background: #f4f7fb;
}

.detail-state-shell {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 48px 0;
}

.detail-error-state {
  display: grid;
  min-height: 70vh;
  place-items: center;
}

.custom-skeleton-loader {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, var(--color-surface-hover) 25%, var(--color-border) 37%, var(--color-surface-hover) 63%);
  background-size: 400% 100%;
  animation: skeleton-loading 1.4s ease infinite;
  border-radius: 4px;
}

.skeleton-line:nth-child(1) { width: 38%; }
.skeleton-line:nth-child(2) { width: 94%; }
.skeleton-line:nth-child(3) { width: 88%; }
.skeleton-line:nth-child(4) { width: 56%; }
.skeleton-line:nth-child(5) { width: 72%; }
.skeleton-line:nth-child(6) { width: 80%; }
.skeleton-line:nth-child(7) { width: 44%; }
.skeleton-line:nth-child(8) { width: 62%; }

@keyframes skeleton-loading {
  0% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.custom-error-empty {
  text-align: center;
  padding: 60px 40px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  max-width: 500px;
  width: 100%;
  box-shadow: var(--shadow-sm);
}

.error-desc {
  font-size: 16px;
  color: var(--color-text-secondary);
  margin-bottom: 20px;
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

/* Custom Modal CSS */
.custom-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.custom-modal-container {
  width: 78%;
  max-width: 1200px;
  max-height: 88vh;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-2xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.custom-modal-container.is-ppt-dialog {
  background: transparent;
  border: none;
  box-shadow: none;
  width: 90%;
  max-width: 1400px;
}

.custom-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
}

.custom-modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.modal-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.modal-close-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.close-icon {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.custom-modal-body {
  flex: 1;
  padding: 24px;
  background: #f4f7fb;
  overflow-y: auto;
}

.custom-modal-body.is-ppt-body {
  padding: 0;
  background: transparent;
}

.preview-dialog-body {
  max-height: 70vh;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid #e1e6ed;
  border-radius: 8px;
  background: #fff;
}

.preview-dialog-body.is-ppt-preview {
  max-height: none;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

/* Animations */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 680px) {
  .detail-state-shell {
    width: calc(100% - 24px);
    padding: 24px 0;
  }
}
</style>
