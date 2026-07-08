<template>
  <div class="elegant-generator-layout history-layout">
    <div class="omni-ambient-bg">
      <div class="ambient-glow glow-blue"></div>
      <div class="ambient-glow glow-indigo"></div>
      <div class="omni-pattern-bg"></div>
    </div>
    
    <div class="history-container">
      <div class="view-header">
        <button @click="router.push('/resource-generator')" class="back-btn">
          <ArrowLeft class="back-btn-icon" />
          <span>返回引擎</span>
        </button>
        <div class="header-titles">
          <h2>资源生成历史</h2>
          <p>查看并回顾您使用多智能体协同生成的所有专属学习资料</p>
        </div>
      </div>

      <div class="history-list-wrapper" v-loading="loading">
        <div v-if="!loading && historyList.length === 0" class="empty-state-container">
          <p>暂无资源生成记录</p>
        </div>
        
        <div v-else class="history-grid">
          <div
            v-for="item in historyList"
            :key="item.id"
            class="history-card"
            @click="goToDetail(item.id)"
          >
            <div class="card-status-bar" :class="item.status"></div>
            <div class="card-header">
              <span class="card-time"><Clock class="card-time-icon" /> {{ formatTime(item.created_at) }}</span>
              <span class="tag-pill" :class="getStatusType(item.status)">{{ getStatusText(item.status) }}</span>
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
// 引入 Vue 组合式 API：响应式状态与挂载钩子
import { ref, onMounted } from 'vue'
// 引入路由实例，用于跳转到资源详情页
import { useRouter } from 'vue-router'
// 引入界面所需的 Phosphor 图标：返回、时钟、右箭头
import { PhArrowLeft as ArrowLeft, PhClock as Clock, PhArrowRight as ArrowRight } from '@phosphor-icons/vue'
// 引入历史资源列表查询接口
import { getGeneratedResources } from '@/features/resource/api/history'
// 引入历史资源条目的类型定义
import type { GeneratedResourceItem } from '@/features/resource/api/history'
// 引入共享的内容类型标签工具，用于展示资源类型中文名
import { getArtifactLabel as getResourceTypeLabel } from '@/shared/content/kind'

// 路由实例
const router = useRouter()
// 列表加载中状态
const loading = ref(false)
// 历史资源列表数据
const historyList = ref<GeneratedResourceItem[]>([])
// 当前分页页码
const currentPage = ref(1)
// 每页条数，默认 12
const pageSize = ref(12)
// 历史资源总数，用于分页计算
const total = ref(0)

// 拉取当前页的历史资源列表，统一处理成功/失败与加载态
const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await getGeneratedResources(currentPage.value, pageSize.value)
    // 仅当后端返回成功（code 200）时写入列表与总数
    if (res.data?.code === 200) {
      historyList.value = res.data.data?.items || []
      total.value = res.data.data?.total || 0
    }
  } catch (err) {
    // 加载失败仅打印错误，不阻断页面其余展示
    console.error('Failed to load history', err)
  } finally {
    // 无论成功失败均关闭加载态
    loading.value = false
  }
}

// 每页条数变更：更新 pageSize 并重新拉取
const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchHistory()
}

// 当前页码变更：更新 currentPage 并重新拉取
const handleCurrentChange = (val: number) => {
  currentPage.value = val
  fetchHistory()
}

// 将 ISO 时间格式化为「年-月-日 时:分」，空值返回「未知时间」
const formatTime = (time: string | null) => {
  if (!time) return '未知时间'
  const date = new Date(time)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

// 将后端状态映射为标签样式类型（success/danger/primary/info）
const getStatusType = (status: string): any => {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed' || status === 'error') return 'danger'
  if (status === 'running' || status === 'processing') return 'primary'
  return 'info'
}

// 将后端状态映射为中文展示文案
const getStatusText = (status: string) => {
  if (status === 'success' || status === 'completed') return '已完成'
  if (status === 'failed' || status === 'error') return '失败'
  if (status === 'running' || status === 'processing') return '生成中'
  return '待处理'
}

// 跳转到指定资源详情页
const goToDetail = (id: number) => {
  router.push(`/resource-detail/${id}`)
}

// 组件挂载后首次拉取历史列表
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
  background: #f4f7fb;
  overflow-x: hidden;
  font-family: var(--font-sans);
}

.omni-ambient-bg {
  display: none;
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
  background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(59,130,246,0) 70%);
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
  margin-bottom: 28px;
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
  font-size: 30px;
  font-weight: 800;
  color: var(--color-text-strong);
  margin: 0 0 12px 0;
  letter-spacing: 0;
}

.header-titles p {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin: 0;
  font-family: var(--agent-body-font);
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.history-card {
  position: relative;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-6);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 200px;
}

.history-card:hover {
  background: var(--color-surface);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(23, 32, 51, 0.08);
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
  background: #4f46e5;
}

.card-status-bar.running, .card-status-bar.processing {
  background: #0ea5e9;
}

.card-status-bar.failed, .card-status-bar.error {
  background: #ef4444;
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

.footer-arrow-icon {
  width: 16px;
  height: 16px;
  color: var(--color-primary);
}

.empty-state-container {
  padding: 80px 40px;
  text-align: center;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.history-card:hover .card-footer {
  opacity: 1;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 40px;
}

.custom-pagination {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 14px;
  color: var(--color-text-secondary);
  background: var(--color-surface);
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
  .history-grid {
    grid-template-columns: 1fr;
  }
  .header-titles h2 {
    font-size: 2rem;
  }
}
</style>
