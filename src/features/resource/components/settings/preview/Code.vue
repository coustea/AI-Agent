<template>
  <div class="code">
    <header>
      <div class="tabs">
        <span class="tab active">{{ filename }}</span>
        <span class="tab">输出</span>
      </div>
      <small>{{ outputStyle }} · {{ focus }}</small>
    </header>
    <pre><code><i># {{ topic }}</i>
<b>{{ keyword }}</b> <em>learn_step</em>(concept):
    <b>if</b> <em>understood</em>(concept):
        <b>return</b> <q>"进入实践"</q>

    example = <em>build_example</em>(concept)
    <b>return</b> <em>explain</em>(example)</code></pre>
    <footer>
      <small>OUTPUT</small>
      <p>✓ 示例运行完成，下一步将逐行解释关键逻辑</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['code']; topic: string }>()
const filename = computed(() => `practice.${({ python: 'py', c: 'c', cpp: 'cpp', java: 'java', go: 'go', javascript: 'js', typescript: 'ts' })[props.config.programming_language]}`)
const keyword = computed(() => props.config.programming_language === 'python' ? 'def' : 'function')
const outputStyle = computed(() => ({ tutorial: '教学演示', reference: '参考实现', challenge: '挑战练习' })[props.config.output_style])
const focus = computed(() => ({ syntax: '语法讲解', application: '工程应用', debugging: '调试分析' })[props.config.focus])
</script>

<style scoped>
.code { min-height: 320px; color: #2d3748; background: #fafaf8; display: flex; flex-direction: column; }
header { display: flex; height: 42px; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid #e8eaf0; background: #f0f1f5; }
.tabs { display: flex; gap: 0; height: 100%; align-items: flex-end; }
.tab { padding: 0 14px; height: 32px; line-height: 32px; font: 10px var(--font-mono, monospace); color: #8b9ab0; border-radius: 6px 6px 0 0; cursor: default; }
.tab.active { background: #fafaf8; color: #2d3748; border: 1px solid #e8eaf0; border-bottom: 1px solid #fafaf8; margin-bottom: -1px; }
header small { color: #8b9ab0; font-size: 9px; letter-spacing: .04em; }
pre { margin: 0; padding: 20px 22px; overflow: auto; font: 11px/2 var(--font-mono, monospace); flex: 1; background: #fafaf8; }
i { color: #8b9ab0; font-style: normal; }
b { color: #4776ab; font-weight: 700; }
em { color: #3a7d44; font-style: normal; }
q { color: #b07a2a; quotes: none; }
footer { margin: 0 16px 16px; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f0faf5; font: 9px/1.5 var(--font-mono, monospace); }
footer small { color: #8b9ab0; font-weight: 700; letter-spacing: .05em; }
footer p { margin: 5px 0 0; color: #2d7a50; }
</style>
