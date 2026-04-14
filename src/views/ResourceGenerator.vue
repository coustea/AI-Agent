<template>
  <div class="agent-studio-container">
    <aside class="control-panel">
      <div class="panel-header">
        <div class="logo-box">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="header-titles">
          <h2>多智能体资源工坊</h2>
          <p>Multi-Agent Resource Studio</p>
        </div>
      </div>

      <div class="form-scroll-area">
        <el-form :model="taskForm" layout="vertical" class="studio-form">
          <div class="input-block">
            <label>学习课题 / 课程名 <span class="req">*</span></label>
            <el-input v-model="taskForm.course" placeholder="例如：计算机网络 TCP/IP" size="large" clearable />
          </div>

          <div class="input-block">
            <label>知识瓶颈 / 痛点盲区 <span class="req">*</span></label>
            <el-input
                v-model="taskForm.gap"
                type="textarea"
                :rows="4"
                placeholder="例如：对三次握手的状态转移过程理解模糊，总是记不住边界条件和异常处理。"
                resize="none"
            />
          </div>

          <div class="input-block">
            <label>资源生成偏好</label>
            <div class="preference-grid">
              <div
                  v-for="opt in needOptions" :key="opt.value"
                  class="pref-card"
                  :class="{ active: taskForm.need === opt.value }"
                  @click="taskForm.need = opt.value"
              >
                <div class="pref-title">{{ opt.label }}</div>
                <div class="pref-desc">{{ opt.desc }}</div>
                <div class="active-indicator" v-if="taskForm.need === opt.value"></div>
              </div>
            </div>
          </div>

          <div class="input-block">
            <label>自定义 Agent 指令 (选填)</label>
            <el-input v-model="taskForm.extra" placeholder="例如：尽量用通俗的比喻，结合前端开发场景" size="large" clearable />
          </div>
        </el-form>
      </div>

      <div class="panel-action">
        <button
            class="primary-btn"
            :disabled="isGenerating || !taskForm.course || !taskForm.gap"
            @click="startGeneration"
        >
          <span v-if="!isGenerating" class="btn-content"><el-icon><Monitor /></el-icon> 唤醒 Agent 集群并生成</span>
          <span v-else class="btn-content"><el-icon class="is-loading"><Loading /></el-icon> 智能体运转中...</span>
        </button>
      </div>
    </aside>

    <main class="workspace">
      <transition name="fade-slide" mode="out-in">

        <div v-if="stage === 'idle'" class="view-layer idle-view" key="idle">
          <div class="idle-graphic">
            <div class="pulse-ring"></div>
            <el-icon class="center-icon"><Position /></el-icon>
          </div>
          <h3>系统矩阵已就绪，等待调度指令</h3>
          <p class="idle-desc">输入学习目标后，Coordinator Agent 将进行意图识别与任务拆解<br/>驱动 6 大专职智能体并发构建全息学习资源。</p>
          <div class="agent-roster">
            <div class="roster-badge" v-for="agent in Object.values(agentMeta)" :key="agent.id">
              <el-icon><component :is="agent.icon" /></el-icon> {{ agent.role }}
            </div>
          </div>
        </div>

        <div v-else-if="stage === 'working'" class="view-layer working-view" key="working">
          <div class="working-top">
            <h3 class="monitor-title"><span class="live-dot"></span> 集群协同网络 (DAG) 实时监控</h3>
            <div class="coordinator-status">
              <el-icon><Guide /></el-icon>
              <span class="typewriter-text">{{ coordinatorMsg }}</span>
            </div>
          </div>

          <div class="dag-topology">
            <div v-for="(phase, idx) in dagPhases" :key="phase.name" class="topology-stage">
              <div class="stage-tag">STAGE 0{{ idx + 1 }} // {{ phase.label }}</div>
              <div class="stage-nodes">
                <div
                    v-for="agentId in phase.agents" :key="agentId"
                    class="white-node"
                    :class="agentStates[agentId]?.status"
                >
                  <div class="node-icon-box">
                    <el-icon v-if="agentStates[agentId]?.status === 'done'" class="text-green"><Select /></el-icon>
                    <el-icon v-else-if="agentStates[agentId]?.status === 'error'" class="text-red"><CloseBold /></el-icon>
                    <el-icon v-else-if="agentStates[agentId]?.status === 'active'" class="is-loading text-primary"><Loading /></el-icon>
                    <el-icon v-else><component :is="agentMeta[agentId].icon" /></el-icon>
                  </div>
                  <div class="node-text">
                    <div class="n-name">{{ agentMeta[agentId].role }}</div>
                    <div class="n-log">{{ agentStates[agentId]?.log }}</div>
                  </div>
                </div>
              </div>
              <div class="stage-arrow" v-if="idx < dagPhases.length - 1">
                <el-icon><ArrowDownBold /></el-icon>
              </div>
            </div>
          </div>

          <!-- 实时产出预览：每个 Agent 完成后立即展示结果 -->
          <div v-if="completedAgentIds.length > 0" class="live-results-section">
            <div class="live-results-header">
              <h3><el-icon class="text-green"><Select /></el-icon> 实时产出预览 <span>({{ completedAgentIds.length }}/{{ totalAgentCount }})</span></h3>
            </div>
            <el-tabs v-model="liveTab" class="modern-tabs">
              <el-tab-pane name="mindmap" v-if="results.mindmap?.success">
                <template #label><el-icon><Share /></el-icon> 知识图谱</template>
                <div class="res-card">
                  <el-alert title="知识拓扑结构生成完毕" type="success" :closable="false" show-icon style="margin-bottom:1rem;" />
                  <div class="code-wrapper">
                    <pre><code>{{ results.mindmap.agent_output }}</code></pre>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="content" v-if="results.content?.success">
                <template #label><el-icon><Document /></el-icon> 核心精讲</template>
                <div class="res-card markdown-body" v-html="parseMarkdown(results.content.content)"></div>
              </el-tab-pane>

              <el-tab-pane name="code" v-if="results.code?.success">
                <template #label><el-icon><Cpu /></el-icon> 实战案例</template>
                <div class="res-card">
                  <div class="lang-tag"><el-icon><Tools /></el-icon> 适配语言: <strong>{{ results.code.detected_language.toUpperCase() }}</strong></div>
                  <div class="markdown-body" v-html="parseMarkdown(results.code.content)"></div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="quiz" v-if="results.quiz?.success">
                <template #label><el-icon><Edit /></el-icon> 专项题库</template>
                <div class="quiz-masonry">
                  <div class="quiz-box" v-for="(q, i) in results.quiz.questions" :key="i">
                    <div class="q-top">
                      <span class="q-num">Q{{ Number(i) + 1 }}</span>
                      <span class="q-diff" :class="q.difficulty">{{ q.difficulty.toUpperCase() }}</span>
                      <span class="q-type">{{ q.question_type }}</span>
                    </div>
                    <div class="q-stem">{{ q.stem }}</div>
                    <div class="q-opts" v-if="q.options">
                      <div class="opt-row" v-for="(opt, oIdx) in q.options" :key="oIdx">{{ opt }}</div>
                    </div>
                    <details class="q-reveal">
                      <summary>解析与答案</summary>
                      <div class="q-answer-box">
                        <p class="ans-correct"><strong>正确答案：</strong>{{ q.answer }}</p>
                        <p class="ans-exp"><strong>深度解析：</strong>{{ q.explanation }}</p>
                      </div>
                    </details>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="reading" v-if="results.reading?.success">
                <template #label><el-icon><Collection /></el-icon> 拓展阅读</template>
                <div class="reading-masonry">
                  <div class="book-card" v-for="(book, i) in results.reading.recommendations" :key="i">
                    <div class="b-type">{{ book.type }}</div>
                    <h4 class="b-title">{{ book.title }}</h4>
                    <div class="b-author"><el-icon><User /></el-icon> {{ book.author_or_source }}</div>
                    <div class="b-abstract">{{ book.abstract }}</div>
                    <div class="b-relevance"><strong>💡 推荐理由：</strong>{{ book.relevance }}</div>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="image" v-if="results.image?.success">
                <template #label><el-icon><Monitor /></el-icon> 教学配图</template>
                <div class="res-card">
                  <div v-if="results.image.images?.length" class="image-grid">
                    <img
                      v-for="(url, i) in results.image.images"
                      :key="i"
                      :src="url"
                      alt="教学配图"
                      class="generated-image"
                    />
                  </div>
                  <div class="markdown-body" v-html="parseMarkdown(results.image.content)"></div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="video" v-if="results.video?.success">
                <template #label><el-icon><VideoPlay /></el-icon> 教学视频</template>
                <div class="res-card">
                  <div v-if="results.video.videos?.length" class="video-links">
                    <a
                      v-for="(url, i) in results.video.videos"
                      :key="i"
                      :href="url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="video-link"
                    >
                      视频资源 {{ Number(i) + 1 }}
                    </a>
                  </div>
                  <div class="markdown-body" v-html="parseMarkdown(results.video.content)"></div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>

          <div class="terminal-window">
            <div class="term-header">
              <div class="mac-dots"><span class="red"></span><span class="yellow"></span><span class="green"></span></div>
              <div class="term-title">System Log - Execution Trace</div>
            </div>
            <div class="term-body" ref="terminalBody">
              <div v-for="(log, idx) in systemLogs" :key="idx" class="term-line">
                <span class="t-time">[{{ log.time }}]</span>
                <span class="t-source" :class="log.source">{{ log.source }}</span>
                <span class="t-msg" :class="log.type">{{ log.msg }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="stage === 'done'" class="view-layer result-view" key="done">
          <div class="result-hero">
            <div class="hero-left">
              <h2>🎉 您的专属资源包已装载完毕</h2>
              <p>知识提取与资源构建成功，已沉淀至您的学习档案。</p>
            </div>
            <el-button class="reset-btn" @click="stage = 'idle'" :icon="RefreshRight">重置并发起新任务</el-button>
          </div>

          <div class="result-tabs-container">
            <el-tabs v-model="activeTab" class="modern-tabs">
              <el-tab-pane name="content" v-if="results.content?.success">
                <template #label><el-icon><Document /></el-icon> 核心精讲</template>
                <div class="res-card markdown-body" v-html="parseMarkdown(results.content.content)"></div>
              </el-tab-pane>

              <el-tab-pane name="mindmap" v-if="results.mindmap?.success">
                <template #label><el-icon><Share /></el-icon> 知识图谱</template>
                <div class="res-card">
                  <el-alert title="知识拓扑结构生成完毕" type="success" :closable="false" show-icon style="margin-bottom:1rem;" />
                  <div class="code-wrapper">
                    <pre><code>{{ results.mindmap.agent_output }}</code></pre>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="code" v-if="results.code?.success">
                <template #label><el-icon><Cpu /></el-icon> 实战案例</template>
                <div class="res-card">
                  <div class="lang-tag"><el-icon><Tools /></el-icon> 适配语言: <strong>{{ results.code.detected_language.toUpperCase() }}</strong></div>
                  <div class="markdown-body" v-html="parseMarkdown(results.code.content)"></div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="quiz" v-if="results.quiz?.success">
                <template #label><el-icon><Edit /></el-icon> 专项题库</template>
                <div class="quiz-masonry">
                  <div class="quiz-box" v-for="(q, i) in results.quiz.questions" :key="i">
                    <div class="q-top">
                      <span class="q-num">Q{{ Number(i) + 1 }}</span>
                      <span class="q-diff" :class="q.difficulty">{{ q.difficulty.toUpperCase() }}</span>
                      <span class="q-type">{{ q.question_type }}</span>
                    </div>
                    <div class="q-stem">{{ q.stem }}</div>
                    <div class="q-opts" v-if="q.options">
                      <div class="opt-row" v-for="(opt, oIdx) in q.options" :key="oIdx">{{ opt }}</div>
                    </div>
                    <details class="q-reveal">
                      <summary>解析与答案</summary>
                      <div class="q-answer-box">
                        <p class="ans-correct"><strong>正确答案：</strong>{{ q.answer }}</p>
                        <p class="ans-exp"><strong>深度解析：</strong>{{ q.explanation }}</p>
                      </div>
                    </details>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="reading" v-if="results.reading?.success">
                <template #label><el-icon><Collection /></el-icon> 拓展阅读</template>
                <div class="reading-masonry">
                  <div class="book-card" v-for="(book, i) in results.reading.recommendations" :key="i">
                    <div class="b-type">{{ book.type }}</div>
                    <h4 class="b-title">{{ book.title }}</h4>
                    <div class="b-author"><el-icon><User /></el-icon> {{ book.author_or_source }}</div>
                    <div class="b-abstract">{{ book.abstract }}</div>
                    <div class="b-relevance"><strong>💡 推荐理由：</strong>{{ book.relevance }}</div>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="image" v-if="results.image?.success">
                <template #label><el-icon><Monitor /></el-icon> 教学配图</template>
                <div class="res-card">
                  <div v-if="results.image.images?.length" class="image-grid">
                    <img
                      v-for="(url, i) in results.image.images"
                      :key="i"
                      :src="url"
                      alt="教学配图"
                      class="generated-image"
                    />
                  </div>
                  <div class="markdown-body" v-html="parseMarkdown(results.image.content)"></div>
                </div>
              </el-tab-pane>

              <el-tab-pane name="video" v-if="results.video?.success">
                <template #label><el-icon><VideoPlay /></el-icon> 教学视频</template>
                <div class="res-card">
                  <div v-if="results.video.videos?.length" class="video-links">
                    <a
                      v-for="(url, i) in results.video.videos"
                      :key="i"
                      :href="url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="video-link"
                    >
                      视频资源 {{ Number(i) + 1 }}
                    </a>
                  </div>
                  <div class="markdown-body" v-html="parseMarkdown(results.video.content)"></div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>

      </transition>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import 'github-markdown-css/github-markdown-light.css'
import {
  Cpu, Document, Edit, Collection, VideoPlay, Monitor, Position, Tools,
  Loading, Select, CloseBold, Share, User, Guide, ArrowDownBold, RefreshRight
} from '@element-plus/icons-vue'

// ======================= 数据定义 =======================
const stage = ref<'idle' | 'working' | 'done'>('idle')
const isGenerating = ref(false)

const taskForm = reactive({ course: '', gap: '', need: 'review', extra: '' })

const needOptions = [
  { value: 'exam', label: '考前突击', desc: '侧重考点与易错题分析' },
  { value: 'review', label: '课后复习', desc: '侧重知识图解与脉络梳理' },
  { value: 'deep', label: '深度探究', desc: '侧重底层原理与工程拓展' }
]

// ======================= 智能体与 DAG 配置 =======================
const dagPhases = [
  { name: 'foundation', label: '知识框架构建', agents: ['mindmap'] },
  { name: 'core', label: '核心资源生成', agents: ['content', 'code'] },
  { name: 'enrichment', label: '拓展资源丰富', agents: ['quiz', 'reading', 'image', 'video'] },
]

const agentMeta: Record<string, any> = {
  'mindmap': { id: 'mindmap', role: 'Mindmap Agent', icon: Share, desc: '构建核心知识拓扑图' },
  'content': { id: 'content', role: 'Content Agent', icon: Document, desc: '撰写深度知识精讲' },
  'code':    { id: 'code', role: 'Code Agent', icon: Cpu, desc: '编写可运行实操案例' },
  'quiz':    { id: 'quiz', role: 'Quiz Agent', icon: Edit, desc: '生成分层练习题库' },
  'reading': { id: 'reading', role: 'Reading Agent', icon: Collection, desc: '检索拓展阅读与论文' },
  'image':   { id: 'image', role: 'Image Agent', icon: Monitor, desc: '生成教学配图与图解资源' },
  'video':   { id: 'video', role: 'Video Agent', icon: VideoPlay, desc: '生成教学动画视频资源' }
}

// 代理实时状态
const agentStates = ref<Record<string, { status: 'wait'|'active'|'done'|'error', log: string }>>({})

// ======================= 监控与日志 =======================
const coordinatorMsg = ref('等待系统唤醒...')
interface LogEntry { time: string; source: string; msg: string; type: 'info'|'success'|'error' }
const systemLogs = ref<LogEntry[]>([])
const terminalBody = ref<HTMLElement | null>(null)

const pushLog = (source: string, msg: string, type: 'info'|'success'|'error' = 'info') => {
  const time = new Date().toLocaleTimeString([], { hour12: false })
  systemLogs.value.push({ time, source, msg, type })
  nextTick(() => {
    if (terminalBody.value) terminalBody.value.scrollTop = terminalBody.value.scrollHeight
  })
}

// ======================= 结果数据 =======================
const results = ref<Record<string, any>>({})
const activeTab = ref('content')
const liveTab = ref('mindmap')

// 已完成的 agent id 列表（实时更新）
const completedAgentIds = computed(() => {
  return Object.keys(results.value).filter(k => results.value[k]?.success)
})
const totalAgentCount = computed(() => Object.keys(agentMeta).length)

// ======================= 核心业务逻辑 =======================
const resetStates = () => {
  systemLogs.value = []
  results.value = {}
  coordinatorMsg.value = '系统初始化...'
  Object.keys(agentMeta).forEach(key => {
    agentStates.value[key] = { status: 'wait', log: '等待分配计算资源...' }
  })
}

const startGeneration = async () => {
  if (!taskForm.course || !taskForm.gap) return

  isGenerating.value = true
  stage.value = 'working'
  resetStates()
  pushLog('SYSTEM', 'Initiating Mult-Agent Workflow...', 'info')

  try {
    const token = localStorage.getItem('token') || ''
    const response = await fetch('/api/v1/ai/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        user_id: Number(localStorage.getItem('user_id') || 1),
        learning_task: { ...taskForm }
      })
    })

    if (!response.ok) {
      const errText = await response.text()
      throw new Error(errText || `HTTP ${response.status}`)
    }

    if (!response.body) throw new Error('流式响应不可用')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6))
            handleSSEEvent(data)
          } catch (e) {
            console.error('SSE JSON 解析错误:', e)
          }
        }
      }
    }
  } catch (err: any) {
    ElMessage.error(`请求异常: ${err.message}`)
    pushLog('SYSTEM', `连接中断: ${err.message}`, 'error')
    isGenerating.value = false
    stage.value = 'idle'
  }
}

// 解析 SSE 事件
const handleSSEEvent = (event: any) => {
  const { type, id, status, msg, log, error, data, message } = event

  if (type === 'coordinator') {
    coordinatorMsg.value = msg || status
    pushLog('COORDINATOR', msg, 'info')
  }
  else if (type === 'agent_start') {
    if (agentStates.value[id]) {
      agentStates.value[id].status = 'active'
      agentStates.value[id].log = '模型推理生成中...'
    }
    pushLog(id.toUpperCase(), 'Agent context loaded and execution started', 'info')
  }
  else if (type === 'agent_log') {
    if (agentStates.value[id]) {
      agentStates.value[id].log = log
    }
  }
  else if (type === 'agent_done') {
    if (agentStates.value[id]) {
      agentStates.value[id].status = 'done'
      agentStates.value[id].log = '内容生成完毕'
    }
    results.value[id] = data
    // 自动切换到最新完成的 tab
    liveTab.value = id
    pushLog(id.toUpperCase(), 'Generation task completed successfully', 'success')
  }
  else if (type === 'agent_error') {
    if (agentStates.value[id]) {
      agentStates.value[id].status = 'error'
      agentStates.value[id].log = `异常: ${error}`
    }
    pushLog(id.toUpperCase(), error, 'error')
  }
  else if (type === 'done') {
    pushLog('SYSTEM', message || 'All agent pipelines finished.', 'success')
    setTimeout(() => {
      isGenerating.value = false
      stage.value = 'done'
      determineInitialTab()
    }, 1200)
  }
}

// ======================= 辅助呈现逻辑 =======================
const parseMarkdown = (raw: string) => {
  if (!raw) return ''
  return marked.parse(raw)
}

const determineInitialTab = () => {
  const priority = ['content', 'mindmap', 'code', 'quiz', 'reading', 'image', 'video']
  for (const p of priority) {
    if (results.value[p] && results.value[p].success) {
      activeTab.value = p
      break
    }
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

/* 全局布局 - 白色主题 */
.agent-studio-container {
  display: flex;
  height: calc(100vh - 60px);
  background-color: #FFFFFF; /* 纯白背景 */
  font-family: 'Inter', system-ui, sans-serif;
  color: #0F172A;
  overflow: hidden;
}

/* ================== 左侧表单 ================== */
.control-panel {
  width: 400px;
  background: #FFFFFF;
  border-right: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  z-index: 10;
  box-shadow: 4px 0 15px rgba(0,0,0,0.02);
  flex-shrink: 0;
}

.panel-header {
  padding: 2rem 2rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  border-bottom: 1px solid #F8FAFC;
}
.logo-box {
  width: 44px; height: 44px;
  background: #EEF2FF; color: #4F46E5;
  border-radius: 12px; display: flex;
  align-items: center; justify-content: center;
  font-size: 1.5rem;
}
.header-titles h2 { margin: 0 0 4px 0; font-size: 1.2rem; font-weight: 700; color: #0F172A; }
.header-titles p { margin: 0; font-size: 0.75rem; color: #64748B; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.5px; }

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.generated-image {
  width: 100%;
  border-radius: 14px;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
  object-fit: cover;
}

.video-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.video-link {
  display: inline-flex;
  align-items: center;
  padding: 0.65rem 0.95rem;
  border-radius: 999px;
  background: #EEF2FF;
  color: #3730A3;
  font-weight: 600;
  text-decoration: none;
}

.form-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem;
}
.studio-form { display: flex; flex-direction: column; gap: 1.75rem; }
.input-block label { display: block; font-size: 0.9rem; font-weight: 600; color: #1E293B; margin-bottom: 0.5rem; }
.req { color: #EF4444; margin-left: 2px; }
:deep(.el-input__wrapper), :deep(.el-textarea__inner) {
  background-color: #F8FAFC; border-color: #E2E8F0; box-shadow: none; transition: all 0.2s;
}
:deep(.el-input__wrapper.is-focus), :deep(.el-textarea__inner:focus) {
  background-color: #FFFFFF; border-color: #4F46E5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1);
}

.preference-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.pref-card {
  position: relative; padding: 1rem 1.25rem;
  border: 1px solid #E2E8F0; border-radius: 10px;
  background: #FFFFFF; cursor: pointer; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.pref-card:hover { border-color: #CBD5E1; background: #F8FAFC; }
.pref-card.active { border-color: #4F46E5; background: #EEF2FF; }
.pref-title { font-size: 0.9rem; font-weight: 600; color: #1E293B; margin-bottom: 4px; transition: color 0.2s; }
.pref-card.active .pref-title { color: #4F46E5; }
.pref-desc { font-size: 0.75rem; color: #64748B; }
.active-indicator {
  position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: #4F46E5;
}

.panel-action { padding: 1.5rem 2rem 2rem; background: #FFFFFF; border-top: 1px solid #F8FAFC; }
.primary-btn {
  width: 100%; height: 52px;
  background: #4F46E5; color: #FFFFFF;
  border: none; border-radius: 12px;
  font-size: 1rem; font-weight: 600;
  cursor: pointer; transition: all 0.3s;
  display: flex; align-items: center; justify-content: center;
}
.primary-btn:hover:not(:disabled) { background: #4338CA; transform: translateY(-2px); box-shadow: 0 10px 20px rgba(79,70,229,0.2); }
.primary-btn:disabled { background: #E2E8F0; color: #94A3B8; cursor: not-allowed; }
.btn-content { display: flex; align-items: center; gap: 8px; }

/* ================== 右侧动态空间 ================== */
.workspace {
  flex: 1;
  position: relative;
  background-color: #F8FAFC; /* 浅色背景区分工作区与表单 */
  background-image: radial-gradient(#E2E8F0 1px, transparent 1px);
  background-size: 24px 24px;
}
.view-layer { position: absolute; inset: 0; display: flex; flex-direction: column; overflow-y: auto; padding: 3rem 4rem; }

/* 1. 待机状态 */
.idle-view { align-items: center; justify-content: center; text-align: center; }
.idle-graphic { position: relative; width: 120px; height: 120px; display: flex; align-items: center; justify-content: center; margin-bottom: 2rem; }
.pulse-ring { position: absolute; inset: 0; border-radius: 50%; border: 2px dashed #CBD5E1; animation: spin-slow 10s linear infinite; }
.center-icon { font-size: 3.5rem; color: #94A3B8; }
.idle-view h3 { font-size: 1.4rem; color: #1E293B; margin: 0 0 1rem 0; font-weight: 700; }
.idle-desc { font-size: 0.95rem; color: #64748B; line-height: 1.6; margin-bottom: 3rem; }
.agent-roster { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; max-width: 600px; }
.roster-badge { display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px; font-size: 0.8rem; font-weight: 600; color: #475569; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }

/* 2. 工作状态 (白色明亮监控) */
.working-top { margin-bottom: 3rem; }
.monitor-title { font-size: 1.25rem; font-weight: 700; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 10px; color: #0F172A; }
.live-dot { display: block; width: 10px; height: 10px; background: #10B981; border-radius: 50%; box-shadow: 0 0 0 0 rgba(16,185,129,0.4); animation: pulse-green 2s infinite; }
.coordinator-status { display: flex; align-items: center; gap: 12px; background: #EEF2FF; border-left: 4px solid #4F46E5; padding: 1rem 1.5rem; border-radius: 8px; color: #3730A3; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; border: 1px solid #C7D2FE; border-left-width: 4px; }

.dag-topology { display: flex; flex-direction: column; align-items: center; gap: 1rem; margin-bottom: 4rem; }
.topology-stage { display: flex; flex-direction: column; align-items: center; width: 100%; max-width: 700px; }
.stage-tag { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #475569; background: #F1F5F9; padding: 4px 16px; border-radius: 20px; margin-bottom: 1.5rem; font-weight: 700; border: 1px solid #E2E8F0; }
.stage-nodes { display: flex; gap: 1.5rem; flex-wrap: wrap; justify-content: center; }
.stage-arrow { margin-top: 1.5rem; color: #94A3B8; font-size: 1.5rem; animation: float-down 2s infinite; }

.white-node { display: flex; align-items: center; gap: 1rem; width: 240px; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 1rem 1.25rem; border-radius: 12px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
.white-node.wait { opacity: 0.5; border-style: dashed; background: #F8FAFC; box-shadow: none; }
.white-node.active { border-color: #4F46E5; background: #EEF2FF; transform: scale(1.02); box-shadow: 0 10px 20px rgba(79,70,229,0.1); }
.white-node.done { border-color: #10B981; background: #F0FDF4; }
.white-node.error { border-color: #EF4444; background: #FEF2F2; }

.node-icon-box { font-size: 1.4rem; color: #64748B; background: #F1F5F9; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border-radius: 8px; flex-shrink: 0; }
.active .node-icon-box { background: #FFFFFF; color: #4F46E5; }
.done .node-icon-box { background: #DCFCE7; color: #10B981; }
.error .node-icon-box { background: #FEE2E2; color: #EF4444; }

.node-text { display: flex; flex-direction: column; overflow: hidden; }
.n-name { font-size: 0.85rem; font-weight: 700; color: #1E293B; margin-bottom: 4px; }
.n-log { font-size: 0.7rem; color: #64748B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-family: 'JetBrains Mono', monospace; }
.active .n-log { color: #4F46E5; }
.done .n-log { color: #10B981; }

.text-primary { color: #4F46E5; }
.text-green { color: #10B981; }
.text-red { color: #EF4444; }

/* 终端日志 (明亮白底) */
.live-results-section { margin-top: 2rem; background: #FFFFFF; border: 1px solid #BBF7D0; border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.08); }
.live-results-header { margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #E2E8F0; }
.live-results-header h3 { margin: 0; font-size: 1.1rem; color: #059669; display: flex; align-items: center; gap: 8px; }
.live-results-header h3 span { font-size: 0.85rem; color: #64748B; font-weight: 400; }

.terminal-window { background: #FFFFFF; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }
.term-header { background: #F8FAFC; padding: 8px 16px; display: flex; align-items: center; gap: 1rem; border-bottom: 1px solid #E2E8F0; }
.mac-dots { display: flex; gap: 6px; }
.mac-dots span { width: 10px; height: 10px; border-radius: 50%; }
.mac-dots .red { background: #EF4444; } .mac-dots .yellow { background: #F59E0B; } .mac-dots .green { background: #10B981; }
.term-title { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; flex: 1; text-align: center; font-weight: 600; }
.term-body { height: 260px; padding: 1rem; overflow-y: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; line-height: 1.6; color: #334155; }
.term-line { display: flex; gap: 1rem; margin-bottom: 4px; word-break: break-all; }
.t-time { color: #94A3B8; flex-shrink: 0; }
.t-source { color: #8B5CF6; width: 100px; flex-shrink: 0; font-weight: 700; }
.t-source.SYSTEM { color: #0284C7; }
.t-source.COORDINATOR { color: #DB2777; }
.t-msg { color: #1E293B; }
.t-msg.success { color: #059669; }
.t-msg.error { color: #DC2626; }

/* 3. 结果状态 (清爽明亮) */
.result-view { background: #FFFFFF; padding: 3rem 4rem; }
.result-hero { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 2.5rem; border-bottom: 1px solid #F1F5F9; padding-bottom: 1.5rem; }
.hero-left h2 { margin: 0 0 8px 0; font-size: 1.8rem; color: #0F172A; font-weight: 800; }
.hero-left p { margin: 0; color: #64748B; font-size: 1rem; }

.reset-btn { border-radius: 8px; font-weight: 600; color: #4F46E5; border-color: #C7D2FE; background: #EEF2FF; }
.reset-btn:hover { background: #E0E7FF; border-color: #A5B4FC; }

.modern-tabs :deep(.el-tabs__nav-wrap::after) { background-color: #E2E8F0; height: 1px; }
.modern-tabs :deep(.el-tabs__item) { font-size: 1rem; color: #64748B; padding: 0 20px; height: 48px; line-height: 48px; }
.modern-tabs :deep(.el-tabs__item.is-active) { color: #4F46E5; font-weight: 700; }
.modern-tabs :deep(.el-tabs__active-bar) { background-color: #4F46E5; height: 3px; border-radius: 3px 3px 0 0; }

.res-card { padding: 2rem 0; }
.lang-tag { display: inline-flex; align-items: center; gap: 8px; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 6px 16px; border-radius: 20px; font-size: 0.85rem; color: #334155; margin-bottom: 1.5rem; }
.code-wrapper { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; overflow-x: auto; }
.code-wrapper pre { margin: 0; color: #1E293B; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; line-height: 1.6; }

.quiz-masonry { display: grid; gap: 1.5rem; padding: 1.5rem 0; }
.quiz-box { border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; background: #FFFFFF; transition: box-shadow 0.2s; }
.quiz-box:hover { box-shadow: 0 10px 25px rgba(0,0,0,0.03); }
.q-top { display: flex; gap: 8px; margin-bottom: 1rem; align-items: center; }
.q-num { font-weight: 800; font-size: 1.1rem; color: #0F172A; margin-right: 4px; }
.q-diff, .q-type { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; }
.q-diff.basic { background: #ECFDF5; color: #047857; }
.q-diff.intermediate { background: #FFFBEB; color: #B45309; }
.q-diff.challenge { background: #FEF2F2; color: #B91C1C; }
.q-type { background: #F1F5F9; color: #475569; }
.q-stem { font-size: 1.05rem; font-weight: 600; color: #1E293B; line-height: 1.6; margin-bottom: 1.25rem; }
.q-opts { display: flex; flex-direction: column; gap: 10px; margin-bottom: 1.5rem; }
.opt-row { padding: 12px 16px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.95rem; color: #334155; }
.q-reveal { background: #EEF2FF; border-radius: 8px; overflow: hidden; border: 1px solid #E0E7FF; }
.q-reveal summary { padding: 12px 16px; cursor: pointer; font-weight: 600; color: #4F46E5; font-size: 0.9rem; outline: none; }
.q-answer-box { padding: 0 16px 16px; font-size: 0.9rem; color: #312E81; line-height: 1.6; }
.ans-correct { color: #047857; margin: 0 0 8px; }
.ans-exp { margin: 0; }

.reading-masonry { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; padding: 1.5rem 0; }
.book-card { border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.5rem; display: flex; flex-direction: column; background: #FFFFFF; transition: transform 0.2s; }
.book-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.04); }
.b-type { font-size: 0.75rem; font-weight: 700; color: #4F46E5; text-transform: uppercase; margin-bottom: 0.75rem; letter-spacing: 0.5px; }
.b-title { margin: 0 0 10px 0; font-size: 1.1rem; color: #0F172A; line-height: 1.4; }
.b-author { font-size: 0.85rem; color: #64748B; margin-bottom: 1rem; display: flex; align-items: center; gap: 6px; }
.b-abstract { font-size: 0.9rem; color: #475569; line-height: 1.6; flex: 1; margin-bottom: 1.25rem; }
.b-relevance { font-size: 0.85rem; background: #F8FAFC; padding: 12px; border-radius: 8px; color: #334155; line-height: 1.5; border-left: 3px solid #10B981; }

/* Markdown 样式 */
:deep(.markdown-body) { font-family: 'Inter', sans-serif; color: #1E293B; }
:deep(.markdown-body h2) { font-size: 1.5rem; border-bottom: 1px solid #E2E8F0; padding-bottom: 0.75rem; margin-top: 1.5rem; color: #0F172A; }
:deep(.markdown-body h3) { font-size: 1.2rem; margin-top: 1.25rem; color: #1E293B; }
:deep(.markdown-body p) { line-height: 1.8; font-size: 1rem; color: #334155; }
:deep(.markdown-body pre) { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-family: 'JetBrains Mono', monospace; padding: 1.25rem; color: #1E293B; }

/* 动画定义 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
.fade-slide-enter-from { opacity: 0; transform: translateY(15px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-15px); }

@keyframes spin-slow { 100% { transform: rotate(360deg); } }
@keyframes pulse-green { 70% { box-shadow: 0 0 0 8px rgba(16,185,129,0); } 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0); } }
@keyframes float-down { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(6px); } }

/* 滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
</style>
