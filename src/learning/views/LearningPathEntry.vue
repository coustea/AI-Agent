<template>
  <main class="path-entry-page">
    <section class="entry-shell">
      <div class="entry-copy">
        <span class="entry-kicker">学习路径</span>
        <h1>先说清你想学什么</h1>
        <p>第一次进入先生成学习路线。系统只会规划节点，不会一次性把教程、题目和辅助资料全都生成出来。</p>
      </div>

      <div class="entry-card">
        <label class="field-label" for="path-goal">学习目标</label>
        <textarea
          id="path-goal"
          v-model="goal"
          class="goal-textarea"
          placeholder="例如：系统学习 FastAPI，从基础接口开发到项目部署"
        />

        <div class="entry-actions">
          <button class="primary-btn" :disabled="submitting" @click="handleSubmit">
            {{ submitting ? '生成中...' : '生成学习路径' }}
          </button>
          <button class="ghost-btn" @click="router.push('/path-planner/history')">查看历史路径</button>
        </div>

        <div class="tag-row">
          <button
            v-for="idea in quickIdeas"
            :key="idea"
            class="idea-tag"
            @click="goal = idea"
          >
            {{ idea }}
          </button>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createLearningPath } from '@/learning/api/path'
import { getErrorMessage } from '@/shared/utils/http'

const router = useRouter()
const goal = ref('')
const submitting = ref(false)

const quickIdeas = [
  '系统学习 FastAPI 后端开发',
  '掌握 Vue 3 组件设计与状态管理',
  '夯实机器学习数学基础',
  '从零开始学操作系统核心原理',
]

const handleSubmit = async () => {
  const value = goal.value.trim()
  if (!value) {
    ElMessage.warning('先输入一个学习目标')
    return
  }

  submitting.value = true
  try {
    const res = await createLearningPath({ goal: value, topic: value })
    const path = res.data.data
    router.push(`/path-planner/overview/${path.id}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成学习路径失败'))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.path-entry-page {
  min-height: calc(100vh - 64px);
  padding: 32px;
  background: #f8fafc;
}

.entry-shell {
  max-width: 1080px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  gap: 24px;
  align-items: start;
}

.entry-copy,
.entry-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.entry-copy {
  padding: 28px;
}

.entry-kicker {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 12px;
}

.entry-copy h1 {
  margin: 0 0 12px;
  font-size: 34px;
  line-height: 1.2;
  color: #0f172a;
}

.entry-copy p {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.entry-card {
  padding: 24px;
}

.field-label {
  display: block;
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.goal-textarea {
  width: 100%;
  min-height: 180px;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 14px 16px;
  font: inherit;
  color: #0f172a;
  background: #fff;
}

.goal-textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.entry-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.primary-btn,
.ghost-btn,
.idea-tag {
  border-radius: 8px;
  font: inherit;
  cursor: pointer;
}

.primary-btn {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 10px 16px;
  font-weight: 600;
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  padding: 10px 16px;
}

.tag-row {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.idea-tag {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  padding: 8px 12px;
}

@media (max-width: 960px) {
  .entry-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .path-entry-page {
    padding: 16px;
  }

  .entry-copy h1 {
    font-size: 28px;
  }

  .entry-actions {
    flex-direction: column;
  }
}
</style>
