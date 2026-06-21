<template>
  <div class="block-code-snippet">
    <div class="code-header">
      <span class="language-badge">{{ block.language }}</span>
    </div>
    <pre class="code-content"><code :class="`language-${block.language}`" v-html="highlightedCode"></code></pre>
    <div v-if="block.highlights.length > 0" class="code-highlights">
      <div
        v-for="highlight in block.highlights"
        :key="highlight.line"
        class="highlight-note"
      >
        <span class="line-number">L{{ highlight.line }}</span>
        <span class="note-text">{{ highlight.note }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CodeSnippetBlock } from '../../types/ppt'
import hljs from 'highlight.js'

const props = defineProps<{
  block: CodeSnippetBlock
}>()

const highlightedCode = computed(() => {
  try {
    return hljs.highlight(props.block.code, { language: props.block.language }).value
  } catch {
    return props.block.code
  }
})
</script>

<style scoped>
.block-code-snippet {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background: #1e293b;
}

.code-header {
  padding: 8px 12px;
  background: #334155;
  border-bottom: 1px solid #475569;
}

.language-badge {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
}

.code-content {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}

.code-content code {
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  color: #e2e8f0;
}

.code-highlights {
  padding: 12px;
  background: #0f172a;
  border-top: 1px solid #475569;
}

.highlight-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.line-number {
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 4px;
  background: #334155;
  color: #94a3b8;
  font-family: monospace;
}

.note-text {
  color: #cbd5e1;
  line-height: 1.4;
}
</style>
