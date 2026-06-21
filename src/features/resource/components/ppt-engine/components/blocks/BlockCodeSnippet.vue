<template>
  <div class="block-code-snippet code-terminal">
    <div class="terminal-header">
      <div class="terminal-dots">
        <span class="dot close"></span>
        <span class="dot minimize"></span>
        <span class="dot expand"></span>
      </div>
      <span class="language-badge">{{ block.language }}</span>
    </div>
    <div class="code-viewport">
      <div class="line-numbers-sidebar">
        <span v-for="n in lineCount" :key="n" class="sidebar-ln">{{ n }}</span>
      </div>
      <pre class="code-content"><code :class="`language-${block.language}`" v-html="highlightedCode"></code></pre>
    </div>
    <div v-if="block.highlights.length > 0" class="code-highlights">
      <div
        v-for="highlight in block.highlights"
        :key="highlight.line"
        class="highlight-note"
      >
        <span class="line-number-badge">Line {{ highlight.line }}</span>
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

const lineCount = computed(() => {
  if (!props.block.code) return 0
  return props.block.code.split('\n').length
})

const highlightedCode = computed(() => {
  try {
    return hljs.highlight(props.block.code, { language: props.block.language }).value
  } catch {
    return props.block.code
  }
})
</script>

<style scoped>
.code-terminal {
  width: 100%;
  border-radius: var(--ppt-radius-md);
  overflow: hidden;
  background: #0B132B;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  background: #1C2541;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.terminal-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.dot.close { background: #FF5F56; }
.dot.minimize { background: #FFBD2E; }
.dot.expand { background: #27C93F; }

.language-badge {
  font-size: 11px;
  font-weight: 800;
  color: #5BC0BE;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  background: rgba(91, 192, 190, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.code-viewport {
  display: flex;
  background: #0B132B;
}

.line-numbers-sidebar {
  display: flex;
  flex-direction: column;
  padding: 16px 8px 16px 16px;
  user-select: none;
  text-align: right;
  border-right: 1px solid rgba(255, 255, 255, 0.03);
}

.sidebar-ln {
  font-family: var(--ppt-font-mono);
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.2);
}

.code-content {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  flex-grow: 1;
}

.code-content code {
  font-family: var(--ppt-font-mono);
  color: #E0E1DD;
}

.code-highlights {
  padding: 16px;
  background: #090E20;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.highlight-note {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--ppt-radius-sm);
  border-left: 3px solid #5BC0BE;
}

.line-number-badge {
  font-size: 11px;
  font-weight: 700;
  color: #5BC0BE;
  background: rgba(91, 192, 190, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--ppt-font-mono);
  white-space: nowrap;
}

.note-text {
  color: #A5A9B4;
  font-size: 0.9rem;
  line-height: 1.4;
}
</style>
