<template>
  <div class="block-terminal">
    <div class="terminal-header">
      <div class="mac-buttons">
        <span class="btn close"></span>
        <span class="btn min"></span>
        <span class="btn max"></span>
      </div>
      <div class="term-title">Terminal</div>
    </div>
    <div class="terminal-body">
      <div class="command" v-if="block.command">
        <span class="prompt">$</span> {{ block.command }}
      </div>
      <pre class="output">{{ block.output }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BlockTerminal } from '../../types/ppt'

defineProps<{
  block: BlockTerminal
}>()
</script>

<style scoped>
.block-terminal {
  background-color: #000000;
  border-radius: var(--ppt-radius);
  overflow: hidden;
  margin-bottom: 1em;
  box-shadow: var(--ppt-shadow);
  border: 1px solid #333;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background-color: #333;
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

.term-title {
  color: #ccc;
  font-size: 0.8rem;
  font-family: sans-serif;
  flex-grow: 1;
  text-align: center;
  margin-right: 48px; /* Offset buttons width for centering */
}

.terminal-body {
  padding: 16px;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 0.9rem;
  line-height: 1.5;
}

.command {
  color: #fff;
  margin-bottom: 8px;
}

.prompt {
  color: #4ade80;
  margin-right: 8px;
}

.output {
  color: #94a3b8;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
