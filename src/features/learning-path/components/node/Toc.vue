<template>
  <aside class="toc-panel">
    <div class="toc-card">
      <div class="side-head">
        <span>Contents</span>
        <strong>教程目录</strong>
      </div>

      <div v-if="items.length" class="toc-list">
        <button
          v-for="item in items"
          :key="item.id"
          type="button"
          :class="['toc-item', `level-${item.level}`, { active: activeId === item.id }]"
          @click="emit('select', item.id)"
        >
          {{ item.title }}
        </button>
      </div>

      <div v-else class="toc-empty">
        <p>当前教程暂未识别到标题目录。</p>
        <span>AI 教程会自动展示在中间阅读区。</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
export type TocItem = {
  id: string
  title: string
  level: number
}

defineProps<{
  items: TocItem[]
  activeId: string
}>()

const emit = defineEmits<{
  select: [id: string]
}>()
</script>

<style scoped>
.toc-panel {
  position: sticky;
  top: 18px;
  align-self: start;
}

.toc-card {
  overflow: hidden;
  border: 1px solid #dfe5ec;
  border-radius: 14px;
  background: #fff;
}

.side-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px;
  border-bottom: 1px solid #edf0f4;
}

.side-head span {
  color: #98a2b3;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.side-head strong {
  color: #263246;
  font-size: 13px;
}

.toc-list {
  display: flex;
  flex-direction: column;
  padding: 8px;
}

.toc-item {
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  color: #667085;
  background: transparent;
  font-size: 11px;
  line-height: 1.4;
  text-align: left;
  cursor: pointer;
}

.toc-item.level-3 {
  padding-left: 22px;
  font-size: 10px;
}

.toc-item:hover,
.toc-item.active {
  color: #24589d;
  background: #edf4fc;
}

.toc-empty {
  padding: 16px;
}

.toc-empty p,
.toc-empty span {
  margin: 0;
  color: #7a8494;
  font-size: 10px;
  line-height: 1.5;
}

.toc-empty span {
  display: block;
  margin-top: 5px;
  color: #98a2b3;
}
</style>
