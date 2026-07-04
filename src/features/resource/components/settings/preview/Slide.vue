<template>
  <div class="slides">
    <aside><span class="active">01</span><span>02</span><span>03</span></aside>
    <main><small>{{ style }} / 01</small><h3>{{ topic }}</h3><p>从一个关键问题开始，建立本次学习的核心理解框架。</p><div><span v-for="item in focus" :key="item">{{ item }}</span></div><b>01 — 08</b></main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['ppt']; topic: string }>()
const style = computed(() => ({ concept: '概念精讲', case_driven: '案例驱动', problem_led: '问题引导', review: '复习提炼' })[props.config.explanation_style])
const focus = computed(() => props.config.focus.slice(0, 3).map(item => ({ core_concepts: '核心概念', cases: '案例分析', pitfalls: '易错提醒', derivation: '推导过程' })[item]))
</script>

<style scoped>
.slides { display: grid; min-height: 414px; grid-template-columns: 48px 1fr; color: #fff; background: #172330; } aside { display: flex; flex-direction: column; align-items: center; gap: 8px; padding-top: 18px; border-right: 1px solid rgb(255 255 255 / 8%); }
aside span { display: grid; width: 27px; height: 18px; place-items: center; border: 1px solid rgb(255 255 255 / 10%); color: #677687; font-size: 7px; } aside .active { border-color: #58b2a8; color: #a6ddd6; background: rgb(75 165 154 / 12%); }
main { position: relative; padding: 56px 42px 30px; background: linear-gradient(120deg, transparent 66%, rgb(76 165 154 / 12%) 66%); } main small { color: #73bdb4; font-size: 8px; font-weight: 800; letter-spacing: .1em; }
h3 { max-width: 410px; margin: 15px 0 12px; color: #f7fafc; font-size: 24px; line-height: 1.22; } p { max-width: 360px; margin: 0; color: #a9b5c1; font-size: 11px; line-height: 1.7; }
main div { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 26px; } main div span { padding: 6px 9px; border: 1px solid rgb(255 255 255 / 11%); border-radius: 5px; color: #c8d1da; font-size: 8px; } main > b { position: absolute; right: 24px; bottom: 20px; color: #647384; font-size: 8px; }
</style>
