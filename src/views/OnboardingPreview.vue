<template>
  <div class="onboarding-preview-container">
    <OnboardingDialog v-model="visible" @success="handleSuccess" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import OnboardingDialog from '@/components/OnboardingDialog.vue'

const visible = ref(true)

const handleSuccess = () => {
  // 预览模式下关闭后自动重新打开，方便重复调试样式
  setTimeout(() => {
    visible.value = true
  }, 500)
}
</script>

<style scoped>
.onboarding-preview-container {
  width: 100vw;
  height: 100vh;
  background-color: var(--color-bg, #f8fafc);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
