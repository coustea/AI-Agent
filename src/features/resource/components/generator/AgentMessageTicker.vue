<template>
  <!-- 智能体工位实时消息区域，外层根据节点状态切换边框/背景主题 -->
  <div class="station-live-log" :class="[`is-${node.status}`]">
    <!-- 有可展示消息时渲染滚动消息队列 -->
    <div v-if="visibleMessages.length" class="live-message-queue">
      <TransitionGroup name="live-message" tag="div" class="live-message-list">
        <!-- 逐条渲染可见消息，最后一条加粗、新消息带高亮动画 -->
        <div
            v-for="(item, index) in visibleMessages"
            :key="item.id"
            class="live-message-row"
            :class="{
            'is-latest': index === visibleMessages.length - 1,
            'is-fresh': freshMessageId === item.id
          }"
        >
          <!-- 状态指示小圆点，颜色随节点状态变化 -->
          <span class="station-live-dot" :class="node.status"></span>
          <p class="live-message-only">{{ item.text }}</p>
        </div>
      </TransitionGroup>
    </div>

    <!-- 无可展示消息时的兜底占位行，展示状态标签或后端消息 -->
    <div v-else class="live-message-row fallback-row">
      <span class="station-live-dot" :class="node.status"></span>
      <p class="live-message-only">{{ fallbackMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 响应式原语与生命周期钩子
import { computed, onScopeDispose, ref, watch } from 'vue'
// 引入 DAG 节点状态类型定义
import type { DagNodeState } from '../../model/catalog'

// 接收父组件传入的当前 DAG 节点状态对象
const props = defineProps<{
  node: DagNodeState
}>()

// 消息条目内部结构：唯一 id、去重 key、展示文本
type LiveMessage = {
  id: string
  key: string
  text: string
}

// 同时最多展示的消息条数（超出滚动淘汰旧消息）
const MAX_VISIBLE_MESSAGES = 2

// 每条消息至少展示多久。
// 1200~1600ms 比较合适，太短会闪，太长会拖。
const MIN_DISPLAY_MS = 1400

// 新消息高亮动画持续时间
const FRESH_ANIMATION_MS = 420

// 当前可见消息列表（响应式，驱动模板渲染）
const visibleMessages = ref<LiveMessage[]>([])
// 最近一条新消息的 id，用于触发高亮动画
const freshMessageId = ref<string | null>(null)

// 待展示消息队列（非响应式，仅内部调度使用）
let pendingQueue: LiveMessage[] = []
// 已消费消息的 key 集合，用于去重防止重复入队
let consumedKeys = new Set<string>()
// 自增序号，用于生成唯一消息 id
let messageSeq = 0
// 上一次消息展示的时间戳，用于节流最小展示时长
let lastDisplayAt = 0

// 队列消费定时器，控制消息逐条出场的节奏
let drainTimer: ReturnType<typeof setTimeout> | null = null
// 高亮动画清除定时器
let freshTimer: ReturnType<typeof setTimeout> | null = null

// 兜底消息：优先用后端消息，否则按状态给出简短标签
const fallbackMessage = computed(() => {
  // 只展示后端发送的消息
  // 没有后端消息时根据状态显示简短状态标签（不是伪造内容）
  if (props.node.currentMessage) {
    return props.node.currentMessage
  }
  const statusLabels: Record<string, string> = {
    waiting: '等待中',
    running: '运行中',
    success: '已完成',
    failed: '执行失败',
    skipped: '已跳过',
  }
  return statusLabels[props.node.status] || ''
})

// 切换节点时重置消息状态并填充初始消息（立即执行一次）
watch(
    () => props.node.id,
    () => {
      resetMessages()
      hydrateInitialMessages()
    },
    { immediate: true }
)

// 监听后端事件日志/步骤历史/当前消息的变化，把新消息排入展示队列
watch(
    () => [
      props.node.eventLogs?.length || 0,
      props.node.stepHistory?.length || 0,
      props.node.currentMessage,
      props.node.lastUpdatedAt || 0,
    ],
    () => {
      enqueueNewBackendMessages()
    },
    { deep: false }
)

// 重置全部消息状态并清除所有定时器
function resetMessages() {
  clearDrainTimer()
  clearFreshTimer()

  visibleMessages.value = []
  pendingQueue = []
  consumedKeys = new Set<string>()
  freshMessageId.value = null
  lastDisplayAt = 0
}

// 初始化时只静态回填最近几条消息，不播放动画也不重新排队历史
function hydrateInitialMessages() {
  const sources = collectAllSources()

  // 页面刚进来时，只静态显示最近 2 条，不播放动画，不把历史消息重新排队。
  const latest = sources.slice(-MAX_VISIBLE_MESSAGES)

  visibleMessages.value = latest.map(source => {
    consumedKeys.add(source.key)
    return createMessage(source.text, source.key)
  })

  lastDisplayAt = Date.now()
}

// 将后端新增的消息（尚未消费的）加入待展示队列并触发消费
function enqueueNewBackendMessages() {
  const sources = collectAllSources()

  for (const source of sources) {
    if (!source.text) continue
    if (consumedKeys.has(source.key)) continue
    if (pendingQueue.some(item => item.key === source.key)) continue

    pendingQueue.push(createMessage(source.text, source.key))
  }

  drainQueue()
}

// 收集节点全部消息来源：事件日志优先，步骤历史兜底，当前消息最后补充
function collectAllSources(): Array<{ key: string; text: string }> {
  const result: Array<{ key: string; text: string }> = []

  const logs = props.node.eventLogs || []
  logs.forEach((log: any, index: number) => {
    const text = String(log?.message || '').trim()
    if (!text) return

    result.push({
      key: buildLogKey(log, index),
      text,
    })
  })

  // 兜底：如果父组件还没有完整 eventLogs，就从 stepHistory 补。
  const history = props.node.stepHistory || []
  history.forEach((message, index) => {
    const text = String(message || '').trim()
    if (!text) return

    result.push({
      key: `history:${props.node.id}:${index}:${text}`,
      text,
    })
  })

  // 最后兜底 currentMessage。
  const current = props.node.currentMessage?.trim()
  if (current) {
    result.push({
      key: `current:${props.node.id}:${props.node.status}:${current}`,
      text: current,
    })
  }

  return dedupeSources(result)
}

// 对消息来源去重：按 key 去重，并剔除相邻重复文本
function dedupeSources(
    sources: Array<{ key: string; text: string }>
): Array<{ key: string; text: string }> {
  const result: Array<{ key: string; text: string }> = []
  const seenKeys = new Set<string>()

  for (const source of sources) {
    if (!source.text) continue
    if (seenKeys.has(source.key)) continue

    const last = result[result.length - 1]
    if (last?.text === source.text) continue

    seenKeys.add(source.key)
    result.push(source)
  }

  return result
}

// 按节流节奏从队列取出下一条消息展示，保证每条至少展示 MIN_DISPLAY_MS
function drainQueue() {
  if (!pendingQueue.length) return

  const now = Date.now()
  const elapsed = now - lastDisplayAt

  // 距上次展示不足最小时长，延迟到满足后再消费
  if (lastDisplayAt > 0 && elapsed < MIN_DISPLAY_MS) {
    scheduleDrain(MIN_DISPLAY_MS - elapsed)
    return
  }

  const next = pendingQueue.shift()
  if (!next) return

  consumedKeys.add(next.key)

  // 追加新消息并裁剪到最大可见条数
  visibleMessages.value = [
    ...visibleMessages.value,
    next,
  ].slice(-MAX_VISIBLE_MESSAGES)

  freshMessageId.value = next.id
  lastDisplayAt = Date.now()

  resetFreshTimer()

  // 队列仍有剩余则安排下一轮消费
  if (pendingQueue.length) {
    scheduleDrain(MIN_DISPLAY_MS)
  }
}

// 安排一次延迟消费（防抖：同一时刻只保留一个定时器）
function scheduleDrain(delay: number) {
  if (drainTimer) return

  drainTimer = setTimeout(() => {
    drainTimer = null
    drainQueue()
  }, Math.max(0, delay))
}

// 构造一条带唯一 id 的消息对象
function createMessage(text: string, key: string): LiveMessage {
  messageSeq += 1

  return {
    id: `${props.node.id}-${Date.now()}-${messageSeq}`,
    key,
    text,
  }
}

// 根据日志字段生成稳定去重 key（优先用序号，其次时间戳，最后索引兜底）
function buildLogKey(log: any, index: number) {
  const sequence = log?.sequence ?? log?.seq ?? log?.id
  const timestamp = log?.timestamp ?? log?.createdAt ?? log?.created_at
  const phase = log?.phase ?? ''
  const status = log?.status ?? ''
  const message = String(log?.message || '').trim()

  if (sequence !== undefined && sequence !== null && sequence !== '') {
    return `log:${props.node.id}:${sequence}`
  }

  if (timestamp) {
    return `log:${props.node.id}:${timestamp}:${phase}:${status}:${message}`
  }

  return `log:${props.node.id}:${index}:${phase}:${status}:${message}`
}

// 设置/重置高亮动画定时器，到期后清除高亮标记
function resetFreshTimer() {
  clearFreshTimer()

  freshTimer = setTimeout(() => {
    freshMessageId.value = null
    freshTimer = null
  }, FRESH_ANIMATION_MS)
}

// 清除队列消费定时器
function clearDrainTimer() {
  if (drainTimer) {
    clearTimeout(drainTimer)
    drainTimer = null
  }
}

// 清除高亮动画定时器
function clearFreshTimer() {
  if (freshTimer) {
    clearTimeout(freshTimer)
    freshTimer = null
  }
}

// 组件作用域销毁时清理所有定时器，避免内存泄漏
onScopeDispose(() => {
  clearDrainTimer()
  clearFreshTimer()
})
</script>

<style scoped>
.station-live-log {
  min-height: 78px;
  margin: 12px 0 12px;
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  flex: 1;
  background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.9));
}

.station-live-log.is-running {
  border-color: rgba(59, 130, 246, 0.34);
  background:
      radial-gradient(circle at 12% 0%, rgba(59, 130, 246, 0.08), transparent 42%),
      linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 246, 255, 0.82));
}

.station-live-log.is-success {
  border-color: rgba(16, 185, 129, 0.34);
  background:
      radial-gradient(circle at 12% 0%, rgba(16, 185, 129, 0.08), transparent 42%),
      linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(240, 253, 250, 0.84));
}

.station-live-log.is-failed {
  border-color: rgba(239, 68, 68, 0.28);
  background:
      radial-gradient(circle at 12% 0%, rgba(239, 68, 68, 0.08), transparent 42%),
      linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(254, 242, 242, 0.86));
}

.live-message-queue {
  width: 100%;
  overflow: hidden;
}

.live-message-list {
  display: flex;
  min-height: 54px;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.live-message-row {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  min-height: 24px;
  padding: 2px 0;
}

.live-message-row.is-latest .live-message-only {
  color: var(--color-text);
  font-weight: var(--weight-bold);
}

.live-message-row:not(.is-latest) {
  opacity: 0.68;
}

.live-message-row.is-fresh {
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.06);
}

.fallback-row {
  min-height: 44px;
}

.station-live-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #3B82F6;
  box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.12);
  flex-shrink: 0;
}

.station-live-dot.waiting,
.station-live-dot.skipped {
  background: #94A3B8 !important;
  box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.2) !important;
}

.station-live-dot.running {
  background: #3B82F6 !important;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.25) !important;
  animation: dot-pulse-glow 1.5s infinite ease-in-out !important;
}

.station-live-dot.success {
  background: #10B981 !important;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.25) !important;
}

.station-live-dot.failed {
  background: #EF4444 !important;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.25) !important;
}

.live-message-only {
  margin: 0;
  color: var(--color-text);
  font-size: 0.76rem;
  font-weight: var(--weight-medium);
  line-height: 1.35;
  display: -webkit-box;
  overflow: hidden;
  font-family: var(--agent-body-font);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.live-message-enter-active {
  animation: live-message-enter 0.36s cubic-bezier(0.16, 1, 0.3, 1);
}

.live-message-leave-active {
  display: none;
}

@keyframes live-message-enter {
  0% {
    opacity: 0;
    transform: translateY(8px);
  }

  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes dot-pulse-glow {
  0% {
    transform: scale(0.9);
    opacity: 0.8;
  }

  50% {
    transform: scale(1.15);
    opacity: 1;
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.6), 0 0 0 5px rgba(59, 130, 246, 0.3) !important;
  }

  100% {
    transform: scale(0.9);
    opacity: 0.8;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-message-enter-active,
  .station-live-dot.running {
    animation: none !important;
  }
}
</style>