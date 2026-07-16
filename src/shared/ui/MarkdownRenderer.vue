<script setup lang="ts">
// Markdown 渲染器：通过 Worker 异步渲染 markdown，支持流式更新、主题切换和代码复制

import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import {
  escapeHtml,
  renderMarkdown,
  type MarkdownTheme,
} from '@/shared/markdown/markdown'

const props = withDefaults(defineProps<{
  content?: string
  streaming?: boolean
}>(), {
  content: '',
  streaming: false,
})

const renderedHtml = ref('')
const degraded = ref(false)
const theme = ref<MarkdownTheme>('light')
const copyTimers = new Map<HTMLButtonElement, ReturnType<typeof setTimeout>>()

const STREAM_RENDER_INTERVAL_MS = 80

let renderTimer: ReturnType<typeof setTimeout> | undefined
let renderVersion = 0
let themeObserver: MutationObserver | undefined

function currentTheme(): MarkdownTheme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

// 执行渲染调用，通过版本号防止竞态（过期结果被忽略）
async function performRender(content: string): Promise<void> {
  const version = ++renderVersion

  try {
    const result = await renderMarkdown(content, theme.value)
    if (version !== renderVersion) {
      return
    }

    renderedHtml.value = result.html
    degraded.value = result.degraded
  } catch {
    if (version !== renderVersion) {
      return
    }

    // 渲染失败时降级为纯文本转义输出
    renderedHtml.value = escapeHtml(content)
    degraded.value = true
  }
}

// 调度渲染：非流式直接渲染，流式模式防抖聚合
function queueRender(): void {
  const content = props.content
  if (!props.streaming) {
    if (renderTimer !== undefined) {
      clearTimeout(renderTimer)
      renderTimer = undefined
    }
    void performRender(content)
    return
  }

  // 流式模式下先用转义文本占位
  if (!renderedHtml.value || degraded.value) {
    renderedHtml.value = escapeHtml(content)
    degraded.value = true
  }

  if (renderTimer !== undefined) {
    return
  }

  renderTimer = setTimeout(() => {
    renderTimer = undefined
    void performRender(props.content)
  }, STREAM_RENDER_INTERVAL_MS)
}

// 代码复制按钮的标签还原（1.6 秒后恢复）
function restoreCopyLabel(button: HTMLButtonElement, label: string): void {
  const existingTimer = copyTimers.get(button)
  if (existingTimer !== undefined) {
    clearTimeout(existingTimer)
  }

  const timer = setTimeout(() => {
    button.textContent = label
    copyTimers.delete(button)
  }, 1_600)
  copyTimers.set(button, timer)
}

// 点击事件代理：处理代码块复制与自动换行。
async function handleClick(event: MouseEvent): Promise<void> {
  const target = event.target
  if (!(target instanceof Element)) {
    return
  }

  const button = target.closest<HTMLButtonElement>('[data-code-action]')
  if (!button) {
    return
  }

  const wrapper = button.closest('.code-block-wrapper')
  if (button.dataset.codeAction === 'wrap') {
    const wrapped = wrapper?.classList.toggle('is-wrapped') ?? false
    button.textContent = wrapped ? '取消换行' : '自动换行'
    button.setAttribute('aria-pressed', String(wrapped))
    return
  }

  if (button.dataset.codeAction !== 'copy') {
    return
  }

  const code = wrapper?.querySelector('pre code')
  if (!code) {
    return
  }

  const originalLabel = button.textContent ?? '复制'

  try {
    await navigator.clipboard.writeText(code.textContent ?? '')
    button.textContent = '已复制'
    restoreCopyLabel(button, originalLabel)
  } catch {
    button.textContent = '复制失败'
  }
}

// 监听内容变化触发渲染
watch(
  () => [props.content, props.streaming] as const,
  queueRender,
  { immediate: true },
)

onMounted(() => {
  theme.value = currentTheme()
  queueRender()

  // 通过 MutationObserver 监听 <html> 的 class 变更（dark 模式切换）
  themeObserver = new MutationObserver(() => {
    const nextTheme = currentTheme()
    if (nextTheme === theme.value) {
      return
    }

    theme.value = nextTheme
    queueRender()
  })
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })
})

onBeforeUnmount(() => {
  renderVersion += 1
  if (renderTimer !== undefined) {
    clearTimeout(renderTimer)
  }
  themeObserver?.disconnect()

  for (const timer of copyTimers.values()) {
    clearTimeout(timer)
  }
  copyTimers.clear()
})
</script>

<template>
  <div
    class="markdown-renderer markdown-body"
    :class="{ streaming }"
    :data-degraded="degraded ? 'true' : 'false'"
    @click="handleClick"
  >
    <div class="model-content" v-html="renderedHtml" />
    <span v-if="streaming" class="markdown-stream-caret" aria-hidden="true" />
  </div>
</template>
