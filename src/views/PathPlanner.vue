<template>
  <div class="path-planner">
    <div class="header-section">
      <div class="info">
        <h2>智能学习路径规划</h2>
        <p>AI 已基于你的最新测评反馈，动态优化了后续的学习步骤与资源权重。</p>
      </div>
      <div class="stats">
        <div class="stat-item">
          <span class="val">45%</span>
          <span class="label">当前总进度</span>
        </div>
        <div class="stat-item">
          <span class="val">Lv.3</span>
          <span class="label">知识掌握等级</span>
        </div>
      </div>
    </div>

    <el-row :gutter="24">
      <el-col :span="16">
        <div class="timeline-card">
          <el-steps direction="vertical" :active="1">
            <el-step v-for="step in steps" :key="step.id" :title="step.title">
              <template #description>
                <div class="step-desc-box">
                  <p>{{ step.desc }}</p>
                  <div class="step-actions" v-if="step.status === 'processing'">
                    <el-button type="primary" size="small">生成本阶段定制资源</el-button>
                  </div>
                  <div class="step-actions" v-else-if="step.status === 'success'">
                    <el-tag size="small" type="success">已达成目标</el-tag>
                  </div>
                </div>
              </template>
              <template #icon>
                <el-icon v-if="step.status === 'success'"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="step.status === 'processing'"><Aim /></el-icon>
                <el-icon v-else><Flag /></el-icon>
              </template>
            </el-step>
          </el-steps>
        </div>
      </el-col>

      <el-col :span="8">
        <div class="insight-card highlight">
          <h4><el-icon><TrendCharts /></el-icon> 路径动态调整策略</h4>
          <p>监测到你在“梯度消失”练习中耗时较长，AI 自动在下个阶段增加了 2 组针对性实验案例，并延长了该知识点的复习周期。</p>
          <el-button type="primary" link>查看调整详情</el-button>
        </div>

        <div class="insight-card">
          <h4><el-icon><DataLine /></el-icon> 预测达成时间</h4>
          <div class="prediction">
            <div class="p-item">
              <span>预计完成时间</span>
              <strong>4月15日</strong>
            </div>
            <div class="p-item">
              <span>置信度</span>
              <strong>88%</strong>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  DataLine, 
  TrendCharts, 
  CircleCheckFilled, 
  Flag,
  Aim
} from '@element-plus/icons-vue'

const steps = ref([
  { id: 1, title: '基础概念', status: 'success', desc: '线性代数与微积分回顾' },
  { id: 2, title: '卷积神经网络', status: 'processing', desc: '池化、卷积与全连接层' },
  { id: 3, title: '循环神经网络', status: 'wait', desc: 'LSTM 与 GRU 序列模型' },
  { id: 4, title: '综合实战', status: 'wait', desc: '端到端图像识别项目' }
])
</script>

<style scoped>
.header-section {
  background: #0F172A; color: white; padding: 2.5rem; border-radius: 20px;
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;
}

.info h2 { font-size: 1.75rem; margin-bottom: 0.5rem; }
.info p { color: rgba(255,255,255,0.7); font-size: 1rem; }

.stats { display: flex; gap: 3rem; }
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-item .val { font-size: 1.75rem; font-weight: 700; color: #3B82F6; }
.stat-item .label { font-size: 0.75rem; color: rgba(255,255,255,0.5); margin-top: 4px; }

.timeline-card { background: white; padding: 3rem; border-radius: 20px; border: 1px solid rgba(0,0,0,0.05); }

.step-desc-box { padding: 0.5rem 0 1.5rem 0; }
.step-desc-box p { font-size: 0.9rem; color: #64748B; margin-bottom: 1rem; }

.insight-card { background: white; padding: 1.5rem; border-radius: 20px; border: 1px solid rgba(0,0,0,0.05); margin-bottom: 1.5rem; }
.insight-card.highlight { background: #EEF2FF; border-color: #C7D2FE; }
.insight-card h4 { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; font-size: 0.95rem; }
.insight-card p { font-size: 0.85rem; line-height: 1.6; color: #475569; margin-bottom: 1rem; }

.prediction { display: flex; flex-direction: column; gap: 1rem; }
.p-item { display: flex; justify-content: space-between; font-size: 0.85rem; }
.p-item strong { color: #0F172A; }

:deep(.el-step__title) { font-size: 1.1rem; font-weight: 700; color: #0F172A; }
:deep(.el-step__icon) { background: white !important; }
</style>