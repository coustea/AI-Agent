<template>
  <Transition name="modal-fade">
    <div v-if="isOpen" class="modal-overlay" @click.self="handleOverlayClick">
      <div class="modal-card" role="dialog" aria-modal="true">
        <!-- Close Button (only for errors or confirmations) -->
        <button
          v-if="type === 'error' || type === 'confirm'"
          type="button"
          class="close-btn"
          aria-label="关闭"
          @click="handleClose"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        <!-- Dynamic Icon Container -->
        <div class="icon-container">
          <!-- Success Animation -->
          <svg v-if="type === 'success'" class="status-svg success" viewBox="0 0 52 52">
            <circle class="success-circle" cx="26" cy="26" r="25" fill="none" />
            <path class="success-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" />
          </svg>

          <!-- Confirm / Warning Animation -->
          <svg v-else-if="type === 'confirm'" class="status-svg confirm" viewBox="0 0 52 52">
            <circle class="confirm-circle" cx="26" cy="26" r="25" fill="none" />
            <path class="confirm-mark-path" fill="none" d="M26 15v16 M26 35.5h.01" />
          </svg>

          <!-- Error Animation -->
          <svg v-else class="status-svg error" viewBox="0 0 52 52">
            <circle class="error-circle" cx="26" cy="26" r="25" fill="none" />
            <path class="error-cross-line1" fill="none" d="M16 16l20 20" />
            <path class="error-cross-line2" fill="none" d="M36 16L16 36" />
          </svg>
        </div>

        <!-- Content -->
        <h3 class="modal-title" :class="type">{{ title }}</h3>
        <p class="modal-message">{{ message }}</p>

        <!-- Countdown indicator (if applicable) -->
        <div v-if="type === 'success' && countdown && timeLeft > 0" class="countdown-text">
          <span>{{ timeLeft }}</span> 秒后将自动跳转
        </div>

        <!-- Action Buttons -->
        <div class="action-container" :class="{ 'confirm-layout': type === 'confirm' }">
          <template v-if="type === 'confirm'">
            <button
              type="button"
              class="btn btn-action btn-secondary"
              @click="handleClose"
            >
              {{ cancelButtonText }}
            </button>
            <button
              type="button"
              class="btn btn-action btn-danger"
              @click="handleConfirm"
            >
              {{ primaryButtonText }}
            </button>
          </template>
          <template v-else>
            <button
              type="button"
              class="btn btn-action"
              :class="type === 'success' ? 'btn-primary' : 'btn-danger'"
              @click="handleConfirm"
            >
              {{ primaryButtonText }}
            </button>
          </template>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  type: {
    type: String as () => 'success' | 'error' | 'confirm',
    default: 'success'
  },
  title: {
    type: String,
    required: true
  },
  message: {
    type: String,
    required: true
  },
  countdown: {
    type: Number,
    default: 0
  },
  primaryButtonText: {
    type: String,
    default: '确定'
  },
  cancelButtonText: {
    type: String,
    default: '取消'
  }
})

// 向父组件发出确认或关闭事件
const emit = defineEmits(['confirm', 'close'])

// 倒计时剩余秒数
const timeLeft = ref(0)
// 倒计时定时器 ID，用于清理
let timerId: number | null = null

// 启动倒计时：归零后自动触发 confirm
const startCountdown = () => {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
  
  if (props.countdown > 0) {
    timeLeft.value = props.countdown
    timerId = window.setInterval(() => {
      timeLeft.value -= 1
      if (timeLeft.value <= 0) {
        if (timerId) clearInterval(timerId)
        timerId = null
        emit('confirm')
      }
    }, 1000)
  }
}

// 清除计时器
const clearTimer = () => {
  if (timerId) {
    clearInterval(timerId)
    timerId = null
  }
}

// 监听弹窗开关：打开时按需在成功态启动倒计时，关闭时清定时器
watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal) {
      if (props.type === 'success' && props.countdown > 0) {
        startCountdown()
      }
    } else {
      clearTimer()
    }
  },
  { immediate: true }
)

// 确认按钮：清定时器并通知父组件
const handleConfirm = () => {
  clearTimer()
  emit('confirm')
}

// 关闭按钮：清定时器并通知父组件
const handleClose = () => {
  clearTimer()
  emit('close')
}

// 点击遮罩层：仅错误或确认态允许关闭
const handleOverlayClick = () => {
  if (props.type === 'error' || props.type === 'confirm') {
    handleClose()
  }
}

// 组件卸载前清理定时器，避免内存泄漏
onBeforeUnmount(() => {
  clearTimer()
})
</script>

<style scoped>
/* Modal Transition Styles */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-card {
  animation: modal-zoom-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-fade-leave-active .modal-card {
  animation: modal-zoom-out 0.25s cubic-bezier(0.4, 0, 1, 1);
}

@keyframes modal-zoom-in {
  from {
    transform: scale(0.92) translateY(12px);
  }
  to {
    transform: scale(1) translateY(0);
  }
}

@keyframes modal-zoom-out {
  from {
    transform: scale(1) translateY(0);
  }
  to {
    transform: scale(0.94) translateY(8px);
  }
}

/* Modal Layout */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background-color: rgba(32, 95, 103, 0.06);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
}

.modal-card {
  position: relative;
  width: 100%;
  max-width: 400px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 252, 251, 0.82) 100%);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  box-shadow: 
    0 10px 40px -10px rgba(32, 95, 103, 0.22),
    inset 0 1px 0 0 rgba(255, 255, 255, 0.8);
  padding: 36px 28px 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

/* Close Button styling */
.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.04);
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.08);
  color: var(--color-text-strong);
}

/* Icon Containers & SVG Animations */
.icon-container {
  width: 72px;
  height: 72px;
  margin-bottom: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-svg {
  width: 68px;
  height: 68px;
  display: block;
}

/* Success SVG Keyframes */
.success-circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 3;
  stroke-miterlimit: 10;
  stroke: var(--color-primary);
  animation: stroke-draw 0.5s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

.success-check {
  transform-origin: 50% 50%;
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke: var(--color-primary);
  animation: stroke-draw 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.45s forwards;
}

/* Confirm SVG Keyframes */
.confirm-circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 3;
  stroke-miterlimit: 10;
  stroke: #F59E0B;
  animation: stroke-draw 0.5s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

.confirm-mark-path {
  stroke-dasharray: 30;
  stroke-dashoffset: 30;
  stroke-width: 4;
  stroke-linecap: round;
  stroke: #F59E0B;
  animation: stroke-draw 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.4s forwards;
}

/* Error SVG Keyframes */
.error-circle {
  stroke-dasharray: 166;
  stroke-dashoffset: 166;
  stroke-width: 3;
  stroke-miterlimit: 10;
  stroke: var(--color-danger);
  animation: stroke-draw 0.5s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}

.error-cross-line1 {
  stroke-dasharray: 40;
  stroke-dashoffset: 40;
  stroke-width: 4;
  stroke-linecap: round;
  stroke: var(--color-danger);
  animation: stroke-draw 0.25s cubic-bezier(0.65, 0, 0.45, 1) 0.4s forwards;
}

.error-cross-line2 {
  stroke-dasharray: 40;
  stroke-dashoffset: 40;
  stroke-width: 4;
  stroke-linecap: round;
  stroke: var(--color-danger);
  animation: stroke-draw 0.25s cubic-bezier(0.65, 0, 0.45, 1) 0.55s forwards;
}

@keyframes stroke-draw {
  to {
    stroke-dashoffset: 0;
  }
}

/* Typography & Layout */
.modal-title {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.modal-title.success {
  color: var(--color-primary-text);
}

.modal-title.confirm {
  color: #D97706;
}

.modal-title.error {
  color: var(--color-danger);
}

.modal-message {
  margin: 0 0 20px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  max-width: 300px;
  word-wrap: break-word;
}

.countdown-text {
  font-size: 13px;
  color: var(--color-text-muted);
  margin-bottom: 22px;
}

.countdown-text span {
  font-weight: 700;
  color: var(--color-primary-text);
}

.action-container {
  width: 100%;
}

.confirm-layout {
  display: flex;
  gap: 12px;
  width: 100%;
}

.btn-action {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: filter var(--transition-fast), transform var(--transition-fast);
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
}

.btn-secondary {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-secondary);
}

.btn-secondary:hover {
  background: rgba(0, 0, 0, 0.08);
}

.btn-danger {
  background: var(--color-danger);
  color: #fff;
}

.btn-action:hover {
  filter: brightness(1.08);
}

.btn-action:active {
  transform: scale(0.98);
}
</style>
