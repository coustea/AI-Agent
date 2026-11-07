<template>
  <div class="tutor-message-content">
    <MarkdownRenderer
      class="stream-markdown markdown-body tutor-markdown-block"
      :class="{ 'is-streaming': props.isStreaming }"
      :content="props.content"
      :streaming="props.isStreaming"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()
</script>

<style scoped>
.tutor-message-content {
  min-width: 0;
}

.tutor-markdown-block {
  min-width: 0;
}

.stream-markdown {
  min-width: 0;
  color: var(--color-text);
  font-size: 0.96875rem;
  line-height: 1.76;
  overflow-wrap: anywhere;
  text-wrap: pretty;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

/* 冰川青流体呼吸光标 */
.stream-markdown :deep(.markdown-stream-caret) {
  display: inline-block;
  width: 3px;
  height: 1.08em;
  margin-left: 4px;
  background: var(--color-primary);
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(70, 184, 180, 0.48);
  vertical-align: -0.14em;
  content: '';
  animation: stream-caret-breathe 1.05s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.stream-markdown :deep(.stream-caret-line) {
  margin: 0;
  min-height: 1.5em;
}

.stream-markdown :deep(p) {
  margin: 0 0 0.85rem;
}

.stream-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.stream-markdown :deep(h1),
.stream-markdown :deep(h2),
.stream-markdown :deep(h3),
.stream-markdown :deep(h4) {
  margin: 1.35rem 0 0.55rem;
  color: var(--color-text-strong);
  font-weight: 700;
  line-height: 1.36;
  letter-spacing: -0.02em;
  text-wrap: balance;
}

.stream-markdown :deep(h1:first-child),
.stream-markdown :deep(h2:first-child),
.stream-markdown :deep(h3:first-child),
.stream-markdown :deep(h4:first-child) {
  margin-top: 0.15rem;
}

.stream-markdown :deep(h1) { font-size: 1.25rem; }
.stream-markdown :deep(h2) { font-size: 1.14rem; }
.stream-markdown :deep(h3) { font-size: 1.04rem; }
.stream-markdown :deep(h4) { font-size: 0.98rem; }

.stream-markdown :deep(ul),
.stream-markdown :deep(ol) {
  display: grid;
  gap: 0.34rem;
  margin: 0.65rem 0 0.9rem;
  padding-left: 1.4rem;
}

.stream-markdown :deep(li) {
  padding-left: 0.15rem;
  line-height: 1.72;
}

.stream-markdown :deep(li::marker) {
  color: var(--color-primary);
  font-weight: 600;
}

.stream-markdown :deep(strong) {
  color: var(--color-text-strong);
  font-weight: 650;
}

.stream-markdown :deep(a) {
  color: var(--color-primary-text);
  font-weight: 500;
  text-decoration: underline;
  text-decoration-color: var(--color-primary-border);
  text-underline-offset: 3px;
  transition: color 150ms ease, text-decoration-color 150ms ease;
}

.stream-markdown :deep(a:hover) {
  color: var(--color-primary);
  text-decoration-color: var(--color-primary);
}

/* 学术引言框：完整细边框 + 冰川浅底（杜绝粗侧边条反模式） */
.stream-markdown :deep(blockquote) {
  margin: 0.95rem 0;
  padding: 0.75rem 1rem;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
}

.stream-markdown :deep(blockquote p:last-child) {
  margin-bottom: 0;
}

.stream-markdown :deep(hr) {
  margin: 1.25rem 0;
  border: 0;
  border-top: 1px solid var(--color-border-light);
}

.stream-markdown :deep(table) {
  display: table;
  width: 100%;
  margin: 1rem 0;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: 0.9rem;
  background: var(--color-surface);
}

.stream-markdown :deep(th),
.stream-markdown :deep(td) {
  padding: 0.68rem 0.85rem;
  border-right: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
  text-align: left;
  vertical-align: top;
}

.stream-markdown :deep(th:last-child),
.stream-markdown :deep(td:last-child) {
  border-right: 0;
}

.stream-markdown :deep(tr:last-child td) {
  border-bottom: 0;
}

.stream-markdown :deep(th) {
  color: var(--color-text-strong);
  background: var(--color-bg);
  font-weight: 650;
}

.stream-markdown :deep(tr:nth-child(even) td) {
  background: color-mix(in srgb, var(--color-bg) 45%, var(--color-surface));
}

.stream-markdown :deep(code:not(pre code)) {
  padding: 0.14rem 0.4rem;
  color: var(--color-primary-text);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: 5px;
  font-size: 0.875em;
  font-weight: 500;
}

.stream-markdown :deep(.hljs-comment),
.stream-markdown :deep(.hljs-quote) {
  color: #329a82 !important;
  font-style: normal;
}

.stream-markdown :deep(.code-block-wrapper) {
  margin: 1rem 0;
  overflow: hidden;
  background: #fbfdfd;
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.stream-markdown :deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 38px;
  padding: 0.45rem 0.85rem;
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border-light);
}

.stream-markdown :deep(.code-block-lang) {
  min-width: 0;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 650;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  user-select: none;
  white-space: nowrap;
}

.stream-markdown :deep(.code-block-copy-btn) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  height: 26px;
  padding: 0 9px;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.72rem;
  font-weight: 500;
  transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
}

.stream-markdown :deep(.code-block-copy-btn:hover) {
  color: var(--color-text-strong);
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
}

.stream-markdown :deep(.code-block-copy-btn.copied) {
  color: var(--color-success);
  border-color: var(--color-primary-border);
  background: var(--color-success-soft);
}

.stream-markdown :deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 14px 16px;
  overflow-x: auto;
  background: transparent;
  font-size: 0.875rem;
  line-height: 1.68;
}

.stream-markdown :deep(.code-block-wrapper code) {
  font-family: var(--font-mono);
}

@keyframes stream-caret-breathe {
  0%, 100% {
    opacity: 1;
    transform: scaleY(1);
  }
  50% {
    opacity: 0.2;
    transform: scaleY(0.88);
  }
}

@media (max-width: 640px) {
  .stream-markdown {
    font-size: 0.9375rem;
    line-height: 1.7;
  }

  .stream-markdown :deep(table) {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stream-markdown :deep(.markdown-stream-caret) {
    animation: none;
  }
}
</style>
