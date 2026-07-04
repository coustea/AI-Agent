<template>
  <div class="map">
    <div class="grid"></div>
    <div class="root">{{ shortTopic }}</div>
    <div class="branch a"><b>核心概念</b><small>{{ leaf }}</small></div>
    <div class="branch b"><b>原理拆解</b><small>{{ config.max_depth }} 层结构</small></div>
    <div class="branch c"><b>实践应用</b><small>{{ relation }}</small></div>
    <i class="line la"></i><i class="line lb"></i><i class="line lc"></i>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['mindmap']; topic: string }>()
const shortTopic = computed(() => props.topic.length > 22 ? `${props.topic.slice(0, 22)}…` : props.topic)
const leaf = computed(() => ({ keyword: '关键词', brief_note: '简要注释', annotated: '详细说明' })[props.config.leaf_detail])
const relation = computed(() => props.config.show_relations ? '含跨分支关联' : '纯树状脉络')
</script>

<style scoped>
.map { position: relative; min-height: 414px; overflow: hidden; background: #fbfcfd; }
.grid { position: absolute; inset: 0; opacity: .45; background-image: radial-gradient(#ccd5df 1px, transparent 1px); background-size: 18px 18px; }
.root,.branch { position: absolute; z-index: 2; border: 1px solid #dce5e7; border-radius: 10px; background: #fff; box-shadow: 0 8px 22px rgb(35 53 73 / 7%); }
.root { top: 172px; left: 50%; width: 162px; padding: 13px; transform: translateX(-50%); color: #1d514e; background: #e9f5f3; font-size: 11px; font-weight: 800; text-align: center; }
.branch { display: grid; width: 126px; gap: 4px; padding: 11px 12px; color: #344355; font-size: 10px; }
.branch small { color: #8b96a4; font-size: 8px; }.a { top: 78px; left: 7%; }.b { top: 78px; right: 7%; }.c { right: 12%; bottom: 54px; }
.line { position: absolute; z-index: 1; width: 120px; height: 1px; background: #a9c9c4; transform-origin: left; }
.la { top: 177px; left: 27%; transform: rotate(18deg); }.lb { top: 177px; right: 25%; transform: rotate(162deg); }.lc { top: 208px; left: 59%; transform: rotate(34deg); }
</style>
