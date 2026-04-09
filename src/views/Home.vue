<template>
  <div class="command-center">
    <header class="global-hud">
      <div class="hud-left">
        <div class="sys-status">
          <span class="pulse-dot"></span>
          <span class="mono">AGENT_SYNC: ONLINE</span>
        </div>
        <div class="insight-box">
          <el-icon class="insight-icon"><Opportunity /></el-icon>
          <span class="insight-text"><strong>AI 核心洞察：</strong>{{ aiInsight }}</span>
        </div>
      </div>
      <div class="hud-right">
        <el-button class="tutor-btn" @click="router.push('/tutor')">
          <el-icon><Aim /></el-icon> 召唤智能辅导
        </el-button>
      </div>
    </header>

    <div class="dashboard-grid">
      <div class="main-stage">
        <div class="clean-card path-section">
          <div class="panel-header">
            <h3 class="mono">LIVE_PATH // 当前学习路径</h3>
            <el-button link type="primary" @click="router.push('/path-planner')">查看全局规划 <el-icon><ArrowRight /></el-icon></el-button>
          </div>
          <div class="path-timeline">
            <el-steps :active="1" align-center finish-status="success">
              <el-step v-for="step in pathSteps" :key="step.id" :title="step.title" :description="step.desc" />
            </el-steps>
          </div>
        </div>

        <div class="clean-card resource-section">
          <div class="panel-header">
            <h3 class="mono">MULTI_AGENT_RESOURCES // 定制资源库</h3>
            <span class="badge">已为您生成 5 份资源</span>
          </div>
          <div class="resource-grid">
            <div
                v-for="(res, index) in multimodalResources"
                :key="res.id"
                :class="['res-card', { 'hero-card': index === 0 }]"
            >
              <div class="res-icon-wrapper" :style="{ background: `${res.color}15`, color: res.color }">
                <el-icon><component :is="res.icon" /></el-icon>
              </div>
              <div class="res-info">
                <span class="res-type">{{ res.type }} <span class="format-tag">{{ res.format }}</span></span>
                <h4 class="res-title">{{ res.title }}</h4>
              </div>
              <div class="res-action">
                <el-button circle size="small" :icon="Lightning" />
              </div>
            </div>
          </div>
          <div class="panel-footer">
            <el-button plain class="w-full" @click="router.push('/resource-generator')">
              进入资源生成加工厂
            </el-button>
          </div>
        </div>
      </div>

      <div class="side-panel">
        <div class="clean-card profile-card">
          <div class="panel-header">
            <h3 class="mono">DYNAMIC_PROFILE // 画像快照</h3>
          </div>
          <div class="radar-container">
            <v-chart class="chart" :option="profileOption" autoresize />
            <div class="profile-overlay">
              <span class="update-time">刚刚更新</span>
            </div>
          </div>
          <el-button link type="primary" class="w-full mt-2" @click="router.push('/profile-assistant')">
            调整画像特征 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>

        <div class="clean-card eval-card">
          <div class="panel-header">
            <h3 class="mono">EVALUATION // 综合评估</h3>
          </div>
          <div class="eval-score">
            <div class="score-num">89<span class="score-unit">分</span></div>
            <div class="score-trend text-emerald">
              <el-icon><TrendCharts /></el-icon> +12% (本周)
            </div>
          </div>
          <div class="trend-chart-container">
            <v-chart class="chart" :option="trendOption" autoresize />
          </div>
          <el-button plain class="w-full mt-4" @click="router.push('/evaluation')">查看深度评估报告</el-button>
        </div>

        <div class="clean-card task-card">
          <div class="task-alert">
            <el-icon class="warn-icon"><Warning /></el-icon>
            <div class="task-info">
              <strong>弱项攻克任务</strong>
              <p>系统发现您在“全连接层参数计算”存在知识盲区，建议进行针对性测验。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Lightning, Opportunity, TrendCharts,
  VideoPlay, Monitor, Document, Cpu, EditPen,
  ArrowRight, Warning, Aim
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, RadarChart, LineChart, GridComponent, TooltipComponent])

const router = useRouter()

// --- 1. HUD 核心洞察 ---
const aiInsight = ref("基于最新评估：感知到您在「反向传播」耗时较长，已自动提升今日实操代码资源权重。")

// --- 2. 学习路径数据 ---
const pathSteps = ref([
  { id: 1, title: '前置理论', desc: '线性代数与导数', status: 'success' },
  { id: 2, title: '核心架构', desc: '卷积神经网络 (CNN)', status: 'process' },
  { id: 3, title: '进阶优化', desc: '残差网络与注意力机制', status: 'wait' }
])

// --- 3. 5类多模态专属资源 ---
const multimodalResources = ref([
  { id: 1, type: '多模态视频', title: 'CNN 3D 卷积核可视化', icon: VideoPlay, color: '#EF4444', format: 'MP4' },
  { id: 2, type: '代码实操', title: '手写反向传播算法', icon: Cpu, color: '#F59E0B', format: 'Python' },
  { id: 3, type: '思维导图', title: '计算机视觉发展拓扑图', icon: Monitor, color: '#8B5CF6', format: 'PNG' },
  { id: 4, type: '专业文档', title: '斯坦福 CS231n 核心笔记', icon: Document, color: '#4F46E5', format: 'PDF' },
  { id: 5, type: '个性题库', title: '针对易错点：池化层专项拔高', icon: EditPen, color: '#10B981', format: '交互式' }
])

// --- 4. 画像与评估数据 ---
const profileOption = computed(() => ({
  radar: {
    indicator: [
      { name: '知识基础', max: 100 },
      { name: '认知风格', max: 100 },
      { name: '易错偏好', max: 100 },
      { name: '学习兴趣', max: 100 },
      { name: '学习效率', max: 100 },
      { name: '实践能力', max: 100 }
    ],
    shape: 'circle',
    splitNumber: 4,
    axisName: { color: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' },
    splitLine: { lineStyle: { color: '#E2E8F0' } },
    splitArea: { show: false }
  },
  series: [{
    type: 'radar',
    data: [{
      value: [85, 60, 40, 92, 75, 88],
      areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
      lineStyle: { color: '#4F46E5', width: 2 },
      symbol: 'circle',
      symbolSize: 4,
      itemStyle: { color: '#4F46E5' }
    }]
  }]
}))

const trendOption = computed(() => ({
  grid: { top: 10, bottom: 20, left: 0, right: 0 },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '今日'], show: false },
  yAxis: { type: 'value', show: false, min: 60 },
  series: [{
    data: [72, 75, 74, 78, 85, 82, 89],
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: { color: '#10B981', width: 3 },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: 'rgba(16,185,129,0.3)' }, { offset: 1, color: 'rgba(16,185,129,0)' }]
      }
    }
  }]
}))
</script>

<style scoped>
.command-center {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  /* 取消原来的强制边距，依靠父容器的填充 */
  padding: 1.5rem 2.5rem;
  max-width: 1800px;
  margin: 0 auto;
  animation: fade-in 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 扁平化统一卡片风格，取代玻璃拟态 */
.clean-card {
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid #E2E8F0;
  padding: 1.75rem;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.03); /* 极弱阴影 */
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.clean-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  color: #64748B;
  font-weight: 700;
}

.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.panel-header h3 { margin: 0; color: #1E293B; }
.badge { background: #EEF2FF; color: #4F46E5; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; }

/* 1. 全景 HUD - 保持深色作为视觉焦点 */
.global-hud {
  display: flex; justify-content: space-between; align-items: center;
  background: #0F172A; color: white; border-radius: 20px; padding: 1.25rem 2rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.1);
}
.hud-left { display: flex; align-items: center; gap: 2rem; }
.sys-status { display: flex; align-items: center; gap: 0.5rem; color: #10B981; }
.pulse-dot { width: 8px; height: 8px; background: #10B981; border-radius: 50%; box-shadow: 0 0 10px #10B981; animation: pulse 2s infinite; }
.insight-box { display: flex; align-items: center; gap: 0.75rem; background: rgba(255,255,255,0.1); padding: 8px 16px; border-radius: 12px; }
.insight-icon { color: #F59E0B; font-size: 1.2rem; }
.insight-text { font-size: 0.85rem; opacity: 0.9; }

.tutor-btn { background: #4F46E5 !important; border: none !important; color: white !important; font-weight: 700; border-radius: 12px !important; }
.tutor-btn:hover { background: #4338CA !important; box-shadow: 0 0 15px rgba(79, 70, 229, 0.4); }

/* 布局 Grid */
.dashboard-grid { display: grid; grid-template-columns: 1.6fr 1fr; gap: 1.5rem; align-items: start; }

/* 2. 主舞台 (左侧) */
.main-stage { display: flex; flex-direction: column; gap: 1.5rem; }

.path-section .path-timeline { padding: 1rem 0; }
:deep(.el-step__title) { font-size: 0.9rem; font-weight: 700; color: #1E293B; }
:deep(.el-step__description) { font-size: 0.75rem; }

.resource-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
.res-card {
  display: flex; align-items: center; gap: 1rem; background: #F8FAFC;
  padding: 1rem; border-radius: 16px; border: 1px solid #F1F5F9;
  transition: all 0.2s;
}
.res-card:hover { background: white; border-color: #E2E8F0; box-shadow: 0 5px 15px rgba(0,0,0,0.03); }
.hero-card { grid-column: span 2; background: #F5F3FF; border-color: #E0E7FF; }
.hero-card:hover { background: #EEF2FF; border-color: #C7D2FE; }

.res-icon-wrapper { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; flex-shrink: 0; }
.res-info { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.res-type { font-size: 0.7rem; color: #64748B; font-weight: 600; margin-bottom: 2px; display: flex; align-items: center; gap: 6px; }
.format-tag { font-family: 'JetBrains Mono'; font-size: 0.6rem; background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px; }
.res-title { font-size: 0.9rem; margin: 0; color: #0F172A; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90%; }
.panel-footer { margin-top: 1.5rem; }

/* 3. 侧边栏 (右侧) */
.side-panel { display: flex; flex-direction: column; gap: 1.5rem; }

.radar-container { height: 220px; position: relative; }
.chart { width: 100%; height: 100%; }
.profile-overlay { position: absolute; bottom: -10px; right: 0; }
.update-time { font-size: 0.65rem; color: #10B981; background: rgba(16,185,129,0.1); padding: 4px 8px; border-radius: 10px; font-weight: 700; }

.eval-score { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 1rem; }
.score-num { font-size: 3rem; font-weight: 900; line-height: 1; color: #0F172A; }
.score-unit { font-size: 1rem; color: #64748B; font-weight: 600; margin-left: 4px; }
.score-trend { display: flex; align-items: center; gap: 4px; font-size: 0.85rem; font-weight: 700; padding-bottom: 6px; }
.text-emerald { color: #10B981; }
.trend-chart-container { height: 80px; width: 100%; margin-top: 0.5rem; }

.task-card { background: #FFF1F2; border-color: #FFE4E6; }
.task-card:hover { transform: none; box-shadow: none; }
.task-alert { display: flex; gap: 1rem; }
.warn-icon { font-size: 1.5rem; color: #E11D48; margin-top: 2px; }
.task-info strong { font-size: 0.9rem; color: #9F1239; display: block; margin-bottom: 0.25rem; }
.task-info p { margin: 0; font-size: 0.8rem; color: #BE123C; line-height: 1.5; }

.w-full { width: 100%; }
.mt-2 { margin-top: 0.5rem; }
.mt-4 { margin-top: 1rem; }

@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.5); } }
@keyframes fade-in { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

/* 响应式调整 */
@media (max-width: 1024px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .hud-left { flex-direction: column; align-items: flex-start; gap: 1rem; }
}
</style>