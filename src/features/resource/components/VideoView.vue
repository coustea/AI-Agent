<template>
  <div class="frontend-video-engine">
    <div class="mockup-header">
      <div class="window-controls">
        <span class="dot close"></span>
        <span class="dot min"></span>
        <span class="dot max"></span>
      </div>
      <div class="mockup-title">{{ resourceTitle }}</div>

      <div class="export-actions">
        <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(totalDuration) }}</span>
        <button
            v-if="hasScenes"
            class="export-btn"
            :class="{ 'is-exporting': isExporting }"
            @click="startExportMP4"
            :disabled="isExporting"
        >
          {{ isExporting ? `渲染中... ${exportProgress}%` : '导出 MP4' }}
        </button>
      </div>
    </div>

    <div v-if="!hasScenes" class="empty-state">
      <div class="loader-circle"></div>
      <p>智能体正在重组知识链路，生成可视化分镜...</p>
    </div>

    <div
        v-else
        class="render-viewport"
        @mouseenter="controlsVisible = true"
        @mouseleave="controlsVisible = false"
        @click="togglePlay"
    >
      <canvas ref="previewCanvas" class="main-canvas" width="1920" height="1080"></canvas>

      <transition name="fade">
        <div v-if="!isPlaying && !isExporting" class="center-play-btn">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </div>
      </transition>

      <div class="engine-controls" :class="{ 'is-visible': controlsVisible || !isPlaying }">
        <div class="controls-wrapper">
          <button class="ctrl-btn play-btn" @click.stop="togglePlay">
            <svg v-if="!isPlaying" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
            <svg v-else viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
          </button>

          <div class="timeline-container" @click.stop="seekTimeline">
            <div
                v-for="(scene, index) in activeScenes"
                :key="'track-' + index"
                class="timeline-track"
                :style="{ flex: scene.duration || 4000 }"
            >
              <div class="timeline-fill" :style="{ width: getTrackProgress(index) + '%' }"></div>
            </div>
          </div>

          <button class="ctrl-btn fullscreen-btn" @click.stop="toggleFullscreen">
            <svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Muxer, ArrayBufferTarget } from 'mp4-muxer'
import { ElMessage } from 'element-plus'

const props = defineProps<{ resultData?: any }>()

// 新增归一化逻辑，兼容资源详情页 envelope
const videoPayload = computed(() => {
  const raw = props.resultData
  if (!raw) return null
  if (raw.content_json?.content) return raw.content_json.content
  if (raw.content_json) return raw.content_json
  if (raw.content) {
    try {
      return typeof raw.content === 'string' ? JSON.parse(raw.content) : raw.content
    } catch {
      return null
    }
  }
  return raw
})

const activeScenes = computed(() => {
  const scenes = videoPayload.value?.scenes
  return Array.isArray(scenes)
    ? scenes.map((scene: any) => ({
        id: scene.scene_id || `scene-${scene.index}`,
        duration: scene.duration_ms || 4000,
        title: scene.title || `分镜 ${scene.index || ''}`.trim(),
        desc: scene.narration || scene.visual_prompt || '',
        visualPrompt: scene.visual_prompt || '',
        visualType: scene.visual_type || 'card',
        captions: Array.isArray(scene.captions) ? scene.captions : [],
        imageUrl: scene.imageUrl || '',
        animation: scene.animation || 'zoom-in',
        filter: scene.filter || 'none'
      }))
    : []
})

const hasScenes = computed(() => activeScenes.value.length > 0)
const resourceTitle = computed(() => videoPayload.value?.title || '讲解视频')
const isWebCodecsSupported = typeof VideoEncoder !== 'undefined'

const totalDuration = computed(() => activeScenes.value.reduce((acc, cur) => acc + (cur.duration || 4000), 0))
const sceneTimepoints = computed(() => {
  return activeScenes.value.reduce((acc, _scene, idx) => {
    const previousStart = acc[idx - 1] ?? 0
    const previousScene = activeScenes.value[idx - 1]
    acc.push(idx === 0 ? 0 : previousStart + (previousScene?.duration || 4000))
    return acc
  }, [] as number[])
})

// 状态控制器
const previewCanvas = ref<HTMLCanvasElement | null>(null)
const isPlaying = ref(true)
const controlsVisible = ref(false)
const currentTime = ref(0)
const isExporting = ref(false)
const exportProgress = ref(0)

// 渲染管线内存
let imageCache = new Map<string, HTMLImageElement>()
let rafId: number | null = null
let lastTimestamp = 0

// --- 3. 图片资源预加载防跨域污染 ---
const preloadImages = async () => {
  imageCache.clear()
  const promises = activeScenes.value
    .filter(scene => scene.imageUrl)
    .map(scene => {
      return new Promise<void>((resolve) => {
        const img = new Image()
        img.crossOrigin = "anonymous" // 极其重要：防止 Canvas Tainted 导致无法导出
        img.onload = () => { imageCache.set(scene.id, img); resolve() }
        img.onerror = () => { resolve() }
        img.src = scene.imageUrl
      })
    })
  await Promise.all(promises)
}

watch(activeScenes, async () => {
  if (hasScenes.value) {
    isPlaying.value = false
    await preloadImages()
    currentTime.value = 0
    isPlaying.value = true
    lastTimestamp = performance.now()
  }
}, { deep: true, immediate: true })

// --- 4. 核心：Canvas 多智能体指令渲染虚拟机 ---
const drawFrameAtTime = (ctx: CanvasRenderingContext2D, timeMs: number, width = 1920, height = 1080) => {
  // 清空底板
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, width, height)

  if (!hasScenes.value) return

  // 4.1 时间轴定位当前分镜
  let currentIdx = 0
  for (let i = activeScenes.value.length - 1; i >= 0; i--) {
    if (timeMs >= (sceneTimepoints.value[i] ?? 0)) {
      currentIdx = i; break
    }
  }

  const scene = activeScenes.value[currentIdx]
  if (!scene) return

  const sceneStart = sceneTimepoints.value[currentIdx] ?? 0
  const sceneDuration = scene.duration || 4000
  const progress = Math.max(0, Math.min(1, (timeMs - sceneStart) / sceneDuration)) // 0.0 ~ 1.0

  const img = imageCache.get(scene.id)

  // 4.2 渲染图像层 (应用滤镜与运镜)
  if (img) {
    ctx.save()

    // 智能体滤镜解析 (Filter Mapping)
    const activeFilter = scene.filter || 'none'
    let filterString = 'none'
    if (activeFilter === 'grayscale') filterString = 'grayscale(100%)'
    if (activeFilter === 'blur') filterString = 'blur(10px)'
    if (activeFilter === 'sepia') filterString = 'sepia(80%)'
    if (activeFilter === 'contrast') filterString = 'contrast(150%) saturate(1.2)'
    ctx.filter = filterString

    // 智能体运镜解析 (Camera Transforms)
    const animType = scene.animation || 'zoom-in'
    let currentScale = 1.0
    let translateX = 0
    let translateY = 0
    const panRange = 60 // 像素平移范围

    switch (animType) {
      case 'zoom-in': currentScale = 1.0 + (0.1 * progress); break;
      case 'zoom-out': currentScale = 1.1 - (0.1 * progress); break;
      case 'pan-right': currentScale = 1.08; translateX = -panRange + (panRange * 2 * progress); break;
      case 'pan-left': currentScale = 1.08; translateX = panRange - (panRange * 2 * progress); break;
      case 'pan-down': currentScale = 1.08; translateY = -panRange + (panRange * 2 * progress); break;
      case 'static': currentScale = 1.0; break;
    }

    // Object-fit: cover 裁切计算
    const imgRatio = img.width / img.height
    const canvasRatio = width / height
    let drawW, drawH
    if (imgRatio > canvasRatio) { drawH = height; drawW = height * imgRatio }
    else { drawW = width; drawH = width / imgRatio }

    // 施加 Camera 矩阵
    ctx.translate(width / 2, height / 2) // 中心点
    ctx.translate(translateX, translateY) // 摇摄 (Pan)
    ctx.scale(currentScale, currentScale) // 推拉镜头 (Zoom)

    ctx.drawImage(img, -drawW / 2, -drawH / 2, drawW, drawH)
    ctx.restore() // 恢复矩阵和滤镜，防止污染后续的字幕渲染
  } else {
    // 渲染无图片时的 Canvas 场景卡片 (Storyboard card)
    ctx.save()
    // 绘制暗色渐变背景
    const grad = ctx.createLinearGradient(0, 0, width, height)
    grad.addColorStop(0, '#1e1b4b') // 深蓝/紫
    grad.addColorStop(1, '#0f172a') // 深灰蓝
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, width, height)

    // 绘制卡片框线或装饰
    ctx.strokeStyle = 'rgba(255,255,255,0.1)'
    ctx.lineWidth = 4
    ctx.strokeRect(40, 40, width - 80, height - 80)

    // 绘制视觉类型徽章 (Visual Type Badge)
    const badgeText = (scene.visualType || 'CARD').toUpperCase()
    ctx.fillStyle = 'rgba(255, 255, 255, 0.15)'
    ctx.font = 'bold 28px monospace'
    const badgeW = ctx.measureText(badgeText).width + 30
    ctx.fillRect(80, 80, badgeW, 48)
    ctx.fillStyle = '#38bdf8'
    ctx.fillText(badgeText, 95, 114)

    // 绘制画面提示 (Visual Prompt) 在屏幕中央
    ctx.fillStyle = 'rgba(255,255,255,0.7)'
    ctx.font = 'italic 38px system-ui, -apple-system, sans-serif'
    ctx.textAlign = 'center'
    
    // 自动折行绘制 visual_prompt
    const promptText = scene.visualPrompt || '无画面提示'
    const words = promptText.split('')
    let line = ''
    const lines: string[] = []
    const maxWidth = width - 300
    ctx.font = 'italic 38px system-ui, -apple-system, sans-serif'
    for (let n = 0; n < words.length; n++) {
      const testLine = line + words[n]
      const metrics = ctx.measureText(testLine)
      if (metrics.width > maxWidth && n > 0) {
        lines.push(line)
        line = words[n]
      } else {
        line = testLine
      }
    }
    lines.push(line)
    
    let startY = height / 2 - (lines.length - 1) * 25
    ctx.fillStyle = 'rgba(255,255,255,0.85)'
    for (let i = 0; i < lines.length; i++) {
      ctx.fillText(lines[i] || '', width / 2, startY + i * 50)
    }

    // 绘制字幕 (Captions) 列表，如果存在
    if (Array.isArray(scene.captions) && scene.captions.length > 0) {
      ctx.fillStyle = '#facc15' // 明黄色
      ctx.font = 'bold 32px system-ui, -apple-system, sans-serif'
      ctx.fillText(`字幕: ${scene.captions.join(' | ')}`, width / 2, height / 2 + 150 + (lines.length * 25))
    }

    ctx.restore()
  }

  // 4.3 渲染后期层 (暗角 Vignette，让文字清晰)
  const gradient = ctx.createRadialGradient(width/2, height/2, height*0.4, width/2, height/2, height)
  gradient.addColorStop(0, 'rgba(0,0,0,0)')
  gradient.addColorStop(1, 'rgba(0,0,0,0.85)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, width, height)

  const linear = ctx.createLinearGradient(0, height, 0, height*0.6)
  linear.addColorStop(0, 'rgba(0,0,0,0.9)')
  linear.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = linear
  ctx.fillRect(0, height*0.6, width, height*0.4)

  // 4.4 渲染图文包装层 (Lower Thirds 动效)
  const textDelayMs = 300
  const textProgress = Math.max(0, Math.min(1, (timeMs - sceneStart - textDelayMs) / 800))
  const easeOut = 1 - Math.pow(1 - textProgress, 3)

  ctx.save()
  ctx.globalAlpha = textProgress
  const yOffset = 25 * (1 - easeOut) // 浮现动效

  // 智能体全局主题皮肤解析
  const styleTheme = videoPayload.value?.style || 'standard'
  const titleColor = styleTheme === 'cyberpunk' ? '#facc15' : '#ffffff' // 赛博朋克用明黄
  const descColor = styleTheme === 'cyberpunk' ? '#2dd4bf' : '#38bdf8'  // 赛博朋克用青绿，标准用亮蓝

  // 主标题
  ctx.fillStyle = titleColor
  ctx.font = 'bold 56px system-ui, -apple-system, sans-serif'
  ctx.shadowColor = 'rgba(0,0,0,0.8)'
  ctx.shadowBlur = 15
  ctx.shadowOffsetY = 4
  ctx.fillText(scene.title, 80, height - 130 + yOffset)

  // 副文本
  ctx.fillStyle = descColor
  ctx.font = '500 34px system-ui, -apple-system, sans-serif'
  ctx.shadowColor = 'rgba(0,0,0,0.6)'
  ctx.shadowBlur = 10
  ctx.shadowOffsetY = 2
  ctx.fillText(scene.desc, 80, height - 60 + yOffset)
  ctx.restore()
}

// --- 5. 实时播放刷新循环 (60FPS) ---
const renderLoop = (timestamp: number) => {
  if (!lastTimestamp) lastTimestamp = timestamp
  const deltaTime = timestamp - lastTimestamp
  lastTimestamp = timestamp

  if (isPlaying.value && hasScenes.value && !isExporting.value) {
    currentTime.value += deltaTime
    if (currentTime.value >= totalDuration.value) currentTime.value = 0

    if (previewCanvas.value) {
      const ctx = previewCanvas.value.getContext('2d')
      if (ctx) drawFrameAtTime(ctx, currentTime.value, 1920, 1080)
    }
  }
  rafId = requestAnimationFrame(renderLoop)
}

// --- 6. 核心：WebCodecs API 离屏超速渲染导出 ---
const startExportMP4 = async () => {
  if (!isWebCodecsSupported) {
    ElMessage.warning('当前浏览器不支持 WebCodecs 导出视频，已降级为导出 JSON 脚本。')
    const blob = new Blob([JSON.stringify(videoPayload.value, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${resourceTitle.value.replace(/\s+/g, '_')}_script.json`
    a.click()
    URL.revokeObjectURL(url)
    return
  }

  if (!hasScenes.value || isExporting.value) return
  isExporting.value = true
  isPlaying.value = false

  try {
    const fps = 30
    const width = 1920
    const height = 1080
    const totalFrames = Math.floor((totalDuration.value / 1000) * fps)

    const muxer = new Muxer({
      target: new ArrayBufferTarget(),
      video: { codec: 'avc', width, height },
      fastStart: 'in-memory',
    })

    const encoder = new (window as any).VideoEncoder({
      output: (chunk: any, meta: any) => muxer.addVideoChunk(chunk, meta),
      error: (e: any) => console.error('H264 Encode Error:', e)
    })

    encoder.configure({
      codec: 'avc1.4d002a',
      width, height,
      bitrate: 8_000_000, // 高清 8Mbps
      framerate: fps,
    })

    const offscreenCanvas = document.createElement('canvas')
    offscreenCanvas.width = width
    offscreenCanvas.height = height
    const ctx = offscreenCanvas.getContext('2d')!

    for (let frameIndex = 0; frameIndex <= totalFrames; frameIndex++) {
      // 内存背压控制：防止密集编码把显存挤爆
      if (encoder.encodeQueueSize > 30) {
        await new Promise(resolve => setTimeout(resolve, 30))
      }

      const timeMs = (frameIndex / fps) * 1000
      drawFrameAtTime(ctx, timeMs, width, height)

      const timestampMicroseconds = frameIndex * (1_000_000 / fps)
      const frame = new (window as any).VideoFrame(offscreenCanvas, { timestamp: timestampMicroseconds })

      encoder.encode(frame, { keyFrame: frameIndex % fps === 0 })
      frame.close()

      exportProgress.value = Math.round((frameIndex / totalFrames) * 100)
    }

    await encoder.flush()
    muxer.finalize()

    const { buffer } = muxer.target
    const blob = new Blob([buffer], { type: 'video/mp4' })
    const url = URL.createObjectURL(blob)

    // 自动下载
    const a = document.createElement('a')
    a.href = url
    a.download = `${resourceTitle.value.replace(/\s+/g, '_')}_AIVideo.mp4`
    a.click()
    URL.revokeObjectURL(url)

  } catch (error) {
    console.error("MP4 Export failed:", error)
    ElMessage.error("导出失败，请检查浏览器是否支持 WebCodecs API")
  } finally {
    isExporting.value = false
    lastTimestamp = performance.now()
    isPlaying.value = true
  }
}

// --- 7. 辅助控制函数 ---
const togglePlay = () => { if (!isExporting.value) isPlaying.value = !isPlaying.value }
const getTrackProgress = (index: number) => {
  if (!hasScenes.value) return 0
  const scene = activeScenes.value[index]
  if (!scene) return 0

  const start = sceneTimepoints.value[index] ?? 0
  const duration = scene.duration || 4000
  const end = start + duration
  if (currentTime.value >= end) return 100
  if (currentTime.value <= start) return 0
  return ((currentTime.value - start) / duration) * 100
}
const seekTimeline = (e: MouseEvent) => {
  if (!hasScenes.value || isExporting.value) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  currentTime.value = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)) * totalDuration.value
}
const toggleFullscreen = () => {
  const el = document.querySelector('.frontend-video-engine')
  if (!document.fullscreenElement) el?.requestFullscreen()
  else document.exitFullscreen()
}
const formatTime = (ms: number) => {
  if (isNaN(ms) || ms === 0) return '00:00'
  const t = Math.floor(ms / 1000)
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`
}

onMounted(() => { rafId = requestAnimationFrame(renderLoop) })
onUnmounted(() => { if (rafId) cancelAnimationFrame(rafId) })
</script>

<style scoped>
.frontend-video-engine {
  width: 100%;
  max-width: 1024px;
  margin: 0 auto;
  border-radius: 12px;
  background: #09090b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.05);
  overflow: hidden;
  font-family: system-ui, -apple-system, sans-serif;
  user-select: none;
}

/* 顶部信息栏 */
.mockup-header {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: #18181b;
  border-bottom: 1px solid #27272a;
}
.window-controls { display: flex; gap: 8px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.close { background: #ef4444; }
.dot.min { background: #eab308; }
.dot.max { background: #22c55e; }

.mockup-title {
  margin-left: 16px;
  font-size: 13px;
  color: #a1a1aa;
  font-weight: 500;
}

/* 导出面板区 */
.export-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}
.time-display {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: #52525b;
}
.export-btn {
  background: #38bdf8;
  color: #0f172a;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.export-btn:hover { background: #7dd3fc; }
.export-btn.is-exporting {
  background: #3f3f46;
  color: #a1a1aa;
  cursor: wait;
}

.empty-state {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #a1a1aa;
  font-size: 14px;
}
.loader-circle {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(56, 189, 248, 0.2);
  border-top-color: #38bdf8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 渲染视口 */
.render-viewport {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  cursor: pointer;
  overflow: hidden;
}

/* 核心画板自适应 */
.main-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.center-play-btn {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 64px; height: 64px;
  background: rgba(255,255,255,0.1);
  backdrop-filter: blur(8px);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: white; border: 1px solid rgba(255,255,255,0.2);
}
.center-play-btn svg { width: 32px; height: 32px; fill: currentColor; margin-left: 4px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.engine-controls {
  position: absolute; bottom: 0; left: 0; width: 100%;
  padding: 20px;
  background: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
  opacity: 0; transform: translateY(10px); transition: all 0.3s ease;
}
.engine-controls.is-visible { opacity: 1; transform: translateY(0); }
.controls-wrapper { display: flex; align-items: center; gap: 16px; }

.ctrl-btn { background: none; border: none; color: #fff; cursor: pointer; padding: 4px; opacity: 0.8; }
.ctrl-btn:hover { opacity: 1; }
.ctrl-btn svg { width: 22px; height: 22px; fill: currentColor; }

.timeline-container {
  flex: 1; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; display: flex; gap: 4px; overflow: hidden;
}
.timeline-track { height: 100%; background: rgba(255,255,255,0.05); position: relative; }
.timeline-fill { position: absolute; top: 0; left: 0; height: 100%; background: #38bdf8; box-shadow: 0 0 10px rgba(56, 189, 248, 0.5); transition: width 0.05s linear; }
</style>
