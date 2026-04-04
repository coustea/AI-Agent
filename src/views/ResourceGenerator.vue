<script setup lang="ts">
import { ref } from 'vue'
import {
  Search, VideoPlay, Monitor, Document, Cpu, EditPen, Download,
  MagicStick, Connection, Aim, Finished
} from '@element-plus/icons-vue'

const command = ref('')
const activeStep = ref(-1)
const isGenerating = ref(false)
const showResults = ref(false)

const steps = [
  { title: '分析 Agent', desc: '拆解需求与短板', icon: Aim },
  { title: '检索 Agent', desc: '构建 CS 知识图谱', icon: Search },
  { title: '渲染 Agent', desc: '合成多模态图文', icon: MagicStick },
  { title: '组卷 Agent', desc: '打包个性化题库', icon: Finished }
]

const generatedResources = ref<any[]>([])

const handleGenerate = () => {
  if (!command.value.trim() || isGenerating.value) return
  isGenerating.value = true
  showResults.value = false
  activeStep.value = 0
  generatedResources.value = []

  // 模拟流水线执行
  const timer = setInterval(() => {
    if (activeStep.value < 3) {
      activeStep.value++
    } else {
      clearInterval(timer)
      finishGeneration()
    }
  }, 1200)
}

const finishGeneration = () => {
  setTimeout(() => {
    isGenerating.value = false
    showResults.value = true
    // 5种赛题明确要求的多模态资源
    generatedResources.value = [
      { id: 1, type: '多模态教学视频', title: '指令集架构 3D 动画解析', meta: '时长 12:45 · 重点突击', icon: VideoPlay, color: '#EF4444', format: 'MP4', img: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800' },
      { id: 2, type: '实操案例代码', title: '手写一个简单的汇编模拟器', meta: 'Python 源码 · 附详细注释', icon: Cpu, color: '#10B981', format: 'PY' },
      { id: 3, type: '拓展阅读材料', title: '冯·诺依曼体系深入探讨', meta: '学术论文摘要 · 难度进阶', icon: Document, color: '#4F46E5', format: 'PDF' },
      { id: 4, type: '知识点思维导图', title: '计算机组成原理全局图谱', meta: '高清矢量图 · 支持缩放', icon: Monitor, color: '#8B5CF6', format: 'PNG' },
      { id: 5, type: '不同类型练习', title: '针对易错点：指令寻址方式特训', meta: '交互测试 · 15道选择与填空', icon: EditPen, color: '#F59E0B', format: 'QUIZ' }
    ]
  }, 800)
}
</script>

<template>
  <div class="factory-container">
    <!-- 顶部指令控制台 (全局搜索栏形态) -->
    <div class="command-center" :class="{ 'is-collapsed': showResults || isGenerating }">
      <div class="center-brand">
        <el-icon class="brand-icon"><Connection /></el-icon>
        <h1 class="cc-title">Agent Resource Factory</h1>
      </div>
      <p class="cc-desc">描述你的专业目标与当前的知识短板，多智能体协同引擎将生成全景式多模态资源。</p>

      <div class="omni-search-box">
        <el-icon class="search-icon"><MagicStick /></el-icon>
        <input
          v-model="command"
          placeholder="例如：我明天要考计算机组成原理，帮我梳理指令集架构，特别是不懂寻址方式..."
          @keyup.enter="handleGenerate"
        />
        <el-button type="primary" class="gen-btn" @click="handleGenerate" :loading="isGenerating">
          启动智能体矩阵
        </el-button>
      </div>
    </div>

    <!-- 中部流水线动画区 -->
    <transition name="fade-up">
      <div class="pipeline-section" v-if="isGenerating">
        <div class="pipeline-header">
          <span class="pulse-dot"></span>
          <span class="mono">MULTI_AGENT_WORKFLOW_ACTIVE</span>
        </div>
        <el-steps :active="activeStep" align-center finish-status="success" class="custom-steps">
          <el-step v-for="(step, idx) in steps" :key="idx" :title="step.title" :description="step.desc">
            <template #icon><el-icon><component :is="step.icon" /></el-icon></template>
          </el-step>
        </el-steps>
        <div class="terminal-log">
          <span class="log-cursor">></span>
          <span class="log-text">[{{ steps[activeStep]?.title }}] 正在处理数据块，节点状态: OK...</span>
        </div>
      </div>
    </transition>

    <!-- 底部结果仪表盘 (Dashboard 资源瀑布流阵列) -->
    <transition name="fade-up">
      <div class="dashboard-section" v-if="showResults">
        <div class="dash-header">
          <h3>协同生成完毕，为您定制了 5 份专属多模态资料</h3>
          <el-button color="#0F172A" :icon="Download" round>一键打包入库</el-button>
        </div>

        <div class="resource-grid">
          <!-- 资源 1: 视频类 (大卡片) -->
          <div class="res-card hero-card" :style="{ backgroundImage: `url(${generatedResources[0].img})` }">
            <div class="card-overlay">
              <div class="hero-top">
                <el-tag effect="dark" color="#EF4444" style="border:none">{{ generatedResources[0].type }}</el-tag>
                <span class="format-badge">{{ generatedResources[0].format }}</span>
              </div>
              <div class="play-btn"><el-icon><VideoPlay /></el-icon></div>
              <div class="hero-bottom">
                <h4>{{ generatedResources[0].title }}</h4>
                <p>{{ generatedResources[0].meta }}</p>
              </div>
            </div>
          </div>

          <!-- 资源 2-5: 文档/代码/导图/题库 (中小型卡片阵列) -->
          <div
            v-for="res in generatedResources.slice(1)"
            :key="res.id"
            class="res-card standard-card"
            :class="{ 'code-card': res.format === 'PY' }"
          >
            <div class="card-body">
              <div class="card-icon-box" :style="{ background: res.format === 'PY' ? 'rgba(255,255,255,0.1)' : `${res.color}15`, color: res.format === 'PY' ? '#10B981' : res.color }">
                <el-icon><component :is="res.icon" /></el-icon>
              </div>
              <div class="card-content">
                <div class="type-row">
                  <span class="res-type" :style="{ color: res.format === 'PY' ? '#9CA3AF' : '#64748B' }">{{ res.type }}</span>
                  <span class="format-badge" :class="{ 'dark-badge': res.format === 'PY' }">{{ res.format }}</span>
                </div>
                <h4 :style="{ color: res.format === 'PY' ? '#fff' : '#1E293B' }">{{ res.title }}</h4>
                <span class="res-meta" :style="{ color: res.format === 'PY' ? '#6EE7B7' : '#94A3B8' }">{{ res.meta }}</span>
              </div>
            </div>
            <div class="card-actions">
              <el-button link :type="res.format === 'PY' ? 'success' : 'primary'">查看详情</el-button>
              <el-button circle :icon="Download" size="small" :class="{ 'dark-btn': res.format === 'PY' }"></el-button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.factory-container { height: 100%; display: flex; flex-direction: column; overflow-y: auto; padding: 0 1rem 3rem; }

/* 顶端全局大搜索框 */
.command-center { padding: 6rem 0 3rem; display: flex; flex-direction: column; align-items: center; transition: all 0.6s cubic-bezier(0.2, 0.8, 0.2, 1); }
.command-center.is-collapsed { padding: 2rem 0; transform: translateY(-10px); opacity: 0.9; }

.center-brand { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; color: #0F172A; }
.brand-icon { font-size: 2.5rem; color: #4F46E5; }
.cc-title { font-size: 2.5rem; font-family: 'Poppins', sans-serif; font-weight: 800; margin: 0; letter-spacing: -0.02em; }
.cc-desc { color: #64748B; margin-bottom: 3rem; font-size: 1.1rem; }

.omni-search-box {
  width: 100%; max-width: 850px; background: white; border-radius: 28px;
  display: flex; align-items: center; padding: 12px 12px 12px 28px;
  box-shadow: 0 20px 50px rgba(0,0,0,0.06); border: 2px solid #E5E7EB;
  transition: all 0.3s;
}
.omni-search-box:focus-within { box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1), 0 20px 50px rgba(0,0,0,0.1); border-color: #4F46E5; }
.search-icon { font-size: 1.5rem; color: #4F46E5; margin-right: 1rem; }
.omni-search-box input { flex: 1; border: none; outline: none; font-size: 1.15rem; color: #0F172A; }
.gen-btn { height: 56px; padding: 0 2.5rem; border-radius: 18px !important; font-weight: 700; font-size: 1.05rem; background: #0F172A !important; border: none !important; transition: transform 0.2s; }
.gen-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(15,23,42,0.2); }

/* 流水线面板 */
.pipeline-section { max-width: 1000px; margin: 0 auto 3rem; width: 100%; padding: 2.5rem; background: white; border-radius: 28px; box-shadow: 0 15px 40px rgba(0,0,0,0.03); border: 1px solid #F1F5F9; }
.pipeline-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 2rem; color: #4F46E5; }
.mono { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; }
.pulse-dot { width: 10px; height: 10px; background: #4F46E5; border-radius: 50%; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.3); } }

.custom-steps { margin-bottom: 2rem; }
:deep(.el-step__title) { font-size: 0.95rem; font-weight: 700; }
:deep(.el-step__description) { font-size: 0.8rem; }
:deep(.el-step__icon) { width: 40px; height: 40px; font-size: 1.25rem; }

.terminal-log { background: #0F172A; color: #10B981; padding: 1.25rem 1.5rem; border-radius: 16px; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; display: flex; gap: 0.5rem; }
.log-cursor { animation: blink 1s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* 资源仪表盘 (瀑布流网格) */
.dashboard-section { flex: 1; max-width: 1100px; margin: 0 auto; width: 100%; }
.dash-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
.dash-header h3 { color: #0F172A; font-size: 1.4rem; font-weight: 800; margin: 0; }

.resource-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; grid-auto-rows: minmax(140px, auto); }

.res-card { background: white; border-radius: 24px; border: 1px solid #F1F5F9; overflow: hidden; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 10px 20px rgba(0,0,0,0.02); display: flex; flex-direction: column; }
.res-card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.06); border-color: #E0E7FF; }

/* 视频大图卡片 */
.hero-card { grid-column: span 2; grid-row: span 2; background-size: cover; background-position: center; position: relative; min-height: 320px; }
.card-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.3) 50%, rgba(15,23,42,0.6) 100%); display: flex; flex-direction: column; justify-content: space-between; padding: 2rem; }
.hero-top { display: flex; justify-content: space-between; align-items: center; }
.play-btn { align-self: center; width: 70px; height: 70px; background: rgba(255,255,255,0.25); backdrop-filter: blur(10px); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; color: white; cursor: pointer; transition: transform 0.2s, background 0.2s; }
.play-btn:hover { transform: scale(1.1); background: #EF4444; }
.hero-bottom h4 { color: white; font-size: 1.75rem; margin: 0 0 0.5rem; font-weight: 800; }
.hero-bottom p { color: #CBD5E1; margin: 0; font-size: 1rem; }

/* 标准与代码卡片 */
.standard-card { padding: 1.5rem; justify-content: space-between; }
.code-card { background: #0F172A; border-color: #1E293B; }
.code-card:hover { border-color: #10B981; box-shadow: 0 20px 40px rgba(16,185,129,0.15); }

.card-body { display: flex; gap: 1.25rem; margin-bottom: 1rem; }
.card-icon-box { width: 56px; height: 56px; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.75rem; flex-shrink: 0; }
.card-content { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.type-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.res-type { font-size: 0.75rem; font-weight: 700; }
.format-badge { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; background: #F1F5F9; color: #475569; padding: 3px 8px; border-radius: 6px; font-weight: 700; }
.dark-badge { background: rgba(255,255,255,0.1); color: #E2E8F0; }
.card-content h4 { margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 700; line-height: 1.4; }
.res-meta { font-size: 0.8rem; }

.card-actions { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #F1F5F9; padding-top: 1rem; margin-top: auto; }
.code-card .card-actions { border-top-color: rgba(255,255,255,0.1); }
.dark-btn { background: rgba(255,255,255,0.1) !important; color: white !important; border: none !important; }
.dark-btn:hover { background: #10B981 !important; }

/* 动画 */
.fade-up-enter-active, .fade-up-leave-active { transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
.fade-up-enter-from { opacity: 0; transform: translateY(40px); }
.fade-up-leave-to { opacity: 0; transform: translateY(-40px); }
</style>