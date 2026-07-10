<script setup lang="ts">
// 侧边栏头部
import type { HTMLAttributes } from "vue"
import { cn } from "@/lib/utils"

const props = defineProps<{ class?: HTMLAttributes["class"] }>()
</script>

<template>
  <div
    data-slot="sheet-header"
    :class="cn('gap-0.5 p-4 flex flex-col', props.class)"
  >
    <slot />
  </div>
</template>
