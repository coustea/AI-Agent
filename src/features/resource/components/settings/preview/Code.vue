<template>
  <div class="code">
    <header><span>{{ filename }}</span><small>{{ difficulty }} · {{ focus }}</small></header>
    <pre><code><i># {{ topic }}</i>
<b>{{ keyword }}</b> <em>learn_step</em>(concept):
    <b>if</b> <em>understood</em>(concept):
        <b>return</b> <q>"进入实践"</q>

    example = <em>build_example</em>(concept)
    <b>return</b> <em>explain</em>(example)</code></pre>
    <footer><small>OUTPUT</small><p>✓ 示例运行完成，下一步将逐行解释关键逻辑</p></footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['code']; topic: string }>()
const filename = computed(() => `practice.${({ python: 'py', c: 'c', cpp: 'cpp', java: 'java', go: 'go', javascript: 'js', typescript: 'ts' })[props.config.programming_language]}`)
const keyword = computed(() => props.config.programming_language === 'python' ? 'def' : 'function')
const difficulty = computed(() => ({ beginner: '入门', intermediate: '进阶', advanced: '挑战' })[props.config.difficulty])
const focus = computed(() => ({ syntax: '语法讲解', application: '工程应用', debugging: '调试分析' })[props.config.focus])
</script>

<style scoped>
.code { min-height: 414px; color: #d7e0ec; background: #15202d; }
header { display: flex; height: 42px; align-items: center; justify-content: space-between; padding: 0 18px; border-bottom: 1px solid rgb(255 255 255 / 8%); color: #aebccc; font: 10px var(--font-mono, monospace); }
header small { color: #718196; } pre { margin: 0; padding: 25px 22px; overflow: auto; font: 10px/2 var(--font-mono, monospace); }
i { color: #6f8497; font-style: normal; } b { color: #f1a66a; } em { color: #7dc8bd; font-style: normal; } q { color: #d7c87c; }
footer { margin: 0 20px; padding: 12px 14px; border: 1px solid rgb(255 255 255 / 7%); border-radius: 8px; background: rgb(0 0 0 / 14%); font: 9px/1.5 var(--font-mono, monospace); }
footer small { color: #708398; } footer p { margin: 5px 0 0; color: #8dd3b4; }
</style>
