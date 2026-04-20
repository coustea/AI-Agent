<template>
  <div :class="['tutor-dashboard', `mode-${chatMode}`]">

    <main class="dashboard-main">
      <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">

        <div class="sidebar-top-header">
          <div class="sidebar-brand" v-if="!sessionSidebarCollapsed">
            <el-icon class="brand-icon"><ChatDotRound /></el-icon>
            <span class="brand-text">智能辅导</span>
          </div>
          <button class="collapse-toggle-btn" @click="sessionSidebarCollapsed = !sessionSidebarCollapsed" :title="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="4" y="4" width="16" height="16" rx="4" ry="4"></rect>
              <line x1="9" y1="4" x2="9" y2="20"></line>
            </svg>
          </button>
        </div>

        <div class="standard-sidebar-nav">
          <div :class="['nav-item', 'new-chat', { active: !currentSessionId }]" @click="newSession" title="新对话">
            <el-icon><EditPen /></el-icon> <span class="nav-text">新对话</span>
          </div>
          <div class="nav-item search-item" title="搜索历史">
            <el-icon><Search /></el-icon> <span class="nav-text">搜索历史</span>
          </div>

          <el-popover
              placement="right-start"
              :width="260"
              trigger="click"
              :disabled="!sessionSidebarCollapsed"
              popper-style="padding: 12px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);"
          >
            <template #reference>
              <div class="nav-item history-toggle-btn" :class="{ 'inactive-click': !sessionSidebarCollapsed }" title="历史记录">
                <el-icon><Clock /></el-icon> <span class="nav-text">历史记录</span>
              </div>
            </template>

            <div class="popover-session-scroll">
              <div class="popover-title">历史记录</div>
              <div
                  v-for="s in sessions"
                  :key="s.id"
                  :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
                  @click="switchSession(s.id)"
              >
                <el-icon class="session-icon"><ChatLineSquare /></el-icon>
                <div class="session-info nav-text">
                  <span class="session-title">{{ s.title || '新对话' }}</span>
                  <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                </div>
                <el-button link class="del-btn nav-text" @click.stop="archiveSession(s.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
            </div>
          </el-popover>
        </div>

        <div class="session-list" v-show="!sessionSidebarCollapsed">
          <div
              v-for="s in sessions"
              :key="s.id"
              :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
              @click="switchSession(s.id)"
              :title="s.title || '新对话'"
          >
            <el-icon class="session-icon"><ChatLineSquare /></el-icon>
            <span class="session-title nav-text">{{ s.title || '新对话' }}</span>
	                <span class="session-time nav-text">{{ formatRelativeTime(s.updated_at) }}</span>
            <el-button link class="del-btn nav-text" @click.stop="archiveSession(s.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
        </div>

        <div class="sidebar-footer">
          <div class="mode-toggle-group">
            <button
                :class="['mode-btn', { active: chatMode === 'standard' }]"
                @click="chatMode = 'standard'"
                title="图文交互"
            >
              <el-icon><ChatLineRound /></el-icon> <span class="nav-text">图文交互</span>
            </button>
            <button
                :class="['mode-btn', { active: chatMode === 'digital_human' }]"
                @click="chatMode = 'digital_human'"
                title="数字人互动"
            >
              <el-icon><Avatar /></el-icon> <span class="nav-text">数字人互动</span>
            </button>
          </div>
        </div>
      </aside>

      <section class="chat-container">

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
          <div class="standard-welcome" v-if="chatMode === 'standard' && messages.length === 0">
            <h2>
              你好，学习者！
            </h2>
          </div>

          <div class="welcome-banner" v-if="chatMode === 'digital_human' && messages.length === 0">
            <div class="welcome-icon"><el-icon><Cpu /></el-icon></div>
            <h3>我是您的 AI 私人导师</h3>
            <p>支持文字、图片、文档等多模态交流，<br>我将在对话中自动更新您的学习画像并提供量身定制的解答</p>
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
              <div :class="['bubble', 'markdown-body', { streaming: msg.id === streamingMsgId && isAIThinking }]" v-html="renderMarkdown(msg.content)"></div>

              <div v-if="msg.attachments && msg.attachments.length > 0" class="msg-attachments">
                <a v-for="att in msg.attachments" :key="att.url" :href="att.url" target="_blank" class="attachment-link">
                  <el-icon v-if="att.type === 'image'"><Picture /></el-icon>
                  <el-icon v-else><Document /></el-icon>
                  <span>{{ att.name }}</span>
                </a>
              </div>

              <div v-if="msg.illustrations && msg.illustrations.length > 0" class="msg-illustrations">
                <img
                    v-for="(img, idx) in msg.illustrations"
                    :key="`${msg.id}-ill-${idx}`"
                    :src="img"
                    alt="AI 图解"
                    class="illustration-image"
                />
              </div>

            </div>
          </div>

          <div v-if="showThinkingIndicator" class="message-row ai thinking-row">
            <div class="msg-avatar"><div class="avatar-circle ai-av"><el-icon><Service /></el-icon></div></div>
            <div class="thinking-bubble">
              <span class="dot-typing"></span>
            </div>
          </div>
        </div>

        <div class="input-panel" :class="{ 'standard-input': chatMode === 'standard' }">
          <div v-if="pendingFiles.length > 0" class="attachments-preview">
            <div v-for="(f, idx) in pendingFiles" :key="idx" class="attachment-chip">
              <el-icon v-if="f.fileType === 'image'"><Picture /></el-icon>
              <el-icon v-else><Document /></el-icon>
              <span class="attachment-name">{{ f.name }}</span>
              <el-icon class="close-icon" @click="removeAttachment(idx)"><Close /></el-icon>
            </div>
          </div>

          <div class="multimodal-option-bar">
            <button
              type="button"
              class="option-chip"
              :class="{ active: generateImage }"
              @click="handleImageToggle"
              :aria-pressed="generateImage"
            >
              生成图片
            </button>
            <button
              type="button"
              class="option-chip"
              :class="{ active: generateVideo }"
              @click="handleVideoToggle"
              :aria-pressed="generateVideo"
            >
              生成视频
            </button>
          </div>

          <div class="input-wrapper" :class="{ 'pill-shape': chatMode === 'standard' }">
            <div class="toolbar-left">
              <template v-if="chatMode === 'standard'">
                <el-dropdown trigger="click" placement="top-start">
                  <button class="standard-plus-btn" :disabled="uploadingFile"><el-icon><Plus /></el-icon></button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="triggerDocUpload">上传文档</el-dropdown-item>
                      <el-dropdown-item @click="triggerImgUpload">上传图片</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </template>
              <template v-else>
                <el-tooltip content="上传文档" placement="top" :show-after="500">
                  <button class="tool-btn" @click="triggerDocUpload" :disabled="uploadingFile"><el-icon><Document /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="上传截图" placement="top" :show-after="500">
                  <button class="tool-btn" @click="triggerImgUpload" :disabled="uploadingFile"><el-icon><Picture /></el-icon></button>
                </el-tooltip>
                <el-tooltip content="语音提问" placement="top" :show-after="500">
                  <button class="tool-btn"><el-icon><Microphone /></el-icon></button>
                </el-tooltip>
              </template>
            </div>

            <textarea
                v-model="userInput"
                :placeholder="chatMode === 'standard' ? '在此输入你的问题(Shift + Enter 换行)' : '向 AI 导师提问 (Shift + Enter 换行)...'"
                @keydown.enter.exact.prevent="handleSend"
            ></textarea>

            <div class="toolbar-right">
              <button class="send-btn" :class="{ 'is-active': userInput.trim() || pendingFiles.length > 0 }" :disabled="(!userInput.trim() && pendingFiles.length === 0) || isAIThinking" @click="handleSend">
                <el-icon><Top /></el-icon>
              </button>
            </div>
          </div>
          <div class="input-footer" v-if="chatMode === 'digital_human'">AI 可能会产生误导性信息，请注意甄别。</div>
        </div>

        <input ref="docInput" type="file" accept=".pdf,.doc,.docx,.txt" style="display:none" @change="onFileSelected($event, 'document')" />
        <input ref="imgInput" type="file" accept=".png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onFileSelected($event, 'image')" />
      </section>

      <aside class="profile-sidebar">
        <div class="sidebar-header">
          <div class="header-title-row">
            <h3>动态学习画像</h3>
            <span class="sync-badge" :class="{ 'is-syncing': profileUpdated }">
              <span class="dot"></span> {{ profileUpdated ? 'Synced' : 'Live' }}
            </span>
          </div>
        </div>
        <p class="sidebar-desc">基于您的对话实时提取的关键特征</p>

        <div class="tags-section">
          <div class="tags-container" v-if="activeProfileTags.length > 0">
            <span v-for="(tag, idx) in activeProfileTags" :key="idx" class="feature-tag shadow-sm">
              <el-icon class="tag-icon"><Discount /></el-icon>
              {{ tag }}
            </span>
          </div>
          <div v-else class="empty-tags">
            对话太少啦，多聊两句让我更了解你～
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
import { ref, nextTick, onMounted, onBeforeUnmount, computed } from 'vue'
import {
  ChatLineRound, Avatar, Cpu, Service, UserFilled,
  Picture, Microphone, Document, ChatDotRound, ChatLineSquare,
  MagicStick, Plus, Delete, Close, Top,
  EditPen, Search, Discount, Clock
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
const chatScroll = ref<HTMLElement | null>(null)
const profileUpdated = ref(false)
const uploadingFile = ref(false)
const generateImage = ref(false)
const generateVideo = ref(false)

// 会话管理
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | undefined>(undefined)
const sessionSidebarCollapsed = ref(false)

// 文件上传
const docInput = ref<HTMLInputElement | null>(null)
const imgInput = ref<HTMLInputElement | null>(null)
interface PendingFile { file?: File; url?: string; fileType: string; name: string }
const pendingFiles = ref<PendingFile[]>([])

// 聊天消息
interface Attachment { url: string; type: string; name: string }
interface ChatMsg { id: number; role: 'user' | 'ai'; content: string; time: string; attachments?: Attachment[] | null; illustrations?: string[] }
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
const tutorStrategy = ref('开始对话后，系统将自动提取特征,为您生成专属策略，快开始您的对话吧！')

const activeProfileTags = computed(() => {
  return extractedTags.value
})

// 流式控制器
let abortController: AbortController | null = null
const streamingMsgId = ref<number | null>(null)
// 画像轮询计时器
let profilePollTimers: ReturnType<typeof setTimeout>[] = []

// ==========================================
// 工具函数
// ==========================================
const renderMarkdown = (text: string) => marked.parse(text)

const showThinkingIndicator = computed(() => {
  if (!isAIThinking.value) return false
  if (chatMode.value === 'digital_human') return false
  const streamingMsg = messages.value.find(m => m.id === streamingMsgId.value)
  return !streamingMsg || !streamingMsg.content
})

let scrollPending = false
const scrollToBottom = () => {
  if (scrollPending) return
  scrollPending = true
  nextTick(() => {
    scrollPending = false
    if (chatScroll.value) {
      chatScroll.value.scrollTop = chatScroll.value.scrollHeight
    }
  })
}

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const formatRelativeTime = (dateStr: string) => {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return new Date(dateStr).toLocaleDateString()
}

const resolveIllustrationUrl = (path: string) => {
  if (!path) return ''
  if (/^https?:\/\//.test(path) || path.startsWith('/')) return path
  return path
}

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

const newSession = () => {
  currentSessionId.value = undefined
  messages.value = []
  pendingFiles.value = []
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
      illustrations: [],
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

const onFileSelected = async (event: Event, expectedType: string) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const fileType = expectedType === 'image' ? 'image' : 'document'
  pendingFiles.value.push({
    file,
    fileType,
    name: file.name,
  })
  input.value = '' // 重置以允许重复选择同一文件
}

const removeAttachment = (idx: number) => {
  pendingFiles.value.splice(idx, 1)
}

// 多模态选项互斥切换
const handleImageToggle = () => {
  if (generateImage.value) {
    generateImage.value = false
  } else {
    generateImage.value = true
    generateVideo.value = false
  }
}

const handleVideoToggle = () => {
  if (generateVideo.value) {
    generateVideo.value = false
  } else {
    generateVideo.value = true
    generateImage.value = false
  }
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

  // 首条消息自动更新会话标题
  if (currentSessionId.value && text) {
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (session && (!session.title || session.title === '新对话')) {
      session.title = text.length > 20 ? text.slice(0, 20) + '...' : text
    }
  }

  const userMsgId = Date.now()

  // 用户消息（附件先占位，上传成功后回填真实链接）
  const displayText = text || (hasFiles ? `[附件分析] ${pendingFiles.value.map(f => f.name).join(', ')}` : '')
  if (displayText) {
    messages.value.push({
      id: userMsgId,
      role: 'user',
      content: displayText,
      time: now(),
      attachments: null,
    })
  }

  userInput.value = ''
  isAIThinking.value = true
  profileUpdated.value = false
  scrollToBottom()

  // 上传未持久化附件（绑定当前会话）
  const currentPending = [...pendingFiles.value]
  const uploadedAttachments: Attachment[] = []

  uploadingFile.value = true
  try {
    const uploaded = await Promise.all(
        currentPending.map(async (pending) => {
          if (pending.url) {
            return {
              url: pending.url,
              fileType: pending.fileType,
              name: pending.name,
            }
          }
          if (!pending.file || !currentSessionId.value) {
            throw new Error('会话不存在，无法上传附件')
          }
          const res = await uploadFile(pending.file, currentSessionId.value)
          const data = res.data.data
          return {
            url: data.url,
            fileType: data.file_type,
            name: data.original_name,
          }
        })
    )
    uploaded.forEach((item) => {
      uploadedAttachments.push({
        url: item.url,
        type: item.fileType,
        name: item.name,
      })
    })
    pendingFiles.value = []
  } catch {
    uploadingFile.value = false
    isAIThinking.value = false
    messages.value.push({
      id: Date.now() + 99,
      role: 'ai',
      content: '附件上传失败，请重试。',
      time: now(),
    })
    return
  }
  uploadingFile.value = false

  const imageUrls = uploadedAttachments.filter(f => f.type === 'image').map(f => f.url)
  const fileUrls = uploadedAttachments.filter(f => f.type === 'document').map(f => f.url)
  const userMsg = messages.value.find(m => m.id === userMsgId)
  if (userMsg) {
    userMsg.attachments = uploadedAttachments.length > 0 ? uploadedAttachments : null
  }

  // AI 消息占位
  const aiMsgId = Date.now() + 1
  messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
  streamingMsgId.value = aiMsgId

  // 发起 SSE 流式请求
  abortController = streamChat(
      {
        message: text || '请分析附件',
        session_id: currentSessionId.value,
        image_urls: imageUrls.length > 0 ? imageUrls : undefined,
        file_urls: fileUrls.length > 0 ? fileUrls : undefined,
        generate_image: generateImage.value,
        generate_video: generateVideo.value,
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
        streamingMsgId.value = null
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
        streamingMsgId.value = null
        abortController = null
      },
      // onEvent
      (evt) => {
        if (evt.event !== 'illustration') return
        const payload = evt.data as { path?: string }
        const imagePath = resolveIllustrationUrl(payload?.path || '')
        if (!imagePath) return
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (!aiMsg) return
        if (!aiMsg.illustrations) aiMsg.illustrations = []
        if (!aiMsg.illustrations.includes(imagePath)) {
          aiMsg.illustrations.push(imagePath)
        }
      },
  )
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
@import url('https://gs.jurieo.com/gemini/fonts-googleapis/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

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

/* ================= 主体排版 ================= */
.dashboard-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* --- 左侧：会话列表 --- */
.session-sidebar {
  position: relative;
  width: 240px;
  background: #FAFAFA;
  border-right: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

/* 折叠状态的侧边栏样式 */
.session-sidebar.collapsed {
  width: 64px;
}

/* 折叠时隐藏所有带有 nav-text 的文字标签 */
.session-sidebar.collapsed .nav-text {
  display: none;
}

/* 折叠时调整各个导航项居中并固定为方形 */
.session-sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 10px 0;
  width: 42px;
  margin-left: auto;
  margin-right: auto;
}

.session-sidebar.collapsed .session-item {
  justify-content: center;
  padding: 10px 0;
  width: 42px;
  margin-left: auto;
  margin-right: auto;
}

.session-sidebar.collapsed .standard-sidebar-nav {
  align-items: stretch;
}

/* 侧边栏顶部 Header */
.sidebar-top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 12px 8px 16px;
  height: 56px;
  box-sizing: border-box;
  flex-shrink: 0;
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0F172A;
  font-weight: 700;
  font-size: 1.05rem;
}
.brand-icon {
  color: #4F46E5;
  font-size: 1.25rem;
}

/* 侧栏折叠控制按钮 - 定制化 SVG 样式 */
.collapse-toggle-btn {
  background: transparent;
  border: none;
  color: #64748B;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s ease;
  width: 36px;
  height: 36px;
  padding: 0;
  margin: 0;
}
.collapse-toggle-btn:hover {
  background: #E2E8F0;
  color: #0F172A;
}
.collapse-toggle-btn svg {
  width: 1.3rem;
  height: 1.3rem;
}

/* ★ 关键对齐：折叠状态下，控制按钮宽度与下方导航项完美统一（均为 42px），确保绝对居中上下对齐 ★ */
.session-sidebar.collapsed .sidebar-top-header {
  justify-content: center;
  padding: 16px 0 8px;
}
.session-sidebar.collapsed .collapse-toggle-btn {
  width: 42px;
  height: 42px;
}

.standard-sidebar-nav {
  padding: 8px 16px 16px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

/* 通用统一导航项/按钮微卡片样式 */
.nav-item {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  color: #475569;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: #F8FAFC;
  border-color: #CBD5E1;
  color: #334155;
}

.nav-item.active {
  background: #EEF2FF;
  color: #4F46E5;
  border-color: #C7D2FE;
  font-weight: 600;
}

/* 不可点击状态的静默历史记录按钮（侧边栏展开时使用） */
.history-toggle-btn.inactive-click {
  cursor: default;
  box-shadow: none;
}
.history-toggle-btn.inactive-click:hover {
  background: #FFFFFF;
  border-color: #E2E8F0;
  color: #475569;
}

/* 折叠悬浮窗内的历史记录滚动区域 */
.popover-session-scroll {
  max-height: 40vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.popover-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #94A3B8;
  padding: 4px 8px 8px;
  border-bottom: 1px solid #E2E8F0;
  margin-bottom: 8px;
}
.popover-session-scroll .session-item {
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  margin: 0;
  padding: 8px;
}
.popover-session-scroll .session-item:hover {
  background: #F8FAFC;
  border-color: #E2E8F0;
}
.popover-session-scroll .session-item.active {
  background: #EEF2FF;
  color: #4F46E5;
  font-weight: 600;
}

/* 下方实际展现的历史记录列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
}

/* 历史记录平时透明，Hover 或 Active 时呈现卡片样式 */
.session-item {
  margin-bottom: 4px;
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}
.session-item:hover {
  background: #FFFFFF;
  border-color: #E2E8F0;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.session-item.active {
  background: #EEF2FF;
  color: #4F46E5;
  border-color: #C7D2FE;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.session-icon {
  font-size: 1.15rem;
  color: #94A3B8;
  transition: color 0.2s;
}
.session-item.active .session-icon {
  color: #4F46E5;
}

.session-info { flex: 1; display: flex; flex-direction: column; gap: 2px; overflow: hidden; min-width: 0; }
.session-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-time { font-size: 0.7rem; color: #94A3B8; white-space: nowrap; }

.del-btn {
  opacity: 0;
  color: #EF4444;
  padding: 4px;
}
.session-item:hover .del-btn { opacity: 1; }

.msg-illustrations {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.illustration-image {
  width: min(480px, 100%);
  border-radius: 10px;
  border: 1px solid #E2E8F0;
  background: #F8FAFC;
}

.session-empty {
  font-size: 0.8rem;
  color: #94A3B8;
  text-align: center;
  margin-top: 2rem;
}

/* ================= 模式切换底部区域 ================= */
.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #E2E8F0;
  margin-top: auto;
  background: #FAFAFA;
  transition: padding 0.3s ease;
}

/* 折叠时，极限缩减水平 padding，让 48px 的大按钮能在 64px 宽度的侧边栏内居中且不溢出 */
.session-sidebar.collapsed .sidebar-footer {
  padding: 16px 4px;
}

.mode-toggle-group {
  display: flex;
  flex-direction: column;
  background: #F1F5F9;
  padding: 6px;
  border-radius: 12px;
  gap: 6px;
  border: 1px solid #E2E8F0;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.02);
}

.mode-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 16px; /* 展开时按钮正常大小 */
  border: 1px solid transparent;
  background: transparent;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #64748B;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.mode-btn:hover:not(.active) {
  background: rgba(255, 255, 255, 0.6);
  color: #334155;
}

.mode-btn.active {
  background: #FFFFFF;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.02);
}

/* 图文交互激活色 */
.mode-btn.active:nth-child(1) {
  color: #0284C7;
  border-color: #E0F2FE;
  background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
}
.mode-btn.active:nth-child(1) .el-icon {
  color: #0EA5E9;
}

/* 数字人互动激活色 */
.mode-btn.active:nth-child(2) {
  color: #6D28D9;
  border-color: #EDE9FE;
  background: linear-gradient(180deg, #FFFFFF 0%, #F5F3FF 100%);
}
.mode-btn.active:nth-child(2) .el-icon {
  color: #8B5CF6;
}

.mode-btn .el-icon {
  font-size: 1.25rem; /* 展开时的基础图标尺寸 */
  transition: color 0.3s ease, transform 0.3s ease;
}

.mode-btn.active .el-icon {
  transform: scale(1.1);
}

/* ================= 折叠时模式切换按钮专属样式（放大版） ================= */
.session-sidebar.collapsed .mode-toggle-group {
  padding: 4px;
  gap: 10px;
}

.session-sidebar.collapsed .mode-btn {
  justify-content: center;
  padding: 0;
  width: 48px;  /* 增加至 48px，让按钮更加庞大饱满 */
  height: 48px; /* 增加至 48px */
  margin: 0 auto;
  border-radius: 12px; /* 按钮变大，对应圆角也变得更平滑 */
}

.session-sidebar.collapsed .mode-btn .el-icon {
  font-size: 1.65rem; /* 大幅增加图标字号，提升视觉分量与操作手感 */
}

/* --- 中央：聊天容器 --- */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  position: relative;
  overflow: hidden;
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
  animation: msg-appear 0.3s ease-out;
}

@keyframes msg-appear {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
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

.multimodal-option-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.option-chip {
  height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid #CBD5E1;
  background: #F8FAFC;
  color: #334155;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-chip:hover {
  border-color: #94A3B8;
  background: #F1F5F9;
}

.option-chip.active {
  color: #0C4A6E;
  border-color: #7DD3FC;
  background: #E0F2FE;
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
  align-items: center; /* 整体侧边栏内容水平居中 */
  text-align: center;
}

.sidebar-header {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.header-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.sidebar-header h3 { margin: 0; font-size: 1.1rem; color: #0F172A; font-weight: 600; text-align: left; }

.sync-badge {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  font-size: 0.7rem; font-family: 'Space Grotesk', monospace;
  color: #64748B; background: #E2E8F0; padding: 2px 8px; border-radius: 12px;
  transition: all 0.3s ease;
}
.sync-badge .dot { width: 6px; height: 6px; border-radius: 50%; background: #94A3B8; }
.sync-badge.is-syncing { background: #ECFEFF; color: #0891B2; }
.sync-badge.is-syncing .dot { background: #0891B2; box-shadow: 0 0 6px rgba(8,145,178,0.5); }

.sidebar-desc { margin: 0; font-size: 0.8rem; color: #64748B; text-align: center; }

.tags-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  width: 100%;
  overflow-y: auto;
  padding: 8px 0;
  align-items: center; /* 子容器对齐 */
}
.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  padding: 4px 0;
}
.feature-tag {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  padding: 8px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  color: #0F172A;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}
.feature-tag:hover {
  background: #F8FAFC;
  border-color: #CBD5E1;
  transform: translateY(-1px);
}
.tag-icon {
  color: #0891B2;
  font-size: 1rem;
}
.empty-tags {
  color: #94A3B8;
  font-size: 0.85rem;
  text-align: center;
  padding: 2rem 0;
  border: 1px dashed #E2E8F0;
  border-radius: 12px;
  background: #FAFAFA;
}

.ai-insight {
  margin-top: auto;
  background: #0F172A;
  border-radius: 12px;
  padding: 1.25rem;
  color: #F8FAFC;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  box-sizing: border-box;
}
.insight-header { display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 0.9rem; font-weight: 600; margin-bottom: 12px; color: #38BDF8; }
.insight-content { font-size: 0.85rem; line-height: 1.6; color: #CBD5E1; }

/* Markdown 内容样式补丁 */
:deep(.markdown-body) { font-family: 'Inter', sans-serif; font-size: 0.95rem !important; background: transparent !important; }
:deep(.markdown-body p) { margin-bottom: 0.5rem; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
:deep(.markdown-body pre) { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }

/* 流式输出光标 */
.bubble.streaming::after {
  content: '▍';
  animation: cursor-blink 1s step-end infinite;
  color: #94A3B8;
  font-weight: 400;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 滚动条 */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 2px; }

/* ============================================== */
/* Standard Mode (图文交互) 极简 UI 定制样式         */
/* ============================================== */
.mode-standard .session-sidebar {
  background: #F9F9F9;
  border-right: 1px solid #F0F0F0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.mode-standard .chat-viewport {
  background: #FFFFFF;
}
.standard-welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.standard-welcome h2 {
  font-size: 1.8rem;
  font-weight: 500;
  color: #111;
  margin-top: -10vh; /* 微微上移，更居中视觉 */
}
.mode-standard .input-panel {
  padding: 0 0 2.5rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: transparent;
}
.mode-standard .input-wrapper.pill-shape {
  width: 65%;
  max-width: 800px;
  min-width: 400px;
  background: #F9F9F9;
  border: 1px solid #E5E5E5;
  border-radius: 32px;
  padding: 10px 16px;
  align-items: center;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}
.mode-standard .input-wrapper.pill-shape:focus-within {
  background: #FFFFFF;
  border-color: #D1D5DB;
  box-shadow: 0 8px 24px rgba(0,0,0,0.05);
}
.mode-standard .toolbar-left {
  padding-bottom: 0;
  margin-right: 12px;
}
.standard-plus-btn {
  font-size: 1.2rem;
  color: #666;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  padding: 0;
  transition: background 0.2s;
}
.standard-plus-btn:hover {
  background: #E5E5E5;
}
.mode-standard textarea {
  height: 24px;
  padding: 0;
  align-self: center;
  font-size: 1rem;
}
.toolbar-right {
  display: flex;
  align-items: center;
  margin-left: 12px;
}
.mode-standard .send-btn {
  margin: 0;
}
</style>
