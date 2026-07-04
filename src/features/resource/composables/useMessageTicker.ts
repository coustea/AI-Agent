import { ref, computed, watch, onScopeDispose } from 'vue'
import type { DagNodeState } from '../model/catalog'

export function useMessageTicker(_nodeId: string, nodeGetter: () => DagNodeState | undefined) {
  const pendingMessages = ref<string[]>([])
  const displayedMessage = ref<string>('')
  const isAnimating = ref(false)
  const lastMessageTime = ref(Date.now())
  const historyMessages = ref<string[]>([])

  // Ticker节奏参数
  const TICK_INTERVAL = 750 // ms (350ms animation + 400ms dwell)
  const IDLE_THRESHOLD = 60000 // 60s 无新消息触发idle轮播
  const IDLE_INTERVAL = 3000 // idle轮播间隔 3s

  let tickerTimer: ReturnType<typeof setInterval> | null = null
  let idleTimer: ReturnType<typeof setInterval> | null = null

  // 监听节点消息变化，入队
  watch(
    () => {
      const node = nodeGetter()
      const currentMsg = node?.currentMessage?.trim()
      const _history = node?.stepHistory || []
      return { currentMsg, _history }
    },
    ({ currentMsg, _history: _h }) => {
      if (!currentMsg) return

      // 去重：如果消息已在pending或刚显示，不重复入队
      if (
        pendingMessages.value.includes(currentMsg) ||
        displayedMessage.value === currentMsg ||
        (historyMessages.value.length > 0 && historyMessages.value[historyMessages.value.length - 1] === currentMsg)
      ) {
        return
      }

      pendingMessages.value.push(currentMsg)
      lastMessageTime.value = Date.now()

      // 停止idle轮播，启动ticker消费
      stopIdle()
      startTicker()
    },
    { immediate: true }
  )

  // 监听history变化，记录最近2条用于idle轮播
  watch(
    () => nodeGetter()?.stepHistory?.slice(-2) || [],
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
        // 检查是否进入idle
        checkIdle()
        return
      }
      const next = pendingMessages.value.shift()!
      displayedMessage.value = next
      isAnimating.value = true

      // 动画标记，350ms后解除
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
      if (msg) displayedMessage.value = msg
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

  return {
    displayedMessage,
    isAnimating,
    pendingCount: computed(() => pendingMessages.value.length),
  }
}