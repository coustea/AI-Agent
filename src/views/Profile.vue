<template>
  <div class="profile-dashboard">
    <el-row :gutter="20" class="top-row">
      <el-col :span="10">
        <div class="dashboard-card user-card">
          <div class="user-header">
            <div class="avatar-box">
              <el-icon class="avatar-icon"><UserFilled /></el-icon>
            </div>
            <div class="user-info">
              <div class="name-row">
                <h3>学习者</h3>
                <el-icon class="verify-icon"><CircleCheckFilled /></el-icon>
              </div>
              <p class="major">软件工程 · 学习中</p>
              <div class="tags">
                <span class="tag">大二</span>
                <span class="tag outline">AI学习路径</span>
              </div>
            </div>
            <el-button plain class="edit-btn" size="small"><el-icon><Edit /></el-icon> 编辑资料</el-button>
          </div>
          <div class="user-stats">
            <div class="stat-item">
              <el-icon class="text-blue"><Clock /></el-icon>
              <div class="stat-val">128<small>h</small></div>
              <div class="stat-label">累计学习时长</div>
            </div>
            <div class="stat-item">
              <el-icon class="text-indigo"><Reading /></el-icon>
              <div class="stat-val">18</div>
              <div class="stat-label">已完成课程</div>
            </div>
            <div class="stat-item">
              <el-icon class="text-green"><DocumentCopy /></el-icon>
              <div class="stat-val">46</div>
              <div class="stat-label">生成资源数</div>
            </div>
            <div class="stat-item">
              <el-icon class="text-orange"><StarFilled /></el-icon>
              <div class="stat-val">89<small>分</small></div>
              <div class="stat-label">综合评分</div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="7">
        <div class="dashboard-card radar-card">
          <div class="card-header-flex">
            <h4>学习画像 <el-icon class="info-icon"><InfoFilled /></el-icon></h4>
          </div>
          <div class="radar-container">
            <v-chart class="chart" :option="radarOption" autoresize />
          </div>
        </div>
      </el-col>

      <el-col :span="7">
        <div class="dashboard-card performance-card">
          <div class="card-header-flex">
            <h4>近期表现</h4>
            <el-select v-model="timeRange" size="small" style="width: 90px">
              <el-option label="近 7 天" value="7" />
              <el-option label="近 30 天" value="30" />
            </el-select>
          </div>
          <div class="perf-grid">
            <div class="perf-box">
              <div class="perf-icon bg-blue-light"><el-icon class="text-blue"><Timer /></el-icon></div>
              <div class="perf-data">
                <span class="label">学习时长</span>
                <span class="value">12.8<small>h</small></span>
              </div>
            </div>
            <div class="perf-box">
              <div class="perf-icon bg-green-light"><el-icon class="text-green"><Checked /></el-icon></div>
              <div class="perf-data">
                <span class="label">完成任务</span>
                <span class="value">16 <small>个</small></span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="main-grid">
      <div class="left-column">
        <div class="dashboard-card">
          <div class="card-header-flex">
            <h4 class="card-title">最近学习记录</h4>
            <span class="link-text">全部 ></span>
          </div>
          <div class="recent-record">
            <div class="record-icon"><el-icon><VideoPlay /></el-icon></div>
            <div class="record-info">
              <h5>CNN 3D 卷积核可视化</h5>
              <div class="record-meta">
                <span class="meta-tag">多模态视频 · MP4</span>
              </div>
            </div>
          </div>
          <div class="record-progress">
            <el-progress :percentage="60" :show-text="false" />
            <div class="prog-text"><span>进度 60%</span><span>今天 19:32</span></div>
          </div>
        </div>
      </div>

      <div class="right-column">
        <div class="dashboard-card history-card">
          <div class="card-header-flex">
            <h4 class="card-title"><el-icon class="text-blue"><Cpu /></el-icon> 资源生成历史</h4>
            <el-radio-group v-model="historyFilter" size="small">
              <el-radio-button label="全部" />
              <el-radio-button label="已完成" />
            </el-radio-group>
          </div>

          <el-table :data="tableData" style="width: 100%" :header-cell-style="{background:'#F8FAFC', color:'#64748B'}">
            <el-table-column label="任务名称 / 学习主题" min-width="200">
              <template #default="scope">
                <div class="task-title-cell">
                  <span>{{ scope.row.title }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small" class="custom-tag">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="时间" width="120" />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default>
                <el-button link type="primary">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="dashboard-card trend-section">
          <div class="card-header-flex">
            <h4 class="card-title">学习成长趋势</h4>
          </div>
          <div class="trend-chart-container">
            <v-chart class="chart" :option="lineOption" autoresize />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  UserFilled, CircleCheckFilled, Edit, Clock, Reading, DocumentCopy, StarFilled,
  InfoFilled, Timer, Checked, VideoPlay, Cpu
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, RadarChart, LineChart, GridComponent, TooltipComponent])

const timeRange = ref('7')
const historyFilter = ref('全部')

// 雷达图配置
const radarOption = computed(() => ({
  radar: {
    indicator: [
      { name: '知识基础', max: 100 },
      { name: '学习节奏', max: 100 },
      { name: '认知风格', max: 100 },
      { name: '兴趣偏好', max: 100 },
      { name: '薄弱环节', max: 100 },
      { name: '学习历史', max: 100 }
    ],
    shape: 'polygon',
    radius: '70%',
    axisName: { color: '#64748B', fontSize: 10 },
    splitArea: { show: false },
    splitLine: { lineStyle: { color: '#E2E8F0' } }
  },
  series: [{
    type: 'radar',
    data: [{
      value: [82, 78, 88, 85, 72, 79],
      areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
      lineStyle: { color: '#4F46E5', width: 2 },
      itemStyle: { color: '#4F46E5' },
      symbol: 'none'
    }]
  }]
}))

// 折线图配置
const lineOption = computed(() => ({
  grid: { top: 20, right: 10, bottom: 20, left: 30 },
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: ['1', '5', '10', '15', '20', '25', '30'],
    axisLine: { lineStyle: { color: '#E2E8F0' } },
    axisLabel: { color: '#94A3B8', fontSize: 10 }
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: '#F1F5F9', type: 'dashed' } },
    axisLabel: { color: '#94A3B8', fontSize: 10 }
  },
  series: [{
    data: [20, 32, 45, 40, 60, 85, 110],
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: { color: '#4F46E5', width: 3 },
    areaStyle: {
      color: {
        type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: 'rgba(79, 70, 229, 0.1)' }, { offset: 1, color: 'rgba(79, 70, 229, 0)' }]
      }
    }
  }]
}))

const tableData = [
  { title: '卷积神经网络基础', status: '已完成', time: '今天 19:32' },
  { title: '反向传播算法', status: '已完成', time: '今天 16:10' },
  { title: '计算机视觉发展脉络', status: '已完成', time: '昨天 21:45' },
  { title: '残差网络与注意力机制', status: '生成中', time: '昨天 14:20' }
]

const getStatusType = (status: string) => {
  if (status === '已完成') return 'success'
  if (status === '生成中') return 'primary'
  return 'info'
}
</script>

<style scoped>
.profile-dashboard {
  padding: 30px;
  background-color: #F8FAFC;
  min-height: 100%;
  font-family: 'Inter', system-ui, sans-serif;
}

.dashboard-card {
  background: #FFFFFF;
  border-radius: 20px;
  padding: 24px;
  border: 1px solid #E2E8F0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  height: 100%;
  box-sizing: border-box;
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #1E293B;
}

.link-text {
  font-size: 0.8rem;
  color: #3B82F6;
  cursor: pointer;
}

/* 用户卡片 */
.user-header { display: flex; align-items: center; gap: 20px; margin-bottom: 24px; position: relative; }
.avatar-box { width: 72px; height: 72px; background: #EEF2FF; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.2rem; color: #4F46E5; }
.user-info h3 { margin: 0; font-size: 1.3rem; font-weight: 800; }
.user-info .major { margin: 4px 0 8px; font-size: 0.9rem; color: #64748B; }
.tags { display: flex; gap: 8px; }
.tag { font-size: 0.75rem; padding: 3px 10px; background: #F1F5F9; color: #475569; border-radius: 6px; }
.edit-btn { position: absolute; right: 0; top: 0; }

.user-stats { display: flex; justify-content: space-between; padding-top: 20px; border-top: 1px solid #F1F5F9; }
.stat-item { text-align: center; }
.stat-val { font-size: 1.4rem; font-weight: 800; color: #0F172A; }
.stat-label { font-size: 0.75rem; color: #94A3B8; margin-top: 2px; }

/* 雷达图与表现 */
.radar-container {
  height: 180px;
  width: 100%;
}

.perf-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.perf-box {
  display: flex;
  align-items: center;
  gap: 15px;
  background: #F8FAFC;
  padding: 14px;
  border-radius: 12px;
}

.perf-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.bg-blue-light {
  background: #EFF6FF;
}

.bg-green-light {
  background: #ECFDF5;
}

.text-blue {
  color: #3B82F6;
}

.text-green {
  color: #10B981;
}

/* 主网格 */
.main-grid {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 24px;
  margin-top: 24px;
}

.left-column, .right-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.recent-record {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-top: 10px;
}

.record-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #FEF2F2;
  color: #EF4444;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
}

.record-info h5 {
  margin: 0 0 5px 0;
  font-size: 0.95rem;
}

.meta-tag {
  font-size: 0.75rem;
  color: #64748B;
  background: #F1F5F9;
  padding: 2px 8px;
  border-radius: 4px;
}

.record-progress {
  margin-top: 15px;
}

.prog-text {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94A3B8;
  margin-top: 6px;
}

.task-title-cell {
  font-weight: 600;
  color: #1E293B;
}

.trend-chart-container {
  height: 160px;
  width: 100%;
}

.custom-tag {
  border-radius: 6px;
}
</style>