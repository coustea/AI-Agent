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
      <div class="resource-header">
        <h2>{{ resource.title || resource.learning_need || '学习资源包' }}</h2>
        <div class="resource-meta">
          <el-tag :type="getStatusType(resource.status)" size="small">
            {{ getStatusText(resource.status) }}
          </el-tag>
          <span class="meta-item">
            <el-icon><Clock /></el-icon>
            {{ formatTime(resource.created_at) }}
          </span>
        </div>
      </div>

      <div class="resource-section">
        <h4>学习需求</h4>
        <p class="learning-need">{{ resource.learning_need || '暂无描述' }}</p>
      </div>

      <div class="resource-section">
        <h4>生成资源 ({{ resource.resources?.length || 0 }})</h4>
        <div v-if="!resource.resources?.length" class="empty-resources">
          暂无生成资源
        </div>
        <div v-else class="resource-items">
          <div
            v-for="item in resource.resources"
            :key="item.id"
            class="resource-item-card"
          >
            <div class="item-header">
              <div class="item-type">
                <el-icon><Document /></el-icon>
                {{ getAgentTypeName(item.type) }}
              </div>
              <el-tag :type="getStatusType(item.status)" size="small">
                {{ getStatusText(item.status) }}
              </el-tag>
            </div>
            <h5 class="item-title">{{ item.title || `${getAgentTypeName(item.type)}资源` }}</h5>
            <div v-if="item.summary" class="item-summary">{{ item.summary }}</div>
            <div v-if="item.error_message" class="item-error">
              <el-icon><WarningFilled /></el-icon>
              {{ item.error_message }}
            </div>
            <el-collapse v-if="item.content" class="item-content-collapse">
              <el-collapse-item title="查看内容">
                <div class="item-content">
                  <ReadingResourceView v-if="item.type === 'reading'" :result-data="item" />
                  <div v-else-if="item.format === 'markdown'" v-html="renderMarkdown(item.content)"></div>
                  <pre v-else-if="item.format === 'json' || typeof item.content === 'object'">{{ JSON.stringify(item.content, null, 2) }}</pre>
                  <div v-else>{{ item.content }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Clock, Document, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { getGeneratedResourceDetail } from '@/api/ai'
import type { GeneratedResourceBundle } from '@/api/ai'
import ReadingResourceView from '@/components/resource/ReadingResourceView.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const resource = ref<GeneratedResourceBundle | null>(null)

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

const renderMarkdown = (content: string) => {
  if (typeof content !== 'string') return ''
  return marked(content)
}

onMounted(() => {
  loadResource()
})
</script>

<style scoped>
.resource-detail-page {
  padding: 24px;
  background-color: #F8FAFC;
  min-height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.loading-container,
.error-container {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 40px;
}

.resource-header {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.resource-header h2 {
  margin: 0 0 12px 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1E293B;
}

.resource-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.875rem;
  color: #64748B;
}

.resource-section {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}

.resource-section h4 {
  margin: 0 0 16px 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1E293B;
}

.learning-need {
  color: #475569;
  line-height: 1.6;
  margin: 0;
}

.empty-resources {
  color: #94A3B8;
  text-align: center;
  padding: 40px 0;
}

.resource-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.resource-item-card {
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-type {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4F46E5;
}

.item-title {
  margin: 0 0 8px 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1E293B;
}

.item-summary {
  font-size: 0.875rem;
  color: #64748B;
  margin-bottom: 12px;
}

.item-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.875rem;
  color: #EF4444;
  background: #FEF2F2;
  padding: 8px 12px;
  border-radius: 8px;
}

.item-content-collapse {
  margin-top: 12px;
}

.item-content {
  font-size: 0.875rem;
  line-height: 1.6;
  color: #475569;
  max-height: 400px;
  overflow-y: auto;
}

.item-content pre {
  background: #F1F5F9;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.8rem;
}
</style>
