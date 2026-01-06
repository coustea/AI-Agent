<template>
  <div class="app-layout">
    
    <aside class="sidebar" :class="{ 'collapsed': isCollapsed }">
      
      <div class="sidebar-header">
        
        <button class="btn-icon-square" @click="toggleSidebar" aria-label="Toggle Menu">
          <svg class="icon-svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
          </svg>
        </button>

        <button class="btn-create" @click="createNewChat" :title="isCollapsed ? 'Create New Conversation' : ''">
          <svg class="icon-svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
          </svg>
          <span class="btn-text" v-show="!isCollapsed">Create New Conversation</span>
        </button>

      </div>

      <div class="sidebar-list">
        <div class="section-label" v-show="!isCollapsed">Today</div>
        
        <div 
          v-for="(chat, index) in recentChats" 
          :key="index"
          class="chat-item" 
          :class="{ active: currentChatId === chat.id }"
          @click="selectChat(chat.id)"
          :title="isCollapsed ? chat.title : ''"
        >
          <svg class="icon-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
          </svg>
          <span class="chat-title" v-show="!isCollapsed">{{ chat.title }}</span>
        </div>

        <div class="section-label" v-show="!isCollapsed">Previous 7 Days</div>
        <div class="chat-item" :title="isCollapsed ? 'Vue3 Composition API' : ''">
          <svg class="icon-chat" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
          </svg>
          <span class="chat-title" v-show="!isCollapsed">Vue3 Composition API</span>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="user-profile" :title="isCollapsed ? 'User Name' : ''">
          <div class="avatar">U</div>
          <div class="user-info" v-show="!isCollapsed">
            <div class="username">User Name</div>
            <div class="user-plan">Pro Plan</div>
          </div>
        </div>
      </div>
    </aside>

    <main class="chat-main">
      <div class="messages-container" :class="{ 'has-messages': messages.length > 0 }" ref="messagesContainerRef">
        <template v-if="messages.length === 0">
          <div class="empty-state">
            <div class="logo-icon">🤖</div>
            <h2>How can I help you today?</h2>
          </div>
        </template>
        <template v-else>
          <div class="message-list">
            <div 
              v-for="msg in messages" 
              :key="msg.id" 
              class="message-row" 
              :class="msg.role === 'ai' ? 'message-ai' : 'message-user'"
            >
              <div class="message-side" v-if="msg.role === 'ai'">
                <div class="avatar ai">🤖</div>
              </div>
              <div class="message-bubble" :class="msg.role === 'ai' ? 'bubble-ai' : 'bubble-user'">
                <div class="message-content" v-if="msg.role === 'ai'" v-html="renderMarkdown(msg.content)"></div>
                <div class="message-content" v-else>{{ msg.content }}</div>
              </div>
              <div class="message-side" v-if="msg.role === 'user'">
                <div class="avatar user">U</div>
              </div>
            </div>
            <div ref="messagesEndRef"></div>
          </div>
        </template>
      </div>

      <div class="input-area-wrapper">
        <div class="input-box-container">
          <textarea 
            v-model="inputText"
            class="chat-textarea" 
            placeholder="Message AI Agent..."
            rows="1"
            ref="textareaRef"
            @input="autoResize"
            @keydown.enter.prevent="sendMessage"
          ></textarea>

          <button 
            class="btn-send" 
            :disabled="!inputText.trim()"
            @click="sendMessage"
          >
            <svg class="icon-send" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        <p class="disclaimer">
          AI can make mistakes. Please check important information.
        </p>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css'; // 使用 GitHub 风格，也可以换成 monokai 等

const md = new MarkdownIt({
  breaks: true, // 软换行转为 <br>
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
               hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
               '</code></pre>';
      } catch (__) {}
    }

    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>';
  }
});

const renderMarkdown = (content) => {
  return md.render(content);
};

const inputText = ref('');
const textareaRef = ref(null);
const currentChatId = ref(1);
const isCollapsed = ref(false);
const messagesEndRef = ref(null);
const messagesContainerRef = ref(null);

const recentChats = ref([
  { id: 1, title: 'AI Agent Platform Design' },
  { id: 2, title: 'Sidebar CSS Logic' },
  { id: 3, title: 'Javascript Arrays' }
]);

const messagesByChat = ref({
  1: [],
  2: [],
  3: []
});

const messages = computed(() => {
  return messagesByChat.value[currentChatId.value] || [];
});

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
};

const autoResize = () => {
  const textarea = textareaRef.value;
  if(!textarea) return;
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';
  if (textarea.scrollHeight > 200) {
    textarea.style.overflowY = 'auto';
  } else {
    textarea.style.overflowY = 'hidden';
  }
};

const sendMessage = () => {
  if (!inputText.value.trim()) return;
  const text = inputText.value.trim();
  const chatId = currentChatId.value;
  const msg = { id: Date.now(), role: 'user', content: text };
  if (!messagesByChat.value[chatId]) messagesByChat.value[chatId] = [];
  messagesByChat.value[chatId].push(msg);
  nextTick(scrollToEnd);
  inputText.value = '';
  if (textareaRef.value) textareaRef.value.style.height = 'auto';
  simulateAiReply(text);
};

const createNewChat = () => {
  const newId = Math.max(...recentChats.value.map(c => c.id)) + 1;
  recentChats.value.unshift({ id: newId, title: 'New Conversation' });
  messagesByChat.value[newId] = [];
  currentChatId.value = newId;
};

const selectChat = (id) => {
  currentChatId.value = id;
};

const scrollToEnd = () => {
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' });
  } else if (messagesContainerRef.value) {
    messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight;
  }
};

const simulateAiReply = (text) => {
  const chatId = currentChatId.value;
  const thinkingId = Date.now() + 1;
  if (!messagesByChat.value[chatId]) messagesByChat.value[chatId] = [];
  
  // 1. 创建 AI 消息占位（初始为空）
  const aiMsgId = Date.now() + 1;
  const aiMsg = { id: aiMsgId, role: 'ai', content: '' };
  messagesByChat.value[chatId].push(aiMsg);
  nextTick(scrollToEnd);

  // 2. 模拟流式输出内容
  const fullReply = `我已收到你的消息：“**${text}**”。\n\n这是一个 **Markdown** 格式的流式输出示例。\n\nGemini 的流式输出通常是逐字（Token）生成的，这样用户可以更快看到响应。\n\n你可以尝试发送代码：\n\`\`\`javascript\nconsole.log("Hello AI");\n\`\`\`\n\n或者列表：\n- 第一点\n- 第二点`;
  
  let currentIndex = 0;
  const streamInterval = setInterval(() => {
    if (currentIndex < fullReply.length) {
      // 每次追加 1-3 个字符模拟不均匀的网络延迟
      const chunk = fullReply.slice(currentIndex, currentIndex + Math.floor(Math.random() * 3) + 1);
      aiMsg.content += chunk;
      currentIndex += chunk.length;
      nextTick(scrollToEnd);
    } else {
      clearInterval(streamInterval);
    }
  }, 30); // 每 30ms 更新一次
};
</script>

<style scoped>
/* ================= 全局布局 ================= */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: #ffffff;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* ================= 左侧 Sidebar 样式 ================= */
.sidebar {
  width: 280px; 
  height: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background-color: #f9fafb; 
  border-right: 1px solid #e5e7eb;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 68px; 
}

/* --- 1. 顶部操作区 --- */
.sidebar-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start; /* 展开时左对齐 */
  padding: 1rem 0.8rem;
  gap: 1rem;
}

.sidebar.collapsed .sidebar-header {
  align-items: center; /* 收缩时居中 */
  padding: 1rem 0;
}

/* 纯图标按钮 (仅用于菜单汉堡按钮) */
.btn-icon-square {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.btn-icon-square:hover {
  background-color: #e5e7eb;
  color: #1f2937;
}

/* ================== 修改核心：新建对话按钮样式 ================== */
.btn-create {
  /* 基础样式 */
  height: 44px; /* 稍微高一点，更有点击感 */
  display: flex;
  align-items: center;
  
  /* 默认（展开）状态 */
  width: 100%; /* 占满宽度 */
  justify-content: flex-start; /* 内容左对齐 */
  padding: 0 0.8rem; /* 给内部留点呼吸空间 */
  gap: 0.75rem; /* 图标和文字的间距 */
  
  background-color: #ffffff; /* 白底，突出重要性 */
  border: 1px solid #e5e7eb; /* 浅灰边框 */
  border-radius: 0.5rem;
  color: #374151;
  font-size: 0.95rem;
  font-weight: 500;
  
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05); /* 轻微阴影 */
  white-space: nowrap; /* 防止文字换行 */
  overflow: hidden;    /* 防止收缩时文字溢出 */
}

/* 收缩状态下的 btn-create */
.sidebar.collapsed .btn-create {
  width: 40px;  /* 变回方形 */
  height: 40px;
  padding: 0;   /* 去掉内边距 */
  justify-content: center; /* 内容居中 */
  background-color: transparent; /* 收缩时变透明背景，保持简洁 */
  border-color: transparent;
  box-shadow: none;
}

/* 悬停效果 */
.btn-create:hover {
  border-color: #d1d5db;
  background-color: #f3f4f6;
  color: #111827;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.btn-text {
  transition: opacity 0.2s;
}

.icon-svg {
  width: 1.5rem;
  height: 1.5rem;
  flex-shrink: 0;
}

/* --- 2. 列表区 --- */
.sidebar-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.5rem 0.8rem;
}

.sidebar.collapsed .sidebar-list {
  padding: 0.5rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.section-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #9ca3af;
  margin: 1.25rem 0 0.5rem 0.5rem;
  white-space: nowrap;
}

.chat-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.75rem;
  margin-bottom: 0.25rem;
  border-radius: 0.5rem;
  cursor: pointer;
  color: #4b5563;
  transition: all 0.2s;
  height: 40px;
  width: 100%;
  box-sizing: border-box;
}

.sidebar.collapsed .chat-item {
  width: 40px;
  padding: 0;
  justify-content: center;
}

.chat-item:hover {
  background-color: #e5e7eb;
  color: #1f2937;
}

.chat-item.active {
  background-color: #eff6ff;
  color: #2563eb;
}

.chat-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.icon-chat { width: 1rem; height: 1rem; opacity: 0.7; flex-shrink: 0; }

/* --- 3. 底部用户区 --- */
.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #e5e7eb;
  height: 70px;
  box-sizing: border-box;
}

.sidebar.collapsed .sidebar-footer {
  padding: 1rem 0;
  display: flex;
  justify-content: center;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  width: 100%; 
}
.sidebar.collapsed .user-profile {
  justify-content: center;
  width: auto;
  padding: 0;
}

.user-profile:hover { background-color: #e5e7eb; }

.avatar {
  width: 2rem; height: 2rem;
  background-color: #3b82f6; color: white;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 0.9rem;
  flex-shrink: 0;
}
.user-info { display: flex; flex-direction: column; white-space: nowrap; overflow: hidden; }
.username { font-size: 0.875rem; font-weight: 500; color: #374151; }
.user-plan { font-size: 0.75rem; color: #6b7280; }

/* ================= 右侧 Main Content (保持不变) ================= */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: #ffffff;
}

.messages-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
  padding-bottom: 2rem;
}

.messages-container.has-messages {
  align-items: stretch;
  justify-content: flex-start;
}

.empty-state { text-align: center; color: #1f2937; }
.logo-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-state h2 { font-weight: 600; font-size: 1.5rem; }

.input-area-wrapper {
  width: 100%;
  max-width: 48rem;
  margin: 0 auto;
  padding: 0 1.5rem 2rem 1.5rem;
  flex-shrink: 0;
}

.input-box-container {
  position: relative;
  background-color: #f3f4f6; 
  border: 1px solid transparent;
  border-radius: 1.5rem;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
  transition: all 0.2s;
}

.input-box-container:focus-within {
  background-color: #ffffff;
  border-color: #d1d5db;
  box-shadow: 0 4px 12px -2px rgba(0,0,0,0.08);
}

.chat-textarea {
  width: 100%;
  max-height: 200px;
  padding: 1rem 3rem 1rem 1.25rem;
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 1rem;
  line-height: 1.5;
  color: #111827;
  resize: none;
  overflow-y: hidden;
}

.chat-textarea::placeholder { color: #9ca3af; }

.btn-send {
  position: absolute;
  bottom: 0.5rem;
  right: 0.5rem;
  width: 2rem; height: 2rem;
  background-color: #111827;
  color: white;
  border: none;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-send:disabled {
  background-color: #e5e7eb;
  color: #9ca3af;
  cursor: not-allowed;
}
.btn-send:not(:disabled):hover {
  background-color: #000000;
  transform: scale(1.05);
}

.icon-send { width: 1rem; height: 1rem; }

.disclaimer {
  text-align: center;
  font-size: 0.75rem;
  color: #9ca3af;
  margin-top: 0.75rem;
}

.message-list {
  width: 100%;
  max-width: 48rem;
  margin: 0 auto;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Gemini 风格对齐：AI 消息无气泡背景，图标置于左上方 */
.message-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.message-ai {
  flex-direction: row;
}

.message-user {
  justify-content: flex-end;
}

.message-side {
  display: flex;
  align-items: flex-start; /* 头像顶对齐 */
  padding-top: 0.2rem;
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.8rem;
  flex-shrink: 0;
}
.avatar.ai { 
  background: linear-gradient(135deg, #4285f4, #d96570); /* Gemini 渐变色 */
  color: #fff; 
}
.avatar.user { background-color: #e5e7eb; color: #374151; }

.message-bubble {
  max-width: 85%;
  border-radius: 12px;
  font-size: 1rem;
  line-height: 1.6;
  word-break: break-word;
}

/* AI 消息：无背景色，左对齐，宽度自适应 */
.bubble-ai {
  background-color: transparent;
  color: #1f2937;
  border: none;
  padding: 0; /* 去除内边距 */
  width: 100%;
}

/* 用户消息：深灰色胶囊背景，右对齐 */
.bubble-user {
  background-color: #f3f4f6;
  color: #1f2937;
  padding: 0.75rem 1.25rem;
  border-radius: 20px 20px 4px 20px; /* 右下角圆角特殊处理 */
}

.message-content {
  white-space: pre-wrap;
  font-size: 0.95rem;
  line-height: 1.6;
}

/* Markdown 样式增强 */
.message-content :deep(p) {
  margin: 0.5rem 0;
}
.message-content :deep(p:first-child) {
  margin-top: 0;
}
.message-content :deep(p:last-child) {
  margin-bottom: 0;
}
.message-content :deep(pre) {
  background-color: #2d2d2d;
  color: #ccc;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0.75rem 0;
}
.message-content :deep(code) {
  font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
  font-size: 0.85em;
  background-color: rgba(0,0,0,0.05);
  padding: 0.1rem 0.3rem;
  border-radius: 0.2rem;
}
.message-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: inherit;
}
.message-content :deep(ul), .message-content :deep(ol) {
  padding-left: 1.5rem;
  margin: 0.5rem 0;
}
.message-content :deep(li) {
  margin: 0.25rem 0;
}
.message-content :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}
.message-content :deep(blockquote) {
  border-left: 4px solid #e5e7eb;
  padding-left: 1rem;
  margin: 0.5rem 0;
  color: #6b7280;
}

/* 调整用户消息的 Markdown 颜色（如果有） */
.bubble-user .message-content :deep(code) {
  background-color: rgba(255,255,255,0.2);
  color: inherit;
}
.bubble-user .message-content :deep(a) {
  color: #93c5fd;
}
</style>
