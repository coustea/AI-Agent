<template>
  <div class="mindmap-resource" :class="{ compact }">
    <iframe
      v-if="fileUrl && fileCategory === 'html'"
      :src="fileUrl"
      class="mindmap-frame"
      frameborder="0"
    ></iframe>
    <MarkdownResourceView v-else :result-data="resultData" :compact="compact" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownResourceView from './MarkdownResourceView.vue'
import { getFileCategory, getFileUrl, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const fileUrl = computed(() => getFileUrl(props.resultData))
const fileCategory = computed(() => getFileCategory(fileUrl.value))
</script>

<style scoped>
.mindmap-resource {
  width: 100%;
}

.mindmap-frame {
  width: 100%;
  height: 62vh;
  min-height: 420px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: #fff;
}

.compact .mindmap-frame {
  height: 180px;
  min-height: 180px;
  pointer-events: none;
}
</style>
