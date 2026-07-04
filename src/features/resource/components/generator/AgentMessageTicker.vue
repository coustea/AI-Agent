<template>
  <div class="station-live-log" :class="[`is-${node.status}`]">
    <!-- 单条消息 Ticker 容器 -->
    <div class="ticker-container">
      <Transition name="ticker-slide" mode="out-in">
        <div :key="displayMessage" class="ticker-message" :class="{ 'is-animating': isAnimating }">
          <span class="station-live-dot" :class="node.status"></span>
          <p class="live-message-only">{{ displayMessage || fallbackMessage }}</p>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue'
import type { DagNodeState } from '../../model/catalog'
import { getNodeFallbackMessage } from '../../model/catalog'

const props = defineProps<{
  node: DagNodeState
}>()

// Ticker 参数
const TICK_INTERVAL = 750 // ms (350ms animation + 400ms dwell)
const IDLE_THRESHOLD = 60000 // 60s 无新消息触发idle轮播
const IDLE_INTERVAL = 3000 // idle轮播间隔 3s

const pendingMessages = ref<string[]>([])
const displayMessage = ref<string>('')
const isAnimating = ref(false)
const lastMessageTime = ref(Date.now())
const historyMessages = ref<string[]>([])

let tickerTimer: ReturnType<typeof setInterval> | null = null
let idleTimer: ReturnType<typeof setInterval> | null = null

const fallbackMessage = computed(() => {
  if (props.node.status === 'failed') return props.node.currentMessage || '工位执行受阻，请检查协同日志'
  if (props.node.currentMessage) return props.node.currentMessage
  return getNodeFallbackMessage(props.node)
})

// 监听 currentMessage 变化，入队
watch(
  () => props.node.currentMessage,
  (msg) => {
    const trimmed = msg?.trim()
    if (!trimmed) return

    // 去重
    if (
      pendingMessages.value.includes(trimmed) ||
      displayMessage.value === trimmed ||
      (historyMessages.value.length > 0 && historyMessages.value[historyMessages.value.length - 1] === trimmed)
    ) {
      return
    }

    pendingMessages.value.push(trimmed)
    lastMessageTime.value = Date.now()
    stopIdle()
    startTicker()
  },
  { immediate: true }
)

// 监听 stepHistory，更新idle轮播历史
watch(
  () => props.node.stepHistory?.slice(-2) || [],
  (history) => {
    if (history.length > 0) {
      historyMessages.value = history.filter(Boolean)
    }
  }
)

function startTicker() {
  if (tickerTimer) return
  tickerTimer = setInterval(() => {
    if (pendingMessages.value.length === 0) {
      stopTicker()
      checkIdle()
      return
    }
    const next = pendingMessages.value.shift()!
    displayMessage.value = next
    isAnimating.value = true
    setTimeout(() => {
      isAnimating.value = false
    }, 350)
  }, TICK_INTERVAL)
}

function stopTicker() {
  if (tickerTimer) {
    clearInterval(tickerTimer)
    tickerTimer = null
  }
}

function checkIdle() {
  const elapsed = Date.now() - lastMessageTime.value
  if (elapsed > IDLE_THRESHOLD && historyMessages.value.length >= 2) {
    startIdle()
  }
}

function startIdle() {
  if (idleTimer) return
  let index = 0
  idleTimer = setInterval(() => {
    if (historyMessages.value.length === 0) return
    const msg = historyMessages.value[index]
    if (msg) displayMessage.value = msg
    isAnimating.value = true
    setTimeout(() => {
      isAnimating.value = false
    }, 350)
    index = (index + 1) % historyMessages.value.length
  }, IDLE_INTERVAL)
}

function stopIdle() {
  if (idleTimer) {
    clearInterval(idleTimer)
    idleTimer = null
  }
}

function cleanup() {
  stopTicker()
  stopIdle()
}

onScopeDispose(cleanup)
</script>

<style scoped>
.station-live-log {
  min-height: 78px;
  margin: 12px 0 12px;
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  padding: 11px 12px;
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

.ticker-container {
  position: relative;
  height: 44px;
  overflow: hidden;
}

.ticker-message {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 44px;
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

.live-message-only {
  margin: 0;
  color: var(--color-text);
  font-size: 0.76rem;
  font-weight: var(--weight-bold);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-family: var(--agent-body-font);
}

/* Ticker 动画：新消息从下方滑入，旧消息向上飞出 */
.ticker-slide-enter-active {
  animation: ticker-enter 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.ticker-slide-leave-active {
  animation: ticker-leave 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes ticker-enter {
  0% {
    opacity: 0;
    transform: translateY(100%);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes ticker-leave {
  0% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-100%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ticker-slide-enter-active,
  .ticker-slide-leave-active {
    animation: none;
  }
  .station-live-dot.running {
    animation: none !important;
  }
}
</style>
