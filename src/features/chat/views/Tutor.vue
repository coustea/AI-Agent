<template>
  <div :class="['tutor-dashboard', `mode-${chatMode}`]">

    <main class="dashboard-main">
      <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">

        <div class="sidebar-top-header">
          <div class="sidebar-brand" v-if="!sessionSidebarCollapsed">
            <AppLogo class="brand-icon" />
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
            <EditPen class="nav-icon" /> <span class="nav-text">新建对话</span>
          </div>

          <PopoverRoot v-model:open="searchPopoverVisible">
            <PopoverTrigger class="nav-item search-item" title="搜索历史" style="background: none; border: none; text-align: left; padding: 0; outline: none; width: 100%;">
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
                        :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
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

          <PopoverRoot>
            <PopoverTrigger v-if="sessionSidebarCollapsed" class="nav-item history-collapsed-btn" title="历史记录" style="background: none; border: none; text-align: left; padding: 0; outline: none; width: 100%;">
              <Timer class="nav-icon" />
            </PopoverTrigger>

            <PopoverPortal>
              <PopoverContent
                class="popover-content-container history-popover-content"
                side="right"
                align="start"
                :side-offset="8"
              >
                <div class="popover-session-scroll">
                  <div class="popover-title">历史记录</div>
                  <div
                      v-for="s in sessions"
                      :key="s.id"
                      :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
                      @click="switchSession(s.id)"
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
              v-for="s in sessions"
              :key="s.id"
              :class="['nav-item', 'session-item', { active: s.id === currentSessionId }]"
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
              <h2>你好，{{ userName }}。欢迎回到思辨书房。</h2>
            </div>

            <div class="welcome-banner" v-if="chatMode === 'digital_human' && messages.length === 0">
              <div class="welcome-icon"><Cpu /></div>
              <h3>进入您的专属认知书房</h3>
              <p class="cognitive-note">在这里，每一次对话都会成为塑形您学习画像的线索。<br>我支持跨媒介文献与视听分析，我们将共同构建您的个性化认知图谱。</p>
            </div>

            <!-- 本地附件上传状态。回答前的 agent 状态由后端 SSE activity 事件驱动。 -->
            <div
              v-if="chatMode === 'standard' && uploadingFile && !streamingMsgId"
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
                  || msg.agentActivities?.length
                  || msg.teachingDiagramGenerating
                  || msg.teachingDiagram
                "
                :class="['message-row', msg.role]"
              >

                <div class="msg-avatar">
                  <div v-if="msg.role === 'ai'" class="avatar-circle ai-av"><Service /></div>
                  <div v-else class="avatar-circle user-av"><UserFilled /></div>
                </div>

                <div class="bubble-wrapper" @click="handleMessageClick">
                  <div class="msg-meta">
                    <span class="sender">{{ msg.role === 'ai' ? 'AI 导师' : '我' }}</span>
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

                  <AgentActivityCard
                    v-if="msg.role === 'ai' && msg.agentActivities?.length"
                    :activities="msg.agentActivities"
                  />

                  <div
                    v-if="getDisplayContent(msg)"
                    :class="[
                      'bubble',
                      'markdown-body',
                      msg.role === 'ai' ? 'assistant-answer' : 'user-message-bubble',
                      { 'digital-human-bubble': chatMode === 'digital_human' && msg.role === 'ai' },
                    ]"
                  >
                    <div v-if="msg.role === 'user'" class="user-plain-text">{{ getDisplayContent(msg) }}</div>
                    <TutorMessageContent
                      v-else
                      :content="getDisplayContent(msg)"
                      :is-streaming="isStreamingMessage(msg)"
                    />
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

                  <div v-if="msg.teachingDiagramGenerating" class="diagram-generation-panel">
                    <div class="diagram-blueprint" aria-hidden="true">
                      <span class="blueprint-node node-a"></span>
                      <span class="blueprint-node node-b"></span>
                      <span class="blueprint-node node-c"></span>
                      <span class="blueprint-node node-d"></span>
                      <i class="blueprint-line line-a"></i>
                      <i class="blueprint-line line-b"></i>
                      <i class="blueprint-line line-c"></i>
                    </div>
                    <div class="diagram-generation-copy">
                      <span class="diagram-generation-kicker">VISUAL EXPLANATION</span>
                      <strong>正在绘制教学图解</strong>
                      <p>将答案整理为关键节点、关系和理解顺序，完成后会直接显示在回答下方。</p>
                      <div class="diagram-generation-progress" aria-hidden="true"><span></span></div>
                    </div>
                  </div>

                  <div v-if="msg.teachingDiagram" class="msg-teaching-diagram">
                    <TeachingDiagramCard
                      :diagram="msg.teachingDiagram"
                      compact
                      @expand="previewTeachingDiagram"
                    />
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
                  aria-label="向 AI 导师提问"
                  placeholder="向 AI 导师提问"
                  @compositionstart="isComposing = true"
                  @compositionend="isComposing = false"
                  @keydown.enter="handleEnter"
                  @input="autoResize"
              ></textarea>

              <div class="minimal-action-bar">
                <div class="action-left">
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
                    :class="{ 'is-active-blue': enableWebSearch }"
                    @click="enableWebSearch = !enableWebSearch"
                    :aria-pressed="enableWebSearch"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="btn-icon" aria-hidden="true">
                      <circle cx="12" cy="12" r="9"></circle>
                      <ellipse cx="12" cy="12" rx="4.5" ry="9"></ellipse>
                      <line x1="3" y1="12" x2="21" y2="12"></line>
                    </svg>
                    <span>联网</span>
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
                </div>

                <div class="action-right">
                  <div v-if="chatMode === 'digital_human'" class="minimal-speech-rate">
                    <span class="rate-label">语速</span>
                    <input
                      type="range"
                      v-model.number="avatarSpeechRate"
                      min="0.8"
                      max="1.5"
                      step="0.1"
                      :disabled="isAvatarSpeaking"
                      @change="handleAvatarSpeechRateChange(avatarSpeechRate)"
                      class="rate-slider-input"
                    />
                    <span class="rate-value">{{ avatarSpeechRate.toFixed(1) }}x</span>
                  </div>

                  <button
                      v-if="chatMode === 'digital_human'"
                      type="button"
                      class="minimal-icon-btn voice-chat-btn"
                      :class="{ 'is-active': isVoiceChatting }"
                      @click="handleVoiceChatToggle"
                      :aria-label="isVoiceChatting ? '结束语音对话' : '开启语音通话'"
                      :title="isVoiceChatting ? '结束语音对话' : '开启语音通话'"
                  >
                    <div class="voice-bars-icon" aria-hidden="true">
                      <span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span>
                    </div>
                  </button>

                  <button
                    v-if="chatMode === 'digital_human'"
                    type="button"
                    class="minimal-icon-btn voice"
                    :class="{ 'is-recording': isRecording }"
                    @click="handleVoiceToggle"
                    :aria-label="isRecording ? '结束录音' : '语音提问'"
                    :title="isRecording ? '结束录音' : '语音提问'"
                  >
                    <Microphone class="btn-icon" aria-hidden="true" />
                  </button>

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
              <ChatLineRound class="nav-icon" />
            </div>
            <div class="menu-text-content">
              <div class="menu-title">图文交互</div>
              <div class="menu-desc">文字、图片多模态交流</div>
            </div>
            <div class="check-icon" v-if="chatMode === 'standard'">
              <CircleCheckFilled class="check-icon-glyph" />
            </div>
          </div>
          <div
              class="fab-menu-item"
              :class="{ active: chatMode === 'digital_human' }"
              @click="setChatMode('digital_human')"
          >
            <div class="menu-icon-box">
              <Avatar class="nav-icon" />
            </div>
            <div class="menu-text-content">
              <div class="menu-title">数字人互动</div>
              <div class="menu-desc">与数字人进行语音对话</div>
            </div>
            <div class="check-icon" v-if="chatMode === 'digital_human'">
              <CircleCheckFilled class="check-icon-glyph" />
            </div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 教学图解全屏预览 -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="teachingDiagramPreviewVisible" class="custom-modal-overlay" @click.self="teachingDiagramPreviewVisible = false">
          <div class="custom-modal-container diagram-preview-dialog">
            <header class="custom-modal-header diagram-dialog-header">
              <div>
                <span class="diagram-kicker">教学图解</span>
                <strong class="diagram-title">{{ teachingDiagramPreviewData?.title || '图解说明' }}</strong>
              </div>
              <button type="button" class="modal-close-btn" @click="teachingDiagramPreviewVisible = false" aria-label="关闭图解">
                <Close class="close-icon" />
              </button>
            </header>

            <div v-if="teachingDiagramPreviewData" class="custom-modal-body diagram-preview-body">
              <div class="preview-content">
                <TeachingDiagramCard :diagram="teachingDiagramPreviewData" />
              </div>
              <div class="preview-footer">
                <span>图解可保存为高清图片，便于复习和整理笔记。</span>
                <div class="footer-actions">
                  <button class="btn btn-outline" :disabled="isCapturing" @click="handleDownloadDiagram">
                    <span v-if="isCapturing" class="spinner mr-2"></span>
                    <Download class="btn-icon-left" />
                    <span>保存图片</span>
                  </button>
                  <button class="btn btn-primary" @click="teachingDiagramPreviewVisible = false">完成</button>
                </div>
              </div>
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
import { ref, nextTick, onMounted, onBeforeUnmount, onActivated, onDeactivated, computed, watch } from 'vue'
import {
  PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent
} from 'radix-vue'
import {
  PhChatCenteredText as ChatLineRound,
  PhUser as Avatar,
  PhCpu as Cpu,
  PhHeadset as Service,
  PhUser as UserFilled,
  PhMicrophone as Microphone,
  PhFileText as Document,
  PhChat as ChatLineSquare,
  PhTrash as Delete,
  PhX as Close,
  PhPaperclip as Paperclip,
  PhPencilSimple as EditPen,
  PhMagnifyingGlass as Search,
  PhClock as Timer,
  PhGraph as DataLine,
  PhCheckCircle as CircleCheckFilled,
  PhDownload as Download,
  PhSpinner as Loading
} from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import { getErrorMessage } from '@/shared/api/http'
import { ensureCurrentUser, useCurrentUser } from '@/features/auth/model/currentUser'
import TutorMessageContent from '@/features/chat/components/TutorMessageContent.vue'
import TeachingDiagramCard from '@/features/chat/components/TeachingDiagramCard.vue'
import AgentActivityCard from '@/features/chat/components/AgentActivityCard.vue'
import AppLogo from '@/shared/ui/AppLogo.vue'

import { useDiagramCapture } from '@/features/chat/composables/useDiagramCapture'

import { triggerGlobalProfileRefresh } from '@/features/profile/model/useGlobalProfile'
import { useChatStreamManager } from '@/features/chat/composables/useChatStreamManager'
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
  TeachingDiagram,
} from '@/features/chat/types/chat'
import type { ChatEvent } from '@/features/chat/types/chatEvent'
import { useDigitalHuman } from '@/features/chat/digital-human/model/useDigitalHuman'
import DigitalHumanCanvas from '@/features/chat/digital-human/views/DigitalHumanCanvas.vue'
import {
  type PendingFile,
  type Attachment,
  type ChatMsg,
  type AgentActivity,
  normalizeTeachingDiagram,
  getDocumentType,
  getDocumentIconColor,
  formatFileSize,
  formatRelativeTime,
  isInsideOpenFence,
  takeNextStreamUnit,
} from './tutorUtils'

defineOptions({ name: 'Tutor' })

const DEFAULT_SESSION_TITLE = '新对话'
const SESSION_TITLE_REFRESH_DELAYS = [300, 800, 1500, 3000]
const { userName } = useCurrentUser()

// 状态
const chatMode = ref('standard')
const userInput = ref('')
const isAIThinking = ref(false)
const digitalHumanBackendStatus = ref('')
const chatScroll = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messageFormRef = ref<HTMLFormElement | null>(null)
const isExpandedInput = ref(false)
const isComposing = ref(false)

const enableWebSearch = ref(false)
const needTeachingDiagram = ref(false)

const imgPreviewVisible = ref(false)
const imgPreviewUrl = ref('')
const triggerImagePreview = (urls: string[], index: number) => {
  const url = urls[index]
  if (url) {
    imgPreviewUrl.value = url
    imgPreviewVisible.value = true
  }
}

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
      clearAgentStatus(messages.value.find(message => message.id === streamingMsgId.value && message.role === 'ai'))
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
    toast.error({ message: msg, plain: true })
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
const searchPopoverVisible = ref(false)
const searchKeyword = ref('')

const messages = ref<ChatMsg[]>([])
const streamingMsgId = ref<number | null>(null)
const streamingMsgRef = ref<ChatMsg | null>(null)

/**
 * 当前会话是否正处于回答链路中。
 * 覆盖附件上传、等待首个 token、流式输出和数字人回答阶段。
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

const streamManager = useChatStreamManager()
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

type AgentStatusPayload = {
  activity_id: string
  kind: AgentActivity['kind']
  stage?: string
  status: 'running' | 'done' | 'failed'
  tool_name?: string
  title: string
  summary?: string
  message?: string
  detail?: AgentActivity['detail']
}

const getCurrentAiTextStarted = (aiMsg?: ChatMsg) => Boolean(
  aiMsg
  && (
    aiMsg.content
    || streamDisplayText.value
    || pendingRenderQueue.length > pendingRenderQueueStart
    || streamRenderedChunks.length
  )
)

const applyAgentStatus = (aiMsg: ChatMsg | undefined, payload: AgentStatusPayload) => {
  if (!aiMsg) return
  const activity: AgentActivity = {
    activity_id: payload.activity_id,
    kind: payload.kind,
    stage: payload.stage,
    status: payload.status,
    tool_name: payload.tool_name,
    title: payload.title,
    summary: payload.summary,
    message: payload.message,
    detail: payload.detail,
  }
  const activities = aiMsg.agentActivities || (aiMsg.agentActivities = [])
  const index = activities.findIndex(item => item.activity_id === activity.activity_id)
  if (index >= 0) activities.splice(index, 1, activity)
  else activities.push(activity)
}

const applyChatEvent = (aiMsg: ChatMsg | undefined, event: ChatEvent) => {
  if (!aiMsg) return

  const data = (event.data || {}) as Record<string, unknown>

  if (event.event === 'content.delta') {
    clearAgentStatus(aiMsg)
    return
  }

  if (event.event === 'content.replace') {
    const content = typeof data.content === 'string' ? data.content : ''
    if (content) {
      stopStreamFlushLoop()
      pendingRenderQueue.length = 0
      pendingRenderQueueStart = 0
      pendingRenderOffset = 0
      pendingRenderChars = 0
      streamRenderedChunks.length = 0
      aiMsg.content = content
      streamDisplayText.value = content
    }
    clearAgentStatus(aiMsg)
    return
  }

  if (event.event === 'diagram.ready') {
    const diagram = normalizeTeachingDiagram(data as unknown as TeachingDiagram)
    if (diagram) {
      aiMsg.teachingDiagram = diagram
      aiMsg.teachingDiagramGenerating = false
    }
    return
  }

  if (event.event === 'run.started') {
    if (getCurrentAiTextStarted(aiMsg)) return
    const title = typeof data.title === 'string' && data.title.trim()
      ? data.title.trim()
      : event.message.trim() || '正在思考'
    applyAgentStatus(aiMsg, {
      activity_id: typeof data.activity_id === 'string' && data.activity_id.trim()
        ? data.activity_id.trim()
        : 'workflow:current',
      kind: 'workflow',
      stage: typeof data.stage === 'string' ? data.stage : 'run_started',
      status: 'running',
      title,
      message: typeof data.message === 'string' && data.message.trim()
        ? data.message.trim()
        : title,
      summary: typeof data.summary === 'string' ? data.summary : undefined,
    })
    return
  }

  if (
    event.event === 'activity.running'
    || event.event === 'activity.completed'
    || event.event === 'activity.failed'
  ) {
    const stage = data.stage as string | undefined
    if (getCurrentAiTextStarted(aiMsg)) {
      clearAgentStatus(aiMsg)
      return
    }
    if (['teaching_diagram_generate', 'diagram_start', 'diagram_generate'].includes(stage || '')) {
      aiMsg.teachingDiagramGenerating = true
    }
    const activityId = String(data.activity_id || '').trim()
    const kind = data.kind === 'tool' || data.kind === 'attachment' || data.kind === 'workflow'
      ? data.kind
      : 'workflow'
    const toolName = typeof data.tool_name === 'string' ? data.tool_name : undefined
    const detail = (
      data.detail && typeof data.detail === 'object'
        ? data.detail
        : {}
    ) as AgentActivity['detail']
    const title = typeof data.title === 'string' && data.title.trim()
      ? data.title.trim()
      : event.message.trim() || '正在处理'
    if (!activityId) return

    applyAgentStatus(aiMsg, {
      activity_id: activityId,
      kind,
      stage: typeof data.stage === 'string' ? data.stage : undefined,
      status: event.event === 'activity.completed' ? 'done' : event.event === 'activity.failed' ? 'failed' : 'running',
      tool_name: toolName || detail?.tool_name,
      title,
      summary: typeof data.summary === 'string' && data.summary
        ? data.summary
        : detail?.files?.length
          ? detail.files.join('、')
          : detail?.input,
      message: typeof data.message === 'string' && data.message.trim()
        ? data.message.trim()
        : event.message,
      detail,
    })
  }
}

const clearAgentStatus = (aiMsg?: ChatMsg) => {
  if (!aiMsg) return
  if (aiMsg.agentActivities?.length) {
    aiMsg.agentActivities = []
  }
}

const clearAvatarThinkingTimeout = () => {
  if (avatarThinkingTimeout) {
    clearTimeout(avatarThinkingTimeout)
    avatarThinkingTimeout = null
  }
}

const detachCurrentStreamCallbacks = () => {
  if (!currentSessionId.value) return
  const streamState = streamManager.getStreamState(currentSessionId.value)
  if (streamState?.status === 'streaming') {
    streamManager.resubscribe(currentSessionId.value, {})
  }
}

const pauseForegroundStreaming = () => {
  detachCurrentStreamCallbacks()
  stopStreamFlushLoop()
  if (streamingMsgId.value !== null) {
    commitStreamTextToMessage(streamingMsgId.value)
  }
  streamingMsgRef.value = null
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
    toast.warning({ message: '数字人响应超时，请重试或重新连接', plain: true })
  }, 30000)
}

let scrollPending = false
let streamFlushHandle: ReturnType<typeof window.setTimeout> | null = null
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

const { isCapturing, captureToDataUrl, downloadImage } = useDiagramCapture()

const previewTeachingDiagram = (diagram: TeachingDiagram) => {
  teachingDiagramPreviewData.value = diagram
  teachingDiagramPreviewVisible.value = true
}

const handleDownloadDiagram = async () => {
  if (!teachingDiagramPreviewData.value) return
  
  const dataUrl = await captureToDataUrl('capture-target', {
    pixelRatio: 2,
    backgroundColor: '#ffffff',
    style: {
      padding: '24px',
      borderRadius: '16px'
    }
  })
  
  if (dataUrl) {
    downloadImage(dataUrl, `${teachingDiagramPreviewData.value.title || '图解说明'}_高清截图`)
    toast.success('图解说明已保存至本地')
  }
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
}

const completeStreamingMessage = (messageId: number) => {
  isStreamDone = true
  stopStreamFlushLoop()
  const aiMsg = messages.value.find(message => message.id === messageId)
  clearAgentStatus(aiMsg)
  if (aiMsg) aiMsg.teachingDiagramGenerating = false
  finishStream(messageId)
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
  } else if (streamDisplayText.value && aiMsg.content !== streamDisplayText.value) {
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

  const minHeight = 28
  const maxHeight = 200

  el.style.height = `${minHeight}px`
  const nextHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight)

  el.style.height = `${nextHeight}px`
  el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
  isExpandedInput.value = nextHeight > 40
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
  // Detach from the current stream's render loop without aborting the SSE.
  // The global streamManager keeps the old session's connection alive so
  // the AI response continues and gets persisted by the backend.
  stopStreamFlushLoop()
  streamingMsgId.value = null
  streamingMsgRef.value = null
  isAIThinking.value = false

  currentSessionId.value = undefined
  messages.value = []
  clearPendingFiles()
}

const loadHistoryFromAPI = async (sessionId: string) => {
  try {
    const res = await getChatHistory(sessionId)
    const history = res.data.data || []
    const visibleHistory = history.filter(msg => msg.role === 'user' || msg.role === 'assistant')
    const mapped = visibleHistory.map((msg, i) => {
      // 从 ContentPart[] 中提取文本和附件
      const contentParts = msg.content || []
      const textContent = contentParts
        .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
        .map(part => part.text)
        .join('')
      const imageAttachments = contentParts
        .filter((part): part is { type: 'image_url'; image_url: { url: string } } => part.type === 'image_url')
        .map(part => ({ url: part.image_url.url, type: 'image', name: '' }))
      const fileAttachments = contentParts
        .filter((part): part is { type: 'file'; file: { file_id?: string; file_data?: string; filename?: string } } => part.type === 'file')
        .map(part => ({ url: part.file.file_id || part.file.file_data || '', type: 'document', name: part.file.filename || '' }))
      const attachments = [...imageAttachments, ...fileAttachments].length > 0
        ? [...imageAttachments, ...fileAttachments]
        : null

      return {
        id: msg.id || Date.now() + i,
        role: msg.role === 'user' ? 'user' as const : 'ai' as const,
        content: textContent,
        time: msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
        attachments,
        agentActivities: [],
      }
    })
    // 防止刷新后历史中相邻重复消息导致双排显示
    messages.value = mapped.filter((item, idx) => {
      if (idx === 0) return true
      const prev = mapped[idx - 1]
      const currentAttachmentKey = (item.attachments || []).map(att => `${att.type}:${att.url}:${att.name}`).join('|')
      const previousAttachmentKey = (prev?.attachments || []).map(att => `${att.type}:${att.url}:${att.name}`).join('|')
      return !(
        prev
        && prev.role === item.role
        && prev.content === item.content
        && previousAttachmentKey === currentAttachmentKey
      )
    })
  } catch (err) {
    toast.error({ message: getErrorMessage(err, '加载会话历史失败'), plain: true })
  }
}

const switchSession = async (sessionId: string) => {
  currentSessionId.value = sessionId
  messages.value = []

  // Check global manager for stream state on this session
  const streamState = streamManager.getStreamState(sessionId)

  if (streamState?.status === 'streaming') {
    // ── Branch 1: Stream still active ──
    // Load persisted history (won't include the in-progress AI msg)
    await loadHistoryFromAPI(sessionId)

    // Show the accumulated AI response from the stream buffer
    const { text, events } = streamManager.getBuffer(sessionId)
    const aiMsgId = Date.now() + 10000
    messages.value.push({
      id: aiMsgId,
      role: 'ai',
      content: text,
      time: now(),
    })
    streamingMsgId.value = aiMsgId
    streamingMsgRef.value = messages.value[messages.value.length - 1] ?? null
    isAIThinking.value = true
    isStreamDone = false
    streamRenderedChunks.length = 0
    streamDisplayText.value = text

    // Process buffered events (diagrams, status, etc.)
    for (const evt of events) {
      applyChatEvent(messages.value.find(m => m.id === aiMsgId), evt)
    }

    // Resubscribe callbacks so new chunks flow to this component
    streamManager.resubscribe(sessionId, {
      onChunk: (chunk) => {
        clearAgentStatus(messages.value.find(m => m.id === aiMsgId))
        enqueueStreamChunk(aiMsgId, chunk)
      },
      onDone: () => {
        completeStreamingMessage(aiMsgId)
        void refreshSessionTitleWithRetry(sessionId)
      },
      onError: (_err) => {
        isStreamDone = false
        flushPendingStreamText(true)
        stopStreamFlushLoop()
        commitStreamTextToMessage(aiMsgId)
        const aiMsg = messages.value.find(m => m.id === aiMsgId)
        clearAgentStatus(aiMsg)
        if (aiMsg) {
          aiMsg.teachingDiagramGenerating = false
          if (!aiMsg.content) {
            aiMsg.content = "生成失败，请重试。"
          }
        }
        stopTeachingDiagramGeneratingForCurrentAi()
        isAIThinking.value = false
        streamingMsgId.value = null
        streamingMsgRef.value = null
      },
      onEvent: (evt) => {
        applyChatEvent(messages.value.find(m => m.id === aiMsgId), evt)
        scrollToBottom()
      },
    })

    // Kick off the render loop to display any pending text
    scheduleStreamFlush(true)

  } else if (streamState?.status === 'done') {
    // ── Branch 2: Stream completed in background ──
    // Backend has persisted the AI message. Load from API only.
    streamManager.clearStream(sessionId)
    await loadHistoryFromAPI(sessionId)

  } else if (streamState?.status === 'error') {
    // ── Branch 3: Stream errored in background ──
    streamManager.clearStream(sessionId)
    await loadHistoryFromAPI(sessionId)
    messages.value.push({
      id: Date.now() + 99999,
      role: 'ai',
      content: `生成失败: ${streamState.error?.message || '未知错误'}`,
      time: now(),
    })

  } else {
    // ── Branch 4: No stream state — normal load ──
    await loadHistoryFromAPI(sessionId)
  }

  scrollToBottom()
}

const archiveSession = async (sessionId: string) => {
  const targetSession = sessions.value.find(session => session.id === sessionId)
  const sessionTitle = targetSession?.title?.trim() || '新建对话'

  if (!window.confirm(`确定删除“${sessionTitle}”吗？删除后无法恢复。`)) {
    return
  }

  try {
    // 只有确认后才清理流状态并调用删除接口。
    streamManager.clearStream(sessionId)
    await deleteSession(sessionId)
    sessions.value = sessions.value.filter(session => session.id !== sessionId)

    if (currentSessionId.value === sessionId) {
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

const getAvatarCapabilities = () => ({
  session_id: digitalHumanSessionId.value,
  enable_search: enableWebSearch.value,
})

const handleTeachingDiagramToggle = () => {
  needTeachingDiagram.value = !needTeachingDiagram.value
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
    toast.error({ message: '创建会话失败，请重试', plain: true })
    return false
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
    toast.success({ message: '已开启语音通话模式，您可以直接说话', plain: true })
  } else {
    stopVad()
    isRecording.value = false
    isVoiceChatting.value = false
    toast.info({ message: '已关闭语音通话模式', plain: true })
  }
}

const handleVoiceToggle = async () => {
  if (isVadListening.value) {
    stopVad()
    isRecording.value = false
    hasSpeechDetected.value = true
    startAsrProcessing(8000)
    return
  }

  if (!await ensureCurrentSession('digital_human')) return
  await startVad(needTeachingDiagram.value, getAvatarCapabilities())
  isRecording.value = isVadListening.value
  clearAsrProcessing()
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
  const currentPending = [...pendingFiles.value]
  const hasFiles = currentPending.length > 0
  if ((!text && !hasFiles) || isAIThinking.value) return

  const shouldGenerateTeachingDiagram = needTeachingDiagram.value
  const sessionMode = chatMode.value === 'digital_human' ? 'digital_human' : 'standard'

  if (chatMode.value === 'digital_human' && !isAvatarConnected.value) {
    toast.warning({ message: '数字人连接已断开，请先点击“重新连接”后再发送', plain: true })
    return
  }

  if (!await ensureCurrentSession(sessionMode)) return
  const activeSessionId = sessionMode === 'digital_human'
    ? digitalHumanSessionId.value
    : currentSessionId.value
  if (!activeSessionId) return

  const session = sessions.value.find(item => item.id === activeSessionId)
  if (session && (!session.title || session.title === DEFAULT_SESSION_TITLE)) {
    const titleSource = text || currentPending.map(file => file.name).join('、') || '附件分析'
    const tempTitle = titleSource.length > 20 ? `${titleSource.slice(0, 20)}...` : titleSource
    session.title = tempTitle
    try {
      await updateSessionTitle(activeSessionId, tempTitle)
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
  digitalHumanBackendStatus.value = ''
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
        const res = await uploadFile(pending.file, activeSessionId)
        const data = res.data.data
        return {
          url: data.url,
          fileType: pending.fileType === 'image' || data.file_type === 'image' ? 'image' : 'document',
          name: data.original_name || pending.name,
          size: data.size || pending.size,
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

  const attachmentUrls = uploadedAttachments.map(file => file.url).filter(Boolean)
  const aiMsgId = Date.now() + 1
  messages.value.push({
    id: aiMsgId,
    role: 'ai',
    content: '',
    time: now(),
    agentActivities: [],
  })
  streamingMsgId.value = aiMsgId
  streamingMsgRef.value = messages.value[messages.value.length - 1] || null
  isStreamDone = false
  streamRenderedChunks.length = 0
  streamDisplayText.value = ''

  if (chatMode.value === 'digital_human' && isAvatarConnected.value) {
    startAvatarThinkingTimeout()
    const aiMsg = messages.value.find(message => message.id === aiMsgId)
    if (aiMsg) aiMsg.teachingDiagramGenerating = shouldGenerateTeachingDiagram

    sendAvatarText({
      text: text || '请分析这些附件',
      need_diagram: shouldGenerateTeachingDiagram,
      attachments: attachmentUrls.length ? attachmentUrls : undefined,
      ...getAvatarCapabilities(),
      speech_rate: avatarSpeechRate.value,
    })
    return
  }

  streamManager.startStream(
    activeSessionId,
    {
      message: text || '请分析这些附件',
      session_id: activeSessionId,
      attachments: attachmentUrls.length ? attachmentUrls : undefined,
      need_teaching_diagram: shouldGenerateTeachingDiagram,
      enable_web_search: enableWebSearch.value,
    },
    {
      onChunk: (chunk) => {
        const aiMsg = messages.value.find(message => message.id === aiMsgId)
        clearAgentStatus(aiMsg)
        if (aiMsg && shouldGenerateTeachingDiagram && !aiMsg.teachingDiagram) {
          aiMsg.teachingDiagramGenerating = true
        }
        enqueueStreamChunk(aiMsgId, chunk)
      },
      onDone: () => {
        completeStreamingMessage(aiMsgId)
        void refreshSessionTitleWithRetry(activeSessionId)
      },
      onError: (_err) => {
        isStreamDone = false
        flushPendingStreamText(true)
        stopStreamFlushLoop()
        commitStreamTextToMessage(aiMsgId)
        const aiMsg = messages.value.find(message => message.id === aiMsgId)
        if (aiMsg) {
          aiMsg.teachingDiagramGenerating = false
          if (!aiMsg.content) aiMsg.content = '连接中断，请刷新页面后重试。'
        }
        stopTeachingDiagramGeneratingForCurrentAi()
        isAIThinking.value = false
        streamingMsgId.value = null
        streamingMsgRef.value = null
      },
      onEvent: (event) => {
        applyChatEvent(messages.value.find(message => message.id === aiMsgId), event)
        scrollToBottom()
      },
    },
  )
}

watch(chatMode, async (newMode) => {
  if (newMode === 'digital_human') {
    sessionSidebarCollapsed.value = true
    digitalHumanSessionId.value = undefined
    messages.value = []
    clearPendingFiles()
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
    clearPendingFiles()
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

  await ensureCurrentUser()
  await loadSessions()

  // If we still have a currentSessionId (from before navigating away),
  // switch back to it. This recovers streams that completed or are still
  // active in the global manager. Otherwise, pick the first session.
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
  resetDimTimer()
  document.addEventListener('mousedown', handleGlobalClick)
  document.addEventListener('touchstart', handleGlobalClick, { passive: true })

  if (currentSessionId.value) {
    await switchSession(currentSessionId.value)
  }
})

onDeactivated(() => {
  tutorWasDeactivated = true
  clearAvatarThinkingTimeout()
  pauseForegroundStreaming()
  showFabMenu.value = false
  document.removeEventListener('mousedown', handleGlobalClick)
  document.removeEventListener('touchstart', handleGlobalClick)
  if (dimTimer) {
    clearTimeout(dimTimer)
    dimTimer = null
  }
})

onBeforeUnmount(() => {
  clearAvatarThinkingTimeout()
  detachCurrentStreamCallbacks()
  disconnectAvatar()
  flushPendingStreamText()
  stopStreamFlushLoop()
  if (streamingMsgId.value !== null) {
    commitStreamTextToMessage(streamingMsgId.value)
  }
  isStreamDone = false
  streamingMsgRef.value = null
  clearPendingFiles()
  if (dimTimer) clearTimeout(dimTimer)
  document.removeEventListener('mousedown', handleGlobalClick)
  document.removeEventListener('touchstart', handleGlobalClick)
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
  color: var(--color-text-secondary);
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
  color: var(--color-text);
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
  color: var(--color-text);
}

.mode-digital_human .digital-human-bubble :deep(ul),
.mode-digital_human .digital-human-bubble :deep(ol) {
  padding-left: 1.25rem;
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

.minimal-icon-btn.voice.is-recording {
  background: var(--color-danger);
  color: var(--color-surface);
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
.minimal-speech-rate .rate-slider-input {
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
  border-right: 1px solid #dde2e8;
  display: flex;
  flex-direction: column;
  height: 100%;
}

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
  margin-right: var(--space-3);
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
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.message-row.ai .assistant-answer {
  padding: 3px 2px 0;
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
  font-size: 0.94rem;
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

.diagram-generation-panel {
  display: grid;
  grid-template-columns: 170px minmax(0, 1fr);
  gap: 18px;
  width: min(680px, 100%);
  margin-top: 8px;
  padding: 14px;
  overflow: hidden;
  background: #fbfdff;
  border: 1px solid #dbe5f2;
  border-radius: 10px;
}

.diagram-blueprint {
  position: relative;
  min-height: 112px;
  overflow: hidden;
  background:
    linear-gradient(rgba(37, 99, 235, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(37, 99, 235, 0.08) 1px, transparent 1px),
    #f4f8ff;
  background-size: 16px 16px;
  border: 1px solid #dbeafe;
  border-radius: 7px;
}

.blueprint-node {
  position: absolute;
  width: 28px;
  height: 18px;
  background: #fff;
  border: 1.5px solid #60a5fa;
  border-radius: 4px;
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.08);
  animation: blueprint-node-pulse 1.8s ease-in-out infinite;
}

.node-a { top: 20px; left: 18px; }
.node-b { top: 19px; right: 20px; animation-delay: .2s; }
.node-c { bottom: 18px; left: 46px; animation-delay: .4s; }
.node-d { right: 34px; bottom: 20px; animation-delay: .6s; }

.blueprint-line {
  position: absolute;
  display: block;
  height: 1.5px;
  background: #93c5fd;
  transform-origin: left center;
}

.line-a { top: 29px; left: 46px; width: 70px; }
.line-b { top: 38px; left: 37px; width: 54px; transform: rotate(54deg); }
.line-c { top: 65px; left: 73px; width: 49px; transform: rotate(22deg); }

.diagram-generation-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
}

.diagram-generation-kicker {
  color: #2563eb;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: .11em;
}

.diagram-generation-copy strong {
  margin-top: 4px;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 680;
}

.diagram-generation-copy p {
  margin: 5px 0 10px;
  color: var(--color-text-muted);
  font-size: 11px;
  line-height: 1.55;
}

.diagram-generation-progress {
  height: 3px;
  overflow: hidden;
  background: #e8eef7;
  border-radius: 2px;
}

.diagram-generation-progress span {
  display: block;
  width: 38%;
  height: 100%;
  background: linear-gradient(90deg, #93c5fd, #2563eb, #93c5fd);
  animation: diagram-progress-scan 1.4s ease-in-out infinite;
}

.msg-teaching-diagram {
  width: min(720px, 100%);
  max-width: 100%;
  margin-top: 10px;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}

.msg-teaching-diagram:hover {
  border-color: transparent;
  box-shadow: none;
  transform: none;
}

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

.diagram-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 62px;
  padding: 11px 16px;
}

.diagram-dialog-header > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.diagram-dialog-header span {
  color: #2563eb;
  font-size: 10px;
  font-weight: 720;
  letter-spacing: .09em;
}

.diagram-dialog-header strong {
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 680;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diagram-dialog-header button {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  color: var(--color-text-muted);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  cursor: pointer;
}

.diagram-dialog-header button:hover {
  color: var(--color-text);
  background: var(--color-bg);
}

.diagram-preview-body {
  gap: 0;
  max-height: 84vh;
  padding: 0;
  background: #f5f7fa;
}

.preview-content {
  min-height: 420px;
  padding: 22px;
  background: #f5f7fa;
  border: 0;
  border-radius: 0;
  align-items: flex-start;
}

.preview-footer {
  position: sticky;
  bottom: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 16px;
  background: rgba(255, 255, 255, .94);
  border-top: 1px solid var(--color-border);
  backdrop-filter: blur(10px);
}

.preview-footer > span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.preview-footer > div {
  display: flex;
  gap: 8px;
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

@keyframes blueprint-node-pulse {
  0%, 100% { opacity: .55; }
  50% { opacity: 1; box-shadow: 0 0 0 5px rgba(96,165,250,.1); }
}

@keyframes diagram-progress-scan {
  from { transform: translateX(-110%); }
  to { transform: translateX(300%); }
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

</style>
