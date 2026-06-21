<template>
  <ResourceBundleView
    :bundle="finalBundle"
    :warning="resultWarning"
    action-label="新建任务"
    action-kind="reset"
    @action="emit('reset')"
    @preview="emit('preview', $event)"
  />
</template>

<script setup lang="ts">
import ResourceBundleView from '@/features/resource/components/ResourceBundleView.vue'

defineProps<{
  finalBundle: any | null
  resultWarning: string
}>()

const emit = defineEmits<{
  reset: []
  preview: [
    data: {
      agentId: string
      resultData: any
      title: string
    },
  ]
}>()
</script>
