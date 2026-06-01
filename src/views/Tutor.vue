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
              :aria-label="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
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

          <div class="digital-human-status-overlay" :class="{ active: isAIThinking || isAvatarSpeaking || isVadListening || isAsrProcessing }">
            <div class="speech-wave" v-if="isAIThinking || isAvatarSpeaking">
              <span></span><span></span><span></span><span></span><span></span>
            </div>
            <div class="asr-processing-dot" v-else-if="isAsrProcessing"></div>
            <div class="listening-dot" v-else-if="isVadListening"></div>
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
                v-memo="[
                  msg.id === streamingMsgId ? streamDisplayText : msg.content,
                  msg.id === streamingMsgId ? isAIThinking : false,
                  msg.searchStage,
                  msg.teachingDiagramGenerating,
                  msg.teachingDiagram,
                  msg.attachments
                ]"
                :class="['message-row', msg.role]"
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

                <div
                    v-if="msg.role === 'user' || getDisplayContent(msg) || (!msg.teachingDiagramGenerating && (msg.searchStage || !msg.teachingDiagram))"
                    :class="['bubble', 'markdown-body', { 'digital-human-bubble': chatMode === 'digital_human' && msg.role === 'ai' }]"
                >
                  <template v-if="msg.role === 'user'">
                    <div class="user-plain-text">{{ getDisplayContent(msg) }}</div>
                  </template>
                  <template v-else>
                    <div v-if="msg.searchStage && !getDisplayContent(msg)" class="search-status-indicator">
                      <span class="diagram-spinner"></span>
                      <span class="search-status-text">{{ msg.searchMessage }}</span>
                    </div>
                    <div v-else-if="isStreamingMessage(msg) && !getDisplayContent(msg) && !msg.teachingDiagramGenerating" class="thinking-loader">
                      <span class="dot"></span>
                      <span class="dot"></span>
                      <span class="dot"></span>
                    </div>
                    <TutorMessageContent
                        v-else-if="getDisplayContent(msg)"
                        :content="getDisplayContent(msg)"
                        :is-streaming="isStreamingMessage(msg)"
                    />
                  </template>
                </div>

                <div v-if="msg.attachments && msg.attachments.length > 0" class="msg-attachments">
                  <a v-for="att in msg.attachments" :key="att.url" :href="att.url" target="_blank" class="attachment-link">
                    <template v-if="att.type === 'image'">
                      <el-image :src="att.url" :alt="att.name || '图片附件'" fit="cover" class="attachment-img-preview" lazy />
                    </template>
                    <template v-else>
                      <div class="file-icon-box" :style="{ backgroundColor: getDocumentIconColor(getDocumentType(att.name)) }">
                        <el-icon aria-hidden="true"><Document /></el-icon>
                      </div>
                      <span class="attachment-name" :title="att.name">{{ att.name }}</span>
                    </template>
                  </a>
                </div>

                <div v-if="msg.teachingDiagramGenerating" class="teaching-diagram-generating">
                  <div class="kg-gen-header">
                    <span class="diagram-spinner"></span>
                    <span class="kg-gen-title">图解说明设计中</span>
                    <span class="kg-gen-subtitle">正在挑选最合适的讲解视角和关键步骤...</span>
                  </div>
                  <div class="diagram-draft-grid">
                    <span>关键结论</span>
                    <span>理解路径</span>
                    <span>快速自测</span>
                  </div>
                </div>

                <div v-if="msg.teachingDiagram" class="msg-teaching-diagram" @click="previewTeachingDiagram(msg.teachingDiagram)">
                  <TeachingDiagramView :diagram="msg.teachingDiagram" compact />
                </div>

                <div v-if="msg.role === 'ai' && msg.knowledgeSources && msg.knowledgeSources.length > 0" class="knowledge-sources">
                  <div class="knowledge-sources-title">回答来源</div>
                  <div
                    v-for="item in msg.knowledgeSources"
                    :key="`${item.rank}-${item.source}-${item.chunk_index}`"
                    class="knowledge-source-item"
                  >
                    <span class="knowledge-source-rank">[{{ item.rank }}]</span>
                    <span class="knowledge-source-name">{{ item.file_name || item.source }}</span>
                    <span v-if="item.chunk_index !== undefined" class="knowledge-source-meta">片段 {{ item.chunk_index }}</span>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <div class="minimal-input-panel">
            <div v-if="pendingFiles.length > 0" class="minimal-attachments-preview">
              <div v-for="(f, idx) in pendingFiles" :key="idx" class="minimal-attachment-chip">
                <template v-if="f.fileType === 'image'">
                  <el-image :src="f.localUrl || f.url" :alt="f.name || '图片预览'" fit="cover" class="attachment-img-preview" />
                </template>
                <template v-else>
                  <div class="file-icon-box" :style="{ backgroundColor: getDocumentIconColor(getDocumentType(f.name)) }">
                    <el-icon aria-hidden="true"><Document /></el-icon>
                  </div>
                </template>
                <span class="attachment-name" :title="f.name">{{ f.name }}</span>
                <button class="remove-attachment-btn" @click="removeAttachment(idx)" aria-label="移除附件"><el-icon aria-hidden="true"><Close /></el-icon></button>
              </div>
            </div>

            <div class="minimal-input-wrapper" :class="{ 'is-expanded': isExpandedInput }">
              <textarea
                  ref="textareaRef"
                  v-model="userInput"
                  placeholder="向 AI 导师提问（Enter 发送，Shift + Enter 换行）"
                  @keydown.enter="handleEnter"
                  @input="autoResize"
              ></textarea>

              <div class="minimal-action-bar">
                <div class="action-left">
                  <el-tooltip content="上传附件" placement="top" :show-after="500">
                    <button class="minimal-icon-btn" :disabled="uploadingFile" @click="triggerFileUpload" aria-label="上传附件">
                      <el-icon aria-hidden="true"><Paperclip /></el-icon>
                    </button>
                  </el-tooltip>

                  <el-tooltip content="联网搜索" placement="top" :show-after="500">
                    <button class="minimal-icon-btn" :class="{ 'is-active-blue': enableWebSearch }" @click="enableWebSearch = !enableWebSearch" :aria-label="enableWebSearch ? '关闭联网搜索' : '开启联网搜索'">
                      <el-icon aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <ellipse cx="12" cy="12" rx="5" ry="10"></ellipse>
                          <line x1="12" y1="2" x2="12" y2="22"></line>
                          <line x1="2" y1="12" x2="22" y2="12"></line>
                        </svg>
                      </el-icon>
                    </button>
                  </el-tooltip>

                  <el-tooltip content="知识库检索" placement="top" :show-after="500">
                    <button class="minimal-icon-btn" :class="{ 'is-active-amber': enableKnowledgeBase }" @click="enableKnowledgeBase = !enableKnowledgeBase" :aria-label="enableKnowledgeBase ? '关闭知识库检索' : '开启知识库检索'">
                      <el-icon aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                        </svg>
                      </el-icon>
                    </button>
                  </el-tooltip>

                  <el-tooltip content="生成图解说明" placement="top" :show-after="500">
                    <button class="minimal-icon-btn" :class="{ 'is-active-teal': needTeachingDiagram }" @click="handleTeachingDiagramToggle" :aria-label="needTeachingDiagram ? '关闭图解说明' : '生成图解说明'">
                      <el-icon aria-hidden="true"><DataLine /></el-icon>
                    </button>
                  </el-tooltip>

                  <el-tooltip content="生成视频" placement="top" :show-after="500">
                    <button class="minimal-icon-btn" :class="{ 'is-active-teal': generateVideo }" @click="handleVideoToggle" :aria-label="generateVideo ? '关闭视频生成' : '生成视频'">
                      <el-icon aria-hidden="true"><VideoCamera /></el-icon>
                    </button>
                  </el-tooltip>
                </div>

                <div class="action-right">
                  <div v-if="chatMode === 'digital_human'" class="minimal-speech-rate">
                    <span class="rate-label">语速</span>
                    <el-slider
                      v-model="avatarSpeechRate"
                      :min="0.8"
                      :max="1.5"
                      :step="0.1"
                      :disabled="isAvatarSpeaking"
                      :show-tooltip="false"
                      @change="handleAvatarSpeechRateChange"
                      class="rate-slider"
                    />
                    <span class="rate-value">{{ avatarSpeechRate.toFixed(1) }}x</span>
                  </div>

                  <el-tooltip
                      v-if="chatMode === 'digital_human'"
                      :content="isVoiceChatting ? '结束语音对话' : '开启语音通话'"
                      placement="top"
                      :show-after="500"
                  >
                    <button
                        class="minimal-icon-btn voice-chat-btn"
                        :class="{ 'is-active': isVoiceChatting }"
                        @click="handleVoiceChatToggle"
                        :aria-label="isVoiceChatting ? '结束语音对话' : '开启语音通话'"
                    >
                      <div class="voice-bars-icon" aria-hidden="true">
                        <span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span>
                      </div>
                    </button>
                  </el-tooltip>

                  <el-tooltip :content="isRecording ? '结束录音' : '语音提问'" placement="top" :show-after="500">
                    <button class="minimal-icon-btn voice" :class="{ 'is-recording': isRecording }" @click="handleVoiceToggle" :aria-label="isRecording ? '结束录音' : '语音提问'">
                      <el-icon aria-hidden="true"><Microphone /></el-icon>
                    </button>
                  </el-tooltip>

                  <button class="minimal-send-btn" :class="{ 'can-send': userInput.trim() || pendingFiles.length > 0 }" @click="handleSend" aria-label="发送消息">
                    <el-icon aria-hidden="true"><Top /></el-icon>
                  </button>
                </div>
              </div>
            </div>
            <div class="input-footer">内容由 AI 生成，仅供参考。</div>
          </div>
        </div>

        <input ref="fileInput" type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp" style="display:none" @change="onCombinedFileSelected" />
      </section>
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

    <!-- 教学图解预览 -->
    <el-dialog
        v-model="teachingDiagramPreviewVisible"
        :title="teachingDiagramPreviewData?.title || '图解说明'"
        width="min(1080px, 92vw)"
        top="5vh"
        destroy-on-close
        class="diagram-preview-dialog"
    >
      <div class="diagram-preview-body" v-if="teachingDiagramPreviewData">
        <div class="preview-content">
          <TeachingDiagramView :diagram="teachingDiagramPreviewData" />
        </div>
        <div class="preview-footer">
          <el-button type="primary" plain @click="copyTeachingDiagramJson(teachingDiagramPreviewData)">复制图解 JSON</el-button>
          <el-button @click="teachingDiagramPreviewVisible = false">关闭</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import {
  ChatLineRound, Avatar, Cpu, Service, UserFilled,
  Microphone, Document, ChatDotRound, ChatLineSquare,
  Delete, Close, Top, Paperclip,
  EditPen, Search, Timer, VideoCamera, DataLine,
  CircleCheckFilled
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getErrorMessage } from '@/utils/http'
import TutorMessageContent from '@/components/TutorMessageContent.vue'
import TeachingDiagramView from '@/components/chat/TeachingDiagramView.vue'

import { triggerGlobalProfileRefresh } from '@/composables/useGlobalProfile'
import {
  streamChat,
  uploadFile,
  getSessions,
  createSession,
  deleteSession,
  updateSessionTitle,
  getChatHistory,
  type ChatSession,
  type KnowledgeSource,
  type StreamChatHistoryItem,
  type TeachingDiagram,
} from '@/api/chat'
import { getMe } from '@/api/auth'
import { useDigitalHuman } from '@/views/digital-human/useDigitalHuman'
import DigitalHumanCanvas from '@/views/digital-human/DigitalHumanCanvas.vue'

defineOptions({ name: 'Tutor' })

// 类型定义
interface PendingFile {
  file?: File;
  url?: string;
  localUrl?: string;
  fileType: string;
  name: string
}
interface Attachment {
  url: string;
  type: string;
  name: string
}
interface ChatMsg {
  id: number
  role: 'user' | 'ai'
  content: string
  time: string
  attachments?: Attachment[] | null
  teachingDiagram?: TeachingDiagram | null
  teachingDiagramGenerating?: boolean
  searchStage?: string
  searchMessage?: string
  knowledgeSources?: KnowledgeSource[]
}

const normalizeTeachingDiagram = (diagram: TeachingDiagram | null | undefined): TeachingDiagram | null => {
  if (!diagram || typeof diagram !== 'object') return null
  if (!['contrast', 'journey', 'anatomy', 'simulation'].includes(diagram.type)) return null
  if (!diagram.title || !diagram.payload || typeof diagram.payload !== 'object') return null
  return diagram
}

const getDocumentType = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['xls', 'xlsx'].includes(ext)) return 'excel'
  if (['pdf'].includes(ext)) return 'pdf'
  return 'other'
}

const getDocumentIconColor = (type: string) => {
  if (type === 'word') return '#2563EB'
  if (type === 'excel') return '#16A34A'
  if (type === 'pdf') return '#DC2626'
  return '#64748B'
}

const buildStreamHistory = (): StreamChatHistoryItem[] => {
  return messages.value
    .filter(msg => msg.role === 'user' || msg.role === 'ai')
    .filter(msg => msg.content.trim())
    .map(msg => ({
      role: msg.role === 'ai' ? 'assistant' : 'user',
      content: msg.content,
      attachments: msg.attachments || null,
      teaching_diagram: msg.teachingDiagram || null,
    }))
}

const DEFAULT_SESSION_TITLE = '新对话'
const SESSION_TITLE_REFRESH_DELAYS = [300, 800, 1500, 3000]

// 状态
const chatMode = ref('standard')
const userInput = ref('')
const isAIThinking = ref(false)
const digitalHumanBackendStatus = ref('')
const chatScroll = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isExpandedInput = ref(false)

const enableWebSearch = ref(false)
const enableKnowledgeBase = ref(true)
const needTeachingDiagram = ref(false)
const generateVideo = ref(false)
const hasToggledMedia = ref(false)

const isRecording = ref(false)
const isVoiceChatting = ref(false)
const lastAsrText = ref('')
const hasSpeechDetected = ref(false)
const lastAsrCommittedText = ref('')
let lastAsrCommitAt = 0

const canvasRef = ref<InstanceType<typeof DigitalHumanCanvas> | null>(null)
const {
  isConnected: isAvatarConnected,
  isAvatarReady,
  isSpeaking: isAvatarSpeaking,
  isListening: isVadListening,
  audioEnabled: avatarAudioEnabled,
  speechRate: avatarSpeechRate,
  idleCountdown: avatarIdleCountdown,
  connect: connectAvatar,
  disconnect: disconnectAvatar,
  sendText: sendAvatarText,
  setSpeechRate: setAvatarSpeechRate,
  setNeedDiagram: setAvatarNeedDiagram,
  startVad,
  stopVad,
  enableAudio: enableAvatarAudio,
  setPlayerContainer,
} = useDigitalHuman({
  onStatus: (status) => {
    digitalHumanBackendStatus.value = status.message || ''
  },
  onAssistantChunk: (chunk) => {
    digitalHumanBackendStatus.value = ''
    clearAsrProcessing()
    startAvatarThinkingTimeout()
    if (isVoiceChatting.value && isVadListening.value) {
      stopVad()
      isRecording.value = false
    }
    if (streamingMsgId.value === null) {
      const aiMsgId = Date.now() + 1
      messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
      streamingMsgId.value = aiMsgId
      streamingMsgRef.value = messages.value[messages.value.length - 1] || null
      isAIThinking.value = true
    }
    if (streamingMsgId.value !== null) {
      enqueueStreamChunk(streamingMsgId.value, chunk)
    }
  },
  onDiagram: (diagram) => {
    if (!diagram) return
    const aiMsg = (
      (streamingMsgId.value !== null
        ? messages.value.find(m => m.id === streamingMsgId.value && m.role === 'ai')
        : null)
      || [...messages.value].reverse().find(m => m.role === 'ai')
    )
    if (!aiMsg) return
    aiMsg.teachingDiagram = normalizeTeachingDiagram(diagram as TeachingDiagram)
    aiMsg.teachingDiagramGenerating = false
    scrollToBottom()
  },
  onAssistantComplete: () => {
    digitalHumanBackendStatus.value = ''
    clearAvatarThinkingTimeout()
    clearAsrProcessing()
    isStreamDone = true
    flushPendingStreamText(true)
    if (streamingMsgId.value !== null) {
      commitStreamTextToMessage(streamingMsgId.value)
    }
    const lastAiMsg = [...messages.value].reverse().find(m => m.role === 'ai')
    if (lastAiMsg && lastAiMsg.teachingDiagramGenerating && !lastAiMsg.teachingDiagram) {
      lastAiMsg.teachingDiagramGenerating = false
    }
    isAIThinking.value = false
    streamingMsgId.value = null
    streamingMsgRef.value = null
    triggerGlobalProfileRefresh()
    if (isVoiceChatting.value && chatMode.value === 'digital_human' && isAvatarConnected.value) {
      window.setTimeout(async () => {
        if (!isVoiceChatting.value || chatMode.value !== 'digital_human' || !isAvatarConnected.value) return
        await startVad(needTeachingDiagram.value, getAvatarCapabilities())
        isRecording.value = isVadListening.value
      }, 350)
    }
  },
  onAsrResult: (text) => {
    if (chatMode.value === 'digital_human' && isAvatarConnected.value) {
      setAvatarNeedDiagram(needTeachingDiagram.value)
    }
    const normalized = text.replace(/\s+/g, ' ').trim()
    lastAsrText.value = normalized
    if (normalized) {
      startAsrProcessing(6000)
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
        streamingMsgRef.value = messages.value[messages.value.length - 1] || null
      }
      if (needTeachingDiagram.value) {
        const aiMsg = streamingMsgId.value !== null
          ? messages.value.find(m => m.id === streamingMsgId.value && m.role === 'ai')
          : null
        if (aiMsg) aiMsg.teachingDiagramGenerating = true
      }
      isAIThinking.value = true
      scrollToBottom()
    }
  },
  onVadStateChange: (listening) => {
    isRecording.value = listening
    if (!listening) {
      hasSpeechDetected.value = false
      if (chatMode.value === 'digital_human' && isVoiceChatting.value) {
        startAsrProcessing(8000)
      } else {
        lastAsrText.value = ''
        clearAsrProcessing()
      }
    }
  },
  onSpeechDetectedChange: (detected) => {
    hasSpeechDetected.value = detected
  },
  onError: (msg) => {
    digitalHumanBackendStatus.value = ''
    clearAvatarThinkingTimeout()
    clearAsrProcessing()
    stopTeachingDiagramGeneratingForCurrentAi()
    if (streamingMsgId.value !== null) {
      flushPendingStreamText(true)
      commitStreamTextToMessage(streamingMsgId.value)
    }
    if (isAIThinking.value) {
      isAIThinking.value = false
      streamingMsgId.value = null
      streamingMsgRef.value = null
    }
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
const digitalHumanSessionId = ref<string | undefined>(undefined)
const sessionSidebarCollapsed = ref(false)
const currentUserId = ref<string | number | null>(null)
const searchPopoverVisible = ref(false)
const searchKeyword = ref('')

const messages = ref<ChatMsg[]>([])
const streamingMsgId = ref<number | null>(null)
const streamingMsgRef = ref<ChatMsg | null>(null)
let abortController: AbortController | null = null
let avatarThinkingTimeout: ReturnType<typeof setTimeout> | null = null
const isAsrProcessing = ref(false)
let asrProcessingTimer: ReturnType<typeof setTimeout> | null = null

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

const clearAvatarThinkingTimeout = () => {
  if (avatarThinkingTimeout) {
    clearTimeout(avatarThinkingTimeout)
    avatarThinkingTimeout = null
  }
}

const stopTeachingDiagramGeneratingForCurrentAi = () => {
  const target = (
    (streamingMsgId.value !== null
      ? messages.value.find(m => m.id === streamingMsgId.value && m.role === 'ai')
      : null)
    || [...messages.value].reverse().find(m => m.role === 'ai')
  )
  if (target) {
    target.teachingDiagramGenerating = false
  }
}

const clearAsrProcessing = () => {
  isAsrProcessing.value = false
  if (asrProcessingTimer) {
    clearTimeout(asrProcessingTimer)
    asrProcessingTimer = null
  }
}

const startAsrProcessing = (timeoutMs = 6000) => {
  isAsrProcessing.value = true
  if (asrProcessingTimer) clearTimeout(asrProcessingTimer)
  asrProcessingTimer = setTimeout(() => {
    isAsrProcessing.value = false
    asrProcessingTimer = null
  }, timeoutMs)
}

const startAvatarThinkingTimeout = () => {
  clearAvatarThinkingTimeout()
  avatarThinkingTimeout = setTimeout(() => {
    if (chatMode.value !== 'digital_human') return
    if (!isAIThinking.value) return
    isAIThinking.value = false
    stopTeachingDiagramGeneratingForCurrentAi()
    streamingMsgId.value = null
    ElMessage.warning({ message: '数字人响应超时，请重试或重新连接', plain: true })
  }, 30000)
}

let scrollPending = false
let streamFlushHandle: ReturnType<typeof setTimeout> | null = null
const streamDisplayText = ref('')
const pendingRenderQueue: string[] = []
let pendingRenderQueueStart = 0
let pendingRenderOffset = 0
let pendingRenderChars = 0
let isStreamDone = false
const streamRenderedChunks: string[] = []
let lastAutoScrollAt = 0
let lastChunkArrivedAt = 0
const STREAM_FIRST_PAINT_UNITS = 1
const STREAM_DEFAULT_UNITS_PER_TICK = 1
const STREAM_FAST_UNITS_PER_TICK = 2
const STREAM_BURST_UNITS_PER_TICK = 3
const STREAM_DONE_UNITS_PER_TICK = 4
const STREAM_BACKLOG_FAST_THRESHOLD = 120
const STREAM_BACKLOG_BURST_THRESHOLD = 320
const STREAM_BASE_DELAY_MS = 14
const STREAM_MIN_DELAY_MS = 6
const STREAM_MAX_DELAY_MS = 44
const DIGITAL_HUMAN_STREAM_BASE_DELAY_MS = 40
const DIGITAL_HUMAN_STREAM_MIN_DELAY_MS = 22
const DIGITAL_HUMAN_STREAM_MAX_DELAY_MS = 90
const STREAM_SCROLL_INTERVAL_MS = 64
const STREAM_AUTO_SCROLL_BOTTOM_GAP_PX = 96

// 计算属性
const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return sessions.value.filter(s => {
    const title = s.title || '新建对话'
    return title.toLowerCase().includes(keyword)
  })
})

const isStreamingMessage = (msg: ChatMsg) => msg.id === streamingMsgId.value && isAIThinking.value
const getDisplayContent = (msg: ChatMsg) => {
  if (msg.id === streamingMsgId.value && streamDisplayText.value) {
    return streamDisplayText.value
  }
  return msg.content
}

const isDigitalHumanPacedStream = () => chatMode.value === 'digital_human'

const getDigitalHumanUnitsPerTick = (streamDone: boolean): number => {
  const rate = Math.max(0.8, Math.min(1.5, Number(avatarSpeechRate.value) || 1.0))
  if (streamDone) return rate >= 1.25 ? 3 : 2
  if (rate <= 0.95) return 1
  if (rate >= 1.2) return 2
  return 1
}

type VoiceAsrStage = 'idle' | 'no_voice' | 'heard_voice' | 'transcribing'
const voiceAsrStage = computed<VoiceAsrStage>(() => {
  if (isAIThinking.value || isAvatarSpeaking.value) return 'idle'
  if (isAsrProcessing.value) return 'transcribing'
  if (isVadListening.value) {
    return hasSpeechDetected.value ? 'heard_voice' : 'no_voice'
  }
  return 'idle'
})

const digitalHumanStatusText = computed(() => {
  if (isAIThinking.value && digitalHumanBackendStatus.value) return digitalHumanBackendStatus.value
  if (isAIThinking.value || isAvatarSpeaking.value) return '正在多模态解答中...'
  if (voiceAsrStage.value === 'no_voice') return '未识别到声音'
  if (voiceAsrStage.value === 'heard_voice') return '已识别到声音'
  if (voiceAsrStage.value === 'transcribing') return '正在转文字'
  return '倾听就绪'
})

const teachingDiagramPreviewVisible = ref(false)
const teachingDiagramPreviewData = ref<TeachingDiagram | null>(null)

const previewTeachingDiagram = (diagram: TeachingDiagram) => {
  teachingDiagramPreviewData.value = diagram
  teachingDiagramPreviewVisible.value = true
}

const copyTeachingDiagramJson = async (diagram: TeachingDiagram) => {
  if (diagram) {
    await copyToClipboard(JSON.stringify(diagram, null, 2))
    ElMessage.success({ message: '图解说明 JSON 已复制', plain: true })
  }
}

const handleEnter = (e: KeyboardEvent) => {
  if (e.isComposing) return
  if (e.shiftKey) return
  
  e.preventDefault()
  handleSend()
}

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

const isCjkCharacter = (char: string): boolean => {
  return /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/.test(char)
}

const isInsideOpenFence = (text: string): boolean => {
  const fences = text.match(/(^|\n)(`{3,}|~{3,})/g)
  return !!fences && fences.length % 2 === 1
}

const takeAsciiWordUnit = (text: string): number => {
  const word = text.match(/^[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*/)
  if (!word) return 1
  let take = word[0].length
  while (take < text.length && /\s/.test(text[take] || '')) {
    take += 1
  }
  return take
}

const takeNextStreamUnit = (text: string, inCodeBlock: boolean): number => {
  if (!text) return 0

  if (text.startsWith('\r\n')) return 2
  if (text.startsWith('\n')) return 1

  const listMarker = text.match(/^(?:[-*+]\s|\d+\.\s)/)
  if (listMarker) return listMarker[0].length

  const fenceMarker = text.match(/^(?:`{3,}|~{3,})/)
  if (fenceMarker) return fenceMarker[0].length

  const currentChar = text[0] || ''
  if (inCodeBlock) {
    if (/^[ \t]+/.test(text)) {
      return (text.match(/^[ \t]+/)?.[0].length) || 1
    }
    if (/[A-Za-z0-9_]/.test(currentChar)) {
      return Math.min(takeAsciiWordUnit(text), 3)
    }
    return 1
  }

  if (isCjkCharacter(currentChar)) return 1

  if (/[A-Za-z0-9_]/.test(currentChar)) {
    return takeAsciiWordUnit(text)
  }

  if (/\s/.test(currentChar)) {
    return 1
  }

  return 1
}

const getUnitsPerTick = (backlogChars: number, inCodeBlock: boolean, streamDone: boolean): number => {
  if (isDigitalHumanPacedStream()) {
    const pacedUnits = getDigitalHumanUnitsPerTick(streamDone)
    return inCodeBlock ? pacedUnits + 1 : pacedUnits
  }
  if (streamDone) {
    if (backlogChars >= STREAM_BACKLOG_BURST_THRESHOLD) return STREAM_DONE_UNITS_PER_TICK + 1
    return STREAM_DONE_UNITS_PER_TICK
  }
  if (backlogChars >= STREAM_BACKLOG_BURST_THRESHOLD) {
    return inCodeBlock ? STREAM_BURST_UNITS_PER_TICK + 1 : STREAM_BURST_UNITS_PER_TICK
  }
  if (backlogChars >= STREAM_BACKLOG_FAST_THRESHOLD) {
    return inCodeBlock ? STREAM_FAST_UNITS_PER_TICK + 1 : STREAM_FAST_UNITS_PER_TICK
  }
  return inCodeBlock ? STREAM_DEFAULT_UNITS_PER_TICK + 1 : STREAM_DEFAULT_UNITS_PER_TICK
}

const getNextStreamDelay = (
  emittedText: string,
  backlogChars: number,
  inCodeBlock: boolean,
  streamDone: boolean,
): number => {
  if (isDigitalHumanPacedStream()) {
    const rate = Math.max(0.8, Math.min(1.5, Number(avatarSpeechRate.value) || 1.0))
    let delay = DIGITAL_HUMAN_STREAM_BASE_DELAY_MS - Math.round((rate - 1.0) * 18)

    if (/[。！？.!?]\s*$/.test(emittedText)) {
      delay += 40
    } else if (/[,，；;：:]\s*$/.test(emittedText)) {
      delay += 18
    } else if (/\n\s*$/.test(emittedText)) {
      delay += 24
    } else if (/[A-Za-z0-9_]\s$/.test(emittedText)) {
      delay += 8
    }

    if (streamDone) {
      delay -= 10
    } else if (backlogChars >= 180) {
      delay -= 8
    } else if (backlogChars >= 80) {
      delay -= 4
    }

    return Math.max(
      DIGITAL_HUMAN_STREAM_MIN_DELAY_MS,
      Math.min(DIGITAL_HUMAN_STREAM_MAX_DELAY_MS, delay),
    )
  }

  let delay = inCodeBlock ? 8 : STREAM_BASE_DELAY_MS

  if (/[。！？.!?]\s*$/.test(emittedText)) {
    delay += 20
  } else if (/[,，；;：:]\s*$/.test(emittedText)) {
    delay += 10
  } else if (/\n\s*$/.test(emittedText)) {
    delay += 14
  } else if (/[A-Za-z0-9_]\s$/.test(emittedText)) {
    delay += 4
  }

  if (backlogChars >= STREAM_BACKLOG_BURST_THRESHOLD) {
    delay -= 6
  } else if (backlogChars >= STREAM_BACKLOG_FAST_THRESHOLD) {
    delay -= 3
  }

  if (streamDone) {
    delay -= 4
  }

  const idleMs = lastChunkArrivedAt ? Date.now() - lastChunkArrivedAt : 0
  if (!streamDone && idleMs > 800 && backlogChars < STREAM_BACKLOG_FAST_THRESHOLD) {
    delay += 6
  }

  return Math.max(STREAM_MIN_DELAY_MS, Math.min(STREAM_MAX_DELAY_MS, delay))
}

const flushPendingStreamText = (forceScroll = false, unitOverride?: number): number | undefined => {
  if (pendingRenderQueueStart >= pendingRenderQueue.length) return
  const aiMsg = streamingMsgRef.value
  if (aiMsg) {
    let unitsRemaining = typeof unitOverride === 'number'
      ? unitOverride
      : getUnitsPerTick(pendingRenderChars, isInsideOpenFence(streamDisplayText.value), isStreamDone)
    let out = ''
    let inCodeBlock = isInsideOpenFence(streamDisplayText.value)
    while (unitsRemaining > 0 && pendingRenderQueueStart < pendingRenderQueue.length) {
      const part = pendingRenderQueue[pendingRenderQueueStart] || ''
      const available = part.length - pendingRenderOffset
      if (available <= 0) {
        pendingRenderQueueStart += 1
        pendingRenderOffset = 0
        continue
      }
      const take = Math.min(available, Math.max(1, takeNextStreamUnit(part.slice(pendingRenderOffset), inCodeBlock)))
      out += part.slice(pendingRenderOffset, pendingRenderOffset + take)
      pendingRenderOffset += take
      pendingRenderChars -= take
      unitsRemaining -= 1
      inCodeBlock = isInsideOpenFence(streamDisplayText.value + out)
      if (pendingRenderOffset >= part.length) {
        pendingRenderQueueStart += 1
        pendingRenderOffset = 0
      }
    }
    if (!out) return
    streamRenderedChunks.push(out)
    streamDisplayText.value += out

    if (pendingRenderQueueStart >= pendingRenderQueue.length) {
      pendingRenderQueue.length = 0
      pendingRenderQueueStart = 0
      pendingRenderOffset = 0
      pendingRenderChars = 0
    }
    scrollToBottomThrottled(forceScroll)
    return getNextStreamDelay(out, pendingRenderChars, inCodeBlock, isStreamDone)
  }
  return STREAM_BASE_DELAY_MS
}

const scheduleStreamFlush = (forceScroll = false, delayMs = STREAM_BASE_DELAY_MS) => {
  if (streamFlushHandle != null) return
  streamFlushHandle = window.setTimeout(() => {
    streamFlushHandle = null
    const nextDelay = flushPendingStreamText(forceScroll)
    if (pendingRenderQueueStart >= pendingRenderQueue.length) {
      if (isStreamDone && streamingMsgId.value != null) {
        const doneId = streamingMsgId.value
        finishStream(doneId)
      }
      return
    }
    scheduleStreamFlush(false, nextDelay)
  }, delayMs)
}

const enqueueStreamChunk = (messageId: number, chunk: string) => {
  if (!chunk) return
  if (streamingMsgRef.value?.id !== messageId) return
  lastChunkArrivedAt = Date.now()
  pendingRenderQueue.push(chunk)
  pendingRenderChars += chunk.length
  const shouldPrimeFirstPaint =
    streamRenderedChunks.length === 0
    && !streamDisplayText.value
    && pendingRenderQueueStart === 0
    && pendingRenderOffset === 0
    && pendingRenderChars === chunk.length
  if (shouldPrimeFirstPaint) {
    flushPendingStreamText(true, STREAM_FIRST_PAINT_UNITS)
  }
  if (pendingRenderQueueStart >= pendingRenderQueue.length) {
    return
  }
  scheduleStreamFlush()
}

const drainPendingStreamText = () => {
  if (pendingRenderQueueStart >= pendingRenderQueue.length) {
    return
  }
  let out = ''
  while (pendingRenderQueueStart < pendingRenderQueue.length) {
    const part = pendingRenderQueue[pendingRenderQueueStart] || ''
    const available = part.length - pendingRenderOffset
    if (available <= 0) {
      pendingRenderQueueStart += 1
      pendingRenderOffset = 0
      continue
    }
    out += part.slice(pendingRenderOffset)
    pendingRenderChars -= available
    pendingRenderQueueStart += 1
    pendingRenderOffset = 0
  }
  if (out) {
    streamRenderedChunks.push(out)
    streamDisplayText.value += out
  }
  pendingRenderQueue.length = 0
  pendingRenderQueueStart = 0
  pendingRenderOffset = 0
  pendingRenderChars = 0
}

const finishStream = (messageId: number) => {
  commitStreamTextToMessage(messageId)
  isAIThinking.value = false
  streamingMsgId.value = null
  streamingMsgRef.value = null
  triggerGlobalProfileRefresh()
  abortController = null
}

const commitStreamTextToMessage = (messageId: number) => {
  const aiMsg = streamingMsgRef.value && streamingMsgRef.value.id === messageId
    ? streamingMsgRef.value
    : messages.value.find(m => m.id === messageId)
  if (!aiMsg) {
    pendingRenderQueue.length = 0
    pendingRenderQueueStart = 0
    pendingRenderOffset = 0
    pendingRenderChars = 0
    streamRenderedChunks.length = 0
    streamDisplayText.value = ''
    return
  }
  drainPendingStreamText()
  if (streamRenderedChunks.length > 0) {
    aiMsg.content += streamRenderedChunks.join('')
  } else if (streamDisplayText.value) {
    aiMsg.content += streamDisplayText.value
  }
  pendingRenderQueue.length = 0
  pendingRenderQueueStart = 0
  pendingRenderOffset = 0
  pendingRenderChars = 0
  isStreamDone = false
  lastChunkArrivedAt = 0
  streamRenderedChunks.length = 0
  streamDisplayText.value = ''
  streamingMsgRef.value = null
}

const stopStreamFlushLoop = () => {
  if (streamFlushHandle != null) {
    clearTimeout(streamFlushHandle)
    streamFlushHandle = null
  }
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
    const mapped = history.map((msg, i) => ({
      id: Date.now() + i,
      role: msg.role === 'assistant' ? 'ai' as const : msg.role as 'user' | 'ai',
      content: msg.content,
      time: msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
      attachments: msg.attachments || null,
      teachingDiagram: normalizeTeachingDiagram(msg.teaching_diagram),
    }))
    // 防止刷新后历史中相邻重复消息导致双排显示
    messages.value = mapped.filter((item, idx) => {
      if (idx === 0) return true
      const prev = mapped[idx - 1]
      return !(prev && prev.role === item.role && prev.content === item.content)
    })
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
  const localUrl = isImage ? URL.createObjectURL(file) : undefined
  pendingFiles.value.push({
    file,
    fileType,
    name: file.name,
    localUrl,
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

const getAvatarCapabilities = () => ({
  session_id: digitalHumanSessionId.value,
  history: buildStreamHistory().map(item => ({ role: item.role, content: item.content })),
  enable_search: enableWebSearch.value,
  generate_video: generateVideo.value,
})

const handleTeachingDiagramToggle = () => {
  hasToggledMedia.value = true
  if (needTeachingDiagram.value) {
    needTeachingDiagram.value = false
  } else {
    needTeachingDiagram.value = true
    generateVideo.value = false
  }
}

const handleVideoToggle = () => {
  hasToggledMedia.value = true
  if (generateVideo.value) {
    generateVideo.value = false
  } else {
    generateVideo.value = true
    needTeachingDiagram.value = false
  }
}

const ensureCurrentSession = async (mode: 'standard' | 'digital_human' = 'standard') => {
  const sessionRef = mode === 'digital_human' ? digitalHumanSessionId : currentSessionId
  if (sessionRef.value) return true
  try {
    const res = await createSession()
    const session = res.data.data
    sessionRef.value = session.id
    sessions.value.unshift({ id: session.id, title: session.title, updated_at: new Date().toISOString() })
    return true
  } catch {
    ElMessage.error({ message: '创建会话失败，请重试', plain: true })
    return false
  }
}

const handleVoiceToggle = async () => {
  if (chatMode.value === 'digital_human') {
    if (isVadListening.value) {
      stopVad()
      isRecording.value = false
      hasSpeechDetected.value = true
      startAsrProcessing(8000)
    } else {
      if (!await ensureCurrentSession('digital_human')) return
      await startVad(needTeachingDiagram.value, getAvatarCapabilities())
      isRecording.value = isVadListening.value
      clearAsrProcessing()
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
    if (!await ensureCurrentSession('digital_human')) return
    isVoiceChatting.value = true
    chatMode.value = 'digital_human'
    await connectAvatar()
    nextTick(() => {
      const container = canvasRef.value?.getContainer()
      if (container) {
        setPlayerContainer(container)
      }
    })
    await startVad(needTeachingDiagram.value, getAvatarCapabilities())
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
  setAvatarSpeechRate(avatarSpeechRate.value)
  nextTick(() => {
    const container = canvasRef.value?.getContainer()
    if (container) {
      setPlayerContainer(container)
    }
  })
}

const handleAvatarSpeechRateChange = (val: number) => {
  setAvatarSpeechRate(val)
}

const handleSend = async () => {
  const text = userInput.value.trim()
  const hasFiles = pendingFiles.value.length > 0
  if ((!text && !hasFiles) || isAIThinking.value) return
  const shouldGenerateTeachingDiagram = needTeachingDiagram.value
  const sessionMode = chatMode.value === 'digital_human' ? 'digital_human' : 'standard'

  if (chatMode.value === 'digital_human' && !isAvatarConnected.value) {
    ElMessage.warning({ message: '数字人连接已断开，请先点击“重新连接”后再发送', plain: true })
    return
  }

  if (!await ensureCurrentSession(sessionMode)) return
  const activeSessionId = sessionMode === 'digital_human' ? digitalHumanSessionId.value : currentSessionId.value

  if (activeSessionId && text) {
    const session = sessions.value.find(s => s.id === activeSessionId)
    if (session && (!session.title || session.title === DEFAULT_SESSION_TITLE)) {
      // 使用用户消息的前20字符作为临时标题
      const tempTitle = text.length > 20 ? text.slice(0, 20) + '...' : text
      session.title = tempTitle
      // 调用后端API更新标题
      try {
        await updateSessionTitle(activeSessionId, tempTitle)
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
  digitalHumanBackendStatus.value = ''
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
          const uploadSessionId = sessionMode === 'digital_human' ? digitalHumanSessionId.value : currentSessionId.value
          if (!pending.file || !uploadSessionId) {
            throw new Error('会话不存在，无法上传附件')
          }
          const res = await uploadFile(pending.file, uploadSessionId)
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
    pendingFiles.value.forEach(f => {
      if (f.localUrl) URL.revokeObjectURL(f.localUrl)
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

  const attachmentUrls = uploadedAttachments.map(f => f.url)
  const userMsg = messages.value.find(m => m.id === userMsgId)
  if (userMsg) {
    userMsg.attachments = uploadedAttachments.length > 0 ? uploadedAttachments : null
  }
  const streamHistory = buildStreamHistory()

  const aiMsgId = Date.now() + 1
  messages.value.push({ id: aiMsgId, role: 'ai', content: '', time: now() })
  streamingMsgId.value = aiMsgId
  streamingMsgRef.value = messages.value[messages.value.length - 1] || null
  isStreamDone = false
  streamRenderedChunks.length = 0
  streamDisplayText.value = ''

  if (chatMode.value === 'digital_human' && isAvatarConnected.value) {
    startAvatarThinkingTimeout()
    const aiMsg = messages.value.find(m => m.id === aiMsgId)
    if (aiMsg) {
      aiMsg.teachingDiagramGenerating = shouldGenerateTeachingDiagram
    }
    sendAvatarText({
      text: text || '请分析附件',
      need_diagram: shouldGenerateTeachingDiagram,
      attachments: attachmentUrls.length > 0 ? attachmentUrls : undefined,
      ...getAvatarCapabilities(),
      speech_rate: avatarSpeechRate.value,
    })
    return
  }

  abortController = streamChat(
      {
        history: streamHistory,
        session_id: currentSessionId.value,
        attachments: attachmentUrls.length > 0 ? attachmentUrls : undefined,
        need_teaching_diagram: shouldGenerateTeachingDiagram,
        generate_video: generateVideo.value,
        enable_search: enableWebSearch.value || enableKnowledgeBase.value,
      },
      (chunk) => {
        enqueueStreamChunk(aiMsgId, chunk)
      },
      () => {
        isStreamDone = true
        const finishedSessionId = currentSessionId.value
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.teachingDiagramGenerating = false
        }
        if (pendingRenderQueueStart >= pendingRenderQueue.length) {
          stopStreamFlushLoop()
          finishStream(aiMsgId)
        }
        if (finishedSessionId) {
          void refreshSessionTitleWithRetry(finishedSessionId)
        }
      },
      (err) => {
        isStreamDone = false
        flushPendingStreamText(true)
        stopStreamFlushLoop()
        commitStreamTextToMessage(aiMsgId)
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        if (aiMsg) {
          aiMsg.teachingDiagramGenerating = false
          if (!aiMsg.content) {
            aiMsg.content = `Generate failed: ${err.message}`
          }
        }
        stopTeachingDiagramGeneratingForCurrentAi()
        isAIThinking.value = false
        streamingMsgId.value = null
        streamingMsgRef.value = null
        abortController = null
      },
      (evt) => {
        if (evt.event === 'status') {
          const payload = evt.data as { stage?: string; message?: string }
          const aiMsg = messages.value.find(m => m.id === aiMsgId)
          if (!aiMsg) return

          if ([
            'preparing_context',
            'classify',
            'search_node',
            'spark_summary',
            'direct_answer',
            'attachment_answer',
            'reading_profile',
            'searching_learning_memory',
            'persisting_turn',
          ].includes(payload?.stage || '')) {
            aiMsg.searchStage = payload.stage
            aiMsg.searchMessage = payload.message || '正在组织本轮回答...'
            scrollToBottom()
            return
          }
          if (payload?.stage === 'teaching_diagram_generate') {
            aiMsg.searchStage = undefined
            aiMsg.searchMessage = undefined
            aiMsg.teachingDiagramGenerating = true
            scrollToBottom()
            return
          }
          return
        }

        if (evt.event === 'diagram') {
          const diagram = normalizeTeachingDiagram(evt.data as TeachingDiagram)
          const aiMsg = messages.value.find(m => m.id === aiMsgId)
          if (!aiMsg || !diagram) return
          aiMsg.searchStage = undefined
          aiMsg.searchMessage = undefined
          aiMsg.teachingDiagram = diagram
          aiMsg.teachingDiagramGenerating = false
          scrollToBottom()
          return
        }

        if (evt.event === 'done') {
          const payload = evt.data as {
            teaching_diagram?: TeachingDiagram | null
            resources?: { teaching_diagram?: TeachingDiagram | null }
            knowledge_sources?: KnowledgeSource[]
          }
          const diagram = normalizeTeachingDiagram(payload?.teaching_diagram || payload?.resources?.teaching_diagram)
          const aiMsg = messages.value.find(m => m.id === aiMsgId)
          if (!aiMsg) return
          aiMsg.searchStage = undefined
          aiMsg.searchMessage = undefined
          aiMsg.teachingDiagramGenerating = false
          if (Array.isArray(payload?.knowledge_sources)) {
            aiMsg.knowledgeSources = payload.knowledge_sources
          }
          if (!diagram) return
          aiMsg.teachingDiagram = diagram
          scrollToBottom()
        }
      },
  )
}

watch(chatMode, async (newMode) => {
  if (newMode === 'digital_human') {
    sessionSidebarCollapsed.value = true
    digitalHumanSessionId.value = undefined
    messages.value = []
    pendingFiles.value = []
    if (!await ensureCurrentSession('digital_human')) return
    await connectAvatar()
    setAvatarNeedDiagram(needTeachingDiagram.value)
    nextTick(() => {
      const container = canvasRef.value?.getContainer()
      if (container) {
        setPlayerContainer(container)
      }
    })
  } else if (newMode === 'standard') {
    sessionSidebarCollapsed.value = false
    disconnectAvatar()
    pendingFiles.value = []
    if (currentSessionId.value) {
      await switchSession(currentSessionId.value)
    } else {
      messages.value = []
    }
  }
})

watch(needTeachingDiagram, (enabled) => {
  if (chatMode.value === 'digital_human' && isAvatarConnected.value) {
    setAvatarNeedDiagram(enabled)
  }
})

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
})

onBeforeUnmount(() => {
  clearAvatarThinkingTimeout()
  disconnectAvatar()
  flushPendingStreamText()
  stopStreamFlushLoop()
  if (streamingMsgId.value !== null) {
    commitStreamTextToMessage(streamingMsgId.value)
  }
  isStreamDone = false
  streamingMsgRef.value = null
  abortController?.abort()
  pendingFiles.value.forEach(f => {
    if (f.localUrl) URL.revokeObjectURL(f.localUrl)
  })
  if (dimTimer) clearTimeout(dimTimer)
  document.removeEventListener('mousedown', handleGlobalClick)
  document.removeEventListener('touchstart', handleGlobalClick)
})
</script>

<style scoped>
/* 覆盖 ElPopover 的默认内边距 */
:global(.el-popover.custom-plus-popover) {
  padding: 0 !important;
  border-radius: var(--radius-xl) !important;
  border: none !important;
  box-shadow: var(--shadow-lg) !important;
}

.search-status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 10px;
  margin-top: 10px;
  color: var(--el-color-primary);
  font-size: 13px;
  font-weight: 500;
  width: fit-content;
}

.search-status-text {
  animation: pulse-text 1.5s infinite ease-in-out;
}
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
  gap: var(--space-2);
  color: var(--color-text);
  font-weight: var(--weight-bold);
  font-size: 1.05rem;
}

.brand-icon {
  color: var(--color-primary);
  font-size: 1.25rem;
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
}
.nav-item.history-collapsed-btn:hover {
  background: var(--color-border);
  color: var(--color-text);
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
.history-section-header .el-icon {
  font-size: 1.25rem;
  color: var(--color-primary);
}

.popover-search-container {
  display: flex;
  flex-direction: column;
}

:deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--color-border) inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border-hover) inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #0891B2 inset !important;
}

.popover-session-scroll {
  max-height: 40vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
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

.teaching-diagram-generating {
  margin-top: var(--space-3);
  padding: var(--space-4);
  width: min(100%, 680px);
  max-width: 100%;
  background: var(--color-surface);
  border: 1px solid var(--color-surface-hover);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
}

.teaching-diagram-generating::after {
  content: '';
  position: absolute;
  top: 0; left: -150%; width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transform: skewX(-20deg);
  animation: diagram-shimmer 2.5s infinite ease-in-out;
  pointer-events: none;
}

@keyframes diagram-shimmer {
  100% { left: 150%; }
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

/* 预览对话框样式 */
.diagram-preview-dialog :deep(.el-dialog__body) {
  padding: 0;
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

.digital-human-stage {
  width: 45%;
  min-width: 320px;
  max-width: 600px;
  background: var(--color-bg);
  border-right: 1px solid var(--color-border);
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
  color: var(--color-text-faint);
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
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  border: 1px solid var(--color-border);
  transition: all var(--transition-slow);
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

.listening-dot,
.asr-processing-dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-pill);
}

.listening-dot {
  background: #0EA5E9;
  box-shadow: 0 0 0 0 rgba(14, 165, 233, 0.45);
  animation: listening-pulse 1.4s infinite;
}

.asr-processing-dot {
  background: var(--color-warning);
  box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.42);
  animation: processing-pulse 1s infinite;
}

@keyframes listening-pulse {
  0% { box-shadow: 0 0 0 0 rgba(14, 165, 233, 0.45); }
  70% { box-shadow: 0 0 0 10px rgba(14, 165, 233, 0); }
  100% { box-shadow: 0 0 0 0 rgba(14, 165, 233, 0); }
}

@keyframes processing-pulse {
  0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.42); transform: scale(1); }
  60% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); transform: scale(1.08); }
  100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); transform: scale(1); }
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
  color: var(--color-text-muted);
  font-family: var(--font-sans);
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

/* ================= 聊天气泡深度优化 ================= */
.message-row {
  display: flex;
  gap: 1rem;
  max-width: 60%;
  animation: msg-appear var(--transition-slow)-out;
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
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.ai-av {
  background: var(--color-text);
  color: var(--color-surface);
}

.user-av {
  background: var(--color-border);
  color: var(--color-text-secondary);
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
}

.message-row.user .msg-meta {
  flex-direction: row-reverse;
}

.sender {
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
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

.mode-digital_human .message-row {
  max-width: min(820px, 92%);
}

.mode-digital_human .message-row.ai {
  align-self: center;
  width: min(820px, 92%);
  gap: 0.75rem;
}

.mode-digital_human .message-row.ai .msg-avatar {
  display: none;
}

.mode-digital_human .message-row.ai .bubble-wrapper {
  width: 100%;
  align-items: stretch;
}

.mode-digital_human .message-row.ai .msg-meta {
  justify-content: center;
  gap: 10px;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}

.mode-digital_human .message-row.ai .sender {
  color: #475569;
}

.digital-human-bubble {
  padding: 18px 22px;
  border-radius: 22px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 250, 252, 0.9)),
    radial-gradient(circle at top, rgba(56, 189, 248, 0.08), transparent 55%);
  box-shadow:
    0 10px 28px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
}

.mode-digital_human .digital-human-bubble :deep(.tutor-message-content) {
  align-items: center;
}

.mode-digital_human .digital-human-bubble :deep(.stream-markdown) {
  font-size: 1.08rem;
  line-height: 1.9;
  letter-spacing: 0.01em;
  color: #0f172a;
  text-align: left;
}

.mode-digital_human .digital-human-bubble :deep(.markdown-body p) {
  margin: 0 0 0.72rem 0;
}

.mode-digital_human .digital-human-bubble :deep(.markdown-body > :last-child) {
  margin-bottom: 0;
}

.mode-digital_human .digital-human-bubble :deep(h1),
.mode-digital_human .digital-human-bubble :deep(h2),
.mode-digital_human .digital-human-bubble :deep(h3),
.mode-digital_human .digital-human-bubble :deep(h4) {
  text-align: left;
  color: #0f172a;
}

.mode-digital_human .digital-human-bubble :deep(ul),
.mode-digital_human .digital-human-bubble :deep(ol) {
  padding-left: 1.25rem;
}

/* AI 气泡：柔和浮动悬浮卡片 */
.message-row.ai .bubble {
  background: var(--color-surface);
  border: 1px solid rgba(0, 0, 0, 0.03);
  border-radius: var(--radius-xl);
  border-top-left-radius: 4px;
  color: var(--color-text);
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.04), 0 2px 8px rgba(15, 23, 42, 0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.message-row.ai .bubble:hover {
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06), 0 3px 10px rgba(15, 23, 42, 0.03);
}

/* AI 正在思考/输入指示器 */
.thinking-loader {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-1) var(--space-2);
  height: 20px;
}

.thinking-loader .dot {
  width: 8px;
  height: 8px;
  background-color: var(--tone-indigo);
  border-radius: var(--radius-pill);
  opacity: 0.4;
  animation: thinking-bounce 1.4s infinite ease-in-out both;
}

.thinking-loader .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking-loader .dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes thinking-bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
    background-color: var(--color-primary);
  }
}


/* 用户气泡：现代渐变蓝紫与发光阴影 */
.message-row.user .bubble {
  background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
  color: #ffffff;
  border: none !important;
  border-radius: var(--radius-xl);
  border-top-right-radius: 4px;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25), 0 2px 6px rgba(99, 102, 241, 0.15);
}

/* 覆盖用户气泡内的 Markdown 颜色 */
.message-row.user :deep(.markdown-body) {
  color: #ffffff !important;
}
.message-row.user :deep(.markdown-body a) {
  color: rgba(255, 255, 255, 0.9) !important;
  text-decoration: underline;
}
.message-row.user :deep(.markdown-body code:not(pre code)) {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #ffffff !important;
  border: none;
}

.user-plain-text {
  margin: 0;
  padding: 0;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
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
  padding: 1var(--space-1) var(--space-4);
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

.knowledge-sources {
  margin-top: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.knowledge-sources-title {
  font-size: 0.8rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.knowledge-source-item {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 0.78rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.knowledge-source-item + .knowledge-source-item {
  margin-top: 6px;
}

.knowledge-source-rank {
  color: var(--color-text-faint);
}

.knowledge-source-name {
  color: var(--color-text);
  word-break: break-word;
}

.knowledge-source-meta {
  color: var(--color-text-faint);
  white-space: nowrap;
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
  background: var(--color-surface); /* 卡片底色 */
  border: 1px solid var(--color-border);
  border-radius: 20px; /* 极简大圆角 */
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: all var(--transition-base);
  box-sizing: border-box;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.minimal-input-wrapper:focus-within {
  border-color: var(--color-border-hover);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.05);
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

.minimal-icon-btn.voice.is-recording {
  background: var(--color-danger);
  color: var(--color-surface);
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

.minimal-send-btn.can-send {
  background: var(--color-text);
  color: var(--color-surface);
  cursor: pointer;
}

.minimal-send-btn.can-send:hover {
  background: var(--color-text-strong);
  transform: scale(1.05);
}

/* 语音语速调整 */
.minimal-speech-rate {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: 8px;
}
.minimal-speech-rate .rate-label {
  font-size: 12px;
  color: var(--color-text-muted);
}
.minimal-speech-rate .rate-value {
  font-size: 12px;
  color: var(--color-text-secondary);
  min-width: 34px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.minimal-speech-rate :deep(.el-slider) {
  width: 60px;
}

/* Digital human voice chat button */
.voice-chat-btn.is-active {
  color: var(--color-text-strong);
}

.voice-bars-icon {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 14px;
}

.voice-bars-icon .bar {
  width: 2px;
  background-color: currentColor;
  border-radius: 1px;
  transition: height var(--transition-base);
}

.voice-bars-icon .bar:nth-child(1) { height: 8px; }
.voice-bars-icon .bar:nth-child(2) { height: 14px; }
.voice-bars-icon .bar:nth-child(3) { height: 10px; }
.voice-bars-icon .bar:nth-child(4) { height: 6px; }

.voice-chat-btn.is-active .bar {
  animation: bar-dance 0.8s infinite ease-in-out alternate;
  background-color: #f43f5e;
}

.voice-chat-btn.is-active .bar:nth-child(1) { animation-delay: 0.0s; }
.voice-chat-btn.is-active .bar:nth-child(2) { animation-delay: 0.2s; }
.voice-chat-btn.is-active .bar:nth-child(3) { animation-delay: 0.1s; }
.voice-chat-btn.is-active .bar:nth-child(4) { animation-delay: 0.3s; }

@keyframes bar-dance {
  from { transform: scaleY(0.6); }
  to { transform: scaleY(1.4); }
}

.input-footer {
  text-align: center;
  font-size: 0.7rem;
  color: var(--color-text-faint);
  margin-top: var(--space-2);
}

/* Empty State */
.profile-empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) var(--space-6);
  text-align: center;
  background: var(--color-surface);
  border-radius: var(--radius-2xl);
  border: 1px solid var(--color-border);
  box-shadow: inset 0 0 20px rgba(148, 163, 184, 0.05);
  margin-top: var(--space-2);
}

.empty-visual-container {
  position: relative;
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-6);
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px solid var(--color-border-hover);
  border-radius: var(--radius-pill);
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
  background: var(--color-bg);
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2rem;
  color: var(--color-text-muted);
  z-index: 2;
  animation: float 4s ease-in-out infinite;
}

.empty-text-wrap h4 {
  margin: 0 0 var(--space-2) 0;
  font-size: 1.05rem;
  color: var(--color-text-strong);
  font-weight: var(--weight-bold);
}

.empty-text-wrap p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.empty-hints {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-3);
  margin-top: var(--space-6);
}

.hint-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-bg);
  padding: 6px var(--space-3);
  border-radius: var(--radius-md);
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: var(--weight-semibold);
  border: 1px solid var(--color-surface-hover);
}

.hint-item .el-icon {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.long-term-memory-section {
  margin-top: auto;
  padding: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
}

.memory-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.memory-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.memory-title {
  font-size: 0.95rem;
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.info-icon {
  font-size: 0.9rem;
  color: var(--color-text-faint);
  cursor: help;
}

.memory-switch-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.switch-status {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: var(--weight-medium);
}

.memory-desc {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--color-border-hover); border-radius: 2px; }

.mode-standard .session-sidebar {
  background: var(--color-bg);
  border-right: 1px solid var(--color-bg);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.mode-standard .chat-viewport {
  background: var(--color-surface);
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

.fab-container {
  position: fixed;
  z-index: 1000;
  touch-action: none;
  transition: all var(--transition-slow) cubic-bezier(0.4, 0, 0.2, 1);
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
  border-radius: var(--radius-pill);
  background: var(--color-text); /* 与整体风格统一 */
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2);
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
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
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: 0 10px 30px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transform-origin: bottom left;
}
.fab-container.stick-right .fab-menu {
  left: auto;
  right: 0;
  transform-origin: bottom right;
}

.fab-menu-item {
  padding: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);
  position: relative;
  background: transparent;
}
.fab-menu-item:hover {
  background: var(--color-bg);
}
.fab-menu-item.active {
  background: var(--color-surface-hover);
}

.menu-icon-box {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  color: var(--color-text-muted);
  font-size: 1.3rem;
  transition: all var(--transition-base);
  flex-shrink: 0;
}
.fab-menu-item.active .menu-icon-box {
  background: var(--color-border);
  color: var(--color-text);
}

.menu-text-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.menu-title {
  font-size: 0.95rem;
  font-weight: var(--weight-semibold);
  color: var(--color-text-secondary);
  transition: color var(--transition-base);
}
.fab-menu-item.active .menu-title {
  color: var(--color-text);
}
.menu-desc {
  font-size: 0.75rem;
  color: var(--color-text-faint);
}

.check-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text);
  font-size: 1.2rem;
  display: flex;
}

.fab-menu-fade-enter-active,
.fab-menu-fade-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
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
  padding: var(--space-1) 0;
  background: var(--color-surface);
  border-radius: var(--radius-xl);
}

.action-item {
  display: flex;
  align-items: center;
  padding: 0 var(--space-4);
  cursor: pointer;
  transition: background-color var(--transition-base);
  border-radius: var(--radius-md);
}

.action-item:hover {
  background-color: var(--color-bg);
}

.item-icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  margin-right: 1var(--space-1);
  margin-top: var(--space-2);
  margin-bottom: var(--space-2);
  flex-shrink: 0;
}

.bg-blue { background-color: var(--color-surface-hover); color: var(--color-text-secondary); }
.bg-purple { background-color: var(--color-surface-hover); color: var(--color-text-secondary); }
.bg-teal { background-color: var(--color-surface-hover); color: var(--color-text-secondary); }
.bg-active { background-color: var(--color-border); color: var(--color-text); }

.item-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-bg);
}

.action-item:last-child .item-content {
  border-bottom: none;
}

.item-text {
  font-size: 14px;
  color: var(--color-text-strong);
  font-weight: var(--weight-medium);
  letter-spacing: 0.5px;
}

.item-arrow {
  color: var(--color-text-faint);
  font-size: 14px;
}

.attachment-img-preview {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-md);
  object-fit: cover;
  flex-shrink: 0;
}
.minimal-attachment-chip .attachment-img-preview {
  width: 40px;
  height: 40px;
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
.minimal-attachment-chip .file-icon-box {
  width: 24px;
  height: 24px;
  font-size: 14px;
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
</style>
