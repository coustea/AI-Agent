<template>
  <div class="mindmap-resource" :class="{ compact }">
    <div v-if="markdownContent" class="mindmap-container">
      <div ref="markmapRef" class="markmap-shell"></div>
    </div>
    <div v-else class="mindmap-empty">暂未收到可展示的思维导图内容</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const markmapRef = ref<HTMLElement | null>(null)
let markmapInstance: Markmap | null = null

const transformer = new Transformer()

// 提取 Markdown 内容
const markdownContent = computed<string>(() => {
  if (!props.resultData) return ''
  if (typeof props.resultData === 'string') return props.resultData

  // 1. 如果有包裹 resource 结构
  let data: Record<string, any> = props.resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  // 2. 从 data 或 data.content 中提取 markdown 字符串
  const content = data.content
  
  if (typeof content === 'string' && content.trim()) {
    // 可能是 JSON 字符串，尝试解析一下看看内部是否有 markdown_content
    const parsed = parseJsonObject(content)
    if (parsed) {
      if (parsed.markdown_content) return parsed.markdown_content
      if (parsed.outline) return parsed.outline
      if (parsed.source) return parsed.source
    }
    return content
  }

  if (typeof content === 'object' && content !== null) {
    if (content.markdown_content) return content.markdown_content
    if (content.outline) return content.outline
    if (content.source) return content.source
  }

  // 3. 回退策略：直接在 data 第一层找
  if (data.markdown_content) return data.markdown_content
  if (data.outline) return data.outline
  if (data.source) return data.source

  return ''
})

// 渲染 markmap
const renderMarkmap = async (content: string) => {
  if (!content.trim() || !markmapRef.value) return

  try {
    const { root } = transformer.transform(content)

    // 创建 SVG 容器
    let svg = markmapRef.value.querySelector('svg')
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      svg.style.width = '100%'
      svg.style.height = props.compact ? '240px' : '500px'
      markmapRef.value.appendChild(svg)
    }

    if (!markmapInstance) {
      markmapInstance = new Markmap(svg, {
        autoFit: true,
        duration: 400,
        maxWidth: 320,
        paddingX: 30, // 增加水平间距
        style: (id) => `
          .${id}-g {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 15px;
          }
          .${id}-g foreignObject {
            overflow: visible;
          }
          .${id}-g .markmap-node text {
            color: #334155;
          }
        `
      })
    }

    markmapInstance.setData(root)
  } catch (err) {
    console.error('[MindmapResourceView] Markmap render error:', err)
    if (markmapRef.value) {
      markmapRef.value.innerHTML = `<pre class="markmap-error">思维导图渲染失败: ${err}</pre>`
    }
  }
}

watch(markdownContent, (content) => {
  renderMarkmap(content)
}, { immediate: true })

onMounted(() => {
  if (markdownContent.value) {
    renderMarkmap(markdownContent.value)
  }
})
</script>

<style scoped>
.mindmap-resource {
  width: 100%;
}

.mindmap-container {
  width: 100%;
}

.markmap-shell {
  width: 100%;
  min-height: 420px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  /* 添加细腻的点状网格背景以增加高级感 */
  background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
  background-size: 24px 24px;
}

.markmap-shell :deep(svg) {
  width: 100%;
  height: 500px;
}

/* 优化 SVG 内部节点及连接线样式 */
.markmap-shell :deep(.markmap-link) {
  stroke: #94a3b8; /* 更柔和的连线颜色 */
  stroke-width: 2px;
}

.markmap-shell :deep(.markmap-node) {
  cursor: pointer;
  transition: opacity 0.2s;
}

.markmap-shell :deep(.markmap-node:hover) {
  opacity: 0.85;
}

.markmap-shell :deep(.markmap-node circle) {
  fill: #ffffff;
  stroke-width: 2.5px;
}

.markmap-shell :deep(.markmap-node text) {
  font-weight: 500;
  fill: #1e293b;
}

/* 一级节点的字体加大 */
.markmap-shell :deep(.markmap-node[data-depth="0"] text) {
  font-size: 1.25rem;
  font-weight: 700;
  fill: #0f172a;
}

.markmap-error {
  padding: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #991b1b;
  font-size: 0.85rem;
  overflow: auto;
}

.compact .markmap-shell {
  min-height: 240px;
  background-size: 16px 16px;
}

.compact .markmap-shell :deep(svg) {
  height: 240px;
}

.mindmap-empty {
  padding: 16px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .markmap-shell {
    min-height: 320px;
  }

  .markmap-shell :deep(svg) {
    height: 320px;
  }

  .compact .markmap-shell {
    min-height: 180px;
  }

  .compact .markmap-shell :deep(svg) {
    height: 180px;
  }
}
</style>