<template>
  <div :class="['tutor-dashboard', `mode-${chatMode}`]">

    <main class="dashboard-main">
      <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">

        <div class="sidebar-top-header">
          <div class="sidebar-brand" v-if="!sessionSidebarCollapsed">
            <el-icon class="brand-icon"><ChatDotRound /></el-icon>
            <span class="brand-text">智能辅导</span>
          </div>
          <button
              v-if="chatMode !== 'digital_human'"
              class="collapse-toggle-btn"
              @click="sessionSidebarCollapsed = !sessionSidebarCollapsed"
              :title="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="4" y="4" width="16" height="16" rx="4" ry="4"></rect>
              <line x1="9" y1="4" x2="9" y2="20"></line>
            </svg>
          </button>
        </div>

        <div class="standard-sidebar-nav">
          <div :class="['nav-item', 'new-chat-btn', { active: !currentSessionId }]" @click="newSession" title="新建对话">
            <el-icon><EditPen /></el-icon> <span class="nav-text">新建对话</span>
          </div>

          <el-popover
              placement="right-start"
              :width="280"
              trigger="click"
              v-model:visible="searchPopoverVisible"
              popper-style="padding: 16px 12px 12px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);"
              @after-leave="searchKeyword = ''"
          >
            <template #reference>
              <div class="nav-item search-item" title="搜索历史">
                <el-icon><Search /></el-icon> <span class="nav-text">搜索历史</span>
              </div>
            </template>

            <div class="popover-search-container">
              <el-input
                  v-model="searchKeyword"
                  placeholder="输入关键词搜索记录..."
                  clearable
                  class="search-input"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>

              <div class="popover-session-scroll search-results-scroll" v-show="searchKeyword.trim() !== ''">
                <div
                    v-for="s in filteredSessions"
                    :key="s.id"
                    :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
                    @click="switchSession(s.id); searchPopoverVisible = false"
                >
                  <el-icon class="session-icon"><ChatLineSquare /></el-icon>
                  <div class="session-info nav-text">
                    <span class="session-title">{{ s.title || '新建对话' }}</span>
                    <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                  </div>
                </div>

                <div v-if="filteredSessions.length === 0" class="session-empty nav-text">
                  未找到相关记录
                </div>
              </div>
            </div>
          </el-popover>

          <el-popover
              v-if="sessionSidebarCollapsed"
              placement="right-start"
              :width="260"
              trigger="click"
              popper-style="padding: 12px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);"
          >
            <template #reference>
              <div class="nav-item history-collapsed-btn" title="历史记录">
                <el-icon><Timer /></el-icon>
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
                  <span class="session-title">{{ s.title || '新建对话' }}</span>
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

        <div class="history-section-header" v-if="!sessionSidebarCollapsed">
          <el-icon><Timer /></el-icon> <span>历史记录</span>
        </div>

        <div class="session-list" v-show="!sessionSidebarCollapsed">
          <div
              v-for="s in sessions"
              :key="s.id"
              :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
              @click="switchSession(s.id)"
              :title="s.title || '新建对话'"
          >
            <el-icon class="session-icon"><ChatLineSquare /></el-icon>
            <div class="session-info nav-text">
              <span class="session-title">{{ s.title || '新建对话' }}</span>
              <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
            </div>
            <el-button link class="del-btn nav-text" @click.stop="archiveSession(s.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
        </div>
      </aside>

      <section class="chat-container">

        <div v-if="chatMode === 'digital_human'" class="digital-human-stage">
          <div class="digital-human-canvas-placeholder">
            <el-icon class="placeholder-icon"><Avatar /></el-icon>
            <p>数字人形象预留位</p>
          </div>

          <div class="digital-human-status-overlay" :class="{ active: isAIThinking || isSpeaking }">
            <div class="speech-wave" v-if="isAIThinking || isSpeaking">
              <span></span><span></span><span></span><span></span><span></span>
            </div>
            <div class="status-badge">{{ (isAIThinking || isSpeaking) ? '正在多模态解答中...' : '倾听就绪' }}</div>
          </div>
        </div>

        <div class="chat-interaction-area">
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

            <div
                v-for="msg in messages"
                :key="msg.id"
                :class="['message-row', msg.role]"
                v-show="!(msg.role === 'ai' && msg.id === streamingMsgId && !msg.content)"
            >
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

                <div v-if="msg.diagramGenerating" class="diagram-generating">
                  <span class="diagram-spinner"></span>
                  <span>图解正在生成...</span>
                </div>

                <div v-if="msg.diagram" class="msg-diagram">
                  <div class="diagram-header">
                    <span class="diagram-title">{{ msg.diagram.title }}</span>
                    <span class="diagram-type-tag">{{ msg.diagram.type }}</span>
                  </div>
                  <div class="diagram-summary" v-if="msg.diagram.summary">{{ msg.diagram.summary }}</div>
                  <div
                      class="diagram-svg-container"
                      v-html="diagramSvgCache.get(msg.diagram.render.source) || ''"
                  ></div>
                </div>

              </div>
            </div>

            <div v-if="showThinkingIndicator" class="message-row ai thinking-row">
              <div class="msg-avatar"><div class="avatar-circle ai-av"><el-icon><Service /></el-icon></div></div>
              <div class="thinking-bubble">
                <el-icon class="is-loading thinking-spinner"><Loading /></el-icon>
                <span class="thinking-text">正在思考...</span>
              </div>
            </div>
          </div>

          <div class="input-panel">
            <div v-if="pendingFiles.length > 0" class="attachments-preview">
              <div v-for="(f, idx) in pendingFiles" :key="idx" class="attachment-chip">
                <el-icon v-if="f.fileType === 'image'"><Picture /></el-icon>
                <el-icon v-else><Document /></el-icon>
                <span class="attachment-name">{{ f.name }}</span>
                <el-icon class="close-icon" @click="removeAttachment(idx)"><Close /></el-icon>
              </div>
            </div>

            <div class="input-wrapper" :class="{ 'is-expanded': isExpandedInput }">

              <div class="toolbar-left">
                <el-dropdown trigger="click" placement="top-start" popper-class="custom-plus-dropdown">
                  <button class="standard-plus-btn" :disabled="uploadingFile"><el-icon><Plus /></el-icon></button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="triggerDocUpload">
                        <el-icon><Paperclip /></el-icon> 添加文件
                      </el-dropdown-item>
                      <el-dropdown-item @click="triggerImgUpload">
                        <el-icon><Picture /></el-icon> 添加图片
                      </el-dropdown-item>

                      <el-dropdown-item divided @click="handleImageToggle">
                        <el-icon><Picture /></el-icon> {{ needDiagram ? '取消生成图解' : '生成图解' }}
                      </el-dropdown-item>
                      <el-dropdown-item @click="handleVideoToggle">
                        <el-icon><VideoPlay /></el-icon> {{ generateVideo ? '取消生成视频' : '生成视频' }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>

                <el-tooltip content="联网搜索" placement="top" :show-after="500">
                  <button class="media-gen-btn btn-web" :class="{ active: enableWebSearch }" @click="enableWebSearch = !enableWebSearch">
                    <el-icon>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <ellipse cx="12" cy="12" rx="5" ry="10"></ellipse>
                        <line x1="12" y1="2" x2="12" y2="22"></line>
                        <line x1="2" y1="12" x2="22" y2="12"></line>
                      </svg>
                    </el-icon>
                  </button>
                </el-tooltip>

                <div class="active-media-chip" v-if="needDiagram" @click="handleImageToggle" title="取消生成图解">
                  <div class="chip-icon-circle">
                    <el-icon class="icon-default"><Picture /></el-icon>
                    <el-icon class="icon-hover"><Close /></el-icon>
                  </div>
                  <span>图解</span>
                </div>

                <div class="active-media-chip" v-if="generateVideo" @click="handleVideoToggle" title="取消生成视频">
                  <div class="chip-icon-circle">
                    <el-icon class="icon-default"><VideoPlay /></el-icon>
                    <el-icon class="icon-hover"><Close /></el-icon>
                  </div>
                  <span>视频</span>
                </div>
              </div>

              <textarea
                  ref="textareaRef"
                  v-model="userInput"
                  placeholder="向 AI 导师提问（Enter 发送，Shift Enter换行）"
                  @keydown.enter.exact.prevent="handleSend"
                  @input="autoResize"
              ></textarea>

              <div class="toolbar-right">
                <el-tooltip :content="isRecording ? '结束录音' : '语音提问'" placement="top" :show-after="500">
                  <button class="voice-btn" :class="{ 'is-recording': isRecording }" @click="handleVoiceToggle">
                    <el-icon><Microphone /></el-icon>
                  </button>
                </el-tooltip>

                <el-tooltip
                    v-if="chatMode === 'digital_human'"
                    :content="isVoiceChatting ? '结束语音对话' : '开启语音通话模式'"
                    placement="top"
                    :show-after="500"
                >
                  <button
                      class="direct-voice-chat-btn"
                      :class="{ 'is-active': isVoiceChatting }"
                      @click="handleVoiceChatToggle"
                  >
                    <div class="voice-bars-icon">
                      <span class="bar"></span>
                      <span class="bar"></span>
                      <span class="bar"></span>
                      <span class="bar"></span>
                    </div>
                  </button>
                </el-tooltip>

                <el-tooltip content="请输入您的问题" placement="top" :show-after="500">
                  <button class="send-btn" :class="{ 'can-send': userInput.trim() || pendingFiles.length > 0 }" @click="handleSend">
                    <el-icon><Top /></el-icon>
                  </button>
                </el-tooltip>
              </div>

            </div>
            <div class="input-footer">AI 可能会产生错误信息，请注意甄别。</div>
          </div>
        </div>

        <input ref="docInput" type="file" accept=".pdf,.doc,.docx,.txt" style="display:none" @change="onFileSelected($event, 'document')" />
        <input ref="imgInput" type="file" accept=".png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onFileSelected($event, 'image')" />
      </section>

      <aside class="profile-sidebar">
        <div class="sidebar-header">
          <div class="header-title-row">
            <h3>动态学习画像</h3>
            <span class="sync-badge" :class="{ 'is-syncing': profileUpdated }">
              <span class="dot"></span> Live
            </span>
          </div>
          <p class="sidebar-desc">基于对话内容为你生成的学习画像</p>
        </div>

        <div class="profile-feature-card">
          <div class="feature-card-header">
            <div class="header-icon"><el-icon><User /></el-icon></div>
            <span class="header-title">学习特征总结</span>
          </div>

          <div class="feature-list" v-if="activeProfileDimensions.length > 0">
            <div class="feature-item" v-for="dim in activeProfileDimensions" :key="dim.key">
              <div class="item-icon-box">
                <el-icon><component :is="getIcon(dim.key)" /></el-icon>
              </div>
              <div class="item-text-box">
                <div class="item-title">{{ dim.name }}</div>
                <div class="item-desc">{{ dim.desc }}</div>
              </div>
            </div>
          </div>

          <div class="feature-list empty-state" v-else>
            <div class="empty-text">对话太少啦，多聊两句让我更了解你～</div>
          </div>
        </div>

        <div class="long-term-memory-section">
          <div class="memory-header-row">
            <div class="memory-title-wrap">
              <span class="memory-title">长期记忆</span>
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </div>
            <div class="memory-switch-wrap">
              <span class="switch-status">{{ memoryEnabled ? '已启用' : '未使用' }}</span>
              <el-switch v-model="memoryEnabled" size="small" />
            </div>
          </div>
          <p class="memory-desc">将重要信息存入长期记忆，以提供更个性化的辅导服务。</p>
        </div>
      </aside>
    </main>

    <div
        class="fab-container"
        :class="{ 'is-dragging': isDragging, 'is-dimmed': isDimmed, 'stick-right': isStickRight }"
        :style="{ left: fabPos.x + 'px', top: fabPos.y + 'px' }"
        @mousedown="startDrag"
        @touchstart="startDrag"
        @mouseenter="resetDimTimer"
    >
      <div class="fab-button">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <path d="M11 2L13.2 8.8L20 11L13.2 13.2L11 20L8.8 13.2L2 11L8.8 8.8L11 2ZM18.5 15.5L19.5 18.5L22.5 19.5L19.5 20.5L18.5 23.5L17.5 20.5L14.5 19.5L17.5 18.5L18.5 15.5Z"/>
        </svg>
      </div>

      <transition name="fab-menu-fade">
        <div v-if="showFabMenu" class="fab-menu" @mousedown.stop @touchstart.stop>
          <div
              class="fab-menu-item"
              :class="{ active: chatMode === 'standard' }"
              @click="setChatMode('standard')"
          >
            <div class="menu-icon-box">
              <el-icon><ChatLineRound /></el-icon>
            </div>
            <div class="menu-text-content">
              <div class="menu-title">图文交互</div>
              <div class="menu-desc">文字、图片多模态交流</div>
            </div>
            <div class="check-icon" v-if="chatMode === 'standard'">
              <el-icon><CircleCheckFilled /></el-icon>
            </div>
          </div>
          <div
              class="fab-menu-item"
              :class="{ active: chatMode === 'digital_human' }"
              @click="setChatMode('digital_human')"
          >
            <div class="menu-icon-box">
              <el-icon><Avatar /></el-icon>
            </div>
            <div class="menu-text-content">
              <div class="menu-title">数字人互动</div>
              <div class="menu-desc">与数字人进行语音对话</div>
            </div>
            <div class="check-icon" v-if="chatMode === 'digital_human'">
              <el-icon><CircleCheckFilled /></el-icon>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
// ==========================================
// 1. 导入
// ==========================================
import { ref, nextTick, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import {
  ChatLineRound, Avatar, Cpu, Service, UserFilled,
  Picture, Microphone, Document, ChatDotRound, ChatLineSquare,
  Plus, Delete, Close, Top,
  EditPen, Search, Discount, Timer, VideoPlay,
  Paperclip, CircleCheckFilled,
  User, InfoFilled, Medal, Aim, Setting, Loading
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import 'github-markdown-css/github-markdown-light.css'
import mermaid from 'mermaid'
import {
  streamChat, getProfile, uploadFile,
  getSessions, createSession, deleteSession, getChatHistory,
  type ProfileData, type ChatSession
} from '@/api/ai'
import { getMe } from '@/api/auth'

// ==========================================
// 2. 常量定义
// ==========================================
const DIMENSION_MAP = [
  { key: 'knowledge_level', name: '擅长领域', defaultDesc: '自动分析中...' },
  { key: 'cognitive_style', name: '认知风格', defaultDesc: '自动分析中...' },
  { key: 'error_pattern', name: '待提升方向', defaultDesc: '自动分析中...' },
  { key: 'learning_goal', name: '学习目标', defaultDesc: '自动分析中...' },
  { key: 'learning_history', name: '学习历史', defaultDesc: '自动分析中...' },
  { key: 'interest_preference', name: '学习风格偏好', defaultDesc: '自动分析中...' },
  { key: 'learning_pace', name: '学习节奏', defaultDesc: '自动分析中...' },
  { key: 'cognitive_level', name: '认知水平', defaultDesc: '自动分析中...' },
] as const

// ==========================================
// 3. 类型定义
// ==========================================
interface PendingFile { file?: File; url?: string; fileType: string; name: string }
interface Attachment { url: string; type: string; name: string }
interface DiagramData {
  type: string
  title: string
  summary: string
  spec: Record<string, unknown>
  render: {
    engine: string
    format: string
    source: string
  }
}
interface ChatMsg {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  illustrations?: string[]
  diagram?: DiagramData | null
  diagramGenerating?: boolean
}
interface ProfileDimension {
  readonly key: string
  readonly name: string
  readonly defaultDesc: string
  score: number | null
  desc: string
}

// ==========================================
// 4. Mermaid 初始化
// ==========================================
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
})

// ==========================================
// 5. 响应式状态
// ==========================================

// --- 聊天模式与输入 ---
const chatMode = ref('standard')
const userInput = ref('')
const isAIThinking = ref(false)
const isSpeaking = ref(false)
const chatScroll = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isExpandedInput = ref(false)

// --- 媒体生成开关 ---
const enableWebSearch = ref(false)
const needDiagram = ref(false)
const generateVideo = ref(false)
const hasToggledMedia = ref(false)

// --- 语音相关 ---
const isRecording = ref(false)
const isVoiceChatting = ref(false)

// --- 文件上传 ---
const uploadingFile = ref(false)
const docInput = ref<HTMLInputElement | null>(null)
const imgInput = ref<HTMLInputElement | null>(null)
const pendingFiles = ref<PendingFile[]>([])

// --- 会话管理 ---
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | undefined>(undefined)
const sessionSidebarCollapsed = ref(false)
const currentUserId = ref<string | number | null>(null)
const searchPopoverVisible = ref(false)
const searchKeyword = ref('')

// --- 消息列表 ---
const messages = ref<ChatMsg[]>([])
const streamingMsgId = ref<number | null>(null)
let abortController: AbortController | null = null

// --- 画像相关 ---
const profileUpdated = ref(false)
const memoryEnabled = ref(false)
const profileDimensions = ref<ProfileDimension[]>(
    DIMENSION_MAP.map(d => ({ ...d, score: null, desc: d.defaultDesc }))
)
let profilePollTimers: ReturnType<typeof setTimeout>[] = []

// --- FAB 悬浮按钮 ---
const fabPos = ref({ x: 16, y: 0 })
const isDragging = ref(false)
const showFabMenu = ref(false)
const isDimmed = ref(false)
const isStickRight = computed(() => fabPos.value.x > window.innerWidth / 2)

// --- FAB 拖拽状态 ---
let dragStartX = 0
let dragStartY = 0
let dragInitialX = 0
let dragInitialY = 0
let dragDistance = 0
let dimTimer: number | null = null

// --- 图解渲染 ---
let diagramRenderSeq = 0
const diagramSvgCache = ref<Map<string, string>>(new Map())

// --- 滚动状态 ---
let scrollPending = false

// ==========================================
// 6. 计算属性
// ==========================================
const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return sessions.value.filter(s => {
    const title = s.title || '新建对话'
    return title.toLowerCase().includes(keyword)
  })
})

const activeProfileDimensions = computed(() => {
  return profileDimensions.value.filter(d => d.score != null && d.desc && d.desc !== d.defaultDesc)
})

const showThinkingIndicator = computed(() => {
  if (!isAIThinking.value) return false
  if (chatMode.value === 'digital_human') return false
  const streamingMsg = messages.value.find(m => m.id === streamingMsgId.value)
  return !streamingMsg || !streamingMsg.content
})

// ==========================================
// 7. 工具函数
// ==========================================
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const renderMarkdown = (text: string) => marked.parse(text)

const getIcon = (key: string) => {
  const map: Record<string, any> = {
    knowledge_level: Medal,
    cognitive_style: Aim,
    error_pattern: Aim,
    learning_goal: Aim,
    learning_history: Timer,
    interest_preference: Setting,
    learning_pace: Timer,
    cognitive_level: Medal
  }
  return map[key] || Discount
}

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
// 8. 滚动相关函数
// ==========================================
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

const autoResize = () => {
  const el = textareaRef.value
  if (!el) return
  el.style.height = '24px'
  const currentHeight = el.scrollHeight

  if (currentHeight > 30) {
    isExpandedInput.value = true
    el.style.height = `${Math.min(currentHeight, 72)}px`
  } else {
    isExpandedInput.value = false
    el.style.height = '24px'
  }
}

// ==========================================
// 9. 图解渲染函数
// ==========================================
const renderMermaid = async (source: string): Promise<string> => {
  try {
    diagramRenderSeq += 1
    const { svg } = await mermaid.render(`mermaid-${Date.now()}-${diagramRenderSeq}`, source)
    return svg
  } catch {
    return `<pre class="mermaid-error">图解渲染失败</pre>`
  }
}

const getDiagramSvg = async (diagram: DiagramData): Promise<string> => {
  const cacheKey = diagram.render.source
  if (diagramSvgCache.value.has(cacheKey)) {
    return diagramSvgCache.value.get(cacheKey)!
  }
  const svg = await renderMermaid(diagram.render.source)
  diagramSvgCache.value.set(cacheKey, svg)
  diagramSvgCache.value = new Map(diagramSvgCache.value)
  scrollToBottom()
  return svg
}

// ==========================================
// 10. FAB 悬浮按钮函数
// ==========================================
const getPointerPosition = (e: MouseEvent | TouchEvent) => {
  if (e instanceof MouseEvent) {
    return { x: e.clientX, y: e.clientY }
  }
  const touch = e.touches[0]
  return touch ? { x: touch.clientX, y: touch.clientY } : null
}

const resetDimTimer = () => {
  isDimmed.value = false
  if (dimTimer) clearTimeout(dimTimer)
  dimTimer = window.setTimeout(() => {
    if (!showFabMenu.value && !isDragging.value) {
      isDimmed.value = true
    }
  }, 3000)
}

const startDrag = (e: MouseEvent | TouchEvent) => {
  if (showFabMenu.value) {
    showFabMenu.value = false
    return
  }
  const pointer = getPointerPosition(e)
  if (!pointer) return

  isDragging.value = true
  dragDistance = 0
  resetDimTimer()

  dragStartX = pointer.x
  dragStartY = pointer.y
  dragInitialX = fabPos.value.x
  dragInitialY = fabPos.value.y

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', endDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', endDrag)
}

const onDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return
  e.preventDefault()
  const pointer = getPointerPosition(e)
  if (!pointer) return

  const dx = pointer.x - dragStartX
  const dy = pointer.y - dragStartY
  dragDistance = Math.abs(dx) + Math.abs(dy)

  fabPos.value = {
    x: dragInitialX + dx,
    y: dragInitialY + dy
  }
}

const endDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', endDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', endDrag)

  if (dragDistance < 5) {
    showFabMenu.value = !showFabMenu.value
  }

  snapToEdge()
  resetDimTimer()
}

const snapToEdge = () => {
  const screenW = window.innerWidth
  const screenH = window.innerHeight
  const fabSize = 48
  const margin = 16

  let targetX = fabPos.value.x
  let targetY = fabPos.value.y

  if (targetX + fabSize / 2 > screenW / 2) {
    targetX = screenW - fabSize - margin
  } else {
    targetX = margin
  }

  const bottomBoundary = screenH - fabSize - 120
  if (targetY < margin) targetY = margin
  if (targetY > bottomBoundary) targetY = bottomBoundary

  fabPos.value = { x: targetX, y: targetY }
}

const setChatMode = (mode: string) => {
  chatMode.value = mode
  showFabMenu.value = false
  resetDimTimer()
}

const handleGlobalClick = (e: MouseEvent | TouchEvent) => {
  const target = e.target as HTMLElement
  if (showFabMenu.value && !target.closest('.fab-container')) {
    showFabMenu.value = false
  }
}

// ==========================================
// 11. 画像加载与轮询
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

    if (changed) {
      profileUpdated.value = true
      setTimeout(() => { profileUpdated.value = false }, 4000)
    }
  } catch {
  }
}

const scheduleProfilePoll = () => {
  profilePollTimers.forEach(t => clearTimeout(t))
  profilePollTimers = []

  const delays = [2000, 5000, 10000]
  delays.forEach((delay) => {
    const timer = setTimeout(() => fetchProfile(), delay)
    profilePollTimers.push(timer)
  })
}

const fetchCurrentUser = async () => {
  if (currentUserId.value) return
  try {
    const res = await getMe()
    currentUserId.value = res.data.data?.id ?? null
  } catch {
    currentUserId.value = null
  }
}

// ==========================================
// 12. 会话管理函数
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
  }
}

// ==========================================
// 13. 文件上传函数
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
  input.value = ''
}

const removeAttachment = (idx: number) => {
  pendingFiles.value.splice(idx, 1)
}

// ==========================================
// 14. 媒体生成开关函数
// ==========================================
const handleImageToggle = () => {
  hasToggledMedia.value = true
  if (needDiagram.value) {
    needDiagram.value = false
  } else {
    needDiagram.value = true
    generateVideo.value = false
  }
}

const handleVideoToggle = () => {
  hasToggledMedia.value = true
  if (generateVideo.value) {
    generateVideo.value = false
  } else {
    generateVideo.value = true
    needDiagram.value = false
  }
}

// ==========================================
// 15. 语音相关函数
// ==========================================
const handleVoiceToggle = () => {
  isRecording.value = !isRecording.value
  if (isRecording.value) {
    ElMessage.success({ message: '开始录音，请说话...', plain: true })
  } else {
    ElMessage.info({ message: '录音结束，正在发送...', plain: true })
  }
}

const handleVoiceChatToggle = () => {
  if (!isVoiceChatting.value) {
    isVoiceChatting.value = true
    chatMode.value = 'digital_human'
    ElMessage.success({ message: '已开启语音通话模式，您可以直接说话', plain: true })
  } else {
    isVoiceChatting.value = false
    ElMessage.info({ message: '已关闭语音通话模式', plain: true })
  }
}

// ==========================================
// 16. 发送消息函数
// ==========================================
const handleSend = async () => {
  const text = userInput.value.trim()
  const hasFiles = pendingFiles.value.length > 0
  if ((!text && !hasFiles) || isAIThinking.value) return
  const shouldGenerateDiagram = needDiagram.value

  if (!currentSessionId.value) {
    try {
      const res = await createSession()
      const session = res.data.data
      currentSessionId.value = session.id
      sessions.value.unshift({ id: session.id, title: session.title, updated_at: new Date().toISOString() })
    } catch {
    }
  }

  if (currentSessionId.value && text) {
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (session && (!session.title || session.title === '新建对话')) {
      session.title = text.length > 20 ? text.slice(0, 20) + '...' : text
    }
  }

  const userMsgId = Date.now()
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
  isExpandedInput.value = false
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = '24px'
    }
  })

  isAIThinking.value = true
  profileUpdated.value = false
  scrollToBottom()

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

  const aiMsgId = Date.now() + 1
  messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
  streamingMsgId.value = aiMsgId

  abortController = streamChat(
      {
        message: text || '请分析附件',
        session_id: currentSessionId.value,
        image_urls: imageUrls.length > 0 ? imageUrls : undefined,
        file_urls: fileUrls.length > 0 ? fileUrls : undefined,
        need_diagram: shouldGenerateDiagram,
        generate_video: generateVideo.value,
      },
      (chunk) => {
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.content += chunk
          scrollToBottom()
        }
      },
      () => {
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.diagramGenerating = false
        }
        isAIThinking.value = false
        streamingMsgId.value = null
        isSpeaking.value = chatMode.value === 'digital_human'
        if (isSpeaking.value) {
          setTimeout(() => { isSpeaking.value = false }, 3000)
        }
        scheduleProfilePoll()
        abortController = null
      },
      (err) => {
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.diagramGenerating = false
          if (!aiMsg.content) {
            aiMsg.content = `Generate failed: ${err.message}`
          }
        }
        isAIThinking.value = false
        streamingMsgId.value = null
        abortController = null
      },
      (evt) => {
        if (evt.event === 'status') {
          const payload = evt.data as { stage?: string; message?: string }
          if (payload?.stage !== 'diagram_generate' || !shouldGenerateDiagram) return
          const aiMsg = messages.value.find(m => m.id === aiMsgId)
          if (!aiMsg) return
          aiMsg.diagramGenerating = true
          scrollToBottom()
          return
        }

        if (evt.event === 'illustration') {
          const payload = evt.data as { path?: string }
          const imagePath = resolveIllustrationUrl(payload?.path || '')
          if (!imagePath) return
          const aiMsg = messages.value.find(m => m.id === aiMsgId)
          if (!aiMsg) return
          if (!aiMsg.illustrations) aiMsg.illustrations = []
          if (!aiMsg.illustrations.includes(imagePath)) {
            aiMsg.illustrations.push(imagePath)
          }
          return
        }

        if (evt.event === 'done') {
          const payload = evt.data as { resources?: { diagram?: DiagramData | null } }
          const diagram = payload?.resources?.diagram
          const aiMsg = messages.value.find(m => m.id === aiMsgId)
          if (!aiMsg) return
          aiMsg.diagramGenerating = false
          if (!diagram) return
          aiMsg.diagram = diagram
          scrollToBottom()
        }
      },
  )
}

// ==========================================
// 17. 监听器
// ==========================================
watch(chatMode, (newMode) => {
  if (newMode === 'digital_human') {
    sessionSidebarCollapsed.value = true
  } else if (newMode === 'standard') {
    sessionSidebarCollapsed.value = false
  }
})

watch(
  () => messages.value.map(m => m.diagram),
  (diagrams) => {
    diagrams.forEach((diagram) => {
      if (diagram && diagram.render?.source && !diagramSvgCache.value.has(diagram.render.source)) {
        getDiagramSvg(diagram)
      }
    })
  },
  { deep: true }
)

// ==========================================
// 18. 生命周期钩子
// ==========================================
onMounted(async () => {
  fabPos.value = { x: 16, y: window.innerHeight - 150 }
  resetDimTimer()
  document.addEventListener('mousedown', handleGlobalClick)
  document.addEventListener('touchstart', handleGlobalClick, { passive: true })

  await fetchCurrentUser()
  await loadSessions()
  if (sessions.value.length > 0) {
    await switchSession(sessions.value[0]!.id)
  }
  await fetchProfile()
})

onBeforeUnmount(() => {
  abortController?.abort()
  profilePollTimers.forEach(t => clearTimeout(t))
  if (dimTimer) clearTimeout(dimTimer)
  document.removeEventListener('mousedown', handleGlobalClick)
  document.removeEventListener('touchstart', handleGlobalClick)
})
</script>

<style scoped>
@import url('https://gs.jurieo.com/gemini/fonts-googleapis/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

.tutor-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #FFFFFF;
  font-family: 'Inter', system-ui, sans-serif;
  color: #0F172A;
  box-sizing: border-box;
}

.dashboard-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

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

.collapse-toggle-btn:hover:not([disabled]) {
  background: #E2E8F0;
  color: #0F172A;
}

.collapse-toggle-btn[disabled] {
  opacity: 0.3;
  cursor: not-allowed;
  background: transparent !important;
}

.collapse-toggle-btn svg {
  width: 1.3rem;
  height: 1.3rem;
}

.standard-sidebar-nav {
  padding: 8px 16px 16px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.nav-item {
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  color: #475569;
}

.nav-item:hover {
  background: #EBF0F5;
  color: #475569;
}

.nav-item.search-item {
  font-weight: 400 !important;
}

.nav-item.new-chat-btn {
  font-weight: 400 !important;
}

.nav-item.history-collapsed-btn {
  color: #475569;
}
.nav-item.history-collapsed-btn:hover {
  background: #E2E8F0;
  color: #0F172A;
}

.history-section-header {
  padding: 12px 16px 8px 16px;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0F172A;
  display: flex;
  align-items: center;
  gap: 8px;
  text-transform: none;
  letter-spacing: normal;
  user-select: none;
}
.history-section-header .el-icon {
  font-size: 1.25rem;
  color: #4F46E5;
}

.popover-search-container {
  display: flex;
  flex-direction: column;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #E2E8F0 inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #CBD5E1 inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #0891B2 inset !important;
}

.popover-session-scroll {
  max-height: 40vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.search-results-scroll {
  margin-top: 12px;
  max-height: 250px;
  overflow-y: auto;
  padding-right: 4px;
}

.search-results-scroll .session-empty {
  margin-top: 1rem;
  margin-bottom: 1rem;
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
  margin: 0;
  padding: 8px 16px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
}

.session-item {
  margin-bottom: 4px;
  color: #475569;
}
.session-item:hover {
  background: #FFFFFF;
  border-color: #E2E8F0;
  color: #334155;
}
.session-item.active {
  color: #4F46E5;
  font-weight: 600;
}

.session-icon {
  font-size: 1.15rem;
  color: #94A3B8;
  transition: color 0.2s;
}

.session-item.active .session-icon {
  color: #4F46E5;
}

.session-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
  min-width: 0;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 0.7rem;
  color: #94A3B8;
  white-space: nowrap;
}

.del-btn {
  opacity: 0;
  color: #EF4444;
  padding: 4px;
}

.session-item:hover .del-btn {
  opacity: 1;
}

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

.diagram-generating {
  width: min(560px, 100%);
  margin-top: 12px;
  padding: 10px 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #475569;
  background: #F8FAFC;
  border: 1px dashed #CBD5E1;
  border-radius: 10px;
  font-size: 0.85rem;
}

.diagram-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #CBD5E1;
  border-top-color: #4F46E5;
  border-radius: 50%;
  animation: diagramSpin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes diagramSpin {
  to {
    transform: rotate(360deg);
  }
}

.msg-diagram {
  margin-top: 12px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px;
  max-width: 560px;
}

.diagram-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.diagram-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #0F172A;
}

.diagram-type-tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  background: #E0E7FF;
  color: #4F46E5;
  border-radius: 4px;
  font-weight: 500;
}

.diagram-summary {
  font-size: 0.85rem;
  color: #64748B;
  margin-bottom: 12px;
  line-height: 1.5;
}

.diagram-svg-container {
  display: flex;
  justify-content: center;
  overflow-x: auto;
}

.diagram-svg-container :deep(svg) {
  max-width: 100%;
  height: auto;
}

.mermaid-error {
  color: #EF4444;
  font-size: 0.85rem;
  padding: 8px;
}

.session-empty {
  font-size: 0.8rem;
  color: #94A3B8;
  text-align: center;
  margin-top: 2rem;
}

.session-sidebar.collapsed {
  width: 64px;
}

.session-sidebar.collapsed .nav-text,
.session-sidebar.collapsed .session-info {
  display: none;
}

.session-sidebar.collapsed .sidebar-top-header,
.session-sidebar.collapsed .standard-sidebar-nav {
  width: 100%;
  padding-left: 0;
  padding-right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.session-sidebar.collapsed .sidebar-top-header {
  padding-top: 16px;
  padding-bottom: 8px;
}

.session-sidebar.collapsed .standard-sidebar-nav {
  padding-top: 8px;
  padding-bottom: 16px;
}

.session-sidebar.collapsed .collapse-toggle-btn,
.session-sidebar.collapsed .nav-item,
.session-sidebar.collapsed .session-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0 0 8px 0;
  width: 42px !important;
  height: 42px !important;
  min-width: 42px !important;
  max-width: 42px !important;
  min-height: 42px !important;
  max-height: 42px !important;
  box-sizing: border-box !important;
  border-radius: 8px;
}

.session-sidebar.collapsed .sidebar-top-header .collapse-toggle-btn {
  margin-bottom: 0;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: row;
  background: #FFFFFF;
  position: relative;
  overflow: hidden;
  height: 100%;
}

.digital-human-stage {
  width: 45%;
  min-width: 320px;
  max-width: 600px;
  background: #F8FAFC;
  border-right: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.digital-human-canvas-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94A3B8;
}

.digital-human-canvas-placeholder .placeholder-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.digital-human-status-overlay {
  position: absolute;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  padding: 12px 24px;
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  border: 1px solid #E2E8F0;
  transition: all 0.3s ease;
  z-index: 10;
}

.digital-human-status-overlay.active {
  border-color: #0EA5E9;
  box-shadow: 0 4px 20px rgba(14, 165, 233, 0.15);
}

.speech-wave {
  display: flex;
  gap: 3px;
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

.speech-wave span:nth-child(2) {
  animation-delay: 0.1s;
}

.speech-wave span:nth-child(3) {
  animation-delay: 0.2s;
}

@keyframes wave-anim {
  0%, 100% {
    height: 8px;
  }
  50% {
    height: 16px;
  }
}

.status-badge {
  font-size: 0.75rem;
  color: #64748B;
  font-family: 'Space Grotesk', monospace;
}

.chat-interaction-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  position: relative;
}

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

.welcome-icon {
  font-size: 2.5rem;
  color: #E2E8F0;
  margin-bottom: 1rem;
}

.welcome-banner h3 {
  font-size: 1.2rem;
  color: #0F172A;
  margin: 0 0 0.5rem;
}

.welcome-banner p {
  font-size: 0.9rem;
  line-height: 1.6;
  margin: 0;
}

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

.msg-avatar {
  flex-shrink: 0;
}

.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.ai-av {
  background: #0F172A;
  color: #FFF;
}

.user-av {
  background: #0891B2;
  color: #FFF;
}

.bubble-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-row.user .bubble-wrapper {
  align-items: flex-end;
}

.msg-meta {
  font-size: 0.75rem;
  color: #94A3B8;
  display: flex;
  gap: 8px;
}

.message-row.user .msg-meta {
  flex-direction: row-reverse;
}

.sender {
  font-weight: 600;
  color: #475569;
}

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

.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.attachment-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #0891B2;
  text-decoration: none;
  transition: border-color 0.2s;
}

.attachment-link:hover {
  border-color: #0891B2;
}

.thinking-bubble {
  background: #FAFAFA;
  border: 1px solid #E2E8F0;
  padding: 0.75rem 1.25rem;
  border-radius: 12px;
  border-top-left-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748B;
  font-size: 0.9rem;
}

.thinking-spinner {
  font-size: 1.2rem;
  color: #4F46E5;
}

.thinking-text {
  animation: pulse-text 1.5s infinite;
}

@keyframes pulse-text {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

.input-panel {
  padding: 0 0 1rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: transparent;
}

.attachments-preview {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  width: 80%;
  max-width: 800px;
  min-width: 300px;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.attachment-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 0.75rem;
  color: #475569;
}

.close-icon {
  cursor: pointer;
  color: #94A3B8;
}

.close-icon:hover {
  color: #EF4444;
}

.input-wrapper {
  width: 80%;
  max-width: 800px;
  min-width: 300px;
  background: #F9F9F9;
  border: 1px solid #E5E5E5;
  border-radius: 32px;
  padding: 10px 16px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px 12px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
}

.input-wrapper:focus-within {
  background: #FFFFFF;
  border-color: #D1D5DB;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
}

.toolbar-left {
  grid-column: 1;
  grid-row: 1;
  display: flex;
  align-items: center;
  gap: 4px;
}

.input-wrapper textarea {
  grid-column: 2;
  grid-row: 1;
  width: 100%;
  border: none;
  background: transparent;
  resize: none;
  height: 24px;
  max-height: 72px;
  overflow-y: auto;
  outline: none;
  font-family: inherit;
  font-size: 1rem;
  color: #0F172A;
  line-height: 1.5;
  padding: 0;
  margin: 0;
}

.toolbar-right {
  grid-column: 3;
  grid-row: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-wrapper.is-expanded {
  border-radius: 20px;
  padding: 12px 16px;
  align-items: end;
}

.input-wrapper.is-expanded textarea {
  grid-column: 1 / 4;
  grid-row: 1;
  margin-bottom: 4px;
}

.input-wrapper.is-expanded .toolbar-left {
  grid-column: 1 / 3;
  grid-row: 2;
}

.input-wrapper.is-expanded .toolbar-right {
  grid-column: 3;
  grid-row: 2;
  justify-self: end;
}

.input-wrapper textarea::placeholder {
  color: #94A3B8;
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

.media-gen-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.15rem;
  transition: all 0.2s;
  margin-left: 2px;
  padding: 0;
  background: transparent;
}

.media-gen-btn.btn-web {
  color: #374151;
}
.media-gen-btn.btn-web:hover {
  background: #E5E5E5;
  color: #111827;
}
.media-gen-btn.btn-web.active {
  color: #0EA5E9;
  background: #F0F9FF;
}

.active-media-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px 4px 4px;
  color: #0EA5E9;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  user-select: none;
  margin-left: 4px;
}

.active-media-chip:hover {
  background: #F0F9FF;
}

.active-media-chip .chip-icon-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: transparent;
  transition: background 0.2s ease;
}

.active-media-chip:hover .chip-icon-circle {
  background: #DBEAFE;
}

.active-media-chip .icon-default {
  display: inline-flex;
  font-size: 1.1rem;
}

.active-media-chip .icon-hover {
  display: none;
  font-size: 1.05rem;
}

.active-media-chip:hover .icon-default {
  display: none;
}

.active-media-chip:hover .icon-hover {
  display: inline-flex;
}

.voice-btn {
  background: transparent;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.2rem;
  margin: 0;
  transition: all 0.2s;
}

.voice-btn:hover {
  background: #E2E8F0;
  color: #111827;
}

.voice-btn.is-recording {
  background: #EF4444;
  color: #FFFFFF;
  animation: pulse-record 1.5s infinite;
}

.direct-voice-chat-btn {
  background: #000000;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
  flex-shrink: 0;
}

.direct-voice-chat-btn:hover {
  transform: scale(1.1);
  background: #1a1a1a;
  box-shadow: 0 6px 15px rgba(0, 0, 0, 0.3);
}

.voice-bars-icon {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 16px;
}

.voice-bars-icon .bar {
  width: 2.5px;
  background-color: #ffffff;
  border-radius: 1px;
  transition: height 0.2s ease;
}

.voice-bars-icon .bar:nth-child(1) {
  height: 8px;
}

.voice-bars-icon .bar:nth-child(2) {
  height: 14px;
}

.voice-bars-icon .bar:nth-child(3) {
  height: 10px;
}

.voice-bars-icon .bar:nth-child(4) {
  height: 6px;
}

.direct-voice-chat-btn.is-active {
  background: #4F46E5;
  animation: pulse-voice-glow 2s infinite;
}

.direct-voice-chat-btn.is-active .bar {
  animation: bar-dance 0.8s infinite ease-in-out alternate;
}

.direct-voice-chat-btn.is-active .bar:nth-child(1) {
  animation-delay: 0.0s;
}

.direct-voice-chat-btn.is-active .bar:nth-child(2) {
  animation-delay: 0.2s;
}

.direct-voice-chat-btn.is-active .bar:nth-child(3) {
  animation-delay: 0.1s;
}

.direct-voice-chat-btn.is-active .bar:nth-child(4) {
  animation-delay: 0.3s;
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #E2E8F0;
  color: #94A3B8;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  transition: all 0.3s ease;
  font-size: 1.2rem;
}

.send-btn.can-send {
  background: #000000;
  color: #FFFFFF;
  cursor: pointer;
}

.send-btn.can-send:hover {
  background: #333333;
}

@keyframes bar-dance {
  from { transform: scaleY(0.7); }
  to { transform: scaleY(1.5); }
}

@keyframes pulse-voice-glow {
  0% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.5); }
  70% { box-shadow: 0 0 0 10px rgba(79, 70, 229, 0); }
  100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
}

@keyframes pulse-record {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.input-footer {
  text-align: center;
  font-size: 0.7rem;
  color: #94A3B8;
  margin-top: 8px;
}

.profile-sidebar {
  width: 320px;
  padding: 1.5rem;
  background: #FAFAFA;
  border-left: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.header-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-title-row h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #0F172A;
  font-weight: 700;
}

.sync-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: #64748B;
  background: #F1F5F9;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.sync-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10B981;
}

.sidebar-desc {
  margin: 0;
  font-size: 0.8rem;
  color: #64748B;
  text-align: center;
}

.profile-feature-card {
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  border: 1px solid #F1F5F9;
}

.feature-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  width: 32px;
  height: 32px;
  background: #EFF6FF;
  color: #3B82F6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.header-title {
  font-size: 1rem;
  font-weight: 700;
  color: #1E293B;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.item-icon-box {
  width: 32px;
  height: 32px;
  background: #F1F5F9;
  color: #3B82F6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
  margin-top: 2px;
}

.item-text-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #334155;
}

.item-desc {
  font-size: 0.8rem;
  color: #64748B;
  line-height: 1.5;
}

.empty-state .empty-text {
  font-size: 0.85rem;
  color: #94A3B8;
  text-align: center;
  padding: 20px 0;
}

.long-term-memory-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 4px;
  margin-top: auto;
}

.memory-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.memory-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.memory-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #1E293B;
}

.info-icon {
  font-size: 0.9rem;
  color: #94A3B8;
  cursor: help;
}

.memory-switch-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch-status {
  font-size: 0.8rem;
  color: #64748B;
}

.memory-desc {
  margin: 0;
  font-size: 0.8rem;
  color: #64748B;
  line-height: 1.6;
}

:deep(.markdown-body) {
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem !important;
  background: transparent !important;
}

:deep(.markdown-body p) {
  margin-bottom: 0.5rem;
}

:deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}

:deep(.markdown-body pre) {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
}

.bubble.streaming::after {
  content: '▍';
  animation: cursor-blink 1s step-end infinite;
  color: #94A3B8;
  font-weight: 400;
}

@keyframes cursor-blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
  100% { opacity: 1; }
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 2px; }

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
  margin-top: -10vh;
}

.fab-container {
  position: fixed;
  z-index: 1000;
  touch-action: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.fab-container.is-dragging {
  transition: none !important;
}
.fab-container.is-dimmed {
  opacity: 0.6;
}
.fab-container.is-dimmed:hover {
  opacity: 1;
}

.fab-button {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #5A52FF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 16px rgba(90, 82, 255, 0.3);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.fab-button:hover {
  transform: scale(1.05);
  box-shadow: 0 8px 20px rgba(90, 82, 255, 0.4);
}
.fab-button:active {
  transform: scale(0.95);
}

.fab-menu {
  position: absolute;
  bottom: 70px;
  left: 0;
  width: 240px;
  background: #FFFFFF;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transform-origin: bottom left;
}
.fab-container.stick-right .fab-menu {
  left: auto;
  right: 0;
  transform-origin: bottom right;
}

.fab-menu-item {
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  background: transparent;
}
.fab-menu-item:hover {
  background: #F8FAFC;
}
.fab-menu-item.active {
  background: #F4F3FF;
}

.menu-icon-box {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F1F5F9;
  color: #64748B;
  font-size: 1.3rem;
  transition: all 0.2s;
  flex-shrink: 0;
}
.fab-menu-item.active .menu-icon-box {
  background: #EBE9FF;
  color: #5A52FF;
}

.menu-text-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.menu-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #334155;
  transition: color 0.2s;
}
.fab-menu-item.active .menu-title {
  color: #5A52FF;
}
.menu-desc {
  font-size: 0.75rem;
  color: #94A3B8;
}

.check-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #5A52FF;
  font-size: 1.2rem;
  display: flex;
}

.fab-menu-fade-enter-active,
.fab-menu-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fab-menu-fade-enter-from,
.fab-menu-fade-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}

.custom-plus-dropdown {
  border-radius: 16px !important;
  padding: 6px !important;
  border: 1px solid #E5E7EB !important;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1) !important;
}

.custom-plus-dropdown .el-dropdown-menu__item {
  border-radius: 10px;
  margin: 2px 6px;
  color: #374151 !important;
  font-size: 0.95rem !important;
  padding: 10px 20px !important;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-weight: 500;
}

.custom-plus-dropdown .el-dropdown-menu__item:hover {
  background-color: #F3F4F6 !important;
  color: #111827 !important;
}

.custom-plus-dropdown .el-dropdown-menu__item .el-icon {
  font-size: 1.2rem;
  color: #374151 !important;
  margin-right: 4px;
}

.custom-plus-dropdown .el-dropdown-menu__item--divided {
  margin-top: 6px !important;
  padding-top: 6px !important;
  border-top: 1px solid #D1D5DB !important;
}

.custom-plus-dropdown .el-dropdown-menu__item--divided::before {
  display: none !important;
}
</style>
