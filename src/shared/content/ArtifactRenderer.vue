<template>
  <Slides v-if="type === 'ppt'" :resource="resource" />
  <Video v-else-if="type === 'cartoon'" :result-data="videoData" />
  <MindMap v-else-if="type === 'mindmap'" :result-data="content" />
  <Quiz v-else-if="type === 'quiz'" :result-data="content" />
  <Reading v-else-if="type === 'reading'" :result-data="content" />
  <Markdown v-else :result-data="content" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Markdown from './renderers/Markdown.vue'
import MindMap from './renderers/MindMap.vue'
import Quiz from './renderers/Quiz.vue'
import Reading from './renderers/Reading.vue'
import Slides from './renderers/Slides.vue'
import Video from './renderers/Video.vue'
import type { ResourceArtifactLike } from './artifact'

const props = defineProps<{
  type: string
  content?: ResourceArtifactLike
  resource?: unknown
}>()

const type = computed(() => props.type.trim().toLowerCase())

// 路径资源把视频地址放在 metadata，资源包产物则通常放在 content；统一交给 Video 解析。
const videoData = computed(() => props.resource ?? props.content)
</script>
