<template>
  <div class="progress-bar">
    <div class="progress-info">
      <span class="step-count">
        <template v-if="total > 0">
          步骤 {{ current }} / {{ total }}
        </template>
        <template v-else>
          准备就绪
        </template>
      </span>
      <span v-if="message" class="step-message">{{ message }}</span>
    </div>
    <div class="progress-track">
      <div
        class="progress-fill"
        :style="{ width: total > 0 ? `${((current / total) * 100).toFixed(1)}%` : '0%' }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  current: number
  total: number
  message?: string
}>()
</script>

<style scoped>
.progress-bar {
  height: 32px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.step-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  min-width: 100px;
}

.step-message {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.progress-track {
  flex: 1;
  height: 3px;
  background: var(--color-border-light);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.3s ease;
}

@media (max-width: 768px) {
  .progress-bar {
    padding: 0 12px;
  }

  .step-message {
    max-width: 150px;
  }
}
</style>
