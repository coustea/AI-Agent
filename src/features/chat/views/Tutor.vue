<template>
  <div class="tutor-dashboard">

    <main class="dashboard-main">
      <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">

        <div class="sidebar-top-header">
          <div class="sidebar-brand" v-if="!sessionSidebarCollapsed">
            <ChatLineRound class="brand-icon" />
            <span class="brand-text">Mentorly</span>
          </div>
          <button
              class="collapse-toggle-btn"
              @click="sessionSidebarCollapsed = !sessionSidebarCollapsed"
              :title="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
              :aria-label="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="4" y="4" width="16" height="16" rx="4" ry="4"></rect>
              <line x1="9" y1="4" x2="9" y2="20"></line>
            </svg>
          </button>
        </div>

        <div class="standard-sidebar-nav">
          <div :class="['nav-item', 'new-chat-btn', { active: !activeSessionId }]" @click="newSession" title="新建对话">
            <EditPen class="nav-icon" /> <span class="nav-text">新建对话</span>
          </div>

          <PopoverRoot v-model:open="searchPopoverVisible">
            <PopoverTrigger as="div" class="nav-item search-item" title="搜索历史">
              <Search class="nav-icon" /> <span class="nav-text">搜索历史</span>
            </PopoverTrigger>

            <PopoverPortal>
              <PopoverContent
                class="popover-content-container search-popover-content"
                side="right"
                align="start"
                :side-offset="8"
              >
                <div class="popover-search-container">
                  <div class="search-input-wrapper">
                    <Search class="search-input-icon" />
                    <input
                        v-model="searchKeyword"
                        type="text"
                        placeholder="输入关键词搜索记录..."
                        class="input-control search-input"
                    />
                    <button v-if="searchKeyword" class="search-clear-btn" @click="searchKeyword = ''">×</button>
                  </div>

                  <div class="popover-session-scroll search-results-scroll" v-show="searchKeyword.trim() !== ''">
                    <div
                        v-for="s in filteredSessions"
                        :key="s.id"
                        :class="['nav-item', 'session-item', { active: s.id === activeSessionId }]"
                        @click="switchSession(s.id); searchPopoverVisible = false"
                    >
                      <ChatLineSquare class="session-icon" />
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
              </PopoverContent>
            </PopoverPortal>
          </PopoverRoot>

          <PopoverRoot v-model:open="historyPopoverVisible">
            <PopoverTrigger
              v-if="sessionSidebarCollapsed"
              class="nav-item history-collapsed-btn"
              title="历史记录"
              aria-label="历史记录"
            >
              <Timer class="nav-icon" />
            </PopoverTrigger>

            <PopoverPortal>
              <PopoverContent
                class="popover-content-container history-popover-content"
                side="right"
                align="start"
                :side-offset="8"
              >
                <div class="history-popover-header">
                  <div class="history-popover-heading">
                    <Timer class="history-popover-icon" aria-hidden="true" />
                    <div>
                      <div class="popover-title">历史记录</div>
                      <div class="history-popover-count">{{ sessions.length }} 个对话</div>
                    </div>
                  </div>
                </div>
                <div class="popover-session-scroll">
                  <div
                      v-for="s in visibleSessions"
                      :key="s.id"
                      :class="['nav-item', 'session-item', { active: s.id === activeSessionId }]"
                      :title="s.title || '新建对话'"
                      :aria-current="s.id === activeSessionId ? 'true' : undefined"
                      @click="switchSession(s.id); historyPopoverVisible = false"
                  >
                    <ChatLineSquare class="session-icon" />
                    <div class="session-info nav-text">
                      <span class="session-title-line">
                        <span class="session-title">{{ s.title || '新建对话' }}</span>
                        <span v-if="s.id === activeSessionId" class="current-session-indicator">当前</span>
                      </span>
                      <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                    </div>
                    <button
                      class="btn-link del-btn nav-text"
                      aria-label="删除对话"
                      title="删除对话"
                      @click.stop="historyPopoverVisible = false; archiveSession(s.id)"
                    >
                      <Delete class="del-icon" />
                    </button>
                  </div>
                  <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
                  <div v-if="hasMoreSessions && !historyExpanded" class="session-expand-btn nav-text" @click="historyExpanded = true">
                    展开全部（{{ sessions.length }} 条）
                  </div>
                  <div v-if="historyExpanded" class="session-expand-btn nav-text" @click="historyExpanded = false">
                    收起
                  </div>
                </div>
              </PopoverContent>
            </PopoverPortal>
          </PopoverRoot>
        </div>

        <div class="history-section-header" v-if="!sessionSidebarCollapsed">
          <Timer class="nav-icon" /> <span>历史记录</span>
        </div>

        <div class="session-list" v-show="!sessionSidebarCollapsed">
          <div
              v-for="s in visibleSessions"
              :key="s.id"
              :class="['nav-item', 'session-item', { active: s.id === activeSessionId }]"
              @click="switchSession(s.id)"
              :title="s.title || '新建对话'"
          >
            <ChatLineSquare class="session-icon" />
            <div class="session-info nav-text">
              <span class="session-title">{{ s.title || '新建对话' }}</span>
              <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
            </div>
            <button class="btn-link del-btn nav-text" @click.stop="archiveSession(s.id)" title="删除对话">
              <Delete class="del-icon" />
            </button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
          <div v-if="hasMoreSessions && !historyExpanded" class="session-expand-btn nav-text" @click="historyExpanded = true">
            展开全部（{{ sessions.length }} 条）
          </div>
          <div v-if="historyExpanded" class="session-expand-btn nav-text" @click="historyExpanded = false">
            收起
          </div>
        </div>
      </aside>

      <section class="chat-container">
        <div class="chat-interaction-area">
          <div class="chat-viewport" ref="chatScroll">
            <div class="standard-welcome" v-if="messages.length === 0">
              <h2>你好，{{ userName }}。欢迎回到 Mentorly。</h2>
            </div>

            <!-- 本地附件上传状态。回答前的 agent 状态由后端 SSE activity 事件驱动。 -->
            <div
              v-if="uploadingFile && !streamingMsgId"
              class="thinking-indicator-row"
            >
              <div class="thinking-avatar">
                <div class="avatar-circle ai-av"><Service /></div>
              </div>
              <div class="pre-answer-state" aria-live="polite">
                <div class="pre-answer-head">
                  <span class="thinking-core" aria-hidden="true">
                    <i></i><i></i><i></i>
                  </span>
                  <div>
                    <strong>正在上传附件</strong>
                    <span>上传完成后，将继续等待后端实时处理状态。</span>
                  </div>
                </div>
              </div>
            </div>

            <template v-for="msg in messages" :key="msg.id">
              <div
                v-if="
                  msg.role === 'user'
                  || getDisplayContent(msg)
                  || msg.attachments?.length
                  || msg.run
                "
                :class="['message-row', msg.role]"
              >

                <div class="msg-avatar">
                  <div v-if="msg.role === 'ai'" class="avatar-circle ai-av"><Service /></div>
                  <div v-else class="avatar-circle user-av"><UserFilled /></div>
                </div>

                <div class="bubble-wrapper" @click="handleMessageClick">
                  <div class="msg-meta">
                    <span class="sender">{{ msg.role === 'ai' ? 'Mentorly' : '我' }}</span>
                    <span class="time">{{ msg.time }}</span>
                  </div>

                  <!-- 图片附件作为消息内容展示，而不是普通文件小图标 -->
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

                  <ChatRunPanel v-if="msg.run" :run="msg.run" />

                  <div
                    v-if="getDisplayContent(msg)"
                    :class="[
                      'bubble',
                      'markdown-body',
                      msg.role === 'ai' ? 'assistant-answer' : 'user-message-bubble',
                    ]"
                  >
                    <div v-if="msg.role === 'user'" class="user-plain-text">{{ getDisplayContent(msg) }}</div>
                    <TutorMessageContent
                      v-else
                      :content="getDisplayContent(msg)"
                      :is-streaming="isStreamingMessage(msg)"
                    />
                  </div>

                  <!-- 失败或超时专用错误卡片 -->
                  <div
                    v-if="msg.role === 'ai' && msg.failed"
                    class="assistant-failed-card"
                  >
                    <div class="failed-header">
                      <span class="failed-icon" aria-hidden="true">
                        <svg viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                      </span>
                      <strong class="failed-title">运行超时 / 生成中断</strong>
                    </div>
                    <p class="failed-message">{{ msg.errorMessage || msg.content || '请求处理超时或服务异常，请重试。' }}</p>
                    <div class="failed-actions">
                      <button
                        type="button"
                        class="failed-retry-btn"
                        :disabled="isAIThinking"
                        @click.stop="handleRetryAssistantMessage(msg)"
                      >
                        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                          <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" stroke-linecap="round" stroke-linejoin="round" />
                        </svg>
                        重试提问
                      </button>
                    </div>
                  </div>

                  <div
                    v-if="msg.role === 'ai' && getDisplayContent(msg) && !isStreamingMessage(msg)"
                    class="message-actions"
                  >
                    <button type="button" @click.stop="copyAssistantAnswer(msg)">
                      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                        <rect x="6" y="6" width="9" height="9" rx="1.5" />
                        <path d="M4 12H3.5A1.5 1.5 0 0 1 2 10.5v-7A1.5 1.5 0 0 1 3.5 2h7A1.5 1.5 0 0 1 12 3.5V4" />
                      </svg>
                      复制回答
                    </button>
                  </div>


                </div>
              </div>
            </template>

          </div>

          <div class="minimal-input-panel">
            <form
              ref="messageFormRef"
              class="minimal-input-wrapper"
              :class="{
                'is-expanded': isExpandedInput,
                'has-attachments': pendingFiles.length > 0,
                'is-responding': isResponding,
              }"
              @submit.prevent="handleSend"
            >
              <div v-if="pendingFiles.length > 0" class="composer-attachments">
                <div
                  v-for="(f, idx) in pendingFiles"
                  :key="`${f.name}-${idx}`"
                  class="composer-attachment"
                  :class="{ 'is-image': f.fileType === 'image', 'is-file': f.fileType !== 'image' }"
                >
                  <template v-if="f.fileType === 'image'">
                    <img
                      :src="f.localUrl || f.url"
                      :alt="f.name || '图片预览'"
                      class="composer-image"
                    />
                    <span class="composer-image-name" :title="f.name">{{ f.name }}</span>
                  </template>
                  <template v-else>
                    <span
                      class="file-icon-box"
                      :style="{ backgroundColor: getDocumentIconColor(getDocumentType(f.name)) }"
                    >
                      <Document class="file-icon" aria-hidden="true" />
                    </span>
                    <span class="file-copy">
                      <strong :title="f.name">{{ f.name }}</strong>
                      <small>{{ formatFileSize(f.size) || getDocumentType(f.name).toUpperCase() }}</small>
                    </span>
                  </template>
                  <button
                    type="button"
                    class="remove-attachment-btn"
                    @click="removeAttachment(idx)"
                    aria-label="移除附件"
                  >
                    <Close class="close-icon" aria-hidden="true" />
                  </button>
                </div>
              </div>

              <textarea
                  ref="textareaRef"
                  v-model="userInput"
                  rows="1"
                  aria-label="向 Mentorly 提问"
                  placeholder="向 Mentorly 提问"
                  @compositionstart="isComposing = true"
                  @compositionend="isComposing = false"
                  @keydown.enter="handleEnter"
                  @input="autoResize"
              ></textarea>

              <div class="minimal-action-bar">
                <div class="action-left" :key="inputToolStateKey">
                  <button
                    type="button"
                    class="input-tool-btn"
                    :disabled="uploadingFile"
                    @click="triggerFileUpload"
                    :aria-label="uploadingFile ? '正在上传附件' : '上传附件'"
                    :title="uploadingFile ? '正在上传附件' : '上传附件'"
                  >
                    <Loading v-if="uploadingFile" class="btn-icon spinner" aria-hidden="true" />
                    <Paperclip v-else class="btn-icon" aria-hidden="true" />
                    <span>{{ uploadingFile ? '上传中' : '附件' }}</span>
                  </button>



                  <button
                    type="button"
                    class="input-tool-btn"
                    :class="{ 'is-active-teal': needTeachingDiagram }"
                    @click="handleTeachingDiagramToggle"
                    :aria-pressed="needTeachingDiagram"
                  >
                    <DataLine class="btn-icon" aria-hidden="true" />
                    <span>图解</span>
                  </button>

                  <button
                    type="button"
                    class="input-tool-btn"
                    :class="{ 'is-active-purple': needVideo }"
                    @click="handleVideoToggle"
                    :aria-pressed="needVideo"
                  >
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" class="btn-icon" aria-hidden="true">
                      <rect x="2.5" y="5" width="11" height="10" rx="1.5" />
                      <path d="m13.5 8 4-2.5v9l-4-2.5z" />
                    </svg>
                    <span>视频</span>
                  </button>

                </div>

                <div class="action-right">
                  <button v-if="isResponding" type="button" class="btn btn-cancel" @click="stopGeneration">停止生成</button>
                  <button
                    type="submit"
                    class="minimal-send-btn"
                    :class="{
                      'can-send': canSendMessage,
                      'is-responding': isResponding,
                    }"
                    :disabled="!canSendMessage"
                    :aria-label="isResponding ? 'AI 正在回答' : '发送消息'"
                    :title="isResponding ? 'AI 正在回答，请稍候' : (canSendMessage ? '发送消息' : '请输入消息')"
                  >
                    <Loading v-if="isResponding" class="responding-spinner spinner" aria-hidden="true" />
                    <span v-else class="send-arrow-glyph" aria-hidden="true">↑</span>
                  </button>
                </div>
              </div>
            </form>
            <div class="input-footer">
              <span>Enter 发送 · Shift + Enter 换行</span>
              <span>内容由 AI 生成，仅供参考</span>
            </div>
          </div>
        </div>

        <input ref="fileInput" type="file" multiple accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.log,.png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onCombinedFileSelected" />
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
              <button class="btn btn-cancel" @click="cancelDeleteSession">取消</button>
              <button class="btn btn-danger" @click="confirmArchiveSession">删除</button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- 全局图片预览 -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="imgPreviewVisible" class="custom-modal-overlay img-preview-overlay" @click="imgPreviewVisible = false">
          <div class="img-preview-container">
            <img :src="imgPreviewUrl" class="img-preview-content" />
            <button class="img-preview-close-btn" @click="imgPreviewVisible = false" aria-label="关闭预览">
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
  PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent
} from 'reka-ui'
import {
  PhChatCenteredText as ChatLineRound,
  PhHeadset as Service,
  PhUser as UserFilled,
  PhFileText as Document,
  PhChat as ChatLineSquare,
  PhTrash as Delete,
  PhX as Close,
  PhPaperclip as Paperclip,
  PhPencilSimple as EditPen,
  PhMagnifyingGlass as Search,
  PhClock as Timer,
  PhGraph as DataLine,
  PhSpinner as Loading
} from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import { getErrorMessage } from '@/shared/api/http'
import { ensureCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import TutorMessageContent from '@/features/chat/components/TutorMessageContent.vue'
import ChatRunPanel from '@/features/chat/components/ChatRunPanel.vue'

import { useChatRun } from '@/features/chat/composables/useChatRun'
import {
  uploadFile,
  getSessions,
  createSession,
  deleteSession,
  updateSessionTitle,
  getChatHistory,
} from '@/features/chat/api/chat'
import type {
  ChatSession,
} from '@/features/chat/types/chat'
import { isRunActive, type RunState } from '@/features/chat/types/chatEvent'
import { consumeTutorEntryIntent } from '@/features/chat/model/tutorEntryIntent'
import {
  type PendingFile,
  type Attachment,
  type ChatMsg,
  getDocumentType,
  getDocumentIconColor,
  formatFileSize,
  formatRelativeTime,
  getInputToolStateKey,
} from './tutorUtils'

defineOptions({ name: 'Tutor' })

const DEFAULT_SESSION_TITLE = '新对话'
const SESSION_TITLE_REFRESH_DELAYS = [300, 800, 1500, 3000]
const { userName } = useCurrentUser()

// 用户输入文本
const userInput = ref('')
// AI 是否正在思考/生成中
const isAIThinking = ref(false)
const chatScroll = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messageFormRef = ref<HTMLFormElement | null>(null)
const isExpandedInput = ref(false)
const isComposing = ref(false)

// 联网搜索开关
// 是否需要生成教学图解
const needTeachingDiagram = ref(false)
// 本轮请求包含视频生成
const needVideo = ref(false)

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






const uploadingFile = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const pendingFiles = ref<PendingFile[]>([])
const inputToolStateKey = computed(() => getInputToolStateKey({
  uploadingFile: uploadingFile.value,
  needTeachingDiagram: needTeachingDiagram.value,
  needVideo: needVideo.value,
}))


// 会话列表
const sessions = ref<ChatSession[]>([])
// 当前活跃会话 ID
const currentSessionId = ref<string | undefined>(undefined)
const activeSessionId = computed(() => currentSessionId.value)
const sessionSidebarCollapsed = ref(false)
const searchPopoverVisible = ref(false)
const historyPopoverVisible = ref(false)
const searchKeyword = ref('')
const historyExpanded = ref(false)
const HISTORY_COLLAPSED_COUNT = 5

// 当前会话的消息列表
const messages = ref<ChatMsg[]>([])
// 正在流式输出的消息 ID
const streamingMsgId = ref<number | null>(null)
// 正在流式输出的消息引用

/**
 * 当前会话是否正处于回答链路中。
 * 覆盖附件上传、等待首个 token、流式输出阶段。
 */
const isResponding = computed(() => (
  uploadingFile.value
  || isAIThinking.value
  || streamingMsgId.value !== null
))

const canSendMessage = computed(() => (
  !isResponding.value
  && Boolean(userInput.value.trim() || pendingFiles.value.length > 0)
))

const chatRun = useChatRun()
let scrollPending = false
let lastAutoScrollAt = 0
const STREAM_SCROLL_INTERVAL_MS = 64
const STREAM_AUTO_SCROLL_BOTTOM_GAP_PX = 96

const applyRun = (messageId: number, state: RunState) => {
  const message = messages.value.find(item => item.id === messageId)
  if (!message) return
  message.run = state
  message.content = state.content
  message.failed = state.status === 'failed' || state.status === 'interrupted'
  message.errorMessage = state.error
  isAIThinking.value = isRunActive(state)
  streamingMsgId.value = isRunActive(state) ? messageId : null
  scrollToBottomThrottled()
}

const stopGeneration = async () => {
  try { await chatRun.cancel() }
  catch (error) { toast.error(getErrorMessage(error, '停止失败')) }
}

// 搜索框过滤后的会话列表
const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return sessions.value.filter(s => {
    const title = s.title || '新建对话'
    return title.toLowerCase().includes(keyword)
  })
})

const visibleSessions = computed(() => {
  if (historyExpanded.value) return sessions.value
  return sessions.value.slice(0, HISTORY_COLLAPSED_COUNT)
})

const hasMoreSessions = computed(() => sessions.value.length > HISTORY_COLLAPSED_COUNT)

// 判断消息是否处于流式输出中
const isStreamingMessage = (msg: ChatMsg) => {
  if (msg.id !== streamingMsgId.value) return false
  return isAIThinking.value
}
const getDisplayContent = (msg: ChatMsg) => msg.content

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


const handleEnter = (e: KeyboardEvent) => {
  if (isComposing.value || e.isComposing) return
  if (e.shiftKey) return

  e.preventDefault()
  messageFormRef.value?.requestSubmit()
}

// 工具函数
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('已复制到剪贴板')
  } catch (err) {
    toast.error('复制失败，请重试')
  }
}

const copyAssistantAnswer = async (msg: ChatMsg) => {
  const content = getDisplayContent(msg).trim()
  if (!content) return
  await copyToClipboard(content)
}

const handleMessageClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (target && target.classList.contains('copy-code-btn')) {
    const code = target.dataset.code
    if (code != null) {
      copyToClipboard(code)
      const originalText = target.innerText
      target.innerText = '已复制'
      target.classList.add('copied')
      setTimeout(() => {
        target.innerText = originalText
        target.classList.remove('copied')
      }, 2000)
    }
  }
}

// 滚动聊天区域到底部
const scrollToBottom = () => {
  if (scrollPending) return
  scrollPending = true

  nextTick(() => {
    requestAnimationFrame(() => {
      if (chatScroll.value) {
        chatScroll.value.scrollTop = chatScroll.value.scrollHeight
      }
      scrollPending = false
    })
  })
}

const scrollToBottomThrottled = (force = false) => {
  if (!force && !isNearBottom()) {
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

const autoResize = () => {
  const el = textareaRef.value
  if (!el) return

  const minHeight = 28
  const maxHeight = 200

  el.style.height = `${minHeight}px`
  const nextHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight)

  el.style.height = `${nextHeight}px`
  el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
  isExpandedInput.value = nextHeight > 40
}



// 加载会话列表
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

// 创建新会话：断开当前流渲染，清空消息
const newSession = () => {
  chatRun.close()
  streamingMsgId.value = null
  isAIThinking.value = false
  currentSessionId.value = undefined
  messages.value = []
  clearPendingFiles()
}

// 从 API 加载指定会话的历史消息
const loadHistoryFromAPI = async (
  sessionId: string,
  shouldApply: () => boolean = () => true,
): Promise<boolean> => {
  try {
    const res = await getChatHistory(sessionId)
    const history = res.data.data || []
    const mapped: ChatMsg[] = history.map((msg) => {
      // 从 ContentPart[] 中提取文本和附件
      const contentParts = msg.content || []
      const textContent = contentParts
        .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
        .map(part => part.text)
        .join('')
      const imageAttachments = contentParts
        .filter(part => part.type === 'image_url')
        .map(part => ({
          url: part.url || part.image_url.url,
          type: 'image',
          name: part.original_name || '',
          size: part.size_bytes,
          mimeType: part.mime_type || undefined,
        }))
      const fileAttachments = contentParts
        .filter(part => part.type === 'file')
        .map(part => ({
          url: part.url || part.file.file_id || part.file.file_data || '',
          type: 'document',
          name: part.original_name || part.file.filename || '',
          size: part.size_bytes,
          mimeType: part.mime_type || undefined,
        }))
      const contentAttachments = [...imageAttachments, ...fileAttachments]
      const attachments = contentAttachments.length > 0 ? contentAttachments : null
      return {
        id: msg.id,
        role: msg.role === 'user' ? 'user' : 'ai',
        content: msg.run?.content ?? textContent,
        time: new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        attachments,
        runId: msg.run_id,
        run: msg.run ?? undefined,
        failed: msg.run?.status === 'failed' || msg.run?.status === 'interrupted',
        errorMessage: msg.run?.error,
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

// 切换会话：加载历史 → 恢复流状态 → 绑定回调
let sessionSwitchToken = 0

const switchSession = async (sessionId: string) => {
  const switchToken = ++sessionSwitchToken
  chatRun.close()
  currentSessionId.value = sessionId
  messages.value = []
  isAIThinking.value = false
  streamingMsgId.value = null
  if (!await loadHistoryFromAPI(sessionId, () => switchToken === sessionSwitchToken)) return
  if (switchToken !== sessionSwitchToken) return
  const running = messages.value.find(message => message.run && isRunActive(message.run))
  if (running?.run) chatRun.connect(running.run, state => applyRun(running.id, state))
  scrollToBottom()
}

const archiveSession = (sessionId: string) => {
  const targetSession = sessions.value.find(session => session.id === sessionId)
  sessionToDeleteTitle.value = targetSession?.title?.trim() || '新建对话'
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
    // 只有确认后才清理流状态并调用删除接口。
    chatRun.close()
    await deleteSession(sessionId)
    sessions.value = sessions.value.filter(session => session.id !== sessionId)

    if (activeSessionId.value === sessionId) {
      currentSessionId.value = undefined
      messages.value = []

      if (sessions.value.length > 0) {
        await switchSession(sessions.value[0]!.id)
      }
    }

    toast.success('会话已删除')
  } catch (error) {
    toast.error(getErrorMessage(error) || '删除会话失败，请稍后重试')
  }
}

const triggerFileUpload = () => fileInput.value?.click()

const MAX_COMPOSER_FILES = 5

const onCombinedFileSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  const selectedFiles = Array.from(input.files || [])
  if (!selectedFiles.length) return

  const remaining = Math.max(0, MAX_COMPOSER_FILES - pendingFiles.value.length)
  if (remaining === 0) {
    toast.warning(`每次最多添加 ${MAX_COMPOSER_FILES} 个附件`)
    input.value = ''
    return
  }

  if (selectedFiles.length > remaining) {
    toast.warning(`每次最多添加 ${MAX_COMPOSER_FILES} 个附件，已保留前 ${remaining} 个`)
  }

  selectedFiles.slice(0, remaining).forEach((file) => {
    const isImage = file.type.startsWith('image/') || /\.(png|jpg|jpeg|gif|webp)$/i.test(file.name)
    pendingFiles.value.push({
      file,
      fileType: isImage ? 'image' : 'document',
      name: file.name,
      localUrl: isImage ? URL.createObjectURL(file) : undefined,
      size: file.size,
      mimeType: file.type,
    })
  })

  input.value = ''
}

const removeAttachment = (idx: number) => {
  const removed = pendingFiles.value[idx]
  if (removed?.localUrl) {
    URL.revokeObjectURL(removed.localUrl)
  }
  pendingFiles.value.splice(idx, 1)
}

const clearPendingFiles = () => {
  pendingFiles.value.forEach(file => {
    if (file.localUrl) URL.revokeObjectURL(file.localUrl)
  })
  pendingFiles.value = []
}

const handleTeachingDiagramToggle = () => {
  needTeachingDiagram.value = !needTeachingDiagram.value
  if (needTeachingDiagram.value) needVideo.value = false
}

const handleVideoToggle = () => {
  needVideo.value = !needVideo.value
  if (needVideo.value) needTeachingDiagram.value = false
}

// 确保当前有活跃会话（没有则创建）
const ensureCurrentSession = async () => {
  if (currentSessionId.value) return true
  try {
    const res = await createSession()
    const session = res.data.data
    currentSessionId.value = session.id
    sessions.value.unshift({ id: session.id, title: session.title, updated_at: new Date().toISOString() })
    return true
  } catch {
    toast.error({ message: '创建会话失败，请重试', plain: true })
    return false
  }
}

// 发送消息：上传附件 → 创建 AI 消息 → 启动 SSE 流
const handleSend = async () => {
  const text = userInput.value.trim()
  const currentPending = [...pendingFiles.value]
  const hasFiles = currentPending.length > 0
  if ((!text && !hasFiles) || isAIThinking.value) return

  const shouldGenerateTeachingDiagram = needTeachingDiagram.value
  const shouldGenerateVideo = needVideo.value

  if (!await ensureCurrentSession()) return
  const sessionId = currentSessionId.value
  if (!sessionId) return

  const session = sessions.value.find(item => item.id === sessionId)
  if (session && (!session.title || session.title === DEFAULT_SESSION_TITLE)) {
    const titleSource = text || currentPending.map(file => file.name).join('、') || '附件分析'
    const tempTitle = titleSource.length > 20 ? `${titleSource.slice(0, 20)}...` : titleSource
    session.title = tempTitle
    try {
      await updateSessionTitle(sessionId, tempTitle)
    } catch (err) {
      console.warn('更新会话标题失败:', err)
    }
  }

  const userMsgId = Date.now()
  const optimisticAttachments: Attachment[] = currentPending.map(file => ({
    url: file.localUrl || file.url || '',
    type: file.fileType === 'image' ? 'image' : 'document',
    name: file.name,
    size: file.size,
    mimeType: file.mimeType,
  }))

  messages.value.push({
    id: userMsgId,
    role: 'user',
    content: text,
    time: now(),
    attachments: optimisticAttachments.length ? optimisticAttachments : null,
  })

  userInput.value = ''
  isExpandedInput.value = false
  nextTick(() => {
    if (textareaRef.value) textareaRef.value.style.height = '24px'
  })

  isAIThinking.value = true
  scrollToBottom()

  const uploadedAttachments: Attachment[] = []
  uploadingFile.value = hasFiles

  try {
    const uploaded = await Promise.all(
      currentPending.map(async (pending) => {
        if (pending.url) {
          return {
            url: pending.url,
            fileType: pending.fileType,
            name: pending.name,
            size: pending.size,
            mimeType: pending.mimeType,
          }
        }

        if (!pending.file) throw new Error('附件内容不存在')
        const res = await uploadFile(pending.file, sessionId)
        const data = res.data.data
        return {
          url: data.url,
          fileType: pending.fileType === 'image' || data.file_type === 'image' ? 'image' : 'document',
          name: data.original_name || pending.name,
          size: data.size_bytes || pending.size,
          mimeType: data.mime_type || pending.mimeType,
        }
      }),
    )

    uploaded.forEach(item => {
      uploadedAttachments.push({
        url: item.url,
        type: item.fileType,
        name: item.name,
        size: item.size,
        mimeType: item.mimeType,
      })
    })

    const userMsg = messages.value.find(message => message.id === userMsgId)
    if (userMsg) {
      userMsg.attachments = uploadedAttachments.length ? uploadedAttachments : null
    }

    pendingFiles.value.forEach(file => {
      if (file.localUrl) URL.revokeObjectURL(file.localUrl)
    })
    pendingFiles.value = []
  } catch (error) {
    uploadingFile.value = false
    isAIThinking.value = false
    messages.value.push({
      id: Date.now() + 99,
      role: 'ai',
      content: `附件上传失败：${getErrorMessage(error, '请检查文件后重试。')}`,
      time: now(),
    })
    return
  } finally {
    uploadingFile.value = false
  }

  const messageAttachments = uploadedAttachments.map(file => ({
    url: file.url,
    file_type: file.type,
    original_name: file.name,
    size_bytes: file.size,
    mime_type: file.mimeType,
  }))
  const aiMsgId = Date.now() + 1
  messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
  streamingMsgId.value = aiMsgId
  try {
    const created = await chatRun.start({
      message: text || '请分析这些附件', session_id: sessionId,
      attachments: messageAttachments, diagram_mode: shouldGenerateTeachingDiagram ? 'required' : 'auto',
      video_mode: shouldGenerateVideo,
    }, state => {
      applyRun(aiMsgId, state)
    })
    const aiMsg = messages.value.find(message => message.id === aiMsgId)
    if (aiMsg) aiMsg.runId = created.run_id
    void refreshSessionTitleWithRetry(sessionId)
  } catch (error) {
    const aiMsg = messages.value.find(message => message.id === aiMsgId)
    if (aiMsg) {
      aiMsg.failed = true
      aiMsg.errorMessage = getErrorMessage(error, '创建运行失败')
      aiMsg.content = aiMsg.errorMessage
    }
    isAIThinking.value = false
    streamingMsgId.value = null
  }
}

// 失败或超时消息快捷重试
const handleRetryAssistantMessage = (failedMsg: ChatMsg) => {
  if (isAIThinking.value) return
  const msgIdx = messages.value.findIndex(m => m.id === failedMsg.id)
  let retryText = ''
  if (msgIdx > 0) {
    const prevUserMsg = messages.value.slice(0, msgIdx).reverse().find(m => m.role === 'user')
    if (prevUserMsg) {
      retryText = prevUserMsg.content
      messages.value = messages.value.filter(m => m.id !== failedMsg.id && m.id !== prevUserMsg.id)
    }
  }
  if (!retryText) {
    messages.value = messages.value.filter(m => m.id !== failedMsg.id)
    toast.error('未找到可重试的提问内容')
    return
  }
  userInput.value = retryText
  void handleSend()
}

// 组件挂载：加载用户信息、会话列表、恢复上次会话
onMounted(async () => {
  const shouldStartBlankSession = consumeTutorEntryIntent()

  await ensureCurrentUser()
  await loadSessions()

  if (shouldStartBlankSession) {
    newSession()
    return
  }

  // If we still have a currentSessionId (from before navigating away),
  // switch back to it. This recovers streams that completed or are still
  // active on the server. Otherwise, pick the first session.
  if (currentSessionId.value) {
    await switchSession(currentSessionId.value)
  } else if (sessions.value.length > 0) {
    await switchSession(sessions.value[0]!.id)
  }
})

let tutorWasDeactivated = false

// 组件重新激活（keep-alive）：恢复会话和滚动
onActivated(async () => {
  if (!tutorWasDeactivated) return
  tutorWasDeactivated = false

  if (currentSessionId.value) {
    await switchSession(currentSessionId.value)
  }
})

// 组件停用时：暂停流渲染、清理事件监听
onDeactivated(() => {
  tutorWasDeactivated = true
  chatRun.close()
})

// 组件卸载前：清理流、释放附件
onBeforeUnmount(() => {
  chatRun.close()
  clearPendingFiles()
})
</script>

<style scoped>
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
  min-height: 0; /* 关键：防止 flex 子项撑破容器 */
  overflow: hidden;
}

.session-sidebar {
  position: relative;
  width: 240px;
  background: var(--color-bg);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-slow);
  flex-shrink: 0;
}

.sidebar-top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-3) var(--space-2) var(--space-4);
  height: 56px;
  box-sizing: border-box;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text);
  font-weight: var(--weight-bold);
  font-size: 0.95rem;
}

.brand-icon {
  color: var(--color-primary);
  width: 30px;
  height: 30px;
  font-size: 20px;
  flex-shrink: 0;
}
:deep(.brand-icon svg) {
  width: 100%;
  height: 100%;
  display: block;
}

.collapse-toggle-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  width: 36px;
  height: 36px;
  padding: 0;
  margin: 0;
}

.collapse-toggle-btn:hover:not([disabled]) {
  background: var(--color-border);
  color: var(--color-text);
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
  padding: var(--space-2) var(--space-4) var(--space-4);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.nav-item {
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  margin-bottom: var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 10px var(--space-4);
  border-radius: var(--radius-pill);
  cursor: pointer;
  font-size: 0.95rem;
  transition: all var(--transition-base);
  color: var(--color-text-secondary);
}

.nav-item:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}

.nav-item.search-item {
  font-weight: var(--weight-normal) !important;
}

.nav-item.new-chat-btn {
  font-weight: var(--weight-normal) !important;
}

.nav-item.history-collapsed-btn {
  color: var(--color-text-secondary);
  width: 100%;
  padding: 0;
  border: 1px solid transparent;
  outline: none;
  text-align: left;
}
.nav-item.history-collapsed-btn:hover {
  background: var(--color-border);
  color: var(--color-text);
}
.nav-item.history-collapsed-btn[data-state='open'] {
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
  color: var(--color-primary);
}

.history-section-header {
  padding: var(--space-3) var(--space-4) var(--space-2) var(--space-4);
  font-size: 1.05rem;
  font-weight: var(--weight-bold);
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-transform: none;
  letter-spacing: normal;
  user-select: none;
}
.popover-search-container {
  display: flex;
  flex-direction: column;
}

.popover-session-scroll {
  max-height: 40vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

:global(.history-popover-content) {
  width: min(320px, calc(100vw - 88px));
  max-height: min(520px, calc(100vh - 32px));
  padding: 12px;
  overflow: hidden;
  box-sizing: border-box;
  background-color: var(--color-surface, #fff);
  color: var(--color-text);
  border: 1px solid var(--color-border-hover);
  border-radius: 8px;
  box-shadow: 0 18px 42px rgba(17, 46, 52, 0.18), 0 4px 12px rgba(17, 46, 52, 0.08);
  outline: none;
  z-index: 1200;
}

:global([data-radix-popper-content-wrapper]:has(.history-popover-content)) {
  z-index: 1200 !important;
}

.history-popover-header {
  display: flex;
  align-items: center;
  min-height: 50px;
  padding: 2px 4px 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.history-popover-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.history-popover-icon {
  width: 32px;
  height: 32px;
  padding: 7px;
  box-sizing: border-box;
  flex-shrink: 0;
  color: var(--color-primary);
  background: var(--color-surface-hover);
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

:global(.history-popover-content .popover-title) {
  padding: 0;
  margin: 0;
  border: 0;
  color: var(--color-text);
  font-size: 0.95rem;
  font-weight: var(--weight-bold);
}

.history-popover-count {
  margin-top: 2px;
  color: var(--color-text-faint);
  font-size: 0.72rem;
}

:global(.history-popover-content .popover-session-scroll) {
  max-height: min(400px, calc(100vh - 150px));
  padding-right: 2px;
  gap: 4px;
}

:global(.history-popover-content .session-item) {
  width: 100%;
  min-height: 58px;
  margin: 0;
  padding: 9px 10px;
  box-sizing: border-box;
  gap: 10px;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
}

:global(.history-popover-content .session-item:hover) {
  background: var(--color-bg);
  border-color: var(--color-border);
  color: var(--color-text);
}

:global(.history-popover-content .session-item.active) {
  color: var(--color-text);
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
  box-shadow: inset 3px 0 0 var(--color-primary);
}

:global(.history-popover-content .session-icon) {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.session-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.session-title-line .session-title {
  flex: 1;
  min-width: 0;
  color: inherit;
  font-size: 0.88rem;
  font-weight: var(--weight-semibold);
}

.current-session-indicator {
  flex-shrink: 0;
  color: var(--color-primary);
  font-size: 0.68rem;
  font-weight: var(--weight-semibold);
}

:global(.history-popover-content .session-time) {
  margin-top: 3px;
  font-size: 0.72rem;
}

:global(.history-popover-content .del-btn) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 6px;
  flex-shrink: 0;
  border-radius: 6px;
  opacity: 0.35;
}

:global(.history-popover-content .session-item:hover .del-btn),
:global(.history-popover-content .del-btn:focus-visible) {
  opacity: 1;
  background: var(--color-danger-soft, #fff1f1);
}

:global(.history-popover-content .session-empty) {
  margin: 24px 0;
  color: var(--color-text-faint);
}

:global(.history-popover-content .session-expand-btn) {
  margin-top: 6px;
  padding: 10px 0 2px;
  border-top: 1px solid var(--color-border);
}

.search-results-scroll {
  margin-top: var(--space-3);
  max-height: 250px;
  overflow-y: auto;
  padding-right: var(--space-1);
}

.search-results-scroll .session-empty {
  margin-top: 1rem;
  margin-bottom: 1rem;
}

.popover-title {
  font-size: 0.8rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text-faint);
  padding: var(--space-1) var(--space-2) var(--space-2);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-2);
}

.popover-session-scroll .session-item {
  margin: 0;
  padding: var(--space-2) var(--space-4);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 1rem 1rem;
  display: flex;
  flex-direction: column;
}

.session-item {
  margin-bottom: var(--space-1);
  color: var(--color-text-secondary);
}
.session-item:hover {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text-secondary);
}
.session-item.active {
  color: var(--color-primary);
  font-weight: var(--weight-semibold);
}

.session-icon {
  font-size: 1.15rem;
  color: var(--color-text-faint);
  transition: color var(--transition-base);
}

.session-item.active .session-icon {
  color: var(--color-primary);
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
  color: var(--color-text-faint);
  white-space: nowrap;
}

.del-btn {
  opacity: 0;
  color: var(--color-danger);
  padding: var(--space-1);
}

.session-item:hover .del-btn {
  opacity: 1;
}

.diagram-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--color-border-hover);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-pill);
  animation: diagramSpin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes diagramSpin {
  to {
    transform: rotate(360deg);
  }
}



.kg-gen-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kg-gen-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-text);
}

.kg-gen-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  animation: pulse-text 2s infinite;
}

.diagram-draft-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  border-radius: var(--radius-md);
}

.diagram-draft-grid span {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: rgba(20, 184, 166, 0.08);
  color: var(--color-text-secondary);
  text-align: center;
  font-size: 0.84rem;
}

.msg-teaching-diagram {
  margin-top: var(--space-3);
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.08), transparent 36%),
    linear-gradient(315deg, rgba(5, 150, 105, 0.08), transparent 30%),
    var(--color-surface);
  border: 1px solid var(--color-surface-hover);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  width: min(100%, 680px);
  max-width: 100%;
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
}

.msg-teaching-diagram:hover {
  transform: translateY(-2px);
  border-color: var(--color-surface-hover);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
}

.diagram-preview-body {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-height: 80vh;
  overflow-y: auto;
}

.preview-content {
  background:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    var(--color-bg);
  background-size: 28px 28px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-surface-hover);
}

.session-empty {
  font-size: 0.8rem;
  color: var(--color-text-faint);
  text-align: center;
  margin-top: 2rem;
}

.session-expand-btn {
  font-size: 0.8rem;
  color: var(--color-primary);
  text-align: center;
  padding: var(--space-2) 0;
  cursor: pointer;
  transition: color var(--transition-base);
  user-select: none;
}

.session-expand-btn:hover {
  color: var(--color-primary-hover, var(--color-primary));
  text-decoration: underline;
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
  padding-top: var(--space-4);
  padding-bottom: var(--space-2);
}

.session-sidebar.collapsed .standard-sidebar-nav {
  padding-top: var(--space-2);
  padding-bottom: var(--space-4);
}

.session-sidebar.collapsed .collapse-toggle-btn,
.session-sidebar.collapsed .nav-item,
.session-sidebar.collapsed .session-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0 0 var(--space-2) 0;
  width: 42px !important;
  height: 42px !important;
  min-width: 42px !important;
  max-width: 42px !important;
  min-height: 42px !important;
  max-height: 42px !important;
  box-sizing: border-box !important;
  border-radius: var(--radius-md);
}

.session-sidebar.collapsed .sidebar-top-header .collapse-toggle-btn {
  margin-bottom: 0;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: row;
  background: var(--color-surface);
  position: relative;
  overflow: hidden;
  height: 100%;
  min-width: 0; /* 关键：防止 flex 子项超出 */
}



.chat-interaction-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0; /* 关键：防止 flex 子项超出 */
  position: relative;
}

.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  box-sizing: border-box; /* 防止 padding 引发溢出 */
}

.welcome-banner {
  text-align: center;
  margin: auto 0;
  color: var(--color-text-secondary);
}

.welcome-icon {
  font-size: 2.5rem;
  color: var(--color-border);
  margin-bottom: 1rem;
}

.welcome-banner h3 {
  font-size: 1.2rem;
  color: var(--color-text);
  margin: 0 0 0.5rem;
}

.welcome-banner p {
  font-size: 0.9rem;
  line-height: 1.6;
  margin: 0;
}

/* ================= 聊天气泡 — 墨韵书房风格 ================= */
.message-row {
  display: flex;
  gap: 0.875rem;
  max-width: 75%;
  animation: msg-appear 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes msg-appear {
  from { opacity: 0; transform: translateY(12px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.message-row.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

/* Avatar — 印章风格 */
.msg-avatar {
  flex-shrink: 0;
  padding-top: 4px;
}

.avatar-circle {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.ai-av {
  background: linear-gradient(135deg, var(--color-text), #3a3a38);
  color: var(--color-surface);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}

.user-av {
  background: var(--color-surface);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}

.bubble-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0; /* 防止内容撑破气泡 */
}

.message-row.user .bubble-wrapper {
  align-items: flex-end;
}

.msg-meta {
  font-size: 0.75rem;
  color: var(--color-text-faint);
  display: flex;
  gap: var(--space-2);
  margin-bottom: 4px;
  align-items: center;
}

.message-row.user .msg-meta {
  flex-direction: row-reverse;
}

.sender {
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
  font-size: 0.8125rem;
  letter-spacing: 0.02em;
}

.message-row.ai .sender {
  color: var(--color-text-muted);
}

.message-row.user .sender {
  color: var(--color-text-faint);
}

/* AI 和 User 气泡高级质感样式 */
.bubble {
  padding: 14px 18px;
  font-size: 0.98rem;
  line-height: 1.65;
  word-break: break-word;
  overflow-wrap: anywhere;
  max-width: 100%;
}



/* AI 气泡：素白宣纸 */
.message-row.ai .bubble {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  border-top-left-radius: 4px;
  color: var(--color-text);
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.message-row.ai .bubble:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  border-color: var(--color-border-hover);
}

/* 用户气泡：淡墨宣纸 */
.message-row.user .bubble {
  background: var(--color-surface-hover) !important;
  color: var(--color-text);
  border: 1px solid var(--color-border) !important;
  border-radius: 16px;
  border-top-right-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}

/* 用户气泡内 Markdown 颜色 */
.message-row.user :deep(.markdown-body) {
  color: var(--color-text) !important;
}
.message-row.user :deep(.markdown-body a) {
  color: var(--color-primary) !important;
  text-decoration: underline;
}
.message-row.user :deep(.markdown-body code:not(pre code)) {
  background: var(--color-border-light) !important;
  color: var(--color-text-secondary) !important;
  border: none;
}

.user-plain-text {
  margin: 0;
  padding: 0;
  color: #1e293b;
  font-size: 16px;
  font-weight: 400;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* markdown 渲染排版及对齐优化 */
:deep(.markdown-body) {
  font-family: var(--font-sans);
  font-size: 0.95rem !important;
  background: transparent !important;
  color: inherit;
  overflow-wrap: anywhere;
  text-align: left; /* 确保严格左对齐 */
  word-break: normal;
  line-height: 1.65;
}

/* 文本 AI 正文使用中性深色与整数像素字号，避免 Windows 字体抗锯齿出现青色笔画。 */
.mode-standard .message-row.ai :deep(.tutor-markdown-block) {
  color: #1e293b !important;
  font-size: 16px !important;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

:deep(.markdown-body > :first-child) {
  margin-top: 0;
}

:deep(.markdown-body > :last-child) {
  margin-bottom: 0;
}

:deep(.markdown-body p) {
  margin: 0 0 0.55rem 0;
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  margin: 0.4rem 0 0.55rem;
  padding-left: 1.15rem;
}

:deep(.markdown-body ul ul),
:deep(.markdown-body ul ol),
:deep(.markdown-body ol ul),
:deep(.markdown-body ol ol) {
  margin: 0.16rem 0 0.1rem;
  padding-left: 1rem;
}

:deep(.markdown-body li) {
  margin: 0.08rem 0;
}

:deep(.markdown-body li > p) {
  margin: 0;
}

:deep(.markdown-body li + li) {
  margin-top: 0.16rem;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4) {
  margin: 0.8rem 0 0.38rem;
  padding-bottom: 0;
  border-bottom: 0;
  line-height: 1.4;
  font-weight: var(--weight-bold);
}

:deep(.markdown-body h1) {
  font-size: 1.16rem;
}

:deep(.markdown-body h2) {
  font-size: 1.08rem;
}

:deep(.markdown-body h3) {
  font-size: 1rem;
}

:deep(.markdown-body h4) {
  font-size: 0.95rem;
}

/* 内联代码优化 */
:deep(.markdown-body code:not(pre code)) {
  padding: 0.12rem 0.32rem;
  border-radius: 5px;
  background: var(--color-surface-hover);
  color: #E11D48;
  font-size: 0.88em;
}

:deep(.markdown-body blockquote) {
  margin: 0.55rem 0;
  padding: 0.08rem 0 0.08rem 0.75rem;
  color: var(--color-text-muted);
  border-left: 3px solid var(--color-border-hover);
}

:deep(.markdown-body pre) {
  margin: 0.8rem 0;
  padding: var(--space-3) var(--space-4);
  overflow-x: auto;
  background: var(--color-bg) !important;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

:deep(.markdown-body pre code),
:deep(.markdown-body pre .hljs) {
  display: block;
  padding: 0;
  background: transparent !important;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.6;
}

/* 附件链接优化 */
.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.attachment-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-base);
}

.attachment-link:hover {
  border-color: var(--color-border-hover);
  background: var(--color-bg);
}

/* ================= 针对极简输入框的优化 ================= */
.minimal-input-panel {
  padding: 0 var(--space-5) var(--space-5) var(--space-5);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: transparent;
  width: 100%;
  box-sizing: border-box;
}

.minimal-attachments-preview {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  width: 100%;
  max-width: 800px;
  flex-wrap: wrap;
  justify-content: flex-start;
  box-sizing: border-box;
}

.minimal-attachment-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-1) var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.minimal-attachment-chip .close-icon {
  cursor: pointer;
  color: var(--color-text-faint);
  transition: color var(--transition-base);
}

.minimal-attachment-chip .close-icon:hover {
  color: var(--color-danger);
}

.minimal-input-wrapper {
  width: 100%;
  max-width: 800px;
  background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-surface-hover) 100%);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255,255,255,0.8);
}

.minimal-input-wrapper:focus-within {
  border-color: var(--color-border-hover);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.9);
}

.minimal-input-wrapper textarea {
  width: 100%;
  border: none;
  background: transparent;
  resize: none;
  height: 24px;
  max-height: 120px;
  overflow-y: auto;
  outline: none;
  font-family: inherit;
  font-size: 1rem;
  color: var(--color-text);
  line-height: 1.5;
  padding: 0 var(--space-1);
  margin: 0;
}

.minimal-input-wrapper textarea::placeholder {
  color: var(--color-text-faint);
}

.minimal-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.action-left, .action-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.minimal-icon-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.15rem;
  background: transparent;
  color: var(--color-text-muted);
  transition: all var(--transition-base);
  padding: 0;
}

.minimal-icon-btn:hover {
  background: var(--color-border);
  color: var(--color-text-secondary);
}

/* Active states (theme colors) */
.minimal-icon-btn.is-active-blue {
  color: #3b82f6;
}
.minimal-icon-btn.is-active-blue:hover {
  background: rgba(59, 130, 246, 0.1);
}

.minimal-icon-btn.is-active-amber {
  color: #d97706;
}
.minimal-icon-btn.is-active-amber:hover {
  background: rgba(217, 119, 6, 0.1);
}

.minimal-icon-btn.is-active-teal {
  color: #14b8a6;
}
.minimal-icon-btn.is-active-teal:hover {
  background: rgba(20, 184, 166, 0.1);
}

.minimal-send-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-border);
  color: var(--color-text-faint);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  transition: all var(--transition-base);
  font-size: 1.1rem;
  margin-left: 4px;
}

.send-arrow-glyph {
  display: block;
  font-family: Arial, sans-serif;
  font-size: 25px;
  font-weight: 600;
  line-height: 1;
  transform: translateY(-1px);
}

.minimal-send-btn.can-send {
  background: var(--color-text);
  color: var(--color-surface);
  cursor: pointer;
}

.minimal-send-btn.can-send:hover {
  background: var(--color-text-strong);
  transform: scale(1.05);
}

.input-footer {
  text-align: center;
  font-size: 0.7rem;
  color: var(--color-text-faint);
  margin-top: var(--space-2);
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--color-border-hover); border-radius: 2px; }

.session-sidebar::after {
  position: absolute;
  top: 0;
  right: -1px;
  bottom: 0;
  z-index: 2;
  width: 1px;
  background: #dde2e8;
  content: "";
  pointer-events: none;
}

.standard-welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.standard-welcome h2 {
  font-size: 1.8rem;
  font-weight: var(--weight-medium);
  color: var(--color-text);
  margin-top: -10vh;
}

.file-icon-box {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}
.remove-attachment-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-faint);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 4px;
}
.remove-attachment-btn:hover {
  color: var(--color-text);
  background: var(--color-surface-hover);
}

/* ================= 思考中指示器 — 类 ChatGPT 风格 ================= */
.thinking-indicator-row {
  display: flex;
  gap: 0.875rem;
  max-width: 75%;
  animation: msg-appear 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.thinking-indicator-row .thinking-avatar {
  flex-shrink: 0;
  padding-top: 4px;
}

.thinking-indicator-row .thinking-avatar .avatar-circle {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  background: linear-gradient(135deg, var(--color-text), #3a3a38);
  color: var(--color-surface);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}

.thinking-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  border-top-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
  width: fit-content;
}

.thinking-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 20px;
}

.thinking-dots span {
  width: 6px;
  height: 6px;
  background: var(--color-text-muted);
  border-radius: 50%;
  animation: thinking-dot-bounce 1.4s infinite ease-in-out both;
}

.thinking-dots span:nth-child(1) {
  animation-delay: 0s;
}

.thinking-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-dot-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.thinking-text {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  font-weight: var(--weight-medium);
  letter-spacing: 0.02em;
}

/* 思考状态与 AI 消息框的区别：
   - AI 消息框：大段文字内容，白色背景，完整消息气泡
   - 思考指示器：更紧凑，带点动画，灰色文字，表示"正在处理中"
*/


/* ================= 优化后的消息、附件、等待状态与输入区 ================= */
.mode-standard .chat-viewport {
  gap: 26px;
  padding: 28px clamp(18px, 4vw, 56px) 32px;
}

.message-row {
  width: min(900px, 100%);
  max-width: 100%;
  gap: 12px;
}

.message-row.ai {
  align-self: flex-start;
}

.message-row.user {
  width: auto;
  max-width: min(680px, 78%);
}

.message-row.ai .bubble-wrapper {
  width: min(830px, calc(100vw - 150px));
  align-items: stretch;
}

.message-row.user .bubble-wrapper {
  max-width: 100%;
}

.msg-avatar {
  padding-top: 2px;
}

.avatar-circle {
  width: 30px;
  height: 30px;
  border-radius: 8px;
}

.ai-av {
  background: #111827;
  box-shadow: none;
}

.msg-meta {
  min-height: 18px;
  margin-bottom: 1px;
  gap: 7px;
}

.sender {
  font-size: 0.76rem;
  letter-spacing: 0;
}

.msg-meta .time {
  font-size: 0.68rem;
}

.bubble {
  max-width: 100%;
  padding: 0;
}

.message-row.ai .bubble,
.message-row.ai .bubble:hover {
  color: var(--color-text);
  background: color-mix(in srgb, var(--color-surface) 92%, transparent);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.035);
}

.message-row.ai .assistant-answer {
  padding: 14px 16px;
}

.assistant-failed-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 100%;
  padding: 12px 14px;
  background: #fff8f8;
  border: 1px solid #fecaca;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(239, 68, 68, 0.06);
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
  color: #dc2626;
}

.failed-icon svg {
  width: 16px;
  height: 16px;
}

.failed-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: #b91c1c;
}

.failed-message {
  margin: 0;
  font-size: 0.84rem;
  line-height: 1.5;
  color: #7f1d1d;
  word-break: break-word;
}

.failed-actions {
  display: flex;
  align-items: center;
  margin-top: 4px;
}

.failed-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #fff;
  background: #dc2626;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.failed-retry-btn:hover:not(:disabled) {
  background: #b91c1c;
}

.failed-retry-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.failed-retry-btn svg {
  width: 14px;
  height: 14px;
}

.message-row.user .bubble {
  padding: 11px 14px;
  color: var(--color-text);
  background: #f4f5f7 !important;
  border: 1px solid #e4e7eb !important;
  border-radius: 12px;
  border-top-right-radius: 4px;
  box-shadow: none;
}

.user-plain-text {
  font-size: 16px;
  line-height: 1.65;
}

.message-image-gallery {
  display: grid;
  gap: 5px;
  width: min(520px, 100%);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: #eef1f4;
}

.message-row.user .message-image-gallery {
  align-self: flex-end;
}

.message-image-gallery.is-single {
  grid-template-columns: minmax(0, 1fr);
  width: min(440px, 100%);
}

.message-image-gallery.is-pair {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.message-image-gallery.is-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.message-image {
  display: block;
  width: 100%;
  height: 180px;
  cursor: zoom-in;
  background: #e5e7eb;
}

.message-image-gallery.is-single .message-image {
  height: clamp(220px, 34vw, 360px);
}

.message-image-gallery.is-grid .message-image:first-child:nth-last-child(3) {
  grid-row: span 2;
  height: 365px;
}

.message-image-gallery.is-grid .message-image:first-child:nth-last-child(3) ~ .message-image {
  height: 180px;
}

.message-image {
  transition: transform 180ms ease;
}

.message-image:hover {
  transform: scale(1.015);
}

.image-load-error {
  display: grid;
  place-items: center;
  gap: 5px;
  width: 100%;
  height: 100%;
  color: var(--color-text-muted);
  background: #f8fafc;
  font-size: 12px;
}

.message-file-list {
  display: grid;
  gap: 7px;
  width: min(420px, 100%);
}

.message-row.user .message-file-list {
  align-self: flex-end;
}

.message-file-card {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 9px 10px;
  color: inherit;
  text-decoration: none;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 9px;
  transition: border-color 150ms ease, background 150ms ease;
}

.message-file-card:hover {
  background: #fafbfc;
  border-color: #cbd5e1;
}

.message-file-card > svg {
  width: 17px;
  height: 17px;
  stroke: var(--color-text-faint);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.5;
}

.file-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.file-copy strong {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-copy small {
  color: var(--color-text-faint);
  font-size: 10px;
}

.message-actions {
  display: flex;
  min-height: 24px;
  align-items: center;
  opacity: 0;
  transition: opacity 150ms ease;
}

.message-row.ai:hover .message-actions,
.message-actions:focus-within {
  opacity: 1;
}

.message-actions button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 6px;
  color: var(--color-text-faint);
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 10px;
}

.message-actions button:hover {
  color: var(--color-text-secondary);
  background: var(--color-bg);
}

.message-actions svg {
  width: 14px;
  height: 14px;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.4;
}

.thinking-indicator-row {
  width: min(900px, 100%);
  max-width: 100%;
}

.pre-answer-state {
  width: min(620px, calc(100vw - 150px));
  padding: 14px 15px 13px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, .96), rgba(248, 250, 252, .94)),
    radial-gradient(circle at 18% 0%, rgba(37, 99, 235, .08), transparent 42%);
  border: 1px solid #dfe6ef;
  border-radius: 12px;
  box-shadow: 0 8px 26px rgba(15, 23, 42, 0.045);
}

.pre-answer-state.is-inline {
  width: min(650px, 100%);
}

.pre-answer-head {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.pre-answer-head > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.pre-answer-head strong {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 650;
}

.pre-answer-head span:not(.thinking-core) {
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.thinking-core {
  position: relative;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  color: #2563eb;
  background: #f8fbff;
  border: 1px solid #d8e5f8;
  border-radius: 10px;
}

.thinking-core::before {
  position: absolute;
  inset: 6px;
  border: 2px solid rgba(37, 99, 235, .15);
  border-top-color: currentColor;
  border-radius: 50%;
  content: '';
  animation: thinking-ring-turn 1.15s linear infinite;
}

.thinking-core i {
  position: absolute;
  width: 3px;
  height: 3px;
  background: currentColor;
  border-radius: 50%;
  animation: thinking-core-pulse 1.35s ease-in-out infinite;
}

.thinking-core i:nth-child(1) { transform: translateX(-6px); animation-delay: 0s; }
.thinking-core i:nth-child(2) { animation-delay: 0.16s; }
.thinking-core i:nth-child(3) { transform: translateX(6px); animation-delay: 0.32s; }

.minimal-input-panel {
  position: relative;
  z-index: 5;
  padding: 16px clamp(16px, 3vw, 38px) 14px;
  background:
    linear-gradient(
      to top,
      var(--color-surface) 0%,
      var(--color-surface) 76%,
      rgba(255, 255, 255, 0.88) 90%,
      transparent 100%
    );
}

.minimal-input-wrapper {
  width: min(100%, 860px);
  max-width: 860px;
  gap: 8px;
  padding: 12px 14px 10px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid #dfe3e8;
  border-radius: 24px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 7px 24px rgba(15, 23, 42, 0.07);
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease;
}

.minimal-input-wrapper:hover {
  border-color: #cfd5dc;
}

.minimal-input-wrapper:focus-within {
  border-color: #b9c1cb;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 9px 30px rgba(15, 23, 42, 0.09);
}

.minimal-input-wrapper textarea {
  width: 100%;
  min-height: 28px;
  max-height: 200px;
  padding: 2px 4px 3px;
  overflow-y: hidden;
  color: var(--color-text);
  font-size: 0.98rem;
  line-height: 1.55;
  scrollbar-color: #c8ced6 transparent;
  scrollbar-width: thin;
}

.minimal-input-wrapper textarea::placeholder {
  color: #8b949f;
  opacity: 1;
}

.minimal-input-wrapper textarea::-webkit-scrollbar {
  width: 5px;
}

.minimal-input-wrapper textarea::-webkit-scrollbar-thumb {
  background: #c8ced6;
  border-radius: 999px;
}

.minimal-input-wrapper textarea::-webkit-scrollbar-track {
  background: transparent;
}

.composer-attachments {
  display: flex;
  gap: 8px;
  width: 100%;
  padding: 0 2px 10px;
  overflow-x: auto;
  border-bottom: 1px solid #edf0f3;
  scrollbar-color: #cfd5dc transparent;
  scrollbar-width: thin;
}

.composer-attachment {
  position: relative;
  flex: 0 0 auto;
  overflow: hidden;
  background: #f7f8fa;
  border: 1px solid #e1e5ea;
  border-radius: 12px;
}

.composer-attachment.is-image {
  width: 116px;
  height: 82px;
}

.composer-image {
  width: 100%;
  height: 100%;
}

.composer-image-name {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  overflow: hidden;
  padding: 18px 7px 5px;
  color: #fff;
  background: linear-gradient(transparent, rgba(15, 23, 42, .72));
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-attachment.is-file {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  width: 230px;
  min-height: 62px;
  padding: 9px 32px 9px 9px;
}

.composer-attachment .remove-attachment-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  padding: 0;
  color: #fff;
  background: rgba(15, 23, 42, .65);
  border: 0;
  border-radius: 50%;
  cursor: pointer;
  backdrop-filter: blur(6px);
}

.composer-attachment.is-file .remove-attachment-btn {
  color: var(--color-text-muted);
  background: #fff;
  border: 1px solid #dfe3e8;
}

.minimal-action-bar {
  min-height: 36px;
  margin-top: 0;
}

.action-left,
.action-right {
  gap: 6px;
}

.action-left {
  min-width: 0;
}

.input-tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 32px;
  padding: 5px 10px;
  color: #5f6874;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 520;
  white-space: nowrap;
  transition:
    color 140ms ease,
    background 140ms ease,
    border-color 140ms ease;
}

.input-tool-btn:hover:not(:disabled) {
  color: #22272e;
  background: #f3f5f7;
  border-color: #e6e9ed;
}

.input-tool-btn.is-active-blue {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.input-tool-btn.is-active-teal {
  color: #0f766e;
  background: #f0fdfa;
  border-color: #99f6e4;
}

.input-tool-btn.is-active-purple {
  color: #7c3aed;
  background: #f5f3ff;
  border-color: #c4b5fd;
}

.input-tool-btn:disabled {
  cursor: wait;
  opacity: .58;
}

.minimal-send-btn {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  margin-left: 2px;
  border-radius: 50%;
}

.send-arrow-glyph {
  font-size: 23px;
  transform: translateY(-1px);
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px 14px;
  width: min(100%, 860px);
  margin-top: 7px;
  color: #8a939e;
  font-size: 10px;
  line-height: 1.4;
  text-align: center;
}

.input-footer span + span::before {
  margin-right: 14px;
  color: #c2c8cf;
  content: "·";
}

.minimal-input-wrapper.is-responding {
  border-color: #d5dae0;
  background: #fcfcfd;
}

.minimal-send-btn:disabled {
  cursor: default;
}

.minimal-send-btn.is-responding,
.minimal-send-btn.is-responding:disabled {
  color: #475569;
  background: #eef2f6;
  cursor: wait;
  opacity: 1;
}

.minimal-send-btn.is-responding:hover {
  background: #eef2f6;
  transform: none;
}

.responding-spinner {
  width: 17px;
  height: 17px;
  font-size: 17px;
  animation: tutor-response-spin 0.8s linear infinite;
}

@keyframes tutor-response-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes thinking-core-pulse {
  0%, 75%, 100% { opacity: .28; transform: translateX(var(--tx, 0)) scale(.72); }
  36% { opacity: 1; transform: translateX(var(--tx, 0)) scale(1); }
}

.thinking-core i:nth-child(1) { --tx: -7px; }
.thinking-core i:nth-child(2) { --tx: 0px; }
.thinking-core i:nth-child(3) { --tx: 7px; }

@keyframes thinking-ring-turn {
  to { transform: rotate(360deg); }
}

@media (max-width: 760px) {
  .mode-standard .chat-viewport {
    padding: 18px 12px 24px;
  }

  .message-row.user {
    max-width: 88%;
  }

  .message-row.ai .bubble-wrapper,
  .pre-answer-state {
    width: calc(100vw - 72px);
  }

  .message-image-gallery.is-single {
    width: min(360px, 100%);
  }

  .message-image-gallery.is-grid .message-image:first-child:nth-last-child(3) {
    grid-row: auto;
    height: 160px;
  }

  .message-image-gallery.is-grid .message-image,
  .message-image-gallery.is-pair .message-image {
    height: 150px;
  }

  .diagram-generation-panel {
    grid-template-columns: 1fr;
  }

  .diagram-blueprint {
    min-height: 96px;
  }

  .minimal-input-panel {
    padding: 0 10px 10px;
  }

  .input-tool-btn span {
    display: none;
  }

  .input-tool-btn {
    width: 31px;
    justify-content: center;
    padding: 0;
  }

  .preview-content {
    padding: 10px;
  }

  .preview-footer > span {
    display: none;
  }

  .preview-footer {
    justify-content: flex-end;
  }
}

@media (prefers-reduced-motion: reduce) {
  .thinking-core i,
  .thinking-core::before,
  .blueprint-node,
  .diagram-generation-progress span {
    animation: none;
  }
}

/* ================= 删除对话确认弹窗 ================= */
.delete-confirm-overlay {
  align-items: flex-start;
  justify-content: center;
  padding-top: 22vh;
}

.delete-confirm-dialog {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 50px rgba(32, 95, 103, 0.12);
  width: 360px;
  max-width: calc(100vw - 32px);
  padding: var(--space-7) var(--space-7) var(--space-5);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  animation: scaleIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.delete-confirm-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-danger);
  font-size: 1.3rem;
  margin-bottom: var(--space-4);
}

.delete-confirm-title {
  margin: 0 0 var(--space-2);
  font-size: 1.1rem;
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.delete-confirm-desc {
  margin: 0 0 var(--space-5);
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--color-text-muted);
  word-break: break-all;
}

.delete-confirm-actions {
  display: flex;
  gap: var(--space-3);
  width: 100%;
}

.delete-confirm-actions .btn {
  flex: 1;
  height: 38px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-confirm-actions .btn-cancel {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.delete-confirm-actions .btn-cancel:hover {
  background: var(--color-border);
  color: var(--color-text);
}

.delete-confirm-actions .btn-danger {
  background: var(--color-danger);
  color: #ffffff;
}

.delete-confirm-actions .btn-danger:hover {
  background: #a8324d;
}

</style>
