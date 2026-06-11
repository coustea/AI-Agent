<template>
  <div class="wrong-questions-container">
    <div class="page-header">
      <h2>错题本</h2>
      <span class="total-count" v-if="total > 0">共 {{ total }} 题</span>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <el-empty description="暂无错题记录" />
    </div>

    <div v-else class="wrong-list">
      <div v-for="item in items" :key="item.id" class="wrong-item">
        <div class="item-header">
          <el-tag size="small" type="info" effect="plain">{{ item.subject }}</el-tag>
          <el-tag size="small" type="warning" effect="light">{{ item.question_type }}</el-tag>
          <span class="wrong-count">错 {{ item.wrong_count }} 次</span>
          <el-button size="small" type="primary" link @click="archiveItem(item.id)">移除</el-button>
        </div>
        <div class="item-content markdown-body" v-html="renderMarkdown(item.content)"></div>
        <div v-if="item.user_answer" class="item-user-answer">
          <span class="label">你的答案：</span>{{ item.user_answer }}
        </div>
        <div v-if="item.standard_answer" class="item-standard-answer">
          <span class="label">正确答案：</span>
          <div class="markdown-body" v-html="renderMarkdown(item.standard_answer)"></div>
        </div>
        <div v-if="item.analysis" class="item-analysis">
          <span class="label">解析：</span>
          <div class="markdown-body" v-html="renderMarkdown(item.analysis)"></div>
        </div>
      </div>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadData"
        class="pagination"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchWrongQuestions, archiveWrongQuestion, type WrongQuestionItem } from '@/features/learning/api/wrongQuestions'

const items = ref<WrongQuestionItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)

function renderMarkdown(text: string): string {
  return text || ''
}

async function loadData() {
  loading.value = true
  try {
    const res = await fetchWrongQuestions({ page: currentPage.value, page_size: pageSize })
    items.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载错题列表失败')
  } finally {
    loading.value = false
  }
}

async function archiveItem(id: number) {
  try {
    await archiveWrongQuestion(id)
    ElMessage.success('已移除')
    loadData()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.wrong-questions-container {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
}

.total-count {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.wrong-item {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.wrong-count {
  color: var(--el-color-danger);
  font-size: 13px;
  margin-left: auto;
}

.item-content {
  margin-bottom: 8px;
  line-height: 1.6;
}

.item-user-answer {
  color: var(--el-color-danger);
  font-size: 14px;
  margin-bottom: 6px;
}

.item-standard-answer,
.item-analysis {
  font-size: 14px;
  margin-bottom: 6px;
}

.label {
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.pagination {
  margin-top: 20px;
  justify-content: center;
}
</style>
