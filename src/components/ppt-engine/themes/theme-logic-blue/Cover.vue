<template>
  <div class="logic-blue-slide logic-blue-cover">
    <div class="cover-content">
      <div class="accent-bar"></div>
      <h1 class="main-title">{{ data.main_title }}</h1>
      <h2 class="sub-title" v-if="data.sub_title">{{ data.sub_title }}</h2>
      <div class="footer">
        <span class="lecturer" v-if="data.lecturer">{{ data.lecturer }}</span>
      </div>
    </div>
    
    <!-- 装饰元素 -->
    <div class="decoration circle-1"></div>
    <div class="decoration circle-2"></div>
    <div class="decoration dots"></div>
  </div>
</template>

<script setup lang="ts">
import type { CoverData } from '../../types/ppt';

defineProps<{
  data: CoverData
}>();
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  background-color: #0F172A;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.cover-content {
  position: relative;
  z-index: 10;
  width: 80%;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.accent-bar {
  width: 120px;
  height: 8px;
  background-color: #3B82F6;
  margin-bottom: 40px;
  border-radius: 4px;
}

.main-title {
  font-size: 80px;
  color: #FFFFFF;
  font-weight: 800;
  letter-spacing: -1px;
  margin-bottom: 24px;
  line-height: 1.2;
}

.sub-title {
  font-size: 36px;
  color: #94A3B8;
  font-weight: 400;
  margin-bottom: 60px;
}

.footer {
  margin-top: 40px;
  padding-top: 40px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  width: 60%;
}

.lecturer {
  font-size: 28px;
  color: #CBD5E1;
  font-weight: 500;
}

/* 装饰背景 */
.decoration {
  position: absolute;
  z-index: 1;
}

.circle-1 {
  width: 600px;
  height: 600px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(37,99,235,0.15) 0%, rgba(15,23,42,0) 70%);
  top: -200px;
  right: -200px;
}

.circle-2 {
  width: 800px;
  height: 800px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(56,189,248,0.1) 0%, rgba(15,23,42,0) 70%);
  bottom: -400px;
  left: -200px;
}

.dots {
  width: 200px;
  height: 200px;
  background-image: radial-gradient(#334155 2px, transparent 2px);
  background-size: 20px 20px;
  top: 100px;
  left: 100px;
  opacity: 0.3;
}
</style>
