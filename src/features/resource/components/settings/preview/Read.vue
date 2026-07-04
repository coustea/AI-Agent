<template>
  <div class="read">
    <header><small>{{ depth }}</small><h3>{{ topic }} · 延伸阅读</h3><p>按相关性与阅读成本排序，帮助你从课程内容自然过渡到更深入的资料。</p></header>
    <article v-for="item in items" :key="item.index"><b>{{ item.index }}</b><div><h5>{{ item.title }}</h5><p>{{ item.source }} · {{ language }}</p></div><span>{{ item.time }}</span></article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['reading']; topic: string }>()
const depth = computed(() => ({ course_extended: '课程延展', engineering: '工程实践', frontier: '前沿研究' })[props.config.reading_depth])
const language = computed(() => ({ chinese: '中文', english: '英文', both: '中英双语' })[props.config.language_preference])
const items = computed(() => [
  { index: '01', title: '核心机制：从概念模型到运行过程', source: '基础导读', time: '8 min' },
  { index: '02', title: '把关键原理放进真实项目中验证', source: props.config.focus === 'paper' ? '研究论文' : '实践指南', time: '12 min' },
  { index: '03', title: '常见误区、边界条件与进一步探索', source: '进阶资料', time: '15 min' },
].slice(0, Math.min(3, props.config.max_items)))
</script>

<style scoped>
.read { padding: 28px 30px; } header { padding-bottom: 18px; border-bottom: 1px solid #edf0f3; } small { color: #2f8179; font-size: 9px; font-weight: 800; }
h3 { margin: 7px 0; color: #182637; font-size: 18px; } header p { margin: 0; color: #778496; font-size: 10px; line-height: 1.6; }
article { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 10px; padding: 16px 0; border-bottom: 1px solid #edf0f3; } article > b { color: #b0b7c1; font-size: 9px; }
h5 { margin: 0 0 4px; color: #344355; font-size: 11px; } article p, article > span { margin: 0; color: #909aa8; font-size: 8px; }
</style>
