<template>
  <div class="ppt-player-container" ref="containerRef">
    <!-- 判断如果是导出模式 (isExportMode)，则一次性渲染所有页面，并隐藏控制器 -->
    <template v-if="isExportMode">
      <div 
        v-for="(slide, index) in documentData.slides" 
        :key="`export-${index}`"
        class="slide-wrapper export-slide"
        :style="slide.metadata?.background_override ? { background: slide.metadata.background_override } : {}"
      >
        <component 
          :is="getLayoutComponent(documentData.config.template_id, slide.layout)"
          :data="slide.data"
          v-if="getLayoutComponent(documentData.config.template_id, slide.layout)"
        />
        <div v-else class="fallback-slide">
          <h3>缺少布局组件</h3>
          <p>主题 {{ documentData.config.template_id }} 未实现 {{ slide.layout }} 布局</p>
        </div>
      </div>
    </template>
    
    <!-- 正常预览模式，动态计算缩放比例，增加翻页动画 -->
    <template v-else>
      <div class="ppt-viewer" :style="{ transform: `scale(${scale})` }">
        <transition-group name="slide-fade">
          <div 
            v-for="(slide, index) in documentData.slides" 
            :key="`${slide.layout}-${index}`"
            v-show="currentIndex === index"
            class="slide-wrapper"
            :style="slide.metadata?.background_override ? { background: slide.metadata.background_override } : {}"
          >
            <component 
              :is="getLayoutComponent(documentData.config.template_id, slide.layout)"
              :data="slide.data"
              v-if="getLayoutComponent(documentData.config.template_id, slide.layout)"
            />
            <div v-else class="fallback-slide">
              <h3>缺少布局组件</h3>
              <p>主题 {{ documentData.config.template_id }} 未实现 {{ slide.layout }} 布局</p>
            </div>
          </div>
        </transition-group>
      </div>
      
      <!-- 播放器控制条 -->
      <div class="controls">
        <button @click="prevSlide" :disabled="currentIndex === 0" class="control-btn">上一页</button>
        <span class="page-indicator">{{ currentIndex + 1 }} / {{ documentData.slides.length }}</span>
        <button @click="nextSlide" :disabled="currentIndex === documentData.slides.length - 1" class="control-btn">下一页</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, defineAsyncComponent, onMounted, onUnmounted } from 'vue';
import type { PPTDocument } from './types/ppt';

const props = defineProps<{
  documentData: PPTDocument,
  isExportMode?: boolean
}>();

const currentIndex = ref(0);
const containerRef = ref<HTMLElement | null>(null);
const scale = ref(1);

const themeModules = import.meta.glob('./themes/**/*.vue');
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  calculateScale();
  
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      calculateScale();
    });
    resizeObserver.observe(containerRef.value);
  }
  
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  window.removeEventListener('keydown', handleKeyDown);
});

const toComponentName = (str: string) => {
  return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join('');
};

const getLayoutComponent = (theme: string, layout: string) => {
  const componentName = toComponentName(layout);
  const path = `./themes/${theme}/${componentName}.vue`;
  
  if (themeModules[path]) {
    return defineAsyncComponent(themeModules[path] as any);
  } else {
    console.warn(`[PPT Engine] 找不到对应组件: ${path}`);
    return null; 
  }
};

const prevSlide = () => {
  if (currentIndex.value > 0) currentIndex.value--;
};

const nextSlide = () => {
  if (currentIndex.value < props.documentData.slides.length - 1) currentIndex.value++;
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowRight' || e.key === 'PageDown') nextSlide();
  if (e.key === 'ArrowLeft' || e.key === 'PageUp') prevSlide();
};

const calculateScale = () => {
  if (!containerRef.value || props.isExportMode) return;
  const { width, height } = containerRef.value.getBoundingClientRect();
  
  if (width <= 32 || height <= 32) {
    scale.value = 0.1;
    return;
  }

  // 给周围留极小的均匀边距 (16px)
  const availableWidth = width - 32;
  const availableHeight = height - 32;

  const scaleX = availableWidth / 1280;
  const scaleY = availableHeight / 720;
  
  // 保持 16:9 比例缩放，并保证缩放比例为正数且合理
  scale.value = Math.max(0.05, Math.min(scaleX, scaleY));
};
</script>

<style scoped>
.ppt-player-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #E5E7EB;
  position: relative;
  overflow: hidden;
}

/* 导出模式专属样式，支持 Playwright 打印分页 */
.export-slide {
  width: 1280px;
  height: 720px;
  position: relative;
  page-break-after: always;
  background: #fff;
  overflow: hidden;
}

.ppt-viewer {
  width: 1280px;
  height: 720px;
  background: #fff;
  position: relative;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); 
  transform-origin: center center;
  overflow: hidden;
}

.slide-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.fallback-slide {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #FEE2E2;
  color: #991B1B;
  text-align: center;
}

.fallback-slide h3 {
  font-size: 32px;
  margin-bottom: 16px;
}

.controls {
  position: absolute;
  bottom: 20px;
  display: flex;
  gap: 20px;
  align-items: center;
  z-index: 10;
  background: rgba(255, 255, 255, 0.9);
  padding: 10px 24px;
  border-radius: 30px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(4px);
}

.control-btn {
  background: transparent;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 16px;
  transition: background 0.2s;
}

.control-btn:hover:not(:disabled) {
  background: #F3F4F6;
}

.control-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-indicator {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  min-width: 50px;
  text-align: center;
}

/* 页面切换动画 */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(50px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-50px);
}
</style>
