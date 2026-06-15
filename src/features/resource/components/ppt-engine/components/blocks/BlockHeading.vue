<template>
  <component :is="tag" class="block-heading">
    {{ block.content }}
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BlockHeading } from '../../types/ppt'

const props = defineProps<{
  block: BlockHeading
}>()

const tag = computed(() => `h${props.block.level || 2}`)
</script>

<style scoped>
.block-heading {
  color: var(--ppt-text-primary);
  margin-top: 0;
  margin-bottom: 0.5em;
  font-weight: 700;
  line-height: 1.2;
}

h1.block-heading { font-size: 2.5rem; }
h2.block-heading { font-size: 2rem; }
h3.block-heading { font-size: 1.5rem; }
</style>
