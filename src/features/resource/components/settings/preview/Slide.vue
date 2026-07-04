<template>
  <div class="slides">
    <aside>
      <div class="thumb active">
        <div class="thumb-bar"></div>
        <div class="thumb-line"></div>
        <div class="thumb-line short"></div>
        <span>01</span>
      </div>
      <div class="thumb">
        <div class="thumb-bar"></div>
        <div class="thumb-line"></div>
        <span>02</span>
      </div>
      <div class="thumb">
        <div class="thumb-line"></div>
        <div class="thumb-line short"></div>
        <span>03</span>
      </div>
    </aside>
    <main>
      <div class="accent-bar"></div>
      <div class="html-badge">HTML</div>
      <small>{{ style }} / 01</small>
      <h3>{{ topic }}</h3>
      <p>从一个关键问题开始，建立本次学习的核心理解框架。</p>
      <div class="tags">
        <span v-for="item in focus" :key="item">{{ item }}</span>
      </div>
      <b class="slide-num">01 — 08</b>
    </main>
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
.slides { display: grid; min-height: 320px; grid-template-columns: 64px 1fr; background: #f4f5f7; }
aside { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 16px 8px; border-right: 1px solid #e2e5ea; background: #f4f5f7; }
.thumb { position: relative; width: 44px; min-height: 30px; padding: 5px 6px 16px; border: 1px solid #dde1e8; border-radius: 3px; background: #fff; display: flex; flex-direction: column; gap: 4px; cursor: default; }
.thumb.active { border-color: #5c6bc0; box-shadow: 0 0 0 1px #5c6bc0; }
.thumb-bar { height: 4px; border-radius: 2px; background: #c5cae9; }
.thumb.active .thumb-bar { background: #5c6bc0; }
.thumb-line { height: 2px; border-radius: 1px; background: #e8eaf0; }
.thumb-line.short { width: 60%; }
.thumb span { position: absolute; bottom: 3px; right: 4px; font-size: 6px; color: #9fa8b0; }
main { position: relative; padding: 0 36px 28px; background: #fff; display: flex; flex-direction: column; justify-content: center; overflow: hidden; }
.accent-bar { position: absolute; top: 0; left: 0; right: 0; height: 5px; background: linear-gradient(90deg, #5c6bc0 0%, #7986cb 100%); }
.html-badge { position: absolute; top: 14px; right: 16px; padding: 2px 7px; border: 1px solid #c5cae9; border-radius: 4px; background: #e8eaf0; color: #5c6bc0; font-size: 8px; font-weight: 700; letter-spacing: .06em; }
main small { color: #7986cb; font-size: 8px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 8px; }
h3 { max-width: 380px; margin: 0 0 10px; color: #1a202c; font-size: 20px; line-height: 1.25; }
p { max-width: 340px; margin: 0; color: #718096; font-size: 10px; line-height: 1.7; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 20px; }
.tags span { padding: 5px 9px; border: 1px solid #e2e8f0; border-radius: 5px; background: #f7f8fc; color: #4a5568; font-size: 8px; }
.slide-num { position: absolute; right: 20px; bottom: 16px; color: #a0aec0; font-size: 8px; font-weight: 600; }
</style>
