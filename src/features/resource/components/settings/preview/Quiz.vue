<template>
  <div class="quiz">
    <div class="progress"><span>第 1 题 / 共 {{ config.question_count }} 题</span><i><b></b></i></div>
    <small>{{ difficulty }} · {{ style }}</small>
    <h3>关于“{{ shortTopic }}”，下面哪一项描述最准确？</h3>
    <div class="options">
      <div><b>A</b><span>只关注最终结果，不需要理解中间过程</span></div>
      <div class="answer"><b>B</b><span>先建立概念模型，再通过实例验证理解</span></div>
      <div><b>C</b><span>记住所有细节后才可以开始实践</span></div>
    </div>
    <p>作答后显示解析与对应知识点</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['quiz']; topic: string }>()
const shortTopic = computed(() => props.topic.length > 18 ? `${props.topic.slice(0, 18)}…` : props.topic)
const difficulty = computed(() => ({ basic: '概念巩固', adaptive: '自适应难度', exam: '考试强化' })[props.config.difficulty_mode])
const style = computed(() => ({ school: '期末风格', postgrad: '考研风格', certification: '认证考试', interview: '技术面试' })[props.config.exam_style])
</script>

<style scoped>
.quiz { padding: 28px 30px; }.progress { display: grid; gap: 8px; color: #8390a1; font-size: 9px; }.progress i { height: 3px; overflow: hidden; border-radius: 3px; background: #edf1f4; }.progress b { display: block; width: 18%; height: 100%; background: #3a9b91; }
small { display: inline-block; margin-top: 22px; color: #2f8179; font-size: 9px; font-weight: 800; } h3 { margin: 9px 0 18px; color: #182637; font-size: 17px; line-height: 1.45; }
.options { display: grid; gap: 9px; }.options div { display: flex; align-items: center; gap: 11px; padding: 11px 12px; border: 1px solid #e5e9ee; border-radius: 9px; color: #627083; font-size: 10px; }
.options b { display: grid; width: 22px; height: 22px; place-items: center; border-radius: 6px; color: #7c899a; background: #f2f4f7; font-size: 9px; }.options .answer { border-color: #abd5ce; color: #275d59; background: #f2f9f7; }.options .answer b { color: #fff; background: #3a9b91; }
p { margin: 14px 0 0; color: #9aa3af; font-size: 9px; }
</style>
