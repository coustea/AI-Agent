<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { escapeHtml } from '@/shared/markdown/escapeHtml'
import type { MarkdownTheme } from '@/shared/markdown/types'
import { renderMarkdown } from '@/shared/markdown/workerClient'

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

let renderTimer: ReturnType<typeof setTimeout> | undefined
let renderVersion = 0
let themeObserver: MutationObserver | undefined

function currentTheme(): MarkdownTheme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

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

    renderedHtml.value = escapeHtml(content)
    degraded.value = true
  }
}

function queueRender(): void {
  if (renderTimer !== undefined) {
    clearTimeout(renderTimer)
    renderTimer = undefined
  }

  const content = props.content
  if (!props.streaming) {
    void performRender(content)
    return
  }

  const version = ++renderVersion
  renderedHtml.value = escapeHtml(content)
  degraded.value = true

  renderTimer = setTimeout(() => {
    renderTimer = undefined
    if (version !== renderVersion) {
      return
    }
    void performRender(content)
  }, 80)
}

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

async function handleClick(event: MouseEvent): Promise<void> {
  const target = event.target
  if (!(target instanceof Element)) {
    return
  }

  const button = target.closest<HTMLButtonElement>('.code-block-copy')
  if (!button) {
    return
  }

  const wrapper = button.closest('.code-block-wrapper')
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

watch(
  () => [props.content, props.streaming] as const,
  queueRender,
  { immediate: true },
)

onMounted(() => {
  theme.value = currentTheme()
  queueRender()

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
