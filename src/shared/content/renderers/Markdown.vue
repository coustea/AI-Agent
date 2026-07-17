<template>
  <div class="markdown-resource" :class="{ compact, 'is-code': isCodeArtifact }">
    <div v-if="content" :class="isCodeArtifact ? 'code-card-content' : 'markdown-plain-shell'">
      <!-- 代码资源：讲解说明 -->
      <div v-if="isCodeArtifact && !compact && parsedData?.explanation" class="code-header-meta">
        <span class="code-summary-text">{{ parsedData.explanation }}</span>
      </div>

      <!-- markdown 主体 -->
      <div class="markdown-body">
        <MarkdownRenderer
          class="markdown-shell"
          :class="{ 'code-markdown-shell': isCodeArtifact }"
          :content="content"
        />
      </div>

      <!-- 代码资源：元数据面板（复杂度 / 调试建议 / 练习序列） -->
      <div v-if="isCodeArtifact && !compact && hasExtraInfo" class="code-footer-extras">
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
    </div>

    <!-- 空状态 -->
    <div v-else class="markdown-empty">
      <div class="empty-icon">!</div>
      <div class="empty-text">NULL_CONTENT: NO_MARKDOWN_RECEIVED</div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Markdown 渲染器：统一处理普通 markdown 和代码资源（含复杂度、调试建议、练习序列）

import { computed } from 'vue'
import {
  PhClock as Timer,
  PhWarning as Warning,
  PhNotePencil as EditPen,
} from '@phosphor-icons/vue'
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'
import { getMarkdownContent, parseJsonObject, type ResourceArtifactLike } from '../artifact'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

function toText(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
}

// 检测文本是否看起来像 Markdown 文档（而非纯代码）
function looksLikeMarkdownDocument(text: string): boolean {
  if (!text.trim()) return false
  const fenceCount = text.match(/```/g)?.length ?? 0
  if (fenceCount >= 2) return true
  const hasMarkdownTitle = /(^|\n)#{1,4}\s+\S/.test(text)
  const hasMarkdownList = /(^|\n)([-*]|\d+\.)\s+\S/.test(text)
  const hasCodeSignals = /(^|\n)\s*(import|from|def|class|#include|public\s+class|function|const|let|var)\b/.test(text)
  return hasMarkdownTitle && hasMarkdownList && !hasCodeSignals
}

// 用反引号包裹代码块，自动选择足够长的 fence 长度
function toFencedMarkdown(code: string, language: unknown): string {
  const longestFence = Math.max(0, ...Array.from(code.matchAll(/`+/g), (match) => match[0].length))
  const fence = '`'.repeat(Math.max(3, longestFence + 1))
  const languageName = toText(language || 'text').trim().toLowerCase().replace(/\s+/g, '-')
  return `${fence}${languageName}\n${code.trimEnd()}\n${fence}`
}

// 代码资源结构化解析（原 Code.vue 逻辑）
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
  // 解包嵌套的 resource 字段
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

// 判别是否按"代码资源"渲染：存在代码字段或代码专属元数据
const isCodeArtifact = computed(() => {
  const d = parsedData.value
  if (!d) return false
  return Boolean(
    d.code || d.full_code || d.language || d.lang ||
    d.markdown || d.markdown_content || d.document || d.content_markdown ||
    d.complexity || d.debug_tips || d.exercises || d.explanation,
  )
})

// 代码资源的 markdown 内容（原 Code.vue rendererContent）
const codeMarkdown = computed(() => {
  const data = parsedData.value
  if (!data) return ''
  const explicitMarkdown = data.markdown || data.markdown_content || data.document || data.content_markdown
  if (typeof explicitMarkdown === 'string' && explicitMarkdown.trim()) return explicitMarkdown
  const codeContent = toText(data.code || data.full_code || '')
  if (!codeContent.trim() || looksLikeMarkdownDocument(codeContent)) return codeContent
  return toFencedMarkdown(codeContent, data.language || data.lang || 'text')
})

// 最终渲染内容：代码资源走 codeMarkdown，其余走 getMarkdownContent（原 Article 路径）
const content = computed(() =>
  isCodeArtifact.value ? codeMarkdown.value : getMarkdownContent(props.resultData),
)

// 是否显示额外元数据面板
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
/* —— 合并自原 Article.vue 的简单 markdown 外壳 —— */
.markdown-resource { min-width: 0; width: 100%; }
.markdown-plain-shell { background: transparent; }
.markdown-body { min-width: 0; }
.markdown-body :deep(h1:first-of-type) {
  display: none;
}

.compact .markdown-plain-shell {
  max-height: 300px;
  overflow: hidden;
  font-size: 0.85rem;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}
.compact .markdown-plain-shell :deep(h1),
.compact .markdown-plain-shell :deep(h2),
.compact .markdown-plain-shell :deep(h3) {
  margin-top: 1em;
  border-bottom: 0;
}

/* —— 合并自原 Code.vue 的代码资源外观与元数据面板 —— */
.markdown-resource.is-code {
  --primary: var(--color-primary);
  --fg: var(--color-text);
  --code-bg: var(--color-bg);
  --code-head-bg: var(--color-surface-hover);
  --code-border: var(--color-border);
  --code-text: var(--color-text-strong);
}
.code-card-content {
  display: flex; flex-direction: column; gap: 16px;
  padding: 0; background: transparent;
  border: none; border-radius: 0;
  box-shadow: none;
}
.markdown-shell { min-width: 0; line-height: 1.78; overflow-wrap: anywhere; font-size: 0.96rem; }
.code-markdown-shell :deep(h1),
.code-markdown-shell :deep(h2),
.code-markdown-shell :deep(h3) {
  margin: 1.7em 0 0.85em; padding-bottom: 0.48em;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-strong); font-weight: 700; line-height: 1.35;
}
.code-markdown-shell :deep(h1) { font-size: 1.42rem; }
.code-markdown-shell :deep(h2) { font-size: 1.18rem; }
.code-markdown-shell :deep(h3) { font-size: 1.02rem; }
.code-markdown-shell :deep(p) { margin: 0.85em 0; color: var(--color-text-secondary); }
.code-markdown-shell :deep(ul),
.code-markdown-shell :deep(ol) { padding-left: 1.35em; margin: 0.85em 0; }
.code-markdown-shell :deep(blockquote) {
  margin: 1em 0; padding: 10px 14px; border-left: 3px solid var(--color-primary);
  background: var(--color-primary-soft); border-radius: 0 var(--radius-md) var(--radius-md) 0;
}
.markdown-resource.is-code :deep(.code-block-wrapper) {
  margin: 1.2em 0; border: 1px solid var(--code-border); border-radius: var(--radius-md);
  background: var(--code-bg); overflow: hidden; box-shadow: none;
}
.markdown-resource.is-code :deep(pre code),
.markdown-resource.is-code :deep(.code-block-wrapper code) {
  display: block; min-width: max-content; padding: 0; background: transparent !important;
  color: var(--code-text) !important; font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; line-height: 1.65;
}
.markdown-resource.is-code :deep(:not(pre) > code) {
  padding: 0.2em 0.4em; border: none; border-radius: var(--radius-sm);
  background: var(--color-primary-soft) !important; color: var(--color-primary-text); font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.86em;
}
.code-header-meta { margin-bottom: 4px; }
.code-summary-text { color: var(--color-text-secondary); font-size: 0.95rem; font-weight: 500; line-height: 1.6; }
.code-footer-extras {
  margin-top: 16px; padding: 18px; border: none;
  border-radius: var(--radius-md); background: var(--color-surface-hover, rgba(0,0,0,0.02)); box-shadow: none;
}
.footer-divider { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.divider-label { font-size: 0.75rem; color: var(--color-primary-text); letter-spacing: 0.5px; font-weight: 700; }
.divider-line { flex: 1; height: 1px; background: linear-gradient(to right, var(--color-border), transparent); }
.extras-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; margin-bottom: 18px; }
.extra-item { display: flex; flex-direction: column; gap: 10px; }
.extra-label { display: flex; align-items: center; gap: 8px; color: var(--color-primary-text); font-size: 0.85rem; font-weight: 700; }
.extra-content { color: var(--color-text-strong); font-family: var(--font-mono); font-size: 0.9rem; }
.extra-content code { padding: 4px 10px; border-radius: var(--radius-sm); background: var(--color-primary-soft); color: var(--color-primary-text); border: 1px solid var(--color-border); font-weight: 700; }
.tips-list { margin: 0; padding-left: 20px; color: var(--color-text-secondary); font-size: 0.9rem; line-height: 1.65; }
.exercises-container { display: flex; flex-direction: column; gap: 10px; margin-top: 4px; }
.exercise-item {
  display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px;
  border: none; border-radius: var(--radius-md); background: var(--color-surface);
  color: var(--color-text-strong); font-size: 0.92rem; box-shadow: none;
}
.ex-num { flex-shrink: 0; padding: 2px 7px; border-radius: var(--radius-sm); background: var(--color-primary-soft); color: var(--color-primary-text); border: 1px solid var(--color-border); font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700; }
.compact .code-card-content { padding: 0; border: none; background: transparent; box-shadow: none; }

/* —— 空状态 —— */
.markdown-empty {
  padding: 48px; border: 1px dashed var(--color-border); border-radius: var(--radius-md);
  background: #fff; color: var(--color-primary-text); text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 12px; box-shadow: var(--shadow-sm);
}
.empty-icon { font-family: var(--font-mono); font-size: 2rem; opacity: 0.5; }
.empty-text { font-size: 0.8rem; }
</style>
