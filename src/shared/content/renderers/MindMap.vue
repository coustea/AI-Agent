<template>
  <div class="mindmap-resource" :class="{ compact }">
    <div v-if="markdownContent" class="mindmap-container">
      <div ref="markmapRef" class="markmap-shell"></div>
    </div>
    <div v-else class="mindmap-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>NO_TOPOLOGY_DATA_FOUND</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { parseJsonObject, type ResourceArtifactLike } from '../artifact'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

type MarkmapInstance = {
  setData: (root: unknown) => void
  destroy?: () => void
}

type MarkmapRuntime = {
  transformer: { transform: (content: string) => { root: unknown } }
  createMarkmap: (svg: SVGElement) => MarkmapInstance
}

const markmapRef = ref<HTMLElement | null>(null)
let markmapInstance: MarkmapInstance | null = null
let markmapRuntimePromise: Promise<MarkmapRuntime> | null = null

const loadMarkmapRuntime = async (): Promise<MarkmapRuntime> => {
  if (!markmapRuntimePromise) {
    markmapRuntimePromise = Promise.all([
      import('markmap-lib'),
      import('markmap-view'),
    ]).then(([markmapLib, markmapView]) => {
      const transformer = new markmapLib.Transformer()

      const createMarkmap = (svg: SVGElement): MarkmapInstance => {
        const instance = new markmapView.Markmap(svg, {
          autoFit: true,
          duration: 400,
          maxWidth: 320,
          paddingX: 30,
          style: (id: string) => `
            .${id}-g {
              font-family: var(--font-sans);
              font-size: 14px;
            }
            .${id}-g foreignObject {
              overflow: visible;
            }
            .${id}-g .markmap-node text {
              fill: var(--color-text);
            }
            .${id}-g .markmap-link {
              stroke-width: 2px;
              opacity: 0.85;
            }
            .${id}-g .markmap-node circle {
              fill: #ffffff;
              stroke-width: 2.5px;
            }
          `,
        })
        return {
          setData: (root: unknown) => { instance.setData(root as any) },
          destroy: () => { 
            if (instance && typeof instance.destroy === 'function') {
              instance.destroy()
            }
          }
        }
      }

      return { transformer, createMarkmap } as MarkmapRuntime
    })
  }

  return markmapRuntimePromise
}

const markdownContent = computed<string>(() => {
  if (!props.resultData) return ''
  if (typeof props.resultData === 'string') return props.resultData

  let data: Record<string, any> = props.resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  const content = data.content

  if (typeof content === 'string' && content.trim()) {
    const parsed = parseJsonObject(content)
    if (parsed) {
      if (parsed.markdown_content) return parsed.markdown_content
      if (parsed.outline) return parsed.outline
      if (parsed.source) return parsed.source
    }

    return content
  }

  if (typeof content === 'object' && content !== null) {
    if ((content as Record<string, any>).root) {
      return JSON.stringify(content)
    }
    if (content.markdown_content) return content.markdown_content
    if (content.outline) return content.outline
    if (content.source) return content.source
    if (content.markdown) return content.markdown
  }

  if (data.root) return JSON.stringify(data)
  if (data.markdown_content) return data.markdown_content
  if (data.outline) return data.outline
  if (data.source) return data.source
  if (data.markdown) return data.markdown

  return ''
})

const preprocessContent = (text: string): string => {
  let content = text.trim()
  const parsedJson = parseJsonObject(content)
  if (parsedJson?.root && typeof parsedJson.root === 'object') {
    return rootTreeToMarkdown(parsedJson.root as Record<string, any>)
  }

  if (content.startsWith('```')) {
    content = content.replace(/^```[a-z]*\n/i, '').replace(/\n```$/, '').trim()
  }

  if (!content.startsWith('mindmap')) {
    return text
  }

  const lines = content.split('\n')
  const markdownLines: string[] = []
  let rootFound = false
  let baseIndent = 0

  for (const line of lines) {
    if (line.trim() === 'mindmap' || !line.trim()) continue

    const match = line.match(/^(\s*)(.*)/)
    const rawIndent = match?.[1] || ''
    const rawNodeText = match?.[2] || ''
    if (!rawNodeText.trim()) continue

    const indent = rawIndent.length
    const nodeText = rawNodeText.replace(/^[\(\[\{]+|[\)\]\}]+$/g, '').trim()

    if (!rootFound) {
      markdownLines.push(`# ${nodeText}`)
      rootFound = true
      baseIndent = indent
      continue
    }

    let depth = Math.floor((indent - baseIndent) / 2)
    if (depth <= 0) depth = 1

    if (depth === 1) {
      markdownLines.push(`## ${nodeText}`)
      continue
    }

    const listIndent = '  '.repeat(depth - 2)
    markdownLines.push(`${listIndent}- ${nodeText}`)
  }

  return markdownLines.join('\n')
}

const rootTreeToMarkdown = (root: Record<string, any>): string => {
  const lines: string[] = []

  const walk = (node: Record<string, any>, depth: number) => {
    const label = String(node.content || node.title || node.name || '').trim()
    if (!label) return
    if (depth === 0) {
      lines.push(`# ${label}`)
    } else if (depth === 1) {
      lines.push(`## ${label}`)
    } else {
      lines.push(`${'  '.repeat(depth - 2)}- ${label}`)
    }

    const children = Array.isArray(node.children) ? node.children : []
    for (const child of children) {
      if (child && typeof child === 'object' && !Array.isArray(child)) {
        walk(child as Record<string, any>, depth + 1)
      }
    }
  }

  walk(root, 0)
  return lines.join('\n')
}

const renderMarkmap = async (rawContent: string) => {
  if (!rawContent.trim() || !markmapRef.value) return

  const content = preprocessContent(rawContent)
  await nextTick()

  try {
    const { transformer, createMarkmap } = await loadMarkmapRuntime()
    const { root } = transformer.transform(content)

    let svg = markmapRef.value.querySelector('svg')
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      const containerWidth = markmapRef.value.clientWidth || 800
      const height = props.compact ? 240 : 500
      svg.setAttribute('width', String(containerWidth))
      svg.setAttribute('height', String(height))
      svg.style.width = `${containerWidth}px`
      svg.style.height = `${height}px`
      markmapRef.value.appendChild(svg)
    }

    if (!markmapInstance) {
      markmapInstance = createMarkmap(svg)
    }

    markmapInstance.setData(root)
  } catch (err) {
    console.error('[MindmapResourceView] Markmap render error:', err)

    const errorMessage = err instanceof Error ? err.message : String(err)
    if (markmapRef.value) {
      markmapRef.value.innerHTML = `<pre class="markmap-error">SYSTEM_RENDER_FAIL: ${errorMessage}</pre>`
    }
  }
}

watch(markdownContent, (content) => {
  void renderMarkmap(content)
}, { immediate: true })

onMounted(() => {
  if (markdownContent.value) {
    void renderMarkmap(markdownContent.value)
  }
})

onBeforeUnmount(() => {
  if (markmapInstance?.destroy) {
    markmapInstance.destroy()
  }
  markmapInstance = null
  if (markmapRef.value) {
    markmapRef.value.innerHTML = ''
  }
})
</script>

<style scoped>
.mindmap-resource {
  width: 100%;
  --primary: var(--color-primary);
  --bg: var(--color-surface);
  --fg: var(--color-text);
  --border: var(--color-border);
  --accent: var(--color-primary);
}

.mindmap-container {
  display: flex;
  flex-direction: column;
}

.markmap-shell {
  width: 100%;
  min-height: 420px;
  background: #ffffff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.markmap-shell :deep(svg) {
  width: 100%;
  height: 500px;
}

.markmap-shell :deep(.markmap-node) {
  cursor: pointer;
  transition: opacity 0.2s;
}

.markmap-shell :deep(.markmap-node:hover) {
  opacity: 0.8;
}

.markmap-shell :deep(.markmap-node[data-depth="0"] text) {
  font-size: 1.15rem;
  font-weight: 700;
  fill: var(--color-primary-text) !important;
}

.markmap-shell :deep(.markmap-node[data-depth="1"] text) {
  font-size: 0.95rem;
  font-weight: 600;
  fill: var(--color-text-strong) !important;
}

.markmap-shell :deep(.markmap-node text) {
  font-size: 0.85rem;
  fill: var(--color-text) !important;
}

.markmap-error {
  padding: 20px;
  background: rgba(0, 0, 0, 0.02);
  border: none;
  border-radius: 8px;
  color: #000000;
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.compact .mindmap-container {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.compact .markmap-shell {
  min-height: 240px;
  background-size: 20px 20px;
}

.compact .markmap-shell :deep(svg) {
  height: 240px;
}

.mindmap-empty-hud {
  padding: 40px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px dashed var(--border);
  padding: 40px 60px;
  border-radius: 4px;
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--color-text-faint);
  letter-spacing: 1px;
}

@media (max-width: 768px) {
  .markmap-shell { min-height: 320px; }
  .markmap-shell :deep(svg) { height: 320px; }
  .compact .markmap-shell { min-height: 180px; }
  .compact .markmap-shell :deep(svg) { height: 180px; }
}
</style>
