<template>
  <article class="teaching-diagram-image">
    <img v-if="imageUrl" :src="imageUrl" :alt="title" />
    <footer v-if="imageUrl">
      <strong>{{ title }}</strong>
      <a :href="imageUrl" :download="`${title || '教学图解'}.png`">下载 PNG</a>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  imageUrl?: string
  image_url?: string
}>()
const imageUrl = computed(() => props.imageUrl ?? props.image_url ?? '')
</script>

<style scoped>
.teaching-diagram-image { overflow: hidden; border: 1px solid var(--color-border); border-radius: 12px; background: var(--color-surface); }
.teaching-diagram-image img { display: block; width: 100%; height: auto; }
.teaching-diagram-image footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; }
.teaching-diagram-image a { color: var(--color-primary); font-size: 13px; }
</style>
