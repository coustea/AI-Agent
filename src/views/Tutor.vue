<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { 
  Service, UserFilled, Loading, Picture, Microphone, 
  VideoPlay, Reading, Download, Opportunity, ChatDotSquare
} from '@element-plus/icons-vue'
import { marked } from 'marked'
import 'github-markdown-css/github-markdown-light.css'

const userInput = ref('')
const isAIThinking = ref(false)
const chatBody = ref<HTMLElement | null>(null)

const messages = ref([
  { 
    id: 1, 
    role: 'ai', 
    type: 'text', 
    content: '你好！我是你的 **AI 私人导师**。 👋\n\n你可以随时向我提问，我会结合你的个人画像提供：\n- **文字解析**：深度原理剖析\n- **多模态图解**：直观的逻辑演示\n- **针对性练习**：即时巩固薄弱点', 
    time: '14:20' 
  }
])

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  })
}

const simulateStreaming = async (text: string, multimodal?: any) => {
  let currentContent = ''
  const newMessage = reactive({ id: Date.now(), role: 'ai', type: 'text', content: '', time: '现在' })
  messages.value.push(newMessage)
  
  const words = text.split('')
  for (let i = 0; i < words.length; i++) {
    currentContent += words[i]
    newMessage.content = currentContent
    scrollToBottom()
    await new Promise(resolve => setTimeout(resolve, 20))
  }

  if (multimodal) {
    messages.value.push({
      id: Date.now() + 1,
      role: 'ai',
      type: 'card',
      content: multimodal,
      time: '现在'
    })
    scrollToBottom()
  }
}

const handleSend = async () => {
  if (!userInput.value.trim() || isAIThinking.value) return
  const text = userInput.value
  messages.value.push({ id: Date.now(), role: 'user', type: 'text', content: text, time: '刚刚' })
  userInput.value = ''
  isAIThinking.value = true
  scrollToBottom()

  setTimeout(async () => {
    isAIThinking.value = false
    const replyText = `针对你提出的关于 **${text}** 的疑问，我通过检索课程知识库并结合你的画像（视觉偏好型）为你生成了以下解答：\n\n1. **核心原理**：这是由于神经网络在反向传播过程中，梯度随着层数增加呈指数级衰减造成的。\n2. **解决建议**：尝试使用 ReLU 激活函数或引入残差连接 (Residual Connection)。`
    
    const multimodalCard = {
      title: '梯度消失现象动态演示',
      desc: '基于你的画像生成的 3D 梯度流动模型预览',
      type: 'video',
      preview: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400'
    }
    
    await simulateStreaming(replyText, multimodalCard)
  }, 1200)
}
</script>

<template>
  <div class="tutor-canvas">
    <div class="chat-interface">
      <!-- 聊天头部：智能优化标识 -->
      <div class="interface-header">
        <div class="ai-status">
          <el-icon class="pulse"><Opportunity /></el-icon>
          <span>多智能体协同答疑模式</span>
        </div>
        <div class="session-meta">SESSION_ID: 0x882A</div>
      </div>

      <div class="chat-body" ref="chatBody">
        <div v-for="msg in messages" :key="msg.id" :class="['msg-row', msg.role]">
          <el-avatar :size="36" :icon="msg.role === 'ai' ? Service : UserFilled" :class="['avatar', msg.role]" />
          
          <div v-if="msg.type === 'text'" class="bubble-container">
            <div class="bubble markdown-body" v-html="marked.parse(msg.content)"></div>
            <span class="time">{{ msg.time }}</span>
          </div>
          
          <!-- 多模态卡片展示 -->
          <div v-else-if="msg.type === 'card'" class="multimodal-card">
            <div class="card-cover" :style="{ backgroundImage: `url(${msg.content.preview})` }">
              <div class="play-overlay"><el-icon><VideoPlay /></el-icon></div>
            </div>
            <div class="card-info">
              <div class="card-tag">图解动画</div>
              <h4>{{ msg.content.title }}</h4>
              <p>{{ msg.content.desc }}</p>
              <div class="card-footer">
                <el-button type="primary" size="small" plain>全屏播放</el-button>
                <el-button type="info" size="small" link :icon="Download">保存</el-button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isAIThinking" class="msg-row ai">
          <el-avatar :size="36" :icon="Service" class="avatar ai" />
          <div class="thinking-bubble">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>AI 正在检索知识库并根据画像进行多模态拟合...</span>
          </div>
        </div>
      </div>

      <!-- 输入区域：现代化卡片样式 -->
      <div class="input-panel">
        <div class="tools-bar">
          <el-button link :icon="Picture">上传截图分析</el-button>
          <el-button link :icon="Microphone">语音提问</el-button>
          <el-divider direction="vertical" />
          <span class="hint">按 Ctrl + Enter 发送</span>
        </div>
        <div class="input-area">
          <textarea 
            v-model="userInput" 
            placeholder="描述您的疑问，AI 将实时为您生成多模态解答..." 
            @keyup.enter.ctrl="handleSend"
          ></textarea>
          <el-button type="primary" circle class="send-btn" @click="handleSend" :disabled="!userInput.trim()">
            <el-icon><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 右侧辅助栏：快捷操作 -->
    <div class="helper-sidebar">
      <div class="helper-card">
        <h3><el-icon><ChatDotSquare /></el-icon> 常见问题建议</h3>
        <div class="faq-list">
          <div class="faq-item">残差连接是如何工作的？</div>
          <div class="faq-item">Batch Norm 的数学推导</div>
          <div class="faq-item">如何处理过拟合问题？</div>
        </div>
      </div>
      <div class="ai-tip">
        <p><strong>智能优化：</strong> 鉴于您偏好“实战驱动”，系统已优先为您准备了代码 Debug 案例。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tutor-canvas { display: flex; height: calc(100vh - 160px); gap: 2rem; }

.chat-interface {
  flex: 1; background: #fff; border-radius: 32px; display: flex; flex-direction: column;
  overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.04);
}

.interface-header { padding: 1.25rem 2rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #F3F4F6; }
.ai-status { display: flex; align-items: center; gap: 0.75rem; font-size: 0.85rem; font-weight: 700; color: #4F46E5; }
.session-meta { font-family: 'JetBrains Mono'; font-size: 0.7rem; color: #94A3B8; }

.chat-body { flex: 1; padding: 2.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 2.5rem; background: #FCFDFE; }

.msg-row { display: flex; gap: 1rem; max-width: 85%; }
.msg-row.user { align-self: flex-end; flex-direction: row-reverse; }

.bubble-container { display: flex; flex-direction: column; gap: 6px; }
.bubble { padding: 1.25rem 1.5rem; border-radius: 20px; font-size: 0.95rem; line-height: 1.6; }
.ai .bubble { background: #fff; border: 1px solid #F3F4F6; color: #1F2937; border-top-left-radius: 4px; box-shadow: 0 10px 25px rgba(0,0,0,0.03); }
.user .bubble { background: #4F46E5; color: #fff; border-top-right-radius: 4px; }

.multimodal-card {
  width: 320px; background: #fff; border-radius: 20px; overflow: hidden;
  border: 1px solid #F3F4F6; box-shadow: 0 15px 35px rgba(0,0,0,0.05);
}
.card-cover { height: 160px; background-size: cover; background-position: center; position: relative; display: flex; align-items: center; justify-content: center; }
.play-overlay { width: 50px; height: 50px; background: rgba(255,255,255,0.9); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #4F46E5; }
.card-info { padding: 1.25rem; }
.card-tag { font-size: 0.65rem; font-weight: 800; color: #4F46E5; text-transform: uppercase; margin-bottom: 0.5rem; }
.card-info h4 { margin: 0 0 0.5rem 0; font-size: 1.05rem; }
.card-info p { font-size: 0.85rem; color: #6B7280; line-height: 1.5; margin-bottom: 1.25rem; }
.card-footer { display: flex; justify-content: space-between; }

.thinking-bubble { color: #94A3B8; font-size: 0.85rem; font-style: italic; display: flex; align-items: center; gap: 0.75rem; }

.input-panel { padding: 1.5rem 2rem 2rem; background: #fff; border-top: 1px solid #F3F4F6; }
.tools-bar { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
.hint { font-size: 0.75rem; color: #94A3B8; }
.input-area { background: #F9FAFB; border-radius: 20px; padding: 1rem; display: flex; align-items: flex-end; gap: 1rem; border: 1px solid #F3F4F6; }
.input-area textarea { flex: 1; background: transparent; border: none; outline: none; resize: none; font-size: 0.95rem; font-family: inherit; line-height: 1.5; color: #1F2937; }
.send-btn { width: 44px; height: 44px; flex-shrink: 0; background: #000 !important; border: none !important; }

.helper-sidebar { width: 300px; display: flex; flex-direction: column; gap: 1.5rem; }
.helper-card { background: #fff; border-radius: 24px; padding: 1.75rem; border: 1px solid rgba(0,0,0,0.04); box-shadow: 0 10px 30px rgba(0,0,0,0.02); }
.helper-card h3 { font-size: 1rem; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; }
.faq-list { display: flex; flex-direction: column; gap: 0.75rem; }
.faq-item { font-size: 0.85rem; padding: 0.75rem 1rem; background: #F9FAFB; border-radius: 12px; cursor: pointer; transition: all 0.2s; color: #4B5563; }
.faq-item:hover { background: #EEF2FF; color: #4F46E5; transform: translateX(5px); }

.ai-tip { background: #0F172A; color: #fff; border-radius: 24px; padding: 1.5rem; font-size: 0.85rem; line-height: 1.6; }
.ai-tip p { opacity: 0.9; }

.time { font-size: 0.7rem; color: #94A3B8; margin-top: 0.5rem; }
.user .time { text-align: right; }

.pulse { animation: pulse-anim 2s infinite; }
@keyframes pulse-anim { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.6; } 100% { transform: scale(1); opacity: 1; } }

:deep(.markdown-body) { font-size: 0.95rem !important; background: transparent !important; }
</style>
