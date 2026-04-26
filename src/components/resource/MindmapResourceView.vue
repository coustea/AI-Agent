<template>
  <div class="mindmap-resource" :class="{ compact }">
    <iframe
      v-if="fileUrl && fileCategory === 'html'"
      :src="fileUrl"
      class="mindmap-frame"
      title="思维导图在线预览"
      frameborder="0"
      loading="lazy"
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
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.compact .mindmap-frame {
  height: 180px;
  min-height: 180px;
  pointer-events: none;
}

@media (max-width: 768px) {
  .mindmap-frame {
    height: 58vh;
    min-height: 320px;
  }

  .compact .mindmap-frame {
    height: 160px;
    min-height: 160px;
  }
}
</style>
