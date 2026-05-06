<template>
  <div class="digital-human-canvas">
    <div ref="videoContainer" class="video-container"></div>
    <div v-if="!isReady" class="placeholder">
      <div v-if="isConnected" class="spinner"></div>
      <el-icon v-else class="placeholder-icon"><Avatar /></el-icon>
      <p>{{ isConnected ? '等待数字人上线...' : '数字人未连接' }}</p>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { Avatar } from '@element-plus/icons-vue'

defineProps<{
  isReady: boolean
  isConnected: boolean
  audioEnabled: boolean
}>()

defineEmits<{
  'enable-audio': []
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
</style>
