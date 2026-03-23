<template>
  <div class="app-layout">
    
    <!-- 侧边栏 (保持不变) -->
    <aside class="sidebar" :class="{ 'collapsed': isCollapsed }">
      <div class="sidebar-header">
        <button class="btn-icon-square" @click="toggleSidebar" aria-label="Toggle Menu">
          <svg class="icon-svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
          </svg>
        </button>
        <button class="btn-create" @click="createNewChat" :title="isCollapsed ? '开启新对话' : ''">
          <svg class="icon-svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
          </svg>
          <span class="btn-text" v-show="!isCollapsed">开启新对话</span>
        </button>
      </div>

      <div class="sidebar-list">
        <div class="section-label" v-show="!isCollapsed">历史记录</div>
        <div 
          v-for="(chat, index) in recentChats" 
          :key="chat.id"
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
      </div>

      <div class="sidebar-footer">
        <div class="user-profile">
          <div class="avatar">U</div>
          <div class="user-info" v-show="!isCollapsed">
            <div class="username">开发者</div>
            <div class="user-plan">Pro版</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主聊天区域 -->
    <main class="chat-main">
      <div class="messages-container" :class="{ 'has-messages': messages.length > 0 }" ref="messagesContainerRef">
        <!-- 空状态 -->
        <template v-if="messages.length === 0">
          <div class="empty-state">
            <div class="logo-icon">🤖</div>
            <h2>有什么可以帮您的吗？</h2>
          </div>
        </template>
        
        <!-- 消息列表 -->
        <template v-else>
          <div class="message-list">
            <div 
              v-for="msg in messages" 
              :key="msg.id" 
              class="message-row" 
              :class="msg.role === 'ai' ? 'message-ai' : 'message-user'"
            >
              <!-- AI 头像 -->
              <div class="message-side" v-if="msg.role === 'ai'">
                <div class="avatar ai">🤖</div>
              </div>

              <!-- 消息气泡 -->
              <div class="message-bubble" :class="msg.role === 'ai' ? 'bubble-ai' : 'bubble-user'">
                
                <!-- 1. 思考中状态：仅在加载中且没有内容时显示 -->
                <div v-if="msg.role === 'ai' && msg.isLoading && !msg.content" class="thinking-state">
                  <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span class="thinking-text">AI 正在思考中...</span>
                </div>

                <!-- 2. AI 内容渲染 (有内容时显示) -->
                <div 
                  v-if="msg.role === 'ai' && msg.content"
                  class="message-content markdown-body" 
                  v-html="renderMarkdown(msg.content)"
                ></div>

                <!-- 3. 用户消息 (纯文本) -->
                <div class="message-content" v-else-if="msg.role === 'user'">{{ msg.content }}</div>
                
                <!-- 4. 打字机光标：有内容且正在加载时显示在末尾 -->
                <span v-if="msg.role === 'ai' && msg.isLoading && msg.content" class="cursor-blink">|</span>
              </div>

              <!-- 用户头像 -->
              <div class="message-side" v-if="msg.role === 'user'">
                <div class="avatar user">U</div>
              </div>
            </div>
            <!-- 滚动锚点 -->
            <div ref="messagesEndRef"></div>
          </div>
        </template>
      </div>

      <!-- 输入框区域 -->
      <div class="input-area-wrapper">
        <div class="input-box-container">
          <textarea 
            v-model="inputText"
            class="chat-textarea" 
            placeholder="给 AI 发送消息..."
            rows="1"
            ref="textareaRef"
            @input="autoResize"
            @keydown.enter.prevent="sendMessage"
            :disabled="isGenerating"
          ></textarea>

          <button 
            class="btn-send" 
            :disabled="!inputText.trim() || isGenerating"
            @click="sendMessage"
          >
            <svg class="icon-send" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
        <p class="disclaimer">
          AI 可能会产生错误信息，请核对重要事实。
        </p>
      </div>
    </main>

  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';

// --- Markdown 配置 ---
const md = new MarkdownIt({
  html: false, 
  breaks: true,
  linkify: true,
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
  if (!content) return ''; 
  return md.render(content);
};

// --- 状态管理 ---
const inputText = ref('');
const textareaRef = ref(null);
const currentChatId = ref(1);
const isCollapsed = ref(false);
const messagesEndRef = ref(null);
const isGenerating = ref(false); 

const recentChats = ref([
  { id: 1, title: '新对话' },
]);

const messagesByChat = ref({
  1: []
});

const messages = computed(() => {
  return messagesByChat.value[currentChatId.value] || [];
});

// --- UI 交互逻辑 ---
const toggleSidebar = () => { isCollapsed.value = !isCollapsed.value; };

const autoResize = () => {
  const textarea = textareaRef.value;
  if(!textarea) return;
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
  textarea.style.overflowY = textarea.scrollHeight > 200 ? 'auto' : 'hidden';
};

const scrollToEnd = () => {
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
};

const createNewChat = () => {
  const newId = Date.now();
  recentChats.value.unshift({ id: newId, title: '新对话' });
  messagesByChat.value[newId] = [];
  currentChatId.value = newId;
  if (window.innerWidth < 768) isCollapsed.value = true;
};

const selectChat = (id) => { currentChatId.value = id; };

// --- 核心发送与流式请求逻辑 ---
const sendMessage = async () => {
  const text = inputText.value.trim();
  if (!text || isGenerating.value) return;

  const chatId = currentChatId.value;
  if (!messagesByChat.value[chatId]) messagesByChat.value[chatId] = [];
  
  // 1. 添加用户消息
  messagesByChat.value[chatId].push({
    id: Date.now(),
    role: 'user',
    content: text
  });

  // 2. 清空输入框并重置高度
  inputText.value = '';
  if (textareaRef.value) textareaRef.value.style.height = 'auto';
  nextTick(scrollToEnd);

  // 3. 准备 AI 消息占位符 (isLoading: true, content: '')
  // 此时模板会渲染 "Thinking..." 状态
  const aiMsgId = Date.now() + 1;
  const aiMsg = { 
    id: aiMsgId, 
    role: 'ai', 
    content: '', 
    isLoading: true 
  };
  messagesByChat.value[chatId].push(aiMsg);
  
  isGenerating.value = true;
  await fetchAiReply(chatId, aiMsg);
};

const fetchAiReply = async (chatId, aiMsg) => {
  try {
    const history = messagesByChat.value[chatId]
      .filter(m => m.id !== aiMsg.id)
      .map(m => ({ role: m.role, content: m.content }));

    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history }),
    });

    if (!response.ok) {
      throw new Error(`服务请求失败: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = ''; 

    // --- 核心流式读取循环 ---
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // 1. 解码二进制流
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;
      
      // 2. 按照 SSE 协议的换行符分割
      const lines = buffer.split('\n');
      
      // 3. 保留最后一个可能不完整的部分在 buffer 中，等待下一次拼接
      buffer = lines.pop(); 

      // 4. 处理完整的行
      for (const line of lines) {
        const trimmed = line.trim();
        // 过滤掉空行和非 data 开头的行
        if (!trimmed || !trimmed.startsWith('data: ')) continue;
        
        const dataStr = trimmed.slice(6).trim(); // 去掉 "data: "
        
        if (dataStr === '[DONE]') {
          // 结束标志
          break;
        }

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.content) {
            // 只要 content 一更新，模板中的 v-if 判断就会自动切换：
            // !content -> content 为真 -> "Thinking" 消失 -> Markdown 渲染出现
            aiMsg.content += parsed.content;
            
            // 收到数据后立即滚动到底部，保证“流式”视觉体验
            nextTick(scrollToEnd);
          }
          if (parsed.error) {
            aiMsg.content += `\n[错误: ${parsed.error}]`;
          }
        } catch (e) {
          console.warn('JSON 解析失败，跳过该行:', line);
        }
      }
    }
  } catch (error) {
    console.error('Chat error:', error);
    aiMsg.content += `\n[网络错误: ${error.message}]`;
  } finally {
    aiMsg.isLoading = false;
    isGenerating.value = false;
    nextTick(scrollToEnd);
  }
};
</script>

<style scoped>
/* 保持原有的布局样式 */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  background-color: #ffffff;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.sidebar {
  width: 260px; 
  height: 100%;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background-color: #f9fafb; 
  border-right: 1px solid #e5e7eb;
  transition: width 0.3s ease;
}

.sidebar.collapsed { width: 60px; }

/* 头部 */
.sidebar-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 1rem 0.8rem;
  gap: 1rem;
}
.sidebar.collapsed .sidebar-header { align-items: center; padding: 1rem 0; }

.btn-icon-square {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: 6px;
  color: #6b7280; cursor: pointer;
}
.btn-icon-square:hover { background-color: #e5e7eb; color: #1f2937; }

.btn-create {
  width: 100%; height: 40px;
  display: flex; align-items: center; justify-content: flex-start;
  padding: 0 0.8rem; gap: 0.5rem;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
  color: #374151; cursor: pointer; transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.sidebar.collapsed .btn-create { width: 36px; padding: 0; justify-content: center; border-color: transparent; background: transparent; box-shadow: none; }
.btn-create:hover { border-color: #d1d5db; background-color: #f9fafb; }

.icon-svg { width: 1.25rem; height: 1.25rem; flex-shrink: 0; }

/* 列表 */
.sidebar-list { flex: 1; overflow-y: auto; padding: 0.5rem; }
.section-label { font-size: 0.75rem; color: #9ca3af; margin: 1rem 0 0.5rem 0.5rem; }

.chat-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem; margin-bottom: 2px;
  border-radius: 6px; cursor: pointer; color: #4b5563;
  height: 36px;
}
.chat-item:hover { background-color: #e5e7eb; color: #1f2937; }
.chat-item.active { background-color: #eff6ff; color: #2563eb; }
.chat-title { font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.icon-chat { width: 1rem; height: 1rem; }

/* 底部 */
.sidebar-footer { padding: 1rem; border-top: 1px solid #e5e7eb; }
.sidebar.collapsed .sidebar-footer { padding: 1rem 0; display: flex; justify-content: center; }
.user-profile { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: white; font-weight: 600; font-size: 0.85rem; flex-shrink: 0;
}
.avatar.ai { background: linear-gradient(135deg, #10a37f, #0d8a6a); }
.avatar.user { background: #8e8e93; }

/* 主区域 */
.chat-main { flex: 1; display: flex; flex-direction: column; position: relative; }
.messages-container { flex: 1; overflow-y: auto; padding-bottom: 2rem; display: flex; flex-direction: column; }
.messages-container.has-messages { padding-top: 2rem; }

.empty-state {
  margin: auto; text-align: center; color: #374151;
}
.logo-icon { font-size: 4rem; margin-bottom: 1rem; }

.message-list { width: 100%; max-width: 800px; margin: 0 auto; padding: 0 1rem; }

.message-row { display: flex; gap: 1rem; margin-bottom: 2rem; }
.message-ai { flex-direction: row; }
.message-user { justify-content: flex-end; }

.message-bubble {
  max-width: 85%;
  font-size: 1rem;
  line-height: 1.6;
}
.bubble-ai { width: 100%; padding-top: 4px; }
.bubble-user { 
  background-color: #f3f4f6; 
  padding: 0.6rem 1rem; 
  border-radius: 12px;
}

/* 输入框 */
.input-area-wrapper {
  width: 100%; max-width: 800px; margin: 0 auto; padding: 0 1rem 2rem 1rem;
}
.input-box-container {
  position: relative;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
  display: flex; flex-direction: column;
}
.input-box-container:focus-within { border-color: #3b82f6; ring: 2px solid #3b82f6; }

.chat-textarea {
  width: 100%; max-height: 200px; padding: 1rem 3rem 1rem 1rem;
  border: none; outline: none; resize: none; background: transparent;
  font-size: 1rem; line-height: 1.5; color: #1f2937;
}
.btn-send {
  position: absolute; bottom: 0.5rem; right: 0.5rem;
  width: 32px; height: 32px; border-radius: 6px;
  background: #1f2937; color: white; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.btn-send:disabled { background: #e5e7eb; cursor: not-allowed; }

.disclaimer { font-size: 0.75rem; color: #9ca3af; text-align: center; margin-top: 0.5rem; }

/* 思考中状态样式 */
.thinking-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  padding: 8px 0;
  font-size: 0.9rem;
}

.thinking-text {
  font-weight: 500;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* 思考中三点跳动动画 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 3px;
}
.typing-indicator span {
  width: 4px;
  height: 4px;
  background-color: #6b7280;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 打字机光标 */
.cursor-blink {
  display: inline-block;
  width: 6px; height: 18px;
  background: #000;
  animation: blink 1s step-end infinite;
  vertical-align: sub; /* 对齐文本基线 */
  margin-left: 2px;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* Markdown 样式微调 */
.message-content :deep(pre) {
  background: #2d2d2d; color: #fff; padding: 1rem; border-radius: 8px; overflow-x: auto;
}
.message-content :deep(p) { margin: 0.5rem 0; }
.message-content :deep(ul) { margin-left: 1.5rem; }
</style>