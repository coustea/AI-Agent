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
              popper-style="padding: 16px 12px 12px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);"
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
              popper-style="padding: 12px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);"
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
          <DigitalHumanCanvas
              :is-ready="isAvatarReady"
              :is-connected="isAvatarConnected"
              :audio-enabled="avatarAudioEnabled"
              :idle-countdown="avatarIdleCountdown"
              ref="canvasRef"
              @enable-audio="enableAvatarAudio"
              @disconnect="disconnectAvatar"
              @reconnect="handleAvatarReconnect"
          />

          <div class="digital-human-status-overlay" :class="{ active: isAIThinking || isAvatarSpeaking || isVadListening }">
            <div class="speech-wave" v-if="isAIThinking || isAvatarSpeaking">
              <span></span><span></span><span></span><span></span><span></span>
            </div>
            <div class="status-badge">{{ digitalHumanStatusText }}</div>
          </div>
        </div>

        <div class="chat-interaction-area">
          <div class="chat-viewport" ref="chatScroll">
            <div class="standard-welcome" v-if="chatMode === 'standard' && messages.length === 0">
              <h2>你好，学习者！</h2>
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

              <div class="bubble-wrapper" @click="handleMessageClick">
                <div class="msg-meta">
                  <span class="sender">{{ msg.role === 'ai' ? 'AI 导师' : 'You' }}</span>
                  <span class="time">{{ msg.time }}</span>
                </div>

                <div class="bubble">
                  <TutorMessageContent
                      :content="msg.content"
                      :is-streaming="isStreamingMessage(msg)"
                  />
                </div>

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

                  <img
                      v-if="msg.diagram.image_url"
                      :src="msg.diagram.image_url"
                      :alt="msg.diagram.title || 'AI 图解'"
                      class="diagram-image"
                  />
                  <div
                      v-else
                      class="diagram-svg-container"
                      v-html="diagramSvgCache.get(msg.diagram.render.source) || ''"
                  ></div>
                </div>
              </div>
            </div>

            <div v-if="showThinkingIndicator" class="message-row ai thinking-row">
              <div class="msg-avatar"><div class="avatar-circle ai-av"><el-icon><Service /></el-icon></div></div>
              <div class="bubble thinking-bubble">
                <div class="typing-dots">
                  <span></span><span></span><span></span>
                </div>
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
                <el-popover
                    placement="top-start"
                    trigger="click"
                    :width="220"
                    popper-class="custom-plus-popover"
                    :show-arrow="false"
                    :offset="12"
                >
                  <template #reference>
                    <button class="standard-plus-btn" :disabled="uploadingFile" title="更多功能">
                      <el-icon><Plus /></el-icon>
                    </button>
                  </template>

                  <div class="action-menu">
                    <div class="action-item" @click="triggerFileUpload">
                      <div class="item-icon-wrapper bg-blue">
                        <el-icon><Document /></el-icon>
                      </div>
                      <div class="item-content">
                        <span class="item-text">上传文件</span>
                        <el-icon class="item-arrow"><ArrowRight /></el-icon>
                      </div>
                    </div>
                    <div class="action-item" @click="triggerFileUpload">
                      <div class="item-icon-wrapper bg-blue">
                        <el-icon><Picture /></el-icon>
                      </div>
                      <div class="item-content">
                        <span class="item-text">上传图片</span>
                        <el-icon class="item-arrow"><ArrowRight /></el-icon>
                      </div>
                    </div>
                    <div class="action-item" @click="handleImageToggle">
                      <div class="item-icon-wrapper" :class="needDiagram ? 'bg-active' : 'bg-purple'">
                        <el-icon><DataLine /></el-icon>
                      </div>
                      <div class="item-content">
                        <span class="item-text">{{ needDiagram ? '取消生成图解' : '生成图解' }}</span>
                        <el-icon class="item-arrow"><ArrowRight /></el-icon>
                      </div>
                    </div>
                    <div class="action-item" @click="handleVideoToggle">
                      <div class="item-icon-wrapper" :class="generateVideo ? 'bg-active' : 'bg-teal'">
                        <el-icon><VideoCamera /></el-icon>
                      </div>
                      <div class="item-content">
                        <span class="item-text">{{ generateVideo ? '取消生成视频' : '生成视频' }}</span>
                        <el-icon class="item-arrow"><ArrowRight /></el-icon>
                      </div>
                    </div>
                  </div>
                </el-popover>

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
                    <el-icon class="icon-default"><DataLine /></el-icon>
                    <el-icon class="icon-hover"><Close /></el-icon>
                  </div>
                  <span>图解</span>
                </div>

                <div class="active-media-chip" v-if="generateVideo" @click="handleVideoToggle" title="取消生成视频">
                  <div class="chip-icon-circle">
                    <el-icon class="icon-default"><VideoCamera /></el-icon>
                    <el-icon class="icon-hover"><Close /></el-icon>
                  </div>
                  <span>视频</span>
                </div>
              </div>

              <textarea
                  ref="textareaRef"
                  v-model="userInput"
                  placeholder="向 AI 导师提问（Enter 发送，Shift + Enter 换行）"
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

                <el-tooltip content="发送问题" placement="top" :show-after="500">
                  <button class="send-btn" :class="{ 'can-send': userInput.trim() || pendingFiles.length > 0 }" @click="handleSend">
                    <el-icon><Top /></el-icon>
                  </button>
                </el-tooltip>
              </div>

            </div>
            <div class="input-footer">内容由 AI 生成，仅供参考。</div>
          </div>
        </div>

        <input ref="fileInput" type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onCombinedFileSelected" />
      </section>

      <aside class="profile-sidebar">
        <div class="sidebar-header">
          <div class="header-title-row">
            <h3>动态学习画像</h3>
            <div class="sync-badge" :class="{ 'is-syncing': profileUpdated }">
              <span class="dot"></span> <span>Live</span>
            </div>
          </div>
        </div>

        <div class="profile-cards-container" v-if="profileCards.length > 0">
          <div
              v-for="card in profileCards"
              :key="card.key"
              :class="['insight-card', { 'special-card': card.key === '最近变化' || card.key === '推荐辅导策略' }]"
          >
            <div class="card-header">
              <div class="card-icon-wrap">
                <el-icon><component :is="getProfileCardIcon(card.key)" /></el-icon>
              </div>
              <span class="card-title">{{ card.title }}</span>
            </div>
            <div class="card-body">
              <div class="card-content">
                <div v-for="(line, idx) in card.content.split('\n')" :key="idx" class="content-line">
                  <template v-if="line.trim().startsWith('-') || line.trim().startsWith('*') || line.trim().startsWith('•')">
                    <span class="bullet-item">
                      <span class="dot-marker"></span>
                      <span class="text">{{ line.trim().replace(/^[-*•]\s*/, '') }}</span>
                    </span>
                  </template>
                  <template v-else-if="line.trim()">
                    <p class="plain-text">{{ line }}</p>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="profile-empty-state" v-else>
          <div class="empty-visual-container">
            <div class="pulse-ring"></div>
            <div class="pulse-ring delay-1"></div>
            <div class="pulse-ring delay-2"></div>
            <div class="empty-visual">
              <el-icon><Cpu /></el-icon>
            </div>
          </div>
          <div class="empty-text-wrap">
            <h4>待捕获画像特征</h4>
            <p>由于对话样本较少，您的动态学习画像仍在生成中。多和我交流，我会为您建立更精准的画像。</p>
          </div>
          <div class="empty-hints">
            <div class="hint-item"><el-icon><ChatLineRound /></el-icon> <span>深度交流</span></div>
            <div class="hint-item"><el-icon><Aim /></el-icon> <span>定位痛点</span></div>
            <div class="hint-item"><el-icon><TrendCharts /></el-icon> <span>反馈进度</span></div>
          </div>
        </div>

        <div class="long-term-memory-section">
          <div class="memory-header-row">
            <div class="memory-title-wrap">
              <span class="memory-title">长期记忆</span>
              <el-icon class="info-icon"><InfoFilled /></el-icon>
            </div>
            <div class="memory-switch-wrap">
              <span class="switch-status">{{ memoryEnabled ? '已启用' : '未启用' }}</span>
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
import { ref, nextTick, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import {
  ChatLineRound, Avatar, Cpu, Service, UserFilled,
  Picture, Microphone, Document, ChatDotRound, ChatLineSquare,
  Plus, Delete, Close, Top, ArrowRight,
  EditPen, Search, Timer, VideoCamera, DataLine,
  CircleCheckFilled,
  InfoFilled, Medal, Aim, Loading, TrendCharts
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import 'github-markdown-css/github-markdown-light.css'
// 更换为深色主题以匹配深色代码块
import 'highlight.js/styles/atom-one-dark.css'
import mermaid from 'mermaid'
import { getErrorMessage } from '@/utils/http'
import TutorMessageContent from '@/components/TutorMessageContent.vue'

import { getProfile } from '@/api/ai'
import {
  streamChat,
  uploadFile,
  uploadDiagramImage,
  getSessions,
  createSession,
  deleteSession,
  updateSessionTitle,
  getChatHistory,
  type ChatSession,
} from '@/api/chat'
import { getMe } from '@/api/auth'
import { useDigitalHuman } from '@/views/digital-human/useDigitalHuman'
import DigitalHumanCanvas from '@/views/digital-human/DigitalHumanCanvas.vue'

// 类型定义
interface PendingFile {
  file?: File;
  url?: string;
  fileType: string;
  name: string
}
interface Attachment {
  url: string;
  type: string;
  name: string
}
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
  image_url?: string
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
interface ProfileCard {
  key: string
  title: string
  content: string
}

const DEFAULT_SESSION_TITLE = '新对话'
const SESSION_TITLE_REFRESH_DELAYS = [300, 800, 1500, 3000]

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
})

// 状态
const chatMode = ref('standard')
const userInput = ref('')
const isAIThinking = ref(false)
const chatScroll = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isExpandedInput = ref(false)

const enableWebSearch = ref(false)
const needDiagram = ref(false)
const generateVideo = ref(false)
const hasToggledMedia = ref(false)

const isRecording = ref(false)
const isVoiceChatting = ref(false)
const lastAsrText = ref('')
const lastAsrCommittedText = ref('')
let lastAsrCommitAt = 0

const canvasRef = ref<InstanceType<typeof DigitalHumanCanvas> | null>(null)
const {
  isConnected: isAvatarConnected,
  isAvatarReady,
  isSpeaking: isAvatarSpeaking,
  isListening: isVadListening,
  audioEnabled: avatarAudioEnabled,
  idleCountdown: avatarIdleCountdown,
  connect: connectAvatar,
  disconnect: disconnectAvatar,
  sendText: sendAvatarText,
  startVad,
  stopVad,
  enableAudio: enableAvatarAudio,
  setPlayerContainer,
} = useDigitalHuman({
  onAssistantChunk: (chunk) => {
    if (isVoiceChatting.value && isVadListening.value) {
      stopVad()
      isRecording.value = false
    }
    if (streamingMsgId.value === null) {
      const aiMsgId = Date.now() + 1
      messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
      streamingMsgId.value = aiMsgId
      isAIThinking.value = true
    }
    if (streamingMsgId.value !== null) {
      enqueueStreamChunk(streamingMsgId.value, chunk)
    }
  },
  onDiagram: (diagram) => {
    if (!diagram || streamingMsgId.value === null) return
    const aiMsg = messages.value.find(m => m.id === streamingMsgId.value)
    if (!aiMsg) return
    aiMsg.diagram = diagram as DiagramData
    aiMsg.diagramGenerating = false
    scrollToBottom()
  },
  onAssistantComplete: () => {
    flushPendingStreamText(true)
    isAIThinking.value = false
    streamingMsgId.value = null
    scheduleProfilePoll()
    if (isVoiceChatting.value && chatMode.value === 'digital_human' && isAvatarConnected.value) {
      window.setTimeout(async () => {
        if (!isVoiceChatting.value || chatMode.value !== 'digital_human' || !isAvatarConnected.value) return
        await startVad()
        isRecording.value = isVadListening.value
      }, 350)
    }
  },
  onAsrResult: (text) => {
    const normalized = text.replace(/\s+/g, ' ').trim()
    lastAsrText.value = normalized
    if (normalized) {
      const nowTs = Date.now()
      const isDup = normalized === lastAsrCommittedText.value
      const isNearDup = normalized.includes(lastAsrCommittedText.value) || lastAsrCommittedText.value.includes(normalized)
      const committedRecently = nowTs - lastAsrCommitAt < 1400
      if (isDup || (isNearDup && committedRecently)) return
      lastAsrCommittedText.value = normalized
      lastAsrCommitAt = nowTs
      messages.value.push({
        id: Date.now(),
        role: 'user',
        content: normalized,
        time: now(),
      })
      if (streamingMsgId.value === null) {
        const aiMsgId = Date.now() + 1
        messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
        streamingMsgId.value = aiMsgId
      }
      isAIThinking.value = true
      scrollToBottom()
    }
  },
  onVadStateChange: (listening) => {
    isRecording.value = listening
    if (!listening) {
      lastAsrText.value = ''
    }
  },
  onError: (msg) => {
    ElMessage.error({ message: msg, plain: true })
  },
  onAvatarReady: () => {
    nextTick(() => {
      const container = canvasRef.value?.getContainer()
      if (container) {
        setPlayerContainer(container)
      }
    })
  },
})

const uploadingFile = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const pendingFiles = ref<PendingFile[]>([])

const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | undefined>(undefined)
const sessionSidebarCollapsed = ref(false)
const currentUserId = ref<string | number | null>(null)
const searchPopoverVisible = ref(false)
const searchKeyword = ref('')

const messages = ref<ChatMsg[]>([])
const streamingMsgId = ref<number | null>(null)
let abortController: AbortController | null = null

const profileUpdated = ref(false)
const memoryEnabled = ref(false)
const profileCards = ref<ProfileCard[]>([])
let profilePollTimers: ReturnType<typeof setTimeout>[] = []

const fabPos = ref({ x: 16, y: 0 })
const isDragging = ref(false)
const showFabMenu = ref(false)
const isDimmed = ref(false)
const isStickRight = computed(() => fabPos.value.x > window.innerWidth / 2)

let dragStartX = 0
let dragStartY = 0
let dragInitialX = 0
let dragInitialY = 0
let dragDistance = 0
let dimTimer: number | null = null

let diagramRenderSeq = 0
const diagramSvgCache = ref<Map<string, string>>(new Map())

let scrollPending = false
let streamFlushHandle: number | null = null
let pendingStreamText = ''
let pendingStreamTargetId: number | null = null
let lastAutoScrollAt = 0
const STREAM_SCROLL_INTERVAL_MS = 64

// 计算属性
const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return sessions.value.filter(s => {
    const title = s.title || '新建对话'
    return title.toLowerCase().includes(keyword)
  })
})

const showThinkingIndicator = computed(() => {
  if (!isAIThinking.value) return false
  if (chatMode.value === 'digital_human') return false
  const streamingMsg = messages.value.find(m => m.id === streamingMsgId.value)
  return !streamingMsg || !streamingMsg.content
})

const isStreamingMessage = (msg: ChatMsg) => msg.id === streamingMsgId.value && isAIThinking.value
const digitalHumanStatusText = computed(() => {
  if (isAIThinking.value || isAvatarSpeaking.value) return '正在多模态解答中...'
  if (isVadListening.value && lastAsrText.value) {
    const preview = lastAsrText.value.length > 36 ? `${lastAsrText.value.slice(0, 36)}...` : lastAsrText.value
    return `识别中：${preview}`
  }
  if (isVadListening.value) return '正在识别语音...'
  return '倾听就绪'
})

// 工具函数
const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败，请重试')
  }
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

const PROFILE_CARD_ICON_MAP: Record<string, any> = {
  基础信息: Medal,
  当前学习项目背景: Aim,
  技术能力判断: Aim,
  学习偏好: Timer,
  当前薄弱点: Aim,
  兴趣方向: Medal,
  推荐辅导策略: Service,
  最近变化: Timer,
}

const normalizeCardKey = (title: string) => title.replace(/[\/\s]/g, '')

const getProfileCardIcon = (key: string) => {
  return PROFILE_CARD_ICON_MAP[key] || DataLine
}

const parseProfileMarkdown = (profileMarkdown: string): ProfileCard[] => {
  const cards: ProfileCard[] = []
  let currentTitle = ''
  const currentLines: string[] = []

  const flush = () => {
    if (!currentTitle) return
    const text = currentLines.join('\n').trim() || '暂无明显信息'
    cards.push({
      key: normalizeCardKey(currentTitle),
      title: currentTitle,
      content: text,
    })
  }

  for (const line of profileMarkdown.split('\n')) {
    const heading = line.match(/^##\s+(.+?)\s*$/)
    if (heading) {
      flush()
      currentTitle = (heading[1] ?? '').trim()
      currentLines.length = 0
      continue
    }
    if (currentTitle) {
      currentLines.push(line)
    }
  }
  flush()
  return cards
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
  const nowTs = Date.now()
  if (!force && nowTs - lastAutoScrollAt < STREAM_SCROLL_INTERVAL_MS) {
    return
  }
  lastAutoScrollAt = nowTs
  scrollToBottom()
}

const flushPendingStreamText = (forceScroll = false) => {
  if (streamFlushHandle != null) {
    cancelAnimationFrame(streamFlushHandle)
    streamFlushHandle = null
  }
  if (!pendingStreamText || pendingStreamTargetId == null) {
    pendingStreamText = ''
    pendingStreamTargetId = null
    return
  }

  const aiMsg = messages.value.find(m => m.id === pendingStreamTargetId)
  if (aiMsg) {
    aiMsg.content += pendingStreamText
    scrollToBottomThrottled(forceScroll)
  }

  pendingStreamText = ''
  pendingStreamTargetId = null
}

const enqueueStreamChunk = (messageId: number, chunk: string) => {
  if (!chunk) return

  if (pendingStreamTargetId !== null && pendingStreamTargetId !== messageId) {
    flushPendingStreamText()
  }

  pendingStreamTargetId = messageId
  pendingStreamText += chunk

  if (streamFlushHandle != null) return
  streamFlushHandle = requestAnimationFrame(() => {
    streamFlushHandle = null
    flushPendingStreamText()
  })
}

const autoResize = () => {
  const el = textareaRef.value
  if (!el) return
  el.style.height = '24px'
  const currentHeight = el.scrollHeight

  if (currentHeight > 30) {
    isExpandedInput.value = true
    el.style.height = `${Math.min(currentHeight, 120)}px`
  } else {
    isExpandedInput.value = false
    el.style.height = '24px'
  }
}

const renderMermaid = async (source: string): Promise<string> => {
  try {
    diagramRenderSeq += 1
    const { svg } = await mermaid.render(`mermaid-${Date.now()}-${diagramRenderSeq}`, source)
    return svg
  } catch {
    return `<pre class="mermaid-error">图解渲染失败</pre>`
  }
}

const svgToPng = (svgString: string): Promise<Blob> => {
  return new Promise((resolve, reject) => {
    const tempDiv = document.createElement('div')
    tempDiv.style.position = 'absolute'
    tempDiv.style.visibility = 'hidden'
    tempDiv.style.width = '800px'
    document.body.appendChild(tempDiv)
    tempDiv.innerHTML = svgString

    const svgElement = tempDiv.querySelector('svg')
    if (!svgElement) {
      document.body.removeChild(tempDiv)
      reject(new Error('SVG element not found'))
      return
    }

    let width = svgElement.clientWidth || svgElement.getBoundingClientRect().width || 600
    let height = svgElement.clientHeight || svgElement.getBoundingClientRect().height || 400

    const maxWidth = 800
    const maxHeight = 600
    if (width > maxWidth) {
      height = (height * maxWidth) / width
      width = maxWidth
    }
    if (height > maxHeight) {
      width = (width * maxHeight) / height
      height = maxHeight
    }

    document.body.removeChild(tempDiv)

    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      reject(new Error('Canvas context not available'))
      return
    }

    canvas.width = width * 2
    canvas.height = height * 2
    ctx.scale(2, 2)

    ctx.fillStyle = '#FFFFFF'
    ctx.fillRect(0, 0, width, height)

    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)

    const img = new Image()
    img.onload = () => {
      ctx.drawImage(img, 0, 0, width, height)
      URL.revokeObjectURL(url)

      canvas.toBlob((blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('Canvas toBlob failed'))
        }
      }, 'image/png')
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Image load failed'))
    }
    img.src = url
  })
}

const uploadDiagramPng = async (sessionId: string, pngBlob: Blob): Promise<string | null> => {
  try {
    const res = await uploadDiagramImage(pngBlob, sessionId)
    return res.data.data?.url || null
  } catch (err) {
    console.error('[Diagram] PNG upload failed:', err)
    return null
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

  if (currentSessionId.value) {
    svgToPng(svg)
        .then((pngBlob) => uploadDiagramPng(currentSessionId.value!, pngBlob))
        .then((imageUrl) => {
          if (imageUrl && diagram) {
            diagram.image_url = imageUrl
          }
        })
        .catch((err) => {
          console.warn('[Diagram] PNG conversion/upload failed:', err)
        })
  }

  return svg
}

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

const fetchProfile = async () => {
  try {
    const res = await getProfile()
    const data = res.data.data
    if (!data) return

    const markdown = (data.profile_markdown || '').trim()
    const nextCards = markdown ? parseProfileMarkdown(markdown) : []
    const changed = JSON.stringify(nextCards) !== JSON.stringify(profileCards.value)
    profileCards.value = nextCards

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
  } catch (err) {
    ElMessage.error({ message: getErrorMessage(err, '加载会话历史失败'), plain: true })
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

const triggerFileUpload = () => fileInput.value?.click()

const onCombinedFileSelected = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const isImage = file.type.startsWith('image/') || /\.(png|jpg|jpeg|gif|webp)$/i.test(file.name)
  const fileType = isImage ? 'image' : 'document'
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

const handleVoiceToggle = async () => {
  if (chatMode.value === 'digital_human') {
    if (isVadListening.value) {
      stopVad()
      isRecording.value = false
    } else {
      await startVad()
      isRecording.value = isVadListening.value
    }
    return
  }
  isRecording.value = !isRecording.value
  if (isRecording.value) {
    ElMessage.success({ message: '开始录音，请说话...', plain: true })
  } else {
    ElMessage.info({ message: '录音结束，正在发送...', plain: true })
  }
}

const handleVoiceChatToggle = async () => {
  if (!isVoiceChatting.value) {
    isVoiceChatting.value = true
    chatMode.value = 'digital_human'
    await connectAvatar()
    nextTick(() => {
      const container = canvasRef.value?.getContainer()
      if (container) {
        setPlayerContainer(container)
      }
    })
    await startVad()
    isRecording.value = isVadListening.value
    ElMessage.success({ message: '已开启语音通话模式，您可以直接说话', plain: true })
  } else {
    stopVad()
    isRecording.value = false
    isVoiceChatting.value = false
    ElMessage.info({ message: '已关闭语音通话模式', plain: true })
  }
}

const handleAvatarReconnect = async () => {
  disconnectAvatar()
  await connectAvatar()
  nextTick(() => {
    const container = canvasRef.value?.getContainer()
    if (container) {
      setPlayerContainer(container)
    }
  })
}

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
    if (session && (!session.title || session.title === DEFAULT_SESSION_TITLE)) {
      // 使用用户消息的前20字符作为临时标题
      const tempTitle = text.length > 20 ? text.slice(0, 20) + '...' : text
      session.title = tempTitle
      // 调用后端API更新标题
      try {
        await updateSessionTitle(currentSessionId.value, tempTitle)
      } catch (err) {
        console.warn('更新会话标题失败:', err)
      }
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

  if (chatMode.value === 'digital_human' && isAvatarConnected.value) {
    const aiMsg = messages.value.find(m => m.id === aiMsgId)
    if (aiMsg) {
      aiMsg.diagramGenerating = shouldGenerateDiagram
    }
    sendAvatarText({
      text: text || '请分析附件',
      need_diagram: shouldGenerateDiagram,
      image_urls: imageUrls.length > 0 ? imageUrls : undefined,
      file_urls: fileUrls.length > 0 ? fileUrls : undefined,
    })
    return
  }

  abortController = streamChat(
      {
        message: text || '请分析附件',
        session_id: currentSessionId.value,
        image_urls: imageUrls.length > 0 ? imageUrls : undefined,
        file_urls: fileUrls.length > 0 ? fileUrls : undefined,
        need_diagram: shouldGenerateDiagram,
        generate_video: generateVideo.value,
        enable_search: enableWebSearch.value,
      },
      (chunk) => {
        enqueueStreamChunk(aiMsgId, chunk)
      },
      () => {
        flushPendingStreamText(true)
        const finishedSessionId = currentSessionId.value
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.diagramGenerating = false
        }
        isAIThinking.value = false
        streamingMsgId.value = null
        scheduleProfilePoll()
        abortController = null
        if (finishedSessionId) {
          void refreshSessionTitleWithRetry(finishedSessionId)
        }
      },
      (err) => {
        flushPendingStreamText(true)
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

watch(chatMode, async (newMode) => {
  if (newMode === 'digital_human') {
    sessionSidebarCollapsed.value = true
    await connectAvatar()
    nextTick(() => {
      const container = canvasRef.value?.getContainer()
      if (container) {
        setPlayerContainer(container)
      }
    })
  } else if (newMode === 'standard') {
    sessionSidebarCollapsed.value = false
    disconnectAvatar()
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
  disconnectAvatar()
  flushPendingStreamText()
  abortController?.abort()
  profilePollTimers.forEach(t => clearTimeout(t))
  if (dimTimer) clearTimeout(dimTimer)
  document.removeEventListener('mousedown', handleGlobalClick)
  document.removeEventListener('touchstart', handleGlobalClick)
})
</script>

<style>
/* 覆盖 ElPopover 的默认内边距 */
.el-popover.custom-plus-popover {
  padding: 0 !important;
  border-radius: 16px !important;
  border: none !important;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08) !important;
}
</style>

<style scoped>
@import url('https://gs.jurieo.com/gemini/fonts-googleapis/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600&display=swap');

.tutor-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden; /* 防止最外层溢出 */
  background-color: #FFFFFF;
  font-family: 'Inter', system-ui, sans-serif;
  color: #0F172A;
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

.diagram-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
  margin: 0 auto;
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
  min-width: 0; /* 关键：防止 flex 子项超出 */
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
  min-width: 0; /* 关键：防止 flex 子项超出 */
  position: relative;
}

.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  box-sizing: border-box; /* 防止 padding 引发溢出 */
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

/* ================= 聊天气泡深度优化 ================= */
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
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.ai-av {
  background: #0F172A;
  color: #FFF;
}

.user-av {
  background: #E2E8F0;
  color: #475569;
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

/* AI 和 User 气泡基础样式：低饱和、干净 */
.bubble {
  padding: 12px 16px;
  font-size: 0.95rem;
  line-height: 1.6;
  word-break: break-word;
  max-width: 100%;
}

/* AI 气泡：白底带极细边框 */
.message-row.ai .bubble {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  border-top-left-radius: 4px;
  color: #0F172A;
}

/* 用户气泡：极淡灰蓝色 */
.message-row.user .bubble {
  background: #F1F5F9;
  color: #0F172A;
  border: 1px solid transparent;
  border-radius: 12px;
  border-top-right-radius: 4px;
}

/* 覆盖用户气泡内的 Markdown 颜色 */
.message-row.user :deep(.markdown-body) {
  color: #0F172A !important;
}
.message-row.user :deep(.markdown-body a) {
  color: #2563EB !important;
}
.message-row.user :deep(.markdown-body code:not(pre code)) {
  background: #E2E8F0 !important;
  color: #E11D48 !important;
}

/* markdown 渲染排版及对齐优化 */
:deep(.markdown-body) {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem !important;
  background: transparent !important;
  color: inherit;
  overflow-wrap: anywhere;
  text-align: left; /* 确保严格左对齐 */
}

:deep(.markdown-body > :first-child) {
  margin-top: 0;
}

:deep(.markdown-body > :last-child) {
  margin-bottom: 0;
}

:deep(.markdown-body p) {
  margin: 0 0 0.8rem 0; /* 统一下边距，不用上边距 */
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  margin: 0.55rem 0 0.75rem;
  padding-left: 1.35rem;
}

:deep(.markdown-body li + li) {
  margin-top: 0.25rem;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4) {
  margin: 0.9rem 0 0.5rem;
  padding-bottom: 0;
  border-bottom: 0;
  line-height: 1.35;
}

:deep(.markdown-body h1) {
  font-size: 1.25rem;
}

:deep(.markdown-body h2) {
  font-size: 1.15rem;
}

:deep(.markdown-body h3) {
  font-size: 1.05rem;
}

/* 内联代码优化 */
:deep(.markdown-body code:not(pre code)) {
  padding: 0.12rem 0.32rem;
  border-radius: 5px;
  background: #F1F5F9;
  color: #E11D48;
  font-size: 0.88em;
}

:deep(.markdown-body blockquote) {
  margin: 0.7rem 0;
  padding: 0.15rem 0 0.15rem 0.85rem;
  color: #64748B;
  border-left: 3px solid #CBD5E1;
}

/* 代码块深色高级质感主题 (匹配截图风格) */
:deep(.code-block-wrapper) {
  position: relative;
  margin: 16px 0;
  border-radius: 12px;
  overflow: hidden;
  background-color: #1E2432; /* 深度暗蓝灰 */
  border: 1px solid #2D3748;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

:deep(.code-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background-color: #252D3D; /* 略浅一点的暗蓝灰，制造层次 */
  border-bottom: 1px solid #2D3748;
}

:deep(.code-lang) {
  color: #E2E8F0;
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', monospace;
  text-transform: uppercase;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.08); /* 胶囊背景 */
  padding: 4px 14px;
  border-radius: 20px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.5px;
}

:deep(.code-lang::before) {
  content: '⟨/⟩';
  color: #60A5FA;
  font-size: 0.85rem;
  font-weight: 800;
  letter-spacing: -1px;
}

:deep(.copy-code-btn) {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #CBD5E1;
  border-radius: 20px;
  padding: 4px 14px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

:deep(.copy-code-btn::before) {
  content: '';
  display: inline-block;
  width: 12px;
  height: 12px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23CBD5E1'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z'/%3E%3C/svg%3E");
  background-size: cover;
}

:deep(.copy-code-btn:hover) {
  background: rgba(255, 255, 255, 0.1);
  color: #FFFFFF;
  border-color: rgba(255, 255, 255, 0.3);
}

:deep(.copy-code-btn.copied) {
  background: #10B981;
  color: white;
  border-color: #10B981;
}
:deep(.copy-code-btn.copied::before) {
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23FFFFFF'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M5 13l4 4L19 7'/%3E%3C/svg%3E");
}

:deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  background: #1E2432 !important;
  border: 0;
  border-radius: 0;
}

:deep(.code-block-wrapper code) {
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre;
  color: #E2E8F0;
}


/* 附件链接优化 */
.msg-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.attachment-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #334155;
  text-decoration: none;
  transition: all 0.2s;
}

.attachment-link:hover {
  border-color: #CBD5E1;
  background: #F8FAFC;
}

/* ----------------------------------
   现代化的思考动画 (Typing Dots)
----------------------------------- */
.thinking-bubble {
  background: #FFFFFF !important;
  border: 1px solid #E2E8F0 !important;
  padding: 12px 16px !important;
  border-radius: 12px !important;
  border-top-left-radius: 4px !important;
  display: flex;
  align-items: center;
  box-shadow: none !important;
}

.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 20px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  background-color: #94A3B8; /* 柔和灰色 */
  border-radius: 50%;
  animation: typingBounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }
.typing-dots span:nth-child(3) { animation-delay: 0s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; background-color: #64748B; }
}

/* ================= 针对输入框的优化 ================= */
.input-panel {
  padding: 0 20px 20px 20px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: transparent;
  width: 100%;
  box-sizing: border-box;
}

.attachments-preview {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  width: 100%;
  max-width: 800px;
  flex-wrap: wrap;
  justify-content: flex-start;
  box-sizing: border-box;
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
  width: 100%;
  max-width: 800px;
  background: #F8FAFC; /* 扁平化浅灰底色 */
  border: 1px solid #E2E8F0;
  border-radius: 16px; /* 扁平化圆角 */
  padding: 12px 20px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 8px 12px;
  transition: all 0.3s ease;
  box-sizing: border-box;
  box-shadow: none; /* 移除发光效果 */
}

.input-wrapper:focus-within {
  background: #FFFFFF;
  border-color: #CBD5E1;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02); /* 极其克制的焦点阴影 */
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
  border-radius: 16px;
  padding: 16px 20px;
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
  color: #64748B;
  width: 28px;
  height: 28px;
  border-radius: 8px; /* 弱化圆角 */
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  padding: 0;
  transition: background 0.2s, color 0.2s;
}

.standard-plus-btn:hover {
  background: #E2E8F0;
  color: #334155;
}

.media-gen-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
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
  color: #64748B;
}

.media-gen-btn.btn-web:hover {
  background: #E2E8F0;
  color: #334155;
}

.media-gen-btn.btn-web.active {
  color: #0F172A;
  background: #E2E8F0;
}

.active-media-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px 4px 4px;
  color: #334155; /* 取消高饱和颜色 */
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  user-select: none;
  margin-left: 4px;
}

.active-media-chip:hover {
  background: #E2E8F0;
}

.active-media-chip .chip-icon-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: transparent;
}

.active-media-chip .icon-default {
  display: inline-flex;
  font-size: 1.1rem;
}

.active-media-chip .icon-hover {
  display: none;
  font-size: 1.05rem;
  color: #EF4444;
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
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: #64748B;
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
  color: #334155;
}

.voice-btn.is-recording {
  background: #EF4444;
  color: #FFFFFF;
}

.direct-voice-chat-btn {
  background: #0F172A;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  flex-shrink: 0;
}

.direct-voice-chat-btn:hover {
  background: #334155;
}

.voice-bars-icon {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 16px;
}

.voice-bars-icon .bar {
  width: 2px;
  background-color: #ffffff;
  border-radius: 1px;
  transition: height 0.2s ease;
}

.voice-bars-icon .bar:nth-child(1) { height: 8px; }
.voice-bars-icon .bar:nth-child(2) { height: 14px; }
.voice-bars-icon .bar:nth-child(3) { height: 10px; }
.voice-bars-icon .bar:nth-child(4) { height: 6px; }

.direct-voice-chat-btn.is-active {
  background: #0F172A;
}

.direct-voice-chat-btn.is-active .bar {
  animation: bar-dance 0.8s infinite ease-in-out alternate;
}

.direct-voice-chat-btn.is-active .bar:nth-child(1) { animation-delay: 0.0s; }
.direct-voice-chat-btn.is-active .bar:nth-child(2) { animation-delay: 0.2s; }
.direct-voice-chat-btn.is-active .bar:nth-child(3) { animation-delay: 0.1s; }
.direct-voice-chat-btn.is-active .bar:nth-child(4) { animation-delay: 0.3s; }

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
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
  background: #0F172A;
  color: #FFFFFF;
  cursor: pointer;
}

.send-btn.can-send:hover {
  background: #334155;
}

@keyframes bar-dance {
  from { transform: scaleY(0.7); }
  to { transform: scaleY(1.5); }
}

.input-footer {
  text-align: center;
  font-size: 0.7rem;
  color: #94A3B8;
  margin-top: 8px;
}

.profile-sidebar {
  width: 340px;
  padding: 1.5rem;
  background: #F8FAFC;
  border-left: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  flex-shrink: 0;
  box-sizing: border-box;
}

.sidebar-header {
  margin-bottom: 4px;
}

.header-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title-row h3 {
  margin: 0;
  font-size: 1.15rem;
  color: #0F172A;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.sync-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  color: #64748B;
  background: #FFFFFF;
  padding: 4px 10px;
  border-radius: 99px;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  border: 1px solid #E2E8F0;
}

.sync-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10B981;
}

.is-syncing .dot {
  animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* Insight Cards */
.profile-cards-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.insight-card {
  background: #FFFFFF;
  border-radius: 14px;
  border: 1px solid #E2E8F0;
  padding: 14px;
  transition: all 0.2s ease;
}

.insight-card:hover {
  border-color: #CBD5E1;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  transform: translateY(-1px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.card-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #F1F5F9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.card-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #334155;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.content-line {
  font-size: 0.825rem;
  color: #475569;
  line-height: 1.5;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.dot-marker {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #94A3B8;
  margin-top: 7px;
  flex-shrink: 0;
}

.plain-text {
  margin: 0;
}

/* Special Cards Styling */
.special-card {
  background: linear-gradient(to bottom right, #FFFFFF, #F8FAFC);
  border-left: 3px solid #334155; /* 弱化高亮颜色 */
}

.special-card.recent-changes-card {
  border-left-color: #94A3B8;
}

/* Empty State */
.profile-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid #E2E8F0;
  box-shadow: inset 0 0 20px rgba(148, 163, 184, 0.05);
  margin-top: 8px;
}

.empty-visual-container {
  position: relative;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px solid #CBD5E1;
  border-radius: 50%;
  opacity: 0;
  animation: pulse-out 3s infinite cubic-bezier(0.215, 0.61, 0.355, 1);
}

.pulse-ring.delay-1 { animation-delay: 1s; }
.pulse-ring.delay-2 { animation-delay: 2s; }

@keyframes pulse-out {
  0% { transform: scale(0.5); opacity: 0; }
  50% { opacity: 0.3; }
  100% { transform: scale(1.5); opacity: 0; }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.empty-visual {
  width: 60px;
  height: 60px;
  background: #F8FAFC;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2rem;
  color: #64748B;
  z-index: 2;
  animation: float 4s ease-in-out infinite;
}

.empty-text-wrap h4 {
  margin: 0 0 8px 0;
  font-size: 1.05rem;
  color: #1E293B;
  font-weight: 700;
}

.empty-text-wrap p {
  margin: 0;
  font-size: 0.85rem;
  color: #64748B;
  line-height: 1.6;
}

.empty-hints {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #F8FAFC;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.75rem;
  color: #475569;
  font-weight: 600;
  border: 1px solid #F1F5F9;
}

.hint-item .el-icon {
  font-size: 0.9rem;
  color: #64748B;
}

.long-term-memory-section {
  margin-top: auto;
  padding: 16px;
  background: #FFFFFF;
  border-radius: 16px;
  border: 1px solid #E2E8F0;
}

.memory-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.memory-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.memory-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0F172A;
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
  font-size: 0.75rem;
  color: #64748B;
  font-weight: 500;
}

.memory-desc {
  margin: 0;
  font-size: 0.75rem;
  color: #64748B;
  line-height: 1.6;
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
  background: #0F172A; /* 与整体风格统一 */
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.fab-button:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.3);
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
  background: #F1F5F9;
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
  background: #E2E8F0;
  color: #0F172A;
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
  color: #0F172A;
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
  color: #0F172A;
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

/* 弹出菜单项样式 */
.action-menu {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
  background: #ffffff;
  border-radius: 16px;
}

.action-item {
  display: flex;
  align-items: center;
  padding: 0 16px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  border-radius: 8px;
}

.action-item:hover {
  background-color: #f9fafb;
}

.item-icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  margin-right: 14px;
  margin-top: 8px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.bg-blue { background-color: #F1F5F9; color: #475569; }
.bg-purple { background-color: #F1F5F9; color: #475569; }
.bg-teal { background-color: #F1F5F9; color: #475569; }
.bg-active { background-color: #E2E8F0; color: #0F172A; }

.item-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid #f3f4f6;
}

.action-item:last-child .item-content {
  border-bottom: none;
}

.item-text {
  font-size: 14px;
  color: #1f2937;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.item-arrow {
  color: #9ca3af;
  font-size: 14px;
}
</style>
