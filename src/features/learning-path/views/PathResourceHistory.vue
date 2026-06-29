<template>
  <div class="elegant-generator-layout history-layout">
    <div class="omni-ambient-bg">
      <div class="ambient-glow glow-cyan"></div>
      <div class="ambient-glow glow-emerald"></div>
      <div class="omni-pattern-bg"></div>
    </div>

    <div class="history-container">
      <div class="view-header">
        <button @click="router.push('/path-planner')" class="back-btn">
          <ArrowLeft class="back-btn-icon" />
          <span>返回路径规划</span>
        </button>
        <div class="header-titles">
          <h2>路径资源记录</h2>
          <p>查看学习路径各节点生成过的资料记录，并回到对应节点继续学习。</p>
        </div>
      </div>

      <div class="history-list-wrapper" v-loading="loading">
        <div v-if="!loading && historyList.length === 0" class="empty-state-container">
          <p>暂无路径资源记录</p>
        </div>

        <div v-else class="history-grid">
          <div
            v-for="item in historyList"
            :key="item.id"
            class="history-card"
            @click="goToDetail(item)"
          >
            <div class="card-status-bar" :class="item.status"></div>
            <div class="card-header">
              <span class="card-time"><Clock class="card-time-icon" /> {{ formatTime(item.created_at) }}</span>
              <span class="tag-pill" :class="getStatusType(item.status)">{{ getStatusText(item.status) }}</span>
            </div>
            <div class="card-body">
              <h3 class="learning-need" :title="item.title || item.node_title || item.learning_need || '未命名路径资源'">
                {{ item.title || item.node_title || item.learning_need || '未命名路径资源' }}
              </h3>
              <p class="node-meta">{{ item.learning_need || '该资源来自路径节点资料生成。' }}</p>
              <div class="resource-types">
                <span v-for="type in normalizedTypes(item)" :key="type" class="type-badge">
                  {{ getResourceTypeLabel(type) }}
                </span>
              </div>
            </div>
            <div class="card-footer">
              <span>查看路径资源</span>
              <ArrowRight class="footer-arrow-icon" />
            </div>
          </div>
        </div>

        <div class="pagination-wrapper" v-if="total > 0">
          <div class="custom-pagination">
            <span class="pagination-total">共 {{ total }} 条</span>
            <div class="pagination-size">
              <select v-model="pageSize" @change="handleSizeChange(pageSize)" class="pagination-select">
                <option :value="12">12 条/页</option>
                <option :value="24">24 条/页</option>
                <option :value="48">48 条/页</option>
              </select>
            </div>
            <div class="pagination-buttons">
              <button 
                class="btn-pager" 
                :disabled="currentPage === 1" 
                @click="handleCurrentChange(currentPage - 1)"
              >
                上一页
              </button>
              <span class="pagination-current">{{ currentPage }} / {{ Math.ceil(total / pageSize) }}</span>
              <button 
                class="btn-pager" 
                :disabled="currentPage >= Math.ceil(total / pageSize)" 
                @click="handleCurrentChange(currentPage + 1)"
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PhArrowLeft as ArrowLeft, PhClock as Clock, PhArrowRight as ArrowRight } from '@phosphor-icons/vue'
import { getPathGeneratedResources } from '@/features/learning-path/api/path-resource'
import type { PathGeneratedResourceItem } from '@/features/resource/api/resource-history'
import { getResourceTypeLabel } from '@/features/resource/model/ResourceGeneratorConstants'

const router = useRouter()
const loading = ref(false)
const historyList = ref<PathGeneratedResourceItem[]>([])
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await getPathGeneratedResources(currentPage.value, pageSize.value)
    if (res.data?.code === 200) {
      historyList.value = res.data.data?.items || []
      total.value = res.data.data?.total || 0
    }
  } catch (err) {
    console.error('Failed to load path resource history', err)
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
  if (status === 'running' || status === 'processing' || status === 'pending' || status === 'generating') return 'primary'
  return 'info'
}

const getStatusText = (status: string) => {
  if (status === 'success' || status === 'completed') return '已完成'
  if (status === 'failed' || status === 'error') return '失败'
  if (status === 'running' || status === 'processing' || status === 'pending' || status === 'generating') return '生成中'
  return '待处理'
}

const goToDetail = (item: PathGeneratedResourceItem) => {
  router.push({
    name: 'PathResourceDetail',
    params: { id: item.id },
    query: {
      pathId: item.path_id ?? undefined,
      pathNodeId: item.path_node_id ?? undefined,
      nodeId: item.node_id ?? undefined,
    },
  })
}

const normalizedTypes = (item: PathGeneratedResourceItem) => {
  if (item.resource_types?.length) return item.resource_types
  if (item.resource_type) return [item.resource_type]
  return []
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.elegant-generator-layout {
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
  background: linear-gradient(135deg, #F5FBFF 0%, #ECFDF5 100%);
}

.ambient-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.6;
  animation: float-glow 20s ease-in-out infinite alternate;
}

.glow-cyan {
  top: -10%;
  left: -10%;
  width: 60vw;
  height: 60vw;
  background: radial-gradient(circle, rgba(14,165,233,0.25) 0%, rgba(14,165,233,0) 70%);
}

.glow-emerald {
  bottom: -20%;
  right: -10%;
  width: 70vw;
  height: 70vw;
  background: radial-gradient(circle, rgba(16,185,129,0.2) 0%, rgba(16,185,129,0) 70%);
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
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: color var(--transition-base);
}

.back-btn:hover {
  color: var(--color-primary);
}

.back-btn-icon {
  width: 16px;
  height: 16px;
}

.header-titles h2 {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--color-text);
  margin: 0 0 12px 0;
}

.header-titles p {
  font-size: 1.1rem;
  color: var(--color-text-secondary);
  margin: 0;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;
}

.history-card {
  position: relative;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 220px;
}

.history-card:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-6px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.08);
}

.card-status-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--color-border);
}

.card-status-bar.success,
.card-status-bar.completed {
  background: linear-gradient(90deg, #10B981, #34D399);
}

.card-status-bar.failed,
.card-status-bar.error {
  background: linear-gradient(90deg, #EF4444, #F97316);
}

.card-status-bar.pending,
.card-status-bar.processing,
.card-status-bar.generating,
.card-status-bar.running {
  background: linear-gradient(90deg, #0EA5E9, #38BDF8);
}

.card-header,
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-time {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.92rem;
  color: var(--color-text-secondary);
}

.card-time-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-muted);
}

.tag-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  border-radius: var(--radius-pill);
}

.tag-pill.success {
  background: rgba(16, 185, 129, 0.08);
  color: #047857;
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.tag-pill.danger {
  background: rgba(239, 68, 68, 0.08);
  color: #B91C1C;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.tag-pill.primary {
  background: rgba(37, 99, 235, 0.08);
  color: #1D4ED8;
  border: 1px solid rgba(37, 99, 235, 0.15);
}

.tag-pill.info {
  background: rgba(100, 116, 139, 0.08);
  color: #475569;
  border: 1px solid rgba(100, 116, 139, 0.15);
}

.card-body {
  flex: 1;
  margin: 20px 0;
}

.learning-need {
  margin: 0 0 12px;
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--color-text);
  line-height: 1.5;
}

.node-meta {
  margin: 0 0 16px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.resource-types {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.08);
  color: #0369A1;
  font-size: 0.86rem;
  font-weight: 700;
}

.card-footer {
  color: #0369A1;
  font-weight: 700;
}

.footer-arrow-icon {
  width: 16px;
  height: 16px;
  color: #0369A1;
}

.empty-state-container {
  padding: 80px 40px;
  text-align: center;
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--color-border);
  border-radius: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

.custom-pagination {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 14px;
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.7);
  padding: 10px 20px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.pagination-select {
  height: 32px;
  padding: 0 8px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  outline: none;
  font-size: 13px;
  color: var(--color-text);
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-pager {
  height: 32px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all var(--transition-base);
  font-size: 12px;
  color: var(--color-text-secondary);
}

.btn-pager:hover:not(:disabled) {
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
  color: var(--color-text);
}

.btn-pager:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  font-weight: 600;
  color: var(--color-text);
}

@media (max-width: 768px) {
  .history-container {
    padding: 24px 16px 64px;
  }

  .header-titles h2 {
    font-size: 2rem;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }
}
</style>
