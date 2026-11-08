<template>
  <div class="tutor-dashboard">
    <main class="dashboard-main">
      <!-- 左侧会话历史导航栏 -->
      <ChatSidebar :sessions="sessions" :active-id="currentSessionId"
        @create="newSession" @select="switchSession" @archive="archiveSession" />

      <!-- 右侧主对话舞台 -->
      <section class="chat-container">
        <div class="chat-interaction-area">
          <div class="chat-viewport" ref="chatScroll" @scroll.passive="handleViewportScroll">
            <!-- 空状态：学术欢迎台 + 启发式快捷提问卡片 -->
            <div class="welcome-stage" v-if="messages.length === 0 && !uploadingFile">
              <div class="welcome-hero">
                <div class="welcome-seal" aria-hidden="true">
                  <Service />
                </div>
                <h2 class="welcome-title">{{ greetingText }}，{{ userName }}。</h2>
                <p class="welcome-subtitle">
                  我是你的个性化 AI 导师 Mentorly。支持知识库检索、视觉课件解析、结构化图解与教学动画视频生成。
                </p>
              </div>

              <div class="starter-prompts-grid">
                <button
                  v-for="(item, idx) in starterPrompts"
                  :key="idx"
                  type="button"
                  class="starter-card"
                  @click="applyStarterPrompt(item)"
                >
                  <div class="starter-card-top">
                    <span class="starter-tag" :class="`is-${item.tone}`">{{ item.badge }}</span>
                    <span class="starter-arrow" aria-hidden="true">↗</span>
                  </div>
                  <strong class="starter-card-title">{{ item.title }}</strong>
                  <span class="starter-card-desc">{{ item.prompt }}</span>
                </button>
              </div>
            </div>

            <!-- 居中阅读轨道 -->
            <div v-else class="chat-stream-track">
              <!-- 本地附件上传等待状态 -->
              <div
                v-if="uploadingFile"
                class="thinking-indicator-row"
              >
                <div class="ai-msg-header">
                  <span class="mentor-seal"><Service /></span>
                  <span class="sender">Mentorly</span>
                  <span class="streaming-live-pill">正在上传附件</span>
                </div>
                <div class="pre-answer-state" aria-live="polite">
                  <div class="pre-answer-head">
                    <span class="thinking-core" aria-hidden="true">
                      <i></i><i></i><i></i>
                    </span>
                    <div>
                      <strong>正在上传附件</strong>
                      <span>上传完成后将提交问题，请稍候。</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 消息列表 -->
              <template v-for="msg in messages" :key="msg.id">
                <article
                  v-if="
                    msg.role === 'user'
                    || messageContent(msg)
                    || msg.attachments?.length
                    || msg.run
                    || messageError(msg)
                  "
                  :class="['message-turn', msg.role, { 'is-streaming': isStreamingMessage(msg) }]"
                >
                  <!-- A. 用户提问（右侧凝练胶囊气泡） -->
                  <template v-if="msg.role === 'user'">
                    <div class="user-turn-container">
                      <!-- 图片附件画廊 -->
                      <div
                        v-if="getImageAttachments(msg.attachments).length"
                        class="message-image-gallery"
                        :class="getImageGalleryClass(msg.attachments)"
                      >
                        <img
                          v-for="(att, imageIndex) in getImageAttachments(msg.attachments)"
                          :key="`${att.url}-${imageIndex}`"
                          :src="att.url"
                          :alt="att.name || `图片 ${imageIndex + 1}`"
                          class="message-image"
                          loading="lazy"
                          @click.stop="triggerImagePreview(getImagePreviewUrls(msg.attachments), imageIndex)"
                        />
                      </div>

                      <!-- 文档附件列表 -->
                      <div
                        v-if="getDocumentAttachments(msg.attachments).length"
                        class="message-file-list"
                      >
                        <a
                          v-for="att in getDocumentAttachments(msg.attachments)"
                          :key="att.url || att.name"
                          :href="att.url"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="message-file-card"
                        >
                          <span
                            class="file-icon-box"
                            :style="{ backgroundColor: getDocumentIconColor(getDocumentType(att.name)) }"
                          >
                            <Document class="file-icon" aria-hidden="true" />
                          </span>
                          <span class="file-copy">
                            <strong :title="att.name">{{ att.name || '文档附件' }}</strong>
                            <small>{{ formatFileSize(att.size) || getDocumentType(att.name).toUpperCase() }}</small>
                          </span>
                          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                            <path d="M7 5h8v8M14.5 5.5 6 14" />
                          </svg>
                        </a>
                      </div>

                      <!-- 用户文本气泡 -->
                      <div
                        v-if="messageContent(msg)"
                        class="user-capsule-bubble"
                      >
                        <div class="user-plain-text">{{ messageContent(msg) }}</div>
                      </div>

                      <!-- 用户消息底部元信息与快捷复制 -->
                      <div class="user-turn-meta">
                        <span class="turn-time">{{ msg.time }}</span>
                        <button
                          v-if="messageContent(msg)"
                          type="button"
                          class="turn-action-btn"
                          :class="{ 'is-copied': copiedMsgId === msg.id }"
                          @click.stop="handleCopyMessage(msg)"
                          title="复制提问"
                        >
                          <svg v-if="copiedMsgId === msg.id" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                            <path d="M3.2 8.3 6.4 11.5 12.8 4.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
                          </svg>
                          <svg v-else viewBox="0 0 16 16" fill="none" aria-hidden="true">
                            <rect x="5.2" y="5.2" width="7.6" height="7.6" rx="1.4" stroke="currentColor" stroke-width="1.35" />
                            <path d="M3.5 10.2H3A1.2 1.2 0 0 1 1.8 9V3A1.2 1.2 0 0 1 3 1.8h6A1.2 1.2 0 0 1 10.2 3v.5" stroke="currentColor" stroke-width="1.35" />
                          </svg>
                          <span>{{ copiedMsgId === msg.id ? '已复制' : '复制' }}</span>
                        </button>
                      </div>
                    </div>
                  </template>

                  <!-- B. AI 导师回答（开放式学术手稿画布 Unboxed Canvas） -->
                  <template v-else>
                    <div class="ai-turn-container">
                      <header class="ai-msg-header">
                        <span class="mentor-seal" :class="{ 'is-pulsing': isStreamingMessage(msg) }">
                          <Service />
                        </span>
                        <span class="sender">Mentorly</span>
                        <span class="turn-time">{{ msg.time }}</span>
                        <span v-if="isStreamingMessage(msg)" class="streaming-live-pill">
                          <i class="live-dot"></i>
                          {{ connection === 'connected' ? msg.run?.phase_label : '等待状态同步' }}
                        </span>
                      </header>

                      <div class="ai-canvas-body">
                        <ChatRunStatus
                          v-if="msg.run"
                          :run="msg.run"
                          :connection="msg.run.run_id === currentRun?.run_id ? connection : undefined"
                        />

                        <!-- 回答正文直接读取运行快照 -->
                        <div
                          v-if="Boolean(messageContent(msg)) || isStreamingMessage(msg)"
                          class="ai-manuscript-content"
                        >
                          <TutorMessageContent
                            :content="messageContent(msg)"
                            :is-streaming="isStreamingMessage(msg) && msg.run?.phase === 'streaming' && connection === 'connected'"
                          />
                        </div>

                        <!-- 4. 多模态生成产物与知识库来源（位于回答正文末尾呈现） -->
                        <ChatArtifactsShowcase v-if="msg.run" :run="msg.run" />

                        <!-- 3. 失败或超时专用错误卡片 -->
                        <div
                          v-if="messageError(msg)"
                          class="assistant-failed-card"
                        >
                          <div class="failed-header">
                            <span class="failed-icon" aria-hidden="true">
                              <svg viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                              </svg>
                            </span>
                            <strong class="failed-title">生成失败</strong>
                          </div>
                          <p class="failed-message">{{ messageError(msg) }}</p>
                          <div class="failed-actions">
                            <button
                              type="button"
                              class="failed-retry-btn"
                              :disabled="isResponding"
                              @click.stop="handleRetryAssistantMessage(msg)"
                            >
                              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                                <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round" />
                              </svg>
                              重新提问
                            </button>
                          </div>
                        </div>

                        <!-- 4. AI 回答底部操作栏 -->
                        <footer
                          v-if="messageContent(msg) && !isStreamingMessage(msg)"
                          class="ai-msg-toolbar"
                        >
                          <button
                            type="button"
                            class="toolbar-btn"
                            :class="{ 'is-copied': copiedMsgId === msg.id }"
                            @click.stop="handleCopyMessage(msg)"
                          >
                            <svg v-if="copiedMsgId === msg.id" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                              <path d="M3.2 8.3 6.4 11.5 12.8 4.8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
                            </svg>
                            <svg v-else viewBox="0 0 16 16" fill="none" aria-hidden="true">
                              <rect x="5.2" y="5.2" width="7.6" height="7.6" rx="1.4" stroke="currentColor" stroke-width="1.35" />
                              <path d="M3.5 10.2H3A1.2 1.2 0 0 1 1.8 9V3A1.2 1.2 0 0 1 3 1.8h6A1.2 1.2 0 0 1 10.2 3v.5" stroke="currentColor" stroke-width="1.35" />
                            </svg>
                            <span>{{ copiedMsgId === msg.id ? '已复制回答' : '复制回答' }}</span>
                          </button>

                          <button
                            type="button"
                            class="toolbar-btn"
                            :disabled="isResponding"
                            @click.stop="handleRetryAssistantMessage(msg)"
                            title="重新生成本轮回答"
                          >
                            <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
                              <path d="M2.8 3.2v3.6h3.6M13.2 12.8V9.2H9.6M12.6 6.2A5.2 5.2 0 0 0 4.1 4.5L2.8 6.8M3.4 9.8a5.2 5.2 0 0 0 8.5 1.7l1.3-2.3" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" />
                            </svg>
                            <span>重新生成</span>
                          </button>
                        </footer>
                      </div>
                    </div>
                  </template>
                </article>
              </template>
            </div>
          </div>

          <!-- 悬浮「回到底部」胶囊按钮 -->
          <transition name="scroll-pill-fade">
            <button
              v-if="showScrollToBottom && messages.length > 0"
              type="button"
              class="scroll-to-bottom-pill"
              @click="scrollToBottomImmediate"
            >
              <span v-if="isResponding" class="pill-live-dot" aria-hidden="true"></span>
              <span>{{ isResponding ? '正在生成新内容 · 回到底部' : '回到底部' }}</span>
              <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M8 3.2v9.6M4.2 9l3.8 3.8L11.8 9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </transition>

          <!-- 底部多模态输入舱 -->
          <ChatComposer ref="composerRef" v-model:text="userInput" v-model:mode="mode"
            v-model:files="pendingFiles" :busy="isResponding" :phase="currentRun?.phase"
            :submit-phase="submitPhase" @submit="handleSend" @cancel="stopGeneration" />
        </div>


      </section>
    </main>

    <!-- 删除对话确认框 -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="isDeleteConfirmVisible" class="custom-modal-overlay delete-confirm-overlay" @click.self="cancelDeleteSession">
          <div class="delete-confirm-dialog">
            <div class="delete-confirm-icon">
              <Delete />
            </div>
            <h3 class="delete-confirm-title">删除对话</h3>
            <p class="delete-confirm-desc">确定要删除「{{ sessionToDeleteTitle }}」吗？删除后将无法恢复。</p>
            <div class="delete-confirm-actions">
              <button type="button" class="btn btn-cancel" @click="cancelDeleteSession">取消</button>
              <button type="button" class="btn btn-danger" @click="confirmArchiveSession">确认删除</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 全局图片预览灯箱 -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="imgPreviewVisible" class="custom-modal-overlay img-preview-overlay" @click="imgPreviewVisible = false">
          <div class="img-preview-container" @click.stop>
            <img :src="imgPreviewUrl" class="img-preview-content" alt="大图预览" />
            <button type="button" class="img-preview-close-btn" @click="imgPreviewVisible = false" aria-label="关闭预览">
              <Close class="close-icon" />
            </button>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated, computed } from 'vue'
import {
  PhHeadset as Service,
  PhFileText as Document,
  PhTrash as Delete,
  PhX as Close,
} from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import { getErrorMessage } from '@/shared/api/http'
import { ensureCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import ChatSidebar from '@/features/chat/components/ChatSidebar.vue'
import ChatComposer from '@/features/chat/components/ChatComposer.vue'
import TutorMessageContent from '@/features/chat/components/TutorMessageContent.vue'
import ChatRunStatus from '@/features/chat/components/ChatRunStatus.vue'
import ChatArtifactsShowcase from '@/features/chat/components/ChatArtifactsShowcase.vue'

import { useChatRun } from '@/features/chat/composables/useChatRun'
import {
  uploadFile,
  getSessions,
  createSession,
  deleteSession,
  getChatHistory,
} from '@/features/chat/api/chat'
import type {
  ChatSession,
} from '@/features/chat/types/chat'
import { isRunActive, type RunState } from '@/features/chat/types/chatRun'
import { consumeTutorEntryIntent } from '@/features/chat/model/tutorEntryIntent'
import {
  type PendingFile,
  type Attachment,
  type ChatMsg,
  getDocumentType,
  getDocumentIconColor,
  formatFileSize,
} from './tutorUtils'

defineOptions({ name: 'Tutor' })

interface StarterPrompt {
  badge: string
  tone: 'teal' | 'purple' | 'blue' | 'slate'
  title: string
  prompt: string
  mode?: 'diagram' | 'video' | 'default'
}

const DEFAULT_SESSION_TITLE = '新对话'
const SESSION_TITLE_REFRESH_DELAYS = [300, 800, 1500, 3000]
const { userName } = useCurrentUser()

const composerRef = ref<InstanceType<typeof ChatComposer> | null>(null)
const userInput = ref('')
const chatScroll = ref<HTMLElement | null>(null)
const showScrollToBottom = ref(false)
const copiedMsgId = ref<number | null>(null)
let copiedResetTimer: ReturnType<typeof setTimeout> | null = null

const mode = ref<'default' | 'diagram' | 'video'>('default')

const greetingText = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const starterPrompts: StarterPrompt[] = [
  {
    badge: '结构化图解',
    tone: 'teal',
    title: '梳理核心算法思想',
    prompt: '请结合结构化图解，帮我梳理「动态规划（DP）」从暴力递归到状态转移方程的推导套路。',
    mode: 'diagram',
  },
  {
    badge: '教学动画视频',
    tone: 'purple',
    title: '生成分镜动画精讲',
    prompt: '请帮我生成一段讲解「二叉树层序遍历与队列进出机制」的教学动画视频。',
    mode: 'video',
  },
  {
    badge: '深度概念辨析',
    tone: 'blue',
    title: '攻克高频疑难考点',
    prompt: '对比解析操作系统中「进程、线程与协程」在上下文切换开销与内存隔离上的本质区别。',
    mode: 'default',
  },
  {
    badge: '代码诊断推演',
    tone: 'slate',
    title: '排查边界与复杂度',
    prompt: '二分查找中 left <= right 和 left < right 的区间开闭原则是什么？如何避免死循环？',
    mode: 'default',
  },
]

const applyStarterPrompt = (item: StarterPrompt) => {
  userInput.value = item.prompt
  mode.value = item.mode || 'default'
  nextTick(() => composerRef.value?.focus())
}

const imgPreviewVisible = ref(false)
const imgPreviewUrl = ref('')
const triggerImagePreview = (urls: string[], index: number) => {
  const url = urls[index]
  if (url) {
    imgPreviewUrl.value = url
    imgPreviewVisible.value = true
  }
}

const isDeleteConfirmVisible = ref(false)
const sessionToDeleteId = ref<string | null>(null)
const sessionToDeleteTitle = ref('')

const submitPhase = ref<'idle' | 'uploading' | 'submitting'>('idle')
const uploadingFile = computed(() => submitPhase.value === 'uploading')
const pendingFiles = ref<PendingFile[]>([])
// 会话列表与分组
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | undefined>(undefined)
const messages = ref<ChatMsg[]>([])
const currentRun = computed(() => messages.value.find(message => message.run && isRunActive(message.run))?.run)
const isResponding = computed(() => submitPhase.value !== 'idle' || Boolean(currentRun.value))
const chatRun = useChatRun()
const { connection } = chatRun
let scrollPending = false
let lastAutoScrollAt = 0
const STREAM_SCROLL_INTERVAL_MS = 64
const STREAM_AUTO_SCROLL_BOTTOM_GAP_PX = 120

const applyRun = (messageId: number, state: RunState) => {
  const message = messages.value.find(item => item.id === messageId)
  if (!message) return
  const wasActive = message.run && isRunActive(message.run)
  message.run = state
  if (wasActive && state.status === 'completed' && currentSessionId.value) {
    void refreshSessionTitleWithRetry(currentSessionId.value)
  }
  scrollToBottomThrottled()
}

const stopGeneration = async () => {
  try { if (currentRun.value) await chatRun.cancel(currentRun.value.run_id) }
  catch (error) { toast.error(getErrorMessage(error, '停止失败')) }
}

const isStreamingMessage = (msg: ChatMsg) => Boolean(msg.run && isRunActive(msg.run))
const messageContent = (msg: ChatMsg) => msg.run?.content ?? msg.content
const messageError = (msg: ChatMsg) => msg.localError || (
  msg.run?.status === 'failed' || msg.run?.status === 'interrupted' ? msg.run.error : ''
)

const getImageAttachments = (attachments?: Attachment[] | null) => (
  (attachments || []).filter(item => item.type === 'image' && Boolean(item.url))
)

const getDocumentAttachments = (attachments?: Attachment[] | null) => (
  (attachments || []).filter(item => item.type !== 'image')
)

const getImagePreviewUrls = (attachments?: Attachment[] | null) => (
  getImageAttachments(attachments).map(item => item.url)
)

const getImageGalleryClass = (attachments?: Attachment[] | null) => {
  const count = getImageAttachments(attachments).length
  if (count <= 1) return 'is-single'
  if (count === 2) return 'is-pair'
  return 'is-grid'
}

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    toast.error('复制失败，请重试')
    return false
  }
}

const handleCopyMessage = async (msg: ChatMsg) => {
  const content = messageContent(msg).trim()
  if (!content) return
  const ok = await copyToClipboard(content)
  if (!ok) return
  copiedMsgId.value = msg.id
  if (copiedResetTimer) clearTimeout(copiedResetTimer)
  copiedResetTimer = setTimeout(() => {
    if (copiedMsgId.value === msg.id) {
      copiedMsgId.value = null
    }
  }, 2000)
}

const handleViewportScroll = () => {
  const el = chatScroll.value
  if (!el) return
  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
  showScrollToBottom.value = gap > 150
}

const scrollToBottom = () => {
  if (scrollPending) return
  scrollPending = true

  nextTick(() => {
    requestAnimationFrame(() => {
      if (chatScroll.value) {
        chatScroll.value.scrollTop = chatScroll.value.scrollHeight
        showScrollToBottom.value = false
      }
      scrollPending = false
    })
  })
}

const scrollToBottomImmediate = () => {
  if (!chatScroll.value) return
  chatScroll.value.scrollTo({
    top: chatScroll.value.scrollHeight,
    behavior: 'smooth',
  })
  showScrollToBottom.value = false
}

const scrollToBottomThrottled = (force = false) => {
  if (!force && !isNearBottom()) {
    handleViewportScroll()
    return
  }
  const nowTs = Date.now()
  if (!force && nowTs - lastAutoScrollAt < STREAM_SCROLL_INTERVAL_MS) {
    return
  }
  lastAutoScrollAt = nowTs
  scrollToBottom()
}

const isNearBottom = () => {
  const el = chatScroll.value
  if (!el) return true
  const gap = el.scrollHeight - el.scrollTop - el.clientHeight
  return gap <= STREAM_AUTO_SCROLL_BOTTOM_GAP_PX
}

const loadSessions = async () => {
  try {
    const res = await getSessions()
    sessions.value = res.data.data || []
  } catch {
    sessions.value = []
  }
}

const refreshSessionTitleWithRetry = async (sessionId: string) => {
  for (const delay of SESSION_TITLE_REFRESH_DELAYS) {
    await new Promise(resolve => setTimeout(resolve, delay))

    try {
      const res = await getSessions()
      const nextSessions = res.data.data || []

      const refreshed = nextSessions.find(s => s.id === sessionId)
      if (refreshed?.title && refreshed.title !== DEFAULT_SESSION_TITLE) {
        sessions.value = nextSessions
        return
      }
    } catch {
      return
    }
  }
}

const newSession = () => {
  sessionSwitchToken++
  submitPhase.value = 'idle'
  chatRun.close()
  currentSessionId.value = undefined
  messages.value = []
  showScrollToBottom.value = false
  clearPendingFiles()
}

const loadHistoryFromAPI = async (
  sessionId: string,
  shouldApply: () => boolean = () => true,
): Promise<boolean> => {
  try {
    const res = await getChatHistory(sessionId)
    const history = res.data.data || []
    const mapped: ChatMsg[] = history.map((msg) => {
      const contentParts = msg.content || []
      const textContent = contentParts
        .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
        .map(part => part.text)
        .join('')
      const attachments = contentParts
        .filter(part => part.type !== 'text')
        .map(part => ({ url: part.url, type: part.file_type, name: part.original_name,
          size: part.size_bytes, mimeType: part.mime_type }))
      return {
        id: msg.id,
        role: msg.role === 'user' ? 'user' : 'ai',
        content: textContent,
        time: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        attachments,
        run: msg.run ?? undefined,
      }
    })
    if (!shouldApply()) return false
    messages.value = mapped
    return true
  } catch (err) {
    if (shouldApply()) {
      toast.error({ message: getErrorMessage(err, '加载会话历史失败'), plain: true })
    }
    return false
  }
}

let sessionSwitchToken = 0
let nextMessageId = Date.now()

const switchSession = async (sessionId: string) => {
  const switchToken = ++sessionSwitchToken
  submitPhase.value = 'idle'
  clearPendingFiles()
  chatRun.close()
  currentSessionId.value = sessionId
  messages.value = []
  showScrollToBottom.value = false
  if (!await loadHistoryFromAPI(sessionId, () => switchToken === sessionSwitchToken)) return
  if (switchToken !== sessionSwitchToken) return
  const running = messages.value.find(message => message.run && isRunActive(message.run))
  if (running?.run) chatRun.connect(running.run, state => applyRun(running.id, state))
  scrollToBottom()
}

const archiveSession = (sessionId: string) => {
  const targetSession = sessions.value.find(session => session.id === sessionId)
  sessionToDeleteTitle.value = targetSession?.title?.trim() || '新对话'
  sessionToDeleteId.value = sessionId
  isDeleteConfirmVisible.value = true
}

const cancelDeleteSession = () => {
  isDeleteConfirmVisible.value = false
  sessionToDeleteId.value = null
  sessionToDeleteTitle.value = ''
}

const confirmArchiveSession = async () => {
  const sessionId = sessionToDeleteId.value
  if (!sessionId) return

  isDeleteConfirmVisible.value = false
  sessionToDeleteId.value = null

  try {
    if (currentSessionId.value === sessionId) chatRun.close()
    await deleteSession(sessionId)
    sessions.value = sessions.value.filter(session => session.id !== sessionId)

    if (currentSessionId.value === sessionId) {
      newSession()

      if (sessions.value.length > 0) {
        await switchSession(sessions.value[0]!.id)
      }
    }

    toast.success('会话已删除')
  } catch (error) {
    toast.error(getErrorMessage(error) || '删除会话失败，请稍后重试')
  }
}

const clearPendingFiles = () => {
  pendingFiles.value.forEach(file => {
    if (file.localUrl) URL.revokeObjectURL(file.localUrl)
  })
  pendingFiles.value = []
}

const handleSend = async () => {
  if (isResponding.value || (!userInput.value.trim() && !pendingFiles.value.length)) return
  const text = userInput.value.trim()
  const files = [...pendingFiles.value]
  const requestedMode = mode.value
  const token = sessionSwitchToken
  submitPhase.value = 'submitting'
  const aiMsg: ChatMsg = { id: ++nextMessageId, role: 'ai', content: '', time: now() }
  try {
    if (!currentSessionId.value) {
      const { data } = await createSession()
      sessions.value.unshift({ ...data.data, updated_at: new Date().toISOString() })
      if (token !== sessionSwitchToken) return
      currentSessionId.value = data.data.id
    }
    const sessionId = currentSessionId.value
    const userMsg: ChatMsg = {
      id: ++nextMessageId, role: 'user', content: text, time: now(),
      attachments: files.map(file => ({ url: file.localUrl || file.url || '',
        type: file.fileType, name: file.name, size: file.size, mimeType: file.mimeType })),
    }
    messages.value.push(userMsg, aiMsg)
    userInput.value = ''
    scrollToBottom()
    submitPhase.value = files.length ? 'uploading' : 'submitting'
    const attachments = await Promise.all(files.map(async file => {
      if (file.url) return { url: file.url, file_type: file.fileType, original_name: file.name,
        size_bytes: file.size, mime_type: file.mimeType }
      if (!file.file) throw new Error('附件内容不存在')
      return (await uploadFile(file.file, sessionId)).data.data
    }))
    if (token !== sessionSwitchToken) return
    const displayed = messages.value.find(message => message.id === userMsg.id)!
    displayed.attachments = attachments.map(file => ({ url: file.url, type: file.file_type,
      name: file.original_name, size: file.size_bytes, mimeType: file.mime_type }))
    clearPendingFiles()
    submitPhase.value = 'submitting'
    await chatRun.start({
      question: text, session_id: sessionId, attachments,
      diagram_mode: requestedMode === 'diagram' ? 'required' : 'auto',
      video_mode: requestedMode === 'video',
    }, state => applyRun(aiMsg.id, state))
  } catch (error) {
    if (token !== sessionSwitchToken) return
    const message = messages.value.find(item => item.id === aiMsg.id)
    const detail = getErrorMessage(error, '发送失败，请重试')
    if (message) message.localError = detail
    else toast.error(detail)
  } finally {
    if (token === sessionSwitchToken) submitPhase.value = 'idle'
  }
}

const handleRetryAssistantMessage = (target: ChatMsg) => {
  if (isResponding.value) return
  const index = messages.value.findIndex(message => message.id === target.id)
  const previous = messages.value.slice(0, index).reverse().find(message => message.role === 'user')
  if (!previous) return
  userInput.value = previous.content
  // 上传失败时保留原始 File；已上传的附件直接复用 URL。
  if (!pendingFiles.value.length) {
    pendingFiles.value = (previous.attachments || []).map(file => ({
      url: file.url, fileType: file.type, name: file.name, size: file.size, mimeType: file.mimeType,
    }))
  }
  void handleSend()
}

onMounted(async () => {
  const shouldStartBlankSession = consumeTutorEntryIntent()

  await ensureCurrentUser()
  await loadSessions()

  if (shouldStartBlankSession) {
    newSession()
    return
  }

  if (currentSessionId.value) {
    await switchSession(currentSessionId.value)
  } else if (sessions.value.length > 0) {
    await switchSession(sessions.value[0]!.id)
  }
})

let tutorWasDeactivated = false

onActivated(async () => {
  if (!tutorWasDeactivated) return
  tutorWasDeactivated = false

  if (currentSessionId.value) {
    await switchSession(currentSessionId.value)
  }
})

onDeactivated(() => {
  tutorWasDeactivated = true
  sessionSwitchToken++
  submitPhase.value = 'idle'
  chatRun.close()
})

onBeforeUnmount(() => {
  sessionSwitchToken++
  chatRun.close()
  clearPendingFiles()
  if (copiedResetTimer) clearTimeout(copiedResetTimer)
})
</script>

<style scoped>
@keyframes thinking-ring-turn {
  to { transform: rotate(360deg); }
}

/* ============================================================
   1. 整体页面骨架
   ============================================================ */
.tutor-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background-color: var(--color-surface);
  font-family: var(--font-sans);
  color: var(--color-text);
  box-sizing: border-box;
}

.dashboard-main {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ============================================================
   2. 主对话视口与学术欢迎台 (Welcome Stage & Viewport)
   ============================================================ */
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: row;
  background: var(--color-surface);
  position: relative;
  overflow: hidden;
  height: 100%;
  min-width: 0;
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
  padding: 28px clamp(16px, 4vw, 48px) 24px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

/* 空状态：欢迎台与启发式提问网格 */
.welcome-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 0 32px;
  gap: 32px;
}

.welcome-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
}

.welcome-seal {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 4px;
  box-shadow: 0 8px 20px rgba(70, 184, 180, 0.14);
}

.welcome-title {
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--color-text-strong);
  letter-spacing: -0.025em;
  text-wrap: balance;
}

.welcome-subtitle {
  margin: 0;
  max-width: 54ch;
  font-size: 0.92rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  text-wrap: pretty;
}

.starter-prompts-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.starter-card {
  height: auto;
  padding: 14px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  gap: 6px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    background-color 180ms ease,
    transform 180ms cubic-bezier(0.32, 0.72, 0, 1),
    box-shadow 180ms ease;
}

.starter-card:hover {
  background: var(--color-bg);
  border-color: var(--color-primary);
  transform: translateY(-1.5px);
  box-shadow: var(--shadow-xs);
}

.starter-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.starter-tag {
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 650;
}

.starter-tag.is-teal {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.starter-tag.is-purple {
  background: var(--cat-eval-soft);
  color: #6d28d9;
}

.starter-tag.is-blue {
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
}

.starter-tag.is-slate {
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-light);
}

.starter-arrow {
  font-size: 13px;
  color: var(--color-text-faint);
  transition: transform 160ms ease, color 160ms ease;
}

.starter-card:hover .starter-arrow {
  color: var(--color-primary-text);
  transform: translate(2px, -2px);
}

.starter-card-title {
  color: var(--color-text-strong);
  font-size: 0.9rem;
  font-weight: 650;
}

.starter-card-desc {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  line-height: 1.5;
  font-weight: 400;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ============================================================
   3. 居中阅读轴线与非对称消息拓扑 (Asymmetric Message Stream)
   ============================================================ */
.chat-stream-track {
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding-bottom: 12px;
}

.message-turn {
  display: flex;
  flex-direction: column;
  width: 100%;
  animation: turn-enter 280ms cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes turn-enter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* A. 用户提问（右侧凝练冰川胶囊） */
.user-turn-container {
  align-self: flex-end;
  max-width: min(640px, 84%);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 7px;
}

.user-capsule-bubble {
  padding: 11px 16px;
  background: var(--color-surface-hover);
  border: 1px solid var(--color-primary-border);
  border-radius: 18px 18px 4px 18px;
  color: var(--color-text-strong);
  box-shadow: 0 1px 2px rgba(32, 95, 103, 0.04);
}

.user-plain-text {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 0.95rem;
  font-weight: 450;
  line-height: 1.62;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.user-turn-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 2px;
  opacity: 0;
  transition: opacity 150ms ease;
}

.message-turn.user:hover .user-turn-meta,
.user-turn-meta:focus-within {
  opacity: 1;
}

.turn-time {
  font-size: 0.7rem;
  color: var(--color-text-faint);
  font-variant-numeric: tabular-nums;
}

.turn-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 6px;
  background: transparent;
  border: none;
  border-radius: 5px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}

.turn-action-btn:hover {
  background: var(--color-bg);
  color: var(--color-text-strong);
}

.turn-action-btn.is-copied {
  color: var(--color-success);
}

.turn-action-btn svg {
  width: 12px;
  height: 12px;
}

/* B. AI 导师回答（开放式学术手稿画布） */
.ai-turn-container {
  align-self: flex-start;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-msg-header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 26px;
}

.mentor-seal {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  background: var(--color-text-strong);
  color: var(--color-surface);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.82rem;
  flex-shrink: 0;
}

.mentor-seal.is-pulsing {
  background: var(--color-primary-text);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.sender {
  font-size: 0.82rem;
  font-weight: 650;
  color: var(--color-text-strong);
}

.streaming-live-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 1.5px 8px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 11px;
  font-weight: 600;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: live-dot-pulse 1.2s ease-in-out infinite;
}

@keyframes live-dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.8); }
}

.ai-canvas-body {
  padding-left: 32px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.ai-manuscript-content {
  min-width: 0;
  padding: 2px 0 4px;
}

/* AI 回答底部工具栏 */
.ai-msg-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-top: 4px;
  opacity: 0.75;
  transition: opacity 150ms ease;
}

.message-turn.ai:hover .ai-msg-toolbar,
.ai-msg-toolbar:focus-within {
  opacity: 1;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 9px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--color-text-muted);
  font-size: 11.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 140ms ease;
}

.toolbar-btn:hover:not(:disabled) {
  background: var(--color-bg);
  border-color: var(--color-border-light);
  color: var(--color-text-strong);
}

.toolbar-btn.is-copied {
  color: var(--color-success);
  background: var(--color-success-soft);
  border-color: var(--color-primary-border);
}

.toolbar-btn svg {
  width: 13.5px;
  height: 13.5px;
}

/* 附件图片画廊与文档卡片 */
.message-image-gallery {
  display: grid;
  gap: 6px;
  width: min(460px, 100%);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg);
}

.message-image-gallery.is-single {
  grid-template-columns: minmax(0, 1fr);
  width: min(380px, 100%);
}

.message-image-gallery.is-pair,
.message-image-gallery.is-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.message-image {
  display: block;
  width: 100%;
  height: 180px;
  object-fit: cover;
  cursor: zoom-in;
  background: var(--color-bg);
  transition: transform 180ms ease;
}

.message-image-gallery.is-single .message-image {
  height: clamp(200px, 30vw, 320px);
}

.message-image:hover {
  transform: scale(1.015);
}

.message-file-list {
  display: grid;
  gap: 6px;
  width: min(380px, 100%);
}

.message-file-card {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 16px;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  padding: 8px 11px;
  color: inherit;
  text-decoration: none;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  transition: border-color 150ms ease, background-color 150ms ease;
}

.message-file-card:hover {
  background: var(--color-bg);
  border-color: var(--color-primary);
}

.message-file-card > svg {
  width: 16px;
  height: 16px;
  stroke: var(--color-text-faint);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.5;
}

.file-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  flex-shrink: 0;
}

.file-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.file-copy strong {
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-copy small {
  color: var(--color-text-muted);
  font-size: 10.5px;
}

/* 失败卡片与上传中卡片 */
.assistant-failed-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 560px;
  padding: 12px 15px;
  background: var(--color-danger-soft);
  border: 1px solid #f8b4c0;
  border-radius: 11px;
}

.failed-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.failed-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: var(--color-danger);
}

.failed-icon svg {
  width: 16px;
  height: 16px;
}

.failed-title {
  font-size: 0.86rem;
  font-weight: 650;
  color: var(--color-danger);
}

.failed-message {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--color-text);
  word-break: break-word;
}

.failed-actions {
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.failed-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 12px;
  font-size: 0.78rem;
  font-weight: 600;
  color: #ffffff;
  background: var(--color-danger);
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.failed-retry-btn svg {
  width: 13px;
  height: 13px;
}

.thinking-indicator-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pre-answer-state {
  margin-left: 32px;
  max-width: 520px;
  padding: 12px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 11px;
}

.pre-answer-head {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 11px;
}

.pre-answer-head > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pre-answer-head strong {
  color: var(--color-text-strong);
  font-size: 12.5px;
  font-weight: 650;
}

.pre-answer-head span:not(.thinking-core) {
  color: var(--color-text-secondary);
  font-size: 11.5px;
}

.thinking-core {
  position: relative;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: var(--color-primary-text);
  background: var(--color-surface);
  border: 1px solid var(--color-primary-border);
  border-radius: 8px;
}

.thinking-core::before {
  position: absolute;
  inset: 5px;
  border: 1.8px solid rgba(70, 184, 180, 0.22);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  content: '';
  animation: thinking-ring-turn 1s linear infinite;
}

.thinking-core i {
  position: absolute;
  width: 3px;
  height: 3px;
  background: var(--color-primary-text);
  border-radius: 50%;
}

/* ============================================================
   4. 悬浮「回到底部」胶囊与底部多模态输入舱 (Composer Dock)
   ============================================================ */
.scroll-to-bottom-pill {
  position: absolute;
  left: 50%;
  bottom: 118px;
  transform: translateX(-50%);
  z-index: 12;
  height: 32px;
  padding: 0 14px;
  border-radius: 999px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-hover);
  color: var(--color-text-strong);
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 6px 20px rgba(23, 59, 66, 0.12);
  cursor: pointer;
}

.scroll-to-bottom-pill:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-primary);
  transform: translateX(-50%) translateY(-1px);
}

.scroll-to-bottom-pill svg {
  width: 13px;
  height: 13px;
  color: var(--color-primary-text);
}

.pill-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: live-dot-pulse 1.2s ease-in-out infinite;
}

.scroll-pill-fade-enter-active,
.scroll-pill-fade-leave-active {
  transition: opacity 180ms ease, transform 180ms cubic-bezier(0.32, 0.72, 0, 1);
}

.scroll-pill-fade-enter-from,
.scroll-pill-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}

/* ============================================================
   5. 弹窗与灯箱 (Delete Confirm & Image Lightbox)
   ============================================================ */
.custom-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(23, 59, 66, 0.36);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-confirm-dialog {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  width: 360px;
  max-width: calc(100vw - 32px);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.delete-confirm-icon {
  width: 44px;
  height: 44px;
  border-radius: 11px;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  margin-bottom: 14px;
}

.delete-confirm-title {
  margin: 0 0 8px;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.delete-confirm-desc {
  margin: 0 0 20px;
  font-size: 0.86rem;
  line-height: 1.55;
  color: var(--color-text-secondary);
}

.delete-confirm-actions {
  display: flex;
  gap: 10px;
  width: 100%;
}

.delete-confirm-actions .btn {
  flex: 1;
  height: 38px;
  border-radius: 9px;
  font-size: 0.86rem;
  font-weight: 600;
}

.delete-confirm-actions .btn-cancel {
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.img-preview-container {
  position: relative;
  max-width: 90vw;
  max-height: 88vh;
}

.img-preview-content {
  max-width: 90vw;
  max-height: 88vh;
  border-radius: 12px;
  box-shadow: var(--shadow-xl);
}

.img-preview-close-btn {
  position: absolute;
  top: -14px;
  right: -14px;
  width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: 50%;
  background: var(--color-text-strong);
  color: #ffffff;
}

@media (max-width: 760px) {
  .starter-prompts-grid {
    grid-template-columns: 1fr;
  }

  .chat-viewport {
    padding: 18px 14px 20px;
  }

  .user-turn-container {
    max-width: 90%;
  }

  .ai-canvas-body {
    padding-left: 0;
  }

}

@media (prefers-reduced-motion: reduce) {
  .message-turn,
  .live-dot,
  .pill-live-dot,
  .thinking-core::before {
    animation: none;
  }
}
</style>
