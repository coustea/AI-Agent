<template>
  <!-- 将日志抽屉挂载到 body，避免被父级样式裁剪 -->
  <Teleport to="body">
    <!-- 抽屉式滑入/滑出过渡动画 -->
    <transition name="slide-over">
      <!-- 仅当 open 为 true 时渲染遮罩层，点击遮罩关闭抽屉 -->
      <div v-if="open" class="custom-modal-overlay" @click="emit('close')">
        <!-- 右侧日志抽屉主体，点击内部不触发遮罩关闭 -->
        <aside class="log-drawer" aria-label="实时调度日志" @click.stop>
          <!-- 抽屉头部：标题与关闭按钮 -->
          <header>
            <h3>实时调度日志</h3>
            <button type="button" aria-label="关闭日志" @click="emit('close')">×</button>
          </header>
          <!-- 日志条目列表 -->
          <div class="drawer-log-list">
            <!-- 遍历日志项，按状态着色显示圆点 -->
            <div
              v-for="item in items"
              :key="item.id"
              class="drawer-log-item"
              :class="`is-${item.status}`"
            >
              <span class="drawer-log-dot"></span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.message }}</p>
              </div>
            </div>
            <!-- 无日志时的占位提示 -->
            <p v-if="!items.length" class="empty-log">等待智能体上报运行日志</p>
          </div>
        </aside>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
// 引入 DAG 节点状态类型，用于约束日志项的状态字段
import type { DagNodeState } from '../../model/catalog'

// 单条工作流日志项的结构定义
export type WorkflowLogItem = {
  id: string
  title: string
  message: string
  status: DagNodeState['status']
}

// 组件入参：是否打开抽屉、日志条目列表
defineProps<{
  open: boolean
  items: WorkflowLogItem[]
}>()

// 组件事件：关闭抽屉
const emit = defineEmits<{
  close: []
}>()
</script>

<style scoped>
.custom-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgb(15 23 42 / 28%);
}

.log-drawer {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  width: min(420px, 100%);
  height: 100%;
  flex-direction: column;
  padding: 24px;
  background: #fff;
  box-shadow: -18px 0 48px rgb(15 23 42 / 14%);
}

.log-drawer header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8ecf1;
}

.log-drawer h3 {
  margin: 0;
  color: #263246;
  font-size: 14px;
}

.log-drawer button {
  border: 0;
  color: #98a2b3;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}

.drawer-log-list {
  overflow-y: auto;
  padding-top: 14px;
}

.drawer-log-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #eef1f5;
}

.drawer-log-dot {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border-radius: 50%;
  background: #98a2b3;
}

.drawer-log-item.is-running .drawer-log-dot {
  background: #3b75bd;
}

.drawer-log-item.is-success .drawer-log-dot {
  background: #168357;
}

.drawer-log-item.is-failed .drawer-log-dot {
  background: #c04444;
}

.drawer-log-item strong {
  color: #344054;
  font-size: 11px;
}

.drawer-log-item p,
.empty-log {
  margin: 3px 0 0;
  color: #7a8494;
  font-size: 10px;
  line-height: 1.5;
}

.slide-over-enter-active,
.slide-over-leave-active {
  transition: opacity 0.2s ease;
}

.slide-over-enter-from,
.slide-over-leave-to {
  opacity: 0;
}
</style>
