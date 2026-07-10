<script setup lang="ts">
// 头像图片
import type { AvatarImageProps } from "reka-ui"
import { AvatarImage } from "reka-ui"

const props = defineProps<AvatarImageProps>()
</script>

<template>
  <AvatarImage
    data-slot="avatar-image"
    v-bind="props"
    class="rounded-full aspect-square size-full object-cover"
  >
    <slot />
  </AvatarImage>
</template>
