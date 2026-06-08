<template>
  <main class="path-node-page">
    <section v-if="loading" class="state-card">正在准备节点学习空间...</section>
    <section v-else-if="!workspace" class="state-card">节点不存在或已经失效。</section>

    <template v-else>
      <header class="node-header">
        <div>
          <button class="text-link" @click="router.push(`/path-planner/overview/${workspace.path.id}`)">返回路径总览</button>
          <span class="page-kicker">节点学习</span>
          <h1>{{ workspace.node.title }}</h1>
          <p>{{ workspace.node.mastery_target || workspace.node.recommendation_reason || '围绕当前节点完成学习、测验和巩固。' }}</p>
        </div>

        <div class="node-summary">
          <span>状态：{{ statusText(workspace.node.status) }}</span>
          <span>轮次：{{ workspace.node.attempt_count }}</span>
          <span v-if="workspace.node.estimated_minutes">建议 {{ workspace.node.estimated_minutes }} 分钟</span>
        </div>
      </header>

      <section class="node-layout">
        <article class="tutorial-panel">
          <div class="panel-head">
            <div>
              <span class="mini-kicker">当前教程</span>
              <h2>{{ workspace.current_tutorial?.title || '暂无教程' }}</h2>
            </div>
            <span class="tutorial-badge">{{ tutorialTypeText(workspace.current_tutorial?.tutorial_type) }}</span>
          </div>

          <MarkdownView
            v-if="workspace.current_tutorial"
            :result-data="{ content: workspace.current_tutorial.content_markdown }"
          />

          <div v-if="workspace.current_tutorial?.weak_knowledge_points?.length" class="weak-box">
            <strong>本轮重点巩固</strong>
            <div class="weak-tags">
              <span v-for="point in workspace.current_tutorial.weak_knowledge_points" :key="point">{{ point }}</span>
            </div>
          </div>
        </article>

        <aside class="side-panel">
          <section class="panel-card">
            <div class="panel-head compact">
              <div>
                <span class="mini-kicker">辅助资源</span>
                <h3>按需生成</h3>
              </div>
            </div>
            <div class="resource-actions">
              <button class="ghost-btn" :disabled="resourceLoading === 'mindmap'" @click="createResource('mindmap')">生成思维导图</button>
              <button class="ghost-btn" :disabled="resourceLoading === 'code'" @click="createResource('code')">生成代码示例</button>
              <button class="ghost-btn" :disabled="resourceLoading === 'ppt'" @click="createResource('ppt')">生成 PPT</button>
            </div>
            <div class="saved-resource-list" v-if="workspace.resources.length">
              <button
                v-for="resource in workspace.resources"
                :key="resource.id"
                class="saved-resource-item"
                @click="router.push(`/path-resource/${resource.id}`)"
              >
                <strong>{{ resource.title }}</strong>
                <span>{{ resource.resource_type }}</span>
              </button>
            </div>
          </section>

          <section class="panel-card">
            <div class="panel-head compact">
              <div>
                <span class="mini-kicker">节点测验</span>
                <h3>固定 5 道单选题</h3>
              </div>
              <button class="primary-btn small" :disabled="quizLoading" @click="loadQuiz">
                {{ quizLoading ? '生成中...' : '开始测验' }}
              </button>
            </div>

            <div v-if="quizRound" class="quiz-panel">
              <article v-for="question in quizRound.questions" :key="question.id" class="quiz-item">
                <strong>{{ question.question_no }}. {{ question.question }}</strong>
                <label
                  v-for="(value, key) in question.choice"
                  :key="key"
                  class="choice-item"
                >
                  <input
                    v-model="answers[question.id]"
                    type="radio"
                    :name="`question-${question.id}`"
                    :value="key"
                  >
                  <span>{{ key }}. {{ value }}</span>
                </label>
              </article>

              <button class="primary-btn submit-btn" :disabled="submitLoading" @click="submitQuiz">
                {{ submitLoading ? '提交中...' : '提交测验' }}
              </button>
            </div>

            <div v-if="quizResult" class="result-box">
              <strong>本轮结果：{{ quizResult.score }}/5</strong>
              <p>{{ resultText(quizResult.outcome) }}</p>
              <div v-if="quizResult.weak_knowledge_points.length" class="weak-tags">
                <span v-for="point in quizResult.weak_knowledge_points" :key="point">{{ point }}</span>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import MarkdownView from '@/features/resource/components/MarkdownView.vue'
import { generateAuxiliaryResource, generateNodeQuestions, getLearningNodeWorkspace, submitNodeQuiz } from '@/features/learning/api/path'
import { recordPathLearningEvent } from '@/features/learning/api/evaluation'
import type { AuxiliaryResourceRequest, LearningPathWorkspace, PathQuizRound, PathQuizSubmitResponse } from '@/features/learning/model/path'
import { getErrorMessage } from '@/shared/api/http'
import { startTracking, stopTracking } from '@/features/learning/model/useLearningTracker'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const quizLoading = ref(false)
const submitLoading = ref(false)
const resourceLoading = ref<AuxiliaryResourceRequest['resource_type'] | ''>('')

const workspace = ref<LearningPathWorkspace | null>(null)
const quizRound = ref<PathQuizRound | null>(null)
const quizResult = ref<PathQuizSubmitResponse | null>(null)
const answers = ref<Record<number, string>>({})

const nodeId = Number(route.params.nodeId || 0)

const loadWorkspace = async () => {
  if (!nodeId) return
  loading.value = true
  try {
    const res = await getLearningNodeWorkspace(nodeId)
    workspace.value = res.data.data
    if (workspace.value) {
      startTracking({
        sourcePage: 'path_node',
        pathId: workspace.value.path.id,
        pathNodeId: workspace.value.node.id,
        nodeId: workspace.value.node.node_id,
        course: workspace.value.path.title,
        topic: workspace.value.node.title,
      })
      await recordPathLearningEvent(workspace.value.path.id, {
        event_type: 'resource_viewed',
        path_id: workspace.value.path.id,
        path_node_id: workspace.value.node.id,
        node_id: workspace.value.node.node_id,
        course: workspace.value.path.title,
        topic: workspace.value.node.title,
      })
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载节点学习空间失败'))
  } finally {
    loading.value = false
  }
}

const loadQuiz = async () => {
  if (!workspace.value) return
  quizLoading.value = true
  quizResult.value = null
  try {
    const res = await generateNodeQuestions(workspace.value.node.id)
    quizRound.value = res.data.data
    answers.value = {}
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成节点测验失败'))
  } finally {
    quizLoading.value = false
  }
}

const submitQuiz = async () => {
  if (!workspace.value || !quizRound.value) return
  const payload = {
    answers: quizRound.value.questions.map((question) => ({
      question_id: question.id,
      response: answers.value[question.id] || '',
    })),
  }

  if (payload.answers.some((item) => !item.response)) {
    ElMessage.warning('请先完成全部 5 道题')
    return
  }

  submitLoading.value = true
  try {
    const res = await submitNodeQuiz(workspace.value.node.id, payload)
    quizResult.value = res.data.data

    await recordPathLearningEvent(workspace.value.path.id, {
      event_type: 'quiz_submitted',
      path_id: workspace.value.path.id,
      path_node_id: workspace.value.node.id,
      node_id: workspace.value.node.node_id,
      course: workspace.value.path.title,
      topic: workspace.value.node.title,
      score: Number(((quizResult.value.score / 5) * 100).toFixed(0)),
      metadata: {
        outcome: quizResult.value.outcome,
        weak_knowledge_points: quizResult.value.weak_knowledge_points,
      },
    })

    await loadWorkspace()
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '提交节点测验失败'))
  } finally {
    submitLoading.value = false
  }
}

const createResource = async (type: AuxiliaryResourceRequest['resource_type']) => {
  if (!workspace.value) return
  resourceLoading.value = type
  try {
    const res = await generateAuxiliaryResource(workspace.value.node.id, { resource_type: type })
    router.push(`/path-resource/${res.data.data.id}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '生成辅助资源失败'))
  } finally {
    resourceLoading.value = ''
    await loadWorkspace()
  }
}

const tutorialTypeText = (value?: string | null) => {
  if (value === 'remediation') return '专项巩固'
  if (value === 'reinforced') return '强化教程'
  return '主教程'
}

const statusText = (status: string) => {
  switch (status) {
    case 'available': return '学习中'
    case 'completed': return '已通过'
    case 'completed_with_gaps': return '带缺口完成'
    default: return status
  }
}

const resultText = (outcome: string) => {
  switch (outcome) {
    case 'passed': return '本节点通过，下一节点已解锁。'
    case 'remediation': return '第一次未通过，已生成围绕错题知识点的专项巩固教程。'
    case 'reinforced': return '第二次未通过，已生成强化教程继续巩固薄弱点。'
    case 'completed_with_gaps': return '两轮后仍未通过，当前节点记为带缺口完成，系统允许进入下一阶段。'
    default: return outcome
  }
}

onMounted(loadWorkspace)
onBeforeUnmount(() => {
  stopTracking()
})
</script>

<style scoped>
.path-node-page {
  min-height: calc(100vh - 64px);
  padding: 28px 32px 48px;
  background: #f8fafc;
}

.node-header,
.tutorial-panel,
.panel-card,
.state-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.node-header {
  max-width: 1240px;
  margin: 0 auto 20px;
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.text-link {
  border: none;
  background: transparent;
  color: #2563eb;
  padding: 0;
  margin-bottom: 12px;
  cursor: pointer;
}

.page-kicker,
.mini-kicker {
  display: inline-block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.node-header h1 {
  margin: 0 0 8px;
  font-size: 30px;
  color: #0f172a;
}

.node-header p {
  margin: 0;
  color: #475569;
  max-width: 680px;
  line-height: 1.6;
}

.node-summary {
  display: grid;
  gap: 10px;
  align-content: start;
  color: #475569;
}

.node-layout {
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) 380px;
  gap: 20px;
}

.tutorial-panel,
.panel-card {
  padding: 20px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  align-items: start;
}

.panel-head h2,
.panel-head h3 {
  margin: 0;
  color: #0f172a;
}

.panel-head.compact h3 {
  font-size: 18px;
}

.tutorial-badge {
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.weak-box {
  margin-top: 16px;
  padding: 14px;
  border-radius: 8px;
  background: #fff7ed;
}

.weak-box strong {
  display: block;
  margin-bottom: 10px;
  color: #9a3412;
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weak-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  background: #fed7aa;
  color: #9a3412;
  font-size: 13px;
}

.side-panel {
  display: grid;
  gap: 16px;
}

.resource-actions {
  display: grid;
  gap: 10px;
}

.saved-resource-list {
  margin-top: 14px;
  display: grid;
  gap: 8px;
}

.saved-resource-item {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  text-align: left;
  cursor: pointer;
}

.saved-resource-item strong,
.quiz-item strong {
  color: #0f172a;
}

.saved-resource-item span {
  display: block;
  margin-top: 4px;
  color: #475569;
  font-size: 13px;
}

.quiz-panel {
  display: grid;
  gap: 16px;
}

.quiz-item {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px;
}

.choice-item {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  color: #334155;
}

.submit-btn {
  width: 100%;
}

.result-box {
  margin-top: 16px;
  padding: 14px;
  border-radius: 8px;
  background: #f8fafc;
}

.result-box strong {
  display: block;
  margin-bottom: 8px;
  color: #0f172a;
}

.result-box p {
  margin: 0 0 10px;
  color: #475569;
  line-height: 1.6;
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

.primary-btn.small {
  padding: 8px 12px;
  font-size: 14px;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

.state-card {
  max-width: 880px;
  margin: 40px auto 0;
  padding: 32px;
  text-align: center;
}

@media (max-width: 980px) {
  .node-layout {
    grid-template-columns: 1fr;
  }

  .node-header {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .path-node-page {
    padding: 16px;
  }

  .node-header h1 {
    font-size: 26px;
  }
}
</style>
