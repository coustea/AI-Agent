<template>
  <div class="mac-light-slide mac-light-process">
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
          <h2 class="slide-title">{{ data.flow_title }}</h2>
        </header>
        
        <div class="layout-body">
          <!-- Top Swimlanes & Timeline -->
          <div class="timeline-area">
            <div class="swimlane-headers">
              <div class="swimlane-header" v-for="lane in data.swimlanes" :key="lane">
                {{ lane }}
              </div>
            </div>
            
            <div class="timeline-track">
              <!-- Background lines for swimlanes -->
              <div class="swimlane-line" v-for="n in data.swimlanes.length" :key="`line-${n}`" :style="{ left: `${(n-0.5) * (100 / data.swimlanes.length)}%` }"></div>
              
              <div class="timeline-steps">
                <div 
                  v-for="(step, index) in data.timeline_steps" 
                  :key="index"
                  class="timeline-step"
                  :class="{ active: activeIndex === index }"
                  @mouseenter="activeIndex = index"
                >
                  <div class="step-time">{{ step.time_seq }}</div>
                  <div class="step-action-box">
                    <span class="action-text">{{ step.action }}</span>
                    <!-- Simple arrow logic based on index if needed, but here we just center it -->
                    <div class="action-arrow"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Bottom Detail Panel -->
          <div class="detail-panel">
            <div class="terminal-mockup">
              <div class="term-header">
                <span class="term-title">Internal State / 内部寄存器解析</span>
              </div>
              <div class="term-body">
                <div class="state-line" v-if="activeStep">
                  <span class="prompt">></span> <span class="command">Analyze step {{ activeStep.time_seq }}: {{ activeStep.action }}</span>
                </div>
                <div class="state-output" v-if="activeStep">
                  {{ activeStep.internal_state }}
                </div>
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
import type { ProcessFlowData } from '../../types/ppt';

const props = defineProps<{
  data: ProcessFlowData
}>();

const activeIndex = ref(0);
const activeStep = computed(() => props.data.timeline_steps[activeIndex.value]);
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

.mac-buttons { display: flex; gap: 8px; }
.mac-btn { width: 12px; height: 12px; border-radius: 50%; }
.mac-btn.close { background: #FF5F56; border: 1px solid #E0443E; }
.mac-btn.minimize { background: #FFBD2E; border: 1px solid #DEA123; }
.mac-btn.maximize { background: #27C93F; border: 1px solid #1AAB29; }

.mac-content {
  flex: 1;
  padding: 30px 40px;
  display: flex;
  flex-direction: column;
}

.slide-header {
  margin-bottom: 20px;
  border-bottom: 2px solid #F3F4F6;
  padding-bottom: 10px;
}

.slide-title {
  font-size: 32px;
  color: #111827;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.layout-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.timeline-area {
  flex: 5;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  padding: 20px;
  position: relative;
}

.swimlane-headers {
  display: flex;
  justify-content: space-around;
  border-bottom: 2px solid #E5E7EB;
  padding-bottom: 10px;
  margin-bottom: 20px;
}

.swimlane-header {
  font-weight: 800;
  color: #374151;
  font-size: 18px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timeline-track {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
}

.swimlane-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(229, 231, 235, 0.5);
  transform: translateX(-50%);
}

.timeline-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  z-index: 10;
}

.timeline-step {
  display: flex;
  align-items: center;
  gap: 20px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.timeline-step.active {
  border-color: #3B82F6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
  transform: translateX(5px);
}

.step-time {
  font-family: var(--font-mono, monospace);
  font-weight: 700;
  color: #6B7280;
  width: 80px;
}

.timeline-step.active .step-time {
  color: #2563EB;
}

.step-action-box {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}

.action-text {
  background: #EFF6FF;
  color: #1D4ED8;
  padding: 6px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 15px;
  z-index: 2;
}

.action-arrow {
  position: absolute;
  width: 100%;
  height: 2px;
  background: #BFDBFE;
  z-index: 1;
}

.detail-panel {
  flex: 4;
  display: flex;
}

.terminal-mockup {
  width: 100%;
  background: #1F2937;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);
}

.term-header {
  background: #374151;
  padding: 8px 16px;
  display: flex;
  align-items: center;
}

.term-title {
  color: #9CA3AF;
  font-size: 12px;
  font-family: var(--font-mono, monospace);
  font-weight: 600;
}

.term-body {
  padding: 20px;
  font-family: var(--font-mono, monospace);
  color: #E5E7EB;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prompt {
  color: #10B981;
  margin-right: 8px;
}

.command {
  color: #FCD34D;
}

.state-output {
  color: #9CA3AF;
  line-height: 1.6;
  white-space: pre-wrap;
  background: rgba(0,0,0,0.2);
  padding: 16px;
  border-radius: 6px;
  border-left: 3px solid #3B82F6;
}
</style>
