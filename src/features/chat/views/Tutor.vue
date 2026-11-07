<template>
  <div class="tutor-dashboard">
    <main class="dashboard-main">
      <!-- 左侧会话历史导航栏 -->
      <aside class="session-sidebar" :class="{ collapsed: sessionSidebarCollapsed }">
        <div class="sidebar-top-header">
          <div class="sidebar-brand" v-if="!sessionSidebarCollapsed">
            <span class="brand-seal">
              <ChatLineRound class="brand-icon" />
            </span>
            <span class="brand-text">Mentorly</span>
          </div>
          <button
            class="collapse-toggle-btn"
            @click="sessionSidebarCollapsed = !sessionSidebarCollapsed"
            :title="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
            :aria-label="sessionSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3.5" y="4" width="17" height="16" rx="3.5"></rect>
              <line x1="9" y1="4" x2="9" y2="20"></line>
            </svg>
          </button>
        </div>

        <div class="standard-sidebar-nav">
          <button
            type="button"
            :class="['nav-item', 'new-chat-btn', { active: !activeSessionId }]"
            @click="newSession"
            title="新建对话"
          >
            <EditPen class="nav-icon" />
            <span class="nav-text">新建对话</span>
          </button>

          <PopoverRoot v-model:open="searchPopoverVisible">
            <PopoverTrigger as="button" type="button" class="nav-item search-item" title="搜索历史对话">
              <Search class="nav-icon" />
              <span class="nav-text">搜索对话</span>
            </PopoverTrigger>

            <PopoverPortal>
              <PopoverContent
                class="popover-content-container search-popover-content"
                side="right"
                align="start"
                :side-offset="10"
              >
                <div class="popover-search-container">
                  <div class="search-input-wrapper">
                    <Search class="search-input-icon" />
                    <input
                      v-model="searchKeyword"
                      type="text"
                      placeholder="输入关键词搜索对话..."
                      class="input-control search-input"
                    />
                    <button v-if="searchKeyword" type="button" class="search-clear-btn" @click="searchKeyword = ''">×</button>
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
                        <span class="session-title">{{ s.title || '新对话' }}</span>
                        <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                      </div>
                    </div>

                    <div v-if="filteredSessions.length === 0" class="session-empty nav-text">
                      未找到匹配的对话记录
                    </div>
                  </div>
                </div>
              </PopoverContent>
            </PopoverPortal>
          </PopoverRoot>

          <!-- 折叠态下的历史记录弹窗入口 -->
          <PopoverRoot v-model:open="historyPopoverVisible">
            <PopoverTrigger
              v-if="sessionSidebarCollapsed"
              as="button"
              type="button"
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
                :side-offset="10"
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
                    v-for="s in sessions"
                    :key="s.id"
                    :class="['nav-item', 'session-item', { active: s.id === activeSessionId }]"
                    :title="s.title || '新对话'"
                    :aria-current="s.id === activeSessionId ? 'true' : undefined"
                    @click="switchSession(s.id); historyPopoverVisible = false"
                  >
                    <ChatLineSquare class="session-icon" />
                    <div class="session-info nav-text">
                      <span class="session-title-line">
                        <span class="session-title">{{ s.title || '新对话' }}</span>
                        <span v-if="s.id === activeSessionId" class="current-session-indicator">当前</span>
                      </span>
                      <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                    </div>
                    <button
                      type="button"
                      class="btn-link del-btn nav-text"
                      aria-label="删除对话"
                      title="删除对话"
                      @click.stop="historyPopoverVisible = false; archiveSession(s.id)"
                    >
                      <Delete class="del-icon" />
                    </button>
                  </div>
                  <div v-if="sessions.length === 0" class="session-empty nav-text">暂无对话记录</div>
                </div>
              </PopoverContent>
            </PopoverPortal>
          </PopoverRoot>
        </div>

        <!-- 展开态：按时间分组的历史会话列表 -->
        <div class="session-list" v-show="!sessionSidebarCollapsed">
          <template v-if="groupedSessions.length > 0">
            <div
              v-for="group in groupedSessions"
              :key="group.label"
              class="session-group"
            >
              <div class="session-group-label">{{ group.label }}</div>
              <div
                v-for="s in group.items"
                :key="s.id"
                :class="['nav-item', 'session-item', { active: s.id === activeSessionId }]"
                :title="s.title || '新对话'"
                @click="switchSession(s.id)"
              >
                <ChatLineSquare class="session-icon" />
                <div class="session-info nav-text">
                  <span class="session-title">{{ s.title || '新对话' }}</span>
                  <span class="session-time">{{ formatRelativeTime(s.updated_at) }}</span>
                </div>
                <button
                  type="button"
                  class="btn-link del-btn nav-text"
                  title="删除对话"
                  aria-label="删除对话"
                  @click.stop="archiveSession(s.id)"
                >
                  <Delete class="del-icon" />
                </button>
              </div>
            </div>
          </template>
          <div v-else class="session-empty nav-text">
            暂无历史对话，开始你的第一次提问吧
          </div>
        </div>
      </aside>

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
                v-if="uploadingFile && !streamingMsgId"
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
                      <strong>正在安全上传并解析附件</strong>
                      <span>上传完成后将自动启动智能体分析链路，请稍候...</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 消息列表 -->
              <template v-for="msg in messages" :key="msg.id">
                <article
                  v-if="
                    msg.role === 'user'
                    || getDisplayContent(msg)
                    || msg.attachments?.length
                    || msg.run
                    || msg.failed
                  "
                  :class="['message-turn', msg.role, { 'is-streaming': isStreamingMessage(msg) }]"
                  @click="handleMessageClick"
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
                        v-if="getDisplayContent(msg)"
                        class="user-capsule-bubble"
                      >
                        <div class="user-plain-text">{{ getDisplayContent(msg) }}</div>
                      </div>

                      <!-- 用户消息底部元信息与快捷复制 -->
                      <div class="user-turn-meta">
                        <span class="turn-time">{{ msg.time }}</span>
                        <button
                          v-if="getDisplayContent(msg)"
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
                          正在回答
                        </span>
                      </header>

                      <div class="ai-canvas-body">
                        <!-- 1. 思考过程卡片（流光呼吸，思考完成自动折叠为胶囊） -->
                        <ChatThinkingBlock v-if="msg.run" :run="msg.run" />

                        <!-- 2. 工具调用行动卡片（独立行动凭证，按执行链展示） -->
                        <ChatToolBlock v-if="msg.run" :run="msg.run" />

                        <!-- 3. 回答正文（开放手稿画布，Append-Only 平滑追加，光标精准跟随） -->
                        <div
                          v-if="Boolean(getDisplayContent(msg)) || isStreamingMessage(msg)"
                          class="ai-manuscript-content"
                        >
                          <TutorMessageContent
                            :content="getDisplayContent(msg)"
                            :is-streaming="isStreamingMessage(msg)"
                          />
                        </div>

                        <!-- 4. 多模态生成产物与知识库来源（位于回答正文末尾呈现） -->
                        <ChatArtifactsShowcase v-if="msg.run" :run="msg.run" />

                        <!-- 3. 失败或超时专用错误卡片 -->
                        <div
                          v-if="msg.failed"
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
                              重新提问
                            </button>
                          </div>
                        </div>

                        <!-- 4. AI 回答底部操作栏 -->
                        <footer
                          v-if="getDisplayContent(msg) && !isStreamingMessage(msg)"
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
              <!-- 待发送附件预览轨 -->
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
                placeholder="输入问题，或粘贴图片/上传文档向 Mentorly 提问..."
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
                    :title="uploadingFile ? '正在上传附件' : '上传图片或文档附件'"
                  >
                    <Loading v-if="uploadingFile" class="tool-icon spinner" aria-hidden="true" />
                    <Paperclip v-else class="tool-icon" aria-hidden="true" />
                    <span>{{ uploadingFile ? '上传中' : '附件' }}</span>
                  </button>

                  <button
                    type="button"
                    class="input-tool-btn"
                    :class="{ 'is-active-teal': needTeachingDiagram }"
                    @click="handleTeachingDiagramToggle"
                    :aria-pressed="needTeachingDiagram"
                    title="开启后将为您生成结构化教学图解"
                  >
                    <DataLine class="tool-icon" aria-hidden="true" />
                    <span>图解</span>
                    <i v-if="needTeachingDiagram" class="active-check" aria-hidden="true">✓</i>
                  </button>

                  <button
                    type="button"
                    class="input-tool-btn"
                    :class="{ 'is-active-purple': needVideo }"
                    @click="handleVideoToggle"
                    :aria-pressed="needVideo"
                    title="开启后将调用动画智能体生成教学讲解视频"
                  >
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" class="tool-icon" aria-hidden="true">
                      <rect x="2.5" y="5" width="11" height="10" rx="1.5" />
                      <path d="m13.5 8 4-2.5v9l-4-2.5z" />
                    </svg>
                    <span>视频</span>
                    <i v-if="needVideo" class="active-check" aria-hidden="true">✓</i>
                  </button>
                </div>

                <div class="action-right">
                  <button
                    v-if="isResponding"
                    type="button"
                    class="stop-gen-btn"
                    @click="stopGeneration"
                  >
                    <span class="stop-square" aria-hidden="true"></span>
                    <span>停止生成</span>
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
                    :title="isResponding ? 'AI 正在回答，请稍候' : (canSendMessage ? '发送消息 (Enter)' : '请输入内容')"
                  >
                    <Loading v-if="isResponding" class="responding-spinner spinner" aria-hidden="true" />
                    <svg v-else viewBox="0 0 20 20" fill="none" aria-hidden="true" class="send-arrow-svg">
                      <path d="M10 15.5V4.5M5.2 9.2 10 4.4l4.8 4.8" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </button>
                </div>
              </div>
            </form>
            <div class="input-footer">
              <span>Enter 发送 · Shift + Enter 换行</span>
              <span>内容由多智能体协同生成，请结合教材核对关键结论</span>
            </div>
          </div>
        </div>

        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.log,.png,.jpg,.jpeg,.gif,.webp"
          style="display:none"
          @change="onCombinedFileSelected"
        />
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
  PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent
} from 'reka-ui'
import {
  PhChatCenteredText as ChatLineRound,
  PhHeadset as Service,
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
import ChatThinkingBlock from '@/features/chat/components/ChatThinkingBlock.vue'
import ChatToolBlock from '@/features/chat/components/ChatToolBlock.vue'
import ChatArtifactsShowcase from '@/features/chat/components/ChatArtifactsShowcase.vue'

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

const userInput = ref('')
const isAIThinking = ref(false)
const chatScroll = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const messageFormRef = ref<HTMLFormElement | null>(null)
const isExpandedInput = ref(false)
const isComposing = ref(false)
const showScrollToBottom = ref(false)
const copiedMsgId = ref<number | null>(null)
let copiedResetTimer: ReturnType<typeof setTimeout> | null = null

const needTeachingDiagram = ref(false)
const needVideo = ref(false)

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
  if (item.mode === 'diagram') {
    needTeachingDiagram.value = true
    needVideo.value = false
  } else if (item.mode === 'video') {
    needVideo.value = true
    needTeachingDiagram.value = false
  }
  nextTick(() => {
    autoResize()
    textareaRef.value?.focus()
  })
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

const uploadingFile = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const pendingFiles = ref<PendingFile[]>([])
const inputToolStateKey = computed(() => getInputToolStateKey({
  uploadingFile: uploadingFile.value,
  needTeachingDiagram: needTeachingDiagram.value,
  needVideo: needVideo.value,
}))

// 会话列表与分组
const sessions = ref<ChatSession[]>([])
const currentSessionId = ref<string | undefined>(undefined)
const activeSessionId = computed(() => currentSessionId.value)
const sessionSidebarCollapsed = ref(false)
const searchPopoverVisible = ref(false)
const historyPopoverVisible = ref(false)
const searchKeyword = ref('')

const groupedSessions = computed(() => {
  if (!sessions.value.length) return []

  const nowDate = new Date()
  const todayStart = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate()).getTime()
  const yesterdayStart = todayStart - 24 * 60 * 60 * 1000
  const weekStart = todayStart - 7 * 24 * 60 * 60 * 1000

  const buckets: Record<'today' | 'yesterday' | 'week' | 'older', ChatSession[]> = {
    today: [],
    yesterday: [],
    week: [],
    older: [],
  }

  for (const s of sessions.value) {
    const ts = s.updated_at ? new Date(s.updated_at).getTime() : 0
    if (ts >= todayStart) {
      buckets.today.push(s)
    } else if (ts >= yesterdayStart) {
      buckets.yesterday.push(s)
    } else if (ts >= weekStart) {
      buckets.week.push(s)
    } else {
      buckets.older.push(s)
    }
  }

  const groups: Array<{ label: string; items: ChatSession[] }> = []
  if (buckets.today.length) groups.push({ label: '今天', items: buckets.today })
  if (buckets.yesterday.length) groups.push({ label: '昨天', items: buckets.yesterday })
  if (buckets.week.length) groups.push({ label: '最近 7 天', items: buckets.week })
  if (buckets.older.length) groups.push({ label: '更早', items: buckets.older })
  return groups
})

const messages = ref<ChatMsg[]>([])
const streamingMsgId = ref<number | null>(null)

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
const STREAM_AUTO_SCROLL_BOTTOM_GAP_PX = 120

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

const filteredSessions = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return []
  return sessions.value.filter(s => {
    const title = s.title || '新对话'
    return title.toLowerCase().includes(keyword)
  })
})

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
  const content = getDisplayContent(msg).trim()
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

const handleMessageClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (target && target.classList.contains('copy-code-btn')) {
    const code = target.dataset.code
    if (code != null) {
      void copyToClipboard(code)
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
  chatRun.close()
  streamingMsgId.value = null
  isAIThinking.value = false
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

let sessionSwitchToken = 0

const switchSession = async (sessionId: string) => {
  const switchToken = ++sessionSwitchToken
  chatRun.close()
  currentSessionId.value = sessionId
  messages.value = []
  isAIThinking.value = false
  streamingMsgId.value = null
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
    if (textareaRef.value) textareaRef.value.style.height = '28px'
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
      failed: true,
      errorMessage: getErrorMessage(error, '附件上传失败，请检查文件后重试。'),
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

const handleRetryAssistantMessage = (targetMsg: ChatMsg) => {
  if (isAIThinking.value) return
  const msgIdx = messages.value.findIndex(m => m.id === targetMsg.id)
  let retryText = ''
  if (msgIdx > 0) {
    const prevUserMsg = messages.value.slice(0, msgIdx).reverse().find(m => m.role === 'user')
    if (prevUserMsg) {
      retryText = prevUserMsg.content
      messages.value = messages.value.filter(m => m.id !== targetMsg.id && m.id !== prevUserMsg.id)
    }
  }
  if (!retryText) {
    messages.value = messages.value.filter(m => m.id !== targetMsg.id)
    toast.error('未找到可重试的提问内容')
    return
  }
  userInput.value = retryText
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
  chatRun.close()
})

onBeforeUnmount(() => {
  chatRun.close()
  clearPendingFiles()
  if (copiedResetTimer) clearTimeout(copiedResetTimer)
})
</script>

<style scoped>
/* ============================================================
   1. 整体页面骨架与左侧会话导航栏 (Glacier Teal Studio)
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

.session-sidebar {
  position: relative;
  width: 256px;
  background: var(--color-bg);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-top-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 12px 10px 16px;
  height: 58px;
  box-sizing: border-box;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--color-text-strong);
  font-weight: 700;
  font-size: 0.98rem;
  letter-spacing: -0.01em;
}

.brand-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  color: var(--color-primary-text);
}

.brand-icon {
  width: 17px;
  height: 17px;
}

.collapse-toggle-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background-color 150ms ease, color 150ms ease;
  width: 34px;
  height: 34px;
  padding: 0;
}

.collapse-toggle-btn:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.collapse-toggle-btn svg {
  width: 18px;
  height: 18px;
}

.standard-sidebar-nav {
  padding: 4px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.nav-item {
  width: 100%;
  height: auto;
  min-height: 38px;
  background: transparent;
  border: 1px solid transparent;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 150ms ease;
  color: var(--color-text-secondary);
  text-align: left;
}

.nav-item:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.nav-item.new-chat-btn {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-text-strong);
  font-weight: 600;
  box-shadow: var(--shadow-xs);
}

.nav-item.new-chat-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-surface-hover);
}

.nav-icon {
  width: 17px;
  height: 17px;
  flex-shrink: 0;
  color: var(--color-primary-text);
}

/* 会话分组列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.session-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-group-label {
  padding: 4px 10px 4px;
  font-size: 11px;
  font-weight: 650;
  color: var(--color-text-faint);
  letter-spacing: 0.02em;
  user-select: none;
}

.session-item {
  min-height: 44px;
  padding: 7px 10px;
  border-radius: 9px;
  color: var(--color-text-secondary);
}

.session-item:hover {
  background: var(--color-surface);
  border-color: var(--color-border-light);
  color: var(--color-text-strong);
}

.session-item.active {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
  color: var(--color-primary-text);
  font-weight: 600;
}

.session-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-faint);
  flex-shrink: 0;
  transition: color 150ms ease;
}

.session-item.active .session-icon {
  color: var(--color-primary-text);
}

.session-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
  min-width: 0;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.84rem;
  line-height: 1.35;
}

.session-time {
  font-size: 0.68rem;
  color: var(--color-text-faint);
  white-space: nowrap;
}

.session-item.active .session-time {
  color: var(--color-text-secondary);
}

.del-btn {
  opacity: 0;
  width: 26px;
  height: 26px;
  min-height: 26px;
  padding: 0;
  border-radius: 6px;
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 140ms ease, background-color 140ms ease, color 140ms ease;
}

.session-item:hover .del-btn,
.del-btn:focus-visible {
  opacity: 1;
}

.del-btn:hover {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.del-icon {
  width: 14px;
  height: 14px;
}

.session-empty {
  font-size: 0.8rem;
  color: var(--color-text-faint);
  text-align: center;
  padding: 28px 12px;
  line-height: 1.5;
}

/* 侧边栏折叠态 */
.session-sidebar.collapsed {
  width: 64px;
}

.session-sidebar.collapsed .nav-text,
.session-sidebar.collapsed .session-info {
  display: none;
}

.session-sidebar.collapsed .sidebar-top-header,
.session-sidebar.collapsed .standard-sidebar-nav {
  padding-left: 0;
  padding-right: 0;
  align-items: center;
}

.session-sidebar.collapsed .collapse-toggle-btn,
.session-sidebar.collapsed .nav-item {
  width: 40px !important;
  height: 40px !important;
  min-width: 40px !important;
  min-height: 40px !important;
  padding: 0;
  justify-content: center;
  border-radius: 10px;
}

/* 侧边栏弹出层 (Search & History Popover) */
:global(.search-popover-content),
:global(.history-popover-content) {
  width: min(320px, calc(100vw - 88px));
  max-height: min(500px, calc(100vh - 32px));
  padding: 12px;
  overflow: hidden;
  box-sizing: border-box;
  background-color: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  box-shadow: var(--shadow-md);
  outline: none;
  z-index: 1200;
}

.popover-search-container {
  display: flex;
  flex-direction: column;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  height: 36px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.search-input-icon {
  width: 15px;
  height: 15px;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.84rem;
  color: var(--color-text);
}

.search-clear-btn {
  width: 20px;
  height: 20px;
  min-height: 20px;
  padding: 0;
  background: transparent;
  color: var(--color-text-muted);
}

.popover-session-scroll {
  max-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.history-popover-header {
  display: flex;
  align-items: center;
  padding: 2px 4px 10px;
  border-bottom: 1px solid var(--color-border-light);
}

.history-popover-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.history-popover-icon {
  width: 30px;
  height: 30px;
  padding: 6px;
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  border-radius: 8px;
}

.popover-title {
  color: var(--color-text-strong);
  font-size: 0.9rem;
  font-weight: 700;
}

.history-popover-count {
  color: var(--color-text-faint);
  font-size: 0.72rem;
}

.session-title-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.current-session-indicator {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 0.65rem;
  font-weight: 650;
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

.minimal-input-panel {
  position: relative;
  z-index: 5;
  padding: 10px clamp(16px, 4vw, 48px) 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: linear-gradient(to top, var(--color-surface) 78%, rgba(252, 255, 255, 0));
}

.minimal-input-wrapper {
  width: 100%;
  max-width: 820px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow:
    0 2px 6px rgba(23, 59, 66, 0.03),
    0 10px 28px rgba(23, 59, 66, 0.06);
  transition: border-color 180ms ease, box-shadow 180ms ease;
}

.minimal-input-wrapper:hover {
  border-color: var(--color-border-hover);
}

.minimal-input-wrapper:focus-within {
  border-color: var(--color-primary);
  box-shadow:
    0 0 0 3px rgba(70, 184, 180, 0.14),
    0 12px 32px rgba(23, 59, 66, 0.08);
}

.minimal-input-wrapper.is-responding {
  background: var(--color-bg);
}

.minimal-input-wrapper textarea {
  width: 100%;
  min-height: 28px;
  max-height: 200px;
  padding: 2px 4px;
  border: none;
  background: transparent;
  resize: none;
  outline: none;
  font-family: inherit;
  font-size: 0.96rem;
  line-height: 1.58;
  color: var(--color-text-strong);
}

.minimal-input-wrapper textarea::placeholder {
  color: var(--color-text-faint);
}

.composer-attachments {
  display: flex;
  gap: 8px;
  width: 100%;
  padding: 0 2px 10px;
  overflow-x: auto;
  border-bottom: 1px solid var(--color-border-light);
}

.composer-attachment {
  position: relative;
  flex: 0 0 auto;
  overflow: hidden;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 10px;
}

.composer-attachment.is-image {
  width: 112px;
  height: 78px;
}

.composer-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.composer-image-name {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  overflow: hidden;
  padding: 14px 6px 4px;
  color: #ffffff;
  background: linear-gradient(transparent, rgba(23, 59, 66, 0.78));
  font-size: 9.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-attachment.is-file {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  width: 220px;
  min-height: 58px;
  padding: 8px 30px 8px 9px;
}

.remove-attachment-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  min-height: 20px;
  padding: 0;
  color: #ffffff;
  background: rgba(23, 59, 66, 0.65);
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.composer-attachment.is-file .remove-attachment-btn {
  color: var(--color-text-muted);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.minimal-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 34px;
}

.action-left,
.action-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.input-tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 30px;
  min-height: 30px;
  padding: 0 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 550;
  transition: all 150ms ease;
}

.input-tool-btn:hover:not(:disabled) {
  color: var(--color-text-strong);
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
}

.input-tool-btn.is-active-teal {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  font-weight: 650;
}

.input-tool-btn.is-active-purple {
  color: #6d28d9;
  background: var(--cat-eval-soft);
  border-color: #c4b5fd;
  font-weight: 650;
}

.tool-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.active-check {
  font-style: normal;
  font-size: 10.5px;
  margin-left: 1px;
}

.stop-gen-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--color-danger-soft);
  border: 1px solid #f8b4c0;
  color: var(--color-danger);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.stop-gen-btn:hover {
  background: #ffe4e9;
}

.stop-square {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: currentColor;
}

.minimal-send-btn {
  width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: 50%;
  background: var(--color-border-light);
  color: var(--color-text-faint);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  transition: all 160ms ease;
}

.minimal-send-btn.can-send {
  background: var(--color-text-strong);
  color: var(--color-surface);
  cursor: pointer;
}

.minimal-send-btn.can-send:hover {
  background: var(--color-primary-text);
  transform: translateY(-1px);
}

.send-arrow-svg {
  width: 16px;
  height: 16px;
}

.responding-spinner {
  width: 16px;
  height: 16px;
  animation: tutor-response-spin 0.8s linear infinite;
}

@keyframes tutor-response-spin {
  to { transform: rotate(360deg); }
}

@keyframes thinking-ring-turn {
  to { transform: rotate(360deg); }
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px 14px;
  width: 100%;
  max-width: 820px;
  margin-top: 7px;
  color: var(--color-text-faint);
  font-size: 11px;
}

.input-footer span + span::before {
  margin-right: 14px;
  color: var(--color-border);
  content: "·";
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

  .minimal-input-panel {
    padding: 8px 12px 10px;
  }

  .input-footer span:last-child {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .message-turn,
  .live-dot,
  .pill-live-dot,
  .thinking-core::before,
  .responding-spinner {
    animation: none;
  }
}
</style>
