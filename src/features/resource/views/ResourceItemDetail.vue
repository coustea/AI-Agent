<template>
  <div class="resource-item-page" :aria-busy="loading">
    <div v-if="loading" class="detail-skeleton" role="status" aria-label="正在打开学习资源">
      <div class="skeleton-topbar">
        <span class="skeleton-line skeleton-back"></span>
        <span class="skeleton-line skeleton-status"></span>
      </div>

      <div class="skeleton-workspace">
        <aside class="skeleton-rail" aria-hidden="true">
          <span class="skeleton-line skeleton-rail-title"></span>
          <span v-for="index in 6" :key="index" class="skeleton-resource"></span>
        </aside>

        <main class="skeleton-viewer" aria-hidden="true">
          <span class="skeleton-line skeleton-overline"></span>
          <span class="skeleton-line skeleton-title"></span>
          <span class="skeleton-line skeleton-copy"></span>
          <span class="skeleton-line skeleton-copy short"></span>
          <div class="skeleton-canvas"></div>
        </main>
      </div>
    </div>

    <section v-else-if="error || !activeCard" class="page-state" aria-labelledby="resource-unavailable-title">
      <span class="state-icon" aria-hidden="true">
        <PhWarningCircle :size="28" weight="duotone" />
      </span>
      <div>
        <h1 id="resource-unavailable-title">资源暂时无法打开</h1>
        <p>该资源可能尚未完成生成，或当前链接已失效。你可以重新加载，或返回资源包选择其他内容。</p>
      </div>
      <div class="state-actions">
        <button type="button" class="secondary-action" @click="goToResourceList">
          返回资源包
        </button>
        <button type="button" class="primary-action" @click="loadResource">
          重新加载
        </button>
      </div>
    </section>

    <template v-else>
      <header class="detail-header">
        <div class="detail-header-main">
          <button type="button" class="back-link" @click="goToResourceList">
            <PhArrowLeft :size="17" />
            <span>资源包</span>
          </button>

          <span class="breadcrumb-separator" aria-hidden="true">/</span>

          <p class="bundle-name" :title="bundleSubtitle">
            {{ bundleSubtitle }}
          </p>
        </div>

        <span class="complete-status">
          <PhCheckCircle :size="16" weight="fill" />
          资源已生成
        </span>
      </header>

      <div class="detail-layout">
        <aside class="resource-rail" aria-label="本次生成的资源目录">
          <div class="rail-heading">
            <div>
              <span>学习资源</span>
              <strong>{{ resourceCards.length }} 项内容</strong>
            </div>
            <span class="rail-progress" :aria-label="`当前第 ${activeIndex + 1} 项，共 ${resourceCards.length} 项`">
              {{ String(activeIndex + 1).padStart(2, '0') }}<i>/</i>{{ String(resourceCards.length).padStart(2, '0') }}
            </span>
          </div>

          <nav class="resource-nav">
            <button
              v-for="(card, index) in resourceCards"
              :key="card.id"
              type="button"
              class="rail-item"
              :class="[`rail-item--${card.type}`, { active: card.type === activeCard.type }]"
              :aria-current="card.type === activeCard.type ? 'page' : undefined"
              @click="openResource(card.type)"
            >
              <span class="rail-type-mark" aria-hidden="true">
                <component :is="getArtifactIcon(card.type)" :size="17" weight="duotone" />
              </span>
              <span class="rail-copy">
                <strong>{{ getArtifactLabel(card.type) }}</strong>
                <small>{{ card.format }}</small>
              </span>
              <span class="rail-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
            </button>
          </nav>
        </aside>

        <main class="resource-viewer">
          <header class="viewer-heading">
            <div class="viewer-title">
              <h1>{{ activeCard.title }}</h1>
              <p class="viewer-summary">{{ activeCard.summary }}</p>
            </div>
          </header>

          <section class="viewer-content" :class="`viewer-${activeCard.type}`" :aria-label="activeCard.title">
            <ArtifactRenderer
              :key="activeCard.id"
              :type="activeCard.type"
              :content="activeCard.content"
              :resource="activeCard.resource"
            />
          </section>

          <footer v-if="previousCard || nextCard" class="resource-pagination" aria-label="切换学习资源">
            <button
              v-if="previousCard"
              type="button"
              class="pagination-action previous"
              @click="openResource(previousCard.type)"
            >
              <PhArrowLeft :size="17" />
              <span>
                <small>上一项</small>
                <strong>{{ getArtifactLabel(previousCard.type) }}</strong>
              </span>
            </button>

            <span v-else class="pagination-spacer" aria-hidden="true"></span>

            <button
              v-if="nextCard"
              type="button"
              class="pagination-action next"
              @click="openResource(nextCard.type)"
            >
              <span>
                <small>下一项</small>
                <strong>{{ getArtifactLabel(nextCard.type) }}</strong>
              </span>
              <PhArrowRight :size="17" />
            </button>
          </footer>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PhArrowLeft,
  PhArrowRight,
  PhBookBookmark,
  PhBookOpenText,
  PhCheckCircle,
  PhCheckSquare,
  PhCode,
  PhFilmReel,
  PhPresentationChart,
  PhTreeStructure,
  PhWarningCircle,
} from '@phosphor-icons/vue'

import { getResourceBundle } from '@/features/resource/api/resource'
import type { GeneratedResourceBundle } from '@/features/resource/model/resource'
import { getArtifactLabel } from '@/shared/content/kind'
import ArtifactRenderer from '@/shared/content/ArtifactRenderer.vue'
import {
  getResourceBundleSubtitle,
  getResourceCards,
} from '../model/resourceDisplay'

const route = useRoute()
const router = useRouter()

const loading = shallowRef(true)
const error = shallowRef(false)
const bundle = shallowRef<GeneratedResourceBundle | null>(null)

const artifactIcons: Record<string, Component> = {
  content: PhBookOpenText,
  mindmap: PhTreeStructure,
  quiz: PhCheckSquare,
  code: PhCode,
  reading: PhBookBookmark,
  ppt: PhPresentationChart,
  cartoon: PhFilmReel,
}

const resourceId = computed(() => {
  const id = Number(route.params.id)
  return Number.isFinite(id) && id > 0 ? id : null
})

const resourceType = computed(() => String(route.params.type || '').trim().toLowerCase())
const bundleSubtitle = computed(() => getResourceBundleSubtitle(bundle.value))
const resourceCards = computed(() => getResourceCards(bundle.value))
const activeIndex = computed(() => resourceCards.value.findIndex(card => card.type === resourceType.value))
const activeCard = computed(() => activeIndex.value === -1 ? null : resourceCards.value[activeIndex.value])
const previousCard = computed(() => activeIndex.value > 0 ? resourceCards.value[activeIndex.value - 1] : null)
const nextCard = computed(() => activeIndex.value >= 0 ? resourceCards.value[activeIndex.value + 1] || null : null)

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

function getArtifactIcon(type: string) {
  return artifactIcons[type] || PhBookOpenText
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
.resource-item-page,
.resource-item-page * {
  box-sizing: border-box;
}

.resource-item-page {
  --page-background: var(--color-bg);
  --surface: var(--color-surface);
  --surface-subtle: var(--color-surface-hover);
  --border: var(--color-border);
  --border-strong: var(--color-border-hover);
  --text: var(--color-text-strong);
  --text-secondary: var(--color-text-secondary);
  --text-muted: var(--color-text-muted);
  --accent: var(--cat-resource);
  --accent-soft: var(--cat-resource-soft);

  min-height: 100%;
  background: var(--page-background);
  color: var(--text);
}

.detail-header {
  display: flex;
  min-height: 64px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 clamp(18px, 2.4vw, 34px);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.detail-header-main,
.back-link,
.complete-status,
.pagination-action {
  display: inline-flex;
  align-items: center;
}

.detail-header-main {
  min-width: 0;
  gap: 12px;
}

.back-link {
  flex: 0 0 auto;
  gap: 7px;
  min-height: 36px;
  padding: 0 2px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease;
}

.back-link:hover {
  background: var(--surface-subtle);
  color: var(--color-primary-text);
}

.breadcrumb-separator {
  color: var(--text-faint, var(--color-text-faint));
  font-size: 14px;
}

.bundle-name {
  max-width: min(56vw, 680px);
  margin: 0;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.complete-status {
  flex: 0 0 auto;
  gap: 6px;
  color: var(--color-success);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.detail-layout {
  display: grid;
  grid-template-columns: 244px minmax(0, 1fr);
  align-items: start;
  min-height: calc(100vh - 64px);
}

.resource-rail {
  position: sticky;
  top: 0;
  min-height: calc(100vh - 64px);
  padding: 24px 14px;
  border-right: 1px solid var(--border);
  background: var(--surface-subtle);
}

.rail-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin: 0 10px 15px;
}

.rail-heading > div {
  display: grid;
  gap: 3px;
}

.rail-heading span:first-child,
.rail-heading strong,
.rail-progress {
  font-variant-numeric: tabular-nums;
}

.rail-heading span:first-child {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: var(--weight-bold);
}

.rail-heading strong {
  color: var(--text);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
}

.rail-progress {
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: var(--weight-bold);
  letter-spacing: 0.02em;
}

.rail-progress i {
  margin: 0 2px;
  color: var(--text-muted);
  font-style: normal;
  font-weight: var(--weight-normal);
}

.resource-nav {
  display: grid;
  gap: 4px;
}

.rail-item {
  --item-accent: var(--color-primary-text);
  --item-accent-soft: var(--color-primary-soft);

  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 8px 9px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
  font: inherit;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.rail-item:hover {
  background: color-mix(in srgb, var(--surface) 82%, var(--item-accent-soft));
  color: var(--text);
}

.rail-item.active {
  border-color: color-mix(in srgb, var(--item-accent) 25%, var(--border));
  background: color-mix(in srgb, var(--surface) 55%, var(--item-accent-soft));
  color: var(--text);
}

.rail-item--content { --item-accent: #276bb5; --item-accent-soft: #e8f2ff; }
.rail-item--mindmap { --item-accent: #7452b8; --item-accent-soft: #f1edff; }
.rail-item--quiz { --item-accent: #16835e; --item-accent-soft: #e4f7ee; }
.rail-item--code { --item-accent: #4e6471; --item-accent-soft: #edf2f4; }
.rail-item--reading { --item-accent: #a06a18; --item-accent-soft: #fff4db; }
.rail-item--ppt { --item-accent: #be5661; --item-accent-soft: #fff0f1; }
.rail-item--cartoon { --item-accent: #5963bd; --item-accent-soft: #eff0ff; }

.rail-type-mark {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  place-items: center;
  border-radius: 8px;
  background: var(--item-accent-soft);
  color: var(--item-accent);
}

.rail-copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 2px;
}

.rail-copy strong,
.rail-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rail-copy strong {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
}

.rail-copy small {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: var(--weight-medium);
}

.rail-index {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: var(--weight-bold);
  font-variant-numeric: tabular-nums;
}

.rail-item.active .rail-index {
  color: var(--item-accent);
}

.resource-viewer {
  min-width: 0;
  background: var(--surface);
}

.viewer-heading,
.viewer-content,
.resource-pagination {
  max-width: 1120px;
  margin-right: auto;
  margin-left: auto;
}

.viewer-heading {
  padding: 34px clamp(24px, 4vw, 52px) 26px;
  border-bottom: 1px solid var(--border);
}

.viewer-title {
  min-width: 0;
  max-width: 780px;
}

.viewer-title h1 {
  margin: 0;
  color: var(--text);
  font-size: var(--text-xl);
  font-weight: var(--weight-extrabold);
  letter-spacing: -0.025em;
  line-height: 1.28;
  text-wrap: balance;
}

.viewer-summary {
  max-width: 68ch;
  margin: 9px 0 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  text-wrap: pretty;
}

.viewer-content {
  min-height: 480px;
  padding: 30px clamp(24px, 4vw, 52px) 40px;
}

.viewer-mindmap,
.viewer-ppt,
.viewer-cartoon {
  max-width: 1160px;
}

.viewer-ppt,
.viewer-cartoon {
  overflow: hidden;
}

.resource-pagination {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 18px;
  padding: 0 clamp(24px, 4vw, 52px) 52px;
}

.pagination-action,
.pagination-spacer {
  width: min(260px, 48%);
}

.pagination-action {
  justify-content: flex-start;
  gap: 10px;
  min-height: 62px;
  padding: 10px 13px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-secondary);
  text-align: left;
  font: inherit;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.pagination-action.next {
  justify-content: flex-end;
  text-align: right;
}

.pagination-action span {
  display: grid;
  gap: 2px;
}

.pagination-action small {
  color: var(--text-muted);
  font-size: 11px;
}

.pagination-action strong {
  color: var(--text);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
}

.pagination-action:hover {
  border-color: var(--border-strong);
  background: var(--surface-subtle);
  color: var(--color-primary-text);
}

.back-link:focus-visible,
.rail-item:focus-visible,
.pagination-action:focus-visible,
.primary-action:focus-visible,
.secondary-action:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 2px;
}

.page-state {
  display: grid;
  min-height: 58vh;
  place-content: center;
  justify-items: center;
  gap: 16px;
  padding: 32px;
  text-align: center;
}

.state-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 12px;
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.page-state h1,
.page-state p {
  margin: 0;
}

.page-state h1 {
  color: var(--text);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
}

.page-state p {
  max-width: 42ch;
  margin-top: 7px;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}

.state-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.primary-action,
.secondary-action {
  min-height: 38px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
}

.primary-action {
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: var(--color-text-strong);
}

.secondary-action {
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text-secondary);
}

.detail-skeleton {
  min-height: 100%;
}

.skeleton-topbar {
  display: flex;
  min-height: 64px;
  align-items: center;
  justify-content: space-between;
  padding: 0 clamp(18px, 2.4vw, 34px);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.skeleton-workspace {
  display: grid;
  grid-template-columns: 244px minmax(0, 1fr);
  min-height: calc(100vh - 64px);
}

.skeleton-rail {
  display: grid;
  align-content: start;
  gap: 8px;
  padding: 27px 24px;
  border-right: 1px solid var(--border);
  background: var(--surface-subtle);
}

.skeleton-viewer {
  display: grid;
  align-content: start;
  gap: 12px;
  max-width: 1120px;
  width: 100%;
  margin: 0 auto;
  padding: 37px clamp(24px, 4vw, 52px);
}

.skeleton-line,
.skeleton-resource,
.skeleton-canvas {
  display: block;
  overflow: hidden;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--surface-subtle) 25%, var(--color-border-light) 50%, var(--surface-subtle) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.25s ease-in-out infinite;
}

.skeleton-back { width: 76px; height: 13px; }
.skeleton-status { width: 72px; height: 13px; }
.skeleton-rail-title { width: 96px; height: 14px; margin-bottom: 10px; }
.skeleton-resource { height: 58px; }
.skeleton-overline { width: 88px; height: 12px; }
.skeleton-title { width: min(520px, 78%); height: 30px; }
.skeleton-copy { width: min(640px, 94%); height: 14px; }
.skeleton-copy.short { width: min(420px, 68%); }
.skeleton-canvas { height: 380px; margin-top: 18px; }

@keyframes skeleton-shimmer {
  to { background-position: -200% 0; }
}

@media (max-width: 900px) {
  .detail-layout,
  .skeleton-workspace {
    display: block;
  }

  .resource-rail {
    position: static;
    min-height: 0;
    overflow-x: auto;
    padding: 12px 14px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }

  .rail-heading { display: none; }
  .resource-nav { display: flex; width: max-content; }
  .rail-item { width: 160px; }
  .rail-index { display: none; }

  .skeleton-rail {
    display: none;
  }

  .skeleton-viewer {
    padding-top: 30px;
  }
}

@media (max-width: 700px) {
  .detail-header { min-height: 58px; }
  .bundle-name,
  .breadcrumb-separator { display: none; }
  .detail-header-main { gap: 0; }
  .complete-status { font-size: 11px; }

  .viewer-heading {
    padding-top: 26px;
    padding-bottom: 21px;
  }

  .viewer-title h1 { font-size: var(--text-lg); }
  .viewer-content { min-height: 360px; padding-top: 24px; }
  .resource-pagination { padding-bottom: 32px; }
}

@media (max-width: 480px) {
  .back-link span { display: none; }
  .back-link { width: 34px; justify-content: center; }
  .complete-status { gap: 4px; }
  .rail-item { width: 146px; min-height: 54px; }
  .pagination-action { width: calc(50% - 4px); }
  .pagination-action small { display: none; }
  .skeleton-canvas { height: 290px; }
}

@media (prefers-reduced-motion: reduce) {
  .resource-item-page *,
  .resource-item-page *::before,
  .resource-item-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
