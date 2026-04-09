<template>
  <div class="tutor-dashboard">
    <header class="dashboard-header glass-effect">
      <div class="header-brand">
        <div class="logo-box">
          <el-icon><Cpu /></el-icon>
        </div>
        <div>
          <h2 class="title">全息智能辅导与动态画像中枢</h2>
          <p class="subtitle">多智能体协同 · 随学随新 · 多模态生成</p>
        </div>
      </div>
      <div class="mode-toggle">
        <el-radio-group v-model="chatMode" size="large">
          <el-radio-button label="standard">
            <div class="toggle-content">
              <el-icon><ChatLineRound /></el-icon>
              <span>图文交互模式</span>
            </div>
          </el-radio-button>
          <el-radio-button label="digital_human">
            <div class="toggle-content">
              <el-icon><Avatar /></el-icon>
              <span>数字人互动模式</span>
            </div>
          </el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <main class="dashboard-main">
      <!-- 左侧：会话列表 -->
      <aside class="session-sidebar glass-effect" :class="{ collapsed: sessionSidebarCollapsed }">
        <div class="session-sidebar-header">
          <el-button link @click="sessionSidebarCollapsed = !sessionSidebarCollapsed">
            <el-icon><Fold /></el-icon>
          </el-button>
          <el-button v-if="!sessionSidebarCollapsed" type="primary" size="small" @click="newSession" :icon="Plus">新对话</el-button>
        </div>
        <div v-if="!sessionSidebarCollapsed" class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            :class="['session-item', { active: s.id === currentSessionId }]"
            @click="switchSession(s.id)"
          >
            <span class="session-title">{{ s.title }}</span>
            <el-button link size="small" @click.stop="archiveSession(s.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty">暂无对话</div>
        </div>
      </aside>

      <!-- 中央：聊天主界面 -->
      <section class="chat-container glass-effect" :class="{ 'has-digital-human': chatMode === 'digital_human' }">

        <!-- 数字人展示舞台 -->
        <div v-if="chatMode === 'digital_human'" class="digital-human-stage">
          <div class="hologram-effect"></div>
          <div class="avatar-ring" :class="{ 'is-speaking': isAIThinking || isSpeaking }">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed=AIAssistant&backgroundColor=6366F1&textureChance=50" alt="Digital Human Avatar" class="bot-avatar-img"/>
          </div>
          <div class="speech-wave" v-if="isAIThinking || isSpeaking">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
          <div class="status-badge">{{ (isAIThinking || isSpeaking) ? '正在多模态解答中...' : '倾听就绪' }}</div>
        </div>

        <div class="chat-viewport" ref="chatScroll">
          <div class="welcome-banner" v-if="messages.length === 0">
            <h3>您好！我是您的多模态私人导师。</h3>
            <p>我们不仅可以通过<strong>文字、图片、文档</strong>进行探讨，我还会通过我们的对话<strong>自动提取并更新您的学习画像</strong>，为您提供量身定制的解答。</p>
          </div>

          <div v-for="msg in messages" :key="msg.id" :class="['message-row', msg.role]">
            <div class="msg-avatar">
              <el-avatar v-if="msg.role === 'ai'" :icon="Service" class="ai-av" :size="38" />
              <el-avatar v-else :icon="UserFilled" class="user-av" :size="38" />
            </div>

            <div class="bubble-wrapper">
              <div class="msg-meta">
                <span class="sender">{{ msg.role === 'ai' ? 'AI 导师' : '您' }}</span>
                <span class="time">{{ msg.time }}</span>
              </div>
              <div class="bubble markdown-body" v-html="renderMarkdown(msg.content)"></div>
              <div v-if="msg.attachments && msg.attachments.length > 0" class="msg-attachments">
                <a v-for="att in msg.attachments" :key="att.url" :href="att.url" target="_blank" class="attachment-link">
                  <el-icon v-if="att.type === 'image'"><Picture /></el-icon>
                  <el-icon v-else><Document /></el-icon>
                  <span>{{ att.name }}</span>
                </a>
              </div>
              <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="msg-tool-calls">
                <div class="tool-call-header">
                  <el-icon><Cpu /></el-icon>
                  <span>工具调用 ({{ msg.toolCalls.length }})</span>
                </div>
                <div v-for="(tc, idx) in msg.toolCalls" :key="idx" class="tool-call-item">
                  <span class="tool-name">{{ tc.tool }}</span>
                  <span class="tool-status" :class="tc.status">{{ tc.status === 'success' ? '成功' : '失败' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isAIThinking" class="message-row ai thinking-row">
            <div class="msg-avatar"><el-avatar :icon="Service" class="ai-av" :size="38" /></div>
            <div class="thinking-bubble">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在分析知识图谱、拟合您的学习画像并生成解答...</span>
            </div>
          </div>
        </div>

        <div class="input-panel">
          <!-- 附件预览 -->
          <div v-if="pendingFiles.length > 0" class="attachments-preview">
            <div v-for="(f, idx) in pendingFiles" :key="idx" class="attachment-chip">
              <el-icon v-if="f.fileType === 'image'"><Picture /></el-icon>
              <el-icon v-else><Document /></el-icon>
              <span class="attachment-name">{{ f.name }}</span>
              <el-button link size="small" @click="removeAttachment(idx)"><el-icon><Close /></el-icon></el-button>
            </div>
          </div>
          <div class="toolbar">
            <el-tooltip content="上传文档解析" placement="top">
              <el-button link :icon="Document" @click="triggerDocUpload" :loading="uploadingFile">文档</el-button>
            </el-tooltip>
            <el-tooltip content="上传截图提问" placement="top">
              <el-button link :icon="Picture" @click="triggerImgUpload" :loading="uploadingFile">截图</el-button>
            </el-tooltip>
            <el-tooltip content="语音输入" placement="top">
              <el-button link :icon="Microphone" :class="{ 'mic-active': isRecording }" @click="toggleRecord">语音</el-button>
            </el-tooltip>
            <span class="shortcut-hint">按 Enter 发送，Shift + Enter 换行</span>
          </div>
          <div class="input-wrapper">
            <textarea
              v-model="userInput"
              placeholder="您可以直接问我：'这段代码为什么报错？' 或 '我准备考研，最近看树的遍历很吃力'..."
              @keydown.enter.exact.prevent="handleSend"
            ></textarea>
            <button class="send-btn" :disabled="(!userInput.trim() && pendingFiles.length === 0) || isAIThinking" @click="handleSend">
              <el-icon><Promotion /></el-icon>
            </button>
          </div>
        </div>

        <!-- 隐藏文件输入 -->
        <input ref="docInput" type="file" accept=".pdf,.doc,.docx,.txt" style="display:none" @change="onFileSelected($event, 'document')" />
        <input ref="imgInput" type="file" accept=".png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onFileSelected($event, 'image')" />
      </section>

      <!-- 右侧：动态画像面板 -->
      <aside class="profile-sidebar glass-effect">
        <div class="sidebar-header">
          <h3><el-icon><DataAnalysis /></el-icon> 动态学习画像</h3>
          <el-tag size="small" type="success" effect="dark" class="sync-tag" v-if="profileUpdated">已更新</el-tag>
        </div>
        <p class="sidebar-desc">通过多智能体在自然对话中隐式抽取的特征，实现随学随新。</p>

        <div class="dimensions-grid">
          <div class="dim-card" v-for="dim in profileDimensions" :key="dim.key">
            <div class="dim-top">
              <span class="dim-name">{{ dim.name }}</span>
              <span class="dim-score" :style="{ color: dim.color }">{{ dim.score ?? '--' }}</span>
            </div>
            <el-progress :percentage="dim.score ?? 0" :color="dim.color" :show-text="false" :stroke-width="8" />
            <div class="dim-desc">{{ dim.desc }}</div>
          </div>
        </div>

        <div class="tags-section">
          <h4>智能提取标签</h4>
          <div class="tags-container">
            <el-tag
              v-for="tag in extractedTags"
              :key="tag"
              class="extracted-tag"
              effect="light"
              type="primary"
              round
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>

        <div class="ai-insight">
          <div class="insight-icon"><el-icon><MagicStick /></el-icon></div>
          <div class="insight-content">
            <h4>辅导策略自动调整</h4>
            <p>{{ tutorStrategy }}</p>
          </div>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import {
  ChatLineRound, Avatar, Cpu, Service, UserFilled, Loading,
  Promotion, Picture, Microphone, Document,
  DataAnalysis, MagicStick, Fold, Plus, Delete, Close
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import 'github-markdown-css/github-markdown-light.css'
import {
  streamChat, getProfile, uploadFile,
  getSessions, createSession, deleteSession, getChatHistory,
  type ProfileData, type ChatSession
} from '@/api/ai'

// ==========================================
// 维度定义（8 维匹配后端 ProfileExtraction）
// ==========================================
const DIMENSION_MAP = [
  { key: 'knowledge_level', name: '知识基础', color: '#6366F1', defaultDesc: '等待对话中自动分析...' },
  { key: 'cognitive_style', name: '认知风格', color: '#10B981', defaultDesc: '等待对话中自动分析...' },
  { key: 'error_pattern', name: '易错倾向', color: '#F59E0B', defaultDesc: '等待对话中自动分析...' },
  { key: 'learning_goal', name: '学习目标', color: '#8B5CF6', defaultDesc: '等待对话中自动分析...' },
  { key: 'learning_history', name: '学习历史', color: '#EC4899', defaultDesc: '等待对话中自动分析...' },
  { key: 'interest_preference', name: '兴趣偏好', color: '#3B82F6', defaultDesc: '等待对话中自动分析...' },
  { key: 'learning_pace', name: '学习节奏', color: '#14B8A6', defaultDesc: '等待对话中自动分析...' },
  { key: 'cognitive_level', name: '认知水平', color: '#F97316', defaultDesc: '等待对话中自动分析...' },
] as const

// ==========================================
// 状态
// ==========================================
const chatMode = ref('standard')
const userInput = ref('')
const isAIThinking = ref(false)
const isSpeaking = ref(false)
const isRecording = ref(false)
const chatScroll = ref<HTMLElement | null>(null)
const profileUpdated = ref(false)
const uploadingFile = ref(false)

// 会话管理
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | undefined>(undefined)
const sessionSidebarCollapsed = ref(false)

// 文件上传
const docInput = ref<HTMLInputElement | null>(null)
const imgInput = ref<HTMLInputElement | null>(null)
interface PendingFile { url: string; fileType: string; name: string }
const pendingFiles = ref<PendingFile[]>([])

// 聊天消息
interface Attachment { url: string; type: string; name: string }
interface ToolCall { tool: string; args: Record<string, unknown> | string; result: string; status: string }
interface ChatMsg { id: number; role: 'user' | 'ai'; content: string; time: string; attachments?: Attachment[] | null; toolCalls?: ToolCall[] | null }
const messages = ref<ChatMsg[]>([])

// 画像
interface ProfileDimension {
  readonly key: string
  readonly name: string
  readonly color: string
  readonly defaultDesc: string
  score: number | null
  desc: string
}

const profileDimensions = ref<ProfileDimension[]>(
  DIMENSION_MAP.map(d => ({ ...d, score: null, desc: d.defaultDesc }))
)
const extractedTags = ref<string[]>([])
const tutorStrategy = ref('开始对话后，系统将自动分析您的学习特征并调整辅导策略。')

// 流式控制器
let abortController: AbortController | null = null
// 画像轮询计时器
let profilePollTimers: ReturnType<typeof setTimeout>[] = []

// ==========================================
// 工具函数
// ==========================================
const renderMarkdown = (text: string) => marked.parse(text)

const scrollToBottom = () => {
  nextTick(() => {
    if (chatScroll.value) {
      chatScroll.value.scrollTop = chatScroll.value.scrollHeight
    }
  })
}

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

// ==========================================
// 画像加载与轮询
// ==========================================
const fetchProfile = async () => {
  try {
    const res = await getProfile()
    const data = res.data.data
    if (!data) return

    let changed = false
    for (const dim of profileDimensions.value) {
      const desc = data[dim.key as keyof ProfileData] as string | null
      const score = data[`${dim.key}_score` as keyof ProfileData] as number | null
      if (desc && desc !== dim.desc) {
        dim.desc = desc
        changed = true
      }
      if (score != null && score !== dim.score) {
        dim.score = score
        changed = true
      }
    }

    if (data.profile_summary) {
      tutorStrategy.value = data.profile_summary
    }

    // 从非空维度描述中提取标签
    const tags = profileDimensions.value
      .filter(d => d.score != null && d.desc && d.desc !== d.defaultDesc)
      .map(d => d.name)
    if (tags.length > 0) {
      extractedTags.value = tags
    }

    if (changed) {
      profileUpdated.value = true
      setTimeout(() => { profileUpdated.value = false }, 4000)
    }
  } catch {
    // 静默处理，画像轮询失败不影响聊天
  }
}

const scheduleProfilePoll = () => {
  // 清除之前的计时器
  profilePollTimers.forEach(t => clearTimeout(t))
  profilePollTimers = []

  const delays = [2000, 5000, 10000]
  delays.forEach((delay) => {
    const timer = setTimeout(() => fetchProfile(), delay)
    profilePollTimers.push(timer)
  })
}

// ==========================================
// 会话管理
// ==========================================
const loadSessions = async () => {
  try {
    const res = await getSessions()
    sessions.value = res.data.data || []
  } catch {
    sessions.value = []
  }
}

const newSession = async () => {
  try {
    const res = await createSession()
    const session = res.data.data
    sessions.value.unshift({ id: session.id, title: session.title, updated_at: new Date().toISOString() })
    await switchSession(session.id)
  } catch {
    // 静默处理
  }
}

const switchSession = async (sessionId: string) => {
  currentSessionId.value = sessionId
  messages.value = []

  try {
    const res = await getChatHistory(sessionId)
    const history = res.data.data || []
    messages.value = history.map((msg, i) => ({
      id: Date.now() + i,
      role: msg.role === 'assistant' ? 'ai' as const : msg.role as 'user' | 'ai',
      content: msg.content,
      time: msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
      attachments: msg.attachments || null,
      toolCalls: msg.tool_calls || null,
    }))
  } catch {
    // 加载历史失败时保持空消息
  }
  scrollToBottom()
}

const archiveSession = async (sessionId: string) => {
  try {
    await deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = undefined
      messages.value = []
      if (sessions.value.length > 0) {
        await switchSession(sessions.value[0]!.id)
      }
    }
  } catch {
    // 静默处理
  }
}

// ==========================================
// 文件上传
// ==========================================
const triggerDocUpload = () => docInput.value?.click()
const triggerImgUpload = () => imgInput.value?.click()

const onFileSelected = async (event: Event, _expectedType: string) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadingFile.value = true
  try {
    const res = await uploadFile(file)
    const data = res.data.data
    pendingFiles.value.push({
      url: data.url,
      fileType: data.file_type,
      name: data.original_name,
    })
  } catch {
    // 上传失败时静默处理
  } finally {
    uploadingFile.value = false
    input.value = '' // 重置以允许重复选择同一文件
  }
}

const removeAttachment = (idx: number) => {
  pendingFiles.value.splice(idx, 1)
}

// ==========================================
// 发送消息（SSE 流式）
// ==========================================
const handleSend = async () => {
  const text = userInput.value.trim()
  const hasFiles = pendingFiles.value.length > 0
  if ((!text && !hasFiles) || isAIThinking.value) return

  // 确保有活跃会话
  if (!currentSessionId.value) {
    try {
      const res = await createSession()
      const session = res.data.data
      currentSessionId.value = session.id
      sessions.value.unshift({ id: session.id, title: session.title, updated_at: new Date().toISOString() })
    } catch {
      // 如果创建失败，使用 undefined（后端会用 global session）
    }
  }

  // 用户消息
  const displayText = text || (hasFiles ? `[附件提问] ${pendingFiles.value.map(f => f.name).join(', ')}` : '')
  if (displayText) {
    messages.value.push({ id: Date.now(), role: 'user', content: displayText, time: now() })
  }

  userInput.value = ''
  isAIThinking.value = true
  profileUpdated.value = false
  scrollToBottom()

  // 收集附件信息
  const imageUrl = pendingFiles.value.find(f => f.fileType === 'image')?.url
  const fileUrls = pendingFiles.value.filter(f => f.fileType === 'document').map(f => f.url)
  pendingFiles.value = []

  // AI 消息占位
  const aiMsgId = Date.now() + 1
  messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })

  // 发起 SSE 流式请求
  abortController = streamChat(
    {
      message: text || '请分析我上传的文件内容',
      session_id: currentSessionId.value,
      image_url: imageUrl,
      file_urls: fileUrls.length > 0 ? fileUrls : undefined,
    },
    // onChunk
    (chunk) => {
      const aiMsg = messages.value.find(m => m.id === aiMsgId)
      if (aiMsg) {
        aiMsg.content += chunk
        scrollToBottom()
      }
    },
    // onDone
    () => {
      isAIThinking.value = false
      isSpeaking.value = chatMode.value === 'digital_human'
      if (isSpeaking.value) {
        setTimeout(() => { isSpeaking.value = false }, 3000)
      }
      // 触发画像轮询
      scheduleProfilePoll()
      abortController = null
    },
    // onError
    (err) => {
      const aiMsg = messages.value.find(m => m.id === aiMsgId)
      if (aiMsg && !aiMsg.content) {
        aiMsg.content = `抱歉，回复生成失败: ${err.message}`
      }
      isAIThinking.value = false
      abortController = null
    },
  )
}

// ==========================================
// 语音输入（保留占位逻辑）
// ==========================================
const toggleRecord = () => {
  isRecording.value = !isRecording.value
  if (!isRecording.value && userInput.value === '') {
    userInput.value = "我其实对动态规划的转移方程一直理解不透，你能用图形化的方式给我讲讲吗？"
  }
}

// ==========================================
// 生命周期
// ==========================================
onMounted(async () => {
  await loadSessions()
  // 如果有会话，自动选择最近的
  if (sessions.value.length > 0) {
    await switchSession(sessions.value[0]!.id)
  }
  // 加载画像
  await fetchProfile()
})

onBeforeUnmount(() => {
  // 清理流式请求
  abortController?.abort()
  // 清理轮询计时器
  profilePollTimers.forEach(t => clearTimeout(t))
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Fira+Sans:wght@400;500;600;700&display=swap');

.tutor-dashboard {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 80px);
  padding: 1.5rem 2rem;
  background: #F3F4F6;
  font-family: 'Fira Sans', sans-serif;
  gap: 1.5rem;
}

.glass-effect {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.05);
  border-radius: 24px;
}

/* Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  flex-shrink: 0;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo-box {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #6366F1, #818CF8);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
}

.title { margin: 0 0 0.25rem 0; font-size: 1.25rem; color: #312E81; }
.subtitle { margin: 0; font-size: 0.85rem; color: #6B7280; }
.toggle-content { display: flex; align-items: center; gap: 0.5rem; font-weight: 500; }

/* Main Layout */
.dashboard-main {
  display: flex;
  flex: 1;
  gap: 1.5rem;
  overflow: hidden;
}

/* Session Sidebar */
.session-sidebar {
  width: 220px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: all 0.3s ease;
  flex-shrink: 0;
}
.session-sidebar.collapsed {
  width: 48px;
  padding: 0.5rem;
  align-items: center;
}

.session-sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
  flex: 1;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 0.85rem;
}
.session-item:hover { background: #F3F4F6; }
.session-item.active { background: #EEF2FF; color: #4F46E5; font-weight: 600; }
.session-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.session-empty { font-size: 0.8rem; color: #9CA3AF; text-align: center; padding: 1rem 0; }

/* Chat Container */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
}

.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  scroll-behavior: smooth;
}

.has-digital-human .chat-viewport {
  flex: 0.5;
  background: rgba(249, 250, 251, 0.8);
  border-top: 1px solid #E5E7EB;
}

/* Digital Human Stage */
.digital-human-stage {
  flex: 0.5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at center, #EEF2FF 0%, transparent 70%);
  position: relative;
  min-height: 250px;
}

.avatar-ring {
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: #fff;
  padding: 8px;
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.2);
  position: relative;
  z-index: 2;
  transition: all 0.3s ease;
}

.avatar-ring.is-speaking {
  box-shadow: 0 0 0 8px rgba(99, 102, 241, 0.1), 0 0 0 16px rgba(99, 102, 241, 0.05);
  animation: pulse-ring 2s infinite;
}

.bot-avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  background: #EEF2FF;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); }
  50% { transform: scale(1.05); }
  100% { transform: scale(0.95); }
}

.speech-wave {
  display: flex;
  gap: 4px;
  margin-top: 1.5rem;
  height: 20px;
  align-items: center;
}

.speech-wave span {
  width: 4px;
  height: 10px;
  background: #6366F1;
  border-radius: 2px;
  animation: wave-anim 1s infinite ease-in-out;
}
.speech-wave span:nth-child(2) { animation-delay: 0.1s; }
.speech-wave span:nth-child(3) { animation-delay: 0.2s; }
.speech-wave span:nth-child(4) { animation-delay: 0.3s; }
.speech-wave span:nth-child(5) { animation-delay: 0.4s; }

@keyframes wave-anim {
  0%, 100% { height: 10px; }
  50% { height: 24px; }
}

.status-badge {
  margin-top: 1rem;
  font-size: 0.8rem;
  color: #4F46E5;
  background: #EEF2FF;
  padding: 0.25rem 1rem;
  border-radius: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}

/* Chat Messages */
.welcome-banner {
  text-align: center;
  color: #4B5563;
  background: #EEF2FF;
  padding: 2rem;
  border-radius: 16px;
  border: 1px dashed #C7D2FE;
}
.welcome-banner h3 { color: #312E81; margin-top: 0; }
.welcome-banner p { margin-bottom: 0; line-height: 1.6; }

.message-row {
  display: flex;
  gap: 1rem;
  max-width: 85%;
}
.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.ai-av { background: #6366F1 !important; color: white !important; }
.user-av { background: #10B981 !important; color: white !important; }

.bubble-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 100%;
}

.message-row.user .bubble-wrapper { align-items: flex-end; }

.msg-meta {
  font-size: 0.75rem;
  color: #9CA3AF;
  display: flex;
  gap: 0.5rem;
}
.message-row.user .msg-meta { flex-direction: row-reverse; }

.bubble {
  padding: 1rem 1.25rem;
  border-radius: 16px;
  font-size: 0.95rem;
  line-height: 1.6;
  color: #1F2937;
  box-shadow: 0 4px 6px rgba(0,0,0,0.02);
}

.message-row.ai .bubble {
  background: #fff;
  border: 1px solid #F3F4F6;
  border-top-left-radius: 4px;
}

.message-row.user .bubble {
  background: #6366F1;
  color: #fff;
  border-top-right-radius: 4px;
}

.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.4rem;
}
.attachment-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.6rem;
  background: #EEF2FF;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #4F46E5;
  text-decoration: none;
  transition: background 0.2s;
}
.attachment-link:hover {
  background: #DDD6FE;
}
.message-row.user .attachment-link {
  background: rgba(255,255,255,0.2);
  color: #fff;
}

.msg-tool-calls {
  margin-top: 0.5rem;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  overflow: hidden;
}
.tool-call-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.6rem;
  background: #F9FAFB;
  font-size: 0.75rem;
  color: #6B7280;
  font-weight: 600;
}
.tool-call-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.3rem 0.6rem;
  font-size: 0.75rem;
  border-top: 1px solid #F3F4F6;
}
.tool-name {
  font-family: 'Fira Code', monospace;
  color: #4F46E5;
}
.tool-status.success { color: #10B981; }
.tool-status.error { color: #EF4444; }

.thinking-row { opacity: 0.8; }
.thinking-bubble {
  background: #EEF2FF;
  padding: 0.75rem 1rem;
  border-radius: 16px;
  border-top-left-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #4F46E5;
  font-size: 0.9rem;
}

/* Input Panel */
.input-panel {
  padding: 1.5rem 2rem;
  background: #fff;
  border-top: 1px solid #E5E7EB;
  border-radius: 0 0 24px 24px;
}

.attachments-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.attachment-chip {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  background: #EEF2FF;
  padding: 0.3rem 0.6rem;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #4F46E5;
}
.attachment-name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: center;
}

.shortcut-hint {
  margin-left: auto;
  font-size: 0.75rem;
  color: #9CA3AF;
}

.input-wrapper {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  padding: 0.75rem;
  transition: border-color 0.2s;
}
.input-wrapper:focus-within { border-color: #6366F1; }

.input-wrapper textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  height: 48px;
  max-height: 120px;
  outline: none;
  font-family: inherit;
  font-size: 0.95rem;
  color: #1F2937;
  line-height: 1.5;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #6366F1;
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) { background: #4F46E5; transform: translateY(-2px); }
.send-btn:disabled { background: #D1D5DB; cursor: not-allowed; }

.mic-active { color: #EF4444 !important; animation: pulse-ring 1s infinite; }

/* Right Profile Sidebar */
.profile-sidebar {
  width: 340px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sidebar-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
  color: #312E81;
}

.sidebar-desc { margin: 0; font-size: 0.85rem; color: #6B7280; line-height: 1.5; }

.dimensions-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dim-card {
  background: #fff;
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid #E5E7EB;
  box-shadow: 0 2px 4px rgba(0,0,0,0.01);
  transition: transform 0.2s;
}
.dim-card:hover { transform: translateY(-2px); }

.dim-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-weight: 600;
  font-size: 0.9rem;
}
.dim-name { color: #374151; }
.dim-desc { margin-top: 0.5rem; font-size: 0.75rem; color: #9CA3AF; }

.tags-section h4 { margin: 0 0 1rem 0; font-size: 1rem; color: #312E81; }
.tags-container { display: flex; flex-wrap: wrap; gap: 0.5rem; }

.ai-insight {
  margin-top: auto;
  background: linear-gradient(135deg, #312E81, #4F46E5);
  border-radius: 16px;
  padding: 1.25rem;
  color: white;
  display: flex;
  gap: 1rem;
  box-shadow: 0 10px 20px rgba(79, 70, 229, 0.2);
}
.insight-icon { font-size: 1.5rem; color: #FCD34D; }
.insight-content h4 { margin: 0 0 0.5rem 0; font-size: 0.95rem; }
.insight-content p { margin: 0; font-size: 0.8rem; line-height: 1.5; opacity: 0.9; }

:deep(.markdown-body) {
  font-family: 'Fira Sans', sans-serif;
  font-size: 0.95rem !important;
  background: transparent !important;
}
:deep(.markdown-body p) { margin-bottom: 0.5rem; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
</style>