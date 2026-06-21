<template>
  <div class="resource-detail-page">
    <div v-if="loading" class="detail-state-shell" aria-label="正在加载资源包">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="detail-state-shell detail-error-state">
      <el-empty description="资源包加载失败">
        <div class="error-actions">
          <el-button @click="goBack">返回个人中心</el-button>
          <el-button type="primary" @click="loadResource">重新加载</el-button>
        </div>
      </el-empty>
    </div>

    <ResourceBundleView
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

    <el-dialog
      v-model="previewVisible"
      :title="previewItem?.title || '资源预览'"
      width="78%"
      top="6vh"
      destroy-on-close
      :class="['resource-preview-dialog', { 'is-ppt-dialog': previewItem?.type === 'ppt' }]"
    >
      <div
        v-if="previewItem"
        class="preview-dialog-body"
        :class="{ 'is-ppt-preview': previewItem.type === 'ppt' }"
      >
        <MindmapView v-if="previewItem.type === 'mindmap'" :result-data="previewItem.content" />
        <QuizView v-else-if="previewItem.type === 'quiz'" :result-data="previewItem.content" />
        <CodeView v-else-if="previewItem.type === 'code'" :result-data="previewItem.content" />
        <ReadingView v-else-if="previewItem.type === 'reading'" :result-data="previewItem.content" />
        <PptView
          v-else-if="previewItem.type === 'ppt' && previewPptDocument"
          :document-data="previewPptDocument"
        />
        <VideoView v-else-if="previewItem.type === 'video'" :result-data="previewItem.content" />
        <MarkdownView v-else :result-data="previewItem.content" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import ResourceBundleView from '@/features/resource/components/ResourceBundleView.vue'
import MindmapView from '@/features/resource/components/MindmapView.vue'
import MarkdownView from '@/features/resource/components/MarkdownView.vue'
import QuizView from '@/features/resource/components/QuizView.vue'
import CodeView from '@/features/resource/components/CodeView.vue'
import ReadingView from '@/features/resource/components/ReadingView.vue'
import PptView from '@/features/resource/components/PptView.vue'
import VideoView from '@/features/resource/components/VideoView.vue'
import { parsePptDocument } from '@/features/resource/components/ppt-engine/types/ppt'
import { getGeneratedResourceDetail } from '@/features/resource/api/resource-history'
import type { GeneratedResourceBundle } from '@/features/resource/api/resource-history'

type PreviewPayload = {
  agentId: string
  resultData: any
  title: string
}

type PreviewItem = {
  type: string
  content: any
  title: string
}

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const resource = shallowRef<GeneratedResourceBundle | null>(null)
const previewItem = shallowRef<PreviewItem | null>(null)
const previewVisible = ref(false)

const resourceId = computed(() => Number(route.params.id) || null)

const resourceWarning = computed(() => {
  if (resource.value?.status !== 'partial_completed') return ''
  return '部分资源未能完成，以下已生成内容仍可正常查看。'
})

const createdAtLabel = computed(() => formatTime(resource.value?.created_at || null))

const previewPptDocument = computed(() => {
  if (previewItem.value?.type !== 'ppt') return null
  const parsed = parsePptDocument(previewItem.value.content)
  return parsed.ok ? parsed.document : null
})

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
    ElMessage.error('加载资源详情失败')
  } finally {
    loading.value = false
  }
}

function openResourcePreview(payload: PreviewPayload) {
  previewItem.value = {
    type: payload.agentId,
    content: payload.resultData,
    title: payload.title,
  }
  previewVisible.value = true
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
  background: #f5f6f8;
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

.error-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
}

:global(.resource-preview-dialog) {
  overflow: hidden;
  border-radius: 18px;
}

:global(.resource-preview-dialog .el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e7ebf0;
}

:global(.resource-preview-dialog .el-dialog__body) {
  padding: 20px 24px 24px;
  background: #f5f6f8;
}

.preview-dialog-body {
  max-height: 70vh;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid #e1e6ed;
  border-radius: 12px;
  background: #fff;
}

:global(.is-ppt-dialog .el-dialog__body) {
  padding: 0;
}

.preview-dialog-body.is-ppt-preview {
  max-height: none;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

@media (max-width: 680px) {
  .detail-state-shell {
    width: calc(100% - 24px);
    padding: 24px 0;
  }
}
</style>
