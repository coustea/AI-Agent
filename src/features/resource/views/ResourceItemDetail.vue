<template>
  <div class="resource-item-page">
    <div v-if="loading" class="page-state">
      <div class="loading-mark"></div>
      <p>正在打开学习资源…</p>
    </div>

    <div v-else-if="error || !activeCard" class="page-state">
      <PhWarningCircle :size="30" />
      <h1>资源暂时无法打开</h1>
      <p>该资源可能尚未完成生成，或当前链接已失效。</p>
      <button type="button" @click="goToResourceList">返回资源列表</button>
    </div>

    <template v-else>
      <header class="detail-header">
        <button type="button" class="back-link" @click="goToResourceList">
          <PhArrowLeft :size="18" />
          返回资源包
        </button>

        <div class="header-separator"></div>

        <p class="bundle-name" :title="bundleSubtitle">
          {{ bundleSubtitle }}
        </p>

        <span class="complete-status">
          <PhCheckCircle :size="16" />
          已生成
        </span>
      </header>

      <div class="detail-layout">
        <aside class="resource-rail" aria-label="本次生成的资源">
          <div class="rail-heading">
            <span>资源目录</span>
            <strong>{{ resourceCards.length }} 项</strong>
          </div>

          <nav>
            <button
              v-for="card in resourceCards"
              :key="card.id"
              type="button"
              class="rail-item"
              :class="{ active: card.type === activeCard.type }"
              :aria-current="card.type === activeCard.type ? 'page' : undefined"
              @click="openResource(card.type)"
            >
              <span class="rail-indicator"></span>
              <span class="rail-copy">
                <strong>{{ getArtifactLabel(card.type) }}</strong>
                <small>{{ card.format }}</small>
              </span>
              <PhArrowRight v-if="card.type !== activeCard.type" :size="15" />
            </button>
          </nav>
        </aside>

        <main class="resource-viewer">
          <header class="viewer-heading">
            <div class="viewer-title">
              <span>当前资源</span>
              <h1>{{ activeCard.title }}</h1>
              <p>{{ activeCard.summary }}</p>
            </div>

            <dl class="viewer-meta">
              <div>
                <dt>资源类型</dt>
                <dd>{{ getArtifactLabel(activeCard.type) }}</dd>
              </div>
              <div>
                <dt>内容格式</dt>
                <dd>{{ activeCard.format }}</dd>
              </div>
            </dl>
          </header>

          <section class="viewer-content" :class="`viewer-${activeCard.type}`">
            <ArtifactRenderer
              :type="activeCard.type"
              :content="activeCard.content"
              :resource="activeCard.resource"
            />
          </section>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PhArrowLeft,
  PhArrowRight,
  PhCheckCircle,
  PhWarningCircle,
} from '@phosphor-icons/vue'

import {
  getResourceBundle,
} from '@/features/resource/api/resource'
import type { GeneratedResourceBundle } from '@/features/resource/model/resource'
import {
  getResourceBundleSubtitle,
  getResourceCards,
} from '../model/resourceDisplay'
import { getArtifactLabel } from '@/shared/content/kind'
import ArtifactRenderer from '@/shared/content/ArtifactRenderer.vue'

const route = useRoute()
const router = useRouter()

const loading = shallowRef(true)
const error = shallowRef(false)
const bundle = shallowRef<GeneratedResourceBundle | null>(null)

const resourceId = computed(() => {
  const id = Number(route.params.id)
  return Number.isFinite(id) && id > 0 ? id : null
})

const resourceType = computed(() => String(route.params.type || '').trim().toLowerCase())
const bundleSubtitle = computed(() => getResourceBundleSubtitle(bundle.value))
const resourceCards = computed(() => getResourceCards(bundle.value))
const activeCard = computed(() => resourceCards.value.find(card => card.type === resourceType.value) || null)

watch(resourceId, loadResource, { immediate: true })

async function loadResource() {
  if (!resourceId.value) {
    loading.value = false
    error.value = true
    bundle.value = null
    return
  }

  loading.value = true
  error.value = false

  try {
    const response = await getResourceBundle(resourceId.value)
    bundle.value = response.data?.data || null
    error.value = !bundle.value
  } catch (exception) {
    console.error('Failed to load resource item detail:', exception)
    bundle.value = null
    error.value = true
  } finally {
    loading.value = false
  }
}

function openResource(type: string) {
  if (!resourceId.value || type === resourceType.value) return
  void router.push({
    name: 'ResourceItemDetail',
    params: { id: resourceId.value, type },
  })
}

function goToResourceList() {
  if (!resourceId.value) {
    void router.push('/resource-generator')
    return
  }

  void router.push({
    name: 'ResourceResult',
    params: { id: resourceId.value },
  })
}
</script>

<style scoped>
.resource-item-page {
  --page-background: var(--color-bg);
  --surface: var(--color-surface);
  --surface-soft: var(--color-surface-hover);
  --border: var(--color-border);
  --border-strong: var(--color-border-hover);
  --text: var(--color-text-strong);
  --text-secondary: var(--color-text-secondary);
  --text-muted: var(--color-text-muted);
  --blue: var(--color-primary-text);

  min-height: 100%;
  background: var(--page-background);
  color: var(--text);
}

.page-state {
  display: grid;
  min-height: 56vh;
  place-content: center;
  justify-items: center;
  gap: 12px;
  padding: 36px;
  color: var(--text-secondary);
  text-align: center;
}

.page-state h1,
.page-state p {
  margin: 0;
}

.page-state h1 {
  color: var(--text);
  font-size: 20px;
}

.page-state p {
  font-size: 14px;
}

.page-state button {
  margin-top: 8px;
  padding: 9px 14px;
  border: 1px solid #b8c9e5;
  border-radius: 8px;
  background: var(--surface);
  color: var(--blue);
  font: inherit;
  cursor: pointer;
}

.loading-mark {
  width: 26px;
  height: 26px;
  border: 3px solid #dce7f7;
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: resource-spin 0.8s linear infinite;
}

.detail-header {
  display: flex;
  min-height: 66px;
  align-items: center;
  gap: 18px;
  padding: 0 28px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 0;
  border: 0;
  color: var(--text-secondary);
  background: transparent;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.back-link:hover { color: var(--blue); }
.back-link:active { transform: translateX(-2px); }
.header-separator { width: 1px; height: 22px; background: var(--border); }

.bundle-name {
  max-width: min(55vw, 680px);
  margin: 0;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.complete-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-left: auto;
  color: #087853;
  font-size: 13px;
  font-weight: 700;
}

.detail-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  min-height: calc(100vh - 66px);
}

.resource-rail {
  padding: 24px 14px;
  border-right: 1px solid var(--border);
  background: var(--surface-soft);
}

.rail-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 10px 12px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}

.rail-heading strong {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.resource-rail nav { display: grid; gap: 4px; }

.rail-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 9px;
  color: var(--text-secondary);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.rail-item:hover { background: #eef4ff; }
.rail-item:active { transform: scale(0.98); }
.rail-item.active { border-color: #bbd2fb; background: #f8fbff; color: var(--blue); }
.rail-item:focus-visible,
.back-link:focus-visible,
.page-state button:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 2px;
}

.rail-indicator {
  width: 6px;
  height: 6px;
  flex: 0 0 auto;
  border-radius: 999px;
  background: var(--text-muted);
  opacity: 0.4;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.rail-item.active .rail-indicator {
  background: var(--blue);
  opacity: 1;
  transform: scale(1.2);
}

.rail-copy { display: grid; min-width: 0; gap: 3px; flex: 1; }
.rail-copy strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.rail-copy small { color: var(--text-muted); font-size: 11px; }

.resource-viewer {
  min-width: 0;
  background: var(--surface);
}

.viewer-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 32px;
  max-width: 1000px;
  margin: 0 auto;
  padding: 28px 40px 22px;
  border-bottom: 1px solid var(--border);
}

.viewer-title {
  min-width: 0;
  max-width: 720px;
}

.viewer-title > span {
  display: block;
  margin-bottom: 5px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.viewer-title h1 {
  margin: 0;
  color: var(--text);
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.25;
  text-wrap: balance;
}

.viewer-title p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.65;
  text-wrap: pretty;
}

.viewer-meta {
  display: grid;
  grid-template-columns: repeat(2, max-content);
  gap: 18px;
  margin: 4px 0 0;
}

.viewer-meta div {
  min-width: 72px;
}

.viewer-meta dt {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}

.viewer-meta dd {
  margin: 4px 0 0;
  color: var(--text);
  font-size: 13px;
  font-weight: 750;
}

.viewer-content {
  max-width: 1000px;
  min-height: 100%;
  margin: 0 auto;
  padding: 28px 40px 64px;
}

.viewer-mindmap,
.viewer-ppt,
.viewer-cartoon {
  max-width: 1040px;
}

.viewer-ppt,
.viewer-cartoon {
  /* Give visual elements breathing room instead of 0 padding */
  padding: clamp(24px, 4vw, 40px) clamp(20px, 3vw, 40px);
  overflow: hidden;
  background: transparent;
}

@keyframes resource-spin { to { transform: rotate(360deg); } }

@media (max-width: 860px) {
  .detail-header { padding: 0 18px; }
  .bundle-name { display: none; }
  .header-separator { display: none; }
  .detail-layout { display: block; }
  .resource-rail { overflow-x: auto; padding: 10px 14px; border-right: 0; border-bottom: 1px solid var(--border); }
  .rail-heading { display: none; }
  .resource-rail nav { display: flex; min-width: max-content; }
  .rail-item { width: auto; min-width: 132px; }
  .resource-viewer { background: var(--surface); }
  .viewer-heading { align-items: flex-start; flex-direction: column; gap: 16px; padding: 22px 16px 18px; }
  .viewer-meta { gap: 24px; margin: 0; }
  .viewer-content { padding: 24px 16px 48px; min-height: 100%; }
}
</style>
