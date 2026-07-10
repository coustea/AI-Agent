<script setup lang="ts">
// 弹出框触发器
import type { PopoverTriggerProps } from "reka-ui"
import { PopoverTrigger } from "reka-ui"

const props = defineProps<PopoverTriggerProps>()
</script>

<template>
  <PopoverTrigger
    data-slot="popover-trigger"
    v-bind="props"
  >
    <slot />
  </PopoverTrigger>
</template>
