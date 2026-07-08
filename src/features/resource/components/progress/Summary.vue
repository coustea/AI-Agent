<template>
  <!-- 工作流顶部状态栏：标题、阶段进度条与统计卡片 -->
  <header class="stage-topbar stage-topbar-v4">
    <div class="stage-title-area">
      <!-- 工作流标题与当前提示文案 -->
      <div class="stage-title-copy">
        <h2>资源生成工作流</h2>
        <p>{{ message }}</p>
      </div>
      <!-- 生成阶段步骤条：遍历步骤并渲染连接线 -->
      <div class="stage-route-progress" aria-label="生成阶段">
        <template v-for="(step, index) in steps" :key="step.key">
          <span class="route-step" :class="step.state">{{ step.label }}</span>
          <span
            v-if="index < steps.length - 1"
            class="route-line"
            :class="step.lineState"
          ></span>
        </template>
      </div>
    </div>

    <!-- 右侧统计区：进度、活跃数、已交付数与日志入口 -->
    <div class="stage-stat-group stage-stat-group-v4">
      <div class="stage-stat-card progress-stat-card">
        <span>生成进度</span>
        <strong>{{ progress }}%</strong>
        <div class="mini-progress-track"><i :style="{ width: `${progress}%` }"></i></div>
      </div>
      <div class="stage-stat-card">
        <span>活跃 Agent</span>
        <strong>{{ running }}<small>/{{ selected }}</small></strong>
      </div>
      <div class="stage-stat-card wide">
        <span>已交付资源</span>
        <strong>{{ delivered }}<small> 项</small></strong>
      </div>
      <!-- 点击打开运行日志抽屉 -->
      <button class="btn btn-outline rounded-full stage-log-btn" type="button" @click="emit('openLogs')">
        运行日志
        <ArrowRight class="h-4 w-4" />
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
// 引入箭头图标，用于“运行日志”按钮
import { PhArrowRight as ArrowRight } from '@phosphor-icons/vue'

// 阶段步骤的结构定义：标签与状态样式
export type RouteStep = {
  key: string
  label: string
  state: string
  lineState: string
}

// 组件入参：提示文案、进度、活跃/已选/已交付数量、步骤列表
defineProps<{
  message: string
  progress: number
  running: number
  selected: number
  delivered: number
  steps: RouteStep[]
}>()

// 组件事件：打开运行日志
const emit = defineEmits<{
  openLogs: []
}>()
</script>

<style scoped>
.stage-topbar {
  display: flex;
  min-height: 92px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 24px;
  border-bottom: 1px solid #e3e8ef;
  background: #fff;
}

.stage-title-area,
.stage-stat-group {
  display: flex;
  align-items: center;
  gap: 18px;
}

.stage-title-copy h2 {
  margin: 0;
  color: #172033;
  font-size: 18px;
}

.stage-title-copy p {
  max-width: 440px;
  margin: 4px 0 0;
  overflow: hidden;
  color: #667085;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-route-progress {
  display: flex;
  align-items: center;
}

.route-step {
  color: #98a2b3;
  font-size: 10px;
  font-weight: 700;
}

.route-step.done {
  color: #168357;
}

.route-step.active {
  color: #2c5f9f;
}

.route-line {
  width: 22px;
  height: 1px;
  margin: 0 6px;
  background: #d8dee8;
}

.route-line.done {
  background: #60b993;
}

.route-line.active {
  background: #7aa4d8;
}

.stage-stat-card {
  min-width: 86px;
  padding: 8px 10px;
  border: 1px solid #e3e8ef;
  border-radius: 9px;
  background: #f8fafc;
}

.stage-stat-card > span {
  display: block;
  color: #7a8494;
  font-size: 9px;
}

.stage-stat-card strong {
  color: #263246;
  font-size: 16px;
}

.stage-stat-card small {
  color: #98a2b3;
  font-size: 9px;
}

.mini-progress-track {
  height: 3px;
  margin-top: 5px;
  overflow: hidden;
  border-radius: 99px;
  background: #e4eaf2;
}

.mini-progress-track i {
  display: block;
  height: 100%;
  background: #3b75bd;
  transition: width 0.3s ease;
}

.stage-log-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

@media (max-width: 960px) {
  .stage-topbar,
  .stage-title-area {
    align-items: flex-start;
    flex-direction: column;
  }

  .stage-stat-group {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
