<script setup lang="ts">
// 选择器选中值展示
import type { SelectValueProps } from "reka-ui"
import { SelectValue } from "reka-ui"

const props = defineProps<SelectValueProps>()
</script>

<template>
  <SelectValue
    data-slot="select-value"
    v-bind="props"
  >
    <slot />
  </SelectValue>
</template>
