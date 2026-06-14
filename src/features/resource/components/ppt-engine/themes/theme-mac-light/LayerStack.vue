<template>
  <div class="mac-light-slide mac-light-layer-stack">
    <div class="mac-window">
      <div class="mac-titlebar">
        <div class="mac-buttons">
          <span class="mac-btn close"></span>
          <span class="mac-btn minimize"></span>
          <span class="mac-btn maximize"></span>
        </div>
      </div>
      <div class="mac-content">
        <header class="slide-header">
          <h2 class="slide-title">{{ data.title }}</h2>
        </header>
        
        <div class="layout-body">
          <div class="left-col">
            <div class="stack-container">
              <div 
                v-for="(layer, index) in data.layers" 
                :key="index"
                class="stack-layer"
                :class="{ active: activeIndex === index }"
                @mouseenter="activeIndex = index"
                :style="{ zIndex: data.layers.length - index, transform: `translateY(${index * -15}px) scale(${1 - index * 0.05})` }"
              >
                <div class="layer-front">{{ layer.level_name }}</div>
                <div class="layer-top"></div>
                <div class="layer-side"></div>
              </div>
            </div>
          </div>
          
          <div class="right-col">
            <div class="detail-card" v-if="activeLayer">
              <h3 class="detail-title">{{ activeLayer.level_name }}</h3>
              <p class="detail-desc">{{ activeLayer.description }}</p>
              
              <div class="tag-group" v-if="activeLayer.protocols && activeLayer.protocols.length">
                <span class="tag" v-for="tag in activeLayer.protocols" :key="tag">{{ tag }}</span>
              </div>
              <div class="tag-group" v-if="activeLayer.components && activeLayer.components.length">
                <span class="tag" v-for="tag in activeLayer.components" :key="tag">{{ tag }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { LayerStackData } from '../../types/ppt';

const props = defineProps<{
  data: LayerStackData
}>();

const activeIndex = ref(0);
const activeLayer = computed(() => props.data.layers[activeIndex.value]);
</script>

<style scoped>
.mac-light-slide {
  width: 100%;
  height: 100%;
  background: #F9FAFB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  padding: 60px 80px;
  box-sizing: border-box;
}

.mac-window {
  width: 100%;
  height: 100%;
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.mac-titlebar {
  height: 38px;
  background: #F3F4F6;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  padding: 0 16px;
}

.mac-buttons {
  display: flex;
  gap: 8px;
}

.mac-btn { width: 12px; height: 12px; border-radius: 50%; }
.mac-btn.close { background: #FF5F56; border: 1px solid #E0443E; }
.mac-btn.minimize { background: #FFBD2E; border: 1px solid #DEA123; }
.mac-btn.maximize { background: #27C93F; border: 1px solid #1AAB29; }

.mac-content {
  flex: 1;
  padding: 40px 60px;
  display: flex;
  flex-direction: column;
}

.slide-header {
  margin-bottom: 40px;
  border-bottom: 2px solid #F3F4F6;
  padding-bottom: 20px;
}

.slide-title {
  font-size: 36px;
  color: #111827;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.layout-body {
  flex: 1;
  display: flex;
  gap: 60px;
}

.left-col {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1000px;
}

.stack-container {
  position: relative;
  width: 300px;
  height: 400px;
  transform-style: preserve-3d;
  transform: rotateX(20deg) rotateY(-20deg);
}

.stack-layer {
  position: absolute;
  width: 100%;
  height: 80px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
}

.stack-layer.active {
  transform: translateY(-20px) scale(1.05) translateZ(50px) !important;
}

.layer-front {
  position: absolute;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid #E5E7EB;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #374151;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(4px);
}

.stack-layer.active .layer-front {
  border-color: #3B82F6;
  color: #1D4ED8;
  box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.3);
}

.right-col {
  flex: 1;
  display: flex;
  align-items: center;
}

.detail-card {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  animation: fadeIn 0.4s ease-out;
}

.detail-title {
  font-size: 28px;
  color: #111827;
  margin: 0 0 20px 0;
  font-weight: 800;
}

.detail-desc {
  font-size: 18px;
  color: #4B5563;
  line-height: 1.6;
  margin: 0 0 30px 0;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 20px;
}

.tag {
  background: #EFF6FF;
  color: #2563EB;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  border: 1px solid #BFDBFE;
}

@keyframes fadeIn {
  0% { opacity: 0; transform: translateX(20px); }
  100% { opacity: 1; transform: translateX(0); }
}
</style>
