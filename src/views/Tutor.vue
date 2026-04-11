<template>
  <div class="tutor-dashboard">

    <!-- 顶部控制栏 (极简模式切换) -->
    <header class="tutor-header">
      <div class="header-left">
        <h2 class="title">全息智能辅导</h2>
      </div>
      <div class="header-center">
        <div class="mode-toggle-group">
          <button 
            :class="['mode-btn', { active: chatMode === 'standard' }]" 
            @click="chatMode = 'standard'"
          >
            <el-icon><ChatLineRound /></el-icon> 图文交互
          </button>
          <button 
            :class="['mode-btn', { active: chatMode === 'digital_human' }]" 
            @click="chatMode = 'digital_human'"
          >
            <el-icon><Avatar /></el-icon> 数字人互动
          </button>
        </div>
      </div>
      <div class="header-right">
        <el-button plain size="small" @click="newSession" :icon="Plus" class="new-chat-btn">新对话</el-button>
      </div>
    </header>

    <main class="dashboard-main">
      <!-- 左侧：会话列表 -->
      <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">
        <div class="session-sidebar-header">
          <span v-if="!sessionSidebarCollapsed" class="sidebar-title">历史记录</span>
          <el-button link @click="sessionSidebarCollapsed = !sessionSidebarCollapsed" class="collapse-btn">
            <el-icon><Fold v-if="!sessionSidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
        </div>
        <div v-if="!sessionSidebarCollapsed" class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            :class="['session-item', { active: s.id === currentSessionId }]"
            @click="switchSession(s.id)"
          >
            <el-icon class="session-icon"><ChatDotRound /></el-icon>
            <span class="session-title">{{ s.title }}</span>
            <el-button link class="del-btn" @click.stop="archiveSession(s.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty">暂无对话记录</div>
        </div>
      </aside>

      <!-- 中央：聊天主界面 -->
      <section class="chat-container">

        <!-- 数字人展示舞台 -->
        <div v-if="chatMode === 'digital_human'" class="digital-human-stage">
          <div class="avatar-ring" :class="{ 'is-speaking': isAIThinking || isSpeaking }">
            <img src="https://api.dicebear.com/7.x/bottts/svg?seed=AIAssistant&backgroundColor=0891B2&textureChance=50" alt="Digital Human Avatar" class="bot-avatar-img"/>
          </div>
          <div class="speech-wave" v-if="isAIThinking || isSpeaking">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
          <div class="status-badge">{{ (isAIThinking || isSpeaking) ? '正在多模态解答中...' : '倾听就绪' }}</div>
        </div>

        <div class="chat-viewport" ref="chatScroll">
          <div class="welcome-banner" v-if="messages.length === 0">
            <div class="welcome-icon"><el-icon><Cpu /></el-icon></div>
            <h3>我是您的 AI 私人导师</h3>
            <p>支持文字、图片、文档等多模态交流，<br>我将在对话中自动更新您的学习画像并提供量身定制的解答。</p>
          </div>

          <div v-for="msg in messages" :key="msg.id" :class="['message-row', msg.role]">
            <div class="msg-avatar">
              <div v-if="msg.role === 'ai'" class="avatar-circle ai-av"><el-icon><Service /></el-icon></div>
              <div v-else class="avatar-circle user-av"><el-icon><UserFilled /></el-icon></div>
            </div>

            <div class="bubble-wrapper">
              <div class="msg-meta">
                <span class="sender">{{ msg.role === 'ai' ? 'AI 导师' : 'You' }}</span>
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
                  <span>Tools Used ({{ msg.toolCalls.length }})</span>
                </div>
                <div v-for="(tc, idx) in msg.toolCalls" :key="idx" class="tool-call-item">
                  <span class="tool-name">{{ tc.tool }}</span>
                  <span class="tool-status" :class="tc.status">{{ tc.status === 'success' ? 'Success' : 'Failed' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isAIThinking" class="message-row ai thinking-row">
            <div class="msg-avatar"><div class="avatar-circle ai-av"><el-icon><Service /></el-icon></div></div>
            <div class="thinking-bubble">
              <span class="dot-typing"></span>
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
              <el-icon class="close-icon" @click="removeAttachment(idx)"><Close /></el-icon>
            </div>
          </div>
          
          <div class="input-wrapper">
            <div class="toolbar-left">
              <el-tooltip content="上传文档" placement="top" :show-after="500">
                <button class="tool-btn" @click="triggerDocUpload" :disabled="uploadingFile"><el-icon><Document /></el-icon></button>
              </el-tooltip>
              <el-tooltip content="上传截图" placement="top" :show-after="500">
                <button class="tool-btn" @click="triggerImgUpload" :disabled="uploadingFile"><el-icon><Picture /></el-icon></button>
              </el-tooltip>
              <el-tooltip content="语音提问" placement="top" :show-after="500">
                <button class="tool-btn" :class="{ 'mic-active': isRecording }" @click="toggleRecord"><el-icon><Microphone /></el-icon></button>
              </el-tooltip>
            </div>

            <textarea
              v-model="userInput"
              placeholder="向 AI 导师提问 (Shift + Enter 换行)..."
              @keydown.enter.exact.prevent="handleSend"
            ></textarea>

            <button class="send-btn" :class="{ 'is-active': userInput.trim() || pendingFiles.length > 0 }" :disabled="(!userInput.trim() && pendingFiles.length === 0) || isAIThinking" @click="handleSend">
              <el-icon><Top /></el-icon>
            </button>
          </div>
          <div class="input-footer">AI 可能会产生误导性信息，请注意甄别。</div>
        </div>

        <!-- 隐藏文件输入 -->
        <input ref="docInput" type="file" accept=".pdf,.doc,.docx,.txt" style="display:none" @change="onFileSelected($event, 'document')" />
        <input ref="imgInput" type="file" accept=".png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onFileSelected($event, 'image')" />
      </section>

      <!-- 右侧：动态画像面板 -->
      <aside class="profile-sidebar">
        <div class="sidebar-header">
          <h3>动态学习画像</h3>
          <span class="sync-badge" :class="{ 'is-syncing': profileUpdated }">
            <span class="dot"></span> {{ profileUpdated ? 'Synced' : 'Live' }}
          </span>
        </div>
        <p class="sidebar-desc">隐式特征抽取，随对话实时更新</p>

        <div class="dimensions-grid">
          <div class="dim-item" v-for="dim in profileDimensions" :key="dim.key">
            <div class="dim-top">
              <span class="dim-name">{{ dim.name }}</span>
              <span class="dim-score" :style="{ color: dim.color }">{{ dim.score ?? '--' }}</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${dim.score ?? 0}%`, backgroundColor: dim.color }"></div>
            </div>
            <div class="dim-desc" :title="dim.desc">{{ dim.desc }}</div>
          </div>
        </div>

        <div class="tags-section" v-if="extractedTags.length > 0">
          <h4>特征标签</h4>
          <div class="tags-container">
            <span v-for="tag in extractedTags" :key="tag" class="feature-tag">{{ tag }}</span>
          </div>
        </div>

        <div class="ai-insight">
          <div class="insight-header">
            <el-icon><MagicStick /></el-icon> 辅导策略
          </div>
          <div class="insight-content">{{ tutorStrategy }}</div>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import {
  ChatLineRound, Avatar, Cpu, Service, UserFilled,
  Picture, Microphone, Document, ChatDotRound,
  MagicStick, Fold, Expand, Plus, Delete, Close, Top
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
  { key: 'knowledge_level', name: '知识基础', color: '#0891B2', defaultDesc: '自动分析中...' },
  { key: 'cognitive_style', name: '认知风格', color: '#10B981', defaultDesc: '自动分析中...' },
  { key: 'error_pattern', name: '易错倾向', color: '#F59E0B', defaultDesc: '自动分析中...' },
  { key: 'learning_goal', name: '学习目标', color: '#8B5CF6', defaultDesc: '自动分析中...' },
  { key: 'learning_history', name: '学习历史', color: '#EC4899', defaultDesc: '自动分析中...' },
  { key: 'interest_preference', name: '兴趣偏好', color: '#3B82F6', defaultDesc: '自动分析中...' },
  { key: 'learning_pace', name: '学习节奏', color: '#14B8A6', defaultDesc: '自动分析中...' },
  { key: 'cognitive_level', name: '认知水平', color: '#F97316', defaultDesc: '自动分析中...' },
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
const tutorStrategy = ref('开始对话后，系统将自动提取特征。')

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
      // 如果创建失败，使用 undefined
    }
  }

  // 用户消息
  const displayText = text || (hasFiles ? `[附件分析] ${pendingFiles.value.map(f => f.name).join(', ')}` : '')
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
      message: text || '请分析附件',
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
      scheduleProfilePoll()
      abortController = null
    },
    // onError
    (err) => {
      const aiMsg = messages.value.find(m => m.id === aiMsgId)
      if (aiMsg && !aiMsg.content) {
        aiMsg.content = `Generate failed: ${err.message}`
      }
      isAIThinking.value = false
      abortController = null
    },
  )
}

const toggleRecord = () => {
  isRecording.value = !isRecording.value
  if (!isRecording.value && userInput.value === '') {
    userInput.value = "我其实对动态规划的转移方程一直理解不透，你能用图形化的方式给我讲讲吗？"
  }
}

onMounted(async () => {
  await loadSessions()
  if (sessions.value.length > 0) {
    await switchSession(sessions.value[0]!.id)
  }
  await fetchProfile()
})

onBeforeUnmount(() => {
  abortController?.abort()
  profilePollTimers.forEach(t => clearTimeout(t))
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

/* ================= 全局设定 ================= */
.tutor-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #FFFFFF;
  font-family: 'Inter', system-ui, sans-serif;
  color: #0F172A;
  box-sizing: border-box;
}

/* ================= 顶部控制栏 ================= */
.tutor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1.5rem;
  height: 60px;
  border-bottom: 1px solid #E2E8F0;
  background-color: #FFFFFF;
  flex-shrink: 0;
  z-index: 10;
}

.header-left .title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.mode-toggle-group {
  display: flex;
  background: #F1F5F9;
  padding: 4px;
  border-radius: 8px;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #64748B;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn.active {
  background: #FFFFFF;
  color: #0F172A;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.new-chat-btn {
  font-size: 0.85rem;
}

/* ================= 主体排版 ================= */
.dashboard-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* --- 左侧：会话列表 --- */
.session-sidebar {
  width: 240px;
  background: #FAFAFA;
  border-right: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.session-sidebar.collapsed {
  width: 60px;
}

.session-sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
}

.sidebar-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #64748B;
}

.collapse-btn {
  color: #94A3B8;
  font-size: 1rem;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 0.75rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: #475569;
  transition: background 0.2s;
  font-size: 0.85rem;
}

.session-item:hover {
  background: #F1F5F9;
}

.session-item.active {
  background: #ECFEFF;
  color: #0891B2;
  font-weight: 500;
}

.session-icon { font-size: 1rem; opacity: 0.7; }
.session-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.del-btn {
  opacity: 0;
  color: #EF4444;
  padding: 4px;
}
.session-item:hover .del-btn { opacity: 1; }

.session-empty {
  font-size: 0.8rem;
  color: #94A3B8;
  text-align: center;
  margin-top: 2rem;
}

/* --- 中央：聊天容器 --- */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  position: relative;
}

.has-digital-human .chat-viewport {
  flex: 0.6;
  border-top: 1px solid #E2E8F0;
  background: #FAFAFA;
}

/* 数字人舞台 */
.digital-human-stage {
  flex: 0.4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #FFFFFF;
}

.avatar-ring {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  padding: 6px;
  border: 1px solid #E2E8F0;
  transition: all 0.3s ease;
}

.avatar-ring.is-speaking {
  border-color: #0891B2;
  box-shadow: 0 0 0 6px rgba(8, 145, 178, 0.1);
  animation: pulse-ring 2s infinite;
}

.bot-avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  background: #F8FAFC;
}

@keyframes pulse-ring {
  0% { transform: scale(0.98); }
  50% { transform: scale(1.02); }
  100% { transform: scale(0.98); }
}

.speech-wave {
  display: flex;
  gap: 3px;
  margin-top: 1rem;
  height: 16px;
  align-items: center;
}

.speech-wave span {
  width: 3px;
  height: 8px;
  background: #0891B2;
  border-radius: 2px;
  animation: wave-anim 1s infinite ease-in-out;
}
.speech-wave span:nth-child(2) { animation-delay: 0.1s; }
.speech-wave span:nth-child(3) { animation-delay: 0.2s; }

@keyframes wave-anim {
  0%, 100% { height: 8px; }
  50% { height: 16px; }
}

.status-badge {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #64748B;
  font-family: 'Space Grotesk', monospace;
}

/* 聊天滚动区 */
.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  scroll-behavior: smooth;
}

.welcome-banner {
  text-align: center;
  margin: auto 0;
  color: #475569;
}
.welcome-icon { font-size: 2.5rem; color: #E2E8F0; margin-bottom: 1rem; }
.welcome-banner h3 { font-size: 1.2rem; color: #0F172A; margin: 0 0 0.5rem; }
.welcome-banner p { font-size: 0.9rem; line-height: 1.6; margin: 0; }

.message-row {
  display: flex;
  gap: 1rem;
  max-width: 85%;
}

.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-avatar { flex-shrink: 0; }
.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}
.ai-av { background: #0F172A; color: #FFF; }
.user-av { background: #0891B2; color: #FFF; }

.bubble-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-row.user .bubble-wrapper { align-items: flex-end; }

.msg-meta {
  font-size: 0.75rem;
  color: #94A3B8;
  display: flex;
  gap: 8px;
}
.message-row.user .msg-meta { flex-direction: row-reverse; }
.sender { font-weight: 600; color: #475569; }

.bubble {
  padding: 0.75rem 1.25rem;
  border-radius: 12px;
  font-size: 0.95rem;
  line-height: 1.6;
}

.message-row.ai .bubble {
  background: #FAFAFA;
  border: 1px solid #E2E8F0;
  border-top-left-radius: 4px;
  color: #0F172A;
}

.message-row.user .bubble {
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  border-top-right-radius: 4px;
  color: #0F172A;
}

/* 附件与工具展示 */
.msg-attachments { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.attachment-link {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px; background: #FFFFFF; border: 1px solid #E2E8F0;
  border-radius: 6px; font-size: 0.8rem; color: #0891B2;
  text-decoration: none; transition: border-color 0.2s;
}
.attachment-link:hover { border-color: #0891B2; }

.msg-tool-calls {
  margin-top: 8px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FAFAFA;
  font-family: 'Space Grotesk', monospace;
}
.tool-call-header {
  padding: 6px 10px;
  font-size: 0.75rem;
  color: #64748B;
  border-bottom: 1px solid #E2E8F0;
  display: flex; align-items: center; gap: 6px;
}
.tool-call-item {
  padding: 6px 10px;
  font-size: 0.75rem;
  display: flex; justify-content: space-between;
}
.tool-name { color: #0F172A; }
.tool-status.success { color: #10B981; }

/* Typing indicator */
.thinking-bubble {
  background: #FAFAFA;
  border: 1px solid #E2E8F0;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  border-top-left-radius: 4px;
  display: flex;
  align-items: center;
}
.dot-typing {
  position: relative;
  width: 6px; height: 6px; border-radius: 50%;
  background-color: #94A3B8; color: #94A3B8;
  animation: dotTyping 1.5s infinite linear;
  box-shadow: 12px 0 0 0 #94A3B8, 24px 0 0 0 #94A3B8;
  margin-right: 24px;
}
@keyframes dotTyping {
  0% { box-shadow: 12px 0 0 0 #94A3B8, 24px 0 0 0 #94A3B8; }
  33% { background-color: #0F172A; box-shadow: 12px 0 0 0 #94A3B8, 24px 0 0 0 #94A3B8; }
  66% { background-color: #94A3B8; box-shadow: 12px 0 0 0 #0F172A, 24px 0 0 0 #94A3B8; }
  100% { background-color: #94A3B8; box-shadow: 12px 0 0 0 #94A3B8, 24px 0 0 0 #0F172A; }
}

/* 输入面板 */
.input-panel {
  padding: 1rem 2rem 1.5rem;
  background: #FFFFFF;
}

.attachments-preview {
  display: flex; gap: 8px; margin-bottom: 8px;
}
.attachment-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 8px; background: #F1F5F9;
  border: 1px solid #E2E8F0; border-radius: 6px;
  font-size: 0.75rem; color: #475569;
}
.close-icon { cursor: pointer; color: #94A3B8; }
.close-icon:hover { color: #EF4444; }

.input-wrapper {
  display: flex;
  align-items: flex-end;
  background: #FAFAFA;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 8px;
  transition: border-color 0.2s;
}
.input-wrapper:focus-within { border-color: #0891B2; background: #FFFFFF; }

.toolbar-left {
  display: flex;
  gap: 4px;
  margin-right: 8px;
  padding-bottom: 4px;
}

.tool-btn {
  background: transparent;
  border: none;
  width: 32px; height: 32px;
  border-radius: 8px;
  color: #64748B;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 1.1rem;
}
.tool-btn:hover { background: #E2E8F0; color: #0F172A; }
.mic-active { color: #EF4444; }

.input-wrapper textarea {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  height: 36px;
  max-height: 160px;
  outline: none;
  font-family: inherit;
  font-size: 0.95rem;
  color: #0F172A;
  line-height: 1.5;
  padding: 6px 0;
}
.input-wrapper textarea::placeholder { color: #94A3B8; }

.send-btn {
  width: 36px; height: 36px;
  border-radius: 8px;
  background: #E2E8F0;
  color: #94A3B8;
  border: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.2rem; cursor: not-allowed;
  margin-left: 8px; margin-bottom: 4px;
  transition: all 0.2s;
}
.send-btn.is-active { background: #0F172A; color: #FFFFFF; cursor: pointer; }
.send-btn.is-active:hover { background: #1E293B; transform: translateY(-1px); }

.input-footer {
  text-align: center;
  font-size: 0.7rem;
  color: #94A3B8;
  margin-top: 8px;
}

/* --- 右侧：画像面板 --- */
.profile-sidebar {
  width: 300px;
  padding: 1.5rem;
  background: #FAFAFA;
  border-left: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-header { display: flex; justify-content: space-between; align-items: center; }
.sidebar-header h3 { margin: 0; font-size: 1.1rem; color: #0F172A; font-weight: 600; }

.sync-badge {
  display: flex; align-items: center; gap: 4px;
  font-size: 0.7rem; font-family: 'Space Grotesk', monospace;
  color: #64748B; background: #E2E8F0; padding: 2px 8px; border-radius: 12px;
  transition: all 0.3s ease;
}
.sync-badge .dot { width: 6px; height: 6px; border-radius: 50%; background: #94A3B8; }
.sync-badge.is-syncing { background: #ECFEFF; color: #0891B2; }
.sync-badge.is-syncing .dot { background: #0891B2; box-shadow: 0 0 6px rgba(8,145,178,0.5); }

.sidebar-desc { margin: 0; font-size: 0.8rem; color: #64748B; }

.dimensions-grid { display: flex; flex-direction: column; gap: 1rem; }
.dim-item { display: flex; flex-direction: column; gap: 6px; }
.dim-top { display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; }
.dim-name { color: #334155; }
.dim-score { font-family: 'Space Grotesk', monospace; }

.progress-track {
  width: 100%; height: 6px; background: #E2E8F0; border-radius: 3px; overflow: hidden;
}
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease-out; }
.dim-desc { font-size: 0.75rem; color: #64748B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.tags-section h4 { margin: 0 0 0.75rem 0; font-size: 0.9rem; color: #0F172A; font-weight: 600; }
.tags-container { display: flex; flex-wrap: wrap; gap: 6px; }
.feature-tag {
  background: #FFFFFF; border: 1px solid #E2E8F0;
  padding: 2px 8px; border-radius: 4px;
  font-size: 0.75rem; color: #475569;
}

.ai-insight {
  margin-top: auto;
  background: #0F172A;
  border-radius: 12px;
  padding: 1rem;
  color: #F8FAFC;
}
.insight-header { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; font-weight: 600; margin-bottom: 8px; color: #38BDF8; }
.insight-content { font-size: 0.8rem; line-height: 1.6; color: #CBD5E1; }

/* Markdown 内容样式补丁 */
:deep(.markdown-body) { font-family: 'Inter', sans-serif; font-size: 0.95rem !important; background: transparent !important; }
:deep(.markdown-body p) { margin-bottom: 0.5rem; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
:deep(.markdown-body pre) { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }

/* 滚动条 */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 2px; }
</style>