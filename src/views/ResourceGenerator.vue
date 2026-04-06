<template>
  <div class="studio-layout">
    
    <aside class="config-sidebar">
      <div class="sidebar-header">
        <el-icon class="brand-icon"><Operation /></el-icon>
        <h2>资源构造器</h2>
        <p>设定目标，AI自动结合你的底层画像生成资源</p>
      </div>

      <div class="form-wrapper">
        <div class="form-group">
          <label>当前学习课程 / 主题 <span>*</span></label>
          <input v-model="taskForm.course" type="text" placeholder="例如：计算机网络、微观经济学" />
        </div>

        <div class="form-group">
          <label>核心疑问 / 知识短板 <span>*</span></label>
          <textarea v-model="taskForm.gap" rows="3" placeholder="你目前卡在了哪里？例如：TCP三次握手为什么不是两次？"></textarea>
        </div>

        <div class="form-group">
          <label>本次学习目标</label>
          <div class="radio-grid">
            <div 
              v-for="opt in needOptions" :key="opt.value"
              class="radio-card"
              :class="{ 'is-active': taskForm.need === opt.value }"
              @click="taskForm.need = opt.value"
            >
              {{ opt.label.split(' ')[0] }}
              <small>{{ opt.label.split(' ')[1] }}</small>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>补充要求 (选填)</label>
          <input v-model="taskForm.extra" type="text" placeholder="例如：尽量用通俗的比喻，多一些图解..." />
        </div>
      </div>

      <div class="sidebar-footer">
        <button 
          class="generate-btn" 
          :disabled="isGenerating || !taskForm.course || !taskForm.gap"
          @click="startSynthesize"
        >
          <el-icon v-if="!isGenerating"><Cpu /></el-icon>
          <el-icon v-else class="is-loading"><Loading /></el-icon>
          {{ isGenerating ? '多智能体协同运算中...' : '开始合成专属学习包' }}
        </button>
      </div>
    </aside>

    <main class="workspace-canvas">
      
      <div v-if="generationStage === 'idle'" class="empty-state">
        <div class="empty-icon"><el-icon><DataBoard /></el-icon></div>
        <h3>等待任务参数</h3>
        <p>请在左侧填写你的学习情境，<br/>后端引擎将自动注入你的专属画像并调度多模态智能体。</p>
      </div>

      <div v-else-if="generationStage === 'working'" class="agent-workflow-view">
        <div class="progress-header">
          <h3><el-icon class="is-loading"><Loading /></el-icon> 正在构建多模态知识空间</h3>
          <span class="pct">{{ progress }}%</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" :style="{ width: `${progress}%` }"></div>
        </div>

        <div class="nodes-container">
          <div 
            v-for="(task, index) in agentTasks" :key="task.id"
            class="agent-node"
            :class="task.status"
          >
            <div class="node-line" v-if="index !== agentTasks.length - 1"></div>
            <div class="node-icon">
              <el-icon v-if="task.status === 'done'"><CircleCheck /></el-icon>
              <el-icon v-else-if="task.status === 'active'" class="is-loading"><Loading /></el-icon>
              <div v-else class="wait-dot"></div>
            </div>
            <div class="node-info">
              <h4>{{ task.role }}</h4>
              <p>{{ task.desc }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="generationStage === 'done'" class="result-matrix">
        <div class="matrix-header">
          <h2>针对「{{ taskForm.gap }}」的专属资源包</h2>
          <div class="tags">
            <span>{{ taskForm.course }}</span>
            <span>已融合底层个人画像</span>
          </div>
        </div>

        <div class="resource-grid">
          <div v-for="(res, idx) in generatedResources" :key="idx" :class="['r-card', `type-${res.type}`]">
            <div class="r-header">
              <div class="r-icon"><el-icon><component :is="res.icon" /></el-icon></div>
              <span class="r-type">{{ res.type.toUpperCase() }}</span>
            </div>
            <h3 class="r-title">{{ res.title }}</h3>
            
            <div class="r-body">
              <p v-if="res.type === 'doc'">{{ res.content }}</p>
              <pre v-if="res.type === 'code'"><code>{{ res.content }}</code></pre>
              <div v-if="res.type === 'mindmap'" class="img-preview" :style="{ backgroundImage: `url(${res.url})` }"></div>
              <p v-if="res.type === 'quiz' || res.type === 'media'" class="r-desc">{{ res.desc }}</p>
            </div>

            <div class="r-action" v-if="res.type !== 'doc' && res.type !== 'code'">
              <button class="action-btn">查看详情 / 开始</button>
            </div>
          </div>
        </div>
      </div>

    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import {
  DataBoard, Reading, Edit, VideoCamera, Document,
  Aim, Cpu, Operation, CircleCheck, Loading, PictureRounded
} from '@element-plus/icons-vue'

// ================= 1. 结构化表单：精准捕获动态缺失信息 =================
// 后端已有"专业、学习风格"等静态画像，前端只负责收集"当下"的动态需求
const taskForm = reactive({
  course: '',       // 课程内容 (例: 计算机网络)
  gap: '',          // 知识短板 (例: TCP三次握手为什么不是两次)
  need: 'review',   // 学习需求/目标
  extra: ''         // 补充描述
})

const needOptions = [
  { value: 'exam', label: '考前突击 (侧重考点与易错题)' },
  { value: 'review', label: '课后复习 (侧重知识梳理与图解)' },
  { value: 'deep', label: '深度探究 (侧重底层原理与拓展)' },
  { value: 'practice', label: '实践应用 (侧重代码或实操案例)' }
]

// ================= 2. 工作台状态与数据 =================
const isGenerating = ref(false)
const generationStage = ref<'idle' | 'working' | 'done'>('idle')
const progress = ref(0)

// 智能体任务链
const agentTasks = ref([
  { id: 1, role: '架构智能体', desc: '解析表单结构，制定5维生成策略', status: 'wait' },
  { id: 2, role: '理论专家 Agent', desc: '撰写核心知识点精讲文档', status: 'wait' },
  { id: 3, role: '逻辑视效 Agent', desc: '渲染知识拓扑与思维导图', status: 'wait' },
  { id: 4, role: '极客实操 Agent', desc: '构建代码示例与运行沙箱', status: 'wait' },
  { id: 5, role: '测评出题 Agent', desc: '针对短板动态生成特训题库', status: 'wait' },
  { id: 6, role: '多模态检索 Agent', desc: '匹配并生成教学动画/视频', status: 'wait' }
])

const generatedResources = ref<any[]>([])

// ================= 3. 核心流转逻辑 =================
const startSynthesize = () => {
  if (!taskForm.course || !taskForm.gap) return
  
  isGenerating.value = true
  generationStage.value = 'working'
  progress.value = 0
  generatedResources.value = []
  agentTasks.value.forEach(t => t.status = 'wait')

  // 模拟智能体序列化工作流
  let currentTask = 0
  const interval = setInterval(() => {
    if (currentTask < agentTasks.value.length) {
      if (currentTask > 0) agentTasks.value[currentTask - 1].status = 'done'
      agentTasks.value[currentTask].status = 'active'
      progress.value = Math.floor(((currentTask + 1) / agentTasks.value.length) * 100)
      currentTask++
    } else {
      clearInterval(interval)
      agentTasks.value[agentTasks.value.length - 1].status = 'done'
      setTimeout(() => {
        generationStage.value = 'done'
        isGenerating.value = false
        populateResults()
      }, 500)
    }
  }, 800)
}

const populateResults = () => {
  generatedResources.value = [
    {
      type: 'doc', title: '核心精讲：TCP三次握手深度剖析', icon: Document,
      content: '为什么不能是两次？为了防止已失效的连接请求报文段突然又传送到了服务端，因而产生错误。假设采用两次握手，客户端发出请求但因网络延迟未收到确认...'
    },
    {
      type: 'mindmap', title: 'TCP/IP 协议栈拓扑图', icon: PictureRounded,
      url: 'https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=600&q=80'
    },
    {
      type: 'code', title: '实操案例：Python Socket 模拟握手过程', icon: Cpu,
      content: 'import socket\n# 创建 socket 对象\ns = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n# 尝试连接服务端 (触发SYN)\ns.connect(("127.0.0.1", 8080))'
    },
    {
      type: 'quiz', title: '短板特训：连接建立异常处理', icon: Edit,
      desc: '基于您填写的短板，已生成 5 道情景选择题，涵盖 SYN Flood 攻击与丢包重传机制。'
    },
    {
      type: 'media', title: '3D动画演示：数据包的时空旅行', icon: VideoCamera,
      desc: '时长 03:45 | 多智能体生成的动态报文交换可视化'
    }
  ]
}
</script>

<style scoped>
/* ================= 全局工作台布局 ================= */
.studio-layout {
  display: flex;
  height: calc(100vh - 60px); /* 减去顶部导航高度 */
  background: #F3F4F6;
  overflow: hidden;
}

/* ================= 左侧：控制台面板 (表单区) ================= */
.config-sidebar {
  width: 380px;
  background: #FFFFFF;
  border-right: 1px solid #E5E7EB;
  display: flex;
  flex-direction: column;
  z-index: 10;
  box-shadow: 2px 0 10px rgba(0,0,0,0.02);
}

.sidebar-header {
  padding: 2rem 2rem 1.5rem;
  border-bottom: 1px solid #F3F4F6;
}
.brand-icon { font-size: 2rem; color: #111827; margin-bottom: 0.5rem; }
.sidebar-header h2 { margin: 0 0 0.25rem; font-size: 1.25rem; color: #111827; font-weight: 700; }
.sidebar-header p { margin: 0; font-size: 0.85rem; color: #6B7280; line-height: 1.5; }

.form-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group { display: flex; flex-direction: column; gap: 0.5rem; }
.form-group label { font-size: 0.85rem; font-weight: 600; color: #374151; }
.form-group label span { color: #EF4444; }

input, textarea {
  width: 100%; padding: 12px;
  background: #F9FAFB; border: 1px solid #E5E7EB;
  border-radius: 8px; font-family: inherit; font-size: 0.9rem;
  transition: all 0.2s; resize: none; color: #111827;
}
input:focus, textarea:focus {
  background: #FFFFFF; border-color: #3B82F6; outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.radio-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.radio-card {
  border: 1px solid #E5E7EB; padding: 10px; border-radius: 8px;
  cursor: pointer; transition: all 0.2s; display: flex; flex-direction: column;
  font-size: 0.9rem; font-weight: 600; color: #374151; background: #F9FAFB;
}
.radio-card small { font-size: 0.7rem; font-weight: 400; color: #6B7280; margin-top: 4px; }
.radio-card.is-active {
  background: #EFF6FF; border-color: #3B82F6; color: #1D4ED8;
}
.radio-card.is-active small { color: #2563EB; }

.sidebar-footer { padding: 1.5rem 2rem; border-top: 1px solid #F3F4F6; background: #FFFFFF; }
.generate-btn {
  width: 100%; height: 48px; border-radius: 8px;
  background: #111827; color: white; border: none;
  font-size: 1rem; font-weight: 600; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all 0.2s;
}
.generate-btn:hover:not(:disabled) { background: #374151; }
.generate-btn:disabled { background: #9CA3AF; cursor: not-allowed; }

/* ================= 右侧：画布区 ================= */
.workspace-canvas {
  flex: 1; padding: 2.5rem; overflow-y: auto;
  position: relative;
}

/* 空闲状态 */
.empty-state {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: #6B7280;
}
.empty-icon { font-size: 4rem; color: #D1D5DB; margin-bottom: 1.5rem; }
.empty-state h3 { color: #374151; font-size: 1.25rem; margin-bottom: 0.5rem; }
.empty-state p { font-size: 0.95rem; line-height: 1.6; }

/* 生成中动画状态 (垂直流式节点) */
.agent-workflow-view {
  max-width: 600px; margin: 4rem auto 0;
}
.progress-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; color: #111827; }
.progress-header h3 { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 1.1rem; }
.pct { font-family: monospace; font-size: 1.25rem; font-weight: 700; color: #3B82F6; }

.progress-bar-bg { height: 6px; background: #E5E7EB; border-radius: 3px; overflow: hidden; margin-bottom: 3rem; }
.progress-bar-fill { height: 100%; background: #3B82F6; transition: width 0.5s ease; }

.nodes-container { display: flex; flex-direction: column; gap: 1rem; }
.agent-node { display: flex; gap: 1.5rem; position: relative; padding: 1rem; border-radius: 12px; transition: all 0.3s; }
.agent-node.wait { opacity: 0.4; }
.agent-node.active { background: white; box-shadow: 0 4px 15px rgba(0,0,0,0.05); transform: translateX(10px); }

.node-line { position: absolute; left: 27px; top: 40px; bottom: -20px; width: 2px; background: #E5E7EB; z-index: 1; }
.active .node-line { background: linear-gradient(to bottom, #3B82F6, #E5E7EB); }

.node-icon {
  width: 24px; height: 24px; border-radius: 50%; background: #F3F4F6;
  display: flex; align-items: center; justify-content: center; z-index: 2;
  color: #9CA3AF; flex-shrink: 0; margin-top: 2px;
}
.active .node-icon { background: #EFF6FF; color: #3B82F6; }
.done .node-icon { background: #10B981; color: white; }
.wait-dot { width: 8px; height: 8px; background: #D1D5DB; border-radius: 50%; }

.node-info h4 { margin: 0 0 4px; font-size: 1rem; color: #111827; }
.node-info p { margin: 0; font-size: 0.85rem; color: #6B7280; }

/* 生成结果矩阵 */
.result-matrix { max-width: 1200px; margin: 0 auto; animation: fadeIn 0.5s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.matrix-header { margin-bottom: 2rem; }
.matrix-header h2 { font-size: 1.8rem; margin: 0 0 0.75rem; color: #111827; }
.tags { display: flex; gap: 0.5rem; }
.tags span { background: #E5E7EB; color: #4B5563; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }

.resource-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 1.5rem; align-items: start;
}

.r-card {
  background: white; border-radius: 16px; padding: 1.5rem; border: 1px solid #E5E7EB;
  display: flex; flex-direction: column; transition: box-shadow 0.2s;
}
.r-card:hover { box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); }

/* 类型定制 */
.type-doc { grid-column: 1 / -1; }
.type-code { background: #111827; color: white; border: none; }

.r-header { display: flex; align-items: center; gap: 8px; margin-bottom: 1rem; }
.r-icon { width: 32px; height: 32px; border-radius: 8px; background: #F3F4F6; display: flex; align-items: center; justify-content: center; color: #3B82F6; }
.type-code .r-icon { background: #374151; color: #10B981; }
.r-type { font-size: 0.75rem; font-weight: 700; color: #6B7280; letter-spacing: 0.05em; }
.type-code .r-type { color: #9CA3AF; }

.r-title { font-size: 1.1rem; margin: 0 0 1rem; line-height: 1.4; color: #111827; }
.type-code .r-title { color: white; }

.r-body p { font-size: 0.9rem; color: #4B5563; line-height: 1.6; margin: 0; }
.r-body pre { background: #1F2937; padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.85rem; color: #10B981; margin: 0; overflow-x: auto; }
.img-preview { height: 180px; background-size: cover; background-position: center; border-radius: 8px; }
.r-desc { color: #6B7280 !important; }

.r-action { margin-top: 1.5rem; }
.action-btn { width: 100%; padding: 8px; background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; cursor: pointer; font-weight: 600; color: #374151; transition: all 0.2s; }
.action-btn:hover { background: #F3F4F6; border-color: #D1D5DB; }

.is-loading { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>