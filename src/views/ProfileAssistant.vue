<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import {
  Promotion, Loading, Aim, DataLine,
  Cpu, UserFilled, Opportunity, CollectionTag, Filter
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, RadarChart, LineChart, TooltipComponent, LegendComponent])

// ================= 状态管理 =================
const userInput = ref('')
const isThinking = ref(false)
const chatScroll = ref<HTMLElement | null>(null)
const extractingText = ref('')

// 6个维度基础得分
const profileScores = ref([65, 50, 40, 70, 55, 60])
const overallLevel = computed(() => {
  const avg = profileScores.value.reduce((a, b) => a + b, 0) / 6
  if (avg > 80) return '专家 (Lv.5)'
  if (avg > 65) return '熟练 (Lv.4)'
  if (avg > 50) return '进阶 (Lv.3)'
  return '入门 (Lv.2)'
})

// 分类特征矩阵 (展示抽取到的标签)
const featureMatrix = ref({
  knowledge: ['高等数学(弱)', '基础编程(中)'],
  cognitive: ['视觉敏感', '跳跃性思维'],
  preference: ['偏好实战', '厌恶长文本'],
})

// 演进日志
const updateLogs = ref<{time: string, changes: string[], context: string}[]>([
  { time: '10:00:12', changes: ['学习兴趣 +5%'], context: '初始探测' }
])

// 对话流
const messages = ref([
  {
    role: 'ai',
    content: '你好！我是你的专属 **AI 学习规划师**。系统正在初始化你的心智模型...\n\n为了更精准地为你推荐资源，请告诉我：**你目前对哪些技术栈最感兴趣？在学习理论时通常会遇到什么困难？**',
    extracted: [] as string[]
  }
])

// ================= 图表配置 =================
const radarOption = computed(() => ({
  radar: {
    indicator: [
      { name: '知识基础', max: 100 },
      { name: '认知风格', max: 100 },
      { name: '易错偏好', max: 100 },
      { name: '学习兴趣', max: 100 },
      { name: '学习效率', max: 100 },
      { name: '实践能力', max: 100 }
    ],
    shape: 'polygon',
    splitNumber: 4,
    axisName: { color: '#94A3B8', fontSize: 12, fontWeight: 700, fontFamily: 'JetBrains Mono' },
    splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    splitArea: { show: false }
  },
  series: [{
    type: 'radar',
    data: [{
      value: profileScores.value,
      areaStyle: { color: 'rgba(99, 102, 241, 0.3)' },
      lineStyle: { color: '#818CF8', width: 2 },
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: { color: '#818CF8', borderColor: '#fff', borderWidth: 2 }
    }]
  }]
}))

// ================= 核心逻辑 =================
const scrollToBottom = () => {
  nextTick(() => {
    if (chatScroll.value) {
      chatScroll.value.scrollTop = chatScroll.value.scrollHeight
    }
  })
}

const handleSubmit = () => {
  if (!userInput.value.trim() || isThinking.value) return

  const text = userInput.value
  messages.value.push({ role: 'user', content: text, extracted: [] })
  userInput.value = ''
  isThinking.value = true
  scrollToBottom()

  // 模拟 AI 处理与特征抽取管线
  extractingText.value = '正在进行语义拆解...'

  setTimeout(() => {
    extractingText.value = '正在匹配特征维度...'

    setTimeout(() => {
      // 1. 模拟特征抽取完成
      const newTag = text.length > 6 ? text.substring(0, 6) : text
      const mockDimIndex = Math.floor(Math.random() * 3) // 随机分配到矩阵
      if(mockDimIndex === 0) featureMatrix.value.knowledge.unshift(newTag)
      else if(mockDimIndex === 1) featureMatrix.value.cognitive.unshift(newTag)
      else featureMatrix.value.preference.unshift(newTag)

      // 2. 计算雷达图数值增长
      const changedIndices = [Math.floor(Math.random() * 6)]
      const newScores = [...profileScores.value]
      const changes: string[] = []

      changedIndices.forEach(idx => {
        const delta = Math.floor(Math.random() * 10) + 5 // 提升 5%~15%
        newScores[idx] = Math.min(100, newScores[idx] + delta)
        const dimName = radarOption.value.radar.indicator[idx].name
        changes.push(`${dimName} +${delta}%`)
      })

      // 3. 应用更新
      profileScores.value = newScores
      updateLogs.value.unshift({
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        changes: changes,
        context: `捕获特征: ${newTag}`
      })

      // 4. AI 响应
      messages.value.push({
        role: 'ai',
        content: `我已经捕获了你的反馈！根据你的描述，系统已为你打上 **[${newTag}]** 的标签，并自动上调了你的 **${changes[0].split(' ')[0]}** 预期值。\n\n接下来，面对长篇的代码文档，你更倾向于看文字解析，还是直接跑一遍源码？`,
        extracted: [newTag, ...changes]
      })

      isThinking.value = false
      scrollToBottom()
    }, 1200)
  }, 800)
}
</script>

<template>
  <div class="profile-dashboard">
    <!-- 头部：全局状态 -->
    <header class="dashboard-header">
      <div class="brand">
        <el-icon class="pulse-icon"><Aim /></el-icon>
        <h2>多维学习画像中枢</h2>
        <span class="mono-badge">AUTO_SYNC_ENABLED</span>
      </div>
      <div class="global-stats">
        <div class="stat"><span>评估模型:</span> <strong>LLM-Profile-v2</strong></div>
        <div class="stat"><span>综合评级:</span> <strong class="highlight">{{ overallLevel }}</strong></div>
      </div>
    </header>

    <div class="dashboard-grid">
      <!-- ================= 左侧：动态雷达图 ================= -->
      <section class="panel left-panel">
        <div class="panel-header">
          <el-icon><DataLine /></el-icon> 实时心智拓扑图
        </div>
        <div class="radar-container">
          <div class="radar-bg-glow"></div>
          <v-chart class="radar-chart" :option="radarOption" autoresize />
        </div>
        <div class="radar-footer">
          <p class="desc">雷达图正根据你的对话实时进行多维参数重塑。</p>
        </div>
      </section>

      <!-- ================= 中柱：神经对话流 ================= -->
      <section class="panel center-panel">
        <div class="panel-header border-b">
          <el-icon><Cpu /></el-icon> 对话式特征捕获引擎
        </div>

        <div class="chat-flow" ref="chatScroll">
          <div v-for="(msg, idx) in messages" :key="idx" :class="['chat-bubble-wrap', msg.role]">
            <div class="avatar"><el-icon><component :is="msg.role === 'ai' ? Cpu : UserFilled" /></el-icon></div>
            <div class="message-content">
              <!-- 内容区 -->
              <div class="bubble">
                {{ msg.content }}
              </div>
              <!-- AI 特征提取结果标签 -->
              <div class="extracted-tags" v-if="msg.extracted && msg.extracted.length > 0">
                <el-icon><Opportunity /></el-icon> 提取到参数:
                <span v-for="tag in msg.extracted" :key="tag" class="e-tag">{{ tag }}</span>
              </div>
            </div>
          </div>

          <!-- 思考与抽取动画 -->
          <div class="chat-bubble-wrap ai" v-if="isThinking">
            <div class="avatar"><el-icon class="is-loading"><Loading /></el-icon></div>
            <div class="message-content">
              <div class="extracting-indicator">
                <span class="loader-bar"></span>
                {{ extractingText }}
              </div>
            </div>
          </div>
        </div>

        <div class="input-area">
          <div class="input-box">
            <textarea
              v-model="userInput"
              placeholder="自然表达你的学习状态，AI 会自动拆解并更新画像..."
              @keyup.enter.exact.prevent="handleSubmit"
            ></textarea>
            <el-button type="primary" class="send-btn" @click="handleSubmit">
              <el-icon><Promotion /></el-icon> 发送
            </el-button>
          </div>
        </div>
      </section>

      <!-- ================= 右侧：特征矩阵与演进日志 ================= -->
      <section class="panel right-panel">
        <div class="panel-header">
          <el-icon><Filter /></el-icon> 解析矩阵 & 演进链路
        </div>

        <div class="right-content-scroll">
          <!-- 特征矩阵 -->
          <div class="feature-matrix">
            <div class="matrix-group">
              <h5><el-icon><CollectionTag /></el-icon> 知识基础 (Knowledge)</h5>
              <div class="tags-container">
                <span v-for="tag in featureMatrix.knowledge" :key="tag" class="matrix-tag knowledge">{{ tag }}</span>
              </div>
            </div>
            <div class="matrix-group">
              <h5><el-icon><CollectionTag /></el-icon> 认知风格 (Cognitive)</h5>
              <div class="tags-container">
                <span v-for="tag in featureMatrix.cognitive" :key="tag" class="matrix-tag cognitive">{{ tag }}</span>
              </div>
            </div>
            <div class="matrix-group">
              <h5><el-icon><CollectionTag /></el-icon> 学习偏好 (Preference)</h5>
              <div class="tags-container">
                <span v-for="tag in featureMatrix.preference" :key="tag" class="matrix-tag preference">{{ tag }}</span>
              </div>
            </div>
          </div>

          <!-- 动态演进日志 -->
          <div class="evolution-timeline">
            <h5>随学随新记录 (Evolution Log)</h5>
            <transition-group name="list" tag="div" class="timeline">
              <div v-for="(log, idx) in updateLogs" :key="idx" class="timeline-item">
                <div class="tl-dot"></div>
                <div class="tl-content">
                  <span class="tl-time">{{ log.time }}</span>
                  <span class="tl-context">{{ log.context }}</span>
                  <div class="tl-changes">
                    <span v-for="c in log.changes" :key="c" class="tl-change-tag">{{ c }}</span>
                  </div>
                </div>
              </div>
            </transition-group>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.profile-dashboard {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-top: 1rem;
}

/* 头部样式 */
.dashboard-header {
  display: flex; justify-content: space-between; align-items: center;
  background: #0F172A; color: white; padding: 1.25rem 2rem; border-radius: 20px;
  box-shadow: 0 10px 30px rgba(15,23,42,0.1);
}
.brand { display: flex; align-items: center; gap: 1rem; }
.pulse-icon { color: #818CF8; font-size: 1.5rem; animation: pulse 2s infinite; }
.brand h2 { margin: 0; font-size: 1.25rem; font-weight: 800; letter-spacing: 0.05em; }
.mono-badge { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; background: rgba(129,140,248,0.2); color: #818CF8; padding: 4px 8px; border-radius: 6px; }

.global-stats { display: flex; gap: 2rem; }
.stat { font-size: 0.85rem; color: #94A3B8; display: flex; gap: 8px; align-items: center; }
.stat strong { color: white; font-family: 'JetBrains Mono'; font-size: 0.95rem; }
.stat .highlight { color: #10B981; }

/* 核心三栏 Grid */
.dashboard-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1.6fr 1.2fr;
  gap: 1.5rem;
  overflow: hidden;
}

/* 通用面板样式 */
.panel {
  background: white; border-radius: 24px; border: 1px solid rgba(0,0,0,0.04);
  box-shadow: 0 15px 35px rgba(0,0,0,0.03); display: flex; flex-direction: column;
  overflow: hidden;
}
.panel-header {
  padding: 1.25rem 1.5rem; font-weight: 800; font-size: 0.95rem; color: #1E293B;
  display: flex; align-items: center; gap: 0.5rem; background: #F8FAFC;
}
.panel-header.border-b { border-bottom: 1px solid #F1F5F9; }

/* 左侧：雷达图 */
.left-panel { background: #0F172A; border-color: #1E293B; }
.left-panel .panel-header { background: transparent; color: white; border-bottom: 1px solid rgba(255,255,255,0.05); }
.radar-container { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.radar-bg-glow { position: absolute; width: 300px; height: 300px; background: radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 60%); top: 50%; left: 50%; transform: translate(-50%, -50%); }
.radar-chart { width: 100%; height: 100%; min-height: 350px; z-index: 10; }
.radar-footer { padding: 1.5rem; text-align: center; }
.radar-footer .desc { font-size: 0.75rem; color: #64748B; margin: 0; }

/* 中间：对话流 */
.center-panel { display: flex; flex-direction: column; }
.chat-flow { flex: 1; padding: 1.5rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; background: #FCFDFE; }

.chat-bubble-wrap { display: flex; gap: 1rem; max-width: 90%; }
.chat-bubble-wrap.user { align-self: flex-end; flex-direction: row-reverse; }

.avatar { width: 36px; height: 36px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.2rem; }
.ai .avatar { background: #EEF2FF; color: #4F46E5; }
.user .avatar { background: #F1F5F9; color: #64748B; }

.message-content { display: flex; flex-direction: column; gap: 8px; }
.user .message-content { align-items: flex-end; }

.bubble { padding: 1rem 1.25rem; border-radius: 16px; font-size: 0.95rem; line-height: 1.6; white-space: pre-wrap; }
.ai .bubble { background: white; border: 1px solid #F1F5F9; color: #334155; border-top-left-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.02); }
.user .bubble { background: #4F46E5; color: white; border-top-right-radius: 4px; }

/* 抽取标签展示 */
.extracted-tags { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 0.75rem; color: #10B981; font-weight: 700; background: rgba(16,185,129,0.05); padding: 8px 12px; border-radius: 12px; border: 1px dashed rgba(16,185,129,0.3); }
.e-tag { background: #10B981; color: white; padding: 2px 8px; border-radius: 6px; }

/* 提取动画指示器 */
.extracting-indicator { display: flex; align-items: center; gap: 1rem; background: #F8FAFC; padding: 12px 16px; border-radius: 16px; font-size: 0.85rem; color: #64748B; border: 1px dashed #E2E8F0; }
.loader-bar { width: 60px; height: 4px; background: #E2E8F0; border-radius: 4px; overflow: hidden; position: relative; }
.loader-bar::after { content: ''; position: absolute; left: 0; top: 0; height: 100%; width: 50%; background: #4F46E5; animation: slide 1s infinite alternate ease-in-out; }
@keyframes slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(200%); } }

/* 输入区 */
.input-area { padding: 1.5rem; background: white; border-top: 1px solid #F1F5F9; }
.input-box { display: flex; gap: 1rem; background: #F8FAFC; padding: 8px 8px 8px 16px; border-radius: 20px; border: 1px solid #E2E8F0; transition: border-color 0.3s; }
.input-box:focus-within { border-color: #4F46E5; background: white; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); }
.input-box textarea { flex: 1; border: none; background: transparent; outline: none; resize: none; font-size: 0.95rem; font-family: inherit; line-height: 1.5; padding-top: 8px; }
.send-btn { border-radius: 14px !important; font-weight: 700; height: auto; }

/* 右侧：矩阵与日志 */
.right-content-scroll { flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 2rem; }

.feature-matrix { display: flex; flex-direction: column; gap: 1.5rem; }
.matrix-group h5 { margin: 0 0 0.75rem 0; font-size: 0.8rem; color: #64748B; display: flex; align-items: center; gap: 4px; }
.tags-container { display: flex; flex-wrap: wrap; gap: 8px; }
.matrix-tag { font-size: 0.75rem; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
.matrix-tag.knowledge { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
.matrix-tag.cognitive { background: #FAF5FF; color: #9333EA; border: 1px solid #E9D5FF; }
.matrix-tag.preference { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }

/* 演进时间轴 */
.evolution-timeline { border-top: 1px dashed #E2E8F0; padding-top: 1.5rem; }
.evolution-timeline h5 { margin: 0 0 1rem 0; font-size: 0.85rem; color: #0F172A; font-weight: 800; }

.timeline { display: flex; flex-direction: column; }
.timeline-item { display: flex; gap: 1rem; position: relative; padding-bottom: 1.5rem; }
.timeline-item::before { content: ''; position: absolute; left: 5px; top: 12px; bottom: 0; width: 2px; background: #F1F5F9; }
.timeline-item:last-child::before { display: none; }
.tl-dot { width: 12px; height: 12px; background: white; border: 3px solid #10B981; border-radius: 50%; position: relative; z-index: 2; margin-top: 2px; }

.tl-content { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.tl-time { font-family: 'JetBrains Mono'; font-size: 0.65rem; color: #94A3B8; }
.tl-context { font-size: 0.85rem; color: #334155; font-weight: 600; }
.tl-changes { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.tl-change-tag { font-family: 'JetBrains Mono'; font-size: 0.7rem; background: #ECFDF5; color: #059669; padding: 2px 8px; border-radius: 6px; font-weight: 700; border: 1px solid #A7F3D0; }

/* 列表动画 */
.list-enter-active, .list-leave-active { transition: all 0.5s ease; }
.list-enter-from { opacity: 0; transform: translateX(-20px); }
.list-leave-to { opacity: 0; transform: translateX(20px); }

@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(1.1); } }
</style>