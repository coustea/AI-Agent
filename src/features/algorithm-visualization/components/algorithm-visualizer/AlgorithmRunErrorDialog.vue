<template>
  <Dialog v-model:open="openModel">
    <DialogContent class="run-error-dialog">
      <DialogHeader>
        <DialogTitle>运行失败</DialogTitle>
        <DialogDescription>
          代码没有生成可视化轨迹，请检查错误信息后再运行。
        </DialogDescription>
      </DialogHeader>

      <div
        v-if="error"
        class="error-body"
      >
        <div class="error-message">{{ error.message }}</div>
        <pre
          v-if="error.details"
          class="error-details"
        >{{ error.details }}</pre>
      </div>

      <DialogFooter>
        <Button @click="openModel = false">知道了</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { RunError } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  open: boolean
  error: RunError | null
}>()

const emit = defineEmits<{
  'update:open': [open: boolean]
}>()

// 弹窗打开状态双向绑定
const openModel = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value),
})
</script>

<style scoped>
:deep(.run-error-dialog) {
  width: min(520px, calc(100vw - 32px));
  border-radius: var(--radius-sm);
  border-color: var(--color-border);
}

.error-body {
  display: grid;
  gap: 10px;
}

.error-message {
  padding: 12px;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  background: var(--color-danger-soft);
  color: var(--color-danger);
  font-size: 13px;
  font-weight: 800;
  line-height: 1.5;
}

.error-details {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}
</style>
