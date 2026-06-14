<template>
  <div class="logic-blue-slide logic-blue-cover">
    <div class="grid-background"></div>
    <div class="orb orb-left"></div>
    <div class="orb orb-right"></div>

    <div class="cover-layout">
      <div class="cover-content-left animate-slide-up">
        <div class="eyebrow">SYSTEM BRIEFING</div>
        <h1 class="main-title">{{ data.main_title }}</h1>
        <h2 class="sub-title" v-if="data.sub_title">{{ data.sub_title }}</h2>
        <div class="bottom-axis"></div>
      </div>

      <div class="cover-content-right animate-fade-in">
        <div class="meta-card">
          <div class="meta-item" v-if="data.lecturer">
            <span class="meta-label">PRESENTER</span>
            <span class="meta-value">{{ data.lecturer }}</span>
          </div>
          <div class="meta-item" v-if="data.date">
            <span class="meta-label">DATE</span>
            <span class="meta-value">{{ data.date }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">MODE</span>
            <span class="meta-value">Interactive Preview Deck</span>
          </div>
        </div>
      </div>
    </div>
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
  background:
    radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.24), transparent 36%),
    radial-gradient(circle at 85% 30%, rgba(14, 165, 233, 0.2), transparent 34%),
    linear-gradient(135deg, #07111f 0%, #0c1830 48%, #101f3a 100%);
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
  font-family: "Avenir Next", "Segoe UI", sans-serif;
}

.grid-background {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
  z-index: 1;
}

.orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(16px);
  opacity: 0.65;
}

.orb-left {
  width: 220px;
  height: 220px;
  left: 80px;
  top: 84px;
  background: radial-gradient(circle, rgba(96, 165, 250, 0.35), transparent 68%);
}

.orb-right {
  width: 280px;
  height: 280px;
  right: 70px;
  bottom: 52px;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.24), transparent 68%);
}

.cover-layout {
  position: relative;
  z-index: 10;
  width: 100%;
  height: 100%;
  display: flex;
  padding: 92px 100px 78px;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
  gap: 48px;
}

.cover-content-left {
  flex: 1;
  max-width: 62%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
  min-width: 0;
}

.eyebrow {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  background: rgba(15, 23, 42, 0.35);
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 2px;
  font-weight: 700;
  margin-bottom: 26px;
}

.main-title {
  font-size: 66px;
  color: transparent;
  background: linear-gradient(135deg, #f8fbff 0%, #c5dcff 52%, #7dd3fc 100%);
  background-clip: text;
  -webkit-background-clip: text;
  font-weight: 800;
  letter-spacing: -1.5px;
  margin: 0 0 18px;
  line-height: 1.08;
  text-align: left;
  text-wrap: balance;
}

.sub-title {
  font-size: 22px;
  color: rgba(226, 232, 240, 0.82);
  font-weight: 500;
  margin: 0;
  text-align: left;
  line-height: 1.6;
  max-width: 620px;
}

.cover-content-right {
  width: 31%;
  display: flex;
  justify-content: flex-end;
}

.meta-card {
  width: 100%;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.58), rgba(15, 23, 42, 0.28));
  backdrop-filter: blur(22px);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 24px;
  padding: 32px 32px 28px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  box-shadow: 0 24px 40px rgba(2, 6, 23, 0.28);
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.meta-label {
  font-size: 11px;
  font-weight: 600;
  color: #7dd3fc;
  letter-spacing: 1.8px;
}

.meta-value {
  font-size: 18px;
  color: #f8fafc;
  font-weight: 500;
}

.bottom-axis {
  width: min(560px, 100%);
  height: 1px;
  margin-top: 34px;
  background: linear-gradient(90deg, rgba(125, 211, 252, 0.55), rgba(255, 255, 255, 0.08));
}

.animate-slide-up {
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: fadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) 0.2s forwards;
  opacity: 0;
}

@keyframes slideUp {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}
</style>
