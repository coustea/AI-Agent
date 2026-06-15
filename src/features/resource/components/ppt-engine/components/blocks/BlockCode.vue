<template>
  <div class="block-code">
    <div class="code-header">
      <div class="mac-buttons">
        <span class="btn close"></span>
        <span class="btn min"></span>
        <span class="btn max"></span>
      </div>
      <div class="lang-label" v-if="block.language">{{ block.language }}</div>
    </div>
    <pre><code :class="`language-${block.language}`">{{ block.code }}</code></pre>
  </div>
</template>

<script setup lang="ts">
import type { BlockCode } from '../../types/ppt'

defineProps<{
  block: BlockCode
}>()
</script>

<style scoped>
.block-code {
  background-color: var(--ppt-code-block-bg);
  border-radius: var(--ppt-radius);
  overflow: hidden;
  margin-bottom: 1em;
  box-shadow: var(--ppt-shadow);
  border: 1px solid var(--ppt-border);
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background-color: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.mac-buttons {
  display: flex;
  gap: 6px;
}

.btn {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.close { background-color: #ff5f56; }
.min { background-color: #ffbd2e; }
.max { background-color: #27c93f; }

.lang-label {
  color: var(--ppt-code-block-text);
  font-size: 0.8rem;
  opacity: 0.7;
  text-transform: uppercase;
}

pre {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
}

code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--ppt-code-block-text);
}
</style>
