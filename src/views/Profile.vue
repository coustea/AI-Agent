<template>
  <div class="profile-dashboard">
<!--    <div class="page-header">-->
<!--      <h2>个人中心 <span class="sub-title">// PERSONAL CENTER</span></h2>-->
<!--      <p>管理你的学习画像、学习数据与个人资料</p>-->
<!--    </div>-->

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
              <div class="stat-trend trend-up">较上周 +18%</div>
            </div>
            <div class="stat-item">
              <el-icon class="text-indigo"><Reading /></el-icon>
              <div class="stat-val">18</div>
              <div class="stat-label">已完成课程</div>
              <div class="stat-trend trend-up">较上周 +2</div>
            </div>
            <div class="stat-item">
              <el-icon class="text-green"><DocumentCopy /></el-icon>
              <div class="stat-val">46</div>
              <div class="stat-label">生成资源数</div>
              <div class="stat-trend trend-up">较上周 +14%</div>
            </div>
            <div class="stat-item">
              <el-icon class="text-orange"><StarFilled /></el-icon>
              <div class="stat-val">89<small>分</small></div>
              <div class="stat-label">当前综合评分</div>
              <div class="stat-trend trend-up">较上周 +12%</div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="7">
        <div class="dashboard-card radar-card">
          <div class="card-header-flex">
            <h4>学习画像 <el-icon class="info-icon"><InfoFilled /></el-icon></h4>
            <span class="link-text">画像详情 ></span>
          </div>
          <div class="radar-container">
            <v-chart class="chart" :option="radarOption" autoresize />
            <div class="radar-legend">
              <div class="legend-item"><span class="dot"></span>知识基础 <b>82</b></div>
              <div class="legend-item"><span class="dot"></span>学习节奏 <b>78</b></div>
              <div class="legend-item"><span class="dot"></span>认知风格 <b>88</b></div>
              <div class="legend-item"><span class="dot"></span>兴趣偏好 <b>85</b></div>
              <div class="legend-item"><span class="dot"></span>薄弱环节 <b>72</b></div>
              <div class="legend-item"><span class="dot"></span>学习历史 <b>79</b></div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="7">
        <div class="dashboard-card performance-card">
          <div class="card-header-flex">
            <h4>近期学习表现</h4>
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
                <span class="trend trend-up">较上周 +18%</span>
              </div>
            </div>
            <div class="perf-box">
              <div class="perf-icon bg-indigo-light"><el-icon class="text-indigo"><Reading /></el-icon></div>
              <div class="perf-data">
                <span class="label">课程学习</span>
                <span class="value">8 <small>节</small></span>
                <span class="trend trend-up">较上周 +3</span>
              </div>
            </div>
            <div class="perf-box">
              <div class="perf-icon bg-green-light"><el-icon class="text-green"><Checked /></el-icon></div>
              <div class="perf-data">
                <span class="label">完成任务</span>
                <span class="value">16 <small>个</small></span>
                <span class="trend trend-up">较上周 +14%</span>
              </div>
            </div>
            <div class="perf-box">
              <div class="perf-icon bg-orange-light"><el-icon class="text-orange"><Star /></el-icon></div>
              <div class="perf-data">
                <span class="label">综合得分</span>
                <span class="value">89 <small>分</small></span>
                <span class="trend trend-up">较上周 +12%</span>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="main-grid">
      <div class="left-column">
        <div class="dashboard-card nav-list-card">
          <h4 class="card-title">账号与安全</h4>
          <div class="nav-list">
            <div class="nav-row"><span><el-icon><User /></el-icon> 账号信息</span> <span class="nav-desc">查看与修改个人信息 <el-icon><ArrowRight /></el-icon></span></div>
            <div class="nav-row"><span><el-icon><Lock /></el-icon> 安全设置</span> <span class="nav-desc">密码修改、设备管理 <el-icon><ArrowRight /></el-icon></span></div>
            <div class="nav-row"><span><el-icon><Key /></el-icon> 隐私与权限</span> <span class="nav-desc">隐私使用声明与设置 <el-icon><ArrowRight /></el-icon></span></div>
            <div class="nav-row"><span><el-icon><Bell /></el-icon> 通知设置</span> <span class="nav-desc">消息与通知偏好设置 <el-icon><ArrowRight /></el-icon></span></div>
          </div>
        </div>

        <div class="dashboard-card badges-card">
          <div class="card-header-flex">
            <h4 class="card-title">成长勋章</h4>
            <span class="link-text">查看全部 ></span>
          </div>
          <div class="badges-row">
            <div class="badge-item">
              <div class="badge-icon b-blue"><el-icon><Medal /></el-icon></div>
              <span class="badge-name">连续学习7天</span>
              <span class="badge-date">2024.05.20</span>
            </div>
            <div class="badge-item">
              <div class="badge-icon b-purple"><el-icon><Aim /></el-icon></div>
              <span class="badge-name">探索者</span>
              <span class="badge-date">2024.05.15</span>
            </div>
            <div class="badge-item">
              <div class="badge-icon b-green"><el-icon><DataBoard /></el-icon></div>
              <span class="badge-name">资源创作者</span>
              <span class="badge-date">2024.05.10</span>
            </div>
            <div class="badge-item">
              <div class="badge-icon b-orange"><el-icon><Trophy /></el-icon></div>
              <span class="badge-name">高效学习者</span>
              <span class="badge-date">2024.05.05</span>
            </div>
            <div class="badge-item disabled">
              <div class="badge-icon"><el-icon><Star /></el-icon></div>
              <span class="badge-name">未来之星</span>
              <span class="badge-date">未解锁</span>
            </div>
          </div>
        </div>

        <div class="dashboard-card">
          <div class="card-header-flex">
            <h4 class="card-title">最近学习记录</h4>
            <span class="link-text">查看全部 ></span>
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
            <div class="prog-text"><span>60%</span><span>今天 19:32</span></div>
          </div>
        </div>
      </div>

      <div class="right-column">
        <div class="dashboard-card history-card">
          <div class="card-header-flex">
            <h4 class="card-title"><el-icon class="text-blue"><Cpu /></el-icon> 多智能体资源生成历史</h4>
            <span class="link-text">查看使用指南</span>
          </div>

          <div class="history-stats-row">
            <div class="h-stat-box">
              <div class="h-icon bg-purple-light"><el-icon class="text-purple"><Box /></el-icon></div>
              <div><p>累计生成任务</p><strong>28</strong></div>
            </div>
            <div class="h-stat-box">
              <div class="h-icon bg-green-light"><el-icon class="text-green"><CircleCheck /></el-icon></div>
              <div><p>成功率</p><strong>92%</strong></div>
            </div>
            <div class="h-stat-box">
              <div class="h-icon bg-blue-light"><el-icon class="text-blue"><TrendCharts /></el-icon></div>
              <div><p>本周新增</p><strong>6</strong></div>
            </div>
            <div class="h-stat-box">
              <div class="h-icon bg-orange-light"><el-icon class="text-orange"><Clock /></el-icon></div>
              <div><p>最近一次生成</p><strong>19:32</strong></div>
            </div>
          </div>

          <div class="table-filters">
            <el-radio-group v-model="historyFilter" size="small">
              <el-radio-button label="全部" />
              <el-radio-button label="已完成" />
              <el-radio-button label="生成中" />
              <el-radio-button label="部分失败" />
              <el-radio-button label="失败" />
            </el-radio-group>
            <el-button size="small" plain>近 7 天 <el-icon class="el-icon--right"><Calendar /></el-icon></el-button>
          </div>

          <el-table :data="tableData" style="width: 100%" :header-cell-style="{background:'#F8FAFC', color:'#64748B'}">
            <el-table-column label="任务名称 / 学习主题" min-width="200">
              <template #default="scope">
                <div class="task-title-cell">
                  <el-icon class="text-blue"><Document /></el-icon>
                  <span>{{ scope.row.title }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="agents" label="多智能体编排" width="140" />
            <el-table-column prop="types" label="生成资源类型" min-width="250" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small" effect="light" class="custom-tag">{{ scope.row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="生成时间" width="120" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default>
                <el-button link type="primary">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="bottom-widgets">
          <div class="dashboard-card">
            <div class="card-header-flex">
              <h4 class="card-title">我的收藏资源</h4>
              <span class="link-text">查看全部 ></span>
            </div>
            <div class="fav-list">
              <div class="fav-item">
                <div class="fav-img img-1"></div>
                <div class="fav-info">
                  <h5>深度学习可视化交互合集</h5>
                  <span>PDF · 24.6MB <i class="date">2024.05.18</i></span>
                </div>
              </div>
              <div class="fav-item">
                <div class="fav-img img-2"></div>
                <div class="fav-info">
                  <h5>Python 机器学习实战项目</h5>
                  <span>代码 · 12MB <i class="date">2024.05.10</i></span>
                </div>
              </div>
            </div>
          </div>

          <div class="dashboard-card">
            <div class="card-header-flex">
              <h4 class="card-title">成长趋势</h4>
              <el-select v-model="trendRange" size="small" style="width: 90px">
                <el-option label="近 30 天" value="30" />
              </el-select>
            </div>
            <div class="trend-chart-container">
              <v-chart class="chart" :option="lineOption" autoresize />
            </div>
          </div>

          <div class="dashboard-card system-help-card">
            <h4 class="card-title">系统与帮助</h4>
            <div class="help-list">
              <div class="help-row"><div class="h-icon"><el-icon><QuestionFilled /></el-icon></div> <span>使用帮助</span> <i>快速上手与常见问题</i></div>
              <div class="help-row"><div class="h-icon"><el-icon><ChatDotSquare /></el-icon></div> <span>意见反馈</span> <i>帮助我们做得更好</i></div>
              <div class="help-row"><div class="h-icon"><el-icon><WarningFilled /></el-icon></div> <span>关于平台</span> <i>版本信息与更新日志</i></div>
            </div>
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
  InfoFilled, Timer, Checked, Star, User, Lock, Key, Bell, ArrowRight,
  Medal, Aim, DataBoard, Trophy, VideoPlay, Cpu, Box, CircleCheck, TrendCharts,
  Calendar, Document, QuestionFilled, ChatDotSquare, WarningFilled
} from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, RadarChart, LineChart, GridComponent, TooltipComponent])

const timeRange = ref('7')
const historyFilter = ref('全部')
const trendRange = ref('30')

// 雷达图配置
const radarOption = computed(() => ({
  radar: {
    indicator: [
      { name: '知识基础', max: 100 },
      { name: '学习节奏', max: 100 },
      { name: '认知风格', max: 100 },
      { name: '兴趣偏好', max: 100 },
      { name: '内部偏好', max: 100 },
      { name: '薄弱环节', max: 100 },
      { name: '学习历史', max: 100 }
    ],
    shape: 'polygon',
    radius: '65%',
    axisName: { color: '#64748B', fontSize: 10 },
    splitArea: { show: false },
    splitLine: { lineStyle: { color: '#E2E8F0' } },
    axisLine: { lineStyle: { color: '#E2E8F0' } }
  },
  series: [{
    type: 'radar',
    data: [{
      value: [82, 78, 88, 85, 90, 72, 79],
      areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
      lineStyle: { color: '#4F46E5', width: 2 },
      itemStyle: { color: '#4F46E5' },
      symbol: 'circle',
      symbolSize: 4
    }]
  }]
}))

// 折线图配置
const lineOption = computed(() => ({
  grid: { top: 30, right: 10, bottom: 20, left: 30 },
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
        colorStops: [
          { offset: 0, color: 'rgba(79, 70, 229, 0.2)' },
          { offset: 1, color: 'rgba(79, 70, 229, 0)' }
        ]
      }
    }
  }]
}))

// 表格数据
const tableData = [
  { title: '卷积神经网络基础', agents: '6个智能体协同', types: '讲解文档、思维导图、练习题、代码案例', status: '已完成', time: '今天 19:32' },
  { title: '反向传播算法', agents: '5个智能体协同', types: '讲解文档、代码案例、专项练习', status: '已完成', time: '今天 16:10' },
  { title: '计算机视觉发展脉络', agents: '4个智能体协同', types: '思维导图、拓扑图、阅读材料', status: '已完成', time: '昨天 21:45' },
  { title: '残差网络与注意力机制', agents: '6个智能体协同', types: '讲解文档、图解、练习题、视频脚本', status: '生成中', time: '昨天 14:20' },
  { title: '卷积层参数优化', agents: '5个智能体协同', types: '个性题库、代码实操、拓展阅读', status: '部分失败', time: '05-18 10:36' }
]

const getStatusType = (status: string) => {
  if (status === '已完成') return 'success'
  if (status === '生成中') return 'primary'
  if (status === '部分失败') return 'danger'
  return 'info'
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.profile-dashboard {
  padding: 24px;
  background-color: #F8FAFC;
  min-height: 100%;
  font-family: 'Inter', system-ui, sans-serif;
  color: #0F172A;
}

.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  font-size: 1.5rem;
  font-weight: 800;
  margin: 0 0 4px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.page-header .sub-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: #94A3B8;
  letter-spacing: 1px;
}
.page-header p {
  margin: 0;
  color: #64748B;
  font-size: 0.9rem;
}

.dashboard-card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 20px;
  border: 1px solid #E2E8F0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
  height: 100%;
  box-sizing: border-box;
}
.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.card-title, .card-header-flex h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1E293B;
  display: flex;
  align-items: center;
  gap: 8px;
}
.link-text {
  font-size: 0.8rem;
  color: #3B82F6;
  cursor: pointer;
  font-weight: 500;
}
.link-text:hover { text-decoration: underline; }

/* 颜色工具类 */
.text-blue { color: #3B82F6; }
.text-indigo { color: #6366F1; }
.text-green { color: #10B981; }
.text-orange { color: #F59E0B; }
.text-purple { color: #8B5CF6; }

.bg-blue-light { background: #EFF6FF; }
.bg-indigo-light { background: #EEF2FF; }
.bg-green-light { background: #ECFDF5; }
.bg-orange-light { background: #FFF7ED; }
.bg-purple-light { background: #F5F3FF; }

/* 顶行 1: 用户卡片 */
.user-card { display: flex; flex-direction: column; gap: 24px; justify-content: space-between; }
.user-header { display: flex; align-items: flex-start; gap: 16px; position: relative; }
.avatar-box { width: 64px; height: 64px; background: #E2E8F0; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #94A3B8; }
.user-info .name-row { display: flex; align-items: center; gap: 6px; }
.user-info h3 { margin: 0; font-size: 1.2rem; font-weight: 800; }
.verify-icon { color: #3B82F6; font-size: 1.1rem; }
.user-info .major { margin: 4px 0 8px; font-size: 0.85rem; color: #64748B; font-weight: 500; }
.tags { display: flex; gap: 8px; }
.tag { font-size: 0.7rem; padding: 2px 8px; background: #F1F5F9; color: #475569; border-radius: 4px; font-weight: 600; }
.tag.outline { background: transparent; border: 1px solid #CBD5E1; }
.edit-btn { position: absolute; right: 0; top: 0; border-radius: 20px; }

.user-stats { display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid #F1F5F9; }
.stat-item { display: flex; flex-direction: column; gap: 4px; }
.stat-item .el-icon { font-size: 1.2rem; margin-bottom: 4px; }
.stat-val { font-size: 1.4rem; font-weight: 800; color: #0F172A; }
.stat-val small { font-size: 0.8rem; font-weight: 600; color: #64748B; margin-left: 2px; }
.stat-label { font-size: 0.75rem; color: #64748B; }
.stat-trend { font-size: 0.7rem; font-weight: 600; }
.trend-up { color: #10B981; }

/* 顶行 2: 雷达图 */
.radar-card { display: flex; flex-direction: column; }
.radar-container { flex: 1; display: flex; align-items: center; justify-content: space-between; height: 160px;}
.radar-container .chart { width: 55%; height: 100%; }
.radar-legend { width: 40%; display: flex; flex-direction: column; gap: 6px; }
.legend-item { display: flex; align-items: center; font-size: 0.75rem; color: #475569; }
.legend-item .dot { width: 6px; height: 6px; border-radius: 50%; background: #4F46E5; margin-right: 8px; }
.legend-item b { margin-left: auto; color: #0F172A; font-family: monospace; font-size: 0.85rem; }

/* 顶行 3: 表现数据 */
.performance-card { display: flex; flex-direction: column; }
.perf-grid { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 16px; flex: 1; }
.perf-box { display: flex; align-items: center; gap: 12px; background: #F8FAFC; padding: 12px; border-radius: 12px; border: 1px solid #F1F5F9; }
.perf-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
.perf-data { display: flex; flex-direction: column; }
.perf-data .label { font-size: 0.75rem; color: #64748B; font-weight: 500; }
.perf-data .value { font-size: 1.1rem; font-weight: 800; color: #0F172A; margin: 2px 0; }
.perf-data .value small { font-size: 0.7rem; font-weight: 600; }
.perf-data .trend { font-size: 0.7rem; }

/* 主体网格布局 */
.main-grid { display: grid; grid-template-columns: 320px 1fr; gap: 20px; margin-top: 20px; align-items: start; }
.left-column { display: flex; flex-direction: column; gap: 20px; }
.right-column { display: flex; flex-direction: column; gap: 20px; min-width: 0; }

/* 左侧栏内容 */
.nav-list-card .card-title { margin-bottom: 12px; }
.nav-list { display: flex; flex-direction: column; }
.nav-row { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid #F1F5F9; font-size: 0.9rem; font-weight: 600; color: #334155; cursor: pointer; }
.nav-row:last-child { border-bottom: none; padding-bottom: 0; }
.nav-row span { display: flex; align-items: center; gap: 8px; }
.nav-row .el-icon { color: #64748B; font-size: 1.1rem; }
.nav-desc { font-size: 0.75rem !important; color: #94A3B8; font-weight: 400 !important; }

.badges-row { display: flex; justify-content: space-between; margin-top: 10px; }
.badge-item { display: flex; flex-direction: column; align-items: center; gap: 6px; }
.badge-item.disabled { filter: grayscale(1); opacity: 0.5; }
.badge-icon { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; background: #F1F5F9; color: #94A3B8; }
.b-blue { background: linear-gradient(135deg, #DBEAFE, #93C5FD); color: #2563EB; }
.b-purple { background: linear-gradient(135deg, #E0E7FF, #A5B4FC); color: #4F46E5; }
.b-green { background: linear-gradient(135deg, #D1FAE5, #6EE7B7); color: #059669; }
.b-orange { background: linear-gradient(135deg, #FFEDD5, #FDBA74); color: #EA580C; }
.badge-name { font-size: 0.7rem; font-weight: 600; color: #334155; }
.badge-date { font-size: 0.6rem; color: #94A3B8; font-family: monospace; }

.recent-record { display: flex; gap: 12px; margin-top: 10px; }
.record-icon { width: 40px; height: 40px; border-radius: 50%; background: #FEF2F2; color: #EF4444; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
.record-info h5 { margin: 0 0 6px 0; font-size: 0.9rem; color: #0F172A; }
.meta-tag { font-size: 0.7rem; padding: 2px 6px; background: #F1F5F9; color: #64748B; border-radius: 4px; }
.record-progress { margin-top: 16px; }
.prog-text { display: flex; justify-content: space-between; font-size: 0.7rem; color: #64748B; margin-top: 4px; }

/* 右侧栏内容 */
.history-stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.h-stat-box { display: flex; align-items: center; gap: 12px; background: #F8FAFC; padding: 16px; border-radius: 12px; border: 1px solid #F1F5F9; }
.h-icon { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
.h-stat-box p { margin: 0 0 4px 0; font-size: 0.75rem; color: #64748B; font-weight: 500; }
.h-stat-box strong { font-size: 1.4rem; font-weight: 800; color: #0F172A; line-height: 1; }

.table-filters { display: flex; justify-content: space-between; margin-bottom: 16px; }
.task-title-cell { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #1E293B; }
.custom-tag { border-radius: 6px; font-weight: 600; }
:deep(.el-table th.el-table__cell) { font-weight: 600; }

.bottom-widgets { display: grid; grid-template-columns: 1fr 1fr 240px; gap: 20px; }
.fav-list { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; }
.fav-item { display: flex; gap: 12px; align-items: center; }
.fav-img { width: 50px; height: 50px; border-radius: 8px; background: #1E293B; flex-shrink: 0; }
.img-1 { background: linear-gradient(135deg, #1E293B, #312E81); }
.img-2 { background: linear-gradient(135deg, #0F172A, #1E40AF); }
.fav-info h5 { margin: 0 0 4px 0; font-size: 0.85rem; color: #1E293B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fav-info span { font-size: 0.7rem; color: #64748B; display: flex; justify-content: space-between; align-items: center; width: 100%; }
.fav-info .date { font-style: normal; color: #94A3B8; }

.trend-chart-container { height: 120px; width: 100%; margin-top: 10px; }
.trend-chart-container .chart { width: 100%; height: 100%; }

.help-list { display: flex; flex-direction: column; gap: 16px; margin-top: 16px; }
.help-row { display: flex; align-items: center; gap: 10px; font-size: 0.85rem; font-weight: 600; color: #334155; cursor: pointer; }
.help-row .h-icon { width: 28px; height: 28px; background: #F1F5F9; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #4F46E5; }
.help-row i { font-style: normal; font-size: 0.7rem; color: #94A3B8; font-weight: 400; margin-left: auto; }
</style>