<template>
  <div class="digital-human-canvas">
    <div ref="videoContainer" class="video-container"></div>

    <!-- Not ready states (connecting / disconnected) -->
    <div v-if="!isReady" class="placeholder">
      <template v-if="isConnected">
        <div class="spinner"></div>
        <p>等待数字人上线...</p>
      </template>
      <template v-else>
        <el-icon class="placeholder-icon"><Avatar /></el-icon>
        <p>数字人未连接</p>
        <button class="reconnect-btn" @click="$emit('reconnect')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          重新连接
        </button>
      </template>
    </div>

    <!-- Audio enable button -->
    <div v-if="isReady && !audioEnabled" class="audio-enable-overlay">
      <button class="audio-enable-btn" @click="$emit('enable-audio')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
        </svg>
        点击启用音频
      </button>
    </div>

    <!-- Disconnect button + idle countdown -->
    <div v-if="isConnected" class="disconnect-bar">
      <span v-if="idleCountdown > 0 && idleCountdown <= 10" class="idle-hint">
        {{ idleCountdown }}s 后自动断开
      </span>
      <button class="disconnect-btn" @click="$emit('disconnect')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
        断开连接
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { Avatar } from '@element-plus/icons-vue'

defineProps<{
  isReady: boolean
  isConnected: boolean
  audioEnabled: boolean
  idleCountdown: number
}>()

defineEmits<{
  'enable-audio': []
  'disconnect': []
  'reconnect': []
}>()

const videoContainer = ref<HTMLElement | null>(null)

// Expose the container ref so parent can pass it to composable.setPlayerContainer
defineExpose({
  getContainer: () => videoContainer.value,
})

onBeforeUnmount(() => {
  if (videoContainer.value) {
    while (videoContainer.value.firstChild) {
      videoContainer.value.removeChild(videoContainer.value.firstChild)
    }
  }
})
</script>

<style scoped>
.digital-human-canvas {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.video-container {
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
}

.video-container :deep(video) {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #94A3AF;
  font-size: 0.85rem;
  z-index: 1;
}

.placeholder-icon {
  font-size: 3rem;
  opacity: 0.4;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(79, 70, 229, 0.2);
  border-top-color: #4F46E5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.reconnect-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: #4F46E5;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.reconnect-btn:hover {
  background: #4338CA;
  transform: scale(1.05);
}

.audio-enable-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
}

.audio-enable-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: rgba(79, 70, 229, 0.9);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4);
  transition: all 0.2s;
  animation: pulse-btn 2s infinite;
}

.audio-enable-btn:hover {
  background: rgba(79, 70, 229, 1);
  transform: scale(1.05);
}

@keyframes pulse-btn {
  0%, 100% { box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4); }
  50% { box-shadow: 0 4px 24px rgba(79, 70, 229, 0.8); }
}

.disconnect-bar {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 10;
}

.idle-hint {
  font-size: 0.7rem;
  color: #F59E0B;
  background: rgba(245, 158, 11, 0.1);
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 500;
  animation: idle-pulse 1s infinite;
}

@keyframes idle-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.disconnect-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.85);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(4px);
}

.disconnect-btn:hover {
  background: rgba(239, 68, 68, 1);
  transform: scale(1.05);
}
</style>
