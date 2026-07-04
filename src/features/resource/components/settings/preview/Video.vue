<template>
  <div class="video">
    <div class="stage">
      <div class="poster">
        <span class="topic-text">{{ shortTopic }}</span>
        <button type="button" aria-label="播放预演" tabindex="-1">
          <PhPlay weight="fill" />
        </button>
      </div>
      <div class="scene-bar">
        <span v-for="scene in scenes" :key="scene">{{ scene }}</span>
      </div>
    </div>
    <div class="controls">
      <div class="timeline">
        <span class="time">00:00</span>
        <div class="track"><div class="fill"></div></div>
        <span class="time">{{ duration }}</span>
      </div>
      <span class="mp4-badge">MP4</span>
    </div>
    <div class="story">
      <div class="scene-card" v-for="scene in scenes" :key="scene">
        <div class="scene-icon">▷</div>
        <span>{{ scene }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PhPlay } from '@phosphor-icons/vue'
import type { AnyAgentConfigs } from '../../../model/catalog'
const props = defineProps<{ config: AnyAgentConfigs['cartoon']; topic: string }>()
const shortTopic = computed(() => props.topic.length > 18 ? `${props.topic.slice(0, 18)}…` : props.topic)
const duration = computed(() => `${Math.floor(props.config.video_length_seconds / 60).toString().padStart(2, '0')}:${(props.config.video_length_seconds % 60).toString().padStart(2, '0')}`)
const scenes = computed(() => ({ concept: ['提出问题', '解释概念', '总结要点'], process: ['起始状态', '过程演化', '结果回顾'], comparison: ['对象 A', '差异对照', '对象 B'], practice: ['任务说明', '动手演示', '运行结果'] })[props.config.focus])
</script>

<style scoped>
.video { min-height: 320px; padding: 16px; background: #fff; display: flex; flex-direction: column; gap: 12px; }
.stage { position: relative; border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; aspect-ratio: 16 / 9; background: #e8f0fe; flex-shrink: 0; }
.poster { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; gap: 14px; }
.topic-text { max-width: 70%; color: #3c4a6b; font-size: 13px; font-weight: 600; text-align: center; line-height: 1.4; }
button { display: grid; width: 40px; height: 40px; place-items: center; border: 0; border-radius: 50%; color: #fff; background: #4f6ef7; box-shadow: 0 4px 16px rgb(79 110 247 / 30%); cursor: default; pointer-events: none; }
button svg { width: 15px; height: 15px; }
.scene-bar { position: absolute; bottom: 0; left: 0; right: 0; display: flex; gap: 0; background: rgb(255 255 255 / 82%); backdrop-filter: blur(4px); border-top: 1px solid rgb(0 0 0 / 6%); }
.scene-bar span { flex: 1; padding: 6px 4px; color: #4a5568; font-size: 7.5px; font-weight: 500; text-align: center; border-right: 1px solid rgb(0 0 0 / 6%); }
.scene-bar span:last-child { border-right: none; }
.controls { display: flex; align-items: center; gap: 10px; padding: 0 2px; }
.timeline { display: flex; flex: 1; align-items: center; gap: 8px; }
.time { color: #8b9ab0; font: 8px var(--font-mono, monospace); white-space: nowrap; }
.track { flex: 1; height: 3px; border-radius: 2px; background: #e2e8f0; }
.fill { width: 28%; height: 100%; border-radius: 2px; background: #4f9e9a; }
.mp4-badge { padding: 2px 7px; border: 1px solid #c5cae9; border-radius: 4px; background: #eef0fb; color: #5c6bc0; font-size: 8px; font-weight: 700; letter-spacing: .06em; white-space: nowrap; }
.story { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.scene-card { display: flex; flex-direction: column; align-items: center; gap: 5px; padding: 10px 6px; border: 1px solid #e8eaf0; border-radius: 8px; background: #fff; }
.scene-icon { color: #4f6ef7; font-size: 12px; }
.scene-card span { color: #4a5568; font-size: 8px; text-align: center; }
</style>
