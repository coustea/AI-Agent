<template>
  <div class="video">
    <div class="stage"><div class="visual"><i></i><i></i><b>{{ shortTopic }}</b></div><span>先从这个核心概念开始，一步步看清它的运行过程。</span><button type="button" aria-label="播放预演" tabindex="-1"><Play weight="fill" /></button></div>
    <div class="timeline"><span>00:00</span><i><b></b></i><span>{{ duration }}</span></div>
    <div class="story"><span v-for="scene in scenes" :key="scene">{{ scene }}</span></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PhPlay as Play } from '@phosphor-icons/vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['cartoon']; topic: string }>()
const shortTopic = computed(() => props.topic.length > 18 ? `${props.topic.slice(0, 18)}…` : props.topic)
const duration = computed(() => `${Math.floor(props.config.video_length_seconds / 60).toString().padStart(2, '0')}:${(props.config.video_length_seconds % 60).toString().padStart(2, '0')}`)
const scenes = computed(() => ({ concept: ['提出问题', '解释概念', '总结要点'], process: ['起始状态', '过程演化', '结果回顾'], comparison: ['对象 A', '差异对照', '对象 B'], practice: ['任务说明', '动手演示', '运行结果'] })[props.config.focus])
</script>

<style scoped>
.video { min-height: 414px; padding: 20px; background: #111c28; }.stage { position: relative; display: grid; min-height: 270px; place-items: center; overflow: hidden; border-radius: 10px; background: #1b2a38; }
.visual { position: relative; display: grid; width: 170px; height: 170px; place-items: center; border: 1px solid rgb(99 194 181 / 28%); border-radius: 50%; }.visual i { position: absolute; inset: 20px -30px; border: 1px solid rgb(99 194 181 / 22%); border-radius: 50%; }.visual i:nth-child(2) { inset: -20px 30px; }
.visual b { z-index: 2; max-width: 118px; color: #e6f5f2; font-size: 12px; line-height: 1.5; text-align: center; }.stage > span { position: absolute; right: 18px; bottom: 13px; left: 18px; padding: 7px 10px; color: #dce7ed; background: rgb(4 10 16 / 65%); font-size: 9px; text-align: center; }
button { position: absolute; display: grid; width: 34px; height: 34px; place-items: center; border: 0; border-radius: 50%; color: #18312e; background: #8dd4ca; pointer-events: none; } button svg { width: 13px; }
.timeline { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 9px; margin-top: 13px; color: #748495; font: 8px var(--font-mono, monospace); }.timeline i { height: 2px; background: #314252; }.timeline b { display: block; width: 28%; height: 100%; background: #66b8ad; }
.story { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; margin-top: 12px; }.story span { padding: 8px; border: 1px solid rgb(255 255 255 / 7%); color: #8392a1; background: #182532; font-size: 8px; text-align: center; }
</style>
