<template>
  <div class="code-resource" :class="{ compact }">
    <Frame v-if="rendererContent" :compact="compact" class="code-card-content">
      <div v-if="!compact && parsedData?.explanation" class="code-header-meta">
        <span class="code-summary-text">{{ parsedData.explanation }}</span>
      </div>

      <div class="code-main-body">
        <MarkdownRenderer
          class="markdown-shell code-markdown-shell"
          :content="rendererContent"
        />
      </div>

      <div v-if="!compact && hasExtraInfo" class="code-footer-extras">
        <div class="footer-divider">
          <span class="divider-label">实现指标</span>
          <div class="divider-line"></div>
        </div>

        <div class="extras-grid">
          <div v-if="hasComplexity" class="extra-item complexity-info">
            <div class="extra-label"><Timer class='w-4 h-4 inline-block align-middle' /> 复杂度分析</div>
            <div class="extra-content">
              <span v-if="parsedData?.complexity?.time">时间: <code>{{ parsedData!.complexity!.time }}</code></span>
              <span v-if="parsedData?.complexity?.space" class="ml-4">空间: <code>{{ parsedData!.complexity!.space }}</code></span>
            </div>
          </div>

          <div v-if="parsedData?.debug_tips?.length" class="extra-item tips-info">
            <div class="extra-label"><Warning class='w-4 h-4 inline-block align-middle' /> 调试建议</div>
            <ul class="tips-list">
              <li v-for="(tip, idx) in parsedData!.debug_tips" :key="idx">{{ tip }}</li>
            </ul>
          </div>
        </div>

        <div v-if="parsedData?.exercises?.length" class="extra-item exercises-info">
          <div class="extra-label"><EditPen class='w-4 h-4 inline-block align-middle' /> 练习序列</div>
          <div class="exercises-container">
            <div v-for="(ex, idx) in parsedData!.exercises" :key="idx" class="exercise-item">
              <span class="ex-num">{{ (Number(idx) + 1).toString().padStart(2, '0') }}</span>
              <span class="ex-text">{{ typeof ex === 'string' ? ex : ex.question || ex.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="frame-footer">
        <span class="mono-tag">可执行</span>
        <div class="footer-line"></div>
      </div>
    </Frame>

    <div v-else class="code-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>未检测到代码内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  PhClock as Timer,
  PhWarning as Warning,
  PhNotePencil as EditPen
} from '@phosphor-icons/vue'
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'
import Frame from '../Frame.vue'
import { parseJsonObject, type ResourceArtifactLike } from '../artifact'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

function toText(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
}

function looksLikeMarkdownDocument(text: string): boolean {
  if (!text.trim()) return false

  const fenceCount = text.match(/```/g)?.length ?? 0
  if (fenceCount >= 2) return true

  const hasMarkdownTitle = /(^|\n)#{1,4}\s+\S/.test(text)
  const hasMarkdownList = /(^|\n)([-*]|\d+\.)\s+\S/.test(text)
  const hasCodeSignals = /(^|\n)\s*(import|from|def|class|#include|public\s+class|function|const|let|var)\b/.test(text)

  return hasMarkdownTitle && hasMarkdownList && !hasCodeSignals
}

function toFencedMarkdown(code: string, language: unknown): string {
  const longestFence = Math.max(0, ...Array.from(code.matchAll(/`+/g), (match) => match[0].length))
  const fence = '`'.repeat(Math.max(3, longestFence + 1))
  const languageName = toText(language || 'text').trim().toLowerCase().replace(/\s+/g, '-')
  return `${fence}${languageName}\n${code.trimEnd()}\n${fence}`
}

const parsedData = computed(() => {
  if (!props.resultData) return null

  let raw: unknown = props.resultData
  if (typeof raw === 'string') {
    const parsed = parseJsonObject(raw)
    if (!parsed) return null
    raw = parsed
  }

  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null

  let data = raw as Record<string, any>
  if (data.resource && typeof data.resource === 'object' && !Array.isArray(data.resource)) {
    data = data.resource
  }

  const content = data.content
  if (content && typeof content === 'object' && !Array.isArray(content)) {
    return content as Record<string, any>
  }

  const parsedContent = parseJsonObject(content)
  if (parsedContent) return parsedContent

  if (data.code || data.full_code || data.markdown || data.markdown_content || data.language) return data

  return null
})

const rendererContent = computed(() => {
  const data = parsedData.value
  if (!data) return typeof props.resultData === 'string' ? props.resultData : ''

  const explicitMarkdown = data.markdown || data.markdown_content || data.document || data.content_markdown
  if (typeof explicitMarkdown === 'string' && explicitMarkdown.trim()) return explicitMarkdown

  const codeContent = toText(data.code || data.full_code || '')
  if (!codeContent.trim() || looksLikeMarkdownDocument(codeContent)) return codeContent
  return toFencedMarkdown(codeContent, data.language || data.lang || 'text')
})

const hasExtraInfo = computed(() => {
  const data = parsedData.value
  return !!(data?.complexity?.time || data?.complexity?.space || data?.debug_tips?.length || data?.exercises?.length)
})

const hasComplexity = computed(() => {
  const complexity = parsedData.value?.complexity
  return !!(complexity?.time || complexity?.space)
})
</script>

<style scoped>
.code-resource {
  min-width: 0;
  width: 100%;
  --primary: var(--color-primary);
  --bg: var(--color-surface);
  --fg: var(--color-text);
  --border: var(--color-border);
  --accent: var(--color-primary);
  --code-bg: var(--color-bg);
  --code-head-bg: var(--color-surface-hover);
  --code-border: var(--color-border);
  --code-text: var(--color-text-strong);
}

.code-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.code-main-body {
  min-width: 0;
}

.code-header-meta {
  margin-bottom: 4px;
}

.code-summary-text {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.6;
}

.markdown-shell {
  min-width: 0;
  color: var(--fg);
  line-height: 1.78;
  overflow-wrap: anywhere;
  font-family: var(--font-sans);
  font-size: 0.96rem;
}

.code-markdown-shell :deep(h1),
.code-markdown-shell :deep(h2),
.code-markdown-shell :deep(h3) {
  margin: 1.7em 0 0.85em;
  padding-bottom: 0.48em;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-strong);
  font-family: var(--font-sans);
  line-height: 1.35;
  font-weight: 700;
}

.code-markdown-shell :deep(h1) { font-size: 1.42rem; }
.code-markdown-shell :deep(h2) { font-size: 1.18rem; }
.code-markdown-shell :deep(h3) { font-size: 1.02rem; }

.code-markdown-shell :deep(p) {
  margin: 0.85em 0;
  color: var(--color-text-secondary);
}

.code-markdown-shell :deep(ul),
.code-markdown-shell :deep(ol) {
  padding-left: 1.35em;
  margin: 0.85em 0;
}

.code-markdown-shell :deep(li) { margin: 0.35em 0; }

.code-markdown-shell :deep(blockquote) {
  margin: 1em 0;
  padding: 10px 14px;
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-text-secondary);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
}

/* --- 重构的代码块卡片外观 --- */

.code-resource :deep(.code-block-wrapper) {
  margin: 1.2em 0;
  border: 1px solid var(--code-border);
  border-radius: var(--radius-md);
  background: var(--code-bg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.code-resource :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--code-head-bg);
  border-bottom: 1px solid var(--code-border);
}

.code-resource :deep(.lang-label) {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.code-resource :deep(.code-block-wrapper pre) {
  margin: 0 !important;
  padding: 18px !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  overflow-x: auto;
  overflow-y: hidden;
}

.code-resource :deep(pre code),
.code-resource :deep(.code-block-wrapper code) {
  display: block;
  min-width: max-content;
  padding: 0;
  background: transparent !important;
  color: var(--code-text) !important;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.76;
  white-space: pre;
  tab-size: 4;
}

.code-resource :deep(pre::-webkit-scrollbar) {
  width: 10px;
  height: 10px;
}

.code-resource :deep(pre::-webkit-scrollbar-track) {
  background: transparent;
}

.code-resource :deep(pre::-webkit-scrollbar-thumb) {
  border: 3px solid transparent;
  border-radius: 999px;
  background-clip: padding-box;
  background-color: var(--color-border-hover);
}

.code-resource :deep(pre::-webkit-scrollbar-thumb:hover) {
  background-color: var(--color-primary-border);
}

/* 行内小代码块样式 */
.code-resource :deep(:not(pre) > code) {
  padding: 0.16em 0.42em;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg) !important;
  color: var(--color-primary-text);
  font-family: var(--font-mono);
  font-size: 0.86em;
  font-weight: 600;
}

/* --- 底部执行标签栏 --- */

.frame-footer {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.mono-tag {
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid var(--color-success-border, var(--color-border));
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

/* --- 复杂度及练习题样式 --- */

.code-footer-extras {
  margin-top: 16px;
  padding: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
}

.footer-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.divider-label {
  font-family: var(--font-sans);
  font-size: 0.75rem;
  color: var(--color-primary-text);
  letter-spacing: 0.5px;
  font-weight: 700;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--color-border), transparent);
}

.extras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}

.extra-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.extra-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-primary-text);
  font-family: var(--font-sans);
  font-size: 0.85rem;
  font-weight: 700;
}

.extra-content {
  color: var(--color-text-strong);
  font-family: var(--font-mono);
  font-size: 0.9rem;
}

.extra-content code {
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border: 1px solid var(--color-border);
  font-weight: 700;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text-secondary);
  font-family: var(--font-sans);
  font-size: 0.9rem;
  line-height: 1.65;
}

.exercises-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.exercise-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #ffffff;
  color: var(--color-text-strong);
  font-family: var(--font-sans);
  font-size: 0.92rem;
  transition: all 0.2s cubic-bezier(0.32, 0.72, 0, 1);
  box-shadow: var(--shadow-sm);
}

.exercise-item:hover {
  border-color: var(--color-primary-border);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.ex-num {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border: 1px solid var(--color-border);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  font-weight: 700;
}

.code-empty-hud {
  padding: 48px;
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: #ffffff;
  color: var(--color-primary-text);
  text-align: center;
}

.empty-frame {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  opacity: 0.55;
}

.compact .markdown-shell {
  max-height: 300px;
  overflow: hidden;
  font-size: 0.86rem;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}
</style>
