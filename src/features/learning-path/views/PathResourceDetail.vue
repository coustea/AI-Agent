<template>
  <main class="path-resource-detail-page">
    <section class="resource-shell">
      <nav class="compact-nav">
        <div class="nav-left">
          <button class="nav-link" @click="router.push('/path-resource-history')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z" />
            </svg>
            返回资源记录
          </button>

          <button
            v-if="pathNodeId"
            class="nav-link"
            @click="router.push(`/path-planner/node/${pathNodeId}`)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 3 20 7.5v9L12 21l-8-4.5v-9L12 3Zm0 2.2L6 8.6v6.8l6 3.4 6-3.4V8.6l-6-3.4Z" />
            </svg>
            返回节点学习
          </button>

          <button class="nav-link" @click="router.push('/path-planner/history')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M13 3a9 9 0 1 0 8.95 10h-2.02A7 7 0 1 1 17.4 7.6L15 10h6V4l-2.18 2.18A8.96 8.96 0 0 0 13 3Zm-1 5v5l4.2 2.5 1-1.7-3.2-1.9V8h-2Z" />
            </svg>
            路径历史
          </button>
        </div>

        <div v-if="resource" class="nav-status">
          <span :class="['status-dot', resource.status || 'completed']"></span>
          {{ resource.status === 'failed' ? '生成失败' : '已生成' }}
        </div>
      </nav>

      <section v-if="loading" class="state-card">
        <div class="state-spinner"></div>
        <p>正在加载路径资源...</p>
      </section>

      <section v-else-if="!resource" class="state-card">
        <h2>路径资源不存在</h2>
        <p>该资源可能已被删除，或者当前账号没有访问权限。</p>
      </section>

      <template v-else>
        <section class="learning-workspace">
          <article class="tutorial-panel">
            <header class="tutorial-head">
              <div class="tutorial-title">
                <span class="section-kicker">{{ resourceTypeLabel(resource.resource_type) }}</span>
                <h1>{{ resource.title }}</h1>
                <p>{{ resource.summary || tutorialIntro }}</p>
              </div>

              <div class="tutorial-meta">
                <span>第 {{ resource.version_no }} 版</span>
                <span>{{ formatTime(resource.created_at) }}</span>
              </div>
            </header>

            <section v-if="resource.status === 'failed'" class="failure-card">
              <div class="failure-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M11 7h2v7h-2V7Zm0 9h2v2h-2v-2Zm1-14 11 20H1L12 2Zm0 4.1L4.4 20h15.2L12 6.1Z" />
                </svg>
              </div>
              <div>
                <strong>资源生成失败</strong>
                <p>{{ resource.error_message || '多智能体资源生成过程中出现异常，请返回节点学习页重新生成。' }}</p>
              </div>
            </section>

            <section v-else class="resource-content-card">
              <div class="content-toolbar">
                <div>
                  <span>AI 教程与学习资源</span>
                  <strong>{{ contentModeTitle }}</strong>
                </div>

                <button
                  v-if="pathNodeId"
                  class="small-action"
                  type="button"
                  @click="router.push(`/path-planner/node/${pathNodeId}`)"
                >
                  回到节点继续学习
                </button>
              </div>

              <div class="resource-view">
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
                <ReadingView
                  v-else-if="resource.resource_type === 'reading'"
                  :result-data="resourceContent"
                />
                <QuizView
                  v-else-if="resource.resource_type === 'quiz'"
                  :result-data="resourceContent"
                />
                <MarkdownView
                  v-else
                  :result-data="resourceContent"
                />
              </div>
            </section>
          </article>

          <aside class="agent-push-panel">
            <section class="side-card current-resource">
              <div class="side-head">
                <span>Resource Agent</span>
                <strong>{{ resourceTypeLabel(resource.resource_type) }}</strong>
              </div>

              <div class="resource-agent-icon" :class="resource.resource_type">
                <svg v-if="resource.resource_type === 'mindmap'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M11 3h2v4h-2V3Zm-7 8h6v2H4v-2Zm10 0h6v2h-6v-2ZM5 17h5v2H5v-2Zm9 0h5v2h-5v-2ZM11 8h2v3h-2V8Zm0 5h2v3h-2v-3Z" />
                </svg>
                <svg v-else-if="resource.resource_type === 'code'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m8.7 16.3-4.3-4.3 4.3-4.3L7.3 6.3 1.6 12l5.7 5.7 1.4-1.4Zm6.6 0 4.3-4.3-4.3-4.3 1.4-1.4 5.7 5.7-5.7 5.7-1.4-1.4ZM10.8 20 13.4 4h2l-2.6 16h-2Z" />
                </svg>
                <svg v-else-if="resource.resource_type === 'ppt'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 3h16v18H4V3Zm2 2v14h12V5H6Zm2 3h8v2H8V8Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z" />
                </svg>
                <svg v-else-if="resource.resource_type === 'quiz'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 11H7V9h2v2Zm0 4H7v-2h2v2Zm0 4H7v-2h2v2Zm2-10h6v2h-6V9Zm0 4h6v2h-6v-2Zm0 4h6v2h-6v-2ZM5 3h14a2 2 0 0 1 2 2v16H3V5a2 2 0 0 1 2-2Zm0 2v14h14V5H5Z" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 3h14a2 2 0 0 1 2 2v16H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm0 2v14h14V5H5Zm2 3h10v2H7V8Zm0 4h10v2H7v-2Zm0 4h6v2H7v-2Z" />
                </svg>
              </div>

              <h2>{{ resource.title }}</h2>
              <p>{{ resource.summary || resourceTypeDescription(resource.resource_type) }}</p>

              <div class="resource-info-grid">
                <div>
                  <label>资源类型</label>
                  <strong>{{ resourceTypeLabel(resource.resource_type) }}</strong>
                </div>
                <div>
                  <label>内容格式</label>
                  <strong>{{ resource.content_format || 'markdown' }}</strong>
                </div>
                <div>
                  <label>版本</label>
                  <strong>V{{ resource.version_no }}</strong>
                </div>
                <div>
                  <label>状态</label>
                  <strong>{{ resource.status === 'failed' ? '失败' : '完成' }}</strong>
                </div>
              </div>
            </section>

            <section class="side-card push-card">
              <div class="side-head">
                <span>Multi-Agent Push</span>
                <strong>资源推送</strong>
              </div>

              <p class="push-desc">
                当前资源由节点学习流程触发生成。不同智能体会围绕同一知识节点，继续推送教程、测验、导图、代码实操、PPT 和拓展阅读。
              </p>

              <div class="agent-flow">
                <div
                  v-for="item in agentPushItems"
                  :key="item.type"
                  :class="['agent-item', { active: item.type === resource.resource_type }]"
                >
                  <div class="agent-dot">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path :d="item.icon" />
                    </svg>
                  </div>

                  <div>
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.desc }}</span>
                  </div>

                  <em>{{ item.type === resource.resource_type ? '当前' : '可推送' }}</em>
                </div>
              </div>

              <button
                v-if="pathNodeId"
                class="push-action"
                type="button"
                @click="router.push(`/path-planner/node/${pathNodeId}`)"
              >
                返回节点生成更多资源
              </button>
            </section>

            <section class="side-card study-card">
              <div class="side-head">
                <span>Study Route</span>
                <strong>建议学习顺序</strong>
              </div>

              <div class="study-steps">
                <div>
                  <span>1</span>
                  <p>先阅读主教程，理解当前节点的核心概念。</p>
                </div>
                <div>
                  <span>2</span>
                  <p>使用导图或 PPT 梳理知识结构。</p>
                </div>
                <div>
                  <span>3</span>
                  <p>通过测验检测薄弱点，必要时触发补救资源。</p>
                </div>
                <div>
                  <span>4</span>
                  <p>结合代码实操或拓展阅读完成巩固。</p>
                </div>
              </div>
            </section>
          </aside>
        </section>
      </template>
    </section>
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
import QuizView from '@/features/resource/components/QuizView.vue'
import ReadingView from '@/features/resource/components/ReadingView.vue'
import { getPathGeneratedResourceDetail } from '@/features/learning-path/api/path-resource'
import type { PathResourceDetail } from '@/features/learning-path/model/path'
import { getErrorMessage } from '@/shared/api/http'

type AgentPushItem = {
  type: string
  title: string
  desc: string
  icon: string
}

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

const tutorialIntro = computed(() => {
  if (!resource.value) return ''
  return resourceTypeDescription(resource.value.resource_type)
})

const contentModeTitle = computed(() => {
  if (!resource.value) return '学习内容'
  if (resource.value.resource_type === 'content') return '节点主教程'
  if (resource.value.resource_type === 'reading') return '拓展阅读材料'
  if (resource.value.resource_type === 'mindmap') return '知识结构导图'
  if (resource.value.resource_type === 'code') return '代码实操案例'
  if (resource.value.resource_type === 'ppt') return '课程演示文稿'
  if (resource.value.resource_type === 'quiz') return '节点练习测验'
  return '学习内容'
})

const agentPushItems = computed<AgentPushItem[]>(() => [
  {
    type: 'content',
    title: '教程智能体',
    desc: '生成面向当前节点的主教程讲义',
    icon: 'M5 3h14a2 2 0 0 1 2 2v16H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm0 2v14h14V5H5Zm2 3h10v2H7V8Zm0 4h10v2H7v-2Zm0 4h6v2H7v-2Z',
  },
  {
    type: 'mindmap',
    title: '导图智能体',
    desc: '抽取概念关系，形成可视化知识结构',
    icon: 'M11 3h2v4h-2V3Zm-7 8h6v2H4v-2Zm10 0h6v2h-6v-2ZM5 17h5v2H5v-2Zm9 0h5v2h-5v-2ZM11 8h2v3h-2V8Zm0 5h2v3h-2v-3Z',
  },
  {
    type: 'quiz',
    title: '题库智能体',
    desc: '生成检测题，识别薄弱知识点',
    icon: 'M9 11H7V9h2v2Zm0 4H7v-2h2v2Zm0 4H7v-2h2v2Zm2-10h6v2h-6V9Zm0 4h6v2h-6v-2Zm0 4h6v2h-6v-2ZM5 3h14a2 2 0 0 1 2 2v16H3V5a2 2 0 0 1 2-2Zm0 2v14h14V5H5Z',
  },
  {
    type: 'code',
    title: '实操智能体',
    desc: '把抽象概念转成代码实验或案例',
    icon: 'm8.7 16.3-4.3-4.3 4.3-4.3L7.3 6.3 1.6 12l5.7 5.7 1.4-1.4Zm6.6 0 4.3-4.3-4.3-4.3 1.4-1.4 5.7 5.7-5.7 5.7-1.4-1.4ZM10.8 20 13.4 4h2l-2.6 16h-2Z',
  },
  {
    type: 'ppt',
    title: '课件智能体',
    desc: '整理成适合演示和复习的课件',
    icon: 'M4 3h16v18H4V3Zm2 2v14h12V5H6Zm2 3h8v2H8V8Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z',
  },
  {
    type: 'reading',
    title: '阅读智能体',
    desc: '推送补充材料和拓展阅读路径',
    icon: 'M12 6.5A5.5 5.5 0 0 0 6.5 1H3v18h4.5A4.5 4.5 0 0 1 12 23a4.5 4.5 0 0 1 4.5-4H21V1h-3.5A5.5 5.5 0 0 0 12 6.5ZM5 3h1.5A3.5 3.5 0 0 1 10 6.5v11.2A6.5 6.5 0 0 0 7.5 17H5V3Zm14 14h-2.5a6.5 6.5 0 0 0-2.5.7V6.5A3.5 3.5 0 0 1 17.5 3H19v14Z',
  },
])

const resourceTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    content: '教程',
    mindmap: '思维导图',
    code: '代码实操',
    reading: '拓展阅读',
    quiz: '练习测验',
    ppt: '课程 PPT',
  }
  return labels[type] || type
}

const resourceTypeDescription = (type: string) => {
  const descriptions: Record<string, string> = {
    content: '围绕当前路径节点生成的主教程内容，适合作为学习入口和知识讲解材料。',
    mindmap: '将当前节点的核心概念、关系和层级结构整理成导图，方便快速建立知识框架。',
    code: '将知识点转化为可操作的代码案例，通过实践理解抽象概念。',
    reading: '补充当前节点的拓展阅读材料，帮助你从更多角度理解知识点。',
    quiz: '围绕当前节点生成的练习题，用于检测掌握程度并暴露薄弱点。',
    ppt: '将教程内容整理成课件形式，适合复习、展示和快速回顾。',
  }
  return descriptions[type] || '由多智能体围绕当前学习节点生成的个性化学习资源。'
}

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

const formatTime = (value: string) => {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

onMounted(loadDetail)
</script>

<style scoped>
.path-resource-detail-page {
  --pr-primary: #4f46e5;
  --pr-primary-dark: #3730a3;
  --pr-primary-soft: #eef2ff;
  --pr-blue: #0ea5e9;
  --pr-cyan: #06b6d4;
  --pr-green: #10b981;
  --pr-orange: #f59e0b;
  --pr-red: #ef4444;
  --pr-slate: #64748b;
  --pr-muted: #94a3b8;
  --pr-text: #0f172a;
  --pr-border: #e2e8f0;
  --pr-border-strong: #c7d2fe;
  --pr-card: #ffffff;
  --pr-shadow: 0 14px 38px rgba(15, 23, 42, 0.06);

  min-height: calc(100vh - 64px);
  padding: 16px;
  background:
    radial-gradient(circle at 8% 0%, rgba(79, 70, 229, 0.07), transparent 30%),
    radial-gradient(circle at 92% 0%, rgba(14, 165, 233, 0.07), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  color: var(--pr-text);
}

.path-resource-detail-page svg {
  width: 1em;
  height: 1em;
  fill: currentColor;
}

.resource-shell {
  width: min(1720px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 14px;
}

.compact-nav {
  min-height: 58px;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(199, 210, 254, 0.75);
  box-shadow: var(--pr-shadow);
  backdrop-filter: blur(16px);
}

.nav-left {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-link {
  min-height: 36px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--pr-primary);
  font: inherit;
  font-size: 0.86rem;
  font-weight: 900;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.18s ease;
}

.nav-link:hover {
  background: var(--pr-primary-soft);
  border-color: var(--pr-border-strong);
  transform: translateY(-1px);
}

.nav-status {
  min-height: 34px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid var(--pr-border);
  color: #475569;
  font-size: 0.8rem;
  font-weight: 900;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pr-green);
}

.status-dot.failed {
  background: var(--pr-red);
}

.state-card {
  min-height: 280px;
  padding: 40px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  text-align: center;
  border-radius: 24px;
  background: var(--pr-card);
  border: 1px solid var(--pr-border);
  box-shadow: var(--pr-shadow);
}

.state-card h2 {
  margin: 0;
  font-size: 1.35rem;
}

.state-card p {
  margin: 0;
  color: var(--pr-slate);
}

.state-spinner {
  width: 34px;
  height: 34px;
  border: 4px solid #e0e7ff;
  border-top-color: var(--pr-primary);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.learning-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 370px;
  gap: 14px;
  align-items: start;
}

.tutorial-panel,
.side-card {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--pr-border);
  box-shadow: var(--pr-shadow);
  backdrop-filter: blur(16px);
}

.tutorial-panel {
  min-width: 0;
  overflow: hidden;
}

.tutorial-head {
  padding: 22px 24px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 18px;
  align-items: start;
  border-bottom: 1px solid var(--pr-border);
  background:
    radial-gradient(circle at 92% 0%, rgba(79, 70, 229, 0.08), transparent 32%),
    linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.tutorial-title {
  min-width: 0;
}

.section-kicker,
.side-head span {
  color: var(--pr-primary);
  font-size: 0.74rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.tutorial-title h1 {
  margin: 8px 0 8px;
  color: var(--pr-text);
  font-size: clamp(1.45rem, 2.3vw, 2.15rem);
  line-height: 1.18;
  letter-spacing: -0.04em;
}

.tutorial-title p {
  max-width: 900px;
  margin: 0;
  color: var(--pr-slate);
  line-height: 1.7;
  font-size: 0.94rem;
}

.tutorial-meta {
  display: grid;
  gap: 8px;
  justify-items: end;
}

.tutorial-meta span {
  min-height: 30px;
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid var(--pr-border);
  color: #475569;
  font-size: 0.78rem;
  font-weight: 800;
  white-space: nowrap;
}

.failure-card {
  margin: 20px;
  padding: 18px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 14px;
  border-radius: 18px;
  border: 1px solid #fca5a5;
  background: #fef2f2;
}

.failure-icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: #991b1b;
  background: #fee2e2;
  font-size: 24px;
}

.failure-card strong {
  display: block;
  margin-bottom: 6px;
  color: #991b1b;
  font-size: 1rem;
}

.failure-card p {
  margin: 0;
  color: #7f1d1d;
  line-height: 1.65;
}

.resource-content-card {
  padding: 18px;
}

.content-toolbar {
  min-height: 56px;
  padding: 12px 14px;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid var(--pr-border);
}

.content-toolbar span {
  display: block;
  margin-bottom: 3px;
  color: var(--pr-muted);
  font-size: 0.72rem;
  font-weight: 900;
}

.content-toolbar strong {
  color: var(--pr-text);
  font-size: 0.92rem;
}

.small-action {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--pr-border-strong);
  border-radius: 12px;
  background: #ffffff;
  color: var(--pr-primary);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 900;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    background 0.18s ease;
}

.small-action:hover {
  transform: translateY(-1px);
  background: var(--pr-primary-soft);
}

.resource-view {
  min-height: 600px;
  padding: 8px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid var(--pr-border);
}

.resource-view :deep(.markdown-view),
.resource-view :deep(.reading-view),
.resource-view :deep(.code-view),
.resource-view :deep(.mindmap-view),
.resource-view :deep(.ppt-view),
.resource-view :deep(.quiz-view) {
  max-width: none;
}

.agent-push-panel {
  position: sticky;
  top: 16px;
  display: grid;
  gap: 14px;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  padding-right: 2px;
  scrollbar-width: thin;
  scrollbar-color: rgba(79, 70, 229, 0.28) transparent;
}

.agent-push-panel::-webkit-scrollbar {
  width: 6px;
}

.agent-push-panel::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(79, 70, 229, 0.28);
}

.agent-push-panel::-webkit-scrollbar-track {
  background: transparent;
}

.side-card {
  padding: 18px;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.side-head strong {
  min-height: 26px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: var(--pr-primary-soft);
  color: var(--pr-primary-dark);
  font-size: 0.72rem;
  font-weight: 900;
  white-space: nowrap;
}

.resource-agent-icon {
  width: 58px;
  height: 58px;
  margin-bottom: 14px;
  display: grid;
  place-items: center;
  border-radius: 22px;
  color: #ffffff;
  font-size: 29px;
  background: linear-gradient(135deg, var(--pr-primary), var(--pr-blue));
  box-shadow: 0 16px 30px rgba(79, 70, 229, 0.18);
}

.resource-agent-icon.mindmap {
  background: linear-gradient(135deg, #7c3aed, #6366f1);
}

.resource-agent-icon.code {
  background: linear-gradient(135deg, #0f766e, #14b8a6);
}

.resource-agent-icon.ppt {
  background: linear-gradient(135deg, #ea580c, #f59e0b);
}

.resource-agent-icon.quiz {
  background: linear-gradient(135deg, #2563eb, #06b6d4);
}

.resource-agent-icon.reading {
  background: linear-gradient(135deg, #059669, #10b981);
}

.current-resource h2 {
  margin: 0 0 8px;
  color: var(--pr-text);
  font-size: 1.15rem;
  line-height: 1.35;
  letter-spacing: -0.03em;
}

.current-resource p,
.push-desc {
  margin: 0;
  color: var(--pr-slate);
  font-size: 0.86rem;
  line-height: 1.65;
}

.resource-info-grid {
  margin-top: 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.resource-info-grid div {
  padding: 11px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--pr-border);
}

.resource-info-grid label {
  display: block;
  margin-bottom: 4px;
  color: var(--pr-muted);
  font-size: 0.7rem;
  font-weight: 900;
}

.resource-info-grid strong {
  color: var(--pr-text);
  font-size: 0.82rem;
}

.agent-flow {
  margin-top: 16px;
  display: grid;
  gap: 8px;
}

.agent-item {
  position: relative;
  min-height: 64px;
  padding: 10px 48px 10px 10px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid var(--pr-border);
}

.agent-item.active {
  border-color: var(--pr-border-strong);
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
}

.agent-dot {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  color: var(--pr-primary);
  background: var(--pr-primary-soft);
  font-size: 18px;
}

.agent-item strong {
  display: block;
  color: var(--pr-text);
  font-size: 0.84rem;
  margin-bottom: 3px;
}

.agent-item span {
  display: block;
  color: var(--pr-slate);
  font-size: 0.74rem;
  line-height: 1.35;
}

.agent-item em {
  position: absolute;
  right: 10px;
  top: 10px;
  padding: 3px 7px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.68rem;
  font-style: normal;
  font-weight: 900;
}

.agent-item.active em {
  background: var(--pr-primary);
  color: #ffffff;
}

.push-action {
  width: 100%;
  min-height: 40px;
  margin-top: 14px;
  border: 0;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--pr-primary), var(--pr-blue));
  color: #ffffff;
  font: inherit;
  font-size: 0.86rem;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 0 12px 28px rgba(79, 70, 229, 0.2);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.push-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 34px rgba(79, 70, 229, 0.25);
}

.study-steps {
  display: grid;
  gap: 8px;
}

.study-steps div {
  padding: 10px;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid var(--pr-border);
}

.study-steps span {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: #ffffff;
  background: linear-gradient(135deg, var(--pr-primary), var(--pr-blue));
  font-size: 0.78rem;
  font-weight: 900;
}

.study-steps p {
  margin: 3px 0 0;
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.55;
  font-weight: 700;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1280px) {
  .learning-workspace {
    grid-template-columns: 1fr;
  }

  .agent-push-panel {
    position: static;
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }
}

@media (max-width: 760px) {
  .path-resource-detail-page {
    padding: 12px;
  }

  .compact-nav,
  .tutorial-head,
  .content-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .compact-nav {
    display: grid;
  }

  .nav-left {
    display: grid;
  }

  .nav-status {
    justify-content: center;
  }

  .tutorial-head {
    grid-template-columns: 1fr;
  }

  .tutorial-meta {
    justify-items: stretch;
  }

  .tutorial-meta span {
    justify-content: center;
  }

  .resource-info-grid {
    grid-template-columns: 1fr;
  }
}
</style>