<template>
  <div class="page-container">
    <div class="eval-content">
      <div class="eval-header">
        <h2 class="title">学习效果多维度评估</h2>
        <p class="subtitle">基于大模型的行为分析与能力建模，实时为您反馈学习状态</p>
      </div>

      <el-row :gutter="24">
        <el-col :span="8">
          <div class="score-card">
            <div class="score-main">
              <el-progress 
                type="dashboard" 
                :percentage="score" 
                :stroke-width="12"
                :color="[
                  { color: '#f56c6c', percentage: 20 },
                  { color: '#e6a23c', percentage: 40 },
                  { color: '#5cb87a', percentage: 60 },
                  { color: '#1989fa', percentage: 80 },
                  { color: '#6f7ad3', percentage: 100 },
                ]"
              >
                <template #default="{ percentage }">
                  <div class="score-text">
                    <span class="score-num">{{ percentage }}</span>
                    <span class="score-unit">综合评分</span>
                  </div>
                </template>
              </el-progress>
            </div>
            <div class="score-footer">
              <el-tag type="success" effect="dark" round>学习状态：极佳</el-tag>
            </div>
          </div>
        </el-col>

        <el-col :span="16">
          <div class="metrics-grid">
            <el-card v-for="m in metrics" :key="m.label" shadow="never" class="metric-card">
              <template #header>
                <div class="metric-header">
                  <span>{{ m.label }}</span>
                  <el-icon><DataAnalysis /></el-icon>
                </div>
              </template>
              <div class="metric-body">
                <span class="m-val">{{ m.value }}%</span>
                <el-progress :percentage="m.value" :status="m.status" :show-text="false" />
              </div>
            </el-card>
          </div>
        </el-col>
      </el-row>

      <div class="eval-sections">
        <div class="section-box">
          <h3 class="section-title"><el-icon><Calendar /></el-icon> 近期测评记录</h3>
          <el-table :data="recentTests" style="width: 100%" border>
            <el-table-column prop="date" label="测试日期" width="150" />
            <el-table-column prop="name" label="测试主题" />
            <el-table-column prop="score" label="得分" width="100">
              <template #default="scope">
                <span :class="scope.row.score >= 90 ? 'text-success' : ''" style="font-weight: 700">
                  {{ scope.row.score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="result" label="等级评价" width="120" />
          </el-table>
        </div>

        <div class="section-box highlight">
          <h3 class="section-title"><el-icon><Medal /></el-icon> AI 评估总结与建议</h3>
          <div class="ai-report">
            <p><strong>学习趋势：</strong> 过去 7 天内，你的逻辑思维能力有明显提升（+12%），但知识点的记忆持久度略有下降。</p>
            <p><strong>策略调整：</strong> 系统已自动在你的学习路径中增加了“遗忘曲线复习”环节，并为您准备了 3 组 CNN 易错题。建议在今天下午 4 点前完成。</p>
            <el-button type="primary" class="mt-4">接受 AI 优化建议并调整计划</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  DataAnalysis, 
  Medal,
  Calendar
} from '@element-plus/icons-vue'

const score = ref(85)
const metrics = [
  { label: '知识掌握度', value: 92, status: 'success' },
  { label: '思维活跃度', value: 78, status: 'primary' },
  { label: '实践完成率', value: 85, status: 'warning' },
  { label: '问题解决速度', value: 64, status: 'primary' }
]

const recentTests = [
  { name: 'CNN 架构基础', score: 95, date: '2026-04-01', result: '优秀' },
  { name: '反向传播算法', score: 72, date: '2026-03-28', result: '良好' },
  { name: 'Python 环境搭建', score: 100, date: '2026-03-25', result: '满分' }
]
</script>

<style scoped>
.page-container { min-height: 100vh; background: #F8FAFC; padding: 3rem; }
.eval-content { max-width: 1100px; margin: 0 auto; }
.eval-header { text-align: center; margin-bottom: 3rem; }
.title { font-size: 2rem; color: #0F172A; margin-bottom: 0.5rem; }
.subtitle { color: #64748B; }

.score-card { background: white; padding: 2.5rem; border-radius: 24px; text-align: center; border: 1px solid rgba(0,0,0,0.05); }
.score-text { display: flex; flex-direction: column; }
.score-num { font-size: 3rem; font-weight: 800; color: #0F172A; }
.score-unit { font-size: 0.875rem; color: #64748B; margin-top: -5px; }

.metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.25rem; }
.metric-card { border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); }
.metric-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 0.9rem; }
.m-val { font-size: 1.5rem; font-weight: 700; display: block; margin-bottom: 0.5rem; }

.eval-sections { margin-top: 2.5rem; display: flex; flex-direction: column; gap: 2rem; }
.section-box { background: white; padding: 2rem; border-radius: 20px; border: 1px solid rgba(0,0,0,0.05); }
.section-box.highlight { background: #EEF2FF; border-color: #C7D2FE; }
.section-title { font-size: 1.15rem; margin-bottom: 1.5rem; display: flex; align-items: center; gap: 0.5rem; }

.ai-report { line-height: 1.8; color: #374151; font-size: 0.95rem; }
.text-success { color: #10B981; }
.mt-4 { margin-top: 1rem; }
</style>