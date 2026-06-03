<template>
  <div class="video-renderer-container">
    <div class="video-grid" v-if="videoData">
      <!-- 左侧：播放器区域 -->
      <div class="player-column">
        <!-- 视频画面视口 -->
        <div class="video-viewport">
          <!-- 场景图片 -->
          <transition name="fade-slide" mode="out-in">
            <img 
              v-if="activeScene" 
              :key="activeScene.title" 
              :src="activeScene.image_url" 
              :alt="activeScene.title"
              class="viewport-image"
            />
          </transition>
          
          <!-- 暗度遮罩与悬浮元素 -->
          <div class="viewport-overlay">
            <div class="scene-title-badge">{{ activeScene?.title }}</div>
          </div>

          <!-- 底部字幕 -->
          <div class="subtitles-container">
            <transition name="sub-fade" mode="out-in">
              <p :key="activeSubtitle" class="subtitle-text" v-if="activeSubtitle">
                {{ activeSubtitle }}
              </p>
            </transition>
          </div>
        </div>

        <!-- 播放控制台 -->
        <div class="controls-panel">
          <!-- 进度条 -->
          <div class="progress-bar-container">
            <el-slider 
              v-model="currentTime" 
              :min="0" 
              :max="videoData.duration" 
              :format-tooltip="formatTime"
              @change="handleSliderChange"
              @input="handleSliderInput"
              class="video-slider"
            />
          </div>

          <div class="controls-row">
            <!-- 左侧：播放/暂停 & 时间 -->
            <div class="controls-left">
              <el-button 
                type="primary" 
                circle 
                class="play-btn"
                @click="togglePlay"
              >
                <el-icon v-if="isPlaying"><VideoPause /></el-icon>
                <el-icon v-else><VideoPlay /></el-icon>
              </el-button>

              <span class="time-display">
                {{ formatTime(currentTime) }} / {{ formatTime(videoData.duration) }}
              </span>
            </div>

            <!-- 中间：CSS 音频波形图动画（只在播放时跳动） -->
            <div class="audio-spectrum" :class="{ 'is-playing': isPlaying }">
              <span></span><span></span><span></span><span></span><span></span>
              <span></span><span></span><span></span><span></span><span></span>
            </div>

            <!-- 右侧：倍速、静音及导出 -->
            <div class="controls-right">
              <!-- 倍速控制 -->
              <el-dropdown trigger="click" @command="handleSpeedChange" class="speed-dropdown">
                <el-button size="small" class="glass-btn">
                  {{ playSpeed }}x <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="1.0">1.0x</el-dropdown-item>
                    <el-dropdown-item command="1.25">1.25x</el-dropdown-item>
                    <el-dropdown-item command="1.5">1.5x</el-dropdown-item>
                    <el-dropdown-item command="2.0">2.0x</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <!-- 静音切换 -->
              <el-button 
                circle 
                size="small" 
                class="glass-btn mute-btn"
                @click="isMuted = !isMuted"
              >
                <!-- 使用高对比度 SVG 音量图标 -->
                <svg v-if="isMuted" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="display:block">
                  <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.21.05-.42.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="display:block">
                  <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                </svg>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：章节列表与讲解脚本 -->
      <div class="script-column">
        <div class="panel-section-title">课程讲解脚本与章节</div>
        
        <!-- 章节选择 -->
        <div class="chapters-list">
          <div 
            v-for="(scene, idx) in videoData.scenes" 
            :key="idx"
            class="chapter-item"
            :class="{ 'is-active': activeSceneIndex === idx }"
            @click="seekToTime(scene.time)"
          >
            <div class="chapter-marker">0{{ idx + 1 }}</div>
            <div class="chapter-info">
              <div class="chapter-name">{{ scene.title }}</div>
              <div class="chapter-time">{{ formatTime(scene.time) }}</div>
            </div>
            <div class="playing-indicator" v-if="activeSceneIndex === idx && isPlaying">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <div class="divider"></div>

        <!-- 配音文稿 -->
        <div class="script-scroll-view" ref="scriptScroll">
          <div 
            v-for="(scene, sIdx) in videoData.scenes" 
            :key="'narration-' + sIdx"
            class="scene-narration-block"
            :class="{ 'is-active-block': activeSceneIndex === sIdx }"
          >
            <h5 class="scene-block-header">{{ scene.title }}</h5>
            <div class="scene-paragraphs">
              <span 
                v-for="(sub, subIdx) in scene.subtitles"
                :key="subIdx"
                class="script-sentence"
                :class="{ 'is-highlighted': currentTime >= (scene.time + sub.start) && currentTime <= (scene.time + sub.end) }"
                @click="seekToTime(scene.time + sub.start)"
              >
                {{ sub.text }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <el-empty description="无法解析视频资源课件" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, watch, nextTick } from 'vue'
import { VideoPlay, VideoPause, ArrowDown } from '@element-plus/icons-vue'
import { type ResourceArtifactLike, parseJsonObject } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
}>()

interface Subtitle {
  start: number
  end: number
  text: string
}

interface Scene {
  time: number
  title: string
  image_url: string
  narration: string
  subtitles: Subtitle[]
}

interface VideoData {
  title: string
  duration: number
  scenes: Scene[]
}

// 提取并解析数据
const videoData = computed<VideoData | null>(() => {
  let content = (typeof props.resultData === 'object' && props.resultData !== null)
    ? (props.resultData as Record<string, any>).content || props.resultData
    : props.resultData
  
  if (typeof content === 'string') {
    const match = content.match(/```json\s*([\s\S]*?)\s*```/)
    if (match) {
      content = match[1]
    }
  }
  return parseJsonObject(content) as VideoData | null
})

const currentTime = ref(0)
const isPlaying = ref(false)
const playSpeed = ref(1.0)
const isMuted = ref(false)
const scriptScroll = ref<HTMLElement | null>(null)

let playInterval: ReturnType<typeof setInterval> | null = null
const TICK_RATE = 100 // 100ms 刷新率

// 格式化时间 00:00
const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = Math.floor(seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

// 计算当前章节索引
const activeSceneIndex = computed(() => {
  if (!videoData.value) return 0
  const scenes = videoData.value.scenes
  for (let i = scenes.length - 1; i >= 0; i--) {
    const scene = scenes[i]
    if (scene && currentTime.value >= scene.time) {
      return i
    }
  }
  return 0
})

// 计算当前活动场景
const activeScene = computed(() => {
  if (!videoData.value) return null
  return videoData.value.scenes[activeSceneIndex.value] || null
})

// 计算当前活动字幕
const activeSubtitle = computed(() => {
  if (!activeScene.value) return ''
  const sceneTime = activeScene.value.time
  const localTime = currentTime.value - sceneTime
  
  const sub = activeScene.value.subtitles.find(
    s => localTime >= s.start && localTime <= s.end
  )
  return sub ? sub.text : ''
})

// 监听时间，实现右侧滚动与聚焦
watch(currentTime, () => {
  nextTick(() => {
    const activeEl = document.querySelector('.script-sentence.is-highlighted')
    if (activeEl && scriptScroll.value) {
      const container = scriptScroll.value
      const elTop = (activeEl as HTMLElement).offsetTop
      const containerHeight = container.clientHeight
      
      container.scrollTo({
        top: elTop - containerHeight / 2 + (activeEl as HTMLElement).clientHeight / 2,
        behavior: 'smooth'
      })
    }
  })
})

// 定时器控制逻辑
const startTimer = () => {
  if (playInterval) clearInterval(playInterval)
  const step = (TICK_RATE / 1000) * playSpeed.value
  
  playInterval = setInterval(() => {
    if (!videoData.value) return
    if (currentTime.value >= videoData.value.duration) {
      currentTime.value = videoData.value.duration
      pause()
      return
    }
    currentTime.value += step
  }, TICK_RATE)
}

const stopTimer = () => {
  if (playInterval) {
    clearInterval(playInterval)
    playInterval = null
  }
}

const togglePlay = () => {
  if (isPlaying.value) {
    pause()
  } else {
    play()
  }
}

const play = () => {
  if (!videoData.value) return
  if (currentTime.value >= videoData.value.duration) {
    currentTime.value = 0
  }
  isPlaying.value = true
  startTimer()
}

const pause = () => {
  isPlaying.value = false
  stopTimer()
}

const handleSpeedChange = (cmd: string) => {
  playSpeed.value = parseFloat(cmd)
  if (isPlaying.value) {
    startTimer()
  }
}

const seekToTime = (time: number) => {
  currentTime.value = time
}

const handleSliderChange = (val: any) => {
  currentTime.value = val
}

const handleSliderInput = (val: any) => {
  currentTime.value = val
}

onBeforeUnmount(() => {
  stopTimer()
})
</script>

<style scoped>
.video-renderer-container {
  width: 100%;
  box-sizing: border-box;
}

.video-grid {
  display: grid;
  grid-template-columns: 1.35fr 0.65fr;
  gap: 24px;
  align-items: stretch;
}

@media (max-width: 992px) {
  .video-grid {
    grid-template-columns: 1fr;
  }
}

/* ============================================================
   左栏：播放器样式
   ============================================================ */
.player-column {
  display: flex;
  flex-direction: column;
  background: #0B0F19; /* 更加纯净深邃的背景 */
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.04);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.video-viewport {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.viewport-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.viewport-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.7) 100%);
  pointer-events: none;
  z-index: 1;
}

.scene-title-badge {
  position: absolute;
  top: 16px;
  left: 16px;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #F1F5F9;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.5px;
}

/* 字幕样式 */
.subtitles-container {
  position: absolute;
  bottom: 24px;
  left: 5%;
  right: 5%;
  z-index: 2;
  text-align: center;
  pointer-events: none;
}

.subtitle-text {
  display: inline-block;
  background: rgba(10, 15, 30, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #FFFFFF;
  padding: 10px 24px;
  border-radius: 12px;
  font-size: 1.12rem;
  font-weight: 500;
  text-shadow: 0 2px 4px rgba(0,0,0,0.5);
  margin: 0;
  max-width: 90%;
  line-height: 1.45;
  word-break: break-word;
}

/* 播放控制栏 */
.controls-panel {
  padding: 16px 24px 20px;
  background: rgba(15, 20, 35, 0.98);
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.progress-bar-container {
  margin-bottom: 12px;
}

/* 覆盖 Element Plus 进度条为精美扁平样式 */
.progress-bar-container :deep(.el-slider) {
  --el-slider-main-bg-color: #3B82F6;
  --el-slider-runway-bg-color: rgba(255, 255, 255, 0.12);
  --el-slider-button-size: 12px;
  --el-slider-button-wrapper-size: 20px;
  height: 6px;
}
.progress-bar-container :deep(.el-slider__runway) {
  height: 4px !important;
}
.progress-bar-container :deep(.el-slider__bar) {
  height: 4px !important;
}
.progress-bar-container :deep(.el-slider__button) {
  border-color: #3B82F6 !important;
  background-color: #FFFFFF !important;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.5) !important;
}

.controls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.controls-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.play-btn {
  background: #3B82F6 !important;
  border: none !important;
  width: 40px !important;
  height: 40px !important;
  font-size: 1.2rem !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}
.play-btn:hover {
  transform: scale(1.08);
  background: #2563EB !important;
}

.time-display {
  color: #9CA3AF;
  font-family: monospace;
  font-size: 0.85rem;
}

/* 音频波形跳动动画 */
.audio-spectrum {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 24px;
}

.audio-spectrum span {
  display: block;
  width: 3px;
  height: 4px;
  background: #10B981;
  border-radius: 2px;
  transition: height 0.1s ease;
}

/* 播放时的跳动动画 */
.audio-spectrum.is-playing span:nth-child(1) { animation: bounce-wave 0.8s infinite alternate 0.1s; }
.audio-spectrum.is-playing span:nth-child(2) { animation: bounce-wave 0.8s infinite alternate 0.3s; }
.audio-spectrum.is-playing span:nth-child(3) { animation: bounce-wave 0.8s infinite alternate 0.5s; }
.audio-spectrum.is-playing span:nth-child(4) { animation: bounce-wave 0.8s infinite alternate 0.2s; }
.audio-spectrum.is-playing span:nth-child(5) { animation: bounce-wave 0.8s infinite alternate 0.4s; }
.audio-spectrum.is-playing span:nth-child(6) { animation: bounce-wave 0.8s infinite alternate 0.1s; }
.audio-spectrum.is-playing span:nth-child(7) { animation: bounce-wave 0.8s infinite alternate 0.6s; }
.audio-spectrum.is-playing span:nth-child(8) { animation: bounce-wave 0.8s infinite alternate 0.3s; }
.audio-spectrum.is-playing span:nth-child(9) { animation: bounce-wave 0.8s infinite alternate 0.5s; }
.audio-spectrum.is-playing span:nth-child(10) { animation: bounce-wave 0.8s infinite alternate 0.2s; }

@keyframes bounce-wave {
  0% { height: 4px; }
  100% { height: 22px; }
}

.controls-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.glass-btn {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: #D1D5DB !important;
  font-family: inherit;
  transition: all 0.2s ease !important;
}
.glass-btn:hover {
  background: rgba(255, 255, 255, 0.16) !important;
  color: #FFFFFF !important;
  border-color: rgba(255, 255, 255, 0.18) !important;
}

/* ============================================================
   右栏：目录与文稿样式
   ============================================================ */
.script-column {
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.02);
  height: 520px;
}

.panel-section-title {
  font-size: 0.92rem;
  font-weight: 800;
  color: #0F172A;
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.chapters-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.chapter-item:hover {
  background: #F1F5F9;
  border-color: #CBD5E1;
  transform: translateX(2px);
}

.chapter-item.is-active {
  background: rgba(59, 130, 246, 0.04);
  border-color: rgba(59, 130, 246, 0.22);
}

.chapter-marker {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #E2E8F0;
  color: #475569;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
}
.chapter-item.is-active .chapter-marker {
  background: #3B82F6;
  color: #FFFFFF;
}

.chapter-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
}

.chapter-name {
  font-size: 0.88rem;
  font-weight: 700;
  color: #334155;
}
.chapter-item.is-active .chapter-name {
  color: #1D4ED8;
}

.chapter-time {
  font-size: 0.8rem;
  color: #94A3B8;
  font-family: monospace;
}

/* 正在播放音柱 */
.playing-indicator {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 12px;
}
.playing-indicator span {
  width: 2px;
  height: 3px;
  background: #3B82F6;
  animation: play-pulse 0.6s infinite alternate;
}
.playing-indicator span:nth-child(1) { animation-delay: 0.1s; }
.playing-indicator span:nth-child(2) { animation-delay: 0.3s; }
.playing-indicator span:nth-child(3) { animation-delay: 0.2s; }

@keyframes play-pulse {
  0% { height: 3px; }
  100% { height: 12px; }
}

.divider {
  height: 1px;
  background: #E2E8F0;
  margin: 8px 0 16px;
}

/* 讲解文稿视图 */
.script-scroll-view {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.scene-narration-block {
  margin-bottom: 20px;
  opacity: 0.5;
  transition: opacity 0.3s ease;
}
.scene-narration-block.is-active-block {
  opacity: 1;
}

.scene-block-header {
  margin: 0 0 8px 0;
  font-size: 0.85rem;
  font-weight: 800;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.scene-narration-block.is-active-block .scene-block-header {
  color: #3B82F6;
}

.scene-paragraphs {
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.6;
}

.script-sentence {
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.25s ease;
}
.script-sentence:hover {
  background: #F1F5F9;
  color: #0F172A;
}

/* 发光高亮效果 */
.script-sentence.is-highlighted {
  background: rgba(59, 130, 246, 0.08) !important;
  color: #1D4ED8 !important;
  font-weight: 700;
  text-shadow: 0 0 1px rgba(59, 130, 246, 0.2);
}

/* ============================================================
   过渡与空状态
   ============================================================ */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.fade-slide-enter-from {
  opacity: 0;
  transform: scale(1.01);
}
.fade-slide-leave-to {
  opacity: 0;
}

.sub-fade-enter-active,
.sub-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.sub-fade-enter-from {
  opacity: 0;
  transform: translateY(3px);
}
.sub-fade-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px dashed #CBD5E1;
}
</style>
