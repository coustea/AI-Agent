<template>
  <section class="error-state-panel" v-loading="isLoading">
    <div class="error-content">
      <div class="error-icon-area">
        <div class="error-icon-ring">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
      </div>

      <span class="error-badge">{{ isLoading ? '加载中' : '加载失败' }}</span>

      <h2 class="error-title">{{ isLoading ? loadingTitle : errorTitle }}</h2>

      <p class="error-message">{{ isLoading ? loadingMessage : (errorMessage || defaultMessage) }}</p>

      <div class="error-actions" v-if="!isLoading && showRetry">
        <BaseButton class="error-retry-btn" @click="handleRetry">
          <el-icon><RefreshRight /></el-icon>
          重新加载
        </BaseButton>
      </div>

      <div class="error-meta" v-if="!isLoading">
        <span class="error-code" v-if="errorCode">{{ errorCode }}</span>
        <span class="error-time">{{ currentTime }}</span>
      </div>
    </div>

    <div class="error-decoration">
      <div class="error-blob blob-1"></div>
      <div class="error-blob blob-2"></div>
      <div class="error-grid"></div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import BaseButton from '@/shared/ui/BaseButton.vue'

const props = withDefaults(defineProps<{
  isLoading?: boolean
  loadingTitle?: string
  loadingMessage?: string
  errorTitle?: string
  errorMessage?: string
  defaultMessage?: string
  errorCode?: string
  showRetry?: boolean
}>(), {
  isLoading: false,
  loadingTitle: '正在同步数据',
  loadingMessage: '正在读取服务器数据，请稍候...',
  errorTitle: '数据加载失败',
  defaultMessage: '暂时无法获取数据，请检查网络连接后重试',
  showRetry: true
})

const emit = defineEmits<{
  retry: []
}>()

const handleRetry = () => {
  emit('retry')
}

const currentTime = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(new Date())
})
</script>

<style scoped>
.error-state-panel {
  min-height: 360px;
  max-width: 520px;
  margin: 0 auto;
  position: relative;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.error-content {
  position: relative;
  z-index: 2;
  max-width: 360px;
  text-align: center;
}

.error-icon-area {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-5);
}

.error-icon-ring {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 8px rgba(239, 68, 68, 0.1);
}

.error-badge {
  display: inline-flex;
  align-items: center;
  color: var(--color-danger);
  background: var(--color-danger-soft);
  border-radius: var(--radius-pill);
  padding: var(--space-1) var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  margin-bottom: var(--space-4);
}

.error-title {
  margin: 0 0 var(--space-3) 0;
  color: var(--color-text-strong);
  font-size: var(--text-xl);
  font-weight: var(--weight-extrabold);
  line-height: 1.25;
}

.error-message {
  margin: 0 0 var(--space-6) 0;
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
}

.error-actions {
  display: flex;
  justify-content: center;
  margin-bottom: var(--space-5);
}

.error-retry-btn {
  min-width: 140px;
  justify-content: center;
}

.error-meta {
  display: flex;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-faint);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
}

.error-code {
  padding: 2px var(--space-2);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.error-decoration {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

.error-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.4;
}

.blob-1 {
  width: 200px;
  height: 200px;
  top: -40px;
  right: -40px;
  background: rgba(239, 68, 68, 0.2);
}

.blob-2 {
  width: 160px;
  height: 160px;
  bottom: -30px;
  left: -30px;
  background: rgba(249, 115, 22, 0.15);
}

.error-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(239, 68, 68, 0.06) 1px, transparent 1px);
  background-size: 24px 24px;
}

@media (max-width: 640px) {
  .error-state-panel {
    min-height: 280px;
    padding: var(--space-6);
    margin: var(--space-4);
    border-radius: var(--radius-lg);
  }

  .error-title {
    font-size: var(--text-lg);
  }

  .error-message {
    font-size: var(--text-sm);
  }
}
</style>