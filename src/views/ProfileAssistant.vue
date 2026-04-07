<template>
  <div class="profile-dashboard">
    <div class="dashboard-grid">

      <section class="panel chat-panel">
        <div class="panel-header glass-header">
          <div class="header-title">
            <div class="icon-box indigo"><el-icon><Connection /></el-icon></div>
            <div>
              <h3>AI 画像建构引擎</h3>
              <p class="subtitle">自然交流中，AI 将自动捕捉您的学习特征</p>
            </div>
          </div>
          <div class="status-indicator">
            <span class="pulse-dot" :class="{ active: isThinking || isUpdatingProfile }"></span>
            <span class="status-text">{{ isUpdatingProfile ? '正在提取特征...' : (isThinking ? '模型思考中' : '监听就绪') }}</span>
          </div>
        </div>

        <div class="chat-viewport" ref="chatScroll">
          <div v-if="messages.length === 0" class="chat-empty">
            <div class="bot-illustration">
              <el-icon><ChatLineRound /></el-icon>
            </div>
            <h4>嗨！我是你的智能学习诊断师</h4>
            <p>你可以告诉我：你的专业是什么？最近在学什么？哪些知识点让你觉得吃力？</p>
            <div class="suggestion-chips">
              <span class="chip" @click="fillSuggest('我是计算机专业的学生，最近在学数据结构，总是搞不懂图的遍历。')">
                "我是计算机专业，最近在学数据结构..."
              </span>
              <span class="chip" @click="fillSuggest('我准备考研，但是英语阅读理解错很多，不知道是不是词汇量不够。')">
                "我准备考研，英语阅读错很多..."
              </span>
            </div>
          </div>

          <div v-for="(msg, idx) in messages" :key="idx" :class="['message-row', msg.role]">
            <div class="msg-avatar" v-if="msg.role === 'assistant'">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/></svg>
            </div>

            <div class="msg-bubble">
              <div v-if="msg.role === 'assistant' && msg.content === '' && isThinking" class="ai-thinking-state">
                <el-icon class="is-loading spin-icon"><Loading /></el-icon>
                <span>系统正在思考与重构知识结构...</span>
              </div>

              <div v-else-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>

              <div v-else class="user-message-text">{{ msg.content }}</div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <div class="input-container" :class="{ 'is-disabled': isThinking }">
            <textarea
                v-model="userInput"
                placeholder="发送消息给 AI，或者描述你目前的学习困惑..."
                :disabled="isThinking"
                @keydown.enter.exact.prevent="handleSubmit"
            ></textarea>

            <div class="input-actions">
              <button class="send-btn" :disabled="isThinking || !userInput.trim()" @click="handleSubmit()">
                <el-icon><Promotion /></el-icon>
              </button>
            </div>
          </div>
          <div class="input-footer">按 <strong>Enter</strong> 发送，<strong>Shift + Enter</strong> 换行</div>
        </div>
      </section>

      <section class="panel profile-data-panel">
        <div class="global-status-card" :class="{ 'is-updating': isUpdatingProfile }">
          <div class="bg-pattern"></div>
          <div class="status-content">
            <div class="status-header">
              <h2>全息学习画像 <span class="badge">LIVE</span></h2>
              <el-icon class="refresh-icon" :class="{'is-spinning': isUpdatingProfile}" @click="refreshProfile" style="cursor:pointer"><RefreshRight /></el-icon>
            </div>
            <p class="summary-text">{{ profileSummary }}</p>
          </div>
        </div>

        <div class="data-split">
          <div class="radar-container">
            <div class="section-title"><el-icon><Compass /></el-icon> 维度光谱分析</div>
            <div class="chart-wrapper">
              <div v-if="!hasProfileData" class="chart-placeholder">
                <el-icon class="icon-large"><Cpu /></el-icon>
                <span>数据采集中</span>
              </div>
              <v-chart v-else class="radar-chart" :option="radarOption" autoresize />
            </div>
          </div>

          <div class="features-container">
            <div class="section-title">特征切片矩阵</div>
            <div class="features-grid">
              <div v-if="extractedFeatures.length === 0" class="empty-features">
                <el-icon style="font-size: 2rem; margin-bottom: 0.5rem; color: #CBD5E1;"><Connection /></el-icon><br/>
                暂无足够数据，开始聊天以建立画像...
              </div>

              <div v-for="(feat, index) in extractedFeatures" :key="index" class="feature-card" :style="{ animationDelay: `${index * 0.1}s` }">
                <div class="fc-header">
                  <svg class="fc-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" :d="feat.icon" /></svg>
                  <span>{{ feat.label }}</span>
                </div>
                <div class="fc-body" :class="{ 'is-empty': !feat.value }">{{ feat.displayValue }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { Promotion, RefreshRight, Cpu, Compass, Connection, Loading, ChatLineRound } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { getProfile, getChatHistory, getProfileHistory } from '@/api/ai'
import type { ProfileHistoryItem, ProfileData, ChatMessageItem } from '@/api/ai'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'

use([CanvasRenderer, RadarChart, TooltipComponent, LegendComponent])

// ================= 状态管理 =================
const userInput = ref('')
const isThinking = ref(false)
const isUpdatingProfile = ref(false)
const chatScroll = ref<HTMLElement | null>(null)

const messages = ref<ChatMessageItem[]>([])
const currentProfile = ref<ProfileData | null>(null)
const profileHistory = ref<ProfileHistoryItem[]>([])

const dimensions = [
  { key: 'knowledge_level', label: '知识基础', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332-4.5 1.253' },
  { key: 'cognitive_style', label: '认知风格', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' },
  { key: 'error_pattern', label: '易错偏好', icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
  { key: 'learning_goal', label: '学习目标', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
  { key: 'learning_history', label: '学习历史', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  { key: 'interest_preference', label: '兴趣偏好', icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z' },
  { key: 'learning_pace', label: '学习节奏', icon: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' },
  { key: 'cognitive_level', label: '认知水平', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' }
]

onMounted(async () => {
  await fetchInitialData()
  scrollToBottom()
})

const fetchInitialData = async () => {
  try {
    const [profileRes, chatRes, historyRes] = await Promise.all([
      getProfile(), getChatHistory(50), getProfileHistory(10)
    ])
    if (profileRes.data.code === 200) currentProfile.value = profileRes.data.data
    if (chatRes.data.code === 200) messages.value = chatRes.data.data || []
    if (historyRes.data.code === 200) profileHistory.value = historyRes.data.data || []
  } catch (error) {
    ElMessage.error('无法拉取数据，请检查网络')
  }
}

const refreshProfile = async () => {
  isUpdatingProfile.value = true
  try {
    const [profileRes, historyRes] = await Promise.all([getProfile(), getProfileHistory(10)])
    if (profileRes.data.code === 200 && profileRes.data.data) currentProfile.value = profileRes.data.data
    if (historyRes.data.code === 200) profileHistory.value = historyRes.data.data || []
  } finally {
    isUpdatingProfile.value = false
  }
}

const hasProfileData = computed(() => !!currentProfile.value && dimensions.some(d => currentProfile.value![d.key as keyof ProfileData]))
const profileSummary = computed(() => currentProfile.value?.profile_summary || '系统正在等待足够的对话数据，以构建您的个性化全息学习画像...')

const radarOption = computed(() => {
  const p = (currentProfile.value || {}) as Partial<ProfileData>
  const getScore = (textVal: string | null | undefined, scoreVal: number | null | undefined) => {
    if (scoreVal != null) return scoreVal
    return textVal ? 40 : 10
  }
  return {
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '知识基础', max: 100 }, { name: '认知风格', max: 100 }, { name: '易错偏好', max: 100 },
        { name: '学习目标', max: 100 }, { name: '学习历史', max: 100 }, { name: '兴趣偏好', max: 100 },
        { name: '学习节奏', max: 100 }, { name: '认知水平', max: 100 }
      ],
      shape: 'circle', splitNumber: 5,
      axisName: { color: '#312E81', fontSize: 12, fontWeight: 600, fontFamily: 'monospace' },
      splitLine: { lineStyle: { color: ['#EEF2FF', '#E0E7FF', '#C7D2FE', '#A5B4FC', '#818CF8'].reverse() } },
      splitArea: { show: true, areaStyle: { color: ['rgba(255,255,255,0.8)', 'rgba(238,242,255,0.5)'] } },
      axisLine: { lineStyle: { color: '#E0E7FF' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          getScore(p.knowledge_level, p.knowledge_level_score),
          getScore(p.cognitive_style, p.cognitive_style_score),
          getScore(p.error_pattern, p.error_pattern_score),
          getScore(p.learning_goal, p.learning_goal_score),
          getScore(p.learning_history, p.learning_history_score),
          getScore(p.interest_preference, p.interest_preference_score),
          getScore(p.learning_pace, p.learning_pace_score),
          getScore(p.cognitive_level, p.cognitive_level_score)
        ],
        name: '能力光谱', areaStyle: { color: 'rgba(79, 70, 229, 0.2)' }, lineStyle: { color: '#4F46E5', width: 2 },
        symbol: 'circle', symbolSize: 6, itemStyle: { color: '#4F46E5', borderColor: '#fff', borderWidth: 2 }
      }]
    }]
  }
})

// === 修改核心：始终保留 8 个维度并设置占位符 ===
const extractedFeatures = computed(() => {
  if (!currentProfile.value) return []

  // 保留原有逻辑：如果所有维度都为空，则返回空数组以触发“暂无足够数据”的占位大卡片
  const hasAnyData = dimensions.some(d => currentProfile.value![d.key as keyof ProfileData])
  if (!hasAnyData) return []

  // 映射所有 8 个维度，不存在的维度赋予一个 displayValue
  return dimensions.map(d => {
    const val = currentProfile.value![d.key as keyof ProfileData]
    return {
      ...d,
      value: val,
      displayValue: val || '数据采集中...'
    }
  })
})

// ================= 核心逻辑：流式对话 =================
const scrollToBottom = () => {
  nextTick(() => { if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight })
}

const renderMarkdown = (text: string) => {
  if (!text) return ''
  return marked.parse(text)
}

const handleSubmit = async (e?: KeyboardEvent) => {
  if (e && e.isComposing) return
  if (!userInput.value.trim() || isThinking.value) return

  const text = userInput.value.trim()
  userInput.value = ''

  isThinking.value = true

  messages.value.push({ role: 'user', content: text, created_at: new Date().toISOString() })
  scrollToBottom()

  const aiMessageIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '', created_at: new Date().toISOString() })
  scrollToBottom()

  try {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/ai/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ message: text })
    })

    if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`)
    if (!response.body) throw new Error("ReadableStream not supported.")

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let done = false

    while (!done) {
      const { value, done: readerDone } = await reader.read()
      done = readerDone
      if (value) {
        const chunk = decoder.decode(value, { stream: true })
        messages.value[aiMessageIndex].content += chunk
        scrollToBottom()
      }
    }

    isUpdatingProfile.value = true
    setTimeout(async () => { await refreshProfile() }, 1500)

  } catch (error) {
    ElMessage.error('对话发生网络异常')
    messages.value[aiMessageIndex].content = '⚠️ 网络异常，未能连接到智能核心，请稍后再试。'
  } finally {
    isThinking.value = false
    scrollToBottom()
  }
}

const fillSuggest = (text: string) => {
  userInput.value = text
  document.querySelector('textarea')?.focus()
}
</script>

<style scoped>
/* 全局与布局 */
.profile-dashboard {
  /* 使用浅灰蓝底层画布，配合 Layout */
  background-color: transparent;
  min-height: calc(100vh - 60px);
  padding: 1.5rem 2.5rem;
  max-width: 1800px;
  margin: 0 auto;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
.dashboard-grid {
  display: grid; grid-template-columns: 4fr 5fr; gap: 1.5rem;
  height: calc(100vh - 120px);
}
.panel {
  background: #FFFFFF; border-radius: 20px; border: 1px solid #E2E8F0;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03); display: flex; flex-direction: column; overflow: hidden;
}

/* 聊天面板头部 */
.chat-panel { position: relative; }
.panel-header {
  padding: 1.25rem 1.5rem; display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid #F1F5F9; background: #FFFFFF; z-index: 10;
}
.header-title { display: flex; align-items: center; gap: 1rem; }
.icon-box { width: 44px; height: 44px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
.icon-box.indigo { background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); color: #4F46E5; }
.header-title h3 { margin: 0 0 0.2rem 0; font-size: 1.15rem; color: #0F172A; font-weight: 800; letter-spacing: -0.02em; }
.header-title .subtitle { margin: 0; font-size: 0.85rem; color: #64748B; }

.status-indicator { display: flex; align-items: center; gap: 8px; background: #F8FAFC; padding: 6px 14px; border-radius: 20px; border: 1px solid #F1F5F9; }
.pulse-dot { width: 8px; height: 8px; background: #94A3B8; border-radius: 50%; transition: all 0.3s; }
.pulse-dot.active { background: #10B981; box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2); animation: pulse 1.5s infinite; }
.status-text { font-size: 0.75rem; color: #475569; font-weight: 600; font-family: monospace;}

/* 聊天流区域 */
.chat-viewport { flex: 1; padding: 2rem; overflow-y: auto; display: flex; flex-direction: column; gap: 2rem; background: #F8FAFC; scroll-behavior: smooth; }

/* 聊天气泡体系优化 */
.message-row { display: flex; gap: 1rem; align-items: flex-start; width: 100%; }
.message-row.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; background: linear-gradient(to bottom, #ffffff, #F1F5F9); color: #4F46E5;
  border: 1px solid #E2E8F0; box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-top: 2px;
}

.msg-bubble {
  max-width: 80%; padding: 1.1rem 1.4rem; border-radius: 20px; font-size: 1rem; line-height: 1.6;
}

.assistant .msg-bubble {
  background: white; color: #1E293B; border-top-left-radius: 4px;
  border: 1px solid #E2E8F0; box-shadow: 0 4px 15px rgba(0,0,0,0.03);
}

.user .msg-bubble {
  background: #4F46E5; color: white; border-bottom-right-radius: 4px;
  box-shadow: 0 4px 15px rgba(79, 70, 229, 0.2);
}

.user-message-text {
  white-space: pre-wrap; word-break: break-word; font-family: inherit; font-size: 0.95rem;
}

/* AI 思考动画 */
.ai-thinking-state { display: flex; align-items: center; gap: 10px; color: #64748B; font-size: 0.9rem; font-style: italic; }
.spin-icon { font-size: 1.2rem; color: #4F46E5; }
.is-loading { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

/* AI Markdown 样式 */
:deep(.markdown-body p) { margin-top: 0; margin-bottom: 0.8rem; }
:deep(.markdown-body p:last-child) { margin-bottom: 0; }
:deep(.markdown-body code) { background: #F1F5F9; padding: 3px 6px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.85em; color: #EF4444; }
:deep(.markdown-body pre) { background: #0F172A; color: #F8FAFC; padding: 1.2rem; border-radius: 12px; overflow-x: auto; margin: 1rem 0; font-size: 0.9em;}
:deep(.markdown-body pre code) { background: transparent; color: inherit; padding: 0; }
:deep(.markdown-body ul), :deep(.markdown-body ol) { padding-left: 1.5rem; margin: 0.5rem 0; }
:deep(.markdown-body li) { margin-bottom: 0.3rem; }

/* 现代化悬浮输入框 */
.chat-input-area {
  padding: 1.5rem 2.5rem 2rem; background: #F8FAFC;
  display: flex; flex-direction: column; gap: 10px;
}

.input-container {
  position: relative; display: flex; flex-direction: column;
  background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px;
  box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); transition: all 0.3s ease;
  padding: 14px 18px 50px 18px;
}
.input-container:focus-within {
  border-color: #4F46E5; box-shadow: 0 10px 30px rgba(79, 70, 229, 0.1);
}
.input-container.is-disabled { background: #F1F5F9; opacity: 0.8; }

.input-container textarea {
  width: 100%; border: none; background: transparent; outline: none; resize: none;
  font-size: 1rem; color: #0F172A; font-family: inherit; line-height: 1.6;
  min-height: 48px; max-height: 200px;
}
.input-container textarea::placeholder { color: #94A3B8; }

.input-actions { position: absolute; right: 12px; bottom: 12px; }

.send-btn {
  width: 42px; height: 42px; border-radius: 12px;
  background: #4F46E5; color: white; border: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem; cursor: pointer; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.send-btn:hover:not(:disabled) { background: #4338CA; transform: translateY(-2px); box-shadow: 0 6px 15px rgba(79, 70, 229, 0.3); }
.send-btn:disabled { background: #CBD5E1; cursor: not-allowed; transform: none; box-shadow: none;}

.input-footer { text-align: center; font-size: 0.75rem; color: #94A3B8; font-family: sans-serif; }
.input-footer strong { color: #64748B; font-weight: 600; }

/* 引导态空视图 */
.chat-empty { margin: auto; text-align: center; max-width: 80%; padding-bottom: 2rem;}
.bot-illustration { width: 80px; height: 80px; margin: 0 auto 1.5rem; background: white; border: 1px solid #E2E8F0; box-shadow: 0 10px 20px rgba(0,0,0,0.03); border-radius: 24px; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; color: #4F46E5;}
.chat-empty h4 { margin: 0 0 0.5rem; color: #0F172A; font-size: 1.3rem; font-weight: 800; letter-spacing: -0.02em;}
.chat-empty p { color: #64748B; font-size: 0.95rem; line-height: 1.6; margin-bottom: 2rem; }
.suggestion-chips { display: flex; flex-direction: column; gap: 0.75rem; }
.chip { background: white; border: 1px solid #E2E8F0; padding: 1.1rem 1.5rem; border-radius: 16px; font-size: 0.95rem; color: #475569; cursor: pointer; transition: all 0.2s ease; text-align: left; }
.chip:hover { border-color: #4F46E5; color: #4F46E5; transform: translateY(-2px); box-shadow: 0 6px 15px rgba(79,70,229,0.08); }

/* 右侧看板样式调整 */
.global-status-card { background: #0F172A; color: white; border-radius: 20px; padding: 2rem; position: relative; overflow: hidden; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.15); transition: all 0.5s ease; flex-shrink: 0;}
.global-status-card.is-updating { box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.3); }
.bg-pattern { position: absolute; inset: 0; opacity: 0.1; background-image: radial-gradient(#4F46E5 1px, transparent 1px); background-size: 20px 20px; }
.status-content { position: relative; z-index: 2; }
.status-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
.status-header h2 { margin: 0; font-size: 1.5rem; font-weight: 800; display: flex; align-items: center; gap: 0.75rem; }
.badge { background: rgba(16, 185, 129, 0.2); color: #34D399; font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.3); }
.refresh-icon { font-size: 1.5rem; color: #64748B; transition: all 0.3s; }
.refresh-icon.is-spinning { color: #34D399; animation: spin 1s linear infinite; }
.summary-text { margin: 0; font-size: 1.05rem; line-height: 1.6; color: #94A3B8; max-width: 90%; }

.data-split { display: flex; flex-direction: column; gap: 1.5rem; flex: 1; min-height: 0; padding: 1.5rem; }
.section-title { font-size: 0.95rem; font-weight: 700; color: #334155; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }
.radar-container { background: white; border-radius: 16px; padding: 1.5rem; border: 1px solid #E2E8F0; display: flex; flex-direction: column; }
.chart-wrapper { height: 280px; width: 100%; position: relative; }
.radar-chart { width: 100%; height: 100%; }
.chart-placeholder { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.5rem; color: #94A3B8; font-size: 0.9rem; }
.icon-large { font-size: 2rem; color: #CBD5E1; }

.features-container { background: white; border-radius: 16px; padding: 1.5rem; border: 1px solid #E2E8F0; flex: 1; overflow-y: auto; }
.features-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
.empty-features { grid-column: 1 / -1; padding: 3rem 0; text-align: center; color: #94A3B8; font-size: 0.95rem; border: 1px dashed #E2E8F0; border-radius: 16px; background: #F8FAFC;}
.feature-card { background: #F8FAFC; border: 1px solid #F1F5F9; border-radius: 16px; padding: 1.25rem; transition: all 0.3s ease; animation: slideUp 0.4s ease forwards; opacity: 0; transform: translateY(10px); cursor: pointer; }
.feature-card:hover { background: white; border-color: #C7D2FE; box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.1); transform: translateY(-2px); }
.fc-header { display: flex; align-items: center; gap: 6px; color: #64748B; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.75rem; }
.fc-icon { color: #818CF8; }
.fc-body { font-size: 0.95rem; color: #1E293B; line-height: 1.5; font-weight: 500; }

/* 缺省态的占位文本样式 */
.fc-body.is-empty {
  color: #94A3B8;
  font-style: italic;
  font-size: 0.85rem;
}

@keyframes pulse { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }
@keyframes slideUp { to { opacity: 1; transform: translateY(0); } }

@media (max-width: 1024px) { .dashboard-grid { grid-template-columns: 1fr; height: auto; } .chat-panel { height: 600px; } }
</style>