<template>
  <div class="onboarding-preview-container">
    <OnboardingDialog v-model="visible" @success="handleSuccess" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import OnboardingDialog from '@/components/OnboardingDialog.vue'

const visible = ref(true)
//预览样式使用的vue（最终需要删除）
const handleSuccess = () => {
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
