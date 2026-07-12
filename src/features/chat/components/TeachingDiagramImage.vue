<template>
  <div
    class="diagram-image"
    :class="{ compact: props.compact, 'is-interactive': props.compact }"
    :role="props.compact ? 'button' : undefined"
    :tabindex="props.compact ? 0 : undefined"
    @click="handleExpand"
    @keydown.enter.prevent="handleExpand"
    @keydown.space.prevent="handleExpand"
  >
    <img
      v-if="props.diagram.image_url"
      :src="props.diagram.image_url"
      :alt="props.diagram.title || '教学图解'"
      loading="lazy"
    >
    <a
      v-if="props.showDownload && !props.compact"
      class="diagram-download"
      :href="props.diagram.image_url"
      download="diagram.png"
      data-testid="diagram-download-link"
      @click.stop
    >
      下载图片
    </a>
    <div v-if="props.compact" class="diagram-image-caption">
      <span>{{ props.diagram.title || '教学图解' }}</span>
      <i>查看大图</i>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TeachingDiagramImage } from '@/features/chat/types/chat'

const props = withDefaults(defineProps<{
  diagram: TeachingDiagramImage
  compact?: boolean
  showDownload?: boolean
}>(), {
  compact: false,
  showDownload: false,
})

const emit = defineEmits<{
  (e: 'expand', diagram: TeachingDiagramImage): void
}>()

const handleExpand = () => {
  if (props.compact) emit('expand', props.diagram)
}
</script>

<style scoped>
.diagram-image {
  position: relative;
  width: 100%;
  margin: 0;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--color-border) 84%, #26a69a);
  border-radius: 10px;
  background: #f8fbfb;
}

.diagram-image:not(.compact) {
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.diagram-image.is-interactive {
  cursor: zoom-in;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}

.diagram-image.is-interactive:hover,
.diagram-image.is-interactive:focus-visible {
  border-color: color-mix(in srgb, #2563eb 44%, var(--color-border));
  box-shadow: 0 14px 32px rgba(37, 99, 235, .12);
  outline: none;
  transform: translateY(-1px);
}

.diagram-image img {
  display: block;
  width: 100%;
  height: auto;
  max-height: 360px;
  object-fit: contain;
  background: #fff;
}

.diagram-image:not(.compact) img {
  width: 100%;
  max-height: none;
  border-radius: 0;
}

.diagram-download {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 4;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 18px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 780;
  text-decoration: none;
  background: linear-gradient(135deg, #26a69a, #2563eb);
  border-radius: 999px;
  box-shadow: 0 14px 34px rgba(37, 99, 235, .24);
}

.diagram-download:hover {
  filter: brightness(1.04);
}

.diagram-image-caption {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  color: #f8fafc;
  background: linear-gradient(180deg, transparent, rgba(15, 23, 42, .74));
}

.diagram-image-caption span {
  min-width: 0;
  overflow: hidden;
  font-size: 15px;
  font-weight: 760;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diagram-image-caption i {
  flex: 0 0 auto;
  font-size: 12px;
  font-style: normal;
  font-weight: 720;
  opacity: .9;
}
</style>
