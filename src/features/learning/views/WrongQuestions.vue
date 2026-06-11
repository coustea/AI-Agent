<template>
  <div class="wrong-questions-container">
    <div class="page-header">
      <h1>错题本</h1>
      <p class="subtitle">记录学习过程中的错题，针对性巩固薄弱知识点</p>
    </div>

    <div class="main-layout">
      <!-- 左侧统计卡片 -->
      <div class="stats-panel">
        <div class="stats-card">
          <div class="stat-item">
            <div class="stat-icon wrong">
              <el-icon><Close /></el-icon>
            </div>
            <div class="stat-info">
              <span class="stat-label">错题总数</span>
              <strong class="stat-value">{{ stats.total }}</strong>
            </div>
          </div>
        </div>

        <div class="practice-card">
          <h3>错题重练</h3>
          <p>随机抽取一道错题进行练习</p>
          <el-button type="primary" :loading="practiceLoading" @click="startPractice">
            <el-icon><Refresh /></el-icon>
            开始练习
          </el-button>
        </div>

        <div class="filter-card">
          <h3>筛选</h3>
          <div class="filter-item">
            <label>科目</label>
            <el-select v-model="filters.subject" placeholder="全部科目" clearable>
              <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
            </el-select>
          </div>
          <div class="filter-item">
            <label>题型</label>
            <el-select v-model="filters.type" placeholder="全部题型" clearable>
              <el-option v-for="t in types" :key="t" :label="t" :value="t" />
            </el-select>
          </div>
          <div class="filter-item">
            <label>状态</label>
            <el-select v-model="filters.isArchived" placeholder="全部状态">
              <el-option label="待练习" :value="false" />
              <el-option label="已归档" :value="true" />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 右侧题目列表 -->
      <div class="questions-panel">
        <div v-if="loading" class="loading-state">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <span>加载中...</span>
        </div>

        <div v-else-if="questions.length === 0" class="empty-state">
          <el-icon class="empty-icon"><FolderOpened /></el-icon>
          <p>暂无错题记录</p>
          <p class="hint">在题库练习中答错的题目会自动收录到这里</p>
        </div>

        <div v-else class="questions-list">
          <div v-for="q in questions" :key="q.id" class="question-card">
            <div class="card-header">
              <div class="tags-row">
                <el-tag size="small" type="info">{{ q.subject }}</el-tag>
                <el-tag size="small" type="warning">{{ q.question_type }}</el-tag>
                <el-tag v-if="q.wrong_count > 1" size="small" type="danger">
                  错误 {{ q.wrong_count }} 次
                </el-tag>
                <el-tag v-if="q.is_archived" size="small" type="success">已归档</el-tag>
              </div>
              <div class="actions">
                <el-button v-if="!q.is_archived" link type="primary" size="small" @click="archiveQuestion(q)">
                  标记已掌握
                </el-button>
                <el-button v-else link type="primary" size="small" @click="unarchiveQuestion(q)">
                  恢复练习
                </el-button>
                <el-button link type="danger" size="small" @click="deleteQuestion(q)">
                  删除
                </el-button>
              </div>
            </div>

            <div class="card-content markdown-body" v-html="renderMarkdown(q.content)"></div>

            <div v-if="q.options" class="options-preview">
              <div v-for="(val, key) in q.options" :key="key" class="option-item">
                <strong>{{ key }}:</strong> {{ val }}
              </div>
            </div>

            <el-collapse class="answer-collapse">
              <el-collapse-item title="查看答案与解析">
                <div class="answer-section">
                  <div class="answer-row">
                    <span class="label">正确答案:</span>
                    <span class="value">{{ q.standard_answer }}</span>
                  </div>
                  <div v-if="q.user_answer" class="answer-row wrong">
                    <span class="label">你的答案:</span>
                    <span class="value">{{ q.user_answer }}</span>
                  </div>
                  <div v-if="q.analysis" class="analysis-section">
                    <span class="label">解析:</span>
                    <div class="analysis-content markdown-body" v-html="renderMarkdown(q.analysis)"></div>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>

        <el-pagination
          v-if="total > pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          class="pagination"
          @current-change="loadQuestions"
        />
      </div>
    </div>

    <!-- 练习弹窗 -->
    <el-dialog v-model="practiceVisible" title="错题重练" width="600px" :close-on-click-modal="false">
      <div v-if="practiceQuestion" class="practice-content">
        <div class="question-meta">
          <el-tag size="small" type="info">{{ practiceQuestion.subject }}</el-tag>
          <el-tag size="small" type="warning">{{ practiceQuestion.question_type }}</el-tag>
        </div>
        <div class="question-text markdown-body" v-html="renderMarkdown(practiceQuestion.content)"></div>

        <div v-if="practiceQuestion.options" class="practice-options">
          <div
            v-for="(val, key) in practiceQuestion.options"
            :key="key"
            :class="['option-item', { selected: practiceAnswer === key }]"
            @click="practiceAnswer = key"
          >
            <strong>{{ key }}:</strong> {{ val }}
          </div>
        </div>
        <div v-else class="practice-input">
          <el-input v-model="practiceAnswer" type="textarea" :rows="3" placeholder="请输入你的答案" />
        </div>
      </div>
      <template #footer>
        <el-button @click="practiceVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!practiceAnswer" @click="submitPractice">提交答案</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Close, Refresh, Loading, FolderOpened } from '@element-plus/icons-vue'
import {
  fetchWrongQuestions,
  removeWrongQuestion,
  archiveWrongQuestion,
  unarchiveWrongQuestion,
  fetchRandomWrongQuestion,
  type WrongQuestion,
} from '@/features/learning/api/wrongQuestions'
import { marked } from 'marked'

const loading = ref(false)
const questions = ref<WrongQuestion[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const subjects = ref<string[]>([])
const types = ref<string[]>([])

const filters = reactive({
  subject: '',
  type: '',
  isArchived: false,
})

const stats = computed(() => ({
  total: total.value,
}))

const practiceVisible = ref(false)
const practiceLoading = ref(false)
const practiceQuestion = ref<WrongQuestion | null>(null)
const practiceAnswer = ref('')

const renderMarkdown = (text: string) => {
  if (!text) return ''
  return marked(text) as string
}

const loadQuestions = async () => {
  loading.value = true
  try {
    const result = await fetchWrongQuestions({
      subject: filters.subject || undefined,
      question_type: filters.type || undefined,
      is_archived: filters.isArchived,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    questions.value = result.items
    total.value = result.total
    subjects.value = result.subjects
    types.value = result.types
  } catch {
    ElMessage.error('加载错题列表失败')
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  currentPage.value = 1
  loadQuestions()
}, { deep: true })

const archiveQuestion = async (q: WrongQuestion) => {
  try {
    await archiveWrongQuestion(q.id)
    ElMessage.success('已标记为已掌握')
    loadQuestions()
  } catch {
    ElMessage.error('操作失败')
  }
}

const unarchiveQuestion = async (q: WrongQuestion) => {
  try {
    await unarchiveWrongQuestion(q.id)
    ElMessage.success('已恢复到错题本')
    loadQuestions()
  } catch {
    ElMessage.error('操作失败')
  }
}

const deleteQuestion = async (q: WrongQuestion) => {
  try {
    await ElMessageBox.confirm('确定要删除这道错题记录吗？', '确认删除', {
      type: 'warning',
    })
    await removeWrongQuestion(q.id)
    ElMessage.success('已删除')
    loadQuestions()
  } catch {
    // 用户取消
  }
}

const startPractice = async () => {
  practiceLoading.value = true
  try {
    const q = await fetchRandomWrongQuestion(filters.subject || undefined)
    if (!q) {
      ElMessage.info('暂无可练习的错题')
      return
    }
    practiceQuestion.value = q
    practiceAnswer.value = ''
    practiceVisible.value = true
  } catch {
    ElMessage.error('获取错题失败')
  } finally {
    practiceLoading.value = false
  }
}

const submitPractice = async () => {
  if (!practiceQuestion.value) return

  const q = practiceQuestion.value
  const isCorrect = checkAnswer(q, practiceAnswer.value)

  if (isCorrect) {
    ElMessage.success('回答正确！')
    await archiveWrongQuestion(q.id)
  } else {
    ElMessage.error('回答错误，继续加油！')
  }

  practiceVisible.value = false
  loadQuestions()
}

const checkAnswer = (q: WrongQuestion, answer: string): boolean => {
  const normalizedAnswer = answer.trim().toUpperCase()
  const normalizedStandard = (q.standard_answer || '').trim().toUpperCase()
  if (q.options) {
    return normalizedAnswer === normalizedStandard
  }
  return normalizedAnswer.length > 0 && normalizedStandard.includes(normalizedAnswer)
}

onMounted(() => {
  loadQuestions()
})
</script>

<style scoped>
.wrong-questions-container {
  padding: 24px;
  min-height: calc(100vh - 64px);
  background: var(--color-bg);
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 8px 0;
}

.subtitle {
  color: var(--color-text-muted);
  margin: 0;
}

.main-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
}

.stats-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-card,
.practice-card,
.filter-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.stat-icon.wrong {
  background: rgba(239, 68, 68, 0.1);
  color: var(--color-danger);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.practice-card h3,
.filter-card h3 {
  margin: 0 0 8px 0;
  font-size: 1rem;
  font-weight: 600;
}

.practice-card p {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin: 0 0 12px 0;
}

.filter-item {
  margin-bottom: 12px;
}

.filter-item label {
  display: block;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.filter-item .el-select {
  width: 100%;
}

.questions-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted);
}

.loading-icon,
.empty-icon {
  font-size: 3rem;
  margin-bottom: 12px;
}

.hint {
  font-size: 0.85rem;
  margin-top: 8px;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.actions {
  display: flex;
  gap: 8px;
}

.card-content {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--color-text);
  margin-bottom: 12px;
}

.options-preview {
  background: var(--color-surface);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.option-item {
  padding: 6px 0;
  font-size: 0.9rem;
}

.answer-collapse {
  margin-top: 12px;
}

.answer-section {
  padding: 12px;
  background: var(--color-surface);
  border-radius: 8px;
}

.answer-row {
  margin-bottom: 8px;
}

.answer-row .label {
  font-weight: 600;
  color: var(--color-text-muted);
  margin-right: 8px;
}

.answer-row.wrong .value {
  color: var(--color-danger);
}

.analysis-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--color-border);
}

.analysis-content {
  margin-top: 8px;
  font-size: 0.9rem;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.practice-content {
  padding: 16px 0;
}

.question-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.question-text {
  font-size: 1rem;
  line-height: 1.6;
  margin-bottom: 20px;
}

.practice-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.practice-options .option-item {
  padding: 12px 16px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.practice-options .option-item:hover {
  border-color: var(--color-primary);
}

.practice-options .option-item.selected {
  background: rgba(90, 82, 255, 0.1);
  border-color: var(--color-primary);
}

@media (max-width: 768px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
}
</style>
