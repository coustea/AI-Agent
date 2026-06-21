<template>
  <div class="elegant-generator-layout history-layout">
    <div class="omni-ambient-bg">
      <div class="ambient-glow glow-blue"></div>
      <div class="ambient-glow glow-indigo"></div>
      <div class="omni-pattern-bg"></div>
    </div>
    
    <div class="history-container">
      <div class="view-header">
        <el-button @click="router.push('/resource-generator')" class="back-btn" link>
          <el-icon><ArrowLeft /></el-icon> 返回引擎
        </el-button>
        <div class="header-titles">
          <h2>资源生成历史</h2>
          <p>查看并回顾您使用多智能体协同生成的所有专属学习资料</p>
        </div>
      </div>

      <div class="history-list-wrapper" v-loading="loading">
        <el-empty v-if="!loading && historyList.length === 0" description="暂无资源生成记录" />
        
        <div v-else class="history-grid">
          <div
            v-for="item in historyList"
            :key="item.id"
            class="history-card"
            @click="goToDetail(item.id)"
          >
            <div class="card-status-bar" :class="item.status"></div>
            <div class="card-header">
              <span class="card-time"><el-icon><Clock /></el-icon> {{ formatTime(item.created_at) }}</span>
              <el-tag size="small" :type="getStatusType(item.status)" effect="light" round>{{ getStatusText(item.status) }}</el-tag>
            </div>
            <div class="card-body">
              <h3 class="learning-need" :title="item.learning_need || '未提供学习需求'">
                {{ item.learning_need || '未提供学习需求' }}
              </h3>
              <div class="resource-types">
                <span v-for="type in (item.resource_types || [])" :key="type" class="type-badge">
                  {{ getResourceTypeLabel(type) }}
                </span>
              </div>
            </div>
            <div class="card-footer">
              <span>查看详情</span>
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
        <div class="pagination-wrapper" v-if="total > 0">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[12, 24, 48]"
            layout="total, sizes, prev, pager, next"
            :total="total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
            background
          />
        </div>
      </div>
    </div>
  </div>

</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Clock, ArrowRight } from '@element-plus/icons-vue'
import { getGeneratedResources } from '@/features/resource/api/resource-history'
import type { GeneratedResourceItem } from '@/features/resource/api/resource-history'
import { getResourceTypeLabel } from '@/features/resource/model/ResourceGeneratorConstants'

const router = useRouter()
const loading = ref(false)
const historyList = ref<GeneratedResourceItem[]>([])
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await getGeneratedResources(currentPage.value, pageSize.value)
    if (res.data?.code === 200) {
      historyList.value = res.data.data?.items || []
      total.value = res.data.data?.total || 0
    }
  } catch (err) {
    console.error('Failed to load history', err)
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchHistory()
}

const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchHistory()
}

const formatTime = (time: string | null) => {
  if (!time) return '未知时间'
  const date = new Date(time)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const getStatusType = (status: string): any => {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed' || status === 'error') return 'danger'
  if (status === 'running' || status === 'processing') return 'primary'
  return 'info'
}

const getStatusText = (status: string) => {
  if (status === 'success' || status === 'completed') return '已完成'
  if (status === 'failed' || status === 'error') return '失败'
  if (status === 'running' || status === 'processing') return '生成中'
  return '待处理'
}

const goToDetail = (id: number) => {
  router.push(`/resource-detail/${id}`)
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.elegant-generator-layout {
  --font-sans: var(--font-ui);
  --agent-body-font: var(--font-body);

  min-height: calc(100vh - 64px);
  position: relative;
  background: var(--color-bg);
  overflow-x: hidden;
  font-family: var(--font-sans);
}

.omni-ambient-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
  background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
}

.ambient-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.6;
  animation: float-glow 20s ease-in-out infinite alternate;
}

.glow-blue {
  top: -10%; left: -10%;
  width: 60vw; height: 60vw;
  background: radial-gradient(circle, rgba(59,130,246,0.3) 0%, rgba(59,130,246,0) 70%);
}

.glow-indigo {
  bottom: -20%; right: -10%;
  width: 70vw; height: 70vw;
  background: radial-gradient(circle, rgba(99,102,241,0.25) 0%, rgba(99,102,241,0) 70%);
  animation-delay: -10s;
}

@keyframes float-glow {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(5%, 5%) scale(1.05); }
}

.history-container {
  position: relative;
  z-index: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 24px 80px;
}

.view-header {
  margin-bottom: 40px;
}

.back-btn {
  margin-bottom: 24px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.back-btn:hover {
  color: var(--color-primary);
}

.header-titles h2 {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin: 0 0 12px 0;
  letter-spacing: -0.03em;
}

.header-titles p {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin: 0;
  font-family: var(--agent-body-font);
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;
}

.history-card {
  position: relative;
  background: var(--color-surface);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 200px;
}

.history-card:hover {
  background: var(--color-surface);
  transform: translateY(-6px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-border-strong);
}

.card-status-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-border);
}

.card-status-bar.success, .card-status-bar.completed {
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-hover));
}

.card-status-bar.running, .card-status-bar.processing {
  background: linear-gradient(90deg, var(--cat-tutor), #60A5FA);
}

.card-status-bar.failed, .card-status-bar.error {
  background: linear-gradient(90deg, var(--color-danger), #F87171);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
}

.card-time {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-mono);
}

.card-body {
  flex: 1;
}

.learning-need {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  line-height: 1.5;
  margin: 0 0 var(--space-4) 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-family: var(--agent-body-font);
}

.resource-types {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
}

.type-badge {
  background: var(--cat-resource-soft);
  color: var(--cat-resource);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-4);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--color-primary);
  opacity: 0.8;
  transition: opacity 0.2s;
}

.history-card:hover .card-footer {
  opacity: 1;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 40px;
}

@media (max-width: 768px) {
  .history-grid {
    grid-template-columns: 1fr;
  }
  .header-titles h2 {
    font-size: 2rem;
  }
}
</style>
