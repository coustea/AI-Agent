<template>
  <main class="path-resource-detail-page">
    <div class="page-topbar">
      <button class="ghost-btn" @click="router.push('/path-resource-history')">返回路径资源记录</button>
      <button
        v-if="pathNodeId"
        class="ghost-btn"
        @click="router.push(`/path-planner/node/${pathNodeId}`)"
      >
        返回当前节点
      </button>
      <button class="ghost-btn" @click="router.push('/path-planner/history')">返回路径历史</button>
    </div>

    <section v-if="loading" class="state-card">正在加载路径资源...</section>
    <section v-else-if="!resource" class="state-card">路径资源不存在。</section>

    <template v-else>
      <header class="detail-header">
        <div>
          <span class="page-kicker">路径辅助资源</span>
          <h1>{{ resource.title }}</h1>
          <p>{{ resource.resource_type }} · 第 {{ resource.version_no }} 版</p>
        </div>
        <span class="meta-time">{{ formatTime(resource.created_at) }}</span>
      </header>

      <section class="detail-card">
        <MindmapView
          v-if="resource.resource_type === 'mindmap'"
          :result-data="resourceContent"
        />
        <CodeView
          v-else-if="resource.resource_type === 'code'"
          :result-data="resourceContent"
        />
        <PptView
          v-else-if="resource.resource_type === 'ppt'"
          :result-data="resourceContent"
        />
        <MarkdownView
          v-else
          :result-data="resourceContent"
        />
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import CodeView from '@/features/resource/components/CodeView.vue'
import MarkdownView from '@/features/resource/components/MarkdownView.vue'
import MindmapView from '@/features/resource/components/MindmapView.vue'
import PptView from '@/features/resource/components/PptView.vue'
import { getPathGeneratedResourceDetail } from '@/features/learning/api/path-resource'
import type { PathResourceDetail } from '@/features/learning/model/path'
import { getErrorMessage } from '@/shared/api/http'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const resource = ref<PathResourceDetail | null>(null)

const resourceId = computed(() => Number(route.params.id || 0))
const pathNodeId = computed(() => Number(route.query.pathNodeId || 0))

const resourceContent = computed(() => {
  if (!resource.value) return null
  if (resource.value.content_json) return { content: resource.value.content_json }
  return { content: resource.value.content_text || '' }
})

const loadDetail = async () => {
  if (!resourceId.value) return
  loading.value = true
  try {
    const res = await getPathGeneratedResourceDetail(resourceId.value)
    resource.value = res.data.data
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载路径资源失败'))
  } finally {
    loading.value = false
  }
}

const formatTime = (value: string) => new Date(value).toLocaleString('zh-CN')

onMounted(loadDetail)
</script>

<style scoped>
.path-resource-detail-page {
  min-height: calc(100vh - 64px);
  padding: 28px 32px 48px;
  background: #f8fafc;
}

.page-topbar,
.detail-header,
.detail-card,
.state-card {
  max-width: 1180px;
  margin: 0 auto;
}

.page-topbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.detail-header,
.detail-card,
.state-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.detail-header {
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.page-kicker {
  display: inline-block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.detail-header h1 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 28px;
}

.detail-header p,
.meta-time {
  margin: 0;
  color: #475569;
}

.detail-card {
  padding: 20px;
}

.state-card {
  padding: 32px;
  text-align: center;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  border-radius: 8px;
  padding: 10px 16px;
  font: inherit;
  cursor: pointer;
}

@media (max-width: 640px) {
  .path-resource-detail-page {
    padding: 16px;
  }

  .page-topbar,
  .detail-header {
    flex-direction: column;
  }
}
</style>
