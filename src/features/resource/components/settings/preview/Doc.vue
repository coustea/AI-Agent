<template>
  <div class="doc">
    <small>{{ structure }} · {{ depth }}</small>
    <h3>{{ topic }}</h3>
    <p class="lead">{{ lead }}</p>
    <div class="outline"><b>本节脉络</b><span>01 核心概念</span><span>02 底层原理</span><span>03 实际应用</span></div>
    <article>
      <b>01</b>
      <div>
        <h5>先建立一个清晰的理解框架</h5>
        <p>{{ paragraph }}</p>
        <blockquote v-if="config.include_examples"><b>举个例子</b><span>把抽象机制放进真实学习场景中，对照输入、过程与结果理解它如何运作。</span></blockquote>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['content']; topic: string }>()
const structure = computed(() => ({ progressive: '渐进式引导', summary_first: '先总后分', exam_points: '考点驱动', case_driven: '案例驱动' })[props.config.structure])
const depth = computed(() => ({ quick: '快速讲述', standard: '标准深度', deep: '深度剖析' })[props.config.depth_level])
const lead = computed(() => ({
  exam_points: '围绕高频考点组织讲解，明确常见题型、判断依据与易错边界。',
  case_driven: '从一个真实问题出发，在解决过程里逐步拆开概念与实现方法。',
  summary_first: '先用一张全景图说明知识结构，再逐层进入关键细节。',
  progressive: '从直观认识开始，逐步走到底层机制，最后把概念放进真实实践中。',
})[props.config.structure])
const paragraph = computed(() => ({
  weak_points: '优先澄清容易混淆的概念，通过对比说明它们在边界条件和实际行为上的差异。',
  full_coverage: '覆盖定义、运行机制、常见用法和限制条件，让知识点形成完整闭环。',
  key_concepts: '聚焦最关键的概念与因果关系，先抓住理解后续内容所需的主干。',
})[props.config.focus_mode])
</script>

<style scoped>
.doc { padding: 30px 32px; color: #6d7989; }
small { color: #2c8f87; font-size: 9px; font-weight: 800; }
h3 { max-width: 520px; margin: 9px 0 8px; color: #182637; font-size: 22px; line-height: 1.3; letter-spacing: -.025em; }
p { margin: 0; font-size: 11px; line-height: 1.75; }
.lead { max-width: 560px; font-size: 12px; }
.outline { display: flex; flex-wrap: wrap; gap: 14px; margin: 24px 0; padding: 13px 0; border-block: 1px solid #edf0f3; font-size: 9px; }
.outline b { margin-right: auto; color: #647285; }
article { display: grid; grid-template-columns: 28px 1fr; gap: 14px; }
article > b { color: #2c8f87; font-size: 10px; }
h5 { margin: 0 0 7px; color: #263648; font-size: 13px; }
blockquote { display: grid; gap: 4px; margin: 14px 0 0; padding: 11px 13px; border-left: 2px solid #46a99b; background: #f3f8f7; font-size: 10px; line-height: 1.55; }
blockquote b { color: #276f68; }
</style>
