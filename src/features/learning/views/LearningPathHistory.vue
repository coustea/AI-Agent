<template>
  <main class="path-history-page">
    <header class="history-header">
      <div>
        <span class="page-kicker">路径历史</span>
        <h1>以前的学习路线都在这里</h1>
        <p>你可以回看旧路径，也可以把任意一条历史路径重新设为当前学习路径继续推进。</p>
      </div>
      <div class="header-actions">
        <button class="ghost-btn" @click="router.push('/path-planner')">新建路径</button>
        <button class="ghost-btn" @click="router.push('/path-planner/overview/latest')">回到当前路径</button>
      </div>
    </header>

    <section v-if="loading" class="state-card">正在加载历史路径...</section>
    <section v-else-if="items.length === 0" class="state-card">还没有历史路径记录。</section>

    <section v-else class="history-grid">
      <article v-for="item in items" :key="item.id" class="history-card">
        <div class="history-top">
          <strong>{{ item.title }}</strong>
          <span>{{ item.status }}</span>
        </div>
        <p>{{ item.goal }}</p>
        <div class="history-meta">
          <span>进度 {{ item.overall_progress }}%</span>
          <span>{{ formatTime(item.updated_at) }}</span>
        </div>
        <div class="history-actions">
          <button class="ghost-btn" @click="viewPath(item.id)">查看总览</button>
          <button class="primary-btn" @click="activate(item.id)">继续学习</button>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { activateLearningPath, getLearningPathHistory } from '@/features/learning/api/path'
import type { LearningPathHistoryItem } from '@/features/learning/model/path'
import { getErrorMessage } from '@/shared/api/http'

const router = useRouter()
const loading = ref(false)
const items = ref<LearningPathHistoryItem[]>([])

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await getLearningPathHistory()
    items.value = res.data.data || []
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载路径历史失败'))
  } finally {
    loading.value = false
  }
}

const activate = async (pathId: number) => {
  try {
    const res = await activateLearningPath(pathId)
    router.push(`/path-planner/overview/${res.data.data.id}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '恢复历史路径失败'))
  }
}

const viewPath = (pathId: number) => {
  router.push(`/path-planner/overview/${pathId}`)
}

const formatTime = (value: string) => new Date(value).toLocaleString('zh-CN')

onMounted(loadHistory)
</script>

<style scoped>
.path-history-page {
  min-height: calc(100vh - 64px);
  padding: 28px 32px 48px;
  background: #f8fafc;
}

.history-header,
.history-card,
.state-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.history-header {
  max-width: 1180px;
  margin: 0 auto 20px;
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.page-kicker {
  display: inline-block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.history-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #0f172a;
}

.history-header p {
  margin: 0;
  color: #475569;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: start;
}

.history-grid {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.history-card {
  padding: 20px;
}

.history-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.history-top strong {
  color: #0f172a;
}

.history-top span,
.history-card p,
.history-meta span {
  color: #475569;
}

.history-card p {
  margin: 0 0 12px;
  line-height: 1.6;
}

.history-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  margin-bottom: 14px;
}

.history-actions {
  display: flex;
  gap: 12px;
}

.state-card {
  max-width: 880px;
  margin: 40px auto 0;
  padding: 32px;
  text-align: center;
}

.primary-btn,
.ghost-btn {
  border-radius: 8px;
  font: inherit;
  cursor: pointer;
  padding: 10px 16px;
}

.primary-btn {
  border: none;
  background: #2563eb;
  color: #fff;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

@media (max-width: 900px) {
  .history-header,
  .history-grid {
    grid-template-columns: 1fr;
  }

  .history-header {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .path-history-page {
    padding: 16px;
  }

  .history-actions,
  .header-actions {
    flex-direction: column;
  }
}
</style>
